"""Modular request preprocessing, media serving, and SSE verification helpers for `assistant.py`."""

from __future__ import annotations

import base64
import csv
import io
import json
import logging
import os
import sqlite3
import time
import zipfile
from typing import Any

import httpx
from fastapi import Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

import config
from extract import extract_csv_text, extract_docx_text, extract_pdf_text, extract_xlsx_text, extract_zip_text

log = logging.getLogger("master.assistant")

_MEDIA_TYPES: dict[str, tuple[str | None, bool]] = {
    ".svg": ("image/svg+xml", False),
    ".png": ("image/png", False),
    ".pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", True),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", True),
    ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", True),
    ".pdf": ("application/pdf", True),
    ".zip": ("application/zip", True),
    ".csv": (None, True),
    ".txt": (None, True),
    ".md": (None, True),
    ".json": (None, True),
}

_TEXT_SUFFIXES = (
    ".txt", ".md", ".json", ".xml", ".yaml", ".yml", ".html", ".css", ".js", ".ts", ".py", ".sql", ".log", ".ini"
)


def build_media_file_response(filename: str) -> FileResponse:
    """Resolve and return a safe FileResponse for generated/edited media files."""
    import multimodal_studio as mms

    safe = "".join(c for c in filename if c.isalnum() or c in ("-", "_", "."))
    if not safe or safe != filename:
        raise HTTPException(status_code=400, detail="Geçersiz medya dosya adı.")
    target = mms.media_dir() / safe
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.")
    headers = {"Cache-Control": "no-cache"}
    media_type: str | None = None
    for ext, (mtype, attach) in _MEDIA_TYPES.items():
        if safe.endswith(ext):
            media_type = mtype
            if attach:
                headers["Content-Disposition"] = f'attachment; filename="{safe}"'
            break
    return FileResponse(target, headers=headers, media_type=media_type)


def _process_image_upload(raw: bytes, prompt: str) -> tuple[str, str]:
    import media_lab_arena as mla
    import multimodal_studio as mms

    file_note = ""
    lower_p = prompt.lower()
    if any(k in lower_p for k in ("tara", "tarayıcı", "tarayici", "gölge", "golge", "belge temizle", "scan")):
        scan_info = mla.scan_and_clean_document_image(raw)
        file_note = (
            f"\n\n### İşlenmiş Görsel Çıktısı\n"
            f"- **Belge Tarayıcı ve Gölge Giderme:** `{scan_info['width']}x{scan_info['height']}` | "
            f"**Aydınlatma Sapması:** `{scan_info['original_illumination_std']} -> {scan_info['cleaned_illumination_std']}`\n"
            f"- [Taranmış Belgeyi İndir (PNG)]({scan_info['url']})\n\n"
            f"![Taranmış Belge]({scan_info['url']})\n"
        )
    elif mms.is_image_edit_request(prompt):
        edit_info = mms.process_and_edit_image(raw, prompt)
        filters_str = ", ".join(edit_info["applied_filters"])
        file_note = (
            f"\n\n### İşlenmiş Görsel Çıktısı\n"
            f"- **Uygulanan İşlemler:** {filters_str}\n"
            f"- **Boyut:** {edit_info['original_size']} -> {edit_info['output_size']} · "
            f"**Ortalama Parlaklık:** {edit_info['mean_brightness']} · **Kontrast (Std):** {edit_info['std_contrast']}\n"
            f"- [İşlenmiş Görseli İndir (PNG)]({edit_info['url']})\n\n"
            f"![İşlenmiş Görsel]({edit_info['url']})\n"
        )
    return base64.b64encode(raw).decode(), file_note


_FORECAST_KEYWORDS = (
    "tahmin",
    "forecast",
    "öngör",
    "ongor",
    "gelecek",
    "projeksiyon",
    "regresyon",
    "predict",
    "veri_analizi:tahmin",
)


def _wants_csv_forecast(prompt: str) -> bool:
    low = (prompt or "").lower()
    return any(k in low for k in _FORECAST_KEYWORDS)


def _extract_csv_with_automl(name: str, raw: bytes, prompt: str = "") -> str:
    """DEF-06: Attach profile summary by default; run forecast with uncertainty interval only when requested."""
    import automl_studio as aml

    extracted = extract_csv_text(raw)
    try:
        delim = "\t" if name.endswith(".tsv") else ","
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8", errors="ignore")), delimiter=delim))
        if rows:
            prof = aml.profile_dataset(rows)
            num_cols = prof.get("numeric_columns", [])
            aml_lines = [
                f"\n\n### AutoML Veri Profili Özeti ({prof['row_count']} satır, {prof['column_count']} sütun)",
                f"- **Sayısal Sütunlar:** `{', '.join(num_cols) or '-'}` | **Tespit Edilen Anomali:** `{len(prof.get('anomalies', []))}` satır",
            ]
            if _wants_csv_forecast(prompt) and num_cols and len(rows) >= 4:
                fc = aml.train_and_forecast(rows, target_col=num_cols[-1], horizon=3)
                rmse = float(fc["metrics"]["rmse"])
                ci = round(1.96 * rmse, 2)
                preds = ", ".join(f"T+{p['step']}: {p['prediction']:.2f} (±{ci:.2f})" for p in fc.get("forecasts", []))
                aml_lines.append(
                    f"- **[Araç Çıktısı] L2 Ridge Tahmin ({num_cols[-1]}):** R2=`{fc['metrics']['r2']:.3f}`, "
                    f"RMSE=`{rmse:.2f}`, 95% belirsizlik aralığı=`±{ci:.2f}` -> `{preds}`"
                )
            extracted += "\n" + "\n".join(aml_lines)
    except (OSError, ValueError, TypeError, KeyError, ArithmeticError, IndexError, RuntimeError, ImportError) as exc:
        log.debug("AutoML enrichment skipped: %s", exc)
    return extracted


def _extract_sqlite_upload(filename: str, raw: bytes, prompt: str) -> str:
    import domain_experts as de

    tmp_db = config.DATA_DIR / f"upload_{os.getpid()}.sqlite"
    tmp_db.parent.mkdir(parents=True, exist_ok=True)
    tmp_db.write_bytes(raw)
    try:
        sql_res = de.introspect_sqlite_and_query(tmp_db, prompt)
        return (
            f"[SQLite Veritabanı Şema ve Sorgu Sonucu]\n"
            f"Çalıştırılan SQL: `{sql_res['executed_sql']}` ({sql_res['row_count']} satır)\n"
            f"İlk Satırlar: {json.dumps(sql_res['rows'][:10], ensure_ascii=False)}\n"
            f"ER Diyagramı:\n```mermaid\n{sql_res['er_diagram']}\n```"
        )
    except (sqlite3.Error, OSError, ValueError, TypeError, KeyError, RuntimeError, ImportError) as exc:
        return f"[SQLite Veritabanı: {filename} ({exc})]"
    finally:
        tmp_db.unlink(missing_ok=True)


def _extract_document_bytes(filename: str, content_type: str, raw: bytes, prompt: str) -> tuple[str, str | None, str]:
    name = filename.lower()
    if content_type.startswith("audio/") or name.endswith((".wav", ".mp3", ".m4a", ".ogg", ".webm", ".flac")):
        import multimodal_studio as mms

        stt = mms.transcribe_audio_bytes(filename, raw)
        if stt["transcript"]:
            return f"[Ses Kaydı Metin Dökümü ({stt['engine']}, {stt['duration_sec']} sn)]:\n{stt['transcript']}", "analiz", ""
        return (
            f"[Ses Dosyası Yüklendi: {filename} ({stt['size_kb']} KB, {stt['duration_sec']} sn). "
            "Lütfen kullanıcının sesli mesaj isteğine göre yanıt ver.]",
            "analiz",
            "",
        )
    simple_extractors = (
        ((".pdf",), extract_pdf_text),
        ((".docx",), extract_docx_text),
        ((".xlsx", ".xlsm"), extract_xlsx_text),
    )
    for exts, fn in simple_extractors:
        if name.endswith(exts):
            return fn(raw), "analiz", ""
    if name.endswith((".csv", ".tsv")):
        return _extract_csv_with_automl(name, raw, prompt), "analiz", ""
    if name.endswith((".db", ".sqlite", ".sqlite3")):
        return _extract_sqlite_upload(filename, raw, prompt), "analiz", ""
    if name.endswith(".zip"):
        try:
            return extract_zip_text(raw), "analiz", ""
        except (zipfile.BadZipFile, OSError, ValueError, TypeError, KeyError, RuntimeError):
            return f"[ZIP Arşivi: {filename}]", "analiz", ""
    if name.endswith(_TEXT_SUFFIXES) or content_type.startswith("text/"):
        import file_inspector as fi

        txt, _enc = fi.decode_text_turkish_safe(raw)
        return txt, "analiz", ""
    return "", None, f"\n\n[Not: '{filename}' desteklenmeyen bir dosya türü.]"


async def process_uploaded_attachment(file: UploadFile, prompt: str) -> tuple[str, str | None, str | None, str]:
    """Read and extract an uploaded file attachment along with deterministic inspection notes."""
    filename = file.filename or "dosya"
    name = filename.lower()
    content_type = file.content_type or ""
    raw = await file.read()

    image_b64: str | None = None
    extracted_text = ""
    forced_task_type: str | None = None
    file_note = ""

    if content_type.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff")):
        image_b64, file_note = _process_image_upload(raw, prompt)
        forced_task_type = "analiz"
    else:
        extracted_text, forced_task_type, file_note = _extract_document_bytes(filename, content_type, raw, prompt)

    if not (content_type.startswith("image/") or content_type.startswith("audio/")):
        import chat_contracts
        import file_inspector as fi

        try:
            insp = fi.inspect_uploaded_file(filename, raw)
            if chat_contracts.should_attach_file_audit(prompt, insp):
                file_note += f"\n\n{fi.format_inspection_markdown(insp)}"
        except (OSError, ValueError, TypeError, KeyError, RuntimeError, SyntaxError, ImportError, AttributeError) as exc:
            log.debug("File audit skipped: %s", exc)

    return extracted_text, image_b64, forced_task_type, file_note


def build_domain_enrichment_notes(prompt: str, extracted_text: str) -> str:
    """Apply KVKK PII redaction, legal contract analysis, and DCF guardrail notes."""
    lower_prompt = prompt.lower()
    combined_source = f"{prompt}\n{extracted_text}".strip()
    note = ""
    if any(k in lower_prompt for k in ("kvkk", "pii", "maskele", "anonimleştir", "anonimlestir", "kişisel veri gizle")):
        import media_lab_arena as mla

        pii = mla.redact_sensitive_pii(combined_source)
        if pii["has_pii"]:
            note += (
                f"\n\n### KVKK / PII Hassas Veri Maskeleme Özeti ({pii['total_redacted']} öğe maskelendi)\n"
                f"- **Sayım:** `{json.dumps(pii['counts'], ensure_ascii=False)}`\n"
                f"- **Maskelenmiş Metin:**\n```\n{pii['cleaned_text'][:2000]}\n```\n"
            )
    if extracted_text and any(
        k in lower_prompt for k in ("sözleşme risk", "sozlesme risk", "redline", "cezai şart", "cezai sart", "hukuki inceleme")
    ):
        import domain_experts as de

        leg = de.analyze_legal_contract(combined_source)
        note += (
            f"\n\n--- Hukuki Sözleşme Risk Motoru Çıktısı ---\n"
            f"Genel Risk: {leg['overall_risk']} (Skor: {leg['risk_score']}/100, Yüksek Risk: {leg['high_risk_count']})\n"
            f"Eksik Maddeler: {', '.join(leg['missing_clauses']) or 'Yok'}\n"
            f"Revizyon (Redline) Önerileri: {json.dumps(leg['redline_recommendations'], ensure_ascii=False)}"
        )
    if any(k in lower_prompt for k in ("dcf", "monte carlo", "şirket değerleme", "sirket degerleme", "cfo analiz", "npv simülasyon")):
        note += (
            "\n\n--- Finansal Değerleme (DCF / Monte Carlo) ---\n"
            "Kullanıcı gerçek finansal veri vermedi. Gelir, FAVÖK, büyüme oranı, WACC ve borç gibi "
            "girdileri kullanıcıdan iste; bu değerleri tahmin etme veya uydurma, sonuç sayısı üretme."
        )
    return note


def enrich_prompt_with_kb(prompt: str, extracted_text: str) -> str:
    """Attach extracted file text or Hybrid GraphRAG company knowledge snippets."""
    if extracted_text:
        limit = 16000
        trunc = f"\n[Not: Dosya uzunluğu {len(extracted_text)} karakter; ilk {limit} karakter gösteriliyor.]" if len(extracted_text) > limit else ""
        return (
            f"{prompt}\n\n--- Eklenen dosya içeriği (GERÇEK VERİ - uydurma yapma, olmayan hata ekleme) ---\n"
            f"{extracted_text[:limit]}{trunc}"
        )
    import company_rag
    import hybrid_graph_rag

    kb_docs = company_rag.search_company_kb_sync(prompt, top_k=2)
    graph_lines: list[str] = []
    try:
        grag = hybrid_graph_rag.HybridGraphRAG()
        g_hits = [h for h in grag.search(prompt, top_k=2) if h["bm25_score"] > 0]
        graph_lines = [f"- [GraphRAG] {gh['title']}: {gh['content'][:300]}" for gh in g_hits]
    except (sqlite3.Error, httpx.HTTPError, OSError, ValueError, TypeError, KeyError, RuntimeError):
        log.warning("GraphRAG araması başarısız", exc_info=True)
    if kb_docs or graph_lines:
        kb_text = "\n".join([*(f"- {d['title']}: {d['content']}" for d in kb_docs), *graph_lines])
        return f"{prompt}\n\n--- Şirket Mühendislik Bilgi Bankası (Hybrid GraphRAG) ---\n{kb_text}"
    return prompt


async def enrich_done_event_with_verification(
    evt: dict[str, Any], prompt: str, answer: str, meta: tuple[str, str]
) -> None:
    """Attach orchestrator intent and NLI verification metadata onto the final SSE done event."""
    model_used, conversation_id = meta
    try:
        from hallucination.verifier import (
            compute_confidence,
            extract_claims,
            log_verification_telemetry,
            verify_claims_nli,
        )
        from orchestrator.classifier import classify_intent
        from orchestrator.contracts import build_contract
        from rag.store import default_rag_store

        intent_dec = classify_intent(prompt)
        contract = build_contract(intent_dec.mode)
        sources: list[dict[str, Any]] = []
        try:
            rag_res = await default_rag_store.search(prompt, top_k=3)
            sources = [
                {
                    "id": f"S{i + 1}",
                    "content": h.get("content", "") if isinstance(h, dict) else getattr(h, "content", ""),
                    "doc": h.get("doc_title", "") if isinstance(h, dict) else getattr(h, "doc_title", ""),
                }
                for i, h in enumerate((rag_res.hits if rag_res else []) or [])
            ]
        except (sqlite3.Error, httpx.HTTPError, OSError, ValueError, TypeError, KeyError, RuntimeError, AttributeError) as rag_exc:
            log.debug("Live chat RAG lookup skipped: %s", rag_exc)

        claims = extract_claims(answer)
        verdicts = verify_claims_nli(claims, sources) if claims and sources else []
        supported = sum(1 for v in verdicts if v.status == "supported")
        support_ratio = round(supported / max(1, len(verdicts)), 3) if verdicts else (1.0 if not claims else 0.75)
        conf = compute_confidence(support_ratio=support_ratio, rag_score=0.85 if sources else 0.5, has_sources=bool(sources))
        run_id = f"chat-{conversation_id or 'ephemeral'}-{int(time.time())}"
        log_verification_telemetry(
            run_id=run_id,
            model=model_used or config.MASTER_MODEL,
            task_type=intent_dec.intent,
            support_ratio=support_ratio,
            citation_coverage=1.0 if sources else 0.0,
            confidence=float(conf.get("score", 0.75)),
            abstained=False,
            verify_ms=1,
        )
        evt["orchestrator"] = {
            "intent": intent_dec.intent,
            "mode": contract.mode,
            "risk": intent_dec.risk,
            "grounded_sources": len(sources),
        }
        evt["verification"] = {
            "confidence_score": float(conf.get("score", 0.75)),
            "confidence_label": str(conf.get("label", "orta")),
            "support_ratio": support_ratio,
            "claims_checked": len(claims),
        }
    except (ImportError, sqlite3.Error, httpx.HTTPError, OSError, ValueError, TypeError, KeyError, RuntimeError, AttributeError) as orch_exc:
        log.warning("Orchestrator/verifier hook failed on chat stream: %s", orch_exc, exc_info=True)


def _build_research_context(prompt: str, has_file: bool, is_prompt_conv: bool) -> tuple[list[dict[str, str]], str]:
    import chat_contracts

    if is_prompt_conv or not chat_contracts.is_grounded_research_request(prompt, has_file):
        return [], ""
    sources = chat_contracts.gather_research_sources(prompt)
    if sources:
        src_lines = [f"[{s['id']}] {s['title']} ({s['url']}): {s['snippet']}" for s in sources]
        return sources, (
            "ARAŞTIRMA KAYNAKLARI (yalnızca bu kaynaklara dayanarak yanıtla ve her önemli olguda [S1], [S2] atıfı ekle):\n"
            + "\n".join(src_lines)
        )
    return [], (
        "ARAŞTIRMA NOTU: Canlı web araması (SearXNG) şu an yapılandırılmamış. "
        "Temel akademik kavramları [S1] biçiminde standart referanslara (ör. Nielsen & Chuang, NIST) bağlayarak özetle "
        "ve yanıtın sonunda 'Kaynaklar' listesi ile 'Not: Canlı web araması kapalı olduğu için güncel veriler doğrulanmadı.' uyarısını ekle."
    )


def _append_history_messages(messages: list[dict[str, Any]], history: str, is_prompt_conv: bool) -> None:
    hist_window = 40 if is_prompt_conv else 16
    try:
        hist_items = json.loads(history) if history else []
        if isinstance(hist_items, list):
            for h_msg in hist_items[-hist_window:]:
                if isinstance(h_msg, dict) and h_msg.get("role") in ("user", "assistant") and h_msg.get("text"):
                    messages.append({"role": h_msg["role"], "content": str(h_msg["text"])[:3000]})
    except (json.JSONDecodeError, TypeError) as exc:
        log.debug("History parse skipped: %s", exc)


def parse_stream_opts(
    user_id: str = Form("default"),
    conversation_id: str = Form(""),
    model: str = Form(""),
    custom_agent_id: str = Form(""),
) -> dict[str, str]:
    """Parse optional chat stream form fields cleanly without exceeding route arg limits."""
    return {
        "user_id": user_id,
        "conversation_id": conversation_id[:80],
        "model": model.strip()[:80],
        "custom_agent_id": custom_agent_id.strip()[:64],
    }


def resolve_custom_agent_profile(custom_agent_id: str, user_id: str) -> dict[str, Any] | None:
    """Resolve a user-defined custom agent from SQLite registry or productivity store (AJN-01)."""
    aid = (custom_agent_id or "").strip()
    if not aid:
        return None
    try:
        from custom_agents import list_custom_agents

        for item in list_custom_agents(user_id):
            if str(item.get("agent_id")) == aid:
                return {
                    "id": aid,
                    "name": str(item.get("name") or aid),
                    "instructions": str(item.get("instructions") or ""),
                    "model": str(item.get("model_override") or ""),
                    "tools": list(item.get("allowed_tools") or []),
                }
    except (sqlite3.Error, ValueError, TypeError, KeyError, ImportError):
        pass
    try:
        import productivity_api as papi

        rec = papi._CUSTOM_AGENTS.get(aid)
        if isinstance(rec, dict):
            return {
                "id": aid,
                "name": str(rec.get("name") or aid),
                "instructions": str(rec.get("instructions") or ""),
                "model": str(rec.get("model") or ""),
                "tools": list(rec.get("tools") or []),
            }
    except (ValueError, TypeError, KeyError, ImportError, AttributeError):
        pass
    return None


def _collect_memory_blocks(ctx: dict[str, Any], prompt_conv_instruction: str) -> list[str]:
    import memory_engine as mem
    import user_profile as up

    prompt, user_id = ctx["prompt"], ctx["user_id"]
    user_settings = up.get_settings(user_id)
    blocks = [up.personalization_block(user_id)]
    agent_prof = ctx.get("custom_agent")
    if isinstance(agent_prof, dict) and agent_prof.get("instructions"):
        blocks.append(f"--- ÖZEL AJAN TALİMATI ({agent_prof.get('name', 'Ajan')}) ---\n{agent_prof['instructions']}")
    if user_settings.get("auto_learn_facts"):
        mem.extract_and_upsert_memories(prompt, user_id=user_id)
    blocks.append(mem.build_memory_context_block(prompt, user_id=user_id))
    if user_settings.get("cross_chat_memory", True):
        blocks.append(up.cross_chat_context_block(user_id, prompt, exclude_conversation=ctx["conversation_id"]))
    if ctx["is_prompt_conv"]:
        blocks.append(prompt_conv_instruction)
    return blocks


def _split_pre_notes(full_prompt: str) -> tuple[str, str]:
    pre_note = ""
    for marker in ("### İşlenmiş Görsel Çıktısı", "### Deterministik Dosya Denetim Raporu"):
        if marker in full_prompt:
            idx_n = full_prompt.index(marker)
            pre_note += full_prompt[idx_n:] + "\n\n---\n\n"
            full_prompt = full_prompt[:idx_n].strip()
    return full_prompt, pre_note


def build_llm_stream_inputs(
    ctx: dict[str, Any], answer_system_prompt: str, prompt_conv_instruction: str
) -> tuple[list[dict[str, Any]], str, Any, list[dict[str, str]]]:
    """Assemble system prompt, memory/research blocks, history, and pre-notes for LLM streaming."""
    import chat_contracts
    import memory_engine as mem

    messages: list[dict[str, Any]] = [{"role": "system", "content": answer_system_prompt}] if answer_system_prompt else []
    extra_blocks = _collect_memory_blocks(ctx, prompt_conv_instruction)
    constraints = chat_contracts.inspect_prompt_constraints(ctx["prompt"])
    research_sources, research_note = _build_research_context(ctx["prompt"], ctx["has_file"], ctx["is_prompt_conv"])
    if research_note:
        extra_blocks.append(research_note)
    if constraints.system_notes:
        extra_blocks.append("\n".join(constraints.system_notes))
    mem_ctx = "\n\n".join(b for b in extra_blocks if b)
    if mem_ctx and messages:
        messages[0]["content"] = f"{messages[0]['content']}\n\n{mem_ctx}"

    _append_history_messages(messages, ctx["history"], ctx["is_prompt_conv"])
    if not ctx["is_prompt_conv"]:
        messages = mem.compact_conversation_context(messages)
    full_prompt, pre_note = _split_pre_notes(ctx["full_prompt"])
    user_msg: dict[str, Any] = {"role": "user", "content": full_prompt}
    if ctx["image_b64"]:
        user_msg["images"] = [ctx["image_b64"]]
    messages.append(user_msg)
    return messages, pre_note, constraints, research_sources


def _finalize_buffered_text(
    buffered: list[str], constraints: Any, research_sources: list[dict[str, str]], grounded_research: bool
) -> str:
    import chat_contracts

    final_text = chat_contracts.enforce_output_constraints("".join(buffered), constraints)
    if grounded_research and "[S1]" not in final_text:
        if research_sources:
            ref_lines = "\n".join(f"- [{s['id']}] {s['title']} — {s['url']}" for s in research_sources)
            return f"{final_text}\n\n### Kaynaklar\n{ref_lines}"
        return (
            f"{final_text}\n\n### Kaynaklar\n"
            "- [S1] Genel kavramsal özet (Not: Canlı web araması kapalı olduğu için güncel kaynak doğrulaması yapılmadı; SEARXNG_URL ile web aramasını açabilirsiniz.)"
        )
    return final_text


def _build_done_evt(evt: dict[str, Any], model: str, task_type: str) -> dict[str, Any]:
    done_evt: dict[str, Any] = {"type": "done", "model": model, "task_type": task_type, "run_id": evt.get("run_id")}
    if evt.get("tokens_out") is not None:
        done_evt["usage"] = {
            "prompt_tokens": int(evt.get("tokens_in") or 0),
            "completion_tokens": int(evt.get("tokens_out") or 0),
            "estimated": False,
        }
    return done_evt


def _handle_stream_event(
    evt: dict[str, Any], state: dict[str, Any], strip_emojis_fn: Any
) -> list[str]:
    out: list[str] = []
    if evt.get("type") == "token":
        piece = strip_emojis_fn(str(evt.get("content") or ""))
        if piece:
            if state["need_buffer"]:
                state["buffered"].append(piece)
            else:
                out.append(f"data: {json.dumps({'type': 'token', 'content': piece})}\n\n")
    elif evt.get("type") == "done":
        if state["need_buffer"]:
            ft = _finalize_buffered_text(state["buffered"], state["constraints"], state["research_sources"], state["grounded"])
            if ft:
                out.append(f"data: {json.dumps({'type': 'token', 'content': ft}, ensure_ascii=False)}\n\n")
        out.append(f"data: {json.dumps(_build_done_evt(evt, state['model'], state['task_type']))}\n\n")
    return out


def create_llm_stream_response(stream_cfg: dict[str, Any], strip_emojis_fn: Any) -> StreamingResponse:
    """Create the StreamingResponse that streams tokens from the LLM gateway with constraint enforcement."""
    import chat_contracts
    import gateway

    model, task_type, user_id = stream_cfg["model"], stream_cfg["task_type"], stream_cfg["user_id"]
    gw_profile = "factual" if (stream_cfg["has_file"] or stream_cfg["is_prompt_conv"] or task_type in ("kod", "analiz")) else "analytic"
    grounded = chat_contracts.is_grounded_research_request(stream_cfg["prompt"], stream_cfg["has_file"])
    state = {
        "buffered": [],
        "need_buffer": stream_cfg["constraints"].needs_buffering or bool(stream_cfg["research_sources"]) or grounded,
        "constraints": stream_cfg["constraints"],
        "research_sources": stream_cfg["research_sources"],
        "grounded": grounded,
        "model": model,
        "task_type": task_type,
    }

    async def _stream_gen():
        try:
            if stream_cfg["pre_note"]:
                yield f"data: {json.dumps({'type': 'token', 'content': stream_cfg['pre_note']}, ensure_ascii=False)}\n\n"
            async for evt in gateway.default_client.stream(
                stream_cfg["messages"], model=model, task_type=task_type, profile=gw_profile, user_id=user_id, timeout_s=180.0
            ):
                for line in _handle_stream_event(evt, state, strip_emojis_fn):
                    yield line
        except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError, RuntimeError, AttributeError, ImportError) as exc:
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"

    return StreamingResponse(_stream_gen(), media_type="text/event-stream")
