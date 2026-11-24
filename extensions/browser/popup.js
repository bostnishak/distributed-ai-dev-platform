// ENT-03: Local-only Chrome/Edge Manifest V3 popup sending user-approved text strictly to localhost master.
const MASTER_BASE = 'http://127.0.0.1:8000';

document.getElementById('extSendBtn').addEventListener('click', async () => {
  const out = document.getElementById('extOut');
  const promptEl = document.getElementById('extPrompt');
  const prompt = (promptEl.value || '').trim();
  if (!prompt) {
    out.textContent = 'Lütfen bir soru veya metin girin.';
    return;
  }
  out.textContent = 'Yerel sunucuya soruluyor...';
  try {
    const fd = new FormData();
    fd.append('prompt', prompt);
    const resp = await fetch(`${MASTER_BASE}/api/assistant/chat`, { method: 'POST', body: fd });
    const data = await resp.json();
    out.textContent = data.content || data.detail || 'Yanıt alınamadı.';
  } catch (err) {
    out.textContent = `Bağlantı hatası: ${err.message}`;
  }
});
