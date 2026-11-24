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

export function initVoiceRecognition(els, updateSendState) {
  if (!els.micBtn) return;

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

  let recording = false;
  let mediaStream = null;
  let audioCtx = null;
  let processor = null;
  let pcmChunks = [];
  let recTimer = null;
  let recStart = 0;
  let heardVoice = false;

  function showVoiceStatus(text, isLive = false) {
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
  }

  function hideVoiceStatus(delayMs = 0) {
    if (delayMs > 0) setTimeout(() => { if (!recording) statusPill.hidden = true; }, delayMs);
    else statusPill.hidden = true;
  }

  async function transcribeBlob(blob, filename) {
    showVoiceStatus('Ses metne çevriliyor (yerel Whisper STT)...', false);
    const fd = new FormData();
    fd.append('file', blob, filename);
    const res = await safeFetchJson('/api/assistant/transcribe', { method: 'POST', body: fd });
    if (res.status === 0) {
      showVoiceStatus(`Ses çevirme hatası: ${res.error}`, false);
      hideVoiceStatus(3400);
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
      showVoiceStatus(`Metne çevrildi (${data.duration_sec || 0} sn)`, false);
      hideVoiceStatus(2400);
    } else {
      showVoiceStatus('Konuşma algılanamadı, mikrofona biraz daha yakın konuşup tekrar deneyin.', false);
      hideVoiceStatus(3200);
    }
  }

  audioPicker.addEventListener('change', () => {
    const f = audioPicker.files && audioPicker.files[0];
    audioPicker.value = '';
    if (f) transcribeBlob(f, f.name);
  });

  function showMicErrorWithUpload(msg) {
    statusPill.hidden = false;
    statusPill.replaceChildren();
    const span = document.createElement('span');
    span.textContent = msg;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = 'Ses Dosyası Seç';
    btn.addEventListener('click', () => audioPicker.click());
    statusPill.append(span, btn);
  }

  async function stopAndTranscribe() {
    recording = false;
    if (typeof recTimer === 'function') recTimer();
    recTimer = null;
    els.micBtn.classList.remove('recording');
    els.micBtn.title = 'Sesli mesajı metne çevir';

    const sampleRate = (audioCtx && audioCtx.sampleRate) || 48000;
    try { if (processor) processor.disconnect(); } catch { /* ignore */ }
    try { if (audioCtx) await audioCtx.close(); } catch { /* ignore */ }
    try { if (mediaStream) mediaStream.getTracks().forEach((t) => t.stop()); } catch { /* ignore */ }
    mediaStream = null; audioCtx = null; processor = null;

    if (!pcmChunks.length) {
      showVoiceStatus('Ses kaydı alınamadı, lütfen mikrofonu kontrol edip tekrar deneyin.', false);
      hideVoiceStatus(3000);
      return;
    }

    const wavBlob = encodeMonoWav16k(pcmChunks, sampleRate);
    pcmChunks = [];
    await transcribeBlob(wavBlob, 'mikrofon.wav');
  }

  async function startRecording() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showMicErrorWithUpload('Tarayıcı canlı mikrofon erişimine izin vermiyor (localhost kullanın veya ses dosyası yükleyin).');
      return;
    }
    showVoiceStatus('Mikrofon açılıyor...', false);
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      audioCtx = new AudioCtx();
      if (audioCtx.state === 'suspended') await audioCtx.resume();
      const source = audioCtx.createMediaStreamSource(mediaStream);
      processor = audioCtx.createScriptProcessor(4096, 1, 1);
      pcmChunks = [];
      heardVoice = false;
      processor.onaudioprocess = (e) => {
        if (!recording) return;
        const ch = new Float32Array(e.inputBuffer.getChannelData(0));
        pcmChunks.push(ch);
        if (!heardVoice) {
          for (let i = 0; i < ch.length; i += 64) {
            if (Math.abs(ch[i]) > 0.015) { heardVoice = true; break; }
          }
        }
      };
      source.connect(processor);
      processor.connect(audioCtx.destination);

      recording = true;
      recStart = Date.now();
      els.micBtn.classList.add('recording');
      els.micBtn.title = 'Kayıt yapılıyor... Durdurmak için tıklayın';
      showVoiceStatus('Dinleniyor · 0 sn (Bitirmek için mikrofona tekrar basın)', true);
      recTimer = startManagedInterval(() => {
        const sec = Math.floor((Date.now() - recStart) / 1000);
        const levelTxt = heardVoice ? ' · Ses algılandı' : '';
        showVoiceStatus(`Dinleniyor · ${sec} sn${levelTxt} (Bitirmek için tekrar basın)`, true);
      }, 400);
    } catch (err) {
      const reason = err.name === 'NotAllowedError'
        ? 'Mikrofon izni kapalı. Adres çubuğundan izin verin veya:'
        : `Mikrofon açılamadı (${err.name || err.message}).`;
      showMicErrorWithUpload(reason);
    }
  }

  els.micBtn.addEventListener('click', () => {
    if (recording) stopAndTranscribe();
    else startRecording();
  });
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
