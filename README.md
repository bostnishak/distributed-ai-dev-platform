# Çoklu-LLM Orkestrasyon Sistemi

Ensar Gül DevOps dersi grup projesi. ChatGPT benzeri bir sohbet arayüzünden bir istem geldiğinde **orkestratör** ("ana AI"), görevi otomatik olarak en nitelikli açık kaynak **alt-AI**'ye yönlendirir ve sonucu döner — kullanıcı hangi modelin cevap vereceğini seçmez.

## Özellikler

- **Otomatik görev yönlendirme** — mesaj içeriğine göre (kod / genel soru-cevap) doğru modele otomatik gider
- **ChatGPT tarzı sohbet arayüzü** — Markdown render (başlık, madde işareti, kod bloğu), sohbet geçmişi (localStorage, silinebilir/devam edilebilir)
- **Dosya yükleme** — PDF, DOCX, TXT dosyaları gerçekten okunup metne çevrilir; görsel yüklenirse (henüz vision modeli olmadığı için) dürüstçe bilgi verir, uydurmaz
- **Bağlama duyarlı içerik denetimi** — basit kelime listesi değil, bağlamı anlayan bir LLM kontrolü (ör. "mal" kelimesi ticari/hakaret anlamına göre ayrılır); belirsiz durumlarda yanlışlıkla engellemek yerine geçirmeyi tercih eder ("fail-open")
- **Cevabı dosya olarak indirme**

## Temel ilkeler

- **%100 lokal, veri gizliliği önceliği.** Sistem hiçbir bulut/harici API'ye veri göndermez — tüm modeller ekip üyelerinin kendi bilgisayarlarında (Ollama ile) çalışır. Bulut LLM API'si (Groq/Gemini/OpenRouter) **kullanılmıyor**.
- **Eğitim/fine-tuning yok.** Sadece hazır (pretrained), açık kaynak modellerle inference yapılır.

## Ekip ve modeller (doğrulandı, 2026-09-25)

| Kim | Model | Şirket | Otomatik yönlendirmede rolü |
|---|---|---|---|
| İshak Bostan (Üye-1, orkestratör + gateway de burada) | Qwen3.5 4B | Alibaba | Genel soru-cevap + sınıflandırıcı |
| Duru Küçük (Üye-2) | Phi-4-mini (3.8B) | Microsoft | *(bağlı, henüz otomatik yönlendirmede kullanılmıyor)* |
| Furkan Kaan (Üye-3) | Llama 3.2 3B | Meta | *(bağlı, henüz otomatik yönlendirmede kullanılmıyor)* |
| Semih Sarıca (Üye-4) | Gemma 4 E4B | Google | *(bağlı, henüz otomatik yönlendirmede kullanılmıyor)* |
| Işıl Karademir (Üye-5) | Qwen2.5-Coder 7B | Alibaba | Kod/uygulama üretimi |
| Berfin Yiğit (Üye-6) | Qwen3 1.7B | Alibaba | *(bağlı, henüz otomatik yönlendirmede kullanılmıyor)* |

5 genel amaçlı model arasında net bir kalite farkı olmadığı için (fan-out + yerel hakem yerine) bilinçli olarak basit/hızlı bir yaklaşım seçildi: genel sorular hep Üye-1'e gider. Diğer 4 model gateway'e bağlı ve hazır durumda, ileride farklı bir göreve atanabilir.

## Durum (2026-09-25 itibarıyla)

**Çalışıyor ve test edildi:**
- 6/6 model gateway üzerinden doğrulandı
- Otomatik yönlendirme: kod istekleri → Qwen2.5-Coder (gerçek, çalışan kod üretiyor), genel sorular → Qwen3.5
- PDF/DOCX/TXT yükleme gerçekten okunuyor (hızlı, birkaç saniye)
- Tam Docker Compose kurulumu (gateway + orkestratör) uçtan uca test edildi
- 17 otomatik birim testi (`orchestrator/tests/`) geçiyor, CI'da çalışıyor

**Bilinen sınırlamalar (küçük yerel modellerin doğal sınırı, "hata" değil):**
- Sınıflandırma %100 değil — nadiren belirsiz mesajlar yanlış kategoriye gidebilir (anahtar kelime güvenlik ağıyla kısmen azaltıldı)
- İçerik denetimi tutarsız olabilir (aynı mesaj farklı çalıştırmalarda farklı sonuç verebilir) — bilinçli olarak "yanlışlıkla engellemek yerine geçir" şeklinde tasarlandı
- Gerçek görsel (fotoğraf) analizi yok — veri gizliliği kararıyla bulut vision API'leri kullanılmıyor, yerel bir vision modeli (ör. Moondream2) henüz eklenmedi

## Hızlı başlangıç

```bash
# .env dosyanizi olusturun (ornek: .env.example) ve LITELLM_MASTER_KEY'i doldurun

# Tum sistemi (gateway + orkestrator) tek komutla ayaga kaldirir:
docker compose up -d --build

# Tarayicida acin:
# http://localhost:8000
```

Aktif geliştirme yaparken (her değişiklikte image yeniden build etmek yerine) orkestratörü doğrudan çalıştırmak daha hızlıdır:

```bash
cd gateway && docker compose up -d && cd ..
cd orchestrator
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m uvicorn app:app --port 8000
```

### Testleri çalıştırma

```bash
cd orchestrator
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest tests/ -v
.venv\Scripts\python -m ruff check .
```

## Mimari (özet)

```
Kullanıcı (tarayıcı) → Orkestratör (FastAPI, Docker) → LiteLLM Gateway (Docker) → 6 üyenin Ollama'sı (lokal)
```

Her üye kendi bilgisayarında farklı bir açık kaynak modeli (Ollama ile) çalıştırır. Tüm modeller tek bir LiteLLM Gateway arkasında birleşir — bulut bileşeni yok.

## Klasörler

- `/gateway` — LiteLLM Gateway config'i
- `/orchestrator` — FastAPI orkestratör uygulaması + sohbet arayüzü (`static/`) + testler (`tests/`)
- `/agent-node` — her üyenin kendi makinesinde çalıştıracağı kurulum script'i

## Katkıda bulunma

Branch/PR akışı için [CONTRIBUTING.md](CONTRIBUTING.md)'ye bakın.
