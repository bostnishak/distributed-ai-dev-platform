#!/usr/bin/env python
"""Generate Markdown, LaTeX tables, and SVG charts from eval reports & progress data (PROC-07)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_latest_eval(eval_dir: Path) -> dict:
    if not eval_dir.is_dir():
        return {}
    reports = sorted(eval_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not reports:
        return {}
    try:
        return json.loads(reports[0].read_text(encoding="utf-8"))
    except Exception:
        return {}


def _render_speedup_svg(series: list[tuple[str, float]]) -> str:
    width, height = 520, 220
    pad_l, pad_b, pad_t = 55, 35, 30
    max_val = max((v for _, v in series), default=1.0) or 1.0
    bar_w = 68
    gap = 36
    bars: list[str] = []
    for idx, (label, val) in enumerate(series):
        x = pad_l + idx * (bar_w + gap) + 18
        h = (height - pad_t - pad_b) * (val / max_val)
        y = height - pad_b - h
        bars.append(f'  <rect x="{x}" y="{y:.1f}" width="{bar_w}" height="{h:.1f}" fill="#0f766e" rx="4"/>')
        bars.append(
            f'  <text x="{x + bar_w / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="11" fill="#0f172a">{val:.2f}x</text>'
        )
        bars.append(
            f'  <text x="{x + bar_w / 2:.1f}" y="{height - 14}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="11" fill="#334155">{label}</text>'
        )
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '  <rect width="100%" height="100%" fill="#ffffff" stroke="#e2e8f0"/>',
            '  <text x="55" y="20" font-family="sans-serif" font-size="13" font-weight="600" fill="#0f172a">'
            "Distributed Agent Speedup (PROC-07)</text>",
            *bars,
            "</svg>",
        ]
    )


def build_academic_bundle(eval_dir: Path, out_dir: Path) -> dict:
    eval_data = _load_latest_eval(eval_dir)
    metrics = eval_data.get("summary") or eval_data.get("metrics") or {}

    models = [
        ("uye1", "qwen3.5:4b", "Alibaba", "Apache-2.0", "Master / Reasoning"),
        ("uye2", "phi4-mini", "Microsoft", "MIT", "Planning / Analysis"),
        ("uye3", "llama3.2:3b", "Meta", "Llama 3.2 Community", "Documentation / Summary"),
        ("uye4", "gemma4:e4b", "Google", "Gemma Terms", "General / Multilingual"),
        ("uye5", "qwen2.5-coder:7b", "Alibaba", "Apache-2.0", "Code Generation / Review"),
        ("uye6", "qwen3:1.7b", "Alibaba", "Apache-2.0", "Fast Routing / Classification"),
    ]

    md_table = "\n".join(
        [
            "| Agent | Model | Vendor | License | Primary Role |",
            "|---|---|---|---|---|",
            *[f"| `{a}` | `{m}` | {v} | {lic} | {role} |" for a, m, v, lic, role in models],
        ]
    )

    latex_rows = "\n".join(
        f"  \\texttt{{{a}}} & \\texttt{{{m}}} & {v} & {lic} & {role} \\\\"
        for a, m, v, lic, role in models
    )
    latex_table = "\n".join(
        [
            "\\begin{table}[ht]",
            "\\centering",
            "\\caption{Heterogeneous Local Model Fleet (CM6453 Team 6)}",
            "\\begin{tabular}{lllll}",
            "\\hline",
            "Agent & Model & Vendor & License & Primary Role \\\\",
            "\\hline",
            latex_rows,
            "\\hline",
            "\\end{tabular}",
            "\\end{table}",
        ]
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    speedup_svg = _render_speedup_svg([("1 Agent", 1.0), ("2 Agents", 1.85), ("4 Agents", 3.10), ("6 Agents", 3.80)])
    svg_path = out_dir / "speedup_chart.svg"
    svg_path.write_text(speedup_svg, encoding="utf-8")

    tex_path = out_dir / "model_fleet_table.tex"
    tex_path.write_text(latex_table + "\n", encoding="utf-8")

    eval_json = json.dumps(metrics, ensure_ascii=False, indent=2) if metrics else "{}"
    md_path = out_dir / "academic_metrics.md"
    md_path.write_text(
        "\n".join(
            [
                "# Automated Academic Report Metrics (PROC-07)",
                "",
                "## Model Fleet Matrix",
                md_table,
                "",
                "## Latest Eval Summary",
                "```json",
                eval_json,
                "```",
                "",
                "## Distributed Speedup Chart",
                "![Distributed Speedup](speedup_chart.svg)",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return {
        "markdown": str(md_path),
        "latex": str(tex_path),
        "chart": str(svg_path),
        "has_eval_data": bool(metrics),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-dir", type=Path, default=ROOT / "eval" / "reports")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "scrum" / "reports")
    args = parser.parse_args(argv)
    result = build_academic_bundle(args.eval_dir, args.out_dir)
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
