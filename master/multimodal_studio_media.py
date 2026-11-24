"""Multimodal Media Engine: CV Image Processing, Local STT, SVG Sanitization, Rasterization & Procedural Art."""

from __future__ import annotations

import io
import logging
import math
import re
import shutil
import sys
import tempfile
import uuid
import wave
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pymupdf as fitz
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

import config
import process_utils

IMAGE_EDIT_KEYWORDS = (
    "siyah beyaz", "gri ton", "grayscale", "kontrast", "netleştir", "netlestir", "keskinleştir", "bulanık",
    "bulanik", "blur", "kenar", "eskiz", "sketch", "edge", "ters çevir", "negatif", "invert", "döndür",
    "dondur", "rotate", "çevir", "ayna", "flip", "mirror", "boyutlandır", "boyutlandir", "resize", "küçült",
    "kucult", "büyüt", "buyut", "ölçekle", "olcekle", "2x", "upscale", "kırp", "kirp", "crop", "parlaklık",
    "parlaklik", "karart", "koyulaştır", "koyulastir", "darken", "doygunluk", "renk canlandır", "renk canlandir",
    "canlı", "canli", "saturate", "çerçeve", "cerceve", "kenarlık", "kenarlik", "border", "frame", "yuvarla",
    "webp", "jpg", "jpeg", "sola döndür", "sola dondur", "sağa döndür", "saga dondur", "270", "sepya", "sepia",
    "arka plan", "arkaplan", "filigran", "yazı ekle", "yazi ekle", "watermark", "düzenle", "duzenle", "efekt",
    "işle", "isle", "görüntü işle", "goruntu isle",
)

_WHISPER_CACHE: dict[str, Any] = {"model": None}
_LOG = logging.getLogger(__name__)
_DANGEROUS_SVG_TAGS = ("script", "foreignobject", "iframe", "object", "embed", "applet")
_SVG_PRIMITIVES = ("rect", "circle", "ellipse", "path", "polygon", "polyline", "line")


def media_dir() -> Path:
    d = config.DATA_DIR / "media"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = ("arialbd.ttf", "DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") if bold else (
        "arial.ttf", "DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    for path in names:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def is_image_edit_request(prompt: str) -> bool:
    lower = prompt.lower()
    return any(k in lower for k in IMAGE_EDIT_KEYWORDS)


def _apply_rotate_and_scale(img: Image.Image, prompt: str, lower: str, applied: list[str]) -> Image.Image:
    if any(k in lower for k in ("döndür", "dondur", "rotate", "sola döndür", "sağa döndür", "270")):
        rot = (180, "180 Derece Döndürme") if "180" in lower else (
            (90, "90 Derece Sola Döndürme") if any(k in lower for k in ("sola", "ccw", "left")) else (
                (270, "270 Derece Döndürme") if "270" in lower else (-90, "90 Derece Sağa Döndürme")
            )
        )
        img = img.rotate(rot[0], expand=True)
        applied.append(rot[1])
    if any(k in lower for k in ("ayna", "yatay çevir", "flip", "mirror")):
        img = ImageOps.mirror(img)
        applied.append("Yatay Aynalama (Mirror)")
    if m_size := re.search(r"(\d{2,4})\s*[xX\u00d7]\s*(\d{2,4})", prompt):
        nw, nh = min(4096, int(m_size.group(1))), min(4096, int(m_size.group(2)))
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
        applied.append(f"Yeniden Boyutlandırma ({nw}x{nh} px)")
    elif any(k in lower for k in ("büyüt", "buyut", "2x", "upscale")):
        nw, nh = min(4096, img.width * 2), min(4096, img.height * 2)
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
        applied.append(f"2x Büyütme ({nw}x{nh} px)")
    elif any(k in lower for k in ("küçült", "kucult", "yarı", "yari")):
        nw, nh = max(64, img.width // 2), max(64, img.height // 2)
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
        applied.append(f"%50 Ölçekleme ({nw}x{nh} px)")
    elif any(k in lower for k in ("kırp", "kirp", "crop")):
        mx, my = int(img.width * 0.12), int(img.height * 0.12)
        img = img.crop((mx, my, img.width - mx, img.height - my))
        applied.append("Merkez Odaklı Kırpma (%76 Alan)")
    return img


def _apply_geometry_ops(img: Image.Image, prompt: str, lower: str, applied: list[str]) -> Image.Image:
    img = _apply_rotate_and_scale(img, prompt, lower, applied)
    if "yuvarla" in lower:
        radius = max(12, min(img.width, img.height) // 10)
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=radius, fill=255)
        canvas = Image.new("RGB", img.size, (15, 23, 42))
        canvas.paste(img, mask=mask)
        img = canvas
        applied.append(f"Yuvarlatılmış Köşeler (r={radius}px)")
    if any(k in lower for k in ("çerçeve", "cerceve", "kenarlık", "kenarlik", "border", "frame")):
        pad = max(14, min(img.width, img.height) // 24)
        img = ImageOps.expand(ImageOps.expand(img, border=3, fill=(56, 189, 248)), border=pad, fill=(15, 23, 42))
        applied.append(f"Stilize Çerçeve ({pad}px)")
    return img


def _apply_background_and_color_ops(img: Image.Image, lower: str, applied: list[str]) -> Image.Image:
    if any(k in lower for k in ("arka plan", "arkaplan", "background")):
        arr = np.array(img, dtype=np.float32)
        bg_color = np.mean(np.vstack([arr[0, 0], arr[0, -1], arr[-1, 0], arr[-1, -1]]), axis=0)
        arr[np.linalg.norm(arr - bg_color, axis=2) < 42.0] = [255.0, 255.0, 255.0]
        img = Image.fromarray(arr.astype(np.uint8), mode="RGB")
        applied.append("Arka Plan Temizleme (Köşe Renk Segmentasyonu)")
    if any(k in lower for k in ("siyah beyaz", "gri", "grayscale")):
        img = ImageOps.grayscale(img).convert("RGB")
        applied.append("Gri Tonlama (Grayscale)")
    if any(k in lower for k in ("sepya", "sepia", "nostalji")):
        gray = np.array(ImageOps.grayscale(img), dtype=np.float32)
        sep = np.stack([np.clip(gray * 1.08 + 28, 0, 255), np.clip(gray * 0.92 + 12, 0, 255), np.clip(gray * 0.74, 0, 255)], axis=-1)
        img = Image.fromarray(sep.astype(np.uint8), mode="RGB")
        applied.append("Sepya Tonlama Filtresi")
    if any(k in lower for k in ("ters çevir", "negatif", "invert")):
        img = ImageOps.invert(img)
        applied.append("Renk Ters Çevirme (Negatif)")
    return img


def _apply_detail_and_tone_filters(img: Image.Image, lower: str, applied: list[str]) -> Image.Image:
    has_border_word = "kenarlık" in lower or "kenarlik" in lower
    if (("kenar" in lower and not has_border_word) or any(k in lower for k in ("eskiz", "sketch", "edge"))):
        edges = ImageOps.grayscale(img).filter(ImageFilter.FIND_EDGES)
        img = ImageEnhance.Contrast(ImageOps.invert(edges)).enhance(2.2).convert("RGB")
        applied.append("Sobel Kenar Tespiti / Teknik Eskiz Dönüşümü")
    if any(k in lower for k in ("bulanık", "bulanik", "blur")):
        img = img.filter(ImageFilter.GaussianBlur(radius=3.5))
        applied.append("Gaussian Bulanıklaştırma (r=3.5)")
    if any(k in lower for k in ("netleştir", "netlestir", "keskin", "sharpen")):
        img = img.filter(ImageFilter.UnsharpMask(radius=2.0, percent=180, threshold=3))
        applied.append("Unsharp Mask Keskinleştirme")
    if any(k in lower for k in ("doygunluk", "renk canlandır", "renk canlandir", "canlı", "canli", "saturate")):
        img = ImageEnhance.Color(img).enhance(1.45)
        applied.append("Renk Doygunluğu Artırma (1.45x)")
    if any(k in lower for k in ("kontrast", "iyileştir", "iyilestir")) or ("canlandır" in lower and "renk canlandır" not in lower):
        img = ImageEnhance.Color(ImageEnhance.Contrast(ImageOps.autocontrast(img, cutoff=1)).enhance(1.32)).enhance(1.18)
        applied.append("Otomatik Histogram Germe ve Kontrast Güçlendirme")
    if any(k in lower for k in ("karart", "koyulaştır", "koyulastir", "darken")):
        img = ImageEnhance.Brightness(img).enhance(0.72)
        applied.append("Karartma (Parlaklık %72)")
    elif any(k in lower for k in ("parlak", "aydınlat", "aydinlat", "brighten")):
        img = ImageEnhance.Brightness(img).enhance(1.28)
        applied.append("Parlaklık Artırma (+%28)")
    return img


def _extract_watermark_text(prompt: str) -> str:
    m_txt = re.search(r'["\u201c\u201d\']([^"\u201c\u201d\']{1,50})["\u201c\u201d\']', prompt)
    if m_txt:
        return m_txt.group(1).strip()
    if ":" in prompt:
        tail = re.sub(r"\b(webp|jpg|jpeg|png)\b", "", prompt.rsplit(":", 1)[1], flags=re.IGNORECASE).strip(" .!?,;\"'")
        if tail:
            return tail[:42]
    return "DADP AI"


def _apply_watermark_or_default(img: Image.Image, prompt: str, lower: str, applied: list[str]) -> Image.Image:
    if any(k in lower for k in ("yazı", "yazi", "filigran", "watermark")):
        wm_text = _extract_watermark_text(prompt)
        draw = ImageDraw.Draw(img)
        font = _load_font(max(18, img.width // 24), bold=True)
        bbox = draw.textbbox((0, 0), wm_text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        px, py = max(14, img.width - tw - 24), max(14, img.height - th - 24)
        draw.rectangle([px - 10, py - 6, px + tw + 10, py + th + 8], fill=(15, 23, 42))
        draw.text((px, py), wm_text, fill=(248, 250, 252), font=font)
        applied.append(f'Metin / Filigran Ekleme ("{wm_text}")')
    if not applied:
        img = ImageEnhance.Contrast(ImageOps.autocontrast(img, cutoff=1)).enhance(1.2).filter(
            ImageFilter.UnsharpMask(radius=1.6, percent=140, threshold=3)
        )
        applied.append("Otomatik Kontrast Dengeleme ve Netleştirme (HDR İyileştirme)")
    return img


def _resolve_output_format(lower: str) -> tuple[str, str, dict[str, Any]]:
    if "webp" in lower:
        return "webp", "WEBP", {"quality": 90}
    if "jpeg" in lower or "jpg" in lower:
        return "jpg", "JPEG", {"quality": 92}
    return "png", "PNG", {}


def process_and_edit_image(raw_bytes: bytes, prompt: str) -> dict[str, Any]:
    """Apply CV filters, geometric transforms, background removal, watermarks, or format conversion."""
    orig = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    img, lower, applied = orig.copy(), prompt.lower(), []
    img = _apply_geometry_ops(img, prompt, lower, applied)
    img = _apply_background_and_color_ops(img, lower, applied)
    img = _apply_detail_and_tone_filters(img, lower, applied)
    img = _apply_watermark_or_default(img, prompt, lower, applied)

    ext, pil_fmt, save_kw = _resolve_output_format(lower)
    if ext != "png":
        applied.append(f"Format Dönüştürme ({pil_fmt})")
    file_id = f"img-edit-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    filename = f"{file_id}.{ext}"
    img.save(media_dir() / filename, format=pil_fmt, **save_kw)
    arr_out = np.array(img)
    return {
        "original_size": f"{orig.width}x{orig.height} px",
        "output_size": f"{img.width}x{img.height} px",
        "mean_brightness": round(float(np.mean(arr_out)), 1),
        "std_contrast": round(float(np.std(arr_out)), 1),
        "applied_filters": applied,
        "file_id": file_id,
        "format": ext,
        "filename": filename,
        "url": f"/api/assistant/media/{filename}",
    }


def _get_whisper_model() -> Any:
    if _WHISPER_CACHE["model"] is None:
        from faster_whisper import WhisperModel  # type: ignore[import-not-found]

        _WHISPER_CACHE["model"] = WhisperModel("base", device="cpu", compute_type="int8")
    return _WHISPER_CACHE["model"]


def _decode_wav_to_float32_16k(raw_bytes: bytes) -> tuple[np.ndarray | None, float]:
    try:
        with wave.open(io.BytesIO(raw_bytes), "rb") as wf:
            nch, sw, rate = wf.getnchannels() or 1, wf.getsampwidth(), wf.getframerate() or 16000
            frames, duration = wf.readframes(wf.getnframes()), round(wf.getnframes() / float(rate), 2)
            if sw == 2:
                arr = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            elif sw == 4:
                arr = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
            else:
                arr = (np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
            if nch > 1:
                arr = arr.reshape(-1, nch).mean(axis=1)
            if rate != 16000 and len(arr) > 0:
                tlen = max(1, round(len(arr) * 16000.0 / rate))
                arr = np.interp(np.linspace(0.0, 1.0, tlen, dtype=np.float32), np.linspace(0.0, 1.0, len(arr), dtype=np.float32), arr).astype(np.float32)
            return arr, duration
    except (wave.Error, OSError, ValueError, TypeError, ZeroDivisionError) as exc:
        _LOG.debug("Recoverable error suppressed: %s", exc)
        return None, 0.0


def _decode_pyav_to_float32_16k(tmp_path: Path) -> tuple[np.ndarray | None, float]:
    try:
        import av  # type: ignore[import-not-found]

        with av.open(str(tmp_path), mode="r") as container:
            stream = next((s for s in container.streams if s.type == "audio"), None)
            if stream is None:
                return None, 0.0
            resampler = av.AudioResampler(format="fltp", layout="mono", rate=16000)
            chunks = [
                r.to_ndarray().reshape(-1).astype(np.float32)
                for f in container.decode(stream) if isinstance(f, av.AudioFrame) for r in resampler.resample(f)
            ]
            if not chunks:
                return None, 0.0
            arr = np.concatenate(chunks)
            return arr, round(len(arr) / 16000.0, 2)
    except (ImportError, OSError, RuntimeError, ValueError, TypeError, AttributeError, KeyError):
        return None, 0.0


def _decode_audio_to_float32_16k(raw_bytes: bytes, tmp_path: Path, suffix: str) -> tuple[np.ndarray | None, float]:
    if suffix == ".wav":
        arr, duration = _decode_wav_to_float32_16k(raw_bytes)
        if arr is not None:
            return arr, duration
    return _decode_pyav_to_float32_16k(tmp_path)


def _transcribe_windows_sapi(tmp_path: Path) -> str:
    ps_bin = shutil.which("powershell")
    if not ps_bin:
        return ""
    ps_script = (
        "Add-Type -AssemblyName System.Speech; $rec = New-Object System.Speech.Recognition.SpeechRecognitionEngine; "
        f"$rec.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar)); $rec.SetInputToWaveFile('{tmp_path}'); "
        "$res = $rec.Recognize(); if ($res) { Write-Output $res.Text }"
    )
    try:
        proc = process_utils.run_process([ps_bin, "-NoProfile", "-Command", ps_script], timeout_s=15.0)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except (OSError, ValueError) as exc:
        _LOG.debug("Recoverable error suppressed: %s", exc)
    return ""


def transcribe_audio_bytes(filename: str, raw_bytes: bytes) -> dict[str, Any]:
    """Transcribe an uploaded or microphone-recorded voice message (.wav, .mp3, .m4a, .ogg, .webm)."""
    suffix = Path(filename).suffix.lower() or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = Path(tmp.name)

    audio_np, duration_sec = _decode_audio_to_float32_16k(raw_bytes, tmp_path, suffix)
    transcript, engine = "", "audio-metadata"
    if audio_np is not None and len(audio_np) > 0:
        try:
            segments, _ = _get_whisper_model().transcribe(audio_np, language="tr", vad_filter=False)
            transcript, engine = " ".join(seg.text.strip() for seg in segments).strip(), "faster-whisper-base (local)"
        except (ImportError, OSError, RuntimeError, ValueError, TypeError, AttributeError) as exc:
            _LOG.debug("Recoverable error suppressed: %s", exc)
    if not transcript and sys.platform == "win32" and suffix == ".wav":
        sapi_text = _transcribe_windows_sapi(tmp_path)
        if sapi_text:
            transcript, engine = sapi_text, "windows-system-speech"
    try:
        tmp_path.unlink(missing_ok=True)
    except OSError:
        pass
    return {"filename": filename, "size_kb": round(len(raw_bytes) / 1024.0, 1), "duration_sec": duration_sec, "transcript": transcript, "engine": engine}


# ============================================================================
# SVG SANITIZATION, GRADIENT-SAFE RASTERIZATION & PROCEDURAL SCENIC ARTWORK
# ============================================================================


def xml_esc(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    s = h.strip().lstrip("#")
    s = "".join(ch * 2 for ch in s) if len(s) == 3 else s
    if len(s) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", s):
        return (15, 23, 42)
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def _lerp_hex(c1: str, c2: str, t: float) -> str:
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    r, g, b = round(r1 + (r2 - r1) * t), round(g1 + (g2 - g1) * t), round(b1 + (b2 - b1) * t)
    return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"


def sanitize_svg(raw: str) -> str | None:
    """Validate and sanitize an LLM-generated SVG into a safe 1200x760 SVG document."""
    text = re.sub(r"```(?:svg|xml|html)?", "", raw or "", flags=re.IGNORECASE).replace("```", "").strip()
    m = re.search(r"<svg\b[\s\S]*?</svg>", text, flags=re.IGNORECASE)
    if not m:
        return None
    svg, low = m.group(0), m.group(0).lower()
    if any(b in low for b in ("javascript:", "vbscript:", "data:text/html")) or re.search(r"\bon[a-z]{2,20}\s*=", low):
        return None
    if re.search(r"<(?:" + "|".join(_DANGEROUS_SVG_TAGS) + r")\b", low):
        return None
    try:
        root = ET.fromstring(svg)
    except ET.ParseError:
        return None
    if not root.tag.lower().endswith("svg"):
        return None
    if sum(1 for el in root.iter() if el.tag.split("}")[-1].lower() in _SVG_PRIMITIVES) < 5:
        return None
    idx = svg.find(">")
    head = svg[: idx + 1]
    if "xmlns=" not in head.lower():
        head = head[:-1] + ' xmlns="http://www.w3.org/2000/svg">'
    if "viewbox=" not in head.lower():
        head = head[:-1] + ' viewBox="0 0 1200 760">'
    return head + svg[idx + 1 :]


def _parse_svg_gradients(svg_text: str) -> dict[str, tuple[str, list[str]]]:
    grads: dict[str, tuple[str, list[str]]] = {}
    for m in re.finditer(r"<(linearGradient|radialGradient)\b([^>]*)>([\s\S]*?)</\1>", svg_text, re.IGNORECASE):
        m_id = re.search(r'id=["\']([^"\']+)["\']', m.group(2))
        stops = re.findall(r'stop-color=["\']?(#[0-9a-fA-F]{3,6})["\']?', m.group(3))
        if m_id and stops:
            grads[m_id.group(1)] = (m.group(1).lower(), stops)
    return grads


def _expand_linear_rect(attrs: str, stops: list[str]) -> str:
    def _num(name: str, default: float) -> float:
        m = re.search(rf'\b{name}=["\']([0-9.]+)["\']', attrs)
        return float(m.group(1)) if m else default

    x, y, w, h = _num("x", 0.0), _num("y", 0.0), _num("width", 1200.0), _num("height", 760.0)
    if w < 300 or h < 120 or len(stops) < 2:
        return f"<rect {re.sub(r'url\(#[^)]+\)', stops[0], attrs)}/>"
    steps, band_h = 28, h / 28.0
    bands = []
    for i in range(steps):
        pos = (i / (steps - 1)) * (len(stops) - 1)
        idx = min(len(stops) - 2, int(pos))
        col = _lerp_hex(stops[idx], stops[idx + 1], pos - idx)
        bands.append(f'<rect x="{x:.1f}" y="{y + i * band_h:.1f}" width="{w:.1f}" height="{band_h + 1.2:.1f}" fill="{col}"/>')
    return "".join(bands)


def flatten_svg_for_raster(svg_text: str) -> str:
    """Replace url(#gradient) fills with smooth bands or stop colors so PyMuPDF never renders black."""
    grads = _parse_svg_gradients(svg_text)
    out = re.sub(r'\s+filter=["\']url\(#[^"\']+\)["\']', "", svg_text)

    def _rect_sub(m: re.Match[str]) -> str:
        attrs = m.group(1)
        mg = re.search(r'fill=["\']url\(#([^)]+)\)["\']', attrs)
        if not mg or mg.group(1) not in grads:
            return m.group(0)
        kind, stops = grads[mg.group(1)]
        return _expand_linear_rect(attrs, stops) if kind == "lineargradient" else f"<rect {re.sub(r'url\(#[^)]+\)', stops[0], attrs)}/>"

    out = re.sub(r"<rect\b([^/>]*?)/>", _rect_sub, out)
    return re.sub(r"url\(#([^)]+)\)", lambda m: grads[m.group(1)][1][0] if m.group(1) in grads else "#38bdf8", out)


def rasterize_svg_to_png(svg_text: str, out_png: Path, fallback_bg: str = "#0f172a", fallback_title: str = "") -> None:
    """Render any SVG cleanly to a crisp high-res PNG using gradient-safe flattening."""
    try:
        doc = fitz.open(stream=flatten_svg_for_raster(svg_text).encode("utf-8"), filetype="svg")
        doc[0].get_pixmap(dpi=150).save(str(out_png))
        doc.close()
    except (OSError, RuntimeError, ValueError, TypeError, IndexError) as exc:
        _LOG.debug("SVG raster fallback triggered: %s", exc)
        im = Image.new("RGB", (1200, 760), hex_to_rgb(fallback_bg))
        if fallback_title:
            ImageDraw.Draw(im).text((600, 380), fallback_title[:36], fill=(248, 250, 252), font=_load_font(54, bold=True), anchor="mm")
        im.save(out_png, format="PNG")


def _star_elements(seed: int, count: int, max_y: int, color: str) -> str:
    return "".join(
        f'<circle cx="{((i * 197 + seed * 83 + 41) % 1160) + 20}" cy="{((i * 113 + seed * 59 + 19) % max(40, max_y - 20)) + 16}" '
        f'r="{1.1 + ((i + seed) % 3) * 0.75:.1f}" fill="{color}" opacity="{0.45 + ((i * 7) % 5) * 0.11:.2f}"/>'
        for i in range(count)
    )


def _scene_cityscape_layers(pal: dict[str, str], seed: int, is_istanbul: bool) -> list[str]:
    far = (
        "0,470 0,380 90,380 90,340 165,340 165,390 250,390 250,315 320,315 320,375 420,375 420,330 "
        "510,330 510,365 620,365 620,295 700,295 700,360 820,360 820,320 940,320 940,370 1070,370 1070,335 1200,335 1200,470"
    )
    layers = [
        '<rect x="0" y="0" width="1200" height="510" fill="url(#gSky)"/>',
        _star_elements(seed, 55, 290, "#f8fafc"),
        f'<circle cx="910" cy="185" r="115" fill="{pal["accent"]}" opacity="0.14"/><circle cx="910" cy="185" r="56" fill="{pal["accent"]}" opacity="0.88"/>',
        f'<polygon points="{far}" fill="{pal["bg3"]}" opacity="0.88"/>',
    ]
    if is_istanbul:
        layers.extend([
            f'<path d="M510,485 Q600,355 690,485 Z" fill="{pal["bg1"]}"/>',
            f'<rect x="468" y="330" width="11" height="155" fill="{pal["bg1"]}"/><polygon points="468,330 473.5,296 479,330" fill="{pal["bg1"]}"/>',
            f'<rect x="720" y="330" width="11" height="155" fill="{pal["bg1"]}"/><polygon points="720,330 725.5,296 731,330" fill="{pal["bg1"]}"/>',
            f'<rect x="200" y="345" width="14" height="145" fill="{pal["primary"]}"/><rect x="975" y="345" width="14" height="145" fill="{pal["primary"]}"/>',
            f'<path d="M60,445 Q207,365 595,432 Q982,365 1140,445" fill="none" stroke="{pal["accent"]}" stroke-width="3.5"/>',
            f'<line x1="40" y1="448" x2="1160" y2="448" stroke="{pal["primary"]}" stroke-width="5"/>',
        ])
    else:
        for i in range(11):
            bx, bh, bw = 30 + i * 106, 135 + ((i * 53 + seed * 29) % 155), 72 + (i % 3) * 14
            by = 485 - bh
            layers.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="4" fill="{pal["bg1"]}"/>')
            layers.extend(
                f'<rect x="{wx}" y="{wy}" width="7" height="10" fill="{pal["accent"]}" opacity="0.72"/>'
                for wy in range(by + 16, 468, 22) for wx in range(bx + 12, bx + bw - 14, 18) if (wx + wy + seed) % 3 != 0
            )
    layers.append('<rect x="0" y="485" width="1200" height="275" fill="url(#gWater)"/>')
    layers.extend(
        f'<rect x="{910 - (260 - i * 12) // 2 + ((i % 3) - 1) * 18}" y="{505 + i * 17}" width="{max(40, 260 - i * 12)}" height="4" rx="2" fill="{pal["accent"]}" opacity="{0.52 - i * 0.03:.2f}"/>'
        for i in range(14)
    )
    layers.append(f'<path d="M0,715 L1200,690 L1200,760 L0,760 Z" fill="{pal["bg1"]}" opacity="0.92"/>')
    return layers


def _scene_nature_layers(pal: dict[str, str], seed: int) -> list[str]:
    sx = 600 + ((seed % 3) - 1) * 160
    layers = [
        '<rect x="0" y="0" width="1200" height="490" fill="url(#gSky)"/>',
        _star_elements(seed, 28, 210, "#fffbeb"),
        f'<circle cx="{sx}" cy="315" r="145" fill="{pal["accent"]}" opacity="0.16"/><circle cx="{sx}" cy="315" r="95" fill="{pal["primary"]}" opacity="0.34"/><circle cx="{sx}" cy="315" r="58" fill="{pal["accent"]}" opacity="0.95"/>',
        f'<ellipse cx="260" cy="145" rx="130" ry="26" fill="{pal["text"]}" opacity="0.14"/><ellipse cx="890" cy="120" rx="150" ry="24" fill="{pal["text"]}" opacity="0.12"/>',
        f'<polygon points="0,475 180,260 390,410 610,230 850,395 1040,275 1200,385 1200,490 0,490" fill="{pal["bg3"]}" opacity="0.82"/>',
        f'<polygon points="0,490 120,355 310,440 520,315 740,445 960,335 1200,440 1200,490" fill="{pal["bg2"]}" opacity="0.95"/>',
        '<rect x="0" y="485" width="1200" height="275" fill="url(#gWater)"/>',
    ]
    layers.extend(
        f'<rect x="{sx - (230 - i * 11) // 2}" y="{502 + i * 16}" width="{max(36, 230 - i * 11)}" height="4.5" rx="2" fill="{pal["accent"]}" opacity="{0.65 - i * 0.035:.2f}"/>'
        for i in range(15)
    )
    layers.extend(f'<polygon points="{tx},{625 - (tx % 45)} {tx - 34},720 {tx + 34},720" fill="{pal["bg1"]}"/>' for tx in (55, 110, 165, 1025, 1085, 1140))
    layers.append(f'<path d="M0,695 Q320,665 600,705 T1200,685 L1200,760 L0,760 Z" fill="{pal["bg1"]}"/>')
    return layers


def _scene_space_layers(pal: dict[str, str], seed: int) -> list[str]:
    return [
        '<rect x="0" y="0" width="1200" height="760" fill="url(#gSky)"/>',
        f'<circle cx="340" cy="280" r="240" fill="{pal["primary"]}" opacity="0.15"/><circle cx="840" cy="440" r="270" fill="{pal["secondary"]}" opacity="0.16"/>',
        _star_elements(seed, 110, 730, "#f8fafc"),
        f'<ellipse cx="640" cy="370" rx="285" ry="62" transform="rotate(-18 640 370)" fill="none" stroke="{pal["accent"]}" stroke-width="14" opacity="0.45"/>',
        f'<circle cx="640" cy="370" r="142" fill="{pal["primary"]}"/>',
        f'<path d="M565,248 A142,142 0 1,0 742,468 A118,132 0 1,1 565,248 Z" fill="{pal["bg1"]}" opacity="0.58"/>',
        f'<ellipse cx="640" cy="370" rx="285" ry="62" transform="rotate(-18 640 370)" fill="none" stroke="{pal["text"]}" stroke-width="4" opacity="0.72"/>',
        f'<circle cx="290" cy="210" r="34" fill="{pal["accent"]}" opacity="0.9"/><circle cx="965" cy="225" r="18" fill="{pal["secondary"]}" opacity="0.88"/>',
        f'<path d="M0,665 Q420,595 820,655 T1200,625 L1200,760 L0,760 Z" fill="{pal["bg1"]}"/>',
    ]


def _scene_abstract_layers(pal: dict[str, str], seed: int) -> list[str]:
    layers = [
        '<rect x="0" y="0" width="1200" height="760" fill="url(#gSky)"/>',
        f'<circle cx="600" cy="360" r="260" fill="{pal["primary"]}" opacity="0.16"/><circle cx="600" cy="360" r="148" fill="{pal["secondary"]}" opacity="0.24"/>',
    ]
    for i in range(6):
        y0, c1 = 190 + i * 78, 220 + ((i + seed) % 3) * 140
        col = pal["primary"] if i % 2 == 0 else pal["accent"]
        layers.append(f'<path d="M-40,{y0} C320,{y0 - 110} {c1 + 360},{y0 + 115} 1240,{y0 - 30}" fill="none" stroke="{col}" stroke-width="{10 - i}" opacity="{0.65 - i * 0.08:.2f}"/>')
    for i in range(5):
        ang = (i * 72 + seed * 24) * math.pi / 180.0
        cx, cy = round(600 + math.cos(ang) * 210), round(360 + math.sin(ang) * 135)
        layers.append(f'<polygon points="{cx},{cy - 54} {cx + 52},{cy + 36} {cx - 52},{cy + 36}" fill="{pal["accent"]}" opacity="0.22" stroke="{pal["primary"]}" stroke-width="2"/>')
    layers.append(_star_elements(seed + 7, 40, 720, pal["text"]))
    return layers


def render_procedural_scene_svg(subtype: str, prompt: str, pal: dict[str, str], seed: int) -> str:
    """Build a rich multi-layered 1200x760 procedural SVG scene as a frontier visual fallback."""
    low = prompt.lower()
    if subtype == "cityscape":
        body, sky_mid, water_top = _scene_cityscape_layers(pal, seed, ("istanbul" in low or "boğaz" in low or "bogaz" in low)), pal["secondary"], pal["bg2"]
    elif subtype == "nature_landscape":
        body, sky_mid, water_top = _scene_nature_layers(pal, seed), pal["primary"], pal["bg3"]
    elif subtype == "space_cosmos":
        body, sky_mid, water_top = _scene_space_layers(pal, seed), pal["bg2"], pal["bg1"]
    else:
        body, sky_mid, water_top = _scene_abstract_layers(pal, seed), pal["bg2"], pal["bg3"]
    return "\n".join([
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 760" width="1200" height="760"><defs>',
        f'<linearGradient id="gSky" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{pal["bg1"]}"/><stop offset="60%" stop-color="{pal["bg2"]}"/><stop offset="100%" stop-color="{sky_mid}"/></linearGradient>',
        f'<linearGradient id="gWater" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{water_top}"/><stop offset="100%" stop-color="{pal["bg1"]}"/></linearGradient>',
        "</defs>", *body, "</svg>",
    ])
