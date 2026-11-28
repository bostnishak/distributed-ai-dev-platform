// Shell: hash router, navigation and the mobile sidebar drawer.
import { renderAgents } from './agents.js';
import { focusAssistant, initAssistant } from './assistant.js';
import { initAuthUi } from './auth_modal.js';
import { initChatEnhancements } from './chat_enhancements.js';
import { renderCnc } from './cnc.js';
import { renderDashboard } from './dashboard.js';
import { initGlassBox } from './glass_box.js';
import { renderHub } from './hub.js';
import { initPalette } from './palette.js';
import { renderArtifacts, renderFiles, renderShare } from './panels.js';
import { initPersonalSpace } from './personal.js';
import { renderNewProject, renderProjectDetail, renderProjects } from './projects.js';
import { createReactiveStore } from './store.js';
import { bindGlobalEvent, startManagedInterval, storageGet, storageSet } from './storage.js';
import { renderStudio } from './studio.js';
import { closeSidebar, isDesktop, openSidebar } from './util.js';
import { announceAriaLive, fetchHealthWizardStatus } from './ux_shell.js';
import { initWarRoom } from './war_room.js';

const appStore = createReactiveStore();
initGlassBox();
window.__DADP_STORE__ = appStore;

if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === '127.0.0.1' || location.hostname === 'localhost')) {
  navigator.serviceWorker.register('/static/sw.js').catch(() => {});
}

const pageView = document.getElementById('view-page');
const assistantView = document.getElementById('view-assistant');
const assistantSide = document.getElementById('assistantSide');

const SITE_TITLE = 'Dağıtık YZ Platformu';
const ROUTES = [
  { pattern: /^#\/new$/, nav: 'new', title: 'Yeni Proje', render: (root) => renderNewProject(root) },
  { pattern: /^#\/projects$/, nav: 'projects', title: 'Projeler', render: (root) => renderProjects(root) },
  { pattern: /^#\/projects\/(\d+)$/, nav: 'projects', title: 'Proje Detayı', render: (root, m, ctx) => renderProjectDetail(root, Number(m[1]), ctx) },
  { pattern: /^#\/agents$/, nav: 'agents', title: 'Ajanlar', render: (root, _m, ctx) => renderAgents(root, ctx) },
  { pattern: /^#\/dashboard$/, nav: 'dashboard', title: 'Performans Panosu', render: (root, _m, ctx) => renderDashboard(root, ctx) },
  { pattern: /^#\/studios$/, nav: 'studios', title: 'Stüdyolar ve Yönetim', render: (root, _m, ctx) => renderHub(root, ctx) },
  { pattern: /^#\/studio$/, nav: 'studio', title: 'Kod Stüdyosu (IDE)', render: (root) => renderStudio(root), fullBleed: true },
  { pattern: /^#\/cnc$/, nav: 'cnc', title: 'CNC Balonlama', render: (root) => renderCnc(root) },
  { pattern: /^#\/artifacts$/, nav: 'artifacts', title: 'Artefaktlar', render: (root, _m, ctx) => renderArtifacts(root, ctx) },
  { pattern: /^#\/files$/, nav: 'files', title: 'Dosyalar ve Bilgi Bankası', render: (root, _m, ctx) => renderFiles(root, ctx) },
  { pattern: /^#\/share\/([\w-]+)$/, nav: 'assistant', title: 'Paylaşılan Sohbet', render: (root, m) => renderShare(root, m[1]) },
  { pattern: /^#\/assistant$/, nav: 'assistant', title: 'Asistan', render: null },
];

function syncHeroHeadingLevel(isAssistant) {
  const cur = document.getElementById('heroGreeting');
  if (!cur) return;
  const desired = isAssistant ? 'H1' : 'H2';
  if (cur.tagName === desired) return;
  const next = document.createElement(desired.toLowerCase());
  next.id = cur.id;
  next.className = cur.className;
  next.textContent = cur.textContent;
  cur.replaceWith(next);
}

let pollTimer = null;
let routeToken = 0;

function stopPoll() {
  if (typeof pollTimer === 'function') pollTimer();
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
  document.title = `${r.title} — ${SITE_TITLE}`;
  syncHeroHeadingLevel(isAssistant);
  assistantView.hidden = !isAssistant;
  assistantSide.hidden = !isAssistant;
  pageView.hidden = isAssistant;
  closeSidebar();

  const mainEl = document.getElementById('main');
  if (isAssistant) {
    announceAriaLive(`Sayfa açıldı: ${r.title}`);
    if (isDesktop()) focusAssistant();
    else if (mainEl) mainEl.focus({ preventScroll: true });
    return;
  }
  const ctx = {
    isCurrent: () => token === routeToken,
    stopPoll,
    poll(fn, ms) {
      stopPoll();
      pollTimer = startManagedInterval(async () => {
        if (token !== routeToken) return stopPoll();
        try { await fn(); } catch { /* transient network error: try again on the next tick */ }
      }, ms);
    },
  };
  pageView.classList.toggle('full-bleed', Boolean(r.fullBleed));
  pageView.scrollTop = 0;
  announceAriaLive(`Sayfa açıldı: ${r.title}`);
  r.render(pageView, m, ctx);
  if (mainEl) mainEl.focus({ preventScroll: true });
}

const SIDEBAR_KEY = 'cm6453_sidebar_collapsed';
function applySidebarCollapsed(collapsed) {
  document.body.classList.toggle('sidebar-collapsed', collapsed);
  document.getElementById('sidebarToggle').setAttribute('aria-expanded', String(!collapsed));
}
applySidebarCollapsed(storageGet(SIDEBAR_KEY, '0') === '1');
document.getElementById('sidebarToggle').addEventListener('click', () => {
  if (isDesktop()) {
    const next = !document.body.classList.contains('sidebar-collapsed');
    applySidebarCollapsed(next);
    storageSet(SIDEBAR_KEY, next ? '1' : '0');
    return;
  }
  document.getElementById('sidebar').classList.contains('open') ? closeSidebar() : openSidebar();
});
document.getElementById('sidebarOverlay').addEventListener('click', closeSidebar);
bindGlobalEvent(window, 'hashchange', route);

initAssistant();
initChatEnhancements();
initPersonalSpace();
initAuthUi();
initPalette();
initWarRoom();
fetchHealthWizardStatus().then((hw) => { if (hw) window.__DADP_HEALTH_WIZARD__ = hw; }).catch(() => {});
route();
