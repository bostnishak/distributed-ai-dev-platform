"""Split pre-computed notes (image/file audit output) from the user prompt."""

from __future__ import annotations


def split_pre_notes(full_prompt: str) -> tuple[str, str]:
    pre_note = ""
    for marker in ("### İşlenmiş Görsel Çıktısı", "### Deterministik Dosya Denetim Raporu"):
        if marker in full_prompt:
            idx_n = full_prompt.index(marker)
            pre_note += full_prompt[idx_n:] + "\n\n---\n\n"
            full_prompt = full_prompt[:idx_n].strip()
    return full_prompt, pre_note
