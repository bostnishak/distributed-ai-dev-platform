# Sprint 2 — Sprint Retrospektifi

| | |
|---|---|
| Sprint | 2 (22 Ekim – 4 Kasım 2026) |
| Tarih | 4 Kasım 2026 |
| Katılımcılar | Tüm ekip (6 kişi) |
| Scrum Master | Zeynep Duru Küçük |
| Yöntem | Start / Stop / Continue |

## İyi Gidenler (Continue)

**Tahmin doğruluğu:** 104 saat tahmin, 104 saat gerçekleşen — sprint boyunca hiç sapma olmadı. Bu, görevlerin önceki sprintten daha iyi ayrıştırıldığını gösteriyor.

**Paralel geliştirme:** PB-21 (benchmark soruları) ve PB-23 (ağırlık vektörleri) birbirinden bağımsız olduğu için aynı anda geliştirildi; PB-22 ve PB-24 bu temeli beklemek zorunda kaldı ama bloke olmadı çünkü mock verilerle çalışabildiler.

**Seçim algoritması tasarımı:** `selection.py` test edilebilir şekilde tasarlandı (saf fonksiyonlar, dışarıdan ajan listesi ve skor geçiliyor). 14 birim testi sıfır harici bağımlılıkla çalıştı.

**Heartbeat altyapısı:** Furkan'ın heartbeat döngüsü ve lease mekanizması Sprint 3'ün görev yürütme kısmını mümkün kıldı; önceden planlanmış olması zaman kazandırdı.

**Benchmark çeşitliliği:** Semih'in 5 boyutlu benchmark seti (coding/reasoning/context/structured/speed) gerçekçi bir yetenek profili çıkardı ve seçim algoritmasına anlamlı girdi sağladı.

## İyileştirilecekler (Stop / Start)

**Stop: PR açmadan doğrudan main'e commit atmak.**
Lint fix'leri için bile PR açılmalı; admin bypass'ı sadece gerçekten acil durumlarda kullanılmalı. Bu sprint'te birkaç küçük düzeltme doğrudan atıldı.

**Stop: Merge conflict'leri geç keşfetmek.**
Sprint 1 dokümantasyon branchi merge edilmemiş kalmıştı; sprint 2 sonunda PR açılınca conflict çıktı. Her sprint başında açık dallar kapatılmalı.

**Start: Her PR'da en az bir review.**
Bu sprint'te bazı PR'lar tek kişi tarafından merge edildi. Küçük değişiklik de olsa bir başkasının gözünden geçmesi hataları erken yakalar.

**Start: Benchmark sonuçlarını görselleştirme testleri.**
Puan çubukları tarayıcıda test edildi ama birim testine girmedi. Frontend bileşenleri için basit smoke test eklenebilir.

## Aksiyon Maddeleri

| # | Aksiyon | Sorumlu | Hedef Sprint |
|---|---|---|---|
| A1 | Her PR için en az 1 reviewer zorunlu hale getirilsin (branch protection güncellensin) | İshak | Sprint 3 başı |
| A2 | Sprint başında açık dal kontrolü gündemine alınsın (Daily Scrum) | Duru (Scrum Master) | Her sprint |
| A3 | Lint hataları CI'da bitmeden PR merge edilemesin | Furkan | Sprint 3 başı (CI değişikliği) |

## Takım Memnuniyet Puanı

Her üye 1–5 arası bir sprint memnuniyet puanı verdi:

| Üye | Puan |
|---|---|
| İshak Bostan | 4 |
| Zeynep Duru Küçük | 5 |
| Furkan Kaan Özbeyli | 4 |
| Semih Sarıca | 4 |
| Işıl Karademir | 5 |
| Berfin Yiğit | 4 |
| **Ortalama** | **4.3 / 5** |

Düşük puan nedeni olarak belirtilen: "Sprint 2 sonuna doğru birkaç lint düzeltmesinin CI'ı bozması stres yarattı."

## Sprint 3 için Taşınan Öğrenmeler

1. Görev tipleri için ağırlık vektörlerinin önceden tanımlanması seçim algoritmasını çok kolaylaştırdı — Sprint 3'te de benzer şekilde gereksinimleri önce veri modeline dökmek faydalı olacak.
2. `asyncio.gather` ile concurrent döngüler yönetilebilir — Sprint 3 DAG scheduler'ı aynı pattern'ı kullanacak.
3. Özellik bağımlılıkları (benchmark → selection, heartbeat → task pull) Sprint 1'de tanımlanmış olsaydı paralelleme daha kolay olurdu.
