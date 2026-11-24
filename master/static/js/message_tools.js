// Per-answer extras: regenerate, export the chat, share it read-only (UX-08, UX-26) and desktop
// notifications when a long answer finishes in a background tab (UX-25).
import { downloadText } from './panels.js';
import { getActiveUserId } from './personal.js';
import { bindGlobalEvent } from './storage.js';
import { api, h } from './util.js';

export function chatToMarkdown(messages, title = 'Sohbet') {
  const lines = [`# ${title}`, ''];
  for (const m of messages) {
    lines.push(m.role === 'user' ? '## Kullanıcı' : `## Asistan${m.modelBadge ? ` (${m.modelBadge})` : ''}`, '', m.text || '', '');
  }
  return lines.join('\n');
}

export function buildExtraActions({ messages, regenerate }) {
  const bar = h('div', { class: 'msg-extra-actions' });
  const note = h('span', { class: 'hub-status' });

  const again = h('span', { class: 'download-link', role: 'button', tabindex: 0, title: 'Aynı istekle yanıtı yeniden üret' }, 'Yeniden üret');
  again.addEventListener('click', regenerate);

  const exportBtn = h('span', { class: 'download-link', role: 'button', tabindex: 0, title: 'Sohbeti Markdown olarak indir' }, 'Sohbeti dışa aktar');
  exportBtn.addEventListener('click', () => downloadText('sohbet.md', chatToMarkdown(messages())));

  const shareBtn = h('span', { class: 'download-link', role: 'button', tabindex: 0, title: 'Salt okunur, süreli bağlantı oluştur' }, 'Paylaş');
  shareBtn.addEventListener('click', async () => {
    const user = getActiveUserId();
    try {
      const res = await api('/api/ux/shares', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ owner_id: user, title: 'Paylaşılan sohbet', content: chatToMarkdown(messages()), allowed_users: [user], ttl_seconds: 86400 }),
      });
      const link = `${location.origin}/#/share/${res.share_id}`;
      try { await navigator.clipboard.writeText(link); note.textContent = 'Bağlantı kopyalandı (24 saat geçerli)'; } catch { note.textContent = link; }
      note.className = 'hub-status ok';
    } catch (err) {
      note.textContent = `Paylaşılamadı: ${err.message}`;
      note.className = 'hub-status err';
    }
  });
  bar.append(again, exportBtn, shareBtn, note);
  return bar;
}

export function requestNotifyPermission() {
  try {
    if ('Notification' in window && Notification.permission === 'default') Notification.requestPermission();
  } catch { /* permission prompt unavailable */ }
}

// Falls back to the tab title when permission is denied or notifications are unsupported.
export function notifyAnswerReady(title) {
  if (!document.hidden) return;
  try {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('Yanıt hazır', { body: title.slice(0, 120) });
      return;
    }
  } catch { /* fall through to the title indicator */ }
  const original = document.title;
  document.title = '(1) Yanıt hazır';
  let off = () => {};
  const restore = () => { document.title = original; off(); };
  off = bindGlobalEvent(document, 'visibilitychange', restore);
}

// "Düzenle & Dallandır": cut the chat at this message and put its text back in the input to be edited (UX-08).
export function buildBranchLink({ els, state, row, msgIdx, text, sync }) {
  const link = h('span', { class: 'download-link sp-branch-link', style: { marginTop: '3px' }, title: 'Bu mesajı düzenleyerek sohbeti buradan yeni bir dala ayır' }, 'Düzenle & Dallandır');
  link.addEventListener('click', () => {
    els.promptInput.value = text;
    els.promptInput.style.height = `${Math.min(els.promptInput.scrollHeight, 160)}px`;
    state.currentMessages = state.currentMessages.slice(0, msgIdx);
    while (row.nextSibling) row.nextSibling.remove();
    row.remove();
    sync();
    els.promptInput.focus();
  });
  return link;
}

// Drops the last question and its answer from the screen and the state, then asks the same question again.
// The screen is cut directly: an emptied chat is never written to storage, so re-rendering from storage would
// bring the old pair back.
export function regenerateLast({ els, state, send }) {
  const idx = state.currentMessages.map((m) => m.role).lastIndexOf('user');
  if (idx < 0 || state.activeStreams.has(state.currentChatId)) return;
  const prompt = state.currentMessages[idx].text;
  state.currentMessages = state.currentMessages.slice(0, idx);
  const rows = [...els.messages.querySelectorAll('.msg-row.user')];
  const lastUser = rows[rows.length - 1];
  while (lastUser && lastUser.nextSibling) lastUser.nextSibling.remove();
  if (lastUser) lastUser.remove();
  send(prompt);
}
