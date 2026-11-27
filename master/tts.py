"""Read text aloud on this machine with a Piper voice: "sesli oku: ..." returns a playable WAV file.

The voice is a local ONNX file in data/voices (or PIPER_VOICE); nothing is sent anywhere. It is loaded on first
use and released again by the daemon manager when it has been idle.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
import wave
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi.responses import StreamingResponse

import chat_stream
import config
import daemons
import multimodal_studio as mms

_ASK_RE = re.compile(r"^\s*(?:(?:bunu|şunu|cevabı|yanıtı)\s+)?(?:sesli\s+oku|seslendir|read\s+(?:this\s+)?aloud)\s*(?::\s*(?P<text>.+))?\s*[.!]*\s*$", re.IGNORECASE | re.DOTALL)
_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
_LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_MARKS_RE = re.compile(r"[#*_`>|]+")
MAX_CHARS = 3000
_VOICE: dict[str, Any] = {}


def voice_file() -> Path | None:
    if configured := os.environ.get("PIPER_VOICE", ""):
        return Path(configured) if Path(configured).is_file() else None
    return next(iter(sorted((config.data_dir() / "voices").glob("*.onnx"))), None)


def speakable(text: str) -> str:
    """Markdown turned into plain sentences: code blocks are announced, links keep their label."""
    text = _LINK_RE.sub(r"\1", _CODE_RE.sub(" (kod bloğu) ", text))
    return re.sub(r"\s+", " ", _MARKS_RE.sub(" ", text)).strip()


def _unload() -> None:
    _VOICE.clear()


def _load() -> Any:
    from piper import PiperVoice

    path = voice_file()
    if path is None:
        raise ValueError("Ses dosyası yok: data/voices klasörüne bir Piper .onnx sesi ve .onnx.json dosyası koyun")
    if "voice" not in _VOICE:
        _VOICE["voice"] = PiperVoice.load(path)
    daemons.touch("ses okuma (Piper)", _unload)
    return _VOICE["voice"]


def synthesize(text: str, target: Path) -> float:
    """Write the spoken text to `target` and return its length in seconds."""
    spoken = speakable(text)[:MAX_CHARS]
    if not spoken:
        raise ValueError("okunacak metin yok")
    voice = _load()
    with wave.open(str(target), "wb") as out:
        voice.synthesize_wav(spoken, out)
    with wave.open(str(target), "rb") as done:
        return done.getnframes() / done.getframerate()


def last_answer(history: str) -> str:
    try:
        items = json.loads(history) if history else []
    except ValueError:
        return ""
    answers = [str(i.get("text", "")) for i in items if isinstance(i, dict) and i.get("role") == "assistant"] if isinstance(items, list) else []
    return answers[-1] if answers else ""


async def _speak(text: str) -> AsyncIterator[str]:
    name = f"ses-{uuid.uuid4().hex[:10]}.wav"
    seconds = await asyncio.to_thread(synthesize, text, mms.media_dir() / name)
    cut = f" Metin uzun olduğu için ilk {MAX_CHARS} karakteri okudum." if len(speakable(text)) > MAX_CHARS else ""
    yield f"[Sesli okuma ({seconds:.0f} sn)](/api/assistant/media/{name})\n\nBu bilgisayarda üretildi.{cut}"


def fastpath(prompt: str, history: str) -> StreamingResponse | None:
    match = _ASK_RE.match(prompt)
    if not match:
        return None
    text = (match["text"] or "").strip() or last_answer(history)
    if not text:
        return None
    return chat_stream.reply(_speak(text), "piper", "ses")
