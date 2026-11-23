"""Cluster B (`[M23]`, Faz 6.2): 5-Stage Autonomous Software Factory Pipeline.

Combines:
1. Stage 1 (Blueprint & Archetype Validation): `project_archetypes`
2. Stage 2 (AST Symbol & Dependency Graph Analysis): `code_graph.build_workspace_code_graph`
3. Stage 3 (Smoke Check & Security Audit): `self_healing_runner.run_workspace_smoke_check`
4. Stage 4 (Visual / Web DOM Verification): `visual_verifier.verify_web_workspace_ui`
5. Stage 5 (Autonomous Self-Healing & Re-Verification): `visual_verifier.auto_fix_web_ui_issues`
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import code_graph
import project_archetypes
import self_healing_runner
import visual_verifier


def _infer_workspace_archetype(ws_dir: Path, files: list[str]) -> str:
    file_set = set(files)
    if "game.js" in file_set:
        return "game_2d"
    if "app_gui.py" in file_set:
        return "desktop_exe"
    if "cli.py" in file_set:
        return "cli_automation"
    if "pipeline.py" in file_set and "metrics.py" in file_set:
        return "data_science_ml"
    if any(f.endswith(".py") for f in file_set) and any(f.endswith(".html") for f in file_set):
        return "fullstack_fastapi"
    if any(f.endswith(".html") for f in file_set):
        return "web_ecommerce"
    return project_archetypes.detect_archetype(ws_dir.name)


def run_autonomous_software_factory(ws_dir: Path) -> dict[str, Any]:
    """Execute the 5-stage autonomous software production and verification pipeline on `ws_dir`."""
    ws_dir = Path(ws_dir).resolve()
    ws_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1: Archetype & Blueprint Inspection (seed starter files if workspace is empty)
    existing_files = [
        p.relative_to(ws_dir).as_posix()
        for p in sorted(ws_dir.rglob("*"))
        if p.is_file() and not any(part in code_graph.IGNORED_DIRS for part in p.parts)
    ]
    archetype_id = _infer_workspace_archetype(ws_dir, existing_files)
    blueprint = project_archetypes.get_archetype_blueprint(archetype_id, project_name=ws_dir.name)

    seeded_files: list[str] = []
    if not existing_files:
        for rel_path, content in blueprint["files"].items():
            target = ws_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            seeded_files.append(rel_path)

    stage1_blueprint = {
        "stage": 1,
        "name": "archetype_blueprint",
        "archetype": archetype_id,
        "required_files": blueprint["required_files"],
        "seeded_files": seeded_files,
    }

    # Stage 2: Workspace Code Graph & Cross-File Dependency Analysis
    graph = code_graph.build_workspace_code_graph(ws_dir)
    stage2_code_graph = {
        "stage": 2,
        "name": "code_graph_analysis",
        "node_count": len(graph.get("nodes", [])),
        "edge_count": len(graph.get("edges", [])),
        "broken_references": graph.get("broken_references", []),
    }

    # Stage 3: Smoke Check & Security Audit
    smoke = self_healing_runner.run_workspace_smoke_check(ws_dir)
    stage3_smoke_check = {
        "stage": 3,
        "name": "smoke_and_security_check",
        "ok": smoke["ok"],
        "errors": smoke["errors"],
        "security": smoke["security"],
    }

    # Stage 4: Web UI & DOM Visual Verification
    ui_report = visual_verifier.verify_web_workspace_ui(ws_dir)
    stage4_visual_verification = {
        "stage": 4,
        "name": "visual_ui_verification",
        "ok": ui_report["ok"],
        "total_issues": ui_report["total_issues"],
        "report": ui_report,
    }

    # Stage 5: Self-Healing & Final Gate
    healing_result: dict[str, Any] = {"fixes_applied": []}
    if not ui_report["ok"]:
        healing_result = visual_verifier.auto_fix_web_ui_issues(ws_dir)
        ui_report = healing_result["verification"]
        smoke = self_healing_runner.run_workspace_smoke_check(ws_dir)

    stage5_self_healing = {
        "stage": 5,
        "name": "autonomous_self_healing",
        "fixes_applied": healing_result.get("fixes_applied", []),
        "final_ui_ok": ui_report["ok"],
        "final_smoke_ok": smoke["ok"],
    }

    overall_ok = bool(smoke["ok"] and ui_report["ok"] and smoke["security"]["ok"])
    return {
        "workspace": str(ws_dir),
        "archetype": archetype_id,
        "ok": overall_ok,
        "stages": [
            stage1_blueprint,
            stage2_code_graph,
            stage3_smoke_check,
            stage4_visual_verification,
            stage5_self_healing,
        ],
        "code_graph": graph,
        "smoke_check": smoke,
        "ui_verification": ui_report,
    }
