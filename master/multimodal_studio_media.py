"""Multimodal Media Engine: Image CV Processing/Editing & Local Voice-to-Text (STT)."""

from __future__ import annotations

import io
import logging
import re
import shutil
import sys
import tempfile
import uuid
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

import config
import process_utils

IMAGE_EDIT_KEYWORDS = (
    "siyah beyaz", "gri ton", "grayscale", "kontrast", "netleştir", "netlestir", "keskinleştir",
    "bulanık", "bulanik", "blur", "kenar", "eskiz", "sketch", "edge", "ters çevir", "negatif",
    "invert", "döndür", "dondur", "rotate", "çevir", "ayna", "flip", "boyutlandır", "boyutlandir",
    "resize", "küçült", "बüyüt", "kırp", "kirp", "crop", "parlaklık", "parlaklik", "sepya",
    "sepia", "arka plan", "arkaplan", "filigran", "yazı ekle", "yazi ekle", "watermark",
    "düzenle", "duzenle", "efekt", "işle", "isle", "görüntü işle", "goruntu isle",
)

_WHISPER_CACHE: dict[str, Any] = {"model": None}


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


def is_image_edit_request(prompt: str) -> bool:
    lower = prompt.lower()
    return any(k in lower for k in IMAGE_EDIT_KEYWORDS)


def _apply_geometry_ops(img: Image.Image, prompt: str, lower: str, applied: list[str]) -> Image.Image:
    if "döndür" in lower or "dondur" in lower or "rotate" in lower:
        if "180" in lower:
            img = img.rotate(180, expand=True)
            applied.append("180 Derece Döndürme")
        else:
            img = img.rotate(-90, expand=True)
            applied.append("90 Derece Döndürme" if "90" in lower else "90 Derece Saat Yönünde Döndürme")

    if "ayna" in lower or "yatay çevir" in lower or "flip" in lower:
        img = ImageOps.mirror(img)
        applied.append("Yatay Aynalama (Mirror)")

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
    return img


def _apply_background_and_color_ops(img: Image.Image, lower: str, applied: list[str]) -> Image.Image:
    if "arka plan" in lower or "arkaplan" in lower or "background" in lower:
        arr = np.array(img, dtype=np.float32)
        corners = np.vstack([arr[0, 0], arr[0, -1], arr[-1, 0], arr[-1, -1]])
        bg_color = np.mean(corners, axis=0)
        mask = np.linalg.norm(arr - bg_color, axis=2) < 42.0
        arr[mask] = [255.0, 255.0, 255.0]
        img = Image.fromarray(arr.astype(np.uint8), mode="RGB")
        applied.append("Arka Plan Temizleme (Köşe Renk Uzaklığı Segmentasyonu)")

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
    return img


def _apply_detail_and_tone_filters(img: Image.Image, lower: str, applied: list[str]) -> Image.Image:
    if "kenar" in lower or "eskiz" in lower or "sketch" in lower or "edge" in lower:
        edges = ImageOps.grayscale(img).filter(ImageFilter.FIND_EDGES)
        edges = ImageEnhance.Contrast(ImageOps.invert(edges)).enhance(2.2)
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
    return img


def _apply_watermark_or_default(img: Image.Image, prompt: str, lower: str, applied: list[str]) -> Image.Image:
    m_txt = re.search(r'["“”\']([^"“”\']{2,50})["“”\']', prompt)
    if ("yazı" in lower or "yazi" in lower or "filigran" in lower or "watermark" in lower) and m_txt:
        wm_text = m_txt.group(1)
        draw = ImageDraw.Draw(img)
        font = _load_font(max(18, img.width // 24), bold=True)
        bbox = draw.textbbox((0, 0), wm_text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        px, py = img.width - tw - 24, img.height - th - 24
        draw.rectangle([px - 10, py - 6, px + tw + 10, py + th + 8], fill=(15, 23, 42))
        draw.text((px, py), wm_text, fill=(248, 250, 252), font=font)
        applied.append(f'Metin / Filigran Ekleme ("{wm_text}")')

    if not applied:
        img = ImageOps.autocontrast(img, cutoff=1)
        img = ImageEnhance.Contrast(img).enhance(1.2)
        img = img.filter(ImageFilter.UnsharpMask(radius=1.6, percent=140, threshold=3))
        applied.append("Otomatik Kontrast Dengeleme ve Netleştirme (HDR İyileştirme)")
    return img


def process_and_edit_image(raw_bytes: bytes, prompt: str) -> dict[str, Any]:
    """Apply computer-vision filters, geometric transforms, background removal, or watermarks."""
    orig = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    img = orig.copy()
    lower = prompt.lower()
    applied: list[str] = []

    img = _apply_geometry_ops(img, prompt, lower, applied)
    img = _apply_background_and_color_ops(img, lower, applied)
    img = _apply_detail_and_tone_filters(img, lower, applied)
    img = _apply_watermark_or_default(img, prompt, lower, applied)

    file_id = f"img-edit-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    out_png = media_dir() / f"{file_id}.png"
    img.save(out_png, format="PNG")

    arr_out = np.array(img)
    return {
        "original_size": f"{orig.width}x{orig.height} px",
        "output_size": f"{img.width}x{img.height} px",
        "mean_brightness": round(float(np.mean(arr_out)), 1),
        "std_contrast": round(float(np.std(arr_out)), 1),
        "applied_filters": applied,
        "file_id": file_id,
        "url": f"/api/assistant/media/{file_id}.png",
    }


def _get_whisper_model() -> Any:
    if _WHISPER_CACHE["model"] is None:
        from faster_whisper import WhisperModel  # type: ignore[import-not-found]

        _WHISPER_CACHE["model"] = WhisperModel("base", device="cpu", compute_type="int8")
    return _WHISPER_CACHE["model"]


def _decode_wav_to_float32_16k(raw_bytes: bytes) -> tuple[np.ndarray | None, float]:
    try:
        with wave.open(io.BytesIO(raw_bytes), "rb") as wf:
            nch = wf.getnchannels() or 1
            sw = wf.getsampwidth()
            rate = wf.getframerate() or 16000
            frames = wf.readframes(wf.getnframes())
            duration = round(wf.getnframes() / float(rate), 2)
            if sw == 2:
                arr = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            elif sw == 4:
                arr = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
            else:
                arr = (np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
            if nch > 1:
                arr = arr.reshape(-1, nch).mean(axis=1)
            if rate != 16000 and len(arr) > 0:
                target_len = max(1, round(len(arr) * 16000.0 / rate))
                x_old = np.linspace(0.0, 1.0, len(arr), dtype=np.float32)
                x_new = np.linspace(0.0, 1.0, target_len, dtype=np.float32)
                arr = np.interp(x_new, x_old, arr).astype(np.float32)
            return arr, duration
    except (wave.Error, OSError, ValueError, TypeError, ZeroDivisionError) as exc:
        logging.getLogger(__name__).debug("Recoverable error suppressed: %s", exc)
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
                resampled.to_ndarray().reshape(-1).astype(np.float32)
                for frame in container.decode(stream)
                if isinstance(frame, av.AudioFrame)
                for resampled in resampler.resample(frame)
            ]
            if not chunks:
                return None, 0.0
            arr = np.concatenate(chunks)
            return arr, round(len(arr) / 16000.0, 2)
    except (ImportError, OSError, RuntimeError, ValueError, TypeError, AttributeError, KeyError):
        return None, 0.0


def _decode_audio_to_float32_16k(raw_bytes: bytes, tmp_path: Path, suffix: str) -> tuple[np.ndarray | None, float]:
    """Decode WAV (stdlib wave) or WebM/MP3/OGG/M4A (PyAV without metadata_errors) to 16kHz mono float32."""
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
        "Add-Type -AssemblyName System.Speech; "
        "$rec = New-Object System.Speech.Recognition.SpeechRecognitionEngine; "
        "$rec.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar)); "
        f"$rec.SetInputToWaveFile('{tmp_path}'); "
        "$res = $rec.Recognize(); "
        "if ($res) { Write-Output $res.Text }"
    )
    try:
        proc = process_utils.run_process([ps_bin, "-NoProfile", "-Command", ps_script], timeout_s=15.0)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except (OSError, ValueError) as exc:
        logging.getLogger(__name__).debug("Recoverable error suppressed: %s", exc)
    return ""


def transcribe_audio_bytes(filename: str, raw_bytes: bytes) -> dict[str, Any]:
    """Transcribe an uploaded or microphone-recorded voice message (.wav, .mp3, .m4a, .ogg, .webm) to Turkish text."""
    suffix = Path(filename).suffix.lower() or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = Path(tmp.name)

    audio_np, duration_sec = _decode_audio_to_float32_16k(raw_bytes, tmp_path, suffix)
    transcript = ""
    engine = "audio-metadata"

    if audio_np is not None and len(audio_np) > 0:
        try:
            wmodel = _get_whisper_model()
            segments, _ = wmodel.transcribe(audio_np, language="tr", vad_filter=False)
            transcript = " ".join(seg.text.strip() for seg in segments).strip()
            engine = "faster-whisper-base (local)"
        except (ImportError, OSError, RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logging.getLogger(__name__).debug("Recoverable error suppressed: %s", exc)

    if not transcript and sys.platform == "win32" and suffix == ".wav":
        sapi_text = _transcribe_windows_sapi(tmp_path)
        if sapi_text:
            transcript = sapi_text
            engine = "windows-system-speech"

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
