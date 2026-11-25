"""Slide renderers for the PowerPoint builder: cover, chrome and every content layout (bullets, KPI cards, chart, table, columns, steps, closing)."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls
from pptx.util import Inches, Pt

_FONT_FAMILY = "Calibri"  # Cross-platform Office standard (fallback: DejaVu Sans / Arial)


_LABELS: dict[str, dict[str, str]] = {
    "tr": {
        "slide": "Slayt", "key_insight": "ÖNEMLİ BULGU", "section": "BÖLÜM",
        "cover_badge": "SUNUM", "cover_sub": "Sunum",
        "left_col": "TEMEL EKSEN", "right_col": "KARŞILAŞTIRMALI EKSEN",
        "closing_kicker": "SONUÇ VE EYLEM PLANI", "takeaways": "ÖNE ÇIKAN ÇIKARIMLAR",
    },
    "en": {
        "slide": "Slide", "key_insight": "KEY INSIGHT", "section": "SECTION",
        "cover_badge": "PRESENTATION", "cover_sub": "Presentation",
        "left_col": "PRIMARY AXIS", "right_col": "COMPARATIVE AXIS",
        "closing_kicker": "CONCLUSION & NEXT STEPS", "takeaways": "KEY TAKEAWAYS",
    },
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


def _tr_upper(text: str, lang: str = "tr") -> str:
    s = text or ""
    return s.replace("i", "İ").replace("ı", "I").upper() if lang == "tr" else s.upper()


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


def _set_speaker_notes(slide: Any, text: str) -> None:
    notes_tf = slide.notes_slide.notes_text_frame
    if notes_tf is not None:
        notes_tf.text = text.strip()


def _auto_notes(title: str, bullets: list[str], key_fact: str, lang: str) -> str:
    """Fallback speaker notes built from the slide's own points (used only when the model wrote none)."""
    points = " ".join(b.rstrip(".") + "." for b in bullets[:4])
    if lang == "en":
        return f"{title}. {points} {('Key takeaway: ' + key_fact) if key_fact else ''}".strip()
    return f"{title}. {points} {('Vurgulanacak çıkarım: ' + key_fact) if key_fact else ''}".strip()


def _bullet_metrics(bullets: list[str], wide: bool, height: float = 4.2) -> tuple[float, float]:
    """(font pt, paragraph spacing pt): the largest size at which the bullets still fit `height` inches (few bullets get big type)."""
    base_cpl = 66 if wide else 42  # characters per line at 16 pt
    for pt in (22.0, 20.0, 18.0, 16.0, 14.5, 13.0, 11.5):
        cpl, space = base_cpl * 16.0 / pt, pt * 0.7
        lines = sum(max(1, math.ceil(len(b) / cpl)) for b in bullets)
        if (lines * pt * 1.22 + len(bullets) * space) / 72 <= height:
            return (pt, space)
    return (10.5, 4.0)


def _add_run(p: Any, text: str, size_pt: float, color: RGBColor, *, bold: bool = False) -> None:
    r = p.add_run()
    r.text, r.font.name, r.font.size, r.font.bold, r.font.color.rgb = text, _FONT_FAMILY, Pt(size_pt), bold, color


def _prep_tf(tf: Any, lr: tuple[float, float], tb: tuple[float, float], *, middle: bool = False, align: Any = PP_ALIGN.LEFT) -> Any:
    """Margins, wrapping and anchoring; python-pptx auto-shapes start centred, so the first paragraph is aligned explicitly."""
    tf.word_wrap = True
    tf.margin_left, tf.margin_right = Inches(lr[0]), Inches(lr[1])
    tf.margin_top, tf.margin_bottom = Inches(tb[0]), Inches(tb[1])
    tf.paragraphs[0].alignment = align
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


def _hanging_bullet(paragraph: Any, indent_in: float = 0.3) -> None:
    """Real PowerPoint bullet with a hanging indent (wrapped lines align under the text, not under the bullet)."""
    pPr = paragraph._p.get_or_add_pPr()
    pPr.set("marL", str(int(Inches(indent_in))))
    pPr.set("indent", str(-int(Inches(indent_in))))
    for tag in ("buNone", "buChar", "buAutoNum"):
        for old in pPr.findall(f"{{http://schemas.openxmlformats.org/drawingml/2006/main}}{tag}"):
            pPr.remove(old)
    pPr.append(parse_xml(f'<a:buChar {nsdecls("a")} char="\u2022"/>'))


def _fill_bullets(tf: Any, items: list[str], font_pt: float, space_pt: float, color: RGBColor, **opts: Any) -> None:
    append = bool(opts.get("append", False))
    for bi, btxt in enumerate(items):
        pb = tf.add_paragraph() if (append or bi > 0) else tf.paragraphs[0]
        pb.space_after, pb.alignment = Pt(space_pt), PP_ALIGN.LEFT
        _hanging_bullet(pb, 0.18 + font_pt / 72 * 0.7)
        _add_run(pb, btxt, font_pt, color)


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
    tf = _prep_tf(card.text_frame, (0.26, 0.24), (0.22, 0.18), middle=True)
    tf.paragraphs[0].space_after = Pt(10)
    _add_run(tf.paragraphs[0], lbl["key_insight"], 11.5, c.accent2, bold=True)
    if key_fact:
        pf = tf.add_paragraph()
        pf.space_after = Pt(10)
        _add_run(pf, key_fact, 21.0 if len(key_fact) <= 60 else (17.0 if len(key_fact) <= 110 else (14.0 if len(key_fact) <= 185 else 12.0)), c.text, bold=True)
    if bullets:
        b_pt, sp = _bullet_metrics(bullets[:4], wide=False)
        _fill_bullets(tf, bullets[:4], min(b_pt, 12.5), min(sp, 6.5), c.muted, append=True)


def _render_bullets_layout(slide: Any, bullets: list[str], key_fact: str, ctx: _SlideCtx) -> None:
    c, has_callout = ctx.colors, bool(key_fact)
    card_w = 7.75 if has_callout else 12.03
    card = _add_box(slide, MSO_SHAPE.ROUNDED_RECTANGLE, (0.65, 1.76, card_w, 4.96), c.card)
    _add_box(slide, MSO_SHAPE.RECTANGLE, (0.65, 1.76, card_w, 0.08), c.accent)
    tf = _prep_tf(card.text_frame, (0.36, 0.3), (0.3, 0.26), middle=len(bullets[:6]) <= 5)
    b_pt, sp = _bullet_metrics(bullets[:6], wide=not has_callout, height=4.3)
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
        _add_box(slide, MSO_SHAPE.ROUNDED_RECTANGLE, (x, 1.76, card_w, 1.95), c.card, border=bar_col, border_pt=1.1)
        _add_box(slide, MSO_SHAPE.RECTANGLE, (x, 1.76, card_w, 0.1), bar_col)
        tf = slide.shapes.add_textbox(Inches(x + 0.16), Inches(1.96), Inches(card_w - 0.32), Inches(1.65)).text_frame
        tf.word_wrap = True
        tf.paragraphs[0].space_after = Pt(6)
        _add_run(tf.paragraphs[0], val, 34.0 if len(val) <= 7 else (28.0 if len(val) <= 10 else 21.0), c.accent2, bold=True)
        p_lbl = tf.add_paragraph()
        p_lbl.space_after = Pt(4)
        _add_run(p_lbl, label, 14.0, c.text, bold=True)
        if delta:
            _add_run(tf.add_paragraph(), delta, 11.5, c.muted)

    has_callout = bool(key_fact)
    low = _add_box(slide, MSO_SHAPE.ROUNDED_RECTANGLE, (0.65, 3.96, 7.75 if has_callout else 12.03, 2.76), c.card)
    b_pt, sp = _bullet_metrics(bullets[:4], wide=not has_callout, height=2.2)
    _fill_bullets(_prep_tf(low.text_frame, (0.3, 0.26), (0.2, 0.18), middle=True), bullets[:4], min(b_pt, 17.0), min(sp, 9.0), c.text)
    if has_callout:
        _render_callout_panel(slide, key_fact, [], (8.65, 3.96, 4.03, 2.76), ctx)


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
    is_trend = len(labels) >= 3 and all(re.fullmatch(r"(19|20)\d\d", lb.strip()) for lb in labels) and values == sorted(values)
    kind = XL_CHART_TYPE.LINE_MARKERS if is_trend and not unit.startswith("%") else XL_CHART_TYPE.COLUMN_CLUSTERED
    frame: Any = slide.shapes.add_chart(kind, Inches(0.85), Inches(1.94), Inches(7.45), Inches(4.6), cdata)
    chart: Any = frame.chart
    chart.has_legend = False
    if chart_title or unit:
        chart.has_title = True
        chart.chart_title.text_frame.text = ""
        full_title = f"{chart_title} ({unit})" if chart_title and unit else (chart_title or unit)
        _add_run(chart.chart_title.text_frame.paragraphs[0], full_title, 13.5, c.text, bold=True)
    series: Any = chart.series[0]
    if kind == XL_CHART_TYPE.LINE_MARKERS:
        series.format.line.color.rgb, series.format.line.width, series.smooth = c.accent2, Pt(3.0), False
        series.marker.format.fill.solid()
        series.marker.format.fill.fore_color.rgb = c.accent
    else:
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = c.accent
    plot: Any = chart.plots[0]
    plot.has_data_labels = True
    plot.data_labels.number_format, plot.data_labels.number_format_is_linked = ("#,##0" if all(v == int(v) for v in values) else "#,##0.0"), False
    chart.value_axis.tick_labels.number_format, chart.value_axis.tick_labels.number_format_is_linked = "#,##0", False
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
    total_h = 4.02 if key_fact else 4.92
    tbl: Any = slide.shapes.add_table(len(rows) + 1, n_cols, Inches(0.65), Inches(1.76), Inches(12.03), Inches(total_h)).table
    for ci in range(n_cols):
        tbl.columns[ci].width = int(Inches(12.03) / n_cols)
    head_h = 0.62
    tbl.rows[0].height = Inches(head_h)
    for ri in range(1, len(rows) + 1):
        tbl.rows[ri].height = Inches(min(1.1, (total_h - head_h) / len(rows)))
    body_pt = 16.0 if n_cols <= 3 and len(rows) <= 4 else (14.0 if n_cols <= 4 and len(rows) <= 5 else 11.5)
    head_fg = _contrast_rgb(c.accent)
    for ri, row_vals in enumerate([headers, *rows]):
        is_head, row_fill = (ri == 0), (c.accent if ri == 0 else (c.card if ri % 2 == 1 else c.alt_row))
        for ci, val in enumerate(row_vals):
            cell: Any = tbl.cell(ri, ci)
            cell.fill.solid()
            cell.fill.fore_color.rgb, cell.vertical_anchor = row_fill, MSO_ANCHOR.MIDDLE
            cell.margin_left, cell.margin_right, cell.margin_top, cell.margin_bottom = Inches(0.12), Inches(0.1), Inches(0.06), Inches(0.06)
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            _add_run(p, val[:110], 13.5 if is_head else body_pt, head_fg if is_head else c.text, bold=is_head)
    if key_fact:
        _render_bottom_insight(slide, key_fact, ctx)


def _text_height(chars: int, size_pt: float, width_in: float) -> float:
    """Rough height in inches of `chars` characters of `size_pt` text wrapped into `width_in` inches."""
    cpl = max(8.0, width_in * 72 / (size_pt * 0.5))
    return math.ceil(max(chars, 1) / cpl) * size_pt * 1.22 / 72


def _render_two_column(slide: Any, cols: dict[str, Any], bullets: list[str], key_fact: str, ctx: _SlideCtx) -> None:
    c, lbl, mid = ctx.colors, _LABELS[ctx.lang], max(1, (len(bullets) + 1) // 2)
    l_items = [str(b).strip() for b in (cols.get("left_bullets") or []) if str(b).strip()] or bullets[:mid]
    r_items = [str(b).strip() for b in (cols.get("right_bullets") or []) if str(b).strip()] or bullets[mid:]
    max_h = 4.02 if key_fact else 4.94
    l_items, r_items = l_items[:5], r_items[:5]
    b_pt, sp = _bullet_metrics(max(l_items, r_items, key=lambda it: sum(len(x) for x in it)), wide=False, height=max_h - 1.15)
    b_pt, sp = min(b_pt, 20.0), min(sp, 11.0)
    need = max(sum(_text_height(len(x) + 3, b_pt, 5.1) + sp / 72 for x in it) for it in (l_items, r_items) if it) if (l_items or r_items) else 1.0
    card_h = max(2.9, min(max_h, 0.54 + 0.5 + need))
    top = 1.76 + (max_h - card_h) / 2 if key_fact else 1.76
    for x, h_title, items, hdr_col in (
        (0.65, str(cols.get("left_title") or lbl["left_col"]).strip(), l_items, c.accent),
        (6.82, str(cols.get("right_title") or lbl["right_col"]).strip(), r_items, c.accent2),
    ):
        _add_box(slide, MSO_SHAPE.ROUNDED_RECTANGLE, (x, top, 5.86, card_h), c.card, border=hdr_col, border_pt=1.1)
        hdr = _add_box(slide, MSO_SHAPE.RECTANGLE, (x, top, 5.86, 0.54), hdr_col)
        _prep_tf(hdr.text_frame, (0.22, 0.16), (0.04, 0.04), middle=True, align=PP_ALIGN.CENTER)
        _add_run(hdr.text_frame.paragraphs[0], _tr_upper(h_title, ctx.lang), 12.5, _contrast_rgb(hdr_col), bold=True)
        tf_b = slide.shapes.add_textbox(Inches(x + 0.22), Inches(top + 0.68), Inches(5.42), Inches(card_h - 0.8)).text_frame
        tf_b.word_wrap = True
        _fill_bullets(tf_b, items, b_pt, sp, c.text)
    if key_fact:
        _render_bottom_insight(slide, key_fact, ctx)


def _split_lead(text: str) -> tuple[str, str]:
    """'Parola yöneticisi kur: tüm hesaplar için ...' -> ('Parola yöneticisi kur', 'tüm hesaplar için ...'); no lead when there is no colon/dash."""
    m = re.match(r"^(.{4,48}?)\s*[:\u2013\u2014-]\s+(.+)$", text)
    return (m.group(1).strip(), m.group(2).strip()) if m else ("", text)


def _card_text_height(txt: str, size: float, width: float) -> float:
    lead, rest = _split_lead(txt)
    if not lead:
        return _text_height(len(rest), size, width)
    return _text_height(len(lead), size, width) + _text_height(len(rest), size - 2.0, width) + 6 / 72


def _step_size(items: list[str]) -> float:
    longest = max((len(t) for t in items), default=0)
    size = 20.0 if longest <= 50 else (18.0 if longest <= 90 else (16.0 if longest <= 130 else 14.0))
    return size - (1.5 if len(items) == 4 else (2.5 if len(items) >= 5 else 0.0))


def _render_step_cards(slide: Any, items: list[str], rect: tuple[float, float, float, float], ctx: _SlideCtx, *, timeline: bool = False) -> None:
    """Numbered cards in a row (closing takeaways, process steps, milestones), sized to their text and centred in `rect`."""
    c = ctx.colors
    x0, y0, w, h = rect
    n, gap, size = len(items), 0.24, _step_size(items)
    cw = (w - gap * (n - 1)) / n
    text_h = max(_card_text_height(t, size, cw - 0.4) for t in items)
    ch = max(2.3, min(h, 1.15 + text_h + 0.35))
    top = y0 + (h - ch) / 2
    for i in range(n):
        _add_box(slide, MSO_SHAPE.ROUNDED_RECTANGLE, (x0 + i * (cw + gap), top, cw, ch), c.card, border=c.accent, border_pt=1.0)
    if timeline:
        _add_box(slide, MSO_SHAPE.RECTANGLE, (x0 + 0.4, top + 0.405, w - 0.8, 0.04), c.accent2)
    for i, txt in enumerate(items):
        x = x0 + i * (cw + gap)
        pill = _add_box(slide, MSO_SHAPE.ROUNDED_RECTANGLE, (x + 0.2, top + 0.2, 0.68, 0.42), c.accent)
        pill.text_frame.vertical_anchor, pill.text_frame.paragraphs[0].alignment = MSO_ANCHOR.MIDDLE, PP_ALIGN.CENTER
        _add_run(pill.text_frame.paragraphs[0], f"{i + 1:02d}", 12.5, _contrast_rgb(c.accent), bold=True)
        lead, rest = _split_lead(txt)
        tf = slide.shapes.add_textbox(Inches(x + 0.2), Inches(top + 0.82), Inches(cw - 0.4), Inches(ch - 1.0)).text_frame
        tf.word_wrap = True
        if lead:
            tf.paragraphs[0].space_after = Pt(6)
            _add_run(tf.paragraphs[0], lead, size, c.text, bold=True)
            _add_run(tf.add_paragraph(), rest, size - 2.0, c.muted)
        else:
            _add_run(tf.paragraphs[0], rest, size, c.text)


def _render_closing_layout(slide: Any, bullets: list[str], key_fact: str, ctx: _SlideCtx) -> None:
    c, lbl = ctx.colors, _LABELS[ctx.lang]
    headline = key_fact or (bullets[0] if bullets else ctx.deck_title)
    banner = _add_box(slide, MSO_SHAPE.ROUNDED_RECTANGLE, (0.65, 1.76, 12.03, 1.3), c.card, border=c.accent2, border_pt=1.5)
    _add_box(slide, MSO_SHAPE.RECTANGLE, (0.65, 1.76, 0.14, 1.3), c.accent2)
    tf_h = _prep_tf(banner.text_frame, (0.34, 0.3), (0.1, 0.1), middle=True)
    tf_h.paragraphs[0].space_after = Pt(4)
    _add_run(tf_h.paragraphs[0], lbl["takeaways"], 11.0, c.accent2, bold=True)
    _add_run(tf_h.add_paragraph(), headline, 21.0 if len(headline) <= 80 else (18.0 if len(headline) <= 130 else 15.0), c.text, bold=True)
    items = bullets[:4]
    if items:
        _render_step_cards(slide, items, (0.65, 3.3, 12.03, 3.4), ctx)


def _render_steps_layout(slide: Any, bullets: list[str], key_fact: str, ctx: _SlideCtx) -> None:
    """Process / roadmap / milestones: up to five numbered cards joined by a timeline line, optional insight bar below."""
    items = bullets[:5]
    _render_step_cards(slide, items, (0.65, 1.76, 12.03, 4.02 if key_fact else 4.94), ctx, timeline=True)
    if key_fact:
        _render_bottom_insight(slide, key_fact, ctx)


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
    elif layout in ("steps", "timeline", "process", "roadmap") and len(bullets) >= 2:
        _render_steps_layout(slide, bullets, key_fact, ctx)
    else:
        _render_bullets_layout(slide, bullets or [stitle], key_fact, ctx)
    _set_speaker_notes(slide, notes_txt or _auto_notes(stitle, bullets, key_fact, ctx.lang))
