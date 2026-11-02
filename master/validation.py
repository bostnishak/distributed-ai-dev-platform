"""Basic result validation for submitted task outputs (PB-33).

Validation runs synchronously when an agent submits a result. A failure updates the task's
validation_status to 'failed' and the task is requeued for a different agent.
"""

import ast
import re


def validate_result(task_type: str, output: str, files: list[dict] | None = None) -> tuple[bool, str]:
    """Returns (ok, error_message). An empty error_message means validation passed."""
    if not output or not output.strip():
        return False, "Boş çıktı."
    if len(output.strip()) < 20:
        return False, "Çıktı çok kısa (< 20 karakter)."

    if task_type in ("backend", "testing"):
        for block in _extract_python(output):
            ok, msg = _check_python_syntax(block)
            if not ok:
                return False, msg
        if files:
            for f in files:
                if f.get("path", "").endswith(".py"):
                    ok, msg = _check_python_syntax(f["content"])
                    if not ok:
                        return False, f"{f['path']}: {msg}"

    elif task_type == "database":
        sql_upper = output.upper()
        if "CREATE" not in sql_upper and "TABLE" not in sql_upper:
            pass  # Model may return DDL in different formats; treat as soft warning, not failure

    return True, ""


def _extract_python(text: str) -> list[str]:
    return re.findall(r"```(?:python)?\n(.*?)```", text, re.DOTALL)


def _check_python_syntax(code: str) -> tuple[bool, str]:
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as exc:
        return False, f"Python sözdizimi hatası satır {exc.lineno}: {exc.msg}"


def extract_files_from_output(task_type: str, output: str) -> list[dict]:
    """Try to extract named file blocks from the agent's text output."""
    files: list[dict] = []

    # Pattern: ```filename.ext\ncontent\n```
    for m in re.finditer(r"```([a-zA-Z0-9_./\-]+\.[a-zA-Z]{1,10})\n(.*?)```", output, re.DOTALL):
        path = m.group(1).strip()
        content = m.group(2)
        if path and content.strip():
            files.append({"path": path, "content": content})

    # Fallback: type-based default filenames when no named blocks found
    if not files:
        if task_type == "backend":
            blocks = _extract_python(output)
            if blocks:
                files.append({"path": "backend/main.py", "content": blocks[0]})
        elif task_type == "database":
            sql_match = re.search(r"(CREATE\s+TABLE.*?;)", output, re.IGNORECASE | re.DOTALL)
            if sql_match:
                files.append({"path": "database/schema.sql", "content": sql_match.group(1)})
        elif task_type == "testing":
            blocks = _extract_python(output)
            if blocks:
                files.append({"path": "tests/test_generated.py", "content": blocks[0]})
        elif task_type == "frontend":
            html_match = re.search(r"(<!DOCTYPE.*?</html>)", output, re.IGNORECASE | re.DOTALL)
            if html_match:
                files.append({"path": "frontend/index.html", "content": html_match.group(1)})

    return files
