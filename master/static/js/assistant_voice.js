// UX-02 Modular Split: Local Whisper STT voice capture + sandboxed Python code execution handlers.
import { safeFetchJson, startManagedInterval } from './storage.js';

export function encodeMonoWav16k(chunks, inputSampleRate) {
  let totalLen = 0;
  for (const c of chunks) totalLen += c.length;
  const merged = new Float32Array(totalLen);
  let offset = 0;
  for (const c of chunks) { merged.set(c, offset); offset += c.length; }

  const targetRate = 16000;
  const ratio = inputSampleRate / targetRate;
  const outLen = Math.max(1, Math.floor(merged.length / ratio));
  const pcm = new Int16Array(outLen);
  for (let i = 0; i < outLen; i++) {
    const s = Math.max(-1, Math.min(1, merged[Math.floor(i * ratio)] || 0));
    pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }

  const buf = new ArrayBuffer(44 + pcm.length * 2);
  const view = new DataView(buf);
  const writeStr = (pos, str) => { for (let i = 0; i < str.length; i++) view.setUint8(pos + i, str.charCodeAt(i)); };
  writeStr(0, 'RIFF');
  view.setUint32(4, 36 + pcm.length * 2, true);
  writeStr(8, 'WAVE');
  writeStr(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, targetRate, true);
  view.setUint32(28, targetRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, 'data');
  view.setUint32(40, pcm.length * 2, true);
  for (let i = 0; i < pcm.length; i++) view.setInt16(44 + i * 2, pcm[i], true);
  return new Blob([buf], { type: 'audio/wav' });
}

function createVoiceUi(els) {
  const statusPill = document.createElement('div');
  statusPill.className = 'sp-voice-status';
  statusPill.hidden = true;
  const inputWrap = document.getElementById('inputWrap');
  if (inputWrap) inputWrap.insertBefore(statusPill, document.getElementById('inputPill'));

  const audioPicker = document.createElement('input');
  audioPicker.type = 'file';
  audioPicker.accept = 'audio/*,.wav,.mp3,.m4a,.ogg,.webm';
  audioPicker.style.display = 'none';
  document.body.appendChild(audioPicker);

  const show = (text, isLive = false) => {
    statusPill.hidden = false;
    statusPill.replaceChildren();
    if (isLive) {
      const dot = document.createElement('span');
      dot.className = 'sp-voice-dot';
      statusPill.appendChild(dot);
    }
    const lbl = document.createElement('span');
    lbl.textContent = text;
    statusPill.appendChild(lbl);
  };
  const hide = (delayMs = 0, isRec = () => false) => {
    if (delayMs > 0) setTimeout(() => { if (!isRec()) statusPill.hidden = true; }, delayMs);
    else statusPill.hidden = true;
  };
  const showError = (msg) => {
    statusPill.hidden = false;
    statusPill.replaceChildren();
    const span = document.createElement('span');
    span.textContent = msg;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = 'Ses Dosyası Seç';
    btn.addEventListener('click', () => audioPicker.click());
    statusPill.append(span, btn);
  };
  return { audioPicker, show, hide, showError };
}

async function transcribeAudioBlob(blob, filename, els, ui, updateSendState, isRec) {
  ui.show('Ses metne çevriliyor (yerel Whisper STT)...', false);
  const fd = new FormData();
  fd.append('file', blob, filename);
  const res = await safeFetchJson('/api/assistant/transcribe', { method: 'POST', body: fd });
  if (res.status === 0) {
    ui.show(`Ses çevirme hatası: ${res.error}`, false);
    ui.hide(3400, isRec);
    return;
  }
  const data = res.data || {};
  if (res.ok && data.transcript) {
    const prefix = els.promptInput.value.trim() ? els.promptInput.value.trim() + ' ' : '';
    els.promptInput.value = prefix + data.transcript;
    els.promptInput.style.height = 'auto';
    els.promptInput.style.height = Math.min(els.promptInput.scrollHeight, 160) + 'px';
    updateSendState();
    els.promptInput.focus();
    ui.show(`Metne çevrildi (${data.duration_sec || 0} sn)`, false);
    ui.hide(2400, isRec);
  } else {
    ui.show('Konuşma algılanamadı, mikrofona biraz daha yakın konuşup tekrar deneyin.', false);
    ui.hide(3200, isRec);
  }
}

export function initVoiceRecognition(els, updateSendState) {
  if (!els.micBtn) return;
  const ui = createVoiceUi(els);
  const st = { recording: false, mediaStream: null, audioCtx: null, processor: null, pcmChunks: [], recTimer: null, recStart: 0, heardVoice: false };
  const isRec = () => st.recording;

  ui.audioPicker.addEventListener('change', () => {
    const f = ui.audioPicker.files && ui.audioPicker.files[0];
    ui.audioPicker.value = '';
    if (f) transcribeAudioBlob(f, f.name, els, ui, updateSendState, isRec);
  });

  async function stopAndTranscribe() {
    st.recording = false;
    if (typeof st.recTimer === 'function') st.recTimer();
    st.recTimer = null;
    els.micBtn.classList.remove('recording');
    els.micBtn.title = 'Sesli mesajı metne çevir';
    const sampleRate = (st.audioCtx && st.audioCtx.sampleRate) || 48000;
    try { if (st.processor) st.processor.disconnect(); } catch { /* ignore */ }
    try { if (st.audioCtx) await st.audioCtx.close(); } catch { /* ignore */ }
    try { if (st.mediaStream) st.mediaStream.getTracks().forEach((t) => t.stop()); } catch { /* ignore */ }
    st.mediaStream = null; st.audioCtx = null; st.processor = null;
    if (!st.pcmChunks.length) { ui.show('Ses kaydı alınamadı, lütfen mikrofonu kontrol edin.', false); ui.hide(3000, isRec); return; }
    const wavBlob = encodeMonoWav16k(st.pcmChunks, sampleRate);
    st.pcmChunks = [];
    await transcribeAudioBlob(wavBlob, 'mikrofon.wav', els, ui, updateSendState, isRec);
  }

  async function startRecording() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      ui.showError('Tarayıcı canlı mikrofon erişimine izin vermiyor (localhost kullanın veya ses dosyası yükleyin).');
      return;
    }
    ui.show('Mikrofon açılıyor...', false);
    try {
      st.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      st.audioCtx = new AudioCtx();
      if (st.audioCtx.state === 'suspended') await st.audioCtx.resume();
      const source = st.audioCtx.createMediaStreamSource(st.mediaStream);
      st.processor = st.audioCtx.createScriptProcessor(4096, 1, 1);
      st.pcmChunks = []; st.heardVoice = false;
      st.processor.onaudioprocess = (e) => {
        if (!st.recording) return;
        const ch = new Float32Array(e.inputBuffer.getChannelData(0));
        st.pcmChunks.push(ch);
        if (!st.heardVoice) {
          for (let i = 0; i < ch.length; i += 64) { if (Math.abs(ch[i]) > 0.015) { st.heardVoice = true; break; } }
        }
      };
      source.connect(st.processor); st.processor.connect(st.audioCtx.destination);
      st.recording = true; st.recStart = Date.now();
      els.micBtn.classList.add('recording');
      els.micBtn.title = 'Kayıt yapılıyor... Durdurmak için tıklayın';
      ui.show('Dinleniyor · 0 sn (Bitirmek için mikrofona tekrar basın)', true);
      st.recTimer = startManagedInterval(() => {
        const sec = Math.floor((Date.now() - st.recStart) / 1000);
        ui.show(`Dinleniyor · ${sec} sn${st.heardVoice ? ' · Ses algılandı' : ''} (Bitirmek için tekrar basın)`, true);
      }, 400);
    } catch (err) {
      ui.showError(err.name === 'NotAllowedError' ? 'Mikrofon izni kapalı. Adres çubuğundan izin verin veya:' : `Mikrofon açılamadı (${err.name || err.message}).`);
    }
  }

  els.micBtn.addEventListener('click', () => { if (st.recording) stopAndTranscribe(); else startRecording(); });
}

export async function showRunButtonsIfEnabled() {
  document.body.classList.add('code-run-disabled');
  const res = await safeFetchJson('/api/assistant/config');
  if (res.ok && res.data && res.data.code_run_enabled) document.body.classList.remove('code-run-disabled');
}

export async function handleRunCodeClick(e) {
  const btn = e.target.closest('.run-code-btn');
  if (!btn) return;
  const block = btn.closest('.code-block');
  const code = block.querySelector('pre code').textContent;
  const outputEl = block.querySelector('.run-output');

  btn.disabled = true;
  btn.textContent = 'Çalışıyor...';
  outputEl.hidden = false;
  outputEl.classList.remove('run-error');
  outputEl.textContent = '';

  const res = await safeFetchJson('/api/assistant/run-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  });
  if (res.status === 0) {
    outputEl.textContent = `Bağlantı hatası: ${res.error}`;
    outputEl.classList.add('run-error');
  } else if (!res.ok) {
    outputEl.textContent = (res.data && res.data.detail) || 'Kod çalıştırılamadı.';
    outputEl.classList.add('run-error');
  } else {
    const data = res.data || {};
    const parts = [];
    if (data.stdout) parts.push(data.stdout);
    if (data.stderr) parts.push(data.stderr);
    outputEl.textContent = parts.join('\n') || '(çıktı yok)';
    outputEl.classList.toggle('run-error', data.exit_code !== 0);
  }
  btn.disabled = false;
  btn.textContent = '▶ Çalıştır';
}
