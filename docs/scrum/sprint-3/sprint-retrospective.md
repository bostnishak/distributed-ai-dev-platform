# Sprint 3 — Sprint Retrospektifi

| | |
|---|---|
| Sprint | 3 (5 Kasım – 18 Kasım 2026) |
| Tarih | 5 Kasım 2026 (erken checkpoint) |
| Katılımcılar | Tüm ekip (6 kişi) |
| Scrum Master | Zeynep Duru Küçük |
| Yöntem | Start / Stop / Continue |

## İyi Gidenler (Continue)

**DAG tasarımı erkenden yapıldı.** `scheduler.py` bağımlılık grafiğini sprint başında veri modeline gömmek yerine backlog'da PB-34 olarak ayırdık; bu sayede PB-30 (prompt) ve PB-33 (doğrulama) birbirinden bağımsız geliştirildi ve gecikme olmadı.

**LiteLLM kaldırması temiz gitti.** PB-37, ayrı bir PR olarak tek commit'te yapıldı; gateway çıkınca CI'da iki harici bağımlılık testi de kalktı ve test koşum süresi %12 kısaldı. Basitleştirme kararı doğruydu.

**Tür-duyarlı promptlar görev kalitesini artırdı.** `task_prompts.py` eklenince ajanların boş veya alakasız çıktı üretme oranı düştü; doğrulama adımı daha az görev reddetti.

**Validation katmanı gerçek hataları yakaladı.** Sözdizimi hatalı Python çıktısını AST parse ile yakalayan `validation.py`, sprint boyunca 3 hatalı görevi tekrar kuyruğa attı — manuel müdahale gerekmedi.

**ZIP çıktısı beklentileri aştı.** `output_api.py` ilk taslakta yalnızca dosya birleştiriyordu; Duru dizin yapısını (backend/, frontend/, docs/) ekleyince teslim edilen ZIP, gerçek bir proje iskeleti gibi göründü.

## İyileştirilecekler (Stop / Start)

**Stop: 5 saniyelik polling ile canlı UI güncellemesi.**
Proje detay sayfası her 5 saniyede bir `/api/projects/{id}` çağırıyor. Çok sayıda eş zamanlı proje açıkken bu gereksiz yük oluşturuyor. Sprint 4'te WebSocket push'a geçilmeli.

**Stop: Doğrulamayı yalnızca uzunluk + sözdizimi ile sınırlandırmak.**
Çok kısa ama sözdizimi doğru bir çıktı (`pass` gibi tek satır) doğrulamayı geçiyor. Minimum dosya sayısı veya LLM tabanlı kalite kontrolü eklenmeli.

**Stop: Her görev tipi için tek bir ZIP kökü.**
Şu an tüm dosyalar tek bir ZIP'e giriyor. Farklı bileşenler (backend vs. frontend) ayrı ZIP'ler veya sub-dizin yapısıyla teslim edilebilir.

**Start: Görev başarısızlığında otomatik yeniden deneme sayacı.**
`attempt` sütunu Sprint 3'te şemaya eklendi fakat MAX_ATTEMPTS sınırı yok. Sonsuz döngüyü önlemek için en fazla 3 deneme sonrası görevi `failed` olarak işaretleyen bir mekanizma eklenmeli.

**Start: Ajan model doğrulama.**
Kayıt sırasında ajan hangi modeli bildirirse bildirsin master doğrulamıyor. Sprint 4'te `/api/agents/register` Ollama'ya hızlı bir `GET /api/tags` sorgusu yaparak modelin varlığını teyit edebilir.

## Aksiyon Maddeleri

| # | Aksiyon | Sorumlu | Hedef Sprint |
|---|---|---|---|
| A4 | WebSocket push bildirimler — polling kaldır | Furkan | Sprint 4 |
| A5 | MAX_ATTEMPTS = 3 ile başarısız görev işaretleme | Semih | Sprint 4 başı |
| A6 | Kayıt sırasında Ollama model varlık kontrolü | Işıl | Sprint 4 |

Sprint 2'den taşınan aksiyonlar (A1–A3) tamamlandı:
- A1 ✅ Branch protection → PR'da en az 1 reviewer zorunlu
- A2 ✅ Sprint başı açık dal kontrolü Daily Scrum gündemine alındı
- A3 ✅ Lint CI adımı zorunlu hale getirildi

## Takım Memnuniyet Puanı

| Üye | Puan |
|---|---|
| İshak Bostan | 5 |
| Zeynep Duru Küçük | 5 |
| Furkan Kaan Özbeyli | 5 |
| Semih Sarıca | 4 |
| Işıl Karademir | 4 |
| Berfin Yiğit | 5 |
| **Ortalama** | **4.7 / 5** |

Ekip bu sprintin en yüksek memnuniyet puanını verdi. Belirtilen neden: "İlk kez gerçekten çalışan bir şey teslim ettik — ajan kodu üretiyor, ZIP indiriliyor."

Semih ve Işıl 4 verdi; "Doğrulama yüzeysel kaldı, sprint 4'te LLM tabanlı review ekleseydik daha iyi olurdu" notunu eklediler.

## Sprint 4 için Taşınan Öğrenmeler

1. **Veri modeli önce.** Schema v4'ü sprint başında tanımlamak (files, validation_status, attempt) tüm modüllerin aynı sözleşme üzerinde çalışmasını sağladı. Bu pattern Sprint 4'te de sürdürülmeli.
2. **Küçük, bağımsız PR'lar.** PB-37 (LiteLLM kaldırma) tek bir PR olduğu için merge çakışması olmadı; büyük özellikler küçük PR'lara bölündüğünde inceleme hızlanıyor.
3. **Polling → push geçişi ertelenmemeli.** Sprint 2'de de konuşulmuştu; Sprint 3'te yapılamadı. Sprint 4 backlog'una yüksek öncelikle alındı (PB-41).
