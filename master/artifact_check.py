"""Open a delivered file with a reader other than the one that wrote it and say what is wrong with it."""

from __future__ import annotations

from pathlib import Path

import office_verify


def _pdf(path: Path) -> list[str]:
    try:
        import pypdfium2
    except ImportError:
        return office_verify.check_pdf(path)
    try:
        document = pypdfium2.PdfDocument(path)
        try:
            if len(document) == 0:
                return ["PDF'te sayfa yok"]
            if not any(document[i].get_textpage().get_text_range().strip() for i in range(len(document))):
                image = document[0].render(scale=0.3).to_pil().convert("L")
                if image.getextrema()[0] > 250:
                    return ["PDF boş görünüyor"]
        finally:
            document.close()
    except pypdfium2.PdfiumError as exc:
        return [f"PDF açılamadı: {exc}"[:160]]
    return []


def _image(path: Path) -> list[str]:
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(path) as picture:
            picture.load()
            extrema = picture.convert("L").getextrema()
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        return [f"görsel açılamadı: {exc}"[:160]]
    return ["görsel tek renk: içerik yok"] if extrema[0] == extrema[1] else []


def problems(path: Path) -> list[str]:
    """[] when the file opens and has real content."""
    if not path.is_file() or path.stat().st_size == 0:
        return ["dosya yok ya da boş"]
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _pdf(path)
    if suffix in (".png", ".jpg", ".jpeg", ".webp"):
        return _image(path)
    if suffix in (".xlsx", ".docx", ".pptx"):
        found = office_verify.check(path)
        return ["LibreOffice olmadığı için denetlenemedi"] if found is None else found
    if suffix == ".svg":
        text = path.read_text(encoding="utf-8", errors="replace")
        return [] if "<svg" in text and any(tag in text for tag in ("<path", "<rect", "<circle", "<text", "<line", "<polygon")) else ["SVG içeriksiz"]
    return []
