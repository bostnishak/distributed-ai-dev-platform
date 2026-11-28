"""Local OCR that keeps Turkish letters: RapidOCR with PaddlePaddle's Latin recognition model, on the CPU.

The bundled default model of RapidOCR drops ğ, ş, ı and İ, so without the Latin model in the vault no text is claimed.
Model files: `python scripts/vendor_fetch.py` (pinned revision and SHA-256).
"""

from __future__ import annotations

import functools
import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import config

_PARTS = ("vendor", "models", "ocr-latin")


class OcrUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Line:
    text: str
    box: tuple[float, float, float, float]  # x0, y0, x1, y1 in pixels of the image read
    score: float


def model_folder() -> Path:
    own = config.data_dir().joinpath(*_PARTS)
    return own if own.is_dir() else Path(__file__).resolve().parent.joinpath("data", *_PARTS)


def available() -> bool:
    return importlib.util.find_spec("rapidocr_onnxruntime") is not None and (model_folder() / "inference.onnx").is_file()


def _keys() -> Path:
    """The character list of the model, written once from its own configuration file."""
    target = config.data_dir() / "ocr_latin_keys.txt"
    if not target.is_file():
        import yaml

        described = yaml.safe_load((model_folder() / "inference.yml").read_text(encoding="utf-8"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(str(c) for c in described["PostProcess"]["character_dict"]), encoding="utf-8")
    return target


@functools.lru_cache(maxsize=1)
def _engine() -> Any:
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR(rec_model_path=str(model_folder() / "inference.onnx"), rec_keys_path=str(_keys()))


def read(image: bytes) -> list[Line]:
    """The text lines of a PNG/JPEG image, top to bottom; OcrUnavailable when the model is not installed."""
    if not available():
        raise OcrUnavailable("OCR modeli kasada yok ya da rapidocr kurulu değil (scripts/vendor_fetch.py)")
    found, _timing = _engine()(image)
    lines = []
    for box, text, score in found or []:
        xs, ys = [p[0] for p in box], [p[1] for p in box]
        lines.append(Line(str(text), (round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)), round(float(score), 3)))
    return lines
