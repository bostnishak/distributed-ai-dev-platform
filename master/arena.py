"""Models and designs side by side on the same request.

"model kapısı: aday, taban" scores two models on tasks decided by running them; the candidate may only replace the
baseline when it passes at least as many (this is the gate an imported GGUF model must clear).
"turnuva: <web isteği>" (or "turnuva (model1, model2): ...") builds the same page with two or three models, one after
another on the single card, and lays out time, check results and requested colours next to each preview.
"kazanan: <model>" records the user's choice as a lasting preference.
"""

from __future__ import annotations

import re
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx
from fastapi.responses import StreamingResponse

import chat_stream
import config
import eval_stats
import preferences
import project_flow
import verified_tasks
import workspace_builder as wb
import workspace_docker

_GATE_RE = re.compile(r"^\s*model\s+kapısı\s*:\s*(?P<candidate>[\w.:/-]+)\s*,\s*(?P<baseline>[\w.:/-]+)\s*$", re.IGNORECASE)
_ARENA_RE = re.compile(r"^\s*turnuva(?:\s*\((?P<models>[^)]+)\))?\s*:\s*(?P<request>.{8,})$", re.IGNORECASE | re.DOTALL)
_WINNER_RE = re.compile(r"^\s*(?:turnuva\s+)?kazanan\s*:\s*(?P<model>[\w.:/-]+)\s*$", re.IGNORECASE)
_HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b")
DEFAULT_MODELS = ("qwen2.5-coder:7b", "qwen3.5:9b")


async def installed() -> set[str]:
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{config.OLLAMA_URL}/v1/models")
        resp.raise_for_status()
        return {m["id"] for m in resp.json().get("data", [])}


def verdict(candidate: dict[str, bool], baseline: dict[str, bool]) -> tuple[bool, str]:
    names = list(baseline)
    new, old = [candidate[n] for n in names], [baseline[n] for n in names]
    p = eval_stats.mcnemar_exact(old, new)
    promote = sum(new) >= sum(old) and sum(new) > 0
    return promote, f"aday {sum(new)}/{len(names)}, taban {sum(old)}/{len(names)} (McNemar p={p:.3f})"


async def _gate(candidate: str, baseline: str) -> AsyncIterator[str]:
    known = await installed()
    if missing := [m for m in (candidate, baseline) if m not in known]:
        yield f"Kurulu olmayan model: {', '.join(missing)}"
        return
    if not workspace_docker.available():
        yield "Kod kutusu (Docker) kapalı olduğu için ölçemiyorum; kapı kapalı kalır."
        return
    results = {}
    for model in (baseline, candidate):
        yield f"`{model}` {len(verified_tasks.TASKS)} görevde çalıştırılarak ölçülüyor...\n"
        results[model] = await verified_tasks.score(model)
    promote, line = verdict(results[candidate], results[baseline])
    rows = "\n".join(f"| {n} | {'geçti' if results[baseline][n] else 'kaldı'} | {'geçti' if results[candidate][n] else 'kaldı'} |" for n in results[baseline])
    yield f"\n| görev | taban | aday |\n|---|---|---|\n{rows}\n\n**{'KAPI AÇIK: aday tabanın yerini alabilir' if promote else 'KAPI KAPALI: aday tabandan kötü'}** — {line}"


async def _build(model: str, request: str) -> dict[str, Any]:
    started = time.perf_counter()
    async for evt in project_flow.stream_generate(request, project_type="web", model_override=model):
        if evt["type"] == "done":
            ws_dir = wb.safe_workspace_dir(evt["workspace"]["id"])
            text = " ".join((ws_dir / f).read_text(encoding="utf-8", errors="replace") for f in wb.list_relative_files(ws_dir) if f.endswith((".html", ".css", ".js"))).lower()
            wanted = [c.lower() for c in _HEX_RE.findall(request)]
            return {"evt": evt, "seconds": round(time.perf_counter() - started), "warnings": [str(w) for w in evt.get("warnings") or []],
                    "colours": f"{sum(c in text for c in wanted)}/{len(wanted)}" if wanted else "-", "files": len(wb.list_relative_files(ws_dir))}
    raise RuntimeError(f"{model} projeyi bitiremedi")


async def _tournament(models: list[str], request: str) -> AsyncIterator[Any]:
    import assistant_stream_fastpaths as fp

    rows = []
    for label, model in zip("ABC", models, strict=False):
        yield f"\n### {label}: `{model}` aynı istekle üretiyor...\n"
        try:
            result = await _build(model, request)
        except chat_stream.FAILURES as exc:
            rows.append(f"| {label} | {model} | - | üretemedi: {exc} | - | - |")
            continue
        checks = "temiz" if not result["warnings"] else f"{len(result['warnings'])} uyarı: {result['warnings'][0][:70]}"
        rows.append(f"| {label} | {model} | {result['seconds']} sn | {checks} | {result['colours']} | {result['files']} |")
        yield fp._attach_workspace_flags(wb, result["evt"]["workspace"], result["evt"]["tree"])
    yield "\n| | model | süre | denetimler | istenen renkler | dosya |\n|---|---|---|---|---|---|\n" + "\n".join(rows)
    yield "\n\nÖnizlemeleri karşılaştır; seçimini kaydetmek için `kazanan: model-adı` yaz."


async def _unknown(missing: list[str]) -> AsyncIterator[str]:
    yield f"Kurulu olmayan model: {', '.join(missing)}"


async def _contest(wanted: list[str], request: str) -> AsyncIterator[Any]:
    known = await installed()
    models = [m for m in (wanted or list(DEFAULT_MODELS)) if m in known][:3]
    if len(models) < 2:
        async for piece in _unknown([m for m in wanted if m not in known] or ["en az iki kurulu model gerekli"]):
            yield piece
        return
    async for piece in _tournament(models, request):
        yield piece


async def _record(model: str) -> AsyncIterator[str]:
    preferences.remember(f"Bundan sonra web sayfası üretirken her zaman {model} modelini tercih et.")
    yield f"Kaydedildi: turnuva kazananı `{model}`. ('tercihlerimi sil' ile kaldırabilirsin.)"


def fastpath(prompt: str) -> StreamingResponse | None:
    if match := _GATE_RE.match(prompt):
        return chat_stream.reply(_gate(match["candidate"], match["baseline"]), "model-kapisi", "ölçüm")
    if match := _ARENA_RE.match(prompt):
        wanted = [m.strip() for m in (match["models"] or "").split(",") if m.strip()]
        return chat_stream.reply(_contest(wanted, match["request"].strip()), "turnuva", "proje")
    if match := _WINNER_RE.match(prompt):
        return chat_stream.reply(_record(match["model"]), "turnuva", "tercih")
    return None
