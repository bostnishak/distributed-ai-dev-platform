"""A many-constraint page is built in three slices, each checked against the requirement ledger before the next.

Slice 1 writes the typed skeleton (so a long file is never produced in one unchecked shot), slices 2 and 3 are patches
anchored into it. After every slice only the unmet REQ ids go back to the model: twice as a surgical patch, then once
from a clean context. A candidate that meets fewer requirements than the current page is thrown away.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import clean_slate
import patch_edit
import req_checks
import req_ledger
from prompt_loader import load_prompt

MIN_REQUIREMENTS = 8
REPORT = ".ai-os/requirements.json"
_FIX_ROUNDS = clean_slate.AFTER_FAILURES + 1
_BLOCK_RE = re.compile(r"```[a-zA-Z0-9_+-]*\s*\n([\s\S]*?)\n```")

Generate = Callable[[str, str], Awaitable[str]]


@dataclass
class _Page:
    ws_dir: Path
    request: str
    generate: Generate
    patcher: Generate
    ledger: tuple[req_ledger.Req, ...]
    system: str
    code: str = ""
    verdicts: dict[str, req_checks.Verdict] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)


def applies(path: str, ledger: tuple[req_ledger.Req, ...]) -> bool:
    return path == "index.html" and len(ledger) >= MIN_REQUIREMENTS


def _whole_page(answer: str) -> str:
    blocks = _BLOCK_RE.findall(answer)
    body = max(blocks, key=len) if blocks else answer.strip()
    return body if "</html>" in body.lower() else ""


async def _checked(page: _Page, code: str, wanted: tuple[req_ledger.Req, ...]) -> dict[str, req_checks.Verdict]:
    (page.ws_dir / "index.html").write_text(code, encoding="utf-8")
    return await asyncio.to_thread(req_checks.evaluate, page.ws_dir, wanted)


def _met(verdicts: dict[str, req_checks.Verdict]) -> int:
    return req_checks.score(verdicts)[0]


async def _keep_if_better(page: _Page, candidate: str, wanted: tuple[req_ledger.Req, ...]) -> bool:
    """Takes the candidate unless it meets fewer requirements than the page in hand; returns True when it meets more."""
    before = await _checked(page, page.code, wanted)
    after = await _checked(page, candidate, wanted) if candidate else {}
    if candidate and _met(after) >= _met(before):
        page.code, page.verdicts = candidate, after
        return _met(after) > _met(before)
    (page.ws_dir / "index.html").write_text(page.code, encoding="utf-8")
    page.verdicts = before
    return False


async def _change(page: _Page, ask: str) -> str:
    """A surgical patch; a file too small to patch, or blocks that do not match, is rewritten whole."""
    full = f"{ask}\n\nKULLANICI İSTEĞİ:\n{page.request}\n\nMEVCUT index.html:\n{page.code}"
    patched = await patch_edit.try_patch(page.patcher, full, page.code)
    return patched if patched is not None else _whole_page(await page.generate(page.system, f"{full}\n\nBu dosyanın güncel ve EKSİKSİZ tüm içeriğini yaz."))


async def _repair(page: _Page, wanted: tuple[req_ledger.Req, ...]) -> None:
    banned: list[str] = []
    for attempt in range(_FIX_ROUNDS):
        missing = req_checks.unmet(wanted, page.verdicts)
        if not missing:
            return
        listed = "\n".join(missing)
        if attempt < clean_slate.AFTER_FAILURES:
            candidate = await _change(page, load_prompt("slice_fix.txt") + listed + clean_slate.ban_list(banned))
        else:
            candidate = _whole_page(await page.generate(page.system, clean_slate.prompt(req_ledger.listing(wanted), "index.html", page.code, listed, banned)))
        before = page.code
        better = await _keep_if_better(page, candidate, wanted)
        page.history.append({"attempt": attempt + 1, "mode": "temiz bağlam" if attempt >= clean_slate.AFTER_FAILURES else "yama", "improved": better, "missing": len(missing)})
        if not better:
            banned.append(clean_slate.failed_approach(before, candidate, listed))


async def _first_slice(page: _Page) -> None:
    ask = f"{page.request}\n\n{load_prompt('slice_first.txt')}{req_ledger.listing(req_ledger.upto(page.ledger, req_ledger.LAYOUT))}"
    page.code = _whole_page(await page.generate(page.system, ask)) or _whole_page(await page.generate(page.system, ask))
    if not page.code:
        raise ValueError("model iskelet sayfayı tamamlayamadı")


def _history(ws_dir: Path) -> list[dict[str, Any]]:
    try:
        return json.loads((ws_dir / REPORT).read_text(encoding="utf-8"))["history"]
    except (OSError, ValueError, KeyError):
        return []


def _report(ws_dir: Path, ledger: tuple[req_ledger.Req, ...], verdicts: dict[str, req_checks.Verdict], history: list[dict[str, Any]]) -> None:
    met, decidable = req_checks.score(verdicts)
    rows = [{**row, "met": verdicts.get(row["id"], (None, ""))[0], "detail": verdicts.get(row["id"], (None, ""))[1]} for row in req_ledger.as_dicts(ledger)]
    target = ws_dir / REPORT
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"met": met, "decidable": decidable, "requirements": rows, "history": history}, ensure_ascii=False, indent=2), encoding="utf-8")


def final(ws_dir: Path, ledger: tuple[req_ledger.Req, ...]) -> tuple[str, list[str]]:
    """The delivered files judged once more (later repairs may have changed them): (one line, unmet requirements)."""
    if not ledger or not (ws_dir / "index.html").is_file():
        return "", []
    _report(ws_dir, ledger, req_checks.evaluate(ws_dir, ledger), _history(ws_dir))
    return summary(ws_dir)


async def build(page_args: tuple[Path, str, str], ledger: tuple[req_ledger.Req, ...], generate: Generate, patcher: Generate) -> str:
    """`page_args` is (workspace, request, system prompt); returns the finished index.html."""
    ws_dir, request, system = page_args
    ws_dir.mkdir(parents=True, exist_ok=True)
    page = _Page(ws_dir, request, generate, patcher, ledger, system)
    await _first_slice(page)
    for stage in req_ledger.SLICES:
        wanted = req_ledger.upto(ledger, stage)
        new = tuple(r for r in ledger if r.slice == stage)
        if stage != req_ledger.LAYOUT and new:
            await _keep_if_better(page, await _change(page, load_prompt("slice_next.txt") + req_ledger.listing(new)), wanted)
        else:
            page.verdicts = await _checked(page, page.code, wanted)
        await _repair(page, wanted)
        met, decidable = req_checks.score(page.verdicts)
        page.history.append({"slice": stage, "met": met, "decidable": decidable})
    _report(ws_dir, ledger, page.verdicts, page.history)
    return page.code


def summary(ws_dir: Path) -> tuple[str, list[str]]:
    """(one line for the user, unmet requirements) of the last ledger report; ("", []) when there is none."""
    try:
        report = json.loads((ws_dir / REPORT).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "", []
    rows = report["requirements"]
    unmet = [f"Koşul karşılanmadı: {r['id']} {r['text']} ({r['detail']})" for r in rows if r["met"] is False]
    by_hand = sum(r["met"] is None for r in rows)
    note = f", {by_hand} koşul elle bakılmalı" if by_hand else ""
    return f"Koşul defteri: {report['met']}/{report['decidable']} makine denetimi geçti{note}.", unmet
