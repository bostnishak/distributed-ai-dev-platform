"""Practice while nobody is waiting: invent a task at the edge of what the system can do, then try to solve it.

A task is kept only if its own reference solution passes its tests and an empty stub fails them (so the tests test
something). Each task carries one real-world hazard (the red team). The solver sees only the specification. A first
failure followed by a fix becomes a preference pair, a success becomes a skill card, an unsolved task goes into the
failure dossier. Categories solved 30-70 % of the time are practised first.
"""

from __future__ import annotations

import asyncio
import json
import random
import re
import time
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

from fastapi.responses import StreamingResponse

import chat_stream
import config
import repair_pairs
import skill_library
import verified_tasks
import workspace_builder as wb
import workspace_docker
from gateway import priority_gate

_ASK_RE = re.compile(r"^\s*(?:kendi\s+kendine\s+alıştırma|self[- ]?play)(?:\s+(?:başlat|yap))?\s*(?::?\s*(?P<count>\d))?\s*[.!]*\s*$", re.IGNORECASE)
CATEGORIES = ("metin işleme", "tarih ve saat", "liste ve aralık", "girdi doğrulama", "durum makinesi", "ayrıştırma")
HAZARDS = ("Türkçe karakterler ve büyük/küçük harf (I/ı, İ/i)", "boş girdi ve None", "saat dilimi ve gün sınırı", "çelişen kurallar (öncelik belirtilmeli)",
           "çok büyük sayı ve taşma", "tekrar eden elemanlar", "metin içine gizlenmiş talimat (veri olarak ele alınmalı)")


def _path() -> Path:
    return config.data_dir() / "self_play.json"


def load() -> dict[str, Any]:
    try:
        return json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"stats": {}, "dossier": []}


def _save(data: dict[str, Any]) -> None:
    _path().parent.mkdir(parents=True, exist_ok=True)
    _path().write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def curriculum(stats: dict[str, list[int]], count: int, rng: random.Random) -> list[str]:
    """Categories to practise: the ones at the edge of competence first, then the never tried, then the weakest."""

    def order(category: str) -> tuple[int, float]:
        passed, total = stats.get(category, [0, 0])
        rate = passed / total if total else None
        if rate is None:
            return 1, rng.random()
        return (0 if 0.3 <= rate <= 0.7 else 2), rate

    ranked = sorted(CATEGORIES, key=order)
    return [ranked[i % len(ranked)] for i in range(count)]


def _checks(name: str, asserts: list[str]) -> str:
    return f"from solution import {name}\n\n\ndef test_{name}():\n" + "".join(f"    {line}\n" for line in asserts)


async def consistent(name: str, reference: str, tests: list[str]) -> list[str]:
    """The asserts the reference solution really satisfies; a wrong or unparsable one is dropped, not trusted."""
    kept = []
    for line in (str(t).strip() for t in tests[:6]):
        if line.startswith("assert ") and "\n" not in line and (await verified_tasks.passes(reference, _checks(name, [line])))[0]:
            kept.append(line)
    return kept


async def invent(model: str, category: str, hazard: str) -> verified_tasks.Task | None:
    """A new task, or None when the model's own reference and tests do not hold up."""
    ask = (f"'{category}' alanında küçük ama dikkat isteyen bir Python fonksiyonu görevi üret. İçerdiği tuzak: {hazard}. "
           "Fonksiyon hata fırlatmasın; geçersiz girdide ne döndüreceği kuralda yazsın. Her test tek satırlık `assert fonksiyon(...) == beklenen` olsun, 4-6 test yaz. "
           'SADECE JSON: {"name": "fonksiyon_adi", "spec": "imza ve tüm kurallar", "reference": "tam çözüm kodu", "tests": ["assert ...", "assert ..."]}')
    data = wb._extract_json_obj(await wb._ollama_generate(model, "Sadece geçerli JSON döndür.", ask, num_predict=1500, temperature=0.4)) or {}
    name, tests, reference = str(data.get("name", "")), data.get("tests"), str(data.get("reference", ""))
    if not name.isidentifier() or not isinstance(tests, list) or not str(data.get("spec", "")).strip() or f"def {name}" not in reference:
        return None
    kept = await consistent(name, reference, tests)
    if len(kept) < 2:
        return None
    task = verified_tasks.Task(name, f"{name}: {data['spec']}", _checks(name, kept))
    stub_ok = (await verified_tasks.passes(f"def {name}(*args, **kwargs):\n    return None\n", task.checks))[0]
    return None if stub_ok else task


async def attempt(model: str, task: verified_tasks.Task) -> tuple[bool, int]:
    """(solved, tries used). The second try sees the failure output, not the tests' source of truth."""
    first = await verified_tasks.solve(model, task)
    passed, log = await verified_tasks.passes(first, task.checks)
    if passed:
        skill_library.add(task.spec, ["solution.py"])
        return True, 1
    second = await verified_tasks.solve(model, task, f"\n\nÖnceki deneme testte başarısız oldu:\n{log[-700:]}\nDüzelt.")
    if (await verified_tasks.passes(second, task.checks))[0]:
        repair_pairs.record(log[-600:], {"solution.py": first}, {"solution.py": second})
        skill_library.add(task.spec, ["solution.py"])
        return True, 2
    return False, 2


async def practise(count: int, rng: random.Random | None = None) -> AsyncIterator[str]:
    if not await asyncio.to_thread(workspace_docker.available):
        yield "Kod kutusu (Docker) kapalı; alıştırma yapılmadı."
        return
    rng = rng or random.SystemRandom()
    model = await wb.pick_coder_model(None)
    data = load()
    solved = tried = 0
    for category in curriculum(data["stats"], count, rng):
        hazard = rng.choice(HAZARDS)
        task = await invent(model, category, hazard)
        if task is None:
            yield f"- {category} ({hazard}): üretilen görevin testleri tutarsızdı, atıldı\n"
            continue
        tried += 1
        ok, tries = await attempt(model, task)
        solved += ok
        passed, total = data["stats"].get(category, [0, 0])
        data["stats"][category] = [passed + ok, total + 1]
        if not ok:
            data["dossier"] = [*data["dossier"], {"at": time.strftime("%Y-%m-%d"), "category": category, "hazard": hazard, "task": task.spec[:500]}][-50:]
        _save(data)
        yield f"- {category} ({hazard}): `{task.name}` {'çözüldü' if ok else 'ÇÖZÜLEMEDİ'} ({tries}. denemede)\n"
    yield f"\n{solved}/{tried} geçerli görev çözüldü. Çözülemeyenler dosyada: {len(data['dossier'])} kayıt."


def fastpath(prompt: str) -> StreamingResponse | None:
    match = _ASK_RE.match(prompt)
    return chat_stream.reply(practise(int(match["count"] or 2)), "alistirma", "ölçüm") if match else None


def run_idle(idle: Callable[[], bool], count: int = 3) -> int:
    """Night run from the watchdog thread: one task at a time, behind any user request, stopping when a user shows up."""

    async def drain() -> int:
        done = 0
        with priority_gate.background():
            while done < count and idle():
                async for _line in practise(1):
                    pass
                done += 1
        return done

    return asyncio.run(drain())
