"""API fuzzing, dependency existence check and mutation testing."""

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

import mutation
import package_check

pytestmark = pytest.mark.unit
_PROBE = (Path(__file__).resolve().parent.parent / "prompts" / "api_probe.py.txt").read_text(encoding="utf-8")


def _probe():
    scope: dict = {}
    exec(compile(_PROBE, "api_probe", "exec"), scope)  # noqa: S102, RUF100
    return scope


def test_fuzzing_finds_a_crash_the_happy_path_misses():
    from fastapi import FastAPI
    from pydantic import BaseModel

    class Item(BaseModel):
        name: str

    app = FastAPI()

    @app.post("/items")
    def create(item: Item):
        return {"first": item.name.split()[0]}  # crashes on an empty or blank name

    with pytest.raises(Exception, match="index"):
        _probe()["check_fastapi"](app)


def test_fuzzing_passes_a_defensive_api():
    from fastapi import FastAPI
    from pydantic import BaseModel, Field

    class Item(BaseModel):
        name: str = Field(min_length=1, max_length=50, pattern=r"\S")

    app = FastAPI()

    @app.post("/items")
    def create(item: Item):
        return {"first": item.name.split()[0]}

    _probe()["check_fastapi"](app)


def test_invented_and_brand_new_packages_are_reported(tmp_path):
    (tmp_path / "requirements.txt").write_text("fastapi>=0.1\nfastapi-magic-orm\nfresh\n# yorum\n", encoding="utf-8")

    def lookup(registry, name):
        stamp = "2026-11-20T00:00:00Z" if name == "fresh" else "2019-01-01T00:00:00Z"
        return None if name == "fastapi-magic-orm" else {"releases": {"1": [{"upload_time_iso_8601": stamp}]}}

    found = package_check.check(tmp_path, lookup, datetime(2026, 11, 27, tzinfo=UTC))
    assert len(found) == 2 and "fastapi-magic-orm" in found[0] and "7 günlük" in found[1]


def test_unreachable_registry_is_said_not_passed(tmp_path):
    (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")

    def lookup(registry, name):
        raise OSError("offline")

    assert "doğrulanmadı" in package_check.check(tmp_path, lookup)[0]


@pytest.mark.parametrize(("test_body", "all_killed"), [
    ("assert grade(50) == 'pass' and grade(49) == 'fail'", True),
    ("grade(80)", False),
])
def test_mutation_score_separates_real_tests_from_vanity_tests(tmp_path, test_body, all_killed):
    logic = "\n".join(["def grade(score):", "    if score >= 50:", "        return 'pass'", "    return 'fail'", ""])
    (tmp_path / "logic.py").write_text(logic, encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_logic.py").write_text("\n".join(["from logic import grade", test_body, ""]), encoding="utf-8")

    def runs_ok(stage):
        code = "import sys; sys.path.insert(0, '.'); exec(open('tests/test_logic.py').read())"
        return subprocess.run([sys.executable, "-B", "-c", code], cwd=stage, capture_output=True, timeout=30).returncode == 0

    tried, survived = mutation.run(tmp_path, runs_ok)
    assert tried >= 3 and (not survived) == all_killed
    assert (tmp_path / "logic.py").read_text(encoding="utf-8") == logic  # the project folder is never modified


@pytest.mark.parametrize(("store", "remove", "error"), [(True, True, None), (False, True, "does not list"), (True, False, "still lists")])
def test_stateful_check_follows_create_and_delete(store, remove, error):
    from fastapi import FastAPI
    from pydantic import BaseModel, Field

    class Note(BaseModel):
        title: str = Field(max_length=100)

    app = FastAPI()
    rows: dict[int, str] = {}

    @app.post("/notes")
    def create(note: Note):
        key = len(rows) + 1
        if store:
            rows[key] = note.title
        return {"id": key}

    @app.get("/notes")
    def every():
        return list(rows.values())

    @app.delete("/notes/{key}")
    def delete(key: int):
        if remove:
            rows.pop(key, None)
        return {"ok": True}

    if error is None:
        _probe()["check_fastapi"](app)
    else:
        with pytest.raises(RuntimeError, match=error):
            _probe()["check_fastapi"](app)


def test_a_loop_without_an_exit_is_found():
    import flowchart_studio

    steps = [{"id": i, "type": t, "label": i} for i, t in (("a", "start"), ("b", "decision"), ("c", "process"), ("d", "process"), ("e", "end"))]
    edges = [{"from": a, "to": b} for a, b in (("a", "b"), ("b", "e"), ("b", "c"), ("c", "d"), ("d", "c"))]
    assert flowchart_studio.stuck_steps({"steps": steps, "edges": edges}) == ["c", "d"]
    assert flowchart_studio.stuck_steps({"steps": steps, "edges": [*edges, {"from": "d", "to": "e"}]}) == []
