"""Verify every 'done' claim in a plan's PROGRESS.json: does the cited test file exist and does the named test function exist?

Usage: python scripts/audit/verify_done.py docs/plan-v3 [out.json]
"""

import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
plan = ROOT / sys.argv[1]
data = json.loads((plan / "PROGRESS.json").read_text(encoding="utf-8"))
items = data.get("items", data)

all_tests: dict[str, str] = {}
for p in list((ROOT / "master" / "tests").rglob("*.py")) + list((ROOT / "agent").rglob("test_*.py")):
    all_tests[p.relative_to(ROOT).as_posix()] = p.read_text(encoding="utf-8", errors="ignore")


def test_refs(ev) -> list[str]:
    if isinstance(ev, str):
        return re.findall(r"[\w/.\-]+\.py(?:::\w+)?", ev)
    if isinstance(ev, dict):
        out = []
        for t in ev.get("tests") or []:
            out += re.findall(r"[\w/.\-]+\.py(?:::\w+)?", str(t))
        return out
    return []


report = {}
verdicts = collections.Counter()
for key, entry in items.items():
    if entry.get("status") != "done":
        continue
    refs = test_refs(entry.get("evidence"))
    ok, why = False, "no test cited"
    for ref in refs:
        path, _, func = ref.partition("::")
        src = next((v for k, v in all_tests.items() if k.endswith(path)), None)
        if src is None:
            why = f"test file not found: {path}"
            continue
        if func and not re.search(rf"def {re.escape(func)}\b", src):
            why = f"test function not found: {ref}"
            continue
        ok, why = True, "ok"
        break
    # an id mentioned in any test counts as indirect evidence only
    indirect = any(key in src for src in all_tests.values())
    verdict = "verified" if ok else ("indirect" if indirect else "unsupported")
    verdicts[verdict] += 1
    report[key] = {"verdict": verdict, "why": why}
print(verdicts)
if len(sys.argv) > 2:
    Path(sys.argv[2]).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
for k, v in report.items():
    if v["verdict"] == "unsupported":
        print(k, v["why"])
