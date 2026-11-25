"""Universal Multimodal AI Studio: Multi-Mode Image Generation, CV Processing, and Voice-to-Text.

100% local, zero emojis, supporting 4 visual modes (logo_brand, diagram_infographic, poster_cover,
scene_illustration), local Diffusion (Automatic1111 / ComfyUI) auto-detection, CV editing, and STT.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

import config
from multimodal_studio_media import (
    IMAGE_EDIT_KEYWORDS,
    _decode_audio_to_float32_16k,
    _get_whisper_model,
    _load_font,
    is_image_edit_request,
    media_dir,
    process_and_edit_image,
    rasterize_svg_to_png,
    render_procedural_scene_svg,
    sanitize_svg,
    transcribe_audio_bytes,
    xml_esc,
)
from prompt_loader import load_prompt

__all__ = [
    "ARCHETYPE_ORDER", "IMAGE_ACTION_RE", "IMAGE_EDIT_KEYWORDS", "IMAGE_NOUN_RE", "LAYOUT_ORDER",
    "STUDIO_PALETTES", "_decode_audio_to_float32_16k", "_get_whisper_model", "_load_font",
    "classify_image_mode", "generate_ai_image", "is_image_edit_request", "is_image_generation_request",
    "media_dir", "pick_best_model", "process_and_edit_image", "sanitize_svg", "transcribe_audio_bytes",
]

_LOG = logging.getLogger(__name__)
_FONT = "Segoe UI, Inter, Arial, sans-serif"


async def pick_best_model(task: str = "general") -> str:
    """Dynamically route to the strongest installed local Ollama model for the task."""
    prefs_map = {
        "code": ["qwen2.5-coder:7b", "qwen3.5:9b", "qwen3.5:4b", config.MASTER_MODEL],
        "vision": ["qwen3.5:9b", "gemma4:e4b", "qwen3.5:4b", config.MASTER_MODEL],
        "deep": ["qwen3.5:9b", "gemma4:e4b", "qwen2.5-coder:7b", "qwen3.5:4b", config.MASTER_MODEL],
    }
    prefs = prefs_map.get(task, ["qwen3.5:9b", "qwen3.5:4b", config.MASTER_MODEL])
    try:
        async with httpx.AsyncClient(timeout=3.5) as client:
            resp = await client.get(f"{config.OLLAMA_URL}/api/tags")
            if resp.status_code == 200:
                installed = {m.get("name", "") for m in resp.json().get("models", [])}
                for cand in prefs:
                    if cand in installed:
                        return cand
    except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError) as exc:
        _LOG.debug("Recoverable error suppressed: %s", exc)
    return config.MASTER_MODEL


IMAGE_NOUN_RE = re.compile(
    r"\b(görsel\w*|gorsel\w*|fotoğraf\w*|fotograf\w*|resim\w*|resm\w*|manzara\w*|çizim\w*|cizim\w*|"
    r"illüstrasyon\w*|illustrasyon\w*|logo\w*|poster\w*|afiş\w*|afis\w*|amblem\w*|banner\w*|kapak\w*|"
    r"davetiye\w*|ilan\w*|ikon\w*|diyagram\w*|şema\w*|sema\w*|infografik\w*|mimari\w*|akış\w*|akis\w*|"
    r"roadmap\w*|harita\w*|sahne\w*|marka\s*kimli\w*|image\w*|photo\w*|picture\w*|illustration\w*|"
    r"drawing\w*|diagram\w*|flowchart\w*|infographic\w*|architecture\w*|icon\w*|emblem\w*|cover\w*|wallpaper\w*|scene\w*|artwork\w*)\b",
    re.IGNORECASE,
)
IMAGE_ACTION_RE = re.compile(
    r"\b(oluştur\w*|olustur\w*|üret\w*|uret\w*|çiz\w*|ciz\w*|tasarla\w*|yap\w*|hazırla\w*|hazirla\w*|"
    r"değiştir\w*|degistir\w*|yenile\w*|generate\w*|create\w*|draw\w*|design\w*|make\w*|render\w*|paint\w*|illustrate\w*|visualize\w*)\b",
    re.IGNORECASE,
)
_STRONG_VISUAL_RE = re.compile(
    r"\b(logo\w*|poster\w*|afiş\w*|afis\w*|amblem\w*|banner\w*|diyagram\w*|diagram\w*|şema\w*|sema\w*|"
    r"infografik\w*|infographic\w*|manzara\w*|illüstrasyon\w*|illustration\w*|resmi\b|görsel\w*|image\b)\b",
    re.IGNORECASE,
)


_DRAW_RE = re.compile(r"\b(?:çiz\w*|ciz\w*|draw\w*|sketch\w*|paint\w*|illustrate\w*)\b", re.IGNORECASE)
_CODE_WORD_RE = re.compile(r"\b(?:kod\w*|code|fonksiyon\w*|function|script\w*|program\w*|python|javascript|html|css|sql|algoritma\w*|grafik\w*|tablo\w*)\b", re.IGNORECASE)
_NON_IMAGE_DOC_RE = re.compile(r"\b(excel\w*|word\w*|pdf\w*|pptx\w*|sunum\w*|exe|kodunu)\b", re.IGNORECASE)
_NON_IMAGE_APP_RE = re.compile(r"\b(web\s*sitesi\w*|e-ticaret\w*|uygulama\w*|oyun(?:u|a|da|dan|un|lar[ıi]?)?)\b", re.IGNORECASE)


def is_image_generation_request(prompt: str, has_file: bool) -> bool:
    """True when the prompt asks for a picture. Words are matched on boundaries so "koyunlar" is not read as "oyun"."""
    if has_file:
        return False
    if _NON_IMAGE_DOC_RE.search(prompt):
        return False
    if _NON_IMAGE_APP_RE.search(prompt) and not _STRONG_VISUAL_RE.search(prompt):
        return False
    if _DRAW_RE.search(prompt) and not _CODE_WORD_RE.search(prompt):
        return True
    return bool(IMAGE_NOUN_RE.search(prompt) and IMAGE_ACTION_RE.search(prompt))


def classify_image_mode(prompt: str) -> str:
    """Classify an image prompt into logo_brand, diagram_infographic, poster_cover, or scene_illustration."""
    low = (prompt or "").lower()
    if any(k in low for k in ("mimari", "diyagram", "diagram", "şema", "sema", "akış", "akis", "flowchart", "infografik", "infographic", "sistem mimarisi", "architecture", "roadmap", "yol haritası", "yol haritasi", "harita", "pipeline", "workflow", "topoloji")):
        return "diagram_infographic"
    if any(k in low for k in ("poster", "afiş", "afis", "banner", "kapak", "cover", "davetiye", "invitation", "ilan", "flyer", "broşür", "brosur", "konser", "festival", "summit")):
        return "poster_cover"
    if any(k in low for k in ("logo", "amblem", "emblem", "marka kimliği", "marka kimligi", "brand", "ikon", "icon", "monogram", "rozet", "badge", "kurumsal kimlik")):
        return "logo_brand"
    return "scene_illustration"


STUDIO_PALETTES: dict[str, dict[str, str]] = {
    "midnight_cyan": {"name": "Gece Laciverti ve Turkuaz", "bg1": "#070b14", "bg2": "#0f172a", "bg3": "#111c33", "primary": "#06b6d4", "secondary": "#3b82f6", "accent": "#38bdf8", "text": "#f8fafc", "muted": "#94a3b8", "card": "#0f172a", "grid": "#38bdf8"},
    "obsidian_gold": {"name": "Obsidyen ve Altin", "bg1": "#0a0a0c", "bg2": "#141418", "bg3": "#1c1917", "primary": "#f59e0b", "secondary": "#d97706", "accent": "#fde68a", "text": "#fafaf9", "muted": "#a8a29e", "card": "#18181b", "grid": "#f59e0b"},
    "nordic_light": {"name": "Nordik Acik Minimal", "bg1": "#f8fafc", "bg2": "#f1f5f9", "bg3": "#e2e8f0", "primary": "#0f766e", "secondary": "#0284c7", "accent": "#14b8a6", "text": "#0f172a", "muted": "#475569", "card": "#ffffff", "grid": "#0f172a"},
    "emerald_slate": {"name": "Zumrut ve Antrasit", "bg1": "#051412", "bg2": "#0c2420", "bg3": "#0f172a", "primary": "#10b981", "secondary": "#06b6d4", "accent": "#6ee7b7", "text": "#ecfdf5", "muted": "#94a3b8", "card": "#0d2622", "grid": "#10b981"},
    "crimson_carbon": {"name": "Karbon ve Kizil", "bg1": "#0c0a0d", "bg2": "#1a1118", "bg3": "#18181b", "primary": "#ef4444", "secondary": "#f97316", "accent": "#fda4af", "text": "#fafafa", "muted": "#a1a1aa", "card": "#1c1519", "grid": "#ef4444"},
    "violet_aurora": {"name": "Indigo ve Aurora", "bg1": "#09071a", "bg2": "#161136", "bg3": "#0f172a", "primary": "#8b5cf6", "secondary": "#ec4899", "accent": "#c4b5fd", "text": "#f5f3ff", "muted": "#a5b4fc", "card": "#151230", "grid": "#8b5cf6"},
}
ARCHETYPE_ORDER = ["hex_nexus", "orbital_ring", "prism_monolith", "wing_aero", "neural_constellation", "wave_pulse", "shield_crest", "leaf_organic"]
LAYOUT_ORDER = ["badge_showcase", "horizontal_lockup", "centered_emblem"]


def _resolve_context_prompt(prompt: str, history: list[dict[str, Any]] | None) -> tuple[str, int]:
    low = (prompt or "").lower()
    is_rev = any(k in low for k in ("farklı", "farkli", "beğenmedim", "begenmedim", "kötü", "kotu", "başka", "baska", "yeniden", "tekrar", "değiştir", "degistir", "alternatif", "revize", "daha iyi", "çevir", "gündüz", "olsun", "ekle"))
    prior_cnt, prior_user = 0, ""
    for m in history or ():
        txt = str(m.get("text") or "")
        if m.get("role") == "assistant" and ("/api/assistant/media/img-gen-" in txt or "Üretilen Görsel" in txt):
            prior_cnt += 1
        elif m.get("role") == "user" and IMAGE_NOUN_RE.search(txt):
            prior_user = txt
    if is_rev and prior_user:
        return f"Ana tasarım konusu: {prior_user}\nKullanıcının revizyon talebi: {prompt}", prior_cnt + 1
    return prompt, prior_cnt


def _pick_palette_from_text(text: str, seed: int) -> str:
    low = text.lower()
    rules = (
        ("nordic_light", ("açık", "acik", "beyaz", "light", "temiz", "minimalist beyaz", "gündüz", "gunduz", "güneşli")),
        ("obsidian_gold", ("altın", "altin", "gold", "lüks", "luks", "premium", "gün batımı", "sunset")),
        ("emerald_slate", ("yeşil", "yesil", "doğa", "doga", "ekoloji", "orman", "zümrüt", "sağlık")),
        ("crimson_carbon", ("kırmızı", "kirmizi", "turuncu", "enerji", "spor", "otomotiv", "konser")),
        ("violet_aurora", ("mor", "violet", "yapay zeka", "ai", "uzay", "galaksi", "fütüristik", "cyberpunk")),
    )
    for pal_key, words in rules:
        if any(w in low for w in words):
            return pal_key
    keys = list(STUDIO_PALETTES)
    return keys[seed % len(keys)]


def _pick_archetype_from_text(text: str, seed: int) -> str:
    if seed > 0:
        return ARCHETYPE_ORDER[seed % len(ARCHETYPE_ORDER)]
    low = text.lower()
    rules = (
        ("wing_aero", ("havacılık", "havacilik", "uçak", "cnc", "otomotiv", "hız", "drone")),
        ("leaf_organic", ("doğa", "doga", "organik", "eko", "tarım", "bitki", "sağlık")),
        ("shield_crest", ("güvenlik", "guvenlik", "siber", "finans", "banka", "hukuk", "savunma")),
        ("wave_pulse", ("ses", "müzik", "muzik", "medya", "enerji", "radyo")),
        ("neural_constellation", ("yapay zeka", "veri", "ağ", "network", "bulut", "yazılım")),
    )
    for arch, words in rules:
        if any(w in low for w in words):
            return arch
    return ARCHETYPE_ORDER[seed % len(ARCHETYPE_ORDER)]


def _extract_quoted_brand(text: str) -> str:
    m = re.search(r'["\u201c\u201d\']([A-Za-z0-9ÇĞİÖŞÜçğıöşü\-\s]{2,26})["\u201c\u201d\']', text)
    return m.group(1).strip().upper() if m else ""


async def _llm_json_call(sys_msg: str, user_msg: str, model: str, num_predict: int = 360) -> dict[str, Any] | None:
    try:
        import gateway

        res = await gateway.default_client.chat(
            [{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}],
            model=model, profile="creative", num_predict=num_predict, timeout_s=35.0, feature="multimodal_studio", max_retries=0,
        )
        m = re.search(r"\{[\s\S]*\}", res.content)
        if m:
            parsed = json.loads(m.group(0))
            if isinstance(parsed, dict):
                return parsed
    except (httpx.HTTPError, OSError, RuntimeError, ValueError, TypeError, KeyError, ImportError) as exc:
        _LOG.debug("LLM JSON spec fallback: %s", exc)
    return None


def _merge_llm_design_spec(spec: dict[str, str], parsed: dict[str, Any], quoted: str, seed: int) -> None:
    bad = ("beğenmedim", "begenmedim", "kötü", "kotu", "görsel", "gorsel", "üret", "uret")
    bname, tag = str(parsed.get("brand_name") or "").strip()[:20], str(parsed.get("tagline") or "").strip()[:38]
    if bname and not any(w in bname.lower() for w in bad):
        spec["brand_name"] = quoted or bname.upper()
    if tag and not any(w in tag.lower() for w in bad[:4]):
        spec["tagline"] = tag.upper()
    arch, pal, lay = parsed.get("archetype"), parsed.get("palette"), parsed.get("layout")
    if isinstance(arch, str) and arch in ARCHETYPE_ORDER and (seed == 0 or arch != ARCHETYPE_ORDER[(seed - 1) % len(ARCHETYPE_ORDER)]):
        spec["archetype"] = arch
    if isinstance(pal, str) and pal in STUDIO_PALETTES:
        spec["palette"] = pal
    if isinstance(lay, str) and lay in LAYOUT_ORDER and seed == 0:
        spec["layout"] = lay


async def _design_spec_from_llm(combined_prompt: str, seed: int) -> dict[str, str]:
    names = ["NEXORA", "AETHERIS", "KINETIX", "VORTEXA", "LUMINEX", "SYNAPSE", "QUANTIX", "SOLARIS"]
    tags = ["GELECEĞİN TEKNOLOJİSİ", "AKILLI ÇÖZÜM MİMARİSİ", "YENİLİKÇİ TASARIM STÜDYOSU", "HASSAS MÜHENDİSLİK"]
    quoted = _extract_quoted_brand(combined_prompt)
    spec = {
        "brand_name": quoted or names[seed % len(names)], "tagline": tags[seed % len(tags)],
        "archetype": _pick_archetype_from_text(combined_prompt, seed),
        "palette": _pick_palette_from_text(combined_prompt, seed), "layout": LAYOUT_ORDER[seed % len(LAYOUT_ORDER)],
    }
    model = await pick_best_model("general")
    sys_msg = (
        f'Brand identity director. Return ONLY JSON: {{"brand_name":"UPPER<=16","tagline":"<=32",'
        f'"archetype":"one of {ARCHETYPE_ORDER}","palette":"one of {list(STUDIO_PALETTES)}","layout":"one of {LAYOUT_ORDER}"}}. Seed {seed}.'
    )
    parsed = await _llm_json_call(sys_msg, combined_prompt, model, num_predict=260)
    if parsed:
        _merge_llm_design_spec(spec, parsed, quoted, seed)
    if seed > 0:
        spec["layout"] = LAYOUT_ORDER[seed % len(LAYOUT_ORDER)]
    spec["model"] = model
    return spec


def _emblem_svg_group(archetype: str, pal: dict[str, str], use_solid: bool = False) -> str:
    p1 = pal["primary"] if use_solid else "url(#gPrimary)"
    p2 = pal["secondary"] if use_solid else "url(#gSecondary)"
    acc, txt, card = pal["accent"], pal["text"], pal["card"]
    if archetype == "neural_constellation":
        return load_prompt("b3_multimodal_neural_svg.txt").format(p1=p1, p2=p2, acc=acc, txt=txt)
    templates: dict[str, list[str]] = {
        "orbital_ring": [
            f'<circle cx="0" cy="0" r="88" fill="none" stroke="{p1}" stroke-width="2" stroke-dasharray="6 8" opacity="0.45"/>',
            f'<ellipse cx="0" cy="0" rx="102" ry="38" transform="rotate(-28)" fill="none" stroke="{p1}" stroke-width="6"/>',
            f'<ellipse cx="0" cy="0" rx="102" ry="38" transform="rotate(28)" fill="none" stroke="{p2}" stroke-width="4.5" opacity="0.88"/>',
            f'<polygon points="0,-42 36,-20 36,20 0,42 -36,20 -36,-20" fill="{p1}" opacity="0.92"/><circle cx="0" cy="0" r="14" fill="{txt}"/><circle cx="88" cy="-42" r="9" fill="{acc}"/>',
        ],
        "prism_monolith": [
            f'<polygon points="0,-96 86,-22 52,86 -52,86 -86,-22" fill="none" stroke="{p1}" stroke-width="4" opacity="0.35"/>',
            f'<polygon points="0,-84 74,0 0,84 -74,0" fill="{p2}" opacity="0.9"/><polygon points="0,-84 74,0 0,14" fill="{p1}"/>',
            f'<polygon points="0,-84 -74,0 0,14" fill="{acc}" opacity="0.55"/><polygon points="0,-44 36,0 0,44 -36,0" fill="none" stroke="{txt}" stroke-width="3.5"/><circle cx="0" cy="0" r="9" fill="{txt}"/>',
        ],
        "wing_aero": [
            f'<circle cx="0" cy="0" r="92" fill="none" stroke="{p1}" stroke-width="2.5" opacity="0.35"/>',
            f'<path d="M-96,-28 L-10,-62 L0,-24 L-72,10 Z" fill="{p1}"/><path d="M96,-28 L10,-62 L0,-24 L72,10 Z" fill="{p2}"/>',
            f'<path d="M-76,20 L-8,-10 L0,22 L-54,48 Z" fill="{acc}" opacity="0.85"/><path d="M76,20 L8,-10 L0,22 L54,48 Z" fill="{p1}" opacity="0.85"/>',
            f'<polygon points="0,-78 16,66 0,44 -16,66" fill="{txt}"/><circle cx="0" cy="-16" r="7" fill="{pal["bg1"]}"/>',
        ],
        "wave_pulse": [
            f'<rect x="-86" y="-86" width="172" height="172" rx="42" fill="{card}" stroke="{p1}" stroke-width="4.5"/>',
            f'<path d="M-64,12 C-42,-48 -18,-48 0,0 C18,48 42,48 64,-12" fill="none" stroke="{p1}" stroke-width="11" stroke-linecap="round"/>',
            f'<path d="M-64,-10 C-40,42 -16,42 0,-6 C16,-52 40,-52 64,14" fill="none" stroke="{acc}" stroke-width="6" stroke-linecap="round"/>',
            f'<circle cx="-64" cy="12" r="7" fill="{txt}"/><circle cx="64" cy="-12" r="7" fill="{txt}"/>',
        ],
        "shield_crest": [
            f'<path d="M0,-92 L78,-58 L78,8 C78,56 44,86 0,100 C-44,86 -78,56 -78,8 L-78,-58 Z" fill="{card}" stroke="{p1}" stroke-width="6"/>',
            f'<path d="M0,-74 L60,-46 L60,6 C60,44 34,68 0,80 C-34,68 -60,44 -60,6 L-60,-46 Z" fill="{p2}" opacity="0.22"/>',
            f'<path d="M-34,-8 L-6,22 L40,-28" fill="none" stroke="{p1}" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>',
            f'<path d="M-34,-8 L-6,22 L40,-28" fill="none" stroke="{acc}" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>',
        ],
        "leaf_organic": [
            f'<circle cx="0" cy="0" r="90" fill="none" stroke="{p1}" stroke-width="3" opacity="0.32"/>',
            f'<path d="M-62,56 C-72,-20 -10,-78 68,-74 C66,8 12,68 -62,56 Z" fill="{p1}" opacity="0.92"/>',
            f'<path d="M-62,56 C-12,24 22,-18 68,-74" fill="none" stroke="{txt}" stroke-width="5" stroke-linecap="round"/><circle cx="-62" cy="56" r="8" fill="{acc}"/>',
        ],
    }
    default_hex = [
        f'<polygon points="0,-94 81,-47 81,47 0,94 -81,47 -81,-47" fill="none" stroke="{p1}" stroke-width="6.5"/>',
        f'<polygon points="0,-72 62,-36 62,36 0,72 -62,36 -62,-36" fill="{card}" stroke="{p2}" stroke-width="3" opacity="0.9"/>',
        f'<polygon points="0,-54 47,-27 0,0 -47,-27" fill="{acc}" opacity="0.9"/><polygon points="-47,-27 0,0 0,54 -47,27" fill="{p1}" opacity="0.92"/>',
        f'<polygon points="47,-27 0,0 0,54 47,27" fill="{p2}" opacity="0.88"/><circle cx="0" cy="0" r="11" fill="{txt}"/>',
    ]
    return "\n".join(templates.get(archetype, default_hex))


def _render_studio_svg(spec: dict[str, str], use_solid: bool = False) -> str:
    pal = STUDIO_PALETTES.get(spec["palette"], STUDIO_PALETTES["midnight_cyan"])
    brand, tagline = xml_esc(spec["brand_name"]), xml_esc(spec["tagline"])
    emblem = _emblem_svg_group(spec["archetype"], pal, use_solid=use_solid)
    grid = "".join([f'<line x1="{x}" y1="0" x2="{x}" y2="760"/>' for x in range(120, 1200, 120)] + [f'<line x1="0" y1="{y}" x2="1200" y2="{y}"/>' for y in range(95, 760, 95)])
    bg_fill, bar_fill = (pal["bg2"], pal["primary"]) if use_solid else ("url(#gBg)", "url(#gPrimary)")

    if spec["layout"] == "horizontal_lockup":
        body = [
            f'<rect x="76" y="76" width="1048" height="608" rx="32" fill="{pal["card"]}" opacity="0.58" stroke="{pal["primary"]}" stroke-opacity="0.28" stroke-width="2"/>',
            f'<g transform="translate(310, 380) scale(1.22)">{emblem}</g><line x1="485" y1="245" x2="485" y2="515" stroke="{pal["primary"]}" stroke-width="3" opacity="0.45"/>',
            f'<text x="535" y="378" fill="{pal["text"]}" font-family="{_FONT}" font-size="74" font-weight="800" letter-spacing="8">{brand}</text>',
            f'<rect x="535" y="404" width="160" height="5" rx="2.5" fill="{bar_fill}"/>',
            f'<text x="535" y="448" fill="{pal["muted"]}" font-family="{_FONT}" font-size="21" font-weight="600" letter-spacing="5">{tagline}</text>',
        ]
    elif spec["layout"] == "badge_showcase":
        body = [
            f'<rect x="64" y="56" width="1072" height="532" rx="30" fill="{pal["card"]}" opacity="0.62" stroke="{pal["primary"]}" stroke-opacity="0.3" stroke-width="2"/>',
            f'<g transform="translate(600, 232) scale(1.18)">{emblem}</g>',
            f'<text x="600" y="438" text-anchor="middle" fill="{pal["text"]}" font-family="{_FONT}" font-size="70" font-weight="800" letter-spacing="12">{brand}</text>',
            f'<rect x="515" y="460" width="170" height="4" rx="2" fill="{bar_fill}"/><text x="600" y="502" text-anchor="middle" fill="{pal["muted"]}" font-family="{_FONT}" font-size="20" font-weight="600" letter-spacing="6">{tagline}</text>',
            f'<rect x="64" y="612" width="1072" height="92" rx="20" fill="{pal["card"]}" opacity="0.72" stroke="{pal["primary"]}" stroke-opacity="0.22" stroke-width="1.5"/>',
            f'<g transform="translate(132, 658) scale(0.28)">{emblem}</g><text x="184" y="654" fill="{pal["text"]}" font-family="{_FONT}" font-size="18" font-weight="700" letter-spacing="3">{brand}</text>',
            f'<text x="184" y="676" fill="{pal["muted"]}" font-family="{_FONT}" font-size="12" letter-spacing="2">KURUMSAL MARKA KIMLIGI</text>',
            f'<rect x="740" y="636" width="44" height="44" rx="10" fill="{pal["primary"]}"/><text x="794" y="663" fill="{pal["muted"]}" font-family="{_FONT}" font-size="13" font-weight="600">{pal["primary"].upper()}</text>',
            f'<rect x="880" y="636" width="44" height="44" rx="10" fill="{pal["secondary"]}"/><text x="934" y="663" fill="{pal["muted"]}" font-family="{_FONT}" font-size="13" font-weight="600">{pal["secondary"].upper()}</text>',
            f'<rect x="1020" y="636" width="44" height="44" rx="10" fill="{pal["accent"]}"/>',
        ]
    else:
        body = [
            f'<circle cx="600" cy="280" r="158" fill="none" stroke="{pal["primary"]}" stroke-width="1.5" opacity="0.28"/>',
            f'<g transform="translate(600, 276) scale(1.28)">{emblem}</g>',
            f'<text x="600" y="510" text-anchor="middle" fill="{pal["text"]}" font-family="{_FONT}" font-size="78" font-weight="800" letter-spacing="14">{brand}</text>',
            f'<rect x="500" y="538" width="200" height="5" rx="2.5" fill="{bar_fill}"/><text x="600" y="586" text-anchor="middle" fill="{pal["muted"]}" font-family="{_FONT}" font-size="22" font-weight="600" letter-spacing="6">{tagline}</text>',
        ]
    return "\n".join([
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 760" width="1200" height="760"><defs>',
        f'<linearGradient id="gBg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="{pal["bg1"]}"/><stop offset="52%" stop-color="{pal["bg2"]}"/><stop offset="100%" stop-color="{pal["bg3"]}"/></linearGradient>',
        f'<linearGradient id="gPrimary" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="{pal["primary"]}"/><stop offset="100%" stop-color="{pal["secondary"]}"/></linearGradient>',
        f'<linearGradient id="gSecondary" x1="1" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{pal["accent"]}"/><stop offset="100%" stop-color="{pal["primary"]}"/></linearGradient>',
        f'</defs><rect width="1200" height="760" fill="{bg_fill}"/><g stroke="{pal["grid"]}" stroke-width="1" opacity="0.06">{grid}</g>',
        *body, "</svg>",
    ])


def _default_diagram_spec(prompt: str, seed: int) -> dict[str, Any]:
    low = prompt.lower()
    if any(k in low for k in ("roadmap", "yol haritası", "yol haritasi", "faz", "aşama")):
        tiers = [
            {"name": "Q1 · TEMEL", "nodes": [{"label": "Keşif & Analiz", "meta": "Gereksinimler"}, {"label": "Mimari Tasarım", "meta": "RFC & Şema"}, {"label": "MVP Çekirdeği", "meta": "İlk Sürüm"}]},
            {"name": "Q2 · ÖLÇEKLEME", "nodes": [{"label": "API & Entegrasyon", "meta": "REST / SSE"}, {"label": "Otomatik Testler", "meta": "CI/CD Pipeline"}, {"label": "Güvenlik Denetimi", "meta": "Auth & RBAC"}]},
            {"name": "Q3 · YAYIN", "nodes": [{"label": "Canlı Gözlem", "meta": "Telemetri"}, {"label": "Performans Ayarı", "meta": "Önbellek"}, {"label": "Genel Sürüm", "meta": "v1.0 Launch"}]},
        ]
        title, sub = "STRATEJİK YOL HARİTASI", "FAZ BAZLI TESLİMAT VE MİMARİ PLAN"
    elif any(k in low for k in ("yapay zeka", "llm", "rag", "ajan", "agent", "ai", "model")):
        tiers = [
            {"name": "İSTEMCİ KATMANI", "nodes": [{"label": "Web & Mobil UI", "meta": "SSE Akış"}, {"label": "API Gateway", "meta": "Auth / Limit"}, {"label": "İstek Yönlendirici", "meta": "Niyet Analizi"}]},
            {"name": "ORKESTRASYON", "nodes": [{"label": "Planlayıcı Ajan", "meta": "Görev Ayrıştırma"}, {"label": "RAG & Bellek", "meta": "Vektör Arama"}, {"label": "Araç Motoru", "meta": "Sandbox / Kod"}]},
            {"name": "MODEL & VERİ", "nodes": [{"label": "Yerel LLM Kümesi", "meta": "Ollama / vLLM"}, {"label": "Bilgi Deposu", "meta": "SQLite / PG"}, {"label": "Denetim & Log", "meta": "Metrik İzleme"}]},
        ]
        title, sub = "YAPAY ZEKA SİSTEM MİMARİSİ", "KATMANLI ORKESTRASYON VE VERİ AKIŞI"
    else:
        tiers = [
            {"name": "SUNUM & ERİŞİM", "nodes": [{"label": "Kullanıcı Arayüzü", "meta": "SPA / Mobil"}, {"label": "Edge & CDN", "meta": "TLS / Önbellek"}, {"label": "API Gateway", "meta": "Yönlendirme"}]},
            {"name": "SERVİS KATMANI", "nodes": [{"label": "Kimlik & Yetki", "meta": "OAuth2 / JWT"}, {"label": "Çekirdek İş Mantığı", "meta": "Mikroservisler"}, {"label": "Olay Kuyruğu", "meta": "Asenkron Akış"}]},
            {"name": "VERİ & ALTYAPI", "nodes": [{"label": "İlişkisel DB", "meta": "Birincil Depo"}, {"label": "Önbellek & Arama", "meta": "Redis / Index"}, {"label": "Gözlemlenebilirlik", "meta": "Log & Metrik"}]},
        ]
        title, sub = "SİSTEM MİMARİ DİYAGRAMI", "KATMANLI SERVİS VE VERİ AKIŞ TOPOLOJİSİ"
    return {"title": _extract_quoted_brand(prompt) or title, "subtitle": sub, "palette": _pick_palette_from_text(prompt, seed), "tiers": tiers}


async def _diagram_spec_from_llm(prompt: str, seed: int) -> dict[str, Any]:
    spec, model = _default_diagram_spec(prompt, seed), await pick_best_model("general")
    sys_msg = 'Return ONLY JSON: {"title":"SHORT TITLE","subtitle":"SHORT SUB","tiers":[{"name":"TIER","nodes":[{"label":"Name","meta":"2 words"}]}]}. 3 tiers, 3 nodes each.'
    parsed = await _llm_json_call(sys_msg, prompt, model, num_predict=400)
    if parsed:
        for k, lim in (("title", 38), ("subtitle", 54)):
            if isinstance(parsed.get(k), str) and parsed[k].strip():
                spec[k] = parsed[k].strip().upper()[:lim]
        tiers = parsed.get("tiers")
        if isinstance(tiers, list) and len(tiers) >= 2:
            cleaned = [
                {"name": str(t.get("name") or "KATMAN")[:20].upper(), "nodes": [{"label": str(n.get("label") or "Node")[:22], "meta": str(n.get("meta") or "")[:24]} for n in t["nodes"][:4] if isinstance(n, dict)]}
                for t in tiers[:4] if isinstance(t, dict) and isinstance(t.get("nodes"), list) and t["nodes"]
            ]
            if len([c for c in cleaned if c["nodes"]]) >= 2:
                spec["tiers"] = [c for c in cleaned if c["nodes"]]
    spec["model"] = model
    return spec


def _render_diagram_svg(spec: dict[str, Any]) -> str:
    pal = STUDIO_PALETTES.get(spec["palette"], STUDIO_PALETTES["midnight_cyan"])
    tiers: list[dict[str, Any]] = spec["tiers"]
    cols = [pal["primary"], pal["secondary"], pal["accent"], "#10b981"]
    top_y, gap = 132, 34
    band_h = min(168, (592 - gap * (len(tiers) - 1)) // max(1, len(tiers)))
    elems = [
        '<rect x="0" y="0" width="1200" height="760" fill="url(#gBg)"/>',
        f'<rect x="44" y="28" width="1112" height="82" rx="16" fill="{pal["card"]}" stroke="{pal["primary"]}" stroke-opacity="0.35" stroke-width="1.5"/>',
        f'<rect x="64" y="48" width="8" height="42" rx="4" fill="{pal["primary"]}"/>',
        f'<text x="88" y="68" fill="{pal["text"]}" font-family="{_FONT}" font-size="28" font-weight="800" letter-spacing="2">{xml_esc(spec["title"])}</text>',
        f'<text x="88" y="93" fill="{pal["muted"]}" font-family="{_FONT}" font-size="14" font-weight="600" letter-spacing="2">{xml_esc(spec["subtitle"])}</text>',
    ]
    prev: list[tuple[int, int]] = []
    for ti, tier in enumerate(tiers):
        col, by, nodes = cols[ti % len(cols)], top_y + ti * (band_h + gap), tier["nodes"]
        elems.extend([
            f'<rect x="44" y="{by}" width="1112" height="{band_h}" rx="18" fill="{pal["card"]}" opacity="0.72" stroke="{col}" stroke-opacity="0.45" stroke-width="1.5"/>',
            f'<rect x="62" y="{by + 14}" width="190" height="24" rx="12" fill="{col}" opacity="0.22"/><text x="76" y="{by + 30}" fill="{col}" font-family="{_FONT}" font-size="12" font-weight="700" letter-spacing="1.5">{xml_esc(tier["name"])}</text>',
        ])
        nw = min(310, (1048 - 24 * (len(nodes) - 1)) // max(1, len(nodes)))
        sx = 600 - (len(nodes) * nw + (len(nodes) - 1) * 24) // 2
        curr: list[tuple[int, int]] = []
        for ni, node in enumerate(nodes):
            nx, ny, nh = sx + ni * (nw + 24), by + 48, band_h - 64
            cx = nx + nw // 2
            curr.append((cx, ny))
            elems.extend([
                f'<rect x="{nx}" y="{ny}" width="{nw}" height="{nh}" rx="12" fill="{pal["bg2"]}" stroke="{col}" stroke-width="2"/><rect x="{nx}" y="{ny}" width="{nw}" height="6" rx="3" fill="{col}"/>',
                f'<text x="{cx}" y="{ny + nh // 2 - 2}" text-anchor="middle" fill="{pal["text"]}" font-family="{_FONT}" font-size="18" font-weight="700">{xml_esc(node["label"])}</text>',
                f'<text x="{cx}" y="{ny + nh // 2 + 22}" text-anchor="middle" fill="{pal["muted"]}" font-family="{_FONT}" font-size="13">{xml_esc(node["meta"])}</text>',
            ])
        for idx, (px, py) in enumerate(prev):
            tx, ty = curr[min(idx, len(curr) - 1)]
            elems.append(f'<line x1="{px}" y1="{py}" x2="{tx}" y2="{ty - 6}" stroke="{col}" stroke-width="2.5" marker-end="url(#arrowHead)"/>')
        prev = [(c[0], by + band_h - 14) for c in curr]
    return "\n".join([
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 760" width="1200" height="760"><defs>',
        f'<linearGradient id="gBg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="{pal["bg1"]}"/><stop offset="100%" stop-color="{pal["bg3"]}"/></linearGradient>',
        f'<marker id="arrowHead" markerWidth="10" markerHeight="10" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 Z" fill="{pal["accent"]}"/></marker>',
        "</defs>", *elems, "</svg>",
    ])


async def _poster_spec_from_llm(prompt: str, seed: int) -> dict[str, Any]:
    year_m = re.search(r"\b(20\d{2})\b", prompt)
    spec: dict[str, Any] = {
        "kicker": "ÖZEL ETKİNLİK · EDİTORYAL", "title": _extract_quoted_brand(prompt) or "GELECEĞİN TASARIM ZİRVESİ",
        "subtitle": "YENİLİKÇİ FİKİRLER VE YARATICI TEKNOLOJİ BULUŞMASI",
        "date_badge": f"15 MAYIS {year_m.group(1)}" if year_m else "2026 SEZONU",
        "location_badge": "İSTANBUL · CANLI YAYIN", "pills": ["KEYNOTE", "ATÖLYE", "NETWORKING"],
        "palette": _pick_palette_from_text(prompt, seed),
    }
    model = await pick_best_model("general")
    sys_msg = 'Return ONLY JSON for an editorial poster: {"kicker":"TAG","title":"HEADLINE<=28","subtitle":"SUB","date_badge":"DATE","location_badge":"CITY","pills":["T1","T2","T3"]}.'
    parsed = await _llm_json_call(sys_msg, prompt, model, num_predict=280)
    if parsed:
        for k, lim in (("kicker", 28), ("title", 32), ("subtitle", 54), ("date_badge", 24), ("location_badge", 26)):
            v = str(parsed.get(k) or "").strip()
            if v:
                spec[k] = v.upper()[:lim]
        if isinstance(parsed.get("pills"), list):
            pills = [str(x).strip().upper()[:16] for x in parsed["pills"][:3] if str(x).strip()]
            if pills:
                spec["pills"] = pills
    spec["model"] = model
    return spec


def _render_poster_svg(spec: dict[str, Any]) -> str:
    pal = STUDIO_PALETTES.get(spec["palette"], STUDIO_PALETTES["crimson_carbon"])
    words = spec["title"].split()
    mid = max(1, len(words) // 2)
    l1, l2 = (xml_esc(" ".join(words[:mid])), xml_esc(" ".join(words[mid:]))) if len(words) > 2 else (xml_esc(spec["title"]), "")
    pills_svg, px = [], 92
    for pill in spec["pills"][:3]:
        pw = max(116, len(pill) * 12 + 34)
        pills_svg.append(f'<rect x="{px}" y="618" width="{pw}" height="38" rx="19" fill="{pal["primary"]}" opacity="0.22" stroke="{pal["primary"]}" stroke-width="1.5"/><text x="{px + pw // 2}" y="642" text-anchor="middle" fill="{pal["text"]}" font-family="{_FONT}" font-size="13" font-weight="700" letter-spacing="2">{xml_esc(pill)}</text>')
        px += pw + 14
    return "\n".join([
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 760" width="1200" height="760"><defs>',
        f'<linearGradient id="gBg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="{pal["bg1"]}"/><stop offset="55%" stop-color="{pal["bg2"]}"/><stop offset="100%" stop-color="{pal["bg3"]}"/></linearGradient>',
        '</defs><rect x="0" y="0" width="1200" height="760" fill="url(#gBg)"/>',
        f'<rect x="44" y="42" width="1112" height="676" rx="28" fill="{pal["card"]}" opacity="0.52" stroke="{pal["primary"]}" stroke-opacity="0.38" stroke-width="2"/>',
        f'<circle cx="910" cy="365" r="235" fill="{pal["primary"]}" opacity="0.16"/><circle cx="910" cy="365" r="168" fill="none" stroke="{pal["accent"]}" stroke-width="3" stroke-dasharray="10 8" opacity="0.65"/>',
        f'<circle cx="910" cy="365" r="118" fill="{pal["primary"]}" opacity="0.88"/><polygon points="770,515 910,275 1050,515" fill="{pal["bg1"]}" opacity="0.82" stroke="{pal["accent"]}" stroke-width="2.5"/>',
        f'<polygon points="845,515 965,335 1085,515" fill="{pal["secondary"]}" opacity="0.72"/><circle cx="1015" cy="245" r="24" fill="{pal["accent"]}"/>',
        f'<rect x="92" y="96" width="290" height="36" rx="18" fill="{pal["primary"]}" opacity="0.22" stroke="{pal["primary"]}" stroke-width="1.5"/>',
        f'<text x="237" y="119" text-anchor="middle" fill="{pal["accent"]}" font-family="{_FONT}" font-size="13" font-weight="700" letter-spacing="2.5">{xml_esc(spec["kicker"])}</text>',
        f'<text x="92" y="255" fill="{pal["text"]}" font-family="{_FONT}" font-size="66" font-weight="900" letter-spacing="2">{l1}</text>',
        f'<text x="92" y="335" fill="{pal["accent"]}" font-family="{_FONT}" font-size="66" font-weight="900" letter-spacing="2">{l2}</text>',
        f'<rect x="92" y="366" width="180" height="6" rx="3" fill="{pal["primary"]}"/><text x="92" y="418" fill="{pal["muted"]}" font-family="{_FONT}" font-size="20" font-weight="600">{xml_esc(spec["subtitle"])}</text>',
        f'<rect x="92" y="476" width="520" height="86" rx="16" fill="{pal["bg1"]}" opacity="0.76" stroke="{pal["accent"]}" stroke-opacity="0.35"/>',
        f'<text x="122" y="512" fill="{pal["accent"]}" font-family="{_FONT}" font-size="18" font-weight="800" letter-spacing="2">{xml_esc(spec["date_badge"])}</text>',
        f'<text x="122" y="542" fill="{pal["text"]}" font-family="{_FONT}" font-size="16" font-weight="600" letter-spacing="1.5">{xml_esc(spec["location_badge"])}</text>',
        *pills_svg, "</svg>",
    ])


def _classify_scene_subtype(prompt: str) -> str:
    low = prompt.lower()
    if any(k in low for k in ("istanbul", "şehir", "sehir", "boğaz", "bogaz", "gökdelen", "köprü", "cyberpunk", "fütüristik", "futuristic", "city")):
        return "cityscape"
    if any(k in low for k in ("uzay", "galaksi", "gezegen", "yıldız", "nebula", "cosmos", "space", "galaxy", "mars", "astronot")):
        return "space_cosmos"
    if any(k in low for k in ("soyut", "abstract", "geometrik", "aurora", "dalga", "modern sanat")):
        return "abstract_art"
    return "nature_landscape"


async def _generate_scene_svg(prompt: str, pal_key: str, seed: int) -> tuple[str, str, str]:
    """Scenes come from the layered template engine: a small local model cannot draw a usable scene as raw SVG."""
    pal, subtype = STUDIO_PALETTES.get(pal_key, STUDIO_PALETTES["midnight_cyan"]), _classify_scene_subtype(prompt)
    return render_procedural_scene_svg(subtype, prompt, pal, seed), f"scene-procedural ({subtype})", subtype


async def _try_stable_diffusion(prompt: str, out_png: Path) -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.post("http://127.0.0.1:7860/sdapi/v1/txt2img", json={"prompt": prompt, "steps": 24, "width": 1024, "height": 640})
            if resp.status_code == 200 and resp.json().get("images"):
                await asyncio.to_thread(out_png.write_bytes, base64.b64decode(resp.json()["images"][0]))
                return True
    except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        _LOG.debug("Stable Diffusion bridge unavailable: %s", exc)
    return False


async def _try_comfyui(prompt: str, out_png: Path) -> bool:
    base = "http://127.0.0.1:8188"
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            if (await client.get(f"{base}/system_stats")).status_code != 200:
                return False
            ckpts = (await client.get(f"{base}/object_info/CheckpointLoaderSimple")).json().get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
            if not ckpts:
                return False
            graph = {
                "3": {"class_type": "KSampler", "inputs": {"seed": 42, "steps": 20, "cfg": 7.0, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0, "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
                "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": ckpts[0]}},
                "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 640, "batch_size": 1}},
                "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
                "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry, low quality, text watermark", "clip": ["4", 1]}},
                "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
                "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "dadp_comfy", "images": ["8", 0]}},
            }
            pid = (await client.post(f"{base}/prompt", json={"prompt": graph}, timeout=10.0)).json().get("prompt_id")
            for _ in range(20 if pid else 0):
                await asyncio.sleep(1.0)
                imgs = (await client.get(f"{base}/history/{pid}", timeout=5.0)).json().get(pid, {}).get("outputs", {}).get("9", {}).get("images", [])
                if imgs:
                    raw = await client.get(f"{base}/view", params={"filename": imgs[0]["filename"], "subfolder": imgs[0].get("subfolder", ""), "type": imgs[0].get("type", "output")}, timeout=10.0)
                    if raw.status_code == 200:
                        await asyncio.to_thread(out_png.write_bytes, raw.content)
                        return True
    except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        _LOG.debug("ComfyUI bridge unavailable: %s", exc)
    return False


def _save_true_color_png(spec_or_svg: dict[str, str] | str, out_png: Path, fallback_bg: str = "#0f172a") -> None:
    """Render SVG artwork cleanly to high-res PNG without PyMuPDF black-gradient artifacts."""
    if isinstance(spec_or_svg, dict):
        pal = STUDIO_PALETTES.get(spec_or_svg.get("palette", ""), STUDIO_PALETTES["midnight_cyan"])
        rasterize_svg_to_png(_render_studio_svg(spec_or_svg, use_solid=False), out_png, pal["bg2"], spec_or_svg.get("brand_name", ""))
    else:
        rasterize_svg_to_png(spec_or_svg, out_png, fallback_bg, "")


async def generate_ai_image(prompt: str, history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Generate multi-mode visual artwork (logo, diagram, poster, or scenic illustration) + crisp PNG."""
    file_id = f"img-gen-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    out_png, out_svg = media_dir() / f"{file_id}.png", media_dir() / f"{file_id}.svg"
    combined_prompt, seed = _resolve_context_prompt(prompt, history)
    mode = classify_image_mode(combined_prompt)

    for bridge_name, bridge_fn in (("stable-diffusion-local", _try_stable_diffusion), ("comfyui-local", _try_comfyui)):
        if await bridge_fn(combined_prompt, out_png):
            return {"file_id": file_id, "mode": mode, "engine": bridge_name, "png_url": f"/api/assistant/media/{file_id}.png", "svg_url": ""}

    if mode == "logo_brand":
        spec = await _design_spec_from_llm(combined_prompt, seed)
        svg_text, pal_key, engine = _render_studio_svg(spec, use_solid=False), spec["palette"], f"vector-studio ({spec.get('model', 'local')})"
        meta = {"brand_name": spec["brand_name"], "tagline": spec["tagline"], "archetype": spec["archetype"], "layout": spec["layout"]}
    elif mode == "diagram_infographic":
        spec_d = await _diagram_spec_from_llm(combined_prompt, seed)
        svg_text, pal_key, engine = _render_diagram_svg(spec_d), spec_d["palette"], f"diagram-studio ({spec_d.get('model', 'local')})"
        meta = {"brand_name": spec_d["title"], "tagline": spec_d["subtitle"]}
    elif mode == "poster_cover":
        spec_p = await _poster_spec_from_llm(combined_prompt, seed)
        svg_text, pal_key, engine = _render_poster_svg(spec_p), spec_p["palette"], f"poster-studio ({spec_p.get('model', 'local')})"
        meta = {"brand_name": spec_p["title"], "tagline": spec_p["subtitle"]}
    else:
        pal_key = _pick_palette_from_text(combined_prompt, seed)
        svg_text, engine, subtype = await _generate_scene_svg(combined_prompt, pal_key, seed)
        meta = {"brand_name": f"SAHNE · {subtype.upper()}", "tagline": combined_prompt[:48]}

    pal = STUDIO_PALETTES.get(pal_key, STUDIO_PALETTES["midnight_cyan"])
    await asyncio.to_thread(out_svg.write_text, svg_text, "utf-8")
    await asyncio.to_thread(_save_true_color_png, svg_text, out_png, pal["bg2"])
    return {
        "file_id": file_id, "mode": mode, "engine": engine, "palette_name": pal["name"],
        "png_url": f"/api/assistant/media/{file_id}.png", "svg_url": f"/api/assistant/media/{file_id}.svg",
        **meta,
    }
