// In-chat slide-over panel. Hosts Code Studio, CNC, Studios hub, Artifacts and Files without leaving the conversation.
import { bindGlobalEvent, startManagedInterval } from './storage.js';
import { h } from './util.js';

const TOOLS = {
  studio: { label: 'Kod Stüdyosu', full: '#/studio', load: async (root) => (await import('./studio.js')).renderStudio(root) },
  cnc: { label: 'CNC Balonlama', full: '#/cnc', load: async (root) => (await import('./cnc.js')).renderCnc(root) },
  studios: { label: 'Stüdyolar', full: '#/studios', load: async (root, ctx) => (await import('./hub.js')).renderHub(root, ctx) },
  artifacts: { label: 'Artefaktlar', full: '#/artifacts', load: async (root, ctx) => (await import('./panels.js')).renderArtifacts(root, ctx) },
  files: { label: 'Dosyalar ve Bilgi Bankası', full: '#/files', load: async (root, ctx) => (await import('./panels.js')).renderFiles(root, ctx) },
};

let dock = null;
let titleEl = null;
let host = null;
let current = null;
let stopTimer = null;

function makeCtx() {
  return {
    isCurrent: () => Boolean(dock && !dock.hidden),
    stopPoll: () => { if (typeof stopTimer === 'function') stopTimer(); stopTimer = null; },
    poll(fn, ms) {
      if (typeof stopTimer === 'function') stopTimer();
      stopTimer = startManagedInterval(async () => { try { await fn(); } catch { /* retry next tick */ } }, ms);
    },
  };
}

function build() {
  const closeBtn = h('button', { type: 'button', class: 'pill-icon-btn', 'aria-label': 'Paneli kapat', title: 'Kapat', onClick: () => closeStudioDock() }, '✕');
  const fullBtn = h('button', { type: 'button', class: 'pill-icon-btn', 'aria-label': 'Tam sayfada aç', title: 'Tam sayfada aç', onClick: () => { const t = TOOLS[current]; closeStudioDock(); if (t) location.hash = t.full; } }, '⤢');
  titleEl = h('strong', null, 'Araç');
  host = h('div', { class: 'studio-dock-body' });
  dock = h('aside', { id: 'studioDock', class: 'studio-dock', 'aria-label': 'Araç paneli', hidden: true },
    h('div', { class: 'studio-dock-head' }, titleEl, h('span', { class: 'studio-dock-actions' }, fullBtn, closeBtn)),
    host);
  document.getElementById('view-assistant')?.append(dock);
  bindGlobalEvent(document, 'keydown', (e) => { if (e.key === 'Escape' && dock && !dock.hidden) closeStudioDock(); });
}

export async function openDock(key = 'studio') {
  const tool = TOOLS[key];
  if (!tool) return;
  if (!dock) build();
  if (!dock) return;
  dock.hidden = false;
  if (current === key) return;
  current = key;
  titleEl.textContent = tool.label;
  dock.dataset.tool = key;
  host.replaceChildren();
  try { await tool.load(host, makeCtx()); } catch (err) { host.append(h('p', { class: 'empty-state' }, `Panel yüklenemedi: ${err.message || err}`)); }
}

export const openStudioDock = () => openDock('studio');

export function closeStudioDock() {
  if (dock) dock.hidden = true;
}
