"""Flow diagrams that follow the user's process: the model lists steps and arrows, code lays them out and draws the SVG."""

from __future__ import annotations

import re
from html import escape
from typing import Any

_FLOW_RE = re.compile(r"(akış|akis|flowchart|flow\s*chart|süreç|surec|workflow|iş\s+akışı|process\s+flow|flow\s+diagram|adımları|adimlari)", re.IGNORECASE)
_NOT_FLOW_RE = re.compile(r"(mimari|architecture|yol\s+haritası|roadmap|infografik)", re.IGNORECASE)
SYSTEM = (
    "Return ONLY JSON describing the flow the user asked for, in the USER'S language: "
    '{"title":"short title","steps":[{"id":"s1","type":"start|process|decision|end","label":"max 5 words"}],'
    '"edges":[{"from":"s1","to":"s2","label":"" }]}. 6 to 11 steps. Exactly one start and at least one end. '
    "A decision has two outgoing edges labelled with the answers (Evet/Hayır or Yes/No). Every step except the end must have an outgoing edge, "
    "and every step must be reachable from the start. The success answer (Evet) continues forward to the next real step; the failure answer (Hayır) "
    "returns to the input step or shows an error and ends. "
    "Example for a order process: s1 start Sipariş al; s2 process Stok kontrol et; s3 decision Stok var mı?; s3 -Evet-> s4 process Ödemeyi al; "
    "s3 -Hayır-> s5 end Müşteriyi bilgilendir; s4 -> s6 end Kargoya ver. "
    "Use only steps that are directly part of this process (no languages, settings or extras the user did not mention)."
)
W, H, DH, GX, GY = 200, 62, 84, 70, 56


def missing_steps(prompt: str, flow: dict[str, Any]) -> list[str]:
    """Clauses the user listed ("...: a, b, c") that no box of the drawing mentions."""
    listed = prompt.split(":", 1)[1] if ":" in prompt else ""
    labels = " ".join(s["label"] for s in flow["steps"]).casefold()
    clauses = [c.strip() for c in re.split(r"[,;.→\n]|->", listed) if len(c.strip()) > 3]
    return [c for c in clauses if not any(w[:4] in labels for w in re.findall(r"\w{4,}", c.casefold()))]


def stuck_steps(flow: dict[str, Any]) -> list[str]:
    """Steps from which no end can be reached: the process would loop for ever there (checked over every path)."""
    finishing = {s["id"] for s in flow["steps"] if s["type"] == "end"}
    grew = True
    while grew:
        grew = False
        for e in flow["edges"]:
            if e["to"] in finishing and e["from"] not in finishing:
                finishing.add(e["from"])
                grew = True
    return [s["label"] for s in flow["steps"] if s["id"] not in finishing]


def is_flow_request(prompt: str) -> bool:
    return bool(_FLOW_RE.search(prompt or "")) and not _NOT_FLOW_RE.search(prompt or "")


def clean(parsed: dict[str, Any] | None) -> dict[str, Any] | None:
    """Validated {"title","steps","edges"} or None when the model's flow is unusable."""
    if not isinstance(parsed, dict) or not isinstance(parsed.get("steps"), list):
        return None
    steps, seen = [], set()
    for s in parsed["steps"][:12]:
        sid = str(s.get("id") or "").strip() if isinstance(s, dict) else ""
        label = str(s.get("label") or "").strip()[:48] if isinstance(s, dict) else ""
        if sid and label and sid not in seen:
            kind = "decision" if label.endswith("?") else str(s.get("type") or "process").lower()
            steps.append({"id": sid, "type": kind if kind in ("start", "process", "decision", "end") else "process", "label": label})
            seen.add(sid)
    edges = [
        {"from": str(e["from"]), "to": str(e["to"]), "label": str(e.get("label") or "")[:14]}
        for e in parsed.get("edges") or []
        if isinstance(e, dict) and str(e.get("from")) in seen and str(e.get("to")) in seen and e.get("from") != e.get("to")
    ]
    if not any(s["type"] == "start" for s in steps):
        return None
    steps, edges = _tidy(steps, edges)
    if len(steps) < 4 or len(edges) < len(steps) - 2 or not any(s["type"] == "end" for s in steps):
        return None
    return {"title": str(parsed.get("title") or "").strip()[:60], "steps": steps, "edges": edges}


def _tidy(steps: list[dict[str, str]], edges: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Drop steps the start cannot reach (stray model additions), make dead ends 'end' steps, demote one-way 'decisions'."""
    start = next(s["id"] for s in steps if s["type"] == "start")
    reach, todo = {start}, [start]
    while todo:
        cur = todo.pop()
        for e in edges:
            if e["from"] == cur and e["to"] not in reach:
                reach.add(e["to"])
                todo.append(e["to"])
    steps = [dict(s) for s in steps if s["id"] in reach]
    edges = [e for e in edges if e["from"] in reach and e["to"] in reach]
    for s in steps:
        outs = sum(e["from"] == s["id"] for e in edges)
        if outs == 0 and s["type"] != "end":
            s["type"] = "end"
        elif s["type"] == "decision" and outs < 2:
            s["type"] = "process"
    return steps, edges


def _back_edges(spec: dict[str, Any], start: str) -> set[int]:
    """Indexes of edges that return to a step still being explored (loops); found with an iterative depth-first walk."""
    state: dict[str, int] = {}
    back: set[int] = set()
    stack = [(start, iter([i for i, e in enumerate(spec["edges"]) if e["from"] == start]))]
    state[start] = 1
    while stack:
        node, it = stack[-1]
        for i in it:
            target = spec["edges"][i]["to"]
            if state.get(target) == 1:
                back.add(i)
            elif target not in state:
                state[target] = 1
                stack.append((target, iter([j for j, e in enumerate(spec["edges"]) if e["from"] == target])))
                break
        else:
            state[node] = 2
            stack.pop()
    return back


def _layers(spec: dict[str, Any]) -> dict[str, int]:
    """Longest-path layers over the forward edges (arrows that return to an earlier step are loops and do not count)."""
    start = next(s["id"] for s in spec["steps"] if s["type"] == "start")
    back = _back_edges(spec, start)
    forward = [e for i, e in enumerate(spec["edges"]) if i not in back]
    depth = {s["id"]: 0 for s in spec["steps"]}
    for _ in range(len(depth)):
        for e in forward:
            depth[e["to"]] = max(depth[e["to"]], depth[e["from"]] + 1)
    return depth


def _wrap(label: str, width: int = 22) -> list[str]:
    lines, cur = [], ""
    for word in label.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return [*lines, cur][:3]


def _positions(spec: dict[str, Any]) -> tuple[dict[str, tuple[int, int]], int, int]:
    depth = _layers(spec)
    by_layer: dict[int, list[str]] = {}
    for s in spec["steps"]:
        by_layer.setdefault(depth[s["id"]], []).append(s["id"])
    cols = max(len(v) for v in by_layer.values())
    width = max(cols * (W + GX) + 160, 560)
    pos = {}
    for layer, ids in by_layer.items():
        for i, sid in enumerate(ids):
            pos[sid] = (int(width / 2 + (i - (len(ids) - 1) / 2) * (W + GX)), 110 + layer * (DH + GY))
    return pos, width, 110 + (max(by_layer) + 1) * (DH + GY) + 20


def _shape(step: dict[str, str], cx: int, cy: int, pal: dict[str, str]) -> str:
    kind, fill, stroke = step["type"], pal["bg2"], pal["primary"]
    if kind == "decision":
        shape = f'<polygon points="{cx},{cy - DH // 2} {cx + W // 2},{cy} {cx},{cy + DH // 2} {cx - W // 2},{cy}" fill="{fill}" stroke="{pal["accent"]}" stroke-width="2.5"/>'
    elif kind in ("start", "end"):
        shape = f'<rect x="{cx - W // 2}" y="{cy - H // 2}" width="{W}" height="{H}" rx="{H // 2}" fill="{stroke}" opacity="0.92"/>'
    else:
        shape = f'<rect x="{cx - W // 2}" y="{cy - H // 2}" width="{W}" height="{H}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>'
    color = pal["bg1"] if kind in ("start", "end") else pal["text"]
    lines = _wrap(step["label"])
    texts = "".join(
        f'<text x="{cx}" y="{cy + (i - (len(lines) - 1) / 2) * 17 + 5}" text-anchor="middle" fill="{color}" font-family="Segoe UI, Arial, sans-serif" font-size="14" font-weight="600">{escape(line)}</text>'
        for i, line in enumerate(lines)
    )
    return shape + texts


def _edge(e: dict[str, str], pos: dict[str, tuple[int, int]], kinds: dict[str, str], pal: dict[str, str]) -> str:
    (x1, y1), (x2, y2) = pos[e["from"]], pos[e["to"]]
    sy = y1 + (DH // 2 if kinds[e["from"]] == "decision" else H // 2)
    ty = y2 - (DH // 2 if kinds[e["to"]] == "decision" else H // 2)
    if y2 > y1 + DH + GY + 10:  # skips a layer: detour along the left margin so the arrow never runs behind another step
        side = min(p[0] for p in pos.values()) - W // 2 - 45
        path, lx, ly = f"M{x1},{sy} V{sy + 16} H{side} V{ty - 16} H{x2} V{ty}", x1 + 6, sy + 12
    elif y2 > y1:
        mid = (sy + ty) // 2
        path, lx, ly = f"M{x1},{sy} V{mid} H{x2} V{ty}", (x1 + x2) // 2 + 6, mid - 6
    else:  # a loop back to an earlier step: around the right-hand side
        side = max(x1, x2) + W // 2 + 40
        path, lx, ly = f"M{x1 + W // 2},{y1} H{side} V{y2} H{x2 + W // 2}", side + 6, (y1 + y2) // 2
    label = f'<text x="{lx}" y="{ly}" fill="{pal["accent"]}" font-family="Segoe UI, Arial, sans-serif" font-size="13" font-weight="700">{escape(e["label"])}</text>' if e["label"] else ""
    return f'<path d="{path}" fill="none" stroke="{pal["muted"]}" stroke-width="2"/>{_arrow_head(e, pos, ty, pal)}{label}'


def _arrow_head(e: dict[str, str], pos: dict[str, tuple[int, int]], ty: int, pal: dict[str, str]) -> str:
    """Filled triangle at the arrow's end (drawn as a shape: SVG markers are dropped by some rasterisers)."""
    (_, y1), (x2, y2) = pos[e["from"]], pos[e["to"]]
    if y2 > y1:
        pts = f"{x2},{ty} {x2 - 7},{ty - 13} {x2 + 7},{ty - 13}"
    else:
        tx = x2 + W // 2
        pts = f"{tx},{y2} {tx + 13},{y2 - 7} {tx + 13},{y2 + 7}"
    return f'<polygon points="{pts}" fill="{pal["muted"]}"/>'


def exports(spec: dict[str, Any]) -> dict[str, str]:
    """The same steps and arrows as Mermaid, Graphviz and PlantUML text, for editing in other tools."""
    def clean_label(text: str) -> str:
        return re.sub(r'["\[\]{}|<>\n]', " ", text).strip()

    ids = {s["id"]: f"n{i}" for i, s in enumerate(spec["steps"], start=1)}
    shapes = {"start": ("([", "])"), "end": ("([", "])"), "decision": ("{", "}"), "process": ("[", "]")}
    mermaid = ["flowchart TD"] + [f'  {ids[s["id"]]}{shapes[s["type"]][0]}"{clean_label(s["label"])}"{shapes[s["type"]][1]}' for s in spec["steps"]]
    mermaid += [f'  {ids[e["from"]]} -->' + (f'|{clean_label(e["label"])}|' if e.get("label") else "") + f' {ids[e["to"]]}' for e in spec["edges"]]
    kinds = {"start": "oval", "end": "oval", "decision": "diamond", "process": "box"}
    dot = ["digraph akis {", "  rankdir=TB;"] + [f'  {ids[s["id"]]} [shape={kinds[s["type"]]}, label="{clean_label(s["label"])}"];' for s in spec["steps"]]
    dot += [f'  {ids[e["from"]]} -> {ids[e["to"]]}' + (f' [label="{clean_label(e["label"])}"]' if e.get("label") else "") + ";" for e in spec["edges"]] + ["}"]
    puml = ["@startuml"] + [f'rectangle "{clean_label(s["label"])}" as {ids[s["id"]]}' for s in spec["steps"]]
    puml += [f'{ids[e["from"]]} --> {ids[e["to"]]}' + (f' : {clean_label(e["label"])}' if e.get("label") else "") for e in spec["edges"]] + ["@enduml"]
    return {"mmd": "\n".join(mermaid) + "\n", "dot": "\n".join(dot) + "\n", "puml": "\n".join(puml) + "\n"}


def render(spec: dict[str, Any], pal: dict[str, str]) -> str:
    """SVG of the flow: shapes by step type, elbow arrows, answer labels on decision branches."""
    pos, width, height = _positions(spec)
    kinds = {s["id"]: s["type"] for s in spec["steps"]}
    body = "".join(_edge(e, pos, kinds, pal) for e in spec["edges"]) + "".join(_shape(s, *pos[s["id"]], pal) for s in spec["steps"])
    title = f'<text x="{width // 2}" y="56" text-anchor="middle" fill="{pal["text"]}" font-family="Segoe UI, Arial, sans-serif" font-size="26" font-weight="800">{escape(spec["title"])}</text>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
        f''
        f'<rect width="{width}" height="{height}" fill="{pal["bg1"]}"/>{title}{body}</svg>'
    )
