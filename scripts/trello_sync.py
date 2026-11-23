#!/usr/bin/env python
"""Plan-to-Backlog mapping and idempotent one-way Trello sync (PROC-02).

Credentials are read strictly from environment variables (TRELLO_API_KEY,
TRELLO_TOKEN, TRELLO_BOARD_ID). Never store secrets in this repository.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import plan_tool  # noqa: E402


def build_backlog_cards(plan_dir: Path, priority_filter: str | None = None) -> list[dict]:
    items, _ = plan_tool.parse_plan(plan_dir)
    progress_path = plan_dir / "PROGRESS.json"
    progress = json.loads(progress_path.read_text(encoding="utf-8")).get("items", {}) if progress_path.is_file() else {}
    cards: list[dict] = []
    for idx, item in enumerate(items, start=1):
        if priority_filter and item.priority != priority_filter:
            continue
        state = progress.get(item.id, {}).get("status", "open")
        pb_id = f"PB-{idx:03d}"
        cards.append(
            {
                "pb_id": pb_id,
                "plan_id": item.id,
                "name": f"[{pb_id}] {item.id}: {item.title}",
                "priority": item.priority,
                "effort": item.effort,
                "status": state,
                "target_list": "Bitti" if state == "done" else "Product Backlog",
                "desc": (
                    f"Plan ID: {item.id}\n"
                    f"Priority: {item.priority} | Effort: {item.effort}\n"
                    f"Acceptance: {item.bullets.get('Kabul', '')}\n"
                ),
            }
        )
    return cards


def sync_to_trello(cards: list[dict], dry_run: bool = True) -> dict:
    if dry_run:
        return {
            "mode": "dry_run",
            "total_cards": len(cards),
            "created": 0,
            "skipped_existing": 0,
            "sample": cards[:10],
        }

    api_key = os.environ.get("TRELLO_API_KEY", "").strip()
    token = os.environ.get("TRELLO_TOKEN", "").strip()
    board_id = os.environ.get("TRELLO_BOARD_ID", "").strip()
    if not (api_key and token and board_id):
        raise RuntimeError("Missing TRELLO_API_KEY, TRELLO_TOKEN, or TRELLO_BOARD_ID environment variables.")

    auth_qs = urllib.parse.urlencode({"key": api_key, "token": token})
    lists_url = f"https://api.trello.com/1/boards/{board_id}/lists?{auth_qs}"
    cards_url = f"https://api.trello.com/1/boards/{board_id}/cards?{auth_qs}"

    with urllib.request.urlopen(lists_url, timeout=15) as resp:
        lists = {entry["name"]: entry["id"] for entry in json.loads(resp.read().decode("utf-8"))}
    with urllib.request.urlopen(cards_url, timeout=15) as resp:
        existing_names = {entry["name"] for entry in json.loads(resp.read().decode("utf-8"))}

    created = 0
    skipped = 0
    for card in cards:
        if card["name"] in existing_names:
            skipped += 1
            continue
        list_id = lists.get(card["target_list"]) or next(iter(lists.values()))
        payload = urllib.parse.urlencode(
            {
                "key": api_key,
                "token": token,
                "idList": list_id,
                "name": card["name"],
                "desc": card["desc"],
            }
        ).encode("utf-8")
        req = urllib.request.Request("https://api.trello.com/1/cards", data=payload, method="POST")
        with urllib.request.urlopen(req, timeout=15):
            created += 1

    return {
        "mode": "live",
        "total_cards": len(cards),
        "created": created,
        "skipped_existing": skipped,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-dir", type=Path, default=ROOT / "docs" / "plan-v2")
    parser.add_argument("--priority", choices=["P0", "P1", "P2", "P3"], default=None)
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--apply", action="store_true", default=False, help="Actually push cards to Trello API")
    args = parser.parse_args(argv)

    cards = build_backlog_cards(args.plan_dir, priority_filter=args.priority)
    result = sync_to_trello(cards, dry_run=not args.apply)
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
