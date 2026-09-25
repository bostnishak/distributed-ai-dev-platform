# Çoklu-LLM Orkestrasyon Sistemi

Ensar Gül DevOps dersi grup projesi. Bir istem geldiğinde **orkestratör** ("ana AI"), görevi en nitelikli açık kaynak **alt-AI**'ye yönlendirir ve sonucu döner. Desteklenen görevler: belge/dosya analizi (PDF, DOCX, görsel), genel soru-cevap, kod/uygulama üretimi.

## Temel ilkeler

- **%100 lokal, veri gizliliği önceliği.** Sistem hiçbir bulut/harici API'ye veri göndermez — tüm modeller ekip üyelerinin kendi bilgisayarlarında (Ollama ile) çalışır. Bulut LLM API'si (Groq/Gemini/OpenRouter) **kullanılmıyor**.
- **Eğitim/fine-tuning yok.** Sadece hazır (pretrained), açık kaynak modellerle inference yapılır.

## Ekip ve modeller (doğrulandı, 2026-09-25)

| Kim | Model | Şirket |
|---|---|---|
| İshak Bostan (Üye-1, orkestratör + gateway de burada) | Qwen3.5 4B | Alibaba |
| Duru Küçük (Üye-2) | Phi-4-mini (3.8B) | Microsoft |
| Furkan Kaan (Üye-3) | Llama 3.2 3B | Meta |
| Semih Sarıca (Üye-4) | Gemma 4 E4B | Google |
| Işıl Karademir (Üye-5) | Qwen2.5-Coder 7B (kod uzmanı) | Alibaba |
| Berfin Yiğit (Üye-6) | Qwen3 1.7B (en hafif) | Alibaba |

## Durum

**Çalışıyor (uçtan uca test edildi, 2026-09-25):** Tüm 6 model gateway üzerinden doğrulandı. Orkestratörün görev yönlendirmesi de test edildi: "kod" görevi → Qwen2.5-Coder, doğru Python kodu döndürdü.

**Şu an geçici olarak:** Üye-2..6'nın modelleri, arkadaşlar kendi makinelerinde kurulumu tamamlayıp gateway'e bağlandığını İshak doğrulayana kadar İshak'ın makinesinde de (staging/referans olarak) çalışıyor. Her biri kendi makinesinde doğrulandıkça oradan silinecek.

**Henüz yok:**
- Belge/görsel analizi için gerçek bir vision modeli (planda bulut/Gemini vardı, gizlilik kararıyla kaldırıldı — yerine lokal bir vision modeli, ör. Moondream2, eklenmesi gerekiyor)
- `analiz` görev tipi şu an sadece metin işleyebiliyor, gerçek PDF/görsel işleyemiyor

## Yerel geliştirme (şu an nasıl çalışıyor)

```bash
# 1) Gateway (Docker)
cd gateway
docker compose up -d

# 2) Orkestratör
cd ../orchestrator
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app:app --port 8000

# 3) Test
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"prompt\": \"merhaba\", \"task_type\": \"genel\"}"
```

## Mimari (özet)

```
Kullanıcı → Orkestratör (FastAPI) → LiteLLM Gateway → 6 üyenin Ollama'sı (farklı açık kaynak model, hepsi lokal)
```

Her üye kendi bilgisayarında farklı bir açık kaynak modeli (Ollama ile) çalıştırır. Tüm modeller tek bir LiteLLM Gateway arkasında birleşir — bulut bileşeni yok.

## Klasörler

- `/gateway` — LiteLLM Gateway config'i
- `/orchestrator` — FastAPI orkestratör uygulaması
- `/agent-node` — her üyenin kendi makinesinde çalıştıracağı kurulum script'i

## Katkıda bulunma

Branch/PR akışı için [CONTRIBUTING.md](CONTRIBUTING.md)'ye bakın.
