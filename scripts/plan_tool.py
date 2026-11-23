#!/usr/bin/env python
"""Validate and count the v2 plan, track evidence-based progress, and check module wiring.

  python scripts/plan_tool.py check            parse docs/plan-v2/0*.md, validate, print counts
  python scripts/plan_tool.py status           merge PROGRESS.json; "done" needs tests + commit
  python scripts/plan_tool.py wiring           modules not reachable from master/app.py
  python scripts/plan_tool.py wiring --write-allowlist
  python scripts/plan_tool.py wiring --fail-on-new --facades

Plan files can never declare an item finished: every item must say "Durum: açık", and the only
place a status changes is PROGRESS.json, where "done" is rejected without test and commit evidence.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN_DIR = ROOT / "docs" / "plan-v2"
MASTER_DIR = ROOT / "master"

HEADING = re.compile(r"^#### ([A-Z]+-\d{2}) · (.+?)\s*$")
BULLET = re.compile(r"^- \*\*(Sorun|Değişiklik|Kabul|Meta):\*\* (.*)$")
META = re.compile(r"^(P[0-3]) · (S|M|L|XL) · Bağ: (.*?) · Durum: (\S+)$")
SOURCE_TAG = re.compile(r"^\[(DOĞRULANDI(?:: (F\d+(?:/F\d+)*))?|ÖNERİ)\]")
FINDING_ROW = re.compile(r"^\|\s*(F\d+)\s*\|")
EN_DASH = chr(0x2013)
EFFORT_DAYS = {"S": 0.5, "M": 2.0, "L": 7.0, "XL": 15.0}
BULLETS = ("Sorun", "Değişiklik", "Kabul", "Meta")


@dataclass
class Item:
    id: str
    title: str
    file: str
    line: int
    bullets: dict[str, str] = field(default_factory=dict)
    priority: str = ""
    effort: str = ""
    deps: list[str] = field(default_factory=list)
    status: str = ""
    verified: bool = False
    findings: list[str] = field(default_factory=list)

    @property
    def area(self) -> str:
        return self.id.split("-")[0]


def parse_plan(plan_dir: Path) -> tuple[list[Item], list[str]]:
    items: list[Item] = []
    errors: list[str] = []
    for path in sorted(plan_dir.glob("0[1-9]-*.md")):
        current: Item | None = None
        for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            heading = HEADING.match(raw)
            if heading:
                current = Item(heading.group(1), heading.group(2), path.name, lineno)
                items.append(current)
                continue
            bullet = BULLET.match(raw)
            if bullet and current is not None:
                current.bullets[bullet.group(1)] = bullet.group(2).strip()
            elif raw.startswith("#"):
                current = None
    for item in items:
        _read_item(item, errors)
    return items, errors


def _read_item(item: Item, errors: list[str]) -> None:
    where = f"{item.id} ({item.file}:{item.line})"
    for name in BULLETS:
        if not item.bullets.get(name):
            errors.append(f"{where}: '{name}' satırı eksik veya boş")
    tag = SOURCE_TAG.match(item.bullets.get("Sorun", ""))
    if tag is None:
        errors.append(f"{where}: 'Sorun' satırı [DOĞRULANDI] veya [ÖNERİ] ile başlamalı")
    else:
        item.verified = tag.group(1).startswith("DOĞRULANDI")
        item.findings = tag.group(2).split("/") if tag.group(2) else []
    meta = META.match(item.bullets.get("Meta", ""))
    if meta is None:
        errors.append(f"{where}: 'Meta' biçimi 'P0 · M · Bağ: X, Y · Durum: açık' olmalı")
        return
    item.priority, item.effort, deps_text, item.status = meta.groups()
    item.deps = [] if deps_text.strip() == "-" else [d.strip() for d in deps_text.split(",")]
    if item.status != "açık":
        errors.append(f"{where}: plan dosyası durum bildiremez ('Durum: açık' olmalı), ilerleme PROGRESS.json'da")


def read_findings(readme: Path) -> set[str]:
    if not readme.is_file():
        return set()
    return {m.group(1) for line in readme.read_text(encoding="utf-8").splitlines() if (m := FINDING_ROW.match(line))}


def validate(items: list[Item], findings: set[str]) -> list[str]:
    errors: list[str] = []
    ids: dict[str, Item] = {}
    for item in items:
        if item.id in ids:
            errors.append(f"{item.id}: yinelenen kimlik ({ids[item.id].file}:{ids[item.id].line} ve {item.file}:{item.line})")
        ids[item.id] = item
    by_area: dict[str, list[int]] = {}
    for item in items:
        by_area.setdefault(item.area, []).append(int(item.id.split("-")[1]))
    for area, numbers in by_area.items():
        if sorted(numbers) != list(range(1, len(numbers) + 1)):
            errors.append(f"{area}: numaralar 01..{len(numbers):02d} aralığında ardışık ve tekil olmalı (bulunan: {sorted(numbers)})")
    for item in items:
        for dep in item.deps:
            if dep == item.id:
                errors.append(f"{item.id}: kendine bağımlı")
            elif dep not in ids:
                errors.append(f"{item.id}: bilinmeyen bağımlılık '{dep}'")
        for finding in item.findings:
            if findings and finding not in findings:
                errors.append(f"{item.id}: README denetim tablosunda olmayan bulgu '{finding}'")
    for group in cyclic_groups({i.id: [d for d in i.deps if d in ids] for i in items}):
        errors.append("bağımlılık döngüsü (karşılıklı bağımlı maddeler): " + ", ".join(sorted(group)))
    return errors


def validate_prose_references(plan_dir: Path, items: list[Item]) -> list[str]:
    """Item ids written anywhere in the plan text (not just in 'Bağ:') must exist."""
    known = {i.id for i in items}
    areas = sorted({i.area for i in items}, key=len, reverse=True)
    pattern = re.compile(r"\b(?:" + "|".join(areas) + r")-\d{2}\b")
    errors: list[str] = []
    for path in sorted(plan_dir.glob("*.md")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for token in pattern.findall(line):
                if token not in known:
                    errors.append(f"{path.name}:{lineno}: planda olmayan madde kimliği '{token}'")
    return errors


def cyclic_groups(graph: dict[str, list[str]]) -> list[list[str]]:
    """Tarjan: every strongly connected component with more than one node (all cycles at once)."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    groups: list[list[str]] = []

    def connect(node: str) -> None:
        index[node] = low[node] = len(index)
        stack.append(node)
        on_stack.add(node)
        for nxt in graph.get(node, []):
            if nxt not in index:
                connect(nxt)
                low[node] = min(low[node], low[nxt])
            elif nxt in on_stack:
                low[node] = min(low[node], index[nxt])
        if low[node] == index[node]:
            group = []
            while True:
                member = stack.pop()
                on_stack.discard(member)
                group.append(member)
                if member == node:
                    break
            if len(group) > 1:
                groups.append(group)

    for node in graph:
        if node not in index:
            connect(node)
    return groups


def find_cycle(graph: dict[str, list[str]]) -> list[str]:
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> list[str]:
        state[node] = 1
        stack.append(node)
        for nxt in graph.get(node, []):
            if state.get(nxt, 0) == 1:
                return [*stack[stack.index(nxt):], nxt]
            if state.get(nxt, 0) == 0 and (found := visit(nxt)):
                return found
        stack.pop()
        state[node] = 2
        return []

    for node in graph:
        if state.get(node, 0) == 0 and (found := visit(node)):
            return found
    return []


def longest_chain(items: list[Item]) -> int:
    """Length of the longest dependency chain; -1 when the graph has a cycle."""
    if has_cycle(items):
        return -1
    deps = {i.id: [d for d in i.deps if d in {x.id for x in items}] for i in items}
    memo: dict[str, int] = {}

    def depth(node: str) -> int:
        if node not in memo:
            memo[node] = 1 + max((depth(d) for d in deps[node]), default=0)
        return memo[node]

    return max((depth(i.id) for i in items), default=0)


def summarize(items: list[Item]) -> dict:
    count = lambda key: {k: sum(1 for i in items if key(i) == k) for k in sorted({key(i) for i in items})}  # noqa: E731
    return {
        "total": len(items),
        "by_area": count(lambda i: i.area),
        "by_priority": count(lambda i: i.priority),
        "by_effort": count(lambda i: i.effort),
        "verified_from_audit": sum(1 for i in items if i.verified),
        "proposals": sum(1 for i in items if not i.verified),
        "effort_person_days": round(sum(EFFORT_DAYS.get(i.effort, 0) for i in items), 1),
        "p0_person_days": round(sum(EFFORT_DAYS.get(i.effort, 0) for i in items if i.priority == "P0"), 1),
        "longest_dependency_chain": longest_chain(items),
    }


def load_phases(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["phases"] if path.is_file() else []


def validate_phases(items: list[Item], phases: list[dict]) -> list[str]:
    """Every item sits in exactly one phase and never before the phase of its prerequisites."""
    errors: list[str] = []
    phase_of: dict[str, int] = {}
    for phase in phases:
        for item_id in phase["items"]:
            if item_id in phase_of:
                errors.append(f"{item_id}: birden fazla fazda (faz {phase_of[item_id]} ve {phase['id']})")
            phase_of[item_id] = phase["id"]
    known = {i.id for i in items}
    for item_id in sorted(known - set(phase_of)):
        errors.append(f"{item_id}: hiçbir faza atanmamış")
    for item_id in sorted(set(phase_of) - known):
        errors.append(f"{item_id}: planda olmayan madde fazda yer alıyor")
    for item in items:
        for dep in item.deps:
            if dep in phase_of and item.id in phase_of and phase_of[dep] > phase_of[item.id]:
                errors.append(f"{item.id} (faz {phase_of[item.id]}) ön koşulu {dep} daha geç fazda (faz {phase_of[dep]})")
    return errors


def phase_table(items: list[Item], phases: list[dict]) -> list[dict]:
    by_id = {i.id: i for i in items}
    rows = []
    for phase in phases:
        members = [by_id[i] for i in phase["items"] if i in by_id]
        rows.append({
            "id": phase["id"],
            "name": phase["name"],
            "weeks": phase["weeks"],
            "items": len(members),
            "p0": sum(1 for m in members if m.priority == "P0"),
            "person_days": round(sum(EFFORT_DAYS.get(m.effort, 0) for m in members), 1),
        })
    return rows


def load_mvp(path: Path) -> list[str]:
    return json.loads(path.read_text(encoding="utf-8")).get("mvp", []) if path.is_file() else []


def has_cycle(items: list[Item]) -> bool:
    ids = {i.id for i in items}
    graph = {i.id: [d for d in i.deps if d in ids] for i in items}
    return any(i in graph[i] for i in graph) or bool(cyclic_groups(graph))


def critical_path(items: list[Item]) -> tuple[list[str], float]:
    """Longest prerequisite chain by effort; returned from the first prerequisite to the last item."""
    if not items or has_cycle(items):
        return [], 0.0
    by_id = {i.id: i for i in items}
    best: dict[str, tuple[float, str | None]] = {}

    def cost(node: str) -> float:
        if node not in best:
            prev = max(((cost(d), d) for d in by_id[node].deps if d in by_id), default=(0.0, None))
            best[node] = (prev[0] + EFFORT_DAYS.get(by_id[node].effort, 0), prev[1])
        return best[node][0]

    end = max(by_id, key=cost)
    chain: list[str] = []
    node: str | None = end
    while node:
        chain.append(node)
        node = best[node][1]
    return chain[::-1], best[end][0]


def longest_chain_ids(items: list[Item]) -> list[str]:
    """The prerequisite chain with the most items, first prerequisite first."""
    if not items or has_cycle(items):
        return []
    by_id = {i.id: i for i in items}
    best: dict[str, tuple[int, str | None]] = {}

    def depth(node: str) -> int:
        if node not in best:
            prev = max(((depth(d), d) for d in by_id[node].deps if d in by_id), default=(0, None))
            best[node] = (prev[0] + 1, prev[1])
        return best[node][0]

    end = max(by_id, key=depth)
    chain: list[str] = []
    node: str | None = end
    while node:
        chain.append(node)
        node = best[node][1]
    return chain[::-1]


def closure(items: list[Item], ids: list[str]) -> set[str]:
    by_id = {i.id: i for i in items}
    seen: set[str] = set()
    stack = [i for i in ids if i in by_id]
    while stack:
        node = stack.pop()
        if node not in seen:
            seen.add(node)
            stack.extend(d for d in by_id[node].deps if d in by_id)
    return seen


def _tr(number: float) -> str:
    text = f"{number:,.1f}"
    return text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def render_blocks(items: list[Item], phases: list[dict], mvp: list[str]) -> dict[str, str]:
    """Generated markdown for the <!-- name:begin --> ... <!-- name:end --> blocks in the plan text."""
    stats = summarize(items)
    p0_days = stats["p0_person_days"]
    blocks: dict[str, str] = {}
    blocks["summary"] = (
        f"**{stats['total']} madde** · P0 {stats['by_priority'].get('P0', 0)} · "
        f"denetim bulgusuna dayalı {stats['verified_from_audit']} · öneri {stats['proposals']} · "
        f"toplam {_tr(stats['effort_person_days'])} kişi-gün (P0: {_tr(p0_days)}) · "
        f"en uzun bağımlılık zinciri {stats['longest_dependency_chain']} madde"
    )
    files: dict[str, dict[str, int]] = {}
    for item in items:
        files.setdefault(item.file, {}).setdefault(item.area, 0)
        files[item.file][item.area] += 1
    rows = ["| Dosya | Alanlar (madde sayısı) | Toplam |", "|---|---|---|"]
    for name, areas in files.items():
        rows.append(f"| `{name}` | {', '.join(f'{a} ({n})' for a, n in areas.items())} | {sum(areas.values())} |")
    blocks["counts"] = "\n".join(rows)
    prow = ["| Faz | Ad | Hafta | Madde | P0 | Kişi-gün |", "|---|---|---|---|---|---|"]
    for row in phase_table(items, phases):
        weeks = str(row["weeks"]).replace("-", EN_DASH)
        prow.append(f"| {row['id']} | {row['name']} | {weeks} | {row['items']} | {row['p0']} | {_tr(row['person_days'])} |")
    prow.append(f"| | **Toplam** | | **{stats['total']}** | **{stats['by_priority'].get('P0', 0)}** | **{_tr(stats['effort_person_days'])}** |")
    blocks["phases"] = "\n".join(prow)
    by_id_all = {i.id: i for i in items}
    for phase in phases:
        p0 = [i for i in phase["items"] if i in by_id_all and by_id_all[i].priority == "P0"]
        blocks[f"p0_{phase['id']}"] = "**P0:** " + (", ".join(p0) if p0 else "yok")
    chain, days = critical_path(items)
    long_chain = longest_chain_ids(items)
    long_days = sum(EFFORT_DAYS.get(by_id_all[i].effort, 0) for i in long_chain)
    blocks["critical"] = (
        f"- **Efora göre kritik yol** ({len(chain)} madde, {_tr(days)} kişi-gün; sonsuz paralellikle bile yaklaşık "
        f"{days / 5:.0f} hafta alt sınır): `{'` → `'.join(chain)}`\n"
        f"- **Madde sayısına göre en uzun zincir** ({len(long_chain)} madde, {_tr(long_days)} kişi-gün): "
        f"`{'` → `'.join(long_chain)}`"
    )
    years = stats["effort_person_days"] / 220
    blocks["effort"] = (
        f"Toplam {_tr(stats['effort_person_days'])} kişi-gün, yoğun tek geliştirici için yaklaşık {_tr(years)} kişi-yıldır "
        f"(220 iş günü/yıl); P0 alt kümesi {_tr(p0_days)} kişi-gün. Tahminler ±%50 belirsizdir."
    )
    by_id = {i.id: i for i in items}
    needed = closure(items, mvp)
    mrows = ["| Madde | Başlık |", "|---|---|"]
    mrows += [f"| {i} | {by_id[i].title} |" for i in mvp if i in by_id]
    mdays = sum(EFFORT_DAYS.get(by_id[i].effort, 0) for i in needed)
    mrows.append("")
    mrows.append(
        f"MVP {len(mvp)} madde; ön koşullarıyla birlikte **{len(needed)} madde, {_tr(mdays)} kişi-gün** "
        f"(planın %{100 * len(needed) / max(1, len(items)):.0f}'i)."
    )
    blocks["mvp"] = "\n".join(mrows)
    return blocks


BLOCK = re.compile(r"(<!-- (\w+):begin -->\n)(.*?)(\n<!-- \2:end -->)", re.S)


def stale_blocks(text: str, blocks: dict[str, str]) -> list[str]:
    return [m.group(2) for m in BLOCK.finditer(text) if m.group(2) in blocks and m.group(3) != blocks[m.group(2)]]


def apply_blocks(text: str, blocks: dict[str, str]) -> str:
    return BLOCK.sub(lambda m: m.group(1) + blocks.get(m.group(2), m.group(3)) + m.group(4), text)


def verify_evidence(item_id: str, evidence: dict) -> list[str]:
    """A 'done' claim must point at test files that exist and a commit that exists in this repository."""
    root = Path(__file__).resolve().parents[1]
    problems = []
    for test in evidence.get("tests", []):
        if not (root / test.split("::")[0]).is_file():
            problems.append(f"{item_id}: kanıt test dosyası yok: {test}")
    commit = evidence.get("commit", "")
    if commit:
        found = subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=root, capture_output=True, check=False)
        if found.returncode != 0:
            problems.append(f"{item_id}: kanıt commit'i depoda yok: {commit}")
    return problems


def merge_progress(items: list[Item], existing: dict) -> tuple[dict, list[str]]:
    errors: list[str] = []
    known = existing.get("items", {})
    merged: dict[str, dict] = {}
    for item in items:
        entry = known.get(item.id, {"status": "open", "evidence": {"tests": [], "commit": "", "eval_report": ""}})
        evidence = entry.get("evidence", {})
        if entry.get("status") == "done" and not (evidence.get("tests") and evidence.get("commit")):
            errors.append(f"{item.id}: 'done' için evidence.tests ve evidence.commit zorunlu")
            entry["status"] = "claimed_without_evidence"
        if entry.get("status") == "done":
            errors += verify_evidence(item.id, evidence)
        merged[item.id] = entry
    result = {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "items": merged}
    return result, errors


# --- module wiring ---------------------------------------------------------------------------


def import_graph(master_dir: Path) -> dict[str, set[str]]:
    modules = {p.stem for p in master_dir.glob("*.py")}
    graph: dict[str, set[str]] = {m: set() for m in modules}
    for path in master_dir.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8", errors="replace"))):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module.split(".")[0]]
            graph[path.stem].update(n for n in names if n in modules and n != path.stem)
    return graph


def unreachable_modules(master_dir: Path, root: str = "app") -> list[str]:
    graph = import_graph(master_dir)
    seen: set[str] = set()
    stack = [root]
    while stack:
        node = stack.pop()
        if node not in seen:
            seen.add(node)
            stack.extend(graph.get(node, ()))
    return sorted(set(graph) - seen)


def facade_modules(master_dir: Path, max_lines: int = 20) -> list[str]:
    result = []
    for path in sorted(master_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        body = [n for n in tree.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
        only_reexports = all(
            isinstance(n, (ast.Import, ast.ImportFrom)) or (isinstance(n, ast.Assign) and _is_all(n)) for n in body
        )
        if body and only_reexports and len(path.read_text(encoding="utf-8").splitlines()) <= max_lines:
            result.append(path.stem)
    return result


def _is_all(node: ast.Assign) -> bool:
    return any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets)


# --- command line ----------------------------------------------------------------------------


def _out(text: str = "") -> None:
    sys.stdout.buffer.write((text + "\n").encode("utf-8"))


def cmd_check(args: argparse.Namespace) -> int:
    items, errors = parse_plan(args.plan_dir)
    errors += validate(items, read_findings(args.plan_dir / "README.md"))
    errors += validate_prose_references(args.plan_dir, items)
    phases = load_phases(args.plan_dir / "phases.json")
    mvp = load_mvp(args.plan_dir / "phases.json")
    if phases:
        errors += validate_phases(items, phases)
    errors += [f"mvp: planda olmayan madde '{i}'" for i in mvp if i not in {x.id for x in items}]
    blocks = render_blocks(items, phases, mvp)
    for path in sorted(args.plan_dir.glob("*.md")):
        for name in stale_blocks(path.read_text(encoding="utf-8"), blocks):
            errors.append(f"{path.name}: '{name}' bloğu güncel değil (python scripts/plan_tool.py render)")
    stats = summarize(items)
    _out(json.dumps(stats, ensure_ascii=False, indent=2))
    for row in phase_table(items, phases):
        _out(f"faz {row['id']}  {row['name']:<40} hafta {row['weeks']:<7} {row['items']:>3} madde  P0={row['p0']:>3}  {row['person_days']:>6} kişi-gün")
    for error in errors:
        _out(f"HATA: {error}")
    _out(f"\n{stats['total']} madde, {len(errors)} hata")
    return 1 if errors else 0


def cmd_render(args: argparse.Namespace) -> int:
    items, errors = parse_plan(args.plan_dir)
    if errors:
        for error in errors:
            _out(f"HATA: {error}")
        return 1
    blocks = render_blocks(items, load_phases(args.plan_dir / "phases.json"), load_mvp(args.plan_dir / "phases.json"))
    for path in sorted(args.plan_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        updated = apply_blocks(text, blocks)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            _out(f"güncellendi: {path.name}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    items, errors = parse_plan(args.plan_dir)
    progress_path = args.plan_dir / "PROGRESS.json"
    existing = json.loads(progress_path.read_text(encoding="utf-8")) if progress_path.is_file() else {}
    merged, evidence_errors = merge_progress(items, existing)
    progress_path.write_text(json.dumps(merged, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    counts: dict[str, int] = {}
    for entry in merged["items"].values():
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    _out(json.dumps(counts, ensure_ascii=False))
    for error in [*errors, *evidence_errors]:
        _out(f"HATA: {error}")
    return 1 if errors or evidence_errors else 0


def cmd_wiring(args: argparse.Namespace) -> int:
    dead = unreachable_modules(args.master_dir)
    allow_path = args.plan_dir / "wiring_allowlist.txt"
    if args.write_allowlist:
        allow_path.write_text("\n".join(dead) + "\n", encoding="utf-8")
        _out(f"{len(dead)} modül izin listesine yazıldı: {allow_path}")
        return 0
    _out(f"app.py'den erişilemeyen modül: {len(dead)}")
    for name in dead:
        _out(f"  {name}")
    code = 0
    if args.facades:
        facades = facade_modules(args.master_dir)
        _out(f"\nyalnızca yeniden yönlendiren ince modül: {len(facades)}")
        for name in facades:
            _out(f"  {name}")
        code = 1 if facades and args.fail_on_new else code
    if args.fail_on_new:
        allowed = set(allow_path.read_text(encoding="utf-8").split()) if allow_path.is_file() else set()
        new = sorted(set(dead) - allowed)
        for name in new:
            _out(f"HATA: yeni bağlanmamış modül: {name}")
        code = 1 if new else code
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--plan-dir", type=Path, default=PLAN_DIR)
    parser.add_argument("--master-dir", type=Path, default=MASTER_DIR)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check").set_defaults(func=cmd_check)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("render").set_defaults(func=cmd_render)
    wiring = sub.add_parser("wiring")
    wiring.add_argument("--write-allowlist", action="store_true")
    wiring.add_argument("--fail-on-new", action="store_true")
    wiring.add_argument("--facades", action="store_true")
    wiring.set_defaults(func=cmd_wiring)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
