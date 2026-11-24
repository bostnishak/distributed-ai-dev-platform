"""Pattern scan of the vanilla-JS frontend; every hit is a concrete file:line finding."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "master" / "static"
RULES = {
    "innerHTML-assignment": r"\.innerHTML\s*=",
    "insertAdjacentHTML": r"insertAdjacentHTML\(",
    "document.write": r"document\.write\(",
    "eval-or-Function": r"\beval\(|new Function\(",
    "empty-catch": r"catch\s*(\([^)]*\))?\s*\{\s*\}",
    "console.log": r"console\.(log|debug)\(",
    "alert-confirm-prompt": r"\b(alert|confirm|prompt)\(",
    "fetch-no-catch-nearby": r"await fetch\(",
    "setInterval-no-clear": r"setInterval\(",
    "addEventListener-on-window-document": r"(window|document)\.addEventListener\(",
    "hardcoded-http-url": r"https?://(?!www\.w3\.org)[a-z0-9.-]+",
    "TODO-FIXME": r"TODO|FIXME|XXX|HACK",
    "inline-style-assignment": r"\.style\.cssText\s*=",
    "localStorage-direct": r"localStorage\.(get|set)Item\(",
    "magic-timeout": r"setTimeout\([^,]+,\s*\d{4,}\)",
    "var-declaration": r"\bvar\s+\w+",
    "double-equals": r"[^=!]==[^=]",
    "parseInt-no-radix": r"parseInt\([^,)]+\)",
}
rows = []
for path in sorted(ROOT.rglob("*")):
    if path.suffix not in (".js", ".html", ".css") or "vendor" in path.parts:
        continue
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    rel = path.relative_to(ROOT).as_posix()
    if path.suffix == ".js":
        for number, line in enumerate(lines, 1):
            for name, pattern in RULES.items():
                if re.search(pattern, line):
                    rows.append({"file": rel, "line": number, "rule": name, "text": line.strip()[:110]})
        if len(lines) > 400:
            rows.append({"file": rel, "line": len(lines), "rule": "file-over-400-lines", "text": f"{len(lines)} satır"})
        # long functions (rough): lines between a function start and the next top-level function
        starts = [i for i, l in enumerate(lines) if re.match(r"(export\s+)?(async\s+)?function\s+\w+", l)]
        for a, b in zip(starts, starts[1:] + [len(lines)]):
            if b - a > 80:
                rows.append({"file": rel, "line": a + 1, "rule": "function-over-80-lines", "text": lines[a].strip()[:80] + f" ({b - a} satır)"})
    if path.suffix == ".html":
        html = "\n".join(lines)
        for match in re.finditer(r"<button(?![^>]*\btype=)[^>]*>", html):
            rows.append({"file": rel, "line": html[: match.start()].count("\n") + 1, "rule": "button-without-type", "text": match.group(0)[:100]})
        for match in re.finditer(r"<img(?![^>]*\balt=)[^>]*>", html):
            rows.append({"file": rel, "line": html[: match.start()].count("\n") + 1, "rule": "img-without-alt", "text": match.group(0)[:100]})
        for match in re.finditer(r"<(input|textarea|select)(?![^>]*(aria-label|aria-labelledby|id=))[^>]*>", html):
            rows.append({"file": rel, "line": html[: match.start()].count("\n") + 1, "rule": "form-control-without-label-hook", "text": match.group(0)[:100]})
        for match in re.finditer(r"onclick=|onerror=|onload=", html):
            rows.append({"file": rel, "line": html[: match.start()].count("\n") + 1, "rule": "inline-event-handler", "text": ""})
    if path.suffix == ".css":
        css = "\n".join(lines)
        rows.append({"file": rel, "line": 1, "rule": "css-size", "text": f"{len(lines)} satır, {css.count('!important')} !important"}) if css.count("!important") > 5 else None
        for match in re.finditer(r"outline:\s*(none|0)", css):
            rows.append({"file": rel, "line": css[: match.start()].count("\n") + 1, "rule": "focus-outline-removed", "text": css[match.start(): match.start() + 60].splitlines()[0]})
        for match in re.finditer(r"font-size:\s*(\d+)px", css):
            if int(match.group(1)) < 11:
                rows.append({"file": rel, "line": css[: match.start()].count("\n") + 1, "rule": "tiny-font", "text": match.group(0)})
Path(sys.argv[1]).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
import collections

print(len(rows), collections.Counter(r["rule"] for r in rows).most_common())
