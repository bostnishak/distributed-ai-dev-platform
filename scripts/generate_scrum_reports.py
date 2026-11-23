#!/usr/bin/env python
"""Generate Scrum sprint reports, burndown SVG, and review/retro drafts from real Git & PROGRESS data (PROC-03)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import plan_tool  # noqa: E402


def render_burndown_svg(total: int, completed: int, sprint_label: str = "Sprint 5") -> str:
    remaining = max(0, total - completed)
    width, height = 560, 260
    pad_l, pad_r, pad_t, pad_b = 55, 25, 35, 45
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    max_y = max(1, total)
    actual_y = pad_t + plot_h * (remaining / max_y)
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '  <rect width="100%" height="100%" fill="#ffffff" stroke="#e2e8f0"/>',
            f'  <text x="{pad_l}" y="22" font-family="sans-serif" font-size="14" font-weight="600" fill="#0f172a">'
            f"{sprint_label} Burndown ({completed}/{total} done)</text>",
            f'  <line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t + plot_h}" stroke="#64748b" stroke-width="1.5"/>',
            f'  <line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{pad_l + plot_w}" y2="{pad_t + plot_h}" stroke="#64748b" stroke-width="1.5"/>',
            f'  <line x1="{pad_l}" y1="{pad_t}" x2="{pad_l + plot_w}" y2="{pad_t + plot_h}" '
            'stroke="#94a3b8" stroke-dasharray="6,4" stroke-width="1.5"/>',
            f'  <polyline fill="none" stroke="#0d9488" stroke-width="2.5" '
            f'points="{pad_l},{pad_t} {pad_l + plot_w},{actual_y:.1f}"/>',
            f'  <circle cx="{pad_l + plot_w}" cy="{actual_y:.1f}" r="4" fill="#0d9488"/>',
            f'  <text x="{pad_l}" y="{height - 14}" font-family="sans-serif" font-size="11" fill="#475569">Day 1</text>',
            f'  <text x="{pad_l + plot_w - 40}" y="{height - 14}" font-family="sans-serif" font-size="11" fill="#475569">Day 14</text>',
            f'  <text x="10" y="{pad_t + 5}" font-family="sans-serif" font-size="11" fill="#475569">{total}</text>',
            f'  <text x="20" y="{pad_t + plot_h}" font-family="sans-serif" font-size="11" fill="#475569">0</text>',
            "</svg>",
        ]
    )


def _recent_commits(limit: int = 12) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "log", f"-n{limit}", "--pretty=format:%h %s (%ad)", "--date=short"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
        return [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def generate_reports(plan_dir: Path, out_dir: Path, sprint: str = "Sprint 5") -> dict:
    items, _ = plan_tool.parse_plan(plan_dir)
    progress_path = plan_dir / "PROGRESS.json"
    progress = json.loads(progress_path.read_text(encoding="utf-8")).get("items", {}) if progress_path.is_file() else {}

    total = len(items)
    done = sum(1 for item in items if progress.get(item.id, {}).get("status") == "done")
    open_cnt = total - done

    by_area: dict[str, dict[str, int]] = {}
    for item in items:
        slot = by_area.setdefault(item.area, {"total": 0, "done": 0})
        slot["total"] += 1
        if progress.get(item.id, {}).get("status") == "done":
            slot["done"] += 1

    out_dir.mkdir(parents=True, exist_ok=True)
    svg_path = out_dir / "burndown.svg"
    svg_path.write_text(render_burndown_svg(total, done, sprint), encoding="utf-8")

    commits = _recent_commits()
    area_rows = "\n".join(
        f"| {area} | {counts['done']} | {counts['total']} | {round(100 * counts['done'] / max(1, counts['total']), 1)}% |"
        for area, counts in sorted(by_area.items())
    )
    commit_lines = "\n".join(f"- `{line}`" for line in commits) or "- (no git commits available)"

    report_md = "\n".join(
        [
            f"# {sprint} Progress, Review & Retrospective Draft (PROC-03)",
            "",
            f"Generated at: `{datetime.now(UTC).isoformat(timespec='seconds')}`",
            "",
            "## 1. Evidence-Based Progress Summary",
            f"- Total Plan Items: **{total}**",
            f"- Verified Done (`PROGRESS.json`): **{done}**",
            f"- Remaining Open: **{open_cnt}**",
            "",
            "| Area | Done | Total | Completion |",
            "|---|---|---|---|",
            area_rows,
            "",
            "## 2. Burndown Chart",
            "![Sprint Burndown](burndown.svg)",
            "",
            "## 3. Recent Verified Commits",
            commit_lines,
            "",
            "## 4. Sprint Review & Retrospective Template",
            "- **What went well:** Evidence-gated CI, modular orchestrator/RAG/studio architecture, zero unprotected mutating routes.",
            "- **What to improve:** Live multi-machine Tailscale rehearsals and nightly hardware benchmark tracking.",
            "- **Daily Scrum Template:** (1) Completed since last sync, (2) Next planned item + test, (3) Blockers.",
            "",
        ]
    )
    md_path = out_dir / "sprint-report.md"
    md_path.write_text(report_md, encoding="utf-8")
    return {"total": total, "done": done, "open": open_cnt, "svg": str(svg_path), "report": str(md_path)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-dir", type=Path, default=ROOT / "docs" / "plan-v2")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "scrum" / "reports")
    parser.add_argument("--sprint", default="Sprint 5")
    args = parser.parse_args(argv)
    result = generate_reports(args.plan_dir, args.out_dir, sprint=args.sprint)
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
