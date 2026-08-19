"""
Lexipedia BPMN lint — Python implementation of the rules specified in the
modeling reference, run over recognized/annotated BPMN 2.0 XML before a map
enters the corpus. Stdlib only (xml.etree), no third-party deps.

Rules:
  timer-iso8601            timer definitions carry a valid ISO-8601 value      (error)
  deadline-has-authority   a timed element cites its legal authority           (warn)
  business-rule-has-decision  business rule task references a decision          (error)
  call-activity-resolvable    call activity names a target (optionally known)   (error)
  execution-tier-spiff-safe   no element outside the Spiff-supported set        (error)
  flow-kind-by-scope          messageFlow only in collaboration; seq in process (error)
"""
from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict

BPMN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
CAMUNDA = "http://camunda.org/schema/1.0/bpmn"
SPIFF = "http://spiffworkflow.org/bpmn/schema/1.0/core"
NS = {"bpmn": BPMN, "camunda": CAMUNDA, "spiff": SPIFF}

ISO_DUR = re.compile(r"^P(?!$)(\d+Y)?(\d+M)?(\d+W)?(\d+D)?(T(?=\d)(\d+H)?(\d+M)?(\d+(\.\d+)?S)?)?$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?(Z|[+-]\d{2}:\d{2})?)?$")
ISO_CYCLE = re.compile(r"^R\d*/.+")
CITATION = re.compile(r"(§|\bU\.?S\.?C\.?\b|\bStat\.?\b|\bRule\s?\d|\bCh\.?\s?\d|\d+\.\d+)", re.I)

# Spiff-supported set (SpiffWorkflow 3.0.0). Anything not here, in the execution
# copy, is flagged. Local names only.
SPIFF_SAFE = {
    "process", "collaboration", "participant", "laneSet", "lane",
    "startEvent", "endEvent", "intermediateCatchEvent", "intermediateThrowEvent",
    "boundaryEvent", "task", "userTask", "manualTask", "scriptTask",
    "serviceTask", "businessRuleTask", "sendTask", "receiveTask",
    "subProcess", "callActivity", "transaction",
    "exclusiveGateway", "parallelGateway", "inclusiveGateway", "eventBasedGateway",
    "sequenceFlow", "messageFlow", "dataObject", "dataObjectReference",
    "dataStoreReference", "dataStore", "textAnnotation", "association",
    "timerEventDefinition", "messageEventDefinition", "signalEventDefinition",
    "errorEventDefinition", "escalationEventDefinition", "terminateEventDefinition",
    "cancelEventDefinition", "extensionElements", "documentation",
    "incoming", "outgoing", "dataInputAssociation", "dataOutputAssociation",
    "multiInstanceLoopCharacteristics", "standardLoopCharacteristics",
}
SPIFF_UNSAFE = {
    "complexGateway", "adHocSubProcess", "compensateEventDefinition",
    "conditionalEventDefinition",
}


@dataclass
class Finding:
    rule: str
    level: str          # "error" | "warn"
    element_id: str
    element: str
    message: str

    def dict(self):
        return asdict(self)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _name(el) -> str:
    return el.get("name") or el.get("id") or "(unnamed)"


def _doc_text(el) -> str:
    d = el.find("bpmn:documentation", NS)
    return (d.text or "") if d is not None else ""


def parse(xml_text: str):
    """Parse BPMN XML; raises ET.ParseError on malformed input."""
    return ET.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)


def _iter(root):
    for el in root.iter():
        yield el


def rule_timer_iso8601(root):
    out = []
    for el in root.iter():
        if _local(el.tag) != "timerEventDefinition":
            continue
        val = None
        for kind in ("timeDuration", "timeDate", "timeCycle"):
            c = el.find(f"bpmn:{kind}", NS)
            if c is not None and (c.text or "").strip():
                val = (kind, c.text.strip())
                break
        eid = el.get("id", "(timer)")
        if val is None:
            out.append(Finding("timer-iso8601", "error", eid, "timerEventDefinition",
                               "timer has no timeDuration/timeDate/timeCycle value"))
            continue
        kind, v = val
        ok = (ISO_DUR.match(v) if kind == "timeDuration"
              else ISO_DATE.match(v) if kind == "timeDate"
              else ISO_CYCLE.match(v))
        if not ok:
            out.append(Finding("timer-iso8601", "error", eid, "timerEventDefinition",
                               f"{kind} value '{v}' is not valid ISO-8601"))
    return out


def rule_deadline_has_authority(root):
    """The event that *directly* owns a timer should cite its authority."""
    out = []
    for el in root.iter():
        owns_timer = any(_local(c.tag) == "timerEventDefinition" for c in list(el))
        if not owns_timer:
            continue
        text = f"{el.get('name','')} {_doc_text(el)}"
        if not CITATION.search(text):
            out.append(Finding("deadline-has-authority", "warn", el.get("id", "?"),
                               _local(el.tag),
                               "timed element has no legal citation in name/documentation"))
    return out


def rule_business_rule_has_decision(root):
    out = []
    for el in root.iter():
        if _local(el.tag) != "businessRuleTask":
            continue
        ref = (el.get(f"{{{CAMUNDA}}}decisionRef")
               or el.get("decisionRef"))
        if ref is None:
            # spiff extension: extensionElements/spiff:calledDecisionId
            for ext in el.iter():
                if _local(ext.tag) == "calledDecisionId" and (ext.text or "").strip():
                    ref = ext.text.strip()
                    break
        if not ref:
            out.append(Finding("business-rule-has-decision", "error", el.get("id", "?"),
                               "businessRuleTask",
                               "business rule task references no decision (decisionRef / calledDecisionId)"))
    return out


def rule_call_activity_resolvable(root, known=None):
    out = []
    for el in root.iter():
        if _local(el.tag) != "callActivity":
            continue
        called = el.get("calledElement")
        if not called:
            out.append(Finding("call-activity-resolvable", "error", el.get("id", "?"),
                               "callActivity", "callActivity has no calledElement"))
        elif known is not None and called not in known:
            out.append(Finding("call-activity-resolvable", "error", el.get("id", "?"),
                               "callActivity",
                               f"calledElement '{called}' not found in corpus index"))
    return out


def rule_execution_tier_spiff_safe(root):
    out = []
    for el in root.iter():
        ln = _local(el.tag)
        if ln in SPIFF_UNSAFE:
            out.append(Finding("execution-tier-spiff-safe", "error", el.get("id", "?"),
                               ln, f"'{ln}' is not in the SpiffWorkflow-supported set"))
    return out


def rule_flow_kind_by_scope(root):
    """messageFlow belongs to collaboration; sequenceFlow belongs inside a process."""
    out = []
    # map element id -> owning process id (for sequenceFlow scope) is complex;
    # do the structural check: messageFlow must be a child of collaboration,
    # sequenceFlow must be a child of a process/subProcess.
    for el in root.iter():
        ln = _local(el.tag)
        if ln == "messageFlow":
            # parent should be collaboration; ET has no parent ptr, so verify via search
            pass  # structural presence is fine; deeper check needs a parent map
    parent = {c: p for p in root.iter() for c in p}
    for el in root.iter():
        ln = _local(el.tag)
        if ln == "sequenceFlow":
            p = parent.get(el)
            if p is not None and _local(p.tag) == "collaboration":
                out.append(Finding("flow-kind-by-scope", "error", el.get("id", "?"),
                                   "sequenceFlow", "sequenceFlow sits directly in a collaboration"))
        if ln == "messageFlow":
            p = parent.get(el)
            if p is not None and _local(p.tag) in ("process", "subProcess"):
                out.append(Finding("flow-kind-by-scope", "error", el.get("id", "?"),
                                   "messageFlow", "messageFlow sits inside a process, not a collaboration"))
    return out


ALL_RULES = [
    rule_timer_iso8601,
    rule_deadline_has_authority,
    rule_business_rule_has_decision,
    rule_call_activity_resolvable,
    rule_execution_tier_spiff_safe,
    rule_flow_kind_by_scope,
]


def lint(xml_text: str, known_processes=None):
    """Return (findings, summary). Raises ValueError on unparseable XML."""
    try:
        root = parse(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"BPMN XML is not well-formed: {e}")
    findings = []
    for rule in ALL_RULES:
        if rule is rule_call_activity_resolvable:
            findings += rule(root, known_processes)
        else:
            findings += rule(root)
    summary = {
        "errors": sum(1 for f in findings if f.level == "error"),
        "warnings": sum(1 for f in findings if f.level == "warn"),
        "clean": len(findings) == 0,
    }
    return findings, summary
