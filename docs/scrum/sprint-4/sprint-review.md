# Sprint 4 — Sprint Review

| | |
|---|---|
| Sprint | 4 (19 Kasım – 2 Aralık 2026) |
| Tarih | 2 Aralık 2026 |
| Katılımcılar | İshak Bostan, Zeynep Duru Küçük, Furkan Kaan Özbeyli, Semih Sarıca, Işıl Karademir, Berfin Yiğit |
| Scrum Master | Zeynep Duru Küçük |
| Toplantı yeri | Online (Discord) + Yüz yüze sunum |

## Sprint Hedefi Değerlendirmesi

**Hedef:** Üretilen kodu gerçekten doğrulayın — sandbox'ta çalıştırın, test üretin, bağımsız ajan incelemesi yapın, dosya çakışmalarını çözün ve hataları otomatik kurtarın.

**Sonuç: Hedef tam olarak karşılandı.** 8 backlog öğesinin tamamı Definition of Done'ı geçti.

## Tamamlanan Backlog Öğeleri

| ID | Öğe | Sorumlu | Durum |
|---|---|---|---|
| PB-40 | API sözleşme kontrolü | İshak Bostan | ✅ |
| PB-41 | Sandbox test koşucusu | Furkan Kaan Özbeyli | ✅ |
| PB-42 | Test üretme + hata döngüsü | Semih Sarıca | ✅ |
| PB-43 | Kod inceleme ajanı (asla yazar değil) | Semih Sarıca | ✅ |
| PB-44 | Maks deneme + otomatik kurtarma | İshak Bostan | ✅ |
| PB-45 | Çakışma çözümü | Işıl Karademir | ✅ |
| PB-46 | Sahte ajan testleri | Zeynep Duru Küçük | ✅ |
| PB-47 | Proje sayfası güncellemeleri | Berfin Yiğit | ✅ |

## Yapılan Demo

### Demo Senaryosu 1 — Çakışma Tespiti
- T3 (backend) ve T7 (integration) aynı projede `backend/main.py` dosyasını üretti.
- Master, T7 sonucu gönderildiğinde çakışmayı otomatik tespit etti.
- `GET /api/projects/1/conflicts` → çakışma listesi API'den alındı.
- Proje sayfasında T7 satırında ⚡ rozeti göründü.

### Demo Senaryosu 2 — Maks Deneme
- Kasıtlı olarak kısa çıktı gönderildi, görev 3 kez reddedildi.
- 3. redde görev `failed` durumuna geçti (sonsuz döngü yok).
- Proje sayfasında görev `failed` rozeti ve `attempt: 3` sayısı gösterildi.

### Demo Senaryosu 3 — Kod İnceleme Yönlendirme
- Backend görevi `uye4` (Semih) tarafından tamamlandı.
- Review görevi otomatik oluşturuldu, `uye4` dışındaki ajanlara yönlendirildi.
- `uye1` (İshak) review'ü aldı ve kod inceleme raporu ürertti.

### Demo Senaryosu 4 — Sözleşme Kontrolü
- `GET /api/admin/contract-check` → 3 backend route'u frontend tarafından çağrılmıyor (eski endpoint'ler).
- `/api/perf/stats` frontend'e eklendi.

## Ürün Sahibi / Hoca Geri Bildirimleri

- Çakışma tespiti ve review yönlendirme Sprint 3'e göre büyük olgunluk adımı.
- Sprint 5'te end-to-end demo ve canlı pano önceliklendirilsin.
- Sandbox Docker kurulumu demo'da çalışması için kurulum adımları belgelenmeli.

## Metrikler

| Metrik | Değer |
|---|---|
| Planlanan / Tamamlanan öğe | 8 / 8 |
| Toplam birim testi | 150 (16 yeni) |
| Yeni modüller | conflict_detector.py, contract_check.py, perf_api.py |
| Schema versiyonu | v5 (conflicts, events) + v6 (perf_ms) |
| MAX_ATTEMPTS | 3 |
