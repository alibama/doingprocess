import os, sys
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pipeline, recognizer as rec

def synthetic_png():
    img = np.full((300, 500, 3), 255, np.uint8)
    cv2.rectangle(img, (60, 120), (200, 180), 0, 2)
    cv2.rectangle(img, (300, 120), (440, 180), 0, 2)
    cv2.arrowedLine(img, (200, 150), (300, 150), 0, 2)
    return cv2.imencode(".png", img)[1].tobytes()

def test_pipeline_with_mock():
    res = pipeline.run(synthetic_png(), rec.MockBackend())
    assert res["ok"] is True
    assert res["flow_nodes"] >= 3
    assert res["lint_summary"]["errors"] == 0
    assert "conditioned_png" in res and res["bpmn"].startswith("<?xml")
    print(f"pipeline+mock OK: nodes={res['flow_nodes']} summary={res['lint_summary']}")

if __name__ == "__main__":
    test_pipeline_with_mock()
    print("PIPELINE MOCK TEST PASSED")
