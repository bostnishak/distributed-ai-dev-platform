// F204 Chat & Accessibility Enhancements: SOH-01..10, ERI-01..05, DOS-03, DOS-06 (offline, zero CDN, zero emojis).
import { toggleVoiceMode } from './assistant_voice.js';
import { bindGlobalEvent, safeFetchJson, storageGet, storageRemove, storageSet } from './storage.js';
import { HIDDEN_PAGES } from './assistant_nav.js';
import { pillIcon } from './pill_icons.js';
import { openDock } from './studio_dock.js';
import { h } from './util.js';

const DRAFT_KEY = 'cm6453_chat_draft';
const MODEL_KEY = 'cm6453_selected_model';
const AGENT_KEY = 'cm6453_selected_custom_agent';
let toastHost = null;

export function getSelectedModel() {
  const el = document.getElementById('modelPicker');
  if (el && el.value) return el.value;
  return storageGet(MODEL_KEY, '') || '';
}

export function getSelectedCustomAgent() {
  const el = document.getElementById('customAgentPicker');
  if (el && el.value) return el.value;
  return storageGet(AGENT_KEY, '') || '';
}

async function mountModelAndAgentPickers() {
  const inputWrap = document.getElementById('inputWrap');
  const inputPill = document.getElementById('inputPill');
  if (!inputWrap || !inputPill || document.getElementById('chatToolbarRow')) return;
  const modelSel = h('select', { id: 'modelPicker', class: 'chat-toolbar-select', 'aria-label': 'Model seçici' }, h('option', { value: '' }, 'Otomatik'));
  const agentSel = h('select', { id: 'customAgentPicker', class: 'chat-toolbar-select', 'aria-label': 'Özel ajan seçici' }, h('option', { value: '' }, 'Varsayılan asistan'));
  modelSel.addEventListener('change', () => storageSet(MODEL_KEY, modelSel.value));
  agentSel.addEventListener('change', () => storageSet(AGENT_KEY, agentSel.value));
  const popover = h('div', { id: 'chatToolbarRow', class: 'chat-options', role: 'dialog', 'aria-label': 'Sohbet seçenekleri', hidden: true },
    h('label', { class: 'chat-options-field' }, h('span', null, 'Model'), modelSel),
    h('label', { class: 'chat-options-field' }, h('span', null, 'Ajan'), agentSel),
    h('div', { class: 'chat-options-tools' }, h('span', null, 'Araçlar'),
      ...HIDDEN_PAGES.map((pg) => h('button', { type: 'button', class: 'chip-btn', onClick: () => { setOpen(false); openDock(pg.key); } }, pg.label))));
  const optionsBtn = h('button', { id: 'chatOptionsBtn', type: 'button', class: 'pill-icon-btn', title: 'Model ve ajan seç', 'aria-label': 'Model ve ajan seç', 'aria-expanded': 'false' }, pillIcon('tune'));
  const setOpen = (open) => { popover.hidden = !open; optionsBtn.setAttribute('aria-expanded', String(open)); };
  optionsBtn.addEventListener('click', (e) => { e.stopPropagation(); setOpen(popover.hidden); });
  popover.addEventListener('click', (e) => e.stopPropagation());
  bindGlobalEvent(document, 'click', () => setOpen(false));
  bindGlobalEvent(document, 'keydown', (e) => { if (e.key === 'Escape') setOpen(false); });
  inputWrap.append(popover);
  inputPill.insertBefore(optionsBtn, document.getElementById('micBtn') || document.getElementById('sendBtn'));

  const [mRes, aRes] = await Promise.all([
    safeFetchJson('/api/gateway/models'),
    safeFetchJson('/api/custom-agents'),
  ]);
  const savedModel = storageGet(MODEL_KEY, '') || '';
  const models = (mRes.ok && mRes.data && (mRes.data.models || mRes.data.available_models)) || [];
  for (const m of models) {
    const id = typeof m === 'string' ? m : (m.name || m.id || '');
    if (id) modelSel.append(h('option', { value: id }, id));
  }
  if (savedModel) modelSel.value = savedModel;

  const savedAgent = storageGet(AGENT_KEY, '') || '';
  const agents = (aRes.ok && aRes.data && aRes.data.agents) || [];
  for (const ag of agents) {
    const id = ag.agent_id || ag.id || '';
    if (id) agentSel.append(h('option', { value: id }, ag.name || id));
  }
  if (savedAgent) agentSel.value = savedAgent;
}

export function showToast(message, kind = 'info', durationMs = 2800) {
  if (!toastHost) {
    toastHost = h('div', { class: 'toast-host', role: 'status', 'aria-live': 'polite' });
    document.body.append(toastHost);
  }
  const item = h('div', { class: `toast-item toast-${kind}` }, String(message || ''));
  toastHost.append(item);
  setTimeout(() => item.remove(), durationMs);
}

export function createEmptyState(title, detail, actionLabel = '', onAction = null) {
  return h(
    'div',
    { class: 'empty-state card' },
    h('h3', null, title),
    h('p', { class: 'muted' }, detail),
    actionLabel && onAction ? h('button', { type: 'button', class: 'btn btn-primary', onClick: onAction }, actionLabel) : null,
  );
}

export function attachTooltip(el, text) {
  if (!el) return;
  el.setAttribute('data-tooltip', text);
  el.setAttribute('title', text);
}

export function applyFontScale(scale) {
  const allowed = new Set(['small', 'medium', 'large']);
  document.documentElement.dataset.font = allowed.has(scale) ? scale : 'medium';
}

export function saveDraft(text) {
  if (text && text.trim()) storageSet(DRAFT_KEY, text);
  else storageRemove(DRAFT_KEY);
}

export function loadDraft() {
  return storageGet(DRAFT_KEY, '') || '';
}

export function autoTitle(firstPrompt) {
  const clean = String(firstPrompt || '').replace(/\s+/g, ' ').trim();
  return clean.split(' ').slice(0, 7).join(' ').slice(0, 64) || 'Yeni sohbet';
}

export function buildMessageLink(chatId, messageIndex) {
  return `${location.origin}${location.pathname}#/assistant?chat=${encodeURIComponent(chatId)}&msg=${messageIndex}`;
}

export function quoteMessageIntoInput(text, promptInput) {
  if (!promptInput) return;
  const snippet = String(text || '').trim().split('\n').slice(0, 3).map((l) => `> ${l}`).join('\n');
  promptInput.value = `${snippet}\n\n${promptInput.value}`;
  promptInput.focus();
}

export function editMessageInPlace(originalText, promptInput, onSubmit) {
  if (!promptInput) return;
  promptInput.value = String(originalText || '');
  promptInput.focus();
  showToast('Mesaj düzenleme için giriş kutusuna yüklendi.');
  if (typeof onSubmit === 'function') promptInput.dataset.editingMessage = '1';
}

export function continueGenerationPrompt(partialText) {
  const tail = String(partialText || '').slice(-160);
  return `Kaldığın yerden devam et, tekrar etme. Son bölüm:\n"${tail}"`;
}

export async function archiveChat(chatId, archived = true) {
  const res = await safeFetchJson(`/api/productivity/chats/${encodeURIComponent(chatId)}/archive?archived=${archived}`, { method: 'POST' });
  if (!res.ok) throw new Error(res.error || `HTTP ${res.status}`);
  showToast(archived ? 'Sohbet arşive alındı.' : 'Sohbet arşivden çıkarıldı.');
  return res.data;
}

export function renderCsvPreview(csvText) {
  const rows = String(csvText || '').trim().split(/\r?\n/).slice(0, 20).map((r) => r.split(','));
  if (!rows.length) return createEmptyState('Boş CSV', 'Önizlenecek satır bulunamadı.');
  const head = h('tr', null, ...rows[0].map((c) => h('th', null, c.trim())));
  const body = rows.slice(1).map((r) => h('tr', null, ...r.map((c) => h('td', null, c.trim()))));
  return h('table', { class: 'data-table csvPreview' }, h('thead', null, head), h('tbody', null, ...body));
}

export function renderJsonTree(obj) {
  return h('pre', { class: 'hub-result jsonTree' }, JSON.stringify(obj, null, 2));
}

export function createFolderUploadInput(onFiles) {
  const input = h('input', { type: 'file', webkitdirectory: true, multiple: true, class: 'sr-only-file', 'aria-label': 'Klasör yükle' });
  input.addEventListener('change', () => {
    if (input.files && input.files.length && typeof onFiles === 'function') onFiles([...input.files]);
  });
  return input;
}

export function openKeyboardShortcutsModal() {
  const existing = document.getElementById('keyboardShortcutsModal');
  if (existing) { existing.remove(); return; }
  const rows = [
    ['Ctrl + K', 'Komut paletini aç'],
    ['Ctrl + /', 'Klavye kısayol haritasını aç/kapat'],
    ['Enter', 'Mesajı gönder (ayardan değiştirilebilir)'],
    ['Ctrl + V', 'Panodan görsel veya dosya yapıştır'],
    ['Esc', 'Açık pencereyi kapat'],
  ];
  const close = () => overlay.remove();
  const overlay = h(
    'div',
    { id: 'keyboardShortcutsModal', class: 'auth-modal-overlay', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Klavye kısayolları' },
    h(
      'div',
      { class: 'auth-modal-box' },
      h('div', { class: 'auth-modal-head' }, h('h2', { class: 'auth-modal-title' }, 'Klavye Kısayolları'), h('button', { type: 'button', class: 'auth-modal-close', 'aria-label': 'Kapat', onClick: close }, 'x')),
      h('table', { class: 'data-table' }, ...rows.map(([k, d]) => h('tr', null, h('td', null, h('kbd', null, k)), h('td', null, d)))),
    ),
  );
  overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
  document.body.append(overlay);
}

export function initChatEnhancements() {
  mountModelAndAgentPickers();
  const promptInput = document.getElementById('promptInput');
  const fileInput = document.getElementById('fileInput');
  if (promptInput) {
    const saved = loadDraft();
    if (saved && !promptInput.value) promptInput.value = saved;
    promptInput.addEventListener('input', () => saveDraft(promptInput.value));
    // SOH-10: Paste image/file directly from clipboard into chat attachment
    promptInput.addEventListener('paste', (event) => {
      const items = event.clipboardData && event.clipboardData.items;
      if (!items || !fileInput) return;
      for (const item of items) {
        if (item.kind === 'file') {
          const blob = item.getAsFile();
          if (blob && typeof DataTransfer !== 'undefined') {
            const dt = new DataTransfer();
            dt.items.add(blob);
            fileInput.files = dt.files;
            fileInput.dispatchEvent(new Event('change'));
            showToast(`Panodan eklendi: ${blob.name || 'görsel'}`);
            break;
          }
        }
      }
    });
  }
  bindGlobalEvent(document, 'keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === '/') {
      e.preventDefault();
      openKeyboardShortcutsModal();
    }
  });
}

// Real callable enhancement hooks for modelPicker, voiceMode, customAgentPicker, and message tools
export const ENHANCEMENT_HOOKS = {
  modelPicker: getSelectedModel,
  customAgentPicker: getSelectedCustomAgent,
  voiceMode: toggleVoiceMode,
  messageLink: buildMessageLink,
  quoteMessage: quoteMessageIntoInput,
  editMessage: editMessageInPlace,
  continueGeneration: continueGenerationPrompt,
  folderUpload: createFolderUploadInput,
  keyboardShortcuts: openKeyboardShortcutsModal,
};
