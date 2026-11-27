"""Modular SSE fast-path handlers and LLM streaming builders for `assistant.py`."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import subprocess
import zipfile
from typing import Any

import httpx
from fastapi import UploadFile
from fastapi.responses import StreamingResponse

import assistant_cad_cnc as _cad
import chat_guard
import clarify as _clarify
import config
import followup
import gcode_chat
import image_chat as _img
import office_verify
import project_flow
import reasoning_mode
import reply_labels
import revise_chat
import run_trace
import text_tools
import untrusted
from deck_flow import call_generator as _call_pptx_generator
from document_chart import chart_series

log = logging.getLogger("master.assistant")

_MEDIA_SSE = "text/event-stream"
_PPTX_ADVICE_RE = re.compile(
    r"(?:nasıl\s*yapıl\w*|nasil\s*yapil\w*|yaparken|nelere\s*dikkat|ipuçlar\w*|ipuclar\w*|"
    r"tavsiyeler\w*|öneriler\w*|oneriler\w*|how\s+to\b|\btips\b|\badvice\b)",
    re.IGNORECASE,
)
_PPTX_NOUN_RE = re.compile(r"\b(?:sunum\w*|slayt\w*|pptx|powerpoint|presentation\w*|slides?)\b", re.IGNORECASE)
_PPTX_VERB_RE = re.compile(
    r"\b(?:yap(?:ar\w*|abil\w*|al[ıi]m|ın|ınız)?|oluştur\w*|olustur\w*|hazırla\w*|hazirla\w*|"
    r"üret\w*|uret\w*|ver(?:ir\w*|ebil\w*|in)?|çıkar\w*|cikar\w*|tasarla\w*|"
    r"creat(?:e|ing)|mak(?:e|ing)|generat(?:e|ing)|build(?:ing)?)\b",
    re.IGNORECASE,
)
_PURE_CONVERT_CUES = ("çevir", "cevir", "dönüştür", "donustur", "aktar", "convert", "export", "haline getir")
_EXPLICIT_ZIP_EXTRACT_CUES = ("unzip", "extract", "ayıkla", "ayikla", "dosyaları çıkar", "dosyalari cikar", "içini çıkar", "icini cikar")
_NEW_PROJECT_BUILD_VERBS = ("oluştur", "olustur", "hazırla", "hazirla", "geliştir", "gelistir", "tasarla", "üret", "uret", "build", "create", "generate", "kodla")


def sse_event(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def single_token_stream(content: str, model: str, task_type: str) -> StreamingResponse:
    async def _gen():
        yield sse_event({"type": "token", "content": content})
        yield sse_event({"type": "done", "model": model, "task_type": task_type})

    return StreamingResponse(_gen(), media_type=_MEDIA_SSE)


def _history_has_messages(history: str) -> bool:
    try:
        items = json.loads(history) if history else []
    except ValueError:
        return False
    return isinstance(items, list) and any(isinstance(i, dict) and i.get("text") for i in items)


def _try_abstain_fastpath(prompt: str, history: str, has_file: bool) -> StreamingResponse | None:
    if has_file:
        return None
    from hallucination.verifier import detect_unanswerable

    gap = detect_unanswerable(prompt)
    if gap["unanswerable"] and gap["reason"] == "private_data" and _history_has_messages(history):
        gap = {"unanswerable": False}
    if gap["unanswerable"]:
        return single_token_stream(str(gap.get("message") or ""), "abstention-policy", "abstain")
    return None


def _build_zip_project_stream(lower_p: str) -> StreamingResponse:
    import workspace_builder as wb

    async def _gen():
        ws_list = wb.list_workspaces()
        if not ws_list:
            msg = "Henüz sıkıştırılacak bir proje çalışma alanı bulunamadı. Önce bir proje oluşturun."
        else:
            target = next(
                (w for w in ws_list if (w.get("name") or "").lower() in lower_p or (w.get("id") or "").lower() in lower_p),
                ws_list[0],
            )
            msg = (
                f"## Proje ZIP Arşivi Hazır: {target.get('name', target['id'])}\n"
                f"- **Çalışma Alanı:** `{target['id']}`\n"
                f"- **ZIP İndirme Bağlantısı:** [Projeyi İndir (.ZIP)](/api/studio/workspaces/{target['id']}/download.zip)"
            )
        yield sse_event({"type": "token", "content": msg})
        yield sse_event({"type": "done", "model": "file-converter", "task_type": "dokuman"})

    return StreamingResponse(_gen(), media_type=_MEDIA_SSE)


def _run_file_conversion_action(act: str, conv_act: dict[str, Any], up_name: str, raw_upload: bytes) -> str:
    import file_converter as fc

    if act == "extract_zip":
        res = fc.extract_zip_to_media(up_name, raw_upload)
        lines = [f"## ZIP Arşivi Açıldı: `{res['zip_filename']}` ({res['file_count']} dosya)", ""]
        if res["files"]:
            lines.extend(["| Dosya | Boyut | İndirme Bağlantısı |", "|---|---|---|",
                          *(f"| `{f['original_path']}` | {f['size_kb']} KB | [İndir]({f['url']}) |" for f in res["files"])])
        else:
            lines.append("Arşiv içinde çıkarılacak dosya bulunamadı.")
        return "\n".join(lines)
    if act == "pack_zip":
        res = fc.pack_files_to_folder_zip(up_name, [(up_name, raw_upload)])
        return (f"## Klasör ve ZIP Arşivi Hazır (`{res['folder_name']}/`)\n"
                f"- **Arşiv İçeriği:** `{', '.join(res['included_files'])}` ({res['size_kb']} KB)\n"
                f"- **İndirme Bağlantısı:** [{res['zip_filename']} (.ZIP İndir)]({res['url']})")
    tfmt = conv_act["target_fmt"]
    cres = fc.convert_uploaded_file(up_name, raw_upload, tfmt)
    if act == "convert_and_zip":
        zres = fc.pack_files_to_folder_zip(up_name, [(up_name, raw_upload), (cres["output_filename"], cres["output_path"].read_bytes())])
        return (f"## Dosya `.{tfmt.upper()}` Formatına Dönüştürüldü ve Klasörlenip Ziplendi\n"
                f"- **Kaynak Dosya:** `{up_name}` · **Dönüştürülen:** [{cres['output_filename']} (.{tfmt.upper()} İndir)]({cres['url']})\n"
                f"- **ZIP Arşivi (`{zres['folder_name']}/`):** [{zres['zip_filename']} (.ZIP İndir)]({zres['url']}) ({zres['size_kb']} KB)")
    return (f"## Dosya Dönüştürme Tamamlandı (`{up_name}` -> `.{tfmt.upper()}`)\n"
            f"- **Çıktı Boyutu:** `{cres['size_kb']} KB` · **Bölüm Sayısı:** `{cres['section_count']}`\n"
            f"- **İndirme Bağlantısı:** [{cres['output_filename']} (.{tfmt.upper()} İndir)]({cres['url']})")


async def _extract_upload_context(file: UploadFile | None, prompt: str) -> str:
    if file is None or not file.filename:
        return ""
    from assistant_prep import _extract_document_bytes

    raw = await file.read()
    if not raw:
        return ""
    txt, _task, _note = _extract_document_bytes(file.filename, file.content_type or "", raw, prompt)
    return untrusted.guard(txt.strip())


async def _try_file_conversion_fastpath(
    prompt: str, file: UploadFile | None, has_file: bool, is_prompt_conv: bool
) -> StreamingResponse | None:
    import file_converter as fc

    conv_act = fc.detect_conversion_or_archive_action(prompt, file.filename if has_file and file else None)
    if not conv_act or is_prompt_conv:
        return None
    act = conv_act["action"]
    low = prompt.lower()
    if act == "extract_zip" and _cad.ZIP_INSPECT_RE.search(low) and not any(k in low for k in _EXPLICIT_ZIP_EXTRACT_CUES):
        return None
    if act == "convert" and not any(v in low for v in _PURE_CONVERT_CUES) and any(
        k in low for k in ("rapor", "sunum", "slayt", "analiz", "detaylı", "detayli")
    ):
        return None
    if act == "zip_project":
        existing_ref = any(k in low for k in ("son proje", "mevcut proje", "bu proje", "çalışma alan", "calisma alan", "workspace"))
        if not existing_ref and _cad.is_project_build_request(prompt, None) and any(v in low for v in _NEW_PROJECT_BUILD_VERBS):
            return None
        return _build_zip_project_stream(low)
    raw_upload = await file.read()  # type: ignore[union-attr]
    up_name = (file.filename or "dosya") if file else "dosya"

    async def _gen():
        try:
            out_md = _run_file_conversion_action(act, conv_act, up_name, raw_upload)
            yield sse_event({"type": "token", "content": out_md})
            yield sse_event({"type": "done", "model": "file-converter", "task_type": "dokuman"})
        except (zipfile.BadZipFile, OSError, ValueError, TypeError, KeyError, RuntimeError, ImportError) as exc:
            yield sse_event({"type": "error", "content": f"Dosya dönüştürme hatası: {exc}"})

    return StreamingResponse(_gen(), media_type=_MEDIA_SSE)


def _format_mcp_connectors_md(conns: list[dict[str, Any]]) -> str:
    if not conns:
        return (
            "## Kayıtlı Harici MCP Bağlayıcısı Yok\nSol alttaki **Kullanıcı Profili -> MCP Bağlantıları** sekmesinden "
            "harici bir MCP sunucu URL'si ve API anahtarı ekleyip **Araçları Keşfet** butonuna tıklayarak doğrudan sohbetten MCP araçlarını çalıştırabilirsiniz."
        )
    lines = ["## Bağlı Harici MCP Sunucuları ve Araçları", ""]
    for c in conns:
        key_txt = f"Tanımlı ({c['api_key_masked']})" if c["has_api_key"] else "Yok"
        lines.extend([f"### {c['name']} ({'Aktif' if c['enabled'] else 'Pasif'}) — `{c['url']}`", f"- **Durum:** {c['last_status']} · **API Anahtarı:** {key_txt}"])
        lines.extend((f"  - `{t['name']}`: {t.get('description') or 'Açıklama yok'}" for t in c["tools"][:15]) if c["tools"]
                     else ["  - Henüz keşfedilen araç yok (**Kişisel Alan -> MCP Bağlantıları -> Araçları Keşfet**)."])
        lines.append("")
    return "\n".join(lines)


def _try_mcp_fastpath(prompt: str, has_file: bool, is_prompt_conv: bool) -> StreamingResponse | None:
    lower_p = prompt.lower()
    mcp_verbs = ("araç", "arac", "listele", "bağlı", "bagli", "çalıştır", "calistir", "kullan", "çağır", "cagir", "bağlan", "baglan")
    if has_file or is_prompt_conv or "mcp" not in lower_p or not any(k in lower_p for k in mcp_verbs):
        return None
    import mcp_connector as mcpc

    async def _gen():
        try:
            conns = mcpc.list_connectors()
            matched = next((t for t in mcpc.list_enabled_tools_summary() if t["tool_name"].lower() in lower_p), None)
            if matched:
                m_args = re.search(r"\{[\s\S]*\}", prompt)
                try:
                    args = json.loads(m_args.group(0)) if m_args else {}
                except json.JSONDecodeError:
                    args = {}
                call_res = await mcpc.call_connector_tool(matched["connector_id"], matched["tool_name"], args)
                md = (
                    f"## MCP Araç Çağrısı: `{matched['connector_name']}` -> `{matched['tool_name']}`\n\n"
                    f"```json\n{json.dumps(call_res, ensure_ascii=False, indent=2)}\n```"
                )
            else:
                md = _format_mcp_connectors_md(conns)
            yield sse_event({"type": "token", "content": md})
            yield sse_event({"type": "done", "model": "mcp-connector", "task_type": "genel"})
        except (httpx.HTTPError, sqlite3.Error, OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
            yield sse_event({"type": "error", "content": f"MCP hatası: {exc}"})

    return StreamingResponse(_gen(), media_type=_MEDIA_SSE)


async def _try_rfq_zip_fastpath(prompt: str, file: UploadFile | None, has_file: bool) -> StreamingResponse | None:
    lower_p = prompt.lower()
    if not (
        has_file and file is not None and (file.filename or "").lower().endswith(".zip")
        and any(k in lower_p for k in ("rfq", "ihale", "toplu teklif", "bom", "balon", "çizim", "cizim"))
    ):
        return None
    import rfq_batch

    raw_rfq = await file.read()

    async def _gen():
        try:
            res = rfq_batch.process_rfq_zip_package(raw_rfq, customer_name="Kurumsal Musteri")
            lines = [
                f"## Toplu RFQ İhale ve Maliyet Teklif Paketi ({res.get('part_count', 0)} Parça)",
                f"- **Toplam İşleme Süresi:** `{res.get('total_cycle_hours', 0)} saat` | **10 Adet Seri Toplamı:** `{res.get('grand_total_10_tl', 0):,.2f} TL`",
            ]
            if res.get("excel_url"):
                lines.append(f"- [Toplu RFQ Excel Teklifi İndir (.xlsx)]({res['excel_url']})")
            if res.get("pdf_url"):
                lines.append(f"- [Kurumsal RFQ Teklif Mektubu İndir (.pdf)]({res['pdf_url']})")
            lines.extend(["", "| Parça | Malzeme | Çevrim (dk) | 1 Adet (TL) | 10 Adet Birim (TL) | 100 Adet Birim (TL) |", "|---|---|---|---|---|---|"])
            lines.extend(
                f"| `{b.get('part_name', '-')}` | {b.get('material', '-')} | {b.get('cycle_time_min', 0)} | "
                f"{b.get('unit_price_1_tl', 0)} | {b.get('unit_price_10_tl', 0)} | {b.get('unit_price_100_tl', 0)} |"
                for b in res.get("bom_items", [])[:30]
            )
            yield sse_event({"type": "token", "content": "\n".join(lines)})
            yield sse_event({"type": "done", "model": "cnc-ballooner", "task_type": "cnc"})
        except (zipfile.BadZipFile, OSError, ValueError, TypeError, KeyError, RuntimeError, ImportError) as exc:
            yield sse_event({"type": "error", "content": str(exc)})

    return StreamingResponse(_gen(), media_type=_MEDIA_SSE)


def _is_pptx_generation_request(prompt: str, is_prompt_conv: bool) -> bool:
    if is_prompt_conv or _PPTX_ADVICE_RE.search(prompt):
        return False
    return bool(_PPTX_NOUN_RE.search(prompt) and _PPTX_VERB_RE.search(prompt))


async def _try_pptx_council_erp_fastpath(
    prompt: str, file: UploadFile | None, has_file: bool, is_prompt_conv: bool
) -> StreamingResponse | None:
    lower_p = prompt.lower()
    if _is_pptx_generation_request(prompt, is_prompt_conv):
        extracted_ctx = await _extract_upload_context(file, prompt) if has_file else ""

        async def _pptx_gen():
            try:
                res = await _call_pptx_generator(prompt, extracted_ctx)
                lb = reply_labels.labels(prompt)
                md = [
                    f"## {res['title']} ({lb['pptx_ready']})", res["subtitle"], "",
                    f"- **{lb['theme']}:** {res['theme_name']} · **{lb['transition']}:** `{res['transition']}` · **{lb['total']}:** `{res['slide_count']} {lb['slides']}`",
                    f"- **{lb['download_pptx']}:** [{res['title']} ({res['filename']})]({res['url']})", "",
                    f"### {lb['content']}",
                ]
                for i, s in enumerate(res["slides"], start=2):
                    md.append(f"#### {lb['slide']} {i}: {s.get('title', '')}")
                    md.extend(f"- {b}" for b in (s.get("bullets") or [])[:5])
                    if s.get("key_fact"):
                        md.append(f"- **{lb['callout']}:** {s['key_fact']}")
                    md.append("")
                yield sse_event({"type": "token", "content": "\n".join(md)})
                yield sse_event({"type": "done", "model": res["model"], "task_type": "dokuman"})
            except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError, RuntimeError, ImportError) as exc:
                yield sse_event({"type": "error", "content": str(exc)})

        return StreamingResponse(_pptx_gen(), media_type=_MEDIA_SSE)

    if not has_file and any(k in lower_p for k in ("konseyde tartış", "konseyde tartis", "ajan konseyi", "çoklu ajan konsey")):
        import tool_executor as rc

        async def _council_gen():
            try:
                c_res = await rc.run_reasoning_council(prompt)
                yield sse_event({"type": "council", "council": c_res})
                final_txt = c_res.get("final_answer") or c_res.get("judge_synthesis") or json.dumps(c_res, ensure_ascii=False)
                yield sse_event({"type": "token", "content": final_txt})
                yield sse_event({"type": "done", "model": "reasoning-council", "task_type": "genel"})
            except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError, RuntimeError, ImportError) as exc:
                yield sse_event({"type": "error", "content": str(exc)})

        return StreamingResponse(_council_gen(), media_type=_MEDIA_SSE)

    if not has_file and any(k in lower_p for k in ("nesting", "fire optimizasyon", "çubuk kesim", "tezgah çizelge", "job-shop gantt")):
        return _build_erp_nesting_stream()
    return None


def _build_erp_nesting_stream() -> StreamingResponse:
    import erp_mes_scheduler as ems

    async def _gen():
        nest = ems.optimize_1d_bar_nesting(3000.0, 3.0, [{"part_id": "MIL-420", "length_mm": 420.0, "quantity": 6}, {"part_id": "BURC-185", "length_mm": 185.0, "quantity": 10}])
        jobs = [
            {"job_id": "IS-101", "due_date_min": 240, "operations": [{"op_code": "OP10", "machine": "CNC-TORNA-01", "setup_min": 15, "run_min": 35}, {"op_code": "OP20", "machine": "CNC-FREZE-01", "setup_min": 20, "run_min": 40}]},
            {"job_id": "IS-102", "due_date_min": 300, "operations": [{"op_code": "OP10", "machine": "CNC-TORNA-01", "setup_min": 10, "run_min": 25}, {"op_code": "OP20", "machine": "CNC-FREZE-01", "setup_min": 15, "run_min": 30}]},
        ]
        sched = ems.schedule_cnc_job_shop(jobs, ["CNC-TORNA-01", "CNC-FREZE-01"])
        gantt_json = json.dumps({"type": "gantt", "title": "CNC İş Atölyesi Gantt Çizelgesi (dk)", "tasks": [{"label": f"{b['job_id']} {b['op_code']}", "start": b["start_min"], "end": b["end_min"]} for b in sched.get("gantt_bars", [])]}, ensure_ascii=False)
        md = (f"## ERP / MES 1B Çubuk Fire Optimizasyonu (Nesting) ve CNC Gantt Çizelgesi\n"
              f"- **1B Çubuk Nesting:** `{nest['bar_count']}` boy çubuk · **Malzeme Verimliliği:** `%{nest['material_utilization_percent']}` · **Fire:** `%{nest['scrap_percent']}`\n"
              f"- **İş Atölyesi Toplam Süre (Makespan):** `{sched['makespan_min']} dk`\n\n```chart\n{gantt_json}\n```")
        yield sse_event({"type": "token", "content": md})
        yield sse_event({"type": "done", "model": "erp-mes-scheduler", "task_type": "cnc"})

    return StreamingResponse(_gen(), media_type=_MEDIA_SSE)


async def _try_zip_workspace_fastpath(prompt: str, file: UploadFile | None) -> StreamingResponse | None:
    if not _cad.is_zip_workspace_request(prompt, file):
        return None
    import workspace_builder as wb

    raw_zip = await file.read()  # type: ignore[union-attr]
    zname = (file.filename or "proje.zip") if file else "proje.zip"
    wants_exe = any(k in prompt.lower() for k in ("exe", "derle"))

    async def _gen():
        try:
            ws_meta, ws_tree = wb.import_zip_workspace(zname, raw_zip)
            yield sse_event({"type": "token", "content": f"### ZIP Projesi İçe Aktarıldı: **{ws_meta['name']}**\n- Çalışma alanı kimliği: `{ws_meta['id']}`\n"})
            if wants_exe:
                yield sse_event({"type": "token", "content": "**PyInstaller ile Windows .EXE derleniyor...**\n"})
                res = await wb.build_workspace_exe(ws_meta["id"])
                if res.get("ok"):
                    ws_dir = wb.safe_workspace_dir(ws_meta["id"])
                    ws_meta = {**wb.load_workspace_meta(ws_dir), "has_exe": True, "exe_name": res["exe_name"]}
                    ws_tree = wb.build_file_tree(ws_dir)
            yield sse_event({"type": "workspace", "workspace": ws_meta, "tree": ws_tree})
            yield sse_event({"type": "done", "model": "workspace-importer", "task_type": "proje"})
        except (zipfile.BadZipFile, subprocess.SubprocessError, OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
            yield sse_event({"type": "error", "content": str(exc)})

    return StreamingResponse(_gen(), media_type=_MEDIA_SSE)


async def _try_media_doc_fastpath(
    prompt: str, file: UploadFile | None, history: str, has_file: bool, is_prompt_conv: bool
) -> StreamingResponse | None:
    if is_prompt_conv:
        return None
    import chat_contracts
    import document_factory as df
    import multimodal_studio as mms

    if chat_contracts.is_chart_generation_request(prompt, has_file):
        async def _chart_gen():
            try:
                res = chat_contracts.build_svg_bar_chart(prompt)
                md = f"## Veri Grafiği Hazır\n- [SVG Grafiği İndir]({res['svg_url']})\n\n{res['svg']}"
                yield sse_event({"type": "artifact", "kind": "chart", "format": "svg", "url": res["svg_url"]})
                yield sse_event({"type": "token", "content": md})
                yield sse_event({"type": "done", "model": "chart-svg", "task_type": "grafik"})
            except (OSError, ValueError, TypeError, KeyError, ArithmeticError, RuntimeError) as exc:
                yield sse_event({"type": "error", "content": str(exc)})

        return StreamingResponse(_chart_gen(), media_type=_MEDIA_SSE)

    if mms.is_image_generation_request(prompt, has_file) or (not has_file and _img.is_image_revision(prompt, _img.parse_history(history))):
        return _img.build_image_gen_stream(prompt, history)

    full = prompt if has_file else followup.merged_request(prompt, history)
    doc_fmt = df.detect_document_request(prompt, has_file) or df.detect_document_request(full, has_file)
    if doc_fmt:
        extracted_ctx = await _extract_upload_context(file, prompt) if has_file else followup.last_answer(prompt, history)
        return _build_doc_gen_stream(full, doc_fmt, context_text=extracted_ctx)
    return _img.build_image_gen_stream(full, history) if full != prompt and mms.is_image_generation_request(full, has_file) else None


def _build_doc_gen_stream(prompt: str, doc_fmt: str, context_text: str = "") -> StreamingResponse:
    import document_factory as df

    async def _gen():
        try:
            res = await office_verify.verified(df.generate_document_deliverable(prompt, doc_fmt, context_text=context_text), doc_fmt)
            lb = reply_labels.labels(prompt)
            md = [
                f"## {res['title']} ({doc_fmt.upper()} {lb['file_ready']})", res.get("summary") or "", "",
                f"- **{lb['download']}:** [{res['title']} (.{doc_fmt} {lb['get']})]({res['url']})", "",
            ]
            headers, rows = res.get("table_headers") or [], res.get("table_rows") or []
            if headers and rows:
                md.extend([
                    "| " + " | ".join(str(h) for h in headers) + " |",
                    "|" + "|".join("---" for _ in headers) + "|",
                    *("| " + " | ".join(str(c) for c in r[: len(headers)]) + " |" for r in rows[:15]),
                ])
            if doc_fmt in ("docx", "pdf") and re.search(r"(grafik|chart|diyagram)", prompt, re.I) and chart_series([str(h) for h in headers], rows) is None:
                md.extend(["", f"> **{lb['note']}:** {lb['chart_note']}"])
            yield sse_event({"type": "artifact", "kind": "document", "format": doc_fmt, "url": res["url"]})
            yield sse_event({"type": "token", "content": "\n".join(md)})
            yield sse_event({"type": "done", "model": res["model"], "task_type": "dokuman"})
        except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError, RuntimeError, ImportError) as exc:
            yield sse_event({"type": "error", "content": str(exc)})

    return StreamingResponse(_gen(), media_type=_MEDIA_SSE)


def _format_project_evt(evt: dict[str, Any]) -> str | None:
    et = evt.get("type")
    if et == "status":
        return f"{evt['message']}\n\n"
    if et == "plan":
        ws_meta = evt["workspace"]
        flist = "\n".join(f"- `{f['path']}` - {f['purpose']}" for f in evt["files"])
        return f"### Proje Planı: **{ws_meta['name']}** ({len(evt['files'])} dosya)\n{flist}\n\n"
    if et == "file_done":
        return f"- `{evt['path']}` ({round(evt['size'] / 1024, 1)} KB)\n"
    return None


async def _maybe_build_project_exe(wb: Any, ws_meta: dict[str, Any], wants_exe: bool) -> tuple[dict[str, Any], Any, list[str]]:
    notes: list[str] = []
    ws_tree: Any = None
    if not (wants_exe and ws_meta.get("project_type") in ("game", "desktop", "cli")):
        return ws_meta, ws_tree, notes
    notes.append("\n**PyInstaller ile Windows .EXE derleniyor...**\n")
    build_res = await wb.build_workspace_exe(ws_meta["id"])
    if build_res.get("ok"):
        ws_dir = wb.safe_workspace_dir(ws_meta["id"])
        ws_meta = wb.load_workspace_meta(ws_dir)
        ws_tree = wb.build_file_tree(ws_dir)
        mb = round(build_res.get("exe_size", 0) / (1024 * 1024), 2)
        notes.append(f"**EXE hazır:** `dist/{build_res['exe_name']}` ({mb} MB)\n")
    else:
        notes.append(f"EXE derleme notu: {build_res.get('error')}\n")
    return ws_meta, ws_tree, notes


def _attach_workspace_flags(wb: Any, ws_meta: dict[str, Any], ws_tree: Any) -> dict[str, Any]:
    ws_dir = wb.safe_workspace_dir(ws_meta["id"])
    ws_meta["has_web_preview"] = (ws_dir / "index.html").is_file() or (ws_dir / "public" / "index.html").is_file()
    exe_files = list((ws_dir / "dist").glob("*.exe")) if (ws_dir / "dist").is_dir() else []
    ws_meta["has_exe"] = len(exe_files) > 0
    ws_meta["exe_name"] = exe_files[0].name if exe_files else ""
    return {"type": "workspace", "workspace": ws_meta, "tree": ws_tree or wb.build_file_tree(ws_dir)}


def _flatten_tree_paths(nodes: Any, out: list[str], depth: int = 0) -> None:
    if not isinstance(nodes, list):
        return
    for n in nodes:
        if not isinstance(n, dict):
            continue
        p = str(n.get("path") or n.get("name") or "").strip()
        if n.get("type") in ("dir", "folder"):
            if p:
                out.append(f"{'  ' * depth}- `{p}/`")
            _flatten_tree_paths(n.get("children"), out, depth + 1)
        elif p:
            out.append(f"{'  ' * depth}- `{p}`")


def _format_project_summary_links(ws_meta: dict[str, Any], ws_tree: Any, prompt: str, failed: str = "") -> str:
    ws_id = ws_meta["id"]
    lines = [
        "",
        f"### {'Proje oluşturuldu ama TESTİ GEÇEMEDİ' if failed else 'Proje Hazır'}: **{ws_meta.get('name', ws_id)}**",
        *([f"> {failed}", "> Sohbete hatayı yazarak düzelttirebilirsin."] if failed else []),
        f"- **ZIP İndirme:** [Projeyi İndir (.ZIP)](/api/studio/workspaces/{ws_id}/download.zip)",
    ]
    if ws_meta.get("has_web_preview"):
        lines.append(f"- **Canlı Önizleme:** [Tarayıcıda Canlı Önizle](/api/studio/workspaces/{ws_id}/preview/index.html)")
    if ws_meta.get("has_exe") and ws_meta.get("exe_name"):
        lines.append(f"- **Windows EXE:** `dist/{ws_meta['exe_name']}`")
    tree_lines: list[str] = []
    _flatten_tree_paths(ws_tree, tree_lines)
    low = prompt.lower()
    wants_tree = any(k in low for k in ("zip", "klasör", "klasor", "dizin", "folder", "yapı", "yapi", "dosya"))
    if tree_lines and (wants_tree or len(tree_lines) <= 25):
        lines.extend(["", "**Oluşturulan Klasör ve Dosya Yapısı:**", *tree_lines[:40]])
    return "\n".join(lines) + "\n"


def _verdict(evt: dict[str, Any]) -> tuple[str, list[str]]:
    """(why the run test failed or "", extra chat notes) from the warnings of a finished generation."""
    warnings = [str(w) for w in evt.get("warnings") or []]
    failed = next((w[w.index("Otomatik çalıştırma"):] for w in warnings if "Otomatik çalıştırma testi hata" in w), "")
    return failed, [f"\n> {w}\n" for w in warnings if w.startswith(("Güvenlik taraması", "Görsel denetim", "Tasarım notu", "Görsel model"))]


def _try_project_build_fastpath(prompt: str, file: UploadFile | None, history: str, is_prompt_conv: bool) -> StreamingResponse | None:
    if is_prompt_conv or not _cad.is_project_build_request(prompt, file):
        return None
    import workspace_builder as wb

    prompt = followup.merged_request(prompt, history)
    detected_type, wants_exe = _cad.detect_project_type(prompt)

    async def _gen():
        ws_meta: dict[str, Any] | None = None
        ws_tree: Any = None
        failed = ""
        used_model = config.STUDIO_CODER_MODEL
        try:
            async for evt in run_trace.traced(project_flow.stream_generate(prompt.strip(), project_type=detected_type), prompt):
                if (msg := _format_project_evt(evt)):
                    yield sse_event({"type": "token", "content": msg})
                if evt.get("type") == "plan":
                    ws_meta = evt["workspace"]
                    used_model = (ws_meta or {}).get("model") or used_model
                elif evt.get("type") == "done":
                    ws_meta, ws_tree = evt["workspace"], evt["tree"]
                    failed, notes = _verdict(evt)
                    yield sse_event({"type": "token", "content": "".join(notes)})
            if ws_meta:
                ws_meta, exe_tree, exe_notes = await _maybe_build_project_exe(wb, ws_meta, wants_exe)
                for note in exe_notes:
                    yield sse_event({"type": "token", "content": note})
                ws_evt = _attach_workspace_flags(wb, ws_meta, exe_tree or ws_tree)
                yield sse_event({"type": "token", "content": _format_project_summary_links(ws_evt["workspace"], ws_evt["tree"], prompt, failed)})
                yield sse_event(ws_evt)
            yield sse_event({"type": "done", "model": used_model, "task_type": "proje"})
        except (httpx.HTTPError, subprocess.SubprocessError, OSError, ValueError, TypeError, KeyError, RuntimeError, ImportError) as exc:
            yield sse_event({"type": "error", "content": str(exc)})

    return StreamingResponse(_gen(), media_type=_MEDIA_SSE)


def _try_guard_fastpaths(prompt: str, has_file: bool) -> StreamingResponse | None:
    """Instruction-extraction refusals and exact answers (counting, sorting, tiny Python) that need no model."""
    if (refusal := chat_guard.refusal_for(prompt)) is not None:
        return single_token_stream(refusal, "guard-policy", "guard")
    if not has_file and (exact := text_tools.answer(prompt)) is not None:
        return single_token_stream(exact, "text-tools", "hesaplama")
    return None


async def dispatch_chat_fastpath(
    prompt: str, file: UploadFile | None, history: str, is_prompt_conv: bool
) -> StreamingResponse | None:
    """Try deterministic/tool SSE fast paths before falling back to general LLM chat."""
    has_file = bool(file is not None and file.filename)
    if (early := _try_guard_fastpaths(prompt, has_file) or revise_chat.fastpath(prompt, history, has_file)) is not None:
        return early
    if (res := _try_abstain_fastpath(prompt, history, has_file)) is not None:
        return res
    if not is_prompt_conv and (question := _clarify.clarifying_question(prompt, history, has_file)):
        return single_token_stream(question, "clarify-policy", "clarify")
    if _cad.is_3d_cad_request(file):
        return single_token_stream(await _cad.run_3d_cad_cam_from_chat(file, prompt), "cnc-ballooner", "cad3d")  # type: ignore[arg-type]
    full = prompt if has_file or is_prompt_conv else followup.merged_request(prompt, history)
    for maybe in (
        await gcode_chat.fastpath(full, has_file),
        await reasoning_mode.fastpath(prompt, has_file),
        await _try_file_conversion_fastpath(prompt, file, has_file, is_prompt_conv),
        _try_mcp_fastpath(prompt, has_file, is_prompt_conv),
        await _try_rfq_zip_fastpath(prompt, file, has_file),
        await _try_pptx_council_erp_fastpath(full, file, has_file, is_prompt_conv),
    ):
        if maybe is not None:
            return maybe
    if _cad.is_cnc_balloon_request(prompt, file):
        return single_token_stream(await _cad.run_cnc_balloon_from_chat(file), "cnc-ballooner", "cnc")  # type: ignore[arg-type]
    for maybe in (
        await _try_zip_workspace_fastpath(prompt, file),
        await _try_media_doc_fastpath(prompt, file, history, has_file, is_prompt_conv),
        _try_project_build_fastpath(prompt, file, history, is_prompt_conv),
    ):
        if maybe is not None:
            return maybe
    return None
