"""Extra procedural scene variants: bright daytime landscape and sunset over the sea."""

from __future__ import annotations


def _is_light_palette(pal: dict[str, str]) -> bool:
    h = pal["bg1"].lstrip("#")
    return sum(int(h[i : i + 2], 16) for i in (0, 2, 4)) / 3 > 200


def _scene_nature_day_layers(seed: int) -> list[str]:
    sx = 600 + ((seed % 3) - 1) * 190
    grads = (
        '<defs><linearGradient id="gDay" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#38bdf8"/><stop offset="100%" stop-color="#e0f2fe"/></linearGradient>'
        '<linearGradient id="gLake" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#7dd3fc"/><stop offset="100%" stop-color="#0ea5e9"/></linearGradient></defs>'
    )
    layers = [
        grads,
        '<rect x="0" y="0" width="1200" height="490" fill="url(#gDay)"/>',
        f'<circle cx="{sx}" cy="150" r="110" fill="#fef9c3" opacity="0.45"/><circle cx="{sx}" cy="150" r="62" fill="#fde047"/>',
        '<g fill="#ffffff" opacity="0.92"><ellipse cx="250" cy="130" rx="95" ry="24"/><ellipse cx="310" cy="112" rx="60" ry="22"/>'
        '<ellipse cx="900" cy="190" rx="110" ry="26"/><ellipse cx="960" cy="168" rx="64" ry="22"/></g>',
        '<polygon points="0,475 180,260 390,410 610,230 850,395 1040,275 1200,385 1200,490 0,490" fill="#94a3b8"/>',
        '<polygon points="180,260 230,318 150,318" fill="#f8fafc"/><polygon points="610,230 670,305 560,305" fill="#f8fafc"/><polygon points="1040,275 1090,330 995,330" fill="#f8fafc"/>',
        '<polygon points="0,490 120,355 310,440 520,315 740,445 960,335 1200,440 1200,490" fill="#4d7c0f"/>',
        '<rect x="0" y="485" width="1200" height="275" fill="url(#gLake)"/>',
        '<path d="M0,695 Q320,655 600,700 T1200,680 L1200,760 L0,760 Z" fill="#65a30d"/>',
    ]
    layers.extend(f'<rect x="{tx - 6}" y="{680 - (tx % 40)}" width="12" height="46" fill="#78350f"/><circle cx="{tx}" cy="{665 - (tx % 40)}" r="40" fill="#15803d"/>' for tx in (70, 150, 1040, 1130))
    return layers


def _scene_sunset_layers(seed: int) -> list[str]:
    sx = 600 + ((seed % 3) - 1) * 150
    grads = (
        '<defs><linearGradient id="gSun" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#312e81"/><stop offset="45%" stop-color="#be185d"/>'
        '<stop offset="80%" stop-color="#f97316"/><stop offset="100%" stop-color="#fde047"/></linearGradient>'
        '<linearGradient id="gSea" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#f97316"/><stop offset="100%" stop-color="#1e1b4b"/></linearGradient></defs>'
    )
    layers = [
        grads,
        '<rect x="0" y="0" width="1200" height="500" fill="url(#gSun)"/>',
        f'<circle cx="{sx}" cy="440" r="150" fill="#fde68a" opacity="0.35"/><circle cx="{sx}" cy="440" r="86" fill="#fef08a"/>',
        '<g fill="#fff7ed" opacity="0.55"><ellipse cx="260" cy="170" rx="120" ry="16"/><ellipse cx="920" cy="130" rx="150" ry="14"/></g>',
        '<rect x="0" y="498" width="1200" height="262" fill="url(#gSea)"/>',
    ]
    layers.extend(
        f'<rect x="{sx - (200 - i * 13) // 2}" y="{512 + i * 17}" width="{max(30, 200 - i * 13)}" height="5" rx="2" fill="#fde68a" opacity="{0.8 - i * 0.05:.2f}"/>'
        for i in range(14)
    )
    layers.append('<path d="M0,500 Q160,452 330,500 T700,498 T1200,500 L1200,520 L0,520 Z" fill="#1e1b4b" opacity="0.9"/>')
    return layers
