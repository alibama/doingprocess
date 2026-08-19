import os, sys
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import layout

SEMANTIC = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" targetNamespace="x">
 <bpmn:process id="P" isExecutable="false">
  <bpmn:startEvent id="s1" name="start"/>
  <bpmn:task id="t1" name="do"/>
  <bpmn:exclusiveGateway id="g1" name="X"/>
  <bpmn:endEvent id="e1" name="end"/>
  <bpmn:sequenceFlow id="f1" sourceRef="s1" targetRef="t1"/>
  <bpmn:sequenceFlow id="f2" sourceRef="t1" targetRef="g1"/>
  <bpmn:sequenceFlow id="f3" sourceRef="g1" targetRef="e1"/>
 </bpmn:process>
</bpmn:definitions>"""
L = lambda t: t.rsplit('}', 1)[-1]

def test_di_added_and_complete():
    out = layout.add_di(SEMANTIC)
    r = ET.fromstring(out)                       # well-formed
    nodes = {e.get('id') for e in r.iter() if L(e.tag) in
             ('startEvent','task','exclusiveGateway','endEvent')}
    shapes = {e.get('bpmnElement') for e in r.iter() if L(e.tag) == 'BPMNShape'}
    edges = {e.get('bpmnElement') for e in r.iter() if L(e.tag) == 'BPMNEdge'}
    flows = {e.get('id') for e in r.iter() if L(e.tag) == 'sequenceFlow'}
    assert nodes <= shapes, f"missing shapes: {nodes - shapes}"
    assert flows <= edges, f"missing edges: {flows - edges}"
    for e in r.iter():
        if L(e.tag) == 'BPMNEdge':
            assert sum(1 for w in e if L(w.tag) == 'waypoint') >= 2
    assert 'xmlns:bpmndi' in out and 'xmlns:dc' in out and 'xmlns:di' in out
    print("layout DI complete OK")

def test_idempotent():
    once = layout.add_di(SEMANTIC)
    twice = layout.add_di(once)
    assert once == twice
    print("layout idempotent OK")

if __name__ == "__main__":
    test_di_added_and_complete(); test_idempotent()
    print("LAYOUT TESTS PASSED")
