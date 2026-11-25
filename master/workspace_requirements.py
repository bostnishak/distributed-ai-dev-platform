"""Build a correct requirements.txt for a generated project from the imports in its code.

Local models often list standard-library modules (os, json) or pin ancient versions, which makes `pip install -r` fail.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

from workspace_kit import inject_theme

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


_ASSET_REF_RE = re.compile(r"""(href|src)=(["'])/?(?!static/|https?:|//|\{|#)([^"'#?]+\.(?:css|js|png|jpe?g|svg|ico|gif|webp))\2""")


def _fix_static_refs(ws_dir: Path) -> None:
    """Flask serves assets from <app>/static under /static/...; point template links there and copy the files."""
    for tpl in [p for p in ws_dir.rglob("*.html") if p.parent.name == "templates" and ".history" not in p.parts]:
        text = tpl.read_text(encoding="utf-8", errors="replace")

        def repl(m: re.Match[str], tpl: Path = tpl) -> str:
            rel = re.sub(r"^(?:static/)+", "", m.group(3).lstrip("./"))  # collapse /static/static/... left by earlier passes
            src = next((c for c in ws_dir.rglob(Path(rel).name) if c.is_file() and ".history" not in c.parts and "static" not in c.parts[:-1]), None)
            dest = tpl.parent.parent / "static" / rel
            if src is not None and not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(src.read_bytes())
            return f"{m.group(1)}={m.group(2)}/static/{rel}{m.group(2)}" if dest.exists() else m.group(0)

        fixed = _ASSET_REF_RE.sub(repl, text)
        if fixed != text:
            tpl.write_text(fixed, encoding="utf-8")


def _refresh_static_copies(ws_dir: Path) -> None:
    """A copy under static/ must not go stale after the original asset was repaired."""
    for dest in [p for p in ws_dir.rglob("*") if p.is_file() and "static" in p.parts and ".history" not in p.parts]:
        src = next((c for c in ws_dir.rglob(dest.name) if c.is_file() and "static" not in c.parts and ".history" not in c.parts), None)
        if src is not None and src.stat().st_mtime > dest.stat().st_mtime:
            dest.write_bytes(src.read_bytes())


def _ensure_db_tables(ws_dir: Path) -> None:
    """Flask-SQLAlchemy apps often create tables only under `if __name__ == "__main__"`, so `flask run`/gunicorn start without tables."""
    for py in _py_files(ws_dir):
        text = py.read_text(encoding="utf-8", errors="replace")
        guard = re.search(r"^if __name__ == ['\"]__main__['\"]:", text, re.M)
        if py.parent != ws_dir or not re.search(r"^app\s*=\s*Flask", text, re.M) or not re.search(r"db\.init_app\(app\)|SQLAlchemy\(app\)", text):
            continue
        head = text[: guard.start()] if guard else text
        if "create_all" not in head:
            block = "with app.app_context():\n    db.create_all()\n\n\n"
            py.write_text(head.rstrip() + "\n\n" + block + (text[guard.start() :] if guard else ""), encoding="utf-8")


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
            lines = [f"from {pkg.name}.{py.stem} import app"]
            if "SQLAlchemy" in text or "db.init_app" in text:
                lines += [f"from {pkg.name}.models import db", "", "with app.app_context():", "    db.create_all()"]
            lines += ["", 'if __name__ == "__main__":', "    app.run(debug=True)", ""]
            launcher.write_text("\n".join(lines), encoding="utf-8")
        return


_EXTERNAL_DB_RE = re.compile(r"(?:postgres(?:ql)?|mysql|mariadb|mssql)(?:\+\w+)?://[^'\"\s]*")


def _use_sqlite(ws_dir: Path) -> None:
    """A starter project must run anywhere: swap external database URLs for a local SQLite file."""
    for py in _py_files(ws_dir):
        text = py.read_text(encoding="utf-8", errors="replace")
        fixed = _EXTERNAL_DB_RE.sub("sqlite:///app.db", text)
        if fixed != text:
            py.write_text(fixed, encoding="utf-8")


_LOCAL_REF_RE = re.compile(r"""(href|src)=(["'])(?!https?:|//|/|\{|#|data:)([^"'#?]+\.(?:css|js|png|jpe?g|svg|ico|gif|webp))\2""")


def _fix_missing_local_refs(ws_dir: Path) -> None:
    """A page that links 'theme.css' while the file is 'css/theme.css' loads nothing: point the link at the file with that name."""
    for page in [p for p in ws_dir.rglob("*.html") if ".history" not in p.parts and p.parent.name != "templates"]:
        text = page.read_text(encoding="utf-8", errors="replace")

        def repl(m: re.Match[str], page: Path = page) -> str:
            if (page.parent / m.group(3)).exists():
                return m.group(0)
            found = next((c for c in ws_dir.rglob(Path(m.group(3)).name) if c.is_file() and ".history" not in c.parts), None)
            if found is None and Path(m.group(3)).name == "theme.css":  # the model linked the shared theme it was told about but never wrote it
                import workspace_kit

                target = page.parent / m.group(3)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(workspace_kit._KIT.read_text(encoding="utf-8"), encoding="utf-8")
                return m.group(0)
            return f"{m.group(1)}={m.group(2)}{found.relative_to(page.parent).as_posix()}{m.group(2)}" if found else m.group(0)

        fixed = _LOCAL_REF_RE.sub(repl, text)
        if fixed != text:
            page.write_text(fixed, encoding="utf-8")


def repair_project(ws_dir: Path) -> None:
    """Fixes for typical integration slips in model-written projects (run right after generation)."""
    _use_sqlite(ws_dir)
    fix_requirements(ws_dir)
    _fix_flask_templates(ws_dir)
    inject_theme(ws_dir)
    _fix_static_refs(ws_dir)
    _fix_missing_local_refs(ws_dir)
    _refresh_static_copies(ws_dir)
    _add_package_launcher(ws_dir)
    _ensure_db_tables(ws_dir)
