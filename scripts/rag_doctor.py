"""RAG-25: CLI health checker and repair tool for the RAG vector + FTS5 index."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "master"))

from rag.api import diagnose_and_repair_rag
from rag.store import default_rag_store


def main() -> int:
    parser = argparse.ArgumentParser(description="RAG index health check and repair utility (RAG-25).")
    parser.add_argument("--repair", action="store_true", help="Remove orphaned, duplicate, and empty-embedding chunks.")
    args = parser.parse_args()
    report = diagnose_and_repair_rag(default_rag_store, repair=args.repair)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["healthy"] or args.repair else 1


if __name__ == "__main__":
    raise SystemExit(main())
