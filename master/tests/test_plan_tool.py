"""scripts/plan_tool.py: the plan is internally consistent and progress can only be proven, not claimed."""

import importlib.util
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "plan_tool.py"
spec = importlib.util.spec_from_file_location("plan_tool", SCRIPT)
pt = importlib.util.module_from_spec(spec)
sys.modules["plan_tool"] = pt
spec.loader.exec_module(pt)


def item(item_id, deps="-", status="açık", problem="[ÖNERİ] sorun", effort="S"):
    return (
        f"#### {item_id} · Başlık {item_id}\n"
        f"- **Sorun:** {problem}\n- **Değişiklik:** değişiklik\n- **Kabul:** kabul\n"
        f"- **Meta:** P1 · {effort} · Bağ: {deps} · Durum: {status}\n\n"
    )


def write_plan(tmp_path, *items, extra=""):
    (tmp_path / "01-test.md").write_text("# Test\n\n" + "".join(items) + extra, encoding="utf-8")
    return tmp_path


def errors_for(plan_dir):
    items, parse_errors = pt.parse_plan(plan_dir)
    return parse_errors + pt.validate(items, set()) + pt.validate_prose_references(plan_dir, items)


def test_real_plan_is_consistent_and_large_enough():
    items, parse_errors = pt.parse_plan(pt.PLAN_DIR)
    findings = pt.read_findings(pt.PLAN_DIR / "README.md")
    phases = pt.load_phases(pt.PLAN_DIR / "phases.json")
    mvp = pt.load_mvp(pt.PLAN_DIR / "phases.json")
    errors = parse_errors + pt.validate(items, findings) + pt.validate_prose_references(pt.PLAN_DIR, items)
    errors += pt.validate_phases(items, phases)
    blocks = pt.render_blocks(items, phases, mvp)
    for path in pt.PLAN_DIR.glob("*.md"):
        errors += [f"{path.name}: {name}" for name in pt.stale_blocks(path.read_text(encoding="utf-8"), blocks)]
    assert errors == []
    assert len(items) >= 200


def test_duplicate_ids_are_reported(tmp_path):
    plan = write_plan(tmp_path, item("AA-01"), item("AA-01"))
    assert any("yinelenen kimlik" in e for e in errors_for(plan))


def test_numbering_must_be_sequential_per_area(tmp_path):
    plan = write_plan(tmp_path, item("AA-01"), item("AA-03"))
    assert any("ardışık" in e for e in errors_for(plan))


def test_plan_files_cannot_declare_an_item_finished(tmp_path):
    plan = write_plan(tmp_path, item("AA-01", status="tamamlandı"))
    assert any("durum bildiremez" in e for e in errors_for(plan))


def test_item_without_evidence_tag_or_bullets_is_rejected(tmp_path):
    plan = write_plan(tmp_path, item("AA-01", problem="etiketsiz sorun"))
    assert any("[DOĞRULANDI] veya [ÖNERİ]" in e for e in errors_for(plan))
    (tmp_path / "01-test.md").write_text("#### AA-01 · Eksik\n- **Sorun:** [ÖNERİ] x\n", encoding="utf-8")
    assert any("eksik" in e for e in errors_for(tmp_path))


def test_unknown_dependency_and_cycles_are_reported(tmp_path):
    plan = write_plan(tmp_path, item("AA-01", deps="AA-09"), item("AA-02", deps="AA-03"), item("AA-03", deps="AA-02"))
    errors = errors_for(plan)
    assert any("bilinmeyen bağımlılık 'AA-09'" in e for e in errors)
    assert any("döngü" in e and "AA-02" in e and "AA-03" in e for e in errors)


def test_prose_reference_to_a_missing_item_is_reported(tmp_path):
    plan = write_plan(tmp_path, item("AA-01"), extra="Bu madde AA-07 ile ilgilidir.\n")
    assert any("'AA-07'" in e for e in errors_for(plan))


def test_findings_must_exist_in_the_readme(tmp_path):
    plan = write_plan(tmp_path, item("AA-01", problem="[DOĞRULANDI: F9] sorun"))
    items, _ = pt.parse_plan(plan)
    assert any("'F9'" in e for e in pt.validate(items, {"F1"}))
    assert pt.validate(items, {"F9"}) == []


def test_done_status_needs_tests_and_commit_evidence(tmp_path):
    items, _ = pt.parse_plan(write_plan(tmp_path, item("AA-01"), item("AA-02")))
    claimed = {"items": {"AA-01": {"status": "done", "evidence": {"tests": [], "commit": ""}}}}
    merged, errors = pt.merge_progress(items, claimed)
    assert merged["items"]["AA-01"]["status"] == "claimed_without_evidence"
    assert merged["items"]["AA-02"]["status"] == "open"
    assert errors
    proven = {"items": {"AA-01": {"status": "done", "evidence": {"tests": ["t::x"], "commit": "abc1234"}}}}
    merged, errors = pt.merge_progress(items, proven)
    assert merged["items"]["AA-01"]["status"] == "done" and errors == []


def test_phase_assignment_must_respect_prerequisites_and_cover_every_item(tmp_path):
    items, _ = pt.parse_plan(write_plan(tmp_path, item("AA-01"), item("AA-02", deps="AA-01"), item("AA-03")))
    wrong_order = [{"id": 0, "name": "a", "weeks": "1-2", "items": ["AA-02"]},
                   {"id": 1, "name": "b", "weeks": "3-4", "items": ["AA-01"]}]
    errors = pt.validate_phases(items, wrong_order)
    assert any("ön koşulu AA-01 daha geç fazda" in e for e in errors)
    assert any("AA-03: hiçbir faza atanmamış" in e for e in errors)
    good = [{"id": 0, "name": "a", "weeks": "1-2", "items": ["AA-01", "AA-03"]},
            {"id": 1, "name": "b", "weeks": "3-4", "items": ["AA-02"]}]
    assert pt.validate_phases(items, good) == []


def test_generated_blocks_cannot_go_stale(tmp_path):
    items, _ = pt.parse_plan(write_plan(tmp_path, item("AA-01"), item("AA-02", deps="AA-01")))
    blocks = pt.render_blocks(items, [], [])
    text = "x\n<!-- summary:begin -->\nel yazısı\n<!-- summary:end -->\n"
    assert pt.stale_blocks(text, blocks) == ["summary"]
    assert pt.stale_blocks(pt.apply_blocks(text, blocks), blocks) == []


def test_critical_path_and_closure_follow_dependencies(tmp_path):
    items, _ = pt.parse_plan(write_plan(tmp_path, item("AA-01", effort="L"), item("AA-02", deps="AA-01"),
                                        item("AA-03", deps="AA-02"), item("AA-04")))
    chain, days = pt.critical_path(items)
    assert chain == ["AA-01", "AA-02", "AA-03"] and days == 7 + 0.5 + 0.5
    assert pt.closure(items, ["AA-03"]) == {"AA-01", "AA-02", "AA-03"}


def make_master(tmp_path):
    (tmp_path / "app.py").write_text("import used\nSTART = 1\n", encoding="utf-8")
    (tmp_path / "used.py").write_text("def f():\n    import lazy\n", encoding="utf-8")
    (tmp_path / "lazy.py").write_text("X = 1\n", encoding="utf-8")
    (tmp_path / "dead.py").write_text("import lazy\nVALUE = 2\n", encoding="utf-8")
    (tmp_path / "facade.py").write_text('"""Re-export."""\nfrom lazy import X\n__all__ = ["X"]\n', encoding="utf-8")
    return tmp_path


def test_unreachable_modules_include_lazy_imports_as_reachable(tmp_path):
    master = make_master(tmp_path)
    assert pt.unreachable_modules(master) == ["dead", "facade"]
    assert pt.facade_modules(master) == ["facade"]


def test_wiring_gate_fails_only_for_new_dead_modules(tmp_path):
    (tmp_path / "master").mkdir()
    master = make_master(tmp_path / "master")
    plan = tmp_path / "plan"
    plan.mkdir()
    base = ["--plan-dir", str(plan), "--master-dir", str(master)]
    assert pt.main([*base, "wiring", "--write-allowlist"]) == 0
    assert pt.main([*base, "wiring", "--fail-on-new"]) == 0
    (master / "newdead.py").write_text("Y = 2\n", encoding="utf-8")
    assert pt.main([*base, "wiring", "--fail-on-new"]) == 1


def test_command_line_exit_codes(tmp_path):
    plan = write_plan(tmp_path, item("AA-01"), item("AA-02", deps="AA-01"))
    (plan / "phases.json").write_text(json.dumps({"phases": [
        {"id": 0, "name": "a", "weeks": "1-2", "items": ["AA-01", "AA-02"]}]}), encoding="utf-8")
    assert pt.main(["--plan-dir", str(plan), "render"]) == 0
    assert pt.main(["--plan-dir", str(plan), "check"]) == 0
    assert pt.main(["--plan-dir", str(plan), "status"]) == 0
    write_plan(tmp_path, item("AA-01", deps="AA-01"))
    assert pt.main(["--plan-dir", str(plan), "check"]) == 1
