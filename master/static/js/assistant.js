// Assistant tab: modularized core chat controller (UX-02 <= 500 lines).
import { createMessageActions, MODEL_LABELS, renderHeroCards } from './assistant_hero.js';
import {
  loadChats,
  persistChatRecord,
  renderSidebarChatList,
  saveChats,
  storageKeys,
  syncChatsWithServer,
} from './assistant_history.js';
import { buildInlineWorkspaceCard } from './assistant_ide_card.js';
import {
  handleRunCodeClick,
  initVoiceRecognition,
  showRunButtonsIfEnabled,
} from './assistant_voice.js';
import { escapeHtml, renderMarkdown } from './markdown.js';
import { getActiveUserId, getPrefs } from './personal.js';
import { buildBranchLink, buildExtraActions, notifyAnswerReady, regenerateLast, requestNotifyPermission } from './message_tools.js';
import { appendSanitizedHtml, setSanitizedHtml } from './sanitizer.js';
import { bindGlobalEvent, safeFetch, startManagedInterval, storageRemove, storageSet } from './storage.js';
import { closeSidebar } from './util.js';
import { parseSlashAndMentions, renderConfidenceBadgeHtml } from './ux_shell.js';

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
  if (clearLastActive) {
    try { localStorage.removeItem(storageKeys().lastChatKey); } catch { /* ignore */ }
  }
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

  const controller = new AbortController();
  const row = document.createElement('div');
  row.className = 'msg-row assistant';
  const wrap = document.createElement('div');
  wrap.className = 'msg-wrap';
  const streamBar = document.createElement('div');
  streamBar.className = 'sp-stream-bar';
  streamBar.hidden = true;
  setSanitizedHtml(streamBar, '<span class="sp-think-ring sm"></span><span class="sp-stream-text">Yanıt yazılıyor...</span>');

  const bubble = document.createElement('div');
  bubble.className = 'msg assistant thinking';
  const stages = fileToSend
    ? ['Dosya okunuyor ve denetleniyor', 'Bağlam ve hafıza taranıyor', 'Düşünüyor ve analiz ediyor', 'Yanıt hazırlanıyor']
    : ['Düşünüyor', 'Hafıza ve sohbetler taranıyor', 'Yanıt hazırlanıyor'];
  setSanitizedHtml(bubble, `<div class="sp-think-head"><span class="sp-think-ring"></span><span class="sp-think-label">${stages[0]}<span class="sp-think-dots"><i></i><i></i><i></i></span></span><span class="sp-think-timer">0 sn</span></div><div class="sp-think-skel"><span></span><span></span><span></span></div>`);

  const thinkLabelEl = bubble.querySelector('.sp-think-label');
  const thinkTimerEl = bubble.querySelector('.sp-think-timer');
  const streamTextEl = streamBar.querySelector('.sp-stream-text');
  const startedAt = performance.now();
  let stageIdx = 0;
  let streaming = false;
  const thinkTicker = startManagedInterval(() => {
    const sec = (performance.now() - startedAt) / 1000;
    const secStr = `${Math.floor(sec)} sn`;
    if (!streaming) {
      if (thinkTimerEl) thinkTimerEl.textContent = secStr;
      const nextIdx = Math.min(stages.length - 1, Math.floor(sec / 2.2));
      if (nextIdx !== stageIdx && thinkLabelEl) {
        stageIdx = nextIdx;
        setSanitizedHtml(thinkLabelEl, `${stages[stageIdx]}<span class="sp-think-dots"><i></i><i></i><i></i></span>`);
      }
    } else if (streamTextEl) streamTextEl.textContent = `Yanıt yazılıyor · ${secStr}`;
  }, 250);

  wrap.append(streamBar, bubble);
  row.appendChild(wrap);
  els.messages.appendChild(row);
  scrollToBottomIfPinned(true);

  state.activeStreams.set(targetChatId, { controller, row, thinkTicker });
  syncSendBtnState();
  renderChatList();

  let fullText = '';
  let usedModel = '';
  let builtWorkspace = null;
  let usageInfo = null;
  let verificationInfo = null;
  let latencyMs = 0;
  let councilTrace = null;
  const reqStartMs = performance.now();
  let ttftMs = 0;

  try {
    const formData = new FormData();
    formData.append('prompt', prompt);
    formData.append('history', JSON.stringify(historySnapshot));
    formData.append('user_id', getActiveUserId());
    formData.append('conversation_id', targetChatId || '');
    if (fileToSend) formData.append('file', fileToSend);

    const resp = await safeFetch('/api/assistant/chat/stream', { method: 'POST', body: formData, signal: controller.signal });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      const errText = data.detail || 'Bilinmeyen hata';
      row.remove();
      if (state.currentChatId === targetChatId) addAssistantMessage(errText, null, true, false, false);
      appendAssistantMessageToChat(targetChatId, { role: 'assistant', text: errText, modelBadge: null, isError: true });
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        let evt;
        try { evt = JSON.parse(line.slice(6)); } catch { continue; }
        if (evt.type === 'token') {
          if (!streaming) {
            streaming = true;
            ttftMs = Math.max(1, Math.round(performance.now() - reqStartMs));
            bubble.classList.remove('thinking');
            bubble.classList.add('streaming');
            bubble.textContent = '';
            streamBar.hidden = false;
          }
          fullText += evt.content;
          setSanitizedHtml(bubble, renderMarkdown(fullText));
          if (state.currentChatId === targetChatId) scrollToBottomIfPinned(false);
        } else if (evt.type === 'council') councilTrace = evt.council;
        else if (evt.type === 'workspace') builtWorkspace = { workspace: evt.workspace, tree: evt.tree };
        else if (evt.type === 'done') {
          usedModel = evt.model || '';
          usageInfo = evt.usage || null;
          latencyMs = evt.latency_ms || 0;
          verificationInfo = evt.verification || null;
        } else if (evt.type === 'error') {
          const errText = 'Model hatası: ' + evt.content;
          row.remove();
          if (state.currentChatId === targetChatId) addAssistantMessage(errText, null, true, false, false);
          appendAssistantMessageToChat(targetChatId, { role: 'assistant', text: errText, modelBadge: null, isError: true });
          return;
        }
      }
    }

    if (fullText || builtWorkspace) {
      setSanitizedHtml(bubble, renderMarkdown(fullText));
      if (builtWorkspace) wrap.appendChild(buildInlineWorkspaceCard(builtWorkspace.workspace, builtWorkspace.tree));
      const label = MODEL_LABELS[usedModel] || usedModel;
      if (label && getPrefs().show_model_badge) {
        const badgeRow = document.createElement('div');
        badgeRow.className = 'badge-row';
        const badge = document.createElement('span');
        badge.className = 'badge';
        badge.textContent = label;
        badgeRow.appendChild(badge);
        if (verificationInfo) {
          appendSanitizedHtml(badgeRow, ' ' + renderConfidenceBadgeHtml(verificationInfo.confidence_label, verificationInfo.confidence_score, 'tr'));
        }
        wrap.insertBefore(badgeRow, bubble);
      }
      if (councilTrace) {
        const det = document.createElement('details');
        det.className = 'sp-card';
        det.style.marginBottom = '6px';
        setSanitizedHtml(det, `<summary>Ajan Konseyi Düşünce Zinciri ve Hakem Sentezi</summary><pre class="sp-preview-pre">${escapeHtml(JSON.stringify(councilTrace, null, 2))}</pre>`);
        wrap.insertBefore(det, bubble);
      }
      if (usageInfo && getPrefs().show_token_counter) {
        const meta = document.createElement('div');
        meta.className = 'sp-meta';
        const approx = usageInfo.estimated ? '~' : '';
        const total = (usageInfo.prompt_tokens || 0) + (usageInfo.completion_tokens || 0);
        const parts = [`${approx}${total.toLocaleString('tr-TR')} token`];
        if (ttftMs) parts.push(`TTFT ${ttftMs} ms`);
        if (latencyMs) parts.push(`${Math.floor(latencyMs / 1000)} sn`);
        for (const p of parts) { const s = document.createElement('span'); s.textContent = p; meta.appendChild(s); }
        wrap.appendChild(meta);
      }
      wrap.appendChild(messageBar(fullText));
      appendAssistantMessageToChat(targetChatId, { role: 'assistant', text: fullText, modelBadge: label, isError: false, workspace: builtWorkspace });
    }
  } catch (err) {
    if (err && err.name === 'AbortError') {
      fullText += '\n\n*[Yanıt kullanıcı tarafından durduruldu]*';
      bubble.classList.remove('thinking');
      setSanitizedHtml(bubble, renderMarkdown(fullText));
      wrap.appendChild(messageBar(fullText));
      appendAssistantMessageToChat(targetChatId, { role: 'assistant', text: fullText, modelBadge: MODEL_LABELS[usedModel] || usedModel, isError: false });
    } else {
      const errText = 'Bağlantı hatası: ' + err.message;
      row.remove();
      if (state.currentChatId === targetChatId) addAssistantMessage(errText, null, true, false, false);
      appendAssistantMessageToChat(targetChatId, { role: 'assistant', text: errText, modelBadge: null, isError: true });
    }
  } finally {
    if (typeof thinkTicker === 'function') thinkTicker();
    bubble.classList.remove('thinking', 'streaming');
    streamBar.remove();
    state.activeStreams.delete(targetChatId);
    syncSendBtnState();
    renderChatList();
    if (state.currentChatId === targetChatId) els.promptInput.focus();
    document.dispatchEvent(new CustomEvent('usage-updated'));
    notifyAnswerReady(fullText || 'Yanıt tamamlandı');
  }
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
  els.messages.addEventListener('click', async (e) => {
    const copyBtn = e.target.closest('.sp-code-copy');
    if (copyBtn) {
      const codeEl = copyBtn.closest('.code-block')?.querySelector('pre code');
      if (!codeEl) return;
      try {
        await navigator.clipboard.writeText(codeEl.textContent || '');
        copyBtn.textContent = 'Kopyalandı'; copyBtn.classList.add('copied');
        const COPY_MS = 1600;
        setTimeout(() => { copyBtn.textContent = 'Kopyala'; copyBtn.classList.remove('copied'); }, COPY_MS);
      } catch { copyBtn.textContent = 'Kopyalanamadı'; }
      return;
    }
    handleRunCodeClick(e);
  });
  initVoiceRecognition(els, syncSendBtnState);
  showRunButtonsIfEnabled();

  bindGlobalEvent(document, 'open-saved-chat', (e) => {
    const cid = e.detail && e.detail.chatId;
    if (!cid) return;
    if (location.hash !== '#/assistant') location.hash = '#/assistant';
    openChat(cid);
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
