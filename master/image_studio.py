"""Cluster B (`[M20]`, Faz 5.4 & Faz 18.2): AI Image Studio & Multi-Layer Corporate Infographic SVG/PNG Generator.

Re-exports:
- `generate_ai_image`
- `process_and_edit_image`
- `is_image_generation_request`
- `is_image_edit_request`
from `multimodal_studio`, and provides:
- `generate_infographic_svg(title: str, metrics: list[dict]) -> dict`
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

import pymupdf as fitz
from PIL import Image, ImageDraw

from multimodal_studio import (
    _load_font,
    generate_ai_image,
    is_image_edit_request,
    is_image_generation_request,
    media_dir,
    process_and_edit_image,
)

__all__ = [
    "generate_ai_image",
    "generate_infographic_svg",
    "is_image_edit_request",
    "is_image_generation_request",
    "process_and_edit_image",
]

_CARD_ACCENTS = ("#4f46e5", "#06b6d4", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6")


def _xml_escape(text: str) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _extract_numeric(val: Any) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    m = re.search(r"[-+]?\d+(?:[.,]\d+)?", str(val or ""))
    if not m:
        return 50.0
    try:
        return float(m.group(0).replace(",", "."))
    except ValueError:
        return 50.0


def generate_infographic_svg(title: str, metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate a multi-layer corporate infographic SVG and high-DPI PNG saved to `media_dir()`."""
    clean_title = _xml_escape((title or "Kurumsal Performans İnfografiği").strip()[:80])
    safe_metrics = list(metrics or [])
    if not safe_metrics:
        safe_metrics = [
            {"label": "Verimlilik", "value": "94%", "trend": "+12%"},
            {"label": "Üretim Kalitesi", "value": "99.2%", "trend": "+3.1%"},
            {"label": "Teslimat Süresi", "value": "1.8 Gün", "trend": "-24%"},
        ]

    file_id = f"infographic-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    out_svg = media_dir() / f"{file_id}.svg"
    out_png = media_dir() / f"{file_id}.png"

    numeric_vals = [abs(_extract_numeric(m.get("value", 50))) for m in safe_metrics[:6]]
    max_num = max(numeric_vals) if numeric_vals and max(numeric_vals) > 0 else 100.0

    cards_svg: list[str] = []
    bars_svg: list[str] = []

    for idx, item in enumerate(safe_metrics[:6]):
        col = idx % 3
        row = idx // 3
        cx = 70 + col * 365
        cy = 150 + row * 175
        accent = _CARD_ACCENTS[idx % len(_CARD_ACCENTS)]
        label = _xml_escape(str(item.get("label") or item.get("name") or f"Metrik {idx + 1}")[:32])
        val_str = _xml_escape(str(item.get("value", "0"))[:20])
        trend_str = _xml_escape(str(item.get("trend") or item.get("unit") or "")[:18])

        cards_svg.append(
            f"""  <g transform="translate({cx}, {cy})">
    <rect width="335" height="145" rx="16" fill="#1e293b" stroke="{accent}" stroke-width="2"/>
    <rect x="0" y="0" width="8" height="145" rx="4" fill="{accent}"/>
    <text x="26" y="42" fill="#94a3b8" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="600">{label}</text>
    <text x="26" y="92" fill="#f8fafc" font-family="Segoe UI, Arial, sans-serif" font-size="36" font-weight="bold">{val_str}</text>
    <text x="26" y="124" fill="{accent}" font-family="Segoe UI, Arial, sans-serif" font-size="15" font-weight="600">{trend_str}</text>
  </g>"""
        )

        # Bottom comparative bar chart layer
        bar_y = 530 + idx * 34
        ratio = min(1.0, max(0.08, numeric_vals[idx] / max_num))
        bar_w = int(680 * ratio)
        bars_svg.append(
            f"""  <g transform="translate(70, {bar_y})">
    <text x="0" y="18" fill="#cbd5e1" font-family="Segoe UI, Arial, sans-serif" font-size="14">{label}</text>
    <rect x="240" y="2" width="680" height="20" rx="10" fill="#0f172a"/>
    <rect x="240" y="2" width="{bar_w}" height="20" rx="10" fill="{accent}"/>
    <text x="935" y="18" fill="#f8fafc" font-family="Segoe UI, Arial, sans-serif" font-size="14" font-weight="bold">{val_str}</text>
  </g>"""
        )

    svg_code = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 780" width="1200" height="780">
  <defs>
    <linearGradient id="bgGrad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#090d16"/>
      <stop offset="50%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#1e1b4b"/>
    </linearGradient>
    <linearGradient id="headerBar" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#4f46e5"/>
      <stop offset="100%" stop-color="#06b6d4"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="780" fill="url(#bgGrad)"/>
  <rect x="70" y="45" width="1060" height="76" rx="14" fill="#1e293b" stroke="url(#headerBar)" stroke-width="2"/>
  <text x="105" y="93" fill="#f8fafc" font-family="Segoe UI, Arial, sans-serif" font-size="28" font-weight="bold">{clean_title}</text>
{chr(10).join(cards_svg)}
  <rect x="55" y="505" width="1090" height="240" rx="16" fill="#1e293b" opacity="0.75" stroke="#334155" stroke-width="1.5"/>
{chr(10).join(bars_svg)}
</svg>"""

    out_svg.write_text(svg_code, encoding="utf-8")

    try:
        svg_doc = fitz.open(stream=svg_code.encode("utf-8"), filetype="svg")
        pix = svg_doc[0].get_pixmap(dpi=150)
        pix.save(str(out_png))
        svg_doc.close()
    except Exception:
        im = Image.new("RGB", (1200, 780), (15, 23, 42))
        dr = ImageDraw.Draw(im)
        dr.rectangle([50, 45, 1150, 735], outline=(79, 70, 229), width=3)
        dr.text((90, 75), title[:60], fill=(248, 250, 252), font=_load_font(26, bold=True))
        im.save(out_png, format="PNG")

    return {
        "file_id": file_id,
        "title": title,
        "metric_count": len(safe_metrics),
        "svg_path": str(out_svg),
        "png_path": str(out_png),
        "svg_url": f"/api/assistant/media/{file_id}.svg",
        "png_url": f"/api/assistant/media/{file_id}.png",
        "svg_content": svg_code,
    }
