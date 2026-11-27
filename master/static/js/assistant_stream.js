// Streaming SSE consumer and post-stream completion renderer for Assistant chat.
import { MODEL_LABELS } from './assistant_hero.js';
import { buildInlineWorkspaceCard } from './assistant_ide_card.js';
import { getSelectedCustomAgent, getSelectedModel } from './chat_enhancements.js';
import { escapeHtml, renderMarkdown } from './markdown.js';
import { notifyAnswerReady } from './message_tools.js';
import { getActiveUserId, getPrefs } from './personal.js';
import { appendSanitizedHtml, setSanitizedHtml } from './sanitizer.js';
import { safeFetch, startManagedInterval } from './storage.js';
import { renderConfidenceBadgeHtml } from './ux_shell.js';

function createStreamPlaceholder(fileToSend, els, scrollToBottomIfPinned) {
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
  setSanitizedHtml(
    bubble,
    `<div class="sp-think-head"><span class="sp-think-ring"></span><span class="sp-think-label">${stages[0]}<span class="sp-think-dots"><i></i><i></i><i></i></span></span><span class="sp-think-timer">0 sn</span></div><div class="sp-think-skel"><span></span><span></span><span></span></div>`,
  );

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
    } else if (streamTextEl) {
      streamTextEl.textContent = `Yanıt yazılıyor · ${secStr}`;
    }
  }, 250);

  wrap.append(streamBar, bubble);
  row.appendChild(wrap);
  els.messages.appendChild(row);
  scrollToBottomIfPinned(true);

  return {
    row,
    wrap,
    streamBar,
    bubble,
    thinkTicker,
    isStreaming: () => streaming,
    setStreaming: (v) => { streaming = v; },
  };
}

async function consumeAssistantStream(resp, ui, ctx) {
  const res = {
    fullText: '',
    usedModel: '',
    builtWorkspace: null,
    usageInfo: null,
    verificationInfo: null,
    latencyMs: 0,
    councilTrace: null,
    ttftMs: 0,
    errorText: null,
  };
  const reqStartMs = performance.now();
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
        if (!ui.isStreaming()) {
          ui.setStreaming(true);
          res.ttftMs = Math.max(1, Math.round(performance.now() - reqStartMs));
          ui.bubble.classList.remove('thinking');
          ui.bubble.classList.add('streaming');
          ui.bubble.textContent = '';
          ui.streamBar.hidden = false;
        }
        res.fullText += evt.content;
        setSanitizedHtml(ui.bubble, renderMarkdown(res.fullText));
        if (ctx.state.currentChatId === ctx.targetChatId) ctx.scrollToBottomIfPinned(false);
      } else if (evt.type === 'restart') {
        res.fullText = '';
        ui.bubble.textContent = 'Yanıt bozulmaya başladı (' + evt.reason + '), yeniden yazılıyor...';
      } else if (evt.type === 'status') {
        if (!ui.isStreaming() && evt.message) ui.bubble.textContent = evt.message;
      } else if (evt.type === 'council') {
        res.councilTrace = evt.council;
      } else if (evt.type === 'workspace') {
        res.builtWorkspace = { workspace: evt.workspace, tree: evt.tree };
      } else if (evt.type === 'done') {
        res.usedModel = evt.model || '';
        res.usageInfo = evt.usage || null;
        res.latencyMs = evt.latency_ms || 0;
        res.verificationInfo = evt.verification || null;
      } else if (evt.type === 'error') {
        res.errorText = 'Model hatası: ' + evt.content;
        return res;
      }
    }
  }
  return res;
}

function renderStreamCompletion(res, ui, ctx) {
  if (!res.fullText && !res.builtWorkspace) return;
  setSanitizedHtml(ui.bubble, renderMarkdown(res.fullText));
  if (res.builtWorkspace) {
    ui.wrap.appendChild(buildInlineWorkspaceCard(res.builtWorkspace.workspace, res.builtWorkspace.tree));
  }
  const label = MODEL_LABELS[res.usedModel] || res.usedModel;
  if (label && getPrefs().show_model_badge) {
    const badgeRow = document.createElement('div');
    badgeRow.className = 'badge-row';
    const badge = document.createElement('span');
    badge.className = 'badge';
    badge.textContent = label;
    badgeRow.appendChild(badge);
    if (res.verificationInfo) {
      appendSanitizedHtml(
        badgeRow,
        ' ' + renderConfidenceBadgeHtml(res.verificationInfo.confidence_label, res.verificationInfo.confidence_score, 'tr'),
      );
    }
    ui.wrap.insertBefore(badgeRow, ui.bubble);
  }
  if (res.councilTrace) {
    const det = document.createElement('details');
    det.className = 'sp-card';
    det.style.marginBottom = '6px';
    setSanitizedHtml(
      det,
      `<summary>Ajan Konseyi Düşünce Zinciri ve Hakem Sentezi</summary><pre class="sp-preview-pre">${escapeHtml(JSON.stringify(res.councilTrace, null, 2))}</pre>`,
    );
    ui.wrap.insertBefore(det, ui.bubble);
  }
  if (res.usageInfo && getPrefs().show_token_counter) {
    const meta = document.createElement('div');
    meta.className = 'sp-meta';
    const approx = res.usageInfo.estimated ? '~' : '';
    const total = (res.usageInfo.prompt_tokens || 0) + (res.usageInfo.completion_tokens || 0);
    const parts = [`${approx}${total.toLocaleString('tr-TR')} token`];
    if (res.ttftMs) parts.push(`TTFT ${res.ttftMs} ms`);
    if (res.latencyMs) parts.push(`${Math.floor(res.latencyMs / 1000)} sn`);
    for (const p of parts) {
      const s = document.createElement('span');
      s.textContent = p;
      meta.appendChild(s);
    }
    ui.wrap.appendChild(meta);
  }
  ui.wrap.appendChild(ctx.messageBar(res.fullText));
  ctx.appendAssistantMessageToChat(ctx.targetChatId, {
    role: 'assistant', text: res.fullText, modelBadge: label, isError: false, workspace: res.builtWorkspace,
  });
}

function showStreamError(errText, ui, ctx) {
  ui.row.remove();
  if (ctx.state.currentChatId === ctx.targetChatId) ctx.addAssistantMessage(errText, null, true, false, false);
  ctx.appendAssistantMessageToChat(ctx.targetChatId, { role: 'assistant', text: errText, modelBadge: null, isError: true });
}

export async function runAssistantStream(ctx) {
  const { prompt, historySnapshot, fileToSend, targetChatId, els, state } = ctx;
  const controller = new AbortController();
  const ui = createStreamPlaceholder(fileToSend, els, ctx.scrollToBottomIfPinned);
  state.activeStreams.set(targetChatId, { controller, row: ui.row, thinkTicker: ui.thinkTicker });
  ctx.syncSendBtnState();
  ctx.renderChatList();

  let finalText = '';
  let usedModel = '';

  try {
    const formData = new FormData();
    formData.append('prompt', prompt);
    formData.append('history', JSON.stringify(historySnapshot));
    formData.append('user_id', getActiveUserId());
    formData.append('conversation_id', targetChatId || '');
    const pickedModel = getSelectedModel();
    if (pickedModel) formData.append('model', pickedModel);
    const pickedAgent = getSelectedCustomAgent();
    if (pickedAgent) formData.append('custom_agent_id', pickedAgent);
    if (fileToSend) formData.append('file', fileToSend);

    const resp = await safeFetch('/api/assistant/chat/stream', { method: 'POST', body: formData, signal: controller.signal });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      showStreamError(data.detail || 'Bilinmeyen hata', ui, ctx);
      return;
    }

    const res = await consumeAssistantStream(resp, ui, ctx);
    finalText = res.fullText;
    usedModel = res.usedModel;
    if (res.errorText) {
      showStreamError(res.errorText, ui, ctx);
      return;
    }
    renderStreamCompletion(res, ui, ctx);
  } catch (err) {
    if (err && err.name === 'AbortError') {
      finalText += '\n\n*[Yanıt kullanıcı tarafından durduruldu]*';
      ui.bubble.classList.remove('thinking');
      setSanitizedHtml(ui.bubble, renderMarkdown(finalText));
      ui.wrap.appendChild(ctx.messageBar(finalText));
      ctx.appendAssistantMessageToChat(targetChatId, {
        role: 'assistant', text: finalText, modelBadge: MODEL_LABELS[usedModel] || usedModel, isError: false,
      });
    } else {
      showStreamError('Bağlantı hatası: ' + err.message, ui, ctx);
    }
  } finally {
    if (typeof ui.thinkTicker === 'function') ui.thinkTicker();
    ui.bubble.classList.remove('thinking', 'streaming');
    ui.streamBar.remove();
    state.activeStreams.delete(targetChatId);
    ctx.syncSendBtnState();
    ctx.renderChatList();
    if (state.currentChatId === targetChatId) els.promptInput.focus();
    document.dispatchEvent(new CustomEvent('usage-updated'));
    if (finalText) {
      document.dispatchEvent(new CustomEvent('assistant-reply-complete', { detail: { text: finalText, model: usedModel } }));
    }
    notifyAnswerReady(finalText || 'Yanıt tamamlandı');
  }
}
