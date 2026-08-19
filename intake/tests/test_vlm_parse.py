import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import recognizer as rec

def test_fenced_with_prose():
    reply = 'Sure! Here is the BPMN:\n```xml\n<?xml version="1.0"?>\n' \
            '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">' \
            '<bpmn:process id="P"><bpmn:task id="t1" name="Do"/></bpmn:process>' \
            '</bpmn:definitions>\n```\nHope that helps!'
    xml, ok = rec.coerce_bpmn(reply)
    assert ok and "<bpmn:task" in xml and "```" not in xml
    print("fenced+prose OK")

def test_missing_namespace_repaired():
    reply = '<bpmn:definitions><bpmn:process id="P">' \
            '<bpmn:startEvent id="s"/></bpmn:process></bpmn:definitions>'
    xml, ok = rec.coerce_bpmn(reply)
    assert ok and 'xmlns:bpmn' in xml
    print("missing-namespace repair OK")

def test_garbage_rejected():
    xml, ok = rec.coerce_bpmn("the model refused and wrote a paragraph with no xml")
    assert not ok and "Process_intake" in xml   # falls back to EMPTY_BPMN
    print("garbage rejected OK")

if __name__ == "__main__":
    test_fenced_with_prose(); test_missing_namespace_repaired(); test_garbage_rejected()
    print("VLM PARSE TESTS PASSED")
