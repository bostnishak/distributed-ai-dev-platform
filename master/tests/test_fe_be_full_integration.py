"""Full Frontend <-> Backend <-> UI integration contract tests (zero 422/405/500 payload bugs, zero orphan UI views)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.contract


def test_zero_orphaned_frontend_js_views():
    """Every frontend JS module under master/static/js/ (except generated api_types.js) must be reachable from index.html."""
    js_dir = REPO_ROOT / "master" / "static" / "js"
    all_js = {p.name for p in js_dir.glob("*.js")} - {"api_types.js"}
    edges: dict[str, set[str]] = {}
    for p in js_dir.glob("*.js"):
        src = p.read_text(encoding="utf-8", errors="ignore")
        edges[p.name] = set(re.findall(r"""(?:import|from)\s+['"]\.\/([^'"]+\.js)['"]""", src))
    html_src = (REPO_ROOT / "master" / "static" / "index.html").read_text(encoding="utf-8")
    roots = set(re.findall(r"""/static/js/([^"']+\.js)""", html_src))
    seen: set[str] = set()
    stack = list(roots)
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        for nxt in edges.get(cur, ()):
            if nxt not in seen:
                stack.append(nxt)
    orphans = sorted(all_js - seen)
    assert orphans == [], f"Bağlı olmayan (orphan) ön yüz JS dosyaları: {orphans}"


def test_every_non_dangerous_workbench_tool_payload_passes_schema_validation(client, monkeypatch):
    """Live-fire every non-dangerous Workbench catalog tool against FastAPI and guarantee 0 HTTP 422/405/500 schema bugs."""
    from rag.store import default_rag_store

    monkeypatch.setattr(default_rag_store, "allow_test_embeddings", True)
    node_bin = shutil.which("node")
    assert node_bin is not None
    script = (
        "import('./master/static/js/workbench_catalog_1.js').then(async m1 => {"
        "const m2 = await import('./master/static/js/workbench_catalog_2.js');"
        "const m3 = await import('./master/static/js/workbench_catalog_3.js');"
        "const m4 = await import('./master/static/js/workbench_catalog_4.js');"
        "const m5 = await import('./master/static/js/workbench_catalog_5.js');"
        "const all = [...m1.PRODUCTIVITY_TOOLS, ...m2.DOMAIN_AND_EDU_TOOLS, ...m2.SECURITY_AND_MEMORY_TOOLS,"
        " ...m3.OPS_AND_AI_TOOLS, ...m4.PLATFORM_EXT_TOOLS, ...m5.ECOSYSTEM_TOOLS];"
        "console.log(JSON.stringify(all));});"
    )
    proc = subprocess.run(
        [node_bin, "-e", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        timeout=15,
    )
    tools = json.loads(proc.stdout)
    assert len(tools) >= 240

    # Skip endpoints that require external live Ollama LLM generation so CI stays offline & deterministic.
    llm_only_ids = {"research-translate", "st-research", "orc-run", "oai-chat", "oai-emb"}
    schema_errors: list[tuple[int, str, str, str]] = []
    for t in tools:
        if t.get("dangerous") or t["id"] in llm_only_ids:
            continue
        url = t["path"]
        for k, v in (t.get("params") or {}).items():
            url = url.replace("{" + k + "}", str(v))
        method = t["method"].upper()
        kwargs: dict = {}
        if t.get("query"):
            kwargs["params"] = t["query"]
        if method not in ("GET", "DELETE") and "body" in t:
            if t.get("form"):
                kwargs["data"] = {k: str(v) for k, v in t["body"].items()}
            else:
                kwargs["json"] = t["body"]
        resp = client.request(method, url, **kwargs)
        if resp.status_code in (405, 422) or resp.status_code >= 500:
            schema_errors.append((resp.status_code, t["id"], f"{method} {url}", resp.text[:220]))

    assert schema_errors == [], f"Ön yüz Workbench şema/sunucu uyumsuzlukları: {schema_errors[:10]}"


def test_direct_ui_views_interactive_labs_cnc_and_studio_roundtrip(client):
    """Verify exact payload/response shapes used by workspace_labs.js, cnc_workspace.js, and studio.js."""
    # 1. workspace_labs.js: Notebook create + run cell 0
    nb = client.post(
        "/api/notebooks",
        json={"user_id": "default", "title": "Lab Test", "cells": [{"cell_type": "code", "source": "print(6 * 7)"}]},
    )
    assert nb.status_code == 200
    nb_id = nb.json()["notebook_id"]
    run = client.post(f"/api/notebooks/{nb_id}/run", json={"user_id": "default", "cell_index": 0})
    assert run.status_code == 200
    assert run.json()["output"]["ok"] is True
    assert "42" in run.json()["output"]["stdout"]

    # 2. workspace_labs.js: Flashcards create + SM-2 review
    fc = client.post(
        "/api/education/flashcards",
        json={"user_id": "default", "topic": "Genel", "front": "WAL nedir?", "back": "Write-Ahead Logging"},
    )
    assert fc.status_code == 200
    card_id = fc.json()["card_id"]
    rev = client.post(f"/api/education/flashcards/{card_id}/review", json={"quality": 4})
    assert rev.status_code == 200
    assert "interval_days" in rev.json()

    # 3. workspace_labs.js: Memory conflicts + HA/Amdahl + Benchmark run
    assert "conflicts" in client.get("/api/memory/conflicts?user_id=default").json()
    ha = client.get("/api/ha/status").json()
    assert "speedup_matrix" in ha and "leader" in ha and "term" in ha
    bench = client.post("/api/eval-studio/benchmark-run", json={"limit": 10}).json()
    assert bench["ok"] is True and bench["evaluated_count"] == 10

    # 4. cnc.js + cnc_workspace.js: Demo + evaluate-measurements exact shape
    demo = client.post("/api/cnc/demo")
    assert demo.status_code == 200
    job = demo.json()
    assert job["id"] and len(job["balloons"]) > 0
    first_nom = float(job["balloons"][0].get("nominal") or 0)
    ev = client.post(
        f"/api/cnc/jobs/{job['id']}/evaluate-measurements",
        json={"measurements": {"1": [first_nom]}},
    )
    assert ev.status_code == 200
    ev_data = ev.json()
    assert ev_data["evaluated_count"] >= 1
    assert "ok_count" in ev_data and "first_pass_yield_pct" in ev_data

    # 5. studio.js: Workspaces list endpoint
    ws = client.get("/api/studio/workspaces")
    assert ws.status_code == 200
    assert "workspaces" in ws.json()

    # 6. Engineering imperial/metric unit conversion & safe notebook range/pow + space_shooter game build
    conv = client.post("/api/domains/engineering/convert", json={"value": 25.4, "from_unit": "mm", "to_unit": "in"})
    assert conv.status_code == 200 and abs(conv.json()["value"] - 1.0) < 1e-6
    conv_p = client.post("/api/domains/engineering/convert", json={"value": 10.0, "from_unit": "bar", "to_unit": "MPa"})
    assert conv_p.status_code == 200 and abs(conv_p.json()["value"] - 1.0) < 1e-6
    nb2 = client.post(
        "/api/notebooks",
        json={"user_id": "default", "title": "Range Test", "cells": [{"cell_type": "code", "source": "print(sum(range(1, 11)), 2 ** 8)"}]},
    )
    assert nb2.status_code == 200
    run2 = client.post(f"/api/notebooks/{nb2.json()['notebook_id']}/run", json={"user_id": "default", "cell_index": 0})
    assert run2.status_code == 200 and "55" in run2.json()["output"]["stdout"] and "256" in run2.json()["output"]["stdout"]
    gm = client.post("/api/games/build", json={"prompt": "Uzay savunma HTML5 oyunu", "genre": "space_shooter"})
    assert gm.status_code == 200

    # 7. Frontier AI routing guards: no false PPTX on advice, no re-zip hijack on ZIP inspection, multi-folder ZIP project allowed
    import document_factory as df
    import file_converter as fc

    assert df.detect_document_request("Sunum yaparken nelere dikkat etmeliyim? 3 kısa madde yaz.", False) is None
    assert df.detect_document_request("Türkiye şehirlerini CSV olarak oluştur", False) == "csv"
    assert fc.detect_conversion_or_archive_action("Bu ZIP içindeki klasörleri incele, hataları bul", "proje.zip") is None
    assert fc.detect_conversion_or_archive_action("İçinde docs/, src/, tests/ olan proje klasörü oluştur ve ZIP olarak ver", None) is None
