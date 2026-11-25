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
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls
from pptx.util import Inches, Pt

import multimodal_studio as mms
from prompt_loader import load_prompt

_FONT_FAMILY = "Calibri"  # Cross-platform Office standard (fallback: DejaVu Sans / Arial)
_TRANSITIONS = ("fade", "push", "wipe", "cover", "split")
_WORD_COUNTS: tuple[tuple[str, int], ...] = (
    ("on beş", 15), ("on bes", 15), ("on dört", 14), ("on dort", 14), ("on üç", 13), ("on uc", 13),
    ("on iki", 12), ("on bir", 11), ("fifteen", 15), ("fourteen", 14), ("thirteen", 13), ("twelve", 12),
    ("eleven", 11), ("dokuz", 9), ("sekiz", 8), ("yedi", 7), ("altı", 6), ("alti", 6), ("beş", 5),
    ("bes", 5), ("dört", 4), ("dort", 4), ("üç", 3), ("uc", 3), ("on", 10), ("ten", 10), ("nine", 9),
    ("eight", 8), ("seven", 7), ("six", 6), ("five", 5), ("four", 4), ("three", 3),
)
_LABELS: dict[str, dict[str, str]] = {
    "tr": {
        "slide": "Slayt", "key_insight": "ÖNEMLİ BULGU", "section": "BÖLÜM",
        "cover_badge": "YAPAY ZEKA ARAŞTIRMA SUNUMU", "cover_sub": "Yapay Zeka Araştırma Sunumu",
        "left_col": "TEMEL EKSEN", "right_col": "KARŞILAŞTIRMALI EKSEN",
        "closing_kicker": "SONUÇ VE EYLEM PLANI", "takeaways": "ÖNE ÇIKAN ÇIKARIMLAR",
    },
    "en": {
        "slide": "Slide", "key_insight": "KEY INSIGHT", "section": "SECTION",
        "cover_badge": "AI RESEARCH BRIEFING", "cover_sub": "AI Research Presentation",
        "left_col": "PRIMARY AXIS", "right_col": "COMPARATIVE AXIS",
        "closing_kicker": "CONCLUSION & NEXT STEPS", "takeaways": "KEY TAKEAWAYS",
    },
}
TOPIC_THEMES: dict[str, dict[str, str]] = {
    "history": {"name": "Tarih ve Medeniyet (Antik Altın & Gece Laciverti)", "bg": "141824", "card": "1E2436", "accent": "D97706", "accent2": "F59E0B", "text": "F8FAFC", "muted": "CBD5E1", "transition": "fade"},
    "tech": {"name": "Teknoloji ve Bilim (Koyu Uzay & Siyan)", "bg": "0B1120", "card": "162033", "accent": "06B6D4", "accent2": "6366F1", "text": "F8FAFC", "muted": "CBD5E1", "transition": "push"},
    "nature": {"name": "Doğa ve Sağlık (Orman Yeşili & Zümrüt)", "bg": "0D1F1A", "card": "163029", "accent": "10B981", "accent2": "34D399", "text": "F0FDF4", "muted": "BBF7D0", "transition": "wipe"},
    "light": {"name": "Aydınlık Kurumsal (Krem & Çivit)", "bg": "F8FAFC", "card": "FFFFFF", "accent": "4F46E5", "accent2": "0EA5E9", "text": "0F172A", "muted": "475569", "transition": "fade"},
    "corporate": {"name": "Modern Kurumsal (Koyu Arduvaz & İndigo)", "bg": "0F172A", "card": "1E293B", "accent": "4F46E5", "accent2": "38BDF8", "text": "F8FAFC", "muted": "CBD5E1", "transition": "cover"},
}


@dataclass(frozen=True)
class _DeckColors:
    bg: RGBColor
    card: RGBColor
    alt_row: RGBColor
    accent: RGBColor
    accent2: RGBColor
    text: RGBColor
    muted: RGBColor
    transition: str


@dataclass(frozen=True)
class _SlideCtx:
    deck_title: str
    idx: int
    total: int
    lang: str
    colors: _DeckColors


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


def _tr_upper(text: str, lang: str = "tr") -> str:
    s = text or ""
    return s.replace("i", "İ").replace("ı", "I").upper() if lang == "tr" else s.upper()


def _parse_slide_count(prompt: str) -> int:
    """Parse requested total slide count (3..15) and return content slide count (2..14)."""
    low = (prompt or "").lower()
    unit = r"(?:adet|tane|sayfalık|slaytlık)?\s*(?:slayt\w*|sayfa\w*|slides?)"
    m_num = re.search(rf"\b(\d{{1,2}})\s*{unit}\b", low)
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


def _hex_rgb(val: Any, fallback: str) -> RGBColor:
    s = re.sub(r"[^0-9A-Fa-f]", "", str(val or ""))
    hx = s.upper() if len(s) == 6 else fallback
    return RGBColor(int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16))


def _contrast_rgb(color: RGBColor) -> RGBColor:
    return RGBColor(15, 23, 42) if (0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]) > 165 else RGBColor(248, 250, 252)


def _resolve_colors(pal: dict[str, str]) -> _DeckColors:
    bg, card = _hex_rgb(pal.get("bg"), "0F172A"), _hex_rgb(pal.get("card"), "1E293B")
    alt = RGBColor(int((bg[0] + card[0]) * 0.5), int((bg[1] + card[1]) * 0.5), int((bg[2] + card[2]) * 0.5))
    return _DeckColors(
        bg=bg, card=card, alt_row=alt,
        accent=_hex_rgb(pal.get("accent"), "4F46E5"), accent2=_hex_rgb(pal.get("accent2"), "38BDF8"),
        text=_hex_rgb(pal.get("text"), "F8FAFC"), muted=_hex_rgb(pal.get("muted"), "CBD5E1"),
        transition=(pal.get("transition") or "fade"),
    )


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


def _set_speaker_notes(slide: Any, text: str) -> None:
    notes_tf = slide.notes_slide.notes_text_frame
    if notes_tf is not None:
        notes_tf.text = text.strip()


def _auto_notes(title: str, bullets: list[str], key_fact: str, lang: str) -> str:
    lead = bullets[0].rstrip(".") if bullets else title
    if lang == "en":
        extra = f" Emphasize the key takeaway: {key_fact}." if key_fact else " Connect these findings to audience goals."
        return f"On this slide covering {title}, walk the audience through {lead}.{extra}"
    extra = f" Özellikle şu kritik bulguyu vurgulayın: {key_fact}." if key_fact else " Bu bulguları sunumun ana hedefiyle ilişkilendirin."
    return f"{title} başlıklı bu slaytta dinleyicilere öncelikle {lead} noktasını aktarın.{extra}"


def _bullet_metrics(bullets: list[str], wide: bool) -> tuple[float, float]:
    cpl = 66 if wide else 42
    lines = sum(max(1, (len(b) + cpl - 1) // cpl) for b in bullets) + len(bullets) * 0.55
    for cap, pt, sp in ((8, 16.0, 10.0), (12, 14.5, 8.0), (16, 13.0, 6.0), (21, 11.5, 4.5)):
        if lines <= cap:
            return (pt, sp)
    return (10.5, 3.5)


def _add_run(p: Any, text: str, size_pt: float, color: RGBColor, *, bold: bool = False) -> None:
    r = p.add_run()
    r.text, r.font.name, r.font.size, r.font.bold, r.font.color.rgb = text, _FONT_FAMILY, Pt(size_pt), bold, color


def _prep_tf(tf: Any, lr: tuple[float, float], tb: tuple[float, float], *, middle: bool = False) -> Any:
    tf.word_wrap = True
    tf.margin_left, tf.margin_right = Inches(lr[0]), Inches(lr[1])
    tf.margin_top, tf.margin_bottom = Inches(tb[0]), Inches(tb[1])
    if middle:
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    return tf


def _add_box(
    slide: Any, shape: MSO_SHAPE, rect: tuple[float, float, float, float],
    fill: RGBColor, **opts: Any,
) -> Any:
    x, y, w, h = rect
    box: Any = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    box.fill.solid()
    box.fill.fore_color.rgb = fill
    border: RGBColor | None = opts.get("border")
    if border is None:
        box.line.fill.background()
    else:
        box.line.color.rgb, box.line.width = border, Pt(float(opts.get("border_pt", 1.25)))
    return box


def _add_textbox(
    slide: Any, rect: tuple[float, float, float, float], text: str,
    size_pt: float, color: RGBColor, **opts: Any,
) -> Any:
    x, y, w, h = rect
    tf = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame
    tf.word_wrap = True
    _add_run(tf.paragraphs[0], text, size_pt, color, bold=bool(opts.get("bold", False)))
    return tf


def _fill_bullets(tf: Any, items: list[str], font_pt: float, space_pt: float, color: RGBColor, **opts: Any) -> None:
    append = bool(opts.get("append", False))
    for bi, btxt in enumerate(items):
        pb = tf.add_paragraph() if (append or bi > 0) else tf.paragraphs[0]
        pb.space_after = Pt(space_pt)
        _add_run(pb, f"\u2022  {btxt}", font_pt, color)


def decompose_research_questions(topic: str) -> list[str]:
    """Decompose a broad research query into 4 orthogonal analytical dimensions."""
    clean = topic.strip().rstrip("?.!")
    return [
        f"1. {clean} - Temel Kavramlar, Tarihsel Gelişim ve Arka Plan",
        f"2. {clean} - Temel Dönüm Noktaları, Bulgular ve Karşılaştırmalı Analiz",
        f"3. {clean} - Güncel Etkiler, Fırsatlar ve Kritik Sorunlar",
        f"4. {clean} - Gelecek Perspektifi ve Özet Çıkarımlar",
    ]


def _render_cover_slide(slide: Any, title: str, subtitle: str, ctx: _SlideCtx, notes: str) -> None:
    c, lbl = ctx.colors, _LABELS[ctx.lang]
    _add_box(slide, MSO_SHAPE.RECTANGLE, (0.0, 0.0, 0.36, 7.5), c.accent)
    _add_box(slide, MSO_SHAPE.RECTANGLE, (0.36, 0.0, 0.08, 7.5), c.accent2)
    _add_box(slide, MSO_SHAPE.ROUNDED_RECTANGLE, (1.05, 1.05, 11.25, 5.4), c.card, border=c.accent, border_pt=1.5)
    badge = _add_box(slide, MSO_SHAPE.ROUNDED_RECTANGLE, (1.55, 1.5, 4.1, 0.42), c.accent)
    tf_b = _prep_tf(badge.text_frame, (0.16, 0.16), (0.04, 0.04), middle=True)
    _add_run(tf_b.paragraphs[0], _tr_upper(lbl["cover_badge"], ctx.lang), 10.5, _contrast_rgb(c.accent), bold=True)
    _add_box(slide, MSO_SHAPE.RECTANGLE, (1.55, 2.12, 1.9, 0.08), c.accent2)

    title_pt = 38.0 if len(title) <= 32 else (32.0 if len(title) <= 45 else (26.0 if len(title) <= 68 else 22.0))
    _add_textbox(slide, (1.55, 2.35, 10.25, 1.95), title, title_pt, c.text, bold=True)
    _add_textbox(slide, (1.55, 4.45, 10.25, 1.2), subtitle, 18.0 if len(subtitle) <= 105 else 15.0, c.muted)
    _add_textbox(slide, (1.55, 5.88, 10.25, 0.36), f"{datetime.now(UTC).strftime('%Y-%m-%d')}   |   {ctx.total} {lbl['slide']}", 10.5, c.muted)

    default_note = (
        f"Welcome to {title}. {subtitle}. Across {ctx.total} slides, we cover key insights and action items."
        if ctx.lang == "en"
        else f"{title} sunumuna hoş geldiniz. {subtitle}. Toplam {ctx.total} slaytta temel bulguları ve stratejik çıkarımları ele alacağız."
    )
    _set_speaker_notes(slide, notes or default_note)


def _render_slide_chrome(slide: Any, kicker: str, title: str, ctx: _SlideCtx) -> None:
    c, lbl = ctx.colors, _LABELS[ctx.lang]
    _add_box(slide, MSO_SHAPE.RECTANGLE, (0.0, 0.0, 13.333, 0.14), c.accent)
    _add_textbox(slide, (0.65, 0.28, 10.5, 0.34), _tr_upper(kicker, ctx.lang), 11.5, c.accent2, bold=True)
    title_pt = 26.0 if len(title) <= 46 else (22.0 if len(title) <= 72 else 19.0)
    _add_textbox(slide, (0.65, 0.62, 12.03, 0.86), title, title_pt, c.text, bold=True)
    _add_box(slide, MSO_SHAPE.RECTANGLE, (0.65, 1.54, 12.03, 0.03), c.accent)
    _add_textbox(slide, (0.65, 6.95, 12.03, 0.34), f"{ctx.deck_title}   |   {lbl['slide']} {ctx.idx} / {ctx.total}", 10.0, c.muted)


def _render_bottom_insight(slide: Any, key_fact: str, ctx: _SlideCtx) -> None:
    c, lbl = ctx.colors, _LABELS[ctx.lang]
    bar = _add_box(slide, MSO_SHAPE.ROUNDED_RECTANGLE, (0.65, 5.96, 12.03, 0.76), c.card, border=c.accent2)
    _add_box(slide, MSO_SHAPE.RECTANGLE, (0.65, 5.96, 0.12, 0.76), c.accent2)
    tf = _prep_tf(bar.text_frame, (0.28, 0.22), (0.06, 0.06), middle=True)
    _add_run(tf.paragraphs[0], f"{lbl['key_insight']}:  ", 11.5, c.accent2, bold=True)
    _add_run(tf.paragraphs[0], key_fact, 12.5 if len(key_fact) <= 125 else 11.0, c.text)


def _render_callout_panel(
    slide: Any, key_fact: str, bullets: list[str], rect: tuple[float, float, float, float], ctx: _SlideCtx
) -> None:
    c, lbl = ctx.colors, _LABELS[ctx.lang]
    card = _add_box(slide, MSO_SHAPE.ROUNDED_RECTANGLE, rect, c.card, border=c.accent2, border_pt=1.5)
    tf = _prep_tf(card.text_frame, (0.24, 0.22), (0.22, 0.18))
    tf.paragraphs[0].space_after = Pt(10)
    _add_run(tf.paragraphs[0], lbl["key_insight"], 11.5, c.accent2, bold=True)
    if key_fact:
        pf = tf.add_paragraph()
        pf.space_after = Pt(10)
        _add_run(pf, key_fact, 15.0 if len(key_fact) <= 110 else (13.0 if len(key_fact) <= 185 else 11.5), c.text, bold=bool(bullets))
    if bullets:
        b_pt, sp = _bullet_metrics(bullets[:4], wide=False)
        _fill_bullets(tf, bullets[:4], min(b_pt, 12.5), min(sp, 6.5), c.muted, append=True)


def _render_bullets_layout(slide: Any, bullets: list[str], key_fact: str, ctx: _SlideCtx) -> None:
    c, has_callout = ctx.colors, bool(key_fact)
    card_w = 7.75 if has_callout else 12.03
    card = _add_box(slide, MSO_SHAPE.ROUNDED_RECTANGLE, (0.65, 1.76, card_w, 4.96), c.card)
    _add_box(slide, MSO_SHAPE.RECTANGLE, (0.65, 1.76, card_w, 0.08), c.accent)
    tf = _prep_tf(card.text_frame, (0.32, 0.28), (0.28, 0.22))
    b_pt, sp = _bullet_metrics(bullets[:6], wide=not has_callout)
    _fill_bullets(tf, bullets[:6], b_pt, sp, c.text)
    if has_callout:
        _render_callout_panel(slide, key_fact, [], (8.65, 1.76, 4.03, 4.96), ctx)


def _render_kpi_grid(slide: Any, kpis: list[dict[str, Any]], bullets: list[str], key_fact: str, ctx: _SlideCtx) -> None:
    c, items, gap = ctx.colors, kpis[:4], 0.24
    card_w = (12.03 - gap * (len(items) - 1)) / len(items)
    for i, kpi in enumerate(items):
        x = 0.65 + i * (card_w + gap)
        val, label, delta = str(kpi.get("value") or "-")[:18], str(kpi.get("label") or "")[:44], str(kpi.get("delta") or "").strip()[:24]
        bar_col = c.accent if i % 2 == 0 else c.accent2
        _add_box(slide, MSO_SHAPE.ROUNDED_RECTANGLE, (x, 1.76, card_w, 2.22), c.card, border=bar_col, border_pt=1.1)
        _add_box(slide, MSO_SHAPE.RECTANGLE, (x, 1.76, card_w, 0.1), bar_col)
        tf = slide.shapes.add_textbox(Inches(x + 0.16), Inches(1.96), Inches(card_w - 0.32), Inches(1.9)).text_frame
        tf.word_wrap = True
        tf.paragraphs[0].space_after = Pt(6)
        _add_run(tf.paragraphs[0], val, 30.0 if len(val) <= 7 else 23.0, c.accent2, bold=True)
        p_lbl = tf.add_paragraph()
        p_lbl.space_after = Pt(4)
        _add_run(p_lbl, label, 13.0, c.text, bold=True)
        if delta:
            _add_run(tf.add_paragraph(), delta, 11.0, c.muted)

    has_callout = bool(key_fact)
    low = _add_box(slide, MSO_SHAPE.ROUNDED_RECTANGLE, (0.65, 4.22, 7.75 if has_callout else 12.03, 2.5), c.card)
    b_pt, sp = _bullet_metrics(bullets[:4], wide=not has_callout)
    _fill_bullets(_prep_tf(low.text_frame, (0.28, 0.24), (0.2, 0.18)), bullets[:4], min(b_pt, 14.0), min(sp, 7.0), c.text)
    if has_callout:
        _render_callout_panel(slide, key_fact, [], (8.65, 4.22, 4.03, 2.5), ctx)


def _parse_chart_data(raw: Any) -> tuple[str, list[str], list[float], str] | None:
    if not isinstance(raw, dict) or not isinstance(raw.get("labels"), list) or not isinstance(raw.get("values"), list):
        return None
    labels, values = [], []
    for lb, vl in zip(raw["labels"][:8], raw["values"][:8], strict=False):
        num_str = re.sub(r"[^0-9.\-]", "", str(vl).replace(",", "."))
        if num_str:
            try:
                values.append(float(num_str))
                labels.append(str(lb).strip()[:22] or str(len(labels) + 1))
            except ValueError:
                continue
    return (str(raw.get("title") or "").strip(), labels, values, str(raw.get("unit") or "").strip()) if len(values) >= 2 else None


def _render_chart_layout(
    slide: Any, chart_spec: tuple[str, list[str], list[float], str], bullets: list[str], key_fact: str, ctx: _SlideCtx
) -> None:
    c, (chart_title, labels, values, unit) = ctx.colors, chart_spec
    _add_box(slide, MSO_SHAPE.ROUNDED_RECTANGLE, (0.65, 1.76, 7.85, 4.96), c.card)
    cdata = CategoryChartData()
    cdata.categories = labels
    cdata.add_series(unit or "Value", values)
    frame: Any = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.85), Inches(1.94), Inches(7.45), Inches(4.6), cdata)
    chart: Any = frame.chart
    chart.has_legend = False
    if chart_title or unit:
        chart.has_title = True
        chart.chart_title.text_frame.text = ""
        full_title = f"{chart_title} ({unit})" if chart_title and unit else (chart_title or unit)
        _add_run(chart.chart_title.text_frame.paragraphs[0], full_title, 13.5, c.text, bold=True)
    series: Any = chart.series[0]
    series.format.fill.solid()
    series.format.fill.fore_color.rgb = c.accent
    plot: Any = chart.plots[0]
    plot.has_data_labels = True
    plot.data_labels.font.name, plot.data_labels.font.size, plot.data_labels.font.color.rgb = _FONT_FAMILY, Pt(10), c.text
    for axis in (chart.category_axis, chart.value_axis):
        axis.tick_labels.font.name, axis.tick_labels.font.size, axis.tick_labels.font.color.rgb = _FONT_FAMILY, Pt(10), c.muted
    chart.value_axis.has_major_gridlines = True
    chart.value_axis.major_gridlines.format.line.color.rgb = c.alt_row
    _render_callout_panel(slide, key_fact, bullets[:3], (8.72, 1.76, 3.96, 4.96), ctx)


def _parse_table_data(raw: Any) -> tuple[list[str], list[list[str]]] | None:
    if not isinstance(raw, dict) or not isinstance(raw.get("headers"), list) or not isinstance(raw.get("rows"), list):
        return None
    headers = [str(h).strip() for h in raw["headers"][:6] if str(h).strip()]
    rows = [[str(cell).strip() for cell in r[: len(headers)]] for r in raw["rows"][:7] if isinstance(r, list) and any(str(cell).strip() for cell in r)]
    return (headers, [r + [""] * (len(headers) - len(r)) for r in rows]) if len(headers) >= 2 and rows else None


def _render_table_layout(slide: Any, headers: list[str], rows: list[list[str]], key_fact: str, ctx: _SlideCtx) -> None:
    c, n_cols = ctx.colors, len(headers)
    tbl: Any = slide.shapes.add_table(len(rows) + 1, n_cols, Inches(0.65), Inches(1.76), Inches(12.03), Inches(4.02 if key_fact else 4.92)).table
    for ci in range(n_cols):
        tbl.columns[ci].width = int(Inches(12.03) / n_cols)
    body_pt, head_fg = (12.5 if n_cols <= 4 and len(rows) <= 5 else 10.5), _contrast_rgb(c.accent)
    for ri, row_vals in enumerate([headers, *rows]):
        is_head, row_fill = (ri == 0), (c.accent if ri == 0 else (c.card if ri % 2 == 1 else c.alt_row))
        for ci, val in enumerate(row_vals):
            cell: Any = tbl.cell(ri, ci)
            cell.fill.solid()
            cell.fill.fore_color.rgb, cell.vertical_anchor = row_fill, MSO_ANCHOR.MIDDLE
            cell.margin_left, cell.margin_right, cell.margin_top, cell.margin_bottom = Inches(0.12), Inches(0.1), Inches(0.06), Inches(0.06)
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            _add_run(p, val[:110], 12.5 if is_head else body_pt, head_fg if is_head else c.text, bold=is_head)
    if key_fact:
        _render_bottom_insight(slide, key_fact, ctx)


def _render_two_column(slide: Any, cols: dict[str, Any], bullets: list[str], key_fact: str, ctx: _SlideCtx) -> None:
    c, lbl, mid = ctx.colors, _LABELS[ctx.lang], max(1, (len(bullets) + 1) // 2)
    l_items = [str(b).strip() for b in (cols.get("left_bullets") or []) if str(b).strip()] or bullets[:mid]
    r_items = [str(b).strip() for b in (cols.get("right_bullets") or []) if str(b).strip()] or bullets[mid:]
    card_h = 4.02 if key_fact else 4.94
    for x, h_title, items, hdr_col in (
        (0.65, str(cols.get("left_title") or lbl["left_col"]).strip(), l_items[:5], c.accent),
        (6.82, str(cols.get("right_title") or lbl["right_col"]).strip(), r_items[:5], c.accent2),
    ):
        _add_box(slide, MSO_SHAPE.ROUNDED_RECTANGLE, (x, 1.76, 5.86, card_h), c.card, border=hdr_col, border_pt=1.1)
        hdr = _add_box(slide, MSO_SHAPE.RECTANGLE, (x, 1.76, 5.86, 0.54), hdr_col)
        _prep_tf(hdr.text_frame, (0.22, 0.16), (0.04, 0.04), middle=True)
        _add_run(hdr.text_frame.paragraphs[0], _tr_upper(h_title, ctx.lang), 12.5, _contrast_rgb(hdr_col), bold=True)
        tf_b = slide.shapes.add_textbox(Inches(x + 0.22), Inches(2.44), Inches(5.42), Inches(card_h - 0.8)).text_frame
        tf_b.word_wrap = True
        b_pt, sp = _bullet_metrics(items, wide=False)
        _fill_bullets(tf_b, items, min(b_pt, 14.5), min(sp, 8.0), c.text)
    if key_fact:
        _render_bottom_insight(slide, key_fact, ctx)


def _render_closing_layout(slide: Any, bullets: list[str], key_fact: str, ctx: _SlideCtx) -> None:
    c, lbl = ctx.colors, _LABELS[ctx.lang]
    headline = key_fact or (bullets[0] if bullets else ctx.deck_title)
    banner = _add_box(slide, MSO_SHAPE.ROUNDED_RECTANGLE, (0.65, 1.76, 12.03, 1.24), c.card, border=c.accent2, border_pt=1.5)
    _add_box(slide, MSO_SHAPE.RECTANGLE, (0.65, 1.76, 0.14, 1.24), c.accent2)
    tf_h = _prep_tf(banner.text_frame, (0.32, 0.28), (0.1, 0.1), middle=True)
    _add_run(tf_h.paragraphs[0], lbl["takeaways"], 11.0, c.accent2, bold=True)
    _add_run(tf_h.add_paragraph(), headline, 17.5 if len(headline) <= 95 else 14.5, c.text, bold=True)

    items = bullets[:4]
    if not items:
        return
    gap, cw = 0.24, (12.03 - 0.24 * (len(items) - 1)) / len(items)
    for i, btxt in enumerate(items):
        x = 0.65 + i * (cw + gap)
        _add_box(slide, MSO_SHAPE.ROUNDED_RECTANGLE, (x, 3.24, cw, 3.46), c.card, border=c.accent, border_pt=1.0)
        pill = _add_box(slide, MSO_SHAPE.ROUNDED_RECTANGLE, (x + 0.2, 3.46, 0.68, 0.42), c.accent)
        pill.text_frame.vertical_anchor, pill.text_frame.paragraphs[0].alignment = MSO_ANCHOR.MIDDLE, PP_ALIGN.CENTER
        _add_run(pill.text_frame.paragraphs[0], f"0{i + 1}", 12.5, _contrast_rgb(c.accent), bold=True)
        _add_textbox(slide, (x + 0.2, 4.06, cw - 0.4, 2.48), btxt, 14.5 if len(btxt) <= 85 else 12.5, c.text)


def _render_content_slide(slide: Any, sdata: dict[str, Any], ctx: _SlideCtx) -> None:
    lbl, layout = _LABELS[ctx.lang], str(sdata.get("layout") or "").strip().lower()
    stitle = str(sdata.get("title") or f"{lbl['slide']} {ctx.idx}").strip()
    kicker = str(sdata.get("kicker") or (lbl["closing_kicker"] if layout == "closing" else f"{lbl['section']} {ctx.idx - 1}")).strip()
    key_fact, notes_txt = str(sdata.get("key_fact") or "").strip(), str(sdata.get("notes") or "").strip()
    raw_b = sdata.get("bullets")
    bullets = [str(b).strip() for b in (raw_b if isinstance(raw_b, list) else []) if str(b).strip()]
    if not bullets and sdata.get("content"):
        bullets = [str(sdata["content"]).strip()]

    _render_slide_chrome(slide, kicker, stitle, ctx)
    kpis = [k for k in (sdata.get("kpis") or []) if isinstance(k, dict) and k.get("value")]
    chart_spec, table_spec = _parse_chart_data(sdata.get("chart")), _parse_table_data(sdata.get("table"))
    cols = sdata.get("columns") if isinstance(sdata.get("columns"), dict) else {}

    if (layout == "chart" or (layout != "closing" and chart_spec)) and chart_spec:
        _render_chart_layout(slide, chart_spec, bullets, key_fact, ctx)
    elif (layout == "table" or (layout != "closing" and table_spec)) and table_spec:
        _render_table_layout(slide, table_spec[0], table_spec[1], key_fact, ctx)
    elif (layout == "kpi_grid" or (layout != "closing" and len(kpis) >= 2)) and len(kpis) >= 2:
        _render_kpi_grid(slide, kpis, bullets, key_fact, ctx)
    elif layout == "two_column" or (layout != "closing" and cols):
        _render_two_column(slide, cols, bullets, key_fact, ctx)
    elif layout == "closing":
        _render_closing_layout(slide, bullets, key_fact, ctx)
    else:
        _render_bullets_layout(slide, bullets or [stitle], key_fact, ctx)
    _set_speaker_notes(slide, notes_txt or _auto_notes(stitle, bullets, key_fact, ctx.lang))


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


def _slides_are_real(spec: dict[str, Any], prompt: str) -> bool:
    """A usable deck has several slides with their own content; slides that just repeat the request are rejected."""
    slides = spec.get("slides")
    if not isinstance(slides, list) or len(slides) < 3:
        return False
    echo = " ".join(prompt.lower().split())[:40]
    filled = 0
    for sl in slides:
        if not isinstance(sl, dict) or not str(sl.get("title") or "").strip():
            return False
        bullets = [str(x) for x in (sl.get("bullets") or [])] + [str(x) for x in ((sl.get("columns") or {}).get("left_bullets") or [])]
        if any(echo and echo in " ".join(x.lower().split()) for x in bullets):
            return False
        filled += 1 if (bullets or sl.get("kpis")) else 0
    return filled >= max(3, len(slides) - 1)


async def _fetch_pptx_spec(sys_prompt: str, user_msg: str, model: str, prompt: str = "") -> dict[str, Any]:
    """Ask the model for the deck outline; one retry. Returns {} when no usable content came back (never a made-up deck)."""
    import gateway

    for attempt in (1, 2):
        try:
            res = await gateway.default_client.chat(
                [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_msg}],
                model=model, profile="analytic", num_predict=4200, timeout_s=240.0, feature="deep_research", max_retries=0,
            )
            m = re.search(r"\{[\s\S]*\}", res.content)
            if m:
                parsed = json.loads(re.sub(r",\s*([}\]])", r"\1", m.group(0)))
                if isinstance(parsed, dict) and _slides_are_real(parsed, prompt):
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
    spec.update(await _fetch_pptx_spec(sys_prompt, user_msg, model, prompt))
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
