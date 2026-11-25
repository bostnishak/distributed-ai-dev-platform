"""Poster layout (SVG, 1200x760): text column on the left, subject emblem on the right, an information band along the bottom.

Everything that has no text is left out and the remaining blocks are centred, so a poster with only a title and a slogan is as
balanced as one with date, place and line-up.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import poster_icons

_Esc = Callable[[str], str]
_W, _H = 1200, 760
_BAND_Y = 590


def wrap(text: str, width: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return [*lines, cur] if cur else lines


def title_size(lines: list[str]) -> int:
    """Largest font size at which the longest title line still fits the 610 px text column (bold capitals are ~0.66 em wide)."""
    longest = max((len(x) for x in lines), default=8)
    return max(46, min(92, int(610 / (0.66 * longest))))


def _kicker(spec: dict[str, Any], pal: dict[str, str], y: int, font: str, esc: _Esc) -> str:
    w = max(150, len(spec["kicker"]) * 14 + 40)
    return (
        f'<rect x="92" y="{y}" width="{w}" height="36" rx="18" fill="{pal["primary"]}" opacity="0.22" stroke="{pal["primary"]}" stroke-width="1.5"/>'
        f'<text x="{92 + w // 2}" y="{y + 23}" text-anchor="middle" fill="{pal["accent"]}" font-family="{font}" font-size="13" font-weight="700" letter-spacing="2.5">{esc(spec["kicker"])}</text>'
    )


def _text_column(spec: dict[str, Any], pal: dict[str, str], ctx: tuple[str, _Esc, bool]) -> list[str]:
    font, esc, has_info = ctx
    lines = wrap(spec["title"], 16)[:3] or [spec["title"]]
    size = title_size(lines)
    slogan = wrap(spec["slogan"], 28)[:2]
    height = (60 if spec["kicker"] else 0) + len(lines) * int(size * 1.12) + (24 + len(slogan) * 42 if slogan else 14)
    top, bottom = 90, (_BAND_Y - 20 if has_info else _H - 90)
    y = int(top + (bottom - top - height) / 2)
    out: list[str] = []
    if spec["kicker"]:
        out.append(_kicker(spec, pal, y, font, esc))
        y += 60
    y += size
    for i, line in enumerate(lines):
        out.append(f'<text x="92" y="{y}" fill="{pal["text"] if i % 2 == 0 else pal["accent"]}" font-family="{font}" font-size="{size}" font-weight="900" letter-spacing="1.5">{esc(line)}</text>')
        y += int(size * 1.12)
    out.append(f'<rect x="92" y="{y - int(size * 0.62)}" width="{min(260, 60 + size * 2)}" height="6" rx="3" fill="{pal["primary"]}"/>')
    y += 22
    for line in slogan:
        out.append(f'<text x="92" y="{y + 18}" fill="{pal["muted"]}" font-family="{font}" font-size="30" font-weight="600">{esc(line)}</text>')
        y += 42
    return out


def _info_band(spec: dict[str, Any], pal: dict[str, str], font: str, esc: _Esc) -> list[str]:
    """Bottom band: date, place and line-up pills, each only when the user supplied it."""
    out = [f'<rect x="92" y="{_BAND_Y}" width="1016" height="96" rx="22" fill="{pal["bg1"]}" opacity="0.82" stroke="{pal["accent"]}" stroke-opacity="0.4" stroke-width="1.5"/>']
    texts = [t for t in (spec["date"], spec["location"]) if t]
    tag_w = [max(110, len(t) * 12 + 34) + 12 for t in spec["tags"]]
    size = 28
    while size > 16 and sum(len(t) * size * 0.72 + 56 for t in texts) + sum(tag_w) > 1016 - 70:
        size -= 2  # shrink the text until date, place and tags fit on one line
    x, mid = 126, _BAND_Y + 48 + size // 2 - 4
    for i, text in enumerate(texts):
        if i:
            out.append(f'<rect x="{x - 28}" y="{_BAND_Y + 24}" width="2" height="48" fill="{pal["accent"]}" opacity="0.5"/>')
        out.append(f'<text x="{x}" y="{mid}" fill="{pal["accent"] if i == 0 else pal["text"]}" font-family="{font}" font-size="{size}" font-weight="800" letter-spacing="1">{esc(text)}</text>')
        x += int(len(text) * size * 0.72) + 56
    right = 1076
    for tag in reversed(spec["tags"]):
        w = max(110, len(tag) * 12 + 34)
        right -= w
        out.append(
            f'<rect x="{right}" y="{_BAND_Y + 29}" width="{w}" height="38" rx="19" fill="{pal["primary"]}" opacity="0.25" stroke="{pal["primary"]}" stroke-width="1.5"/>'
            f'<text x="{right + w // 2}" y="{_BAND_Y + 53}" text-anchor="middle" fill="{pal["text"]}" font-family="{font}" font-size="14" font-weight="700" letter-spacing="1.5">{esc(tag)}</text>'
        )
        right -= 12
    return out


def render(spec: dict[str, Any], palettes: dict[str, dict[str, str]], esc: _Esc, font: str) -> str:
    pal = palettes.get(spec["palette"], palettes["crimson_carbon"])
    has_info = bool(spec["date"] or spec["location"] or spec["tags"])
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_W} {_H}" width="{_W}" height="{_H}"><defs>',
        f'<linearGradient id="gBg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="{pal["bg1"]}"/><stop offset="55%" stop-color="{pal["bg2"]}"/><stop offset="100%" stop-color="{pal["bg3"]}"/></linearGradient>',
        f'</defs><rect x="0" y="0" width="{_W}" height="{_H}" fill="url(#gBg)"/>',
        f'<rect x="44" y="42" width="1112" height="676" rx="28" fill="{pal["card"]}" opacity="0.52" stroke="{pal["primary"]}" stroke-opacity="0.38" stroke-width="2"/>',
        poster_icons.emblem(spec.get("subject", ""), 900, 320 if has_info else 380, pal),
        *_text_column(spec, pal, (font, esc, has_info)),
    ]
    if has_info:
        out += _info_band(spec, pal, font, esc)
    return "\n".join([*out, "</svg>"])
