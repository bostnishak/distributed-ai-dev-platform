"""Build a correct requirements.txt for a generated project from the imports in its code.

Local models often list standard-library modules (os, json) or pin ancient versions, which makes `pip install -r` fail.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

_PIP_NAMES = {
    "cv2": "opencv-python", "PIL": "Pillow", "yaml": "PyYAML", "sklearn": "scikit-learn", "bs4": "beautifulsoup4",
    "dotenv": "python-dotenv", "flask_sqlalchemy": "Flask-SQLAlchemy", "flask_cors": "Flask-Cors", "flask_login": "Flask-Login",
    "flask_wtf": "Flask-WTF", "flask_migrate": "Flask-Migrate", "jose": "python-jose", "jwt": "PyJWT", "serial": "pyserial",
    "docx": "python-docx", "pptx": "python-pptx", "dateutil": "python-dateutil", "magic": "python-magic", "fitz": "PyMuPDF",
    "flask": "Flask", "fastapi": "fastapi", "uvicorn": "uvicorn", "pydantic": "pydantic", "sqlalchemy": "SQLAlchemy",
}
_STDLIB = set(sys.stdlib_module_names)


def _third_party_imports(ws_dir: Path) -> list[str]:
    local = {p.stem for p in ws_dir.rglob("*.py")} | {p.name for p in ws_dir.iterdir() if p.is_dir()}
    found: set[str] = set()
    for py in ws_dir.rglob("*.py"):
        if ".history" in py.parts:
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.add(node.module.split(".")[0])
    return sorted(m for m in found if m not in _STDLIB and m not in local and not m.startswith("_"))


def fix_requirements(ws_dir: Path) -> bool:
    """Rewrite requirements.txt when the project has Python code; returns True if a file was written."""
    if not any(p for p in ws_dir.rglob("*.py") if ".history" not in p.parts):
        return False
    pkgs = [_PIP_NAMES.get(m, m) for m in _third_party_imports(ws_dir)]
    body = "\n".join(pkgs) + "\n" if pkgs else "# Ek bağımlılık yok: proje yalnızca Python standart kütüphanesini kullanıyor.\n"
    (ws_dir / "requirements.txt").write_text(body, encoding="utf-8")
    return True


_TEMPLATE_CALL_RE = re.compile(r"render_template\(\s*['\"]([^'\"]+)['\"]")


def _py_files(ws_dir: Path) -> list[Path]:
    return [p for p in ws_dir.rglob("*.py") if ".history" not in p.parts and "venv" not in p.parts]


def _fix_flask_templates(ws_dir: Path) -> None:
    """Flask only looks for templates/ next to the app module; copy a template that was written somewhere else."""
    for py in _py_files(ws_dir):
        for name in _TEMPLATE_CALL_RE.findall(py.read_text(encoding="utf-8", errors="replace")):
            target = py.parent / "templates" / name
            if target.exists():
                continue
            src = next((c for c in ws_dir.rglob(Path(name).name) if c.is_file() and ".history" not in c.parts), None)
            if src is not None:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(src.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")


def _add_package_launcher(ws_dir: Path) -> None:
    """`python backend/app.py` cannot import `backend.*`; give such projects an `app.py`-style launcher at the root."""
    for py in _py_files(ws_dir):
        pkg = py.parent
        if pkg == ws_dir or pkg.parent != ws_dir or py.name not in ("app.py", "main.py"):
            continue
        text = py.read_text(encoding="utf-8", errors="replace")
        if f"from {pkg.name}." not in text and f"import {pkg.name}." not in text:
            continue
        (pkg / "__init__.py").touch()
        launcher = ws_dir / "run.py"
        if not launcher.exists() and re.search(r"^app\s*=", text, re.M):
            body = f"from {pkg.name}.{py.stem} import app\n\nif __name__ == \"__main__\":\n    app.run(debug=True)\n"
            if "SQLAlchemy" in text or "db.init_app" in text:
                body = body.replace("    app.run", f"    from {pkg.name}.models import db\n\n    with app.app_context():\n        db.create_all()\n    app.run")
            launcher.write_text(body, encoding="utf-8")
        return


def repair_project(ws_dir: Path) -> None:
    """Fixes for typical integration slips in model-written projects (run right after generation)."""
    fix_requirements(ws_dir)
    _fix_flask_templates(ws_dir)
    _add_package_launcher(ws_dir)
