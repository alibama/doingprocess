"""Live check — only runs if Ollama + the model are reachable; else exits 1 (skip)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import recognizer as rec
from make_sample import p as SAMPLE  # writing the sample also gives its path

be = rec.LocalVLMBackend(model=os.environ.get("OLLAMA_MODEL", "qwen3.6"))
if not be.available():
    print("Ollama/model not reachable — skipping live test")
    sys.exit(1)
xml = be.draft_bpmn(SAMPLE)
assert xml.strip().startswith("<?xml") or "<bpmn:definitions" in xml
import xml.etree.ElementTree as ET
ET.fromstring(xml)
print("LIVE VLM TEST PASSED — model returned parseable BPMN")
