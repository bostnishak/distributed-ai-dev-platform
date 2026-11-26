"""Word and PDF requests: the model writes document blocks plus the inputs of any calculation; code does the maths and renders the file."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import deliverable_score
import doc_calc
import doc_polish
import doc_proof
import doc_render_docx
import doc_render_pdf
import doc_research
import doc_sanity
import doc_spec
import json_repair
from prompt_loader import load_prompt

MAX_ATTEMPTS = 3
RETRY_FLOOR = 75
CLEAN_DRAFT = 92  # a draft that already passes every deterministic check skips the slow editor generation
NO_CONTENT = "Belgenin içeriğini üretemedim (model geçerli bir belge yapısı döndürmedi). Kalıp ya da boş bir dosya vermemek için oluşturmadım; lütfen tekrar dener misin? Belgenin amacını ve bildiğin bilgileri (taraflar, tutarlar, süre) yazarsan sonuç daha iyi olur."


async def _reviewed(prompt: str, draft: dict[str, Any], model: str) -> dict[str, Any] | None:
    """Second pass: an editor prompt fixes typos, removes invented facts and fills structural gaps; None when it returned nothing usable."""
    import gateway

    ask = f"KULLANICININ İSTEĞİ:\n{prompt}\n\nTASLAK JSON:\n{json.dumps(draft, ensure_ascii=False)}"
    try:
        res = await gateway.default_client.chat([{"role": "system", "content": load_prompt("b3_doc_review.txt")}, {"role": "user", "content": ask}], model=model, profile="factual", num_predict=4500, timeout_s=240.0, feature="document_factory", max_retries=0)
    except (OSError, RuntimeError, ValueError, TypeError):
        return None
    fixed = json_repair.loads_top(res.content)
    old, new = doc_spec.parse(draft), doc_spec.parse(fixed) if fixed else None
    return fixed if old and new and len(new["blocks"]) >= 0.7 * len(old["blocks"]) else None


def _requested_pages(prompt: str) -> int:
    m = re.search(r"(\d{1,2})\s*sayfa", prompt.split("ARAŞTIRMA BULGULARI")[0], re.IGNORECASE)
    return int(m.group(1)) if m else 0


def _length_budget(prompt: str) -> str:
    """A requested page count becomes a word budget the model can follow (a 1-page request used to come back as 2 pages)."""
    pages = _requested_pages(prompt)
    return f"\n\n[Uzunluk sınırı: {pages} sayfa; en fazla {330 * pages} kelime ve en fazla {4 + 2 * pages} içerik bloğu yaz, fazlasını yazma.]" if pages else ""


def _build_pdf_fitting(out_path: Path, spec: dict[str, Any], fonts: Any, prompt: str) -> int:
    """Render the PDF; when the user asked for N pages and it came out longer, shrink the type step by step until it fits. Returns the page count."""
    limit, pages = _requested_pages(prompt), 0
    for scale in (1.0, 0.93, 0.86, 0.8, 0.74, 0.68):
        pages = doc_render_pdf.build(out_path, spec, fonts, scale)
        if pages <= (limit or 99):
            break
    return pages


async def _complete_calc(prompt: str, draft: dict[str, Any], model: str) -> dict[str, Any]:
    """Placeholders the model used but never defined would print as blanks: ask for the missing definitions (up to two rounds) and merge them."""
    import gateway

    for _ in range(2):
        missing = doc_calc.missing_keys(draft)
        if not missing:
            break
        rows = doc_calc.run(draft.get("calc"))[2]
        known = "\n".join(f"- {r['key']} = {r['value']} ({r['label']})" for r in rows) or "(yok)"
        todo = "\n".join(f"- {k}: \"{ctx}\"" for k, ctx in missing.items())
        ask = f"KULLANICININ İSTEĞİ:\n{prompt}\n\nMEVCUT GİRDİ/ÇIKTILAR:\n{known}\n\nTANIMSIZ ANAHTARLAR:\n{todo}"
        try:
            res = await gateway.default_client.chat([{"role": "system", "content": load_prompt("b3_doc_calc_fix.txt")}, {"role": "user", "content": ask}], model=model, profile="factual", num_predict=1400, timeout_s=240.0, feature="document_factory", max_retries=0)
        except (OSError, RuntimeError, ValueError, TypeError):
            break
        extra = json_repair.loads_top(res.content) or {}
        calc = draft.setdefault("calc", {})
        if not isinstance(calc, dict):
            calc = draft["calc"] = {}
        for kind in ("inputs", "outputs"):
            known_keys = {i.get("key") for i in calc.get(kind) or [] if isinstance(i, dict)}
            calc.setdefault(kind, [])
            calc[kind] += [i for i in extra.get(kind) or [] if isinstance(i, dict) and i.get("key") not in known_keys]
    return draft


async def _draft(prompt: str, target_lang: str, model: str) -> dict[str, Any] | None:
    """First pass: up to two attempts, because a local model sometimes returns broken JSON."""
    import gateway

    system = load_prompt("b3_doc_blocks_schema.txt").replace("{target_lang}", target_lang)
    for tries in range(4):
        short = "\n\n[Kısa ve basit tut: en fazla 8 blok, hesap gerekmiyorsa calc kullanma, geçerli JSON'u eksiksiz bitir.]" if tries == 3 else ""  # last resort after three broken drafts
        res = await gateway.default_client.chat([{"role": "system", "content": system}, {"role": "user", "content": prompt + doc_polish.request_facts(prompt) + _length_budget(prompt) + short}], model=model, profile="factual", num_predict=4500, timeout_s=300.0, feature="document_factory", max_retries=1)
        draft = json_repair.loads_top(res.content)
        if draft and doc_spec.parse(draft, prompt) is not None:
            return draft
    return None


async def _attempt(prompt: str, fmt: str, ctx: tuple[str, str, list[dict[str, str]]], out_path: Path, fonts: Any) -> tuple[dict[str, Any], int, list[str]]:
    """One full pass: draft, complete the calculations, editor review, proofreading, render, score. Returns (spec, score, problems)."""
    target_lang, model, sources = ctx
    draft = await _draft(prompt, target_lang, model)
    if draft is None:
        raise RuntimeError(NO_CONTENT)
    draft = await _complete_calc(prompt, draft, model)
    spec = doc_spec.parse(draft, prompt)
    if spec is None or deliverable_score.score_document(spec, prompt)[0] < CLEAN_DRAFT:
        spec = doc_spec.parse(await _reviewed(prompt, draft, model), prompt) or spec  # the editor pass only when the checks found something to fix
    if spec is None:
        raise RuntimeError(NO_CONTENT)
    await doc_proof.proofread(spec["blocks"], model)
    if unsure := doc_sanity.implausible_results(spec):  # never hand over absurd figures silently
        spec["blocks"].append({"type": "para", "text": "Not: Bu belgedeki bazı hesap sonuçları otomatik tutarlılık denetiminden geçemedi (" + unsure[0][:160] + "). Kullanmadan önce rakamları doğrulayın."})
    spec["blocks"] += doc_research.bibliography(sources)
    pages = _build_pdf_fitting(out_path, spec, fonts, prompt) if fmt == "pdf" else 0
    if fmt != "pdf":
        doc_render_docx.build(out_path, spec, fonts)
    score, issues = deliverable_score.score_document(spec, prompt, _requested_pages(prompt), pages)
    return spec, score, issues


async def generate(prompt: str, fmt: str, ctx: tuple[str, str], out_path: Path, helpers: tuple[Any, Any]) -> dict[str, Any]:
    """Quality loop: build, score, and when the score is below target retry once with the concrete problems; the best attempt is kept."""
    fonts, best, extra = helpers[1], None, ""
    sources, note = await doc_research.gather(prompt)
    prompt, ctx3 = prompt + note, (*ctx, sources)
    for attempt in range(MAX_ATTEMPTS):
        try:
            spec, score, issues = await _attempt(prompt + extra, fmt, ctx3, out_path if best is None else out_path.with_suffix(f".try{attempt}{out_path.suffix}"), fonts)
        except RuntimeError:
            if best is None:
                raise
            break
        if best is None or score > best[1]:
            if best is not None:
                out_path.with_suffix(f".try{attempt}{out_path.suffix}").replace(out_path)
            best = (spec, score, issues)
        else:
            out_path.with_suffix(f".try{attempt}{out_path.suffix}").unlink(missing_ok=True)
        if best[1] >= deliverable_score.TARGET or (attempt >= 1 and best[1] >= RETRY_FLOOR):
            break  # a second round only fixes what is clearly wrong; a good-enough result is not worth another 3-5 minutes
        extra = deliverable_score.feedback(best[2])
    spec = best[0]  # type: ignore[index]
    tables = next((b for b in spec["blocks"] if b["type"] == "table"), None)
    first_para = next((b["text"] for b in spec["blocks"] if b["type"] == "para"), "")
    return {
        "file_id": out_path.stem, "format": fmt, "title": spec["title"], "summary": spec["subtitle"] or first_para[:240], "sections": [],
        "table_headers": tables["headers"] if tables else [], "table_rows": tables["rows"][:10] if tables else [],
        "model": ctx[1], "sources": [s["url"] for s in sources], "url": f"/api/assistant/media/{out_path.name}", "quality_score": best[1],  # type: ignore[index]
    }
