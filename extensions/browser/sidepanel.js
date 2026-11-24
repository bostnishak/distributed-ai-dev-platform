// EPK-34 / ENT-03: Consent-gated local DADP browser sidepanel controller.
const LOCAL_ENDPOINT = 'http://127.0.0.1:8000/v1/chat/completions';

function initSidepanel() {
  const consentEl = document.getElementById('consent');
  const selEl = document.getElementById('sel');
  const sendBtn = document.getElementById('sendBtn');
  const outEl = document.getElementById('out');
  if (!consentEl || !selEl || !sendBtn || !outEl) return;

  if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.onMessage) {
    chrome.runtime.onMessage.addListener((msg) => {
      if (msg && msg.type === 'DADP_SELECTION' && typeof msg.text === 'string') {
        selEl.value = msg.text;
      }
    });
  }

  sendBtn.addEventListener('click', async () => {
    if (!consentEl.checked) {
      outEl.textContent = 'Gönderim için açık onay kutusunu işaretleyin.';
      return;
    }
    const text = selEl.value.trim();
    if (!text) {
      outEl.textContent = 'Özetlenecek metin boş olamaz.';
      return;
    }
    sendBtn.disabled = true;
    outEl.textContent = 'Yerel DADP sunucusuna gönderiliyor...';
    try {
      const resp = await fetch(LOCAL_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'qwen3.5:9b',
          messages: [{ role: 'user', content: `Aşağıdaki metni Türkçe olarak kısaca özetle:\n\n${text}` }],
        }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        outEl.textContent = `Sunucu hatası (${resp.status}): ${data.detail || 'Bilinmeyen hata'}`;
      } else {
        const msg = data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content;
        outEl.textContent = msg || JSON.stringify(data, null, 2);
      }
    } catch (err) {
      outEl.textContent = `Yerel sunucuya ulaşılamadı: ${err.message}`;
    } finally {
      sendBtn.disabled = false;
    }
  });
}

if (typeof document !== 'undefined') initSidepanel();
