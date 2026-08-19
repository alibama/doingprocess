#!/usr/bin/env bash
# Launch the human-correction UI: dwslab/bpmn-image-annotator (bpmn-js).
# Runs a LOCAL webpack-dev-server on http://localhost:8080 and opens your browser.
# The scanned image is loaded client-side and never leaves your machine.
set -euo pipefail
DIR="${ANNOTATOR_DIR:-$HOME/bpmn-image-annotator}"

command -v node >/dev/null 2>&1 || { echo "Node.js required: https://nodejs.org"; exit 1; }
command -v npm  >/dev/null 2>&1 || { echo "npm required"; exit 1; }

if [ ! -d "$DIR/.git" ]; then
  echo "== cloning bpmn-image-annotator into $DIR =="
  git clone --depth 1 https://github.com/dwslab/bpmn-image-annotator "$DIR"
fi
cd "$DIR"
[ -d node_modules ] || { echo "== npm install (first run) =="; npm install; }

echo "== starting annotator on http://localhost:8080 (Ctrl-C to stop) =="
echo "   In the intake app sidebar, set the annotator URL to http://localhost:8080"
exec npm run dev   # webpack-dev-server --static=public --open  -> opens the browser
