"""CLI runner for the 300-sample Turkish benchmark and multi-agent Amdahl speedup report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "master"))


def main(argv: list[str] | None = None) -> int:
    from eval_studio import run_turkish_benchmark_suite

    parser = argparse.ArgumentParser(description="DADP Türkçe Benchmark & Çoklu Ajan Amdahl Raporlayıcı")
    parser.add_argument("--limit", type=int, default=300)
    args = parser.parse_args(argv)
    report = run_turkish_benchmark_suite(limit=args.limit)
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
