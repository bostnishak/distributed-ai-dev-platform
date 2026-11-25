"""Generated projects get a requirements.txt that pip can install."""

import pytest

from workspace_requirements import fix_requirements

pytestmark = pytest.mark.unit


def test_stdlib_modules_are_dropped_and_third_party_added(tmp_path):
    (tmp_path / "app.py").write_text("import os, json\nfrom flask import Flask\nimport helpers\nfrom PIL import Image\n", encoding="utf-8")
    (tmp_path / "helpers.py").write_text("import datetime\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("os\njson\nFlask==2.0.1\n", encoding="utf-8")
    assert fix_requirements(tmp_path)
    lines = (tmp_path / "requirements.txt").read_text(encoding="utf-8").split()
    assert sorted(lines) == ["Flask", "Pillow"]


def test_stdlib_only_project_has_no_packages(tmp_path):
    (tmp_path / "main.py").write_text("import os\nimport json\n", encoding="utf-8")
    fix_requirements(tmp_path)
    assert (tmp_path / "requirements.txt").read_text(encoding="utf-8").startswith("# ")


def test_non_python_project_is_left_alone(tmp_path):
    (tmp_path / "index.html").write_text("<p>x</p>", encoding="utf-8")
    assert not fix_requirements(tmp_path)
    assert not (tmp_path / "requirements.txt").exists()


def test_template_written_elsewhere_is_copied_next_to_the_app(tmp_path):
    from workspace_requirements import repair_project

    (tmp_path / "backend").mkdir()
    (tmp_path / "frontend").mkdir()
    (tmp_path / "backend" / "app.py").write_text("from flask import Flask, render_template\napp = Flask(__name__)\nrender_template('index.html')\n", encoding="utf-8")
    (tmp_path / "frontend" / "index.html").write_text("<p>hi</p>", encoding="utf-8")
    repair_project(tmp_path)
    assert (tmp_path / "backend" / "templates" / "index.html").read_text(encoding="utf-8") == "<p>hi</p>"


def test_package_style_app_gets_a_root_launcher(tmp_path):
    from workspace_requirements import repair_project

    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "app.py").write_text("from flask import Flask\nfrom backend.routes import bp\napp = Flask(__name__)\n", encoding="utf-8")
    (tmp_path / "backend" / "routes.py").write_text("bp = 1\n", encoding="utf-8")
    repair_project(tmp_path)
    assert "from backend.app import app" in (tmp_path / "run.py").read_text(encoding="utf-8")
    assert (tmp_path / "backend" / "__init__.py").exists()
