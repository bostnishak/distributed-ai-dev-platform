// Personal space: profile card in the sidebar, theme/preferences and a full settings panel with
// usage statistics, personalization, cross-chat memory and data controls. No framework, no CDN.
import { renderSectionAppearance, renderSectionAssistant, renderSectionOverview, renderSectionProfile } from './personal_charts.js';
import { renderSectionData, renderSectionMcp, renderSectionMemory } from './personal_sections.js';
import { api, formatNumber, h, svg } from './util.js';

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

let activeUserId = localStorage.getItem(LS_USER) || 'default';
let profile = null;
let avatarColors = Object.values(ACCENTS);
const listeners = new Set();

export function getActiveUserId() { return activeUserId; }

export function getPrefs() {
  if (profile) return profile.settings;
  try { return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(LS_PREFS) || '{}') }; } catch { return { ...DEFAULTS }; }
}

export function onPrefsChange(fn) { listeners.add(fn); }

// ---------------------------------------------------------------- icons

const ICONS = {
  chart: 'M4 20V10M10 20V4M16 20v-8M22 20H2',
  user: 'M12 12a4 4 0 100-8 4 4 0 000 8zM4 21c0-4 4-6 8-6s8 2 8 6',
  sun: 'M12 16a4 4 0 100-8 4 4 0 000 8zM12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4',
  moon: 'M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z',
  spark: 'M12 3l2 5 5 2-5 2-2 5-2-5-5-2 5-2z',
  memory: 'M4 6c0-1.5 3.5-3 8-3s8 1.5 8 3-3.5 3-8 3-8-1.5-8-3zM4 6v6c0 1.5 3.5 3 8 3s8-1.5 8-3V6M4 12v6c0 1.5 3.5 3 8 3s8-1.5 8-3v-6',
  shield: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z',
  plug: 'M12 22v-5M9 8V2M15 8V2M18 8v5a6 6 0 01-12 0V8z',
  close: 'M6 6l12 12M18 6L6 18',
  gear: 'M12 15a3 3 0 100-6 3 3 0 000 6zM19.4 15a1.7 1.7 0 00.3 1.9l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.9-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.9.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.9 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.9l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.9.3h.1a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.9-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.9v.1a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z',
};

function icon(name) {
  const el = svg('svg', { class: 'sp-ico', viewBox: '0 0 24 24', 'aria-hidden': 'true' });
  el.append(svg('path', { d: ICONS[name] }));
  return el;
}

// ---------------------------------------------------------------- theme application

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
  try { localStorage.setItem(LS_PREFS, JSON.stringify(s)); } catch { /* storage unavailable */ }
  renderCard();
  listeners.forEach((fn) => fn(s));
}

window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  if (getPrefs().theme === 'system') applyPrefs(getPrefs());
});

// ---------------------------------------------------------------- profile persistence

let pending = {};
let saveTimer = null;
let statusEl = null;

function setStatus(text, ok = false) {
  if (!statusEl) return;
  statusEl.textContent = text;
  statusEl.classList.toggle('ok', ok);
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
  if (immediate) {
    return flushSave();
  }
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

// ---------------------------------------------------------------- sidebar card

function initials(name) {
  const parts = (name || '?').trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] || '?') + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toLocaleUpperCase('tr-TR');
}

function avatar(p, size = '') {
  const el = h('span', { class: `sp-avatar ${size}`, style: { background: p.avatar_color } }, initials(p.display_name));
  return el;
}

let monthTokens = null;
let monthMessages = 0;
let memoryCount = 0;

function compact(n) {
  if (n == null) return '—';
  if (n >= 1e6) return `${(n / 1e6).toFixed(1).replace('.', ',')} Mn`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1).replace('.', ',')} B`;
  return String(n);
}

function renderTopBar() {
  const bar = document.getElementById('assistantTopBar');
  if (!bar || !profile) return;
  const s = profile.settings || DEFAULTS;
  const themeLabel = s.theme === 'dark' ? 'Koyu Mod' : s.theme === 'light' ? 'Açık Mod' : 'Sistem Teması';
  const crossOn = s.cross_chat_memory !== false;
  const styleMap = { concise: 'Kısa', balanced: 'Dengeli', detailed: 'Ayrıntılı' };
  const toneMap = { professional: 'Profesyonel', friendly: 'Samimi', technical: 'Teknik' };

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
        profile.role_title ? h('span', { class: 'muted' }, `· ${profile.role_title}`) : null),
      h('button', { type: 'button', class: 'sp-pill', title: 'Sohbetler arası bilgi ve öğrenilen hafıza', onClick: () => openPanel('memory') },
        h('span', { class: `sp-pill-dot${crossOn ? '' : ' off'}` }),
        `Sohbetler Arası Bilgi: ${crossOn ? 'Açık' : 'Kapalı'} · ${memoryCount} hafıza kaydı`),
      h('button', { type: 'button', class: 'sp-pill', title: 'Asistan kişiselleştirme ayarları', onClick: () => openPanel('assistant') },
        icon('spark'),
        `${styleMap[s.response_style] || 'Dengeli'} · ${toneMap[s.tone] || 'Profesyonel'}`)),
    h('div', { class: 'sp-topbar-right' },
      h('button', { type: 'button', class: 'sp-pill', title: 'Token kullanımı ve performans istatistikleri', onClick: () => openPanel('overview') },
        icon('chart'),
        h('strong', null, `${compact(monthTokens || 0)} token`),
        h('span', { class: 'muted' }, `· ${monthMessages} mesaj`)),
      h('button', { type: 'button', class: 'sp-pill', title: 'Görünüm, tema ve yazı boyutu ayarları', onClick: () => openPanel('appearance') },
        icon(document.documentElement.dataset.theme === 'dark' ? 'sun' : 'moon'),
        themeLabel)));
}

function renderCard() {
  const host = document.getElementById('userCard');
  if (!host || !profile) return;
  host.replaceChildren(
    avatar(profile),
    h('div', { class: 'sp-usercard-text' },
      h('div', { class: 'sp-usercard-name' }, profile.display_name),
      h('div', { class: 'sp-usercard-sub' }, monthTokens == null ? 'Kişisel alan ve ayarlar' : `${compact(monthTokens)} token bu ay`)),
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

// ---------------------------------------------------------------- widgets

function seg(options, value, onChange) {
  const box = h('div', { class: 'sp-seg', role: 'group' });
  for (const [val, label] of options) {
    const btn = h('button', { type: 'button', class: val === value ? 'active' : '' }, label);
    btn.addEventListener('click', () => {
      box.querySelectorAll('button').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      onChange(val);
    });
    box.append(btn);
  }
  return box;
}

function toggleRow(label, desc, value, onChange) {
  const input = h('input', { type: 'checkbox', 'aria-label': label });
  input.checked = Boolean(value);
  input.addEventListener('change', () => onChange(input.checked));
  return h('div', { class: 'sp-row' },
    h('div', { class: 'sp-row-text' }, h('div', { class: 'sp-row-label' }, label), desc && h('div', { class: 'sp-row-desc' }, desc)),
    h('label', { class: 'sp-switch' }, input, h('span', { class: 'sp-switch-track' })));
}

function settingRow(label, desc, control) {
  return h('div', { class: 'sp-row' },
    h('div', { class: 'sp-row-text' }, h('div', { class: 'sp-row-label' }, label), desc && h('div', { class: 'sp-row-desc' }, desc)),
    control);
}

function textField(label, value, { multiline = false, max = 400, hint = '', onInput, placeholder = '' }) {
  const control = multiline ? h('textarea', { class: 'sp-textarea', maxlength: max, placeholder }) : h('input', { class: 'sp-input', type: 'text', maxlength: max, placeholder });
  control.value = value || '';
  const counter = multiline ? h('div', { class: 'sp-counter' }, `${control.value.length}/${max}`) : null;
  control.addEventListener('input', () => {
    if (counter) counter.textContent = `${control.value.length}/${max}`;
    onInput(control.value);
  });
  return h('div', { class: 'sp-field' }, h('label', null, label), control, counter, hint && h('div', { class: 'sp-hint' }, hint));
}

function swatches(colors, current, onPick, labels = null) {
  const box = h('div', { class: 'sp-swatches' });
  for (const [key, color] of colors) {
    const b = h('button', { type: 'button', class: `sp-swatch${key === current ? ' active' : ''}`, style: { background: color }, title: labels ? labels[key] : color, 'aria-label': labels ? labels[key] : color });
    b.addEventListener('click', () => {
      box.querySelectorAll('.sp-swatch').forEach((x) => x.classList.remove('active'));
      b.classList.add('active');
      onPick(key);
    });
    box.append(b);
  }
  return box;
}

function group(...children) { return h('div', { class: 'sp-group' }, ...children); }
function groupTitle(text) { return h('div', { class: 'sp-group-title' }, text); }

function confirmButton(label, onConfirm, cls = 'danger') {
  const holder = h('span', { class: 'sp-inline' });
  const reset = () => {
    holder.replaceChildren(h('button', { type: 'button', class: `sp-btn ${cls} sm`, onClick: ask }, label));
  };
  const ask = () => {
    holder.replaceChildren(
      h('span', { class: 'muted small' }, 'Emin misiniz?'),
      h('button', {
        type: 'button',
        class: `sp-btn ${cls} sm`,
        onClick: async () => {
          try {
            await onConfirm();
          } catch (err) {
            setStatus(`İşlem başarısız: ${err.message}`);
          } finally {
            reset();
          }
        },
      }, 'Evet'),
      h('button', { type: 'button', class: 'sp-btn sm', onClick: reset }, 'Vazgeç'));
  };
  reset();
  return holder;
}

// ---------------------------------------------------------------- sections (charts & overview in personal_charts.js)

async function sectionOverview(body, state) {
  return renderSectionOverview(body, state, {
    activeUserId,
    setMonthTokens: (n) => { monthTokens = n; },
    renderCard,
    seg,
    compact,
  });
}

async function sectionProfile(body) {
  return renderSectionProfile(body, {
    activeUserId, profile, avatar, avatarColors,
    setAvatarColors: (c) => { avatarColors = c; },
    switchProfile, confirmButton, setStatus, textField, swatches, savePatch, group, groupTitle,
  });
}

function switchProfile(uid) {
  localStorage.setItem(LS_USER, uid);
  location.reload();
}

function sectionAppearance(body) {
  return renderSectionAppearance(body, {
    profile, ACCENTS, ACCENT_LABELS, savePatch, group, groupTitle, settingRow, swatches, seg, toggleRow,
  });
}

async function sectionAssistant(body) {
  return renderSectionAssistant(body, {
    activeUserId, profile, savePatch, flushSave, group, groupTitle, settingRow, seg, textField,
  });
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

async function sectionMemory(body) {
  return renderSectionMemory(body, _sectionCtx());
}

function sectionData(body) {
  return renderSectionData(body, _sectionCtx());
}

async function sectionMcp(body) {
  return renderSectionMcp(body, _sectionCtx());
}

const SECTIONS = [
  ['overview', 'İstatistikler', 'chart', 'Kullanım özeti', 'Token, yanıt süresi, model ve zaman dağılımı'],
  ['profile', 'Profil', 'user', 'Profil ve hesaplar', 'Kimlik bilgileriniz ve profil geçişi'],
  ['appearance', 'Görünüm', 'sun', 'Görünüm ve sohbet', 'Tema, renk, yazı boyutu ve davranışlar'],
  ['assistant', 'Kişiselleştirme', 'spark', 'Asistanı kişiselleştir', 'Üslup, seviye, özel talimatlar ve bütçe'],
  ['memory', 'Hafıza', 'memory', 'Hafıza ve sohbetler arası bilgi', 'Öğrenilen bilgiler ve geçmiş sohbet araması'],
  ['mcp', 'MCP Bağlantıları', 'plug', 'Harici MCP Bağlayıcıları', 'API anahtarı ile harici MCP sunucularına bağlanın ve araç çalıştırın'],
  ['data', 'Veri ve gizlilik', 'shield', 'Veri ve gizlilik', 'Dışa aktarma ve silme'],
];

let overlay = null;

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
      if (key === 'overview') await sectionOverview(body, state);
      else if (key === 'profile') await sectionProfile(body);
      else if (key === 'appearance') sectionAppearance(body);
      else if (key === 'assistant') await sectionAssistant(body);
      else if (key === 'memory') await sectionMemory(body);
      else if (key === 'mcp') await sectionMcp(body);
      else sectionData(body);
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
  document.addEventListener('keydown', onKey);
  document.body.append(overlay);
  show(section);
}

// ---------------------------------------------------------------- init

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
  document.addEventListener('usage-updated', refreshMonthTokens);
  await loadProfile();
  refreshMonthTokens();
}
