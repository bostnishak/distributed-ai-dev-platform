# Kullanım Kılavuzu — Dağıtık YZ Yazılım Geliştirme Platformu

## Giriş

Bu platform bir yazılım gereksinim dokümanını (SRS) alır, onu görevlere ayırır ve takım üyelerinin bilgisayarında çalışan YZ ajanlarına dağıtır. Sonuç: indirilebilir bir yazılım projesi ZIP dosyası.

> **Veriler bilgisayarlarınızdan çıkmaz.** Tüm model çağrıları Tailscale ağı üzerinden lokal Ollama sunucularına gider.

---

## Hızlı Başlangıç

### 1. Depoyu klonlayın

```bash
git clone https://github.com/bostnishak/distributed-ai-dev-platform.git
cd distributed-ai-dev-platform
```

### 2. `.env` dosyasını oluşturun

```bash
cp .env.example .env
# .env içinde AGENT_TOKEN değerini değiştirin
```

Minimum `.env` içeriği:
```
AGENT_TOKEN=güvenli-bir-token-buraya
```

### 3. Master sunucusunu başlatın

```bash
cd master
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Ajanları başlatın

Kendi bilgisayarınızda:
```bash
python start_agents.py
```

Diğer ekip üyeleri kendi bilgisayarlarında aynı komutu çalıştırır (Tailscale ile bağlı olmaları gerekir).

### 5. Tarayıcıda açın

```
http://127.0.0.1:8000
```

---

## Proje Oluşturma

1. Sol menüden **+ Yeni Proje** sekmesine tıklayın.
2. **Proje adı** alanına projenin adını girin (örn. `Kütüphane Yönetim Sistemi`).
3. **Gereksinim dokümanı** bölümünde:
   - `Metin yapıştır` sekmesinden SRS metnini yapıştırın, **veya**
   - `Dosya yükle` sekmesinden `.txt`, `.md`, `.pdf` veya `.docx` dosyası seçin.
4. **Analiz et** butonuna tıklayın.

Master ajan dokümanı analiz ederek DAG (Yönlü Döngüsüz Graf) biçiminde görev planı oluşturur. Bu işlem ~30–90 saniye sürer.

---

## Görev Yürütmeyi İzleme

**Projeler** sekmesinden projeye tıklayın. Proje detay sayfasında:

| Durum rozeti | Anlam |
|---|---|
| `planlandı` | Görev hazır, bir ajan çekecek |
| `⟳ ... çalışıyor` | Ajan görevi işliyor |
| `tamamlandı` | Çıktı doğrulandı |
| `başarısız` | 3 denemede başarısız oldu (kalıcı) |
| `! doğrulama hatası` | Çıktı formatı geçersiz |
| `↻N` | N. deneme (sarı) |
| `⚡ çakışma` | Başka bir görevle aynı dosyayı üretti |

Görevler bağımlılıklarına göre sıralanır. T1 ve T2 tamamlanmadan T3 başlamaz.

**Pano** sekmesinde canlı ajan durumları ve son olaylar görüntülenir (10 saniyede bir güncellenir).

---

## ZIP İndirme

Projedeki tüm görevler tamamlandığında proje detay sayfasında **ZIP İndir** butonu etkinleşir. İndirilen arşivde:

```
backend/
  main.py
  models.py
frontend/
  index.html
  app.js
docs/
  README.md
tests/
  test_backend.py
```

---

## Ajan Yönetimi

**Ajanlar** sekmesinde kayıtlı tüm ajanlar listelenir:

- **Çevrimiçi / Çevrimdışı**: Son heartbeat 5 dakikadan eskiyse çevrimdışı.
- **Meşgul**: Şu anda bir görevi işliyor.
- **Yeniden Değerlendir**: Ajanın model puanlarını güncel benchmark'larla yeniden hesaplar.

---

## Güvenlik Notları

- Master sunucu varsayılan olarak yalnızca `127.0.0.1:8000`'e bağlanır. Dış erişim için `HOST=0.0.0.0` ortam değişkeni gerekir.
- Ajan istekleri `AGENT_TOKEN` Bearer token ile doğrulanır. Yanlış token → `401 Unauthorized`.
- Tailscale ile ekip üyeleri birbirinin master sunucusuna güvenli tünel üzerinden bağlanabilir.

---

## Sorun Giderme

| Sorun | Çözüm |
|---|---|
| "Master modeline ulaşılamıyor" | Ollama'yı başlatın: `ollama serve` |
| Ajanlar çevrimdışı görünüyor | `start_agents.py`'ı yeniden çalıştırın |
| Görev "başarısız" durumunda | Proje sayfasında görevin çıktısını kontrol edin, gerekirse **Yeniden analiz et** |
| PORT çakışması | `uvicorn ... --port 8001` ile farklı port kullanın |
