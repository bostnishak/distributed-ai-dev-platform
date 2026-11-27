"""Interactive charts and graphs as single files that open with no network, and D2 drawings.

The libraries come from the local vendor vault (scripts/vendor_fetch.py) and are written into the file, so nothing is
fetched when it is opened. Data goes in as JSON, never as markup. Files are offered as downloads: the platform's own
pages never execute them.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

import config
from process_utils import run_process
from prompt_loader import load_prompt

_LIBS = {
    "vega": ("vega/build/vega.min.js", "vega-lite/build/vega-lite.min.js", "vega-embed/build/vega-embed.min.js"),
    "plotly": ("plotly.js-basic-dist-min/plotly-basic.min.js",),
    "chart.js": ("chart.js/dist/chart.umd.min.js",),
    "cytoscape": ("cytoscape/dist/cytoscape.min.js",),
}
_START = {"vega": "chart_vega.js.txt", "plotly": "chart_plotly.js.txt", "chart.js": "chart_chartjs.js.txt", "cytoscape": "graph_cytoscape.js.txt"}


def vault() -> Path:
    return config.data_dir() / "vendor"


def available(library: str) -> bool:
    return all((vault() / "lib" / part).is_file() for part in _LIBS[library])


def chart_library(prompt: str) -> str:
    lowered = prompt.casefold()
    return "plotly" if "plotly" in lowered else "chart.js" if "chart.js" in lowered or "chartjs" in lowered else "vega"


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")  # data can never close the script element


def page(library: str, title: str, data: dict[str, Any]) -> str:
    """A complete HTML document; OSError when the library is not in the vault."""
    scripts = "\n".join(f"<script>{(vault() / 'lib' / part).read_text(encoding='utf-8')}</script>" for part in _LIBS[library])
    return (f"<!doctype html><html lang=\"tr\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{html.escape(title)}</title><style>body{{margin:0;padding:16px;font:16px/1.5 system-ui,sans-serif}}h1{{font-size:20px}}#view{{width:100%;height:70vh}}</style></head>"
            f"<body><h1>{html.escape(title)}</h1><div id=\"view\"></div>\n{scripts}\n<script type=\"application/json\" id=\"data\">{_json(data)}</script>"
            f"<script>{load_prompt(_START[library])}</script></body></html>")


def chart_data(label: str, value: str, pairs: list[tuple[str, float]]) -> dict[str, Any]:
    return {"label": label, "value": value, "rows": [{"name": str(name), "value": float(number)} for name, number in pairs]}


def graph_data(flow: dict[str, Any]) -> dict[str, Any]:
    nodes = [{"data": {"id": s["id"], "label": s["label"], "kind": s["type"]}} for s in flow["steps"]]
    edges = [{"data": {"source": e["from"], "target": e["to"], "label": e.get("label", "")}} for e in flow["edges"]]
    return {"elements": nodes + edges}


def _quoted(text: str) -> str:
    return '"' + re.sub(r'["\\{}$|;\n]', " ", text).strip() + '"'


def d2_text(flow: dict[str, Any]) -> str:
    shapes = {"start": "oval", "end": "oval", "decision": "diamond", "process": "rectangle"}
    names = {s["id"]: f"n{i}" for i, s in enumerate(flow["steps"], start=1)}
    lines = ["direction: down"]
    lines += [f"{names[s['id']]}: {_quoted(s['label'])} {{ shape: {shapes[s['type']]} }}" for s in flow["steps"]]
    lines += [f"{names[e['from']]} -> {names[e['to']]}" + (f": {_quoted(e['label'])}" if e.get("label") else "") for e in flow["edges"]]
    return "\n".join(lines) + "\n"


def d2_program() -> str:
    own = vault() / "bin" / "d2.exe"
    return str(own) if own.is_file() else (shutil.which("d2") or "")


def d2_svg(source: str, target: Path, run=run_process) -> bool:
    """Draw with D2's ELK layout (it orders nodes to cross as little as it can); False when D2 is not installed or fails."""
    program = d2_program()
    if not program:
        return False
    with tempfile.TemporaryDirectory(prefix="cm6453_d2_", ignore_cleanup_errors=True) as tmp:
        script = Path(tmp) / "akis.d2"
        script.write_text(source, encoding="utf-8")
        done = run([program, "--layout", "elk", str(script), str(target)], cwd=Path(tmp), timeout_s=60)
    return done.returncode == 0 and target.is_file()
