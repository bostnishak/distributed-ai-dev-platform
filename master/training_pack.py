"""Export verified runs as fine-tuning data for a cloud GPU, and register the returned GGUF with Ollama.

SFT pairs come from projects that passed every check; preference pairs from the same request that failed and later
passed. Secrets are redacted. Training itself does not run on this machine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import config
import security_scan

_SOURCE_EXTS = (".html", ".css", ".js", ".py", ".json", ".md", ".txt")
_MAX_CHARS = 24000


def _data() -> Path:
    return Path(config.DB_PATH).resolve().parent


def _project_text(workspace: str) -> str:
    root = _data() / "workspaces" / workspace
    if not workspace or not root.is_dir():
        return ""
    parts = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_file() and path.suffix in _SOURCE_EXTS and not any(p.startswith(".") for p in relative.parts):
            parts.append(f"### {relative.as_posix()}\n{path.read_text(encoding='utf-8', errors='replace')}")
    return security_scan.redact("\n\n".join(parts))[:_MAX_CHARS]


def _runs() -> list[dict[str, Any]]:
    try:
        lines = (_data() / "trajectories.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [json.loads(line) for line in lines if line.startswith("{")]


def build() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(sft records, preference records)"""
    sft: dict[str, dict[str, Any]] = {}
    failed: dict[str, str] = {}
    preferences: list[dict[str, Any]] = []
    for run in _runs():
        request, text = run.get("request", ""), _project_text(run.get("workspace", ""))
        if not request or not text:
            continue
        if not run.get("passed"):
            failed[request] = text
            continue
        sft[request] = {"messages": [{"role": "user", "content": request}, {"role": "assistant", "content": text}]}
        if request in failed:
            preferences.append({"prompt": request, "chosen": text, "rejected": failed.pop(request)})
    return list(sft.values()), preferences


def export(out_dir: Path) -> dict[str, int]:
    sft, preferences = build()
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in (("sft_verified.jsonl", sft), ("dpo_pairs.jsonl", preferences)):
        (out_dir / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    template = Path(__file__).parent / "prompts" / "train_unsloth.py.txt"
    (out_dir / "train_unsloth.py").write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    return {"sft": len(sft), "dpo": len(preferences)}


def modelfile(gguf: Path) -> str:
    if not gguf.is_file() or gguf.suffix.lower() != ".gguf" or gguf.read_bytes()[:4] != b"GGUF":
        raise ValueError(f"geçerli bir GGUF dosyası değil: {gguf}")
    return f'FROM "{gguf.resolve()}"\nPARAMETER temperature 0.15\nPARAMETER num_ctx 8192\n'
