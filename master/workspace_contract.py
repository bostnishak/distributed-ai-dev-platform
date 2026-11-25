"""Cross-file contract checks for generated web projects: do the URLs the JS calls exist on the server?"""

from __future__ import annotations

import re
from pathlib import Path

_FETCH_RE = re.compile(r"""fetch\(\s*[`'"]([^`'"]+)""")


def _rule_regex(rule: str) -> re.Pattern[str]:
    return re.compile("^" + re.sub(r"<[^>]+>", "[^/]+", re.escape(rule).replace(r"\<", "<").replace(r"\>", ">")) + "/?$")


def contract_problem(ws_dir: Path, routes: list[str]) -> tuple[Path, str] | None:
    """Return (js file, message) for the first fetch() URL that no server route answers, else None."""
    if not routes:
        return None
    patterns = [_rule_regex(r) for r in routes]
    for js in sorted(ws_dir.rglob("*.js")):
        if ".history" in js.parts or "node_modules" in js.parts:
            continue
        for raw in _FETCH_RE.findall(js.read_text(encoding="utf-8", errors="replace")):
            path = re.sub(r"\$\{[^}]*\}", "1", raw).split("?")[0]
            if path.startswith("/") and not path.startswith("//") and not any(p.match(path) for p in patterns):
                shown = ", ".join(r for r in routes if not r.startswith("/static"))
                return js, f"{js.name} dosyası `{raw}` adresini çağırıyor ama sunucuda böyle bir rota yok. Sunucudaki rotalar: {shown}. JS içindeki fetch adreslerini bu rotalara birebir uyacak şekilde düzelt."
    return None
