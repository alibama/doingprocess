# Lexipedia Sketch Intake & Review Station (automated)

Scanned hand-drawn legal-process map -> lint-clean, provenance-stamped **BPMN 2.0**,
ready for the corpus. This is the transform between a mailed contributor map and
your SpiffWorkflow / bpmnlint / merge pipeline.

**Automated draft, human sign-off.** The recognizer is now automatic: a **local
Ollama vision model (`qwen3.6`)** drafts the BPMN from the image. Promotion to the
corpus still requires a reviewer sign-off — the draft is a starting point, not
ground truth (the paper's own finding: recognize-then-correct).

## Pipeline
1. **Intake** — contributor ID (join key; never the legal name), handle, scan.
2. **Auto-draft** — condition the image → recognizer drafts BPMN → **auto-layout
   (DI)** so it renders in Camunda/bpmn-js → lint. One pass.
3. **Correct (optional)** — self-hosted `bpmn-image-annotator` for a human pass.
4. **Sign off & promote** — CC0 + contributor ID + reviewer sign-off; blocked on
   lint errors or an empty draft.

## Detector track — fully local & headless

`scripts/run_elca.sh` clones the ELCA space (for its `modules/` + the
`ELCA-SA/BPMN_Detection` weights), then serves a **local** recognizer via
`serve_recognize.py`:

```
POST /recognize  (image bytes) -> BPMN 2.0 XML with DI (renders as drawn)
POST /detect     (image bytes) -> boxes + labels (+ token) for correction
POST /assemble   (JSON)        -> BPMN from corrected boxes  (create_XML)
```

- **No cloud.** OCR is OFF by default — the ELCA space's Azure OCR is bypassed
  entirely (elements come back unlabeled; you type labels in the correction
  pass). `--ocr tesseract` uses a local engine instead.
- **Automated:** `python cli.py scans/ --backend elca --endpoint http://127.0.0.1:8600/recognize`.
- **In-page box correction (no round-trip):** in the app, backend=`elca` adds a
  "correct boxes" step using `streamlit-image-annotation` (the ELCA component),
  then `/assemble` builds the BPMN. Install the optional component to enable it.
- The pipeline preserves the detector's DI (from pixel coords) and only
  synthesizes layout for the semantic-only VLM track.

The ELCA seam is confirmed from their source (`create_XML(full_pred,
text_mapping, size_scale, scale)`, models via `get_faster_rcnn_model` /
`get_arrow_model`, prediction via `modules.eval.full_prediction`). `run_elca.sh`
runs `serve_recognize.py --selftest` on a bundled example first; if
`full_prediction`'s return shape or the weight filenames differ on your build,
the selftest says so and points at the one function to adjust.

## Recognizer tracks

Two ways to turn a scan into BPMN; both feed the same correct -> lint -> sign-off tail.

- **Purpose-built detector (ELCA)** — `scripts/run_elca.sh` runs ELCA-SA/sketch-to-BPMN
  locally: a torchvision detector (`ELCA-SA/BPMN_Detection`) + `toXML` that writes
  **DI from pixel coordinates**, so the diagram renders *as drawn*. Highest fidelity
  on shapes; needs torch + the model. Backend: `--backend elca --endpoint http://127.0.0.1:PORT`.
- **General VLM (default)** — local `qwen3.6` on Ollama drafts semantic BPMN; the
  pipeline adds **synthetic** layout DI. No torch/model download; rougher.

The pipeline preserves recognizer-provided DI (ELCA) and only synthesizes layout
when absent (VLM). Both are LOCAL; the one cloud dependency to remove is the ELCA
space's **Azure OCR** — run it with OCR off, or swap `modules/OCR.py` for a local
engine, so contributor scans never leave your machine.

## Renders in Camunda

Recognizer/VLM drafts are semantic-only and will NOT render on their own —
bpmn-js needs diagram interchange (DI). `layout.py` synthesizes a deterministic
left-to-right layout (shape bounds + edge waypoints) and the pipeline adds it
automatically. To fix an existing semantic-only file:

```bash
python layout.py in.bpmn out.bpmn      # out.bpmn opens in Camunda Modeler
```

## Quick start
```bash
cd lexipedia_intake
bash scripts/setup.sh            # pip install + ollama pull qwen3.6   (one time)
bash scripts/smoke_test.sh       # verify everything offline (mock recognizer)
bash scripts/run_app.sh          # the Streamlit UI (needs Ollama running)
```
Ollama must be running (`ollama serve`) for the live auto-draft. Change the model
with `OLLAMA_MODEL=qwen3-vl bash scripts/setup.sh` (or in the app sidebar).

## Headless / batch
```bash
python cli.py samples/            --outdir corpus_staging          # local-vlm, staged
python cli.py samples/ --backend mock --sign "Anson" --outdir out  # offline, promote clean
```
Everything not lint-clean lands in `<outdir>/review/` for a human pass.

## Scripts
- `scripts/setup.sh`      python deps + `ollama pull qwen3.6`
- `scripts/run_app.sh`    launch the Streamlit UI
- `scripts/run_cli.sh`    batch a folder through the pipeline
- `scripts/run_annotator.sh`  clone+run the bpmn-image-annotator on http://localhost:8080
- `scripts/run_elca.sh`      run the ELCA detector locally (renders as drawn)
- `scripts/smoke_test.sh` unit + parse + pipeline + CLI end-to-end (+ live VLM if up)

## What is verified vs. what needs your box
Verified headless (in `tests/`, run by smoke_test):
- image conditioning, all six lint rules, provenance + sign-off gate,
- VLM reply parsing/repair (fences, prose, missing namespaces),
- full pipeline + CLI end-to-end with the deterministic **mock** recognizer.

Needs Ollama on your machine (guarded, skips cleanly otherwise):
- the live `qwen3.6` call — `tests/test_vlm_live.py`, run by smoke_test.

## Notes / honest edges
- VLM output on hand-drawn BPMN is rough; lint catches structure, the human
  fixes the rest. Draft BPMN carries no DI (layout) — bpmn-js auto-lays-out on
  open, or correct it in the annotator.
- `flow-kind-by-scope` is a structural (parent-scope) check; full cross-pool
  validation needs the collaboration graph and is left as a noted limitation.
- Legal identity lives only in your scanned-originals archive; this station
  handles only the contributor ID.

License: Apache-2.0 (code). Contributed maps: CC0-1.0. Model tag `qwen3.6` per
your request; swap freely (e.g. `qwen3-vl`).
