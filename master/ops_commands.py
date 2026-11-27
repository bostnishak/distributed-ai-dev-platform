"""Chat commands about the platform itself: quality status and the training-data export."""

from __future__ import annotations

import re

import config
import release_guard
import training_pack

_QUALITY_RE = re.compile(r"^\s*(?:kalite\s+durumu|quality\s+status)\s*\??\s*$", re.IGNORECASE)
_EXPORT_RE = re.compile(r"^\s*(?:eğitim\s+(?:paketini|verisini)\s+dışa\s+aktar|export\s+training\s+data)\s*[.!]*\s*$", re.IGNORECASE)


def answer(prompt: str) -> str:
    """The reply for a platform command, '' for anything else."""
    if _QUALITY_RE.match(prompt):
        return release_guard.status()
    if _EXPORT_RE.match(prompt):
        folder = config.data_dir() / "training-pack"
        counts = training_pack.export(folder)
        return (f"Eğitim paketi yazıldı: `{folder}` — {counts['sft']} doğrulanmış örnek, {counts['dpo']} tercih çifti. "
                "Eğitim bu bilgisayarda yapılmaz; paketteki betik bulut ekran kartı içindir.")
    return ""
