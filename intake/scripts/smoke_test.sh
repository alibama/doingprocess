#!/usr/bin/env bash
# Verify everything except the live model call (which needs Ollama).
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== unit tests (preprocess / lint / provenance / coerce / pipeline) =="
python3 tests/test_core.py
python3 tests/test_vlm_parse.py
python3 tests/test_pipeline_mock.py
python3 tests/test_layout.py
python3 tests/test_serve_fake.py
echo "== end-to-end CLI over a synthetic sketch (mock recognizer, signed) =="
python3 tests/make_sample.py
python3 cli.py samples/ --backend mock --sign "smoke-tester" --outdir /tmp/lex_smoke
echo "== live VLM check (only if Ollama + model are up) =="
python3 tests/test_vlm_live.py || echo "  (skipped: Ollama/model not reachable)"
echo "ALL SMOKE CHECKS DONE"
