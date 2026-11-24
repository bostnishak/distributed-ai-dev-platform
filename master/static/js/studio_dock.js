// Code Studio as a slide-over panel inside the chat. Opened on request (assistant or composer menu); the full-page route stays.
import { bindGlobalEvent } from './storage.js';
import { h } from './util.js';

let dock = null;
let host = null;
let mounted = false;

function build() {
  host = h('div', { class: 'studio-dock-body' });
  const closeBtn = h('button', { type: 'button', class: 'pill-icon-btn', 'aria-label': 'Paneli kapat', title: 'Kapat', onClick: () => closeStudioDock() }, '✕');
  const fullBtn = h('button', { type: 'button', class: 'pill-icon-btn', 'aria-label': 'Tam sayfada aç', title: 'Tam sayfada aç', onClick: () => { closeStudioDock(); location.hash = '#/studio'; } }, '⤢');
  dock = h('aside', { id: 'studioDock', class: 'studio-dock', 'aria-label': 'Kod Stüdyosu', hidden: true },
    h('div', { class: 'studio-dock-head' }, h('strong', null, 'Kod Stüdyosu'), h('span', { class: 'studio-dock-actions' }, fullBtn, closeBtn)),
    host);
  document.getElementById('view-assistant')?.append(dock);
  bindGlobalEvent(document, 'keydown', (e) => { if (e.key === 'Escape' && dock && !dock.hidden) closeStudioDock(); });
}

export async function openStudioDock() {
  if (!dock) build();
  if (!dock) return;
  dock.hidden = false;
  if (!mounted) {
    mounted = true;
    const { renderStudio } = await import('./studio.js');
    await renderStudio(host);
  }
}

export function closeStudioDock() {
  if (dock) dock.hidden = true;
}
