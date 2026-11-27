// War room: the live graph of a running build, pause/resume, course corrections, a time slider and branching.
import { bindGlobalEvent, safeFetchJson } from './storage.js';
import { extraButtons } from './war_extras.js';

const COLORS = { waiting: '#e2e8f0', running: '#fde68a', done: '#bbf7d0', failed: '#fecaca', skipped: '#f1f5f9' };
const LABELS = { waiting: 'bekliyor', running: 'çalışıyor', done: 'bitti', failed: 'hata', skipped: 'atlandı' };
const SVG = 'http://www.w3.org/2000/svg';
const STATES = { running: 'çalışıyor', done: 'bitti', interrupted: 'kesildi', 'duraklatıldı': 'duraklatıldı', paused: 'duraklatıldı' };

const RECONNECT_MS = 3000;
const LIVE_PATH = '/api/runs/ws';

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function svg(tag, attrs, text) {
  const node = document.createElementNS(SVG, tag);
  Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
  if (text !== undefined) node.textContent = text;
  return node;
}

function post(path, body) {
  return safeFetchJson(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
}

// The state of every step after the first `upTo` events (this is what the time slider replays).
export function replay(events, upTo) {
  const nodes = new Map();
  let state = 'running';
  const notes = [];
  events.slice(0, upTo).forEach((e) => {
    if (e.kind === 'node') nodes.set(e.node.id, e.node);
    if (e.kind === 'paused') state = 'duraklatıldı';
    if (e.kind === 'resumed') state = 'running';
    if (e.kind === 'steer') notes.push(e.note);
    if (e.kind === 'finished') state = e.state;
  });
  return { nodes: [...nodes.values()], state, notes };
}

function depthOf(node, byId, seen = new Set()) {
  if (!node.deps || !node.deps.length || seen.has(node.id)) return 0;
  seen.add(node.id);
  return 1 + Math.max(...node.deps.map((d) => (byId.has(d) ? depthOf(byId.get(d), byId, new Set(seen)) : 0)));
}

function drawGraph(nodes, onPick) {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const columns = [];
  nodes.forEach((n) => { const d = depthOf(n, byId); (columns[d] = columns[d] || []).push(n); });
  const at = new Map();
  columns.forEach((col, x) => (col || []).forEach((n, y) => at.set(n.id, { x: 10 + x * 230, y: 10 + y * 74 })));
  const width = Math.max(460, columns.length * 230);
  const height = Math.max(90, ...columns.map((c) => (c ? c.length * 74 + 12 : 0)));
  const root = svg('svg', { width, height, viewBox: `0 0 ${width} ${height}` });
  nodes.forEach((n) => (n.deps || []).forEach((d) => {
    const a = at.get(d);
    const b = at.get(n.id);
    if (a && b) root.append(svg('line', { x1: a.x + 200, y1: a.y + 30, x2: b.x, y2: b.y + 30, stroke: '#94a3b8' }));
  }));
  nodes.forEach((n) => {
    const { x, y } = at.get(n.id);
    const group = svg('g', { 'data-node': n.id });
    group.append(svg('rect', { x, y, width: 200, height: 62, rx: 8, fill: COLORS[n.status] || '#fff', stroke: '#475569' }));
    const title = String(n.title || n.id);
    group.append(svg('text', { x: x + 8, y: y + 18, 'font-size': 12, 'font-weight': 700, fill: '#0f172a' }, title.length > 28 ? `…${title.slice(-27)}` : title));
    group.append(svg('text', { x: x + 8, y: y + 35, 'font-size': 11, fill: '#334155' }, `${LABELS[n.status] || n.status}${n.seconds !== undefined ? ` · ${n.seconds} sn` : ''}${n.tokens_per_s && !n.background ? ` · ~${n.tokens_per_s} tok/sn` : ''}`));
    group.append(svg('text', { x: x + 8, y: y + 52, 'font-size': 10, fill: '#475569' }, n.background ? 'arka plan' : String(n.model || '')));
    group.addEventListener('click', () => onPick(n));
    root.append(group);
  });
  return root;
}

// Builds the toggle button and the panel; returns the parts the behaviour below drives.
function buildDom() {
  const toggle = el('button', 'Ajan grafiği', 'war-toggle');
  toggle.type = 'button';
  toggle.hidden = true;
  const panel = el('div', undefined, 'war-panel');
  panel.hidden = true;
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-label', 'Ajan grafiği');
  const picker = el('select');
  picker.setAttribute('aria-label', 'İş seç');
  const status = el('strong');
  const pauseBtn = el('button', 'Duraklat');
  pauseBtn.type = 'button';
  const note = el('input', undefined, 'war-note');
  note.placeholder = 'Kalan adımlar için talimat ekle (ör. butonlar yeşil olsun)';
  note.setAttribute('aria-label', 'Talimat');
  const send = el('button', 'Talimatı ekle');
  send.type = 'button';
  const graph = el('div', undefined, 'war-graph');
  const slider = el('input', undefined, 'war-slider');
  slider.type = 'range';
  slider.setAttribute('aria-label', 'Zaman');
  const sliderLabel = el('div', '', 'war-small');
  const detail = el('div', undefined, 'war-small');
  const branchRow = el('div', undefined, 'war-row');
  const head = el('div', undefined, 'war-row');
  head.append(picker, status, pauseBtn);
  const steerRow = el('div', undefined, 'war-row');
  steerRow.append(note, send);
  panel.append(head, steerRow, graph, sliderLabel, slider, detail, branchRow);
  document.body.append(toggle, panel);
  return { toggle, panel, picker, status, pauseBtn, note, send, graph, slider, sliderLabel, detail, branchRow, steerRow };
}

function nodeEditor(runId, n) {
  const input = el('input', undefined, 'war-purpose');
  input.value = n.purpose || '';
  input.setAttribute('aria-label', 'Adımın görevi');
  const save = el('button', 'Görevi değiştir');
  const skip = el('button', 'Bu adımı atla');
  save.addEventListener('click', () => post(`/api/runs/${runId}/node`, { node: n.id, purpose: input.value }));
  skip.addEventListener('click', () => post(`/api/runs/${runId}/node`, { node: n.id, skip: true }));
  return [input, save, skip];
}

// The saved versions of a project and the button that opens a new branch from one of them.
async function showVersions(wsId, row) {
  const res = await safeFetchJson(`/api/runs/versions/${encodeURIComponent(wsId)}`);
  const list = (res.data && res.data.versions) || [];
  row.replaceChildren();
  if (!list.length) return false;
  const select = el('select');
  select.setAttribute('aria-label', 'Sürüm');
  list.forEach((v) => { const o = el('option', `${v.version} · ${v.label}`); o.value = v.version; select.append(o); });
  const go = el('button', 'Bu sürümden dallan');
  const out = el('span');
  go.addEventListener('click', async () => {
    const done = await post(`/api/runs/branch/${encodeURIComponent(wsId)}`, { version: select.value });
    out.textContent = done.ok ? `Yeni çalışma alanı: ${done.data.workspace.name}` : 'Dallanamadı.';
    if (done.ok) out.append(...extraButtons(done.data.workspace.id));
  });
  row.append(el('span', 'Kontrol noktaları:'), select, go, out, ...extraButtons(wsId));
  return true;
}

function fillPicker(picker, state) {
  picker.replaceChildren(...state.runs.map((r) => { const o = el('option', `${r.title.slice(0, 60)} (${STATES[r.state] || r.state})`); o.value = r.id; return o; }));
  picker.value = state.current;
}

// The live feed; reconnects after a drop, but not when the server refuses this origin.
function connect(state, onMessage) {
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${scheme}://${location.host}${LIVE_PATH}`);
  state.socket = socket;
  bindGlobalEvent(socket, 'open', () => { state.events = []; if (state.current) socket.send(JSON.stringify({ watch: state.current })); });
  bindGlobalEvent(socket, 'message', (e) => onMessage(JSON.parse(e.data)));
  bindGlobalEvent(socket, 'close', (e) => { if (e.code !== 1008) globalThis.setTimeout(() => connect(state, onMessage), RECONNECT_MS); });
}

// Without a live connection the record is fetched once, so a finished run can still be replayed.
async function loadOnce(state, id, redraw) {
  const [list, record] = await Promise.all([safeFetchJson('/api/runs'), safeFetchJson(`/api/runs/${id}/events`)]);
  if (id !== state.current || !record.ok) return;
  state.runs = (list.data && list.data.runs) || state.runs;
  state.events = record.data.events;
  redraw();
}

function createRoom() {
  const state = { runs: [], current: '', events: [], upTo: null, socket: null, versionsFor: '' };
  const { toggle, panel, picker, status, pauseBtn, note, send, graph, slider, sliderLabel, detail, branchRow, steerRow } = buildDom();

  const runInfo = () => state.runs.find((r) => r.id === state.current);

  function showNode(n) {
    detail.replaceChildren(el('div', `${n.title || n.id}: ${n.purpose || n.error || ''}`));
    const live = runInfo() && ['running', 'paused'].includes(runInfo().state);
    if (n.status === 'waiting' && live) detail.append(...nodeEditor(state.current, n));
  }

  function render() {
    const total = state.events.length;
    const upTo = state.upTo === null ? total : Math.min(state.upTo, total);
    const view = replay(state.events, upTo);
    const info = runInfo();
    const live = info && ['running', 'paused'].includes(info.state);
    status.textContent = view.state === 'running' && !live && upTo === total ? 'kesildi' : (STATES[view.state] || view.state);
    pauseBtn.hidden = !live;
    steerRow.hidden = !live;
    pauseBtn.textContent = info && info.state === 'paused' ? 'Devam ettir' : 'Duraklat';
    graph.replaceChildren(drawGraph(view.nodes, showNode));
    slider.max = String(total);
    slider.value = String(upTo);
    const last = state.events[upTo - 1];
    sliderLabel.textContent = `Zaman: olay ${upTo}/${total}${last ? ` (${last.t} sn)` : ''}${view.notes.length ? ` · talimatlar: ${view.notes.join(' | ')}` : ''}`;
  }

  async function loadVersions(wsId) {
    if (!wsId || state.versionsFor === wsId) return;
    state.versionsFor = wsId;
    if (!(await showVersions(wsId, branchRow))) state.versionsFor = '';
  }

  function watch(id) {
    state.current = id;
    state.events = [];
    state.upTo = null;
    state.versionsFor = '';
    branchRow.replaceChildren();
    detail.replaceChildren();
    if (state.socket && state.socket.readyState === 1) state.socket.send(JSON.stringify({ watch: id }));
    else loadOnce(state, id, () => { if (!panel.hidden) render(); });
  }

  function onMessage(msg) {
    if (msg.runs) {
      state.runs = msg.runs;
      toggle.hidden = !state.runs.length;
      const active = state.runs.find((r) => r.state === 'running');
      toggle.textContent = active ? '● Ajan grafiği (çalışıyor)' : 'Ajan grafiği';
      if (active && active.id !== state.current) watch(active.id);
      else if (!state.current && state.runs.length) watch(state.runs[0].id);
      fillPicker(picker, state);
    }
    if (msg.run === state.current && msg.events) state.events.push(...msg.events);
    if (!panel.hidden) { render(); const info = runInfo(); if (info) loadVersions(info.ws_id); }
  }

  toggle.addEventListener('click', () => { panel.hidden = !panel.hidden; if (!panel.hidden) { render(); const info = runInfo(); if (info) loadVersions(info.ws_id); } });
  picker.addEventListener('change', () => watch(picker.value));
  slider.addEventListener('input', () => { state.upTo = Number(slider.value) >= state.events.length ? null : Number(slider.value); render(); });
  pauseBtn.addEventListener('click', () => post(runInfo() && runInfo().state === 'paused' ? `/api/runs/${state.current}/resume` : `/api/runs/${state.current}/pause`));
  send.addEventListener('click', async () => {
    if (note.value.trim().length < 2) return;
    const res = await post(`/api/runs/${state.current}/steer`, { note: note.value.trim() });
    if (res.ok) note.value = '';
  });
  connect(state, onMessage);
}

export function initWarRoom() {
  if (typeof WebSocket === 'function') createRoom();
}
