"""Walk every reachable state of a state machine and show the shortest way into each fault.

Faults: a state that is not final and has no way out (deadlock), states from which no final state can ever be reached
(livelock), states nothing leads to (orphan), and one event leading to two different states (race). The machine comes
from the message ("durum makinesi: yeni -onayla-> onaylı; ... ; son: kapalı") or from a `TRANSITIONS` table in the
project's Python or JavaScript.
"""

from __future__ import annotations

import ast
import json
import re
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

_ASK_RE = re.compile(r"^\s*durum\s+makinesi(?:ni)?(?:\s+(?:denetle|doğrula|kontrol\s+et))?\s*(?::\s*(?P<body>.+))?$", re.IGNORECASE | re.DOTALL)
_EDGE_RE = re.compile(r"^\s*(?P<from>[\w çğıöşüÇĞİÖŞÜ]+?)\s*-\s*(?P<event>[^-<>;]*?)\s*->\s*(?P<to>[\w çğıöşüÇĞİÖŞÜ]+?)\s*$")
_FINAL_RE = re.compile(r"^\s*(?:son|final|bitiş)\s*:\s*(?P<names>.+)$", re.IGNORECASE)
_START_RE = re.compile(r"^\s*(?:başlangıç|start)\s*:\s*(?P<name>.+)$", re.IGNORECASE)
_JS_RE = re.compile(r"(?:const|let|var|export const)\s+(\w*TRANSITIONS?\w*|\w*[Tt]ransitions)\s*=\s*(\{.*?\n\});", re.DOTALL)


@dataclass
class Machine:
    edges: list[tuple[str, str, str]] = field(default_factory=list)  # (from, event, to)
    start: str = ""
    final: set[str] = field(default_factory=set)
    name: str = "durum makinesi"

    def states(self) -> list[str]:
        out = [self.start] if self.start else []
        for a, _e, b in self.edges:
            out += [a, b]
        return list(dict.fromkeys(out + sorted(self.final)))


def from_text(body: str) -> Machine | None:
    machine = Machine()
    for line in re.split(r"[;\n]+", body):
        if match := _FINAL_RE.match(line):
            machine.final |= {n.strip() for n in match["names"].split(",") if n.strip()}
        elif match := _START_RE.match(line):
            machine.start = match["name"].strip()
        elif match := _EDGE_RE.match(line):
            machine.edges.append((match["from"], match["event"], match["to"]))
    if not machine.edges:
        return None
    machine.start = machine.start or machine.edges[0][0]
    return machine


def from_table(table: dict, name: str) -> Machine | None:
    """{state: {event: next}} or {state: [next, ...]}."""
    machine = Machine(name=name, start=str(next(iter(table), "")))
    for state, out in table.items():
        pairs = out.items() if isinstance(out, dict) else [("", t) for t in out] if isinstance(out, list | tuple | set) else None
        if pairs is None:
            return None
        for event, target in pairs:
            machine.edges += [(str(state), str(event), str(t)) for t in (target if isinstance(target, list | tuple) else [target])]
    machine.final = {s for s in machine.states() if s.casefold() in ("done", "closed", "cancelled", "completed", "finished", "bitti", "kapalı", "iptal")}
    return machine if machine.edges else None


def in_project(ws_dir: Path) -> list[Machine]:
    found = []
    for path in sorted(ws_dir.rglob("*")):
        if ".history" in path.parts or path.suffix not in (".py", ".js", ".ts") or not path.is_file():
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        tables: list[tuple[str, str]] = []
        if path.suffix == ".py":
            try:
                nodes = ast.walk(ast.parse(source))
            except SyntaxError:
                continue
            for node in nodes:
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict) and any("transition" in ast.unparse(t).lower() for t in node.targets):
                    tables.append((ast.unparse(node.targets[0]), ast.unparse(node.value)))
        else:
            tables = [(name, re.sub(r"([{,]\s*)([A-Za-z_]\w*)\s*:", r'\1"\2":', body.replace("'", '"'))) for name, body in _JS_RE.findall(source)]
        for name, body in tables:
            try:
                value = ast.literal_eval(body) if path.suffix == ".py" else json.loads(re.sub(r",(\s*[}\]])", r"\1", body))
            except (ValueError, SyntaxError):
                continue
            if machine := from_table(value, f"{path.name}:{name}"):
                found.append(machine)
    return found


def _paths(machine: Machine) -> dict[str, list[str]]:
    """Shortest event path to every reachable state (breadth first, so each path is minimal)."""
    paths = {machine.start: [machine.start]}
    queue = deque([machine.start])
    while queue:
        state = queue.popleft()
        for source, event, target in machine.edges:
            if source == state and target not in paths:
                paths[target] = [*paths[state], f"-{event}-> {target}" if event else f"-> {target}"]
                queue.append(target)
    return paths


def _can_finish(machine: Machine, finals: set[str]) -> set[str]:
    good = set(finals)
    while grown := {a for a, _e, b in machine.edges if b in good and a not in good}:
        good |= grown
    return good


def check(machine: Machine) -> dict[str, list[str]]:
    paths = _paths(machine)
    sources = {a for a, _e, _b in machine.edges}
    finals = machine.final or {s for s in machine.states() if s not in sources}
    declared = bool(machine.final)
    deadlocks = [" ".join(paths[s]) for s in paths if s not in sources and declared and s not in finals]
    good = _can_finish(machine, finals) if finals else set()
    livelocks = [" ".join(paths[s]) for s in paths if s in sources and s not in good]
    races: dict[tuple[str, str], set[str]] = {}
    for a, event, b in machine.edges:
        if event:
            races.setdefault((a, event), set()).add(b)
    return {
        "Ulaşılan durumlar": [f"{len(paths)}/{len(machine.states())} (başlangıç: {machine.start}, son: {', '.join(sorted(finals)) or 'yok'})"],
        "Çıkmaz (deadlock)": deadlocks,
        "Bitişe hiç ulaşamayan döngü (livelock)": livelocks,
        "Hiçbir yoldan ulaşılamayan": [s for s in machine.states() if s not in paths],
        "Aynı olay iki farklı duruma (yarış)": [f"{a} · {e} → {', '.join(sorted(t))}" for (a, e), t in races.items() if len(t) > 1],
    }


def report(machine: Machine) -> str:
    result = check(machine)
    faults = sum(len(v) for k, v in result.items() if k != "Ulaşılan durumlar")
    lines = [f"**{machine.name}** — tüm durumlar tarandı, {faults} sorun." if faults else f"**{machine.name}** — tüm durumlar tarandı, sorun yok."]
    for title, items in result.items():
        if items:
            lines.append(f"- {title}: " + " | ".join(items[:6]))
    return "\n".join(lines)


def answer(prompt: str, ws_dir: Path | None) -> str:
    match = _ASK_RE.match(prompt)
    if not match:
        return ""
    if match["body"] and (machine := from_text(match["body"])):
        return report(machine)
    machines = in_project(ws_dir) if ws_dir else []
    if machines:
        return "\n\n".join(report(m) for m in machines[:4])
    return "Taranacak makine bulamadım. Yaz: `durum makinesi: yeni -onayla-> onaylı; onaylı -kapat-> kapalı; son: kapalı` ya da projede `TRANSITIONS` tablosu olsun."
