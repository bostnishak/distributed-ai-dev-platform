# Sprint 5 — Sprint Review

| | |
|---|---|
| Sprint | 5 (3 Aralık – 16 Aralık 2026) |
| Tarih | 16 Aralık 2026 |
| Katılımcılar | İshak Bostan, Zeynep Duru Küçük, Furkan Kaan Özbeyli, Semih Sarıca, Işıl Karademir, Berfin Yiğit |
| Scrum Master | Zeynep Duru Küçük |
| Toplantı yeri | Online (Discord) + Son sunum |

## Sprint Hedefi Değerlendirmesi

**Hedef:** Platformu uçtan uca sertleştirin ve demo hazır hale getirin — canlı pano, performans ölçümü, model karşılaştırma, güvenlik ve son belgeleme.

**Sonuç: Hedef tam olarak karşılandı.** 7 backlog öğesinin tamamı Definition of Done'ı geçti.

## Tamamlanan Backlog Öğeleri

| ID | Öğe | Sorumlu | Durum |
|---|---|---|---|
| PB-50 | Uçtan uca iş akışı sertleştirme | İshak Bostan | ✅ |
| PB-51 | Pano: genel bakış + canlı olay akışı | Berfin Yiğit | ✅ |
| PB-52 | Performans ölçümleri | Zeynep Duru Küçük | ✅ |
| PB-53 | Ajan / model karşılaştırma görünümü | Berfin Yiğit | ✅ |
| PB-54 | Son belgeleme ve kullanıcı rehberi | Işıl Karademir | ✅ |
| PB-55 | Son testler ve demo provası | Semih Sarıca | ✅ |
| PB-56 | Güvenlik sertleştirme | Furkan Kaan Özbeyli | ✅ |

## Yapılan Demo

### Demo Senaryosu 1 — Uçtan Uca Tam Akış
1. `uvicorn master.app:app` ve `python start_agents.py` başlatıldı.
2. Pano'da (◈ Pano sekmesi) 6 ajan çevrimiçi, modelleri farklı görüldü.
3. "Kütüphane Yönetim Sistemi" SRS belgesi yüklendi.
4. 15 görev otomatik oluşturuldu; DAG planlayıcı T1–T2'yi hemen, T3–T11'i T2 bittikten sonra açtı.
5. Ajanlar görevleri paralel çalıştırdı; pano canlı güncellendi.
6. ZIP indirildi: `backend/main.py`, `frontend/index.html`, `docs/README.md` ve diğerleri.

### Demo Senaryosu 2 — Hata Kurtarma
- `uye3` (Furkan) demo sırasında durduruldu.
- 5 dakika sonra `uye3`'ün kiralık görevi `uye1`'e yeniden atandı.
- Hiçbir manuel müdahale gerekmedi; pano "task_assigned" olayını kayıt altına aldı.

### Demo Senaryosu 3 — Pano ve Performans
- Pano sekmesi: ajan sayıları, proje durumu, son 20 olay.
- Performans istatistikleri: `backend` görevleri ort. 47 s, `documentation` görevleri ort. 18 s.
- Model karşılaştırma: `gemma2:9b` (Semih) `coding` boyutunda en yüksek skor.

### Demo Senaryosu 4 — Güvenlik
- Master yalnızca `127.0.0.1:8000`'e bağlandı; dışarıdan erişim denemesi reddedildi.
- Tailscale aracılığıyla diğer bilgisayarlardan `uye2–uye6` ajanları bağlandı.
- `AGENT_TOKEN` olmadan gönderilen heartbeat → 401 Unauthorized.

## Ürün Sahibi / Hoca Geri Bildirimleri

- Beş sprint boyunca gereksinimlerin %100'ü teslim edildi; sıfır borç.
- Pano ve performans metrikleri akademik rapor için değerli veri.
- Tailscale + localhost güvenlik modeli pragmatik ve yeterli.
- Öneri: gelecek projede WebSocket push ilk sprintten planlanabilir.

## Metrikler

| Metrik | Değer |
|---|---|
| Planlanan / Tamamlanan öğe | 7 / 7 |
| Toplam sprint sayısı | 5 |
| Toplam birim testi | 162 |
| Toplam backlog öğesi teslim edildi | 40 (PB-01 → PB-56, PB-14 hariç) |
| End-to-end çalışma sayısı | 5 |
| Dashboard refresh | 10 s |
| Desteklenen görev tipi | 7 |
| Desteklenen model | 6 |
