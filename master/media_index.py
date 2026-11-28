"""Recordings become searchable, time-stamped knowledge: speech by faster-whisper on the CPU, video by scene changes.

Transcription runs on the processor with INT8 weights, so it takes no video memory. For video, a frame is kept each
time the picture changes clearly, with its time.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

import multimodal_studio_media as media

AUDIO = (".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm", ".mp4", ".mkv", ".mov", ".avi")
VIDEO = (".mp4", ".mkv", ".mov", ".avi", ".webm")
_SCENE_CHANGE = 0.35  # share of the brightness histogram that moved
_MIN_GAP_S = 2.0
_MAX_FRAMES = 40
_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str


def clock(seconds: float) -> str:
    whole = int(seconds)
    return f"{whole // 3600:d}:{whole // 60 % 60:02d}:{whole % 60:02d}" if whole >= 3600 else f"{whole // 60:02d}:{whole % 60:02d}"


def transcribe(path: Path, language: str | None = None) -> list[Segment]:
    """Speech with its times; ValueError when the file has no readable sound."""
    samples, _duration = media._decode_audio_to_float32_16k(path.read_bytes(), path, path.suffix.lower())
    if samples is None or not len(samples):
        raise ValueError(f"{path.name}: okunabilir ses yok")
    segments, _info = media._get_whisper_model().transcribe(samples, language=language, vad_filter=False)
    return [Segment(round(s.start, 1), round(s.end, 1), s.text.strip()) for s in segments if s.text.strip()]


def _histogram(frame: Any) -> np.ndarray:
    small = frame.reformat(width=64, height=36, format="gray").to_ndarray()
    counts = np.histogram(small, bins=32, range=(0, 256))[0].astype(np.float32)
    return counts / counts.sum()


def keyframes(path: Path, folder: Path) -> list[tuple[float, str]]:
    """[(seconds, image file)] at every clear scene change, the first frame included; [] for a file without video."""
    import av

    kept: list[tuple[float, str]] = []
    previous: np.ndarray | None = None
    with av.open(str(path)) as container:
        stream = next((s for s in container.streams if s.type == "video"), None)
        if stream is None:
            return []
        folder.mkdir(parents=True, exist_ok=True)
        for frame in container.decode(stream):
            moment = float(frame.time or 0.0)
            if kept and moment - kept[-1][0] < _MIN_GAP_S:
                continue
            now = _histogram(frame)
            if previous is None or float(np.abs(now - previous).sum()) / 2 > _SCENE_CHANGE:
                name = f"{path.stem}-{len(kept) + 1:02d}.jpg"
                frame.to_image().save(folder / name, quality=80)
                kept.append((round(moment, 1), name))
                previous = now
            if len(kept) >= _MAX_FRAMES:
                break
    return kept
