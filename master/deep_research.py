"""Cluster A (`[M10]` & `[M11]`): Deep Research Engine & Agency-Grade AI PowerPoint (.pptx) Builder.

- `decompose_research_questions`: breaks a complex topic into structured analytical dimensions.
- `build_pptx_presentation`: creates a themed, multi-layout OpenXML `.pptx` deck via `python-pptx`
  with dynamic cover sizing, KPI grids, native editable charts and tables, two-column comparisons,
  closing action slides, speaker notes on every slide, Turkish-safe typography, and ECMA-376 valid
  PowerPoint slide transitions (`fade`, `push`, `wipe`, `cover`, `split`).
- `generate_ai_pptx_presentation`: researches the user's topic (plus optional uploaded document
  context) via local Ollama LLM and compiles a complete themed `.pptx` file.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from pptx import Presentation
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls
from pptx.util import Inches

import deck_plan
import json_repair
import multimodal_studio as mms
from deck_layouts import (  # noqa: F401 - re-exported: other modules and tests use these names from deep_research
    _FONT_FAMILY,
    _LABELS,
    _add_box,
    _add_run,
    _add_textbox,
    _auto_notes,
    _bullet_metrics,
    _contrast_rgb,
    _DeckColors,
    _fill_bullets,
    _hex_rgb,
    _parse_chart_data,
    _parse_table_data,
    _prep_tf,
    _render_bottom_insight,
    _render_bullets_layout,
    _render_callout_panel,
    _render_chart_layout,
    _render_closing_layout,
    _render_content_slide,
    _render_cover_slide,
    _render_kpi_grid,
    _render_slide_chrome,
    _render_table_layout,
    _render_two_column,
    _resolve_colors,
    _set_speaker_notes,
    _SlideCtx,
    _tr_upper,
)
from pptx_guard import clean_spec
from prompt_loader import load_prompt

_TRANSITIONS = ("fade", "push", "wipe", "cover", "split")
_WORD_COUNTS: tuple[tuple[str, int], ...] = (
    ("on beş", 15), ("on bes", 15), ("on dört", 14), ("on dort", 14), ("on üç", 13), ("on uc", 13),
    ("on iki", 12), ("on bir", 11), ("fifteen", 15), ("fourteen", 14), ("thirteen", 13), ("twelve", 12),
    ("eleven", 11), ("dokuz", 9), ("sekiz", 8), ("yedi", 7), ("altı", 6), ("alti", 6), ("beş", 5),
    ("bes", 5), ("dört", 4), ("dort", 4), ("üç", 3), ("uc", 3), ("on", 10), ("ten", 10), ("nine", 9),
    ("eight", 8), ("seven", 7), ("six", 6), ("five", 5), ("four", 4), ("three", 3),
)
TOPIC_THEMES: dict[str, dict[str, str]] = {
    "history": {"name": "Tarih ve Medeniyet (Antik Altın & Gece Laciverti)", "bg": "141824", "card": "1E2436", "accent": "D97706", "accent2": "F59E0B", "text": "F8FAFC", "muted": "CBD5E1", "transition": "fade"},
    "tech": {"name": "Teknoloji ve Bilim (Koyu Uzay & Siyan)", "bg": "0B1120", "card": "162033", "accent": "06B6D4", "accent2": "6366F1", "text": "F8FAFC", "muted": "CBD5E1", "transition": "push"},
    "nature": {"name": "Doğa ve Sağlık (Orman Yeşili & Zümrüt)", "bg": "0D1F1A", "card": "163029", "accent": "10B981", "accent2": "34D399", "text": "F0FDF4", "muted": "BBF7D0", "transition": "wipe"},
    "light": {"name": "Aydınlık Kurumsal (Krem & Çivit)", "bg": "F8FAFC", "card": "FFFFFF", "accent": "4F46E5", "accent2": "0EA5E9", "text": "0F172A", "muted": "475569", "transition": "fade"},
    "corporate": {"name": "Modern Kurumsal (Koyu Arduvaz & İndigo)", "bg": "0F172A", "card": "1E293B", "accent": "4F46E5", "accent2": "38BDF8", "text": "F8FAFC", "muted": "CBD5E1", "transition": "cover"},
}


def _detect_language(text: str, explicit: str | None = None) -> str:
    if explicit and explicit.strip().lower() in ("tr", "en"):
        return explicit.strip().lower()
    low = (text or "").lower()
    if any(k in low for k in ("in english", "ingilizce", "english presentation", "english deck")):
        return "en"
    if any(ch in text for ch in "çğıöşüÇĞİÖŞÜ") or re.search(
        r"\b(?:sunum|slayt|hazırla|hakkında|araştırma|özet|bölüm|ve|için|ile)\b", low
    ):
        return "tr"
    if re.search(r"\b(?:presentation|slides?|deck|report|overview|strategy|create|about|the|and|for)\b", low):
        return "en"
    return "tr"


def _parse_slide_count(prompt: str) -> int:
    """Parse requested total slide count (3..15) and return content slide count (2..14)."""
    low = (prompt or "").lower()
    unit = r"(?:(?:adet|tane)\s*)?(?:slayt\w*|sayfa\w*|slides?)"
    m_num = re.search(rf"\b(\d{{1,2}})[\s-]*{unit}\b", low)
    if m_num:
        return max(2, min(14, int(m_num.group(1)) - 1))
    for word, val in _WORD_COUNTS:
        if re.search(rf"\b{re.escape(word)}\s+{unit}\b", low):
            return max(2, min(14, val - 1))
    return 6


def _pick_theme_for_topic(prompt: str) -> dict[str, str]:
    low = (prompt or "").lower()
    rules = (
        ("light", ("açık tema", "acik tema", "beyaz arka plan", "aydınlık", "light theme", "white background")),
        ("history", ("tarih", "medeniyet", "uygarlık", "antik", "osmanlı", "insanlık", "savaş", "arkeoloji", "sanat", "history", "civilization", "ancient")),
        ("nature", ("doğa", "çevre", "iklim", "biyoloji", "sağlık", "tıp", "tarım", "enerji", "yeşil", "nature", "climate", "health", "medicine", "sustainability")),
        ("tech", ("yapay zeka", "yazılım", "bilgisayar", "uzay", "fizik", "robot", "teknoloji", "siber", "veri", "software", "cyber", "cloud", "quantum", "technology", "machine learning")),
    )
    for key, terms in rules:
        if any(k in low for k in terms):
            return dict(TOPIC_THEMES[key])
    return dict(TOPIC_THEMES["corporate"])


def _apply_slide_transition(slide: Any, kind: str) -> None:
    """Insert <p:transition> at ECMA-376 valid position (before <p:timing> / <p:extLst>)."""
    sld = slide._element
    for child in list(sld):
        if child.tag.rsplit("}", 1)[-1] == "transition":
            sld.remove(child)
    tags = {"push": '<p:push dir="l"/>', "wipe": '<p:wipe dir="r"/>', "cover": '<p:cover dir="l"/>', "split": '<p:split orient="horz" dir="out"/>'}
    trans_el = parse_xml(f'<p:transition {nsdecls("p")} spd="med">{tags.get((kind or "fade").strip().lower(), "<p:fade/>")}</p:transition>')
    for i, child in enumerate(sld):
        if child.tag.rsplit("}", 1)[-1] in ("timing", "extLst"):
            sld.insert(i, trans_el)
            return
    sld.append(trans_el)


def decompose_research_questions(topic: str) -> list[str]:
    """Decompose a broad research query into 4 orthogonal analytical dimensions."""
    clean = topic.strip().rstrip("?.!")
    return [
        f"1. {clean} - Temel Kavramlar, Tarihsel Gelişim ve Arka Plan",
        f"2. {clean} - Temel Dönüm Noktaları, Bulgular ve Karşılaştırmalı Analiz",
        f"3. {clean} - Güncel Etkiler, Fırsatlar ve Kritik Sorunlar",
        f"4. {clean} - Gelecek Perspektifi ve Özet Çıkarımlar",
    ]


def build_pptx_presentation(
    title: str,
    subtitle: str,
    slides: list[dict[str, Any]],
    out_path: Path | None = None,
    theme: dict[str, str] | None = None,
    **opts: Any,
) -> Path:
    """Build a 16:9 Microsoft PowerPoint-compliant multi-layout `.pptx` deck using `python-pptx`."""
    language: str | None = opts.get("language")
    cover_notes = str(opts.get("cover_notes") or "")
    if out_path is None:
        out_path = mms.media_dir() / f"pres-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}.pptx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lang, colors = _detect_language(f"{title} {subtitle}", explicit=language), _resolve_colors(theme or _pick_theme_for_topic(title))
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    cover_sub = subtitle or _LABELS[lang]["cover_sub"]
    all_slides: list[dict[str, Any]] = [{"_cover": True, "title": title, "subtitle": cover_sub}, *(slides or [])]
    for idx, sdata in enumerate(all_slides, start=1):
        slide: Any = prs.slides.add_slide(prs.slide_layouts[6])
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = colors.bg
        _apply_slide_transition(slide, colors.transition)
        ctx = _SlideCtx(deck_title=title, idx=idx, total=len(all_slides), lang=lang, colors=colors)
        if sdata.get("_cover"):
            _render_cover_slide(slide, str(sdata.get("title") or title), str(sdata.get("subtitle") or cover_sub), ctx, cover_notes)
        else:
            _render_content_slide(slide, sdata, ctx)
    prs.save(str(out_path))
    return out_path


_PLACEHOLDER_RE = re.compile(r"<[^<>\n]{2,40}>")


def _slide_has_content(sl: dict[str, Any]) -> bool:
    cols = sl.get("columns") or {}
    return bool(sl.get("bullets") or cols.get("left_bullets") or cols.get("right_bullets") or sl.get("kpis") or sl.get("table") or sl.get("chart"))


def _slides_are_real(spec: dict[str, Any], prompt: str) -> bool:
    """A usable deck has several slides with their own content; slides that just repeat the request or keep schema placeholders are rejected."""
    slides = spec.get("slides")
    if not isinstance(slides, list) or len(slides) < 3 or _PLACEHOLDER_RE.search(json.dumps(slides, ensure_ascii=False).replace("<br>", "")):
        return False  # an <angle-bracket> field means the model copied the schema placeholders
    echo = " ".join(prompt.lower().split())[:40]
    filled = 0
    for sl in slides:
        if not isinstance(sl, dict) or not str(sl.get("title") or "").strip():
            return False
        bullets = [str(x) for x in (sl.get("bullets") or [])] + [str(x) for x in ((sl.get("columns") or {}).get("left_bullets") or [])]
        if any(echo and echo in " ".join(x.lower().split()) for x in bullets):
            return False
        filled += 1 if _slide_has_content(sl) else 0
    return filled >= max(3, len(slides) - 1)


async def _fetch_pptx_spec(sys_prompt: str, user_msg: str, model: str, prompt: str = "") -> dict[str, Any]:
    """Ask the model for the deck outline; one retry. Returns {} when no usable content came back (never a made-up deck)."""
    import gateway

    for attempt in (1, 2, 3):
        try:
            res = await gateway.default_client.chat(
                [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_msg}],
                model=model, profile="analytic", num_predict=4200, timeout_s=480.0, feature="deep_research", max_retries=0,
            )
            parsed = json_repair.loads_top(res.content)
            if parsed and _slides_are_real(parsed, prompt):
                return parsed
            logging.getLogger(__name__).warning("pptx outline attempt %s unusable", attempt)
        except (httpx.HTTPError, OSError, RuntimeError, ValueError, TypeError, KeyError, ImportError) as exc:
            logging.getLogger(__name__).warning("pptx outline attempt %s failed: %s", attempt, exc)
    return {}


async def generate_ai_pptx_presentation(prompt: str, context_text: str = "") -> dict[str, Any]:
    """Research the user's topic (plus optional document context) via Ollama LLM and build a `.pptx` deck."""
    model, theme, lang = await mms.pick_best_model("deep"), _pick_theme_for_topic(prompt), _detect_language(prompt)
    sys_prompt = load_prompt("b3_deep_research_pptx_system.txt").replace("{slide_count}", str(_parse_slide_count(prompt)))
    user_msg = prompt.strip()
    if context_text and context_text.strip():
        user_msg += f"\n\n[SOURCE DOCUMENT CONTEXT - ground facts, metrics, tables, and charts in this data]\n{context_text.strip()[:12000]}"

    spec: dict[str, Any] = {
        "language": lang, "title": prompt.strip()[:72], "subtitle": _LABELS[lang]["cover_sub"],
        "cover_notes": "", "transition": theme["transition"], "slides": [],
    }
    count = _parse_slide_count(prompt)
    planned = deck_plan.request_note(count, user_msg)
    raw = await _fetch_pptx_spec(sys_prompt, user_msg + planned, model, prompt)
    spec.update(clean_spec(raw, user_msg, count))
    spec["slides"] = deck_plan.apply(spec.get("slides") or [], deck_plan.layout_plan(count, user_msg))
    final_lang = _detect_language(prompt, explicit=str(spec.get("language") or ""))
    if not spec.get("slides"):
        raise RuntimeError("Sunumun içeriğini üretemedim (model yanıt vermedi ya da geçerli bir slayt planı döndürmedi). Boş ya da isteğini kopyalayan bir sunum vermemek için dosya oluşturmadım; lütfen tekrar dener misin? Konuyu biraz daha açarsan (kaç slayt, hangi dönem/odak) sonuç daha iyi olur.")
    if spec.get("transition") in _TRANSITIONS:
        theme["transition"] = str(spec["transition"])

    deck_title, deck_sub = str(spec.get("title") or prompt[:70]), str(spec.get("subtitle") or _LABELS[final_lang]["cover_sub"])
    out_path = build_pptx_presentation(
        title=deck_title, subtitle=deck_sub, slides=spec["slides"], theme=theme,
        language=final_lang, cover_notes=str(spec.get("cover_notes") or ""),
    )
    return {
        "title": deck_title, "subtitle": deck_sub, "theme_name": theme["name"], "transition": theme["transition"],
        "slides": spec["slides"], "slide_count": len(spec["slides"]) + 1, "model": model,
        "filename": out_path.name, "url": f"/api/assistant/media/{out_path.name}",
    }
