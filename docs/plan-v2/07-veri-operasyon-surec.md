# Parça 7 — Veri ve Depolama (DAT), Operasyon ve Kalite (OPS), Scrum Süreci (PROC)

## A. DAT — Veri, Depolama ve Hafıza

#### DAT-01 · Tek veritabanı stratejisi
- **Sorun:** [DOĞRULANDI: F14] `platform.db`, `user_profile.db`, `cognitive_memory.db`, `graph_rag.db` (ve `cmm_quality.db`) ayrı dosyalar; ayrı bağlantı ayarları, ayrı yedekleme/göç, tutarsız kilitlenme davranışı; kullanıcı ve sohbet verisi iki farklı veritabanında.
- **Değişiklik:** Karar D8: tek `platform.db` (WAL) + modül başına şema ön eki; mevcut dosyalardan veri göçü betiği (doğrulamalı, geri alınabilir); `rag` vektör verisi gerekirse ayrı dosya olarak kalır (açık gerekçeyle).
- **Kabul:** Göç sonrası kayıt sayıları ve özet toplamları eşleşir (otomatik denetim); eski dosyalar yedeklenir; uygulama tek `DB_PATH` ile çalışır.
- **Meta:** P1 · L · Bağ: DAT-02 · Durum: açık

#### DAT-02 · Sürümlü göç (migration) çerçevesi
- **Sorun:** [DOĞRULANDI: F14] `db.py` içinde elle yazılmış `ALTER TABLE ... ADD COLUMN` listesi (satır ~28) ve `CREATE TABLE IF NOT EXISTS` blokları; şema sürümü ve geri alma yok.
- **Değişiklik:** `migrations/0001_*.sql` sıralı dosyalar, `schema_version` tablosu, uygulama başlangıcında otomatik uygulama, kuru çalıştırma ve yedekleme öncesi anlık görüntü; modül başına göç.
- **Kabul:** Sıfırdan kurulum ve eski şemadan yükseltme aynı sonuç şemasını üretir (test: şema karşılaştırma); başarısız göç veritabanını eski haline döndürür.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### DAT-03 · SQLite çalışma ayarları ve eşzamanlılık
- **Sorun:** [DOĞRULANDI: F14] WAL yalnız `memory_engine`'de (`PRAGMA journal_mode=WAL`); `db.py` yalnız `foreign_keys=ON`; arka plan iş parçacıkları (kiralama, DAG) ve istek iş parçacıkları aynı dosyaya yazıyor.
- **Değişiklik:** Ortak `connect()`: WAL, `synchronous=NORMAL`, `busy_timeout`, `foreign_keys=ON`; tek yazıcı kuralı/yeniden deneme; uzun okumalar için ayrı bağlantı; kilitlenme metrikleri.
- **Kabul:** 8 yazıcı + 8 okuyucu 60 sn stres testinde "database is locked" 0; WAL dosyası kontrolsüz büyümez (checkpoint politikası).
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### DAT-04 · Veri modeli ve ERD
- **Sorun:** [ÖNERİ] Planın varlıkları (kullanıcı, oturum, sohbet, mesaj, artefakt, dosya, koleksiyon, parça, gömme, LLM çağrısı, geri bildirim, eval sonucu, iş) tek şemada tanımlı değil.
- **Değişiklik:** `docs/plan-v2/erd.md` (Mermaid ERD) ve göç dosyaları; ilişkiler, silme davranışı (CASCADE/RESTRICT), indeksler, sahiplik (`owner_id`).
- **Kabul:** ERD göç sonrası gerçek şemadan otomatik üretilen çıktıyla tutarlı (CI karşılaştırması); her tabloda sahiplik ve zaman damgaları.
- **Meta:** P0 · M · Bağ: DAT-02 · Durum: açık

#### DAT-05 · İçerik adresli dosya deposu
- **Sorun:** [DOĞRULANDI: F20] Yüklenen/üretilen dosyalar `cnc_jobs/`, `workspaces/`, `media/` gibi dizinlere dağınık; yinelenen yükleme tekilleştirilmiyor; yetkilendirme dosya adına bağlı.
- **Değişiklik:** SHA-256 adresli blob deposu + `files` tablosu (sahip, ad, tür, boyut, özet, referans sayısı); URL'ler imzalı/yetkili (MM-14); yinelenen içerik tek kopya; çöp toplama.
- **Kabul:** Aynı dosya iki kez yüklenince tek blob; yetkisiz erişim reddedilir; referansı olmayan blob çöp toplayıcıyla silinir (test).
- **Meta:** P1 · L · Bağ: DAT-04, SEC-03 · Durum: açık

#### DAT-06 · Saklama süresi ve tam silme
- **Sorun:** [DOĞRULANDI: F20] Süresiz saklama; "verilerimi sil" gerçek temizliği (blob, gömme, FTS, önbellek, WAL) garanti etmiyor.
- **Değişiklik:** Kullanıcı kontrollü saklama süreleri, otomatik temizlik işi, tam silme akışı (`wal_checkpoint(TRUNCATE)`/`VACUUM`), silme kayıtları denetim izinde; yedeklerdeki durum açıkça belgelenir.
- **Kabul:** Silme sonrası kullanıcıya ait benzersiz dizge veritabanı ve dosya sisteminde bulunmaz (test); süresi dolan veri otomatik silinir.
- **Meta:** P1 · M · Bağ: DAT-05 · Durum: açık

#### DAT-07 · Zamanlı, artımlı yedek ve geri yükleme testi
- **Sorun:** [DOĞRULANDI: F2] Yedek yalnız manuel indirilebilir ZIP (şifresiz); geri yükleme akışı ve testi yok.
- **Değişiklik:** Zamanlı artımlı yedek (şifreli, SEC-12), saklama politikası (günlük/haftalık), geri yükleme komutu ve arayüzü, **CI'da gerçek yedekle-geri yükle turu**.
- **Kabul:** Yedekle → temiz ortamda geri yükle → kayıt sayıları ve dosya özetleri aynı; bozuk yedek reddedilir.
- **Meta:** P1 · M · Bağ: SEC-12 · Durum: açık

#### DAT-08 · Veri taşınabilirliği (dışa/içe aktarım)
- **Sorun:** [DOĞRULANDI] Kullanıcı dışa aktarımı JSON; dosyalar, hafıza, artefaktlar ve koleksiyonlar içe aktarılamıyor.
- **Değişiklik:** Tek paket (JSON + dosyalar + gömme yeniden üretilebilir), başka makinede içe aktarma, çakışma çözümü (kimlik yeniden eşleme), gizli bilgi hariç.
- **Kabul:** A makinesinden dışa aktar, B'ye içe aktar → sohbetler/artefaktlar/koleksiyonlar tamam; sır içermez (tarama).
- **Meta:** P2 · M · Bağ: DAT-05 · Durum: açık

#### DAT-09 · Hafıza konsolidasyonu ve unutma
- **Sorun:** [DOĞRULANDI] `semantic_memories` otomatik çıkarım yapıyor; yinelenen/çelişen kayıtlar birikir, yaşlanma ve kullanıcı onayı yok.
- **Değişiklik:** Benzer kayıt birleştirme, çelişki çözümü (kullanıcı sorulur), güven/yaş bozunumu, kaynak mesaj bağlantısı, kullanıcı düzenleme/silme, hafızanın hangi yanıtta kullanıldığı görünürlüğü.
- **Kabul:** Çelişen iki tercih tespit edilir ve kullanıcıya sorulur; silinen hafıza hiçbir bağlamda görünmez (test).
- **Meta:** P2 · M · Bağ: HAL-24 · Durum: açık

#### DAT-10 · Birleşik tam metin arama (FTS5)
- **Sorun:** [DOĞRULANDI] Sohbet araması ayrı mekanizmalarla (`cross_chat_snippets`) yapılıyor; belge ve kod araması ayrı.
- **Değişiklik:** FTS5 sanal tabloları (sohbet, belge, kod, artefakt), Türkçe tokenizer (RAG-07), tek arama API'si; yeniden indeksleme komutu.
- **Kabul:** Tek sorgu sohbet+belge+artefakt sonuçlarını sahip filtresiyle döndürür; 100.000 kayıtta p95 < 100 ms.
- **Meta:** P1 · M · Bağ: RAG-07, SEC-03 · Durum: açık

#### DAT-11 · Vektör verisinin sürümlenmesi
- **Sorun:** [DOĞRULANDI: F8] Gömme blob'ları model/boyut bilgisi taşımıyor (yalnız boyut farkında sessiz yedekleme).
- **Değişiklik:** `embedding_model`, `dim`, `version` sütunları; model değişince arka planda yeniden gömme (RAG-25); karışık sürümde arama reddedilir veya uyarır.
- **Kabul:** Farklı modelle gömülmüş kayıtlar aynı sorguda karıştırılmaz (test); yeniden gömme sırasında arama kesintisiz.
- **Meta:** P1 · S · Bağ: RAG-05 · Durum: açık

#### DAT-12 · Veri kalitesi ve onarım aracı
- **Sorun:** [ÖNERİ] Yetim kayıt, bozuk JSON sütunu, yabancı anahtar ihlali birikebilir.
- **Değişiklik:** `scripts/db_doctor.py`: bütünlük kontrolü (`PRAGMA integrity_check`, `foreign_key_check`), JSON sütun doğrulama, yetim blob/kayıt tespiti, güvenli onarım önerisi; yönetici arayüzünde rapor.
- **Kabul:** Elle bozulmuş veritabanında doctor sorunların tümünü listeler ve onarılabilenleri onarır (test).
- **Meta:** P2 · M · Bağ: DAT-02 · Durum: açık

#### DAT-13 · Büyük veri: arşivleme ve sorgu planları
- **Sorun:** [ÖNERİ] Mesaj ve çağrı tabloları zamanla büyür; sayfalama/indeksler denetlenmiyor.
- **Değişiklik:** Sayfalamalı API'ler, sık sorgular için indeks, `EXPLAIN QUERY PLAN` testleri (tam tarama yasak), eski mesajları arşivleme.
- **Kabul:** 1 milyon satırlık sentetik veride kritik sorgular indeks kullanır ve p95 < 50 ms (test).
- **Meta:** P2 · M · Bağ: DAT-04 · Durum: açık

#### DAT-14 · Olay günlüğü
- **Sorun:** [DOĞRULANDI: F17] `/api/events` var ama arayüzü, şeması ve saklama politikası yok.
- **Değişiklik:** Olay şeması (tür, aktör, nesne, zaman, ayrıntı), halka tampon/saklama süresi, filtreli arayüz ve dışa aktarma; denetim izinden ayrı (operasyonel olaylar).
- **Kabul:** Önemli olaylar (görev atama, hata, yeniden atama, model terfisi) kaydedilir ve arayüzde filtrelenir.
- **Meta:** P2 · M · Bağ: UX-24 · Durum: açık

#### DAT-15 · Çok kiracılı veri izolasyonu hazırlığı
- **Sorun:** [DOĞRULANDI: F13] Tablolarda tutarlı `owner_id` yok; filtreleme istemciye bırakılmış.
- **Değişiklik:** Tüm kullanıcı verisi tablolarında `owner_id` zorunlu; sorgu katmanı sahip filtresini otomatik uygular (depo/repository katmanı); filtresiz sorgu yazmak lint ile yasak.
- **Kabul:** Her tablo için "A'nın verisi B'ye sızmaz" testi otomatik üretilir.
- **Meta:** P0 · M · Bağ: SEC-03, DAT-04 · Durum: açık

#### DAT-16 · Postgres uyumluluk katmanı (isteğe bağlı)
- **Sorun:** [ÖNERİ] Takım/ölçek büyürse SQLite sınırlayıcı olabilir; şimdilik gerek kanıtlanmadı.
- **Değişiklik:** Yalın SQL veya SQLAlchemy Core ile uyumluluk testleri; Postgres ile CI işi (isteğe bağlı); yalnız gerçek ihtiyaç ölçülürse aktifleştirilir.
- **Kabul:** Aynı test paketi SQLite ve Postgres'te geçer (CI isteğe bağlı iş).
- **Meta:** P3 · L · Bağ: DAT-02 · Durum: açık

---

## B. OPS — Operasyon, Gözlemlenebilirlik, Test ve Dağıtım

#### OPS-01 · Yapılandırılmış günlük ve korelasyon
- **Sorun:** [DOĞRULANDI: F11] Günlük yaklaşımı tutarsız; birçok yerde `log` yok, bazı modüllerde `print`/sessizlik.
- **Değişiklik:** `structlog`/JSON günlük, `request_id` ve `run_id` korelasyonu, seviye politikası, PII/gizli maskeleme (SEC-23), dönen günlük dosyaları.
- **Kabul:** Bir isteğin tüm günlük satırları aynı `request_id`'yi taşır; `print` kullanımı lint ile yasak.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### OPS-02 · Metrikler ve izleme
- **Sorun:** [ÖNERİ] Süre ölçümleri (TTFT, retrieval, doğrulama) ve sistem metrikleri toplanmıyor.
- **Değişiklik:** `/metrics` (Prometheus metin biçimi), süre/sayaç/histogram metrikleri; isteğe bağlı OpenTelemetry izleri; Grafana gerekmeden yerel pano.
- **Kabul:** Ana yolların süreleri metriklerde görünür; metrik adları belgeli ve sabit.
- **Meta:** P1 · M · Bağ: OPS-01 · Durum: açık

#### OPS-03 · Canlılık ve hazır olma sağlığı
- **Sorun:** [DOĞRULANDI] `/health` yalnız `{"status":"ok"}` döndürüyor; Ollama, DB, disk, model, gömme, arka plan döngüleri bilinmiyor.
- **Değişiklik:** `/health` (canlılık) ve `/ready` (Ollama erişimi, model varlığı, gömme modeli, DB yazılabilirliği, disk alanı, arka plan döngüleri, sandbox) ayrımı; ayrıntılı rapor yöneticiye.
- **Kabul:** Her bağımlılık kapatıldığında `/ready` doğru bileşeni "degraded" gösterir; arayüz sihirbazı bunu kullanır (UX-17).
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### OPS-04 · Tek komutla başlatma
- **Sorun:** [DOĞRULANDI] Başlatma bu denetimde `python -m uvicorn ... --host 0.0.0.0` ve ayrı `start_agents.py` ile elle yapıldı; bağlama adresi/port çakışması/venv seçimi hatalara yol açtı (sistem Python'unda `pymupdf` yok, venv gerekli).
- **Değişiklik:** `scripts/dev.ps1` ve `scripts/dev.sh`: venv doğrulama/kurulum, port çakışma tespiti, Ollama/model kontrolü, master + (isteğe bağlı) ajanlar, tailnet IP'sine güvenli bağlama (SEC-24), tarayıcıyı açma.
- **Kabul:** Temiz klonda tek komut sistemi başlatır ve `/ready` yeşil olur; hata durumunda eyleme dönük mesaj.
- **Meta:** P0 · M · Bağ: SEC-24, DEF-18 · Durum: açık

#### OPS-05 · Windows kurulum paketi
- **Sorun:** [ÖNERİ] Takım arkadaşları kurulum için komut satırı ve Python bilgisi gerektiriyor.
- **Değişiklik:** Tek tıkla kurulum (gömülü/venv Python, bağımlılıklar, Ollama kontrol yönlendirmesi, kısayollar, servis seçeneği), kaldırma; sürüm kontrolü.
- **Kabul:** Temiz Windows 11'de kurulum ve ilk çalıştırma ≤ 15 dk, belgeli ve test edilmiş.
- **Meta:** P2 · L · Bağ: OPS-04 · Durum: açık

#### OPS-06 · Docker: güvenli imaj ve compose profilleri
- **Sorun:** [DOĞRULANDI] `docker-compose.yml` ve imajlar var; kullanıcı root, HEALTHCHECK, imaj taraması yok; profiller (staging) sınırlı.
- **Değişiklik:** Çok aşamalı imaj, root olmayan kullanıcı, `HEALTHCHECK`, Trivy taraması, profiller: `core`, `agents`, `gpu`, `web-search` (SearXNG), `sandbox`; yerelde `127.0.0.1` bağlama.
- **Kabul:** `docker compose --profile core up` ile sistem açılır ve duman testi geçer (CI); Trivy yüksek/kritik açık 0.
- **Meta:** P1 · M · Bağ: DEF-14, SEC-19 · Durum: açık

#### OPS-07 · CI hattının genişletilmesi
- **Sorun:** [DOĞRULANDI] CI yalnız `ruff` + `pytest` + docker build; tip, güvenlik, frontend, eval, kapsam yok.
- **Değişiklik:** İşler: Python matrisi (3.12 + güncel), ruff + format, tip denetimi (pyright/mypy kademeli), pytest + kapsam, `pip-audit`, gitleaks, bağlantı kapısı (DEF-01), frontend (lint/tip/birim/e2e), docker duman, hızlı eval (HAL-05); yavaş işler gece.
- **Kabul:** PR kontrolleri < 15 dk; her kapı bir iş olarak ayrı raporlanır; ana dal korumalı.
- **Meta:** P0 · L · Bağ: DEF-01, UX-01 · Durum: açık

#### OPS-08 · Kapsam politikası
- **Sorun:** [ÖNERİ] Test kapsamı ölçülmüyor; 280 testin neyi kapsadığı belirsiz.
- **Değişiklik:** `coverage`/`diff-cover`: değişen satırlarda ≥ %85, kritik paketlerde (gateway, guard, verify, auth) ≥ %90; kapsam raporu PR'a yorum.
- **Kabul:** Kapsamı düşüren PR CI'da uyarı/kırmızı verir; rapor erişilebilir.
- **Meta:** P1 · S · Bağ: OPS-07 · Durum: açık

#### OPS-09 · Test piramidi ve işaretleri
- **Sorun:** [DOĞRULANDI: F18] Tüm testler tek dizinde; tam koşu ~100 sn; hızlı/yavaş/entegrasyon ayrımı yok.
- **Değişiklik:** `pytest -m unit|contract|integration|e2e|security|slow` işaretleri; varsayılan hızlı küme < 30 sn; gerçek Ollama gerektiren entegrasyonlar isteğe bağlı iş.
- **Kabul:** Hızlı küme < 30 sn; her test bir işaret taşır (CI kontrolü).
- **Meta:** P1 · M · Bağ: OPS-07 · Durum: açık

#### OPS-10 · Deterministik sahte LLM sunucusu (kayıt/tekrar)
- **Sorun:** [DOĞRULANDI] Testler sahte model çağrısı kullanıyor ama ortak, gerçeğe yakın bir test ikizi yok; uçtan uca sohbet davranışı sınanamıyor.
- **Değişiklik:** Ollama API uyumlu sahte sunucu: kayıtlı yanıtlar (VCR benzeri), akış, araç çağrısı, hata enjeksiyonu; e2e ve orkestratör senaryolarında kullanılır.
- **Kabul:** 60 orkestratör senaryosu (ORC-24) ve 25 e2e akışı (UX-28) sahte sunucuyla deterministik çalışır.
- **Meta:** P0 · M · Bağ: GW-01 · Durum: açık

#### OPS-11 · Özellik bayrakları
- **Sorun:** [ÖNERİ] Deneysel/yarım özellikler (konsey, CoVe, GraphRAG, difüzyon) açık/kapalı yönetilemiyor.
- **Değişiklik:** `features` yapılandırması/tablosu: varsayılan, kullanıcı/rol bazlı, eval kapılı özellikler "kanıtlanana kadar kapalı"; `/api/assistant/config` yetenek bildirimi (DEF-15).
- **Kabul:** Kapalı özellik hiçbir yolla tetiklenmez (test); bayrak değişikliği denetim izine yazılır.
- **Meta:** P1 · S · Bağ: DEF-15 · Durum: açık

#### OPS-12 · Sürüm yönetimi
- **Sorun:** [ÖNERİ] Sürüm numarası, değişiklik günlüğü ve etiket süreci yok.
- **Değişiklik:** SemVer, Conventional Commits, otomatik `CHANGELOG.md`, sürüm etiketi ve notları, `main` koruması ve PR zorunluluğu.
- **Kabul:** Etiket oluşturunca değişiklik günlüğü ve sürüm notu otomatik üretilir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### OPS-13 · Bağımlılık yönetimi
- **Sorun:** [DOĞRULANDI: F6] Kilit dosyası ve otomatik güncelleme yok; eksik bağımlılık ancak temiz ortamda ortaya çıktı.
- **Değişiklik:** `uv`/pip-tools kilidi (DEF-13), Dependabot/Renovate, lisans denetimi, CycloneDX SBOM, GPL/AGPL bağımlılık uyarısı.
- **Kabul:** Kilit dosyası güncel değilse CI kırmızı; lisans ihlali raporlanır.
- **Meta:** P1 · S · Bağ: DEF-13 · Durum: açık

#### OPS-14 · Mimari karar kayıtları (ADR)
- **Sorun:** [ÖNERİ] Önemli kararlar (LiteLLM kaldırma, SQLite, Tailscale, bulut sağlayıcı) yazılı gerekçesiz.
- **Değişiklik:** `docs/adr/NNNN-*.md` şablonuyla D1–D8 ve sonraki kararlar; plan maddeleri ilgili ADR'ye bağlanır.
- **Kabul:** D1–D8 için ADR vardır; değişiklik gerektiren karar yeni ADR ile yapılır (PR kontrol listesi).
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### OPS-15 · Çalıştırma kılavuzları (runbook)
- **Sorun:** [DOĞRULANDI] Bu denetimde yaşanan sorunlar (Tailscale bağlanamama, Ollama/model eksik, IPv6/TLS, ajan kopuk) için yazılı çözüm yok.
- **Değişiklik:** `docs/runbooks/`: Ollama çöktü, model eksik, disk doldu, DB kilitli, ajan çevrimdışı, Tailscale bağlanamıyor (DNS/IPv6/TLS/ISS), eval gerilemesi, yedekten dönüş; her biri belirti → teşhis → çözüm.
- **Kabul:** Her `/ready` uyarı türü bir runbook'a bağlantı verir.
- **Meta:** P1 · M · Bağ: OPS-03 · Durum: açık

#### OPS-16 · Yük ve performans testleri
- **Sorun:** [ÖNERİ] Eşzamanlı kullanımda davranış ölçülmedi; Ollama kuyruğunun etkisi bilinmiyor.
- **Değişiklik:** Locust/k6: 10 eşzamanlı sohbet, 5 proje üretimi, 3 araştırma; bütçeler: p95 TTFT, bellek tepe, hata oranı; sonuçlar raporda.
- **Kabul:** Hedef yükte hata oranı < %1 ve TTFT bütçesi sağlanır; regresyon kapısı gece işi.
- **Meta:** P2 · M · Bağ: GW-09 · Durum: açık

#### OPS-17 · Dayanıklılık (kaos) testleri
- **Sorun:** [ÖNERİ] Ollama yeniden başlatma, disk dolu, DB kilidi, ağ kesintisi altında davranış sınanmıyor.
- **Değişiklik:** Hata enjeksiyonu paketi: Ollama durdurma/başlatma, disk dolu simülasyonu, DB kilidi, ağ kesintisi, yavaş yanıt; beklenen zarif düşüş davranışları testlenir.
- **Kabul:** Her senaryoda veri kaybı 0 ve kullanıcı bilgilendirilir; toparlanma otomatik.
- **Meta:** P2 · M · Bağ: GW-08, DIST-22 · Durum: açık

#### OPS-18 · Kaynak koruması
- **Sorun:** [DOĞRULANDI: F20] İstek başına bellek/süre sınırı yok; büyük dosyalar belleğe okunuyor (`await file.read()`), ZIP açma sınırsız.
- **Değişiklik:** Akışlı yükleme/işleme, istek başına bellek ve süre sınırı, arka plan iş bütçeleri, eşzamanlı ağır iş sınırı; OOM öncesi reddetme.
- **Kabul:** 200 MB dosya yüklemesi bellek tepe < 300 MB ile işlenir; sınır aşımında net hata.
- **Meta:** P1 · M · Bağ: SEC-07 · Durum: açık

#### OPS-19 · Hata izleme
- **Sorun:** [ÖNERİ] Yakalanmamış istisnalar yalnız terminalde kalıyor.
- **Değişiklik:** Yerel hata toplayıcı (günlük özeti veya GlitchTip, isteğe bağlı), yineleyen hata gruplama, yönetici uyarısı; gizlilik filtresi.
- **Kabul:** Zorla atılan istisna toplayıcıda gruplanır ve uyarı üretir; içerik maskeli.
- **Meta:** P2 · M · Bağ: OPS-01, SEC-23 · Durum: açık

#### OPS-20 · Kod kalitesi kapıları
- **Sorun:** [DOĞRULANDI: F9] 9 fonksiyon 150 satırı aşıyor (`_chat_stream_impl` 575, `analyze_3d_cad_file` 342, `export_excel_report` 225...); karmaşıklık denetimi yok.
- **Değişiklik:** `radon`/ruff `C901` ve fonksiyon uzunluğu eşiği (≤ 150, hedef ≤ 80), bağlantı kapısı (DEF-01), modül boyutu uyarısı; mevcut ihlaller izin listesinde azalan sayıyla.
- **Kabul:** İhlal sayısı izin listesinde 9 → 0'a iner; yeni ihlal CI'ı kırar.
- **Meta:** P1 · S · Bağ: DEF-01 · Durum: açık

#### OPS-21 · Pre-commit kancaları
- **Sorun:** [ÖNERİ] Hatalar CI'a kadar fark edilmiyor (bu denetimde `import sys` ruff hatası ve satır sonu uyarıları gibi).
- **Değişiklik:** `pre-commit`: ruff, format, gitleaks, JSON/YAML denetimi, satır sonu, büyük dosya engeli; yerel hızlı geri bildirim.
- **Kabul:** Kurulumdan sonra hatalı commit yerelde reddedilir; CI ile aynı kurallar.
- **Meta:** P2 · S · Bağ: SEC-20 · Durum: açık

#### OPS-22 · Belgelendirme sitesi
- **Sorun:** [DOĞRULANDI] `docs/user-guide.md`, `architecture.md` var; güncelliği kod değişimleriyle doğrulanmıyor.
- **Değişiklik:** MkDocs (yerel): mimari, kullanıcı, geliştirici, API (OpenAPI'den otomatik), runbook'lar, ADR'ler; bozuk bağlantı denetimi CI'da; kod örnekleri çalıştırılarak doğrulanır.
- **Kabul:** Belge sitesi yerelde derlenir; bozuk bağlantı 0; API belgesi güncel OpenAPI'den.
- **Meta:** P2 · M · Bağ: OPS-14 · Durum: açık

#### OPS-23 · Demo ve sunum kiti
- **Sorun:** [ÖNERİ] Ders gösterimi için tekrarlanabilir senaryo ve yedek plan yok; bu denetimde ağ sorunu gösterimi riske attı.
- **Değişiklik:** `scripts/demo_*.ps1` senaryoları, örnek veri, "gösterimden önce kontrol listesi" (Tailscale, Ollama, modeller, portlar), çevrimdışı yedek video/ekran görüntüleri, tek komutla "demo moduna al".
- **Kabul:** Kontrol listesi betiği 10 dk içinde tüm bağımlılıkları doğrular ve eksiği raporlar.
- **Meta:** P1 · M · Bağ: OPS-04, PROC-06 · Durum: açık

#### OPS-24 · Kaynak ve enerji yönetimi
- **Sorun:** [ÖNERİ] Dizüstü/yerel GPU üzerinde model sürekli bellekte kalıyor; ısı/pil sorunları olabilir.
- **Değişiklik:** Boşta modelleri boşaltma politikası, güç profili (pilde küçük model), GPU/CPU kullanım ölçümü, uyarılar.
- **Kabul:** Boşta 10 dk sonra model boşaltılır (`/api/ps` ile doğrulanır); pil modunda büyük model yerine küçük model önerilir.
- **Meta:** P3 · S · Bağ: GW-06 · Durum: açık

---

## C. PROC — Scrum Süreci, Ders Gereksinimleri ve Belgeler

> Bu bölüm, hocanın gereksinimlerinin (Scrum, Trello, GitHub, 5 sprint, sprint review/retro/progress raporu, ajan/model karşılaştırma) **izlenebilir ve otomatik** karşılanmasını sağlar. Plan genişledikçe ders teslimi gözden kaçmamalı.

#### PROC-01 · Gereksinim izlenebilirlik matrisi
- **Sorun:** [ÖNERİ] Hoca PDF'indeki maddelerin (S1–S5) hangi özellik, test ve belgeyle karşılandığı tek yerde yok.
- **Değişiklik:** `docs/scrum/traceability.md`: PDF maddesi → özellik → test → belge/ekran görüntüsü; betikle üretilip CI'da tutarlılığı doğrulanır (bağlantılar çözülür).
- **Kabul:** Tüm PDF maddeleri (5 sprint, ~30 madde) bir teste/belgeye bağlı; kırık bağlantı 0.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### PROC-02 · Bu planın ürün backlog'una eşlenmesi ve Trello senkronu
- **Sorun:** [ÖNERİ] Plan maddeleri Scrum backlog'u ve Trello'dan kopuk; yeni sprint planlama zor.
- **Değişiklik:** Plan maddeleri → PB-xx eşlemesi (öncelik/efor), sprint adayı seçimi; Trello'ya tek yönlü aktarım betiği (API anahtarı yalnız ortam değişkeninden, **repoya/Trello'ya sır yazılmaz**).
- **Kabul:** Betik kuru çalıştırmada kartları listeler; gerçek aktarımda tekrar çalıştırma yinelenen kart oluşturmaz.
- **Meta:** P1 · M · Bağ: PROC-09 · Durum: açık

#### PROC-03 · Otomatik Scrum belgeleri
- **Sorun:** [DOĞRULANDI] Sprint belgeleri elle yazılmış (`docs/scrum/sprint-N/*`); burndown yalnız Sprint 1'de SVG.
- **Değişiklik:** Git + backlog + PROGRESS verisinden sprint backlog, burndown SVG, ilerleme raporu, review/retro taslağı üretici betik; günlük scrum notu şablonu.
- **Kabul:** Betik her sprint için gerçek veriden burndown ve rapor üretir; elle düzenleme taslak üstüne yapılır.
- **Meta:** P2 · M · Bağ: PROC-09 · Durum: açık

#### PROC-04 · Definition of Done güncellemesi
- **Sorun:** [DOĞRULANDI] `docs/scrum/definition-of-done.md` var ama bu denetimde ortaya çıkan kalite kapılarını (bağlantı, kimlik, eval, atıf) içermiyor.
- **Değişiklik:** DoD maddeleri: kabul testi, **bağlantı kapısı geçti**, yetki testi, eval eşiği, güvenlik kontrolü, dokümantasyon, demoda gösterilebilir.
- **Kabul:** DoD PR şablonunda kontrol listesi olarak bulunur; maddesiz PR birleştirilemez.
- **Meta:** P1 · S · Bağ: DEF-01 · Durum: açık

#### PROC-05 · Katkı kuralları ve inceleme kontrol listesi
- **Sorun:** [ÖNERİ] Birden çok kişi/yapay zekâ aracı değişiklik yapıyor (Antigravity, Claude vb.); hepsi aynı kalite beklentisine tabi olmalı.
- **Değişiklik:** `CONTRIBUTING.md` güncellemesi: yapay zekâ araçları için kurallar ("tamam" demeden önce kanıt, `plan_tool.py` kapıları, yer tutucu yasağı), PR şablonu, inceleme kontrol listesi (halüsinasyon/yetki/bağlantı/test).
- **Kabul:** PR şablonu kontrol listesi içerir; yapay zekâ aracı çıktıları için "kanıt" bölümü zorunlu.
- **Meta:** P1 · S · Bağ: PROC-04 · Durum: açık

#### PROC-06 · Demo senaryosu
- **Sorun:** [ÖNERİ] Ders gösterimi akışı yazılı ve prova edilmiş değil.
- **Değişiklik:** 10 dakikalık akış: ajan bağlama (Tailscale) → gereksinim yükleme → master ayrıştırma → yetenek tabanlı dağıtım → çıktı atfı → hata kurtarma (ajan öldür) → çakışma çözümü → pano/model karşılaştırma; canlı + yedek video.
- **Kabul:** Senaryo betikle (OPS-23) iki kez baştan sona sorunsuz oynatılır; her adımın beklenen ekranı belgelenmiş.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### PROC-07 · Akademik rapor ve ölçüm grafikleri
- **Sorun:** [ÖNERİ] Ders raporu için ölçümler (model karşılaştırma, hızlanma, halüsinasyon) elle toplanıyor.
- **Değişiklik:** `eval/` ve `perf` çıktılarından otomatik grafik/tablo (CSV → PNG/LaTeX); rapor iskeleti: mimari, yöntem, deneyler, bulgular, sınırlılıklar, gelecek çalışma.
- **Kabul:** Rapor şekilleri tek komutla yeniden üretilir; sayılar eval/pano verisiyle birebir.
- **Meta:** P1 · M · Bağ: DIST-19, HAL-03 · Durum: açık

#### PROC-08 · Etik, gizlilik ve model lisansları
- **Sorun:** [ÖNERİ] Kullanılan modellerin (Qwen, Llama, Phi, Gemma...) lisans/kullanım şartları ve veri gizliliği notları derlenmemiş.
- **Değişiklik:** Model × lisans × ticari/akademik kullanım × kısıt tablosu; KVKK ve yerel işleme beyanı; üretilen içeriğin sorumluluk notu; damıtma/ince ayarda lisans denetimi (ML-13).
- **Kabul:** Registry'deki her model için lisans alanı dolu; tablo CI'da registry ile karşılaştırılır.
- **Meta:** P2 · S · Bağ: GW-03 · Durum: açık

#### PROC-09 · Hesaplanan ilerleme dosyası
- **Sorun:** [DOĞRULANDI: F16] Önceki ilerleme dosyası kendi beyanına dayalı "completed" listesiydi; hiçbiri kanıtlı değildi.
- **Değişiklik:** `docs/plan-v2/PROGRESS.json`: her madde için `status` yalnızca kanıtla hesaplanır: kabul testi ID'si + commit + (gerekiyorsa) eval raporu + bağlantı kapısı sonucu; `plan_tool.py status` bunu üretir ve "kanıtsız bitti" iddiasını reddeder.
- **Kabul:** Kanıtı olmayan madde "bitti" olarak işaretlenemez (test); rapor toplam/kalan/engelli madde sayısını verir.
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### PROC-10 · Risk kaydı ve MVP kesme çizgisi
- **Sorun:** [ÖNERİ] Plan çok büyük; ders teslimi için hangi maddelerin zorunlu olduğu ve riskler yazılı değil.
- **Değişiklik:** `08-yol-haritasi-riskler.md` risk tablosu (olasılık/etki/azaltma) haftalık gözden geçirme; "ders teslimi MVP" listesi (P0 alt kümesi), kapsam kayması denetimi.
- **Kabul:** MVP listesi ders gereksinimleriyle (PROC-01) çakışmaz eksiksiz örter; riskler haftalık güncellenir.
- **Meta:** P1 · S · Bağ: PROC-01 · Durum: açık
