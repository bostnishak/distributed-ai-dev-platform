"""Fast diagnostics for the web files with eslint, stylelint and HTMLHint (installed offline under data/lint-tools)."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

import config
import process_utils

_log = logging.getLogger(__name__)
_SKIP = {"node_modules", ".history", ".ai-os", "dist", "vendor", "__pycache__"}
_ESLINT_RULES = {"no-undef": "error", "no-unused-vars": "warn", "no-unreachable": "error", "no-dupe-keys": "error", "no-redeclare": "error"}
_STYLE_RULES = {"block-no-empty": True, "property-no-unknown": True, "color-no-invalid-hex": True, "unit-no-unknown": True, "declaration-block-no-duplicate-properties": True}


def _tools() -> Path:
    return config.data_dir() / "lint-tools" / "node_modules"


def available() -> bool:
    return bool(shutil.which("node")) and (_tools() / "eslint" / "package.json").is_file()


def _files(ws_dir: Path, suffixes: tuple[str, ...]) -> list[Path]:
    return [p for p in sorted(ws_dir.rglob("*")) if p.suffix in suffixes and p.is_file() and not _SKIP & set(p.relative_to(ws_dir).parts)][:40]


def _run(script: str, args: list[str], cwd: Path) -> list:
    done = process_utils.run_process([shutil.which("node") or "node", str(_tools() / script), *args], cwd=cwd, timeout_s=60, max_output_chars=200_000)
    for stream in (done.stdout, done.stderr):  # stylelint writes its report to stderr
        text = stream.strip()
        if text.startswith("["):
            try:
                return json.loads(text)
            except ValueError:
                continue
    return []


def _eslint(ws_dir: Path, folder: Path, files: list[Path]) -> list[str]:
    modules = _tools().as_uri()
    config_file = folder / "eslint.config.mjs"
    config_file.write_text(f'import globals from "{modules}/globals/index.js";\nexport default [{{ files: ["**/*.js", "**/*.mjs"], languageOptions: {{ ecmaVersion: "latest", '
                           f'globals: {{ ...globals.browser, ...globals.node }} }}, rules: {json.dumps(_ESLINT_RULES)} }}];\n', encoding="utf-8")
    report = _run("eslint/bin/eslint.js", ["--no-config-lookup", "-c", str(config_file), "-f", "json", *[str(f) for f in files]], ws_dir)
    return [f"{Path(entry['filePath']).relative_to(ws_dir.resolve()).as_posix()}:{m.get('line', 0)} {m['message']}" for entry in report for m in entry.get("messages", []) if m.get("severity") == 2]


def _stylelint(ws_dir: Path, folder: Path, files: list[Path]) -> list[str]:
    config_file = folder / "stylelint.json"
    config_file.write_text(json.dumps({"rules": _STYLE_RULES}), encoding="utf-8")
    report = _run("stylelint/bin/stylelint.mjs", ["--config", str(config_file), "--formatter", "json", *[str(f) for f in files]], ws_dir)
    return [f"{Path(entry['source']).name}:{w.get('line', 0)} {w['text']}" for entry in report for w in entry.get("warnings", [])]


def _htmlhint(ws_dir: Path, folder: Path, files: list[Path]) -> list[str]:
    config_file = folder / "htmlhint.json"
    config_file.write_text(json.dumps({"tagname-lowercase": True, "attr-no-duplication": True, "id-unique": True, "tag-pair": True, "src-not-empty": True, "spec-char-escape": False}), encoding="utf-8")
    report = _run("htmlhint/bin/htmlhint", ["--config", str(config_file), "--format", "json", *[str(f) for f in files]], ws_dir)
    return [f"{Path(entry['file']).name}:{m.get('line', 0)} {m['message']}" for entry in report for m in entry.get("messages", [])]


def findings(ws_dir: Path) -> list[str]:
    """Errors found by the three linters ([] when they are not installed)."""
    if not available():
        return []
    out: list[str] = []
    with tempfile.TemporaryDirectory(prefix="cm6453_lint_", ignore_cleanup_errors=True) as tmp:
        for runner, suffixes in ((_eslint, (".js", ".mjs")), (_stylelint, (".css",)), (_htmlhint, (".html",))):
            if files := _files(ws_dir, suffixes):
                try:
                    out += runner(ws_dir.resolve(), Path(tmp), [f.resolve() for f in files])
                except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
                    _log.warning("lint tool failed: %r", exc)
    return out[:20]
