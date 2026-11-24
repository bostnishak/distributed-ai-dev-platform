"""Basic result validation for submitted task outputs (PB-33).

Validation runs synchronously when an agent submits a result. A failure updates the task's
validation_status to 'failed' and the task is requeued for a different agent.
"""

import ast
import re


def _validate_python_output(output: str, files: list[dict] | None) -> tuple[bool, str]:
    for block in _extract_python(output):
        ok, msg = _check_python_syntax(block)
        if not ok:
            return False, msg
    for f in files or ():
        if f.get("path", "").endswith(".py"):
            ok, msg = _check_python_syntax(f["content"])
            if not ok:
                return False, f"{f['path']}: {msg}"
    return True, ""


def validate_result(task_type: str, output: str, files: list[dict] | None = None) -> tuple[bool, str]:
    """Returns (ok, error_message). An empty error_message means validation passed."""
    if not output or not output.strip():
        return False, "Boş çıktı."
    if len(output.strip()) < 20:
        return False, "Çıktı çok kısa (< 20 karakter)."
    if task_type in ("backend", "testing"):
        return _validate_python_output(output, files)
    return True, ""


def _extract_python(text: str) -> list[str]:
    return re.findall(r"```(?:python)?\n(.*?)```", text, re.DOTALL)


def _check_python_syntax(code: str) -> tuple[bool, str]:
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as exc:
        return False, f"Python sözdizimi hatası satır {exc.lineno}: {exc.msg}"


def _fallback_extract_files(task_type: str, output: str) -> list[dict]:
    if task_type in ("backend", "testing"):
        blocks = _extract_python(output)
        default_path = "backend/main.py" if task_type == "backend" else "tests/test_generated.py"
        return [{"path": default_path, "content": blocks[0]}] if blocks else []
    if task_type == "database":
        sql_match = re.search(r"(CREATE\s+TABLE.*?;)", output, re.IGNORECASE | re.DOTALL)
        return [{"path": "database/schema.sql", "content": sql_match.group(1)}] if sql_match else []
    if task_type == "frontend":
        html_match = re.search(r"(<!DOCTYPE.*?</html>)", output, re.IGNORECASE | re.DOTALL)
        return [{"path": "frontend/index.html", "content": html_match.group(1)}] if html_match else []
    return []


def extract_files_from_output(task_type: str, output: str) -> list[dict]:
    """Try to extract named file blocks from the agent's text output."""
    files: list[dict] = []
    for m in re.finditer(r"```([a-zA-Z0-9_./\-]+\.[a-zA-Z]{1,10})\n(.*?)```", output, re.DOTALL):
        path = m.group(1).strip()
        content = m.group(2)
        if path and content.strip():
            files.append({"path": path, "content": content})
    return files if files else _fallback_extract_files(task_type, output)
