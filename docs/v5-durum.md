# v5.0 durumu

Şartnamenin 16 aşaması sırayla yapılıyor. Bir aşama, kod testi ve canlı kanıtı geçmeden "tamam" sayılmaz.

| Aşama | Konu | Durum | Kanıt |
|---|---|---|---|
| 01 | Windows dayanıklılığı ve çürümeye karşı çekirdek | tamam | `tests/test_v5_m01_windows.py`, `python scripts/verify_milestone_01.py` (5/5) |
| 02 | Hile engeli ve değişmez test kehaneti | tamam | `tests/test_v5_m02_anticheat.py`, `python scripts/verify_milestone_02.py` (4/4) |
| 03 | Canlı kanıt çalıştırıcısı | bekliyor | |
| 04 | Küçük model destekleri | bekliyor | |
| 05 | Ajan sürüsü yönetimi | bekliyor | |
| 06 | Gerçek dünya zorlama testleri | bekliyor | |
| 07 | Mimari sağlık ve erişilebilirlik | bekliyor | |
| 08 | Çevrimdışı varlık kasası | bekliyor (dosyalar indirildi: `scripts/vendor_fetch.py`) | |
| 09 | Çoklu ortam alımı | bekliyor | |
| 10 | Araştırma sertleştirme | bekliyor | |
| 11 | Çok alanlı doğrulama sertleştirme | bekliyor | |
| 12 | Canlı belge ve taşınabilir paket | bekliyor | |
| 13 | Yedekleme ve geri yükleme | bekliyor | |
| 14 | Arayüz ve donanım göstergesi | bekliyor | |
| 15 | Uzun süreli dayanıklılık testi | bekliyor | |
| 16 | Son istemler ve sertifikasyon | bekliyor | |

## 01 aşamasında denenemeyen

- Bilgisayarın gerçekten uykuya girip uyanması denenmedi; saat sıçraması algılaması yalnız birim testiyle doğrulandı.
- Ekran kartının 82 °C sınırında beklemesi gerçek ısıyla değil, test verisiyle doğrulandı.

## 02 aşamasının sınırları

- Teslim "tamamlandı" sayılmak için çalıştırılabilir test ister. Tek sayfalık web projelerinde test olmadığından sonuç şimdilik hep "kanıt eksik" olur; 3. ve 6. aşamalar gerçek kullanıcı yolculuğu testleri ekleyecek.
- Test kehaneti klasörü (`.ai-os/oracles/`) onarımlara kapalı; ama henüz hiçbir ajan oraya kendiliğinden kehanet yazmıyor (3. aşama).
- Kaçamak denetimi bilinen kalıpları arar; her türlü uydurmayı yakalayamaz.
- Proje klasörü OneDrive içinde olduğu için dosyalar zaman zaman eşitleme tarafından kilitleniyor.
