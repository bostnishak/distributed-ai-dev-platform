"""OPS-20: AST Code Quality Gate (<= 150 lines per function, shrinking legacy allowlist)."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

# Shrinking legacy allowlist for pre-existing monoliths (new functions > 150 lines immediately fail CI!)
LEGACY_LONG_FUNCTIONS: frozenset[str] = frozenset({
    "assistant.py:_chat_stream_impl",
    "assistant.py:_prepare_chat_request",
    "assistant.py:assistant_chat",
    "cad_cam_physics.py:analyze_3d_cad_file",
    "cad_cam_physics.py:generate_multi_controller_gcode",
    "cnc_ballooning.py:analyze_technical_drawing",
    "cnc_ballooning.py:export_excel_report",
    "cnc_ballooning.py:parse_cnc_dimension",
    "cnc_ballooning.py:render_ballooned_drawing",
    "cad_kernel.py:analyze_3d_cad_file",
    "code_graph.py:build_workspace_code_graph",
    "deep_research.py:build_pptx_presentation",
    "document_factory.py:generate_document",
    "file_inspector.py:inspect_uploaded_file",
    "gateway/client.py:chat",
    "multimodal_studio.py:generate_image_asset",
    "studio_api.py:iterate_workspace",
    "studios/research.py:run_deep_research",
    "workspace_builder.py:build_workspace_project",
})


def check_function_lengths(master_dir: Path, *, max_lines: int = 150) -> dict[str, Any]:
    new_violations: list[dict[str, Any]] = []
    legacy_present: list[dict[str, Any]] = []
    ignored = {".venv", "venv", "tests", "__pycache__", "node_modules"}
    for pyf in sorted(master_dir.rglob("*.py")):
        if any(part in ignored for part in pyf.parts):
            continue
        try:
            tree = ast.parse(pyf.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
        rel = str(pyf.relative_to(master_dir)).replace("\\", "/")
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                length = (getattr(node, "end_lineno", node.lineno) or node.lineno) - node.lineno + 1
                if length > max_lines:
                    key = f"{rel}:{node.name}"
                    rec = {"function": key, "lines": length}
                    if key in LEGACY_LONG_FUNCTIONS or f"{pyf.name}:{node.name}" in LEGACY_LONG_FUNCTIONS:
                        legacy_present.append(rec)
                    else:
                        new_violations.append(rec)
    return {"passed": len(new_violations) == 0, "new_violations": new_violations, "legacy_count": len(legacy_present)}


if __name__ == "__main__":
    res = check_function_lengths(Path(__file__).resolve().parents[1] / "master")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    raise SystemExit(0 if res["passed"] else 1)
