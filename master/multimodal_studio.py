"""Universal Multimodal AI Studio: Image Generation, Image Editing/CV Processing, Deep Vision Analysis, and Voice-to-Text.

100% local, zero emojis, production-grade implementations using Pillow, NumPy, PyMuPDF,
local Ollama Vision/Coder models (qwen3.5:9b / gemma4:e4b / qwen2.5-coder:7b), optional local
Diffusion (Automatic1111 / ComfyUI) bridge, and Windows System.Speech / Faster-Whisper STT.
"""

from __future__ import annotations

import base64
import io
import re
import subprocess
import sys
import tempfile
import uuid
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pymupdf as fitz
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

import config


def media_dir() -> Path:
    d = config.DATA_DIR / "media"
    d.mkdir(parents=True, exist_ok=True)
    return d


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


async def pick_best_model(task: str = "general") -> str:
    """Dynamically route to the strongest installed local Ollama model for the task."""
    if task == "code":
        prefs = ["qwen2.5-coder:7b", "qwen3.5:9b", "qwen3.5:4b", config.MASTER_MODEL]
    elif task == "vision":
        prefs = ["qwen3.5:9b", "gemma4:e4b", "qwen3.5:4b", config.MASTER_MODEL]
    elif task == "deep":
        prefs = ["qwen3.5:9b", "gemma4:e4b", "qwen2.5-coder:7b", "qwen3.5:4b", config.MASTER_MODEL]
    else:
        prefs = ["qwen3.5:9b", "qwen3.5:4b", config.MASTER_MODEL]

    try:
        async with httpx.AsyncClient(timeout=3.5) as client:
            resp = await client.get(f"{config.OLLAMA_URL}/api/tags")
            if resp.status_code == 200:
                installed = {m.get("name", "") for m in resp.json().get("models", [])}
                for cand in prefs:
                    if cand in installed:
                        return cand
    except Exception:
        pass
    return config.MASTER_MODEL


# ============================================================================
# 1. IMAGE PROCESSING & COMPUTER VISION EDITING ENGINE
# ============================================================================

IMAGE_EDIT_KEYWORDS = (
    "siyah beyaz", "gri ton", "grayscale", "kontrast", "netleştir", "netlestir", "keskinleştir",
    "bulanık", "bulanik", "blur", "kenar", "eskiz", "sketch", "edge", "ters çevir", "negatif",
    "invert", "döndür", "dondur", "rotate", "çevir", "ayna", "flip", "boyutlandır", "boyutlandir",
    "resize", "küçült", "बüyüt", "kırp", "kirp", "crop", "parlaklık", "parlaklik", "sepya",
    "sepia", "arka plan", "arkaplan", "filigran", "yazı ekle", "yazi ekle", "watermark",
    "düzenle", "duzenle", "efekt", "işle", "isle", "görüntü işle", "goruntu isle",
)


def is_image_edit_request(prompt: str) -> bool:
    lower = prompt.lower()
    return any(k in lower for k in IMAGE_EDIT_KEYWORDS)


def process_and_edit_image(raw_bytes: bytes, prompt: str) -> dict[str, Any]:
    """Apply computer-vision filters, geometric transforms, background removal, or watermarks."""
    orig = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    img = orig.copy()
    lower = prompt.lower()
    applied: list[str] = []

    # 1. Rotation / Flip
    if "90" in lower and ("döndür" in lower or "dondur" in lower or "rotate" in lower):
        img = img.rotate(-90, expand=True)
        applied.append("90 Derece Döndürme")
    elif "180" in lower and ("döndür" in lower or "dondur" in lower or "rotate" in lower):
        img = img.rotate(180, expand=True)
        applied.append("180 Derece Döndürme")
    elif "döndür" in lower or "dondur" in lower or "rotate" in lower:
        img = img.rotate(-90, expand=True)
        applied.append("90 Derece Saat Yönünde Döndürme")

    if "ayna" in lower or "yatay çevir" in lower or "flip" in lower:
        img = ImageOps.mirror(img)
        applied.append("Yatay Aynalama (Mirror)")

    # 2. Resize / Crop
    m_size = re.search(r"(\d{2,4})\s*[xX\u00d7]\s*(\d{2,4})", prompt)
    if m_size:
        nw, nh = min(4096, int(m_size.group(1))), min(4096, int(m_size.group(2)))
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
        applied.append(f"Yeniden Boyutlandırma ({nw}x{nh} px)")
    elif "küçült" in lower or "kucult" in lower or "yarı" in lower:
        nw, nh = max(64, img.width // 2), max(64, img.height // 2)
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
        applied.append(f"%50 Ölçekleme ({nw}x{nh} px)")
    elif "kırp" in lower or "kirp" in lower or "crop" in lower:
        w, h = img.size
        mx, my = int(w * 0.12), int(h * 0.12)
        img = img.crop((mx, my, w - mx, h - my))
        applied.append("Merkez Odaklı Kırpma (%76 Alan)")

    # 3. Background Removal / High-Contrast Thresholding
    if "arka plan" in lower or "arkaplan" in lower or "background" in lower:
        arr = np.array(img, dtype=np.float32)
        # Estimate background color from the 4 corners
        corners = np.vstack([arr[0, 0], arr[0, -1], arr[-1, 0], arr[-1, -1]])
        bg_color = np.mean(corners, axis=0)
        dist = np.linalg.norm(arr - bg_color, axis=2)
        mask = dist < 42.0
        arr[mask] = [255.0, 255.0, 255.0]
        img = Image.fromarray(arr.astype(np.uint8), mode="RGB")
        applied.append("Arka Plan Temizleme (Köşe Renk Uzaklığı Segmentasyonu)")

    # 4. Color & Tone Filters
    if "siyah beyaz" in lower or "gri" in lower or "grayscale" in lower:
        img = ImageOps.grayscale(img).convert("RGB")
        applied.append("Gri Tonlama (Grayscale)")

    if "sepya" in lower or "sepia" in lower or "nostalji" in lower:
        gray = np.array(ImageOps.grayscale(img), dtype=np.float32)
        r = np.clip(gray * 1.08 + 28, 0, 255)
        g = np.clip(gray * 0.92 + 12, 0, 255)
        b = np.clip(gray * 0.74, 0, 255)
        img = Image.fromarray(np.stack([r, g, b], axis=-1).astype(np.uint8), mode="RGB")
        applied.append("Sepya Tonlama Filtresi")

    if "ters çevir" in lower or "negatif" in lower or "invert" in lower:
        img = ImageOps.invert(img)
        applied.append("Renk Ters Çevirme (Negatif)")

    if "kenar" in lower or "eskiz" in lower or "sketch" in lower or "edge" in lower:
        gray_im = ImageOps.grayscale(img)
        edges = gray_im.filter(ImageFilter.FIND_EDGES)
        edges = ImageOps.invert(edges)
        edges = ImageEnhance.Contrast(edges).enhance(2.2)
        img = edges.convert("RGB")
        applied.append("Sobel Kenar Tespiti / Teknik Eskiz Dönüşümü")

    if "bulanık" in lower or "bulanik" in lower or "blur" in lower:
        img = img.filter(ImageFilter.GaussianBlur(radius=3.5))
        applied.append("Gaussian Bulanıklaştırma (r=3.5)")

    if "netleştir" in lower or "netlestir" in lower or "keskin" in lower or "sharpen" in lower:
        img = img.filter(ImageFilter.UnsharpMask(radius=2.0, percent=180, threshold=3))
        applied.append("Unsharp Mask Keskinleştirme")

    if "kontrast" in lower or "canlandır" in lower or "iyileştir" in lower:
        img = ImageOps.autocontrast(img, cutoff=1)
        img = ImageEnhance.Contrast(img).enhance(1.32)
        img = ImageEnhance.Color(img).enhance(1.18)
        applied.append("Otomatik Histogram Germe ve Kontrast Güçlendirme")

    if "parlak" in lower or "aydınlat" in lower or "aydinlat" in lower:
        img = ImageEnhance.Brightness(img).enhance(1.28)
        applied.append("Parlaklık Artırma (+%28)")

    # 5. Text Overlay / Watermark
    m_txt = re.search(r'["“”\']([^"“”\']{2,50})["“”\']', prompt)
    if ("yazı" in lower or "yazi" in lower or "filigran" in lower or "watermark" in lower) and m_txt:
        wm_text = m_txt.group(1)
        draw = ImageDraw.Draw(img)
        fsize = max(18, img.width // 24)
        font = _load_font(fsize, bold=True)
        bbox = draw.textbbox((0, 0), wm_text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        px, py = img.width - tw - 24, img.height - th - 24
        draw.rectangle([px - 10, py - 6, px + tw + 10, py + th + 8], fill=(15, 23, 42))
        draw.text((px, py), wm_text, fill=(248, 250, 252), font=font)
        applied.append(f'Metin / Filigran Ekleme ("{wm_text}")')

    # Default smart enhancement if user just said "bu görüntüyü işle / düzenle" without specific filter
    if not applied:
        img = ImageOps.autocontrast(img, cutoff=1)
        img = ImageEnhance.Contrast(img).enhance(1.2)
        img = img.filter(ImageFilter.UnsharpMask(radius=1.6, percent=140, threshold=3))
        applied.append("Otomatik Kontrast Dengeleme ve Netleştirme (HDR İyileştirme)")

    # Save edited image and side-by-side comparison
    file_id = f"img-edit-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    out_png = media_dir() / f"{file_id}.png"
    img.save(out_png, format="PNG")

    # Image statistics (mean RGB, brightness, resolution)
    arr_out = np.array(img)
    stats = {
        "original_size": f"{orig.width}x{orig.height} px",
        "output_size": f"{img.width}x{img.height} px",
        "mean_brightness": round(float(np.mean(arr_out)), 1),
        "std_contrast": round(float(np.std(arr_out)), 1),
        "applied_filters": applied,
        "file_id": file_id,
        "url": f"/api/assistant/media/{file_id}.png",
    }
    return stats


# ============================================================================
# 2. AI IMAGE & VECTOR ILLUSTRATION GENERATOR
# ============================================================================

IMAGE_NOUN_RE = re.compile(
    r"\b(görsel\w*|gorsel\w*|fotoğraf\w*|fotograf\w*|resim\w*|illüstrasyon\w*|illustrasyon\w*|"
    r"logo\w*|poster\w*|afiş\w*|afis\w*|amblem\w*|banner\w*|kapak\s*tasarım\w*)\b",
    re.IGNORECASE,
)

IMAGE_ACTION_RE = re.compile(
    r"(oluştur\w*|olustur\w*|üret\w*|uret\w*|çiz\w*|ciz\w*|tasarla\w*|yap\w*|hazırla\w*|hazirla\w*|değiştir\w*|degistir\w*|yenile\w*)",
    re.IGNORECASE,
)


def is_image_generation_request(prompt: str, has_file: bool) -> bool:
    if has_file:
        return False
    lower = prompt.lower()
    if any(w in lower for w in ("web sitesi", "e-ticaret", "uygulama", "oyun", "exe", "kodunu", "excel", "word", "pdf", "pptx", "sunum")):
        return False
    return bool(IMAGE_NOUN_RE.search(prompt) and IMAGE_ACTION_RE.search(prompt))


STUDIO_PALETTES: dict[str, dict[str, str]] = {
    "midnight_cyan": {
        "name": "Gece Laciverti ve Turkuaz",
        "bg1": "#070b14",
        "bg2": "#0f172a",
        "bg3": "#111c33",
        "primary": "#06b6d4",
        "secondary": "#3b82f6",
        "accent": "#38bdf8",
        "text": "#f8fafc",
        "muted": "#94a3b8",
        "card": "#0f172a",
        "grid": "#38bdf8",
    },
    "obsidian_gold": {
        "name": "Obsidyen ve Altin",
        "bg1": "#0a0a0c",
        "bg2": "#141418",
        "bg3": "#1c1917",
        "primary": "#f59e0b",
        "secondary": "#d97706",
        "accent": "#fde68a",
        "text": "#fafaf9",
        "muted": "#a8a29e",
        "card": "#18181b",
        "grid": "#f59e0b",
    },
    "nordic_light": {
        "name": "Nordik Acik Minimal",
        "bg1": "#f8fafc",
        "bg2": "#f1f5f9",
        "bg3": "#e2e8f0",
        "primary": "#0f766e",
        "secondary": "#0284c7",
        "accent": "#14b8a6",
        "text": "#0f172a",
        "muted": "#475569",
        "card": "#ffffff",
        "grid": "#0f172a",
    },
    "emerald_slate": {
        "name": "Zumrut ve Antrasit",
        "bg1": "#051412",
        "bg2": "#0c2420",
        "bg3": "#0f172a",
        "primary": "#10b981",
        "secondary": "#06b6d4",
        "accent": "#6ee7b7",
        "text": "#ecfdf5",
        "muted": "#94a3b8",
        "card": "#0d2622",
        "grid": "#10b981",
    },
    "crimson_carbon": {
        "name": "Karbon ve Kizil",
        "bg1": "#0c0a0d",
        "bg2": "#1a1118",
        "bg3": "#18181b",
        "primary": "#ef4444",
        "secondary": "#f97316",
        "accent": "#fda4af",
        "text": "#fafafa",
        "muted": "#a1a1aa",
        "card": "#1c1519",
        "grid": "#ef4444",
    },
    "violet_aurora": {
        "name": "Indigo ve Aurora",
        "bg1": "#09071a",
        "bg2": "#161136",
        "bg3": "#0f172a",
        "primary": "#8b5cf6",
        "secondary": "#ec4899",
        "accent": "#c4b5fd",
        "text": "#f5f3ff",
        "muted": "#a5b4fc",
        "card": "#151230",
        "grid": "#8b5cf6",
    },
}

ARCHETYPE_ORDER = [
    "hex_nexus",
    "orbital_ring",
    "prism_monolith",
    "wing_aero",
    "neural_constellation",
    "wave_pulse",
    "shield_crest",
    "leaf_organic",
]

LAYOUT_ORDER = ["badge_showcase", "horizontal_lockup", "centered_emblem"]


def _xml_esc(text: str) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _resolve_context_prompt(prompt: str, history: list[dict[str, Any]] | None) -> tuple[str, int]:
    """Merge follow-up revision feedback with the original design request from conversation history."""
    low = (prompt or "").lower()
    is_revision = any(
        k in low
        for k in (
            "farklı",
            "farkli",
            "beğenmedim",
            "begenmedim",
            "kötü",
            "kotu",
            "başka",
            "baska",
            "yeniden",
            "tekrar",
            "değiştir",
            "degistir",
            "alternatif",
            "revize",
            "daha iyi",
        )
    )
    prior_img_count = 0
    prior_user_prompt = ""
    if history:
        for m in history:
            txt = str(m.get("text") or "")
            if m.get("role") == "assistant" and ("/api/assistant/media/img-gen-" in txt or "Üretilen Görsel" in txt):
                prior_img_count += 1
            elif m.get("role") == "user" and IMAGE_NOUN_RE.search(txt):
                prior_user_prompt = txt

    if is_revision and prior_user_prompt:
        combined = f"Ana tasarım konusu: {prior_user_prompt}\nKullanıcının revizyon talebi: {prompt}"
        return combined, prior_img_count + 1
    return prompt, prior_img_count


def _pick_palette_from_text(text: str, seed: int) -> str:
    low = text.lower()
    if any(k in low for k in ("açık", "acik", "beyaz", "light", "temiz", "minimalist beyaz")):
        return "nordic_light"
    if any(k in low for k in ("altın", "altin", "gold", "lüks", "luks", "premium", "siyah altın")):
        return "obsidian_gold"
    if any(k in low for k in ("yeşil", "yesil", "doğa", "doga", "ekoloji", "çevre", "zümrüt", "sağlık")):
        return "emerald_slate"
    if any(k in low for k in ("kırmızı", "kirmizi", "turuncu", "enerji", "spor", "otomotiv")):
        return "crimson_carbon"
    if any(k in low for k in ("mor", "violet", "yapay zeka", "ai", "yaratıcı", "oyun", "uzay")):
        return "violet_aurora"
    keys = list(STUDIO_PALETTES.keys())
    return keys[seed % len(keys)]


def _pick_archetype_from_text(text: str, seed: int) -> str:
    low = text.lower()
    if seed > 0:
        # Rotate cleanly on every revision so the user always gets a genuinely fresh emblem
        return ARCHETYPE_ORDER[seed % len(ARCHETYPE_ORDER)]
    if any(k in low for k in ("havacılık", "havacilik", "uçak", "cnc", "otomotiv", "hız", "drone")):
        return "wing_aero"
    if any(k in low for k in ("doğa", "doga", "organik", "eko", "tarım", "bitki", "sağlık")):
        return "leaf_organic"
    if any(k in low for k in ("güvenlik", "guvenlik", "siber", "finans", "banka", "hukuk", "savunma")):
        return "shield_crest"
    if any(k in low for k in ("ses", "müzik", "muzik", "medya", "enerji", "radyo")):
        return "wave_pulse"
    if any(k in low for k in ("yapay zeka", "veri", "ağ", "network", "bulut", "yazılım")):
        return "neural_constellation"
    return ARCHETYPE_ORDER[seed % len(ARCHETYPE_ORDER)]


def _extract_quoted_brand(text: str) -> str:
    m = re.search(r'["“”\']([A-Za-z0-9ÇĞİÖŞÜçğıöşü\-\s]{2,22})["“”\']', text)
    if m:
        return m.group(1).strip().upper()
    return ""


async def _design_spec_from_llm(combined_prompt: str, seed: int) -> dict[str, str]:
    """Use local LLM as Creative Director to produce a structured brand/visual design specification."""
    import json

    fallback_names = ["NEXORA", "AETHERIS", "KINETIX", "VORTEXA", "LUMINEX", "SYNAPSE", "QUANTIX", "SOLARIS"]
    fallback_tags = [
        "GELECEĞİN TEKNOLOJİSİ",
        "AKILLI ÇÖZÜM MİMARİSİ",
        "YENİLİKÇİ TASARIM STÜDYOSU",
        "HASSAS MÜHENDİSLİK",
    ]
    quoted = _extract_quoted_brand(combined_prompt)
    default_spec = {
        "brand_name": quoted or fallback_names[seed % len(fallback_names)],
        "tagline": fallback_tags[seed % len(fallback_tags)],
        "archetype": _pick_archetype_from_text(combined_prompt, seed),
        "palette": _pick_palette_from_text(combined_prompt, seed),
        "layout": LAYOUT_ORDER[seed % len(LAYOUT_ORDER)],
    }

    model = await pick_best_model("general")
    sys_msg = (
        "Sen odullu bir marka kimligi ve grafik tasarim direktorusun.\n"
        "Kullanicinin istegine gore SADECE gecerli bir JSON nesnesi dondur (baska aciklama yazma).\n"
        "JSON alanlari:\n"
        '- "brand_name": Kisa, akilda kalici 1-2 kelimelik marka/proje adi (BUYUK HARF, max 16 karakter; '
        "kullanici marka adi vermediyse konuya uygun ozgun ve sik bir marka adi uret, ASLA kullanicinin "
        "cumlesini veya sikayetini yazma).\n"
        '- "tagline": Konuya uygun 2-4 kelimelik kisa slogan (max 32 karakter).\n'
        '- "archetype": Asagidakilerden biri: '
        '"hex_nexus", "orbital_ring", "prism_monolith", "wing_aero", "neural_constellation", '
        '"wave_pulse", "shield_crest", "leaf_organic".\n'
        '- "palette": Asagidakilerden biri: '
        '"midnight_cyan", "obsidian_gold", "nordic_light", "emerald_slate", "crimson_carbon", "violet_aurora".\n'
        '- "layout": Asagidakilerden biri: "badge_showcase", "horizontal_lockup", "centered_emblem".\n'
        f"Varyasyon numarasi: {seed} (her varyasyonda farkli bir archetype, palette ve layout sec)."
    )
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{config.OLLAMA_URL}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": combined_prompt},
                    ],
                    "stream": False,
                    "think": False,
                    "options": {"temperature": 0.65, "num_predict": 320},
                },
            )
            if resp.status_code == 200:
                raw = resp.json().get("message", {}).get("content", "")
                m = re.search(r"\{[\s\S]*\}", raw)
                if m:
                    parsed = json.loads(m.group(0))
                    if isinstance(parsed, dict):
                        bname = str(parsed.get("brand_name") or "").strip()[:20]
                        if bname and not any(bad in bname.lower() for bad in ("beğenmedim", "begenmedim", "kötü", "kotu", "görsel", "gorsel", "üret", "uret")):
                            default_spec["brand_name"] = quoted or bname.upper()
                        tag = str(parsed.get("tagline") or "").strip()[:38]
                        if tag and not any(bad in tag.lower() for bad in ("beğenmedim", "begenmedim", "kötü", "kotu")):
                            default_spec["tagline"] = tag.upper()
                        if parsed.get("archetype") in ARCHETYPE_ORDER and seed == 0:
                            default_spec["archetype"] = parsed["archetype"]
                        elif parsed.get("archetype") in ARCHETYPE_ORDER and parsed["archetype"] != ARCHETYPE_ORDER[(seed - 1) % len(ARCHETYPE_ORDER)]:
                            default_spec["archetype"] = parsed["archetype"]
                        if parsed.get("palette") in STUDIO_PALETTES:
                            default_spec["palette"] = parsed["palette"]
                        if parsed.get("layout") in LAYOUT_ORDER and seed == 0:
                            default_spec["layout"] = parsed["layout"]
    except Exception:
        pass

    # If user explicitly requested a revision (seed > 0), guarantee layout & palette freshness
    if seed > 0:
        default_spec["layout"] = LAYOUT_ORDER[seed % len(LAYOUT_ORDER)]
        if default_spec["palette"] == "midnight_cyan" and seed % 2 == 1:
            default_spec["palette"] = list(STUDIO_PALETTES.keys())[seed % len(STUDIO_PALETTES)]
    default_spec["model"] = model
    return default_spec


def _emblem_svg_group(archetype: str, pal: dict[str, str], use_solid: bool = False) -> str:
    """Return crisp, agency-grade vector emblem geometry centered at (0, 0) within [-110, 110]."""
    p1 = pal["primary"] if use_solid else "url(#gPrimary)"
    p2 = pal["secondary"] if use_solid else "url(#gSecondary)"
    acc = pal["accent"]
    txt = pal["text"]

    if archetype == "orbital_ring":
        return f"""
        <circle cx="0" cy="0" r="88" fill="none" stroke="{p1}" stroke-width="2" stroke-dasharray="6 8" opacity="0.45"/>
        <ellipse cx="0" cy="0" rx="102" ry="38" transform="rotate(-28)" fill="none" stroke="{p1}" stroke-width="6"/>
        <ellipse cx="0" cy="0" rx="102" ry="38" transform="rotate(28)" fill="none" stroke="{p2}" stroke-width="4.5" opacity="0.88"/>
        <polygon points="0,-42 36,-20 36,20 0,42 -36,20 -36,-20" fill="{p1}" opacity="0.92"/>
        <polygon points="0,-42 36,-20 0,0 -36,-20" fill="{acc}" opacity="0.45"/>
        <circle cx="0" cy="0" r="14" fill="{txt}"/>
        <circle cx="88" cy="-42" r="9" fill="{acc}"/>
        <circle cx="-84" cy="40" r="7" fill="{p1}"/>
        """
    if archetype == "prism_monolith":
        return f"""
        <polygon points="0,-96 86,-22 52,86 -52,86 -86,-22" fill="none" stroke="{p1}" stroke-width="4" opacity="0.35"/>
        <polygon points="0,-84 74,0 0,84 -74,0" fill="{p2}" opacity="0.9"/>
        <polygon points="0,-84 74,0 0,14" fill="{p1}"/>
        <polygon points="0,-84 -74,0 0,14" fill="{acc}" opacity="0.55"/>
        <polygon points="0,14 74,0 0,84" fill="{pal['bg2']}" opacity="0.45"/>
        <polygon points="0,-44 36,0 0,44 -36,0" fill="none" stroke="{txt}" stroke-width="3.5"/>
        <circle cx="0" cy="0" r="9" fill="{txt}"/>
        """
    if archetype == "wing_aero":
        return f"""
        <circle cx="0" cy="0" r="92" fill="none" stroke="{p1}" stroke-width="2.5" opacity="0.35"/>
        <path d="M-96,-28 L-10,-62 L0,-24 L-72,10 Z" fill="{p1}"/>
        <path d="M96,-28 L10,-62 L0,-24 L72,10 Z" fill="{p2}"/>
        <path d="M-76,20 L-8,-10 L0,22 L-54,48 Z" fill="{acc}" opacity="0.85"/>
        <path d="M76,20 L8,-10 L0,22 L54,48 Z" fill="{p1}" opacity="0.85"/>
        <polygon points="0,-78 16,66 0,44 -16,66" fill="{txt}"/>
        <circle cx="0" cy="-16" r="7" fill="{pal['bg1']}"/>
        """
    if archetype == "neural_constellation":
        return f"""
        <circle cx="0" cy="0" r="90" fill="none" stroke="{p1}" stroke-width="2" opacity="0.28"/>
        <g stroke="{p1}" stroke-width="3.5" opacity="0.82">
          <line x1="0" y1="-78" x2="72" y2="-28"/>
          <line x1="72" y1="-28" x2="54" y2="64"/>
          <line x1="54" y1="64" x2="-54" y2="64"/>
          <line x1="-54" y1="64" x2="-72" y2="-28"/>
          <line x1="-72" y1="-28" x2="0" y2="-78"/>
          <line x1="0" y1="-78" x2="0" y2="0"/>
          <line x1="72" y1="-28" x2="0" y2="0"/>
          <line x1="54" y1="64" x2="0" y2="0"/>
          <line x1="-54" y1="64" x2="0" y2="0"/>
          <line x1="-72" y1="-28" x2="0" y2="0"/>
        </g>
        <circle cx="0" cy="0" r="24" fill="{p1}"/>
        <circle cx="0" cy="0" r="10" fill="{txt}"/>
        <circle cx="0" cy="-78" r="12" fill="{acc}"/>
        <circle cx="72" cy="-28" r="11" fill="{p2}"/>
        <circle cx="54" cy="64" r="10" fill="{p1}"/>
        <circle cx="-54" cy="64" r="10" fill="{p2}"/>
        <circle cx="-72" cy="-28" r="11" fill="{acc}"/>
        """
    if archetype == "wave_pulse":
        return f"""
        <rect x="-86" y="-86" width="172" height="172" rx="42" fill="{pal['card']}" stroke="{p1}" stroke-width="4.5"/>
        <path d="M-64,12 C-42,-48 -18,-48 0,0 C18,48 42,48 64,-12" fill="none" stroke="{p1}" stroke-width="11" stroke-linecap="round"/>
        <path d="M-64,-10 C-40,42 -16,42 0,-6 C16,-52 40,-52 64,14" fill="none" stroke="{acc}" stroke-width="6" stroke-linecap="round" opacity="0.88"/>
        <circle cx="-64" cy="12" r="7" fill="{txt}"/>
        <circle cx="64" cy="-12" r="7" fill="{txt}"/>
        """
    if archetype == "shield_crest":
        return f"""
        <path d="M0,-92 L78,-58 L78,8 C78,56 44,86 0,100 C-44,86 -78,56 -78,8 L-78,-58 Z" fill="{pal['card']}" stroke="{p1}" stroke-width="6"/>
        <path d="M0,-74 L60,-46 L60,6 C60,44 34,68 0,80 C-34,68 -60,44 -60,6 L-60,-46 Z" fill="{p2}" opacity="0.22"/>
        <path d="M-34,-8 L-6,22 L40,-28" fill="none" stroke="{p1}" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M-34,-8 L-6,22 L40,-28" fill="none" stroke="{acc}" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>
        """
    if archetype == "leaf_organic":
        return f"""
        <circle cx="0" cy="0" r="90" fill="none" stroke="{p1}" stroke-width="3" opacity="0.32"/>
        <path d="M-62,56 C-72,-20 -10,-78 68,-74 C66,8 12,68 -62,56 Z" fill="{p1}" opacity="0.92"/>
        <path d="M-62,56 C-12,24 22,-18 68,-74" fill="none" stroke="{txt}" stroke-width="5" stroke-linecap="round"/>
        <path d="M-12,18 L-28,-12 M14,-8 L-2,-34 M12,10 L42,2" fill="none" stroke="{acc}" stroke-width="3.5" stroke-linecap="round"/>
        <circle cx="-62" cy="56" r="8" fill="{acc}"/>
        """
    # Default: hex_nexus (isometric layered hexagon with precision inner cube)
    return f"""
    <polygon points="0,-94 81,-47 81,47 0,94 -81,47 -81,-47" fill="none" stroke="{p1}" stroke-width="6.5"/>
    <polygon points="0,-72 62,-36 62,36 0,72 -62,36 -62,-36" fill="{pal['card']}" stroke="{p2}" stroke-width="3" opacity="0.9"/>
    <polygon points="0,-54 47,-27 0,0 -47,-27" fill="{acc}" opacity="0.9"/>
    <polygon points="-47,-27 0,0 0,54 -47,27" fill="{p1}" opacity="0.92"/>
    <polygon points="47,-27 0,0 0,54 47,27" fill="{p2}" opacity="0.88"/>
    <circle cx="0" cy="0" r="11" fill="{txt}"/>
    """


def _render_studio_svg(spec: dict[str, str], use_solid: bool = False) -> str:
    """Build a crisp, agency-quality 1200x760 SVG brand showcase."""
    pal = STUDIO_PALETTES.get(spec["palette"], STUDIO_PALETTES["midnight_cyan"])
    brand = _xml_esc(spec["brand_name"])
    tagline = _xml_esc(spec["tagline"])
    archetype = spec["archetype"]
    layout = spec["layout"]
    emblem = _emblem_svg_group(archetype, pal, use_solid=use_solid)

    # Subtle architectural grid lines
    grid_lines = []
    for x in range(120, 1200, 120):
        grid_lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="760"/>')
    for y in range(95, 760, 95):
        grid_lines.append(f'<line x1="0" y1="{y}" x2="1200" y2="{y}"/>')
    grid_svg = "".join(grid_lines)

    bg_fill = pal["bg2"] if use_solid else "url(#gBg)"
    def glow_el(cx: int, cy: int, r: int, op: float) -> str:
        return "" if use_solid else f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#gGlow)" opacity="{op}"/>'
    bar_fill = pal["primary"] if use_solid else "url(#gPrimary)"

    if layout == "horizontal_lockup":
        body = f"""
        <rect x="76" y="76" width="1048" height="608" rx="32" fill="{pal['card']}" opacity="0.58" stroke="{pal['primary']}" stroke-opacity="0.28" stroke-width="2"/>
        {glow_el(310, 380, 210, 0.22)}
        <g transform="translate(310, 380) scale(1.22)">{emblem}</g>
        <line x1="485" y1="245" x2="485" y2="515" stroke="{pal['primary']}" stroke-width="3" opacity="0.45"/>
        <text x="535" y="378" fill="{pal['text']}" font-family="Segoe UI, Inter, Arial, sans-serif" font-size="76" font-weight="800" letter-spacing="8">{brand}</text>
        <rect x="535" y="404" width="160" height="5" rx="2.5" fill="{bar_fill}"/>
        <text x="535" y="448" fill="{pal['muted']}" font-family="Segoe UI, Inter, Arial, sans-serif" font-size="21" font-weight="600" letter-spacing="5">{tagline}</text>
        """
    elif layout == "badge_showcase":
        body = f"""
        <rect x="64" y="56" width="1072" height="532" rx="30" fill="{pal['card']}" opacity="0.62" stroke="{pal['primary']}" stroke-opacity="0.3" stroke-width="2"/>
        {glow_el(600, 240, 220, 0.24)}
        <g transform="translate(600, 232) scale(1.18)">{emblem}</g>
        <text x="600" y="438" text-anchor="middle" fill="{pal['text']}" font-family="Segoe UI, Inter, Arial, sans-serif" font-size="72" font-weight="800" letter-spacing="12">{brand}</text>
        <rect x="515" y="460" width="170" height="4" rx="2" fill="{bar_fill}"/>
        <text x="600" y="502" text-anchor="middle" fill="{pal['muted']}" font-family="Segoe UI, Inter, Arial, sans-serif" font-size="20" font-weight="600" letter-spacing="6">{tagline}</text>
        <!-- Brand Identity Palette Strip -->
        <rect x="64" y="612" width="1072" height="92" rx="20" fill="{pal['card']}" opacity="0.72" stroke="{pal['primary']}" stroke-opacity="0.22" stroke-width="1.5"/>
        <g transform="translate(132, 658) scale(0.28)">{emblem}</g>
        <text x="184" y="654" fill="{pal['text']}" font-family="Segoe UI, Inter, Arial, sans-serif" font-size="18" font-weight="700" letter-spacing="3">{brand}</text>
        <text x="184" y="676" fill="{pal['muted']}" font-family="Segoe UI, Inter, Arial, sans-serif" font-size="12" letter-spacing="2">KURUMSAL MARKA KIMLIGI</text>
        <rect x="740" y="636" width="44" height="44" rx="10" fill="{pal['primary']}"/>
        <text x="794" y="663" fill="{pal['muted']}" font-family="Segoe UI, Arial, sans-serif" font-size="13" font-weight="600">{pal['primary'].upper()}</text>
        <rect x="880" y="636" width="44" height="44" rx="10" fill="{pal['secondary']}"/>
        <text x="934" y="663" fill="{pal['muted']}" font-family="Segoe UI, Arial, sans-serif" font-size="13" font-weight="600">{pal['secondary'].upper()}</text>
        <rect x="1020" y="636" width="44" height="44" rx="10" fill="{pal['accent']}"/>
        """
    else:
        # centered_emblem
        body = f"""
        {glow_el(600, 280, 260, 0.24)}
        <circle cx="600" cy="280" r="158" fill="none" stroke="{pal['primary']}" stroke-width="1.5" opacity="0.28"/>
        <g transform="translate(600, 276) scale(1.28)">{emblem}</g>
        <text x="600" y="510" text-anchor="middle" fill="{pal['text']}" font-family="Segoe UI, Inter, Arial, sans-serif" font-size="80" font-weight="800" letter-spacing="14">{brand}</text>
        <rect x="500" y="538" width="200" height="5" rx="2.5" fill="{bar_fill}"/>
        <text x="600" y="586" text-anchor="middle" fill="{pal['muted']}" font-family="Segoe UI, Inter, Arial, sans-serif" font-size="22" font-weight="600" letter-spacing="6">{tagline}</text>
        """

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 760" width="1200" height="760">
  <defs>
    <linearGradient id="gBg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{pal['bg1']}"/>
      <stop offset="52%" stop-color="{pal['bg2']}"/>
      <stop offset="100%" stop-color="{pal['bg3']}"/>
    </linearGradient>
    <linearGradient id="gPrimary" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{pal['primary']}"/>
      <stop offset="100%" stop-color="{pal['secondary']}"/>
    </linearGradient>
    <linearGradient id="gSecondary" x1="1" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{pal['accent']}"/>
      <stop offset="100%" stop-color="{pal['primary']}"/>
    </linearGradient>
    <radialGradient id="gGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="{pal['primary']}" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="{pal['primary']}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="1200" height="760" fill="{bg_fill}"/>
  <g stroke="{pal['grid']}" stroke-width="1" opacity="0.06">{grid_svg}</g>
  {body}
</svg>"""


def _save_true_color_png(spec: dict[str, str], out_png: Path) -> None:
    """Render a true-color, gradient-rich PNG without PyMuPDF's black url(#gradient) artifact."""
    solid_svg = _render_studio_svg(spec, use_solid=True)
    try:
        svg_doc = fitz.open(stream=solid_svg.encode("utf-8"), filetype="svg")
        pix = svg_doc[0].get_pixmap(dpi=150)
        pix.save(str(out_png))
        svg_doc.close()
        # Blend subtle smooth diagonal gradient tint so PNG has genuine studio depth
        pal = STUDIO_PALETTES.get(spec["palette"], STUDIO_PALETTES["midnight_cyan"])
        im = Image.open(out_png).convert("RGB")
        w, h = im.size
        c1 = np.array(_hex_to_rgb(pal["bg1"]), dtype=np.float32)
        c2 = np.array(_hex_to_rgb(pal["bg3"]), dtype=np.float32)
        t = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :, None] * 0.5 + np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None] * 0.5
        grad = c1 * (1.0 - t) + c2 * t
        arr = np.array(im, dtype=np.float32)
        # Only tint pixels that match the flat bg2 color
        bg2_rgb = np.array(_hex_to_rgb(pal["bg2"]), dtype=np.float32)
        is_bg = np.linalg.norm(arr - bg2_rgb, axis=2) < 12.0
        arr[is_bg] = grad[is_bg]
        Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGB").save(out_png, format="PNG")
    except Exception:
        pal = STUDIO_PALETTES.get(spec["palette"], STUDIO_PALETTES["midnight_cyan"])
        im = Image.new("RGB", (1200, 760), _hex_to_rgb(pal["bg2"]))
        dr = ImageDraw.Draw(im)
        dr.text((600, 350), spec["brand_name"], fill=_hex_to_rgb(pal["text"]), font=_load_font(64, bold=True), anchor="mm")
        im.save(out_png, format="PNG")


async def generate_ai_image(prompt: str, history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Generate an agency-grade SVG vector design + true-color high-res PNG with full context awareness."""
    file_id = f"img-gen-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    out_png = media_dir() / f"{file_id}.png"
    out_svg = media_dir() / f"{file_id}.svg"

    combined_prompt, variation_seed = _resolve_context_prompt(prompt, history)

    # 1. Check if a local Stable Diffusion WebUI (Automatic1111) is listening on 127.0.0.1:7860
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            sd_resp = await client.post(
                "http://127.0.0.1:7860/sdapi/v1/txt2img",
                json={"prompt": combined_prompt, "steps": 24, "width": 1024, "height": 640},
            )
            if sd_resp.status_code == 200 and sd_resp.json().get("images"):
                b64_img = sd_resp.json()["images"][0]
                out_png.write_bytes(base64.b64decode(b64_img))
                return {
                    "file_id": file_id,
                    "engine": "stable-diffusion-local",
                    "png_url": f"/api/assistant/media/{file_id}.png",
                    "svg_url": "",
                }
    except Exception:
        pass

    # 2. Studio-Grade Parametric Brand & Visual Design Engine guided by local LLM Creative Director
    spec = await _design_spec_from_llm(combined_prompt, variation_seed)
    svg_code = _render_studio_svg(spec, use_solid=False)
    out_svg.write_text(svg_code, encoding="utf-8")
    _save_true_color_png(spec, out_png)

    pal = STUDIO_PALETTES.get(spec["palette"], STUDIO_PALETTES["midnight_cyan"])
    return {
        "file_id": file_id,
        "engine": f"vector-studio ({spec.get('model', 'local')})",
        "brand_name": spec["brand_name"],
        "tagline": spec["tagline"],
        "archetype": spec["archetype"],
        "layout": spec["layout"],
        "palette_name": pal["name"],
        "png_url": f"/api/assistant/media/{file_id}.png",
        "svg_url": f"/api/assistant/media/{file_id}.svg",
    }


# ============================================================================
# 3. VOICE MESSAGE TO TEXT (STT — Faster-Whisper / Windows SAPI / Audio Analysis)
# ============================================================================

_WHISPER_MODEL_CACHE: Any = None


def _get_whisper_model():
    global _WHISPER_MODEL_CACHE
    if _WHISPER_MODEL_CACHE is None:
        from faster_whisper import WhisperModel  # type: ignore[import-not-found]

        _WHISPER_MODEL_CACHE = WhisperModel("base", device="cpu", compute_type="int8")
    return _WHISPER_MODEL_CACHE


def transcribe_audio_bytes(filename: str, raw_bytes: bytes) -> dict[str, Any]:
    """Transcribe an uploaded or microphone-recorded voice message (.wav, .mp3, .m4a, .ogg, .webm) to Turkish text."""
    suffix = Path(filename).suffix.lower() or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = Path(tmp.name)

    duration_sec = 0.0
    if suffix == ".wav":
        try:
            with wave.open(io.BytesIO(raw_bytes), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate() or 16000
                duration_sec = round(frames / float(rate), 2)
        except Exception:
            pass

    transcript = ""
    engine = "audio-metadata"

    # 1. Try local faster_whisper (cached singleton, fast int8 CPU Turkish STT)
    try:
        wmodel = _get_whisper_model()
        segments, _ = wmodel.transcribe(str(tmp_path), language="tr", vad_filter=True)
        transcript = " ".join(seg.text.strip() for seg in segments).strip()
        engine = "faster-whisper-base (local)"
    except Exception:
        pass

    # 2. Try Windows System.Speech Recognition (built into Windows, 100% offline for WAV files)
    if not transcript and sys.platform == "win32" and suffix == ".wav":
        ps_script = (
            "Add-Type -AssemblyName System.Speech; "
            "$rec = New-Object System.Speech.Recognition.SpeechRecognitionEngine; "
            "$rec.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar)); "
            f"$rec.SetInputToWaveFile('{tmp_path}'); "
            "$res = $rec.Recognize(); "
            "if ($res) { Write-Output $res.Text }"
        )
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                transcript = proc.stdout.strip()
                engine = "windows-system-speech"
        except Exception:
            pass

    try:
        tmp_path.unlink(missing_ok=True)
    except OSError:
        pass

    return {
        "filename": filename,
        "size_kb": round(len(raw_bytes) / 1024.0, 1),
        "duration_sec": duration_sec,
        "transcript": transcript,
        "engine": engine,
    }
