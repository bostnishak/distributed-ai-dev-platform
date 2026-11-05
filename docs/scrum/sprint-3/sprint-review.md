# Sprint 3 — Sprint Review

| | |
|---|---|
| Sprint | 3 (5 Kasım – 18 Kasım 2026) |
| Tarih | 5 Kasım 2026 (erken checkpoint — tüm öğeler tamamlandı) |
| Katılımcılar | İshak Bostan, Zeynep Duru Küçük, Furkan Kaan Özbeyli, Semih Sarıca, Işıl Karademir, Berfin Yiğit |
| Scrum Master | Zeynep Duru Küçük |
| Toplantı yeri | Online (Discord) + Yüz yüze sunum |

## Sprint Hedefi Değerlendirmesi

**Hedef:** Platforma uçtan uca görev yürütme kazandırmak — ajanlar gerçek kod üretmeli, master çıktıyı doğrulamalı, DAG planlayıcı bağımlı görevleri otomatik açmalı, tamamlanan dosyalar ZIP olarak indirilebilmeli ve arayüz canlı ilerleme göstermeli.

**Sonuç: Hedef tam olarak karşılandı.** 8 backlog öğesinin tamamı Definition of Done'ı geçti.

## Tamamlanan Backlog Öğeleri

| ID | Öğe | Sorumlu | Durum |
|---|---|---|---|
| PB-30 | Gerçek görev yürütme — tür-duyarlı promptlar | İshak Bostan | ✅ |
| PB-31 | Sonuç protokolü v2 (files[], cancel) | Işıl Karademir | ✅ |
| PB-32 | ZIP çıktı indirme | Zeynep Duru Küçük | ✅ |
| PB-33 | Çıktı doğrulama + dosya çıkarma | Semih Sarıca | ✅ |
| PB-34 | DAG planlayıcı | İshak Bostan | ✅ |
| PB-35 | Canlı proje detay arayüzü | Furkan Kaan Özbeyli | ✅ |
| PB-36 | Görsel yönlendirme | Berfin Yiğit | ✅ |
| PB-37 | LiteLLM gateway kaldırma | Işıl Karademir / Berfin Yiğit | ✅ |

Tamamlanmayan öğe: **Yok.**

## Yapılan Demo

Demo, `localhost:8000` üzerinde canlı platform ile gerçekleştirildi.

### Demo Senaryosu 1 — Uçtan Uca Çalışma
1. "Kütüphane Yönetim Sistemi" gereksinim dokümanı platforma yüklendi.
2. Master, dokümanı analiz ederek 15 göreve böldü (7 varlık, 12 API ucu, 9 sayfa).
3. 6 ajan başlatıldı — her birinin farklı bir model (phi4-mini, llama3.2:3b, gemma2:9b, qwen2.5:7b, qwen3.1:7b, qwen3.5:4b) çalıştırdığı gösterildi.
4. Master, görev tiplerine göre farklı ajanları seçti (backend→Semih, frontend→İshak, testing→Duru, documentation→Berfin).
5. Ajanlar görevleri paralel yürüttü; proje detay sayfasındaki progress bar ve ajan rozetleri canlı güncellendi.

### Demo Senaryosu 2 — DAG Planlayıcı
- T1 (gereksinim) ve T2 (veritabanı) tamamlandı.
- Bağımlı T3–T11 (backend + frontend) otomatik olarak "blocked" → "planned" durumuna geçti.
- T12–T15 (testing, review, integration, documentation) T3–T11 bitmeden "blocked" kaldı.
- Planlayıcının 60 saniyelik arka plan döngüsü gösterildi.

### Demo Senaryosu 3 — Doğrulama
- Kasıtlı olarak kısa (< 20 karakter) bir çıktı gönderildi → görev reddedildi, kuyruğa geri döndü.
- Sözdizimi hatalı Python bloğu gönderildi → AST parse hatası yakalandı, `validation_status = failed`.
- Geçerli bir Python fonksiyonu gönderildi → `done` olarak işaretlendi, `files` alanı dolduruldu.

### Demo Senaryosu 4 — ZIP İndirme
- Tamamlanan görevlerin çıktıları "Çıktıları İndir (.zip)" butonuyla indirildi.
- ZIP içeriği: backend/main.py, frontend/index.html, docs/README.md gibi dosyalar.

## Ürün Sahibi / Hoca Geri Bildirimleri

- Uçtan uca akış (gereksinim → görev → ajan → kod → ZIP) açıkça gözlemlenebildi.
- LiteLLM'in kaldırılması deployment'ı basitleştirdi; tek servis (Ollama) yeterli.
- Sprint 4 önerisi: LLM tabanlı kod incelemesi (validation'ı derinleştirme) ve WebSocket push (5 saniyelik polling yerine).
- Görsel yönlendirme (image → vision-capable agent routing) Sprint 4'te genişletilebilir.

## Backlog Güncellemeleri

Sprint 4 için önerilen öğeler:
- **PB-40:** LLM tabanlı kod incelemesi (AST yerine model ile review)
- **PB-41:** WebSocket push bildirimler (polling kaldırma)
- **PB-42:** ZIP çıktısını çalıştırılabilir proje yapısına dönüştürme
- **PB-43:** Çoklu ajan paralel yürütme (aynı proje, farklı ajanlar eşzamanlı)

## Metrikler

| Metrik | Değer |
|---|---|
| Planlanan / Tamamlanan öğe | 8 / 8 |
| Tahmini / Gerçekleşen süre | 102 h / 102 h |
| Toplam birim testi | 134 (22 yeni) |
| Yeni modüller | scheduler.py, validation.py, output\_api.py, task\_prompts.py |
| Schema versiyonu | v4 (files, validation\_status, validation\_message, attempt sütunları eklendi) |
| Desteklenen görev tipi | 7 (database, backend, frontend, testing, review, integration, documentation) |
