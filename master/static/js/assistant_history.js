// UX-02 Modular Split: Chat history localStorage + SQLite persistence & sidebar chat list renderer.
import { pullMeta } from './chat_meta_sync.js';
import { getActiveUserId } from './personal.js';
import { buildFolderSection, buildSection, createFolder, loadChatMeta, loadFolders, loadSections, openCtxMenu, patchMeta, patchSections, showMenu } from './chat_sections.js';
import { safeFetchJson, storageGet, storageSet } from './storage.js';

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
  await pullMeta();
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

function bindListDrop(list, callbacks) {
  if (list.dataset.dropBound) return;
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

function buildGroupButton(sortMode, callbacks) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'chat-section-action';
  btn.title = 'Grupla ve sırala';
  btn.setAttribute('aria-label', 'Grupla ve sırala');
  btn.textContent = '☰';
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    const r = btn.getBoundingClientRect();
    const pick = (patch) => () => { patchSections(patch); callbacks.renderChatList(); };
    showMenu({ preventDefault() {}, clientX: r.left, clientY: r.bottom + 4 }, [
      { sep: 'Sırala' },
      { label: `${sortMode === 'recent' ? '✓ ' : ''}En son kullanılan`, fn: pick({ sort: 'recent' }) },
      { label: `${sortMode === 'title' ? '✓ ' : ''}Başlığa göre (A–Z)`, fn: pick({ sort: 'title' }) },
      { sep: 'Grupla' },
      { label: '＋ Yeni klasör', fn: () => createFolder('', callbacks) },
    ]);
  });
  return btn;
}

function renderSearchResults(list, entries, item) {
  for (const e of entries) list.appendChild(item(e));
  if (entries.length) return;
  const none = document.createElement('div');
  none.className = 'chat-section-empty';
  none.textContent = 'Eşleşen sohbet yok';
  list.appendChild(none);
}

function buildPinnedSection(pinned, sec, item, callbacks) {
  const pinSec = buildSection('Sabitlenmiş', Boolean(sec.pinnedCollapsed), () => { patchSections({ pinnedCollapsed: !sec.pinnedCollapsed }); callbacks.renderChatList(); },
    (cid) => { patchMeta(cid, { pinned: true, folder: '' }); callbacks.renderChatList(); });
  for (const e of pinned) pinSec.body.appendChild(item(e));
  if (!pinned.length) {
    const hint = document.createElement('div');
    hint.className = 'chat-section-empty';
    hint.textContent = 'Sohbeti buraya sürükleyerek sabitle';
    pinSec.body.appendChild(hint);
  }
  return pinSec.section;
}

function buildRecentSection(rest, sec, sortMode, item, callbacks) {
  const recent = buildSection('Son kullanılanlar', Boolean(sec.recentCollapsed), () => { patchSections({ recentCollapsed: !sec.recentCollapsed }); callbacks.renderChatList(); },
    (cid) => { patchMeta(cid, { pinned: false, folder: '' }); callbacks.renderChatList(); });
  recent.head.appendChild(buildGroupButton(sortMode, callbacks));
  for (const e of (sec.showAll ? rest : rest.slice(0, RECENT_LIMIT))) recent.body.appendChild(item(e));
  if (rest.length > RECENT_LIMIT) {
    const more = document.createElement('button');
    more.type = 'button';
    more.className = 'chat-section-more';
    more.textContent = sec.showAll ? 'Daha az göster' : 'Tümünü görüntüle';
    more.addEventListener('click', () => { patchSections({ showAll: !sec.showAll }); callbacks.renderChatList(); });
    recent.body.appendChild(more);
  }
  return recent.section;
}

export function renderSidebarChatList(els, state, callbacks) {
  const chats = loadChats();
  const list = els.chatList;
  list.replaceChildren();
  const q = (els.chatSearchInput ? els.chatSearchInput.value : '').trim().toLowerCase();
  const meta = loadChatMeta();
  const sec = loadSections();
  const sortMode = sec.sort === 'title' ? 'title' : 'recent';
  const titleOf = ([id, c]) => String((meta[id] && meta[id].title) || c.title || '');
  const matches = (chat) => !q || (chat.title || '').toLowerCase().includes(q) || (chat.messages || []).some((m) => (m.text || '').toLowerCase().includes(q));
  const byOrder = (a, b) => (sortMode === 'title' ? titleOf(a).localeCompare(titleOf(b), 'tr') : (b[1].updatedAt || 0) - (a[1].updatedAt || 0));
  const entries = Object.entries(chats).filter(([, c]) => matches(c)).sort(byOrder);
  const item = ([id, chat]) => buildChatItem(id, chat, meta, state, callbacks);
  bindListDrop(list, callbacks);
  if (q) { renderSearchResults(list, entries, item); return; }

  const folders = loadFolders();
  const folderIds = new Set(folders.map((f) => f.id));
  const isPinned = ([id]) => Boolean(meta[id] && meta[id].pinned);
  const folderOf = ([id]) => (meta[id] && meta[id].folder) || '';
  list.appendChild(buildPinnedSection(entries.filter(isPinned), sec, item, callbacks));
  for (const f of folders) {
    const built = buildFolderSection(f, callbacks);
    for (const e of entries.filter((x) => !isPinned(x) && folderOf(x) === f.id)) built.body.appendChild(item(e));
    list.appendChild(built.section);
  }
  const rest = entries.filter((x) => !isPinned(x) && !folderIds.has(folderOf(x)));
  list.appendChild(buildRecentSection(rest, sec, sortMode, item, callbacks));
}
