# Parça 6 — Dağıtık Ajan Mimarisi (DIST) ve Arayüz (UX)

## A. DIST — Dağıtık Ajanlar (dersin çekirdek gereksinimi)

**Hoca gereksinimi (CM6453 PDF):** her bilgisayarda LLM tabanlı bir ajan; master ajan görevleri alt görevlere böler, **ajanların yeteneklerini değerlendirip** (kodlama/akıl yürütme/bağlam puanları) rastgele değil bilinçli dağıtır; sonuçları toplar ve entegre eder; test, kod inceleme, hata kurtarma, çakışma çözümü, başarısız görevin yeniden atanması, pano, performans ölçümü ve model karşılaştırması.

**Bugünkü durum [DOĞRULANDI: F12]:** Bu mimari yalnız Scrum **proje görev hattında** çalışıyor (kayıt, heartbeat, kuyruk, kiralama, doğrulama, inceleme görevleri, yeniden kuyruğa alma). Sohbet, stüdyo, araştırma ve sunum master'da tek düğümle yürüyor; `swarm_coordinator`, `map_reduce_llm`, `fault_tolerance`, `bandit_router`, `cluster_telemetry` (sıcak model) erişilemez. Bu parça mimariyi **ürünün tamamına** yayar ve dersin kabul kriterlerini ölçülebilir kılar.

#### DIST-01 · Ajan yetenek profili standardı
- **Sorun:** [DOĞRULANDI: F12] Profil alanları (`model_family`, `parameter_size`, `context_length`, `capabilities`...) var; ancak donanım, yük ve ölçülmüş benchmark puanları tek şemada sürümlü değil; `start_agents.py` demo yolunda bu alanlar sabit tablodan geliyor.
- **Değişiklik:** `agent_profile` JSON şeması (sürümlü): model bilgisi (Ollama `/api/show`), donanım (VRAM/RAM/CPU), yetenekler, benchmark puanları (coding/reasoning/context/structured/speed + halüsinasyon HAL-28), anlık yük, sıcak modeller; `agent/model_info.py` genişletilir.
- **Kabul:** Her kayıtlı ajanın profili şemaya uyar (doğrulayıcı); profil alanlarının tamamı gerçek kaynaktan (sabit tablo yok); sürüm uyuşmazlığında master eski ajanı reddetmez, uyarır.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### DIST-02 · Benchmark paketi ve periyodik yeniden değerlendirme
- **Sorun:** [DOĞRULANDI] `benchmarks.py` görevleri ve `tasks_api._score_benchmark_task` var; görev sayısı/çeşitliliği küçük, puanlayıcı kalibrasyonu belirsiz, geçmiş skor eğilimi görünmüyor.
- **Değişiklik:** Her boyut için ≥ 10 deterministik görev (kod: test geçen çözüm, akıl yürütme: doğrulanabilir cevap, bağlam: uzun belgede iğne arama, yapılandırılmış çıktı: şema uyumu, hız: tok/s); sonuçlar zaman serisi; periyodik ve model değişince otomatik yeniden değerlendirme.
- **Kabul:** Aynı ajan ardışık iki koşuda ±5 puan içinde tutarlı (tekrarlanabilirlik); skor geçmişi grafiği ve "puan neden değişti" notu.
- **Meta:** P0 · L · Bağ: DIST-01 · Durum: açık

#### DIST-03 · Seçim algoritmasının eval ile ayarlanması ve açıklanabilirliği
- **Sorun:** [DOĞRULANDI] `selection.py`/`task_weights.py` ağırlıklı skorla seçiyor; ağırlıklar elle verilmiş, seçimin sonucu (görev başarısı) ağırlıkları ayarlamak için kullanılmıyor.
- **Değişiklik:** Skor = görev ağırlıkları × ajan puanları + sıcak model/yük/geçmiş başarı (bandit) − maliyet; ağırlıklar geçmiş görev sonuçlarından (başarı/süre/yeniden deneme) ayarlanır; her atamada gerekçe kaydı ve arayüzde "neden bu ajan".
- **Kabul:** Rastgele atamaya göre ortalama görev başarısı ≥ 15 puan, süre ≥ %20 daha iyi (simülasyon + gerçek koşu); her atama gerekçesi görünür.
- **Meta:** P0 · L · Bağ: DIST-02, DIST-04 · Durum: açık

#### DIST-04 · Thompson Sampling yönlendiricisinin bağlanması
- **Sorun:** [DOĞRULANDI: F1/F12] `bandit_router` ve `cluster_telemetry.ThompsonBanditRouter` erişilemez; seçim deterministik, keşif yok.
- **Değişiklik:** Beta(α,β) başarı/başarısızlık sayaçları (görev türü × ajan), keşif/sömürü dengesi; `tasks_api` seçiminde ve gateway'de (GW-04) kullanılır; sayaçlar kalıcı.
- **Kabul:** Sentetik ajan simülasyonunda 200 görevde en iyi ajana yakınsama (regret sınırı) testi; kapatılabilir ve belgelenmiş.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DIST-05 · Görev sınıflandırma taksonomisinin hizalanması
- **Sorun:** [ÖNERİ] Scrum hattındaki görev türleri (`backend`, `frontend`, `testing`, `documentation`, `review`...) ile sohbet niyetleri (ORC-03) ayrı kavramlar.
- **Değişiklik:** Tek görev türü sözlüğü; niyet → görev türü eşleme tablosu; ağırlık tablosu bu sözlükten üretilir.
- **Kabul:** Her niyet bir görev türüne eşlenir (test); yeni tür eklemek ağırlık tablosuna otomatik yansır.
- **Meta:** P1 · S · Bağ: ORC-03 · Durum: açık

#### DIST-06 · Kiralama, yeniden atama ve idempotent sonuç
- **Sorun:** [DOĞRULANDI] Kiralama süresi dolunca yeniden atama var (`start_lease_expiry`); aynı görev için çift sonuç gönderimi ve yarış durumları test edilmemiş.
- **Değişiklik:** Sonuç gönderimi idempotent (görev sürüm numarası/ETag), süresi dolmuş kiralama sonucu reddedilir veya "geç sonuç" olarak saklanır; yarış testleri; yeniden deneme sayacı ve geri çekilme.
- **Kabul:** Aynı sonuç iki kez gönderilince bir kez işlenir; kiralaması dolan ajanın geç sonucu aktif atamayı ezmez (test).
- **Meta:** P0 · M · Bağ: SEC-18 · Durum: açık

#### DIST-07 · Ajan yetkilendirme ve sonuç sahipliği
- **Sorun:** [DOĞRULANDI: F13] Ortak token; `submit_result` çağıranın atanmış ajan olduğunu doğrulamıyor.
- **Değişiklik:** SEC-18 uygulanır: ajan başına anahtar, sonuç yalnız `assigned_to` ajandan; yönetici arayüzünden anahtar iptali.
- **Kabul:** Başka ajan adına sonuç gönderimi 403; iptal edilen ajan görev alamaz (test).
- **Meta:** P0 · M · Bağ: SEC-18 · Durum: açık

#### DIST-08 · Checkpoint ve görev devri
- **Sorun:** [DOĞRULANDI: F1/F12] `fault_tolerance` (checkpoint/göç) erişilemez; uzun görevde ajan kopunca iş baştan başlar.
- **Değişiklik:** Uzun görevlerde adım bazlı ara çıktı (checkpoint); ajan kopunca başka ajan checkpoint'ten sürdürür; checkpoint boyutu/ömrü sınırlı.
- **Kabul:** 10 dk'lık görevde ajan 5. dk'da öldürülür, görev başka ajanda ≤ 6 dk'da biter (baştan başlamaktan kısa; chaos testi).
- **Meta:** P1 · L · Bağ: DIST-06 · Durum: açık

#### DIST-09 · Map-Reduce yürütmenin bağlanması
- **Sorun:** [DOĞRULANDI: F1/F12] `map_reduce_llm` erişilemez; büyük belge/çok dosyalı üretim tek düğümde sıralı.
- **Değişiklik:** Map: parçalar ajanlarda paralel; Reduce: master birleştirme + tutarlılık denetimi (çelişki/tekrar); kısmi başarısızlıkta yalnız başarısız parça yeniden çalıştırılır.
- **Kabul:** 6 ajanla 200 sayfalık belge analizi ve 15 dosyalı proje üretimi tek ajana göre ≥ 3x hızlı; birleştirilmiş sonuç parçalarla çelişmez (denetim).
- **Meta:** P0 · L · Bağ: ORC-07, DIST-08 · Durum: açık

#### DIST-10 · Yük dengeleme ve iş çalma
- **Sorun:** [ÖNERİ] Hızlı ajan boşta kalırken yavaş ajanın kuyruğu uzayabilir.
- **Değişiklik:** Ajan başına kuyruk derinliği/tahmini bitiş süresi; boşta ajan, uyumlu görev türünde en uzun kuyruktan iş çalar; çalma kiralama kurallarına uyar.
- **Kabul:** Heterojen 6 ajanla 60 görevlik koşuda toplam süre statik atamaya göre ≥ %20 kısa (simülasyon + gerçek).
- **Meta:** P2 · M · Bağ: DIST-06 · Durum: açık

#### DIST-11 · Canlı ajan durumu (SSE) ve telemetri
- **Sorun:** [DOĞRULANDI] Ajanlar sayfası 10 sn aralıkla sorguluyor (yapıldı); gerçek zamanlı değil, telemetri (VRAM, sıcaklık, tok/s) görünmüyor.
- **Değişiklik:** `GET /api/agents/stream` SSE (durum değişimi anında), telemetri alanları (VRAM kullanımı, yüklü modeller, tok/s, kuyruk), çevrimdışı eşik ayarı; arayüz rozetleri.
- **Kabul:** Ajan kapatılınca arayüz ≤ 15 sn'de "çevrimdışı" gösterir (heartbeat'e bağlı), durum değişimi için sorgulama yok.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DIST-12 · Heterojen donanım politikası
- **Sorun:** [ÖNERİ] CPU-only ve GPU'lu makineler aynı görevlere atanıyor; model/bellek uyuşmazlığı yavaşlık/OOM yaratıyor.
- **Değişiklik:** Donanım sınıfı (GPU/CPU, VRAM) → izinli model boyutu ve görev ağırlığı; yetersiz belleğe sahip ajana büyük model görevi atanmaz; model çekme (pull) yalnız kullanıcı onayıyla.
- **Kabul:** 4 GB VRAM'li ajana 9B görev atanmaz (test); OOM kaynaklı görev başarısızlığı 0 (simülasyon).
- **Meta:** P1 · M · Bağ: DIST-01 · Durum: açık

#### DIST-13 · Tailscale ağı: keşif, kimlik ve güvenli bağlama
- **Sorun:** [DOĞRULANDI: F2] Ajanlar master adresini elle girer; master `0.0.0.0`'a bağlı; güvenlik duvarı kuralı kapsamı geniş (SEC-24). Ev ağında Tailscale kontrol sunucusuna ulaşma sorunu (IPv6/TLS) yaşandı; ağ tanılama yok.
- **Değişiklik:** `tailscale status --json` ile ajan adayı/IP keşfi, MagicDNS adları, master'ın yalnız tailnet IP'sine bağlanması, ajan tarafı bağlantı tanılama (DNS, IPv4/IPv6, TLS, port) ve "neden bağlanamıyorum" kontrol listesi, ACL öneri belgesi.
- **Kabul:** Tanılama betiği bilinen 5 arıza türünü (control plane erişilemez, port kapalı, yanlış IP, ACL engeli, sürüm uyuşmazlığı) doğru sınıflandırır; master tailnet dışı arayüzden erişilemez.
- **Meta:** P0 · M · Bağ: SEC-24 · Durum: açık

#### DIST-14 · Tek komutla ajan kurulumu ve servisleştirme
- **Sorun:** [DOĞRULANDI] `agent-node/setup.ps1|sh` var; model çekme, servis olarak çalıştırma, otomatik başlatma, güncelleme akışı sınırlı/doğrulanmamış.
- **Değişiklik:** Kurulum betiği: Ollama kontrol/kurulum yönlendirmesi, model çekme (onaylı), ajan kaydı, Windows görev zamanlayıcı/servis, otomatik güncelleme, kaldırma; her adım doğrulanır ve hata mesajları eyleme dönük.
- **Kabul:** Temiz Windows ve Linux makinede betik tek komutla ajanı kaydeder ve heartbeat'e başlatır (belgelenmiş test planı + CI'da konteynerde Linux testi).
- **Meta:** P1 · M · Bağ: DIST-01 · Durum: açık

#### DIST-15 · Çıktı entegrasyonu ve çakışma çözümü (arayüzlü)
- **Sorun:** [DOĞRULANDI: F17] `conflict_detector` aynı dosyaya yazan görevleri tespit ediyor; çözme uç noktaları (`/conflicts`, `/resolve`) var ama arayüz yok ve otomatik birleştirme yok.
- **Değişiklik:** Çakışan çıktılar için yan yana diff ve 3 yollu otomatik birleştirme (mümkünse), çözülemeyen çakışma için "birini seç/elle birleştir/yeniden üret" arayüzü; çözüm sonrası ilgili testlerin yeniden çalışması.
- **Kabul:** 20 çakışma senaryosunda ≥ %70 otomatik çözülür, kalanı arayüzden çözülür; çözüm sonrası proje çıktısı derlenir/test geçer.
- **Meta:** P0 · L · Bağ: - · Durum: açık

#### DIST-16 · Kod inceleme ajanı kalitesi
- **Sorun:** [DOĞRULANDI] İnceleme görevleri gerçek kodla oluşturuluyor ve yazar≠inceleyici kuralı var; inceleme bulgularının kalitesi ve düzeltme görevine dönüşme akışı ölçülmemiş, `fix-tasks` arayüzü yok.
- **Değişiklik:** İnceleme çıktısı yapılandırılmış (önem, dosya:satır, açıklama, öneri); bulgudan düzeltme görevi (arayüzden onayla), inceleme isabeti eval'i (bilerek hatalı kodlarda yakalama).
- **Kabul:** Bilerek hata eklenmiş 40 kodda inceleme recall'u ≥ %70, uydurma bulgu < %15; bulgu → düzeltme görevi → yeniden inceleme döngüsü çalışır.
- **Meta:** P1 · L · Bağ: DIST-17 · Durum: açık

#### DIST-17 · Test ajanı: gerçek yürütme
- **Sorun:** [ÖNERİ] Test görevleri test **metni** üretiyor; testlerin çalıştırılıp sonucunun görev çıktısına işlendiği garanti değil.
- **Değişiklik:** Üretilen test ve ilgili kod sandbox'ta çalıştırılır (SEC-13), sonuç (geçti/kaldı/hata) görev çıktısına ve proje özetine yazılır; başarısız test ilgili kod görevini yeniden açar.
- **Kabul:** 10 projede test görevi çıktısı gerçek `pytest` sonucunu içerir; başarısız test kod görevini yeniden kuyruğa alır (test).
- **Meta:** P0 · L · Bağ: SEC-13, DIST-06 · Durum: açık

#### DIST-18 · Hata kurtarma politikası
- **Sorun:** [DOĞRULANDI] Başarısız görev yeniden kuyruğa alınıyor; deneme sayısı sonrası davranış, model yükseltme ve insana yönlendirme tanımsız.
- **Değişiklik:** Politika: 1. deneme aynı ajan → 2. farklı ajan → 3. daha güçlü ajan/konsey → kalıcı hata (insana raporla + nedeni); hata türü sınıflaması (bağlantı, model, çıktı geçersiz, doğrulama başarısız).
- **Kabul:** Her hata türü için beklenen yol testlenir; kalıcı hata kullanıcıya özet ve önerilen eylemle bildirilir.
- **Meta:** P1 · M · Bağ: DIST-06 · Durum: açık

#### DIST-19 · Performans panosu ve model karşılaştırması
- **Sorun:** [DOĞRULANDI] `/api/perf/stats` ve pano var; model/ajan × görev türü başarı matrisi, halüsinasyon profili ve dışa aktarma yok. Dersin Sprint 5 gereksinimi "ajan/model karşılaştırması".
- **Değişiklik:** Ajan × görev türü başarı oranı, tok/s, gecikme, yeniden deneme (halüsinasyon oranı sütunu HAL-28 tamamlanınca eklenir); radar/tablo karşılaştırma; zaman aralığı; CSV/PNG dışa aktarma; rapor sayfası (PROC-07 için).
- **Kabul:** Pano değerleri veritabanı toplamlarıyla birebir uyumlu (test); dışa aktarılan CSV akademik rapora doğrudan girer.
- **Meta:** P0 · M · Bağ: DIST-02 · Durum: açık

#### DIST-20 · Kaynak izlenebilirliği (provenance)
- **Sorun:** [DOĞRULANDI] Görev çıktısında "Üreten: ajan·model·tok/s" gösteriliyor (bu denetimde eklendi); proje ZIP'inde hangi dosyayı hangi ajanın üretttiği kaydı yok.
- **Değişiklik:** Proje çıktısına `PROVENANCE.json`: dosya → görev → ajan → model → istem özeti → sürüm → doğrulama sonucu; arayüzde dosya başına "üreten" rozeti.
- **Kabul:** ZIP'teki her dosya `PROVENANCE.json`'da kayıtlı (test); rozet gerçek `performed_by` verisinden gelir.
- **Meta:** P1 · S · Bağ: ORC-17 · Durum: açık

#### DIST-21 · Dağıtık hızlanma ölçümü
- **Sorun:** [ÖNERİ] "Dağıtık daha hızlı" iddiası ölçülmüyor.
- **Değişiklik:** Standart iş yükleri (15 dosyalı proje, 8 alt soruluk araştırma, 200 sayfa analiz) 1/2/4/6 ajanla koşturulur; hızlanma ve verim grafiği; Amdahl analizi (seri kısımlar).
- **Kabul:** 6 ajanla ≥ 3x hızlanma (hedef) veya sınırlayıcı seri kısım belgeli; rapor otomatik üretilir.
- **Meta:** P1 · M · Bağ: DIST-09 · Durum: açık

#### DIST-22 · Kaos testi ve toparlanma senaryoları
- **Sorun:** [ÖNERİ] Hata kurtarma (dersin Sprint 4 gereksinimi) yalnız birim testlerle sınanıyor; gösterimde canlı kanıt yok.
- **Değişiklik:** `scripts/chaos/*.ps1`: ajan öldürme, ağ kesme (Tailscale), yavaş ajan, Ollama çökmesi, master yeniden başlatma; toparlanma süresi ve görev kaybı ölçümü; gösteri senaryosu (PROC-06).
- **Kabul:** Her senaryoda görev kaybı 0 ve toparlanma < 60 sn (hedef); sonuçlar rapora otomatik girer.
- **Meta:** P1 · M · Bağ: DIST-08, DIST-18 · Durum: açık

---

## B. UX — Arayüz, Erişilebilirlik ve Geliştirici Deneyimi

> Bugünkü durum [DOĞRULANDI: F15]: ~6.000 satır vanilla JS (`assistant.js` 1952, `personal.js` 855, `projects.js` 558...), `package.json` yok → lint, tip denetimi, birim/e2e test, derleme yok. Mesaj yeniden üretme/düzenleme yok; `aria-` yalnız 3 dosyada; erişilebilirlik ve çok dilli destek tutarsız. Güçlü yanlar: çevrimdışı çalışma (CDN yok), tutarlı koyu tema, akış deneyimi, IDE paneli.

#### UX-01 · Derleme zinciri: ES modül + TypeScript (kademeli) + lint + test
- **Sorun:** [DOĞRULANDI: F15] Frontend için hiçbir kalite kapısı yok; backend sözleşmesiyle tip bağı yok (DEF-17).
- **Değişiklik:** `frontend/` altında `package.json`, Vite (ES modül, CDN yok), TypeScript `checkJs` ile kademeli geçiş, ESLint + Prettier, Vitest (birim), OpenAPI'den tip üretimi; derleme çıktısı `master/static/` altına; CI'da çalışır.
- **Kabul:** `npm run lint && npm run typecheck && npm test && npm run build` temiz ve CI'da yeşil; backend response şeması değişince frontend derlemesi kırılır.
- **Meta:** P0 · L · Bağ: - · Durum: açık

#### UX-02 · `assistant.js` ve dev dosyaların bileşenlere ayrılması
- **Sorun:** [DOĞRULANDI: F15] `assistant.js` 1952 satır: sohbet, akış, IDE, ekler, ses, araçlar tek dosyada; değişiklik riski yüksek.
- **Değişiklik:** Modüller: `chat/`, `stream/`, `ide/`, `attachments/`, `voice/`, `artifacts/`; tek sorumluluk, ≤ 300 satır; arayüz sözleşmeleriyle birim testli.
- **Kabul:** Hiçbir frontend dosyası 500 satırı geçmez (lint kapısı); mevcut davranışlar e2e testlerle (UX-28) korunur.
- **Meta:** P1 · XL · Bağ: UX-01 · Durum: açık

#### UX-03 · Durum yönetimi ve depolama şeması sürümü
- **Sorun:** [DOĞRULANDI] `localStorage` kullanımı dağınık; şema sürümü/göç yok; durum bileşenler arasında paylaşılıyor.
- **Değişiklik:** Küçük reaktif store (signals), sohbet/oturum/ayar durumu tek kaynak; `localStorage`/IndexedDB şema sürümü ve göç; kayıt hatasında zarif düşüş (gizli pencere).
- **Kabul:** Eski depolama şemalı veri yeni sürümde göç eder (test); depolama kapalıyken uygulama çalışır.
- **Meta:** P1 · M · Bağ: UX-01 · Durum: açık

#### UX-04 · Tasarım sistemi ve tema birleştirme
- **Sorun:** [DOĞRULANDI] `app.css` (825 satır) ve `theme.css` (480 satır) ayrı; bileşen kuralları tutarsız olabilir.
- **Değişiklik:** CSS jetonları (renk/boşluk/tipografi/gölge), bileşen kitaplığı (düğme, kart, rozet, modal, sekme, tablo, toast, form), karanlık/aydınlık/yüksek kontrast; kullanılmayan CSS temizliği.
- **Kabul:** Tüm bileşenler üç temada kontrast ≥ AA (otomatik); ölü CSS oranı < %5.
- **Meta:** P2 · L · Bağ: UX-01 · Durum: açık

#### UX-05 · Erişilebilirlik (WCAG 2.2 AA)
- **Sorun:** [DOĞRULANDI: F15] ARIA/klavye gezinme eksik; akış sırasında ekran okuyucu bildirimi yok.
- **Değişiklik:** Klavye ile tam gezinme, odak yönetimi (modal/çekmece), ARIA rolleri ve canlı bölgeler (akış ilerlemesi), kontrast, `prefers-reduced-motion`, odak halkası; axe-core CI denetimi.
- **Kabul:** axe-core kritik/ciddi ihlal 0; yalnız klavye ile sohbet, dosya yükleme ve ayarlar kullanılabilir (e2e).
- **Meta:** P1 · L · Bağ: UX-04 · Durum: açık

#### UX-06 · Çok dil (TR/EN) ve yerelleştirme
- **Sorun:** [ÖNERİ] Arayüz metinleri kod içine gömülü Türkçe; sayı/tarih biçimleri tutarsız.
- **Değişiklik:** Dize dosyaları (TR/EN), `Intl` ile sayı/tarih/saat, çoğul kuralları, dil seçici; çevrilmemiş anahtar CI uyarısı.
- **Kabul:** Dil değişimi tüm sayfaları kapsar; eksik çeviri anahtarı 0.
- **Meta:** P2 · M · Bağ: UX-01 · Durum: açık

#### UX-07 · Duyarlı düzen ve PWA
- **Sorun:** [DOĞRULANDI] Mobil çekmece var; dokunmatik hedefler, telefon düzeni, çevrimdışı kabuk eksik.
- **Değişiklik:** Telefon/tablet düzenleri, dokunmatik hedef ≥ 44 px, PWA (manifest + service worker) ve çevrimdışı kabuk, bağlantı kesintisi göstergesi.
- **Kabul:** 375 px genişlikte yatay kaydırma yok, tüm akışlar kullanılabilir (e2e); PWA kurulabilir.
- **Meta:** P2 · M · Bağ: UX-04 · Durum: açık

#### UX-08 · Sohbet: yeniden üret, düzenle-dallan, paylaş, dışa aktar
- **Sorun:** [DOĞRULANDI: F15] Yeniden üretme ve mesaj düzenleme yok; sohbet yönetimi sınırlı.
- **Değişiklik:** Yeniden üret (farklı model/mod seçeneğiyle), mesaj düzenle ve dal oluştur, kopyala, salt-okunur paylaşım bağlantısı (tailnet), dışa aktar (MD/PDF), sabitle, etiketle, tam metin ara.
- **Kabul:** Düzenleme dalı orijinal sohbeti bozmaz (test); dışa aktarılan sohbet kaynak ve atıfları korur.
- **Meta:** P1 · L · Bağ: ORC-17, DAT-10 · Durum: açık

#### UX-09 · Akış deneyimi ve adım zaman çizelgesi
- **Sorun:** [DOĞRULANDI] "Düşünüyor" ve saniye sayaçları var; gerçek plan/araç/kaynak adımları görünmüyor.
- **Değişiklik:** ORC-11 olaylarına bağlı adım zaman çizelgesi (plan, araç çağrısı, arama, doğrulama), iptal, hata ve yeniden deneme, canlı kaynak sayacı; kullanıcı ayrıntıyı açıp kapatır.
- **Kabul:** Her adım gerçek olaydan gelir (sahte animasyon yok); iptal düğmesi tüm adımları durdurur (e2e).
- **Meta:** P0 · L · Bağ: ORC-11 · Durum: açık

#### UX-10 · Atıf ve güven arayüzü
- **Sorun:** [DOĞRULANDI: F11] Atıf ve güven gösterimi yok.
- **Değişiklik:** İddia yanında üst simgeli kaynak, tıklayınca kaynak paneli (RAG-27), "doğrulandı/doğrulanamadı/çıkarıldı" rozeti, güven göstergesi (renk + metin, yalnız renk değil), açıklama ipucu.
- **Kabul:** Atıf sayısı yanıttaki `citation` olaylarıyla eşleşir; güven etiketi HAL-14 skoruna bağlı (test); renk körü kullanıcı için metin eşdeğeri var.
- **Meta:** P0 · M · Bağ: RAG-11, HAL-14 · Durum: açık

#### UX-11 · Artefakt paneli
- **Sorun:** [DOĞRULANDI] Kod/proje için IDE paneli var; sunum, belge, görsel, veri için ortak artefakt görüntüleyici yok.
- **Değişiklik:** Sağ panel: tür-duyarlı görüntüleyici (kod, slayt şeridi, belge önizleme, tablo, grafik, görsel), sürüm geçmişi, yan yana karşılaştırma, indir, yeniden aç, "yeni sohbette devam et".
- **Kabul:** Her artefakt türü panelde açılır ve sürümleri gezilir (e2e); sohbet silinse de kalan artefakt açılır.
- **Meta:** P0 · L · Bağ: ORC-17 · Durum: açık

#### UX-12 · Dosya ve bilgi yöneticisi
- **Sorun:** [ÖNERİ] Yüklenen, üretilen dosyalar ve bilgi koleksiyonları yönetilemiyor.
- **Değişiklik:** Dosya listesi (yükleme/üretilen/çalışma alanları/bilgi koleksiyonu), sürükle-bırak çoklu yükleme, ilerleme/ingest durumu, boyut-tür uyarıları, silme/yeniden dizinleme.
- **Kabul:** 20 dosya yüklemesi ilerlemeyle görünür; ingest hatası dosya yanında nedenle gösterilir.
- **Meta:** P1 · L · Bağ: RAG-12 · Durum: açık

#### UX-13 · Komut paleti (Ctrl+K)
- **Sorun:** [ÖNERİ] Eylemlere hızlı erişim yok.
- **Değişiklik:** Komut paleti: sohbet arama, yeni sohbet, mod/model değiştir, artefakt aç, ayarlar, ajan durumu; klavye kısayolu haritası.
- **Kabul:** Her ana eylem paletten erişilebilir; erişilebilirlik testinden geçer.
- **Meta:** P3 · M · Bağ: UX-05 · Durum: açık

#### UX-14 · Slash komutları, @-bahsetmeler ve istem kitaplığı
- **Sorun:** [ÖNERİ] Tekrarlayan istem kalıpları (sunum, araştırma, kod) her seferinde elle yazılıyor.
- **Değişiklik:** `/sunum`, `/araştır`, `/kod`, `/özet`; `@dosya`, `@bilgi`, `@web`; kullanıcı istem şablonları; slash komutu niyeti doğrudan seçer (ORC-03).
- **Kabul:** Slash/bahsetme seçimi niyet sınıflandırmasını atlar ve yanıt meta verisinde görünür.
- **Meta:** P2 · M · Bağ: ORC-03 · Durum: açık

#### UX-15 · Model/ajan seçici ve gerekçe
- **Sorun:** [DOĞRULANDI: F10] Seçim kullanıcıdan gizli; hangi modelin neden seçildiği bilinmiyor.
- **Değişiklik:** Otomatik (varsayılan) veya elle model/ajan seçimi, seçim gerekçesi ("kodlama puanı 92, sıcak model"), hız/kalite/halüsinasyon göstergeleri; kısıtlı donanımda uyarı.
- **Kabul:** Elle seçim yanıt meta verisine yansır; gerekçe `selection` kaydıyla uyumlu.
- **Meta:** P1 · M · Bağ: GW-04, DIST-03 · Durum: açık

#### UX-16 · Ayarlar
- **Sorun:** [DOĞRULANDI] Ayarlar anında kalıcı (yapıldı); yanıt dili/uzunluğu/ton, güven göstergesi, web araması, veri saklama, kısayollar için tutarlı bir ayar mimarisi yok.
- **Değişiklik:** Ayar şeması (tür/varsayılan/doğrulama), ayar sayfası, kullanıcı/yönetici ayrımı, dışa/içe aktarım, değişiklik denetim kaydı.
- **Kabul:** Her ayar şemada tanımlı ve test edilebilir; geçersiz değer reddedilir.
- **Meta:** P2 · M · Bağ: UX-03 · Durum: açık

#### UX-17 · İlk kullanım ve sağlık sihirbazı
- **Sorun:** [ÖNERİ] Ollama/model/web/ajan eksikliğinde kullanıcı belirsiz hatalarla karşılaşıyor (bu denetim sırasında da tekrar tekrar yaşandı).
- **Değişiklik:** İlk açılışta sağlık kontrolü sihirbazı: Ollama var mı, modeller çekili mi, gömme modeli, web araması, Docker/sandbox, ajanlar, Tailscale; her eksik için tek tıkla/komutla çözüm yönergesi (DEF-15).
- **Kabul:** Her bileşen eksik olduğunda sihirbaz nedenini ve çözüm adımını gösterir (e2e: sahte eksiklikler).
- **Meta:** P1 · M · Bağ: DEF-15, OPS-03 · Durum: açık

#### UX-18 · Boş/hata/yükleniyor durumları ve ağ dayanıklılığı
- **Sorun:** [ÖNERİ] Hata mesajları teknik ("Ollama hatası: ...") ve çözümsüz; ağ kesintisinde akış yeniden bağlanmıyor.
- **Değişiklik:** Standart durum bileşenleri; hata → ne oldu/ne yapmalı/yeniden dene; SSE/iş yeniden bağlanma (ORC-13); çevrimdışı göstergesi.
- **Kabul:** Hata türü başına metin sözlüğü; ağ kesilip dönünce iş kaldığı yerden izlenir (e2e).
- **Meta:** P1 · M · Bağ: ORC-13 · Durum: açık

#### UX-19 · Performans bütçesi
- **Sorun:** [ÖNERİ] Uzun sohbette DOM şişmesi, Markdown/vurgulama ana iş parçacığında.
- **Değişiklik:** Sanal liste, Markdown/vurgulama Web Worker'da, görseller tembel yüklenir, kod-bölme (Monaco/IDE lazy), paket boyutu ≤ 300 KB gz (çekirdek), Lighthouse performans ≥ 90.
- **Kabul:** 1.000 mesajlık sohbette kaydırma ≥ 50 FPS ve ilk boyama < 1.5 sn (profil testi); bütçe aşımı CI'ı kırar.
- **Meta:** P2 · M · Bağ: UX-01 · Durum: açık

#### UX-20 · Güvenli içerik işleme
- **Sorun:** [DOĞRULANDI: F2] Sohbette `<svg>` blokları görsel olarak çiziliyor (commit "render any <svg> block"); model/belge kaynaklı HTML/SVG içindeki betik ve olay öznitelikleri XSS riski.
- **Değişiklik:** Markdown/HTML/SVG temizleme (DOMPurify yerel paket), SVG için betiksiz izinli etiket kümesi, sandbox'lı iframe ile önizleme, CSP uyumu.
- **Kabul:** Betik/`onerror`/`javascript:` içeren 40 saldırı örneği çalışmaz (test); zararsız SVG/diyagramlar doğru çizilir.
- **Meta:** P0 · M · Bağ: SEC-16 · Durum: açık

#### UX-21 · İkon seti ve emoji yok kuralının otomatiği
- **Sorun:** [DOĞRULANDI] Proje ilkesi "arayüzde emoji yok"; ihlaller elle yakalanıyor, sunucu tarafında süzme yan etki yaratıyor (DEF-23).
- **Değişiklik:** SVG sprite ikon seti; derleme/lint kuralı arayüz dizelerinde ve şablonlarda emoji aralığını yasaklar (kod blokları hariç).
- **Kabul:** Emoji içeren arayüz dizesi CI'ı kırar; ikonlar tek kaynaktan.
- **Meta:** P3 · S · Bağ: UX-01 · Durum: açık

#### UX-22 · Ajanlar sayfası: yük, geçmiş, değerlendirme, ekleme sihirbazı
- **Sorun:** [DOĞRULANDI] Canlı durum rozeti var (yapıldı); kuyruk/yük, görev geçmişi, benchmark geçmişi ve ajan ekleme akışı yok.
- **Değişiklik:** Ajan kartında yük/kuyruk/son görevler/benchmark eğilimi; "ajan ekle" sihirbazı (kurulum komutu üretir, DIST-14); yeniden değerlendir; çevrimdışı ajan için son görülme.
- **Kabul:** Kart verileri API ile birebir; sihirbazın ürettiği komut test ortamında ajanı kaydeder.
- **Meta:** P1 · M · Bağ: DIST-11, DIST-14 · Durum: açık

#### UX-23 · Projeler (Scrum hattı) sayfası: DAG, çakışma, yeniden atama
- **Sorun:** [DOĞRULANDI: F17] Çakışma rozeti görünüyor ama çözme yok; görev iptal/yeniden atama/fix-tasks düğmeleri yok.
- **Değişiklik:** DAG görünümü iyileştirme (durum renkleri, kritik yol), çakışma çözme paneli (DIST-15), görev iptal/yeniden atama/fix-task onayı, canlı ilerleme (SSE), çıktı karşılaştırma.
- **Kabul:** Çakışma çözme ve yeniden atama arayüzden uçtan uca çalışır (e2e); ilerleme sayfa yenilemeden akar.
- **Meta:** P0 · L · Bağ: DIST-15 · Durum: açık

#### UX-24 · Pano: SLO kartları, model karşılaştırma, hata dökümü
- **Sorun:** [DOĞRULANDI] Pano görev/ajan sayıları gösteriyor; kalite (halüsinasyon, atıf), gecikme ve model karşılaştırması yok.
- **Değişiklik:** SLO kartları (halüsinasyon oranı, atıf kapsamı, kaçınma, TTFT, başarı), model/ajan karşılaştırma, hata türü dökümü, zaman aralığı, dışa aktarma; eşik uyarıları.
- **Kabul:** Her kart veri kaynağıyla (sorgu) belgeli; sayılar `eval`/üretim telemetrisiyle tutarlı.
- **Meta:** P1 · L · Bağ: HAL-26, DIST-19 · Durum: açık

#### UX-25 · Bildirimler
- **Sorun:** [ÖNERİ] Uzun işler bittiğinde veya onay gerektiğinde kullanıcı sekmeyi izlemek zorunda.
- **Değişiklik:** Tarayıcı bildirimi (izinli), sayfa başlığı rozeti, "iş bitti / onay gerekli / ajan çevrimdışı" olayları; sessiz saatler.
- **Kabul:** Uzun iş bitince başka sekmedeyken bildirim gelir (e2e, izin verilmişse); izin reddinde yedek gösterge.
- **Meta:** P3 · S · Bağ: ORC-13 · Durum: açık

#### UX-26 · Paylaşım ve yorumlar
- **Sorun:** [ÖNERİ] Takım arkadaşlarıyla sohbet/artefakt paylaşımı yok.
- **Değişiklik:** Salt-okunur paylaşım bağlantısı (tailnet), yorum, yetki (SEC-04), bağlantı süre sonu; paylaşılan içerikte gizli bilgi taraması.
- **Kabul:** Yetkisiz kullanıcı paylaşıma erişemez; süresi dolan bağlantı 404.
- **Meta:** P3 · M · Bağ: SEC-04 · Durum: açık

#### UX-27 · Geri bildirim akışı
- **Sorun:** [ÖNERİ] Beğeni/beğenmeme ve "yanlış bilgi" bildirimi yok (ORC-22/HAL-25 arayüzü).
- **Değişiklik:** Her yanıtta beğen/beğenme + neden etiketi + "yanlış bilgi bildir" (doğru cevap/kaynak alanı); gönderim onayı ve gizlilik notu.
- **Kabul:** Geri bildirim `run_id` ile ilişkili kaydedilir; kullanıcı kendi geri bildirimini silebilir.
- **Meta:** P1 · S · Bağ: ORC-22 · Durum: açık

#### UX-28 · Uçtan uca (e2e) testler ve görsel regresyon
- **Sorun:** [DOĞRULANDI: F15] Arayüz için otomatik test yok; arayüz regresyonları elle fark ediliyor.
- **Değişiklik:** Playwright ile 25 kritik akış (sohbet, akış/durdur, dosya yükleme, sunum üret, proje üret, IDE, ajan sayfası, ayarlar, çakışma çözümü, yeniden bağlanma); görsel regresyon (ekran görüntüsü karşılaştırma); sahte LLM sunucusuyla deterministik.
- **Kabul:** 25 akış CI'da < 8 dk yeşil; akış kıran PR kırmızı; görsel fark eşiği belgeli.
- **Meta:** P0 · L · Bağ: UX-01, OPS-10 · Durum: açık
