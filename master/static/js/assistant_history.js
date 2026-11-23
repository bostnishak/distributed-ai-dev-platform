// UX-02 Modular Split: Chat history localStorage + SQLite persistence & sidebar chat list renderer.
import { getActiveUserId } from './personal.js';

export function storageKeys() {
  const uid = getActiveUserId();
  return {
    storageKey: uid === 'default' ? 'coklu_llm_chats' : `coklu_llm_chats:${uid}`,
    lastChatKey: `cm6453_last_chat:${uid}`,
  };
}

export function loadChats() {
  try {
    return JSON.parse(localStorage.getItem(storageKeys().storageKey) || '{}');
  } catch {
    return {};
  }
}

export function saveChats(chats) {
  try {
    localStorage.setItem(storageKeys().storageKey, JSON.stringify(chats));
  } catch { /* storage unavailable */ }
}

export function persistChatRecord(chatId, messages, currentChatId, onListChanged) {
  if (!chatId || !Array.isArray(messages) || messages.length === 0) return;
  const chats = loadChats();
  const firstUserMsg = messages.find((m) => m.role === 'user');
  const title = firstUserMsg ? firstUserMsg.text.slice(0, 42) : 'Yeni sohbet';
  const record = { title, updatedAt: Date.now(), messages: messages.slice() };
  chats[chatId] = record;
  saveChats(chats);
  if (chatId === currentChatId) {
    try { localStorage.setItem(storageKeys().lastChatKey, chatId); } catch { /* ignore */ }
  }
  if (typeof onListChanged === 'function') onListChanged();
  const uid = getActiveUserId();
  fetch(`/api/user/${encodeURIComponent(uid)}/chats/${encodeURIComponent(chatId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(record),
  }).catch(() => { /* offline fallback already saved */ });
}

export async function syncChatsWithServer(state, callbacks) {
  const uid = getActiveUserId();
  const localChats = loadChats();
  try {
    const resp = await fetch(`/api/user/${encodeURIComponent(uid)}/chats`);
    if (!resp.ok) return;
    const data = await resp.json();
    const serverChats = (data && data.chats) || {};
    const merged = { ...serverChats };
    const toUpload = [];
    for (const [cid, lchat] of Object.entries(localChats)) {
      if (!lchat || !Array.isArray(lchat.messages) || lchat.messages.length === 0) continue;
      const schat = serverChats[cid];
      if (!schat || (lchat.updatedAt || 0) > (schat.updatedAt || 0)) {
        merged[cid] = lchat;
        toUpload.push([cid, lchat]);
      }
    }
    saveChats(merged);
    callbacks.renderChatList();
    for (const [cid, chatObj] of toUpload) {
      fetch(`/api/user/${encodeURIComponent(uid)}/chats/${encodeURIComponent(cid)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chatObj),
      }).catch(() => { /* ignore */ });
    }
    if (!state.started && state.currentMessages.length === 0) {
      const lastId = localStorage.getItem(storageKeys().lastChatKey);
      if (lastId && merged[lastId] && merged[lastId].messages && merged[lastId].messages.length > 0) {
        callbacks.openChat(lastId);
      }
    }
  } catch { /* keep localStorage chats */ }
}

export function renderSidebarChatList(els, state, callbacks) {
  const chats = loadChats();
  els.chatList.innerHTML = '';
  const q = (els.chatSearchInput ? els.chatSearchInput.value : '').trim().toLowerCase();
  const sorted = Object.entries(chats).sort((a, b) => b[1].updatedAt - a[1].updatedAt);

  for (const [id, chat] of sorted) {
    if (q) {
      const inTitle = (chat.title || '').toLowerCase().includes(q);
      const inMsgs = (chat.messages || []).some((m) => (m.text || '').toLowerCase().includes(q));
      if (!inTitle && !inMsgs) continue;
    }
    const item = document.createElement('div');
    item.className = 'chat-item' + (id === state.currentChatId ? ' active' : '');

    if (state.pendingDeleteId === id) {
      item.classList.add('confirm-mode');
      const label = document.createElement('span');
      label.textContent = 'Silinsin mi?';
      label.style.fontSize = '12px';
      const yes = document.createElement('span');
      yes.className = 'confirm-yes';
      yes.textContent = 'Evet';
      yes.addEventListener('click', (e) => { e.stopPropagation(); callbacks.deleteChat(id); });
      const no = document.createElement('span');
      no.className = 'confirm-no';
      no.textContent = 'Vazgeç';
      no.addEventListener('click', (e) => { e.stopPropagation(); state.pendingDeleteId = null; callbacks.renderChatList(); });
      item.append(label, yes, no);
    } else {
      if (state.activeStreams.has(id)) {
        const busy = document.createElement('span');
        busy.className = 'sp-chat-busy';
        busy.title = 'Arka planda yanıt üretiliyor';
        item.appendChild(busy);
      } else if (state.unreadCompletedChats.has(id)) {
        const dot = document.createElement('span');
        dot.className = 'sp-chat-unread';
        dot.title = 'Yanıt hazır';
        item.appendChild(dot);
      }
      const titleSpan = document.createElement('span');
      titleSpan.className = 'sp-chat-title';
      titleSpan.textContent = chat.title || 'Sohbet';
      const del = document.createElement('span');
      del.className = 'del';
      del.textContent = '✕';
      del.title = 'Sohbeti sil';
      del.addEventListener('click', (e) => {
        e.stopPropagation();
        state.pendingDeleteId = id;
        callbacks.renderChatList();
      });
      item.append(titleSpan, del);
      item.addEventListener('click', () => callbacks.openChat(id));
    }
    els.chatList.appendChild(item);
  }
}
