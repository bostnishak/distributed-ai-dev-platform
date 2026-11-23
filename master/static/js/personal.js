// Personal space: profile card in the sidebar, theme/preferences and a full settings panel with
// usage statistics, personalization, cross-chat memory and data controls. No framework, no CDN.
import { api, formatDateTime, formatNumber, h, svg } from './util.js';

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

function savePatch({ settings, ...fields }) {
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
  setStatus('Kaydediliyor...');
  clearTimeout(saveTimer);
  saveTimer = setTimeout(flushSave, 450);
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
      h('button', { type: 'button', class: `sp-btn ${cls} sm`, onClick: async () => { await onConfirm(); reset(); } }, 'Evet'),
      h('button', { type: 'button', class: 'sp-btn sm', onClick: reset }, 'Vazgeç'));
  };
  reset();
  return holder;
}

// ---------------------------------------------------------------- charts

function dailyChart(daily) {
  const W = 720; const H = 190; const padL = 36; const padB = 22; const padT = 8;
  const max = Math.max(1, ...daily.map((d) => d.tokens));
  const niceMax = Math.ceil(max / 10 ** Math.max(0, String(max).length - 1)) * 10 ** Math.max(0, String(max).length - 1);
  const plotW = W - padL - 6; const plotH = H - padB - padT;
  const bw = plotW / daily.length;
  const root = svg('svg', { class: 'sp-chart', viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Günlük token kullanımı' });
  for (let i = 0; i <= 4; i += 1) {
    const y = padT + plotH - (plotH * i) / 4;
    root.append(svg('line', { class: 'grid', x1: padL, x2: W - 6, y1: y, y2: y }));
    root.append(svg('text', { x: padL - 5, y: y + 3, 'text-anchor': 'end' }, compact(Math.round((niceMax * i) / 4))));
  }
  daily.forEach((d, i) => {
    const bh = (plotH * d.tokens) / niceMax;
    const rect = svg('rect', { class: 'sp-bar', x: padL + i * bw + bw * 0.14, y: padT + plotH - bh, width: Math.max(1, bw * 0.72), height: Math.max(d.tokens ? 2 : 0, bh), rx: 2 });
    rect.append(svg('title', null, `${new Date(d.date).toLocaleDateString('tr-TR', { day: 'numeric', month: 'long' })}: ${formatNumber(d.tokens)} token, ${d.messages} mesaj`));
    root.append(rect);
    const step = Math.ceil(daily.length / 7);
    if (i % step === 0) {
      root.append(svg('text', { x: padL + i * bw + bw / 2, y: H - 6, 'text-anchor': 'middle' }, new Date(d.date).toLocaleDateString('tr-TR', { day: 'numeric', month: 'short' })));
    }
  });
  return root;
}

function hbars(items, nameKey, valueKey, valueLabel) {
  const max = Math.max(1, ...items.map((i) => i[valueKey]));
  return h('div', null, ...items.map((it) => h('div', { class: 'sp-hbar' },
    h('div', { class: 'sp-hbar-name', title: it[nameKey] }, it[nameKey]),
    h('div', { class: 'sp-hbar-track' }, h('div', { class: 'sp-hbar-fill', style: { width: `${(it[valueKey] / max) * 100}%` } })),
    h('div', { class: 'sp-hbar-val' }, valueLabel(it)))));
}

function hourStrip(byHour) {
  const max = Math.max(1, ...byHour);
  return h('div', null,
    h('div', { class: 'sp-hours' }, ...byHour.map((c, hr) => h('div', { class: 'sp-hour', title: `${String(hr).padStart(2, '0')}:00 - ${c} mesaj`, style: { opacity: c ? 0.18 + (0.82 * c) / max : 0.07 } }))),
    h('div', { class: 'sp-hours-axis' }, h('span', null, '00'), h('span', null, '06'), h('span', null, '12'), h('span', null, '18'), h('span', null, '23')));
}

// ---------------------------------------------------------------- sections

const TASK_LABELS = { genel: 'Genel sohbet', kod: 'Kod', analiz: 'Dosya analizi', cnc: 'CNC 2B', cad3d: 'CNC 3B CAD/CAM', proje: 'Proje üretimi', gorsel: 'Görsel', dokuman: 'Doküman', hesaplama: 'Hesaplama', engellendi: 'Engellenen' };

async function sectionOverview(body, state) {
  body.replaceChildren(h('div', { class: 'loading' }, h('span', { class: 'spinner' }), 'İstatistikler yükleniyor…'));
  const s = await api(`/api/user/${activeUserId}/stats?days=${state.days}`);
  monthTokens = s.budget.month_tokens;
  renderCard();
  const t = s.totals;

  const range = seg([[7, 'Son 7 gün'], [30, 'Son 30 gün'], [90, 'Son 90 gün']], state.days, (v) => { state.days = Number(v); sectionOverview(body, state); });
  range.style.marginBottom = '14px';

  if (!t.messages) {
    body.replaceChildren(range, h('div', { class: 'sp-card' }, h('div', { class: 'sp-empty' },
      'Bu dönemde henüz kullanım kaydı yok.', h('br'), 'Asistan ile sohbet ettikçe token, yanıt süresi ve model istatistikleri burada görünecek.')));
    return;
  }

  const kpi = (num, lbl, sub) => h('div', { class: 'sp-kpi' }, h('div', { class: 'sp-kpi-num' }, num), h('div', { class: 'sp-kpi-lbl' }, lbl), sub && h('div', { class: 'sp-kpi-sub' }, sub));
  const kpis = h('div', { class: 'sp-kpis' },
    kpi(formatNumber(t.total_tokens), 'Toplam token', `${formatNumber(t.prompt_tokens)} giriş · ${formatNumber(t.completion_tokens)} çıkış`),
    kpi(formatNumber(t.messages), 'Mesaj', `${formatNumber(t.conversations)} sohbet`),
    kpi(formatNumber(t.avg_tokens_per_message), 'Mesaj başına token'),
    kpi(`${(t.avg_latency_ms / 1000).toFixed(1).replace('.', ',')} sn`, 'Ort. yanıt süresi'),
    kpi(`${t.streak_days} gün`, 'Kesintisiz kullanım', `${t.active_days} aktif gün`));

  const cards = [range, kpis];

  const b = s.budget;
  if (b.monthly_token_budget > 0) {
    const cls = b.percent >= 100 ? 'danger' : b.percent >= 80 ? 'warn' : '';
    cards.push(h('div', { class: 'sp-card' },
      h('h3', null, 'Aylık token bütçesi', h('small', null, `%${String(b.percent).replace('.', ',')}`)),
      h('div', { class: 'small muted' }, `${formatNumber(b.month_tokens)} / ${formatNumber(b.monthly_token_budget)} token kullanıldı (bu takvim ayı)`),
      h('div', { class: `sp-progress ${cls}` }, h('div', { style: { width: `${Math.min(100, b.percent)}%` } }))));
  }

  cards.push(h('div', { class: 'sp-card' }, h('h3', null, 'Günlük token kullanımı', h('small', null, `${s.days} gün`)), dailyChart(s.daily)));

  const twoCol = h('div', { class: 'sp-grid-2' },
    h('div', { class: 'sp-card' }, h('h3', null, 'Modele göre kullanım'),
      hbars(s.by_model.slice(0, 7), 'model', 'tokens', (i) => `${compact(i.tokens)} tok · ${i.messages}`)),
    h('div', { class: 'sp-card' }, h('h3', null, 'İş türüne göre dağılım'),
      hbars(s.by_task.slice(0, 7).map((x) => ({ ...x, label: TASK_LABELS[x.task_type] || x.task_type })), 'label', 'messages', (i) => `${i.messages} mesaj`)));
  cards.push(twoCol);

  cards.push(h('div', { class: 'sp-card' }, h('h3', null, 'Günün hangi saatlerinde çalışıyorsunuz', h('small', null, 'yerel saat')), hourStrip(s.by_hour)));
  cards.push(h('div', { class: 'sp-note' }, `Bu sistem tamamen yerel çalışır; kullanım ücretsizdir. Karşılaştırma için: aynı hacim ücretli bir bulut API'sinde (varsayım: 1 USD / 1 Mn giriş, 4 USD / 1 Mn çıkış token) yaklaşık ${String(s.cloud_equivalent_usd).replace('.', ',')} USD tutardı. Bazı yanıtlarda model token sayısı bildirmez; bu durumda sayı karakter uzunluğundan tahmin edilir.`));
  body.replaceChildren(...cards);
}

async function sectionProfile(body) {
  const list = h('div');
  async function renderProfiles() {
    const data = await api('/api/user/profiles');
    avatarColors = data.avatar_colors || avatarColors;
    list.replaceChildren(...data.profiles.map((p) => h('div', { class: 'sp-list-item' },
      avatar(p, 'sm'),
      h('div', { class: 'sp-list-main' }, h('div', { class: 'sp-list-title' }, p.display_name, p.user_id === activeUserId && h('span', { class: 'sp-tag', style: { marginLeft: '8px' } }, 'Aktif')), h('div', { class: 'sp-list-sub' }, p.role_title || p.user_id)),
      p.user_id !== activeUserId && h('button', { type: 'button', class: 'sp-btn sm', onClick: () => switchProfile(p.user_id) }, 'Geç'),
      p.user_id !== 'default' && confirmButton('Sil', async () => {
        await api(`/api/user/${p.user_id}`, { method: 'DELETE' });
        if (p.user_id === activeUserId) switchProfile('default'); else renderProfiles();
      }))));
  }
  const newName = h('input', { class: 'sp-input', type: 'text', maxlength: 40, placeholder: 'Yeni profil adı (ör. Ayşe, Kalite Birimi)' });
  const addBtn = h('button', { type: 'button', class: 'sp-btn primary', onClick: async () => {
    if (!newName.value.trim()) return;
    const created = await api('/api/user/profiles', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ display_name: newName.value }) });
    switchProfile(created.user_id);
  } }, 'Profil oluştur');

  body.replaceChildren(
    h('div', { class: 'sp-inline', style: { marginBottom: '16px' } }, avatar(profile, 'lg'),
      h('div', null, h('div', { style: { fontWeight: 600, fontSize: '16px' } }, profile.display_name), h('div', { class: 'small muted' }, `Profil kimliği: ${profile.user_id}`))),
    h('div', { class: 'sp-grid-2' },
      textField('Görünen ad', profile.display_name, { max: 40, onInput: (v) => savePatch({ display_name: v }) }),
      textField('Unvan / rol', profile.role_title, { max: 60, placeholder: 'ör. Yazılım Geliştirici, Araştırmacı, Öğrenci', onInput: (v) => savePatch({ role_title: v }) })),
    textField('Hakkında', profile.bio, { multiline: true, max: 400, hint: 'Asistan bu bilgiyi sizi daha iyi tanımak için kullanmaz; yalnızca profil kartınızda görünür.', onInput: (v) => savePatch({ bio: v }) }),
    h('div', { class: 'sp-field' }, h('label', null, 'Avatar rengi'), swatches(avatarColors.map((c) => [c, c]), profile.avatar_color, (c) => { savePatch({ avatar_color: c }); sectionProfile(body); })),
    groupTitle('Profiller'),
    h('div', { class: 'sp-note' }, 'Her profilin kendi sohbet geçmişi, ayarları, hafızası ve istatistikleri vardır. Ortak bilgisayarda herkes kendi alanını kullanabilir.'),
    group(list),
    h('div', { class: 'sp-inline' }, newName, addBtn));
  await renderProfiles();
}

function switchProfile(uid) {
  localStorage.setItem(LS_USER, uid);
  location.reload();
}

function sectionAppearance(body) {
  const s = profile.settings;
  const themeCard = (val, label, cls) => {
    const btn = h('button', { type: 'button', class: `sp-theme-card${s.theme === val ? ' active' : ''}` },
      h('div', { class: `sp-prev ${cls}` }, h('div', { class: 'side' }), h('div', { class: 'main' }, h('i'), h('i'))), h('span', null, label));
    btn.addEventListener('click', () => { savePatch({ settings: { theme: val } }); sectionAppearance(body); });
    return btn;
  };
  body.replaceChildren(
    h('div', { class: 'sp-group-title', style: { marginTop: 0 } }, 'Tema'),
    h('div', { class: 'sp-theme-cards', style: { marginBottom: '16px' } }, themeCard('light', 'Açık', 'light'), themeCard('dark', 'Koyu', 'dark'), themeCard('system', 'Sistem', 'auto')),
    group(
      settingRow('Vurgu rengi', 'Düğmeler, bağlantılar ve seçili öğeler', swatches(Object.entries(ACCENTS), s.accent, (k) => savePatch({ settings: { accent: k } }), ACCENT_LABELS)),
      settingRow('Yazı boyutu', 'Sohbet ve sayfa metinleri', seg([['small', 'Küçük'], ['medium', 'Orta'], ['large', 'Büyük']], s.font_size, (v) => savePatch({ settings: { font_size: v } }))),
      settingRow('Yoğunluk', 'Boşlukları sıkılaştırarak ekrana daha çok içerik sığdırır', seg([['comfortable', 'Rahat'], ['compact', 'Sıkı']], s.density, (v) => savePatch({ settings: { density: v } }))),
      toggleRow('Animasyonları azalt', 'Geçiş ve hareket efektlerini kapatır', s.reduce_motion, (v) => savePatch({ settings: { reduce_motion: v } }))),
    groupTitle('Sohbet davranışı'),
    group(
      toggleRow('Enter ile gönder', 'Kapalıysa mesaj Ctrl+Enter ile gönderilir, Enter yeni satır ekler', s.send_with_enter, (v) => savePatch({ settings: { send_with_enter: v } })),
      toggleRow('Token ve süre bilgisini göster', 'Her yanıtın altında kullanılan token sayısı ve yanıt süresi', s.show_token_counter, (v) => savePatch({ settings: { show_token_counter: v } })),
      toggleRow('Model rozetini göster', 'Yanıtı üreten modelin adı', s.show_model_badge, (v) => savePatch({ settings: { show_model_badge: v } }))));
}

async function sectionAssistant(body) {
  const s = profile.settings;
  const preview = h('pre', { class: 'sp-preview-pre' }, '…');
  let previewTimer = null;
  async function refreshPreview() {
    try { preview.textContent = (await api(`/api/user/${activeUserId}/personalization-preview`)).system_note; } catch { preview.textContent = 'Önizleme alınamadı.'; }
  }
  function patch(p) {
    savePatch({ settings: p });
    clearTimeout(previewTimer);
    previewTimer = setTimeout(async () => { await flushSave(); refreshPreview(); }, 900);
  }
  const budget = h('input', { class: 'sp-input', type: 'number', min: 0, step: 10000, style: { width: '170px' } });
  budget.value = s.monthly_token_budget || 0;
  budget.addEventListener('input', () => patch({ monthly_token_budget: Math.max(0, parseInt(budget.value || '0', 10) || 0) }));

  body.replaceChildren(
    h('div', { class: 'sp-note' }, 'Bu tercihler asistanın her yanıtına gizli bir yönerge olarak eklenir. Yanıt biçimini ve dilini size göre ayarlar.'),
    group(
      settingRow('Yanıt uzunluğu', null, seg([['concise', 'Kısa'], ['balanced', 'Dengeli'], ['detailed', 'Ayrıntılı']], s.response_style, (v) => patch({ response_style: v }))),
      settingRow('Üslup', null, seg([['professional', 'Profesyonel'], ['friendly', 'Samimi'], ['technical', 'Teknik']], s.tone, (v) => patch({ tone: v }))),
      settingRow('Deneyim seviyesi', 'Açıklamaların derinliğini belirler', seg([['beginner', 'Başlangıç'], ['intermediate', 'Orta'], ['expert', 'Uzman']], s.expertise_level, (v) => patch({ expertise_level: v })))),
    textField('İlgi alanları ve çalışma bağlamı', s.interests, { max: 400, placeholder: 'ör. Yazılım geliştirme, veri analizi, akademik araştırma, tasarım', hint: 'Asistan örnekleri ve önerileri bu alanlara göre seçer.', onInput: (v) => patch({ interests: v }) }),
    textField('Özel talimatlar', s.custom_instructions, { multiline: true, max: 1500, placeholder: 'ör. Ölçüleri her zaman mm cinsinden ver. Tabloları tercih et. Önce kısa özet, sonra detay.', hint: 'Her yeni sohbette geçerli olan kalıcı kurallarınız.', onInput: (v) => patch({ custom_instructions: v }) }),
    groupTitle('Kullanım bütçesi'),
    group(settingRow('Aylık token bütçesi', '0 = sınırsız. Aşıldığında istatistik sayfasında uyarı gösterilir; kullanım engellenmez.', budget)),
    groupTitle('Asistana giden kişiselleştirme notu'),
    preview);
  refreshPreview();
}

async function sectionMemory(body) {
  const s = profile.settings;
  const factsBox = h('div');
  const convBox = h('div');
  const searchOut = h('div');

  async function renderFacts() {
    const { memories } = await api(`/api/user/${activeUserId}/memories`);
    factsBox.replaceChildren(...(memories.length ? memories.map((m) => h('div', { class: 'sp-list-item' },
      h('div', { class: 'sp-list-main' }, h('div', { class: 'sp-list-title' }, h('span', { class: 'sp-tag' }, m.category), m.fact_value), h('div', { class: 'sp-list-sub' }, formatDateTime(m.updated_at))),
      h('button', { type: 'button', class: 'sp-btn danger sm', onClick: async () => { await api(`/api/user/${activeUserId}/memories/${m.id}`, { method: 'DELETE' }); renderFacts(); } }, 'Unut'))) : [h('div', { class: 'sp-empty' }, 'Henüz öğrenilmiş bilgi yok. Sohbet ettikçe tercihleriniz ve proje bilgileriniz burada birikir.')]));
  }
  async function renderConvs() {
    const { conversations } = await api(`/api/user/${activeUserId}/conversations`);
    convBox.replaceChildren(...(conversations.length ? conversations.slice(0, 12).map((c) => h('div', {
      class: 'sp-list-item',
      style: { cursor: 'pointer' },
      title: 'Bu sohbeti aç',
      onClick: () => {
        closePanel();
        document.dispatchEvent(new CustomEvent('open-saved-chat', { detail: { chatId: c.id } }));
      },
    },
      h('div', { class: 'sp-list-main' }, h('div', { class: 'sp-list-title' }, c.title), h('div', { class: 'sp-list-sub' }, `${c.message_count} mesaj · ${formatDateTime(c.updated_at)}`)))) : [h('div', { class: 'sp-empty' }, 'Kayıtlı sohbet yok.')]));
  }

  const addInput = h('input', { class: 'sp-input', type: 'text', maxlength: 300, placeholder: 'Asistanın hatırlamasını istediğiniz bilgi (ör. Yanıtlarda kısa özet ve tablo tercih ederim)' });
  const addBtn = h('button', { type: 'button', class: 'sp-btn primary', onClick: async () => {
    if (!addInput.value.trim()) return;
    await api(`/api/user/${activeUserId}/memories`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ category: 'preference', fact_value: addInput.value }) });
    addInput.value = '';
    renderFacts();
  } }, 'Hatırla');

  const searchInput = h('input', { class: 'sp-input', type: 'text', placeholder: 'Geçmiş sohbetlerde ara (ör. proje planı, bütçe tablosu)' });
  async function doSearch() {
    if (!searchInput.value.trim()) { searchOut.replaceChildren(); return; }
    const { results } = await api(`/api/user/${activeUserId}/history/search?q=${encodeURIComponent(searchInput.value)}`);
    searchOut.replaceChildren(...(results.length ? results.map((r) => h('div', { class: 'sp-list-item' },
      h('div', { class: 'sp-list-main' }, h('div', { class: 'sp-list-title' }, r.title), h('div', { class: 'sp-list-sub' }, `${r.role === 'user' ? 'Siz' : 'Asistan'}: ${r.snippet}`)))) : [h('div', { class: 'sp-empty' }, 'Eşleşen kayıt bulunamadı.')]));
  }
  let searchTimer = null;
  searchInput.addEventListener('input', () => { clearTimeout(searchTimer); searchTimer = setTimeout(doSearch, 350); });

  body.replaceChildren(
    group(
      toggleRow('Diğer sohbetlerden bilgi al', 'Yeni bir soruda ilgili eski sohbetleriniz taranır ve bulunan bilgiler asistanın bağlamına eklenir.', s.cross_chat_memory, (v) => savePatch({ settings: { cross_chat_memory: v } })),
      toggleRow('Tercihleri otomatik öğren', 'Mesajlarınızdan standart, malzeme, teknoloji ve ad gibi kalıcı bilgiler çıkarılır.', s.auto_learn_facts, (v) => savePatch({ settings: { auto_learn_facts: v } }))),
    groupTitle('Öğrenilen bilgiler'),
    group(factsBox),
    h('div', { class: 'sp-inline', style: { marginBottom: '8px' } }, addInput, addBtn),
    groupTitle('Sohbet geçmişinde ara'),
    searchInput, searchOut,
    groupTitle('Son sohbetler'),
    group(convBox));
  addInput.style.flex = '1';
  await Promise.all([renderFacts(), renderConvs()]);
}

function sectionData(body) {
  const wipe = (scope, label, desc) => settingRow(label, desc, confirmButton('Sil', async () => {
    await api(`/api/user/${activeUserId}/data?scope=${scope}`, { method: 'DELETE' });
    if (scope === 'usage' || scope === 'all') { monthTokens = 0; renderCard(); }
    if (scope === 'conversations' || scope === 'all') { document.dispatchEvent(new CustomEvent('chats-wiped')); }
    setStatus('Silindi', true);
  }));
  body.replaceChildren(
    h('div', { class: 'sp-note' }, 'Tüm veriler yalnızca bu bilgisayardaki sunucuda tutulur ve hiçbir yere gönderilmez.'),
    group(
      settingRow('Verilerimi dışa aktar', 'Profil, ayarlar, öğrenilen bilgiler, istatistikler ve sohbetler tek bir JSON dosyası olarak iner.',
        h('a', { class: 'sp-btn primary', href: `/api/user/${activeUserId}/export`, download: '' }, 'JSON indir')),
      settingRow('Tam sistem yedeği (ZIP)', 'Tüm veritabanları, sohbetler ve üretilen çalışma alanlarını tek arşivde indirir.',
        h('a', { class: 'sp-btn', href: '/api/admin/backup.zip', download: '' }, 'Tam Yedek (.ZIP)'))),
    groupTitle('Verileri sil'),
    group(
      wipe('usage', 'Kullanım istatistikleri', 'Token ve yanıt süresi kayıtlarını siler.'),
      wipe('memories', 'Öğrenilen bilgiler', 'Asistanın sizin hakkınızda öğrendiği her şeyi unutturur.'),
      wipe('conversations', 'Sunucudaki sohbet kayıtları', 'Sohbetler arası arama için tutulan kopyayı siler. Tarayıcıdaki sohbet listeniz etkilenmez.'),
      wipe('all', 'Hepsi', 'Yukarıdakilerin tamamını siler. Profil ve ayarlar kalır.')));
}

// ---------------------------------------------------------------- panel shell

async function sectionMcp(body) {
  const listBox = h('div');
  const outPre = h('pre', { class: 'sp-preview-pre', hidden: true });

  async function renderConnectors() {
    const { connectors } = await api('/api/mcp/connectors');
    if (!connectors.length) {
      listBox.replaceChildren(h('div', { class: 'sp-empty' }, 'Henüz harici MCP bağlayıcısı eklenmedi. Yukarıdaki formdan herhangi bir MCP sunucu URL\'si ve API anahtarı ile bağlanabilirsiniz.'));
      return;
    }
    listBox.replaceChildren(...connectors.map((c) => {
      const toolsRow = c.tools && c.tools.length
        ? h('div', { style: { marginTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '6px' } },
          ...c.tools.map((t) => h('button', {
            type: 'button',
            class: 'sp-btn sm',
            title: t.description || t.name,
            onClick: async () => {
              const rawArgs = prompt(`"${t.name}" aracı için JSON argümanları (boş bırakabilirsiniz):`, '{}');
              if (rawArgs === null) return;
              let parsed = {};
              try { parsed = rawArgs.trim() ? JSON.parse(rawArgs) : {}; } catch { setStatus('Geçersiz JSON argümanı.'); return; }
              setStatus(`${t.name} çalıştırılıyor...`);
              try {
                const res = await api(`/api/mcp/connectors/${c.id}/call`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ tool_name: t.name, arguments: parsed }),
                });
                outPre.hidden = false;
                outPre.textContent = JSON.stringify(res, null, 2);
                setStatus(`${t.name} tamamlandı`, true);
              } catch (err) {
                outPre.hidden = false;
                outPre.textContent = String(err.message);
                setStatus('MCP çağrısı başarısız');
              }
            },
          }, `Çalıştır: ${t.name}`)))
        : null;

      return h('div', { class: 'sp-list-item', style: { flexDirection: 'column', alignItems: 'stretch' } },
        h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'space-between', flexWrap: 'wrap' } },
          h('div', { class: 'sp-list-main' },
            h('div', { class: 'sp-list-title' }, c.name, h('span', { class: 'sp-tag', style: { marginLeft: '8px' } }, c.enabled ? 'Aktif' : 'Pasif')),
            h('div', { class: 'sp-list-sub' }, `${c.url} · ${c.last_status}${c.has_api_key ? ` · Anahtar: ${c.api_key_masked}` : ''}`)),
          h('div', { class: 'sp-inline' },
            h('button', {
              type: 'button',
              class: 'sp-btn sm primary',
              onClick: async () => {
                setStatus(`${c.name} keşfediliyor...`);
                const res = await api(`/api/mcp/connectors/${c.id}/discover`, { method: 'POST' });
                setStatus(res.ok ? 'Araçlar keşfedildi' : (res.error || 'Bağlantı hatası'), Boolean(res.ok));
                renderConnectors();
              },
            }, 'Araçları Keşfet'),
            h('button', {
              type: 'button',
              class: 'sp-btn sm',
              onClick: async () => {
                await api(`/api/mcp/connectors/${c.id}`, {
                  method: 'PUT',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ enabled: !c.enabled }),
                });
                renderConnectors();
              },
            }, c.enabled ? 'Pasifleştir' : 'Aktifleştir'),
            confirmButton('Sil', async () => {
              await api(`/api/mcp/connectors/${c.id}`, { method: 'DELETE' });
              renderConnectors();
            }))),
        toolsRow);
    }));
  }

  const nameIn = h('input', { class: 'sp-input', type: 'text', placeholder: 'Bağlayıcı adı (ör. GitHub MCP, Notion, Özel API)' });
  const urlIn = h('input', { class: 'sp-input', type: 'url', placeholder: 'MCP Sunucu URL (ör. https://mcp.example.com/mcp)' });
  const keyIn = h('input', { class: 'sp-input', type: 'password', placeholder: 'MCP Connector API Key / Bearer Token (opsiyonel)' });
  const hdrIn = h('input', { class: 'sp-input', type: 'text', value: 'Authorization', placeholder: 'Başlık (Authorization veya X-API-Key)' });
  const addBtn = h('button', {
    type: 'button',
    class: 'sp-btn primary',
    onClick: async () => {
      if (!nameIn.value.trim() || !urlIn.value.trim()) {
        setStatus('Ad ve geçerli URL zorunludur.');
        return;
      }
      const hdr = hdrIn.value.trim() || 'Authorization';
      const prefix = hdr.toLowerCase() === 'authorization' ? 'Bearer ' : '';
      try {
        await api('/api/mcp/connectors', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: nameIn.value, url: urlIn.value, api_key: keyIn.value, auth_header: hdr, auth_prefix: prefix }),
        });
        nameIn.value = ''; urlIn.value = ''; keyIn.value = '';
        setStatus('MCP bağlayıcısı eklendi', true);
        renderConnectors();
      } catch (err) {
        setStatus(err.message);
      }
    },
  }, 'MCP Bağlayıcı Ekle');

  body.replaceChildren(
    h('div', { class: 'sp-note' }, 'Dışarıdaki herhangi bir MCP (Model Context Protocol) sunucusuna URL ve API anahtarı ile bağlanın. Keşfedilen araçları buradan veya doğrudan sohbet ekranından çalıştırabilirsiniz.'),
    h('div', { class: 'sp-grid-2' },
      h('div', { class: 'sp-field' }, h('label', null, 'Bağlayıcı Adı'), nameIn),
      h('div', { class: 'sp-field' }, h('label', null, 'MCP Sunucu URL'), urlIn)),
    h('div', { class: 'sp-grid-2' },
      h('div', { class: 'sp-field' }, h('label', null, 'API Anahtarı / Connector Key'), keyIn),
      h('div', { class: 'sp-field' }, h('label', null, 'Yetki Başlığı'), hdrIn)),
    h('div', { class: 'sp-inline', style: { marginBottom: '14px' } }, addBtn),
    groupTitle('Kayıtlı MCP Bağlayıcıları'),
    group(listBox),
    outPre);
  await renderConnectors();
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
    flushSave();
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
