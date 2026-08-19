#!/usr/bin/env python3
"""
Local recognizer service — wraps the ELCA sketch-to-BPMN detector behind a tiny
HTTP API so the detector track runs headless and fully local (no Azure, no cloud).

Endpoints (all local):
  GET  /health                      -> {"ok": true, "bridge": "..."}
  POST /recognize   (image bytes)   -> BPMN 2.0 XML (with DI, renders as drawn)
  POST /detect      (image bytes)   -> {"token","boxes","labels","label_list","size"}
  POST /assemble    (JSON)          -> BPMN 2.0 XML   (apply corrected boxes -> create_XML)

Two bridges:
  FakeBridge  (default with --fake)  deterministic, no ML — used by tests/offline.
  ELCABridge  (default)              real detector: run inside the cloned ELCA repo
                                     (scripts/run_elca.sh sets --elca-dir).

Local-first: OCR is OFF by default (elements come back unlabeled; labels are typed
in the correction pass). This deliberately bypasses the ELCA space's Azure OCR so
scans never leave the machine. Pass --ocr tesseract to use a LOCAL engine instead.

Confirmed ELCA seam (from modules/streamlit_utils.py):
  get_faster_rcnn_model(len(object_dict)) , get_arrow_model(len(arrow_dict), 2)
  weights via huggingface_hub.hf_hub_download("ELCA-SA/BPMN_Detection", ...)
  full_pred = modules.eval.full_prediction(...)
  xml = modules.toXML.create_XML(full_pred, text_mapping, size_scale, scale)
"""
from __future__ import annotations
import argparse
import io
import json
import os
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FAKE_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" targetNamespace="https://lexipedia.xyz/intake">
  <bpmn:process id="P" isExecutable="false">
    <bpmn:startEvent id="s1" name="start"/>
    <bpmn:task id="t1" name="do the thing"/>
    <bpmn:endEvent id="e1" name="end"/>
    <bpmn:sequenceFlow id="f1" sourceRef="s1" targetRef="t1"/>
    <bpmn:sequenceFlow id="f2" sourceRef="t1" targetRef="e1"/>
  </bpmn:process>
  <bpmndi:BPMNDiagram id="D"><bpmndi:BPMNPlane id="PL" bpmnElement="P">
    <bpmndi:BPMNShape id="s1_di" bpmnElement="s1"><dc:Bounds x="140" y="120" width="36" height="36"/></bpmndi:BPMNShape>
    <bpmndi:BPMNShape id="t1_di" bpmnElement="t1"><dc:Bounds x="240" y="98" width="100" height="80"/></bpmndi:BPMNShape>
    <bpmndi:BPMNShape id="e1_di" bpmnElement="e1"><dc:Bounds x="400" y="120" width="36" height="36"/></bpmndi:BPMNShape>
  </bpmndi:BPMNPlane></bpmndi:BPMNDiagram>
</bpmn:definitions>
"""


class FakeBridge:
    name = "fake"

    def detect(self, image_bytes):
        token = uuid.uuid4().hex
        return {"token": token, "size": [600, 400],
                "label_list": ["task", "event", "gateway"],
                "boxes": [[240, 98, 100, 80], [140, 120, 36, 36]],
                "labels": [0, 1]}

    def assemble(self, payload):
        return FAKE_BPMN

    def recognize(self, image_bytes):
        return FAKE_BPMN


class ELCABridge:
    name = "elca"

    def __init__(self, elca_dir, score=0.5, ocr="none",
                 obj_weights=None, arrow_weights=None):
        self.elca_dir = elca_dir
        self.score = score
        self.ocr = ocr
        self.obj_weights = obj_weights or os.environ.get("ELCA_OBJ_WEIGHTS", "model_object.pth")
        self.arrow_weights = arrow_weights or os.environ.get("ELCA_ARROW_WEIGHTS", "model_arrow.pth")
        self._loaded = False
        self._store = {}          # token -> full_pred (for /detect -> /assemble)

    # ---- ELCA seam (runs on your machine, inside the cloned repo) -------------
    def _ensure(self):
        if self._loaded:
            return
        if self.elca_dir and self.elca_dir not in sys.path:
            sys.path.insert(0, self.elca_dir)
        import torch
        from huggingface_hub import hf_hub_download
        from modules.utils import object_dict, arrow_dict            # noqa
        from modules.train import get_faster_rcnn_model, get_arrow_model
        from modules.eval import full_prediction
        from modules.toXML import create_XML
        self._torch = torch
        self._full_prediction = full_prediction
        self._create_XML = create_XML
        self._object_dict, self._arrow_dict = object_dict, arrow_dict
        mo = get_faster_rcnn_model(len(object_dict))
        ma = get_arrow_model(len(arrow_dict), 2)
        op = hf_hub_download("ELCA-SA/BPMN_Detection", self.obj_weights)
        ap = hf_hub_download("ELCA-SA/BPMN_Detection", self.arrow_weights)
        mo.load_state_dict(torch.load(op, map_location="cpu")); mo.eval()
        ma.load_state_dict(torch.load(ap, map_location="cpu")); ma.eval()
        self._model_object, self._model_arrow = mo, ma
        self._loaded = True

    def _predict(self, image_bytes):
        """Return (full_pred, size_scale, scale). CONFIRM full_prediction's return
        shape against modules/eval.py on your machine (surfaced by --selftest)."""
        from PIL import Image
        import numpy as np
        self._ensure()
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        arr = np.array(img)
        out = self._full_prediction(self._model_object, self._model_arrow, arr,
                                    score_threshold=self.score)
        # full_prediction returns a tuple; the dict with 'boxes'/'labels' is full_pred.
        full_pred, size_scale, scale = _unpack_prediction(out, img.size)
        return full_pred, size_scale, scale

    def _text_mapping(self, image_bytes, full_pred):
        if self.ocr == "tesseract":
            try:
                return _tesseract_mapping(image_bytes, full_pred)
            except Exception:
                return {}
        return {}                 # local default: no OCR -> label in correction pass

    def recognize(self, image_bytes):
        full_pred, size_scale, scale = self._predict(image_bytes)
        tm = self._text_mapping(image_bytes, full_pred)
        return self._create_XML(full_pred, tm, size_scale, scale)

    def detect(self, image_bytes):
        full_pred, size_scale, scale = self._predict(image_bytes)
        token = uuid.uuid4().hex
        self._store[token] = (full_pred, size_scale, scale)
        boxes = [list(map(float, b)) for b in full_pred.get("boxes", [])]
        labels = [int(l) for l in full_pred.get("labels", [])]
        names = list(self._object_dict.values())
        return {"token": token, "boxes": boxes, "labels": labels,
                "label_list": names, "size": list(size_scale)}

    def assemble(self, payload):
        token = payload.get("token")
        if token not in self._store:
            raise KeyError("unknown token; call /detect first")
        full_pred, size_scale, scale = self._store.pop(token)
        if "boxes" in payload:
            full_pred["boxes"] = payload["boxes"]
        if "labels" in payload:
            full_pred["labels"] = payload["labels"]
        tm = payload.get("text_mapping", {})
        return self._create_XML(full_pred, tm, size_scale, scale)


def _unpack_prediction(out, pil_size):
    """Best-effort unpack of full_prediction's return into (full_pred, size_scale, scale)."""
    full_pred, size_scale, scale = None, list(pil_size), 1.0
    if isinstance(out, tuple):
        for item in out:
            if isinstance(item, dict) and ("boxes" in item or "labels" in item):
                full_pred = item
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                size_scale = list(item)
            elif isinstance(item, (int, float)):
                scale = float(item)
        if full_pred is None and out and isinstance(out[0], dict):
            full_pred = out[0]
    elif isinstance(out, dict):
        full_pred = out
    if full_pred is None:
        raise ValueError("could not locate full_pred dict in full_prediction() return; "
                         "bind _unpack_prediction to your modules/eval.py")
    return full_pred, size_scale, scale


def _tesseract_mapping(image_bytes, full_pred):
    import pytesseract
    from PIL import Image
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    words = [(data["text"][i], data["left"][i], data["top"][i],
              data["width"][i], data["height"][i])
             for i in range(len(data["text"])) if data["text"][i].strip()]
    # map each detected object box to words whose center falls inside it
    mapping = {}
    for idx, b in enumerate(full_pred.get("boxes", [])):
        x1, y1, x2, y2 = (b if len(b) == 4 else (0, 0, 0, 0))
        inside = [w for (w, wx, wy, ww, wh) in words
                  if x1 <= wx + ww / 2 <= x2 and y1 <= wy + wh / 2 <= y2]
        if inside:
            mapping[idx] = " ".join(inside)
    return mapping


class Handler(BaseHTTPRequestHandler):
    bridge = None

    def _send(self, code, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read(self):
        n = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(n) if n else b""

    def do_GET(self):
        if self.path == "/health":
            self._send(200, json.dumps({"ok": True, "bridge": self.bridge.name}))
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        try:
            if self.path == "/recognize":
                xml = self.bridge.recognize(self._read())
                self._send(200, xml, "application/xml")
            elif self.path == "/detect":
                self._send(200, json.dumps(self.bridge.detect(self._read())))
            elif self.path == "/assemble":
                payload = json.loads(self._read() or b"{}")
                self._send(200, self.bridge.assemble(payload), "application/xml")
            else:
                self._send(404, json.dumps({"error": "not found"}))
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))

    def log_message(self, *a):
        pass


def selftest(bridge, elca_dir):
    import glob
    imgs = glob.glob(os.path.join(elca_dir or ".", "images", "*")) or \
        glob.glob("samples/*.png")
    imgs = [p for p in imgs if p.lower().endswith((".png", ".jpg", ".jpeg"))]
    if not imgs:
        print("selftest: no example images found"); return 1
    p = imgs[0]
    print(f"selftest: recognizing {p} with bridge={bridge.name}")
    xml = bridge.recognize(open(p, "rb").read())
    import xml.etree.ElementTree as ET
    ET.fromstring(xml)
    has_di = "BPMNDiagram" in xml
    print(f"selftest OK: parseable BPMN, DI={'yes' if has_di else 'no'}, {len(xml)} bytes")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8600)
    ap.add_argument("--elca-dir", default=os.environ.get("ELCA_DIR", ""))
    ap.add_argument("--score", type=float, default=0.5)
    ap.add_argument("--ocr", choices=["none", "tesseract"], default="none")
    ap.add_argument("--fake", action="store_true", help="use the no-ML fake bridge")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    bridge = FakeBridge() if a.fake else ELCABridge(a.elca_dir, a.score, a.ocr)
    if a.selftest:
        return selftest(bridge, a.elca_dir)
    Handler.bridge = bridge
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"recognizer [{bridge.name}] on http://127.0.0.1:{a.port}  "
          f"(POST /recognize, /detect, /assemble)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
