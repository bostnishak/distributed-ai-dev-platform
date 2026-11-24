// F204 Chat & Accessibility Enhancements: SOH-01..10, ERI-01..05, DOS-03, DOS-06 (offline, zero CDN, zero emojis).
import { h } from './util.js';

const DRAFT_KEY = 'cm6453_chat_draft';
let toastHost = null;

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
  try {
    if (text && text.trim()) localStorage.setItem(DRAFT_KEY, text);
    else localStorage.removeItem(DRAFT_KEY);
  } catch { /* storage unavailable */ }
}

export function loadDraft() {
  try { return localStorage.getItem(DRAFT_KEY) || ''; } catch { return ''; }
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
  const resp = await fetch(`/api/productivity/chats/${encodeURIComponent(chatId)}/archive?archived=${archived}`, { method: 'POST' });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  showToast(archived ? 'Sohbet arşive alındı.' : 'Sohbet arşivden çıkarıldı.');
  return resp.json();
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
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === '/') {
      e.preventDefault();
      openKeyboardShortcutsModal();
    }
  });
}

// Named exports preserved for modelPicker, voiceMode, and messageLink hooks
export const ENHANCEMENT_HOOKS = {
  modelPicker: true,
  voiceMode: true,
  messageLink: buildMessageLink,
  quoteMessage: quoteMessageIntoInput,
  editMessage: editMessageInPlace,
  continueGeneration: continueGenerationPrompt,
  folderUpload: createFolderUploadInput,
  keyboardShortcuts: openKeyboardShortcutsModal,
};
