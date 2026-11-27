"""Static diagnostics, input-to-sink data flow, query performance and licence checks."""

import pytest

import code_audit

pytestmark = pytest.mark.unit


def _src(*lines):
    return "\n".join(lines) + "\n"


def test_user_input_reaching_sql_text_is_found_but_bound_parameters_are_not():
    bad = _src("def find(cur):", "    name = input()", "    q = 'select * from t where n=' + name", "    cur.execute(q)")
    safe = _src("def find(cur):", "    name = input()", "    cur.execute('select * from t where n=?', (name,))")
    converted = _src("def find(cur):", "    n = int(input())", "    cur.execute(f'select * from t where id={n}')")
    assert code_audit.flows(bad) == [(4, "SQL")]
    assert code_audit.flows(safe) == [] and code_audit.flows(converted) == []


def test_route_parameter_is_input_unless_typed_as_a_number():
    app = _src("@app.get('/a/{name}')", "def a(name: str):", "    os.system('echo ' + name)", "@app.get('/b/{n}')", "def b(n: int):", "    os.system(f'echo {n}')")
    assert code_audit.flows(app) == [(3, "kabuk")]


def test_query_per_row_and_missing_index(tmp_path):
    code = _src(
        "SCHEMA = 'CREATE TABLE orders (id INTEGER PRIMARY KEY, customer TEXT)'",
        "def load(cur, ids):",
        "    for i in ids:",
        "        cur.execute('SELECT * FROM orders WHERE id=?', (i,))",
        "    cur.execute(\"SELECT * FROM orders WHERE customer=?\", ('a',))",
    )
    (tmp_path / "db.py").write_text(code, encoding="utf-8")
    assert code_audit.loops_with_queries(code) == [4]
    scans = code_audit.full_scans(tmp_path)
    assert len(scans) == 1 and "db.py:5" in scans[0]


def test_undefined_name_is_a_diagnostic(tmp_path):
    pytest.importorskip("ruff")
    (tmp_path / "a.py").write_text(_src("def f():", "    return missing_name"), encoding="utf-8")
    assert any("F821" in line for line in code_audit.diagnostics(tmp_path))


def test_copyleft_dependency_conflicts_with_an_mit_request(tmp_path):
    (tmp_path / "requirements.txt").write_text("gpl-lib\nok-lib\n", encoding="utf-8")
    licences = {"gpl-lib": "GPL-3.0", "ok-lib": "MIT"}
    found = code_audit.licence_conflicts(tmp_path, "MIT lisanslı bir araç yap", lambda _r, n: licences[n])
    assert len(found) == 1 and "gpl-lib" in found[0]
    assert code_audit.licence_conflicts(tmp_path, "bir araç yap", lambda _r, n: licences[n]) == []
