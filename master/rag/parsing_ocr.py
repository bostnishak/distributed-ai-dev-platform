"""RAG-03 & DOS-08: Tesseract OCR and Handwriting OCR preprocessing helpers."""

from __future__ import annotations

import importlib
import importlib.util
import io
import subprocess
from typing import Any


def _collect_tesseract_words(data: dict[str, Any]) -> tuple[str, float]:
    words: list[str] = []
    confs: list[float] = []
    for txt, conf in zip(data.get("text", []), data.get("conf", []), strict=False):
        cleaned = str(txt or "").strip()
        if not cleaned:
            continue
        words.append(cleaned)
        try:
            c = float(conf)
            if c >= 0:
                confs.append(c / 100.0)
        except ValueError:
            continue
    avg_conf = round(sum(confs) / len(confs), 3) if confs else 0.0
    return " ".join(words), avg_conf


def run_ocr_on_image_bytes(image_bytes: bytes) -> tuple[str, float, list[str]]:
    """RAG-03: Run Tesseract OCR (tur+eng) if installed; return clear DEF-15 message if unavailable."""
    try:
        pytesseract = importlib.import_module("pytesseract")
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        data = pytesseract.image_to_data(img, lang="tur+eng", output_type=pytesseract.Output.DICT)
        text, avg_conf = _collect_tesseract_words(data)
        warnings = ["Düşük OCR güveni: taranmış sayfa bulanık olabilir."] if avg_conf < 0.75 else []
        return text, avg_conf, warnings
    except (
        ImportError, OSError, RuntimeError, ValueError, TypeError, AttributeError, LookupError, subprocess.SubprocessError
    ) as exc:
        return (
            "",
            0.0,
            [f"OCR motoru (Tesseract) kurulu değil veya çalıştırılamadı; taranmış sayfa okunamadı ({type(exc).__name__})."],
        )


def _preprocess_handwriting(image_bytes: bytes) -> tuple[Any, Any, dict[str, Any]]:
    from PIL import Image, ImageFilter, ImageOps

    if not image_bytes:
        raise ValueError("Görsel içeriği boş.")
    enhanced = ImageOps.autocontrast(ImageOps.grayscale(Image.open(io.BytesIO(image_bytes))), cutoff=2).filter(
        ImageFilter.SHARPEN
    )
    w, h = enhanced.size
    total_px = max(1, w * h)
    mean_luma = sum(i * c for i, c in enumerate(enhanced.histogram()[:256])) / total_px
    thresh = max(60, min(200, int(mean_luma * 0.85)))
    binary = enhanced.point(lambda p: 255 if p > thresh else 0)
    raw_bin = binary.tobytes()
    ink_ratio = round(sum(1 for px in raw_bin if px == 0) / total_px, 4)

    min_row_ink = max(2, int(w * 0.015))
    line_bands = 0
    in_band = False
    for y in range(h):
        has_ink = sum(1 for x in range(w) if raw_bin[y * w + x] == 0) > min_row_ink
        if has_ink and not in_band:
            line_bands += 1
        in_band = has_ink

    meta: dict[str, Any] = {
        "width": w,
        "height": h,
        "threshold": thresh,
        "ink_ratio": ink_ratio,
        "estimated_lines": line_bands,
    }
    return enhanced, binary, meta


def _try_local_trocr(enhanced: Any, language: str, meta: dict[str, Any]) -> dict[str, Any] | None:
    try:
        if not (importlib.util.find_spec("transformers") and importlib.util.find_spec("torch")):
            return None
        transformers = importlib.import_module("transformers")
        proc = transformers.TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten", local_files_only=True)
        mdl = transformers.VisionEncoderDecoderModel.from_pretrained(
            "microsoft/trocr-base-handwritten", local_files_only=True
        )
        pixel_values = proc(images=enhanced.convert("RGB"), return_tensors="pt").pixel_values
        text = str(proc.batch_decode(mdl.generate(pixel_values), skip_special_tokens=True)[0] or "").strip()
        return {
            "engine": "trocr-local",
            "text": text,
            "confidence": 0.88 if text else 0.0,
            "language": language,
            "preprocessed": meta,
            "warnings": [] if text else ["TrOCR çıktı üretmedi."],
        }
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        meta["trocr_fallback_reason"] = type(exc).__name__
        return None


def recognize_handwriting_image_bytes(image_bytes: bytes, *, language: str = "tur+eng") -> dict[str, Any]:
    """DOS-08: Preprocess handwritten note images and run local TrOCR or Tesseract handwriting OCR."""
    enhanced, binary, meta = _preprocess_handwriting(image_bytes)
    trocr_res = _try_local_trocr(enhanced, language, meta)
    if trocr_res is not None:
        return trocr_res

    try:
        pytesseract = importlib.import_module("pytesseract")
        data = pytesseract.image_to_data(
            binary, lang=language, config="--oem 1 --psm 6", output_type=pytesseract.Output.DICT
        )
        text, avg_conf = _collect_tesseract_words(data)
        warnings = ["El yazısı güven skoru düşük; daha yüksek kontrastlı çekim önerilir."] if avg_conf < 0.7 else []
        return {
            "engine": "tesseract-handwriting",
            "text": text,
            "confidence": avg_conf,
            "language": language,
            "preprocessed": meta,
            "warnings": warnings,
        }
    except (
        ImportError, OSError, RuntimeError, ValueError, TypeError, AttributeError, LookupError, subprocess.SubprocessError
    ) as exc:
        return {
            "engine": "preprocessed-offline",
            "text": "",
            "confidence": 0.0,
            "language": language,
            "preprocessed": meta,
            "warnings": [
                f"Görsel el yazısı için ön işlendi ({meta['estimated_lines']} satır bandı, "
                f"mürekkep oranı {meta['ink_ratio']}), ancak yerel Tesseract/TrOCR motoru bulunamadı ({type(exc).__name__})."
            ],
        }
