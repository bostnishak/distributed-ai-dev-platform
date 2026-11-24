"""Lists plan-v2 'done' items whose id appears in no test file (F101 in docs/plan-v3)."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
progress = json.loads((ROOT / "docs/plan-v2/PROGRESS.json").read_text(encoding="utf-8"))["items"]
files = [
    p for d in ("master/tests", "agent/tests", "frontend/tests", "eval")
    for p in (ROOT / d).rglob("*") if p.is_file() and p.suffix in (".py", ".mjs")
]
texts = {p: p.read_text(encoding="utf-8", errors="ignore") for p in files}
missing = []
for item_id, entry in progress.items():
    if entry["status"] != "done":
        continue
    area, number = item_id.split("-")
    pattern = re.compile(rf"(?<![A-Za-z]){area}[-_ ]?0*{int(number)}(?!\d)", re.I)
    if not any(pattern.search(text) for text in texts.values()):
        missing.append(item_id)
print(f"{len(missing)} done madde hiçbir test dosyasında anılmıyor")
print(" ".join(missing))
