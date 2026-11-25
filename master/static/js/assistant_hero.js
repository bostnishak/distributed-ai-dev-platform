import { iconButton } from './message_icons.js';
// UX-02 Modular Split: Model labels, hero suggestion cards & message action toolbar.

export const MODEL_LABELS = {
  'uye1-qwen': 'Üye-1 (İshak Bostan) · Qwen3.5 4B',
  'uye2-phi4mini': 'Üye-2 (Zeynep Duru Küçük) · Phi-4-mini',
  'uye3-llama': 'Üye-3 (Furkan Kaan Özbeyli) · Llama 3.2',
  'uye4-gemma': 'Üye-4 (Semih Sarıca) · Gemma 4',
  'uye5-coder': 'Üye-5 (Işıl Karademir) · Qwen2.5-Coder',
  'uye6-qwen-light': 'Üye-6 (Berfin Yiğit) · Qwen3 1.7B',
  'cnc-ballooner': 'CNC Balonlama Motoru (AS9102 / ISO 2768)',
  'qwen2.5-coder:7b': 'Proje Üretici · Qwen2.5-Coder 7B',
  'moderation': 'İçerik denetimi',
  'hesaplama': 'Hesap makinesi (anında, model kullanılmadı)',
};

export function downloadAsFile(text) {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'yanit.txt';
  a.click();
  URL.revokeObjectURL(url);
}

export function createMessageActions(text, onPromptify) {
  const bar = document.createElement('div');
  bar.className = 'msg-actions';

  const copyBtn = iconButton('copy', 'Kopyala', async () => {
    try {
      await navigator.clipboard.writeText(text);
      copyBtn.setState('check', 'Kopyalandı');
    } catch {
      copyBtn.setState('copy', 'Kopyalanamadı');
    }
    const COPY_RESET_MS = 1600;
    setTimeout(() => copyBtn.setState('copy', 'Kopyala'), COPY_RESET_MS);
  });

  const dl = iconButton('download', 'Dosya olarak indir', () => downloadAsFile(text));

  const ttsBtn = iconButton('speak', 'Sesli oku', () => {
    if (!('speechSynthesis' in window)) return;
    if (window.speechSynthesis.speaking) {
      window.speechSynthesis.cancel();
      ttsBtn.setState('speak', 'Sesli oku');
      return;
    }
    const clean = String(text || '').replace(/```[\s\S]*?```/g, '').replace(/[#*|`_~]/g, ' ').slice(0, 1800);
    const utt = new SpeechSynthesisUtterance(clean);
    utt.lang = 'tr-TR';
    utt.onend = () => ttsBtn.setState('speak', 'Sesli oku');
    utt.onerror = () => ttsBtn.setState('speak', 'Sesli oku');
    ttsBtn.setState('stop', 'Okumayı durdur');
    window.speechSynthesis.speak(utt);
  });

  const promptifyBtn = iconButton('sparkles', 'Sohbeti master prompt yap (başka yapay zekada kullan)', () => {
    if (typeof onPromptify === 'function') {
      onPromptify(
        'Bu sohbet geçmişinin tamamını başka bir yapay zeka aracında baştan sona kullanabileceğim, eksiksiz ve kopyalanabilir tek bir master prompt haline çevir.'
      );
    }
  });

  bar.append(copyBtn, ttsBtn, dl, promptifyBtn);
  return bar;
}

export function renderHeroCards(els, updateSendState) {
  if (!els || !els.heroCards) return;
  const cards = [
    { title: 'Web sitesi veya uygulama yap', prompt: 'Modern, koyu arayüzlü, arama ve filtreleme özellikli bir görev takip web uygulaması oluştur.' },
    { title: 'Excel, Word veya sunum hazırla', prompt: 'Aylık kişisel bütçe takibi için formüllü, grafikli bir Excel (.xlsx) tablosu oluştur.' },
    { title: 'Dosyamı incele', prompt: 'Yüklediğim dosyayı incele, hataları ve iyileştirme önerilerini listele.', attach: true },
    { title: 'Görsel veya logo üret', prompt: 'Minimalist bir teknoloji markası için kurumsal bir logo tasarla.' },
    { title: 'Veriyi analiz et', prompt: '12 aylık örnek satış verisi üzerinden trend analizi ve 3 aylık tahmin raporu hazırla.' },
    { title: 'Araştır ve özetle', prompt: 'Yeni bir yazılım girişimi için pazar araştırması yap ve kaynaklarla özetle.' },
  ];
  els.heroCards.replaceChildren();
  for (const c of cards) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'sp-hero-card';
    btn.textContent = c.title;
    btn.addEventListener('click', () => {
      els.promptInput.value = c.prompt;
      els.promptInput.style.height = 'auto';
      els.promptInput.style.height = Math.min(els.promptInput.scrollHeight, 160) + 'px';
      updateSendState();
      if (c.attach) els.fileInput.click();
      else els.promptInput.focus();
    });
    els.heroCards.appendChild(btn);
  }
}
