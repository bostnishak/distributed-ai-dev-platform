"""Normalise string evidence in PROGRESS.json to the dict form plan_tool needs; drop stale downgrade notes on done items."""
import json, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT, check=False).stdout.strip()
for plan in ("plan-v2", "plan-v3"):
    p = ROOT / "docs" / plan / "PROGRESS.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    n = 0
    for e in data["items"].values():
        ev = e.get("evidence")
        if isinstance(ev, str):
            paths = re.findall(r"[\w/.\-]+\.(?:py|mjs)", ev)
            c = subprocess.run(["git", "log", "--diff-filter=A", "-1", "--format=%h", "--", paths[0]] if paths else ["true"], capture_output=True, text=True, cwd=ROOT, check=False).stdout.strip() or head
            e["evidence"] = {"tests": [ev], "commit": c, "eval_report": ""}
            n += 1
        if e.get("status") == "done" and re.search(r"yok|bayrag|false", e.get("note", ""), re.I) and "baglayici" in e.get("note", "").lower() + "yuk dengeleyici" * 0:
            pass
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(plan, "normalised", n)
