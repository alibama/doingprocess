import os, sys, time, json, threading, urllib.request
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import serve_recognize as srv
import recognizer as rec, pipeline, svc_client

PORT = 8791

def _start():
    srv.Handler.bridge = srv.FakeBridge()
    server = srv.ThreadingHTTPServer(("127.0.0.1", PORT), srv.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.3)
    return server

def _post(path, data, ctype="application/octet-stream"):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=data,
                                 headers={"Content-Type": ctype})
    return urllib.request.urlopen(req, timeout=5).read()

def test_endpoints_and_backend_wiring():
    s = _start()
    try:
        h = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health").read())
        assert h["ok"] and h["bridge"] == "fake"
        xml = _post("/recognize", b"\x89PNG_fake").decode()
        assert "<bpmn:definitions" in xml and "BPMNDiagram" in xml
        det = json.loads(_post("/detect", b"img").decode())
        assert "token" in det and det["boxes"] and det["label_list"]
        asm = _post("/assemble", json.dumps({"token": det["token"], "boxes": det["boxes"],
                    "labels": det["labels"]}).encode(), "application/json").decode()
        assert "BPMNDiagram" in asm
        print("server endpoints OK")

        import numpy as np, cv2
        img = np.full((200, 320, 3), 255, np.uint8); cv2.rectangle(img,(40,60),(140,120),0,2)
        png = cv2.imencode(".png", img)[1].tobytes()
        be = rec.get_backend("elca", endpoint=f"http://127.0.0.1:{PORT}/recognize")
        assert be.available()
        res = pipeline.run(png, be)
        assert res["ok"], res.get("notes")
        assert any("preserved recognizer-provided layout" in n for n in res["notes"])
        assert res["lint_summary"]["errors"] == 0
        print(f"backend->pipeline OK: nodes={res['flow_nodes']} notes={res['notes']}")
    finally:
        s.shutdown()

def test_svc_client():
    s = _start()
    try:
        base = f"http://127.0.0.1:{PORT}"
        assert svc_client.health(base)["ok"]
        det = svc_client.detect(base, b"img")
        xml = svc_client.assemble(base, {"token": det["token"], "boxes": det["boxes"],
                                         "labels": det["labels"]})
        assert "BPMNDiagram" in xml
        assert "<bpmn:definitions" in svc_client.recognize(base, b"img")
        print("svc_client OK")
    finally:
        s.shutdown()

if __name__ == "__main__":
    test_endpoints_and_backend_wiring()
    test_svc_client()
    print("SERVE FAKE TESTS PASSED")
