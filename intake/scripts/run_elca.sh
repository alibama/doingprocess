#!/usr/bin/env bash
# Run the purpose-built detector as a LOCAL headless service (no UI, no cloud).
# Clones the ELCA space (for its modules + model), then serves our /recognize,
# /detect, /assemble endpoints via serve_recognize.py using the ELCABridge.
#
# DATA SOVEREIGNTY: OCR is OFF by default (Azure is bypassed entirely); elements
# come back unlabeled and you type labels in the correction pass. For local OCR,
# add: --ocr tesseract  (needs the tesseract binary). Scans never leave the box.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
DIR="${ELCA_DIR:-$HOME/elca-sketch-to-bpmn}"
PORT="${ELCA_PORT:-8600}"

command -v git >/dev/null || { echo "git required"; exit 1; }
if [ ! -d "$DIR/.git" ]; then
  echo "== cloning ELCA space into $DIR (for modules + model) =="
  git clone https://huggingface.co/spaces/ELCA-SA/sketch-to-BPMN "$DIR"
fi

python3 -m venv "$DIR/.venv" 2>/dev/null || true
# shellcheck disable=SC1091
source "$DIR/.venv/bin/activate" 2>/dev/null || true
echo "== installing ELCA deps (torch/torchvision — large, one time) =="
# Skip the Azure OCR dep; we run OCR locally or not at all:
grep -v '^azure-ai-vision' "$DIR/requirements.txt" > "$DIR/requirements.local.txt" || true
pip install -r "$DIR/requirements.local.txt"

echo "== self-test the ELCA bridge on a bundled example =="
ELCA_DIR="$DIR" python3 "$HERE/serve_recognize.py" --elca-dir "$DIR" --selftest || {
  echo "  selftest failed — confirm the seam in serve_recognize.py (_unpack_prediction /"
  echo "  weight filenames) against modules/eval.py + modules/streamlit_utils.py, then retry."; }

echo "== serving detector on http://127.0.0.1:$PORT =="
echo "   In the intake app: backend=elca, Recognizer service URL=http://127.0.0.1:$PORT"
exec python3 "$HERE/serve_recognize.py" --elca-dir "$DIR" --port "$PORT" --ocr none
