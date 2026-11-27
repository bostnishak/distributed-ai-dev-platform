"""Find hollow work in a generated project: swallowed errors, fake waiting, empty tests, controls that do nothing."""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from pathlib import Path

import cheat_guard

_SKIP_PARTS = {".history", ".git", "node_modules", "__pycache__", "venv", ".venv", "dist", ".ai-os"}
_JS_EMPTY_CATCH_RE = re.compile(r"catch\s*(?:\([^)]*\))?\s*\{\s*(?:/\*.*?\*/\s*|//[^\n]*\n\s*)*\}", re.DOTALL)
_JS_FAKE_RE = re.compile(r"setTimeout\s*\(\s*(?:\(\s*\)|function\s*\(\s*\))\s*(?:=>)?\s*\{[^{}]{0,300}?[\"'`][^\"'`]*(?:başarıyla|successfully|kaydedildi|gönderildi|yanıtı|response)[^\"'`]*[\"'`]", re.IGNORECASE)
_PY_QUIET = (type(None), dict, list, str, bool, int)


def _files(ws_dir: Path, *suffixes: str) -> Iterator[tuple[str, str]]:
    for path in sorted(ws_dir.rglob("*")):
        relative = path.relative_to(ws_dir)
        if path.is_file() and path.suffix in suffixes and not _SKIP_PARTS & set(relative.parts) and path.stat().st_size < 400_000:
            yield relative.as_posix(), path.read_text(encoding="utf-8", errors="replace")


def _empty_value(node: ast.expr | None) -> bool:
    if node is None:
        return True
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return False
    return isinstance(value, _PY_QUIET) and not value


def _silent(handler: ast.ExceptHandler) -> bool:
    broad = handler.type is None or (isinstance(handler.type, ast.Name) and handler.type.id in ("Exception", "BaseException"))
    body = handler.body
    if all(isinstance(s, ast.Pass) or (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)) for s in body):
        return True
    return broad and len(body) == 1 and isinstance(body[0], ast.Return) and _empty_value(body[0].value)


def _is_route(function: ast.AST) -> bool:
    return any(re.search(r"\.(?:get|post|put|patch|delete|route)\b", ast.unparse(d)) for d in getattr(function, "decorator_list", []))


def _python(path: str, source: str) -> Iterator[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return
    testing = cheat_guard.is_test(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and _silent(node):
            yield f"{path}:{node.lineno} hata sessizce yutuluyor"
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if _is_route(node) and any(isinstance(c, ast.Call) and ast.unparse(c.func) in ("time.sleep", "asyncio.sleep") for c in ast.walk(node)):
                yield f"{path}:{node.lineno} istek işleyicide yapay bekleme ({node.name})"
            if testing and node.name.startswith("test_") and cheat_guard.checks_of(ast.unparse(node))[0] == 0:
                yield f"{path}:{node.lineno} gerçek denetimi olmayan test ({node.name})"


def _javascript(path: str, source: str) -> Iterator[str]:
    def line(match: re.Match) -> int:
        return source.count("\n", 0, match.start()) + 1

    for match in _JS_EMPTY_CATCH_RE.finditer(source):
        yield f"{path}:{line(match)} boş catch bloğu"
    for match in _JS_FAKE_RE.finditer(source):
        yield f"{path}:{line(match)} gerçek işlem yerine zamanlayıcıyla uydurma sonuç"
    if cheat_guard.is_test(path) and (cheat_guard.checks_of(source)[0] <= 0 and re.search(r"\b(?:it|test)\s*\(", source)):
        yield f"{path}:1 gerçek denetimi olmayan test"


def findings(ws_dir: Path) -> list[str]:
    out: list[str] = []
    for path, source in _files(ws_dir, ".py"):
        out += _python(path, source)
    for path, source in _files(ws_dir, ".js", ".ts", ".jsx", ".tsx", ".html"):
        out += _javascript(path, source)
    return out


_WANTED = {"click", "mousedown", "mouseup", "pointerdown", "pointerup", "keydown", "submit", "change", "input"}


def unwired(page) -> list[str]:
    """Buttons nothing reacts to, read from a loaded page through the browser's own listener table."""
    script = """() => [...document.querySelectorAll('button, input[type=button]')].map((b, i) => {
        b.setAttribute('data-audit', String(i));
        const form = b.form;
        const submits = form && (b.type === 'submit') && (form.getAttribute('action') || form.onsubmit);
        const inline = b.onclick || b.getAttribute('onclick') || b.getAttribute('popovertarget') || b.getAttribute('commandfor');
        return { index: i, label: (b.innerText || b.value || b.getAttribute('aria-label') || 'düğme').trim().slice(0, 40), wired: Boolean(submits || inline || b.disabled), form: Boolean(form && b.type === 'submit') };
    })"""
    session = page.context.new_cdp_session(page)

    def listeners(expression: str) -> set[str]:
        target = session.send("Runtime.evaluate", {"expression": expression}).get("result", {}).get("objectId")
        if not target:
            return set()
        return {item["type"] for item in session.send("DOMDebugger.getEventListeners", {"objectId": target}).get("listeners", [])}

    shared = (listeners("window") | listeners("document") | listeners("document.body")) & {"click", "pointerdown", "pointerup", "mousedown", "mouseup"}
    dead = []
    for button in page.evaluate(script):
        if button["wired"] or shared:
            continue
        chain = f"document.querySelector('[data-audit=\"{button['index']}\"]')"
        own: set[str] = set()
        node = chain
        for _depth in range(8):
            own |= listeners(node)
            if button["form"]:
                own |= listeners(f"{chain}.form") & {"submit"}
            node += ".parentElement"
            if not session.send("Runtime.evaluate", {"expression": f"Boolean({node.replace('.parentElement', '?.parentElement')})"}).get("result", {}).get("value"):
                break
        if not own & _WANTED:
            dead.append(button["label"])
    return dead
