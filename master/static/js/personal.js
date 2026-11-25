// Personal space: profile card in the sidebar, theme/preferences and a full settings panel with
// usage statistics, personalization, cross-chat memory and data controls. No framework, no CDN.
import { renderSectionAppearance, renderSectionAssistant, renderSectionOverview, renderSectionProfile } from './personal_charts.js';
import { renderSectionData, renderSectionMcp, renderSectionMemory } from './personal_sections.js';
import {
  avatar,
  compact,
  confirmButton as buildConfirmButton,
  group,
  groupTitle,
  icon,
  seg,
  settingRow,
  swatches,
  textField,
  toggleRow,
} from './personal_ui.js';
import { bindGlobalEvent, storageGet, storageSet } from './storage.js';
import { api, h } from './util.js';

const LS_USER = 'cm6453_user_id';
const LS_PREFS = 'cm6453_prefs';

const DEFAULTS = {
  theme: 'system', accent: 'indigo', font_size: 'medium', density: 'comfortable',
  reduce_motion: false, send_with_enter: true, show_token_counter: true, show_model_badge: true,
  response_style: 'balanced', tone: 'professional', expertise_level: 'intermediate',
  interests: '', custom_instructions: '', cross_chat_memory: true, auto_learn_facts: true,
  monthly_token_budget: 0,
};

const ACCENTS = { indigo: '#4f46e5', teal: '#0d9488', emerald: '#059669', rose: '#e11d48', amber: '#d97706', slate: '#475569' };
const ACCENT_LABELS = { indigo: 'Çivit', teal: 'Turkuaz', emerald: 'Zümrüt', rose: 'Gül', amber: 'Kehribar', slate: 'Arduvaz' };
const SECTIONS = [
  ['overview', 'İstatistikler', 'chart', 'Kullanım özeti', 'Token, yanıt süresi, model ve zaman dağılımı'],
  ['profile', 'Profil', 'user', 'Profil ve hesaplar', 'Kimlik bilgileriniz ve profil geçişi'],
  ['appearance', 'Görünüm', 'sun', 'Görünüm ve sohbet', 'Tema, renk, yazı boyutu ve davranışlar'],
  ['assistant', 'Kişiselleştirme', 'spark', 'Asistanı kişiselleştir', 'Üslup, seviye, özel talimatlar ve bütçe'],
  ['memory', 'Hafıza', 'memory', 'Hafıza ve sohbetler arası bilgi', 'Öğrenilen bilgiler ve geçmiş sohbet araması'],
  ['mcp', 'MCP Bağlantıları', 'plug', 'Harici MCP Bağlayıcıları', 'API anahtarı ile harici MCP sunucularına bağlanın ve araç çalıştırın'],
  ['data', 'Veri ve gizlilik', 'shield', 'Veri ve gizlilik', 'Dışa aktarma ve silme'],
];

let activeUserId = storageGet(LS_USER, 'default') || 'default';
let profile = null;
let avatarColors = Object.values(ACCENTS);
const listeners = new Set();
let pending = {};
let saveTimer = null;
let statusEl = null;
let monthTokens = null;
let monthMessages = 0;
let memoryCount = 0;
let overlay = null;

export function getActiveUserId() { return activeUserId; }

export function getPrefs() {
  if (profile) return profile.settings;
  try { return { ...DEFAULTS, ...JSON.parse(storageGet(LS_PREFS, '{}') || '{}') }; } catch { return { ...DEFAULTS }; }
}

export function onPrefsChange(fn) { listeners.add(fn); }

function resolveTheme(t) {
  if (t === 'system') return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  return t;
}

export function applyPrefs(s) {
  const root = document.documentElement;
  root.dataset.theme = resolveTheme(s.theme);
  root.dataset.accent = s.accent;
  root.dataset.font = s.font_size;
  root.dataset.density = s.density;
  root.dataset.motion = s.reduce_motion ? 'reduced' : 'normal';
  storageSet(LS_PREFS, JSON.stringify(s));
  renderCard();
  listeners.forEach((fn) => fn(s));
}

window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  if (getPrefs().theme === 'system') applyPrefs(getPrefs());
});

function setStatus(text, ok = false) {
  if (!statusEl) return;
  statusEl.textContent = text;
  statusEl.classList.toggle('ok', ok);
}

function confirmButton(label, onConfirm, cls = 'danger') {
  return buildConfirmButton(label, onConfirm, cls, (err) => setStatus(`İşlem başarısız: ${err.message}`));
}

async function flushSave() {
  if (!Object.keys(pending).length) return;
  const body = pending;
  pending = {};
  clearTimeout(saveTimer);
  try {
    const updated = await api(`/api/user/${activeUserId}/profile`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    profile = { ...profile, ...updated, settings: { ...profile.settings, ...updated.settings } };
    renderCard();
    setStatus('Kaydedildi', true);
  } catch (err) {
    setStatus(`Kaydedilemedi: ${err.message}`);
  }
}

function savePatch({ settings, ...fields }, immediate = false) {
  if (settings) {
    profile.settings = { ...profile.settings, ...settings };
    pending.settings = { ...(pending.settings || {}), ...settings };
    applyPrefs(profile.settings);
  }
  for (const [k, v] of Object.entries(fields)) {
    profile[k] = v;
    pending[k] = v;
  }
  renderCard();
  syncRailHead();
  setStatus('Kaydediliyor...');
  clearTimeout(saveTimer);
  if (immediate) return flushSave();
  saveTimer = setTimeout(flushSave, 350);
  return Promise.resolve();
}

function syncRailHead() {
  if (!overlay || !profile) return;
  const head = overlay.querySelector('.sp-rail-head');
  if (!head) return;
  head.replaceChildren(
    avatar(profile),
    h('div', null,
      h('div', { class: 'sp-rail-name' }, profile.display_name),
      h('div', { class: 'sp-rail-sub' }, profile.role_title || 'Kişisel alan')),
  );
}

async function loadProfile() {
  try {
    profile = await api(`/api/user/${activeUserId}/profile`);
  } catch {
    profile = { user_id: activeUserId, display_name: 'Kullanıcı', role_title: '', bio: '', avatar_color: ACCENTS.indigo, settings: { ...DEFAULTS, ...getPrefs() } };
  }
  profile.settings = { ...DEFAULTS, ...profile.settings };
  applyPrefs(profile.settings);
}

function renderTopBar() {
  const bar = document.getElementById('assistantTopBar');
  if (!bar || !profile) return;
  const s = profile.settings || DEFAULTS;

  const greet = document.getElementById('heroGreeting');
  if (greet) {
    greet.textContent = profile.display_name && profile.display_name !== 'Kullanici'
      ? `Merhaba ${profile.display_name}, bugün ne üretelim?`
      : 'Bugün aklında ne var?';
  }

  bar.replaceChildren(
    h('div', { class: 'sp-topbar-left' },
      h('button', { type: 'button', class: 'sp-pill', title: 'Profil ve hesap ayarları', onClick: () => openPanel('profile') },
        avatar(profile, 'sm'),
        h('strong', null, profile.display_name),
        profile.role_title ? h('span', { class: 'muted' }, `· ${profile.role_title}`) : null)),
    h('div', { class: 'sp-topbar-right' },
      h('button', { type: 'button', class: 'sp-pill', title: 'Token kullanımı ve performans istatistikleri', onClick: () => openPanel('overview') },
        icon('chart'),
        h('strong', null, `${compact(monthTokens || 0)} token`),
        h('span', { class: 'muted' }, `· ${monthMessages} mesaj`)),
      h('button', { type: 'button', class: 'sp-pill', title: document.documentElement.dataset.theme === 'dark' ? 'Açık temaya geç' : 'Koyu temaya geç', 'aria-label': 'Temayı değiştir', onClick: () => { savePatch({ settings: { theme: document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark' } }); flushSave(); } },
        icon(document.documentElement.dataset.theme === 'dark' ? 'sun' : 'moon'))));
}

function renderCard() {
  const host = document.getElementById('userCard');
  if (!host || !profile) return;
  host.replaceChildren(
    avatar(profile),
    h('div', { class: 'sp-usercard-text' },
      h('div', { class: 'sp-usercard-name' }, profile.display_name),
      h('div', { class: 'sp-usercard-sub' }, (monthTokens === null || monthTokens === undefined) ? 'Kişisel alan ve ayarlar' : `${compact(monthTokens)} token bu ay`)),
    h('span', { class: 'sp-icon-btn', title: 'Ayarlar' }, icon('gear')),
  );
  renderTopBar();
}

async function refreshMonthTokens() {
  try {
    const [s, m] = await Promise.all([
      api(`/api/user/${activeUserId}/stats?days=30`),
      api(`/api/user/${activeUserId}/memories`),
    ]);
    monthTokens = s.budget.month_tokens;
    monthMessages = (s.totals && s.totals.messages) || 0;
    memoryCount = (m.memories && m.memories.length) || 0;
    renderCard();
  } catch { /* stats are optional for the card */ }
}

function switchProfile(uid) {
  storageSet(LS_USER, uid);
  location.reload();
}

function _sectionCtx() {
  return {
    activeUserId,
    profile,
    setStatus,
    setMemoryCount: (n) => { memoryCount = n; },
    resetCounters: (scope) => {
      if (scope === 'usage' || scope === 'all') { monthTokens = 0; monthMessages = 0; }
      if (scope === 'memories' || scope === 'all') memoryCount = 0;
    },
    renderCard,
    closePanel,
    group,
    groupTitle,
    toggleRow,
    settingRow,
    seg,
    savePatch,
    confirmButton,
  };
}

async function renderActiveSection(key, body, state) {
  if (key === 'overview') {
    await renderSectionOverview(body, state, { activeUserId, setMonthTokens: (n) => { monthTokens = n; }, renderCard, seg, compact });
  } else if (key === 'profile') {
    await renderSectionProfile(body, {
      activeUserId, profile, avatar, avatarColors, setAvatarColors: (c) => { avatarColors = c; },
      switchProfile, confirmButton, setStatus, textField, swatches, savePatch, group, groupTitle,
    });
  } else if (key === 'appearance') {
    renderSectionAppearance(body, { profile, ACCENTS, ACCENT_LABELS, savePatch, group, groupTitle, settingRow, swatches, seg, toggleRow });
  } else if (key === 'assistant') {
    await renderSectionAssistant(body, { activeUserId, profile, savePatch, flushSave, group, groupTitle, settingRow, seg, textField });
  } else if (key === 'memory') {
    await renderSectionMemory(body, _sectionCtx());
  } else if (key === 'mcp') {
    await renderSectionMcp(body, _sectionCtx());
  } else {
    renderSectionData(body, _sectionCtx());
  }
}

function closePanel() {
  flushSave();
  overlay?.remove();
  overlay = null;
  statusEl = null;
  document.removeEventListener('keydown', onKey);
  document.getElementById('userCard')?.focus();
  refreshMonthTokens();
}

function onKey(e) { if (e.key === 'Escape') closePanel(); }

export function openPanel(section = 'overview') {
  if (overlay || !profile) return;
  const state = { days: 30 };
  const body = h('div', { class: 'sp-body' });
  const title = h('h2', { class: 'sp-content-title' });
  const lead = h('p', { class: 'sp-content-lead' });
  statusEl = h('div', { class: 'sp-status' });
  const navButtons = {};

  async function show(key) {
    await flushSave();
    for (const [k, btn] of Object.entries(navButtons)) btn.classList.toggle('active', k === key);
    const meta = SECTIONS.find((x) => x[0] === key);
    title.textContent = meta[3];
    lead.textContent = meta[4];
    setStatus('');
    body.scrollTop = 0;
    try {
      await renderActiveSection(key, body, state);
    } catch (err) {
      body.replaceChildren(h('div', { class: 'card error' }, `Bu bölüm yüklenemedi: ${err.message}`));
    }
  }

  const rail = h('aside', { class: 'sp-rail' },
    h('div', { class: 'sp-rail-head' }, avatar(profile),
      h('div', null, h('div', { class: 'sp-rail-name' }, profile.display_name), h('div', { class: 'sp-rail-sub' }, profile.role_title || 'Kişisel alan'))));
  for (const [key, label, ic] of SECTIONS) {
    const btn = h('button', { type: 'button', class: 'sp-nav-btn' }, icon(ic), label);
    btn.addEventListener('click', () => show(key));
    navButtons[key] = btn;
    rail.append(btn);
  }
  rail.append(h('div', { class: 'sp-rail-foot' }, 'Veriler yalnızca bu sunucuda saklanır. %100 lokal.'));

  const closeBtn = h('button', { type: 'button', class: 'sp-icon-btn sp-close', title: 'Kapat (Esc)', 'aria-label': 'Kapat', onClick: closePanel }, icon('close'));
  const content = h('section', { class: 'sp-content' },
    h('div', { class: 'sp-content-head' }, h('div', null, title, lead), h('div', { class: 'sp-inline' }, statusEl, closeBtn)), body);

  overlay = h('div', { class: 'sp-overlay' }, h('div', { class: 'sp-modal', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Kişisel alan' }, rail, content));
  overlay.addEventListener('mousedown', (e) => { if (e.target === overlay) closePanel(); });
  bindGlobalEvent(document, 'keydown', onKey);
  document.body.append(overlay);
  show(section);
}

export async function initPersonalSpace() {
  const card = document.getElementById('userCard');
  if (card) card.addEventListener('click', () => openPanel('overview'));
  const toggle = document.getElementById('themeToggle');
  if (toggle) {
    const sync = () => {
      toggle.replaceChildren(icon(document.documentElement.dataset.theme === 'dark' ? 'sun' : 'moon'));
      toggle.title = document.documentElement.dataset.theme === 'dark' ? 'Açık temaya geç' : 'Koyu temaya geç';
    };
    onPrefsChange(sync);
    toggle.addEventListener('click', () => {
      savePatch({ settings: { theme: document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark' } });
      flushSave();
    });
    sync();
  }
  bindGlobalEvent(document, 'usage-updated', refreshMonthTokens);
  await loadProfile();
  refreshMonthTokens();
}
