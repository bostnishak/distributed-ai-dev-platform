"""Chat-reply wording for generated files, in the language the user wrote in."""

from __future__ import annotations

_TR = {
    "pptx_ready": "PowerPoint Sunumu Hazır",
    "theme": "Tema & Arka Plan",
    "transition": "Slayt Geçiş Animasyonu",
    "total": "Toplam",
    "slides": "slayt",
    "download_pptx": "Sunumu İndir (.PPTX)",
    "content": "Araştırılan Slayt İçeriği",
    "slide": "Slayt",
    "callout": "Vurgu Kartı",
    "file_ready": "Dosyası Hazır",
    "download": "Dosya İndirme Bağlantısı",
    "get": "İndir",
    "chart_note": "Grafik istedin ama tabloda grafiğe çevrilecek sayısal veri yok; sayı uydurmamak için grafik eklemedim. Verilerini yazarsan grafikli hazırlarım.",
    "note": "Not",
}
_EN = {
    "pptx_ready": "PowerPoint presentation ready",
    "theme": "Theme & background",
    "transition": "Slide transition",
    "total": "Total",
    "slides": "slides",
    "download_pptx": "Download presentation (.PPTX)",
    "content": "Slide content",
    "slide": "Slide",
    "callout": "Key insight",
    "file_ready": "file ready",
    "download": "Download link",
    "get": "download",
    "chart_note": "You asked for a chart, but the table has no numeric data to plot; I did not add one rather than invent numbers. Send your figures and I will add it.",
    "note": "Note",
}


def labels(prompt: str) -> dict[str, str]:
    """English labels when the request is in English, Turkish otherwise."""
    from document_factory import _detect_requested_language

    return _EN if _detect_requested_language(prompt) == "English" else _TR


_DAYS = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")


def now_context() -> str:
    """System-prompt line with the server's current date and time, so 'what day is it' has a real answer."""
    from datetime import datetime

    now = datetime.now()
    return (
        f"Güncel tarih ve saat (sunucu saati): {now:%d.%m.%Y} {_DAYS[now.weekday()]}, {now:%H:%M}. "
        "Tarih, gün veya saat sorulursa bunu kullan; canlı veri veya internet erişimin olmadığını unutma."
    )
