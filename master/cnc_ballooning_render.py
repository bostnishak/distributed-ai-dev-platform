"""Visual CNC Ballooning Renderer & Synthetic CNC Technical Drawing Generators (PDF/PNG/DXF)."""

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path

import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont

from cnc_ballooning_plan import BalloonItem


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        ["arialbd.ttf", "DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
        if bold
        else ["arial.ttf", "DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _render_spec_sheet_image(title: str, lines: list[str]) -> Image.Image:
    """Fallback visual sheet when DOCX/XLSX has dimension tables but no embedded drawing image."""
    width = 1600
    height = max(900, 180 + len(lines) * 44)
    img = Image.new("RGB", (width, height), (252, 253, 255))
    draw = ImageDraw.Draw(img)
    font_title = _load_font(26, bold=True)
    font_body = _load_font(18, bold=False)

    draw.rectangle([20, 20, width - 20, height - 20], outline=(30, 41, 59), width=3)
    draw.rectangle([20, 20, width - 20, 88], fill=(30, 41, 59))
    draw.text((44, 40), f"CNC TEKNİK ÖZELLİK VE ÖLÇÜ LİSTESİ — {title}", fill=(255, 255, 255), font=font_title)

    y = 120
    for line in lines:
        draw.line([(40, y + 32), (width - 40, y + 32)], fill=(226, 232, 240), width=1)
        draw.text((110, y), line[:115], fill=(15, 23, 42), font=font_body)
        y += 44
    return img


_BALLOON_OFFSETS = [
    (-2.2, -1.9), (2.2, -1.9), (-2.2, 1.9), (2.2, 1.9),
    (0.0, -2.5), (0.0, 2.5), (-3.0, 0.0), (3.0, 0.0),
    (-3.2, -2.6), (3.2, -2.6), (-3.2, 2.6), (3.2, 2.6),
]


def _pick_balloon_center(
    target: tuple[float, float, float, float],
    canvas_size: tuple[int, int],
    radius: int,
    placed: list[tuple[float, float]],
) -> tuple[float, float]:
    tx, ty, bw, bh = target
    w, h = canvas_size
    min_dist = radius * 2.45
    for ox, oy in _BALLOON_OFFSETS:
        cx = tx + ox * radius + (bw * 0.35 if ox > 0 else (-bw * 0.35 if ox < 0 else 0))
        cy = ty + oy * radius + (bh * 0.35 if oy > 0 else (-bh * 0.35 if oy < 0 else 0))
        cx = max(radius + 6, min(w - radius - 6, cx))
        cy = max(radius + 6, min(h - radius - 6, cy))
        if all(math.hypot(cx - px, cy - py) >= min_dist for px, py in placed):
            return cx, cy
    return tx - radius * 2.2, ty - radius * 1.8


def render_ballooned_image(
    base_img: Image.Image,
    balloons: list[BalloonItem],
    metadata: dict[str, str],
) -> Image.Image:
    """Draw non-overlapping numbered red CNC balloons + leader lines onto the technical drawing."""
    w, h = base_img.size
    footer_h = max(48, int(h * 0.045))
    canvas = Image.new("RGB", (w, h + footer_h), (255, 255, 255))
    canvas.paste(base_img, (0, 0))
    draw = ImageDraw.Draw(canvas)

    radius = max(14, min(26, int(min(w, h) * 0.016)))
    font_num = _load_font(max(12, int(radius * 1.1)), bold=True)
    font_foot = _load_font(max(13, int(footer_h * 0.36)), bold=False)
    placed: list[tuple[float, float]] = []

    for b in balloons:
        tx, ty = b.x_pct / 100.0 * w, b.y_pct / 100.0 * h
        bw, bh = max(radius * 1.5, b.w_pct / 100.0 * w * 0.5), max(radius * 0.8, b.h_pct / 100.0 * h * 0.5)
        cx, cy = _pick_balloon_center((tx, ty, bw, bh), (w, h), radius, placed)
        placed.append((cx, cy))

        dx, dy = tx - cx, ty - cy
        dist = math.hypot(dx, dy) or 1.0
        scale = max(0.35, 1.0 - (min(bw, bh) * 0.45) / dist)
        ax, ay = cx + dx * scale, cy + dy * scale
        draw.line([(cx, cy), (ax, ay)], fill=(255, 255, 255), width=max(4, radius // 4 + 2))
        draw.line([(cx, cy), (ax, ay)], fill=(220, 38, 38), width=max(2, radius // 7))

        dot_r = max(3, radius // 6)
        draw.ellipse([ax - dot_r, ay - dot_r, ax + dot_r, ay + dot_r], fill=(220, 38, 38))
        ring = max(2, radius // 7)
        draw.ellipse([cx - radius - ring, cy - radius - ring, cx + radius + ring, cy + radius + ring], fill=(255, 255, 255))
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=(220, 38, 38), outline=(153, 27, 27), width=2)

        label = str(b.balloon_no)
        bbox = draw.textbbox((0, 0), label, font=font_num)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((cx - tw / 2, cy - th / 2 - bbox[1] * 0.65), label, fill=(255, 255, 255), font=font_num)

    draw.rectangle([0, h, w, h + footer_h], fill=(15, 23, 42))
    foot_text = (
        f"CNC BALONLAMA RAPORU  |  Parça: {metadata.get('part_name') or 'Teknik Çizim'} ({metadata.get('part_number') or '—'})  |  "
        f"Malzeme: {metadata.get('material') or '—'}  |  Standart: {metadata.get('standard') or 'ISO 2768-mK'}  |  "
        f"Toplam Balon: {len(balloons)}  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    draw.text((18, h + int(footer_h * 0.28)), foot_text, fill=(241, 245, 249), font=font_foot)
    return canvas


def _draw_sample_front_view(page: fitz.Page) -> None:
    navy, dim_col, center_col, light = (0.08, 0.12, 0.2), (0.12, 0.28, 0.55), (0.75, 0.15, 0.15), (0.55, 0.6, 0.68)
    cx, cy = 245, 290
    page.draw_line((cx - 155, cy), (cx + 155, cy), color=center_col, width=0.7, dashes="[6 3 1 3]")
    page.draw_line((cx, cy - 155), (cx, cy + 155), color=center_col, width=0.7, dashes="[6 3 1 3]")
    page.draw_circle((cx, cy), 128, color=navy, width=1.8)
    page.draw_circle((cx, cy), 96, color=center_col, width=0.7, dashes="[5 3]")
    page.draw_circle((cx, cy), 66, color=navy, width=1.2)
    page.draw_circle((cx, cy), 48, color=navy, width=1.8)
    for deg in (45, 135, 225, 315):
        rad = math.radians(deg)
        hx, hy = cx + 96 * math.cos(rad), cy + 96 * math.sin(rad)
        page.draw_circle((hx, hy), 10, color=navy, width=1.3)
        page.draw_circle((hx, hy), 13, color=light, width=0.6, dashes="[3 2]")
        page.draw_line((hx - 15, hy), (hx + 15, hy), color=center_col, width=0.5)
        page.draw_line((hx, hy - 15), (hx, hy + 15), color=center_col, width=0.5)
    page.draw_rect(fitz.Rect(cx - 10, cy - 57, cx + 10, cy - 46), color=navy, fill=(1, 1, 1), width=1.4)
    front_dims = [
        ((cx - 52, cy - 144), "Ø110 ±0.05"), ((cx + 78, cy - 122), "Ø80 ±0.03"),
        ((cx - 34, cy - 8), "Ø42 H7"), ((cx + 72, cy + 88), "4x Ø9 THRU"),
        ((cx - 148, cy + 118), "4x M8x1.25-6H"), ((cx - 150, cy - 105), "R5 ±0.1"),
        ((cx + 98, cy - 42), "45° ±0.5°"), ((cx - 28, cy - 72), "10.0 +0.03/-0.00"),
    ]
    for pos, txt in front_dims:
        page.insert_text(pos, txt, fontsize=10, color=dim_col)
    page.insert_text((cx - 55, cy + 168), "FRONT VIEW (A-A)", fontsize=9, color=navy)


def _draw_sample_side_and_title(page: fitz.Page) -> None:
    navy, dim_col, center_col = (0.08, 0.12, 0.2), (0.12, 0.28, 0.55), (0.75, 0.15, 0.15)
    sx, sy = 575, 290
    page.draw_rect(fitz.Rect(sx - 55, sy - 128, sx - 15, sy + 128), color=navy, width=1.8)
    page.draw_rect(fitz.Rect(sx - 15, sy - 66, sx + 55, sy + 66), color=navy, width=1.8)
    page.draw_line((sx - 55, sy - 48), (sx + 55, sy - 48), color=navy, width=1.0, dashes="[4 3]")
    page.draw_line((sx - 55, sy + 48), (sx + 55, sy + 48), color=navy, width=1.0, dashes="[4 3]")
    page.draw_line((sx - 80, sy), (sx + 85, sy), color=center_col, width=0.7, dashes="[6 3 1 3]")
    for p1, p2, w in [
        ((sx - 55, sy - 148), (sx + 55, sy - 148), 0.8), ((sx - 55, sy - 128), (sx - 55, sy - 154), 0.6),
        ((sx + 55, sy - 66), (sx + 55, sy - 154), 0.6), ((sx - 55, sy + 148), (sx - 15, sy + 148), 0.8),
        ((sx + 88, sy - 66), (sx + 88, sy + 66), 0.8),
    ]:
        page.draw_line(p1, p2, color=dim_col, width=w)
    side_dims = [
        ((sx - 25, sy - 155), "36.0 ±0.05"), ((sx - 60, sy + 162), "14.0 ±0.05"), ((sx + 94, sy - 4), "Ø56 h6"),
        ((sx + 62, sy - 88), "2x45°"), ((sx + 62, sy + 88), "Ra 0.8"), ((sx - 118, sy - 92), "Ra 1.6"),
        ((sx + 58, sy - 122), "FLAT 0.02"), ((sx + 58, sy + 124), "PERP 0.03 A"), ((sx - 135, sy + 95), "CONC 0.02 A"),
    ]
    for (tx, ty), txt in side_dims:
        if txt.startswith(("FLAT", "PERP", "CONC")):
            page.draw_rect(fitz.Rect(tx - 4, ty - 11, tx + len(txt) * 6.2 + 4, ty + 4), color=dim_col, width=0.8)
        page.insert_text((tx, ty), txt, fontsize=10, color=dim_col)
    page.insert_text((sx - 45, sy + 184), "SECTION VIEW A-A", fontsize=9, color=navy)

    page.draw_rect(fitz.Rect(525, 470, 818, 571), color=navy, fill=(0.97, 0.98, 1.0), width=1.4)
    for y_line in (496, 522, 546):
        page.draw_line((525, y_line), (818, y_line), color=navy, width=0.8)
    page.draw_line((670, 496), (670, 571), color=navy, width=0.8)
    for pos, txt, fs in [
        ((533, 487), "PART NAME: CNC BEARING HOUSING FLANGE", 9), ((533, 513), "PART NO: FLN-2026-042", 8.5),
        ((678, 513), "REV: B", 8.5), ((533, 538), "MATERIAL: AISI 4140 STEEL", 8.5), ((678, 538), "SCALE: 1:1", 8.5),
        ((533, 562), "TOLERANCE: ISO 2768-mK", 8.5), ((678, 562), "UNIT: MM", 8.5),
        ((34, 540), "NOTE: ALL DIMENSIONS IN MM. DEBURR ALL SHARP EDGES 0.3 MAX.", 8),
        ((34, 556), "UNLESS OTHERWISE SPECIFIED: ISO 2768-mK · CNC 5-AXIS TURNING/MILLING", 8),
    ]:
        page.insert_text(pos, txt, fontsize=fs, color=navy)


def generate_sample_cnc_drawing_pdf(out_pdf: Path, out_png: Path | None = None) -> Path:
    """Generate a realistic vector CNC Machined Bearing Housing Flange technical drawing (PDF + optional PNG)."""
    doc = fitz.open()
    page = doc.new_page(width=842, height=595)
    navy = (0.08, 0.12, 0.2)
    page.draw_rect(fitz.Rect(18, 18, 824, 577), color=navy, width=1.6)
    page.draw_rect(fitz.Rect(24, 24, 818, 571), color=navy, width=0.6)
    _draw_sample_front_view(page)
    _draw_sample_side_and_title(page)

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_pdf))
    if out_png is not None:
        out_png.parent.mkdir(parents=True, exist_ok=True)
        page.get_pixmap(dpi=220).save(str(out_png))
    doc.close()
    return out_pdf


def generate_sample_cnc_dxf(out_dxf: Path) -> Path:
    """Generate a realistic AutoCAD ASCII .DXF technical drawing of the CNC Bearing Housing Flange."""
    entities: list[str] = ["0", "SECTION", "2", "ENTITIES"]

    def add_circle(cx: float, cy: float, r: float) -> None:
        entities.extend(["0", "CIRCLE", "8", "0", "10", f"{cx}", "20", f"{cy}", "40", f"{r}"])

    def add_line(x1: float, y1: float, x2: float, y2: float) -> None:
        entities.extend(["0", "LINE", "8", "0", "10", f"{x1}", "20", f"{y1}", "11", f"{x2}", "21", f"{y2}"])

    for r in (55, 40, 28, 21):
        add_circle(120, 150, r)
    for deg in (45, 135, 225, 315):
        rad = math.radians(deg)
        add_circle(round(120 + 40 * math.cos(rad), 2), round(150 + 40 * math.sin(rad), 2), 4.5)
    for seg in ((240, 95, 260, 95), (260, 95, 260, 205), (260, 205, 240, 205), (240, 205, 240, 95),
                (260, 122, 295, 122), (295, 122, 295, 178), (295, 178, 260, 178)):
        add_line(*seg)
    callouts = [
        (95, 215, "%%c110 %%p0.05"), (155, 198, "%%c80 %%p0.03"), (108, 150, "%%c42 H7"), (155, 108, "4x %%c9 THRU"),
        (60, 98, "4x M8x1.25-6H"), (62, 195, "R5 %%p0.1"), (252, 218, "36.0 %%p0.05"), (235, 82, "14.0 %%p0.05"),
        (302, 150, "%%c56 h6"), (275, 190, "2x45%%d"), (275, 110, "Ra 0.8"), (215, 185, "Ra 1.6"),
        (275, 205, "FLAT 0.02"), (275, 92, "PERP 0.03 A"), (210, 112, "CONC 0.02 A"),
        (20, 35, "PART NAME: CNC BEARING HOUSING FLANGE"), (20, 25, "PART NO: FLN-2026-042"), (20, 15, "MATERIAL: AISI 4140 STEEL"),
    ]
    for tx, ty, txt in callouts:
        entities.extend(["0", "TEXT", "8", "DIMS", "10", f"{tx}", "20", f"{ty}", "40", "4.0", "1", txt])
    entities.extend(["0", "ENDSEC", "0", "EOF"])
    out_dxf.parent.mkdir(parents=True, exist_ok=True)
    out_dxf.write_text("\n".join(entities), encoding="utf-8")
    return out_dxf
