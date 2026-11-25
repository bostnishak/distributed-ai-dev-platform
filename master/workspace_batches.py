"""Order and prompts for file-by-file project generation."""

from __future__ import annotations

import os
from typing import Any


def file_batches(planned: list[dict[str, str]]) -> list[list[dict[str, str]]]:
    """Generation order: the first (anchor) file alone so the others can use its ids/classes, then independent files in pairs
    (Ollama serves several requests at once), tests last and alone because they need every other file. WS_PARALLEL=1 restores one-by-one."""
    width = max(1, int(os.environ.get("WS_PARALLEL", "2")))
    if not planned:
        return []
    tests = [f for f in planned[1:] if "test" in f["path"].lower()]
    middle = [f for f in planned[1:] if f not in tests]
    batches = [[planned[0]]] + [middle[i : i + width] for i in range(0, len(middle), width)] + [[f] for f in tests]
    return [b for b in batches if b]


def file_prompt(meta: dict[str, Any], prompt: str, tree_summary: str, done: tuple[list[str], list[str]], fspec: dict[str, str]) -> str:
    """Prompt for one file: project facts, file tree, the contracts (ids, classes, exports) and snippets of files written so far."""
    contracts, written = done
    manifest = "\n".join(contracts)
    tail = "\n\n".join(written[-3:])
    head = f"Proje Adı: {meta['name']}\nProje Türü: {meta['project_type']}\nKullanıcı İsteği: {prompt}\n\nTüm Dosya Ağacı:\n{tree_summary}\n\n"
    if manifest:
        head += f"Yazılan Dosyaların Sözleşme Özeti (ID/CSS/Export/Sembol):\n{manifest}\n\n"
    if tail:
        head += f"Son dosyaların kod özetleri:\n{tail}\n\n"
    return head + f"ŞİMDİ SADECE ŞU DOSYANIN EKSİKSİZ İÇERİĞİNİ YAZ: `{fspec['path']}`\nDosya amacı: {fspec['purpose']}"
