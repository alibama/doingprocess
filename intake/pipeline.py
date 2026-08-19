"""
End-to-end intake pipeline (no UI): image bytes -> conditioned image -> BPMN
draft (recognizer) -> lint -> result dict. Fails soft so a missing recognizer
never crashes the run; it just yields an empty model flagged for attention.
"""
from __future__ import annotations
import tempfile
import os
import xml.etree.ElementTree as ET

import preprocess
import lint as bpmnlint
import layout


FLOW_NODES = {
    "task", "userTask", "manualTask", "scriptTask", "serviceTask",
    "businessRuleTask", "sendTask", "receiveTask", "callActivity", "subProcess",
    "startEvent", "endEvent", "intermediateCatchEvent", "intermediateThrowEvent",
    "boundaryEvent", "exclusiveGateway", "parallelGateway", "inclusiveGateway",
    "eventBasedGateway",
}


def count_flow_nodes(bpmn_xml: str) -> int:
    try:
        root = ET.fromstring(bpmn_xml)
    except ET.ParseError:
        return 0
    return sum(1 for el in root.iter() if el.tag.rsplit("}", 1)[-1] in FLOW_NODES)


def run(image_bytes: bytes, backend, *, condition_opts=None, known_processes=None):
    """Return a result dict. Never raises for recognizer/lint issues."""
    result = {"backend": backend.name, "notes": [], "ok": False}
    try:
        img = preprocess.load_image(image_bytes)
    except Exception as e:
        result["notes"].append(f"image decode failed: {e}")
        return result
    cond, report = preprocess.condition(img, **(condition_opts or {}))
    cond_png = preprocess.encode_png(cond)
    result["conditioned_png"] = cond_png
    result["condition_report"] = report.dict()

    tmp = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            tf.write(cond_png)
            tmp = tf.name
        bpmn_xml = backend.draft_bpmn(tmp)
        result["notes"].append(f"recognizer '{backend.name}' produced a draft")
    except Exception as e:
        from recognizer import EMPTY_BPMN
        bpmn_xml = EMPTY_BPMN
        result["notes"].append(f"recognizer unavailable ({e}); using empty model")
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)

    # give it a diagram so it renders in Camunda / bpmn-js.
    # A purpose-built detector (ELCA) already carries DI from pixel coordinates —
    # keep that (it matches the drawing). Only synthesize layout when absent.
    if "BPMNDiagram" in bpmn_xml:
        result["notes"].append("preserved recognizer-provided layout (DI)")
    else:
        try:
            bpmn_xml = layout.add_di(bpmn_xml)
            result["notes"].append("added synthetic layout (DI)")
        except Exception as e:
            result["notes"].append(f"layout skipped: {e}")

    result["bpmn"] = bpmn_xml
    n = count_flow_nodes(bpmn_xml)
    result["flow_nodes"] = n
    if n == 0:
        result["notes"].append("no flow nodes recognized — needs manual annotation")

    try:
        findings, summary = bpmnlint.lint(bpmn_xml, known_processes=known_processes)
        result["findings"] = [f.dict() for f in findings]
        result["lint_summary"] = summary
    except ValueError as e:
        result["findings"] = []
        result["lint_summary"] = {"errors": 1, "warnings": 0, "clean": False}
        result["notes"].append(f"lint could not parse BPMN: {e}")

    result["ok"] = (result["lint_summary"]["errors"] == 0 and n > 0)
    return result
