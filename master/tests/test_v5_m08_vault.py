"""v5 milestone 08: the local asset vault, the zero-CDN gate, the ZIP export and the offline documentation index."""

from __future__ import annotations

import io
import json
import zipfile

import pytest

import asset_vault
import docs_index
import done_gate

pytestmark = pytest.mark.unit

_CDN_PAGE = """<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>Pano</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Plus+Jakarta+Sans&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script defer src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.js"></script>
</head><body><script type="module">
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
mermaid.initialize({startOnLoad: true});
</script></body></html>"""


def _need_vault():
    if not (asset_vault.source() / "chart.js" / "dist" / "chart.umd.min.js").is_file():
        pytest.skip("varlık kasası yok (scripts/vendor_fetch.py)")


def test_known_cdn_links_become_project_copies(tmp_path):
    _need_vault()
    (tmp_path / "index.html").write_text(_CDN_PAGE, encoding="utf-8")
    (tmp_path / "tek.html").write_text("<head></head><script type='module'>import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs'; mermaid.initialize({});</script>", encoding="utf-8")
    (tmp_path / "pages").mkdir()
    (tmp_path / "pages" / "alt.html").write_text('<script src="https://unpkg.com/cytoscape/dist/cytoscape.min.js"></script>', encoding="utf-8")
    done = asset_vault.localize(tmp_path)
    page = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert len(done) >= 5 and "//cdn" not in page and "googleapis" not in page and "gstatic" not in page and "import mermaid" not in page
    for part in ("chart.js/dist/chart.umd.min.js", "mermaid/dist/mermaid.min.js", "katex/dist/katex.min.css", "katex/dist/katex.min.js"):
        assert f"vendor/{part}" in page and (tmp_path / "vendor" / part).is_file()
    assert any((tmp_path / "vendor" / "katex" / "dist" / "fonts").iterdir())
    one_line = (tmp_path / "tek.html").read_text(encoding="utf-8")
    assert "import mermaid" not in one_line and "vendor/mermaid/dist/mermaid.min.js" in one_line and "mermaid.initialize" in one_line
    assert 'src="../vendor/cytoscape/dist/cytoscape.min.js"' in (tmp_path / "pages" / "alt.html").read_text(encoding="utf-8")
    fonts = next((tmp_path / "vendor").glob("fonts-*.css")).read_text(encoding="utf-8")
    assert "font-family:'Inter'" in fonts and "font-family:'Plus Jakarta Sans'" in fonts and "latin-ext" in fonts
    assert asset_vault.external(tmp_path) == [] and asset_vault.localize(tmp_path) == []


def test_link_the_vault_cannot_serve_blocks_delivery_unless_asked_for(tmp_path):
    (tmp_path / "index.html").write_text('<script src="https://cdn.tailwindcss.com"></script><script type="module">import x from "https://esm.sh/yok";</script><a href="https://ornek.com">bağlantı</a>', encoding="utf-8")
    (tmp_path / "s.css").write_text('body{background:url(https://ornek.com/a.png)}', encoding="utf-8")
    asset_vault.localize(tmp_path)
    found = asset_vault.external(tmp_path)
    assert any("tailwindcss" in line for line in found) and any("a.png" in line for line in found) and any("esm.sh" in line for line in found) and len(found) == 3
    assert asset_vault.blocking(tmp_path, "https://cdn.tailwindcss.com ve https://esm.sh/yok kullan, https://ornek.com/a.png arka plan olsun") == []
    status, detail = done_gate.live_proof(tmp_path, [])
    assert status == done_gate.FAILED and "dış bağlantı" in detail


def test_vendored_libraries_are_not_audited_as_project_code(tmp_path):
    import req_checks
    import shortcut_audit

    (tmp_path / "vendor").mkdir()
    (tmp_path / "vendor" / "lib.js").write_text("var c = '#123456'; // TODO\ntry{x()}catch(e){}", encoding="utf-8")
    (tmp_path / "index.html").write_text("<p>boş</p>", encoding="utf-8")
    assert shortcut_audit.findings(tmp_path) == []
    assert "#123456" not in req_checks._source(tmp_path)


def test_zip_export_carries_the_vendor_files(tmp_path, monkeypatch):
    _need_vault()
    import asyncio

    import studio_api
    import workspace_builder as wb

    ws_dir = tmp_path / "pano-1"
    ws_dir.mkdir()
    (ws_dir / "index.html").write_text('<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>', encoding="utf-8")
    asset_vault.localize(ws_dir)
    monkeypatch.setattr(wb, "safe_workspace_dir", lambda _ws: ws_dir)

    async def read():
        response = await studio_api.download_workspace_zip("pano-1")
        return b"".join([chunk async for chunk in response.body_iterator])

    names = zipfile.ZipFile(io.BytesIO(asyncio.run(read()))).namelist()
    assert "pano-1/vendor/chart.js/dist/chart.umd.min.js" in names


def test_vault_is_served_read_only_from_the_local_preview_origin():
    _need_vault()
    from fastapi.testclient import TestClient

    import preview_server

    client = TestClient(preview_server.preview_app)
    assert client.get("/vendor/chart.js/dist/chart.umd.min.js").status_code == 200
    assert client.get("/vendor/%2e%2e/vendor.lock.json").status_code == 404
    assert client.get("/vendor/yok.js").status_code == 404


def test_documentation_index_searches_offline_and_rebuilds_only_on_change(tmp_path, monkeypatch):
    docs = tmp_path / "docs" / "sqlite"
    docs.mkdir(parents=True)
    monkeypatch.setattr(docs_index, "folder", lambda: tmp_path / "docs")
    monkeypatch.setattr(docs_index, "database", lambda: tmp_path / "docs.sqlite")
    assert docs_index.build() == 0
    (docs / "index.json").write_text(json.dumps({"entries": [{"name": "Write-Ahead Logging", "path": "wal#x"}, {"name": "VACUUM", "path": "vacuum"}]}), encoding="utf-8")
    (docs / "db.json").write_text(json.dumps({"wal": "<h1>WAL</h1><p>journal_mode checkpoint readers</p><script>gizli</script>", "vacuum": "<p>rebuilds the database file</p>"}), encoding="utf-8")
    assert docs_index.build() == 2
    hit = docs_index.search("journal_mode checkpoint")[0]
    assert hit[:3] == ("sqlite", "wal", "Write-Ahead Logging") and "gizli" not in hit[3]
    assert docs_index.search("rebuilds", ("python~3.12",)) == [] and docs_index.search("!!") == []
    assert docs_index.build() == 2


def test_icon_placeholders_become_inline_svg_and_the_icon_script_goes(tmp_path):
    if not (asset_vault.source() / "lucide-static" / "sprite.svg").is_file():
        pytest.skip("ikon kaydı yok")
    (tmp_path / "index.html").write_text('<script src="https://unpkg.com/lucide@latest"></script><button><i data-lucide="trash-2" class="ik"></i> Sil</button><script>lucide.createIcons();</script>', encoding="utf-8")
    done = asset_vault.localize(tmp_path)
    page = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "lucide:trash-2" in done and '<svg class="ik"' in page and "<path" in page and "data-lucide" not in page
    assert "createIcons" not in page and "unpkg" not in page and asset_vault.external(tmp_path) == []
    assert asset_vault.icon("boyle-bir-ikon-yok") == ""


def test_export_keyword_is_removed_without_leaving_stray_characters(tmp_path):
    import workspace_requirements

    (tmp_path / "index.html").write_text('<script src="a.js"></script>', encoding="utf-8")
    (tmp_path / "a.js").write_text("export function bir() {}\n  export const iki = 2;\n", encoding="utf-8")
    workspace_requirements._classic_scripts(tmp_path)
    assert (tmp_path / "a.js").read_text(encoding="utf-8") == "function bir() {}\n  const iki = 2;\n"
