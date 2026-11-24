// Assistant tab: modularized core chat controller (UX-02 <= 400 lines).
import { createMessageActions, renderHeroCards } from './assistant_hero.js';
import {
  loadChats,
  persistChatRecord,
  renderSidebarChatList,
  saveChats,
  storageKeys,
  syncChatsWithServer,
} from './assistant_history.js';
import { buildInlineWorkspaceCard } from './assistant_ide_card.js';
import { runAssistantStream } from './assistant_stream.js';
import {
  handleRunCodeClick,
  initVoiceRecognition,
  showRunButtonsIfEnabled,
} from './assistant_voice.js';
import { renderMarkdown } from './markdown.js';
import { buildBranchLink, buildExtraActions, regenerateLast, requestNotifyPermission } from './message_tools.js';
import { getActiveUserId, getPrefs } from './personal.js';
import { setSanitizedHtml } from './sanitizer.js';
import { bindGlobalEvent, storageRemove, storageSet } from './storage.js';
import { closeSidebar } from './util.js';
import { parseSlashAndMentions } from './ux_shell.js';

let els;
let selectedFile = null;
let userScrolledUp = false;
const state = {
  started: false,
  currentChatId: null,
  currentMessages: [],
  pendingDeleteId: null,
  activeStreams: new Map(),
  unreadCompletedChats: new Set(),
};

function scrollToBottomIfPinned(force = false) {
  if (!els || !els.messages) return;
  if (force) {
    userScrolledUp = false;
    els.messages.scrollTop = els.messages.scrollHeight;
    return;
  }
  if (!userScrolledUp) els.messages.scrollTop = els.messages.scrollHeight;
}

function renderChatList() {
  renderSidebarChatList(els, state, { deleteChat, openChat, renderChatList });
}

function persistChatById(chatId, messages) {
  persistChatRecord(chatId, messages, state.currentChatId, renderChatList);
}

function persistCurrentChat() {
  persistChatById(state.currentChatId, state.currentMessages);
}

function deleteChat(id) {
  const running = state.activeStreams.get(id);
  if (running) {
    running.controller.abort();
    state.activeStreams.delete(id);
  }
  state.unreadCompletedChats.delete(id);
  const chats = loadChats();
  delete chats[id];
  saveChats(chats);
  state.pendingDeleteId = null;
  const uid = getActiveUserId();
  fetch(`/api/user/${encodeURIComponent(uid)}/chats/${encodeURIComponent(id)}`, { method: 'DELETE' }).catch(() => {});
  if (id === state.currentChatId) startNewChat();
  else renderChatList();
}

function syncSendBtnState() {
  if (!els || !els.sendBtn) return;
  if (state.activeStreams.has(state.currentChatId)) {
    els.sendBtn.textContent = '■';
    els.sendBtn.title = 'Bu sohbetin yanıtını durdur';
    els.sendBtn.classList.add('ready');
  } else {
    els.sendBtn.textContent = '↑';
    els.sendBtn.title = 'Gönder';
    els.sendBtn.classList.toggle('ready', els.promptInput.value.trim().length > 0);
  }
}

function ensureStarted() {
  if (!state.started) {
    state.started = true;
    els.centerStage.style.display = 'none';
    els.messages.classList.add('active');
  }
}

function openChat(id) {
  const chat = loadChats()[id];
  if (!chat) return;
  state.currentChatId = id;
  state.unreadCompletedChats.delete(id);
  storageSet(storageKeys().lastChatKey, id);
  state.currentMessages = (chat.messages || []).slice();
  els.messages.replaceChildren();
  ensureStarted();
  for (const m of state.currentMessages) {
    if (m.role === 'user') addUserMessage(m.text, m.fileName, false);
    else {
      const row = addAssistantMessage(m.text, m.modelBadge, m.isError, false, false);
      if (m.workspace) {
        row.querySelector('.msg-wrap').appendChild(buildInlineWorkspaceCard(m.workspace.workspace, m.workspace.tree));
      }
    }
  }
  const live = state.activeStreams.get(id);
  if (live && live.row) {
    els.messages.appendChild(live.row);
    els.messages.scrollTop = els.messages.scrollHeight;
  }
  syncSendBtnState();
  renderChatList();
  closeSidebar();
}

function startNewChat(clearLastActive = false) {
  if (clearLastActive) storageRemove(storageKeys().lastChatKey);
  state.currentChatId = 'chat_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
  state.currentMessages = [];
  els.messages.replaceChildren();
  els.messages.classList.remove('active');
  els.centerStage.style.display = 'flex';
  state.started = false;
  syncSendBtnState();
  renderChatList();
  closeSidebar();
}

function addUserMessage(text, fileName, record = true) {
  const msgIdx = state.currentMessages.length;
  const row = document.createElement('div');
  row.className = 'msg-row user';
  const wrap = document.createElement('div');
  wrap.className = 'msg-user-wrap';
  const bubble = document.createElement('div');
  bubble.className = 'msg user';
  bubble.style.maxWidth = '100%';
  bubble.textContent = fileName ? `[Dosya: ${fileName}]\n${text}` : text;

  const branchBtn = buildBranchLink({ els, state, row, msgIdx, text, sync: syncSendBtnState });

  wrap.append(bubble, branchBtn);
  row.appendChild(wrap);
  els.messages.appendChild(row);
  els.messages.scrollTop = els.messages.scrollHeight;
  if (record) state.currentMessages.push({ role: 'user', text, fileName });
}

function addAssistantMessage(text, modelBadge, isError, isThinking, record = true) {
  const row = document.createElement('div');
  row.className = 'msg-row assistant';
  const wrap = document.createElement('div');
  wrap.className = 'msg-wrap';

  if (modelBadge) {
    const badgeRow = document.createElement('div');
    badgeRow.className = 'badge-row';
    const badge = document.createElement('span');
    badge.className = 'badge';
    badge.textContent = modelBadge;
    badgeRow.appendChild(badge);
    wrap.appendChild(badgeRow);
  }

  const bubble = document.createElement('div');
  bubble.className = 'msg assistant' + (isError ? ' error' : '') + (isThinking ? ' thinking' : '');
  if (isError || isThinking) bubble.textContent = text;
  else setSanitizedHtml(bubble, renderMarkdown(text));
  wrap.appendChild(bubble);

  if (!isError && !isThinking) wrap.appendChild(messageBar(text));
  row.appendChild(wrap);
  els.messages.appendChild(row);
  els.messages.scrollTop = els.messages.scrollHeight;
  if (record && !isThinking) state.currentMessages.push({ role: 'assistant', text, modelBadge, isError });
  return row;
}

function messageBar(text) {
  const bar = createMessageActions(text, sendMessage);
  bar.append(buildExtraActions({ messages: () => state.currentMessages, regenerate: () => regenerateLast({ els, state, send: sendMessage }) }));
  return bar;
}

function appendAssistantMessageToChat(chatId, msgObj) {
  const chats = loadChats();
  const existing = chats[chatId] && Array.isArray(chats[chatId].messages)
    ? chats[chatId].messages.slice()
    : (chatId === state.currentChatId ? state.currentMessages.slice() : []);
  existing.push(msgObj);
  if (chatId === state.currentChatId) state.currentMessages = existing.slice();
  else state.unreadCompletedChats.add(chatId);
  persistChatById(chatId, existing);
}

async function sendMessage(overridePrompt = null) {
  const isOverride = typeof overridePrompt === 'string' && overridePrompt.trim().length > 0;
  if (!isOverride && state.activeStreams.has(state.currentChatId)) {
    const running = state.activeStreams.get(state.currentChatId);
    if (running && running.controller) running.controller.abort();
    return;
  }
  const rawPrompt = isOverride ? overridePrompt.trim() : els.promptInput.value.trim();
  if (!rawPrompt) return;
  const parsedSlash = parseSlashAndMentions(rawPrompt);
  const prompt = parsedSlash.slash && parsedSlash.cleanPrompt ? parsedSlash.cleanPrompt : rawPrompt;

  requestNotifyPermission();
  ensureStarted();
  const targetChatId = state.currentChatId;
  const fileToSend = isOverride ? null : selectedFile;
  addUserMessage(rawPrompt, fileToSend ? fileToSend.name : null);
  persistChatById(targetChatId, state.currentMessages);
  const historySnapshot = state.currentMessages.slice(0, -1).slice(-40);

  if (!isOverride) {
    els.promptInput.value = '';
    els.promptInput.style.height = 'auto';
    selectedFile = null;
    els.fileInput.value = '';
    els.fileChip.classList.remove('active');
  }

  await runAssistantStream({
    prompt,
    historySnapshot,
    fileToSend,
    targetChatId,
    els,
    state,
    scrollToBottomIfPinned,
    syncSendBtnState,
    renderChatList,
    addAssistantMessage,
    appendAssistantMessageToChat,
    messageBar,
  });
}

async function handleMessagesClick(e) {
  const copyBtn = e.target.closest('.sp-code-copy');
  if (copyBtn) {
    const codeEl = copyBtn.closest('.code-block')?.querySelector('pre code');
    if (!codeEl) return;
    try {
      await navigator.clipboard.writeText(codeEl.textContent || '');
      copyBtn.textContent = 'Kopyalandı';
      copyBtn.classList.add('copied');
      const COPY_MS = 1600;
      setTimeout(() => { copyBtn.textContent = 'Kopyala'; copyBtn.classList.remove('copied'); }, COPY_MS);
    } catch { copyBtn.textContent = 'Kopyalanamadı'; }
    return;
  }
  handleRunCodeClick(e);
}

export function initAssistant() {
  const byId = (id) => document.getElementById(id);
  els = {
    messages: byId('messages'), centerStage: byId('centerStage'), promptInput: byId('promptInput'),
    sendBtn: byId('sendBtn'), micBtn: byId('micBtn'), attachBtn: byId('attachBtn'),
    fileInput: byId('fileInput'), fileChip: byId('fileChip'), fileChipName: byId('fileChipName'),
    removeFile: byId('removeFile'), chatList: byId('chatList'), chatSearchInput: byId('chatSearchInput'),
    heroCards: byId('heroCards'), newChatBtn: byId('newChatBtn'),
  };
  if (els.chatSearchInput) els.chatSearchInput.addEventListener('input', renderChatList);
  renderHeroCards(els, syncSendBtnState);

  els.promptInput.addEventListener('input', () => {
    els.promptInput.style.height = 'auto';
    els.promptInput.style.height = Math.min(els.promptInput.scrollHeight, 160) + 'px';
    syncSendBtnState();
  });
  els.attachBtn.addEventListener('click', () => els.fileInput.click());
  els.fileInput.addEventListener('change', () => {
    if (els.fileInput.files.length > 0) {
      selectedFile = els.fileInput.files[0];
      els.fileChipName.textContent = selectedFile.name;
      els.fileChip.classList.add('active');
    }
  });
  els.removeFile.addEventListener('click', () => {
    selectedFile = null; els.fileInput.value = ''; els.fileChip.classList.remove('active');
  });
  els.sendBtn.addEventListener('click', () => sendMessage());
  els.promptInput.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' || e.shiftKey) return;
    if (getPrefs().send_with_enter !== false || e.ctrlKey || e.metaKey) { e.preventDefault(); sendMessage(); }
  });
  els.newChatBtn.addEventListener('click', () => { persistCurrentChat(); startNewChat(true); });
  const brandHomeLink = byId('brandHomeLink');
  if (brandHomeLink) {
    brandHomeLink.addEventListener('click', (e) => {
      e.preventDefault(); persistCurrentChat(); startNewChat(true);
      if (location.hash !== '#/assistant') location.hash = '#/assistant';
    });
  }
  els.messages.addEventListener('scroll', () => {
    const dist = els.messages.scrollHeight - els.messages.scrollTop - els.messages.clientHeight;
    if (dist > 64) userScrolledUp = true; else if (dist <= 36) userScrolledUp = false;
  }, { passive: true });
  els.messages.addEventListener('wheel', (e) => { if (e.deltaY < 0) userScrolledUp = true; }, { passive: true });
  els.messages.addEventListener('click', handleMessagesClick);
  initVoiceRecognition(els, syncSendBtnState);
  showRunButtonsIfEnabled();

  bindGlobalEvent(document, 'open-saved-chat', (e) => {
    const cid = e.detail && e.detail.chatId;
    if (!cid) return;
    if (location.hash !== '#/assistant') location.hash = '#/assistant';
    openChat(cid);
  });
  bindGlobalEvent(document, 'voice-auto-submit', (e) => {
    const txt = (e.detail && e.detail.transcript) || els.promptInput.value.trim();
    if (txt) sendMessage(txt);
  });
  bindGlobalEvent(document, 'chats-wiped', () => {
    saveChats({});
    storageRemove(storageKeys().lastChatKey);
    startNewChat(true);
  });

  startNewChat(false);
  syncChatsWithServer(state, { openChat, renderChatList });
}

export function focusAssistant() {
  els.promptInput.focus();
}
