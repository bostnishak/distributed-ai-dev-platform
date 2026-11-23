// Shell: hash router, navigation and the mobile sidebar drawer.
import { renderAgents } from './agents.js';
import { focusAssistant, initAssistant } from './assistant.js';
import { initAuthUi } from './auth_modal.js';
import { renderDashboard } from './dashboard.js';
import { renderHub } from './hub.js';
import { initPalette } from './palette.js';
import { renderArtifacts, renderFiles, renderShare } from './panels.js';
import { initPersonalSpace } from './personal.js';
import { renderNewProject, renderProjectDetail, renderProjects } from './projects.js';
import { createReactiveStore } from './store.js';
import { closeSidebar, isDesktop, openSidebar } from './util.js';
import { announceAriaLive, fetchHealthWizardStatus } from './ux_shell.js';

const appStore = createReactiveStore();
window.__DADP_STORE__ = appStore;

if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === '127.0.0.1' || location.hostname === 'localhost')) {
  navigator.serviceWorker.register('/static/sw.js').catch(() => {});
}

const pageView = document.getElementById('view-page');
const assistantView = document.getElementById('view-assistant');
const assistantSide = document.getElementById('assistantSide');

const ROUTES = [
  { pattern: /^#\/new$/, nav: 'new', render: (root) => renderNewProject(root) },
  { pattern: /^#\/projects$/, nav: 'projects', render: (root) => renderProjects(root) },
  { pattern: /^#\/projects\/(\d+)$/, nav: 'projects', render: (root, m, ctx) => renderProjectDetail(root, Number(m[1]), ctx) },
  { pattern: /^#\/agents$/, nav: 'agents', render: (root, _m, ctx) => renderAgents(root, ctx) },
  { pattern: /^#\/dashboard$/, nav: 'dashboard', render: (root, _m, ctx) => renderDashboard(root, ctx) },
  { pattern: /^#\/studios$/, nav: 'studios', render: (root, _m, ctx) => renderHub(root, ctx) },
  { pattern: /^#\/artifacts$/, nav: 'artifacts', render: (root, _m, ctx) => renderArtifacts(root, ctx) },
  { pattern: /^#\/files$/, nav: 'files', render: (root, _m, ctx) => renderFiles(root, ctx) },
  { pattern: /^#\/share\/([\w-]+)$/, nav: 'assistant', render: (root, m) => renderShare(root, m[1]) },
  { pattern: /^#\/assistant$/, nav: 'assistant', render: null },
];

let pollTimer = null;
let routeToken = 0;

function stopPoll() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = null;
}

function route() {
  stopPoll();
  const token = ++routeToken;
  const hash = location.hash || '#/new';
  const match = ROUTES.map((r) => ({ r, m: hash.match(r.pattern) })).find((x) => x.m);
  if (!match) {
    location.hash = '#/new';
    return;
  }
  const { r, m } = match;

  for (const link of document.querySelectorAll('#nav a')) {
    link.classList.toggle('active', link.dataset.view === r.nav);
  }
  const isAssistant = r.render === null;
  assistantView.hidden = !isAssistant;
  assistantSide.hidden = !isAssistant;
  pageView.hidden = isAssistant;
  closeSidebar();

  if (isAssistant) {
    if (isDesktop()) focusAssistant();
    return;
  }
  const ctx = {
    isCurrent: () => token === routeToken,
    stopPoll,
    poll(fn, ms) {
      stopPoll();
      pollTimer = setInterval(async () => {
        if (token !== routeToken) return stopPoll();
        try { await fn(); } catch { /* transient network error: try again on the next tick */ }
      }, ms);
    },
  };
  pageView.classList.toggle('full-bleed', Boolean(r.fullBleed));
  pageView.scrollTop = 0;
  announceAriaLive(`Sayfa açıldı: ${r.nav}`);
  r.render(pageView, m, ctx);
}

document.getElementById('sidebarToggle').addEventListener('click', () => {
  document.getElementById('sidebar').classList.contains('open') ? closeSidebar() : openSidebar();
});
document.getElementById('sidebarOverlay').addEventListener('click', closeSidebar);
window.addEventListener('hashchange', route);

initAssistant();
initPersonalSpace();
initAuthUi();
initPalette();
fetchHealthWizardStatus().then((hw) => { if (hw) window.__DADP_HEALTH_WIZARD__ = hw; }).catch(() => {});
route();
