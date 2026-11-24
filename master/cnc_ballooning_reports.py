"""AS9102 / FAI Multi-Format CNC Ballooning Report Exporters (PDF, Excel .xlsx, Word .docx)."""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Any

import pymupdf as fitz
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Inches, Pt, RGBColor
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from PIL import Image

from cnc_ballooning_plan import BalloonItem, build_cnc_manufacturing_plan


def export_ballooned_pdf(
    ballooned_img: Image.Image, balloons: list[BalloonItem], metadata: dict[str, str], out_path: Path
) -> Path:
    """Create a multi-page PDF: Page 1 = high-res ballooned drawing, Page 2+ = AS9102 inspection table."""
    doc = fitz.open()
    page = doc.new_page(width=842, height=595)
    img_buf = io.BytesIO()
    ballooned_img.save(img_buf, format="PNG")
    page.insert_image(fitz.Rect(16, 16, 826, 579), stream=img_buf.getvalue(), keep_proportion=True)

    rows_per_page = 24
    chunks = [balloons[i : i + rows_per_page] for i in range(0, max(1, len(balloons)), rows_per_page)]
    headers = ["No", "Bölge", "Karakteristik / Ölçü", "Kategori", "Nominal", "+Tol", "-Tol", "Min", "Max", "Ölçüm Aleti", "Kritiklik"]
    col_x = [24, 52, 88, 215, 315, 365, 412, 460, 510, 565, 745]

    for p_idx, chunk in enumerate(chunks, start=1):
        tp = doc.new_page(width=842, height=595)
        tp.draw_rect(fitz.Rect(20, 18, 822, 54), color=(0.12, 0.16, 0.23), fill=(0.12, 0.16, 0.23))
        tp.insert_text(
            (30, 41),
            f"CNC BALONLAMA VE KALITE KONTROL FORMU (AS9102 / FAI)  -  Parca: {metadata.get('part_name', '')} "
            f"({metadata.get('part_number', '-')})  |  Sayfa {p_idx}/{len(chunks)}",
            fontsize=10.5, color=(1, 1, 1),
        )
        y = 72
        tp.draw_rect(fitz.Rect(20, y - 12, 822, y + 6), color=(0.86, 0.15, 0.15), fill=(0.86, 0.15, 0.15))
        for cx, htext in zip(col_x, headers, strict=False):
            tp.insert_text((cx, y), htext, fontsize=8.5, color=(1, 1, 1))
        y += 20
        for idx, b in enumerate(chunk):
            if idx % 2 == 1:
                tp.draw_rect(fitz.Rect(20, y - 11, 822, y + 7), color=(0.96, 0.97, 0.98), fill=(0.96, 0.97, 0.98))
            vals = [
                str(b.balloon_no), b.zone or "-", b.raw_text[:22], b.category[:16],
                f"{b.nominal:g}" if b.nominal is not None else "-",
                f"+{b.tol_plus:g}" if b.tol_plus is not None else "-",
                f"{b.tol_minus:g}" if b.tol_minus is not None else "-",
                f"{b.min_limit:g}" if b.min_limit is not None else "-",
                f"{b.max_limit:g}" if b.max_limit is not None else "-",
                b.gage[:30], b.criticality,
            ]
            for cx, val in zip(col_x, vals, strict=False):
                tp.insert_text((cx, y), val, fontsize=8, color=(0.1, 0.1, 0.15))
            y += 20

    doc.save(str(out_path))
    doc.close()
    return out_path


def _excel_styles() -> dict[str, Any]:
    thin = Side(style="thin", color="CBD5E1")
    return {
        "navy": PatternFill("solid", fgColor="1E293B"),
        "slate": PatternFill("solid", fgColor="334155"),
        "red": PatternFill("solid", fgColor="DC2626"),
        "soft": PatternFill("solid", fgColor="F8FAFC"),
        "meta": PatternFill("solid", fgColor="EFF6FF"),
        "crit": PatternFill("solid", fgColor="FEE2E2"),
        "warn": PatternFill("solid", fgColor="FEF3C7"),
        "border": Border(left=thin, right=thin, top=thin, bottom=thin),
    }


def _populate_excel_form3(
    ws: Any, balloons: list[BalloonItem], metadata: dict[str, str], plan: dict[str, Any], st: dict[str, Any]
) -> None:
    ws.title = "Form 3 - Balonlama (FAI)"
    ws.merge_cells("A1:T1")
    ws["A1"].value = "AS9102 FORM 3 — CNC TEKNİK ÇİZİM BALONLAMA, TOLERANS VE KALİTE KONTROL RAPORU"
    ws["A1"].font, ws["A1"].fill, ws["A1"].alignment = Font(name="Calibri", size=14, bold=True, color="FFFFFF"), st["navy"], Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    s = plan["summary"]
    meta_rows = [
        ("Parça No:", metadata.get("part_number") or "—", "Parça Adı:", metadata.get("part_name") or "—", "Revizyon:", metadata.get("revision") or "A", "Toplam Balon:", str(s["total"])),
        ("Malzeme:", metadata.get("material") or "—", "Standart:", metadata.get("standard") or "ISO 2768-mK", "Tarih:", datetime.now().strftime("%Y-%m-%d %H:%M"), "Kritik / Majör / Minör:", f"{s['critical']} / {s['major']} / {s['minor']}"),
    ]
    for r_off, mrow in enumerate(meta_rows, start=2):
        ws.row_dimensions[r_off].height = 20
        for idx_m, val in enumerate(mrow):
            c = ws.cell(row=r_off, column=idx_m + 1, value=val)
            c.border = st["border"]
            c.font = Font(bold=(idx_m % 2 == 0), size=10, color="1E293B" if idx_m % 2 == 0 else "000000")
            if idx_m % 2 == 0:
                c.fill = st["meta"]

    headers = [
        "Balon No", "Bölge", "Çizim İfadesi", "Kategori", "Adet", "Nominal", "+Tol", "-Tol", "Min Limit", "Max Limit",
        "Tol. Bandı", "Operasyon (OP)", "Önerilen Kesici Takım", "Ölçüm Ekipmanı", "Kontrol Sıklığı",
        "Numune 1", "Numune 2", "Numune 3", "Ortalama", "Sonuç (OK/NOK)",
    ]
    ws.row_dimensions[5].height = 26
    for col_i, htext in enumerate(headers, start=1):
        c = ws.cell(row=5, column=col_i, value=htext)
        c.font, c.fill, c.border = Font(bold=True, color="FFFFFF", size=10), st["red"], st["border"]
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for idx, b in enumerate(balloons, start=1):
        _write_form3_row(ws, 5 + idx, idx, b, st)
    for col_i, width in enumerate([9, 7, 20, 17, 6, 10, 9, 9, 10, 10, 10, 26, 30, 26, 22, 11, 11, 11, 11, 15], start=1):
        ws.column_dimensions[get_column_letter(col_i)].width = width
    ws.freeze_panes = "D6"


def _write_form3_row(ws: Any, r: int, idx: int, b: BalloonItem, st: dict[str, Any]) -> None:
    ws.row_dimensions[r].height = 22
    has_lim = b.min_limit is not None and b.max_limit is not None
    span = round(abs(b.max_limit - b.min_limit), 4) if has_lim else None  # type: ignore[operator]
    avg_f = f'=IF(COUNT(P{r}:R{r})=0,"",ROUND(AVERAGE(P{r}:R{r}),4))'
    res_f = f'=IF(S{r}="","",IF(AND(MIN(P{r}:R{r})>=I{r},MAX(P{r}:R{r})<=J{r}),"OK","NOK"))' if has_lim else f'=IF(P{r}="","","MANUEL ONAY")'
    vals = [
        b.balloon_no, b.zone or "—", b.raw_text, b.category, b.quantity, b.nominal, b.tol_plus, b.tol_minus,
        b.min_limit, b.max_limit, span, b.operation, b.tooling, b.gage, b.inspection_freq, None, None, None, avg_f, res_f,
    ]
    for ci, val in enumerate(vals, start=1):
        c = ws.cell(row=r, column=ci, value=val)
        c.border = st["border"]
        c.alignment = Alignment(horizontal="left" if ci in (3, 4, 12, 13, 14, 15) else "center", vertical="center", wrap_text=ci in (12, 13, 14, 15))
        if idx % 2 == 0:
            c.fill = st["soft"]
        if ci == 1:
            c.font = Font(bold=True, color="DC2626")
        if b.criticality == "Kritik" and ci == 3:
            c.fill, c.font = st["crit"], Font(bold=True, color="991B1B")


def _populate_excel_process_sheet(wb: Workbook, plan: dict[str, Any], st: dict[str, Any]) -> None:
    ws: Any = wb.create_sheet("CNC Proses & Operasyon Planı")
    ws.merge_cells("A1:F1")
    ws["A1"].value = "CNC İMALAT PROSES ROTASI, KESME PARAMETRELERİ VE DFM RİSK ANALİZİ"
    ws["A1"].font, ws["A1"].fill, ws["A1"].alignment = Font(size=13, bold=True, color="FFFFFF"), st["navy"], Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    cp = plan["cutting_parameters"]
    ws["A3"].value, ws["A3"].font = "MALZEME KESME PARAMETRE REHBERİ", Font(bold=True, size=11, color="1E293B")
    param_rows = [("ISO Malzeme Grubu", cp["group"]), ("Torna Kesme Hızı (Vc)", cp["vc_turn"]), ("Freze Kesme Hızı (Vc)", cp["vc_mill"]), ("İlerleme (f)", cp["feed"]), ("Soğutma Sıvısı", cp["coolant"]), ("Takım / Proses Notu", cp["note"])]
    for i, (k, v) in enumerate(param_rows, start=4):
        c1, c2 = ws.cell(i, 1, k), ws.cell(i, 2, v)
        ws.merge_cells(start_row=i, start_column=2, end_row=i, end_column=6)
        c1.font, c1.fill, c1.border, c2.border = Font(bold=True), st["meta"], st["border"], st["border"]

    ws.cell(11, 1, "OPERASYON ROTASI (OP10 - OP50)").font = Font(bold=True, size=11, color="1E293B")
    for ci, ht in enumerate(["OP", "Operasyon Adı", "Tezgâh", "Bağlama / Fikstür", "Kapsanan Balonlar", "Mühendislik / Setup Notu"], start=1):
        c = ws.cell(12, ci, ht)
        c.font, c.fill, c.border = Font(bold=True, color="FFFFFF"), st["slate"], st["border"]
    for idx_o, op in enumerate(plan["operations"], start=13):
        b_list = ", ".join(f"#{n}" for n in op["balloons"]) if op["balloons"] else "Genel"
        for ci, val in enumerate([op["op"], op["name"], op["machine"], op["fixture"], b_list, op["notes"]], start=1):
            c = ws.cell(idx_o, ci, val)
            c.border, c.alignment = st["border"], Alignment(wrap_text=True, vertical="center")
        ws.row_dimensions[idx_o].height = 28

    risk_start = 14 + len(plan["operations"])
    ws.cell(risk_start, 1, "DFM VE KRİTİK KALİTE RİSK UYARILARI").font = Font(bold=True, size=11, color="991B1B")
    for idx_r, rtext in enumerate(plan["dfm_risks"], start=risk_start + 1):
        ws.merge_cells(start_row=idx_r, start_column=1, end_row=idx_r, end_column=6)
        c = ws.cell(idx_r, 1, f"[RİSK] {rtext}")
        c.fill, c.border, c.alignment = st["warn"], st["border"], Alignment(wrap_text=True, vertical="center")
        ws.row_dimensions[idx_r].height = 26
    for ci, w in enumerate([10, 32, 26, 30, 22, 46], start=1):
        ws.column_dimensions[get_column_letter(ci)].width = w


def _populate_excel_form12_and_cost(
    wb: Workbook, metadata: dict[str, str], plan: dict[str, Any], st: dict[str, Any]
) -> None:
    ws_f1: Any = wb.create_sheet("Form 1-2 - Parça & Malzeme")
    ws_f1.merge_cells("A1:D1")
    ws_f1["A1"].value, ws_f1["A1"].font, ws_f1["A1"].fill = "AS9102 FORM 1 & 2 — PARÇA TANIMLAMA, MALZEME VE İZLENEBİLİRLİK", Font(size=12, bold=True, color="FFFFFF"), st["navy"]
    ws_f1.row_dimensions[1].height = 26
    f1_rows = [
        ("1. Parça Numarası", metadata.get("part_number") or "—", "2. Parça Adı", metadata.get("part_name") or "—"),
        ("3. Revizyon", metadata.get("revision") or "A", "4. Genel Tolerans", metadata.get("standard") or "ISO 2768-mK"),
        ("5. Ham Malzeme", metadata.get("material") or "—", "6. Malzeme Sertifikası (3.1)", "Bekleniyor / Lot No: ____"),
        ("7. Isıl İşlem / Sertlik", "Çizim notlarına göre", "8. Yüzey Kaplama", "Çizim notlarına göre"),
        ("9. Toplam Karakteristik", str(plan["summary"]["total"]), "10. Kritik Karakteristik", str(plan["summary"]["critical"])),
        ("11. Hazırlayan (Mühendis)", "____________________", "12. Kalite Onayı (FAI)", "____________________"),
    ]
    _write_kv_grid(ws_f1, f1_rows, st, [26, 30, 26, 30])

    ws_cost: Any = wb.create_sheet("Maliyet & Fanuc G-Kodu")
    ws_cost.merge_cells("A1:D1")
    ws_cost["A1"].value, ws_cost["A1"].font, ws_cost["A1"].fill = "CNC OTOMATİK MALİYET, İŞLEME SÜRESİ TEKLİFİ VE FANUC G-KODU TASLAĞI", Font(size=12, bold=True, color="FFFFFF"), st["navy"]
    ws_cost.row_dimensions[1].height = 26
    ce, bd = plan.get("cost_estimate", {}), plan.get("cost_estimate", {}).get("breakdown_min", {})
    cost_rows = [
        ("Önerilen Ham Kütük Boyutu", ce.get("stock_dimensions", "-"), "Ham / Net Ağırlık (kg)", f"{ce.get('raw_weight_kg', 0)} kg / {ce.get('net_weight_kg', 0)} kg"),
        ("Hazırlık / Setup Süresi", f"{ce.get('setup_time_min', 0)} dk", "Parça Başı İşleme Süresi (Cycle)", f"{ce.get('cycle_time_min', 0)} dk"),
        ("Torna / Freze Süresi", f"{bd.get('turn_mill', 0)} dk", "Delik / Kılavuz Süresi", f"{bd.get('drill_tap', 0)} dk"),
        ("Taşlama Süresi", f"{bd.get('grinding', 0)} dk", "CMM / Kalite Kontrol Süresi", f"{bd.get('quality_cmm', 0)} dk"),
        ("Ham Malzeme Maliyeti", f"{ce.get('material_cost_tl', 0)} TL", "CNC İşçilik + Takım Maliyeti", f"{round(ce.get('machining_cost_tl', 0) + ce.get('tooling_cost_tl', 0), 2)} TL"),
        ("1 Adet (Prototip) Birim Teklif", f"{ce.get('unit_quote_1_tl', 0)} TL", "10 Adet Birim Teklif", f"{ce.get('unit_quote_10_tl', 0)} TL"),
        ("100 Adet (Seri) Birim Teklif", f"{ce.get('unit_quote_100_tl', 0)} TL", "Teklif Para Birimi", "TRY (KDV Hariç)"),
    ]
    _write_kv_grid(ws_cost, cost_rows, st, [28, 28, 28, 28])
    ws_cost.cell(12, 1, "BAŞLANGIÇ FANUC ISO G-KODU TASLAĞI").font = Font(bold=True, size=11, color="1E293B")
    for idx_g, gline in enumerate((plan.get("gcode_template") or "").splitlines(), start=13):
        ws_cost.merge_cells(start_row=idx_g, start_column=1, end_row=idx_g, end_column=4)
        ws_cost.cell(idx_g, 1, gline).font = Font(name="Consolas", size=9.5)


def _write_kv_grid(ws: Any, rows: list[tuple[str, str, str, str]], st: dict[str, Any], widths: list[int]) -> None:
    for r_i, tup in enumerate(rows, start=3):
        for c_i, v in enumerate(tup, start=1):
            cell = ws.cell(r_i, c_i, v)
            cell.border = st["border"]
            if c_i in (1, 3):
                cell.font, cell.fill = Font(bold=True), st["meta"]
    for ci, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(ci)].width = w


def export_excel_report(balloons: list[BalloonItem], metadata: dict[str, str], out_path: Path) -> Path:
    """Create a comprehensive 4-sheet AS9102 / FAI & CNC Manufacturing Process Excel workbook."""
    plan = build_cnc_manufacturing_plan(balloons, metadata)
    wb = Workbook()
    ws: Any = wb.active
    if ws is None:
        raise RuntimeError("OpenPyXL workbook has no active worksheet")
    st = _excel_styles()
    _populate_excel_form3(ws, balloons, metadata, plan, st)
    _populate_excel_process_sheet(wb, plan, st)
    _populate_excel_form12_and_cost(wb, metadata, plan, st)
    wb.save(str(out_path))
    return out_path


def _style_word_cell(cell: Any, text: str, size_pt: float, bold: bool = False) -> None:
    cell.text = text
    for p in cell.paragraphs:
        for r in p.runs:
            r.bold = bold
            r.font.size = Pt(size_pt)


def _word_add_form3_table(doc: Any, balloons: list[BalloonItem]) -> None:
    doc.add_heading(f"2. AS9102 Form 3 — Karakteristik, Operasyon ve Ölçüm Tablosu ({len(balloons)} Balon)", level=1)
    tbl = doc.add_table(rows=1, cols=9)
    tbl.style = "Table Grid"
    for i, text in enumerate(["No", "Bölge", "Ölçü", "Kategori", "Min / Max", "Operasyon", "Kesici Takım", "Ölçüm Aleti", "Sıklık"]):
        _style_word_cell(tbl.rows[0].cells[i], text, 8.0, bold=True)
    for b in balloons:
        row_cells = tbl.add_row().cells
        mm = f"{b.min_limit:g} / {b.max_limit:g}" if (b.min_limit is not None and b.max_limit is not None) else "—"
        vals = [str(b.balloon_no), b.zone or "—", b.raw_text, b.category, mm, b.operation, b.tooling, b.gage, b.inspection_freq]
        for i, val in enumerate(vals):
            _style_word_cell(row_cells[i], val, 7.5)


def _word_add_process_and_cost(doc: Any, plan: dict[str, Any]) -> None:
    doc.add_heading("3. CNC Operasyon Rotası ve Kesme Parametreleri", level=1)
    cp = plan["cutting_parameters"]
    doc.add_paragraph(
        f"Malzeme Grubu: {cp['group']} | Torna Vc: {cp['vc_turn']} | Freze Vc: {cp['vc_mill']} | "
        f"İlerleme: {cp['feed']} | Soğutma: {cp['coolant']}. Not: {cp['note']}"
    )
    op_tbl = doc.add_table(rows=1, cols=5)
    op_tbl.style = "Table Grid"
    for i, ht in enumerate(["OP", "Operasyon", "Tezgâh", "Bağlama / Fikstür", "Balonlar"]):
        _style_word_cell(op_tbl.rows[0].cells[i], ht, 8.5, bold=True)
    for op in plan["operations"]:
        rc = op_tbl.add_row().cells
        b_str = ", ".join(f"#{n}" for n in op["balloons"]) if op["balloons"] else "Genel"
        for i, val in enumerate([op["op"], op["name"], op["machine"], op["fixture"], b_str]):
            _style_word_cell(rc[i], val, 8.0)

    doc.add_heading("4. DFM ve Kritik İmalat Risk Analizi", level=1)
    for risk in plan["dfm_risks"]:
        doc.add_paragraph(risk, style="List Bullet")

    if (ce := plan.get("cost_estimate")):
        doc.add_heading("5. Otomatik Maliyet, İşleme Süresi ve Teklif Hesabı", level=1)
        doc.add_paragraph(
            f"Ham Kütük: {ce.get('stock_dimensions')} ({ce.get('raw_weight_kg')} kg ham / {ce.get('net_weight_kg')} kg net) | "
            f"Parça Başı İşleme Süresi: {ce.get('cycle_time_min')} dk (Setup: {ce.get('setup_time_min')} dk) | "
            f"Birim Teklif: 1 Adet = {ce.get('unit_quote_1_tl')} TL · 10 Adet = {ce.get('unit_quote_10_tl')} TL · 100 Adet = {ce.get('unit_quote_100_tl')} TL."
        )
    if plan.get("gcode_template"):
        doc.add_heading("6. Başlangıç Fanuc G-Kodu Taslağı", level=1)
        for r in doc.add_paragraph(plan["gcode_template"]).runs:
            r.font.size = Pt(8)


def export_word_report(
    ballooned_img_path: Path, balloons: list[BalloonItem], metadata: dict[str, str], out_path: Path
) -> Path:
    """Create a comprehensive Mechanical Engineering CNC Ballooning & Process Plan Word (.docx) report."""
    plan = build_cnc_manufacturing_plan(balloons, metadata)
    doc = Document()
    title = doc.add_heading("CNC İmalat, Teknik Çizim Balonlama ve Kalite Kontrol Raporu (AS9102 / FAI)", level=0)
    for run in title.runs:
        run.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)

    meta_table = doc.add_table(rows=3, cols=4)
    meta_table.style = "Table Grid"
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    s = plan["summary"]
    pairs = [
        ("Parça No", metadata.get("part_number") or "—", "Parça Adı", metadata.get("part_name") or "—"),
        ("Malzeme", metadata.get("material") or "—", "Standart / Rev", f"{metadata.get('standard', 'ISO 2768-mK')} / Rev {metadata.get('revision', 'A')}"),
        ("Toplam Balon", str(s["total"]), "Kritik / Majör / Minör", f"{s['critical']} / {s['major']} / {s['minor']}"),
    ]
    for r_i, (k1, v1, k2, v2) in enumerate(pairs):
        cells = meta_table.rows[r_i].cells
        _style_word_cell(cells[0], k1, 9.0, bold=True)
        cells[1].text = v1
        _style_word_cell(cells[2], k2, 9.0, bold=True)
        cells[3].text = v2

    doc.add_heading("1. Balonlanmış Teknik Çizim", level=1)
    if ballooned_img_path.exists():
        doc.add_picture(str(ballooned_img_path), width=Inches(6.3))
    _word_add_form3_table(doc, balloons)
    _word_add_process_and_cost(doc, plan)
    doc.save(str(out_path))
    return out_path
