"""
Lexipedia Sketch Intake & Review Station (automated draft)
==========================================================
Scanned hand-drawn legal-process map -> lint-clean, provenance-stamped BPMN 2.0.

Default recognizer: a LOCAL Ollama vision model (qwen3.6). The draft is produced
automatically; a human still signs off before anything enters the corpus.

Run:  streamlit run app.py    (Ollama must be running for the auto-draft step)
"""
from __future__ import annotations
import streamlit as st

import pipeline
import lint as bpmnlint
import provenance as prov
import recognizer as rec

st.set_page_config(page_title="Lexipedia Sketch Intake", layout="wide")

st.sidebar.title("Intake configuration")
st.sidebar.caption("Local-first. No cloud service is contacted.")
backend_kind = st.sidebar.selectbox("Recognizer", ["local-vlm", "mock", "manual", "self-hosted"])
model = st.sidebar.text_input("Ollama model", "qwen3.6") if backend_kind == "local-vlm" else ""
host = st.sidebar.text_input("Ollama host", "http://127.0.0.1:11434") if backend_kind == "local-vlm" else ""
endpoint = st.sidebar.text_input("Local endpoint", "http://127.0.0.1:8501/recognize") if backend_kind == "self-hosted" else ""
svc_base = st.sidebar.text_input("Recognizer service URL", "http://127.0.0.1:8600") if backend_kind == "elca" else ""
annotator_url = st.sidebar.text_input("bpmn-image-annotator URL (optional correction)", "http://localhost:8080")
outdir = st.sidebar.text_input("Corpus staging dir", "./corpus_staging")
backend = rec.get_backend(backend_kind, model=model, host=host, endpoint=endpoint)
st.sidebar.write(f"Backend **{backend.name}** — " + ("available ✅" if backend.available() else "not reachable ⚠️"))

st.title("Lexipedia Sketch Intake & Review Station")

ss = st.session_state
for k in ("result", "active_bpmn", "source_bytes", "source_name"):
    ss.setdefault(k, None)

# 1 · intake
st.header("1 · Intake")
c1, c2, c3 = st.columns(3)
contributor_id = c1.text_input("Contributor ID", help="Stable join key. Never the legal name.")
handle = c2.text_input("Handle (optional)")
display_public = c3.checkbox("Show handle publicly", value=False)
up = st.file_uploader("Scanned map", type=["jpg", "jpeg", "png", "tif", "tiff", "bmp"])
if up is not None:
    ss.source_bytes = up.getvalue(); ss.source_name = up.name

# 2 · automated draft (condition + recognize + lint, one click)
st.header("2 · Auto-draft")
st.caption("Conditions the image, runs the recognizer, and lints — one pass.")
if ss.source_bytes and st.button(f"Run auto-draft ({backend.name})"):
    with st.spinner("conditioning · recognizing · linting…"):
        ss.result = pipeline.run(ss.source_bytes, backend, known_processes=None)
        ss.active_bpmn = ss.result.get("bpmn")

res = ss.result
if res:
    a, b = st.columns(2)
    if ss.source_bytes:
        a.image(ss.source_bytes, caption="original", use_container_width=True)
    if res.get("conditioned_png"):
        b.image(res["conditioned_png"], caption=f"conditioned · {res['condition_report'].get('steps')}",
                use_container_width=True)
    for n in res.get("notes", []):
        st.write("•", n)
    m1, m2, m3 = st.columns(3)
    m1.metric("Flow nodes", res.get("flow_nodes", 0))
    m2.metric("Errors", res.get("lint_summary", {}).get("errors", "?"))
    m3.metric("Warnings", res.get("lint_summary", {}).get("warnings", "?"))
    if res.get("findings"):
        st.dataframe(res["findings"], use_container_width=True)
    st.download_button("Download draft .bpmn", res.get("bpmn", ""), file_name="draft.bpmn",
                       mime="application/xml")

# 2b · detector: correct boxes in-page (no browser round-trip), then assemble
if backend_kind == "elca" and ss.source_bytes:
    st.header("2b · Detector — correct boxes")
    st.caption("Fix the detector's boxes/labels over the image, then assemble BPMN "
               "(DI comes from the pixel coordinates — renders as drawn).")
    import svc_client
    try:
        from streamlit_image_annotation import detection as _bbox_annot
        _have_annot = True
    except Exception:
        _have_annot = False
    if st.button("Detect elements"):
        try:
            ss.detect = svc_client.detect(svc_base, res["conditioned_png"] if res else ss.source_bytes)
        except Exception as e:
            st.error(f"detect failed (is the recognizer service running? scripts/run_elca.sh): {e}")
    det = ss.get("detect")
    if det:
        if _have_annot:
            from PIL import Image
            import io as _io
            src = (res or {}).get("conditioned_png") or ss.source_bytes
            img = Image.open(_io.BytesIO(src)).convert("RGB")
            corrected = _bbox_annot(img, det["label_list"],
                                    bboxes=det["boxes"], labels=det["labels"],
                                    key="elca_boxes")
            boxes = [c["bbox"] for c in corrected] if corrected else det["boxes"]
            labels = [c["label_id"] for c in corrected] if corrected else det["labels"]
        else:
            st.info("Install streamlit-image-annotation for in-page box editing; "
                    "using detector boxes as-is.")
            boxes, labels = det["boxes"], det["labels"]
        if st.button("Assemble BPMN from boxes"):
            try:
                ss.active_bpmn = svc_client.assemble(svc_base, {"token": det["token"],
                                                    "boxes": boxes, "labels": labels})
                st.success("Assembled BPMN from corrected boxes.")
            except Exception as e:
                st.error(f"assemble failed: {e}")

# 3 · optional human correction
st.header("3 · Correct (optional)")
st.caption("Load the conditioned image + draft into a self-hosted bpmn-image-annotator, "
           "correct, export, and re-upload here to replace the draft.")
if annotator_url:
    with st.expander("Embed annotator"):
        st.components.v1.iframe(annotator_url, height=520)
corrected = st.file_uploader("Corrected .bpmn (replaces the draft)", type=["bpmn", "xml"], key="corr")
if corrected is not None:
    ss.active_bpmn = corrected.getvalue().decode("utf-8")
    st.success("Using corrected BPMN as the active model.")

# 4 · re-lint active model + provenance + sign-off
st.header("4 · Sign off & promote")
active = ss.active_bpmn
summary = None
if active:
    try:
        findings, summary = bpmnlint.lint(active)
        c1, c2, c3 = st.columns(3)
        c1.metric("Errors", summary["errors"]); c2.metric("Warnings", summary["warnings"])
        c3.metric("Status", "clean" if summary["clean"] else "needs work")
        if findings:
            st.dataframe([f.dict() for f in findings], use_container_width=True)
    except ValueError as e:
        st.error(str(e))

signer = st.text_input("Reviewer sign-off (your name)")
nodes = pipeline.count_flow_nodes(active) if active else 0
can = bool(active and summary and summary["errors"] == 0 and nodes > 0
           and contributor_id.strip() and signer.strip())
if summary and summary["errors"]:
    st.warning("Resolve all errors before promotion.")
if active and nodes == 0:
    st.warning("Draft has no flow nodes — correct it before promotion.")
if st.button("Promote to corpus", disabled=not can):
    try:
        record = prov.build(contributor_id, handle, display_public,
                            source_bytes=ss.source_bytes or b"",
                            conditioned_bytes=(res or {}).get("conditioned_png", b""),
                            bpmn_text=active, source_filename=ss.source_name or "",
                            recognizer_backend=backend.name,
                            condition_report=(res or {}).get("condition_report", {}),
                            lint_summary=summary)
        paths = prov.promote(outdir, record, bpmn_text=active,
                            conditioned_bytes=(res or {}).get("conditioned_png", b""), signer=signer)
        st.success(f"Promoted:\n- {paths['bpmn']}\n- {paths['provenance']}")
    except Exception as e:
        st.error(f"Promotion failed: {e}")
