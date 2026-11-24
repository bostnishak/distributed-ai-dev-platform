"""ENT-04: Command-line client (dadp-cli) for querying health, models, RAG, and tools."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sdk.dadp_sdk import DadpClient


def main() -> int:
    parser = argparse.ArgumentParser(prog="dadp-cli", description="Distributed AI Platform CLI client")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--admin-token", default="")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health")
    sub.add_parser("ready")
    sub.add_parser("models")
    p_rag = sub.add_parser("search")
    p_rag.add_argument("query")
    args = parser.parse_args()

    client = DadpClient(base_url=args.base_url, admin_token=args.admin_token)
    if args.cmd == "health":
        out = client.health()
    elif args.cmd == "ready":
        out = client.ready()
    elif args.cmd == "models":
        out = client.list_models()
    else:
        out = client.rag_search(args.query)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
