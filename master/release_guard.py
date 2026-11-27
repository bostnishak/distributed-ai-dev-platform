"""Keep the last good prompt set and put it back when a benchmark run gets worse.

A run that loses no scenario becomes the new champion (its prompts are copied aside). A run that fails something the
champion passed is a regression: the changed prompt files can be restored, the replaced ones are kept for inspection.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import config
import eval_stats
import release_history

PROMPTS = Path(__file__).resolve().parent / "prompts"


def _store() -> Path:
    return config.data_dir() / "champion"


def champion() -> dict:
    try:
        return json.loads((_store() / "results.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def compare(results: dict[str, bool]) -> tuple[str, list[str], str]:
    """("promote" | "keep" | "regressed", lost scenario names, statistics line)."""
    best = champion().get("results", {})
    shared = [name for name in results if name in best]
    lost = sorted(name for name in shared if best[name] and not results[name])
    if not best:
        return "promote", [], "ilk ölçüm"
    detail = ""
    if shared:
        old, new = [best[n] for n in shared], [results[n] for n in shared]
        detail = f"{sum(old)} -> {sum(new)} / {len(shared)}, p={eval_stats.mcnemar_exact(old, new):.3f}"
    if lost:
        return "regressed", lost, detail
    return ("promote" if set(results) >= set(best) else "keep"), [], detail


def promote(results: dict[str, bool]) -> None:
    store = _store()
    target = store / "prompts"
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(PROMPTS, target)
    (store / "results.json").write_text(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")


def changed_prompts() -> list[str]:
    kept = _store() / "prompts"
    if not kept.is_dir():
        return []
    return sorted(p.name for p in kept.iterdir() if p.is_file() and (not (PROMPTS / p.name).is_file() or (PROMPTS / p.name).read_bytes() != p.read_bytes()))


def rollback() -> list[str]:
    """Restore the champion's version of every changed prompt; the replaced files are saved first."""
    names = changed_prompts()
    rejected = _store() / "rejected" / time.strftime("%Y%m%d-%H%M%S")
    for name in names:
        if (PROMPTS / name).is_file():
            rejected.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PROMPTS / name, rejected / name)
        shutil.copy2(_store() / "prompts" / name, PROMPTS / name)
    return names


def status() -> str:
    """Chat answer to "how good is the system right now"."""
    best = champion()
    if not best:
        return "Henüz ölçüm yok. Ölçmek için: `python scripts/golden.py`"
    results = best["results"]
    failed = sorted(n for n, ok in results.items() if not ok)
    changed = changed_prompts()
    lines = [f"Son iyi ölçüm ({best['at']}): **{sum(results.values())}/{len(results)}** senaryo geçti.",
             f"Ardışık oran testi (SPRT): {eval_stats.sprt(list(results.values()))}"]
    if failed:
        lines.append("Kalan senaryolar: " + ", ".join(failed))
    if changed:
        lines.append("Bu ölçümden sonra değişen istemler (yeniden ölçülmeli): " + ", ".join(changed[:6]))
    if release_history.points():
        lines += ["", release_history.describe()]
    return "\n".join(lines)
