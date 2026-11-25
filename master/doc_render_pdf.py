"""Render a validated block spec (doc_spec.parse) as a paginated A4 PDF through PyMuPDF's HTML layout engine."""

from __future__ import annotations

import html
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pymupdf

import doc_tables
from document_chart import render_bar_chart_png, to_number

_CSS = (Path(__file__).parent / "prompts" / "doc_pdf.css").read_text(encoding="utf-8")


def _e(text: str) -> str:
    return html.escape(text).replace("\n", "<br>")


def _table(block: dict[str, Any]) -> str:
    head = "".join(f"<th>{_e(h)}</th>" for h in block["headers"])
    rows = ""
    for ri, row in enumerate(block["rows"]):
        bg = ' style="background-color:#f1f5f9"' if ri % 2 else ""
        bold = doc_tables.is_total_row(row)
        rows += "<tr>" + "".join(f'<td{bg} align="{"right" if to_number(c) is not None else "left"}">{"<b>" if bold else ""}{_e(c)}{"</b>" if bold else ""}</td>' for c in row) + "</tr>"
    cap = f'<p class="cap">{_e(block["caption"])}</p>' if block.get("caption") else ""
    return f'{cap}<table width="100%" cellspacing="0"><tr>{head}</tr>{rows}</table><p></p>'


def _chart(block: dict[str, Any], archive: Any, n: int, fonts: tuple[str | None, str | None]) -> str:
    png = render_bar_chart_png(["", block["title"] or "Değer"], [[lab, v] for lab, v in zip(block["labels"], block["values"], strict=True)], block["title"], fonts)
    if not png:
        return ""
    archive.add(png, f"chart{n}.png")
    return f'<p style="text-align:center"><img src="chart{n}.png" width="440"></p>'


def _html(spec: dict[str, Any], archive: Any, fonts: tuple[str | None, str | None]) -> str:
    sub = " · ".join(x for x in (spec["subtitle"], datetime.now(UTC).strftime("%d.%m.%Y")) if x)
    out = [f'<table width="100%" cellspacing="0"><tr><td style="background-color:#1e293b;padding:12pt"><span style="font-size:18pt;font-weight:bold;color:#ffffff">{_e(spec["title"])}</span><br><span style="font-size:9pt;color:#cbd5e1">{_e(sub)}</span></td></tr></table><p></p>']
    charts = 0
    for b in spec["blocks"]:
        kind = b["type"]
        if kind == "heading":
            out.append(f"<h{b['level']}>{_e(b['text'])}</h{b['level']}>")
        elif kind == "para":
            out.append(f"<p>{_e(b['text'])}</p>")
        elif kind == "numbered" and b.get("own_numbers"):
            out.extend(f"<p>{_e(i)}</p>" for i in b["items"])  # items already start with "Madde 1 -" / "1."
        elif kind == "numbered":
            out.append("<ol>" + "".join(f"<li>{_e(i)}</li>" for i in b["items"]) + "</ol>")
        elif kind == "bullets":
            out.append("<ul>" + "".join(f"<li>{_e(i)}</li>" for i in b["items"]) + "</ul>")
        elif kind == "table":
            out.append(_table(b))
        elif kind == "signature":
            out.append('<table width="100%"><tr>' + "".join(f'<td class="sig" style="border-bottom:0">____________________<br><b>{_e(p)}</b><br><span class="cap">İmza / Tarih</span></td>' for p in b["parties"]) + "</tr></table>")
        elif kind == "chart":
            charts += 1
            out.append(_chart(b, archive, charts, fonts))
    return "".join(out)


def _number_pages(path: Path, title: str, reg: str) -> None:
    doc = pymupdf.open(stream=path.read_bytes(), filetype="pdf")  # from memory: no file handle blocks rewriting the path
    total = doc.page_count
    for page in doc:
        page.insert_font(fontname="uf", fontfile=reg)
        page.insert_text((56, page.rect.height - 28), f"{title[:60]}  ·  {page.number + 1} / {total}", fontname="uf", fontsize=8, color=(0.4, 0.45, 0.55))
    data = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    path.write_bytes(data)


def build(out_path: Path, spec: dict[str, Any], fonts: tuple[str | None, str | None], scale: float = 1.0) -> int:
    """Write the PDF (text scaled by `scale`) and return its page count."""
    reg, bold = fonts
    if not reg:
        raise RuntimeError("no Unicode font found for PDF output")
    archive = pymupdf.Archive()
    archive.add(Path(reg).read_bytes(), "reg.ttf")
    archive.add(Path(bold or reg).read_bytes(), "bold.ttf")
    css = _CSS.replace("font-size: 10.5pt", f"font-size: {10.5 * scale:.2f}pt")
    story = pymupdf.Story(html=_html(spec, archive, fonts), user_css=css, archive=archive)
    writer = pymupdf.DocumentWriter(str(out_path))
    page_rect = pymupdf.paper_rect("a4")
    area = pymupdf.Rect(page_rect.x0 + 56, page_rect.y0 + 50, page_rect.x1 - 56, page_rect.y1 - 56)
    more = 1
    while more:
        device = writer.begin_page(page_rect)
        more, _ = story.place(area)
        story.draw(device)
        writer.end_page()
    writer.close()
    _number_pages(out_path, spec["title"], reg)
    return int(pymupdf.open(str(out_path)).page_count)
