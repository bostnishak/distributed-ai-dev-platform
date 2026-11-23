# Parça 8 — Yol Haritası, Kritik Yol, Ders Teslimi Asgarisi, Riskler ve Kapsam Dışı

Bu dosyadaki fazlar `phases.json` ile birebir aynıdır; araç (`plan_tool.py check`) her maddenin tam olarak bir fazda olduğunu ve hiçbir maddenin ön koşulundan önceki bir fazda yer almadığını doğrular. Faz sınırı **katı değildir, bağımlılık katıdır:** bir madde, ön koşulları `done` olunca (kanıtlı) başlayabilir.

## 1. Faz özeti

<!-- phases:begin -->
| Faz | Ad | Hafta | Madde | P0 | Kişi-gün |
|---|---|---|---|---|---|
| 0 | Güvenilir temel: güvenlik, bağlantı, veri | 1–4 | 34 | 25 | 57,0 |
| 1 | Gateway ve orkestratör iskeleti | 3–10 | 60 | 32 | 198,0 |
| 2 | Ölç ve temellendir: eval ve RAG çekirdeği | 6–14 | 33 | 29 | 105,0 |
| 3 | Doğrulama katmanı ve güvenilirlik | 10–20 | 48 | 6 | 99,5 |
| 4 | Web araştırması, sunum ve belge fabrikası | 12–26 | 51 | 13 | 156,5 |
| 5 | Dağıtık yürütme ve ders gereksinimleri | 14–28 | 28 | 5 | 104,5 |
| 6 | Yazılım fabrikası ve oyun stüdyosu | 18–36 | 24 | 8 | 131,0 |
| 7 | Arayüz yeniden yapılandırma (paralel) | 8–36 | 19 | 1 | 84,5 |
| 8 | Genişleme: medya, veri, alan motorları, ML | 28–48 | 52 | 0 | 183,0 |
| 9 | Sürekli: operasyon, veri bakımı, süreç | 1–52 | 27 | 1 | 55,5 |
| | **Toplam** | | **376** | **120** | **1.174,5** |
<!-- phases:end -->

**Zaman gerçekçiliği:** <!-- effort:begin -->
Toplam 1.174,5 kişi-gün, yoğun tek geliştirici için yaklaşık 5,3 kişi-yıldır (220 iş günü/yıl); P0 alt kümesi 487,0 kişi-gün. Tahminler ±%50 belirsizdir.
<!-- effort:end -->
Paralel çalışan birden çok yapay zekâ aracı ve bir-iki insan gözden geçiren ile bu iş yılın büyük bölümünü alır.

### Kritik yol ve en uzun zincir

<!-- critical:begin -->
- **Efora göre kritik yol** (9 madde, 61,0 kişi-gün; sonsuz paralellikle bile yaklaşık 12 hafta alt sınır): `DEF-04` → `GW-01` → `GW-11` → `ORC-08` → `ORC-05` → `ORC-06` → `ORC-07` → `DIST-09` → `GW-18`
- **Madde sayısına göre en uzun zincir** (11 madde, 55,5 kişi-gün): `DEF-04` → `GW-01` → `GW-11` → `ORC-08` → `ORC-05` → `ORC-06` → `RES-01` → `RES-02` → `RES-04` → `PPT-01` → `MODE-05`
<!-- critical:end -->

Bu zincirin herhangi bir halkasındaki gecikme, kullanıcının en çok istediği senaryoyu geciktirir; bu yüzden bu maddeler en yüksek gözden geçirme önceliğine sahiptir.

## 2. Fazlar, çıkış kriterleri ve kapılar

### Faz 0 — Güvenilir temel (hafta 1–4)
<!-- p0_0:begin -->
**P0:** DEF-01, DEF-02, DEF-04, SEC-01, SEC-03, SEC-04, SEC-05, SEC-07, SEC-10, SEC-11, SEC-13, SEC-14, SEC-17, SEC-18, SEC-20, SEC-22, SEC-24, DAT-02, DAT-03, DAT-04, DAT-15, OPS-01, OPS-03, PROC-01, PROC-09
<!-- p0_0:end -->
**Çıkış kriterleri:**
- `plan_tool.py wiring --fail-on-new` CI'da çalışır; `WIRING_TRIAGE.md` 47 modülün tamamı için karar içerir.
- OpenAPI'den üretilen yetki matrisi testi: korumasız değiştirici route sayısı **0** (SEC-22).
- Oturum + RBAC çalışır; kullanıcı verisi izolasyon testleri geçer (SEC-01/03/04).
- Hiçbir route ana makinede serbest komut çalıştırmaz; kod çalıştırma yalnız sandbox'ta (SEC-13/14); önizleme ayrı origin'den (SEC-17).
- ZIP bombası/zip-slip, SSRF, sır tarama testleri yeşil (SEC-07/10/20).
- Tek veritabanı göç çerçevesi, WAL, stres testinde "database is locked" 0 (DAT-02/03).
- `ruff`, `pytest`, `plan_tool.py check` yeşil.

### Faz 1 — Gateway ve orkestratör iskeleti (hafta 3–10)
<!-- p0_1:begin -->
**P0:** GW-01, GW-02, GW-03, GW-07, GW-08, GW-11, ORC-01, ORC-03, ORC-05, ORC-06, ORC-08, ORC-10, ORC-11, ORC-13, ORC-15, ORC-17, ORC-24, MODE-01, MM-13, DIST-01, DIST-02, DIST-06, DIST-07, DIST-13, DIST-15, DIST-17, DIST-19, UX-01, UX-20, OPS-04, OPS-07, OPS-10
<!-- p0_1:end -->
**Çıkış kriterleri:**
- Gateway dışında Ollama URL'sine çağrı yok (grep testi); model kayıt defteri Ollama ile senkron.
- Sohbet hattı aşamalara bölünmüş; hiçbir aşama fonksiyonu 150 satırı geçmez; 60 orkestratör senaryosu CI'da < 60 sn.
- SSE olay şeması sürümlü; iş kuyruğu: sayfa yenilense ilerleme sürer (ORC-13).
- Ajan başına anahtar, sonuç sahipliği, idempotent sonuç (SEC-18, DIST-06/07); Tailscale tanılama betiği (DIST-13).
- Frontend derleme zinciri (lint/tip/birim) CI'da; XSS koruması (UX-01/20).
- `scripts/dev.ps1` temiz klonda sistemi başlatır, `/ready` yeşil (OPS-04).

### Faz 2 — Ölç ve temellendir (hafta 6–14)
<!-- p0_2:begin -->
**P0:** DEF-07, SEC-09, GW-05, ORC-02, ORC-19, RAG-01, RAG-02, RAG-04, RAG-05, RAG-07, RAG-08, RAG-11, RAG-12, RAG-14, RAG-26, HAL-01, HAL-02, HAL-03, HAL-04, HAL-05, HAL-06, HAL-07, HAL-08, HAL-09, HAL-12, HAL-19, HAL-22, ML-01, ML-05
<!-- p0_2:end -->
**Çıkış kriterleri:**
- Altın eval (≥ 300 örnek), koşucu ve **CI regresyon kapısı** çalışır (HAL-02/03/05).
- Yüklenen belge aranabilir; retrieval eval: alakasız sorularda bağlama giren parça < %5 (RAG-08/26).
- Atıf standardı + NLI atıf doğrulaması + atıf zorunluluğu çalışır (RAG-11, HAL-06/07/08); sayısal doğrulama (HAL-09).
- Üretilen kod sandbox'ta çalıştırılarak doğrulanır (HAL-12).
- **İlk gerçek taban çizgisi raporu yayımlanır; README Bölüm 7 hedefleri bu rapora göre revize edilir** (ADR ile).

### Faz 3 — Doğrulama katmanı ve güvenilirlik (hafta 10–20)
<!-- p0_3:begin -->
**P0:** RAG-30, HAL-14, HAL-15, DOM-01, UX-09, UX-10
<!-- p0_3:end -->
**Çıkış kriterleri:** ECE ≤ 0,08; doğru kaçınma ≥ %85, gereksiz kaçınma ≤ %7; CoVe/öz-tutarlılık/konsey yalnız eval'de kazanç gösterdiyse açık (aksi halde kapalı, HAL-10/11, GW-18); kırmızı takım seti ve telemetri panosu (HAL-26/27); atıf ve güven arayüzde görünür (UX-10); alan motorlarında varsayılan değer yok (DOM-01).

### Faz 4 — Web araştırması, sunum ve belge fabrikası (hafta 12–26)
<!-- p0_4:begin -->
**P0:** MODE-04, RAG-18, HAL-23, RES-01, RES-02, RES-04, RES-10, PPT-03, PPT-06, PPT-07, DOC-02, DS-02, UX-11
<!-- p0_4:end -->
**Çıkış kriterleri:** web araması + `safe_fetch` (SSRF testleri) çalışır; 30 konulu araştırma setinde atıf doğruluğu ≥ %95, uydurma kaynak 0 (RES-12); sunum kontrol listesi ≥ %90, render denetimi ve kaynak slaytı (PPT-07/06/10); belge eval ≥ %90 ve formül hatası 0 (DOC-02/10); artefakt paneli (UX-11).

### Faz 5 — Dağıtık yürütme ve ders gereksinimleri (hafta 14–28)
<!-- p0_5:begin -->
**P0:** GW-04, ORC-07, DIST-03, DIST-09, UX-23
<!-- p0_5:end -->
**Çıkış kriterleri:** sohbet/araştırma adımları ajanlara yetenek puanıyla dağıtılır ve çıktıda "Üreten: ajan·model" görünür (ORC-07, DIST-20); 6 ajanla ≥ 3x hızlanma (DIST-21); çakışma çözümü ve yeniden atama arayüzden uçtan uca (UX-23, DIST-15); kaos senaryolarında görev kaybı 0 (DIST-22); model karşılaştırma panosu ve CSV dışa aktarma (DIST-19, UX-24).

### Faz 6 — Yazılım fabrikası ve oyun stüdyosu (hafta 18–36)
<!-- p0_6:begin -->
**P0:** IDE-01, IDE-02, IDE-03, IDE-04, IDE-05, IDE-17, IDE-24, GAME-05
<!-- p0_6:end -->
**Çıkış kriterleri:** tek `factory/` paketi; 20 istemde çalışan proje ≥ %80, test geçme ≥ %85 (IDE-24); 8 testli şablon (IDE-17); tarayıcı doğrulaması (IDE-06); oyun eval ≥ %85, bot testi (GAME-05/10).

### Faz 7 — Arayüz yeniden yapılandırma (paralel, hafta 8–36)
<!-- p0_7:begin -->
**P0:** UX-28
<!-- p0_7:end -->
**Çıkış kriterleri:** `assistant.js` bileşenlere ayrılmış, hiçbir frontend dosyası 500 satırı geçmez (UX-02); axe-core kritik/ciddi ihlal 0 (UX-05); 25 e2e akış CI'da yeşil (UX-28).

### Faz 8 — Genişleme (hafta 28–48)
Medya (MM), veri bilimi (DS), alan motorları (DOM), ML adaptörleri (ML-07..13), oyun/IDE cilası. **Hiç P0 yok;** her madde kendi eval setini ve kapısını getirir. Kazancı kanıtlanmayan özellik kapalı kalır (OPS-11).

### Faz 9 — Sürekli (hafta 1–52)
Yedek/geri yükleme turu (DAT-07), runbook'lar (OPS-15), belge sitesi (OPS-22), demo kiti ve senaryo (OPS-23, PROC-06), Scrum belgeleri (PROC-02..10). Faz 0'dan itibaren paralel yürür.

## 3. Paralel çalışma şeritleri (çakışmayı önlemek için dosya sahipliği)

> Denetim sırasında iki aracın aynı çalışma ağacında eş zamanlı çalışması dosya çakışması riskini gösterdi. Her şerit kendi `git worktree`/dalında çalışır; aşağıdaki dizinler şerit başına tek sahiplidir. `master/assistant.py` ORC-01 tamamlanana kadar **yalnız Şerit B**'ye aittir.

| Şerit | Alanlar | Sahip olduğu yollar |
|---|---|---|
| A — Güvenlik ve veri | SEC, DAT, DEF-11..13 | `master/auth/`, `master/access_control.py`, `master/db.py`, `migrations/`, `master/secret_store.py` |
| B — Gateway ve orkestratör | GW, ORC, MODE | `master/gateway/`, `master/orchestrator/`, `master/assistant.py`, `prompts/` |
| C — Bilgi ve doğrulama | RAG, HAL, ML | `master/rag/`, `master/web/`, `master/verify/`, `eval/`, `training/` |
| D — Stüdyolar | RES, PPT, DOC, DS, MM, IDE, GAME, DOM | `master/studios/`, `master/factory/`, `master/workspace_builder.py`, şablon deposu |
| E — Dağıtık ajanlar | DIST | `agent/`, `agent-node/`, `master/tasks_api.py`, `master/selection.py`, `master/scheduler.py` |
| F — Arayüz | UX | `frontend/`, `master/static/` |
| G — Operasyon ve süreç | OPS, PROC, DEF-01..04 | `scripts/`, `.github/`, `docs/`, `docker/` |

## 4. Ders teslimi asgarisi (MVP kesme çizgisi)

Hocanın gereksinimleri (CM6453 PDF: dağıtık ajanlar, yetenek tabanlı atama, Scrum, 5 sprint, hata kurtarma, çakışma çözümü, pano, model karşılaştırma) temel olarak mevcut sistemde karşılanıyor. Ders teslimi için **aşağıdaki maddeler ve ön koşulları zorunludur**; kalan plan ders sonrası ürünleştirmedir (PROC-10). Ön koşul kapanışı aracın bağımlılık grafiğinden hesaplanır; gerçek MVP büyüklüğü satır sayısından büyüktür.

<!-- mvp:begin -->
| Madde | Başlık |
|---|---|
| PROC-01 | Gereksinim izlenebilirlik matrisi |
| PROC-06 | Demo senaryosu |
| PROC-09 | Hesaplanan ilerleme dosyası |
| PROC-10 | Risk kaydı ve MVP kesme çizgisi |
| DIST-02 | Benchmark paketi ve periyodik yeniden değerlendirme |
| DIST-03 | Seçim algoritmasının eval ile ayarlanması ve açıklanabilirliği |
| DIST-06 | Kiralama, yeniden atama ve idempotent sonuç |
| DIST-07 | Ajan yetkilendirme ve sonuç sahipliği |
| DIST-13 | Tailscale ağı: keşif, kimlik ve güvenli bağlama |
| DIST-15 | Çıktı entegrasyonu ve çakışma çözümü (arayüzlü) |
| DIST-17 | Test ajanı: gerçek yürütme |
| DIST-19 | Performans panosu ve model karşılaştırması |
| DIST-20 | Kaynak izlenebilirliği (provenance) |
| DIST-21 | Dağıtık hızlanma ölçümü |
| DIST-22 | Kaos testi ve toparlanma senaryoları |
| UX-23 | Projeler (Scrum hattı) sayfası: DAG, çakışma, yeniden atama |
| UX-24 | Pano: SLO kartları, model karşılaştırma, hata dökümü |
| SEC-18 | Ajan kimliği ve sonuç sahipliği |
| SEC-24 | Ağ ayrıntısı: bağlama adresi ve güvenlik duvarı kapsamı |
| OPS-04 | Tek komutla başlatma |
| OPS-23 | Demo ve sunum kiti |

MVP 21 madde; ön koşullarıyla birlikte **46 madde, 176,0 kişi-gün** (planın %12'i).
<!-- mvp:end -->

Gösterimden önce `OPS-23` kontrol listesi çalıştırılır (Tailscale, Ollama, modeller, port, ajan kaydı). **MVP dışındaki hiçbir madde MVP maddesinin önüne geçmez.**

## 5. Risk kaydı

| Kod | Risk | Olasılık | Etki | Azaltma |
|---|---|---|---|---|
| R1 | Plan büyüklüğü (376 madde) kapsam kaymasına yol açar | Yüksek | Yüksek | MVP çizgisi (Bölüm 4), faz kapıları, haftalık gözden geçirme (PROC-10) |
| R2 | Yerel 4B–9B modellerin kalite tavanı hedefin altında kalır | Yüksek | Yüksek | Gateway kademeleri (GW-19), dağıtık büyük ajan, isteğe bağlı bulut (D1), dürüst sınır beyanı (HAL-30) |
| R3 | GPU/VRAM/ısı kısıtı; çok modelli akışlar OOM veya aşırı yavaşlık verir | Yüksek | Orta | VRAM yönetimi ve kuyruk (GW-06/09/10), donanım politikası (DIST-12), güç profili (OPS-24) |
| R4 | Aynı ağaçta eşzamanlı araçlar dosyaları sessizce ezer (**yaşandı**) | Yüksek | Yüksek | Şerit/dal/worktree kuralı (README Bölüm 8, madde 9), PR ile birleştirme |
| R5 | Eval kümesi sızıntısı veya güvenilmez hakem, ölçümü anlamsızlaştırır | Orta | Yüksek | Hakem kalibrasyonu κ ≥ 0,7 (HAL-04), eğitim/eval ayrımı (ML-07), sürümlü veri kümesi |
| R6 | Ağ/Tailscale sorunları gösterimi bozar (**yaşandı**: IPv6/TLS, ev ağı) | Yüksek | Yüksek | Tanılama (DIST-13), runbook (OPS-15), çevrimdışı demo ve yedek video (OPS-23/PROC-06) |
| R7 | Güvenlik regresyonu (yeni route kimliksiz kalır; **yaşandı**) | Orta | Yüksek | OpenAPI yetki matrisi CI'da (SEC-22), eş zamanlı araç denetimi |
| R8 | Frontend yeniden yapılandırması regresyon üretir | Orta | Orta | e2e önce (UX-28), kademeli geçiş, görsel regresyon |
| R9 | Bağımlılık/lisans sorunları (model lisansları, Monaco/three.js/Playwright) | Orta | Orta | Lisans tablosu (PROC-08), SBOM ve denetim (OPS-13, SEC-19) |
| R10 | Docker/sandbox kullanılamayan makineler | Orta | Orta | Özellik kapalı + açık mesaj (DEF-15), Docker'sız güvenli alt küme |
| R11 | Web erişiminin etik/hukuki/robots sorunları | Orta | Orta | Telif/robots politikası (RES-11), kısa alıntı sınırı, kaynak gösterme |
| R12 | Takvim: ders teslimi ile plan çakışır | Orta | Yüksek | MVP asgarisi, Faz 0'da bile PROC-06 senaryosu |
| R13 | "Halüsinasyon biter" beklentisi yanlış yönlendirir | Yüksek | Orta | HAL-30 şeffaflık sayfası, ML-14 dürüstlük notu, ölçülmüş oranlar |
| R14 | Eski planın "DONE" iddialarına güvenmek | Orta | Yüksek | Kanıta dayalı `PROGRESS.json`, bağlantı kapısı (DEF-01), `plan_tool.py status` |

## 6. Kapsam dışı (bu planda yapılmayacaklar)

- Sıfırdan temel LLM ön eğitimi veya büyük ölçekli eğitim altyapısı (yalnız adaptör ince ayarı, ML-08, kanıt şartıyla).
- Ticari seviye CAD/CAM çekirdeği ve gerçek tezgâh kontrolü: mevcut CNC modülleri yalnız **doğrulama ve güvenlik** (DOM-06..08) açısından iyileştirilir; yeni geometri çekirdeği yazılmaz.
- Gerçek zamanlı çok kullanıcılı ortak düzenleme (CRDT): IDE-23 yalnız salt-okunur/yorum paylaşımını kapsar.
- Native mobil uygulama (PWA yeterlidir, UX-07).
- Teşhis, ilaç dozu veya yatırım tavsiyesi üretimi (HAL-19, DOM-04).
- Genel amaçlı otonom "bilgisayar kullanımı" ajanı: `browser_agent` ve `desktop_automation` modülleri DEF-02 triyajında "dondur/sil" adayıdır; ihtiyaç doğarsa ayrı plan ve güvenlik incelemesi gerekir (ağ ve dosya eylemleri ORC-10 onay kapısına tabidir).
- Çok kiracılı SaaS, faturalama ve genel internete açık yayın (tailnet ile sınırlı çalışma varsayılır; açma kararı ayrı tehdit modeli gerektirir, SEC-22).

## 7. Faz geçiş kontrol listesi (her faz sonu, 15 dakika)

1. `plan_tool.py check` ve `wiring --fail-on-new` temiz mi?
2. Fazın tüm P0 maddeleri `PROGRESS.json`'da kanıtlı `done` mu? (kanıtsız olanlar geri açılır)
3. İlgili eval raporu (varsa) hedefleri sağlıyor mu? Hedefler gerçek taban çizgisine göre güncellendi mi (ADR)?
4. Yeni bulgu (F#) çıktı mı? Plana eklendi mi?
5. Risk kaydı güncellendi mi? MVP çizgisi etkilendi mi?
6. Gösterim kiti (OPS-23) hâlâ çalışıyor mu?
