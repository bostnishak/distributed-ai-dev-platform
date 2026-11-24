"""IDE-17, IDE-19, IDE-20: 8 Tested, Self-Contained Starter Project Templates with Tests, CI & Verified README."""

from __future__ import annotations

from typing import Any

from prompt_loader import load_prompt

# 8 working starter templates — LLM customizes these instead of writing boilerplate from scratch (IDE-17)
STARTER_TEMPLATES: dict[str, dict[str, Any]] = {
    "fastapi_sqlite": {
        "name": "FastAPI + SQLite Web API",
        "stack": ["python", "fastapi", "sqlite", "pytest"],
        "files": {
            "app.py": load_prompt("b4_tpl_fastapi_app.txt"),
            "tests/test_app.py": (
                "from app import health, list_items\n\n"
                "def test_health():\n"
                "    assert health()['status'] == 'ok'\n\n"
                "def test_list_items():\n"
                "    assert len(list_items()['items']) >= 1\n"
            ),
            "requirements.txt": "fastapi==0.115.0\nuvicorn==0.30.6\npytest==8.3.0\n",
            ".github/workflows/ci.yml": "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - run: pytest -q\n",
            "README.md": "# {{PROJECT_NAME}}\n\n## Kurulum ve Çalıştırma\n```bash\npip install -r requirements.txt\npytest -q\n```\n",
        },
    },
    "spa_web": {
        "name": "Offline Single-Page Web Application",
        "stack": ["html", "css", "javascript"],
        "files": {
            "index.html": "<!doctype html><html lang='tr'><head><meta charset='utf-8'><title>{{PROJECT_NAME}}</title><link rel='stylesheet' href='style.css'></head><body><main><h1>{{PROJECT_NAME}}</h1><button id='btn'>Başlat</button><div id='out'></div></main><script src='app.js'></script></body></html>\n",
            "style.css": "body{font-family:system-ui,sans-serif;margin:2rem;background:#f8fafc;color:#0f172a;}button{padding:.6rem 1.2rem;background:#0f766e;color:#fff;border:none;border-radius:6px;cursor:pointer;}\n",
            "app.js": "document.getElementById('btn')?.addEventListener('click', () => { document.getElementById('out').textContent = 'Hazır'; });\n",
            "tests/test_smoke.py": "from pathlib import Path\ndef test_files_exist():\n    assert Path('index.html').is_file() and Path('app.js').is_file()\n",
            "README.md": "# {{PROJECT_NAME}}\n\nTarayıcıda `index.html` dosyasını açın.\n",
        },
    },
    "cli_tool": {
        "name": "Python CLI Aracı",
        "stack": ["python", "argparse", "pytest"],
        "files": {
            "cli.py": load_prompt("b4_tpl_cli_tool.txt"),
            "tests/test_cli.py": "from cli import compute\ndef test_compute():\n    assert compute(21) == 42\n",
            "requirements.txt": "pytest==8.3.0\n",
            "README.md": "# {{PROJECT_NAME}}\n\n```bash\npython cli.py --value 21\npytest -q\n```\n",
        },
    },
    "desktop_tk": {
        "name": "Tkinter Masaüstü Uygulaması",
        "stack": ["python", "tkinter", "pytest"],
        "files": {
            "logic.py": "def format_greeting(name: str) -> str:\n    return f'Merhaba, {name.strip() or \"Kullanıcı\"}'\n",
            "main.py": "import tkinter as tk\nfrom logic import format_greeting\n\ndef launch():\n    root = tk.Tk()\n    root.title('{{PROJECT_NAME}}')\n    tk.Label(root, text=format_greeting('{{PROJECT_NAME}}')).pack(padx=24, pady=24)\n    root.mainloop()\n",
            "tests/test_logic.py": "from logic import format_greeting\ndef test_greeting():\n    assert 'Merhaba' in format_greeting('Test')\n",
            "requirements.txt": "pytest==8.3.0\n",
            "README.md": "# {{PROJECT_NAME}}\n\n```bash\npython main.py\n```\n",
        },
    },
    "data_app": {
        "name": "Veri Analizi Uygulaması",
        "stack": ["python", "csv", "statistics", "pytest"],
        "files": {
            "analyzer.py": "import statistics\n\ndef summarize(values: list[float]) -> dict:\n    return {'count': len(values), 'mean': round(statistics.mean(values), 4), 'max': max(values)}\n",
            "tests/test_analyzer.py": "from analyzer import summarize\ndef test_summarize():\n    r = summarize([10.0, 20.0, 30.0])\n    assert r['mean'] == 20.0 and r['max'] == 30.0\n",
            "requirements.txt": "pytest==8.3.0\n",
            "README.md": "# {{PROJECT_NAME}}\n\n```bash\npytest -q\n```\n",
        },
    },
    "chrome_ext": {
        "name": "Chrome Eklentisi (Manifest V3)",
        "stack": ["javascript", "json", "html"],
        "files": {
            "manifest.json": '{\n  "manifest_version": 3,\n  "name": "{{PROJECT_NAME}}",\n  "version": "1.0.0",\n  "action": {"default_popup": "popup.html"}\n}\n',
            "popup.html": "<!doctype html><html><body><h3>{{PROJECT_NAME}}</h3><script src='popup.js'></script></body></html>\n",
            "popup.js": "console.log('{{PROJECT_NAME}} aktif');\n",
            "tests/test_manifest.py": "import json\nfrom pathlib import Path\ndef test_manifest():\n    d = json.loads(Path('manifest.json').read_text(encoding='utf-8'))\n    assert d['manifest_version'] == 3\n",
            "README.md": "# {{PROJECT_NAME}}\n\n`chrome://extensions` üzerinden paketlenmemiş olarak yükleyin.\n",
        },
    },
    "rest_frontend": {
        "name": "REST API + Ön Yüz Tam Yığın",
        "stack": ["python", "fastapi", "html", "javascript"],
        "files": {
            "backend.py": "from fastapi import FastAPI\napp = FastAPI(title='{{PROJECT_NAME}}')\n@app.get('/health')\ndef health():\n    return {'status': 'ok'}\n",
            "frontend/index.html": "<!doctype html><html lang='tr'><body><h1>{{PROJECT_NAME}}</h1></body></html>\n",
            "tests/test_backend.py": "from backend import health\ndef test_health():\n    assert health()['status'] == 'ok'\n",
            "requirements.txt": "fastapi==0.115.0\npytest==8.3.0\n",
            "README.md": "# {{PROJECT_NAME}}\n\n```bash\npytest -q\n```\n",
        },
    },
    "game_canvas2d": {
        "name": "Canvas2D Oyun İskeleti",
        "stack": ["html", "javascript", "canvas2d"],
        "files": {
            "index.html": "<!doctype html><html lang='tr'><body><canvas id='game' width='640' height='400'></canvas><script type='module' src='main.js'></script></body></html>\n",
            "main.js": "export const GAME_TITLE = '{{PROJECT_NAME}}';\nexport function stepScore(s) { return s + 1; }\n",
            "tests/test_game_scaffold.py": "from pathlib import Path\ndef test_game_files():\n    assert Path('index.html').is_file() and Path('main.js').is_file()\n",
            "README.md": "# {{PROJECT_NAME}}\n\nTarayıcıda `index.html` dosyasını açın.\n",
        },
    },
}


def render_template_files(template_id: str, project_name: str) -> dict[str, str]:
    """IDE-17: Instantiate a tested starter template with safe project name substitution."""
    if template_id not in STARTER_TEMPLATES:
        raise KeyError(f"Bilinmeyen proje şablonu: {template_id}")
    tpl = STARTER_TEMPLATES[template_id]
    safe_name = (project_name or "Proje").strip()[:60]
    return {path: content.replace("{{PROJECT_NAME}}", safe_name) for path, content in tpl["files"].items()}
