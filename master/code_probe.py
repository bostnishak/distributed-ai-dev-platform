"""'Why does this code fail?' questions: run the snippet (Python in the offline Docker sandbox, JS under Node's permission sandbox) and hand the REAL error to the model."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

_ASK_RE = re.compile(r"(hata|error|neden|why|çalışm|calism|fail|bug|exception|doesn'?t work|not working|undefined|çöküyor|crash)", re.IGNORECASE)
_FENCE_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
_JS_HINT = re.compile(r"\b(console\.log|const |let |=>|function\s*\(|document\.|require\()")
_PY_HINT = re.compile(r"(\bdef |\bprint\(|\bfor \w+ in\b|\bimport \w+|\bwhile .*:|\bclass \w+|^\s*if .*:)", re.MULTILINE)


def _extract(prompt: str) -> tuple[str, str] | None:
    """(language, code) from a fenced block or from the text after the question's colon/question mark."""
    if m := _FENCE_RE.search(prompt):
        code, lang = m.group(2).strip(), (m.group(1) or "").lower()
    else:
        parts = re.split(r"[?:]\s+", prompt, maxsplit=1)
        code, lang = (parts[1].strip() if len(parts) == 2 else ""), ""
    if len(code) < 6:
        return None
    lang = lang or ("js" if _JS_HINT.search(code) else "py" if _PY_HINT.search(code) else "")
    return (lang, code) if lang in ("js", "javascript", "py", "python") else None


def _colon_fix(code: str) -> str:
    """If inserting a single ':' makes the snippet compile, say exactly where it was missing."""
    for m in re.finditer(r"(?<=[\w)\]\"'])(?=\s+\S)", code):
        trial = code[: m.start()] + ":" + code[m.start() :]
        try:
            compile(trial, "<fix>", "exec")
        except SyntaxError:
            continue
        return f"\nTek değişiklikle düzelir: iki nokta (:) eksik; şu satır derlenir -> {trial.splitlines()[0][:120]}"
    return ""


def _python(code: str) -> str:
    try:
        compile(code, "<snippet>", "exec")
    except SyntaxError as exc:
        return f"SyntaxError: {exc.msg} (satır {exc.lineno})" + _colon_fix(code)
    from sandbox import runner

    if not runner.docker_daemon_ready()[0]:
        return ""
    with tempfile.TemporaryDirectory(prefix="cm6453_probe_") as tmp:
        Path(tmp, "snippet.py").write_text(code, encoding="utf-8")
        res = runner.run_workspace_command(Path(tmp), ["python", "/sandbox/snippet.py"], timeout_s=10)
    err = (res.get("stderr") or "").strip().splitlines()
    return err[-1][:300] if err and not res.get("timed_out") else ""


def _javascript(code: str) -> str:
    node = shutil.which("node")
    if not node:
        return ""
    with tempfile.TemporaryDirectory(prefix="cm6453_probe_") as tmp:
        path = Path(tmp, "snippet.js")
        path.write_text(code, encoding="utf-8")
        # Node's permission model: no file-system (beyond the snippet), network, child-process or worker access
        cmd = [node, "--permission", f"--allow-fs-read={path}", str(path)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=6, check=False)  # noqa: S603, RUF100
        except subprocess.TimeoutExpired:
            return ""
    lines = [ln for ln in proc.stderr.splitlines() if re.match(r"\w*Error", ln)]
    return lines[-1][:300] if proc.returncode and lines else ""


def note(prompt: str) -> str:
    """System note with the verified error (or the verified fact that the snippet runs cleanly); '' when not a debug question."""
    if not _ASK_RE.search(prompt or "") or len(prompt) > 1500:
        return ""
    found = _extract(prompt)
    if not found:
        return ""
    lang, code = found
    try:
        error = _python(code) if lang.startswith("py") else _javascript(code)
    except (OSError, subprocess.SubprocessError, ValueError):
        return ""
    if not error:
        return ""
    return f"DOĞRULANMIŞ HATA (kod gerçekten çalıştırıldı/derlendi): {error}\nHatayı yalnızca bu çıktıya dayanarak açıkla ve düzeltilmiş kodu ver; çıktıda olmayan bir neden uydurma."


_EXPR_RE = re.compile(r"(?<![\w.])(\d+(?:[.,]\d+)?(?:\s*[-+*/x\u00d7:÷^]\s*\d+(?:[.,]\d+)?){1,4})(?![\w.])")


def calc_note(prompt: str) -> str:
    """Plain arithmetic in the question ('17 x 23 kaç eder'): the code computes the result so the model only explains it."""
    if not re.search(r"(kaç|ne\s+eder|hesapla|çarp|topla|böl|çıkar|calculate|compute|what\s+is|how\s+much)", prompt or "", re.IGNORECASE):
        return ""
    m = _EXPR_RE.search(prompt)
    if not m:
        return ""
    expr = re.sub(r"\s+", "", m.group(1)).replace(",", ".").replace("x", "*").replace("\u00d7", "*").replace(":", "/").replace("÷", "/").replace("^", "**")
    if "**" in expr:
        return ""
    try:
        value = eval(compile(expr, "<calc>", "eval", dont_inherit=True), {"__builtins__": {}}, {})  # noqa: S307, RUF100  # digits and + - * / only (regex-checked above)
    except (SyntaxError, ZeroDivisionError, ValueError):
        return ""
    shown = f"{value:.6f}".rstrip("0").rstrip(".") if isinstance(value, float) else str(value)
    return f"DOĞRULANMIŞ HESAP: {m.group(1).strip()} = {shown}. Sonuç budur; adımları bu sonuca götüren basit bir yolla (ör. parçala-topla) kısaca açıkla, kuralı yanlış anlatma."


def verified_prefix(prompt: str, has_file: bool) -> str:
    """Code-verified facts (real error output, exact arithmetic) placed in front of the user's question."""
    notes = [n for n in ("" if has_file else note(prompt), calc_note(prompt)) if n]
    return "\n".join(notes) + "\n\nKULLANICI SORUSU:\n" if notes else ""
