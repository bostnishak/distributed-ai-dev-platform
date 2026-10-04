// Assistant tab: the chat assistant. History is stored per browser in localStorage.
import { renderMarkdown } from './markdown.js';
import { closeSidebar } from './util.js';

const STORAGE_KEY = 'coklu_llm_chats';

const MODEL_LABELS = {
  'uye1-qwen': 'Üye-1 (İshak Bostan) · Qwen3.5 4B',
  'uye2-phi4mini': 'Üye-2 (Zeynep Duru Küçük) · Phi-4-mini',
  'uye3-llama': 'Üye-3 (Furkan Kaan Özbeyli) · Llama 3.2',
  'uye4-gemma': 'Üye-4 (Semih Sarıca) · Gemma 4',
  'uye5-coder': 'Üye-5 (Işıl Karademir) · Qwen2.5-Coder',
  'uye6-qwen-light': 'Üye-6 (Berfin Yiğit) · Qwen3 1.7B',
  'moderation': '⚠️ İçerik denetimi',
  'hesaplama': '🧮 Hesap makinesi (anında, model kullanılmadı)',
};

let els;
let selectedFile = null;
let started = false;
let currentChatId = null;
let currentMessages = []; // {role: 'user'|'assistant', text, modelBadge?, fileName?}
let pendingDeleteId = null;

function loadChats() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
  } catch {
    return {};
  }
}

function saveChats(chats) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chats));
  } catch { /* storage may be full or unavailable; history is a convenience only */ }
}

function persistCurrentChat() {
  if (!currentChatId || currentMessages.length === 0) return;
  const chats = loadChats();
  const firstUserMsg = currentMessages.find((m) => m.role === 'user');
  const title = firstUserMsg ? firstUserMsg.text.slice(0, 40) : 'Yeni sohbet';
  chats[currentChatId] = { title, updatedAt: Date.now(), messages: currentMessages };
  saveChats(chats);
  renderChatList();
}

function deleteChat(id) {
  const chats = loadChats();
  delete chats[id];
  saveChats(chats);
  pendingDeleteId = null;
  if (id === currentChatId) startNewChat();
  else renderChatList();
}

function renderChatList() {
  const chats = loadChats();
  els.chatList.innerHTML = '';
  const sorted = Object.entries(chats).sort((a, b) => b[1].updatedAt - a[1].updatedAt);
  for (const [id, chat] of sorted) {
    const item = document.createElement('div');
    item.className = 'chat-item' + (id === currentChatId ? ' active' : '');

    if (pendingDeleteId === id) {
      // In-page confirmation instead of the native confirm() dialog.
      item.classList.add('confirm-mode');
      const label = document.createElement('span');
      label.textContent = 'Silinsin mi?';
      label.style.fontSize = '12px';
      item.appendChild(label);

      const yes = document.createElement('span');
      yes.className = 'confirm-yes';
      yes.textContent = 'Evet';
      yes.addEventListener('click', (e) => { e.stopPropagation(); deleteChat(id); });
      item.appendChild(yes);

      const no = document.createElement('span');
      no.className = 'confirm-no';
      no.textContent = 'Vazgeç';
      no.addEventListener('click', (e) => { e.stopPropagation(); pendingDeleteId = null; renderChatList(); });
      item.appendChild(no);
    } else {
      const titleSpan = document.createElement('span');
      titleSpan.textContent = chat.title || 'Sohbet';
      item.appendChild(titleSpan);

      const del = document.createElement('span');
      del.className = 'del';
      del.textContent = '✕';
      del.title = 'Sohbeti sil';
      del.addEventListener('click', (e) => {
        e.stopPropagation();
        pendingDeleteId = id;
        renderChatList();
      });
      item.appendChild(del);
      item.addEventListener('click', () => openChat(id));
    }

    els.chatList.appendChild(item);
  }
}

function openChat(id) {
  const chat = loadChats()[id];
  if (!chat) return;
  currentChatId = id;
  currentMessages = chat.messages.slice();
  els.messages.innerHTML = '';
  ensureStarted();
  for (const m of currentMessages) {
    if (m.role === 'user') addUserMessage(m.text, m.fileName, false);
    else addAssistantMessage(m.text, m.modelBadge, m.isError, false, false);
  }
  renderChatList();
  closeSidebar();
}

function startNewChat() {
  currentChatId = 'chat_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
  currentMessages = [];
  els.messages.innerHTML = '';
  els.messages.classList.remove('active');
  els.centerStage.style.display = 'flex';
  started = false;
  renderChatList();
  closeSidebar();
}

function updateSendState() {
  els.sendBtn.classList.toggle('ready', els.promptInput.value.trim().length > 0);
}

function ensureStarted() {
  if (!started) {
    started = true;
    els.centerStage.style.display = 'none';
    els.messages.classList.add('active');
  }
}

function addUserMessage(text, fileName, record = true) {
  const row = document.createElement('div');
  row.className = 'msg-row user';
  const bubble = document.createElement('div');
  bubble.className = 'msg user';
  bubble.textContent = fileName ? `📎 ${fileName}\n${text}` : text;
  row.appendChild(bubble);
  els.messages.appendChild(row);
  els.messages.scrollTop = els.messages.scrollHeight;
  if (record) currentMessages.push({ role: 'user', text, fileName });
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
  if (isError || isThinking) {
    bubble.textContent = text;
  } else {
    bubble.innerHTML = renderMarkdown(text);
  }
  wrap.appendChild(bubble);

  if (!isError && !isThinking) {
    const dl = document.createElement('span');
    dl.className = 'download-link';
    dl.textContent = 'Dosya olarak indir';
    dl.style.marginTop = '4px';
    dl.addEventListener('click', () => downloadAsFile(text));
    wrap.appendChild(dl);
  }

  row.appendChild(wrap);
  els.messages.appendChild(row);
  els.messages.scrollTop = els.messages.scrollHeight;
  if (record && !isThinking) currentMessages.push({ role: 'assistant', text, modelBadge, isError });
  return row;
}

function downloadAsFile(text) {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'yanit.txt';
  a.click();
  URL.revokeObjectURL(url);
}

async function sendMessage() {
  const prompt = els.promptInput.value.trim();
  if (!prompt) return;

  ensureStarted();
  addUserMessage(prompt, selectedFile ? selectedFile.name : null);

  const fileToSend = selectedFile;
  els.promptInput.value = '';
  els.promptInput.style.height = 'auto';
  selectedFile = null;
  els.fileInput.value = '';
  els.fileChip.classList.remove('active');
  els.sendBtn.disabled = true;
  updateSendState();

  const thinkingRow = addAssistantMessage('düşünüyor...', null, false, true);

  try {
    const formData = new FormData();
    formData.append('prompt', prompt);
    if (fileToSend) formData.append('file', fileToSend);

    const resp = await fetch('/api/assistant/chat', { method: 'POST', body: formData });
    const data = await resp.json();
    thinkingRow.remove();

    if (!resp.ok) {
      addAssistantMessage(data.detail || 'Bilinmeyen hata', null, true, false);
    } else {
      const label = MODEL_LABELS[data.used_model] || data.used_model;
      addAssistantMessage(data.content, label, false, false);
    }
  } catch (err) {
    thinkingRow.remove();
    addAssistantMessage('Bağlantı hatası: ' + err.message, null, true, false);
  } finally {
    els.sendBtn.disabled = false;
    els.promptInput.focus();
    persistCurrentChat();
  }
}

export function initAssistant() {
  const byId = (id) => document.getElementById(id);
  els = {
    messages: byId('messages'),
    centerStage: byId('centerStage'),
    promptInput: byId('promptInput'),
    sendBtn: byId('sendBtn'),
    attachBtn: byId('attachBtn'),
    fileInput: byId('fileInput'),
    fileChip: byId('fileChip'),
    fileChipName: byId('fileChipName'),
    removeFile: byId('removeFile'),
    chatList: byId('chatList'),
    newChatBtn: byId('newChatBtn'),
  };

  els.promptInput.addEventListener('input', () => {
    els.promptInput.style.height = 'auto';
    els.promptInput.style.height = Math.min(els.promptInput.scrollHeight, 160) + 'px';
    updateSendState();
  });
  els.attachBtn.addEventListener('click', () => els.fileInput.click());
  els.fileInput.addEventListener('change', () => {
    if (els.fileInput.files.length > 0) {
      selectedFile = els.fileInput.files[0];
      els.fileChipName.textContent = '📎 ' + selectedFile.name;
      els.fileChip.classList.add('active');
    }
  });
  els.removeFile.addEventListener('click', () => {
    selectedFile = null;
    els.fileInput.value = '';
    els.fileChip.classList.remove('active');
  });
  els.sendBtn.addEventListener('click', sendMessage);
  els.promptInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  els.newChatBtn.addEventListener('click', () => {
    persistCurrentChat();
    startNewChat();
  });
  els.messages.addEventListener('click', handleRunCodeClick);
  showRunButtonsIfEnabled();

  startNewChat();
}

// The master keeps code running off unless CODE_RUN_ENABLED is set, so the Run buttons stay
// hidden (body class) until the master confirms the feature is on.
async function showRunButtonsIfEnabled() {
  document.body.classList.add('code-run-disabled');
  try {
    const resp = await fetch('/api/assistant/config');
    const data = await resp.json();
    if (data.code_run_enabled) document.body.classList.remove('code-run-disabled');
  } catch {
    // Leave the buttons hidden when the master cannot be asked.
  }
}

// Delegated on the messages container: messages (including ones restored from chat history)
// are inserted via innerHTML, so a single listener here covers every "Run" button rather than
// binding one per code block.
async function handleRunCodeClick(e) {
  const btn = e.target.closest('.run-code-btn');
  if (!btn) return;
  const block = btn.closest('.code-block');
  const code = block.querySelector('pre code').textContent;
  const outputEl = block.querySelector('.run-output');

  btn.disabled = true;
  btn.textContent = '⏳ Çalışıyor...';
  outputEl.hidden = false;
  outputEl.classList.remove('run-error');
  outputEl.textContent = '';

  try {
    const resp = await fetch('/api/assistant/run-code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      outputEl.textContent = data.detail || 'Kod çalıştırılamadı.';
      outputEl.classList.add('run-error');
    } else {
      const parts = [];
      if (data.stdout) parts.push(data.stdout);
      if (data.stderr) parts.push(data.stderr);
      outputEl.textContent = parts.join('\n') || '(çıktı yok)';
      outputEl.classList.toggle('run-error', data.exit_code !== 0);
    }
  } catch (err) {
    outputEl.textContent = 'Bağlantı hatası: ' + err.message;
    outputEl.classList.add('run-error');
  } finally {
    btn.disabled = false;
    btn.textContent = '▶ Çalıştır';
  }
}

export function focusAssistant() {
  els.promptInput.focus();
}
