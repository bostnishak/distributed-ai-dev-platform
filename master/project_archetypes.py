"""Cluster B (`[M22]`, Faz 6.1): Specialized Project Archetypes & Blueprint Contracts.

Defines the 6 specialized project archetypes:
- `web_ecommerce`
- `fullstack_fastapi`
- `game_2d`
- `desktop_exe`
- `cli_automation`
- `data_science_ml`
and provides `detect_archetype(prompt: str) -> str` and `get_archetype_blueprint(archetype: str, project_name: str) -> dict`.
"""

from __future__ import annotations

from typing import Any

ARCHETYPES: dict[str, dict[str, Any]] = {
    "web_ecommerce": {
        "id": "web_ecommerce",
        "title": "Modern Web & E-Ticaret Uygulaması",
        "keywords": ("e-ticaret", "eticaret", "ecommerce", "mağaza", "magaza", "sepet", "ürün", "urun", "landing", "web sitesi", "vitrin"),
        "required_files": ["index.html", "styles.css", "app.js"],
        "interface_contracts": {
            "dom_ids": ["app-header", "product-grid", "cart-summary", "search-input"],
            "js_functions": ["renderProducts", "addToCart", "updateCartSummary"],
        },
        "templates": {
            "index.html": """<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{project_name}</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header id="app-header">
    <h1>{project_name}</h1>
    <input id="search-input" type="search" placeholder="Ürün ara...">
    <div id="cart-summary">Sepet (0)</div>
  </header>
  <main id="product-grid"></main>
  <script src="app.js"></script>
</body>
</html>
""",
            "styles.css": """* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; padding: 24px; }
header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
#product-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
.card { background: #1e293b; padding: 16px; border-radius: 12px; border: 1px solid #334155; }
""",
            "app.js": """const state = { cart: [], products: [
  { id: 1, name: "Endüstriyel Sensör", price: 1450 },
  { id: 2, name: "CNC Kontrol Modülü", price: 3200 }
]};

function renderProducts(list = state.products) {
  const grid = document.getElementById("product-grid");
  if (!grid) return;
  grid.innerHTML = "";
  list.forEach((p) => {
    const card = document.createElement("div");
    card.className = "card";
    card.textContent = `${p.name} - ${p.price} TL`;
    card.addEventListener("click", () => addToCart(p.id));
    grid.appendChild(card);
  });
}

function addToCart(productId) {
  const item = state.products.find((p) => p.id === productId);
  if (item) state.cart.push(item);
  updateCartSummary();
}

function updateCartSummary() {
  const el = document.getElementById("cart-summary");
  if (el) el.textContent = `Sepet (${state.cart.length})`;
}

document.addEventListener("DOMContentLoaded", () => renderProducts());
""",
        },
    },
    "fullstack_fastapi": {
        "id": "fullstack_fastapi",
        "title": "Full-Stack FastAPI + SQLite + Frontend Uygulaması",
        "keywords": ("fastapi", "api", "fullstack", "full-stack", "backend", "rest", "crud", "veritabanı", "veritabani", "dashboard"),
        "required_files": ["main.py", "database.py", "index.html", "requirements.txt"],
        "interface_contracts": {
            "routes": ["GET /api/health", "GET /api/items", "POST /api/items"],
            "dom_ids": ["item-list", "item-form"],
        },
        "templates": {
            "database.py": """from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "app.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL)")
    return conn
""",
            "main.py": """from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

import database

app = FastAPI(title="{project_name}")


class ItemCreate(BaseModel):
    title: str


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {{"status": "ok", "project": "{project_name}"}}


@app.get("/api/items")
def list_items() -> list[dict[str, object]]:
    with database.get_connection() as conn:
        rows = conn.execute("SELECT id, title FROM items ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


@app.post("/api/items")
def create_item(payload: ItemCreate) -> dict[str, object]:
    with database.get_connection() as conn:
        cur = conn.execute("INSERT INTO items (title) VALUES (?)", (payload.title,))
        return {{"id": cur.lastrowid, "title": payload.title}}
""",
            "index.html": """<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{project_name}</title>
</head>
<body>
  <h1>{project_name}</h1>
  <form id="item-form"><input id="item-title" required><button type="submit">Ekle</button></form>
  <ul id="item-list"></ul>
</body>
</html>
""",
            "requirements.txt": "fastapi>=0.110.0\nuvicorn>=0.29.0\npydantic>=2.6.0\n",
        },
    },
    "game_2d": {
        "id": "game_2d",
        "title": "HTML5 Canvas 2D Oyun Motoru",
        "keywords": ("oyun", "game", "2d", "canvas", "arcade", "platformer", "uzay", "snake", "tetris", "pong"),
        "required_files": ["index.html", "game.js", "styles.css"],
        "interface_contracts": {
            "dom_ids": ["game-canvas", "score-board", "restart-btn"],
            "js_functions": ["updateGame", "renderGame", "resetGame"],
        },
        "templates": {
            "index.html": """<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{project_name}</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div class="hud">
    <span id="score-board">Skor: 0</span>
    <button id="restart-btn" type="button">Yeniden Başlat</button>
  </div>
  <canvas id="game-canvas" width="800" height="500"></canvas>
  <script src="game.js"></script>
</body>
</html>
""",
            "styles.css": """body { background: #090d16; color: #f8fafc; font-family: sans-serif; text-align: center; margin: 0; padding: 20px; }
canvas { border: 2px solid #4f46e5; border-radius: 8px; background: #0f172a; }
.hud { margin-bottom: 12px; display: flex; justify-content: center; gap: 16px; align-items: center; }
""",
            "game.js": """const canvas = document.getElementById("game-canvas");
const ctx = canvas ? canvas.getContext("2d") : null;
let score = 0;
let player = { x: 400, y: 250, vx: 2, vy: 2, radius: 14 };

function updateGame() {
  player.x += player.vx;
  player.y += player.vy;
  if (player.x < 14 || player.x > 786) player.vx *= -1;
  if (player.y < 14 || player.y > 486) player.vy *= -1;
}

function renderGame() {
  if (!ctx) return;
  ctx.clearRect(0, 0, 800, 500);
  ctx.fillStyle = "#06b6d4";
  ctx.beginPath();
  ctx.arc(player.x, player.y, player.radius, 0, Math.PI * 2);
  ctx.fill();
}

function resetGame() {
  score = 0;
  player.x = 400;
  player.y = 250;
  const sb = document.getElementById("score-board");
  if (sb) sb.textContent = `Skor: ${score}`;
}

const btn = document.getElementById("restart-btn");
if (btn) btn.addEventListener("click", resetGame);
""",
        },
    },
    "desktop_exe": {
        "id": "desktop_exe",
        "title": "Masaüstü Tkinter / PyInstaller EXE Uygulaması",
        "keywords": ("exe", "masaustu", "masaüstü", "desktop", "tkinter", "gui", "pencere", "pyinstaller"),
        "required_files": ["app_gui.py", "core_logic.py", "requirements.txt"],
        "interface_contracts": {
            "python_functions": ["calculate_summary", "create_main_window"],
        },
        "templates": {
            "core_logic.py": """from __future__ import annotations


def calculate_summary(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0.0, "total": 0.0, "average": 0.0}
    total = float(sum(values))
    return {"count": float(len(values)), "total": round(total, 4), "average": round(total / len(values), 4)}
""",
            "app_gui.py": """from __future__ import annotations

import tkinter as tk
from core_logic import calculate_summary


def create_main_window() -> tk.Tk:
    root = tk.Tk()
    root.title("{project_name}")
    root.geometry("480x320")
    lbl = tk.Label(root, text="{project_name} Hazır")
    lbl.pack(pady=16)
    return root


if __name__ == "__main__":
    summary = calculate_summary([10.0, 20.0, 30.0])
    if summary["count"] > 0:
        win = create_main_window()
        win.mainloop()
""",
            "requirements.txt": "pyinstaller>=6.0.0\n",
        },
    },
    "cli_automation": {
        "id": "cli_automation",
        "title": "Komut Satırı (CLI) ve Otomasyon Aracı",
        "keywords": ("cli", "komut satırı", "komut satiri", "argparse", "otomasyon", "script", "batch", "terminal"),
        "required_files": ["cli.py", "processor.py"],
        "interface_contracts": {
            "python_functions": ["build_parser", "run_pipeline"],
        },
        "templates": {
            "processor.py": """from __future__ import annotations


def run_pipeline(items: list[str]) -> dict[str, object]:
    cleaned = [x.strip() for x in items if x.strip()]
    return {"processed_count": len(cleaned), "items": cleaned}
""",
            "cli.py": """from __future__ import annotations

import argparse
from processor import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="{project_name}")
    parser.add_argument("--items", nargs="*", default=["sample_a", "sample_b"])
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result = run_pipeline(args.items)
    print(f"Processed: {{result['processed_count']}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
""",
        },
    },
    "data_science_ml": {
        "id": "data_science_ml",
        "title": "Veri Bilimi ve Makine Öğrenmesi Hattı",
        "keywords": ("veri bilimi", "data science", "makine öğrenmesi", "makine ogrenmesi", "ml", "regresyon", "tahmin", "analitik", "numpy"),
        "required_files": ["pipeline.py", "metrics.py", "requirements.txt"],
        "interface_contracts": {
            "python_functions": ["train_linear_model", "evaluate_predictions"],
        },
        "templates": {
            "metrics.py": """from __future__ import annotations

import math


def evaluate_predictions(y_true: list[float], y_pred: list[float]) -> dict[str, float]:
    n = min(len(y_true), len(y_pred))
    if n == 0:
        return {"rmse": 0.0, "mae": 0.0}
    sq_err = sum((y_true[i] - y_pred[i]) ** 2 for i in range(n)) / n
    abs_err = sum(abs(y_true[i] - y_pred[i]) for i in range(n)) / n
    return {"rmse": round(math.sqrt(sq_err), 6), "mae": round(abs_err, 6)}
""",
            "pipeline.py": """from __future__ import annotations

from metrics import evaluate_predictions


def train_linear_model(xs: list[float], ys: list[float]) -> dict[str, object]:
    n = min(len(xs), len(ys))
    if n < 2:
        return {"slope": 0.0, "intercept": 0.0, "metrics": {"rmse": 0.0, "mae": 0.0}}
    mean_x = sum(xs[:n]) / n
    mean_y = sum(ys[:n]) / n
    num = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    den = sum((xs[i] - mean_x) ** 2 for i in range(n)) or 1.0
    slope = num / den
    intercept = mean_y - slope * mean_x
    preds = [slope * xs[i] + intercept for i in range(n)]
    return {
        "slope": round(slope, 6),
        "intercept": round(intercept, 6),
        "metrics": evaluate_predictions(ys[:n], preds),
    }
""",
            "requirements.txt": "numpy>=1.26.0\n",
        },
    },
}


def detect_archetype(prompt: str) -> str:
    """Detect the best-matching archetype ID from a user prompt."""
    lower = (prompt or "").lower()
    best_arch = "web_ecommerce"
    best_score = 0
    for arch_id, spec in ARCHETYPES.items():
        score = sum(1 for kw in spec["keywords"] if kw in lower)
        if score > best_score:
            best_score = score
            best_arch = arch_id
    return best_arch


def get_archetype_blueprint(archetype: str, project_name: str = "Enterprise AI App") -> dict[str, Any]:
    """Return the blueprint specification and starter file templates for an archetype."""
    arch_key = archetype if archetype in ARCHETYPES else detect_archetype(archetype)
    spec = ARCHETYPES[arch_key]
    clean_name = (project_name or "Enterprise AI App").strip() or "Enterprise AI App"

    rendered_files: dict[str, str] = {}
    for filename, tpl in spec["templates"].items():
        if "{project_name}" in tpl:
            rendered_files[filename] = tpl.replace("{project_name}", clean_name).replace("{{", "{").replace("}}", "}")
        else:
            rendered_files[filename] = tpl

    return {
        "archetype": arch_key,
        "title": spec["title"],
        "project_name": clean_name,
        "required_files": list(spec["required_files"]),
        "interface_contracts": dict(spec["interface_contracts"]),
        "files": rendered_files,
    }
