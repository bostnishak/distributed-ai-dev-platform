"""Generated projects get a requirements.txt that pip can install."""

import pytest

from workspace_requirements import fix_requirements, repair_project

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


def test_external_database_url_becomes_sqlite(tmp_path):
    from workspace_requirements import repair_project

    (tmp_path / "config.py").write_text("URI = os.environ.get('DB') or 'postgresql://user:pw@localhost/todo'\n", encoding="utf-8")
    repair_project(tmp_path)
    assert "sqlite:///app.db" in (tmp_path / "config.py").read_text(encoding="utf-8")


def test_asset_links_point_to_flask_static(tmp_path):
    from workspace_requirements import repair_project

    (tmp_path / "backend" / "templates").mkdir(parents=True)
    (tmp_path / "frontend" / "css").mkdir(parents=True)
    (tmp_path / "frontend" / "css" / "styles.css").write_text("body{}", encoding="utf-8")
    (tmp_path / "backend" / "templates" / "index.html").write_text('<link rel="stylesheet" href="/css/styles.css">', encoding="utf-8")
    repair_project(tmp_path)
    assert "/static/css/styles.css" in (tmp_path / "backend" / "templates" / "index.html").read_text(encoding="utf-8")
    assert (tmp_path / "backend" / "static" / "css" / "styles.css").exists()


def test_js_fetch_without_matching_route_is_reported(tmp_path):
    from workspace_contract import contract_problem

    (tmp_path / "app.js").write_text("fetch('/api/tasks'); fetch(`/tasks/tasks/${id}`)", encoding="utf-8")
    found = contract_problem(tmp_path, ["/tasks/tasks", "/tasks/tasks/<int:id>", "/static/<path:filename>"])
    assert found and "/api/tasks" in found[1]
    assert contract_problem(tmp_path, ["/api/tasks", "/tasks/tasks/<int:id>"]) is None


def test_tables_are_created_outside_main_guard(tmp_path):
    (tmp_path / "app.py").write_text(
        "from flask import Flask\nfrom models import db\napp = Flask(__name__)\ndb.init_app(app)\n\nif __name__ == '__main__':\n    with app.app_context():\n        db.create_all()\n    app.run()\n",
        encoding="utf-8",
    )
    repair_project(tmp_path)
    head = (tmp_path / "app.py").read_text(encoding="utf-8").split("if __name__")[0]
    assert "db.create_all()" in head


def test_static_refs_are_not_nested_on_repeat(tmp_path):
    (tmp_path / "templates").mkdir()
    (tmp_path / "static" / "css").mkdir(parents=True)
    (tmp_path / "static" / "css" / "a.css").write_text("x{}", encoding="utf-8")
    (tmp_path / "templates" / "i.html").write_text('<link rel="stylesheet" href="/static/css/a.css">', encoding="utf-8")
    for _ in range(3):
        repair_project(tmp_path)
    assert not (tmp_path / "static" / "static").exists()
