"""Synthetic CNC Technical Drawing & Ground-Truth Ballooning Dataset Generator.

Generates randomized vector CNC drawings (PNG + PDF) with exact ground-truth normalized
coordinates and writes a ShareGPT / Qwen-VL compatible JSONL dataset for QLoRA fine-tuning.

Usage:
    python training/cnc_ballooning/generate_synthetic_dataset.py --count 50 --out training/cnc_ballooning/data
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

import fitz  # PyMuPDF

MATERIALS = ["AISI 4140 STEEL", "AL 6061-T6", "AISI 304 STAINLESS", "C45 CARBON STEEL", "7075-T651 AL"]
FITS = ["H7", "H8", "h6", "g6", "k6"]
THREADS = ["M6x1.0-6H", "M8x1.25-6H", "M10x1.5-6H", "M12x1.75-6H"]
ROUGHNESS = ["Ra 0.4", "Ra 0.8", "Ra 1.6", "Ra 3.2"]
GDTS = ["⏥ 0.02", "⊥ 0.03 A", "◎ 0.02 A", "∥ 0.03 B", "↗ 0.02 A"]


def generate_one(idx: int, out_dir: Path, rng: random.Random) -> dict:
    doc = fitz.open()
    page = doc.new_page(width=842, height=595)
    navy = (0.08, 0.12, 0.2)
    dim_col = (0.12, 0.28, 0.55)
    center_col = (0.75, 0.15, 0.15)

    page.draw_rect(fitz.Rect(18, 18, 824, 577), color=navy, width=1.5)
    part_no = f"CNC-SYN-{idx:04d}"
    mat = rng.choice(MATERIALS)
    rev = rng.choice(["A", "B", "C"])

    outer_d = rng.choice([80, 90, 100, 110, 120, 140])
    pcd_d = int(outer_d * 0.72)
    bore_d = rng.choice([25, 30, 35, 40, 42, 50])
    fit = rng.choice(FITS)
    n_holes = rng.choice([4, 6, 8])
    hole_d = rng.choice([6.6, 8.5, 9.0, 11.0])
    thread = rng.choice(THREADS)
    total_len = rng.choice([24.0, 30.0, 36.0, 42.0, 48.0])
    flange_t = rng.choice([10.0, 12.0, 14.0, 16.0])
    chamfer = rng.choice(["1.5x45°", "2x45°", "C2", "C1.5"])
    ra1 = rng.choice(ROUGHNESS[:2])
    ra2 = rng.choice(ROUGHNESS[2:])
    gdt1, gdt2 = rng.sample(GDTS, 2)

    cx, cy = 245, 290
    page.draw_circle((cx, cy), 125, color=navy, width=1.8)
    page.draw_circle((cx, cy), 92, color=center_col, width=0.7, dashes="[5 3]")
    page.draw_circle((cx, cy), 46, color=navy, width=1.8)
    for k in range(n_holes):
        ang = math.radians(360 * k / n_holes + 45)
        page.draw_circle((cx + 92 * math.cos(ang), cy + 92 * math.sin(ang)), 9, color=navy, width=1.2)

    sx, sy = 575, 290
    page.draw_rect(fitz.Rect(sx - 55, sy - 125, sx - 15, sy + 125), color=navy, width=1.8)
    page.draw_rect(fitz.Rect(sx - 15, sy - 62, sx + 55, sy + 62), color=navy, width=1.8)

    callouts = [
        (cx - 52 + rng.randint(-8, 8), cy - 142, f"Ø{outer_d} ±0.05"),
        (cx + 76, cy - 118, f"Ø{pcd_d} ±0.03"),
        (cx - 34, cy - 6, f"Ø{bore_d} {fit}"),
        (cx + 70, cy + 88, f"{n_holes}x Ø{hole_d:g} THRU"),
        (cx - 148, cy + 114, f"{n_holes}x {thread}"),
        (sx - 28, sy - 150, f"{total_len:.1f} ±0.05"),
        (sx - 58, sy + 158, f"{flange_t:.1f} ±0.05"),
        (sx + 62, sy - 86, chamfer),
        (sx + 62, sy + 86, ra1),
        (sx - 118, sy - 88, ra2),
        (sx + 58, sy - 120, gdt1),
        (sx + 58, sy + 122, gdt2),
    ]

    gt_balloons = []
    for x, y, txt in callouts:
        page.insert_text((x, y), txt, fontsize=10, color=dim_col)
        gt_balloons.append({
            "raw_text": txt,
            "x_pct": round((x + len(txt) * 2.8) / 842.0 * 100.0, 2),
            "y_pct": round((y - 3.5) / 595.0 * 100.0, 2),
        })

    # Title block
    page.draw_rect(fitz.Rect(525, 470, 818, 571), color=navy, fill=(0.97, 0.98, 1.0), width=1.2)
    page.insert_text((533, 490), f"PART NO: {part_no}  REV: {rev}", fontsize=9, color=navy)
    page.insert_text((533, 515), f"MATERIAL: {mat}", fontsize=8.5, color=navy)
    page.insert_text((533, 540), "TOLERANCE: ISO 2768-mK  UNIT: MM", fontsize=8.5, color=navy)

    img_dir = out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    img_path = img_dir / f"{part_no}.png"
    page.get_pixmap(dpi=180).save(str(img_path))
    doc.close()

    gt_json = {
        "metadata": {
            "part_number": part_no,
            "part_name": "CNC Bearing Flange",
            "material": mat,
            "revision": rev,
            "standard": "ISO 2768-mK",
        },
        "balloons": gt_balloons,
    }
    return {
        "image": str(img_path.as_posix()),
        "messages": [
            {
                "role": "user",
                "content": "Bu CNC teknik çizimdeki tüm ölçüleri, toleransları, dişleri, yüzey pürüzlülüklerini ve GD&T sembollerini eksiksiz balonla ve JSON olarak döndür.",
            },
            {
                "role": "assistant",
                "content": json.dumps(gt_json, ensure_ascii=False),
            },
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--out", type=Path, default=Path("training/cnc_ballooning/data"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    args.out.mkdir(parents=True, exist_ok=True)
    jsonl_path = args.out / "dataset.jsonl"

    with jsonl_path.open("w", encoding="utf-8") as fh:
        for i in range(1, args.count + 1):
            rec = generate_one(i, args.out, rng)
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Generated {args.count} synthetic CNC drawings & ground-truth records at {jsonl_path}")


if __name__ == "__main__":
    main()
