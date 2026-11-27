# Windows + 8 GB ekran kartı: teknik uygunluk raporu

Bu makinede ölçülen durum (27.11.2026). "Ölçüldü / görüldü" dışındaki bir şey yazılmadı.

## Ortam

| Bileşen | Sürüm |
|---|---|
| İşletim sistemi | Windows 11 Pro |
| Ekran kartı | RTX 4060 Laptop, 8188 MiB, sürücü 617.42 |
| Bellek | 32 GB; WSL2 10 GB ile sınırlı (`.wslconfig`) |
| Sunucu Python'u | 3.12.10 (`master/venv`) |
| Testlerde sistem Python'u | 3.15.0 |
| Node | 26.12.0 |
| Docker | 29.9.1 |
| Ofis doğrulaması | LibreOffice 26.8 |

Ollama ayarları: `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_MAX_LOADED_MODELS=1`.
Denetlemek için: `python scripts/ai_os.py doctor`.

## 8 GB'ın anlamı

- Aynı anda tek model yüklü tutulabiliyor. Model değiştirmek yeniden yükleme demek.
- 4–6 GB'lık modeller (`qwen3.5:4b/9b`, `qwen2.5-coder:7b`, `deepseek-r1:8b`, `qwen2.5vl:7b`) karta sığıyor.
- `qwen2.5-coder:14b` (8,4 GB) ve `gemma4:e4b` (8,9 GB) karta tam sığmıyor; kalanı ana belleğe taşar ve yavaşlar.
- Tarayıcı, oyun ya da başka bir uygulama kartı kullanırken üretim belirgin biçimde yavaşlıyor.
- Uzun işler pahalı: "iki varyant" denemesi 30 dakika sürdü.

## Sorun çıkaran noktalar ve çözümü

| Konu | Görülen sorun | Uygulanan çözüm |
|---|---|---|
| OneDrive içindeki proje klasörü | Dosyalar eşitleme sırasında kısa süre kilitleniyor | Yeniden deneyen atomik yazım (`atomic_io.py`). Klasörü OneDrive dışına almak daha sağlam olur |
| Port çakışması | Önizleme portunu başka program tutabiliyor | Kimlik denetimi ve boş port kiralama |
| Alt süreçler | Zaman aşımında torun süreçler hayatta kalıyordu | Windows Job Object |
| Dil sunucusu | 1 GB sınırında açılamıyordu | Sınır 4 GB |
| Varsayılan kod sayfası | Türkçe harfler bozulabiliyor | Her yerde UTF-8 |
| NVIDIA okuma | Eski `pynvml` paketi | `nvidia-ml-py` |
| Çevrimdışı OCR | RapidOCR Türkçe harfleri kaybediyor | Açık: aşama M09 |
| Üretilen kod | Windows'ta gVisor / Firecracker yok | Docker (WSL2) + Job Object + WASM |
| Node testleri | Node Docker imajı yok | Node izin modeli + Job Object |

## Kurulmayanlar ve nedeni

- **Docling, WeasyPrint:** kurulu değil. Docling büyük bir model yığını ister; WeasyPrint Windows'ta ayrıca GTK/Pango kitaplıkları ister. PDF işleri PyMuPDF ile yapılıyor.
- **Yerel eğitim (LoRA/DPO):** 8 GB yetmiyor.
- **GBNF / logit maskesi:** Ollama bu denetimi vermiyor.

## Kurulum yolu

1. Ollama, Docker Desktop, Node ve LibreOffice kurulur.
2. `python -m venv master/venv` (3.12), ardından `master/venv/Scripts/pip install -r master/requirements.txt`.
3. `master/venv/Scripts/playwright install chromium`
4. `docker build -t platform-sandbox:latest docker/sandbox`
5. `python scripts/vendor_fetch.py` (yazı tipleri, grafik/diyagram kitaplıkları, çevrimdışı belgeler)
6. `python scripts/ai_os.py setup`, sonra `python scripts/ai_os.py up`
