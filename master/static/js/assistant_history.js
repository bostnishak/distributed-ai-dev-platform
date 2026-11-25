// UX-02 Modular Split: Chat history localStorage + SQLite persistence & sidebar chat list renderer.
import { getActiveUserId } from './personal.js';
import { bindGlobalEvent, safeFetchJson, storageGet, storageSet } from './storage.js';

// Pin and rename are per-browser conveniences kept beside the chats (the server only stores title/messages).
function metaKey() { return `cm6453_chat_meta:${getActiveUserId()}`; }
export function loadChatMeta() {
  try { return JSON.parse(storageGet(metaKey(), '{}') || '{}'); } catch { return {}; }
}
function saveChatMeta(meta) { storageSet(metaKey(), JSON.stringify(meta)); }
function patchMeta(id, patch) {
  const meta = loadChatMeta();
  meta[id] = { ...(meta[id] || {}), ...patch };
  if (!meta[id].pinned && !meta[id].title) delete meta[id];
  saveChatMeta(meta);
}

let ctxMenu = null;
function closeCtxMenu() { if (ctxMenu) { ctxMenu.remove(); ctxMenu = null; } }
let ctxBound = false;
function bindCtxClose() {
  if (ctxBound) return;
  ctxBound = true;
  bindGlobalEvent(document, 'click', closeCtxMenu);
  bindGlobalEvent(document, 'keydown', (e) => { if (e.key === 'Escape') closeCtxMenu(); });
  bindGlobalEvent(window, 'blur', closeCtxMenu);
}

function openCtxMenu(evt, id, chat, state, callbacks, startRename) {
  evt.preventDefault();
  closeCtxMenu();
  bindCtxClose();
  const pinned = Boolean(loadChatMeta()[id]?.pinned);
  const entry = (label, fn, danger) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'ctx-item' + (danger ? ' danger' : '');
    b.textContent = label;
    b.addEventListener('click', (e) => { e.stopPropagation(); closeCtxMenu(); fn(); });
    return b;
  };
  ctxMenu = document.createElement('div');
  ctxMenu.className = 'chat-ctx-menu';
  ctxMenu.setAttribute('role', 'menu');
  ctxMenu.append(
    entry(pinned ? 'Sabitlemeyi kaldır' : 'Sabitle', () => { patchMeta(id, { pinned: !pinned }); callbacks.renderChatList(); }),
    entry('Yeniden adlandır', startRename),
    entry('Sil', () => { state.pendingDeleteId = id; callbacks.renderChatList(); }, true),
  );
  document.body.append(ctxMenu);
  const w = ctxMenu.offsetWidth; const h = ctxMenu.offsetHeight;
  ctxMenu.style.left = `${Math.min(evt.clientX, window.innerWidth - w - 8)}px`;
  ctxMenu.style.top = `${Math.min(evt.clientY, window.innerHeight - h - 8)}px`;
  ctxMenu.querySelector('button')?.focus();
}

function renameInline(item, titleSpan, id, chat, callbacks) {
  const input = document.createElement('input');
  input.className = 'chat-rename-input';
  input.value = titleSpan.textContent;
  input.maxLength = 80;
  let done = false;
  const finish = (save) => {
    if (done) return;
    done = true;
    const next = input.value.trim();
    if (save && next && next !== titleSpan.textContent) {
      patchMeta(id, { title: next });
      const chats = loadChats();
      if (chats[id]) {
        chats[id].title = next;
        saveChats(chats);
        safeFetchJson(`/api/user/${encodeURIComponent(getActiveUserId())}/chats/${encodeURIComponent(id)}`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(chats[id]),
        });
      }
    }
    callbacks.renderChatList();
  };
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') finish(true); else if (e.key === 'Escape') finish(false); e.stopPropagation(); });
  input.addEventListener('blur', () => finish(true));
  input.addEventListener('click', (e) => e.stopPropagation());
  titleSpan.replaceWith(input);
  input.focus();
  input.select();
}

export function storageKeys() {
  const uid = getActiveUserId();
  return {
    storageKey: uid === 'default' ? 'coklu_llm_chats' : `coklu_llm_chats:${uid}`,
    lastChatKey: `cm6453_last_chat:${uid}`,
  };
}

export function loadChats() {
  try {
    return JSON.parse(storageGet(storageKeys().storageKey, '{}') || '{}');
  } catch {
    return {};
  }
}

export function saveChats(chats) {
  storageSet(storageKeys().storageKey, JSON.stringify(chats));
}

export function persistChatRecord(chatId, messages, currentChatId, onListChanged) {
  if (!chatId || !Array.isArray(messages) || messages.length === 0) return;
  const chats = loadChats();
  const firstUserMsg = messages.find((m) => m.role === 'user');
  const title = loadChatMeta()[chatId]?.title || (firstUserMsg ? firstUserMsg.text.slice(0, 42) : 'Yeni sohbet');
  const record = { title, updatedAt: Date.now(), messages: messages.slice() };
  chats[chatId] = record;
  saveChats(chats);
  if (chatId === currentChatId) {
    storageSet(storageKeys().lastChatKey, chatId);
  }
  if (typeof onListChanged === 'function') onListChanged();
  const uid = getActiveUserId();
  safeFetchJson(`/api/user/${encodeURIComponent(uid)}/chats/${encodeURIComponent(chatId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(record),
  });
}

export async function syncChatsWithServer(state, callbacks) {
  const uid = getActiveUserId();
  const localChats = loadChats();
  const res = await safeFetchJson(`/api/user/${encodeURIComponent(uid)}/chats`);
  if (!res.ok || !res.data) return;
  const serverChats = (res.data && res.data.chats) || {};
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
    safeFetchJson(`/api/user/${encodeURIComponent(uid)}/chats/${encodeURIComponent(cid)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(chatObj),
    });
  }
  if (!state.started && state.currentMessages.length === 0) {
    const lastId = storageGet(storageKeys().lastChatKey, null);
    if (lastId && merged[lastId] && merged[lastId].messages && merged[lastId].messages.length > 0) {
      callbacks.openChat(lastId);
    }
  }
}

export function renderSidebarChatList(els, state, callbacks) {
  const chats = loadChats();
  els.chatList.replaceChildren();
  const q = (els.chatSearchInput ? els.chatSearchInput.value : '').trim().toLowerCase();
  const meta = loadChatMeta();
  const sorted = Object.entries(chats).sort((a, b) => (Number(Boolean(meta[b[0]]?.pinned)) - Number(Boolean(meta[a[0]]?.pinned))) || (b[1].updatedAt - a[1].updatedAt));

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
      titleSpan.textContent = meta[id]?.title || chat.title || 'Sohbet';
      const del = document.createElement('span');
      del.className = 'del';
      del.textContent = '✕';
      del.title = 'Sohbeti sil';
      del.addEventListener('click', (e) => {
        e.stopPropagation();
        state.pendingDeleteId = id;
        callbacks.renderChatList();
      });
      if (meta[id]?.pinned) {
        const pin = document.createElement('span');
        pin.className = 'chat-pin';
        pin.title = 'Sabitlenmiş';
        pin.textContent = '📌';
        item.append(pin);
      }
      item.append(titleSpan, del);
      item.addEventListener('contextmenu', (e) => openCtxMenu(e, id, chat, state, callbacks, () => renameInline(item, titleSpan, id, chat, callbacks)));
      item.addEventListener('click', () => callbacks.openChat(id));
    }
    els.chatList.appendChild(item);
  }
}
