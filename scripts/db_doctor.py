#!/usr/bin/env python
"""DAT-12: CLI wrapper for database integrity diagnostics and safe repairs (scripts/db_doctor.py)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "master"))

import config  # noqa: E402
import db_doctor  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(config.DB_PATH), help="Path to SQLite database")
    parser.add_argument("--repair", action="store_true", help="Apply safe, lossless repairs before final check")
    parser.add_argument("--json", dest="as_json", action="store_true", help="Emit JSON output")
    args = parser.parse_args(argv)

    actions = db_doctor.repair(args.db) if args.repair else []
    findings = db_doctor.diagnose(args.db)
    has_error = any(f.severity == "error" for f in findings)

    if args.as_json:
        payload = {
            "db": str(args.db),
            "ok": not has_error,
            "repairs": actions,
            "findings": [{"severity": f.severity, "check": f.check, "detail": f.detail} for f in findings],
        }
        sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    else:
        for act in actions:
            print(f"REPAIR: {act}")
        for f in findings:
            print(str(f))
        if not findings:
            print(f"OK: {args.db} passed all integrity checks.")
    return 1 if has_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
