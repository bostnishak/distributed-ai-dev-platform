"""HAL-03 & HAL-05: CLI Eval Runner (`python eval/run.py --suite golden --config baseline`)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "master"))

from hallucination.eval_runner import (  # noqa: E402
    default_grounded_demo_predictor,
    ensure_eval_datasets,
    run_golden_eval,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Hallucination & RAG Evaluation Suite (HAL-03).")
    parser.add_argument("--suite", default="golden", choices=["golden"])
    parser.add_argument("--config", default="baseline")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    ensure_eval_datasets()
    report = run_golden_eval(default_grounded_demo_predictor, config_name=args.config, limit=args.limit)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
