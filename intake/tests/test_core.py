import os, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import preprocess, lint, provenance

SAMPLE_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
  xmlns:camunda="http://camunda.org/schema/1.0/bpmn"
  targetNamespace="https://lexipedia.xyz/us-fl/foia">
 <bpmn:collaboration id="C">
   <bpmn:messageFlow id="mf1" sourceRef="t_serve" targetRef="t_reply"/>
 </bpmn:collaboration>
 <bpmn:process id="P" isExecutable="true">
  <bpmn:startEvent id="s1" name="FOIA request submitted"/>
  <bpmn:userTask id="t_serve" name="Serve notice"/>
  <bpmn:boundaryEvent id="dl" name="Determination due (5 U.S.C. 552(a)(6)(A))" attachedToRef="t_serve">
    <bpmn:timerEventDefinition><bpmn:timeDuration>P20D</bpmn:timeDuration></bpmn:timerEventDefinition>
  </bpmn:boundaryEvent>
  <bpmn:boundaryEvent id="dl_bad" name="Appeal window" attachedToRef="t_serve">
    <bpmn:timerEventDefinition><bpmn:timeDuration>20 days</bpmn:timeDuration></bpmn:timerEventDefinition>
  </bpmn:boundaryEvent>
  <bpmn:businessRuleTask id="brt_ok" name="Determine eligibility" camunda:decisionRef="ExemptionApplies"/>
  <bpmn:businessRuleTask id="brt_bad" name="Classify record"/>
  <bpmn:callActivity id="ca_ok" name="Run appeal" calledElement="Process_FL_Appeal"/>
  <bpmn:callActivity id="ca_bad" name="Run something"/>
  <bpmn:complexGateway id="cg" name="Complex"/>
  <bpmn:userTask id="t_reply" name="Process response"/>
  <bpmn:sequenceFlow id="sf1" sourceRef="s1" targetRef="t_serve"/>
 </bpmn:process>
</bpmn:definitions>
"""

def test_preprocess_pipeline():
    # synthetic "sketch": white page, a black rectangle (task) and a ruled line
    img = np.full((400, 600, 3), 255, np.uint8)
    img[:, 100:102] = 0                      # a vertical ruled line
    img[150:250, 200:400] = 0                # a filled box
    img[170:230, 220:380] = 255              # hollow it out -> a task rectangle
    out, rep = preprocess.condition(img)
    assert out.ndim == 2 and out.size > 0
    assert "grayscale" in rep.steps and any("deskew" in s for s in rep.steps)
    png = preprocess.encode_png(out)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    print("preprocess OK:", rep.steps, "->", rep.out_shape)

def test_lint_rules():
    findings, summary = lint.lint(SAMPLE_BPMN, known_processes={"Process_FL_Appeal"})
    rules = sorted({f.rule for f in findings})
    got = {(f.rule, f.element_id) for f in findings}
    # expected hits
    assert ("timer-iso8601", "dl_bad") in got or any(f.rule=="timer-iso8601" for f in findings)
    assert any(f.rule == "business-rule-has-decision" and f.element_id == "brt_bad" for f in findings)
    assert any(f.rule == "call-activity-resolvable" and f.element_id == "ca_bad" for f in findings)
    assert any(f.rule == "execution-tier-spiff-safe" and f.element_id == "cg" for f in findings)
    assert any(f.rule == "deadline-has-authority" and f.element_id == "dl_bad" for f in findings)
    # the good timer (P20D with a citation in the name) must NOT be flagged for authority
    assert not any(f.rule == "deadline-has-authority" and f.element_id == "dl" for f in findings)
    # the good business rule task / call activity must NOT be flagged
    assert not any(f.element_id == "brt_ok" for f in findings)
    assert not any(f.element_id == "ca_ok" for f in findings)
    print(f"lint OK: {summary}; rules fired: {rules}")
    for f in findings:
        print("  -", f.level, f.rule, f.element_id, "-", f.message)

def test_lint_rejects_malformed():
    try:
        lint.lint("<not valid xml")
        raise AssertionError("should have raised")
    except ValueError:
        print("lint rejects malformed XML OK")

def test_provenance_signoff_gate():
    with tempfile.TemporaryDirectory() as d:
        prov = provenance.build("CONTRIB-0007", "riverwriter", True,
                                source_bytes=b"img", conditioned_bytes=b"png",
                                bpmn_text=SAMPLE_BPMN, source_filename="scan.jpg",
                                recognizer_backend="manual",
                                condition_report={"steps": ["grayscale"]},
                                lint_summary={"errors": 0, "warnings": 1, "clean": False})
        # sign-off gate
        try:
            provenance.promote(d, prov, bpmn_text=SAMPLE_BPMN, conditioned_bytes=b"png", signer="")
            raise AssertionError("promotion without signer should fail")
        except PermissionError:
            pass
        paths = provenance.promote(d, prov, bpmn_text=SAMPLE_BPMN, conditioned_bytes=b"png", signer="anson")
        assert all(os.path.exists(p) for p in paths.values())
        import json
        meta = json.load(open(paths["provenance"]))
        assert meta["license"] == "CC0-1.0" and meta["contributor_id"] == "CONTRIB-0007"
        assert meta["signed_off_by"] == "anson" and meta["bpmn_sha256"]
        print("provenance OK:", {k: os.path.basename(v) for k, v in paths.items()})

if __name__ == "__main__":
    test_preprocess_pipeline()
    test_lint_rules()
    test_lint_rejects_malformed()
    test_provenance_signoff_gate()
    print("\nALL CORE TESTS PASSED")
