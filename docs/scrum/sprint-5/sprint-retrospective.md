# Sprint 5 — Sprint Retrospektifi

| | |
|---|---|
| Sprint | 5 (3 Aralık – 16 Aralık 2026) |
| Tarih | 16 Aralık 2026 |
| Katılımcılar | Tüm ekip (6 kişi) |
| Scrum Master | Zeynep Duru Küçük |
| Yöntem | Start / Stop / Continue |

## İyi Gidenler (Continue)

**Pano ilk sprintten sonra en çok "vay be" duyduğumuz özellik.** `dashboard.js` tek dosyada yazıldı ve mevcut `api()` / `h()` yardımcılarını yeniden kullanarak sıfırdan gereksiz bağımlılık eklenmedi. 10 saniyelik auto-refresh `ctx.poll` mekanizmasını zaten varolan rotadan aldı.

**`perf_ms` ölçümü beklentimizden değerli çıktı.** `backend` görevlerinin documentation görevlerinden ~2.5x daha yavaş olduğunu sayısal olarak gördük; bu Sprint 1'de "ajanlar eşit zaman alır" varsayımını çürüttü.

**Demo provası sorun buldu.** Semih'in demo prova scripti, `uye3`'ün durdurulduğu senaryoda lease expiry döngüsünün 5 dakika yerine 6 dakika geçmesini beklediğini ortaya çıkardı (saat senkronizasyonu). Prova olmasaydı demo'da paniklenirdi.

**`e2e_test.py` smoke script çok işe yaradı (A9).** İshak'ın smoke script'i CI'a eklenebilecek kadar hızlı; sadece mock değil gerçek FastAPI test istemcisi kullanıyor.

## İyileştirilecekler (Stop / Start)

**Stop: Güvenlik ayarlarını son sprint'e bırakmak.**
`HOST = 0.0.0.0` varsayılanı Sprint 1'den beri kod tabanında duruyordu; 5 sprint boyunca fark edilmedi. Güvenlik öğeleri her sprintte backlog'da olmalı, yalnızca final sprint'te değil.

**Stop: Belgeleme sprint'in son günlerine sıkıştırılması.**
Işıl, `docs/user-guide.md`'yi son 2 günde yazdı. Belgeleme her sprint'te ilgili özellikle eş zamanlı yazılmalı.

**Start: Performans regresyon testi.**
`perf_ms` artık kaydediliyor ama CI'da "bu görev tipi şu sprintten X ms daha yavaşladı" uyarısı yok. Bir sonraki projede performans eşiği CI'a eklenebilir.

**Start: Her sprint'te deployment testi.**
`docker compose up` test edilmedi; CI yalnızca pytest çalıştırıyor. Docker Compose ile uçtan uca entegrasyon testi eklenebilir.

## Proje Kapanış Değerlendirmesi

5 sprint, 40 backlog öğesi, 162 test, 5 uçtan uca çalışma. Platformun Product Goal'ı karşıladığı kanıtlandı: bir gereksinim belgesi girdi, platform onu görevlere ayırdı, ajanlar kodu ürettiler, master doğruladı ve ZIP olarak teslim etti — hiçbir veri bilgisayarlarımızın dışına çıkmadan.

## Takım Memnuniyet Puanı

| Üye | Puan |
|---|---|
| İshak Bostan | 5 |
| Zeynep Duru Küçük | 5 |
| Furkan Kaan Özbeyli | 5 |
| Semih Sarıca | 5 |
| Işıl Karademir | 5 |
| Berfin Yiğit | 5 |
| **Ortalama** | **5.0 / 5** |

Proje kapanış sprintinde herkes tam puan verdi. Genel görüş: "Gerçekten çalışan, demo edilebilir bir şey yaptık."

## Öğrenmeler — Tüm Proje

1. **Küçük, bağımsız PR'lar sürekli teslimi mümkün kıldı.** Hiçbir özellik 2 günden uzun bloke olmadı.
2. **Veri modeli önce.** Her sprint başında şema tanımlamak, paralel geliştirmeyi sorunsuz yaptı.
3. **Güvenlik ve performans ilk sprintten planlanmalı** — sonradan eklenmek daha zahmetli.
4. **Demo provaları sürprizleri erkenden yakalar.** Her sprint son demosundan en az 2 gün önce prova yapılmalı.
5. **`asyncio.gather` + staggered start** basit ama etkili çok-ajan koordinasyon modeli olduğunu kanıtladı.
