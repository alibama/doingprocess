"""
Recognizer adapters. The neural sketch->BPMN step is now automated by default
via a LOCAL vision model on Ollama (qwen3.6). It stays swappable, and it stays
LOCAL-only: no third-party cloud service is contacted.

Backends:
  LocalVLMBackend  (default)  -> Ollama qwen3.6 vision, drafts BPMN from the image
  SelfHostedSketch2Process    -> your own local inference service, if you have it
  ManualBackend               -> blank canvas for hand annotation (fallback)
  MockBackend                 -> deterministic valid BPMN, for tests / offline smoke

Automated != unattended: treat every draft as a draft. Promotion to the corpus
still requires a human sign-off (see provenance.py / cli.py --sign).
"""
from __future__ import annotations
import base64
import json
import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from dataclasses import dataclass

BPMN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI = "http://www.omg.org/spec/BPMN/20100524/DI"
DC = "http://www.omg.org/spec/DD/20100524/DC"
DI = "http://www.omg.org/spec/DD/20100524/DI"
CAMUNDA = "http://camunda.org/schema/1.0/bpmn"
SPIFF = "http://spiffworkflow.org/bpmn/schema/1.0/core"

EMPTY_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
    targetNamespace="https://lexipedia.xyz/intake">
  <bpmn:process id="Process_intake" isExecutable="false"/>
</bpmn:definitions>
"""

PROMPT = """You convert a photo of a HAND-DRAWN legal-process map into BPMN 2.0 XML.
Output ONLY valid BPMN 2.0 XML. No prose. No markdown fences.

Conventions:
- Exactly one <bpmn:process>. Wrap it and lanes as needed.
- Shapes: thin circle=<bpmn:startEvent>, bold circle=<bpmn:endEvent>,
  box=<bpmn:task>, diamond with X or a yes/no=<bpmn:exclusiveGateway>,
  diamond with +=<bpmn:parallelGateway>. Connect with <bpmn:sequenceFlow>.
- A clock / a written deadline = a timer. Attach
  <bpmn:boundaryEvent attachedToRef="...">
    <bpmn:timerEventDefinition><bpmn:timeDuration>P15D</bpmn:timeDuration></bpmn:timerEventDefinition>
  </bpmn:boundaryEvent>. Convert "within 15 days" -> P15D, "20 business days" -> P20D.
- Put the handwritten action in each element's name="". If a law/rule/statute is
  written next to a step, append it: name="Warden responds (Rule 33-103)".
- Each role/column becomes a <bpmn:laneSet><bpmn:lane name="ROLE"> with
  <bpmn:flowNodeRef> children.
- Declare namespaces on <bpmn:definitions> using the bpmn: prefix.
- Do NOT emit BPMNDI / layout. Preserve labels verbatim; use [unclear] if illegible.

Skeleton:
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" targetNamespace="https://lexipedia.xyz/intake">
  <bpmn:process id="P" isExecutable="false">
    <bpmn:startEvent id="s1" name="..."/>
    <bpmn:task id="t1" name="..."/>
    <bpmn:sequenceFlow id="f1" sourceRef="s1" targetRef="t1"/>
    <bpmn:endEvent id="e1" name="..."/>
  </bpmn:process>
</bpmn:definitions>

Return the XML for the drawing now."""


# ---------------------------------------------------------------- coerce/repair
def _inject_ns(xml: str) -> str:
    m = re.search(r"<(bpmn:)?definitions\b", xml)
    if not m:
        return xml
    at = m.end()
    open_tag = xml[m.start():xml.find(">", m.start()) + 1]
    decls = []
    if "<bpmn:" in xml:  # prefixed but perhaps undeclared
        for p, u in [("bpmn", BPMN), ("bpmndi", BPMNDI), ("dc", DC), ("di", DI),
                     ("camunda", CAMUNDA), ("spiffworkflow", SPIFF)]:
            if f":{p}=" not in open_tag and (f"<{p}:" in xml or p == "bpmn"):
                decls.append(f'xmlns:{p}="{u}"')
    elif "xmlns" not in open_tag:  # no namespaces at all -> default to BPMN
        decls.append(f'xmlns="{BPMN}"')
    if not decls:
        return xml
    return xml[:at] + " " + " ".join(decls) + xml[at:]


def coerce_bpmn(text: str):
    """Turn a raw model reply into (bpmn_xml, ok). Strips fences/prose, repairs ns."""
    if not text or not text.strip():
        return EMPTY_BPMN, False
    t = text.strip()
    t = re.sub(r"```[a-zA-Z]*", "", t)          # drop code fences
    start = min([i for i in (t.find("<?xml"), t.find("<bpmn:definitions"),
                             t.find("<definitions")) if i != -1] or [-1])
    if start < 0:
        return EMPTY_BPMN, False
    m = re.search(r"</\w*:?definitions\s*>", t)
    xml = t[start:(m.end() if m else len(t))].strip()
    try:
        ET.fromstring(xml)
        return xml, True
    except ET.ParseError:
        repaired = _inject_ns(xml)
        try:
            ET.fromstring(repaired)
            return repaired, True
        except ET.ParseError:
            return EMPTY_BPMN, False


# ---------------------------------------------------------------------- backends
class RecognizerBackend:
    name = "base"

    def available(self) -> bool:
        return False

    def draft_bpmn(self, image_path: str) -> str:
        raise NotImplementedError


class ManualBackend(RecognizerBackend):
    name = "manual"

    def available(self) -> bool:
        return True

    def draft_bpmn(self, image_path: str) -> str:
        return EMPTY_BPMN


def _is_local(url: str) -> bool:
    return any(h in url for h in ("127.0.0.1", "localhost", "0.0.0.0", "::1"))


@dataclass
class LocalVLMBackend(RecognizerBackend):
    """Automated recognizer: a LOCAL Ollama vision model drafts BPMN from the image."""
    host: str = "http://127.0.0.1:11434"
    model: str = "qwen3.6"
    timeout: int = 300
    name: str = "local-vlm"

    def available(self) -> bool:
        if not _is_local(self.host):
            return False
        try:
            with urllib.request.urlopen(self.host + "/api/tags", timeout=3):
                return True
        except Exception:
            return False

    def draft_bpmn(self, image_path: str) -> str:
        if not _is_local(self.host):
            raise RuntimeError("VLM host must be a local address")
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": PROMPT, "images": [b64]}],
            "stream": False,
            "options": {"temperature": 0.1},
        }
        req = urllib.request.Request(
            self.host + "/api/chat",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise ConnectionError(f"Ollama not reachable at {self.host}: {e}")
        content = (data.get("message") or {}).get("content", "")
        xml, ok = coerce_bpmn(content)
        if not ok:
            raise ValueError("model reply did not contain parseable BPMN XML")
        return xml


@dataclass
class SelfHostedSketch2Process(RecognizerBackend):
    endpoint: str = ""
    name: str = "self-hosted-sketch2process"

    def available(self) -> bool:
        return bool(self.endpoint) and _is_local(self.endpoint)

    def draft_bpmn(self, image_path: str) -> str:
        if not self.available():
            raise RuntimeError("self-hosted recognizer endpoint not configured/local")
        with open(image_path, "rb") as f:
            data = f.read()
        req = urllib.request.Request(self.endpoint, data=data,
                                     headers={"Content-Type": "application/octet-stream"})
        with urllib.request.urlopen(req, timeout=120) as r:
            xml, ok = coerce_bpmn(r.read().decode("utf-8"))
        if not ok:
            raise ValueError("recognizer reply was not parseable BPMN")
        return xml


@dataclass
class ELCADetectionBackend(RecognizerBackend):
    """Adapter for the ELCA sketch-to-BPMN detector (ELCA-SA/BPMN_Detection).

    This is the purpose-built track: a torchvision detector returns pixel boxes
    + keypoints, and their toXML step emits BPMN 2.0 XML *with DI derived from
    those coordinates* — so it renders as drawn. Run their Streamlit space
    locally (scripts/run_elca.sh) and expose an image->BPMN endpoint, then point
    `endpoint` at it (local address enforced).

    Sovereignty note: the ELCA space uses Azure OCR for labels by default. For
    contributor data, run it with OCR disabled or swap its modules/OCR.py for a
    local engine (Tesseract/TrOCR); shapes still detect, labels get typed in the
    correction pass.
    """
    endpoint: str = ""          # e.g. "http://127.0.0.1:8600/recognize"
    name: str = "elca-detector"

    def available(self) -> bool:
        return bool(self.endpoint) and _is_local(self.endpoint)

    def draft_bpmn(self, image_path: str) -> str:
        if not self.available():
            raise RuntimeError("ELCA detector endpoint not configured/local")
        with open(image_path, "rb") as f:
            data = f.read()
        req = urllib.request.Request(self.endpoint, data=data,
                                     headers={"Content-Type": "application/octet-stream"})
        with urllib.request.urlopen(req, timeout=180) as r:
            xml, ok = coerce_bpmn(r.read().decode("utf-8"))
        if not ok:
            raise ValueError("ELCA detector reply was not parseable BPMN")
        return xml


class MockBackend(RecognizerBackend):
    """Deterministic lint-clean BPMN for tests / offline smoke runs."""
    name = "mock"

    def available(self) -> bool:
        return True

    def draft_bpmn(self, image_path: str) -> str:
        return """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
  targetNamespace="https://lexipedia.xyz/us/foia">
 <bpmn:process id="P" isExecutable="false">
  <bpmn:startEvent id="s1" name="FOIA request submitted (5 U.S.C. 552(a)(3))"/>
  <bpmn:task id="t1" name="Search and review (5 U.S.C. 552(b))"/>
  <bpmn:boundaryEvent id="d1" name="Determination due (5 U.S.C. 552(a)(6)(A))" attachedToRef="t1">
    <bpmn:timerEventDefinition><bpmn:timeDuration>P20D</bpmn:timeDuration></bpmn:timerEventDefinition>
  </bpmn:boundaryEvent>
  <bpmn:endEvent id="e1" name="Determination issued"/>
  <bpmn:sequenceFlow id="f1" sourceRef="s1" targetRef="t1"/>
  <bpmn:sequenceFlow id="f2" sourceRef="t1" targetRef="e1"/>
 </bpmn:process>
</bpmn:definitions>
"""


def get_backend(kind: str = "local-vlm", **kw) -> RecognizerBackend:
    kind = (kind or "local-vlm").lower()
    if kind in ("mock",):
        return MockBackend()
    if kind in ("manual", "blank"):
        return ManualBackend()
    if kind.startswith("self"):
        return SelfHostedSketch2Process(endpoint=kw.get("endpoint", ""))
    if kind.startswith("elca"):
        return ELCADetectionBackend(endpoint=kw.get("endpoint", ""))
    return LocalVLMBackend(host=kw.get("host", "http://127.0.0.1:11434"),
                           model=kw.get("model", "qwen3.6"),
                           timeout=int(kw.get("timeout", 300)))
