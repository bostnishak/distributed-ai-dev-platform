# Sprint 4 — Sprint Retrospektifi

| | |
|---|---|
| Sprint | 4 (19 Kasım – 2 Aralık 2026) |
| Tarih | 2 Aralık 2026 |
| Katılımcılar | Tüm ekip (6 kişi) |
| Scrum Master | Zeynep Duru Küçük |
| Yöntem | Start / Stop / Continue |

## İyi Gidenler (Continue)

**Modüler tasarım korundu.** `conflict_detector.py` ve `contract_check.py` tamamen bağımsız modüller olarak yazıldı; mevcut test'lerin hiçbirini bozmadı. 150 testin tamamı geçti.

**Sahte ajan testleri güçlü çıktı.** `test_sprint4.py` gerçek DB (tmp_path ile izole) kullanarak entegrasyon senaryolarını kapsıyor; mock sayısı sıfır. Bu Sprint 3'teki "doğrulama yüzeysel" sorununu aşıyor.

**PB-44 en hızlı biten öğe oldu.** `MAX_ATTEMPTS = 3` ve `requeue_task()` değişikliği 2 saatte tamamlandı; tek bir satır bile test başarısızlığına yol açmadı. Küçük, odaklı değişikliklerin gücü.

**Review yönlendirme temiz çalıştı.** `exclude_agent_id` parametresi `select_agent()`'e eklenmesi, PB-43'ü 4 satıra indirdi ve mevcut seçim mantığını hiç kırmadı.

## İyileştirilecekler (Stop / Start)

**Stop: Sandbox Docker kurulumunu dökümansız bırakmak.**
Furkan'ın sandbox'ı demo'da çalıştırmak için Docker Desktop'ın açık olması gerekiyor; bu durum demo sırasında keşfedildi. Kurulum ön koşulları README'ye eklenmeli.

**Stop: PR açıklamalarına "Sprint X" etiketinden fazlasını yazmamak.**
Birkaç PR'da değişikliğin motivasyonu (neden MAX_ATTEMPTS = 3, neden 30 saniye değil 300 saniye) eksikti. Reviewer'lar "neden" sorusuna cevap bulamadı.

**Start: Conflict detection sonuçlarını UI'a daha belirgin yansıtmak.**
Şu an ⚡ rozeti var ama çakışmanın ne olduğunu görmek için API çağrısı gerekiyor. Sprint 5'te proje detay sayfasına inline çakışma açıklaması eklenmeli.

**Start: `e2e_test.py` gibi uçtan uca smoke test.**
Sprint 4 boyunca hiç gerçek akış testi yapılmadı; her şey birim test seviyesinde kaldı. Sprint 5'te demo provası sırasında bir script çalıştırılabilmeli.

## Aksiyon Maddeleri

| # | Aksiyon | Sorumlu | Hedef Sprint |
|---|---|---|---|
| A7 | Docker sandbox kurulum adımları README'ye eklensin | Furkan | Sprint 5 başı |
| A8 | Proje detay sayfasına inline çakışma mesajı eklenmeli | Berfin | Sprint 5 |
| A9 | `e2e_test.py` smoke script yazılsın | İshak | Sprint 5 |

Sprint 3'ten taşınan aksiyonlar (A4–A6) tamamlandı:
- A4 ✅ WebSocket yerli proje için tartışıldı; polling → push Sprint 5'e taşındı (PB-51 dashboard'da uygulandı)
- A5 ✅ MAX_ATTEMPTS = 3 ile başarısız görev işaretleme (PB-44)
- A6 ✅ Kayıt sırasında Ollama model varlık kontrolü (PB-56 kapsamında değerlendirildi)

## Takım Memnuniyet Puanı

| Üye | Puan |
|---|---|
| İshak Bostan | 4 |
| Zeynep Duru Küçük | 5 |
| Furkan Kaan Özbeyli | 4 |
| Semih Sarıca | 5 |
| Işıl Karademir | 4 |
| Berfin Yiğit | 5 |
| **Ortalama** | **4.5 / 5** |

Furkan ve Işıl 4 verdi: "Sandbox Docker bağımlılığı ve çakışma UI'ı bitiremeyelim derdi biraz stres yarattı."

## Sprint 5 için Taşınan Öğrenmeler

1. Küçük, bağımsız değişiklikler (PB-44) büyük özelliklerden (PB-41) daha hızlı teslim edilir; backlog'u daha ince dilimlemek faydalı.
2. `exclude_agent_id` gibi opsiyonel parametreler mevcut kodu kırmadan yeni davranış ekler — bu pattern Sprint 5'te de kullanılabilir.
3. Demo öncesi Docker ortamı checklist'i şart; ortam kurulumunu asla "herkes bilir" diye atlama.
