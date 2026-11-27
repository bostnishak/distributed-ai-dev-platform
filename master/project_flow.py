"""Projects are researched before they are written and checked for missing features afterwards.

1. Research: what is this product in the real world? Wikipedia gives the grounding text, the model turns it into a complete
   feature / UI / edge-case list (a calculator needs % and sqrt and memory keys, not just + - * /).
2. The list is added to the request that the architect and every file writer see.
3. Coverage: after generation and smoke test the code is audited against the list; missing items are written in a repair pass.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import agent_contracts
import complexity_governor
import design_system
import docs_vault
import json_repair
import ledger
import post_checks
import preferences
import skill_library
import spec_contract
import wiki_ground
from prompt_loader import load_prompt
from workspace_batches import wants_single_html
from workspace_checks import extract_file

_CODE_EXTS = (".js", ".html", ".py", ".css")
_MAX_CODE_CHARS = 16000
_EMPTY: dict[str, Any] = {"topic": "", "purpose": "", "features": [], "ui": [], "edge_cases": [], "source": ""}


def _json(raw: str) -> dict[str, Any]:
    return json_repair.loads_top(raw) or {}


def _items(data: dict[str, Any], key: str, limit: int) -> list[str]:
    value = data.get(key)
    return [str(x).strip() for x in value if str(x).strip()][:limit] if isinstance(value, list) else []


async def research(prompt: str, generate: Any) -> dict[str, Any]:
    """{"topic","purpose","features","ui","edge_cases","source"}; empty lists when the model returned nothing usable."""
    guess_raw = await generate('JSON döndür: {"topic": "yapılacak ürünün 2-4 kelimelik genel adı, ör. hesap makinesi"}', prompt, 60, 0.0)
    topic_guess = str(_json(guess_raw).get("topic") or "").strip()
    sources, note = await asyncio.to_thread(wiki_ground.lookup, topic_guess or prompt, force=True)
    ask = f"Kullanıcının isteği:\n{prompt}\n\n" + (f"ARAŞTIRMA KAYNAĞI:\n{note}\n" if note else "ARAŞTIRMA KAYNAĞI: bulunamadı, kendi bilginle yaz.\n")
    data = _json(await generate(load_prompt("b4_project_research.txt"), ask, 2200, 0.2))
    return {
        "topic": str(data.get("topic") or topic_guess), "purpose": str(data.get("purpose") or ""), "features": _items(data, "features", 12),
        "ui": _items(data, "ui", 14), "edge_cases": _items(data, "edge_cases", 6), "source": sources[0]["title"] if sources else "",
    }


def brief_text(info: dict[str, Any]) -> str:
    """The block appended to the user's request for the architect and the file writers."""
    if not info["features"]:
        return ""
    lines = [f"\n\n--- ARAŞTIRILMIŞ ÜRÜN TANIMI ({info['topic']}) ---", info["purpose"], "ZORUNLU ÖZELLİKLER (hepsi çalışır halde uygulanmalı):"]
    lines += [f"- {f}" for f in info["features"]]
    if info["ui"]:
        lines += ["ZORUNLU ARAYÜZ ÖĞELERİ (hepsi ekranda olmalı ve işlevine bağlanmalı):", *[f"- {u}" for u in info["ui"]]]
    if info["edge_cases"]:
        lines += ["ELE ALINMASI GEREKEN UÇ DURUMLAR:", *[f"- {e}" for e in info["edge_cases"]]]
    return "\n".join(lines)


def _code_files(ws_dir: Path) -> list[Path]:
    skip = {".history", "node_modules", "static"}
    return [p for p in sorted(ws_dir.rglob("*")) if p.is_file() and p.suffix in _CODE_EXTS and not skip & set(p.relative_to(ws_dir).parts)]


def _code_bundle(ws_dir: Path) -> str:
    text = "\n\n".join(f"=== {p.relative_to(ws_dir).as_posix()} ===\n{p.read_text(encoding='utf-8', errors='replace')}" for p in _code_files(ws_dir))
    return text[:_MAX_CODE_CHARS]


async def missing_features(ws_dir: Path, info: dict[str, Any], generate: Any) -> list[str]:
    code, wanted = _code_bundle(ws_dir), info["features"] + info["ui"]
    if not code or not wanted:
        return []
    ask = "ZORUNLU ÖZELLİKLER:\n" + "\n".join(f"- {w}" for w in wanted) + f"\n\nKAYNAK KOD:\n{code}"
    return _items(_json(await generate(load_prompt("b4_project_coverage.txt"), ask, 1200, 0.0)), "missing", 12)


async def complete_missing(ws_dir: Path, missing: list[str], generate: Any, write_file: Any) -> list[str]:
    """Rewrite the logic file (and the page, when UI items are missing) so the missing items exist; returns the files changed.

    A rewrite that breaks the static checks (syntax, DOM ids, eval) is rolled back, so the second pass can only improve a project.
    """
    from workspace_checks import static_problem

    files = _code_files(ws_dir)
    logic = [p for p in files if p.suffix in (".js", ".py") and p.stat().st_size > 200 and p.stem in ("calc", "calculator", "app", "main", "logic", "script")][:1]
    logic = logic or [p for p in files if p.suffix in (".js", ".py") and p.stat().st_size > 200][:1]
    page = [p for p in files if p.suffix == ".html" and "templates" not in p.parts][:1]
    changed: list[str] = []
    for p in logic + page:
        rel, before = p.relative_to(ws_dir).as_posix(), p.read_text(encoding="utf-8", errors="replace")
        ask = (
            f"`{rel}` dosyası şu ZORUNLU özellikleri/öğeleri eksik bırakıyor:\n" + "\n".join(f"- {m}" for m in missing)
            + f"\n\nMevcut içerik:\n{before[:12000]}\n\n"
            f"SADECE `{rel}` dosyasının eksiksiz, çalışan güncel içeriğini tek bir kod bloğunda yaz (başka dosya yazma). Eksiklerin HEPSİNİ ekle; çalışan kısımları bozma, id/sınıf adlarını koru."
        )
        body = extract_file(await generate(None, ask, 4096, 0.15), p.suffix)
        if not body:
            continue
        write_file(ws_dir, rel, body)
        problem = static_problem(ws_dir)
        if problem is not None:
            write_file(ws_dir, rel, before)  # roll back a rewrite that broke the project
            continue
        changed.append(rel)
    return changed


REASONING_MODEL = "qwen3.5:9b"  # research and coverage audits need reading comprehension; the 7B coder only writes files


async def _coverage_pass(ws_dir: Path, info: dict[str, Any], gens: tuple[Any, Any], request: str = "") -> AsyncIterator[dict[str, Any]]:
    """Audit the finished project against the researched feature list; complete what is missing, then re-run the browser/smoke checks.

    Yields status events and finally {"type": "coverage", "missing": int, "warning": str}.
    """
    import workspace_builder as wb
    from workspace_requirements import repair_project
    from workspace_smoke import smoke_and_repair

    think, write = gens
    yield {"type": "status", "message": "Eksik özellik denetimi yapılıyor..."}
    missing = await missing_features(ws_dir, info, think) if info.get("features") else []
    changed: list[str] = []
    if missing:
        yield {"type": "status", "message": f"{len(missing)} eksik özellik bulundu, tamamlanıyor..."}
        changed = await complete_missing(ws_dir, missing, write, wb._write_workspace_file)
        repair_project(ws_dir)
    from workspace_kit import ensure_theme_toggle

    ensure_theme_toggle(ws_dir, request)
    smoke_warning = ""  # the single browser/smoke run of the whole generation happens here, after the last file change
    fixer = think if wants_single_html(request) else write  # a whole page needs the stronger model and room for all of it
    attempts: list[str] = []

    def repair_with_escalation(rel: str, ask: str):
        attempts.append(rel)  # the first repair uses the usual model; a second one is handed to the other model
        model = fixer if len(attempts) == 1 else (think if fixer is write else write)
        return model(None, ask, min(14000, max(4096, len(ask) // 2)), 0.1)

    async for evt in smoke_and_repair(ws_dir, repair_with_escalation, request=request):
        if evt["type"] == "status":
            yield evt
        else:
            smoke_warning = evt.get("warning", "")
    added = f"Eksik bulunan {len(missing)} özellik ikinci geçişte eklendi ({', '.join(changed) or 'dosya değişmedi'})." if missing else ""
    yield {"type": "coverage", "missing": len(missing), "warning": " ".join(w for w in (added, smoke_warning) if w)}


async def _contract_events(prompt: str) -> AsyncIterator[dict[str, Any]]:
    """Intake and Architect agents for detailed requests: status lines, then {"type": "contract"}."""
    contract = await agent_contracts.intake(prompt)
    yield {"type": "status", "message": f"Intake ajanı: {len(contract.colors)} renk, {len(contract.sizes)} ölçü, {len(contract.buttons)} buton davranışı çıkarıldı."}
    audit = await agent_contracts.review(prompt)
    for item in audit.warnings:
        yield {"type": "status", "message": f"Mimar uyarısı: {item.issue} Öneri: {item.alternative}"}
    for item in audit.assumptions:
        yield {"type": "status", "message": f"Varsayım (doğrulanmadı): {item}"}
    yield {"type": "contract", "contract": contract}


async def _no_events() -> AsyncIterator[dict[str, Any]]:
    return
    yield {}


async def _preparation_events(prompt: str, think: Any) -> AsyncIterator[dict[str, Any]]:
    """Research, then Intake and Architect: status lines followed by {"type": "ready", info, contract, notes}."""
    info: dict[str, Any] = dict(_EMPTY)
    gear = complexity_governor.classify(prompt)
    async for evt in _research_events(prompt, think) if gear.research else _no_events():
        if evt["type"] == "info":
            info = evt["info"]
        else:
            yield evt
    info["request"] = prompt  # the user's own words: the scenario tests are written from them
    contract = None
    async for evt in _contract_events(prompt) if gear.agents else _no_events():
        if evt["type"] == "contract":
            contract = evt["contract"]
        else:
            yield evt
    yield {"type": "ready", "info": info, "contract": contract, "notes": (agent_contracts.writer_notes(contract) if contract else "") + skill_library.reference(prompt)
           + design_system.brief(prompt) + await asyncio.to_thread(docs_vault.brief, prompt) + preferences.brief()}


def _note_assumptions(ws_id: str, assumed: list[str]) -> None:
    import workspace_builder as wb

    if assumed:
        ledger.assume(wb.safe_workspace_dir(ws_id), assumed)


async def stream_generate(prompt: str, project_type: str = "auto", model_override: str | None = None) -> AsyncIterator[dict[str, Any]]:
    """Drop-in replacement for workspace_builder.stream_generate_project with research and a coverage pass."""
    import workspace_builder as wb

    model = await wb.pick_coder_model(model_override)
    reasoner = await wb.pick_coder_model(REASONING_MODEL)

    def caller(which: str) -> Any:
        async def gen(system: str | None, user: str, tokens: int, temp: float) -> str:
            return await wb._ollama_generate(which, system or wb.FILE_WRITER_SYSTEM_PROMPT, user, num_predict=tokens, temperature=temp)

        return gen

    think, write = caller(reasoner), caller(model)
    ready: dict[str, Any] = {}
    spoken: list[str] = []
    async for evt in _preparation_events(prompt, think):
        if evt["type"] == "ready":
            ready = evt
        else:
            spoken.append(str(evt.get("message") or ""))
            yield evt
    info, contract, notes = ready["info"], ready["contract"], ready["notes"]
    done: dict[str, Any] = {}
    assumed = ledger.assumption_lines(spoken)
    async for evt in wb.stream_generate_project(prompt + brief_text(info) + notes, project_type=project_type, model_override=model_override, run_smoke=False):
        if evt["type"] == "done":
            done = evt
        else:
            yield evt
    if done and contract:
        (wb.safe_workspace_dir(done["workspace"]["id"]) / spec_contract.SPEC_FILE).write_text(contract.model_dump_json(indent=2), encoding="utf-8")
    if done:
        _note_assumptions(done["workspace"]["id"], assumed)
        async for evt in _coverage_events(done, info, (think, write)):
            yield evt


async def _research_events(prompt: str, think: Any) -> AsyncIterator[dict[str, Any]]:
    """Status lines of the research step, then {"type": "info", "info": ...} with the brief (empty when research failed)."""
    if len(prompt) >= 700:  # a detailed description is the specification; invented "typical features" would only dilute it
        yield {"type": "status", "message": "Tarif ayrıntılı: yazdığın şekilde uygulanacak."}
        yield {"type": "info", "info": dict(_EMPTY)}
        return
    yield {"type": "status", "message": "Konu araştırılıyor: ürünün gerçek dünyadaki işlevleri ve arayüzü çıkarılıyor..."}
    try:
        info = await research(prompt, think)
    except (OSError, RuntimeError, ValueError, TypeError, KeyError):
        info = dict(_EMPTY)
    if info["features"]:
        src = f" (kaynak: {info['source']})" if info["source"] else ""
        yield {"type": "status", "message": f"Araştırma tamamlandı{src}: {len(info['features'])} işlev, {len(info['ui'])} arayüz öğesi belirlendi."}
    yield {"type": "info", "info": info}


async def _coverage_events(done: dict[str, Any], info: dict[str, Any], callers: tuple[Any, Any]) -> AsyncIterator[dict[str, Any]]:
    """Progress events of the coverage pass, then the updated 'done' event (with the new file tree and warnings)."""
    import workspace_builder as wb

    ws_dir = wb.safe_workspace_dir(done["workspace"]["id"])
    try:
        async for evt in _coverage_pass(ws_dir, info, callers, str(info.get("request") or "")):
            if evt["type"] == "coverage":
                warnings = [*done.get("warnings", []), *([evt["warning"]] if evt["warning"] else [])]
                done = {**done, "tree": wb.build_file_tree(ws_dir), "warnings": warnings}
            else:
                yield evt
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
        done = {**done, "warnings": [*done.get("warnings", []), f"Özellik denetimi tamamlanamadı: {exc}"]}
    yield await post_checks.apply(ws_dir, str(info.get("request") or ""), done)
