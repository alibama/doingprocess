#!/usr/bin/env bash
# One-time setup: python deps + pull the local vision model.
set -euo pipefail
cd "$(dirname "$0")/.."
MODEL="${OLLAMA_MODEL:-qwen3.6}"
HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"

echo "== python deps =="
python3 -m pip install -r requirements.txt

echo "== ollama =="
if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama not found. Install it: https://ollama.com/download"; exit 1
fi
if ! curl -fsS "$HOST/api/tags" >/dev/null 2>&1; then
  echo "Ollama server not responding at $HOST."
  echo "Start it in another terminal:  ollama serve"; exit 1
fi
echo "pulling $MODEL (vision) — this is large, one time…"
ollama pull "$MODEL"
echo "== done =="
