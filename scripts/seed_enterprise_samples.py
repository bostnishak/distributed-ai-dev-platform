"""Seed real, verified enterprise sample results for both modules:
1. CNC Technical Drawing Ballooning (PDF, PNG, Ballooned PNG/PDF, Excel .xlsx, Word .docx)
2. E-Commerce Web Application Workspace (multi-file HTML/CSS/JS, live previewable in Kod Stüdyosu)
3. Playable Python Arcade Game Workspace + compiled Windows .exe (via PyInstaller)

Outputs are written to both `master/data/` (so they show up immediately in the web UI)
and `samples/` (for easy sharing/demoing to the company).
"""

from __future__ import annotations

import asyncio
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER_DIR = ROOT / "master"
sys.path.insert(0, str(MASTER_DIR))

import cnc_api  # noqa: E402
import config  # noqa: E402
import workspace_builder as wb  # noqa: E402

SAMPLES_DIR = ROOT / "samples"


async def seed_cnc_sample() -> dict:
    job = await cnc_api.create_cnc_demo()
    src_dir = config.CNC_JOBS_DIR / job["id"]
    dst_dir = SAMPLES_DIR / "cnc_ballooning"
    dst_dir.mkdir(parents=True, exist_ok=True)
    for fname in ("source.pdf", "original.png", "ballooned.png", "ballooned.pdf", "report.xlsx", "report.docx", "job.json"):
        p = src_dir / fname
        if p.exists():
            shutil.copy2(p, dst_dir / fname)
    return job


def seed_ecommerce_workspace() -> Path:
    ws_id = "cnc-yedek-parca-store"
    ws_dir = wb.safe_workspace_dir(ws_id)
    if ws_dir.exists():
        shutil.rmtree(ws_dir)
    ws_dir.mkdir(parents=True, exist_ok=True)

    files: dict[str, str] = {
        "index.html": """<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ProCNC Store — Endüstriyel CNC Parça & Takım E-Ticaret</title>
  <link rel="stylesheet" href="css/styles.css">
</head>
<body>
  <header class="navbar">
    <div class="container nav-inner">
      <div class="logo">ProCNC <span>Store</span></div>
      <input id="searchInput" type="search" placeholder="Rulman, freze, pens, kumpas ara..." />
      <button id="cartToggle" class="cart-btn">Sepet (<span id="cartCount">0</span>)</button>
    </div>
  </header>

  <section class="hero">
    <div class="container">
      <h1>Hassas CNC Parçaları & Kalite Kontrol Ekipmanları</h1>
      <p>ISO 2768-mK sertifikalı talaşlı imalat bileşenleri, karbür kesici takımlar ve ölçüm cihazları aynı gün kargoda.</p>
      <div class="filters" id="categoryFilters"></div>
    </div>
  </section>

  <main class="container">
    <div id="productGrid" class="product-grid"></div>
  </main>

  <aside id="cartDrawer" class="cart-drawer" hidden>
    <div class="cart-head">
      <h2>Sepetim</h2>
      <button id="closeCart" class="icon-btn">✕</button>
    </div>
    <div id="cartItems" class="cart-items"></div>
    <div class="cart-foot">
      <div class="coupon-row">
        <input id="couponInput" placeholder="Kupon kodu (CNC10)" />
        <button id="applyCoupon" class="btn-secondary">Uygula</button>
      </div>
      <div class="total-row"><span>Toplam:</span><strong id="cartTotal">0 ₺</strong></div>
      <button id="checkoutBtn" class="btn-primary full">Siparişi Tamamla</button>
    </div>
  </aside>

  <div id="toast" class="toast" hidden></div>

  <script src="js/products.js"></script>
  <script src="js/cart.js"></script>
  <script src="js/app.js"></script>
</body>
</html>
""",
        "css/styles.css": """* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: "Segoe UI", system-ui, sans-serif; background: #0f172a; color: #f1f5f9; line-height: 1.5; }
.container { max-width: 1180px; margin: 0 auto; padding: 0 20px; }
.navbar { background: #1e293b; border-bottom: 1px solid #334155; position: sticky; top: 0; z-index: 20; }
.nav-inner { display: flex; align-items: center; gap: 16px; padding: 14px 20px; flex-wrap: wrap; }
.logo { font-size: 20px; font-weight: 800; letter-spacing: -0.02em; }
.logo span { color: #38bdf8; }
#searchInput {
  flex: 1; min-width: 220px; background: #0f172a; border: 1px solid #334155;
  color: #f8fafc; padding: 9px 14px; border-radius: 10px; font-size: 14px;
}
.cart-btn, .btn-primary, .btn-secondary {
  border: none; border-radius: 10px; padding: 9px 16px; cursor: pointer; font-weight: 600; font-size: 13.5px;
}
.cart-btn, .btn-primary { background: #2563eb; color: #fff; }
.cart-btn:hover, .btn-primary:hover { background: #1d4ed8; }
.btn-secondary { background: #334155; color: #f8fafc; }
.full { width: 100%; margin-top: 10px; padding: 12px; }

.hero { padding: 36px 0 24px; background: linear-gradient(135deg, #0f172a, #1e1b4b); border-bottom: 1px solid #1e293b; }
.hero h1 { font-size: 30px; margin-bottom: 8px; }
.hero p { color: #94a3b8; max-width: 680px; margin-bottom: 18px; }
.filters { display: flex; gap: 8px; flex-wrap: wrap; }
.filter-btn {
  background: #1e293b; color: #cbd5e1; border: 1px solid #334155;
  padding: 7px 14px; border-radius: 999px; cursor: pointer; font-size: 13px;
}
.filter-btn.active { background: #38bdf8; color: #0f172a; border-color: #38bdf8; font-weight: 700; }

.product-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 18px; padding: 26px 0 48px;
}
.card {
  background: #1e293b; border: 1px solid #334155; border-radius: 14px; padding: 18px;
  display: flex; flex-direction: column; gap: 10px; transition: transform 0.15s;
}
.card:hover { transform: translateY(-3px); border-color: #38bdf8; }
.card-badge { font-size: 11px; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 700; }
.card-icon { font-size: 38px; text-align: center; padding: 14px; background: #0f172a; border-radius: 10px; }
.card h3 { font-size: 16px; }
.card p { font-size: 13px; color: #94a3b8; flex: 1; }
.card-foot { display: flex; align-items: center; justify-content: space-between; margin-top: 6px; }
.price { font-size: 18px; font-weight: 800; color: #4ade80; }

.cart-drawer {
  position: fixed; right: 0; top: 0; bottom: 0; width: 360px; max-width: 92vw;
  background: #1e293b; border-left: 1px solid #334155; z-index: 40;
  display: flex; flex-direction: column; padding: 18px; box-shadow: -8px 0 30px rgba(0,0,0,0.45);
}
.cart-head { display: flex; justify-content: space-between; align-items: center; padding-bottom: 12px; border-bottom: 1px solid #334155; }
.icon-btn { background: transparent; border: none; color: #94a3b8; font-size: 18px; cursor: pointer; }
.cart-items { flex: 1; overflow-y: auto; padding: 12px 0; display: flex; flex-direction: column; gap: 10px; }
.cart-item { background: #0f172a; border-radius: 10px; padding: 10px 12px; display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.qty-ctrl { display: flex; align-items: center; gap: 6px; }
.qty-ctrl button { width: 24px; height: 24px; border-radius: 6px; border: none; background: #334155; color: #fff; cursor: pointer; }
.cart-foot { border-top: 1px solid #334155; padding-top: 12px; }
.coupon-row { display: flex; gap: 6px; margin-bottom: 10px; }
.coupon-row input { flex: 1; background: #0f172a; border: 1px solid #334155; color: #fff; padding: 7px 10px; border-radius: 8px; }
.total-row { display: flex; justify-content: space-between; font-size: 18px; }
.toast {
  position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
  background: #16a34a; color: #fff; padding: 10px 18px; border-radius: 10px; font-weight: 600; z-index: 50;
}
""",
        "js/products.js": """window.PRODUCTS = [
  { id: 1, name: "AISI 4140 Rulman Yatağı Flanşı (Ø42 H7)", category: "CNC Parçalar", price: 1450, icon: "FLN-042", desc: "5 eksen CNC işlenmiş, Ra 0.8 taşlanmış hassas flanş." },
  { id: 2, name: "Karbür 4 Ağızlı Parmak Freze Ø10", category: "Kesici Takımlar", price: 890, icon: "FRZ-010", desc: "TiAlN kaplamalı, yüksek hızlı çelik işleme için." },
  { id: 3, name: "Mitutoyo Tipi Dijital Kumpas 0-150mm", category: "Ölçüm Aletleri", price: 3250, icon: "KMP-150", desc: "0.01 mm çözünürlük, IP67 su ve soğutma sıvısı korumalı." },
  { id: 4, name: "ER32 Hassas Pens Seti (18 Parça)", category: "Tutucular", price: 4100, icon: "ER32-18", desc: "0.005 mm salgı hassasiyeti, DIN 6499 standardı." },
  { id: 5, name: "İç Çap Mikrometresi 25-50 mm", category: "Ölçüm Aletleri", price: 5600, icon: "MKR-050", desc: "H7 geçme kontrolü için 3 ayaklı hassas ölçüm." },
  { id: 6, name: "Al 7075-T651 Havacılık Bağlantı Braketi", category: "CNC Parçalar", price: 2150, icon: "BRK-7075", desc: "AS9102 FAI raporlu, eloksal kaplamalı hafif gövde." },
];
""",
        "js/cart.js": """window.CartStore = (() => {
  let items = [];
  let discount = 0;

  function add(product) {
    const existing = items.find((i) => i.id === product.id);
    if (existing) existing.qty += 1;
    else items.push({ ...product, qty: 1 });
  }
  function updateQty(id, delta) {
    const it = items.find((i) => i.id === id);
    if (!it) return;
    it.qty += delta;
    if (it.qty <= 0) items = items.filter((i) => i.id !== id);
  }
  function applyCoupon(code) {
    if (code.trim().toUpperCase() === "CNC10") {
      discount = 0.10;
      return true;
    }
    return false;
  }
  function clear() { items = []; discount = 0; }
  function total() {
    const sub = items.reduce((s, i) => s + i.price * i.qty, 0);
    return Math.round(sub * (1 - discount));
  }
  return { getItems: () => items, add, updateQty, applyCoupon, clear, total };
})();
""",
        "js/app.js": """(() => {
  let activeCategory = "Tümü";
  const grid = document.getElementById("productGrid");
  const filters = document.getElementById("categoryFilters");
  const search = document.getElementById("searchInput");
  const drawer = document.getElementById("cartDrawer");
  const toast = document.getElementById("toast");

  function showToast(msg) {
    toast.textContent = msg;
    toast.hidden = false;
    setTimeout(() => { toast.hidden = true; }, 2200);
  }

  function renderFilters() {
    const cats = ["Tümü", ...new Set(window.PRODUCTS.map((p) => p.category))];
    filters.innerHTML = "";
    cats.forEach((cat) => {
      const btn = document.createElement("button");
      btn.className = "filter-btn" + (cat === activeCategory ? " active" : "");
      btn.textContent = cat;
      btn.onclick = () => { activeCategory = cat; renderFilters(); renderProducts(); };
      filters.appendChild(btn);
    });
  }

  function renderProducts() {
    const q = search.value.trim().toLowerCase();
    const list = window.PRODUCTS.filter((p) =>
      (activeCategory === "Tümü" || p.category === activeCategory) &&
      (!q || p.name.toLowerCase().includes(q) || p.desc.toLowerCase().includes(q))
    );
    grid.innerHTML = "";
    list.forEach((p) => {
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <div class="card-badge">${p.category}</div>
        <div class="card-icon">${p.icon}</div>
        <h3>${p.name}</h3>
        <p>${p.desc}</p>
        <div class="card-foot">
          <span class="price">${p.price.toLocaleString("tr-TR")} ₺</span>
          <button class="btn-primary">Sepete Ekle</button>
        </div>
      `;
      card.querySelector("button").onclick = () => {
        window.CartStore.add(p);
        renderCart();
        showToast(`${p.name} sepete eklendi`);
      };
      grid.appendChild(card);
    });
  }

  function renderCart() {
    const items = window.CartStore.getItems();
    document.getElementById("cartCount").textContent = items.reduce((s, i) => s + i.qty, 0);
    document.getElementById("cartTotal").textContent = `${window.CartStore.total().toLocaleString("tr-TR")} ₺`;
    const box = document.getElementById("cartItems");
    box.innerHTML = items.length ? "" : '<p style="color:#94a3b8;font-size:13px;">Sepetiniz boş.</p>';
    items.forEach((it) => {
      const row = document.createElement("div");
      row.className = "cart-item";
      row.innerHTML = `
        <div><strong>${it.name}</strong><div style="font-size:12px;color:#94a3b8;">${it.price.toLocaleString("tr-TR")} ₺</div></div>
        <div class="qty-ctrl">
          <button class="minus">-</button><span>${it.qty}</span><button class="plus">+</button>
        </div>
      `;
      row.querySelector(".minus").onclick = () => { window.CartStore.updateQty(it.id, -1); renderCart(); };
      row.querySelector(".plus").onclick = () => { window.CartStore.updateQty(it.id, 1); renderCart(); };
      box.appendChild(row);
    });
  }

  document.getElementById("cartToggle").onclick = () => { drawer.hidden = false; };
  document.getElementById("closeCart").onclick = () => { drawer.hidden = true; };
  document.getElementById("applyCoupon").onclick = () => {
    const ok = window.CartStore.applyCoupon(document.getElementById("couponInput").value);
    renderCart();
    showToast(ok ? "CNC10 kuponu uygulandı (%10 indirim)!" : "Geçersiz kupon kodu (CNC10 deneyin)");
  };
  document.getElementById("checkoutBtn").onclick = () => {
    if (!window.CartStore.getItems().length) return showToast("Sepetiniz boş!");
    window.CartStore.clear();
    renderCart();
    drawer.hidden = true;
    showToast("Siparişiniz başarıyla alındı!");
  };
  search.oninput = renderProducts;

  renderFilters();
  renderProducts();
  renderCart();
})();
""",
        "README.md": "# ProCNC Store (Örnek E-Ticaret Projesi)\n\nKod Stüdyosu tarafından oluşturulan çok dosyalı e-ticaret vitrini. `▶ Canlı Önizleme` ile anında test edebilirsiniz.\n",
    }

    for rel, content in files.items():
        p = ws_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    wb.save_workspace_meta(ws_dir, {
        "id": ws_id,
        "name": "ProCNC E-Ticaret Sitesi",
        "project_type": "web",
        "description": "Kategori filtreli, canlı sepetli ve indirim kuponlu modern CNC e-ticaret vitrini.",
        "entry_point": "index.html",
        "model": "qwen2.5-coder:7b",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    })

    sample_out = SAMPLES_DIR / "workspaces" / ws_id
    if sample_out.exists():
        shutil.rmtree(sample_out)
    shutil.copytree(ws_dir, sample_out)
    return ws_dir


async def seed_game_workspace_and_exe() -> tuple[Path, dict]:
    ws_id = "neon-arcade-game"
    ws_dir = wb.safe_workspace_dir(ws_id)
    if ws_dir.exists():
        shutil.rmtree(ws_dir)
    ws_dir.mkdir(parents=True, exist_ok=True)

    files: dict[str, str] = {
        "main.py": '''"""Neon Arcade Space Defender — Entry Point."""

from game.engine import NeonArcadeApp


def main() -> None:
    app = NeonArcadeApp()
    app.run()


if __name__ == "__main__":
    main()
''',
        "game/__init__.py": "",
        "game/config.py": '''"""Game configuration and neon color palette."""

WIDTH = 720
HEIGHT = 540
FPS_MS = 16
BG_COLOR = "#090d16"
PLAYER_COLOR = "#38bdf8"
BULLET_COLOR = "#facc15"
ENEMY_COLOR = "#f43f5e"
TEXT_COLOR = "#f8fafc"
''',
        "game/entities.py": '''"""Player, Bullet, and Enemy data structures."""

from dataclasses import dataclass


@dataclass
class Player:
    x: float
    y: float
    width: int = 44
    height: int = 20
    speed: float = 8.0
    lives: int = 3


@dataclass
class Bullet:
    x: float
    y: float
    speed: float = 11.0


@dataclass
class Enemy:
    x: float
    y: float
    size: int = 26
    speed: float = 2.4
''',
        "game/engine.py": '''"""Main Tkinter Canvas game loop for Neon Arcade Space Defender."""

from __future__ import annotations

import random
import tkinter as tk

from game.config import BG_COLOR, BULLET_COLOR, ENEMY_COLOR, FPS_MS, HEIGHT, PLAYER_COLOR, TEXT_COLOR, WIDTH
from game.entities import Bullet, Enemy, Player


class NeonArcadeApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Neon Arcade Space Defender")
        self.root.resizable(False, False)
        self.canvas = tk.Canvas(self.root, width=WIDTH, height=HEIGHT, bg=BG_COLOR, highlightthickness=0)
        self.canvas.pack()

        self.keys: set[str] = set()
        self.root.bind("<KeyPress>", self._on_key_down)
        self.root.bind("<KeyRelease>", self._on_key_up)
        self.reset()

    def reset(self) -> None:
        self.player = Player(x=WIDTH / 2, y=HEIGHT - 44)
        self.bullets: list[Bullet] = []
        self.enemies: list[Enemy] = []
        self.score = 0
        self.level = 1
        self.frame = 0
        self.paused = False
        self.game_over = False

    def _on_key_down(self, event: tk.Event) -> None:
        sym = event.keysym.lower()
        self.keys.add(sym)
        if sym == "space" and not self.game_over and not self.paused:
            self.bullets.append(Bullet(x=self.player.x, y=self.player.y - 16))
        elif sym == "p" and not self.game_over:
            self.paused = not self.paused
        elif sym == "r" and self.game_over:
            self.reset()

    def _on_key_up(self, event: tk.Event) -> None:
        self.keys.discard(event.keysym.lower())

    def _step(self) -> None:
        if not self.paused and not self.game_over:
            self.frame += 1
            if "left" in self.keys or "a" in self.keys:
                self.player.x = max(28, self.player.x - self.player.speed)
            if "right" in self.keys or "d" in self.keys:
                self.player.x = min(WIDTH - 28, self.player.x + self.player.speed)

            spawn_every = max(18, 48 - self.level * 4)
            if self.frame % spawn_every == 0:
                self.enemies.append(Enemy(x=random.randint(30, WIDTH - 30), y=-20, speed=2.2 + self.level * 0.45))

            for b in self.bullets:
                b.y -= b.speed
            self.bullets = [b for b in self.bullets if b.y > -10]

            for e in self.enemies:
                e.y += e.speed

            # Collisions
            survivors: list[Enemy] = []
            for e in self.enemies:
                hit = False
                for b in list(self.bullets):
                    if abs(b.x - e.x) < e.size * 0.7 and abs(b.y - e.y) < e.size * 0.7:
                        self.bullets.remove(b)
                        self.score += 10
                        self.level = 1 + self.score // 100
                        hit = True
                        break
                if hit:
                    continue
                if e.y > HEIGHT - 20:
                    self.player.lives -= 1
                    if self.player.lives <= 0:
                        self.game_over = True
                else:
                    survivors.append(e)
            self.enemies = survivors

        self._render()
        self.root.after(FPS_MS, self._step)

    def _render(self) -> None:
        self.canvas.delete("all")
        # HUD
        self.canvas.create_text(
            14, 14, anchor="nw", fill=TEXT_COLOR, font=("Consolas", 13, "bold"),
            text=f"SKOR: {self.score}   SEVIYE: {self.level}   CAN: {'*' * max(0, self.player.lives)}",
        )
        self.canvas.create_text(
            WIDTH - 14, 14, anchor="ne", fill="#64748b", font=("Consolas", 10),
            text="A/D veya ←/→: Hareket  |  SPACE: Ates  |  P: Duraklat",
        )
        # Player ship
        px, py = self.player.x, self.player.y
        self.canvas.create_polygon(px, py - 18, px - 22, py + 12, px + 22, py + 12, fill=PLAYER_COLOR, outline="#e0f2fe")
        # Bullets
        for b in self.bullets:
            self.canvas.create_rectangle(b.x - 2, b.y - 8, b.x + 2, b.y + 4, fill=BULLET_COLOR, outline="")
        # Enemies
        for e in self.enemies:
            half = e.size / 2
            self.canvas.create_rectangle(e.x - half, e.y - half, e.x + half, e.y + half, fill=ENEMY_COLOR, outline="#fecdd3")

        if self.paused:
            self.canvas.create_text(WIDTH / 2, HEIGHT / 2, fill="#facc15", font=("Consolas", 26, "bold"), text="DURAKLATILDI (P)")
        if self.game_over:
            self.canvas.create_text(WIDTH / 2, HEIGHT / 2 - 20, fill="#f43f5e", font=("Consolas", 28, "bold"), text="OYUN BITTI")
            self.canvas.create_text(WIDTH / 2, HEIGHT / 2 + 24, fill=TEXT_COLOR, font=("Consolas", 14), text=f"Toplam Skor: {self.score}  |  Yeniden baslamak icin R")

    def run(self) -> None:
        self._step()
        self.root.mainloop()
''',
        "README.md": "# Neon Arcade Space Defender (.EXE Oyun Örneği)\n\nPython Tkinter ile geliştirilmiş modüler arcade oyunu. Kod Stüdyosu içindeki `.EXE Oluştur` butonuyla tek dosyalık Windows `.exe` olarak derlenmiştir.\n",
    }

    for rel, content in files.items():
        p = ws_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    wb.save_workspace_meta(ws_dir, {
        "id": ws_id,
        "name": "Neon Arcade Game",
        "project_type": "game",
        "description": "Modüler Python Tkinter uzay savunma oyunu — tek dosyalık Windows .EXE olarak derlenebilir.",
        "entry_point": "main.py",
        "model": "qwen2.5-coder:7b",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    })

    # Compile real Windows .EXE!
    build_res = await wb.build_workspace_exe(ws_id, windowed=True)

    sample_out = SAMPLES_DIR / "workspaces" / ws_id
    if sample_out.exists():
        shutil.rmtree(sample_out)
    shutil.copytree(ws_dir, sample_out)
    return ws_dir, build_res


async def main() -> None:
    print("1/3 Seeding CNC Technical Drawing Ballooning sample...")
    cnc_job = await seed_cnc_sample()
    print(f"    OK: {cnc_job['id']} -> {len(cnc_job['balloons'])} balloons (PNG/PDF/XLSX/DOCX generated)")

    print("2/3 Seeding E-Commerce Website Workspace sample...")
    ecom_dir = seed_ecommerce_workspace()
    print(f"    OK: {ecom_dir}")

    print("3/3 Seeding Neon Arcade Game Workspace & compiling real Windows .EXE...")
    game_dir, build_res = await seed_game_workspace_and_exe()
    print(f"    OK: {game_dir} -> EXE build ok={build_res['ok']} file={build_res.get('exe_name')} size={build_res.get('exe_size')}")
    if not build_res["ok"]:
        print(build_res.get("error"))
        print(build_res.get("logs", "")[-1000:])


if __name__ == "__main__":
    asyncio.run(main())
