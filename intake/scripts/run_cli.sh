#!/usr/bin/env bash
# Batch a folder of scans through the automated pipeline (staged for review).
set -euo pipefail
cd "$(dirname "$0")/.."
IN="${1:-samples}"
python3 cli.py "$IN" --backend "${BACKEND:-local-vlm}" --model "${OLLAMA_MODEL:-qwen3.6}" \
  --host "${OLLAMA_HOST:-http://127.0.0.1:11434}" --outdir "${OUTDIR:-corpus_staging}"
