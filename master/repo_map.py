"""A compact map of a workspace for the model: the most connected files first, within a character budget.

Symbols and import edges come from code_graph; files named in the request and files that depend on them rank higher,
so a large project fits in a small context. `affected` lists who breaks when a file changes.
"""

from __future__ import annotations

from pathlib import Path

import code_graph


def rank(nodes: list[str], edges: list[dict[str, str]], focus: set[str], rounds: int = 30) -> dict[str, float]:
    """PageRank over "source depends on target": heavily used files score high, with weight pulled towards `focus`."""
    if not nodes:
        return {}
    base = {n: (3.0 if n in focus else 1.0) for n in nodes}
    total = sum(base.values())
    base = {n: v / total for n, v in base.items()}
    out: dict[str, list[str]] = {n: [] for n in nodes}
    for edge in edges:
        if edge["source"] in out and edge["target"] in out:
            out[edge["source"]].append(edge["target"])
    score = dict(base)
    for _ in range(rounds):
        loose = sum(score[n] for n in nodes if not out[n])
        new = {n: 0.15 * base[n] + 0.85 * loose * base[n] for n in nodes}
        for source, targets in out.items():
            for target in targets:
                new[target] += 0.85 * score[source] / len(targets)
        score = new
    return score


def affected(edges: list[dict[str, str]], changed: set[str]) -> list[str]:
    """Files that directly or indirectly depend on the changed ones (the blast radius), without the changed files."""
    seen = set(changed)
    frontier = list(changed)
    while frontier:
        current = frontier.pop()
        for edge in edges:
            if edge["target"] == current and edge["source"] not in seen:
                seen.add(edge["source"])
                frontier.append(edge["source"])
    return sorted(seen - changed)


def build(ws_dir: Path, request: str, budget: int = 6000) -> str:
    """Signatures of the most relevant files; '' when the project has no analysable code."""
    graph = code_graph.build_workspace_code_graph(ws_dir)
    symbols = graph["symbols"]
    focus = {path for path in symbols if path.lower() in request.lower() or Path(path).name.lower() in request.lower()}
    scores = rank(list(symbols), graph["edges"], focus)
    parts: list[str] = []
    used = 0
    skipped: list[str] = []
    for path in sorted(symbols, key=lambda p: (p not in focus, -scores[p], p)):
        block = code_graph._format_symbol_contract(path, symbols[path])
        if used + len(block) > budget:
            skipped.append(path)
            continue
        parts.append(block)
        used += len(block)
    if skipped:
        parts.append("Diğer dosyalar (yalnız ad): " + ", ".join(skipped)[:800])
    return "\n".join(parts)


def affected_tests(ws_dir: Path, changed: list[str]) -> list[str]:
    """Test files that import a changed file directly or indirectly, plus changed test files."""
    graph = code_graph.build_workspace_code_graph(ws_dir)
    reached = [*changed, *affected(graph["edges"], set(changed))]
    return sorted({p for p in reached if Path(p).name.startswith("test_") and p.endswith(".py")})


def dependents_note(ws_dir: Path, changed: list[str]) -> str:
    """A warning line naming unchanged files that depend on what was edited."""
    graph = code_graph.build_workspace_code_graph(ws_dir)
    found = affected(graph["edges"], set(changed))
    broken = [f"{b['source']} -> {b['target']}" for b in graph["broken_references"]]
    notes = []
    if broken:
        notes.append("Kırık başvuru: " + ", ".join(broken[:4]))
    if found:
        notes.append("Değişen dosyalara bağlı olup güncellenmeyen dosyalar (kontrol edin): " + ", ".join(found[:6]))
    return "; ".join(notes)
