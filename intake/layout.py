"""
Give a semantic-only BPMN model a diagram (BPMN DI) so it renders in
Camunda Modeler / bpmn-js. Pure-Python, deterministic layered left-to-right
layout — no Node, no bpmn-auto-layout dependency.

Why this exists: bpmn-js refuses to render an element that has no <BPMNShape>
bounds, and won't draw a flow without <BPMNEdge> waypoints. A recognizer/VLM
draft is semantic-only, so we synthesize a readable layout and DI here. The
result opens in Camunda where a human can tidy or drag as needed.

    python layout.py in.bpmn out.bpmn      # or add_di(xml) -> xml
"""
from __future__ import annotations
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

BPMN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI = "http://www.omg.org/spec/BPMN/20100524/DI"
DC = "http://www.omg.org/spec/DD/20100524/DC"
DI = "http://www.omg.org/spec/DD/20100524/DI"

EVENTS = {"startEvent", "endEvent", "intermediateCatchEvent",
          "intermediateThrowEvent", "boundaryEvent"}
GATEWAYS = {"exclusiveGateway", "parallelGateway", "inclusiveGateway",
            "eventBasedGateway", "complexGateway"}
DATA = {"dataObjectReference", "dataStoreReference", "dataObject", "dataStore"}
TASKS = {"task", "userTask", "manualTask", "scriptTask", "serviceTask",
         "businessRuleTask", "sendTask", "receiveTask", "callActivity", "subProcess"}
FLOW_NODES = EVENTS | GATEWAYS | DATA | TASKS | {"textAnnotation"}
EDGES = {"sequenceFlow", "messageFlow", "association", "dataInputAssociation",
         "dataOutputAssociation"}

COL_GAP = 190
ROW_GAP = 120
MARGIN_X = 160
MID_Y = 260


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _size(kind):
    if kind in EVENTS:
        return 36, 36
    if kind in GATEWAYS:
        return 50, 50
    if kind in DATA:
        return 36, 50
    if kind == "textAnnotation":
        return 100, 30
    return 100, 80


def _ranks(nodes, edges):
    succ = defaultdict(list)
    nodeset = set(nodes)
    for s, t in edges:
        if s in nodeset and t in nodeset:
            succ[s].append(t)
    rank = {n: 0 for n in nodes}
    for _ in range(len(nodes) + 1):          # bounded relaxation (cycle-safe)
        changed = False
        for s in nodes:
            for t in succ[s]:
                if rank[t] < rank[s] + 1:
                    rank[t] = rank[s] + 1
                    changed = True
        if not changed:
            break
    return rank


def _order_columns(nodes, rank, edges):
    cols = defaultdict(list)
    for n in nodes:                          # insertion order preserved
        cols[rank[n]].append(n)
    preds = defaultdict(list)
    for s, t in edges:
        preds[t].append(s)
    ypos = {}
    for r in sorted(cols):
        col = cols[r]
        if r > 0:
            prev_index = {n: i for i, n in enumerate(cols.get(r - 1, []))}
            col.sort(key=lambda n: (
                sum(prev_index.get(p, 0) for p in preds[n] if p in prev_index)
                / max(1, sum(1 for p in preds[n] if p in prev_index))))
        cols[r] = col
        for i, n in enumerate(col):
            ypos[n] = i
    return cols


def add_di(xml_text: str) -> str:
    """Return the BPMN with a synthesized <bpmndi:BPMNDiagram>. Idempotent-ish:
    if a diagram already exists, the input is returned unchanged."""
    if "BPMNDiagram" in xml_text:
        return xml_text
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return xml_text

    procs = [el for el in root.iter() if _local(el.tag) == "process"]
    collab = next((el for el in root.iter() if _local(el.tag) == "collaboration"), None)
    if not procs:
        return xml_text

    # gather flow nodes (direct children of processes) and edges
    nodes, kinds, attached = [], {}, {}
    edges = []            # (id, src, tgt)
    for proc in procs:
        for el in list(proc):
            ln = _local(el.tag)
            if ln in FLOW_NODES:
                nid = el.get("id")
                if not nid:
                    continue
                nodes.append(nid)
                kinds[nid] = ln
                host = el.get("attachedToRef")
                if ln == "boundaryEvent" and host:
                    attached[nid] = host
            elif ln in EDGES:
                eid = el.get("id")
                s = el.get("sourceRef"); t = el.get("targetRef")
                if eid and s and t:
                    edges.append((eid, s, t))
    if collab is not None:
        for el in list(collab):
            if _local(el.tag) == "messageFlow":
                eid = el.get("id"); s = el.get("sourceRef"); t = el.get("targetRef")
                if eid and s and t:
                    edges.append((eid, s, t))

    ranked = [n for n in nodes if n not in attached]
    flow_edges = [(s, t) for (_id, s, t) in edges if s in ranked and t in ranked]
    rank = _ranks(ranked, flow_edges)
    cols = _order_columns(ranked, rank, flow_edges)

    bounds = {}
    for r in sorted(cols):
        col = cols[r]
        k = len(col)
        for i, nid in enumerate(col):
            w, h = _size(kinds[nid])
            cx = MARGIN_X + r * COL_GAP
            cy = MID_Y + (i - (k - 1) / 2.0) * ROW_GAP
            bounds[nid] = (cx - w / 2, cy - h / 2, w, h)

    # boundary events: hang on the bottom edge of their host
    for bid, host in attached.items():
        w, h = _size("boundaryEvent")
        if host in bounds:
            hx, hy, hw, hh = bounds[host]
            bounds[bid] = (hx + hw * 0.7 - w / 2, hy + hh - h / 2, w, h)
        else:
            bounds[bid] = (MARGIN_X, MID_Y, w, h)

    # any edge endpoint without a shape gets a default box (keeps bpmn-js happy)
    maxx = max((b[0] + b[2] for b in bounds.values()), default=MARGIN_X)
    for _id, s, t in edges:
        for end in (s, t):
            if end not in bounds:
                bounds[end] = (maxx + COL_GAP, MID_Y, 100, 80)
                maxx += COL_GAP

    def center(nid):
        x, y, w, h = bounds[nid]
        return x + w / 2, y + h / 2

    def right(nid):
        x, y, w, h = bounds[nid]
        return x + w, y + h / 2

    def left(nid):
        x, y, w, h = bounds[nid]
        return x, y + h / 2

    # waypoints
    wpts = {}
    for eid, s, t in edges:
        if s not in bounds or t not in bounds:
            continue
        sx, sy = right(s); tx, ty = left(t)
        if tx <= sx:                          # backward / loop: route beneath
            scx, scy = center(s); tcx, tcy = center(t)
            ny = max(b[1] + b[3] for b in bounds.values()) + 40
            wpts[eid] = [(scx, bounds[s][1] + bounds[s][3]), (scx, ny), (tcx, ny),
                         (tcx, bounds[t][1] + bounds[t][3])]
        elif abs(sy - ty) < 1:
            wpts[eid] = [(sx, sy), (tx, ty)]
        else:
            mx = (sx + tx) / 2.0
            wpts[eid] = [(sx, sy), (mx, sy), (mx, ty), (tx, ty)]

    # build DI
    plane_el = collab.get("id") if collab is not None else procs[0].get("id")
    lines = ['  <bpmndi:BPMNDiagram id="BPMNDiagram_1">',
             f'    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="{plane_el}">']
    for nid, (x, y, w, h) in bounds.items():
        lines.append(f'      <bpmndi:BPMNShape id="{nid}_di" bpmnElement="{nid}">')
        lines.append(f'        <dc:Bounds x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}"/>')
        lines.append('      </bpmndi:BPMNShape>')
    for eid, s, t in edges:
        if eid not in wpts:
            continue
        lines.append(f'      <bpmndi:BPMNEdge id="{eid}_di" bpmnElement="{eid}">')
        for (x, y) in wpts[eid]:
            lines.append(f'        <di:waypoint x="{x:.0f}" y="{y:.0f}"/>')
        lines.append('      </bpmndi:BPMNEdge>')
    lines += ['    </bpmndi:BPMNPlane>', '  </bpmndi:BPMNDiagram>']
    di_xml = "\n".join(lines)

    # ensure namespaces on <definitions>
    out = xml_text
    m = out.find("<bpmn:definitions")
    tagname = "<bpmn:definitions"
    if m < 0:
        m = out.find("<definitions")
        tagname = "<definitions"
    end_open = out.find(">", m)
    open_tag = out[m:end_open]
    add = []
    for p, u in [("bpmndi", BPMNDI), ("dc", DC), ("di", DI)]:
        if f"xmlns:{p}" not in open_tag:
            add.append(f'xmlns:{p}="{u}"')
    if add:
        out = out[:end_open] + " " + " ".join(add) + out[end_open:]

    close = out.rfind("</bpmn:definitions>")
    tagclose = "</bpmn:definitions>"
    if close < 0:
        close = out.rfind("</definitions>")
        tagclose = "</definitions>"
    return out[:close] + di_xml + "\n" + out[close:]


def _main(argv):
    if not argv:
        print(__doc__); return 1
    src = open(argv[0], encoding="utf-8").read()
    out = add_di(src)
    if len(argv) > 1:
        open(argv[1], "w", encoding="utf-8").write(out)
        print(f"wrote {argv[1]}")
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
