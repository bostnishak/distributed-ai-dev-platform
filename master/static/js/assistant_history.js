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
export function createFolder(chatIdToMove, callbacks) {
  const id = `f_${Date.now().toString(36)}`;
  saveFolders([...loadFolders(), { id, name: 'Yeni klasör', collapsed: false }]);
  if (chatIdToMove) patchMeta(chatIdToMove, { folder: id, pinned: false });
  renamingFolderId = id;
  callbacks.renderChatList();
}
function moveChat(chatId, folderId, callbacks) {
  patchMeta(chatId, { folder: folderId || '', pinned: false });
  callbacks.renderChatList();
}

function openCtxMenu(evt, id, chat, state, callbacks, startRename) {
  const meta = loadChatMeta()[id] || {};
  const folders = loadFolders();
  const entries = [
    { label: meta.pinned ? 'Sabitlemeyi kaldır' : 'Sabitle', fn: () => { patchMeta(id, meta.pinned ? { pinned: false } : { pinned: true, folder: '' }); callbacks.renderChatList(); } },
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

// Sidebar sections (Sabitlenmiş / folders / Son kullanılanlar): collapsible headers that also accept dragged chats.
function sectionsKey() { return `cm6453_chat_sections:${getActiveUserId()}`; }
function loadSections() {
  try { return JSON.parse(storageGet(sectionsKey(), '{}') || '{}'); } catch { return {}; }
}
function patchSections(patch) { storageSet(sectionsKey(), JSON.stringify({ ...loadSections(), ...patch })); }

function makeDropTarget(el, host, onDrop) {
  el.addEventListener('dragover', (e) => {
    if (e.dataTransfer && e.dataTransfer.types.includes('text/x-chat-id')) { e.preventDefault(); e.stopPropagation(); host.classList.add('drop-target'); }
  });
  el.addEventListener('dragleave', (e) => { if (!host.contains(e.relatedTarget)) host.classList.remove('drop-target'); });
  el.addEventListener('drop', (e) => {
    host.classList.remove('drop-target');
    const cid = e.dataTransfer && e.dataTransfer.getData('text/x-chat-id');
    if (!cid) return;
    e.preventDefault();
    e.stopPropagation();
    onDrop(cid);
  });
}

function buildSectionHead(label, collapsed, onToggle) {
  const head = document.createElement('div');
  head.className = 'chat-section-head';
  head.tabIndex = 0;
  head.setAttribute('role', 'button');
  head.setAttribute('aria-expanded', String(!collapsed));
  const text = document.createElement('span');
  text.className = 'chat-section-label';
  text.textContent = label;
  const chev = document.createElement('span');
  chev.className = 'chat-section-chev';
  chev.textContent = collapsed ? '›' : '⌄';
  head.append(text, chev);
  head.addEventListener('click', onToggle);
  head.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle(); } });
  return { head, text };
}

function buildSection(label, collapsed, onToggle, onDrop) {
  const section = document.createElement('div');
  section.className = 'chat-section' + (collapsed ? ' collapsed' : '');
  const { head, text } = buildSectionHead(label, collapsed, onToggle);
  const body = document.createElement('div');
  body.className = 'chat-section-body';
  body.hidden = collapsed;
  section.append(head, body);
  if (onDrop) { makeDropTarget(head, section, onDrop); makeDropTarget(body, section, onDrop); }
  return { section, head, text, body };
}

function buildFolderSection(folder, callbacks) {
  const built = buildSection(
    folder.name,
    Boolean(folder.collapsed),
    () => { saveFolders(loadFolders().map((f) => (f.id === folder.id ? { ...f, collapsed: !f.collapsed } : f))); callbacks.renderChatList(); },
    (cid) => moveChat(cid, folder.id, callbacks),
  );
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
    built.text.replaceWith(input);
    input.focus();
    input.select();
  };
  built.head.addEventListener('contextmenu', (e) => openFolderMenu(e, folder, callbacks, startRename));
  if (renamingFolderId === folder.id) queueMicrotask(startRename);
  return built;
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

function buildChatItem(id, chat, meta, state, callbacks) {
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
    return item;
  }
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
  titleSpan.textContent = (meta[id] && meta[id].title) || chat.title || 'Sohbet';
  const del = document.createElement('span');
  del.className = 'del';
  del.textContent = '✕';
  del.title = 'Sohbeti sil';
  del.addEventListener('click', (e) => { e.stopPropagation(); state.pendingDeleteId = id; callbacks.renderChatList(); });
  item.append(titleSpan, del);
  item.addEventListener('contextmenu', (e) => openCtxMenu(e, id, chat, state, callbacks, () => renameInline(item, titleSpan, id, chat, callbacks)));
  item.draggable = true;
  item.addEventListener('dragstart', (e) => { e.dataTransfer.setData('text/x-chat-id', id); e.dataTransfer.effectAllowed = 'move'; item.classList.add('dragging'); });
  item.addEventListener('dragend', () => item.classList.remove('dragging'));
  item.addEventListener('click', () => callbacks.openChat(id));
  return item;
}

const RECENT_LIMIT = 10;

export function renderSidebarChatList(els, state, callbacks) {
  const chats = loadChats();
  const list = els.chatList;
  list.replaceChildren();
  const q = (els.chatSearchInput ? els.chatSearchInput.value : '').trim().toLowerCase();
  const meta = loadChatMeta();
  const sec = loadSections();
  const sortMode = sec.sort === 'title' ? 'title' : 'recent';

  const matches = (chat) => {
    if (!q) return true;
    return (chat.title || '').toLowerCase().includes(q) || (chat.messages || []).some((m) => (m.text || '').toLowerCase().includes(q));
  };
  const byOrder = (a, b) => (sortMode === 'title'
    ? String((meta[a[0]] && meta[a[0]].title) || a[1].title || '').localeCompare(String((meta[b[0]] && meta[b[0]].title) || b[1].title || ''), 'tr')
    : (b[1].updatedAt || 0) - (a[1].updatedAt || 0));
  const entries = Object.entries(chats).filter(([, c]) => matches(c)).sort(byOrder);
  const item = ([id, chat]) => buildChatItem(id, chat, meta, state, callbacks);

  if (!list.dataset.dropBound) {
    list.dataset.dropBound = '1';
    list.addEventListener('dragover', (e) => { if (e.dataTransfer && e.dataTransfer.types.includes('text/x-chat-id')) e.preventDefault(); });
    list.addEventListener('drop', (e) => {
      const cid = e.dataTransfer && e.dataTransfer.getData('text/x-chat-id');
      if (!cid) return;
      e.preventDefault();
      patchMeta(cid, { pinned: false, folder: '' });
      callbacks.renderChatList();
    });
  }

  if (q) {
    for (const e of entries) list.appendChild(item(e));
    if (!entries.length) {
      const none = document.createElement('div');
      none.className = 'chat-section-empty';
      none.textContent = 'Eşleşen sohbet yok';
      list.appendChild(none);
    }
    return;
  }

  const folders = loadFolders();
  const folderIds = new Set(folders.map((f) => f.id));
  const pinned = entries.filter(([id]) => meta[id] && meta[id].pinned);
  const inFolder = (fid) => entries.filter(([id]) => !(meta[id] && meta[id].pinned) && meta[id] && meta[id].folder === fid);
  const rest = entries.filter(([id]) => !(meta[id] && meta[id].pinned) && !(meta[id] && meta[id].folder && folderIds.has(meta[id].folder)));

  const pinSec = buildSection('Sabitlenmiş', Boolean(sec.pinnedCollapsed), () => { patchSections({ pinnedCollapsed: !sec.pinnedCollapsed }); callbacks.renderChatList(); },
    (cid) => { patchMeta(cid, { pinned: true, folder: '' }); callbacks.renderChatList(); });
  for (const e of pinned) pinSec.body.appendChild(item(e));
  if (!pinned.length) {
    const hint = document.createElement('div');
    hint.className = 'chat-section-empty';
    hint.textContent = 'Sohbeti buraya sürükleyerek sabitle';
    pinSec.body.appendChild(hint);
  }
  list.appendChild(pinSec.section);

  for (const f of folders) {
    const built = buildFolderSection(f, callbacks);
    for (const e of inFolder(f.id)) built.body.appendChild(item(e));
    list.appendChild(built.section);
  }

  const recent = buildSection('Son kullanılanlar', Boolean(sec.recentCollapsed), () => { patchSections({ recentCollapsed: !sec.recentCollapsed }); callbacks.renderChatList(); },
    (cid) => { patchMeta(cid, { pinned: false, folder: '' }); callbacks.renderChatList(); });
  const groupBtn = document.createElement('button');
  groupBtn.type = 'button';
  groupBtn.className = 'chat-section-action';
  groupBtn.title = 'Grupla ve sırala';
  groupBtn.setAttribute('aria-label', 'Grupla ve sırala');
  groupBtn.textContent = '☰';
  groupBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const r = groupBtn.getBoundingClientRect();
    showMenu({ preventDefault() {}, clientX: r.left, clientY: r.bottom + 4 }, [
      { sep: 'Sırala' },
      { label: `${sortMode === 'recent' ? '✓ ' : ''}En son kullanılan`, fn: () => { patchSections({ sort: 'recent' }); callbacks.renderChatList(); } },
      { label: `${sortMode === 'title' ? '✓ ' : ''}Başlığa göre (A–Z)`, fn: () => { patchSections({ sort: 'title' }); callbacks.renderChatList(); } },
      { sep: 'Grupla' },
      { label: '＋ Yeni klasör', fn: () => createFolder('', callbacks) },
    ]);
  });
  recent.head.appendChild(groupBtn);
  const shown = sec.showAll ? rest : rest.slice(0, RECENT_LIMIT);
  for (const e of shown) recent.body.appendChild(item(e));
  if (rest.length > RECENT_LIMIT) {
    const more = document.createElement('button');
    more.type = 'button';
    more.className = 'chat-section-more';
    more.textContent = sec.showAll ? 'Daha az göster' : 'Tümünü görüntüle';
    more.addEventListener('click', () => { patchSections({ showAll: !sec.showAll }); callbacks.renderChatList(); });
    recent.body.appendChild(more);
  }
  list.appendChild(recent.section);
}
