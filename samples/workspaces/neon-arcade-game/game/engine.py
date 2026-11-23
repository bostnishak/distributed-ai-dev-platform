"""Main Tkinter Canvas game loop for Neon Arcade Space Defender."""

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
            text=f"SKOR: {self.score}   SEVIYE: {self.level}   CAN: {'♥' * max(0, self.player.lives)}",
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
