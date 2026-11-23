"""Cluster B (`[M18]`, Faz 5 & Faz 18.3): Voice Engine, Meeting Transcript Analyzer, and Offline Formant WAV TTS Synthesizer.

Provides:
- `transcribe_audio_bytes`: re-exported from `multimodal_studio`
- `analyze_meeting_transcript(transcript_text: str) -> dict`: splits transcript into timestamped segments (`[00:00:00]`), extracts `decisions`, `action_items` (`owner`, `task`, `due`), and `executive_summary`
- `synthesize_speech_wav(text: str, sample_rate: int = 16000) -> bytes`: pure-Python deterministic formant/prosody speech-like WAV audio synthesizer
"""

from __future__ import annotations

import io
import math
import re
import wave
from typing import Any

import numpy as np

from multimodal_studio import transcribe_audio_bytes

__all__ = [
    "analyze_meeting_transcript",
    "synthesize_speech_wav",
    "transcribe_audio_bytes",
]

_TIMESTAMP_LINE_RE = re.compile(
    r"^\s*(?:\[(\d{1,2}:\d{2}(?::\d{2})?)\]|(\d{1,2}:\d{2}(?::\d{2})?))\s*(?:[-:]\s*)?(.*)$"
)
_SPEAKER_RE = re.compile(r"^\s*([A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü0-9_.\s]{1,28}?)\s*:\s*(.+)$")
_DECISION_KEYWORDS = (
    "karar",
    "onaylandı",
    "onaylandi",
    "kabul edildi",
    "belirlendi",
    "mutabık",
    "mutabik",
    "decided",
    "approved",
    "agreed",
    "kesinleşti",
    "kesinlesti",
)
_ACTION_KEYWORDS = (
    "yapacak",
    "hazırlayacak",
    "hazirlayacak",
    "tamamlayacak",
    "gönderecek",
    "gonderecek",
    "teslim",
    "aksiyon",
    "görev",
    "gorev",
    "action",
    "todo",
    "will ",
    "üstlenecek",
    "ustlenecek",
    "sorumlu",
)
_DUE_RE = re.compile(
    r"\b(\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?|"
    r"pazartesi|salı|sali|çarşamba|carsamba|perşembe|persembe|cuma|cumartesi|pazar|"
    r"yarın|yarin|bugün|bugun|haftaya|ay sonu|cuma günü|cuma gunu|"
    r"q[1-4]|monday|tuesday|wednesday|thursday|friday|tomorrow|next week)\b",
    re.IGNORECASE,
)


def _normalize_timestamp(raw_ts: str | None, index: int) -> str:
    if raw_ts:
        parts = [int(p) for p in raw_ts.strip().split(":")]
        if len(parts) == 2:
            return f"[{0:02d}:{parts[0]:02d}:{parts[1]:02d}]"
        if len(parts) == 3:
            return f"[{parts[0]:02d}:{parts[1]:02d}:{parts[2]:02d}]"
    total_sec = index * 30
    hh = total_sec // 3600
    mm = (total_sec % 3600) // 60
    ss = total_sec % 60
    return f"[{hh:02d}:{mm:02d}:{ss:02d}]"


def analyze_meeting_transcript(transcript_text: str) -> dict[str, Any]:
    """Split meeting transcript into timestamped segments and extract decisions, action items, and executive summary."""
    cleaned = (transcript_text or "").strip()
    if not cleaned:
        return {
            "segments": [],
            "decisions": [],
            "action_items": [],
            "executive_summary": "Toplantı kaydı boş veya metin içermiyor.",
        }

    raw_lines = [ln.strip() for ln in re.split(r"[\r\n]+", cleaned) if ln.strip()]
    if len(raw_lines) == 1 and len(cleaned) > 120:
        raw_lines = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]

    segments: list[dict[str, str]] = []
    decisions: list[str] = []
    action_items: list[dict[str, str]] = []

    for idx, line in enumerate(raw_lines):
        ts_match = _TIMESTAMP_LINE_RE.match(line)
        raw_ts = (ts_match.group(1) or ts_match.group(2)) if ts_match else None
        body = ts_match.group(3).strip() if ts_match else line
        timestamp = _normalize_timestamp(raw_ts, idx)

        speaker = "Katılımcı"
        text_content = body
        sp_match = _SPEAKER_RE.match(body)
        if sp_match:
            speaker = sp_match.group(1).strip()
            text_content = sp_match.group(2).strip()

        segments.append(
            {
                "timestamp": timestamp,
                "speaker": speaker,
                "text": text_content,
                "formatted": f"{timestamp} {speaker}: {text_content}",
            }
        )

        lower_body = text_content.lower()
        if any(k in lower_body for k in _DECISION_KEYWORDS):
            decisions.append(text_content)

        if any(k in lower_body for k in _ACTION_KEYWORDS):
            due_match = _DUE_RE.search(text_content)
            due_str = due_match.group(1) if due_match else "Belirtilmedi"
            owner = speaker
            if owner == "Katılımcı":
                name_match = re.match(r"^([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)?)\b", text_content)
                if name_match:
                    owner = name_match.group(1)
            action_items.append(
                {
                    "owner": owner,
                    "task": text_content,
                    "due": due_str,
                    "timestamp": timestamp,
                }
            )

    if not decisions and segments:
        decisions.append(segments[0]["text"])

    speakers = sorted({s["speaker"] for s in segments if s["speaker"]})
    summary_parts = [
        f"Toplantı {len(segments)} zaman damgalı segment ve {len(speakers)} konuşmacı ({', '.join(speakers[:5])}) içeriyor.",
        f"Toplam {len(decisions)} kritik karar ve {len(action_items)} aksiyon maddesi tespit edildi.",
    ]
    if decisions:
        summary_parts.append(f"Ana Karar: {decisions[0][:180]}")
    if action_items:
        first_act = action_items[0]
        summary_parts.append(f"Öncelikli Aksiyon: {first_act['owner']} -> {first_act['task'][:140]} (Termin: {first_act['due']}).")

    return {
        "segments": segments,
        "decisions": decisions,
        "action_items": action_items,
        "executive_summary": " ".join(summary_parts),
    }


# Formant table (F1, F2, F3 in Hz) for vowel-like timbre variation across syllables
_VOWEL_FORMANTS: dict[str, tuple[float, float, float]] = {
    "a": (730.0, 1090.0, 2440.0),
    "e": (530.0, 1840.0, 2480.0),
    "i": (270.0, 2290.0, 3010.0),
    "ı": (320.0, 1450.0, 2400.0),
    "o": (570.0, 840.0, 2410.0),
    "ö": (500.0, 1500.0, 2350.0),
    "u": (300.0, 870.0, 2240.0),
    "ü": (280.0, 1750.0, 2200.0),
}


def synthesize_speech_wav(text: str, sample_rate: int = 16000) -> bytes:
    """Pure-Python deterministic formant/prosody speech-like WAV audio synthesizer.

    Generates a valid 16-bit mono PCM `.wav` buffer whose duration scales with word count and
    syllable cadence so `/api/assistant/tts` always returns a playable `.wav` offline.
    """
    sr = max(8000, min(int(sample_rate or 16000), 48000))
    cleaned = (text or "").strip()
    words = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]+", cleaned)
    if not words:
        words = ["merhaba"]

    chunks: list[np.ndarray] = []
    pause_samples = int(sr * 0.045)
    pause_wave = np.zeros(pause_samples, dtype=np.float64)

    total_words = len(words[:120])
    for w_idx, word in enumerate(words[:120]):
        vowels = [ch.lower() for ch in word if ch.lower() in _VOWEL_FORMANTS]
        if not vowels:
            vowels = ["a"]

        # Prosody pitch declination across sentence (135 Hz -> 108 Hz)
        progress = w_idx / float(max(1, total_words - 1))
        base_f0 = 135.0 - 25.0 * progress

        for s_idx, v_char in enumerate(vowels[:6]):
            f1, f2, f3 = _VOWEL_FORMANTS.get(v_char, (600.0, 1400.0, 2400.0))
            syl_dur = 0.085 + min(0.045, len(word) * 0.006)
            n_samples = max(128, int(sr * syl_dur))
            t = np.linspace(0.0, syl_dur, n_samples, endpoint=False)

            # Slight vibrato & pitch contour per syllable
            f0 = base_f0 + 6.0 * ((s_idx % 2) * 2 - 1)
            phase0 = 2.0 * math.pi * f0 * t + 0.15 * np.sin(2.0 * math.pi * 5.5 * t)

            # Glottal harmonic source + formant resonances
            glottal = 0.45 * np.sin(phase0) + 0.25 * np.sin(2.0 * phase0) + 0.12 * np.sin(3.0 * phase0)
            formant_sig = (
                0.50 * np.sin(2.0 * math.pi * f1 * t)
                + 0.30 * np.sin(2.0 * math.pi * f2 * t)
                + 0.12 * np.sin(2.0 * math.pi * f3 * t)
            )
            raw_syl = 0.55 * glottal + 0.45 * formant_sig

            # Smooth raised-cosine attack/decay envelope per syllable
            attack = max(16, int(0.18 * n_samples))
            release = max(16, int(0.24 * n_samples))
            env = np.ones(n_samples, dtype=np.float64)
            env[:attack] = np.linspace(0.0, 1.0, attack)
            env[-release:] = np.linspace(1.0, 0.0, release)

            chunks.append(raw_syl * env)

        chunks.append(pause_wave)

    full_signal = np.concatenate(chunks) if chunks else np.zeros(int(sr * 0.25), dtype=np.float64)
    peak = float(np.max(np.abs(full_signal))) or 1.0
    pcm16 = np.clip((full_signal / peak) * 26000.0, -32767, 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm16.tobytes())
    return buf.getvalue()
