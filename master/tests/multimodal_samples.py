"""Real sample files for milestone 09, generated on the spot: PDFs, a scan, an ugly workbook, speech and video."""

from __future__ import annotations

import io
import wave
from pathlib import Path

import pymupdf
from openpyxl import Workbook

_FONT = next((p for p in (Path("C:/Windows/Fonts/arial.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")) if p.is_file()), None)
SCAN_LINES = ["Depo Teslim Tutanağı", "Teslim eden: Ayşe Yılmaz", "Şişe kapağı koli sayısı: 1.250", "Toplam ağırlık: 842,5 kg", "Kontrol sonucu: uygun, iğne hasarı yok."]
SPOKEN = "Üçüncü hattaki dolum makinesi salı günü bakıma alınacak. Bakım dört saat sürecek ve sorumlusu Mehmet."


def _write(page: pymupdf.Page, rows: list[tuple[float, float, str]], size: float = 12) -> None:
    writer = pymupdf.TextWriter(page.rect)
    font = pymupdf.Font(fontfile=str(_FONT)) if _FONT else pymupdf.Font("helv")
    for x, y, text in rows:
        writer.append((x, y), text, font=font, fontsize=size)
    writer.write_text(page)


def two_column_pdf() -> bytes:
    """A heading, two columns whose lines interleave by height, a formula and a ruled table with a merged cell."""
    document = pymupdf.open()
    page = document.new_page(width=595, height=842)
    _write(page, [(60, 60, "Yıllık Kalite Raporu: Dolum ve Paketleme Hatlarının Ayrıntılı Değerlendirmesi Hakkında")], 11)
    for index in range(3):
        _write(page, [(60, 120 + index * 60, f"Sol sütun paragraf {index + 1}: dolum")], 11)
        _write(page, [(340, 100 + index * 60, f"Sağ sütun paragraf {index + 1}: paket")], 11)
    _write(page, [(60, 330, "Verim = (uretim - hata) / uretim * 100")])
    x, y = (60, 200, 340, 480), (380, 405, 430, 455)
    for number, top in enumerate(y):
        page.draw_line((x[1] if number == 2 else x[0], top), (x[-1], top))  # no line inside the merged "Hat A" cell
    for left in x:
        page.draw_line((left, y[0]), (left, y[-1]))
    for row, cells in enumerate((("Hat", "Ay", "Adet"), ("Hat A", "Ocak", "120"), ("", "Şubat", "135"))):
        _write(page, [(x[col] + 6, y[row] + 17, text) for col, text in enumerate(cells) if text])
    return document.tobytes()


def scanned_pdf(turned: int = 0) -> bytes:
    """Pages that are only pictures of text; `turned` degrees makes a sideways scan."""
    source = pymupdf.open()
    page = source.new_page(width=595, height=420)
    _write(page, [(50, 70 + index * 45, line) for index, line in enumerate(SCAN_LINES)], 17)
    picture = page.get_pixmap(matrix=pymupdf.Matrix(200 / 72, 200 / 72).prerotate(turned)).tobytes("png")
    document = pymupdf.open()
    width, height = (420, 595) if turned in (90, 270) else (595, 420)
    document.new_page(width=width, height=height).insert_image(pymupdf.Rect(0, 0, width, height), stream=picture)
    return document.tobytes()


def messy_workbook() -> bytes:
    """Title rows above the header, a merged label, Turkish amounts, text dates and an empty column."""
    book = Workbook()
    sheet = book.active
    sheet.title = "Satış"
    sheet.append(["ACME Lojistik - 2026 sevkiyat listesi"])
    sheet.append([None])
    sheet.append(["Bölge", "Tarih", None, "Ürün", "Tutar", "Adet"])
    for row in (["Marmara", "03.01.2026", None, "Şişe", "1.250,50 TL", "12"], [None, "15.01.2026", None, "Kapak", "980,00 TL", "7"],
                ["Ege", "02.02.2026", None, "İğne", "12.480,75 TL", "1.250"]):
        sheet.append(row)
    sheet.merge_cells("A4:A5")
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


def speech(path: Path, voice: Path, text: str = SPOKEN) -> Path:
    """Real speech from the local Turkish voice."""
    from piper import PiperVoice

    spoken = PiperVoice.load(str(voice))
    with wave.open(str(path), "wb") as out:
        spoken.synthesize_wav(text, out)
    return path


def video(path: Path) -> Path:
    """Nine seconds with two clear scene changes."""
    import av
    import numpy as np

    with av.open(str(path), "w") as container:
        stream = container.add_stream("mpeg4", rate=10)
        stream.width, stream.height, stream.pix_fmt = 160, 96, "yuv420p"
        for number in range(90):
            shade = (20, 130, 240)[number // 30]
            frame = av.VideoFrame.from_ndarray(np.full((96, 160, 3), shade, dtype=np.uint8), format="rgb24")
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return path
