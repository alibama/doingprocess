#!/usr/bin/env python3
"""Build the BPMN diagrams for doingprocess.org.

Reads every model in models/src/*.json and writes

  models/<id>.bpmn               BPMN 2.0 XML with diagram interchange (opens in
                                 Camunda Modeler, bpmn.io, SpiffWorkflow, ...)
  site/assets/diagrams/<id>.svg  the same diagram drawn in the site's palette

Standard library only. Run from anywhere:  python tools/build_diagrams.py

Spec format (one JSON object per file)
--------------------------------------
{
  "id": "obtain_id",                 # file name + BPMN process id
  "name": "Getting an ID",           # human title
  "summary": "one sentence",         # SVG <desc>; also BPMN documentation
  "col_width": 175, "row_height": 104,   # optional grid pitch overrides
  "lanes": [ {"name": "Returning citizen", "rows": [0, 1]}, ... ],   # optional
  "nodes": [
    {"id": "s", "type": "start", "name": "...", "col": 0, "row": 0},
    {"id": "t1", "type": "user", "name": "...", "col": 1, "row": 0,
     "cite": "Va. Code § 46.2-345",  # legal authority; "?" = citation still needed
     "inside": true,                  # can start before release
     "who": "DMV"}                    # small role label (lane-less diagrams)
    {"id": "b1", "type": "boundary-timer", "attached": "t1", "name": "P30D"},
    {"id": "n1", "type": "note", "for": "t1", "text": "...", "col": 1, "row": 1}
  ],
  "flows": [ {"from": "s", "to": "t1"}, {"from": "g", "to": "t2", "name": "no",
              "via": [[2.5, 1]]},      # via = grid points (col,row) the line passes
             {"from": "t3", "to": "t1", "via": [[3.5, 1], [3.5, 0]], "join": true} ]
                                       # join = stop at the last via point (merge into a line)
}

Node types: start, timer-start, end, timer, message, xor, and, event, task,
user, service, script, rule, manual, subprocess, boundary-timer, note.
Grid: col/row are integers (fractions allowed); x grows to the right, y downward.
"""
from __future__ import annotations

import html
import json
import math
import pathlib
import sys
from xml.sax.saxutils import quoteattr

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "models" / "src"
OUT_BPMN = ROOT / "models"
OUT_SVG = ROOT / "site" / "assets" / "diagrams"
OUT_SITE_MODELS = ROOT / "site" / "models"   # downloadable copies

# palette (matches site/assets/site.css)
INK, INK2, INK3 = "#1b1813", "#514c41", "#7c7566"
TEAL, TEAL2 = "#0d6b60", "#0a4f47"
OCHRE, OCHRE2 = "#b0741a", "#7d5210"
PAPER, PAPER2, PAPER3 = "#e7e2d6", "#f1eee6", "#dcd6c6"
LINE, LINE2 = "#cec8b8", "#bdb5a1"
SANS = "'Segoe UI', system-ui, -apple-system, Helvetica, Arial, sans-serif"
MONO = "ui-monospace, 'Cascadia Code', 'JetBrains Mono', Menlo, Consolas, monospace"

TASK_W, TASK_H = 148, 74
GW = 48          # gateway diamond size
EV = 38          # event circle diameter
BEV = 28         # boundary event diameter
LANE_STRIP = 40  # width of the lane-label strip
MARGIN = 26

TASK_TYPES = {"task", "user", "service", "script", "rule", "manual", "subprocess"}
GATEWAYS = {"xor", "and", "event"}
EVENTS = {"start", "timer-start", "end", "timer", "message"}


# ----------------------------------------------------------------------------- helpers
def esc(s: str) -> str:
    return html.escape(s, quote=True)


def wrap(text: str, max_chars: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_chars:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines or [""]


class Model:
    def __init__(self, spec: dict):
        self.spec = spec
        self.id = spec["id"]
        self.name = spec["name"]
        self.col_w = spec.get("col_width", 178)
        self.row_h = spec.get("row_height", 104)
        self.lanes = spec.get("lanes", [])
        self.nodes = {n["id"]: dict(n) for n in spec["nodes"]}
        self.flows = spec.get("flows", [])
        self.x0 = MARGIN + (LANE_STRIP if self.lanes else 0)
        self.y0 = MARGIN + 18
        rows = [n["row"] for n in self.nodes.values() if "row" in n]
        cols = [n["col"] for n in self.nodes.values() if "col" in n]
        for lane in self.lanes:
            rows += lane["rows"]
        self.n_rows = int(math.floor(max(rows))) + 1
        self.n_cols = int(math.floor(max(cols))) + 1
        self.width = self.x0 + self.n_cols * self.col_w + MARGIN
        self.height = self.y0 + self.n_rows * self.row_h + MARGIN
        for n in self.nodes.values():
            self._place(n)

    # grid -> pixel centre
    def cx(self, col: float) -> float:
        return self.x0 + col * self.col_w + self.col_w / 2

    def cy(self, row: float) -> float:
        return self.y0 + row * self.row_h + self.row_h / 2

    def _place(self, n: dict) -> None:
        t = n["type"]
        if t == "boundary-timer":
            host = self.nodes[n["attached"]]
            if "w" not in host:
                self._place(host)
            n["w"] = n["h"] = BEV
            n["x"] = host["x"] + host["w"] - BEV * 0.5 - 18 + n.get("dx", 0)
            n["y"] = host["y"] - BEV / 2
            n["col"], n["row"] = host["col"], host["row"]
            return
        if t in TASK_TYPES:
            w, h = n.get("w", TASK_W), n.get("h", TASK_H)
        elif t in GATEWAYS:
            w = h = GW
        elif t in EVENTS:
            w = h = EV
        elif t == "note":
            w, h = n.get("w", 150), n.get("h", 56)
        else:
            raise ValueError(f"unknown node type {t!r} ({n['id']})")
        n["w"], n["h"] = w, h
        n["x"] = self.cx(n["col"]) - w / 2 + n.get("dx", 0)
        n["y"] = self.cy(n["row"]) - h / 2 + n.get("dy", 0)

    # ------------------------------------------------------------------ routing
    def _centre(self, n):
        return n["x"] + n["w"] / 2, n["y"] + n["h"] / 2

    def _port(self, n, side):
        cx, cy = self._centre(n)
        return {"l": (n["x"], cy), "r": (n["x"] + n["w"], cy),
                "t": (cx, n["y"]), "b": (cx, n["y"] + n["h"])}[side]

    def route(self, f: dict) -> list[tuple[float, float]]:
        s, d = self.nodes[f["from"]], self.nodes[f["to"]]
        scx, scy = self._centre(s)
        dcx, dcy = self._centre(d)
        if f.get("via"):
            pts = [self._centre(s)] + [(self.cx(c), self.cy(r)) for c, r in f["via"]] + [self._centre(d)]
            # make orthogonal: insert corners where consecutive points share neither axis
            ortho = [pts[0]]
            for p in pts[1:]:
                q = ortho[-1]
                if abs(p[0] - q[0]) > 1 and abs(p[1] - q[1]) > 1:
                    ortho.append((p[0], q[1]))
                ortho.append(p)
            # clip first/last segments to the shape borders
            ortho[0] = self._exit_toward(s, ortho[1])
            if f.get("join"):
                ortho.pop()          # arrow ends on the last via point (merging into another line)
            else:
                ortho[-1] = self._exit_toward(d, ortho[-2])
            return ortho
        same_row = abs(scy - dcy) < 2
        if s["type"] == "boundary-timer":
            sx, sy = self._port(s, "t")
            if same_row:
                y = s["y"] - 22
                return [(sx, sy), (sx, y), (dcx, y), self._port(d, "t")]
            if dcx > scx + d["w"]:
                return [(sx, sy), (sx, dcy), self._port(d, "l")]
            return [(sx, sy), (sx, dcy), self._port(d, "r")]
        if same_row:
            if dcx > scx:
                return [self._port(s, "r"), self._port(d, "l")]
            # backward loop: run beneath both
            y = max(s["y"] + s["h"], d["y"] + d["h"]) + 30
            return [self._port(s, "b"), (scx, y), (dcx, y), self._port(d, "b")]
        going_down = dcy > scy
        if s["type"] in GATEWAYS or s["type"] in EVENTS:
            start = self._port(s, "b" if going_down else "t")
            if dcx > scx:
                return [start, (scx, dcy), self._port(d, "l")]
            if abs(dcx - scx) < 2:
                return [start, self._port(d, "t" if going_down else "b")]
            return [start, (scx, dcy), self._port(d, "r")]
        if d["type"] in GATEWAYS and dcx > scx:
            return [self._port(s, "r"), (dcx, scy), self._port(d, "t" if going_down else "b")]
        if dcx > scx:
            xm = s["x"] + s["w"] + (d["x"] - (s["x"] + s["w"])) / 2
            return [self._port(s, "r"), (xm, scy), (xm, dcy), self._port(d, "l")]
        # backwards and different row
        y = max(s["y"] + s["h"], d["y"] + d["h"]) + 30 if going_down else min(s["y"], d["y"]) - 30
        return [self._port(s, "b" if going_down else "t"), (scx, y), (dcx, y),
                self._port(d, "b" if going_down else "t")]

    def bg_at(self, y: float) -> str:
        """Background colour at a given y (lanes alternate), for label backing."""
        for i, lane in enumerate(self.lanes):
            top = self.y0 + min(lane["rows"]) * self.row_h
            bottom = self.y0 + (max(lane["rows"]) + 1) * self.row_h
            if top <= y <= bottom:
                return PAPER if i % 2 else PAPER2
        return PAPER2

    def _exit_toward(self, n, p):
        cx, cy = self._centre(n)
        dx, dy = p[0] - cx, p[1] - cy
        if abs(dx) >= abs(dy):
            return self._port(n, "r" if dx > 0 else "l")
        return self._port(n, "b" if dy > 0 else "t")


# ----------------------------------------------------------------------------- SVG
def svg_icon(t: str, x: float, y: float) -> str:
    """Small BPMN marker in the top-left corner of a task."""
    s = 'fill="none" stroke="%s" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"' % INK2
    if t == "user":
        return (f'<g {s}><circle cx="{x+6}" cy="{y+4.5}" r="3.2"/>'
                f'<path d="M{x} {y+13.5}c0-3.6 2.7-5.6 6-5.6s6 2 6 5.6"/></g>')
    if t == "service":
        return (f'<g {s}><circle cx="{x+6}" cy="{y+7}" r="2.6"/>'
                f'<path d="M{x+6} {y+1}v2M{x+6} {y+11}v2M{x} {y+7}h2M{x+10} {y+7}h2'
                f'M{x+1.8} {y+2.8}l1.4 1.4M{x+8.8} {y+9.8}l1.4 1.4M{x+10.2} {y+2.8}l-1.4 1.4M{x+3.2} {y+9.8}l-1.4 1.4"/></g>')
    if t == "script":
        return (f'<g {s}><path d="M{x+2} {y+1}h9c-2 2-2 4 0 6s2 4 0 6h-9c2-2 2-4 0-6s-2-4 0-6z"/>'
                f'<path d="M{x+4} {y+4.5}h5M{x+4} {y+9.5}h5"/></g>')
    if t == "rule":
        return (f'<g {s}><rect x="{x}" y="{y+1}" width="13" height="11" rx="1"/>'
                f'<path d="M{x} {y+4.8}h13M{x} {y+8.5}h13M{x+4.5} {y+4.8}v7.2"/>'
                f'<rect x="{x}" y="{y+1}" width="13" height="3.8" fill="{INK2}" stroke="none"/></g>')
    if t == "manual":
        return (f'<g {s}><path d="M{x+1} {y+8}v-3h9M{x+1} {y+8}c0 3 2 5 5 5h4v-11c0-1.5-2-1.5-2 0v2"/></g>')
    return ""


def render_svg(m: Model) -> str:
    out = []
    W, H = m.width, m.height
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" '
               f'role="img" aria-labelledby="t d" font-family="{SANS}">')
    out.append(f'<title id="t">{esc(m.name)}</title><desc id="d">{esc(m.spec.get("summary", ""))}</desc>')
    out.append('<defs>'
               f'<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
               f'<path d="M0 0.5 L10 5 L0 9.5 z" fill="{INK}"/></marker>'
               f'<marker id="arrow-ochre" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
               f'<path d="M0 0.5 L10 5 L0 9.5 z" fill="{OCHRE2}"/></marker>'
               '</defs>')
    out.append(f'<rect width="{W}" height="{H}" fill="{PAPER2}" rx="12"/>')

    # lanes (pool)
    if m.lanes:
        px, py = MARGIN, m.y0 - 6
        pw, ph = W - 2 * MARGIN, m.n_rows * m.row_h + 12
        out.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" fill="none" stroke="{LINE2}" stroke-width="1.2" rx="6"/>')
        for i, lane in enumerate(m.lanes):
            r0, r1 = min(lane["rows"]), max(lane["rows"]) + 1
            ly, lh = m.y0 + r0 * m.row_h - (6 if i == 0 else 0), (r1 - r0) * m.row_h + (6 if i == 0 else 0) + (6 if i == len(m.lanes) - 1 else 0)
            fill = PAPER if i % 2 else "none"
            out.append(f'<rect x="{px}" y="{ly}" width="{pw}" height="{lh}" fill="{fill}" stroke="{LINE2}" stroke-width="1"/>')
            out.append(f'<rect x="{px}" y="{ly}" width="{LANE_STRIP}" height="{lh}" fill="{PAPER3}" stroke="{LINE2}" stroke-width="1"/>')
            cx_, cy_ = px + LANE_STRIP / 2, ly + lh / 2
            lines = wrap(lane["name"], max(8, int((lh - 16) / 6.3)))
            off = -(len(lines) - 1) * 6
            spans = "".join(f'<tspan x="0" dy="{0 if i == 0 else 12}">{esc(l)}</tspan>' for i, l in enumerate(lines))
            out.append(f'<text transform="translate({cx_+4+off:.1f} {cy_:.1f}) rotate(-90)" text-anchor="middle" font-size="10.5" '
                       f'font-weight="600" fill="{INK2}" letter-spacing=".04em">{spans}</text>')

    # flows first so shapes sit on top
    for f in m.flows:
        pts = m.route(f)
        d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        colour, marker = (OCHRE2, "arrow-ochre") if f.get("tone") == "ochre" else (INK, "arrow")
        dash = ' stroke-dasharray="5 4"' if f.get("dashed") else ""
        out.append(f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="1.6"{dash} marker-end="url(#{marker})" stroke-linejoin="round"/>')
        if f.get("name"):
            (x1, y1), (x2, y2) = pts[0], pts[1]
            horizontal = abs(y2 - y1) < 2
            if horizontal:
                lx, ly, anchor = x1 + 10, y1 - 7, "start"
            else:
                # at the corner where the line turns toward its target
                cx_, cy_ = pts[1]
                nxt = pts[2] if len(pts) > 2 else pts[1]
                lx, ly, anchor = (cx_ + 10, cy_ - 7, "start") if nxt[0] >= cx_ else (cx_ - 10, cy_ - 7, "end")
            tw = len(f["name"]) * 6.4 + 8
            bx = lx - 4 if anchor == "start" else lx - tw + 4
            out.append(f'<rect x="{bx:.1f}" y="{ly-10:.1f}" width="{tw:.1f}" height="14" fill="{m.bg_at(ly)}" rx="3"/>')
            out.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" font-family="{MONO}" font-size="10.5" '
                       f'font-weight="700" fill="{OCHRE2}" letter-spacing=".04em">{esc(f["name"])}</text>')

    # nodes
    for n in m.nodes.values():
        out.append(render_node_svg(m, n))

    out.append("</svg>")
    return "\n".join(out)


def render_node_svg(m: Model, n: dict) -> str:
    t, x, y, w, h = n["type"], n["x"], n["y"], n["w"], n["h"]
    cx, cy = x + w / 2, y + h / 2
    g = []
    label_lines, label_y, label_size, label_colour, label_weight = [], cy, 12.5, INK, 600
    if t in TASK_TYPES:
        stroke = TEAL if t != "subprocess" else TEAL2
        g.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="#fbfaf6" stroke="{stroke}" stroke-width="1.8"/>')
        if t == "subprocess":
            g.append(f'<rect x="{x+1.5}" y="{y+1.5}" width="{w-3}" height="{h-3}" rx="7" fill="none" stroke="{stroke}" stroke-width="1" opacity=".55"/>')
            bx, by = cx - 7, y + h - 15
            g.append(f'<rect x="{bx}" y="{by}" width="14" height="14" rx="2" fill="#fbfaf6" stroke="{INK2}" stroke-width="1.3"/>'
                     f'<path d="M{bx+3} {by+7}h8M{bx+7} {by+3}v8" stroke="{INK2}" stroke-width="1.3"/>')
        g.append(svg_icon(t, x + 9, y + 8))
        label_lines = wrap(n["name"], 20)
        label_y += {1: 0, 2: 3}.get(len(label_lines), 5)
        if t == "subprocess":
            label_y -= 5
    elif t in GATEWAYS:
        g.append(f'<path d="M{cx} {y} L{x+w} {cy} L{cx} {y+h} L{x} {cy} Z" fill="#fbfaf6" stroke="{OCHRE}" stroke-width="1.8" stroke-linejoin="round"/>')
        if t == "xor":
            g.append(f'<path d="M{cx-8} {cy-8}l16 16M{cx+8} {cy-8}l-16 16" stroke="{OCHRE2}" stroke-width="2.2" stroke-linecap="round"/>')
        elif t == "and":
            g.append(f'<path d="M{cx-10} {cy}h20M{cx} {cy-10}v20" stroke="{OCHRE2}" stroke-width="2.2" stroke-linecap="round"/>')
        else:  # event-based
            g.append(f'<circle cx="{cx}" cy="{cy}" r="11" fill="none" stroke="{OCHRE2}" stroke-width="1.3"/>'
                     f'<circle cx="{cx}" cy="{cy}" r="8.5" fill="none" stroke="{OCHRE2}" stroke-width="1.3"/>'
                     f'<path d="M{cx} {cy-5.2} L{cx+5} {cy-1.4} L{cx+3.1} {cy+4.4} L{cx-3.1} {cy+4.4} L{cx-5} {cy-1.4} Z" fill="none" stroke="{OCHRE2}" stroke-width="1.2"/>')
        # gateway label above the diamond (flows usually leave from the bottom)
        label_lines = wrap(n.get("name", ""), 20)
        label_y = y - 9 - (len(label_lines) - 1) * 11.5 * 1.18
        label_size, label_colour, label_weight = 11.5, INK2, 600
    elif t in EVENTS:
        r = w / 2
        sw = 3.2 if t == "end" else 1.8
        fill = "#fbfaf6"
        stroke = INK if t == "end" else TEAL
        g.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
        if t in ("timer", "timer-start"):
            g.append(_clock(cx, cy, r - 7))
        if t == "message":
            g.append(f'<rect x="{cx-9}" y="{cy-6}" width="18" height="12" rx="1.5" fill="none" stroke="{INK}" stroke-width="1.4"/>'
                     f'<path d="M{cx-9} {cy-6}l9 7 9-7" fill="none" stroke="{INK}" stroke-width="1.4"/>')
        if t == "timer":
            g.append(f'<circle cx="{cx}" cy="{cy}" r="{r-3.5}" fill="none" stroke="{TEAL}" stroke-width="1.2"/>')
        label_lines = wrap(n.get("name", ""), 18)
        label_y = y + h + 14
        label_size, label_colour, label_weight = 11.5, INK2, 600
    elif t == "boundary-timer":
        r = w / 2
        g.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#fbfaf6" stroke="{INK}" stroke-width="1.5"/>'
                 f'<circle cx="{cx}" cy="{cy}" r="{r-3}" fill="none" stroke="{INK}" stroke-width="1.1"/>')
        g.append(_clock(cx, cy, r - 6))
        label_lines = wrap(n.get("name", ""), 16)
        label_y = y - 8 - (len(label_lines) - 1) * 10.5 * 1.18
        label_size, label_colour, label_weight = 10.5, INK2, 600
    elif t == "note":
        g.append(f'<path d="M{x+10} {y} H{x} V{y+h} H{x+10}" fill="none" stroke="{INK3}" stroke-width="1.3"/>')
        if n.get("for"):
            tgt = m.nodes[n["for"]]
            tx, ty = m._exit_toward(tgt, (cx, cy))
            g.append(f'<path d="M{x} {cy} L{tx} {ty}" stroke="{INK3}" stroke-width="1.1" stroke-dasharray="3 3" fill="none"/>')
        lines = wrap(n["text"], int(w / 6.0))
        g.append(_text_block(lines, x + 16, y + 14, 11, INK2, 400, "start", 14))
        return "".join(g)

    if label_lines:
        lh = label_size * 1.18
        anchor_x = cx
        ty = label_y - (len(label_lines) - 1) * lh / 2 + label_size * 0.35 if t in TASK_TYPES else label_y + label_size * 0.35
        g.append(_text_block(label_lines, anchor_x, ty, label_size, label_colour, label_weight, "middle", lh))

    # citation / badges
    cite = n.get("cite")
    if cite is not None:
        if t in TASK_TYPES:
            by = y + h + 13
        elif t in GATEWAYS:
            by = label_y - len(label_lines) * 11.5 * 1.18 + 3   # above the name, above the diamond
        else:
            by = y + h + 14 + len(label_lines) * 13.5 + 2
        if cite == "?":
            g.append(f'<text x="{cx}" y="{by}" text-anchor="middle" font-family="{MONO}" font-size="9.5" font-weight="700" '
                     f'fill="{OCHRE2}" letter-spacing=".06em">citation needed</text>')
        else:
            g.append(f'<text x="{cx}" y="{by}" text-anchor="middle" font-family="{MONO}" font-size="9.5" fill="{TEAL2}">{esc(cite)}</text>')
    who_below = bool(n.get("who")) and bool(n.get("inside"))
    if n.get("inside"):
        bw = 96
        bx = x + w - bw - 2
        by = y - 9
        g.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="16" rx="8" fill="{TEAL}"/>'
                 f'<text x="{bx+bw/2}" y="{by+11.5}" text-anchor="middle" font-family="{MONO}" font-size="8.6" font-weight="700" '
                 f'fill="#f6f4ec" letter-spacing=".08em">CAN START INSIDE</text>')
    if n.get("who"):
        wy = (y + h + 13 + (13 if cite is not None else 0)) if who_below else (y - 6)
        g.append(f'<text x="{x}" y="{wy}" font-family="{MONO}" font-size="9.5" fill="{INK3}" letter-spacing=".08em">{esc(n["who"].upper())}</text>')
    return "".join(g)


def _clock(cx, cy, r):
    ticks = "".join(
        f'<path d="M{cx + r * math.cos(a):.1f} {cy + r * math.sin(a):.1f} L{cx + (r - 3) * math.cos(a):.1f} {cy + (r - 3) * math.sin(a):.1f}"/>'
        for a in [i * math.pi / 6 for i in range(12)])
    return (f'<g fill="none" stroke="{INK}" stroke-width="1.2" stroke-linecap="round">'
            f'<circle cx="{cx}" cy="{cy}" r="{r}"/>{ticks}'
            f'<path d="M{cx} {cy}L{cx} {cy-r*0.65}M{cx} {cy}L{cx+r*0.45} {cy+r*0.3}"/></g>')


def _text_block(lines, x, y, size, colour, weight, anchor, lh):
    tspans = "".join(f'<tspan x="{x:.1f}" dy="{0 if i == 0 else lh:.1f}">{esc(l)}</tspan>' for i, l in enumerate(lines))
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" font-weight="{weight}" '
            f'fill="{colour}">{tspans}</text>')


# ----------------------------------------------------------------------------- BPMN XML
BPMN_TAG = {
    "start": "startEvent", "timer-start": "startEvent", "end": "endEvent",
    "timer": "intermediateCatchEvent", "message": "intermediateCatchEvent",
    "xor": "exclusiveGateway", "and": "parallelGateway", "event": "eventBasedGateway",
    "task": "task", "user": "userTask", "service": "serviceTask", "script": "scriptTask",
    "rule": "businessRuleTask", "manual": "manualTask", "subprocess": "subProcess",
    "boundary-timer": "boundaryEvent",
}


def render_bpmn(m: Model) -> str:
    L = []
    pid = f"Process_{m.id}"
    L.append('<?xml version="1.0" encoding="UTF-8"?>')
    L.append('<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" '
             'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" '
             'xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" '
             'xmlns:di="http://www.omg.org/spec/DD/20100524/DI" '
             'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
             f'id="Definitions_{m.id}" targetNamespace="https://doingprocess.org/bpmn" exporter="doingprocess build_diagrams.py" exporterVersion="1">')
    L.append(f'  <bpmn:collaboration id="Collab_{m.id}">')
    L.append(f'    <bpmn:participant id="Participant_{m.id}" name={quoteattr(m.name)} processRef="{pid}" />')
    L.append('  </bpmn:collaboration>')
    L.append(f'  <bpmn:process id="{pid}" name={quoteattr(m.name)} isExecutable="false">')
    if m.spec.get("summary"):
        L.append(f'    <bpmn:documentation>{esc(m.spec["summary"])}</bpmn:documentation>')
    if m.lanes:
        L.append(f'    <bpmn:laneSet id="LaneSet_{m.id}">')
        for i, lane in enumerate(m.lanes):
            L.append(f'      <bpmn:lane id="Lane_{m.id}_{i}" name={quoteattr(lane["name"])}>')
            for n in m.nodes.values():
                if n["type"] != "note" and int(math.floor(n["row"])) in lane["rows"]:
                    L.append(f'        <bpmn:flowNodeRef>{n["id"]}</bpmn:flowNodeRef>')
            L.append('      </bpmn:lane>')
        L.append('    </bpmn:laneSet>')
    incoming = {k: [] for k in m.nodes}
    outgoing = {k: [] for k in m.nodes}
    for i, f in enumerate(m.flows):
        f["_id"] = f"Flow_{i}"
        outgoing[f["from"]].append(f["_id"])
        incoming[f["to"]].append(f["_id"])
    for n in m.nodes.values():
        t = n["type"]
        if t == "note":
            L.append(f'    <bpmn:textAnnotation id="{n["id"]}"><bpmn:text>{esc(n["text"])}</bpmn:text></bpmn:textAnnotation>')
            if n.get("for"):
                L.append(f'    <bpmn:association id="Assoc_{n["id"]}" sourceRef="{n["for"]}" targetRef="{n["id"]}" />')
            continue
        attrs = f'id="{n["id"]}"'
        if n.get("name"):
            attrs += f' name={quoteattr(n["name"])}'
        if t == "boundary-timer":
            attrs += f' attachedToRef="{n["attached"]}" cancelActivity="{"false" if n.get("non_interrupting") else "true"}"'
        L.append(f'    <bpmn:{BPMN_TAG[t]} {attrs}>')
        doc = []
        if n.get("cite") and n["cite"] != "?":
            doc.append(f"Authority: {n['cite']}")
        if n.get("cite") == "?":
            doc.append("Authority: CITATION NEEDED")
        if n.get("inside"):
            doc.append("Can start before release: yes")
        if n.get("who"):
            doc.append(f"Role: {n['who']}")
        if doc:
            L.append(f'      <bpmn:documentation>{esc("; ".join(doc))}</bpmn:documentation>')
        for fid in incoming[n["id"]]:
            L.append(f'      <bpmn:incoming>{fid}</bpmn:incoming>')
        for fid in outgoing[n["id"]]:
            L.append(f'      <bpmn:outgoing>{fid}</bpmn:outgoing>')
        if t in ("timer", "timer-start", "boundary-timer"):
            dur = n.get("duration")
            inner = f'<bpmn:timeDuration xsi:type="bpmn:tFormalExpression">{esc(dur)}</bpmn:timeDuration>' if dur else ""
            L.append(f'      <bpmn:timerEventDefinition id="TimerDef_{n["id"]}">{inner}</bpmn:timerEventDefinition>')
        if t == "message":
            L.append(f'      <bpmn:messageEventDefinition id="MsgDef_{n["id"]}" />')
        L.append(f'    </bpmn:{BPMN_TAG[t]}>')
    for f in m.flows:
        attrs = f'id="{f["_id"]}" sourceRef="{f["from"]}" targetRef="{f["to"]}"'
        if f.get("name"):
            attrs += f' name={quoteattr(f["name"])}'
        L.append(f'    <bpmn:sequenceFlow {attrs} />')
    L.append('  </bpmn:process>')

    # --- DI
    L.append(f'  <bpmndi:BPMNDiagram id="Diagram_{m.id}">')
    L.append(f'    <bpmndi:BPMNPlane id="Plane_{m.id}" bpmnElement="Collab_{m.id}">')
    pw = m.width - 2 * MARGIN
    ph = m.n_rows * m.row_h + 12
    L.append(f'      <bpmndi:BPMNShape id="Participant_{m.id}_di" bpmnElement="Participant_{m.id}" isHorizontal="true">'
             f'<dc:Bounds x="{MARGIN}" y="{m.y0-6}" width="{pw:.0f}" height="{ph:.0f}" /></bpmndi:BPMNShape>')
    for i, lane in enumerate(m.lanes):
        r0, r1 = min(lane["rows"]), max(lane["rows"]) + 1
        L.append(f'      <bpmndi:BPMNShape id="Lane_{m.id}_{i}_di" bpmnElement="Lane_{m.id}_{i}" isHorizontal="true">'
                 f'<dc:Bounds x="{MARGIN+30}" y="{m.y0 + r0*m.row_h:.0f}" width="{pw-30:.0f}" height="{(r1-r0)*m.row_h:.0f}" /></bpmndi:BPMNShape>')
    for n in m.nodes.values():
        extra = ' isExpanded="false"' if n["type"] == "subprocess" else ""
        L.append(f'      <bpmndi:BPMNShape id="{n["id"]}_di" bpmnElement="{n["id"]}"{extra}>'
                 f'<dc:Bounds x="{n["x"]:.0f}" y="{n["y"]:.0f}" width="{n["w"]:.0f}" height="{n["h"]:.0f}" /></bpmndi:BPMNShape>')
        if n["type"] == "note" and n.get("for"):
            tgt = m.nodes[n["for"]]
            tx, ty = m._exit_toward(tgt, (n["x"] + n["w"] / 2, n["y"] + n["h"] / 2))
            L.append(f'      <bpmndi:BPMNEdge id="Assoc_{n["id"]}_di" bpmnElement="Assoc_{n["id"]}">'
                     f'<di:waypoint x="{tx:.0f}" y="{ty:.0f}" /><di:waypoint x="{n["x"]:.0f}" y="{n["y"]+n["h"]/2:.0f}" /></bpmndi:BPMNEdge>')
    for f in m.flows:
        wps = "".join(f'<di:waypoint x="{x:.0f}" y="{y:.0f}" />' for x, y in m.route(f))
        L.append(f'      <bpmndi:BPMNEdge id="{f["_id"]}_di" bpmnElement="{f["_id"]}">{wps}</bpmndi:BPMNEdge>')
    L.append('    </bpmndi:BPMNPlane>')
    L.append('  </bpmndi:BPMNDiagram>')
    L.append('</bpmn:definitions>')
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------------------- legend
def render_legend() -> str:
    spec = {
        "id": "legend", "name": "How to read these maps", "col_width": 150, "row_height": 96,
        "nodes": [
            {"id": "l_start", "type": "start", "name": "start", "col": 0, "row": 0},
            {"id": "l_task", "type": "user", "name": "a step someone does", "col": 1, "row": 0, "cite": "Va. Code § 00.0-000"},
            {"id": "l_xor", "type": "xor", "name": "a question: one way out", "col": 2, "row": 0},
            {"id": "l_sub", "type": "subprocess", "name": "a smaller process inside", "col": 3, "row": 0, "inside": True},
            {"id": "l_rule", "type": "rule", "name": "a decision table (DMN) decides", "col": 4, "row": 0, "cite": "?"},
            {"id": "l_ev", "type": "event", "name": "waiting: whichever comes first", "col": 5, "row": 0},
            {"id": "l_msg", "type": "message", "name": "an answer arrives", "col": 6, "row": 0},
            {"id": "l_timer", "type": "timer", "name": "a clock runs out", "col": 6, "row": 1},
            {"id": "l_end", "type": "end", "name": "end", "col": 7, "row": 0},
            {"id": "l_b", "type": "boundary-timer", "attached": "l_task", "name": "a deadline on a step"},
        ],
        "flows": [
            {"from": "l_start", "to": "l_task"}, {"from": "l_task", "to": "l_xor"},
            {"from": "l_xor", "to": "l_sub", "name": "yes"}, {"from": "l_sub", "to": "l_rule"},
            {"from": "l_rule", "to": "l_ev"}, {"from": "l_ev", "to": "l_msg"}, {"from": "l_ev", "to": "l_timer"},
            {"from": "l_msg", "to": "l_end"},
        ],
    }
    return render_svg(Model(spec))


# ----------------------------------------------------------------------------- main
def main(argv: list[str]) -> int:
    OUT_BPMN.mkdir(parents=True, exist_ok=True)
    OUT_SVG.mkdir(parents=True, exist_ok=True)
    OUT_SITE_MODELS.mkdir(parents=True, exist_ok=True)
    for dmn in (ROOT / "models" / "dmn").glob("*.dmn"):
        (OUT_SITE_MODELS / dmn.name).write_text(dmn.read_text(encoding="utf-8"), encoding="utf-8")
    specs = sorted(SRC.glob("*.json"))
    if not specs:
        print(f"no specs in {SRC}", file=sys.stderr)
        return 1
    for p in specs:
        spec = json.loads(p.read_text(encoding="utf-8"))
        m = Model(spec)
        (OUT_SVG / f"{m.id}.svg").write_text(render_svg(m), encoding="utf-8")
        bpmn = render_bpmn(m)
        (OUT_BPMN / f"{m.id}.bpmn").write_text(bpmn, encoding="utf-8")
        (OUT_SITE_MODELS / f"{m.id}.bpmn").write_text(bpmn, encoding="utf-8")
        print(f"  {m.id:<22} {m.width:.0f}x{m.height:.0f}px  {len(m.nodes)} nodes, {len(m.flows)} flows")
    (OUT_SVG / "legend.svg").write_text(render_legend(), encoding="utf-8")
    print("  legend")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
