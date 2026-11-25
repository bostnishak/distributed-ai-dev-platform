// Sidebar chat organisation: pin/rename metadata, folders, collapsible sections and the right-click menus.
import { getActiveUserId } from './personal.js';
import { scheduleMetaPush } from './chat_meta_sync.js';
import { bindGlobalEvent, storageGet, storageSet } from './storage.js';

// Pin and rename are per-browser conveniences kept beside the chats (the server only stores title/messages).
function metaKey() { return `cm6453_chat_meta:${getActiveUserId()}`; }
export function loadChatMeta() {
  try { return JSON.parse(storageGet(metaKey(), '{}') || '{}'); } catch { return {}; }
}
export function saveChatMeta(meta) { storageSet(metaKey(), JSON.stringify(meta)); scheduleMetaPush(); }
export function patchMeta(id, patch) {
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

export function showMenu(evt, entries) {
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
export function saveFolders(list) { storageSet(foldersKey(), JSON.stringify(list)); scheduleMetaPush(); }
let renamingFolderId = null;
export function createFolder(chatIdToMove, callbacks) {
  const id = `f_${Date.now().toString(36)}`;
  saveFolders([...loadFolders(), { id, name: 'Yeni klasör', collapsed: false }]);
  if (chatIdToMove) patchMeta(chatIdToMove, { folder: id, pinned: false });
  renamingFolderId = id;
  callbacks.renderChatList();
}
export function moveChat(chatId, folderId, callbacks) {
  patchMeta(chatId, { folder: folderId || '', pinned: false });
  callbacks.renderChatList();
}

export function openCtxMenu(evt, id, chat, state, callbacks, startRename) {
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

export function openFolderMenu(evt, folder, callbacks, startRename) {
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
export function loadSections() {
  try { return JSON.parse(storageGet(sectionsKey(), '{}') || '{}'); } catch { return {}; }
}
export function patchSections(patch) { storageSet(sectionsKey(), JSON.stringify({ ...loadSections(), ...patch })); scheduleMetaPush(); }

export function makeDropTarget(el, host, onDrop) {
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
  const svgEl = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svgEl.setAttribute('viewBox', '0 0 16 16');
  svgEl.setAttribute('width', '12');
  svgEl.setAttribute('height', '12');
  svgEl.setAttribute('fill', 'none');
  svgEl.setAttribute('stroke', 'currentColor');
  svgEl.setAttribute('stroke-width', '1.8');
  svgEl.setAttribute('stroke-linecap', 'round');
  svgEl.setAttribute('stroke-linejoin', 'round');
  svgEl.setAttribute('aria-hidden', 'true');
  const pathEl = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  pathEl.setAttribute('d', collapsed ? 'M6 3.5l4.5 4.5L6 12.5' : 'M3.5 6l4.5 4.5L12.5 6');
  svgEl.append(pathEl);
  chev.append(svgEl);
  head.append(text, chev);
  head.addEventListener('click', onToggle);
  head.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle(); } });
  return { head, text };
}

export function buildSection(label, collapsed, onToggle, onDrop) {
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

export function buildFolderSection(folder, callbacks) {
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
