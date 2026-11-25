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
  if (!meta[id].pinned && !meta[id].title && !meta[id].folder) delete meta[id];
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

function showMenu(evt, entries) {
  evt.preventDefault();
  closeCtxMenu();
  bindCtxClose();
  ctxMenu = document.createElement('div');
  ctxMenu.className = 'chat-ctx-menu';
  ctxMenu.setAttribute('role', 'menu');
  for (const e of entries) {
    if (e.sep) {
      const l = document.createElement('div');
      l.className = 'ctx-label';
      l.textContent = e.sep;
      ctxMenu.append(l);
      continue;
    }
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'ctx-item' + (e.danger ? ' danger' : '');
    b.textContent = e.label;
    b.addEventListener('click', (ev) => { ev.stopPropagation(); closeCtxMenu(); e.fn(); });
    ctxMenu.append(b);
  }
  document.body.append(ctxMenu);
  const w = ctxMenu.offsetWidth; const h = ctxMenu.offsetHeight;
  ctxMenu.style.left = `${Math.max(8, Math.min(evt.clientX, window.innerWidth - w - 8))}px`;
  ctxMenu.style.top = `${Math.max(8, Math.min(evt.clientY, window.innerHeight - h - 8))}px`;
  ctxMenu.querySelector('button')?.focus();
}

// Folders: per-browser grouping of chats, stored next to pin/rename metadata.
function foldersKey() { return `cm6453_chat_folders:${getActiveUserId()}`; }
export function loadFolders() {
  try { const v = JSON.parse(storageGet(foldersKey(), '[]') || '[]'); return Array.isArray(v) ? v : []; } catch { return []; }
}
function saveFolders(list) { storageSet(foldersKey(), JSON.stringify(list)); }
let renamingFolderId = null;
function createFolder(chatIdToMove, callbacks) {
  const id = `f_${Date.now().toString(36)}`;
  saveFolders([...loadFolders(), { id, name: 'Yeni klasör', collapsed: false }]);
  if (chatIdToMove) patchMeta(chatIdToMove, { folder: id });
  renamingFolderId = id;
  callbacks.renderChatList();
}
function moveChat(chatId, folderId, callbacks) {
  patchMeta(chatId, { folder: folderId || '' });
  callbacks.renderChatList();
}

function openCtxMenu(evt, id, chat, state, callbacks, startRename) {
  const meta = loadChatMeta()[id] || {};
  const folders = loadFolders();
  const entries = [
    { label: meta.pinned ? 'Sabitlemeyi kaldır' : 'Sabitle', fn: () => { patchMeta(id, { pinned: !meta.pinned }); callbacks.renderChatList(); } },
    { label: 'Yeniden adlandır', fn: startRename },
    { sep: 'Klasöre taşı' },
    ...folders.filter((f) => f.id !== meta.folder).map((f) => ({ label: `📁 ${f.name}`, fn: () => moveChat(id, f.id, callbacks) })),
    { label: '＋ Yeni klasör', fn: () => createFolder(id, callbacks) },
  ];
  if (meta.folder) entries.push({ label: 'Klasörden çıkar', fn: () => moveChat(id, '', callbacks) });
  entries.push({ sep: ' ' }, { label: 'Sil', danger: true, fn: () => { state.pendingDeleteId = id; callbacks.renderChatList(); } });
  showMenu(evt, entries);
}

function openFolderMenu(evt, folder, callbacks, startRename) {
  showMenu(evt, [
    { label: 'Yeniden adlandır', fn: startRename },
    { label: 'Klasörü sil (sohbetler kalır)', danger: true, fn: () => {
      saveFolders(loadFolders().filter((f) => f.id !== folder.id));
      const meta = loadChatMeta();
      for (const k of Object.keys(meta)) {
        if (meta[k].folder === folder.id) {
          meta[k].folder = '';
          if (!meta[k].pinned && !meta[k].title) delete meta[k];
        }
      }
      saveChatMeta(meta);
      callbacks.renderChatList();
    } },
  ]);
}

function buildFolderSection(folder, count, callbacks) {
  const section = document.createElement('div');
  section.className = 'chat-folder' + (folder.collapsed ? ' collapsed' : '');
  const head = document.createElement('div');
  head.className = 'chat-folder-head';
  const chev = document.createElement('span');
  chev.className = 'chat-folder-chev';
  chev.textContent = folder.collapsed ? '▸' : '▾';
  const name = document.createElement('span');
  name.className = 'chat-folder-name';
  name.textContent = `📁 ${folder.name}`;
  const cnt = document.createElement('span');
  cnt.className = 'chat-folder-count';
  cnt.textContent = String(count);
  head.append(chev, name, cnt);
  const body = document.createElement('div');
  body.className = 'chat-folder-body';
  body.hidden = Boolean(folder.collapsed);

  const startRename = () => {
    const input = document.createElement('input');
    input.className = 'chat-rename-input';
    input.value = folder.name;
    input.maxLength = 40;
    let done = false;
    const finish = (save) => {
      if (done) return;
      done = true;
      renamingFolderId = null;
      const next = input.value.trim();
      if (save && next) saveFolders(loadFolders().map((f) => (f.id === folder.id ? { ...f, name: next } : f)));
      callbacks.renderChatList();
    };
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') finish(true); else if (e.key === 'Escape') finish(false); e.stopPropagation(); });
    input.addEventListener('blur', () => finish(true));
    input.addEventListener('click', (e) => e.stopPropagation());
    name.replaceWith(input);
    input.focus();
    input.select();
  };
  head.addEventListener('click', () => {
    saveFolders(loadFolders().map((f) => (f.id === folder.id ? { ...f, collapsed: !f.collapsed } : f)));
    callbacks.renderChatList();
  });
  head.addEventListener('contextmenu', (e) => openFolderMenu(e, folder, callbacks, startRename));
  for (const el of [head, body]) {
    el.addEventListener('dragover', (e) => {
      if (e.dataTransfer && e.dataTransfer.types.includes('text/x-chat-id')) { e.preventDefault(); e.stopPropagation(); section.classList.add('drop-target'); }
    });
    el.addEventListener('dragleave', () => section.classList.remove('drop-target'));
    el.addEventListener('drop', (e) => {
      const cid = e.dataTransfer && e.dataTransfer.getData('text/x-chat-id');
      section.classList.remove('drop-target');
      if (!cid) return;
      e.preventDefault();
      e.stopPropagation();
      moveChat(cid, folder.id, callbacks);
    });
  }
  section.append(head, body);
  if (renamingFolderId === folder.id) queueMicrotask(startRename);
  return { section, body };
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
  const folders = q ? [] : loadFolders();
  const folderIds = new Set(folders.map((f) => f.id));
  const counts = {};
  for (const cid of Object.keys(chats)) {
    const fid = meta[cid] && meta[cid].folder;
    if (fid && folderIds.has(fid)) counts[fid] = (counts[fid] || 0) + 1;
  }
  const bodies = {};
  for (const f of folders) {
    const built = buildFolderSection(f, counts[f.id] || 0, callbacks);
    els.chatList.appendChild(built.section);
    bodies[f.id] = built.body;
  }
  if (!els.chatList.dataset.dropBound) {
    els.chatList.dataset.dropBound = '1';
    els.chatList.addEventListener('dragover', (e) => { if (e.dataTransfer && e.dataTransfer.types.includes('text/x-chat-id')) e.preventDefault(); });
    els.chatList.addEventListener('drop', (e) => {
      const cid = e.dataTransfer && e.dataTransfer.getData('text/x-chat-id');
      if (!cid) return;
      e.preventDefault();
      moveChat(cid, '', callbacks);
    });
  }
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
      item.draggable = true;
      item.addEventListener('dragstart', (e) => { e.dataTransfer.setData('text/x-chat-id', id); e.dataTransfer.effectAllowed = 'move'; item.classList.add('dragging'); });
      item.addEventListener('dragend', () => item.classList.remove('dragging'));
      item.addEventListener('click', () => callbacks.openChat(id));
    }
    const folderBody = meta[id] && meta[id].folder && bodies[meta[id].folder];
    (folderBody || els.chatList).appendChild(item);
  }
}
