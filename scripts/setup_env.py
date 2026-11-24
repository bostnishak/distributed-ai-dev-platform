"""One-command local setup, .env secret hardening, and runtime capability audit for DADP."""

from __future__ import annotations

import argparse
import importlib.util
import json
import secrets
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

_SECRET_DEFAULTS: tuple[tuple[str, int], ...] = (
    ("SECRET_KEY", 32),
    ("ADMIN_TOKEN", 24),
    ("AGENT_TOKEN", 24),
    ("BACKUP_PASSWORD", 24),
)

_NON_SECRET_DEFAULTS: dict[str, str] = {
    "UNIFIED_DB": "true",
    "OLLAMA_URL": "http://127.0.0.1:11434",
    "MASTER_MODEL": "qwen3.5:4b",
    "STUDIO_CODER_MODEL": "qwen2.5-coder:7b",
    "HOST_BIND": "127.0.0.1",
}


def _parse_env_lines(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        k, v = stripped.split("=", 1)
        values[k.strip()] = v.strip().strip('"').strip("'")
    return values


def ensure_hardened_env(env_path: Path, *, write: bool = True) -> dict[str, Any]:
    """Generate missing secrets and recommended defaults in .env without clobbering existing values."""
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.is_file() else []
    existing = _parse_env_lines(lines)
    generated_keys: list[str] = []
    preserved_keys: list[str] = []

    updates: dict[str, str] = {}
    for key, nbytes in _SECRET_DEFAULTS:
        if existing.get(key):
            preserved_keys.append(key)
        else:
            updates[key] = secrets.token_urlsafe(nbytes)
            generated_keys.append(key)
    for key, default_val in _NON_SECRET_DEFAULTS.items():
        if existing.get(key):
            preserved_keys.append(key)
        else:
            updates[key] = default_val
            generated_keys.append(key)

    if write and updates:
        out_lines: list[str] = []
        handled: set[str] = set()
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k = stripped.split("=", 1)[0].strip()
                if k in updates:
                    out_lines.append(f"{k}={updates[k]}")
                    handled.add(k)
                    continue
            out_lines.append(line)
        for k, v in updates.items():
            if k not in handled:
                out_lines.append(f"{k}={v}")
        env_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    return {
        "env_path": str(env_path),
        "written": bool(write and updates),
        "generated_keys": generated_keys,
        "preserved_keys": preserved_keys,
    }


def audit_runtime_environment() -> dict[str, Any]:
    """Inspect local binaries and optional Python packages and produce Turkish install hints."""
    binaries = {b: bool(shutil.which(b)) for b in ("docker", "ollama", "ffmpeg", "tesseract", "node", "git")}
    packages = {
        pkg: importlib.util.find_spec(pkg) is not None
        for pkg in ("pytesseract", "faster_whisper", "pyttsx3", "PIL", "numpy", "pymupdf", "openpyxl", "docx", "pptx", "pytest_cov", "hypothesis")
    }
    hints: list[str] = []
    if not binaries["tesseract"] or not packages["pytesseract"]:
        hints.append("Taranmış PDF OCR için Tesseract OCR + `pip install pytesseract` kurun.")
    if not binaries["ffmpeg"]:
        hints.append("MP4/MP3 medya dönüştürme için FFmpeg kurun (çevrimdışı WAV/GIF yedekleri hazır).")
    if not packages["pytest_cov"]:
        hints.append("Yerel kapsama ölçümü için `pip install pytest-cov hypothesis` kurun.")
    if not binaries["ollama"]:
        hints.append("Yerel LLM yürütme için Ollama kurun ve `ollama pull qwen3.5:4b bge-m3` çalıştırın.")
    return {"binaries": binaries, "packages": packages, "hints": hints}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DADP tek komutluk .env sertleştirme ve ortam denetimi")
    parser.add_argument("--env-file", default=str(REPO_ROOT / ".env"))
    parser.add_argument("--dry-run", action="store_true", help=".env dosyasına yazmadan denetle")
    parser.add_argument("--json", action="store_true", help="JSON çıktısı üret")
    args = parser.parse_args(argv)

    env_res = ensure_hardened_env(Path(args.env_file), write=not args.dry_run)
    audit = audit_runtime_environment()
    payload = {"ok": True, "env": env_res, "runtime": audit}
    if args.json:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(
            f"Ortam dosyası: {env_res['env_path']} | Üretilen anahtarlar: {len(env_res['generated_keys'])} | "
            f"Korunanlar: {len(env_res['preserved_keys'])}\n"
        )
        for hint in audit["hints"]:
            sys.stdout.write(f"  - {hint}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
