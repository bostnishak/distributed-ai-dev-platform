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
  bar.style.display = 'flex';
  bar.style.gap = '12px';
  bar.style.marginTop = '5px';

  const copyBtn = document.createElement('span');
  copyBtn.className = 'download-link';
  copyBtn.textContent = 'Kopyala';
  copyBtn.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(text);
      copyBtn.textContent = 'Kopyalandı';
      setTimeout(() => { copyBtn.textContent = 'Kopyala'; }, 1600);
    } catch {
      copyBtn.textContent = 'Kopyalanamadı';
    }
  });

  const dl = document.createElement('span');
  dl.className = 'download-link';
  dl.textContent = 'Dosya olarak indir';
  dl.addEventListener('click', () => downloadAsFile(text));

  const ttsBtn = document.createElement('span');
  ttsBtn.className = 'download-link';
  ttsBtn.textContent = 'Sesli oku';
  ttsBtn.addEventListener('click', () => {
    if (!('speechSynthesis' in window)) return;
    if (window.speechSynthesis.speaking) {
      window.speechSynthesis.cancel();
      ttsBtn.textContent = 'Sesli oku';
      return;
    }
    const clean = String(text || '').replace(/```[\s\S]*?```/g, '').replace(/[#*|`_~]/g, ' ').slice(0, 1800);
    const utt = new SpeechSynthesisUtterance(clean);
    utt.lang = 'tr-TR';
    utt.onend = () => { ttsBtn.textContent = 'Sesli oku'; };
    utt.onerror = () => { ttsBtn.textContent = 'Sesli oku'; };
    ttsBtn.textContent = 'Durdur';
    window.speechSynthesis.speak(utt);
  });

  const promptifyBtn = document.createElement('span');
  promptifyBtn.className = 'download-link';
  promptifyBtn.textContent = 'Sohbeti Prompt Yap';
  promptifyBtn.title = 'Bu sohbet geçmişini başka yapay zeka araçlarında kullanabileceğin tek bir master prompt haline çevir';
  promptifyBtn.addEventListener('click', () => {
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
    {
      title: 'Kod, Web ve Masaüstü Proje Geliştirme',
      tag: 'IDE · Web · .EXE',
      desc: 'Çok klasörlü web sitesi, masaüstü uygulaması veya oyun oluşturun; gömülü kod editöründe canlı önizleyin, düzenleyin ve .EXE olarak derleyin.',
      prompt: 'Modern karanlık arayüzlü, arama ve filtreleme özellikli bir görev ve proje takip web uygulaması oluştur.',
    },
    {
      title: 'Doküman, Sunum ve Tablo Üretimi',
      tag: '.XLSX · .DOCX · .PPTX · .PDF',
      desc: 'İstediğiniz herhangi bir konuda formüllü ve grafikli Excel tablosu, Word raporu, PowerPoint sunumu veya Türkçe karakter uyumlu PDF oluşturun.',
      prompt: 'Aylık kişisel bütçe ve harcama takibi için formüllü, grafikli ve kategorili bir Excel (.xlsx) tablosu oluştur.',
    },
    {
      title: 'Görsel Tasarım ve Fotoğraf Düzenleme',
      tag: 'Görsel · Filtre · Tarayıcı',
      desc: 'Metin komutundan görsel, logo veya afiş üretin; yüklediğiniz fotoğrafları düzenleyin, arka planı temizleyin veya belge gölgelerini giderin.',
      prompt: 'Minimalist ve modern bir teknoloji markası için yüksek çözünürlüklü kurumsal bir logo ve görsel tasarım üret.',
    },
    {
      title: 'Dosya Analizi ve Hata Denetimi',
      tag: 'Kod · PDF · Excel · CSV',
      desc: 'Herhangi bir kod, PDF, Word, Excel, CSV veya JSON dosyası yükleyin; sözdizimi, formül ve veri hatalarını satır satır yakalayın.',
      prompt: 'Yüklediğim dosyayı satır satır incele, bulduğun tüm hataları ve iyileştirme önerilerini listele.',
      attach: true,
    },
    {
      title: 'Veri Bilimi, Tahminleme ve SQL',
      tag: 'AutoML · Grafik · SQL',
      desc: 'Veri setlerindeki trendleri ve anormallikleri analiz edin, gelecek dönem tahminleri yapın, veritabanlarını doğal dille sorgulayın.',
      prompt: '12 aylık örnek satış ve maliyet verisi üzerinden trend analizi, gelecek 3 ay tahmini ve özet grafik raporu hazırla.',
    },
    {
      title: 'Araştırma, Hukuk, Finans ve Teknik Analiz',
      tag: 'Konsey · Analiz · Rapor',
      desc: 'Sözleşme risk incelemesi, finansal değerleme, derin araştırma, akademik özetleme veya 2B/3B teknik çizim analizi yapın.',
      prompt: 'Yeni bir yazılım girişimi için 5 yıllık finansal değerleme (DCF) ve yatırım risk analizi raporu hazırla.',
    },
  ];
  els.heroCards.innerHTML = '';
  for (const c of cards) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'sp-hero-card';
    btn.innerHTML = `
      <div class="sp-hero-card-top">
        <span class="sp-hero-card-title">${c.title}</span>
        <span class="sp-hero-card-tag">${c.tag}</span>
      </div>
      <div class="sp-hero-card-desc">${c.desc}</div>
    `;
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
