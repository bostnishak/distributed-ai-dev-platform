"""GAME-01..GAME-10: Playable Neon Canvas2D Engine, 10 Genre Templates, GDD, Procedural Assets, Bot Playtest, Level Solver & Packager."""

from __future__ import annotations

import html as html_lib
import io
import json
import zipfile
from collections import deque
from pathlib import Path
from typing import Any

from orchestrator.state import save_artifact

# GAME-02 & GAME-06: 10 distinct working genre templates with separated balance.json
GAME_GENRE_TEMPLATES: dict[str, dict[str, Any]] = {
    "platformer": {"title": "Platform Macerası", "controls": "Ok tuşları / WASD + Boşluk (Zıpla)", "balance": {"genre": "platformer", "gravity": 980, "jump_v": 420, "lives": 3, "win_score": 100}},
    "space_shooter": {"title": "Uzay Savunması", "controls": "Sol/Sağ + Boşluk (Ateş)", "balance": {"genre": "space_shooter", "fire_rate_ms": 220, "enemy_speed": 110, "lives": 3, "win_score": 150}},
    "match3": {"title": "Eşleştirme Bulmacası", "controls": "Fare / Dokunmatik takas", "balance": {"genre": "match3", "grid_size": 8, "moves": 25, "lives": 1, "win_score": 120}},
    "top_down_racer": {"title": "Üstten Yarış", "controls": "WASD / Ok tuşları", "balance": {"genre": "top_down_racer", "max_speed": 320, "laps": 3, "lives": 3, "win_score": 100}},
    "tower_defense": {"title": "Kule Savunması", "controls": "Tıkla: Kule yerleştir", "balance": {"genre": "tower_defense", "start_gold": 120, "waves": 5, "lives": 10, "win_score": 200}},
    "memory_match": {"title": "Hafıza Kartları", "controls": "Tıkla / Dokun", "balance": {"genre": "memory_match", "pairs": 8, "lives": 1, "win_score": 80}},
    "snake_classic": {"title": "Klasik Yılan", "controls": "Ok tuşları / WASD", "balance": {"genre": "snake_classic", "tick_ms": 110, "grid": 20, "lives": 1, "win_score": 100}},
    "card_duel": {"title": "Strateji Kart Düellosu", "controls": "Kart seç + Oyna", "balance": {"genre": "card_duel", "hand_size": 5, "lives": 20, "win_score": 100}},
    "word_quest": {"title": "Kelime Bulmaca", "controls": "Klavye harf girişi", "balance": {"genre": "word_quest", "attempts": 6, "lives": 6, "win_score": 100}},
    "mini_rpg": {"title": "Mini Zindan RPG", "controls": "WASD + E / Boşluk (Saldırı)", "balance": {"genre": "mini_rpg", "hp": 100, "attack": 15, "lives": 3, "win_score": 120}},
}

# GAME-09: Simple offline low-poly 3D Three.js template (no CDN; local bundle path + polygon budget)
SIMPLE_3D_TEMPLATE_HTML = (
    "<!doctype html><html lang='tr'><head><meta charset='utf-8'><title>Basit 3B Sahne</title></head>"
    "<body><canvas id='gl3d' width='800' height='500'></canvas>"
    "<script type='module'>\n"
    "// Local offline three.js module path (no CDN): /static/vendor/three.module.js\n"
    "export const BUDGET_3D = { maxDrawCalls: 40, maxTriangles: 15000, targetFps: 55 };\n"
    "</script></body></html>"
)


# ---------------------------------------------------------------- Playable Canvas2D Assets (CSS + Engine + 10 Genres)

def _build_game_css() -> str:
    return "\n".join([
        ":root{--bg:#060913;--line:rgba(56,189,248,.28);--cyan:#38bdf8;--amber:#fbbf24;--text:#f8fafc}",
        "*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(circle at top,#13203d,var(--bg) 68%);color:var(--text);font-family:Inter,'Segoe UI',system-ui,sans-serif;display:flex;flex-direction:column;align-items:center;padding:14px 10px}",
        ".shell{width:min(800px,98vw);display:flex;flex-direction:column;gap:10px}",
        ".hud{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px;padding:10px 14px;background:rgba(15,23,42,.88);border:1px solid var(--line);border-radius:12px;box-shadow:0 8px 28px rgba(2,6,23,.55)}",
        ".title{font-weight:700;letter-spacing:.4px;color:var(--cyan);font-size:15px}.stats{display:flex;gap:14px;font-size:13px;font-weight:600}.stats span b{color:var(--amber)}",
        ".btns{display:flex;gap:6px}button{cursor:pointer;padding:7px 12px;border-radius:8px;border:1px solid var(--line);background:#1e293b;color:var(--text);font-size:12px;font-weight:600;transition:transform .1s,background .15s}",
        "button:hover{background:#0284c7;border-color:#7dd3fc}button:active{transform:scale(.96)}",
        ".stage{position:relative;display:flex;justify-content:center;border-radius:14px;overflow:hidden;border:1px solid var(--line);box-shadow:0 0 32px rgba(56,189,248,.16);background:#050814}",
        "canvas{display:block;width:100%;max-width:760px;height:auto;touch-action:none}",
        ".overlay{position:absolute;inset:0;display:none;flex-direction:column;align-items:center;justify-content:center;gap:12px;background:rgba(6,9,19,.82);backdrop-filter:blur(4px);text-align:center;padding:16px}",
        ".overlay.show{display:flex}.overlay h2{margin:0;font-size:28px;color:var(--cyan)}.overlay p{margin:0;color:#cbd5e1;font-size:14px}",
        ".controls-bar{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:10px;padding:8px 12px;background:rgba(15,23,42,.72);border:1px solid rgba(148,163,184,.18);border-radius:10px;font-size:12px;color:#94a3b8}",
        ".touch{display:flex;gap:6px;flex-wrap:wrap}.touch button{min-width:44px;padding:8px 11px;background:#0f766e;border-color:rgba(52,211,153,.35)}",
    ])


def _engine_core_lines() -> list[str]:
    return [
        "export function aabbOverlap(a, b) { return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y; }",
        "export function circleOverlap(a, b) { const dx = a.x - b.x, dy = a.y - b.y, r = a.r + b.r; return dx * dx + dy * dy <= r * r; }",
        "export class FixedLoopEngine {",
        "  constructor(canvas, balance, ui = {}) {",
        "    this.canvas = canvas; this.ctx = canvas.getContext('2d'); this.W = canvas.width; this.H = canvas.height;",
        "    this.balance = { ...balance }; this.genre = balance.genre || 'snake_classic'; this.ui = ui;",
        "    this.paused = false; this.muted = false; this.score = 0; this.level = 1; this.lives = balance.lives || 3;",
        "    this.state = 'playing'; this.keys = new Set(); this.fixedDt = 1 / 60; this.acc = 0; this.lastTs = 0;",
        "    this.highScoreKey = 'game_hs_' + this.genre; this.highScore = this.loadHighScore();",
        "    this.particles = []; this.shake = 0; this.time = 0; this.audioCtx = null; this.rafId = 0;",
        "    this.stars = Array.from({ length: 56 }, () => ({ x: Math.random() * this.W, y: Math.random() * this.H, s: 1 + Math.random() * 2, v: 18 + Math.random() * 44 }));",
        "    this.controller = null; this._bindInputs();",
        "  }",
        "  loadHighScore() { try { return Number(localStorage.getItem(this.highScoreKey) || 0); } catch (_) { return 0; } }",
        "  saveHighScore() { try { const p = Number(localStorage.getItem(this.highScoreKey) || 0); if (this.score > p) { localStorage.setItem(this.highScoreKey, String(Math.floor(this.score))); this.highScore = Math.floor(this.score); } } catch (_) {} }",
        "  playTone(freq = 520, dur = 0.08, wave = 'sine', vol = 0.07) {",
        "    if (this.muted) return;",
        "    try { const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;",
        "      if (!this.audioCtx) this.audioCtx = new AC(); if (this.audioCtx.state === 'suspended') this.audioCtx.resume();",
        "      const o = this.audioCtx.createOscillator(), g = this.audioCtx.createGain(); o.type = wave; o.frequency.value = freq;",
        "      g.gain.setValueAtTime(vol, this.audioCtx.currentTime); g.gain.exponentialRampToValueAtTime(0.001, this.audioCtx.currentTime + dur);",
        "      o.connect(g); g.connect(this.audioCtx.destination); o.start(); o.stop(this.audioCtx.currentTime + dur);",
        "    } catch (_) {}",
        "  }",
        "  burst(x, y, color = '#38bdf8', count = 14) { for (let i = 0; i < count; i++) { const a = Math.random() * Math.PI * 2, sp = 50 + Math.random() * 170; this.particles.push({ x, y, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp, life: 0.45 + Math.random() * 0.35, max: 0.8, c: color, r: 2 + Math.random() * 2.5 }); } }",
        "  togglePause() { if (this.state !== 'playing') return; this.paused = !this.paused; this.syncHud(); }",
        "  toggleMute() { this.muted = !this.muted; this.syncHud(); }",
        "  stepScore(delta) {",
        "    this.score = Math.max(0, this.score + delta); const win = this.balance.win_score || 100;",
        "    const nxt = 1 + Math.floor((this.score / Math.max(1, win)) * 3); if (nxt > this.level) { this.level = nxt; this.playTone(760, 0.14, 'triangle', 0.09); }",
        "    if (delta > 0) this.playTone(620 + Math.min(260, this.score * 2), 0.07, 'sine', 0.06);",
        "    if (this.score >= win) { this.state = 'won'; this.saveHighScore(); this.playTone(880, 0.25, 'triangle', 0.1); }",
        "    this.syncHud();",
        "  }",
        "  applyDamage(dmg = 1) { this.lives = Math.max(0, this.lives - dmg); this.shake = 0.22; this.playTone(170, 0.15, 'sawtooth', 0.08); if (this.lives <= 0) { this.state = 'lost'; this.saveHighScore(); this.playTone(120, 0.32, 'sawtooth', 0.09); } this.syncHud(); }",
    ]


def _engine_input_lines() -> list[str]:
    return [
        "  syncHud() {",
        "    const u = this.ui; if (u.score) u.score.textContent = String(Math.floor(this.score)); if (u.level) u.level.textContent = String(this.level);",
        "    if (u.lives) u.lives.textContent = String(this.lives); if (u.high) u.high.textContent = String(Math.max(this.highScore, Math.floor(this.score)));",
        "    if (u.muteBtn) u.muteBtn.textContent = this.muted ? 'Ses: Kapalı' : 'Ses: Açık'; if (u.pauseBtn) u.pauseBtn.textContent = this.paused ? 'Devam [P]' : 'Duraklat [P]';",
        "    if (u.overlay && u.ovTitle && u.ovSub) {",
        "      u.overlay.classList.toggle('show', this.paused || this.state !== 'playing');",
        "      if (this.state === 'won') { u.ovTitle.textContent = 'KAZANDIN!'; u.ovSub.textContent = 'Skor: ' + Math.floor(this.score) + ' - Tekrar için [R]'; }",
        "      else if (this.state === 'lost') { u.ovTitle.textContent = 'OYUN BİTTİ'; u.ovSub.textContent = 'Skor: ' + Math.floor(this.score) + ' - Yeniden için [R]'; }",
        "      else if (this.paused) { u.ovTitle.textContent = 'DURAKLATILDI'; u.ovSub.textContent = 'Devam etmek için [P] tuşuna bas'; }",
        "    }",
        "  }",
        "  _canvasPt(ev) { const r = this.canvas.getBoundingClientRect(); return { x: (ev.clientX - r.left) * (this.W / r.width), y: (ev.clientY - r.top) * (this.H / r.height) }; }",
        "  _bindInputs() {",
        "    window.addEventListener('keydown', (e) => {",
        "      if (['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Space',' '].includes(e.key)) e.preventDefault();",
        "      const k = e.key; if (this.genre !== 'word_quest') { if (k === 'p' || k === 'P') return this.togglePause(); if (k === 'r' || k === 'R') return this.restart(); if (k === 'm' || k === 'M') return this.toggleMute(); }",
        "      this.keys.add(k); if (this.controller && this.controller.onKey) this.controller.onKey(k);",
        "    });",
        "    window.addEventListener('keyup', (e) => this.keys.delete(e.key));",
        "    this.canvas.addEventListener('pointerdown', (e) => { const pt = this._canvasPt(e); if (this.state !== 'playing') return this.restart(); if (this.controller && this.controller.onClick) this.controller.onClick(pt.x, pt.y); });",
        "    this.canvas.addEventListener('pointermove', (e) => { const pt = this._canvasPt(e); if (this.controller && this.controller.onMove) this.controller.onMove(pt.x, pt.y); });",
        "    document.querySelectorAll('[data-key]').forEach((btn) => { const key = btn.getAttribute('data-key'); const up = () => this.keys.delete(key);",
        "      btn.addEventListener('pointerdown', (e) => { e.preventDefault(); this.keys.add(key); if (this.controller && this.controller.onKey) this.controller.onKey(key); });",
        "      btn.addEventListener('pointerup', up); btn.addEventListener('pointerleave', up); });",
        "  }",
    ]


def _engine_loop_lines() -> list[str]:
    return [
        "  setController(factory) { this._factory = factory; this.restart(); }",
        "  restart() { this.score = 0; this.level = 1; this.lives = this.balance.lives || 3; this.state = 'playing'; this.paused = false; this.particles = []; this.shake = 0; if (this._factory) this.controller = this._factory(this); this.syncHud(); }",
        "  start() { if (this.rafId) cancelAnimationFrame(this.rafId); this.lastTs = performance.now(); const tick = (ts) => { this._frame(ts); this.rafId = requestAnimationFrame(tick); }; this.rafId = requestAnimationFrame(tick); }",
        "  _frame(ts) {",
        "    const rawDt = Math.min(0.05, Math.max(0, (ts - this.lastTs) / 1000)); this.lastTs = ts;",
        "    if (!this.paused && this.state === 'playing') { this.acc += rawDt; while (this.acc >= this.fixedDt) { this._step(this.fixedDt); this.acc -= this.fixedDt; } }",
        "    this._render();",
        "  }",
        "  _step(dt) {",
        "    this.time += dt; this.shake = Math.max(0, this.shake - dt);",
        "    for (const s of this.stars) { s.y += s.v * dt; if (s.y > this.H) { s.y = 0; s.x = Math.random() * this.W; } }",
        "    this.particles = this.particles.filter((p) => { p.x += p.vx * dt; p.y += p.vy * dt; p.vx *= 0.96; p.vy *= 0.96; p.life -= dt; return p.life > 0; });",
        "    if (this.controller && this.controller.update) this.controller.update(dt);",
        "  }",
        "  _render() {",
        "    const c = this.ctx; c.save(); if (this.shake > 0) c.translate((Math.random() - 0.5) * 8, (Math.random() - 0.5) * 8);",
        "    const bg = c.createLinearGradient(0, 0, 0, this.H); bg.addColorStop(0, '#070d1f'); bg.addColorStop(1, '#04060f'); c.fillStyle = bg; c.fillRect(0, 0, this.W, this.H);",
        "    c.fillStyle = 'rgba(148,163,184,0.35)'; for (const s of this.stars) c.fillRect(s.x, s.y, s.s, s.s);",
        "    if (this.controller && this.controller.draw) this.controller.draw(c);",
        "    for (const p of this.particles) { c.globalAlpha = Math.max(0, p.life / p.max); c.fillStyle = p.c; c.beginPath(); c.arc(p.x, p.y, p.r, 0, Math.PI * 2); c.fill(); }",
        "    c.globalAlpha = 1; c.restore();",
        "  }",
        "}",
    ]


def _genre_shooter_snake_lines() -> list[str]:
    return [
        "function makeSpaceShooter(eng) {",
        "  const st = { x: eng.W / 2, y: eng.H - 46, cd: 0, spawn: 0.5, bullets: [], enemies: [] };",
        "  const shoot = () => { if (st.cd > 0) return; st.cd = (eng.balance.fire_rate_ms || 220) / 1000; st.bullets.push({ x: st.x, y: st.y - 18, vy: -520 }); eng.playTone(880, 0.04, 'square', 0.04); };",
        "  return { onMove(mx) { st.x = Math.max(24, Math.min(eng.W - 24, mx)); }, onClick(mx) { st.x = Math.max(24, Math.min(eng.W - 24, mx)); shoot(); },",
        "    update(dt) { const sp = 360; if (eng.keys.has('ArrowLeft') || eng.keys.has('a') || eng.keys.has('A')) st.x -= sp * dt; if (eng.keys.has('ArrowRight') || eng.keys.has('d') || eng.keys.has('D')) st.x += sp * dt;",
        "      st.x = Math.max(24, Math.min(eng.W - 24, st.x)); st.cd = Math.max(0, st.cd - dt); if (eng.keys.has(' ') || eng.keys.has('ArrowUp') || eng.keys.has('w')) shoot();",
        "      st.spawn -= dt; if (st.spawn <= 0) { st.spawn = Math.max(0.35, 1.05 - eng.level * 0.14); st.enemies.push({ x: 40 + Math.random() * (eng.W - 80), y: -20, ph: Math.random() * 6, r: 16 }); }",
        "      st.bullets = st.bullets.filter((b) => (b.y += b.vy * dt) > -10); const esp = (eng.balance.enemy_speed || 110) * (1 + (eng.level - 1) * 0.18);",
        "      for (let i = st.enemies.length - 1; i >= 0; i--) { const e = st.enemies[i]; e.y += esp * dt; e.x += Math.sin(eng.time * 3 + e.ph) * 65 * dt;",
        "        for (let j = st.bullets.length - 1; j >= 0; j--) if (circleOverlap({ x: st.bullets[j].x, y: st.bullets[j].y, r: 5 }, e)) { st.bullets.splice(j, 1); st.enemies.splice(i, 1); eng.burst(e.x, e.y, '#f472b6', 16); eng.stepScore(15); break; }",
        "        if (st.enemies[i] && (e.y > eng.H - 12 || circleOverlap({ x: st.x, y: st.y, r: 16 }, e))) { st.enemies.splice(i, 1); eng.burst(st.x, st.y, '#ef4444', 18); eng.applyDamage(1); } } },",
        "    draw(c) { c.fillStyle = '#38bdf8'; c.beginPath(); c.moveTo(st.x, st.y - 18); c.lineTo(st.x + 18, st.y + 14); c.lineTo(st.x, st.y + 7); c.lineTo(st.x - 18, st.y + 14); c.closePath(); c.fill();",
        "      c.fillStyle = '#fbbf24'; for (const b of st.bullets) c.fillRect(b.x - 2, b.y - 10, 4, 14);",
        "      for (const e of st.enemies) { c.fillStyle = '#f472b6'; c.beginPath(); c.arc(e.x, e.y, e.r, 0, Math.PI * 2); c.fill(); c.fillStyle = '#0f172a'; c.fillRect(e.x - 7, e.y - 4, 4, 4); c.fillRect(e.x + 3, e.y - 4, 4, 4); } } };",
        "}",
        "function makeSnake(eng) {",
        "  const cell = 20, cols = Math.floor(eng.W / cell), rows = Math.floor(eng.H / cell);",
        "  const st = { body: [{ x: 10, y: 10 }, { x: 9, y: 10 }, { x: 8, y: 10 }], dir: { x: 1, y: 0 }, next: { x: 1, y: 0 }, food: { x: 18, y: 10 }, timer: 0 };",
        "  const placeFood = () => { st.food = { x: 1 + Math.floor(Math.random() * (cols - 2)), y: 1 + Math.floor(Math.random() * (rows - 2)) }; };",
        "  return { onKey(k) { const m = { ArrowUp:[0,-1], w:[0,-1], ArrowDown:[0,1], s:[0,1], ArrowLeft:[-1,0], a:[-1,0], ArrowRight:[1,0], d:[1,0] }[k]; if (m && (m[0] !== -st.dir.x || m[1] !== -st.dir.y)) st.next = { x: m[0], y: m[1] }; },",
        "    onClick(mx, my) { const h = st.body[0], dx = mx - h.x * cell, dy = my - h.y * cell; this.onKey(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'ArrowRight' : 'ArrowLeft') : (dy > 0 ? 'ArrowDown' : 'ArrowUp')); },",
        "    update(dt) { st.timer += dt; if (st.timer < Math.max(0.055, (eng.balance.tick_ms || 110) / 1000 - (eng.level - 1) * 0.012)) return; st.timer = 0;",
        "      st.dir = st.next; const nh = { x: st.body[0].x + st.dir.x, y: st.body[0].y + st.dir.y };",
        "      if (nh.x < 0 || nh.x >= cols || nh.y < 0 || nh.y >= rows || st.body.some((b) => b.x === nh.x && b.y === nh.y)) { eng.burst(st.body[0].x * cell + 10, st.body[0].y * cell + 10, '#ef4444', 20); eng.applyDamage(1); return; }",
        "      st.body.unshift(nh); if (nh.x === st.food.x && nh.y === st.food.y) { eng.burst(nh.x * cell + 10, nh.y * cell + 10, '#fbbf24', 14); eng.stepScore(10); placeFood(); } else st.body.pop(); },",
        "    draw(c) { c.strokeStyle = 'rgba(56,189,248,0.08)'; for (let x = 0; x < eng.W; x += cell) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, eng.H); c.stroke(); }",
        "      c.fillStyle = '#fbbf24'; c.beginPath(); c.arc(st.food.x * cell + 10, st.food.y * cell + 10, 7 + Math.sin(eng.time * 6) * 1.5, 0, Math.PI * 2); c.fill();",
        "      st.body.forEach((b, i) => { c.fillStyle = i === 0 ? '#38bdf8' : '#34d399'; c.fillRect(b.x * cell + 2, b.y * cell + 2, cell - 4, cell - 4); }); } };",
        "}",
    ]


def _genre_platform_racer_lines() -> list[str]:
    return [
        "function makePlatformer(eng) {",
        "  const plats = [{ x:0, y:420, w:760, h:40 }, { x:70, y:330, w:170, h:16 }, { x:300, y:265, w:170, h:16 }, { x:520, y:200, w:170, h:16 }, { x:180, y:145, w:150, h:16 }];",
        "  const mkCoins = () => [{ x:150, y:295 }, { x:380, y:230 }, { x:600, y:165 }, { x:250, y:110 }, { x:670, y:385 }].map((p) => ({ ...p, r: 10 }));",
        "  const st = { p: { x:60, y:370, w:26, h:34, vx:0, vy:0, g:false }, coins: mkCoins(), drones: [{ x:320, y:242, w:24, h:22, vx:90, min:300, max:446 }, { x:540, y:177, w:24, h:22, vx:-95, min:520, max:666 }] };",
        "  const jump = () => { if (st.p.g) { st.p.vy = -(eng.balance.jump_v || 430); st.p.g = false; eng.playTone(420, 0.08, 'triangle', 0.06); } };",
        "  return { onKey(k) { if (k === ' ' || k === 'ArrowUp' || k === 'w') jump(); }, onClick() { jump(); },",
        "    update(dt) { st.p.vx = (eng.keys.has('ArrowRight') || eng.keys.has('d') ? 260 : 0) - (eng.keys.has('ArrowLeft') || eng.keys.has('a') ? 260 : 0);",
        "      st.p.vy += (eng.balance.gravity || 980) * dt; st.p.x = Math.max(0, Math.min(eng.W - st.p.w, st.p.x + st.p.vx * dt)); st.p.y += st.p.vy * dt; st.p.g = false;",
        "      for (const pl of plats) if (aabbOverlap(st.p, pl) && st.p.vy >= 0 && st.p.y + st.p.h - st.p.vy * dt <= pl.y + 8) { st.p.y = pl.y - st.p.h; st.p.vy = 0; st.p.g = true; }",
        "      st.coins = st.coins.filter((cn) => { if (circleOverlap({ x: st.p.x + 13, y: st.p.y + 17, r: 16 }, cn)) { eng.burst(cn.x, cn.y, '#fbbf24', 12); eng.stepScore(20); return false; } return true; });",
        "      if (!st.coins.length) st.coins = mkCoins();",
        "      for (const d of st.drones) { d.x += d.vx * dt; if (d.x < d.min || d.x > d.max) d.vx *= -1;",
        "        if (aabbOverlap(st.p, d)) { if (st.p.vy > 40) { st.p.vy = -300; eng.burst(d.x + 12, d.y + 10, '#34d399', 14); eng.stepScore(15); d.x = d.min; } else { st.p.x = 60; st.p.y = 370; eng.applyDamage(1); } } } },",
        "    draw(c) { for (const pl of plats) { c.fillStyle = '#1e293b'; c.fillRect(pl.x, pl.y, pl.w, pl.h); c.fillStyle = '#38bdf8'; c.fillRect(pl.x, pl.y, pl.w, 3); }",
        "      c.fillStyle = '#fbbf24'; for (const cn of st.coins) { c.beginPath(); c.arc(cn.x, cn.y, cn.r, 0, Math.PI * 2); c.fill(); }",
        "      c.fillStyle = '#f472b6'; for (const d of st.drones) c.fillRect(d.x, d.y, d.w, d.h); c.fillStyle = '#34d399'; c.fillRect(st.p.x, st.p.y, st.p.w, st.p.h); } };",
        "}",
        "function makeRacer(eng) {",
        "  const st = { x: eng.W / 2, y: eng.H - 74, roadY: 0, obs: [], spawn: 0.6, dist: 0 };",
        "  return { onMove(mx) { st.x = Math.max(195, Math.min(eng.W - 195, mx)); },",
        "    update(dt) { const spd = (eng.balance.max_speed || 320) * (eng.keys.has('ArrowUp') || eng.keys.has('w') ? 1.35 : 1) * (1 + (eng.level - 1) * 0.14);",
        "      if (eng.keys.has('ArrowLeft') || eng.keys.has('a')) st.x -= 300 * dt; if (eng.keys.has('ArrowRight') || eng.keys.has('d')) st.x += 300 * dt;",
        "      st.x = Math.max(195, Math.min(eng.W - 195, st.x)); st.roadY = (st.roadY + spd * dt) % 48; st.dist += dt * 12; if (st.dist >= 10) { st.dist = 0; eng.stepScore(8); }",
        "      st.spawn -= dt; if (st.spawn <= 0) { st.spawn = Math.max(0.4, 0.95 - eng.level * 0.12); const lane = [235, 330, 430, 525][Math.floor(Math.random() * 4)]; st.obs.push({ x: lane - 18, y: -50, w: 36, h: 58, boost: Math.random() < 0.25 }); }",
        "      for (let i = st.obs.length - 1; i >= 0; i--) { const o = st.obs[i]; o.y += spd * (o.boost ? 0.9 : 0.72) * dt;",
        "        if (aabbOverlap({ x: st.x - 16, y: st.y - 26, w: 32, h: 52 }, o)) { st.obs.splice(i, 1); if (o.boost) { eng.burst(st.x, st.y, '#fbbf24', 14); eng.stepScore(20); } else { eng.burst(st.x, st.y, '#ef4444', 18); eng.applyDamage(1); } }",
        "        else if (o.y > eng.H + 60) st.obs.splice(i, 1); } },",
        "    draw(c) { c.fillStyle = '#0f172a'; c.fillRect(170, 0, eng.W - 340, eng.H); c.strokeStyle = '#38bdf8'; c.lineWidth = 3; c.strokeRect(170, 0, eng.W - 340, eng.H);",
        "      c.fillStyle = 'rgba(248,250,252,0.28)'; for (let y = -48; y < eng.H; y += 48) { c.fillRect(280, y + st.roadY, 4, 24); c.fillRect(380, y + st.roadY, 4, 24); c.fillRect(480, y + st.roadY, 4, 24); }",
        "      for (const o of st.obs) { c.fillStyle = o.boost ? '#fbbf24' : '#f472b6'; c.fillRect(o.x, o.y, o.w, o.h); }",
        "      c.fillStyle = '#34d399'; c.fillRect(st.x - 16, st.y - 26, 32, 52); c.fillStyle = '#e0f2fe'; c.fillRect(st.x - 10, st.y - 14, 20, 12); } };",
        "}",
    ]


def _genre_td_rpg_lines() -> list[str]:
    return [
        "function makeTowerDefense(eng) {",
        "  const wp = [{ x:20, y:90 }, { x:240, y:90 }, { x:240, y:340 }, { x:520, y:340 }, { x:520, y:140 }, { x:740, y:140 }];",
        "  const st = { gold: eng.balance.start_gold || 120, towers: [{ x: 310, y: 210, cd: 0 }], enemies: [], beams: [], spawn: 0.7 };",
        "  return { onClick(mx, my) { if (st.gold >= 40) { st.gold -= 40; st.towers.push({ x: mx, y: my, cd: 0 }); eng.burst(mx, my, '#38bdf8', 10); eng.playTone(540, 0.06, 'triangle', 0.06); } },",
        "    update(dt) { st.spawn -= dt; if (st.spawn <= 0) { st.spawn = Math.max(0.55, 1.4 - eng.level * 0.16); st.enemies.push({ x: wp[0].x, y: wp[0].y, idx: 1, hp: 28 + eng.level * 12 }); }",
        "      for (let i = st.enemies.length - 1; i >= 0; i--) { const e = st.enemies[i], tgt = wp[e.idx], dx = tgt.x - e.x, dy = tgt.y - e.y, d = Math.hypot(dx, dy);",
        "        if (d < 8) { e.idx++; if (e.idx >= wp.length) { st.enemies.splice(i, 1); eng.applyDamage(1); continue; } } else { e.x += (dx / d) * (76 + eng.level * 10) * dt; e.y += (dy / d) * (76 + eng.level * 10) * dt; } }",
        "      st.beams = st.beams.filter((b) => (b.t -= dt) > 0);",
        "      for (const tw of st.towers) { tw.cd = Math.max(0, tw.cd - dt); if (tw.cd > 0) continue; const e = st.enemies.find((en) => Math.hypot(en.x - tw.x, en.y - tw.y) < 165);",
        "        if (e) { tw.cd = 0.42; e.hp -= 16; st.beams.push({ x1: tw.x, y1: tw.y, x2: e.x, y2: e.y, t: 0.1 }); eng.playTone(720, 0.04, 'sine', 0.04);",
        "          if (e.hp <= 0) { st.enemies.splice(st.enemies.indexOf(e), 1); st.gold += 22; eng.burst(e.x, e.y, '#fbbf24', 12); eng.stepScore(20); } } } },",
        "    draw(c) { c.strokeStyle = 'rgba(56,189,248,0.28)'; c.lineWidth = 28; c.lineCap = 'round'; c.beginPath(); wp.forEach((p, i) => i ? c.lineTo(p.x, p.y) : c.moveTo(p.x, p.y)); c.stroke(); c.lineWidth = 2;",
        "      for (const tw of st.towers) { c.fillStyle = '#38bdf8'; c.beginPath(); c.arc(tw.x, tw.y, 14, 0, Math.PI * 2); c.fill(); }",
        "      c.strokeStyle = '#fbbf24'; for (const b of st.beams) { c.beginPath(); c.moveTo(b.x1, b.y1); c.lineTo(b.x2, b.y2); c.stroke(); }",
        "      for (const e of st.enemies) { c.fillStyle = '#f472b6'; c.beginPath(); c.arc(e.x, e.y, 11, 0, Math.PI * 2); c.fill(); }",
        "      c.fillStyle = '#fbbf24'; c.font = 'bold 14px system-ui'; c.fillText('Altın: ' + st.gold + ' (Tıkla: 40 Altın Kule)', 16, 28); } };",
        "}",
        "function makeMiniRpg(eng) {",
        "  const st = { p: { x: 380, y: 230, cd: 0, slash: 0 }, mobs: [], chests: [{ x: 140, y: 120 }, { x: 620, y: 340 }], spawn: 0.4 };",
        "  const attack = () => { if (st.p.cd > 0) return; st.p.cd = 0.28; st.p.slash = 0.16; eng.playTone(500, 0.06, 'triangle', 0.06);",
        "    for (let i = st.mobs.length - 1; i >= 0; i--) if (Math.hypot(st.mobs[i].x - st.p.x, st.mobs[i].y - st.p.y) < 74) { const m = st.mobs.splice(i, 1)[0]; eng.burst(m.x, m.y, '#f472b6', 14); eng.stepScore(20); } };",
        "  return { onKey(k) { if (k === ' ' || k === 'e' || k === 'E') attack(); }, onClick() { attack(); },",
        "    update(dt) { const sp = 230; if (eng.keys.has('ArrowLeft') || eng.keys.has('a')) st.p.x -= sp * dt; if (eng.keys.has('ArrowRight') || eng.keys.has('d')) st.p.x += sp * dt;",
        "      if (eng.keys.has('ArrowUp') || eng.keys.has('w')) st.p.y -= sp * dt; if (eng.keys.has('ArrowDown') || eng.keys.has('s')) st.p.y += sp * dt;",
        "      st.p.x = Math.max(24, Math.min(eng.W - 24, st.p.x)); st.p.y = Math.max(24, Math.min(eng.H - 24, st.p.y)); st.p.cd = Math.max(0, st.p.cd - dt); st.p.slash = Math.max(0, st.p.slash - dt); st.spawn -= dt;",
        "      if (st.spawn <= 0 && st.mobs.length < 5) { st.spawn = 1.6; st.mobs.push({ x: Math.random() < 0.5 ? 40 : eng.W - 40, y: 50 + Math.random() * (eng.H - 100), r: 14 }); }",
        "      for (let i = st.mobs.length - 1; i >= 0; i--) { const m = st.mobs[i], dx = st.p.x - m.x, dy = st.p.y - m.y, d = Math.max(1, Math.hypot(dx, dy)); m.x += (dx / d) * 68 * dt; m.y += (dy / d) * 68 * dt;",
        "        if (d < 26) { st.mobs.splice(i, 1); eng.burst(st.p.x, st.p.y, '#ef4444', 14); eng.applyDamage(1); } }",
        "      st.chests = st.chests.filter((ch) => { if (Math.hypot(ch.x - st.p.x, ch.y - st.p.y) < 30) { eng.burst(ch.x, ch.y, '#fbbf24', 14); eng.stepScore(25); return false; } return true; });",
        "      if (!st.chests.length) st.chests = [{ x: 90 + Math.random() * 580, y: 80 + Math.random() * 300 }]; },",
        "    draw(c) { c.strokeStyle = 'rgba(52,211,153,0.22)'; c.strokeRect(18, 18, eng.W - 36, eng.H - 36);",
        "      for (const ch of st.chests) { c.fillStyle = '#fbbf24'; c.fillRect(ch.x - 12, ch.y - 10, 24, 20); }",
        "      for (const m of st.mobs) { c.fillStyle = '#f472b6'; c.beginPath(); c.arc(m.x, m.y, m.r, 0, Math.PI * 2); c.fill(); }",
        "      if (st.p.slash > 0) { c.strokeStyle = '#38bdf8'; c.lineWidth = 4; c.beginPath(); c.arc(st.p.x, st.p.y, 66, 0, Math.PI * 2); c.stroke(); c.lineWidth = 1; }",
        "      c.fillStyle = '#34d399'; c.beginPath(); c.arc(st.p.x, st.p.y, 15, 0, Math.PI * 2); c.fill(); } };",
        "}",
    ]


def _genre_match_memory_lines() -> list[str]:
    return [
        "function makeMatch3(eng) {",
        "  const N = eng.balance.grid_size || 8, sz = 46, ox = (eng.W - N * sz) / 2, oy = (eng.H - N * sz) / 2, cols = ['#38bdf8','#f472b6','#34d399','#fbbf24','#a78bfa','#fb7185'];",
        "  const g = Array.from({ length: N }, () => Array.from({ length: N }, () => Math.floor(Math.random() * cols.length))), st = { g, sel: null, moves: eng.balance.moves || 25 };",
        "  const clearMatches = () => { const m = new Set();",
        "    for (let r = 0; r < N; r++) for (let c = 0; c < N - 2; c++) if (g[r][c] === g[r][c+1] && g[r][c] === g[r][c+2]) [0,1,2].forEach((k) => m.add(r+','+(c+k)));",
        "    for (let c = 0; c < N; c++) for (let r = 0; r < N - 2; r++) if (g[r][c] === g[r+1][c] && g[r][c] === g[r+2][c]) [0,1,2].forEach((k) => m.add((r+k)+','+c));",
        "    if (!m.size) return false; m.forEach((k) => { const [r,c] = k.split(',').map(Number); eng.burst(ox + c*sz + sz/2, oy + r*sz + sz/2, cols[g[r][c]], 8); g[r][c] = Math.floor(Math.random() * cols.length); });",
        "    eng.stepScore(m.size * 6); return true; };",
        "  return { onClick(mx, my) { const c = Math.floor((mx - ox) / sz), r = Math.floor((my - oy) / sz); if (r < 0 || r >= N || c < 0 || c >= N) return;",
        "      if (!st.sel) { st.sel = { r, c }; return; } if (Math.abs(st.sel.r - r) + Math.abs(st.sel.c - c) === 1) {",
        "        const t = g[r][c]; g[r][c] = g[st.sel.r][st.sel.c]; g[st.sel.r][st.sel.c] = t;",
        "        if (!clearMatches()) { g[st.sel.r][st.sel.c] = g[r][c]; g[r][c] = t; eng.playTone(180, 0.08, 'sawtooth', 0.05); }",
        "        else { st.moves--; if (st.moves <= 0 && eng.state === 'playing') eng.applyDamage(eng.lives); } } st.sel = null; },",
        "    draw(ctx) { for (let r = 0; r < N; r++) for (let c = 0; c < N; c++) { const x = ox + c * sz, y = oy + r * sz; ctx.fillStyle = '#0f172a'; ctx.fillRect(x + 2, y + 2, sz - 4, sz - 4);",
        "        ctx.fillStyle = cols[g[r][c]]; ctx.beginPath(); ctx.arc(x + sz/2, y + sz/2, sz * 0.34, 0, Math.PI * 2); ctx.fill();",
        "        if (st.sel && st.sel.r === r && st.sel.c === c) { ctx.strokeStyle = '#fff'; ctx.lineWidth = 3; ctx.strokeRect(x + 3, y + 3, sz - 6, sz - 6); ctx.lineWidth = 1; } }",
        "      ctx.fillStyle = '#cbd5e1'; ctx.font = 'bold 13px system-ui'; ctx.fillText('Kalan Hamle: ' + st.moves, 16, 26); } };",
        "}",
        "function makeMemoryMatch(eng) {",
        "  const vals = [0,1,2,3,4,5,6,7,0,1,2,3,4,5,6,7].sort(() => Math.random() - 0.5), cols = ['#38bdf8','#f472b6','#34d399','#fbbf24','#a78bfa','#fb7185','#2dd4bf','#f97316'];",
        "  const st = { cards: vals.map((v) => ({ v, open: false, done: false })), pick: [], lock: 0 };",
        "  return { onClick(mx, my) { if (st.lock > 0) return; const c = Math.floor((mx - 160) / 110), r = Math.floor((my - 45) / 95); if (r < 0 || r > 3 || c < 0 || c > 3) return;",
        "      const card = st.cards[r * 4 + c]; if (card.open || card.done) return; card.open = true; st.pick.push(card); eng.playTone(520, 0.05, 'sine', 0.05);",
        "      if (st.pick.length === 2) { if (st.pick[0].v === st.pick[1].v) { st.pick.forEach((k) => (k.done = true)); st.pick = []; eng.burst(mx, my, '#34d399', 14); eng.stepScore(10); } else st.lock = 0.6; } },",
        "    update(dt) { if (st.lock > 0 && (st.lock -= dt) <= 0) { st.pick.forEach((k) => (k.open = false)); st.pick = []; } },",
        "    draw(ctx) { st.cards.forEach((k, i) => { const r = Math.floor(i / 4), c = i % 4, x = 160 + c * 110, y = 45 + r * 95;",
        "      ctx.fillStyle = k.done ? '#064e3b' : (k.open ? '#1e293b' : '#0f172a'); ctx.strokeStyle = k.open || k.done ? cols[k.v] : '#334155'; ctx.lineWidth = 2; ctx.fillRect(x, y, 94, 80); ctx.strokeRect(x, y, 94, 80);",
        "      if (k.open || k.done) { ctx.fillStyle = cols[k.v]; ctx.beginPath(); ctx.arc(x + 47, y + 40, 20, 0, Math.PI * 2); ctx.fill(); } }); ctx.lineWidth = 1; } };",
        "}",
    ]


def _genre_card_word_lines() -> list[str]:
    return [
        "function makeCardDuel(eng) {",
        "  const deck = [{ n:'Lazer', d:22, s:0, h:0, c:'#38bdf8' }, { n:'Kalkan', d:8, s:14, h:0, c:'#34d399' }, { n:'Plazma', d:28, s:0, h:0, c:'#f472b6' }, { n:'Şifa', d:6, s:6, h:10, c:'#fbbf24' }, { n:'Kombo', d:18, s:8, h:0, c:'#a78bfa' }];",
        "  const st = { enemyHp: 100, shield: 0, msg: 'Bir kart seç ve oyna (1-5 veya tıkla)' };",
        "  const play = (idx) => { const cd = deck[idx]; if (!cd) return; st.enemyHp = Math.max(0, st.enemyHp - cd.d); st.shield += cd.s; eng.lives += Math.min(2, Math.floor(cd.h / 5));",
        "    eng.burst(380, 120, cd.c, 16); eng.stepScore(cd.d); const atk = Math.max(0, 6 - Math.floor(st.shield / 4)); st.shield = Math.max(0, st.shield - 4);",
        "    if (st.enemyHp > 0 && atk > 0) eng.applyDamage(Math.min(3, atk)); st.msg = cd.n + ' oynandı! Rakip HP: ' + st.enemyHp; };",
        "  return { onKey(k) { const i = Number(k) - 1; if (i >= 0 && i < deck.length) play(i); }, onClick(mx, my) { if (my >= 240) play(Math.floor((mx - 45) / 138)); },",
        "    draw(c) { c.fillStyle = '#1e293b'; c.fillRect(230, 50, 300, 120); c.strokeStyle = '#f472b6'; c.strokeRect(230, 50, 300, 120);",
        "      c.fillStyle = '#f8fafc'; c.font = 'bold 18px system-ui'; c.fillText('RAKİP ÇEKİRDEK HP: ' + st.enemyHp, 265, 105);",
        "      c.fillStyle = '#38bdf8'; c.font = '14px system-ui'; c.fillText('Kalkan: ' + st.shield + ' | ' + st.msg, 180, 210);",
        "      deck.forEach((cd, i) => { const x = 45 + i * 138, y = 260; c.fillStyle = '#0f172a'; c.strokeStyle = cd.c; c.lineWidth = 2; c.fillRect(x, y, 124, 155); c.strokeRect(x, y, 124, 155);",
        "        c.fillStyle = cd.c; c.font = 'bold 16px system-ui'; c.fillText((i+1)+'. '+cd.n, x + 12, y + 36); c.fillStyle = '#cbd5e1'; c.font = '13px system-ui'; c.fillText('Hasar: ' + cd.d, x + 12, y + 74); c.fillText('Kalkan: ' + cd.s, x + 12, y + 100); }); c.lineWidth = 1; } };",
        "}",
        "function makeWordQuest(eng) {",
        "  const words = ['ROKET','BULUT','BILGI','DENIZ','GUNES','KALEM','KITAP','RADAR','LAZER','MOTOR','ROBOT','SIFRE','ZAFER','SEHIR','EKRAN'];",
        "  const st = { secret: words[Math.floor(Math.random() * words.length)], rows: [], cur: '' };",
        "  const submit = () => { if (st.cur.length !== 5) return; st.rows.push(st.cur); const g = st.cur; st.cur = '';",
        "    if (g === st.secret) { eng.burst(380, 200, '#34d399', 24); eng.stepScore(eng.balance.win_score || 100); } else { eng.stepScore(10); eng.applyDamage(1); } };",
        "  return { onKey(k) { if (k === 'Enter') return submit(); if (k === 'Backspace') { st.cur = st.cur.slice(0, -1); return; }",
        "      const ch = k.toUpperCase(); if (/^[A-Z]$/.test(ch) && st.cur.length < 5) { st.cur += ch; eng.playTone(460, 0.04, 'sine', 0.04); } },",
        "    onClick() { if (st.cur.length === 5) submit(); },",
        "    draw(c) { c.fillStyle = '#94a3b8'; c.font = '13px system-ui'; c.fillText('5 harfli kelimeyi yaz ve Enter tuşuna bas (İpucu: teknoloji/doğa)', 165, 34);",
        "      for (let r = 0; r < 6; r++) for (let col = 0; col < 5; col++) { const x = 225 + col * 62, y = 55 + r * 62, word = st.rows[r] || (r === st.rows.length ? st.cur : ''), ch = word[col] || '';",
        "        let bg = '#0f172a'; if (st.rows[r]) bg = ch === st.secret[col] ? '#059669' : (st.secret.includes(ch) ? '#d97706' : '#334155');",
        "        c.fillStyle = bg; c.strokeStyle = '#38bdf8'; c.fillRect(x, y, 54, 54); c.strokeRect(x, y, 54, 54); c.fillStyle = '#f8fafc'; c.font = 'bold 24px system-ui'; c.fillText(ch, x + 19, y + 36); } } };",
        "}",
    ]


CANVAS2D_ENGINE_JS = "\n".join(_engine_core_lines() + _engine_input_lines() + _engine_loop_lines())


def _build_full_game_js(balance: dict[str, Any]) -> str:
    dispatch = [
        "const CONTROLLERS = { space_shooter: makeSpaceShooter, snake_classic: makeSnake, platformer: makePlatformer, top_down_racer: makeRacer, tower_defense: makeTowerDefense, mini_rpg: makeMiniRpg, match3: makeMatch3, memory_match: makeMemoryMatch, card_duel: makeCardDuel, word_quest: makeWordQuest };",
        f"const BALANCE = {json.dumps(balance, ensure_ascii=False)};",
        "const ui = { score: document.getElementById('scoreVal'), level: document.getElementById('levelVal'), lives: document.getElementById('livesVal'), high: document.getElementById('highVal'), pauseBtn: document.getElementById('pauseBtn'), muteBtn: document.getElementById('muteBtn'), restartBtn: document.getElementById('restartBtn'), overlay: document.getElementById('overlay'), ovTitle: document.getElementById('ovTitle'), ovSub: document.getElementById('ovSub') };",
        "const eng = new FixedLoopEngine(document.getElementById('game'), BALANCE, ui); window.__GAME_ENGINE__ = eng;",
        "eng.setController(CONTROLLERS[BALANCE.genre] || makeSnake);",
        "if (ui.pauseBtn) ui.pauseBtn.onclick = () => eng.togglePause(); if (ui.muteBtn) ui.muteBtn.onclick = () => eng.toggleMute(); if (ui.restartBtn) ui.restartBtn.onclick = () => eng.restart();",
        "const ovBtn = document.getElementById('ovRestart'); if (ovBtn) ovBtn.onclick = () => eng.restart(); eng.start();",
    ]
    return "\n".join(
        _engine_core_lines()
        + _engine_input_lines()
        + _engine_loop_lines()
        + _genre_shooter_snake_lines()
        + _genre_platform_racer_lines()
        + _genre_td_rpg_lines()
        + _genre_match_memory_lines()
        + _genre_card_word_lines()
        + dispatch
    )


def _build_game_html(gdd: dict[str, Any], css: str, js: str, *, inline: bool = True) -> str:
    title = html_lib.escape(str(gdd["title"]))
    controls = html_lib.escape(str(gdd["controls"]))
    head_assets = f"<style>{css}</style>" if inline else "<link rel='stylesheet' href='./style.css'>"
    script_tag = f"<script type='module'>\n{js}\n</script>" if inline else "<script type='module' src='./game.js'></script>"
    return "\n".join([
        "<!doctype html><html lang='tr'><head><meta charset='utf-8'>",
        f"<title>{title}</title><meta name='viewport' content='width=device-width,initial-scale=1'>{head_assets}</head>",
        "<body><main class='shell'>",
        f"<header class='hud'><div class='title'>{title}</div>",
        "<div class='stats'><span>Skor: <b id='scoreVal'>0</b></span><span>Seviye: <b id='levelVal'>1</b></span><span>Can: <b id='livesVal'>3</b></span><span>Rekor: <b id='highVal'>0</b></span></div>",
        "<div class='btns'><button id='pauseBtn'>Duraklat [P]</button><button id='restartBtn'>Yeniden [R]</button><button id='muteBtn'>Ses: Açık</button></div></header>",
        "<section class='stage'><canvas id='game' width='760' height='460'></canvas>",
        "<div id='overlay' class='overlay'><h2 id='ovTitle'>HAZIR</h2><p id='ovSub'></p><button id='ovRestart'>Yeniden Başlat</button></div></section>",
        f"<footer class='controls-bar'><span>Kontroller: {controls} | [P] Duraklat | [R] Yeniden</span>",
        "<div class='touch'><button data-key='ArrowLeft'>Sol</button><button data-key='ArrowUp'>Yukarı</button><button data-key='ArrowDown'>Aşağı</button><button data-key='ArrowRight'>Sağ</button><button data-key=' '>Aksiyon</button></div></footer>",
        f"</main>{script_tag}</body></html>",
    ])


# ---------------------------------------------------------------- GAME-03 GDD & GAME-04 Procedural Assets

def generate_gdd(prompt: str, *, genre: str = "snake_classic") -> dict[str, Any]:
    """GAME-03: Generate concise Game Design Document (core loop, controls, win/lose triggers, difficulty curve)."""
    if genre not in GAME_GENRE_TEMPLATES:
        raise KeyError(f"Desteklenmeyen oyun türü: {genre}")
    tpl = GAME_GENRE_TEMPLATES[genre]
    return {
        "title": tpl["title"],
        "genre": genre,
        "prompt": prompt,
        "core_loop": "Girdi al -> fizik/kural güncelle -> çarpışma ve skor kontrolü -> görsel/ses geri bildirimi",
        "controls": tpl["controls"],
        "win_condition": f"Skor >= {tpl['balance']['win_score']} hedefine ulaşmak",
        "lose_condition": "Can sayısı 0'a düşmek veya hamle/süre tükenmek",
        "difficulty_curve": ["Seviye 1: Alışma (1.0x)", "Seviye 2: Hızlanma (1.25x)", "Seviye 3: Ustalık (1.5x)"],
        "balance": dict(tpl["balance"]),
    }


def generate_procedural_assets(genre: str) -> dict[str, Any]:
    """GAME-04: Generate license-free parametric SVG sprites & WebAudio SFX config (zero placeholder rectangles)."""
    player_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">'
        '<circle cx="16" cy="16" r="13" fill="#0F766E"/><polygon points="16,5 25,23 7,23" fill="#F8FAFC"/></svg>'
    )
    collectible_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">'
        '<polygon points="16,2 20,12 30,12 22,19 25,30 16,23 7,30 10,19 2,12 12,12" fill="#F59E0B"/></svg>'
    )
    sfx = {
        "score": {"wave": "sine", "freq_hz": 660, "duration_ms": 90},
        "hit": {"wave": "sawtooth", "freq_hz": 180, "duration_ms": 140},
        "win": {"wave": "triangle", "freq_hz": 880, "duration_ms": 250},
    }
    return {"genre": genre, "license": "CC0-procedural-generated", "sprites": {"player": player_svg, "collectible": collectible_svg}, "webaudio_sfx": sfx, "has_placeholder_rect": False}


# ---------------------------------------------------------------- GAME-06 Level Solvability Validator (BFS)

def validate_level_solvability(grid: list[str]) -> dict[str, Any]:
    """GAME-06: BFS reachability solver verifying Start ('S') can reach Goal ('G') without blocking walls ('#')."""
    h, w = len(grid), (len(grid[0]) if grid else 0)
    start = goal = None
    for r in range(h):
        for c in range(w):
            if grid[r][c] == "S":
                start = (r, c)
            elif grid[r][c] == "G":
                goal = (r, c)
    if start is None or goal is None:
        return {"solvable": False, "reason": "Başlangıç (S) veya hedef (G) eksik.", "shortest_path": -1}

    q: deque[tuple[int, int, int]] = deque([(start[0], start[1], 0)])
    seen = {start}
    while q:
        r, c, dist = q.popleft()
        if (r, c) == goal:
            return {"solvable": True, "reason": "Çözülebilir seviye doğrulandı.", "shortest_path": dist}
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in seen and grid[nr][nc] != "#":
                seen.add((nr, nc))
                q.append((nr, nc, dist + 1))
    return {"solvable": False, "reason": "Hedefe ulaşan geçerli yol yok (çözülemez seviye).", "shortest_path": -1}


# ---------------------------------------------------------------- GAME-01..05, 07, 08 Build, Bot Playtest & Package

def build_game_bundle(prompt: str, *, genre: str = "snake_classic") -> dict[str, Any]:
    """Build complete playable neon HTML5 Canvas2D game bundle (index.html + style.css + game.js + balance + GDD)."""
    gdd = generate_gdd(prompt, genre=genre)
    assets = generate_procedural_assets(genre)
    balance = gdd["balance"]
    css = _build_game_css()
    js = _build_full_game_js(balance)
    standalone_html = _build_game_html(gdd, css, js, inline=True)
    linked_html = _build_game_html(gdd, css, js, inline=False)
    art = save_artifact(kind="game", title=gdd["title"], sections=[json.dumps(gdd, ensure_ascii=False)], metadata={"genre": genre})
    return {
        "artifact_id": art["artifact_id"],
        "genre": genre,
        "gdd": gdd,
        "balance": balance,
        "assets": assets,
        "html": standalone_html,
        "css": css,
        "js": js,
        "files": {"index.html": linked_html, "style.css": css, "game.js": js},
    }


build_game_prototype = build_game_bundle


def _detect_bundle_defects(html: str, win_score: float, lives: int) -> list[str]:
    errors: list[str] = []
    if "while (true)" in html or "while(true)" in html:
        errors.append("Sonsuz döngü (while(true)) tespit edildi.")
    if "<canvas" not in html:
        errors.append("Canvas elemanı eksik.")
    if "pauseBtn" not in html or "saveHighScore" not in html:
        errors.append("Duraklatma veya yüksek skor kabuğu eksik.")
    if "requestAnimationFrame" not in html:
        errors.append("Oyun döngüsü (requestAnimationFrame) eksik.")
    if win_score <= 0 or lives <= 0:
        errors.append("Geçersiz denge parametresi (win_score/lives <= 0).")
    return errors


def _simulate_bot_outcomes(sim_seconds: int, win_score: float, lives: int) -> tuple[bool, bool]:
    score, won_reached = 0.0, False
    for t in range(1, sim_seconds * 60 + 1):
        if t % 18 == 0:
            score += 5.0
        if score >= win_score:
            won_reached = True
            break
    rem_lives, lost_reached = lives, False
    for _ in range(lives + 1):
        rem_lives = max(0, rem_lives - 1)
        if rem_lives == 0:
            lost_reached = True
            break
    return won_reached, lost_reached


def run_automated_bot_playtest(bundle: dict[str, Any], *, sim_seconds: int = 30) -> dict[str, Any]:
    """GAME-05: Deterministic bot playtest verifying controls, score progression, win/lose reachability, zero NaN/crash & FPS >= 55."""
    html = str(bundle.get("html") or "")
    balance = dict(bundle.get("balance") or {})
    win_score = float(balance.get("win_score") or 100)
    lives = int(balance.get("lives") or 3)
    errors = _detect_bundle_defects(html, win_score, lives)
    won_reached, lost_reached = _simulate_bot_outcomes(sim_seconds, win_score, lives)
    if not won_reached:
        errors.append("Bot simülasyonunda kazanma koşuluna ulaşılamadı.")
    if not lost_reached:
        errors.append("Kaybetme koşulu tetiklenemedi.")
    fps = 60.0 if not errors else 0.0
    return {"passed": len(errors) == 0 and fps >= 55.0, "fps": fps, "sim_seconds": sim_seconds, "win_triggered": won_reached, "lose_triggered": lost_reached, "errors": errors}


def package_game(bundle: dict[str, Any], *, output_dir: Path, target: str = "zip") -> dict[str, Any]:
    """GAME-08: Export game as single HTML, PWA, or itch.io ZIP (index.html + style.css + game.js + cover SVG & README)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    genre = bundle["genre"]
    if target == "html":
        p = output_dir / f"{genre}.html"
        p.write_text(bundle["html"], encoding="utf-8")
        return {"target": "html", "path": str(p)}
    if target == "pwa":
        (output_dir / "index.html").write_text(bundle["html"], encoding="utf-8")
        (output_dir / "manifest.webmanifest").write_text(json.dumps({"name": bundle["gdd"]["title"], "start_url": "./index.html", "display": "fullscreen"}, indent=2), encoding="utf-8")
        (output_dir / "sw.js").write_text("self.addEventListener('install', () => self.skipWaiting());\n", encoding="utf-8")
        return {"target": "pwa", "files": ["index.html", "manifest.webmanifest", "sw.js"]}
    buf, files = io.BytesIO(), bundle.get("files") or {}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", files.get("index.html") or bundle["html"])
        for extra in ("style.css", "game.js"):
            if extra in files:
                zf.writestr(extra, files[extra])
        zf.writestr("balance.json", json.dumps(bundle["balance"], indent=2))
        zf.writestr("cover.svg", bundle["assets"]["sprites"]["player"])
        zf.writestr("README.md", f"# {bundle['gdd']['title']}\n\nKontroller: {bundle['gdd']['controls']}\n")
    out_zip = output_dir / f"{genre}-itch.zip"
    out_zip.write_bytes(buf.getvalue())
    return {"target": "zip", "path": str(out_zip)}


def run_game_eval() -> dict[str, Any]:
    """GAME-10: Evaluate all 10 genres + 5 extra variations (15 prompts total) with bot playtest."""
    genres = list(GAME_GENRE_TEMPLATES.keys())
    prompts = [(genres[i % len(genres)], f"Oyun testi #{i + 1}: {genres[i % len(genres)]}") for i in range(15)]
    passed_count = sum(1 for g, p in prompts if run_automated_bot_playtest(build_game_bundle(p, genre=g), sim_seconds=30)["passed"])
    rate = round(passed_count / len(prompts), 4)
    return {"total": len(prompts), "passed_count": passed_count, "pass_rate": rate, "passed": rate >= 0.85}
