"""Order and prompts for file-by-file project generation."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any

import event_log
import merge3
import patch_edit
from prompt_loader import load_prompt

_SINGLE_HTML_RE = re.compile(r"\btek(?: bir)?(?: html)? dosya|\bsingle[- ](?:html[- ])?file\b|\bone html file\b", re.IGNORECASE)


def wants_single_html(prompt: str) -> bool:
    """The user asked for everything in one HTML file (not a server project, not a file tree)."""
    return bool(_SINGLE_HTML_RE.search(prompt or "")) and "html" in prompt.lower()


_API_RE = re.compile(r"\b(?:rest\s*api|api)\w*", re.IGNORECASE)
_NOT_ONLY_API_RE = re.compile(r"arayüz|ön\s*yüz|frontend|web (?:sitesi|sayfası|uygulaması)|html|react|\w+\.py\b|\w+/|mikroservis|microservice|katman", re.IGNORECASE)


def wants_single_api(prompt: str) -> bool:
    """A small API without a user interface or a requested file layout: one module avoids names that do not match across files."""
    return len(prompt) < 700 and bool(_API_RE.search(prompt)) and bool(re.search(r"fastapi|flask", prompt, re.IGNORECASE)) and not _NOT_ONLY_API_RE.search(prompt)


def fixed_plan(prompt: str) -> dict[str, Any] | None:
    """Plan overrides for requests whose layout must not be left to the model."""
    if wants_single_html(prompt):
        return {"files": single_html_plan(), "project_type": "web", "entry_point": "index.html"}
    if wants_single_api(prompt):
        purpose = "TÜM sunucu tek dosyada: modeller, sqlite3 tabloları ve uç noktalar; `app` adlı uygulama nesnesi; yerel modül içe aktarma yok"
        return {"project_type": "fullstack", "entry_point": "app.py", "files": [
            {"path": "app.py", "purpose": purpose, "tokens": 7000, "model": "qwen3.5:9b"},
            {"path": "requirements.txt", "purpose": "Bağımlılıklar"},
            {"path": "README.md", "purpose": "Kurulum, çalıştırma ve uç nokta örnekleri"}]}
    return None


def single_html_plan() -> list[dict[str, Any]]:
    purpose = "TÜM uygulama tek dosyada: <style> ve <script> içeride, harici dosya/kütüphane yok; istenen renkler, yerleşim, butonlar ve örnek veriler birebir"
    return [{"path": "index.html", "purpose": purpose, "tokens": 9000, "model": "qwen3.5:9b", "system": load_prompt("b4_single_file_writer.txt")}]


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
    if fspec["path"].endswith(".py") and meta.get("project_type") == "fullstack":
        head += load_prompt("agent_backend.md") + "\n\n"
    return head + f"ŞİMDİ SADECE ŞU DOSYANIN EKSİKSİZ İÇERİĞİNİ YAZ: `{fspec['path']}`\nDosya amacı: {fspec['purpose']}"


def _patcher(model: str, tokens: int) -> Any:
    async def generate(system: str, user: str) -> str:
        import workspace_builder as wb

        return await wb._ollama_generate(await wb.pick_coder_model(model), system, user, num_predict=tokens, temperature=0.1)

    return generate


def _store(ws_dir: Any, path: str, current: str, code: str) -> str:
    """Write the model's version, merging in whatever the user changed on disk while it was being generated."""
    target = ws_dir / path
    on_disk = target.read_text(encoding="utf-8", errors="replace") if target.is_file() else current
    if current and on_disk != current:
        code, conflicts = merge3.merge(current, code, on_disk, path)
        event_log.record(ws_dir, "elle değişiklik korundu", f"{path}" + (f", çakışan satırlar: {conflicts[:5]}" if conflicts else ""))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(code, encoding="utf-8")
    return code


async def apply_edit(write: Any, target: tuple[Any, str, str], fspec: dict[str, Any], current: str) -> str:
    """Rewrite one existing file with a budget that fits it; a cut-off answer never replaces a working page."""
    ws_dir, model, ask = target
    spec = {**fspec, "tokens": min(14000, max(4096, len(current) // 2))}
    if str(fspec["path"]).endswith(".html") and "<style" in current:  # self-contained page: same writer as when it was created
        spec.update(model="qwen3.5:9b", system=load_prompt("b4_single_file_writer.txt"))
    patched = await patch_edit.try_patch(_patcher(spec.get("model") or model, spec["tokens"]), ask, current)
    if patched is not None:
        return _store(ws_dir, fspec["path"], current, pure_source(patched))
    with tempfile.TemporaryDirectory(prefix="cm6453_edit_", ignore_cleanup_errors=True) as tmp:  # generated aside: the real file is touched only once
        code = await write(Path(tmp), model, spec, ask)
    if "</html>" in current.lower() and "</html>" not in code.lower():
        if not (ws_dir / fspec["path"]).is_file():  # a working page is never replaced by a cut-off one
            (ws_dir / fspec["path"]).write_text(current, encoding="utf-8")
        return current
    return _store(ws_dir, fspec["path"], current, pure_source(code))


_HIGHLIGHT_RE = re.compile(r"<span class=\"hl-(?:tag|attr|str|kw|num|comment)\">(.*?)</span>", re.DOTALL)


def pure_source(code: str) -> str:
    """Workspace files hold source only: editor colouring spans that ended up in an answer are removed before writing."""
    while _HIGHLIGHT_RE.search(code):
        code = _HIGHLIGHT_RE.sub(r"\1", code)
    return code
