# Parça 8 — Programların iş paketleri (öneri, WBS)

## PKA · İş paketleri (1)

#### PKA-01 · EPK-01 · Tasarım belgesi ve ADR: Yerel web arama ve tarama altyapısı
- **Sorun:** [ÖNERİ] Program EPK-01 «Yerel web arama ve tarama altyapısı» iş paketi 1/10. Bağlam: Web araması yapılandırılmamış (SEARXNG_URL yok, sağlık sihirbazı 4/6): araştırma modelin hafızasından yazıyor.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### PKA-02 · EPK-01 · Veri modeli ve göç: Yerel web arama ve tarama altyapısı
- **Sorun:** [ÖNERİ] Program EPK-01 «Yerel web arama ve tarama altyapısı» iş paketi 2/10. Bağlam: Web araması yapılandırılmamış (SEARXNG_URL yok, sağlık sihirbazı 4/6): araştırma modelin hafızasından yazıyor.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P0 · M · Bağ: PKA-01 · Durum: açık

#### PKA-03 · EPK-01 · Çekirdek mantık: Yerel web arama ve tarama altyapısı
- **Sorun:** [ÖNERİ] Program EPK-01 «Yerel web arama ve tarama altyapısı» iş paketi 3/10. Bağlam: Web araması yapılandırılmamış (SEARXNG_URL yok, sağlık sihirbazı 4/6): araştırma modelin hafızasından yazıyor.
- **Değişiklik:** SearXNG'yi kurulumla birlikte getir, çok sağlayıcılı yedek, kibar tarayıcı (robots, hız sınırı), sayfa arşivi, tekilleştirme, kaynak puanlama, çevrimdışı mod.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P0 · L · Bağ: PKA-02 · Durum: açık

#### PKA-04 · EPK-01 · API ve yanıt şemaları: Yerel web arama ve tarama altyapısı
- **Sorun:** [ÖNERİ] Program EPK-01 «Yerel web arama ve tarama altyapısı» iş paketi 4/10. Bağlam: Web araması yapılandırılmamış (SEARXNG_URL yok, sağlık sihirbazı 4/6): araştırma modelin hafızasından yazıyor.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P0 · M · Bağ: PKA-03 · Durum: açık

#### PKA-05 · EPK-01 · Arayüz ve erişilebilirlik: Yerel web arama ve tarama altyapısı
- **Sorun:** [ÖNERİ] Program EPK-01 «Yerel web arama ve tarama altyapısı» iş paketi 5/10. Bağlam: Web araması yapılandırılmamış (SEARXNG_URL yok, sağlık sihirbazı 4/6): araştırma modelin hafızasından yazıyor.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P0 · M · Bağ: PKA-04 · Durum: açık

#### PKA-06 · EPK-01 · Birim ve sözleşme testleri: Yerel web arama ve tarama altyapısı
- **Sorun:** [ÖNERİ] Program EPK-01 «Yerel web arama ve tarama altyapısı» iş paketi 6/10. Bağlam: Web araması yapılandırılmamış (SEARXNG_URL yok, sağlık sihirbazı 4/6): araştırma modelin hafızasından yazıyor.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P0 · M · Bağ: PKA-05 · Durum: açık

#### PKA-07 · EPK-01 · Hata enjeksiyonu ve dayanıklılık: Yerel web arama ve tarama altyapısı
- **Sorun:** [ÖNERİ] Program EPK-01 «Yerel web arama ve tarama altyapısı» iş paketi 7/10. Bağlam: Web araması yapılandırılmamış (SEARXNG_URL yok, sağlık sihirbazı 4/6): araştırma modelin hafızasından yazıyor.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P0 · M · Bağ: PKA-06 · Durum: açık

#### PKA-08 · EPK-01 · Güvenlik ve gizlilik incelemesi: Yerel web arama ve tarama altyapısı
- **Sorun:** [ÖNERİ] Program EPK-01 «Yerel web arama ve tarama altyapısı» iş paketi 8/10. Bağlam: Web araması yapılandırılmamış (SEARXNG_URL yok, sağlık sihirbazı 4/6): araştırma modelin hafızasından yazıyor.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P0 · S · Bağ: PKA-07 · Durum: açık

#### PKA-09 · EPK-01 · Uçtan uca senaryo ve eval kümesi: Yerel web arama ve tarama altyapısı
- **Sorun:** [ÖNERİ] Program EPK-01 «Yerel web arama ve tarama altyapısı» iş paketi 9/10. Bağlam: Web araması yapılandırılmamış (SEARXNG_URL yok, sağlık sihirbazı 4/6): araştırma modelin hafızasından yazıyor.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P0 · M · Bağ: PKA-08 · Durum: açık

#### PKA-10 · EPK-01 · Ölçüm, belge ve runbook: Yerel web arama ve tarama altyapısı
- **Sorun:** [ÖNERİ] Program EPK-01 «Yerel web arama ve tarama altyapısı» iş paketi 10/10. Bağlam: Web araması yapılandırılmamış (SEARXNG_URL yok, sağlık sihirbazı 4/6): araştırma modelin hafızasından yazıyor.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Temiz kurulumda tek komutla çalışan arama; 50 güncel soruda kaynaklı yanıt oranı ≥ %90; ağ yokken net uyarı.
- **Meta:** P0 · M · Bağ: PKA-09 · Durum: açık

#### PKA-11 · EPK-02 · Tasarım belgesi ve ADR: Etiketli Türkçe değerlendirme veri kümeleri programı
- **Sorun:** [ÖNERİ] Program EPK-02 «Etiketli Türkçe değerlendirme veri kümeleri programı» iş paketi 1/10. Bağlam: ECE, κ, NLI F1, VQA ve olgusallık ölçümleri insan etiketli veri istiyor; depoda yok.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### PKA-12 · EPK-02 · Veri modeli ve göç: Etiketli Türkçe değerlendirme veri kümeleri programı
- **Sorun:** [ÖNERİ] Program EPK-02 «Etiketli Türkçe değerlendirme veri kümeleri programı» iş paketi 2/10. Bağlam: ECE, κ, NLI F1, VQA ve olgusallık ölçümleri insan etiketli veri istiyor; depoda yok.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P0 · M · Bağ: PKA-11 · Durum: açık

#### PKA-13 · EPK-02 · Çekirdek mantık: Etiketli Türkçe değerlendirme veri kümeleri programı
- **Sorun:** [ÖNERİ] Program EPK-02 «Etiketli Türkçe değerlendirme veri kümeleri programı» iş paketi 3/10. Bağlam: ECE, κ, NLI F1, VQA ve olgusallık ölçümleri insan etiketli veri istiyor; depoda yok.
- **Değişiklik:** Etiketleme arayüzü, iki etiketleyici, uyum ölçümü, sürümlü veri kümeleri (olgusallık, atıf, NLI, niyet, görsel, ses).
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P0 · L · Bağ: PKA-12 · Durum: açık

#### PKA-14 · EPK-02 · API ve yanıt şemaları: Etiketli Türkçe değerlendirme veri kümeleri programı
- **Sorun:** [ÖNERİ] Program EPK-02 «Etiketli Türkçe değerlendirme veri kümeleri programı» iş paketi 4/10. Bağlam: ECE, κ, NLI F1, VQA ve olgusallık ölçümleri insan etiketli veri istiyor; depoda yok.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P0 · M · Bağ: PKA-13 · Durum: açık

#### PKA-15 · EPK-02 · Arayüz ve erişilebilirlik: Etiketli Türkçe değerlendirme veri kümeleri programı
- **Sorun:** [ÖNERİ] Program EPK-02 «Etiketli Türkçe değerlendirme veri kümeleri programı» iş paketi 5/10. Bağlam: ECE, κ, NLI F1, VQA ve olgusallık ölçümleri insan etiketli veri istiyor; depoda yok.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P0 · M · Bağ: PKA-14 · Durum: açık

#### PKA-16 · EPK-02 · Birim ve sözleşme testleri: Etiketli Türkçe değerlendirme veri kümeleri programı
- **Sorun:** [ÖNERİ] Program EPK-02 «Etiketli Türkçe değerlendirme veri kümeleri programı» iş paketi 6/10. Bağlam: ECE, κ, NLI F1, VQA ve olgusallık ölçümleri insan etiketli veri istiyor; depoda yok.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P0 · M · Bağ: PKA-15 · Durum: açık

#### PKA-17 · EPK-02 · Hata enjeksiyonu ve dayanıklılık: Etiketli Türkçe değerlendirme veri kümeleri programı
- **Sorun:** [ÖNERİ] Program EPK-02 «Etiketli Türkçe değerlendirme veri kümeleri programı» iş paketi 7/10. Bağlam: ECE, κ, NLI F1, VQA ve olgusallık ölçümleri insan etiketli veri istiyor; depoda yok.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P0 · M · Bağ: PKA-16 · Durum: açık

#### PKA-18 · EPK-02 · Güvenlik ve gizlilik incelemesi: Etiketli Türkçe değerlendirme veri kümeleri programı
- **Sorun:** [ÖNERİ] Program EPK-02 «Etiketli Türkçe değerlendirme veri kümeleri programı» iş paketi 8/10. Bağlam: ECE, κ, NLI F1, VQA ve olgusallık ölçümleri insan etiketli veri istiyor; depoda yok.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P0 · S · Bağ: PKA-17 · Durum: açık

#### PKA-19 · EPK-02 · Uçtan uca senaryo ve eval kümesi: Etiketli Türkçe değerlendirme veri kümeleri programı
- **Sorun:** [ÖNERİ] Program EPK-02 «Etiketli Türkçe değerlendirme veri kümeleri programı» iş paketi 9/10. Bağlam: ECE, κ, NLI F1, VQA ve olgusallık ölçümleri insan etiketli veri istiyor; depoda yok.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P0 · M · Bağ: PKA-18 · Durum: açık

#### PKA-20 · EPK-02 · Ölçüm, belge ve runbook: Etiketli Türkçe değerlendirme veri kümeleri programı
- **Sorun:** [ÖNERİ] Program EPK-02 «Etiketli Türkçe değerlendirme veri kümeleri programı» iş paketi 10/10. Bağlam: ECE, κ, NLI F1, VQA ve olgusallık ölçümleri insan etiketli veri istiyor; depoda yok.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Her küme ≥ 300 örnek, κ ≥ 0.7, sürüm ve veri kartı; eval raporları bu kümelere bağlı.
- **Meta:** P0 · M · Bağ: PKA-19 · Durum: açık

#### PKA-21 · EPK-03 · Tasarım belgesi ve ADR: Gerçek çok kullanıcılı kimlik ve yetki mimarisi
- **Sorun:** [ÖNERİ] Program EPK-03 «Gerçek çok kullanıcılı kimlik ve yetki mimarisi» iş paketi 1/10. Bağlam: Kullanıcı kimliği sorgu parametresinden geliyor; 8 /api/user/* rotası oturumsuz 200 veriyor; roller route'a bağlı değil.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### PKA-22 · EPK-03 · Veri modeli ve göç: Gerçek çok kullanıcılı kimlik ve yetki mimarisi
- **Sorun:** [ÖNERİ] Program EPK-03 «Gerçek çok kullanıcılı kimlik ve yetki mimarisi» iş paketi 2/10. Bağlam: Kullanıcı kimliği sorgu parametresinden geliyor; 8 /api/user/* rotası oturumsuz 200 veriyor; roller route'a bağlı değil.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P0 · M · Bağ: PKA-21 · Durum: açık

#### PKA-23 · EPK-03 · Çekirdek mantık: Gerçek çok kullanıcılı kimlik ve yetki mimarisi
- **Sorun:** [ÖNERİ] Program EPK-03 «Gerçek çok kullanıcılı kimlik ve yetki mimarisi» iş paketi 3/10. Bağlam: Kullanıcı kimliği sorgu parametresinden geliyor; 8 /api/user/* rotası oturumsuz 200 veriyor; roller route'a bağlı değil.
- **Değişiklik:** Oturumdan türeyen kimlik, rol matrisinin route bağımlılığı olması, organizasyon/ekip kavramı, davet akışı, yönetici arayüzü.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P0 · L · Bağ: PKA-22 · Durum: açık

#### PKA-24 · EPK-03 · API ve yanıt şemaları: Gerçek çok kullanıcılı kimlik ve yetki mimarisi
- **Sorun:** [ÖNERİ] Program EPK-03 «Gerçek çok kullanıcılı kimlik ve yetki mimarisi» iş paketi 4/10. Bağlam: Kullanıcı kimliği sorgu parametresinden geliyor; 8 /api/user/* rotası oturumsuz 200 veriyor; roller route'a bağlı değil.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P0 · M · Bağ: PKA-23 · Durum: açık

#### PKA-25 · EPK-03 · Arayüz ve erişilebilirlik: Gerçek çok kullanıcılı kimlik ve yetki mimarisi
- **Sorun:** [ÖNERİ] Program EPK-03 «Gerçek çok kullanıcılı kimlik ve yetki mimarisi» iş paketi 5/10. Bağlam: Kullanıcı kimliği sorgu parametresinden geliyor; 8 /api/user/* rotası oturumsuz 200 veriyor; roller route'a bağlı değil.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P0 · M · Bağ: PKA-24 · Durum: açık

#### PKA-26 · EPK-03 · Birim ve sözleşme testleri: Gerçek çok kullanıcılı kimlik ve yetki mimarisi
- **Sorun:** [ÖNERİ] Program EPK-03 «Gerçek çok kullanıcılı kimlik ve yetki mimarisi» iş paketi 6/10. Bağlam: Kullanıcı kimliği sorgu parametresinden geliyor; 8 /api/user/* rotası oturumsuz 200 veriyor; roller route'a bağlı değil.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P0 · M · Bağ: PKA-25 · Durum: açık

#### PKA-27 · EPK-03 · Hata enjeksiyonu ve dayanıklılık: Gerçek çok kullanıcılı kimlik ve yetki mimarisi
- **Sorun:** [ÖNERİ] Program EPK-03 «Gerçek çok kullanıcılı kimlik ve yetki mimarisi» iş paketi 7/10. Bağlam: Kullanıcı kimliği sorgu parametresinden geliyor; 8 /api/user/* rotası oturumsuz 200 veriyor; roller route'a bağlı değil.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P0 · M · Bağ: PKA-26 · Durum: açık

#### PKA-28 · EPK-03 · Güvenlik ve gizlilik incelemesi: Gerçek çok kullanıcılı kimlik ve yetki mimarisi
- **Sorun:** [ÖNERİ] Program EPK-03 «Gerçek çok kullanıcılı kimlik ve yetki mimarisi» iş paketi 8/10. Bağlam: Kullanıcı kimliği sorgu parametresinden geliyor; 8 /api/user/* rotası oturumsuz 200 veriyor; roller route'a bağlı değil.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P0 · S · Bağ: PKA-27 · Durum: açık

#### PKA-29 · EPK-03 · Uçtan uca senaryo ve eval kümesi: Gerçek çok kullanıcılı kimlik ve yetki mimarisi
- **Sorun:** [ÖNERİ] Program EPK-03 «Gerçek çok kullanıcılı kimlik ve yetki mimarisi» iş paketi 9/10. Bağlam: Kullanıcı kimliği sorgu parametresinden geliyor; 8 /api/user/* rotası oturumsuz 200 veriyor; roller route'a bağlı değil.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P0 · M · Bağ: PKA-28 · Durum: açık

#### PKA-30 · EPK-03 · Ölçüm, belge ve runbook: Gerçek çok kullanıcılı kimlik ve yetki mimarisi
- **Sorun:** [ÖNERİ] Program EPK-03 «Gerçek çok kullanıcılı kimlik ve yetki mimarisi» iş paketi 10/10. Bağlam: Kullanıcı kimliği sorgu parametresinden geliyor; 8 /api/user/* rotası oturumsuz 200 veriyor; roller route'a bağlı değil.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Her route için A→B sızıntı testi otomatik üretilir; oturumsuz hiçbir kullanıcı verisi okunamaz.
- **Meta:** P0 · M · Bağ: PKA-29 · Durum: açık

#### PKA-31 · EPK-04 · Tasarım belgesi ve ADR: Sözleşme-öncelikli API: tam yanıt şemaları
- **Sorun:** [ÖNERİ] Program EPK-04 «Sözleşme-öncelikli API: tam yanıt şemaları» iş paketi 1/10. Bağlam: 188 işlemin hiçbirinin 200 yanıtı için şeması yok; arayüz-API uyumu ve sözleşme testi yazılamıyor.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### PKA-32 · EPK-04 · Veri modeli ve göç: Sözleşme-öncelikli API: tam yanıt şemaları
- **Sorun:** [ÖNERİ] Program EPK-04 «Sözleşme-öncelikli API: tam yanıt şemaları» iş paketi 2/10. Bağlam: 188 işlemin hiçbirinin 200 yanıtı için şeması yok; arayüz-API uyumu ve sözleşme testi yazılamıyor.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P0 · M · Bağ: PKA-31 · Durum: açık

#### PKA-33 · EPK-04 · Çekirdek mantık: Sözleşme-öncelikli API: tam yanıt şemaları
- **Sorun:** [ÖNERİ] Program EPK-04 «Sözleşme-öncelikli API: tam yanıt şemaları» iş paketi 3/10. Bağlam: 188 işlemin hiçbirinin 200 yanıtı için şeması yok; arayüz-API uyumu ve sözleşme testi yazılamıyor.
- **Değişiklik:** Tüm route'lara Pydantic yanıt modeli, OpenAPI'den TypeScript tipi, arayüz çağrılarının tip denetimi, schemathesis fuzz.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P0 · L · Bağ: PKA-32 · Durum: açık

#### PKA-34 · EPK-04 · API ve yanıt şemaları: Sözleşme-öncelikli API: tam yanıt şemaları
- **Sorun:** [ÖNERİ] Program EPK-04 «Sözleşme-öncelikli API: tam yanıt şemaları» iş paketi 4/10. Bağlam: 188 işlemin hiçbirinin 200 yanıtı için şeması yok; arayüz-API uyumu ve sözleşme testi yazılamıyor.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P0 · M · Bağ: PKA-33 · Durum: açık

#### PKA-35 · EPK-04 · Arayüz ve erişilebilirlik: Sözleşme-öncelikli API: tam yanıt şemaları
- **Sorun:** [ÖNERİ] Program EPK-04 «Sözleşme-öncelikli API: tam yanıt şemaları» iş paketi 5/10. Bağlam: 188 işlemin hiçbirinin 200 yanıtı için şeması yok; arayüz-API uyumu ve sözleşme testi yazılamıyor.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P0 · M · Bağ: PKA-34 · Durum: açık

#### PKA-36 · EPK-04 · Birim ve sözleşme testleri: Sözleşme-öncelikli API: tam yanıt şemaları
- **Sorun:** [ÖNERİ] Program EPK-04 «Sözleşme-öncelikli API: tam yanıt şemaları» iş paketi 6/10. Bağlam: 188 işlemin hiçbirinin 200 yanıtı için şeması yok; arayüz-API uyumu ve sözleşme testi yazılamıyor.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P0 · M · Bağ: PKA-35 · Durum: açık

#### PKA-37 · EPK-04 · Hata enjeksiyonu ve dayanıklılık: Sözleşme-öncelikli API: tam yanıt şemaları
- **Sorun:** [ÖNERİ] Program EPK-04 «Sözleşme-öncelikli API: tam yanıt şemaları» iş paketi 7/10. Bağlam: 188 işlemin hiçbirinin 200 yanıtı için şeması yok; arayüz-API uyumu ve sözleşme testi yazılamıyor.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P0 · M · Bağ: PKA-36 · Durum: açık

#### PKA-38 · EPK-04 · Güvenlik ve gizlilik incelemesi: Sözleşme-öncelikli API: tam yanıt şemaları
- **Sorun:** [ÖNERİ] Program EPK-04 «Sözleşme-öncelikli API: tam yanıt şemaları» iş paketi 8/10. Bağlam: 188 işlemin hiçbirinin 200 yanıtı için şeması yok; arayüz-API uyumu ve sözleşme testi yazılamıyor.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P0 · S · Bağ: PKA-37 · Durum: açık

#### PKA-39 · EPK-04 · Uçtan uca senaryo ve eval kümesi: Sözleşme-öncelikli API: tam yanıt şemaları
- **Sorun:** [ÖNERİ] Program EPK-04 «Sözleşme-öncelikli API: tam yanıt şemaları» iş paketi 9/10. Bağlam: 188 işlemin hiçbirinin 200 yanıtı için şeması yok; arayüz-API uyumu ve sözleşme testi yazılamıyor.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P0 · M · Bağ: PKA-38 · Durum: açık

#### PKA-40 · EPK-04 · Ölçüm, belge ve runbook: Sözleşme-öncelikli API: tam yanıt şemaları
- **Sorun:** [ÖNERİ] Program EPK-04 «Sözleşme-öncelikli API: tam yanıt şemaları» iş paketi 10/10. Bağlam: 188 işlemin hiçbirinin 200 yanıtı için şeması yok; arayüz-API uyumu ve sözleşme testi yazılamıyor.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** 188/188 route yanıt şemalı; alan adı değişince derleme kırılır.
- **Meta:** P0 · M · Bağ: PKA-39 · Durum: açık

#### PKA-41 · EPK-05 · Tasarım belgesi ve ADR: Üretim kalitesinde kod üretim fabrikası
- **Sorun:** [ÖNERİ] Program EPK-05 «Üretim kalitesinde kod üretim fabrikası» iş paketi 1/10. Bağlam: Proje üretiminde 'çalışan proje' oranı ölçülmedi; şablon deposu yok; tarayıcı doğrulama yok.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### PKA-42 · EPK-05 · Veri modeli ve göç: Üretim kalitesinde kod üretim fabrikası
- **Sorun:** [ÖNERİ] Program EPK-05 «Üretim kalitesinde kod üretim fabrikası» iş paketi 2/10. Bağlam: Proje üretiminde 'çalışan proje' oranı ölçülmedi; şablon deposu yok; tarayıcı doğrulama yok.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P0 · M · Bağ: PKA-41 · Durum: açık

#### PKA-43 · EPK-05 · Çekirdek mantık: Üretim kalitesinde kod üretim fabrikası
- **Sorun:** [ÖNERİ] Program EPK-05 «Üretim kalitesinde kod üretim fabrikası» iş paketi 3/10. Bağlam: Proje üretiminde 'çalışan proje' oranı ölçülmedi; şablon deposu yok; tarayıcı doğrulama yok.
- **Değişiklik:** 8 testli şablon, kur-derle-test-çalıştır-sağlık döngüsü, Playwright doğrulama, hedefli onarım, kalite panosu.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P0 · L · Bağ: PKA-42 · Durum: açık

#### PKA-44 · EPK-05 · API ve yanıt şemaları: Üretim kalitesinde kod üretim fabrikası
- **Sorun:** [ÖNERİ] Program EPK-05 «Üretim kalitesinde kod üretim fabrikası» iş paketi 4/10. Bağlam: Proje üretiminde 'çalışan proje' oranı ölçülmedi; şablon deposu yok; tarayıcı doğrulama yok.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P0 · M · Bağ: PKA-43 · Durum: açık

#### PKA-45 · EPK-05 · Arayüz ve erişilebilirlik: Üretim kalitesinde kod üretim fabrikası
- **Sorun:** [ÖNERİ] Program EPK-05 «Üretim kalitesinde kod üretim fabrikası» iş paketi 5/10. Bağlam: Proje üretiminde 'çalışan proje' oranı ölçülmedi; şablon deposu yok; tarayıcı doğrulama yok.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P0 · M · Bağ: PKA-44 · Durum: açık

#### PKA-46 · EPK-05 · Birim ve sözleşme testleri: Üretim kalitesinde kod üretim fabrikası
- **Sorun:** [ÖNERİ] Program EPK-05 «Üretim kalitesinde kod üretim fabrikası» iş paketi 6/10. Bağlam: Proje üretiminde 'çalışan proje' oranı ölçülmedi; şablon deposu yok; tarayıcı doğrulama yok.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P0 · M · Bağ: PKA-45 · Durum: açık

#### PKA-47 · EPK-05 · Hata enjeksiyonu ve dayanıklılık: Üretim kalitesinde kod üretim fabrikası
- **Sorun:** [ÖNERİ] Program EPK-05 «Üretim kalitesinde kod üretim fabrikası» iş paketi 7/10. Bağlam: Proje üretiminde 'çalışan proje' oranı ölçülmedi; şablon deposu yok; tarayıcı doğrulama yok.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P0 · M · Bağ: PKA-46 · Durum: açık

#### PKA-48 · EPK-05 · Güvenlik ve gizlilik incelemesi: Üretim kalitesinde kod üretim fabrikası
- **Sorun:** [ÖNERİ] Program EPK-05 «Üretim kalitesinde kod üretim fabrikası» iş paketi 8/10. Bağlam: Proje üretiminde 'çalışan proje' oranı ölçülmedi; şablon deposu yok; tarayıcı doğrulama yok.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P0 · S · Bağ: PKA-47 · Durum: açık

#### PKA-49 · EPK-05 · Uçtan uca senaryo ve eval kümesi: Üretim kalitesinde kod üretim fabrikası
- **Sorun:** [ÖNERİ] Program EPK-05 «Üretim kalitesinde kod üretim fabrikası» iş paketi 9/10. Bağlam: Proje üretiminde 'çalışan proje' oranı ölçülmedi; şablon deposu yok; tarayıcı doğrulama yok.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P0 · M · Bağ: PKA-48 · Durum: açık

#### PKA-50 · EPK-05 · Ölçüm, belge ve runbook: Üretim kalitesinde kod üretim fabrikası
- **Sorun:** [ÖNERİ] Program EPK-05 «Üretim kalitesinde kod üretim fabrikası» iş paketi 10/10. Bağlam: Proje üretiminde 'çalışan proje' oranı ölçülmedi; şablon deposu yok; tarayıcı doğrulama yok.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** 20 istemde çalışan proje ≥ %80; kırık projelerin ≥ %85'i yakalanır.
- **Meta:** P0 · M · Bağ: PKA-49 · Durum: açık

#### PKA-51 · EPK-06 · Tasarım belgesi ve ADR: Tam IDE deneyimi
- **Sorun:** [ÖNERİ] Program EPK-06 «Tam IDE deneyimi» iş paketi 1/10. Bağlam: Monaco yok, terminal komut-yanıt, LSP/DAP yok, gerçek git geçmişi yok.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### PKA-52 · EPK-06 · Veri modeli ve göç: Tam IDE deneyimi
- **Sorun:** [ÖNERİ] Program EPK-06 «Tam IDE deneyimi» iş paketi 2/10. Bağlam: Monaco yok, terminal komut-yanıt, LSP/DAP yok, gerçek git geçmişi yok.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P0 · M · Bağ: PKA-51 · Durum: açık

#### PKA-53 · EPK-06 · Çekirdek mantık: Tam IDE deneyimi
- **Sorun:** [ÖNERİ] Program EPK-06 «Tam IDE deneyimi» iş paketi 3/10. Bağlam: Monaco yok, terminal komut-yanıt, LSP/DAP yok, gerçek git geçmişi yok.
- **Değişiklik:** Monaco (yerel), PTY terminal, LSP köprüsü, DAP, git grafiği, çok dosyalı düzenleme, birleşik diff.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P0 · L · Bağ: PKA-52 · Durum: açık

#### PKA-54 · EPK-06 · API ve yanıt şemaları: Tam IDE deneyimi
- **Sorun:** [ÖNERİ] Program EPK-06 «Tam IDE deneyimi» iş paketi 4/10. Bağlam: Monaco yok, terminal komut-yanıt, LSP/DAP yok, gerçek git geçmişi yok.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P0 · M · Bağ: PKA-53 · Durum: açık

#### PKA-55 · EPK-06 · Arayüz ve erişilebilirlik: Tam IDE deneyimi
- **Sorun:** [ÖNERİ] Program EPK-06 «Tam IDE deneyimi» iş paketi 5/10. Bağlam: Monaco yok, terminal komut-yanıt, LSP/DAP yok, gerçek git geçmişi yok.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P0 · M · Bağ: PKA-54 · Durum: açık

#### PKA-56 · EPK-06 · Birim ve sözleşme testleri: Tam IDE deneyimi
- **Sorun:** [ÖNERİ] Program EPK-06 «Tam IDE deneyimi» iş paketi 6/10. Bağlam: Monaco yok, terminal komut-yanıt, LSP/DAP yok, gerçek git geçmişi yok.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P0 · M · Bağ: PKA-55 · Durum: açık

#### PKA-57 · EPK-06 · Hata enjeksiyonu ve dayanıklılık: Tam IDE deneyimi
- **Sorun:** [ÖNERİ] Program EPK-06 «Tam IDE deneyimi» iş paketi 7/10. Bağlam: Monaco yok, terminal komut-yanıt, LSP/DAP yok, gerçek git geçmişi yok.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P0 · M · Bağ: PKA-56 · Durum: açık

#### PKA-58 · EPK-06 · Güvenlik ve gizlilik incelemesi: Tam IDE deneyimi
- **Sorun:** [ÖNERİ] Program EPK-06 «Tam IDE deneyimi» iş paketi 8/10. Bağlam: Monaco yok, terminal komut-yanıt, LSP/DAP yok, gerçek git geçmişi yok.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P0 · S · Bağ: PKA-57 · Durum: açık

#### PKA-59 · EPK-06 · Uçtan uca senaryo ve eval kümesi: Tam IDE deneyimi
- **Sorun:** [ÖNERİ] Program EPK-06 «Tam IDE deneyimi» iş paketi 9/10. Bağlam: Monaco yok, terminal komut-yanıt, LSP/DAP yok, gerçek git geçmişi yok.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P0 · M · Bağ: PKA-58 · Durum: açık

#### PKA-60 · EPK-06 · Ölçüm, belge ve runbook: Tam IDE deneyimi
- **Sorun:** [ÖNERİ] Program EPK-06 «Tam IDE deneyimi» iş paketi 10/10. Bağlam: Monaco yok, terminal komut-yanıt, LSP/DAP yok, gerçek git geçmişi yok.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Python/JS projesinde tanıma gitme, kesme noktası, etkileşimli terminal ve git geçmişi çalışır (e2e).
- **Meta:** P0 · M · Bağ: PKA-59 · Durum: açık

#### PKA-61 · EPK-07 · Tasarım belgesi ve ADR: Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi
- **Sorun:** [ÖNERİ] Program EPK-07 «Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi» iş paketi 1/10. Bağlam: Halüsinasyon ölçümleri küçük/şablonlu kümeyle; atıf doğruluğu ve kod doğrulama ölçülmedi.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### PKA-62 · EPK-07 · Veri modeli ve göç: Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi
- **Sorun:** [ÖNERİ] Program EPK-07 «Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi» iş paketi 2/10. Bağlam: Halüsinasyon ölçümleri küçük/şablonlu kümeyle; atıf doğruluğu ve kod doğrulama ölçülmedi.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P0 · M · Bağ: PKA-61 · Durum: açık

#### PKA-63 · EPK-07 · Çekirdek mantık: Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi
- **Sorun:** [ÖNERİ] Program EPK-07 «Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi» iş paketi 3/10. Bağlam: Halüsinasyon ölçümleri küçük/şablonlu kümeyle; atıf doğruluğu ve kod doğrulama ölçülmedi.
- **Değişiklik:** Cümle düzeyinde iddia-atıf eşleme, NLI hakemi, sayısal/birim denetimi, kodu sandbox'ta çalıştırma, çıktı sözleşmesi denetleyicisi.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P0 · L · Bağ: PKA-62 · Durum: açık

#### PKA-64 · EPK-07 · API ve yanıt şemaları: Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi
- **Sorun:** [ÖNERİ] Program EPK-07 «Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi» iş paketi 4/10. Bağlam: Halüsinasyon ölçümleri küçük/şablonlu kümeyle; atıf doğruluğu ve kod doğrulama ölçülmedi.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P0 · M · Bağ: PKA-63 · Durum: açık

#### PKA-65 · EPK-07 · Arayüz ve erişilebilirlik: Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi
- **Sorun:** [ÖNERİ] Program EPK-07 «Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi» iş paketi 5/10. Bağlam: Halüsinasyon ölçümleri küçük/şablonlu kümeyle; atıf doğruluğu ve kod doğrulama ölçülmedi.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P0 · M · Bağ: PKA-64 · Durum: açık

#### PKA-66 · EPK-07 · Birim ve sözleşme testleri: Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi
- **Sorun:** [ÖNERİ] Program EPK-07 «Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi» iş paketi 6/10. Bağlam: Halüsinasyon ölçümleri küçük/şablonlu kümeyle; atıf doğruluğu ve kod doğrulama ölçülmedi.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P0 · M · Bağ: PKA-65 · Durum: açık

#### PKA-67 · EPK-07 · Hata enjeksiyonu ve dayanıklılık: Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi
- **Sorun:** [ÖNERİ] Program EPK-07 «Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi» iş paketi 7/10. Bağlam: Halüsinasyon ölçümleri küçük/şablonlu kümeyle; atıf doğruluğu ve kod doğrulama ölçülmedi.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P0 · M · Bağ: PKA-66 · Durum: açık

#### PKA-68 · EPK-07 · Güvenlik ve gizlilik incelemesi: Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi
- **Sorun:** [ÖNERİ] Program EPK-07 «Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi» iş paketi 8/10. Bağlam: Halüsinasyon ölçümleri küçük/şablonlu kümeyle; atıf doğruluğu ve kod doğrulama ölçülmedi.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P0 · S · Bağ: PKA-67 · Durum: açık

#### PKA-69 · EPK-07 · Uçtan uca senaryo ve eval kümesi: Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi
- **Sorun:** [ÖNERİ] Program EPK-07 «Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi» iş paketi 9/10. Bağlam: Halüsinasyon ölçümleri küçük/şablonlu kümeyle; atıf doğruluğu ve kod doğrulama ölçülmedi.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P0 · M · Bağ: PKA-68 · Durum: açık

#### PKA-70 · EPK-07 · Ölçüm, belge ve runbook: Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi
- **Sorun:** [ÖNERİ] Program EPK-07 «Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi» iş paketi 10/10. Bağlam: Halüsinasyon ölçümleri küçük/şablonlu kümeyle; atıf doğruluğu ve kod doğrulama ölçülmedi.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Etiketli kümede atıf doğruluğu ≥ %90, uydurma sayı yakalama ≥ %90, kod çalışma oranı +15 puan.
- **Meta:** P0 · M · Bağ: PKA-69 · Durum: açık

#### PKA-71 · EPK-08 · Tasarım belgesi ve ADR: Sunum ve belge fabrikası: render, görsel kalite, şablonlar
- **Sorun:** [ÖNERİ] Program EPK-08 «Sunum ve belge fabrikası: render, görsel kalite, şablonlar» iş paketi 1/10. Bağlam: PPTX'te gerçek grafik oranı, geçiş geçerliliği ve render denetimi ölçülmedi; DOCX şablon yüklemesi yok.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### PKA-72 · EPK-08 · Veri modeli ve göç: Sunum ve belge fabrikası: render, görsel kalite, şablonlar
- **Sorun:** [ÖNERİ] Program EPK-08 «Sunum ve belge fabrikası: render, görsel kalite, şablonlar» iş paketi 2/10. Bağlam: PPTX'te gerçek grafik oranı, geçiş geçerliliği ve render denetimi ölçülmedi; DOCX şablon yüklemesi yok.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P0 · M · Bağ: PKA-71 · Durum: açık

#### PKA-73 · EPK-08 · Çekirdek mantık: Sunum ve belge fabrikası: render, görsel kalite, şablonlar
- **Sorun:** [ÖNERİ] Program EPK-08 «Sunum ve belge fabrikası: render, görsel kalite, şablonlar» iş paketi 3/10. Bağlam: PPTX'te gerçek grafik oranı, geçiş geçerliliği ve render denetimi ölçülmedi; DOCX şablon yüklemesi yok.
- **Değişiklik:** LibreOffice başsız render, taşma/çakışma/kontrast denetimi, şablon/tema kitaplığı, slayt başına yeniden üretme, kaynak slaytı.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P0 · L · Bağ: PKA-72 · Durum: açık

#### PKA-74 · EPK-08 · API ve yanıt şemaları: Sunum ve belge fabrikası: render, görsel kalite, şablonlar
- **Sorun:** [ÖNERİ] Program EPK-08 «Sunum ve belge fabrikası: render, görsel kalite, şablonlar» iş paketi 4/10. Bağlam: PPTX'te gerçek grafik oranı, geçiş geçerliliği ve render denetimi ölçülmedi; DOCX şablon yüklemesi yok.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P0 · M · Bağ: PKA-73 · Durum: açık

#### PKA-75 · EPK-08 · Arayüz ve erişilebilirlik: Sunum ve belge fabrikası: render, görsel kalite, şablonlar
- **Sorun:** [ÖNERİ] Program EPK-08 «Sunum ve belge fabrikası: render, görsel kalite, şablonlar» iş paketi 5/10. Bağlam: PPTX'te gerçek grafik oranı, geçiş geçerliliği ve render denetimi ölçülmedi; DOCX şablon yüklemesi yok.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P0 · M · Bağ: PKA-74 · Durum: açık

#### PKA-76 · EPK-08 · Birim ve sözleşme testleri: Sunum ve belge fabrikası: render, görsel kalite, şablonlar
- **Sorun:** [ÖNERİ] Program EPK-08 «Sunum ve belge fabrikası: render, görsel kalite, şablonlar» iş paketi 6/10. Bağlam: PPTX'te gerçek grafik oranı, geçiş geçerliliği ve render denetimi ölçülmedi; DOCX şablon yüklemesi yok.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P0 · M · Bağ: PKA-75 · Durum: açık

#### PKA-77 · EPK-08 · Hata enjeksiyonu ve dayanıklılık: Sunum ve belge fabrikası: render, görsel kalite, şablonlar
- **Sorun:** [ÖNERİ] Program EPK-08 «Sunum ve belge fabrikası: render, görsel kalite, şablonlar» iş paketi 7/10. Bağlam: PPTX'te gerçek grafik oranı, geçiş geçerliliği ve render denetimi ölçülmedi; DOCX şablon yüklemesi yok.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P0 · M · Bağ: PKA-76 · Durum: açık

#### PKA-78 · EPK-08 · Güvenlik ve gizlilik incelemesi: Sunum ve belge fabrikası: render, görsel kalite, şablonlar
- **Sorun:** [ÖNERİ] Program EPK-08 «Sunum ve belge fabrikası: render, görsel kalite, şablonlar» iş paketi 8/10. Bağlam: PPTX'te gerçek grafik oranı, geçiş geçerliliği ve render denetimi ölçülmedi; DOCX şablon yüklemesi yok.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P0 · S · Bağ: PKA-77 · Durum: açık

#### PKA-79 · EPK-08 · Uçtan uca senaryo ve eval kümesi: Sunum ve belge fabrikası: render, görsel kalite, şablonlar
- **Sorun:** [ÖNERİ] Program EPK-08 «Sunum ve belge fabrikası: render, görsel kalite, şablonlar» iş paketi 9/10. Bağlam: PPTX'te gerçek grafik oranı, geçiş geçerliliği ve render denetimi ölçülmedi; DOCX şablon yüklemesi yok.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P0 · M · Bağ: PKA-78 · Durum: açık

#### PKA-80 · EPK-08 · Ölçüm, belge ve runbook: Sunum ve belge fabrikası: render, görsel kalite, şablonlar
- **Sorun:** [ÖNERİ] Program EPK-08 «Sunum ve belge fabrikası: render, görsel kalite, şablonlar» iş paketi 10/10. Bağlam: PPTX'te gerçek grafik oranı, geçiş geçerliliği ve render denetimi ölçülmedi; DOCX şablon yüklemesi yok.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Eval sunumlarında görsel hata < %3; 30 dosya PowerPoint ve LibreOffice'te hatasız açılır.
- **Meta:** P0 · M · Bağ: PKA-79 · Durum: açık

#### PKA-81 · EPK-09 · Tasarım belgesi ve ADR: Çok modlu anlama: görsel, ses, video, OCR
- **Sorun:** [ÖNERİ] Program EPK-09 «Çok modlu anlama: görsel, ses, video, OCR» iş paketi 1/10. Bağlam: OCR kurulu değil; VLM/VQA, video ve ses ölçümleri yok.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### PKA-82 · EPK-09 · Veri modeli ve göç: Çok modlu anlama: görsel, ses, video, OCR
- **Sorun:** [ÖNERİ] Program EPK-09 «Çok modlu anlama: görsel, ses, video, OCR» iş paketi 2/10. Bağlam: OCR kurulu değil; VLM/VQA, video ve ses ölçümleri yok.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P0 · M · Bağ: PKA-81 · Durum: açık

#### PKA-83 · EPK-09 · Çekirdek mantık: Çok modlu anlama: görsel, ses, video, OCR
- **Sorun:** [ÖNERİ] Program EPK-09 «Çok modlu anlama: görsel, ses, video, OCR» iş paketi 3/10. Bağlam: OCR kurulu değil; VLM/VQA, video ve ses ölçümleri yok.
- **Değişiklik:** Tesseract/PaddleOCR kurulumu, VLM hattı, ses→metin (WER ölçümü), video anahtar kare özeti, 'okunamadı' dürüstlüğü.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P0 · L · Bağ: PKA-82 · Durum: açık

#### PKA-84 · EPK-09 · API ve yanıt şemaları: Çok modlu anlama: görsel, ses, video, OCR
- **Sorun:** [ÖNERİ] Program EPK-09 «Çok modlu anlama: görsel, ses, video, OCR» iş paketi 4/10. Bağlam: OCR kurulu değil; VLM/VQA, video ve ses ölçümleri yok.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P0 · M · Bağ: PKA-83 · Durum: açık

#### PKA-85 · EPK-09 · Arayüz ve erişilebilirlik: Çok modlu anlama: görsel, ses, video, OCR
- **Sorun:** [ÖNERİ] Program EPK-09 «Çok modlu anlama: görsel, ses, video, OCR» iş paketi 5/10. Bağlam: OCR kurulu değil; VLM/VQA, video ve ses ölçümleri yok.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P0 · M · Bağ: PKA-84 · Durum: açık

#### PKA-86 · EPK-09 · Birim ve sözleşme testleri: Çok modlu anlama: görsel, ses, video, OCR
- **Sorun:** [ÖNERİ] Program EPK-09 «Çok modlu anlama: görsel, ses, video, OCR» iş paketi 6/10. Bağlam: OCR kurulu değil; VLM/VQA, video ve ses ölçümleri yok.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P0 · M · Bağ: PKA-85 · Durum: açık

#### PKA-87 · EPK-09 · Hata enjeksiyonu ve dayanıklılık: Çok modlu anlama: görsel, ses, video, OCR
- **Sorun:** [ÖNERİ] Program EPK-09 «Çok modlu anlama: görsel, ses, video, OCR» iş paketi 7/10. Bağlam: OCR kurulu değil; VLM/VQA, video ve ses ölçümleri yok.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P0 · M · Bağ: PKA-86 · Durum: açık

#### PKA-88 · EPK-09 · Güvenlik ve gizlilik incelemesi: Çok modlu anlama: görsel, ses, video, OCR
- **Sorun:** [ÖNERİ] Program EPK-09 «Çok modlu anlama: görsel, ses, video, OCR» iş paketi 8/10. Bağlam: OCR kurulu değil; VLM/VQA, video ve ses ölçümleri yok.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P0 · S · Bağ: PKA-87 · Durum: açık

#### PKA-89 · EPK-09 · Uçtan uca senaryo ve eval kümesi: Çok modlu anlama: görsel, ses, video, OCR
- **Sorun:** [ÖNERİ] Program EPK-09 «Çok modlu anlama: görsel, ses, video, OCR» iş paketi 9/10. Bağlam: OCR kurulu değil; VLM/VQA, video ve ses ölçümleri yok.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P0 · M · Bağ: PKA-88 · Durum: açık

#### PKA-90 · EPK-09 · Ölçüm, belge ve runbook: Çok modlu anlama: görsel, ses, video, OCR
- **Sorun:** [ÖNERİ] Program EPK-09 «Çok modlu anlama: görsel, ses, video, OCR» iş paketi 10/10. Bağlam: OCR kurulu değil; VLM/VQA, video ve ses ölçümleri yok.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** 60 görselde VQA ≥ %75; Türkçe WER ölçülür; OCR yokken kullanıcıya net uyarı.
- **Meta:** P0 · M · Bağ: PKA-89 · Durum: açık

#### PKA-91 · EPK-10 · Tasarım belgesi ve ADR: Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı
- **Sorun:** [ÖNERİ] Program EPK-10 «Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı» iş paketi 1/10. Bağlam: 6 ajanla 3x hızlanma ve ajan düşme senaryoları otomatik ölçülmedi.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### PKA-92 · EPK-10 · Veri modeli ve göç: Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı
- **Sorun:** [ÖNERİ] Program EPK-10 «Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı» iş paketi 2/10. Bağlam: 6 ajanla 3x hızlanma ve ajan düşme senaryoları otomatik ölçülmedi.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P0 · M · Bağ: PKA-91 · Durum: açık

#### PKA-93 · EPK-10 · Çekirdek mantık: Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı
- **Sorun:** [ÖNERİ] Program EPK-10 «Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı» iş paketi 3/10. Bağlam: 6 ajanla 3x hızlanma ve ajan düşme senaryoları otomatik ölçülmedi.
- **Değişiklik:** Standart iş yükleri, 1/2/4/6 ajan ölçümü, Amdahl analizi, kaos betikleri, idempotent sonuç kabulü.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P0 · L · Bağ: PKA-92 · Durum: açık

#### PKA-94 · EPK-10 · API ve yanıt şemaları: Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı
- **Sorun:** [ÖNERİ] Program EPK-10 «Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı» iş paketi 4/10. Bağlam: 6 ajanla 3x hızlanma ve ajan düşme senaryoları otomatik ölçülmedi.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P0 · M · Bağ: PKA-93 · Durum: açık

#### PKA-95 · EPK-10 · Arayüz ve erişilebilirlik: Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı
- **Sorun:** [ÖNERİ] Program EPK-10 «Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı» iş paketi 5/10. Bağlam: 6 ajanla 3x hızlanma ve ajan düşme senaryoları otomatik ölçülmedi.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P0 · M · Bağ: PKA-94 · Durum: açık

#### PKA-96 · EPK-10 · Birim ve sözleşme testleri: Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı
- **Sorun:** [ÖNERİ] Program EPK-10 «Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı» iş paketi 6/10. Bağlam: 6 ajanla 3x hızlanma ve ajan düşme senaryoları otomatik ölçülmedi.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P0 · M · Bağ: PKA-95 · Durum: açık

#### PKA-97 · EPK-10 · Hata enjeksiyonu ve dayanıklılık: Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı
- **Sorun:** [ÖNERİ] Program EPK-10 «Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı» iş paketi 7/10. Bağlam: 6 ajanla 3x hızlanma ve ajan düşme senaryoları otomatik ölçülmedi.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P0 · M · Bağ: PKA-96 · Durum: açık

#### PKA-98 · EPK-10 · Güvenlik ve gizlilik incelemesi: Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı
- **Sorun:** [ÖNERİ] Program EPK-10 «Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı» iş paketi 8/10. Bağlam: 6 ajanla 3x hızlanma ve ajan düşme senaryoları otomatik ölçülmedi.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P0 · S · Bağ: PKA-97 · Durum: açık

#### PKA-99 · EPK-10 · Uçtan uca senaryo ve eval kümesi: Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı
- **Sorun:** [ÖNERİ] Program EPK-10 «Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı» iş paketi 9/10. Bağlam: 6 ajanla 3x hızlanma ve ajan düşme senaryoları otomatik ölçülmedi.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P0 · M · Bağ: PKA-98 · Durum: açık

## PKB · İş paketleri (2)

#### PKB-01 · EPK-10 · Ölçüm, belge ve runbook: Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı
- **Sorun:** [ÖNERİ] Program EPK-10 «Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı» iş paketi 10/10. Bağlam: 6 ajanla 3x hızlanma ve ajan düşme senaryoları otomatik ölçülmedi.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Hızlanma raporu otomatik; ajan düşünce görev yeniden atanır ve çift sonuç oluşmaz.
- **Meta:** P0 · M · Bağ: PKA-99 · Durum: açık

#### PKB-02 · EPK-11 · Tasarım belgesi ve ADR: Kullanıcı tanımlı asistan/ajan oluşturucu
- **Sorun:** [ÖNERİ] Program EPK-11 «Kullanıcı tanımlı asistan/ajan oluşturucu» iş paketi 1/10. Bağlam: GPT/Gem benzeri özel asistan tanımlama yok.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### PKB-03 · EPK-11 · Veri modeli ve göç: Kullanıcı tanımlı asistan/ajan oluşturucu
- **Sorun:** [ÖNERİ] Program EPK-11 «Kullanıcı tanımlı asistan/ajan oluşturucu» iş paketi 2/10. Bağlam: GPT/Gem benzeri özel asistan tanımlama yok.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P1 · M · Bağ: PKB-02 · Durum: açık

#### PKB-04 · EPK-11 · Çekirdek mantık: Kullanıcı tanımlı asistan/ajan oluşturucu
- **Sorun:** [ÖNERİ] Program EPK-11 «Kullanıcı tanımlı asistan/ajan oluşturucu» iş paketi 3/10. Bağlam: GPT/Gem benzeri özel asistan tanımlama yok.
- **Değişiklik:** Talimat, bilgi koleksiyonu, araç izni, model seçimi ve paylaşım içeren asistan tanımı; sürümleme.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P1 · L · Bağ: PKB-03 · Durum: açık

#### PKB-05 · EPK-11 · API ve yanıt şemaları: Kullanıcı tanımlı asistan/ajan oluşturucu
- **Sorun:** [ÖNERİ] Program EPK-11 «Kullanıcı tanımlı asistan/ajan oluşturucu» iş paketi 4/10. Bağlam: GPT/Gem benzeri özel asistan tanımlama yok.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P1 · M · Bağ: PKB-04 · Durum: açık

#### PKB-06 · EPK-11 · Arayüz ve erişilebilirlik: Kullanıcı tanımlı asistan/ajan oluşturucu
- **Sorun:** [ÖNERİ] Program EPK-11 «Kullanıcı tanımlı asistan/ajan oluşturucu» iş paketi 5/10. Bağlam: GPT/Gem benzeri özel asistan tanımlama yok.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P1 · M · Bağ: PKB-05 · Durum: açık

#### PKB-07 · EPK-11 · Birim ve sözleşme testleri: Kullanıcı tanımlı asistan/ajan oluşturucu
- **Sorun:** [ÖNERİ] Program EPK-11 «Kullanıcı tanımlı asistan/ajan oluşturucu» iş paketi 6/10. Bağlam: GPT/Gem benzeri özel asistan tanımlama yok.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P1 · M · Bağ: PKB-06 · Durum: açık

#### PKB-08 · EPK-11 · Hata enjeksiyonu ve dayanıklılık: Kullanıcı tanımlı asistan/ajan oluşturucu
- **Sorun:** [ÖNERİ] Program EPK-11 «Kullanıcı tanımlı asistan/ajan oluşturucu» iş paketi 7/10. Bağlam: GPT/Gem benzeri özel asistan tanımlama yok.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P1 · M · Bağ: PKB-07 · Durum: açık

#### PKB-09 · EPK-11 · Güvenlik ve gizlilik incelemesi: Kullanıcı tanımlı asistan/ajan oluşturucu
- **Sorun:** [ÖNERİ] Program EPK-11 «Kullanıcı tanımlı asistan/ajan oluşturucu» iş paketi 8/10. Bağlam: GPT/Gem benzeri özel asistan tanımlama yok.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P1 · S · Bağ: PKB-08 · Durum: açık

#### PKB-10 · EPK-11 · Uçtan uca senaryo ve eval kümesi: Kullanıcı tanımlı asistan/ajan oluşturucu
- **Sorun:** [ÖNERİ] Program EPK-11 «Kullanıcı tanımlı asistan/ajan oluşturucu» iş paketi 9/10. Bağlam: GPT/Gem benzeri özel asistan tanımlama yok.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P1 · M · Bağ: PKB-09 · Durum: açık

#### PKB-11 · EPK-11 · Ölçüm, belge ve runbook: Kullanıcı tanımlı asistan/ajan oluşturucu
- **Sorun:** [ÖNERİ] Program EPK-11 «Kullanıcı tanımlı asistan/ajan oluşturucu» iş paketi 10/10. Bağlam: GPT/Gem benzeri özel asistan tanımlama yok.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Kullanıcı kod yazmadan özel asistan oluşturur, paylaşır ve sürümünü geri alır.
- **Meta:** P1 · M · Bağ: PKB-10 · Durum: açık

#### PKB-12 · EPK-12 · Tasarım belgesi ve ADR: Zamanlanmış ve olay tetiklemeli görevler
- **Sorun:** [ÖNERİ] Program EPK-12 «Zamanlanmış ve olay tetiklemeli görevler» iş paketi 1/10. Bağlam: Cron/webhook yok; 'her sabah rapor' yapılamıyor.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### PKB-13 · EPK-12 · Veri modeli ve göç: Zamanlanmış ve olay tetiklemeli görevler
- **Sorun:** [ÖNERİ] Program EPK-12 «Zamanlanmış ve olay tetiklemeli görevler» iş paketi 2/10. Bağlam: Cron/webhook yok; 'her sabah rapor' yapılamıyor.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P1 · M · Bağ: PKB-12 · Durum: açık

#### PKB-14 · EPK-12 · Çekirdek mantık: Zamanlanmış ve olay tetiklemeli görevler
- **Sorun:** [ÖNERİ] Program EPK-12 «Zamanlanmış ve olay tetiklemeli görevler» iş paketi 3/10. Bağlam: Cron/webhook yok; 'her sabah rapor' yapılamıyor.
- **Değişiklik:** Zamanlayıcı, webhook alıcı/gönderici, görev geçmişi, başarısızlık uyarısı.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P1 · L · Bağ: PKB-13 · Durum: açık

#### PKB-15 · EPK-12 · API ve yanıt şemaları: Zamanlanmış ve olay tetiklemeli görevler
- **Sorun:** [ÖNERİ] Program EPK-12 «Zamanlanmış ve olay tetiklemeli görevler» iş paketi 4/10. Bağlam: Cron/webhook yok; 'her sabah rapor' yapılamıyor.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P1 · M · Bağ: PKB-14 · Durum: açık

#### PKB-16 · EPK-12 · Arayüz ve erişilebilirlik: Zamanlanmış ve olay tetiklemeli görevler
- **Sorun:** [ÖNERİ] Program EPK-12 «Zamanlanmış ve olay tetiklemeli görevler» iş paketi 5/10. Bağlam: Cron/webhook yok; 'her sabah rapor' yapılamıyor.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P1 · M · Bağ: PKB-15 · Durum: açık

#### PKB-17 · EPK-12 · Birim ve sözleşme testleri: Zamanlanmış ve olay tetiklemeli görevler
- **Sorun:** [ÖNERİ] Program EPK-12 «Zamanlanmış ve olay tetiklemeli görevler» iş paketi 6/10. Bağlam: Cron/webhook yok; 'her sabah rapor' yapılamıyor.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P1 · M · Bağ: PKB-16 · Durum: açık

#### PKB-18 · EPK-12 · Hata enjeksiyonu ve dayanıklılık: Zamanlanmış ve olay tetiklemeli görevler
- **Sorun:** [ÖNERİ] Program EPK-12 «Zamanlanmış ve olay tetiklemeli görevler» iş paketi 7/10. Bağlam: Cron/webhook yok; 'her sabah rapor' yapılamıyor.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P1 · M · Bağ: PKB-17 · Durum: açık

#### PKB-19 · EPK-12 · Güvenlik ve gizlilik incelemesi: Zamanlanmış ve olay tetiklemeli görevler
- **Sorun:** [ÖNERİ] Program EPK-12 «Zamanlanmış ve olay tetiklemeli görevler» iş paketi 8/10. Bağlam: Cron/webhook yok; 'her sabah rapor' yapılamıyor.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P1 · S · Bağ: PKB-18 · Durum: açık

#### PKB-20 · EPK-12 · Uçtan uca senaryo ve eval kümesi: Zamanlanmış ve olay tetiklemeli görevler
- **Sorun:** [ÖNERİ] Program EPK-12 «Zamanlanmış ve olay tetiklemeli görevler» iş paketi 9/10. Bağlam: Cron/webhook yok; 'her sabah rapor' yapılamıyor.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P1 · M · Bağ: PKB-19 · Durum: açık

#### PKB-21 · EPK-12 · Ölçüm, belge ve runbook: Zamanlanmış ve olay tetiklemeli görevler
- **Sorun:** [ÖNERİ] Program EPK-12 «Zamanlanmış ve olay tetiklemeli görevler» iş paketi 10/10. Bağlam: Cron/webhook yok; 'her sabah rapor' yapılamıyor.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Zamanlanmış görev çalışır, sonucu bildirir, hata yeniden denenir.
- **Meta:** P1 · M · Bağ: PKB-20 · Durum: açık

#### PKB-22 · EPK-13 · Tasarım belgesi ve ADR: Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-post
- **Sorun:** [ÖNERİ] Program EPK-13 «Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-posta» iş paketi 1/10. Bağlam: Bağlayıcılar yok; MCP yalnız istemci.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### PKB-23 · EPK-13 · Veri modeli ve göç: Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-post
- **Sorun:** [ÖNERİ] Program EPK-13 «Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-posta» iş paketi 2/10. Bağlam: Bağlayıcılar yok; MCP yalnız istemci.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P1 · M · Bağ: PKB-22 · Durum: açık

#### PKB-24 · EPK-13 · Çekirdek mantık: Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-post
- **Sorun:** [ÖNERİ] Program EPK-13 «Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-posta» iş paketi 3/10. Bağlam: Bağlayıcılar yok; MCP yalnız istemci.
- **Değişiklik:** OAuth'suz yerel öncelikli bağlayıcılar, MCP sunucusu olarak dışa açma, izin kapsamları, onay kapısı.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P1 · L · Bağ: PKB-23 · Durum: açık

#### PKB-25 · EPK-13 · API ve yanıt şemaları: Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-post
- **Sorun:** [ÖNERİ] Program EPK-13 «Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-posta» iş paketi 4/10. Bağlam: Bağlayıcılar yok; MCP yalnız istemci.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P1 · M · Bağ: PKB-24 · Durum: açık

#### PKB-26 · EPK-13 · Arayüz ve erişilebilirlik: Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-post
- **Sorun:** [ÖNERİ] Program EPK-13 «Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-posta» iş paketi 5/10. Bağlam: Bağlayıcılar yok; MCP yalnız istemci.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P1 · M · Bağ: PKB-25 · Durum: açık

#### PKB-27 · EPK-13 · Birim ve sözleşme testleri: Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-post
- **Sorun:** [ÖNERİ] Program EPK-13 «Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-posta» iş paketi 6/10. Bağlam: Bağlayıcılar yok; MCP yalnız istemci.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P1 · M · Bağ: PKB-26 · Durum: açık

#### PKB-28 · EPK-13 · Hata enjeksiyonu ve dayanıklılık: Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-post
- **Sorun:** [ÖNERİ] Program EPK-13 «Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-posta» iş paketi 7/10. Bağlam: Bağlayıcılar yok; MCP yalnız istemci.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P1 · M · Bağ: PKB-27 · Durum: açık

#### PKB-29 · EPK-13 · Güvenlik ve gizlilik incelemesi: Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-post
- **Sorun:** [ÖNERİ] Program EPK-13 «Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-posta» iş paketi 8/10. Bağlam: Bağlayıcılar yok; MCP yalnız istemci.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P1 · S · Bağ: PKB-28 · Durum: açık

#### PKB-30 · EPK-13 · Uçtan uca senaryo ve eval kümesi: Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-post
- **Sorun:** [ÖNERİ] Program EPK-13 «Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-posta» iş paketi 9/10. Bağlam: Bağlayıcılar yok; MCP yalnız istemci.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P1 · M · Bağ: PKB-29 · Durum: açık

#### PKB-31 · EPK-13 · Ölçüm, belge ve runbook: Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-post
- **Sorun:** [ÖNERİ] Program EPK-13 «Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-posta» iş paketi 10/10. Bağlam: Bağlayıcılar yok; MCP yalnız istemci.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Her bağlayıcı için izinli/izinsiz senaryo testi; onaysız yan etki yok.
- **Meta:** P1 · M · Bağ: PKB-30 · Durum: açık

#### PKB-32 · EPK-14 · Tasarım belgesi ve ADR: Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli
- **Sorun:** [ÖNERİ] Program EPK-14 «Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli» iş paketi 1/10. Bağlam: Vektör arama ölçeği ve reranker kazancı ölçülmedi.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### PKB-33 · EPK-14 · Veri modeli ve göç: Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli
- **Sorun:** [ÖNERİ] Program EPK-14 «Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli» iş paketi 2/10. Bağlam: Vektör arama ölçeği ve reranker kazancı ölçülmedi.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P1 · M · Bağ: PKB-32 · Durum: açık

#### PKB-34 · EPK-14 · Çekirdek mantık: Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli
- **Sorun:** [ÖNERİ] Program EPK-14 «Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli» iş paketi 3/10. Bağlam: Vektör arama ölçeği ve reranker kazancı ölçülmedi.
- **Değişiklik:** sqlite-vec/HNSW, cross-encoder, parent-child getirme, sorgu yeniden yazma, çok dilli gömme, retrieval eval.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P1 · L · Bağ: PKB-33 · Durum: açık

#### PKB-35 · EPK-14 · API ve yanıt şemaları: Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli
- **Sorun:** [ÖNERİ] Program EPK-14 «Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli» iş paketi 4/10. Bağlam: Vektör arama ölçeği ve reranker kazancı ölçülmedi.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P1 · M · Bağ: PKB-34 · Durum: açık

#### PKB-36 · EPK-14 · Arayüz ve erişilebilirlik: Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli
- **Sorun:** [ÖNERİ] Program EPK-14 «Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli» iş paketi 5/10. Bağlam: Vektör arama ölçeği ve reranker kazancı ölçülmedi.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P1 · M · Bağ: PKB-35 · Durum: açık

#### PKB-37 · EPK-14 · Birim ve sözleşme testleri: Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli
- **Sorun:** [ÖNERİ] Program EPK-14 «Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli» iş paketi 6/10. Bağlam: Vektör arama ölçeği ve reranker kazancı ölçülmedi.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P1 · M · Bağ: PKB-36 · Durum: açık

#### PKB-38 · EPK-14 · Hata enjeksiyonu ve dayanıklılık: Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli
- **Sorun:** [ÖNERİ] Program EPK-14 «Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli» iş paketi 7/10. Bağlam: Vektör arama ölçeği ve reranker kazancı ölçülmedi.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P1 · M · Bağ: PKB-37 · Durum: açık

#### PKB-39 · EPK-14 · Güvenlik ve gizlilik incelemesi: Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli
- **Sorun:** [ÖNERİ] Program EPK-14 «Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli» iş paketi 8/10. Bağlam: Vektör arama ölçeği ve reranker kazancı ölçülmedi.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P1 · S · Bağ: PKB-38 · Durum: açık

#### PKB-40 · EPK-14 · Uçtan uca senaryo ve eval kümesi: Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli
- **Sorun:** [ÖNERİ] Program EPK-14 «Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli» iş paketi 9/10. Bağlam: Vektör arama ölçeği ve reranker kazancı ölçülmedi.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P1 · M · Bağ: PKB-39 · Durum: açık

#### PKB-41 · EPK-14 · Ölçüm, belge ve runbook: Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli
- **Sorun:** [ÖNERİ] Program EPK-14 «Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli» iş paketi 10/10. Bağlam: Vektör arama ölçeği ve reranker kazancı ölçülmedi.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** 100.000 parçada p95 < 150 ms; nDCG@5 +5 puan; çapraz dil recall ≥ %70.
- **Meta:** P1 · M · Bağ: PKB-40 · Durum: açık

#### PKB-42 · EPK-15 · Tasarım belgesi ve ADR: Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünü
- **Sorun:** [ÖNERİ] Program EPK-15 «Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünürlük» iş paketi 1/10. Bağlam: Hafıza düzenleme/zaman çizelgesi/dışa aktarma eksik.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### PKB-43 · EPK-15 · Veri modeli ve göç: Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünü
- **Sorun:** [ÖNERİ] Program EPK-15 «Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünürlük» iş paketi 2/10. Bağlam: Hafıza düzenleme/zaman çizelgesi/dışa aktarma eksik.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P1 · M · Bağ: PKB-42 · Durum: açık

#### PKB-44 · EPK-15 · Çekirdek mantık: Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünü
- **Sorun:** [ÖNERİ] Program EPK-15 «Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünürlük» iş paketi 3/10. Bağlam: Hafıza düzenleme/zaman çizelgesi/dışa aktarma eksik.
- **Değişiklik:** Hafıza düzenleyici, çelişki çözümü, bozunum, hangi yanıtta kullanıldığı, dışa/içe aktarma.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P1 · L · Bağ: PKB-43 · Durum: açık

#### PKB-45 · EPK-15 · API ve yanıt şemaları: Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünü
- **Sorun:** [ÖNERİ] Program EPK-15 «Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünürlük» iş paketi 4/10. Bağlam: Hafıza düzenleme/zaman çizelgesi/dışa aktarma eksik.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P1 · M · Bağ: PKB-44 · Durum: açık

#### PKB-46 · EPK-15 · Arayüz ve erişilebilirlik: Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünü
- **Sorun:** [ÖNERİ] Program EPK-15 «Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünürlük» iş paketi 5/10. Bağlam: Hafıza düzenleme/zaman çizelgesi/dışa aktarma eksik.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P1 · M · Bağ: PKB-45 · Durum: açık

#### PKB-47 · EPK-15 · Birim ve sözleşme testleri: Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünü
- **Sorun:** [ÖNERİ] Program EPK-15 «Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünürlük» iş paketi 6/10. Bağlam: Hafıza düzenleme/zaman çizelgesi/dışa aktarma eksik.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P1 · M · Bağ: PKB-46 · Durum: açık

#### PKB-48 · EPK-15 · Hata enjeksiyonu ve dayanıklılık: Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünü
- **Sorun:** [ÖNERİ] Program EPK-15 «Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünürlük» iş paketi 7/10. Bağlam: Hafıza düzenleme/zaman çizelgesi/dışa aktarma eksik.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P1 · M · Bağ: PKB-47 · Durum: açık

#### PKB-49 · EPK-15 · Güvenlik ve gizlilik incelemesi: Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünü
- **Sorun:** [ÖNERİ] Program EPK-15 «Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünürlük» iş paketi 8/10. Bağlam: Hafıza düzenleme/zaman çizelgesi/dışa aktarma eksik.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P1 · S · Bağ: PKB-48 · Durum: açık

#### PKB-50 · EPK-15 · Uçtan uca senaryo ve eval kümesi: Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünü
- **Sorun:** [ÖNERİ] Program EPK-15 «Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünürlük» iş paketi 9/10. Bağlam: Hafıza düzenleme/zaman çizelgesi/dışa aktarma eksik.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P1 · M · Bağ: PKB-49 · Durum: açık

#### PKB-51 · EPK-15 · Ölçüm, belge ve runbook: Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünü
- **Sorun:** [ÖNERİ] Program EPK-15 «Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünürlük» iş paketi 10/10. Bağlam: Hafıza düzenleme/zaman çizelgesi/dışa aktarma eksik.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Çelişen tercih kullanıcıya sorulur; silinen hafıza hiçbir bağlamda görünmez.
- **Meta:** P1 · M · Bağ: PKB-50 · Durum: açık

#### PKB-52 · EPK-16 · Tasarım belgesi ve ADR: Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)
- **Sorun:** [ÖNERİ] Program EPK-16 «Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)» iş paketi 1/10. Bağlam: Studios sayfasında 341 etiketsiz kontrol; prefers-reduced-motion yok; sayfa başlıkları aynı.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### PKB-53 · EPK-16 · Veri modeli ve göç: Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)
- **Sorun:** [ÖNERİ] Program EPK-16 «Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)» iş paketi 2/10. Bağlam: Studios sayfasında 341 etiketsiz kontrol; prefers-reduced-motion yok; sayfa başlıkları aynı.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P1 · M · Bağ: PKB-52 · Durum: açık

#### PKB-54 · EPK-16 · Çekirdek mantık: Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)
- **Sorun:** [ÖNERİ] Program EPK-16 «Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)» iş paketi 3/10. Bağlam: Studios sayfasında 341 etiketsiz kontrol; prefers-reduced-motion yok; sayfa başlıkları aynı.
- **Değişiklik:** Bileşen kitaplığı, jetonlar, üç tema, axe CI, klavye e2e, ekran okuyucu testleri.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P1 · L · Bağ: PKB-53 · Durum: açık

#### PKB-55 · EPK-16 · API ve yanıt şemaları: Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)
- **Sorun:** [ÖNERİ] Program EPK-16 «Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)» iş paketi 4/10. Bağlam: Studios sayfasında 341 etiketsiz kontrol; prefers-reduced-motion yok; sayfa başlıkları aynı.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P1 · M · Bağ: PKB-54 · Durum: açık

#### PKB-56 · EPK-16 · Arayüz ve erişilebilirlik: Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)
- **Sorun:** [ÖNERİ] Program EPK-16 «Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)» iş paketi 5/10. Bağlam: Studios sayfasında 341 etiketsiz kontrol; prefers-reduced-motion yok; sayfa başlıkları aynı.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P1 · M · Bağ: PKB-55 · Durum: açık

#### PKB-57 · EPK-16 · Birim ve sözleşme testleri: Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)
- **Sorun:** [ÖNERİ] Program EPK-16 «Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)» iş paketi 6/10. Bağlam: Studios sayfasında 341 etiketsiz kontrol; prefers-reduced-motion yok; sayfa başlıkları aynı.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P1 · M · Bağ: PKB-56 · Durum: açık

#### PKB-58 · EPK-16 · Hata enjeksiyonu ve dayanıklılık: Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)
- **Sorun:** [ÖNERİ] Program EPK-16 «Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)» iş paketi 7/10. Bağlam: Studios sayfasında 341 etiketsiz kontrol; prefers-reduced-motion yok; sayfa başlıkları aynı.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P1 · M · Bağ: PKB-57 · Durum: açık

#### PKB-59 · EPK-16 · Güvenlik ve gizlilik incelemesi: Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)
- **Sorun:** [ÖNERİ] Program EPK-16 «Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)» iş paketi 8/10. Bağlam: Studios sayfasında 341 etiketsiz kontrol; prefers-reduced-motion yok; sayfa başlıkları aynı.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P1 · S · Bağ: PKB-58 · Durum: açık

#### PKB-60 · EPK-16 · Uçtan uca senaryo ve eval kümesi: Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)
- **Sorun:** [ÖNERİ] Program EPK-16 «Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)» iş paketi 9/10. Bağlam: Studios sayfasında 341 etiketsiz kontrol; prefers-reduced-motion yok; sayfa başlıkları aynı.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P1 · M · Bağ: PKB-59 · Durum: açık

#### PKB-61 · EPK-16 · Ölçüm, belge ve runbook: Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)
- **Sorun:** [ÖNERİ] Program EPK-16 «Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)» iş paketi 10/10. Bağlam: Studios sayfasında 341 etiketsiz kontrol; prefers-reduced-motion yok; sayfa başlıkları aynı.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** axe kritik/ciddi 0; yalnız klavye ile sohbet, yükleme ve ayarlar kullanılabilir.
- **Meta:** P1 · M · Bağ: PKB-60 · Durum: açık

#### PKB-62 · EPK-17 · Tasarım belgesi ve ADR: Performans bütçesi ve gözlemlenebilirlik
- **Sorun:** [ÖNERİ] Program EPK-17 «Performans bütçesi ve gözlemlenebilirlik» iş paketi 1/10. Bağlam: Lighthouse/paket boyutu/yük testi yok; yavaş uç noktalar var.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### PKB-63 · EPK-17 · Veri modeli ve göç: Performans bütçesi ve gözlemlenebilirlik
- **Sorun:** [ÖNERİ] Program EPK-17 «Performans bütçesi ve gözlemlenebilirlik» iş paketi 2/10. Bağlam: Lighthouse/paket boyutu/yük testi yok; yavaş uç noktalar var.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P1 · M · Bağ: PKB-62 · Durum: açık

#### PKB-64 · EPK-17 · Çekirdek mantık: Performans bütçesi ve gözlemlenebilirlik
- **Sorun:** [ÖNERİ] Program EPK-17 «Performans bütçesi ve gözlemlenebilirlik» iş paketi 3/10. Bağlam: Lighthouse/paket boyutu/yük testi yok; yavaş uç noktalar var.
- **Değişiklik:** Sanal liste, worker, kod bölme, yük/soak testleri, OpenTelemetry, SLO panoları.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P1 · L · Bağ: PKB-63 · Durum: açık

#### PKB-65 · EPK-17 · API ve yanıt şemaları: Performans bütçesi ve gözlemlenebilirlik
- **Sorun:** [ÖNERİ] Program EPK-17 «Performans bütçesi ve gözlemlenebilirlik» iş paketi 4/10. Bağlam: Lighthouse/paket boyutu/yük testi yok; yavaş uç noktalar var.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P1 · M · Bağ: PKB-64 · Durum: açık

#### PKB-66 · EPK-17 · Arayüz ve erişilebilirlik: Performans bütçesi ve gözlemlenebilirlik
- **Sorun:** [ÖNERİ] Program EPK-17 «Performans bütçesi ve gözlemlenebilirlik» iş paketi 5/10. Bağlam: Lighthouse/paket boyutu/yük testi yok; yavaş uç noktalar var.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P1 · M · Bağ: PKB-65 · Durum: açık

#### PKB-67 · EPK-17 · Birim ve sözleşme testleri: Performans bütçesi ve gözlemlenebilirlik
- **Sorun:** [ÖNERİ] Program EPK-17 «Performans bütçesi ve gözlemlenebilirlik» iş paketi 6/10. Bağlam: Lighthouse/paket boyutu/yük testi yok; yavaş uç noktalar var.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P1 · M · Bağ: PKB-66 · Durum: açık

#### PKB-68 · EPK-17 · Hata enjeksiyonu ve dayanıklılık: Performans bütçesi ve gözlemlenebilirlik
- **Sorun:** [ÖNERİ] Program EPK-17 «Performans bütçesi ve gözlemlenebilirlik» iş paketi 7/10. Bağlam: Lighthouse/paket boyutu/yük testi yok; yavaş uç noktalar var.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P1 · M · Bağ: PKB-67 · Durum: açık

#### PKB-69 · EPK-17 · Güvenlik ve gizlilik incelemesi: Performans bütçesi ve gözlemlenebilirlik
- **Sorun:** [ÖNERİ] Program EPK-17 «Performans bütçesi ve gözlemlenebilirlik» iş paketi 8/10. Bağlam: Lighthouse/paket boyutu/yük testi yok; yavaş uç noktalar var.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P1 · S · Bağ: PKB-68 · Durum: açık

#### PKB-70 · EPK-17 · Uçtan uca senaryo ve eval kümesi: Performans bütçesi ve gözlemlenebilirlik
- **Sorun:** [ÖNERİ] Program EPK-17 «Performans bütçesi ve gözlemlenebilirlik» iş paketi 9/10. Bağlam: Lighthouse/paket boyutu/yük testi yok; yavaş uç noktalar var.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P1 · M · Bağ: PKB-69 · Durum: açık

#### PKB-71 · EPK-17 · Ölçüm, belge ve runbook: Performans bütçesi ve gözlemlenebilirlik
- **Sorun:** [ÖNERİ] Program EPK-17 «Performans bütçesi ve gözlemlenebilirlik» iş paketi 10/10. Bağlam: Lighthouse/paket boyutu/yük testi yok; yavaş uç noktalar var.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** 1.000 mesajda ≥ 50 FPS; 20 eşzamanlı kullanıcıda hata < %1.
- **Meta:** P1 · M · Bağ: PKB-70 · Durum: açık

#### PKB-72 · EPK-18 · Tasarım belgesi ve ADR: Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML
- **Sorun:** [ÖNERİ] Program EPK-18 «Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML» iş paketi 1/10. Bağlam: Veri kütüphaneleri sohbetten kullanılamıyor.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### PKB-73 · EPK-18 · Veri modeli ve göç: Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML
- **Sorun:** [ÖNERİ] Program EPK-18 «Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML» iş paketi 2/10. Bağlam: Veri kütüphaneleri sohbetten kullanılamıyor.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P1 · M · Bağ: PKB-72 · Durum: açık

#### PKB-74 · EPK-18 · Çekirdek mantık: Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML
- **Sorun:** [ÖNERİ] Program EPK-18 «Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML» iş paketi 3/10. Bağlam: Veri kütüphaneleri sohbetten kullanılamıyor.
- **Değişiklik:** DuckDB/Polars motoru, otomatik grafik, istatistik testleri, ARIMA/Prophet, AutoML, sızıntı denetimi, pano üretimi.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P1 · L · Bağ: PKB-73 · Durum: açık

#### PKB-75 · EPK-18 · API ve yanıt şemaları: Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML
- **Sorun:** [ÖNERİ] Program EPK-18 «Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML» iş paketi 4/10. Bağlam: Veri kütüphaneleri sohbetten kullanılamıyor.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P1 · M · Bağ: PKB-74 · Durum: açık

#### PKB-76 · EPK-18 · Arayüz ve erişilebilirlik: Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML
- **Sorun:** [ÖNERİ] Program EPK-18 «Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML» iş paketi 5/10. Bağlam: Veri kütüphaneleri sohbetten kullanılamıyor.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P1 · M · Bağ: PKB-75 · Durum: açık

#### PKB-77 · EPK-18 · Birim ve sözleşme testleri: Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML
- **Sorun:** [ÖNERİ] Program EPK-18 «Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML» iş paketi 6/10. Bağlam: Veri kütüphaneleri sohbetten kullanılamıyor.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P1 · M · Bağ: PKB-76 · Durum: açık

#### PKB-78 · EPK-18 · Hata enjeksiyonu ve dayanıklılık: Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML
- **Sorun:** [ÖNERİ] Program EPK-18 «Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML» iş paketi 7/10. Bağlam: Veri kütüphaneleri sohbetten kullanılamıyor.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P1 · M · Bağ: PKB-77 · Durum: açık

#### PKB-79 · EPK-18 · Güvenlik ve gizlilik incelemesi: Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML
- **Sorun:** [ÖNERİ] Program EPK-18 «Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML» iş paketi 8/10. Bağlam: Veri kütüphaneleri sohbetten kullanılamıyor.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P1 · S · Bağ: PKB-78 · Durum: açık

#### PKB-80 · EPK-18 · Uçtan uca senaryo ve eval kümesi: Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML
- **Sorun:** [ÖNERİ] Program EPK-18 «Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML» iş paketi 9/10. Bağlam: Veri kütüphaneleri sohbetten kullanılamıyor.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P1 · M · Bağ: PKB-79 · Durum: açık

#### PKB-81 · EPK-18 · Ölçüm, belge ve runbook: Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML
- **Sorun:** [ÖNERİ] Program EPK-18 «Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML» iş paketi 10/10. Bağlam: Veri kütüphaneleri sohbetten kullanılamıyor.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** 200 vakalık set ≥ %95 doğruluk; AutoML sızıntı uyarısı.
- **Meta:** P1 · M · Bağ: PKB-80 · Durum: açık

#### PKB-82 · EPK-19 · Tasarım belgesi ve ADR: Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlend
- **Sorun:** [ÖNERİ] Program EPK-19 «Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlendirme» iş paketi 1/10. Bağlam: Quiz/flashcard/ilerleme takibi yok.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### PKB-83 · EPK-19 · Veri modeli ve göç: Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlend
- **Sorun:** [ÖNERİ] Program EPK-19 «Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlendirme» iş paketi 2/10. Bağlam: Quiz/flashcard/ilerleme takibi yok.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P1 · M · Bağ: PKB-82 · Durum: açık

#### PKB-84 · EPK-19 · Çekirdek mantık: Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlend
- **Sorun:** [ÖNERİ] Program EPK-19 «Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlendirme» iş paketi 3/10. Bağlam: Quiz/flashcard/ilerleme takibi yok.
- **Değişiklik:** Müfredat uyumlu ders planı, alıştırma ve cevap anahtarı, aralıklı tekrar, ödev otomatik değerlendirme.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P1 · L · Bağ: PKB-83 · Durum: açık

#### PKB-85 · EPK-19 · API ve yanıt şemaları: Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlend
- **Sorun:** [ÖNERİ] Program EPK-19 «Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlendirme» iş paketi 4/10. Bağlam: Quiz/flashcard/ilerleme takibi yok.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P1 · M · Bağ: PKB-84 · Durum: açık

#### PKB-86 · EPK-19 · Arayüz ve erişilebilirlik: Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlend
- **Sorun:** [ÖNERİ] Program EPK-19 «Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlendirme» iş paketi 5/10. Bağlam: Quiz/flashcard/ilerleme takibi yok.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P1 · M · Bağ: PKB-85 · Durum: açık

#### PKB-87 · EPK-19 · Birim ve sözleşme testleri: Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlend
- **Sorun:** [ÖNERİ] Program EPK-19 «Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlendirme» iş paketi 6/10. Bağlam: Quiz/flashcard/ilerleme takibi yok.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P1 · M · Bağ: PKB-86 · Durum: açık

#### PKB-88 · EPK-19 · Hata enjeksiyonu ve dayanıklılık: Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlend
- **Sorun:** [ÖNERİ] Program EPK-19 «Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlendirme» iş paketi 7/10. Bağlam: Quiz/flashcard/ilerleme takibi yok.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P1 · M · Bağ: PKB-87 · Durum: açık

#### PKB-89 · EPK-19 · Güvenlik ve gizlilik incelemesi: Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlend
- **Sorun:** [ÖNERİ] Program EPK-19 «Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlendirme» iş paketi 8/10. Bağlam: Quiz/flashcard/ilerleme takibi yok.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P1 · S · Bağ: PKB-88 · Durum: açık

#### PKB-90 · EPK-19 · Uçtan uca senaryo ve eval kümesi: Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlend
- **Sorun:** [ÖNERİ] Program EPK-19 «Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlendirme» iş paketi 9/10. Bağlam: Quiz/flashcard/ilerleme takibi yok.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P1 · M · Bağ: PKB-89 · Durum: açık

#### PKB-91 · EPK-19 · Ölçüm, belge ve runbook: Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlend
- **Sorun:** [ÖNERİ] Program EPK-19 «Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlendirme» iş paketi 10/10. Bağlam: Quiz/flashcard/ilerleme takibi yok.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Üretilen 20 sınavda cevap anahtarı doğruluğu ≥ %95.
- **Meta:** P1 · M · Bağ: PKB-90 · Durum: açık

#### PKB-92 · EPK-20 · Tasarım belgesi ve ADR: Hukuk, sağlık, finans bilgi tabanları (kaynaklı)
- **Sorun:** [ÖNERİ] Program EPK-20 «Hukuk, sağlık, finans bilgi tabanları (kaynaklı)» iş paketi 1/10. Bağlam: Mevzuat, ilaç ve kur veri tabanları yok.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### PKB-93 · EPK-20 · Veri modeli ve göç: Hukuk, sağlık, finans bilgi tabanları (kaynaklı)
- **Sorun:** [ÖNERİ] Program EPK-20 «Hukuk, sağlık, finans bilgi tabanları (kaynaklı)» iş paketi 2/10. Bağlam: Mevzuat, ilaç ve kur veri tabanları yok.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P1 · M · Bağ: PKB-92 · Durum: açık

#### PKB-94 · EPK-20 · Çekirdek mantık: Hukuk, sağlık, finans bilgi tabanları (kaynaklı)
- **Sorun:** [ÖNERİ] Program EPK-20 «Hukuk, sağlık, finans bilgi tabanları (kaynaklı)» iş paketi 3/10. Bağlam: Mevzuat, ilaç ve kur veri tabanları yok.
- **Değişiklik:** Mevzuat koleksiyonu madde atıflı, ilaç etkileşimi, TCMB kuru, sorumluluk reddi ve acil yönlendirme.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P1 · L · Bağ: PKB-93 · Durum: açık

#### PKB-95 · EPK-20 · API ve yanıt şemaları: Hukuk, sağlık, finans bilgi tabanları (kaynaklı)
- **Sorun:** [ÖNERİ] Program EPK-20 «Hukuk, sağlık, finans bilgi tabanları (kaynaklı)» iş paketi 4/10. Bağlam: Mevzuat, ilaç ve kur veri tabanları yok.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P1 · M · Bağ: PKB-94 · Durum: açık

#### PKB-96 · EPK-20 · Arayüz ve erişilebilirlik: Hukuk, sağlık, finans bilgi tabanları (kaynaklı)
- **Sorun:** [ÖNERİ] Program EPK-20 «Hukuk, sağlık, finans bilgi tabanları (kaynaklı)» iş paketi 5/10. Bağlam: Mevzuat, ilaç ve kur veri tabanları yok.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P1 · M · Bağ: PKB-95 · Durum: açık

#### PKB-97 · EPK-20 · Birim ve sözleşme testleri: Hukuk, sağlık, finans bilgi tabanları (kaynaklı)
- **Sorun:** [ÖNERİ] Program EPK-20 «Hukuk, sağlık, finans bilgi tabanları (kaynaklı)» iş paketi 6/10. Bağlam: Mevzuat, ilaç ve kur veri tabanları yok.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P1 · M · Bağ: PKB-96 · Durum: açık

#### PKB-98 · EPK-20 · Hata enjeksiyonu ve dayanıklılık: Hukuk, sağlık, finans bilgi tabanları (kaynaklı)
- **Sorun:** [ÖNERİ] Program EPK-20 «Hukuk, sağlık, finans bilgi tabanları (kaynaklı)» iş paketi 7/10. Bağlam: Mevzuat, ilaç ve kur veri tabanları yok.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P1 · M · Bağ: PKB-97 · Durum: açık

#### PKB-99 · EPK-20 · Güvenlik ve gizlilik incelemesi: Hukuk, sağlık, finans bilgi tabanları (kaynaklı)
- **Sorun:** [ÖNERİ] Program EPK-20 «Hukuk, sağlık, finans bilgi tabanları (kaynaklı)» iş paketi 8/10. Bağlam: Mevzuat, ilaç ve kur veri tabanları yok.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P1 · S · Bağ: PKB-98 · Durum: açık

## PKC · İş paketleri (3)

#### PKC-01 · EPK-20 · Uçtan uca senaryo ve eval kümesi: Hukuk, sağlık, finans bilgi tabanları (kaynaklı)
- **Sorun:** [ÖNERİ] Program EPK-20 «Hukuk, sağlık, finans bilgi tabanları (kaynaklı)» iş paketi 9/10. Bağlam: Mevzuat, ilaç ve kur veri tabanları yok.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P1 · M · Bağ: PKB-99 · Durum: açık

#### PKC-02 · EPK-20 · Ölçüm, belge ve runbook: Hukuk, sağlık, finans bilgi tabanları (kaynaklı)
- **Sorun:** [ÖNERİ] Program EPK-20 «Hukuk, sağlık, finans bilgi tabanları (kaynaklı)» iş paketi 10/10. Bağlam: Mevzuat, ilaç ve kur veri tabanları yok.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Bu alan yanıtlarının %100'ü atıflı ve uyarılı.
- **Meta:** P1 · M · Bağ: PKC-01 · Durum: açık

#### PKC-03 · EPK-21 · Tasarım belgesi ve ADR: Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj
- **Sorun:** [ÖNERİ] Program EPK-21 «Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj» iş paketi 1/10. Bağlam: Alan formülleri literatür vakasıyla sınanmadı; malzeme/Spice/metraj yok.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### PKC-04 · EPK-21 · Veri modeli ve göç: Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj
- **Sorun:** [ÖNERİ] Program EPK-21 «Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj» iş paketi 2/10. Bağlam: Alan formülleri literatür vakasıyla sınanmadı; malzeme/Spice/metraj yok.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P1 · M · Bağ: PKC-03 · Durum: açık

#### PKC-05 · EPK-21 · Çekirdek mantık: Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj
- **Sorun:** [ÖNERİ] Program EPK-21 «Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj» iş paketi 3/10. Bağlam: Alan formülleri literatür vakasıyla sınanmadı; malzeme/Spice/metraj yok.
- **Değişiklik:** Doğrulanmış formül kitaplığı, malzeme veri tabanı, ngspice, DXF ölçü çıkarımı, G-kod simülasyonu.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P1 · L · Bağ: PKC-04 · Durum: açık

#### PKC-06 · EPK-21 · API ve yanıt şemaları: Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj
- **Sorun:** [ÖNERİ] Program EPK-21 «Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj» iş paketi 4/10. Bağlam: Alan formülleri literatür vakasıyla sınanmadı; malzeme/Spice/metraj yok.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P1 · M · Bağ: PKC-05 · Durum: açık

#### PKC-07 · EPK-21 · Arayüz ve erişilebilirlik: Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj
- **Sorun:** [ÖNERİ] Program EPK-21 «Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj» iş paketi 5/10. Bağlam: Alan formülleri literatür vakasıyla sınanmadı; malzeme/Spice/metraj yok.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P1 · M · Bağ: PKC-06 · Durum: açık

#### PKC-08 · EPK-21 · Birim ve sözleşme testleri: Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj
- **Sorun:** [ÖNERİ] Program EPK-21 «Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj» iş paketi 6/10. Bağlam: Alan formülleri literatür vakasıyla sınanmadı; malzeme/Spice/metraj yok.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P1 · M · Bağ: PKC-07 · Durum: açık

#### PKC-09 · EPK-21 · Hata enjeksiyonu ve dayanıklılık: Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj
- **Sorun:** [ÖNERİ] Program EPK-21 «Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj» iş paketi 7/10. Bağlam: Alan formülleri literatür vakasıyla sınanmadı; malzeme/Spice/metraj yok.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P1 · M · Bağ: PKC-08 · Durum: açık

#### PKC-10 · EPK-21 · Güvenlik ve gizlilik incelemesi: Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj
- **Sorun:** [ÖNERİ] Program EPK-21 «Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj» iş paketi 8/10. Bağlam: Alan formülleri literatür vakasıyla sınanmadı; malzeme/Spice/metraj yok.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P1 · S · Bağ: PKC-09 · Durum: açık

#### PKC-11 · EPK-21 · Uçtan uca senaryo ve eval kümesi: Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj
- **Sorun:** [ÖNERİ] Program EPK-21 «Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj» iş paketi 9/10. Bağlam: Alan formülleri literatür vakasıyla sınanmadı; malzeme/Spice/metraj yok.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P1 · M · Bağ: PKC-10 · Durum: açık

#### PKC-12 · EPK-21 · Ölçüm, belge ve runbook: Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj
- **Sorun:** [ÖNERİ] Program EPK-21 «Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj» iş paketi 10/10. Bağlam: Alan formülleri literatür vakasıyla sınanmadı; malzeme/Spice/metraj yok.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** 15 literatür vakasında sapma ≤ %5; 30 hatalı G-kodun ≥ %85'i yakalanır.
- **Meta:** P1 · M · Bağ: PKC-11 · Durum: açık

#### PKC-13 · EPK-22 · Tasarım belgesi ve ADR: Medya üretimi: görsel, ses, video, 3B
- **Sorun:** [ÖNERİ] Program EPK-22 «Medya üretimi: görsel, ses, video, 3B» iş paketi 1/10. Bağlam: Yerel görsel/TTS/video üretimi yok veya doğrulanmadı.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### PKC-14 · EPK-22 · Veri modeli ve göç: Medya üretimi: görsel, ses, video, 3B
- **Sorun:** [ÖNERİ] Program EPK-22 «Medya üretimi: görsel, ses, video, 3B» iş paketi 2/10. Bağlam: Yerel görsel/TTS/video üretimi yok veya doğrulanmadı.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P1 · M · Bağ: PKC-13 · Durum: açık

#### PKC-15 · EPK-22 · Çekirdek mantık: Medya üretimi: görsel, ses, video, 3B
- **Sorun:** [ÖNERİ] Program EPK-22 «Medya üretimi: görsel, ses, video, 3B» iş paketi 3/10. Bağlam: Yerel görsel/TTS/video üretimi yok veya doğrulanmadı.
- **Değişiklik:** ComfyUI/SD köprüsü, yerel TTS, SRT, moviepy montaj, three.js 3B şablon.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P1 · L · Bağ: PKC-14 · Durum: açık

#### PKC-16 · EPK-22 · API ve yanıt şemaları: Medya üretimi: görsel, ses, video, 3B
- **Sorun:** [ÖNERİ] Program EPK-22 «Medya üretimi: görsel, ses, video, 3B» iş paketi 4/10. Bağlam: Yerel görsel/TTS/video üretimi yok veya doğrulanmadı.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P1 · M · Bağ: PKC-15 · Durum: açık

#### PKC-17 · EPK-22 · Arayüz ve erişilebilirlik: Medya üretimi: görsel, ses, video, 3B
- **Sorun:** [ÖNERİ] Program EPK-22 «Medya üretimi: görsel, ses, video, 3B» iş paketi 5/10. Bağlam: Yerel görsel/TTS/video üretimi yok veya doğrulanmadı.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P1 · M · Bağ: PKC-16 · Durum: açık

#### PKC-18 · EPK-22 · Birim ve sözleşme testleri: Medya üretimi: görsel, ses, video, 3B
- **Sorun:** [ÖNERİ] Program EPK-22 «Medya üretimi: görsel, ses, video, 3B» iş paketi 6/10. Bağlam: Yerel görsel/TTS/video üretimi yok veya doğrulanmadı.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P1 · M · Bağ: PKC-17 · Durum: açık

#### PKC-19 · EPK-22 · Hata enjeksiyonu ve dayanıklılık: Medya üretimi: görsel, ses, video, 3B
- **Sorun:** [ÖNERİ] Program EPK-22 «Medya üretimi: görsel, ses, video, 3B» iş paketi 7/10. Bağlam: Yerel görsel/TTS/video üretimi yok veya doğrulanmadı.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P1 · M · Bağ: PKC-18 · Durum: açık

#### PKC-20 · EPK-22 · Güvenlik ve gizlilik incelemesi: Medya üretimi: görsel, ses, video, 3B
- **Sorun:** [ÖNERİ] Program EPK-22 «Medya üretimi: görsel, ses, video, 3B» iş paketi 8/10. Bağlam: Yerel görsel/TTS/video üretimi yok veya doğrulanmadı.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P1 · S · Bağ: PKC-19 · Durum: açık

#### PKC-21 · EPK-22 · Uçtan uca senaryo ve eval kümesi: Medya üretimi: görsel, ses, video, 3B
- **Sorun:** [ÖNERİ] Program EPK-22 «Medya üretimi: görsel, ses, video, 3B» iş paketi 9/10. Bağlam: Yerel görsel/TTS/video üretimi yok veya doğrulanmadı.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P1 · M · Bağ: PKC-20 · Durum: açık

#### PKC-22 · EPK-22 · Ölçüm, belge ve runbook: Medya üretimi: görsel, ses, video, 3B
- **Sorun:** [ÖNERİ] Program EPK-22 «Medya üretimi: görsel, ses, video, 3B» iş paketi 10/10. Bağlam: Yerel görsel/TTS/video üretimi yok veya doğrulanmadı.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Her üretici için kapalıysa net mesaj, açıksa örnek çıktı testi.
- **Meta:** P1 · M · Bağ: PKC-21 · Durum: açık

#### PKC-23 · EPK-23 · Tasarım belgesi ve ADR: Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu
- **Sorun:** [ÖNERİ] Program EPK-23 «Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu API» iş paketi 1/10. Bağlam: OpenAI uyumlu uç nokta, CLI, SDK, masaüstü paket yok.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### PKC-24 · EPK-23 · Veri modeli ve göç: Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu
- **Sorun:** [ÖNERİ] Program EPK-23 «Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu API» iş paketi 2/10. Bağlam: OpenAI uyumlu uç nokta, CLI, SDK, masaüstü paket yok.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P1 · M · Bağ: PKC-23 · Durum: açık

#### PKC-25 · EPK-23 · Çekirdek mantık: Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu
- **Sorun:** [ÖNERİ] Program EPK-23 «Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu API» iş paketi 3/10. Bağlam: OpenAI uyumlu uç nokta, CLI, SDK, masaüstü paket yok.
- **Değişiklik:** /v1/chat/completions uyumluluk katmanı, Python/JS SDK, CLI, Tauri/Electron paketi, tam PWA çevrimdışı.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P1 · L · Bağ: PKC-24 · Durum: açık

#### PKC-26 · EPK-23 · API ve yanıt şemaları: Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu
- **Sorun:** [ÖNERİ] Program EPK-23 «Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu API» iş paketi 4/10. Bağlam: OpenAI uyumlu uç nokta, CLI, SDK, masaüstü paket yok.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P1 · M · Bağ: PKC-25 · Durum: açık

#### PKC-27 · EPK-23 · Arayüz ve erişilebilirlik: Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu
- **Sorun:** [ÖNERİ] Program EPK-23 «Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu API» iş paketi 5/10. Bağlam: OpenAI uyumlu uç nokta, CLI, SDK, masaüstü paket yok.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P1 · M · Bağ: PKC-26 · Durum: açık

#### PKC-28 · EPK-23 · Birim ve sözleşme testleri: Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu
- **Sorun:** [ÖNERİ] Program EPK-23 «Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu API» iş paketi 6/10. Bağlam: OpenAI uyumlu uç nokta, CLI, SDK, masaüstü paket yok.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P1 · M · Bağ: PKC-27 · Durum: açık

#### PKC-29 · EPK-23 · Hata enjeksiyonu ve dayanıklılık: Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu
- **Sorun:** [ÖNERİ] Program EPK-23 «Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu API» iş paketi 7/10. Bağlam: OpenAI uyumlu uç nokta, CLI, SDK, masaüstü paket yok.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P1 · M · Bağ: PKC-28 · Durum: açık

#### PKC-30 · EPK-23 · Güvenlik ve gizlilik incelemesi: Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu
- **Sorun:** [ÖNERİ] Program EPK-23 «Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu API» iş paketi 8/10. Bağlam: OpenAI uyumlu uç nokta, CLI, SDK, masaüstü paket yok.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P1 · S · Bağ: PKC-29 · Durum: açık

#### PKC-31 · EPK-23 · Uçtan uca senaryo ve eval kümesi: Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu
- **Sorun:** [ÖNERİ] Program EPK-23 «Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu API» iş paketi 9/10. Bağlam: OpenAI uyumlu uç nokta, CLI, SDK, masaüstü paket yok.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P1 · M · Bağ: PKC-30 · Durum: açık

#### PKC-32 · EPK-23 · Ölçüm, belge ve runbook: Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu
- **Sorun:** [ÖNERİ] Program EPK-23 «Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu API» iş paketi 10/10. Bağlam: OpenAI uyumlu uç nokta, CLI, SDK, masaüstü paket yok.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Bir OpenAI SDK örneği platforma karşı çalışır; CLI ile sohbet edilir.
- **Meta:** P1 · M · Bağ: PKC-31 · Durum: açık

#### PKC-33 · EPK-24 · Tasarım belgesi ve ADR: Kurulum, güncelleme ve yedekleme ürünleşmesi
- **Sorun:** [ÖNERİ] Program EPK-24 «Kurulum, güncelleme ve yedekleme ürünleşmesi» iş paketi 1/10. Bağlam: Windows kurulum paketi, otomatik güncelleme ve zamanlı yedek arayüzü yok.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### PKC-34 · EPK-24 · Veri modeli ve göç: Kurulum, güncelleme ve yedekleme ürünleşmesi
- **Sorun:** [ÖNERİ] Program EPK-24 «Kurulum, güncelleme ve yedekleme ürünleşmesi» iş paketi 2/10. Bağlam: Windows kurulum paketi, otomatik güncelleme ve zamanlı yedek arayüzü yok.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P1 · M · Bağ: PKC-33 · Durum: açık

#### PKC-35 · EPK-24 · Çekirdek mantık: Kurulum, güncelleme ve yedekleme ürünleşmesi
- **Sorun:** [ÖNERİ] Program EPK-24 «Kurulum, güncelleme ve yedekleme ürünleşmesi» iş paketi 3/10. Bağlam: Windows kurulum paketi, otomatik güncelleme ve zamanlı yedek arayüzü yok.
- **Değişiklik:** Tek tıkla kurulum, sürüm kontrolü, güncelleme/geri alma, yedek zamanlama arayüzü, geri yükleme turu CI'da.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P1 · L · Bağ: PKC-34 · Durum: açık

#### PKC-36 · EPK-24 · API ve yanıt şemaları: Kurulum, güncelleme ve yedekleme ürünleşmesi
- **Sorun:** [ÖNERİ] Program EPK-24 «Kurulum, güncelleme ve yedekleme ürünleşmesi» iş paketi 4/10. Bağlam: Windows kurulum paketi, otomatik güncelleme ve zamanlı yedek arayüzü yok.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P1 · M · Bağ: PKC-35 · Durum: açık

#### PKC-37 · EPK-24 · Arayüz ve erişilebilirlik: Kurulum, güncelleme ve yedekleme ürünleşmesi
- **Sorun:** [ÖNERİ] Program EPK-24 «Kurulum, güncelleme ve yedekleme ürünleşmesi» iş paketi 5/10. Bağlam: Windows kurulum paketi, otomatik güncelleme ve zamanlı yedek arayüzü yok.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P1 · M · Bağ: PKC-36 · Durum: açık

#### PKC-38 · EPK-24 · Birim ve sözleşme testleri: Kurulum, güncelleme ve yedekleme ürünleşmesi
- **Sorun:** [ÖNERİ] Program EPK-24 «Kurulum, güncelleme ve yedekleme ürünleşmesi» iş paketi 6/10. Bağlam: Windows kurulum paketi, otomatik güncelleme ve zamanlı yedek arayüzü yok.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P1 · M · Bağ: PKC-37 · Durum: açık

#### PKC-39 · EPK-24 · Hata enjeksiyonu ve dayanıklılık: Kurulum, güncelleme ve yedekleme ürünleşmesi
- **Sorun:** [ÖNERİ] Program EPK-24 «Kurulum, güncelleme ve yedekleme ürünleşmesi» iş paketi 7/10. Bağlam: Windows kurulum paketi, otomatik güncelleme ve zamanlı yedek arayüzü yok.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P1 · M · Bağ: PKC-38 · Durum: açık

#### PKC-40 · EPK-24 · Güvenlik ve gizlilik incelemesi: Kurulum, güncelleme ve yedekleme ürünleşmesi
- **Sorun:** [ÖNERİ] Program EPK-24 «Kurulum, güncelleme ve yedekleme ürünleşmesi» iş paketi 8/10. Bağlam: Windows kurulum paketi, otomatik güncelleme ve zamanlı yedek arayüzü yok.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P1 · S · Bağ: PKC-39 · Durum: açık

#### PKC-41 · EPK-24 · Uçtan uca senaryo ve eval kümesi: Kurulum, güncelleme ve yedekleme ürünleşmesi
- **Sorun:** [ÖNERİ] Program EPK-24 «Kurulum, güncelleme ve yedekleme ürünleşmesi» iş paketi 9/10. Bağlam: Windows kurulum paketi, otomatik güncelleme ve zamanlı yedek arayüzü yok.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P1 · M · Bağ: PKC-40 · Durum: açık

#### PKC-42 · EPK-24 · Ölçüm, belge ve runbook: Kurulum, güncelleme ve yedekleme ürünleşmesi
- **Sorun:** [ÖNERİ] Program EPK-24 «Kurulum, güncelleme ve yedekleme ürünleşmesi» iş paketi 10/10. Bağlam: Windows kurulum paketi, otomatik güncelleme ve zamanlı yedek arayüzü yok.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Temiz Windows 11'de kurulum ≤ 15 dk; yedek→geri yükleme kayıt sayıları aynı.
- **Meta:** P1 · M · Bağ: PKC-41 · Durum: açık

#### PKC-43 · EPK-25 · Tasarım belgesi ve ADR: Gizlilik mühendisliği: PII, silme hakkı, şifreleme
- **Sorun:** [ÖNERİ] Program EPK-25 «Gizlilik mühendisliği: PII, silme hakkı, şifreleme» iş paketi 1/10. Bağlam: TOTP, hesap kilidi, oturum listesi, antivirüs ve sır taraması yok.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### PKC-44 · EPK-25 · Veri modeli ve göç: Gizlilik mühendisliği: PII, silme hakkı, şifreleme
- **Sorun:** [ÖNERİ] Program EPK-25 «Gizlilik mühendisliği: PII, silme hakkı, şifreleme» iş paketi 2/10. Bağlam: TOTP, hesap kilidi, oturum listesi, antivirüs ve sır taraması yok.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P1 · M · Bağ: PKC-43 · Durum: açık

#### PKC-45 · EPK-25 · Çekirdek mantık: Gizlilik mühendisliği: PII, silme hakkı, şifreleme
- **Sorun:** [ÖNERİ] Program EPK-25 «Gizlilik mühendisliği: PII, silme hakkı, şifreleme» iş paketi 3/10. Bağlam: TOTP, hesap kilidi, oturum listesi, antivirüs ve sır taraması yok.
- **Değişiklik:** TOTP, kilitleme, oturum yönetimi, alan şifreleme, antivirüs, silme akışı kanıtı, gizlilik sayfası.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P1 · L · Bağ: PKC-44 · Durum: açık

#### PKC-46 · EPK-25 · API ve yanıt şemaları: Gizlilik mühendisliği: PII, silme hakkı, şifreleme
- **Sorun:** [ÖNERİ] Program EPK-25 «Gizlilik mühendisliği: PII, silme hakkı, şifreleme» iş paketi 4/10. Bağlam: TOTP, hesap kilidi, oturum listesi, antivirüs ve sır taraması yok.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P1 · M · Bağ: PKC-45 · Durum: açık

#### PKC-47 · EPK-25 · Arayüz ve erişilebilirlik: Gizlilik mühendisliği: PII, silme hakkı, şifreleme
- **Sorun:** [ÖNERİ] Program EPK-25 «Gizlilik mühendisliği: PII, silme hakkı, şifreleme» iş paketi 5/10. Bağlam: TOTP, hesap kilidi, oturum listesi, antivirüs ve sır taraması yok.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P1 · M · Bağ: PKC-46 · Durum: açık

#### PKC-48 · EPK-25 · Birim ve sözleşme testleri: Gizlilik mühendisliği: PII, silme hakkı, şifreleme
- **Sorun:** [ÖNERİ] Program EPK-25 «Gizlilik mühendisliği: PII, silme hakkı, şifreleme» iş paketi 6/10. Bağlam: TOTP, hesap kilidi, oturum listesi, antivirüs ve sır taraması yok.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P1 · M · Bağ: PKC-47 · Durum: açık

#### PKC-49 · EPK-25 · Hata enjeksiyonu ve dayanıklılık: Gizlilik mühendisliği: PII, silme hakkı, şifreleme
- **Sorun:** [ÖNERİ] Program EPK-25 «Gizlilik mühendisliği: PII, silme hakkı, şifreleme» iş paketi 7/10. Bağlam: TOTP, hesap kilidi, oturum listesi, antivirüs ve sır taraması yok.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P1 · M · Bağ: PKC-48 · Durum: açık

#### PKC-50 · EPK-25 · Güvenlik ve gizlilik incelemesi: Gizlilik mühendisliği: PII, silme hakkı, şifreleme
- **Sorun:** [ÖNERİ] Program EPK-25 «Gizlilik mühendisliği: PII, silme hakkı, şifreleme» iş paketi 8/10. Bağlam: TOTP, hesap kilidi, oturum listesi, antivirüs ve sır taraması yok.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P1 · S · Bağ: PKC-49 · Durum: açık

#### PKC-51 · EPK-25 · Uçtan uca senaryo ve eval kümesi: Gizlilik mühendisliği: PII, silme hakkı, şifreleme
- **Sorun:** [ÖNERİ] Program EPK-25 «Gizlilik mühendisliği: PII, silme hakkı, şifreleme» iş paketi 9/10. Bağlam: TOTP, hesap kilidi, oturum listesi, antivirüs ve sır taraması yok.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P1 · M · Bağ: PKC-50 · Durum: açık

#### PKC-52 · EPK-25 · Ölçüm, belge ve runbook: Gizlilik mühendisliği: PII, silme hakkı, şifreleme
- **Sorun:** [ÖNERİ] Program EPK-25 «Gizlilik mühendisliği: PII, silme hakkı, şifreleme» iş paketi 10/10. Bağlam: TOTP, hesap kilidi, oturum listesi, antivirüs ve sır taraması yok.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Silme sonrası benzersiz dizge hiçbir yerde bulunmaz; 2FA'sız yönetici işlemi reddedilir (açıksa).
- **Meta:** P1 · M · Bağ: PKC-51 · Durum: açık

#### PKC-53 · EPK-26 · Tasarım belgesi ve ADR: Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam
- **Sorun:** [ÖNERİ] Program EPK-26 «Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam» iş paketi 1/10. Bağlam: Coverage dev bağımlılığı değil; e2e/eslint/tsc/playwright yapılandırması yok.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### PKC-54 · EPK-26 · Veri modeli ve göç: Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam
- **Sorun:** [ÖNERİ] Program EPK-26 «Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam» iş paketi 2/10. Bağlam: Coverage dev bağımlılığı değil; e2e/eslint/tsc/playwright yapılandırması yok.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P1 · M · Bağ: PKC-53 · Durum: açık

#### PKC-55 · EPK-26 · Çekirdek mantık: Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam
- **Sorun:** [ÖNERİ] Program EPK-26 «Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam» iş paketi 3/10. Bağlam: Coverage dev bağımlılığı değil; e2e/eslint/tsc/playwright yapılandırması yok.
- **Değişiklik:** Playwright, eslint, tsc, hypothesis, mutmut, diff-cover, görsel gerileme, flaky tespiti.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P1 · L · Bağ: PKC-54 · Durum: açık

#### PKC-56 · EPK-26 · API ve yanıt şemaları: Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam
- **Sorun:** [ÖNERİ] Program EPK-26 «Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam» iş paketi 4/10. Bağlam: Coverage dev bağımlılığı değil; e2e/eslint/tsc/playwright yapılandırması yok.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P1 · M · Bağ: PKC-55 · Durum: açık

#### PKC-57 · EPK-26 · Arayüz ve erişilebilirlik: Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam
- **Sorun:** [ÖNERİ] Program EPK-26 «Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam» iş paketi 5/10. Bağlam: Coverage dev bağımlılığı değil; e2e/eslint/tsc/playwright yapılandırması yok.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P1 · M · Bağ: PKC-56 · Durum: açık

#### PKC-58 · EPK-26 · Birim ve sözleşme testleri: Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam
- **Sorun:** [ÖNERİ] Program EPK-26 «Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam» iş paketi 6/10. Bağlam: Coverage dev bağımlılığı değil; e2e/eslint/tsc/playwright yapılandırması yok.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P1 · M · Bağ: PKC-57 · Durum: açık

#### PKC-59 · EPK-26 · Hata enjeksiyonu ve dayanıklılık: Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam
- **Sorun:** [ÖNERİ] Program EPK-26 «Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam» iş paketi 7/10. Bağlam: Coverage dev bağımlılığı değil; e2e/eslint/tsc/playwright yapılandırması yok.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P1 · M · Bağ: PKC-58 · Durum: açık

#### PKC-60 · EPK-26 · Güvenlik ve gizlilik incelemesi: Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam
- **Sorun:** [ÖNERİ] Program EPK-26 «Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam» iş paketi 8/10. Bağlam: Coverage dev bağımlılığı değil; e2e/eslint/tsc/playwright yapılandırması yok.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P1 · S · Bağ: PKC-59 · Durum: açık

#### PKC-61 · EPK-26 · Uçtan uca senaryo ve eval kümesi: Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam
- **Sorun:** [ÖNERİ] Program EPK-26 «Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam» iş paketi 9/10. Bağlam: Coverage dev bağımlılığı değil; e2e/eslint/tsc/playwright yapılandırması yok.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P1 · M · Bağ: PKC-60 · Durum: açık

#### PKC-62 · EPK-26 · Ölçüm, belge ve runbook: Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam
- **Sorun:** [ÖNERİ] Program EPK-26 «Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam» iş paketi 10/10. Bağlam: Coverage dev bağımlılığı değil; e2e/eslint/tsc/playwright yapılandırması yok.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Kritik paketlerde mutant öldürme ≥ %70; kapsam ≥ %90; e2e CI'da.
- **Meta:** P1 · M · Bağ: PKC-61 · Durum: açık

#### PKC-63 · EPK-27 · Tasarım belgesi ve ADR: Çok dilli arayüz ve içerik (en az 5 dil)
- **Sorun:** [ÖNERİ] Program EPK-27 «Çok dilli arayüz ve içerik (en az 5 dil)» iş paketi 1/10. Bağlam: Yalnız TR/EN anahtarları var.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PKC-64 · EPK-27 · Veri modeli ve göç: Çok dilli arayüz ve içerik (en az 5 dil)
- **Sorun:** [ÖNERİ] Program EPK-27 «Çok dilli arayüz ve içerik (en az 5 dil)» iş paketi 2/10. Bağlam: Yalnız TR/EN anahtarları var.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P2 · M · Bağ: PKC-63 · Durum: açık

#### PKC-65 · EPK-27 · Çekirdek mantık: Çok dilli arayüz ve içerik (en az 5 dil)
- **Sorun:** [ÖNERİ] Program EPK-27 «Çok dilli arayüz ve içerik (en az 5 dil)» iş paketi 3/10. Bağlam: Yalnız TR/EN anahtarları var.
- **Değişiklik:** i18n altyapısı, çeviri iş akışı, RTL, yerel tarih/sayı biçimi, dil algılama.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P2 · L · Bağ: PKC-64 · Durum: açık

#### PKC-66 · EPK-27 · API ve yanıt şemaları: Çok dilli arayüz ve içerik (en az 5 dil)
- **Sorun:** [ÖNERİ] Program EPK-27 «Çok dilli arayüz ve içerik (en az 5 dil)» iş paketi 4/10. Bağlam: Yalnız TR/EN anahtarları var.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P2 · M · Bağ: PKC-65 · Durum: açık

#### PKC-67 · EPK-27 · Arayüz ve erişilebilirlik: Çok dilli arayüz ve içerik (en az 5 dil)
- **Sorun:** [ÖNERİ] Program EPK-27 «Çok dilli arayüz ve içerik (en az 5 dil)» iş paketi 5/10. Bağlam: Yalnız TR/EN anahtarları var.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P2 · M · Bağ: PKC-66 · Durum: açık

#### PKC-68 · EPK-27 · Birim ve sözleşme testleri: Çok dilli arayüz ve içerik (en az 5 dil)
- **Sorun:** [ÖNERİ] Program EPK-27 «Çok dilli arayüz ve içerik (en az 5 dil)» iş paketi 6/10. Bağlam: Yalnız TR/EN anahtarları var.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P2 · M · Bağ: PKC-67 · Durum: açık

#### PKC-69 · EPK-27 · Hata enjeksiyonu ve dayanıklılık: Çok dilli arayüz ve içerik (en az 5 dil)
- **Sorun:** [ÖNERİ] Program EPK-27 «Çok dilli arayüz ve içerik (en az 5 dil)» iş paketi 7/10. Bağlam: Yalnız TR/EN anahtarları var.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P2 · M · Bağ: PKC-68 · Durum: açık

#### PKC-70 · EPK-27 · Güvenlik ve gizlilik incelemesi: Çok dilli arayüz ve içerik (en az 5 dil)
- **Sorun:** [ÖNERİ] Program EPK-27 «Çok dilli arayüz ve içerik (en az 5 dil)» iş paketi 8/10. Bağlam: Yalnız TR/EN anahtarları var.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P2 · S · Bağ: PKC-69 · Durum: açık

#### PKC-71 · EPK-27 · Uçtan uca senaryo ve eval kümesi: Çok dilli arayüz ve içerik (en az 5 dil)
- **Sorun:** [ÖNERİ] Program EPK-27 «Çok dilli arayüz ve içerik (en az 5 dil)» iş paketi 9/10. Bağlam: Yalnız TR/EN anahtarları var.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P2 · M · Bağ: PKC-70 · Durum: açık

#### PKC-72 · EPK-27 · Ölçüm, belge ve runbook: Çok dilli arayüz ve içerik (en az 5 dil)
- **Sorun:** [ÖNERİ] Program EPK-27 «Çok dilli arayüz ve içerik (en az 5 dil)» iş paketi 10/10. Bağlam: Yalnız TR/EN anahtarları var.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** 5 dilde tam çeviri; eksik anahtar 0.
- **Meta:** P2 · M · Bağ: PKC-71 · Durum: açık

#### PKC-73 · EPK-28 · Tasarım belgesi ve ADR: Uyarı ve entegrasyon kanalları
- **Sorun:** [ÖNERİ] Program EPK-28 «Uyarı ve entegrasyon kanalları» iş paketi 1/10. Bağlam: E-posta/Telegram/Discord uyarısı yok.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PKC-74 · EPK-28 · Veri modeli ve göç: Uyarı ve entegrasyon kanalları
- **Sorun:** [ÖNERİ] Program EPK-28 «Uyarı ve entegrasyon kanalları» iş paketi 2/10. Bağlam: E-posta/Telegram/Discord uyarısı yok.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P2 · M · Bağ: PKC-73 · Durum: açık

#### PKC-75 · EPK-28 · Çekirdek mantık: Uyarı ve entegrasyon kanalları
- **Sorun:** [ÖNERİ] Program EPK-28 «Uyarı ve entegrasyon kanalları» iş paketi 3/10. Bağlam: E-posta/Telegram/Discord uyarısı yok.
- **Değişiklik:** Olay → kanal eşleme, şablonlar, sessiz saatler, hız sınırı.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P2 · L · Bağ: PKC-74 · Durum: açık

#### PKC-76 · EPK-28 · API ve yanıt şemaları: Uyarı ve entegrasyon kanalları
- **Sorun:** [ÖNERİ] Program EPK-28 «Uyarı ve entegrasyon kanalları» iş paketi 4/10. Bağlam: E-posta/Telegram/Discord uyarısı yok.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P2 · M · Bağ: PKC-75 · Durum: açık

#### PKC-77 · EPK-28 · Arayüz ve erişilebilirlik: Uyarı ve entegrasyon kanalları
- **Sorun:** [ÖNERİ] Program EPK-28 «Uyarı ve entegrasyon kanalları» iş paketi 5/10. Bağlam: E-posta/Telegram/Discord uyarısı yok.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P2 · M · Bağ: PKC-76 · Durum: açık

#### PKC-78 · EPK-28 · Birim ve sözleşme testleri: Uyarı ve entegrasyon kanalları
- **Sorun:** [ÖNERİ] Program EPK-28 «Uyarı ve entegrasyon kanalları» iş paketi 6/10. Bağlam: E-posta/Telegram/Discord uyarısı yok.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P2 · M · Bağ: PKC-77 · Durum: açık

#### PKC-79 · EPK-28 · Hata enjeksiyonu ve dayanıklılık: Uyarı ve entegrasyon kanalları
- **Sorun:** [ÖNERİ] Program EPK-28 «Uyarı ve entegrasyon kanalları» iş paketi 7/10. Bağlam: E-posta/Telegram/Discord uyarısı yok.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P2 · M · Bağ: PKC-78 · Durum: açık

#### PKC-80 · EPK-28 · Güvenlik ve gizlilik incelemesi: Uyarı ve entegrasyon kanalları
- **Sorun:** [ÖNERİ] Program EPK-28 «Uyarı ve entegrasyon kanalları» iş paketi 8/10. Bağlam: E-posta/Telegram/Discord uyarısı yok.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P2 · S · Bağ: PKC-79 · Durum: açık

#### PKC-81 · EPK-28 · Uçtan uca senaryo ve eval kümesi: Uyarı ve entegrasyon kanalları
- **Sorun:** [ÖNERİ] Program EPK-28 «Uyarı ve entegrasyon kanalları» iş paketi 9/10. Bağlam: E-posta/Telegram/Discord uyarısı yok.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P2 · M · Bağ: PKC-80 · Durum: açık

#### PKC-82 · EPK-28 · Ölçüm, belge ve runbook: Uyarı ve entegrasyon kanalları
- **Sorun:** [ÖNERİ] Program EPK-28 «Uyarı ve entegrasyon kanalları» iş paketi 10/10. Bağlam: E-posta/Telegram/Discord uyarısı yok.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Kritik olay ayarlı kanala 1 dk içinde ulaşır.
- **Meta:** P2 · M · Bağ: PKC-81 · Durum: açık

#### PKC-83 · EPK-29 · Tasarım belgesi ve ADR: Pazaryeri: şablon, araç ve ajan galerisi
- **Sorun:** [ÖNERİ] Program EPK-29 «Pazaryeri: şablon, araç ve ajan galerisi» iş paketi 1/10. Bağlam: Araç/şablon galerisi yok.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PKC-84 · EPK-29 · Veri modeli ve göç: Pazaryeri: şablon, araç ve ajan galerisi
- **Sorun:** [ÖNERİ] Program EPK-29 «Pazaryeri: şablon, araç ve ajan galerisi» iş paketi 2/10. Bağlam: Araç/şablon galerisi yok.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P2 · M · Bağ: PKC-83 · Durum: açık

#### PKC-85 · EPK-29 · Çekirdek mantık: Pazaryeri: şablon, araç ve ajan galerisi
- **Sorun:** [ÖNERİ] Program EPK-29 «Pazaryeri: şablon, araç ve ajan galerisi» iş paketi 3/10. Bağlam: Araç/şablon galerisi yok.
- **Değişiklik:** İmzalı paket biçimi, kurulum/kaldırma, izin gösterimi, derecelendirme.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P2 · L · Bağ: PKC-84 · Durum: açık

#### PKC-86 · EPK-29 · API ve yanıt şemaları: Pazaryeri: şablon, araç ve ajan galerisi
- **Sorun:** [ÖNERİ] Program EPK-29 «Pazaryeri: şablon, araç ve ajan galerisi» iş paketi 4/10. Bağlam: Araç/şablon galerisi yok.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P2 · M · Bağ: PKC-85 · Durum: açık

#### PKC-87 · EPK-29 · Arayüz ve erişilebilirlik: Pazaryeri: şablon, araç ve ajan galerisi
- **Sorun:** [ÖNERİ] Program EPK-29 «Pazaryeri: şablon, araç ve ajan galerisi» iş paketi 5/10. Bağlam: Araç/şablon galerisi yok.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P2 · M · Bağ: PKC-86 · Durum: açık

#### PKC-88 · EPK-29 · Birim ve sözleşme testleri: Pazaryeri: şablon, araç ve ajan galerisi
- **Sorun:** [ÖNERİ] Program EPK-29 «Pazaryeri: şablon, araç ve ajan galerisi» iş paketi 6/10. Bağlam: Araç/şablon galerisi yok.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P2 · M · Bağ: PKC-87 · Durum: açık

#### PKC-89 · EPK-29 · Hata enjeksiyonu ve dayanıklılık: Pazaryeri: şablon, araç ve ajan galerisi
- **Sorun:** [ÖNERİ] Program EPK-29 «Pazaryeri: şablon, araç ve ajan galerisi» iş paketi 7/10. Bağlam: Araç/şablon galerisi yok.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P2 · M · Bağ: PKC-88 · Durum: açık

#### PKC-90 · EPK-29 · Güvenlik ve gizlilik incelemesi: Pazaryeri: şablon, araç ve ajan galerisi
- **Sorun:** [ÖNERİ] Program EPK-29 «Pazaryeri: şablon, araç ve ajan galerisi» iş paketi 8/10. Bağlam: Araç/şablon galerisi yok.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P2 · S · Bağ: PKC-89 · Durum: açık

#### PKC-91 · EPK-29 · Uçtan uca senaryo ve eval kümesi: Pazaryeri: şablon, araç ve ajan galerisi
- **Sorun:** [ÖNERİ] Program EPK-29 «Pazaryeri: şablon, araç ve ajan galerisi» iş paketi 9/10. Bağlam: Araç/şablon galerisi yok.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P2 · M · Bağ: PKC-90 · Durum: açık

#### PKC-92 · EPK-29 · Ölçüm, belge ve runbook: Pazaryeri: şablon, araç ve ajan galerisi
- **Sorun:** [ÖNERİ] Program EPK-29 «Pazaryeri: şablon, araç ve ajan galerisi» iş paketi 10/10. Bağlam: Araç/şablon galerisi yok.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Galeriden kurulan araç izin onayıyla çalışır.
- **Meta:** P2 · M · Bağ: PKC-91 · Durum: açık

#### PKC-93 · EPK-30 · Tasarım belgesi ve ADR: Yüksek erişilebilirlik ve çoklu master
- **Sorun:** [ÖNERİ] Program EPK-30 «Yüksek erişilebilirlik ve çoklu master» iş paketi 1/10. Bağlam: Tek master, çoğaltma yok.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PKC-94 · EPK-30 · Veri modeli ve göç: Yüksek erişilebilirlik ve çoklu master
- **Sorun:** [ÖNERİ] Program EPK-30 «Yüksek erişilebilirlik ve çoklu master» iş paketi 2/10. Bağlam: Tek master, çoğaltma yok.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P2 · M · Bağ: PKC-93 · Durum: açık

#### PKC-95 · EPK-30 · Çekirdek mantık: Yüksek erişilebilirlik ve çoklu master
- **Sorun:** [ÖNERİ] Program EPK-30 «Yüksek erişilebilirlik ve çoklu master» iş paketi 3/10. Bağlam: Tek master, çoğaltma yok.
- **Değişiklik:** DB çoğaltma, lider seçimi, ajan yeniden bağlanma, rolling update.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P2 · L · Bağ: PKC-94 · Durum: açık

#### PKC-96 · EPK-30 · API ve yanıt şemaları: Yüksek erişilebilirlik ve çoklu master
- **Sorun:** [ÖNERİ] Program EPK-30 «Yüksek erişilebilirlik ve çoklu master» iş paketi 4/10. Bağlam: Tek master, çoğaltma yok.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P2 · M · Bağ: PKC-95 · Durum: açık

#### PKC-97 · EPK-30 · Arayüz ve erişilebilirlik: Yüksek erişilebilirlik ve çoklu master
- **Sorun:** [ÖNERİ] Program EPK-30 «Yüksek erişilebilirlik ve çoklu master» iş paketi 5/10. Bağlam: Tek master, çoğaltma yok.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P2 · M · Bağ: PKC-96 · Durum: açık

#### PKC-98 · EPK-30 · Birim ve sözleşme testleri: Yüksek erişilebilirlik ve çoklu master
- **Sorun:** [ÖNERİ] Program EPK-30 «Yüksek erişilebilirlik ve çoklu master» iş paketi 6/10. Bağlam: Tek master, çoğaltma yok.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P2 · M · Bağ: PKC-97 · Durum: açık

#### PKC-99 · EPK-30 · Hata enjeksiyonu ve dayanıklılık: Yüksek erişilebilirlik ve çoklu master
- **Sorun:** [ÖNERİ] Program EPK-30 «Yüksek erişilebilirlik ve çoklu master» iş paketi 7/10. Bağlam: Tek master, çoğaltma yok.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P2 · M · Bağ: PKC-98 · Durum: açık

## PKD · İş paketleri (4)

#### PKD-01 · EPK-30 · Güvenlik ve gizlilik incelemesi: Yüksek erişilebilirlik ve çoklu master
- **Sorun:** [ÖNERİ] Program EPK-30 «Yüksek erişilebilirlik ve çoklu master» iş paketi 8/10. Bağlam: Tek master, çoğaltma yok.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P2 · S · Bağ: PKC-99 · Durum: açık

#### PKD-02 · EPK-30 · Uçtan uca senaryo ve eval kümesi: Yüksek erişilebilirlik ve çoklu master
- **Sorun:** [ÖNERİ] Program EPK-30 «Yüksek erişilebilirlik ve çoklu master» iş paketi 9/10. Bağlam: Tek master, çoğaltma yok.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P2 · M · Bağ: PKD-01 · Durum: açık

#### PKD-03 · EPK-30 · Ölçüm, belge ve runbook: Yüksek erişilebilirlik ve çoklu master
- **Sorun:** [ÖNERİ] Program EPK-30 «Yüksek erişilebilirlik ve çoklu master» iş paketi 10/10. Bağlam: Tek master, çoğaltma yok.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Master düşünce ajanlar bekler ve geri dönünce görevler tutarlı.
- **Meta:** P2 · M · Bağ: PKD-02 · Durum: açık

#### PKD-04 · EPK-31 · Tasarım belgesi ve ADR: Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri a
- **Sorun:** [ÖNERİ] Program EPK-31 «Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri alma» iş paketi 1/10. Bağlam: Model terfisi eval kapısız; ince ayar planı kanıtsız.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PKD-05 · EPK-31 · Veri modeli ve göç: Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri a
- **Sorun:** [ÖNERİ] Program EPK-31 «Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri alma» iş paketi 2/10. Bağlam: Model terfisi eval kapısız; ince ayar planı kanıtsız.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P2 · M · Bağ: PKD-04 · Durum: açık

#### PKD-06 · EPK-31 · Çekirdek mantık: Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri a
- **Sorun:** [ÖNERİ] Program EPK-31 «Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri alma» iş paketi 3/10. Bağlam: Model terfisi eval kapısız; ince ayar planı kanıtsız.
- **Değişiklik:** Model kartı, eval kapısı, LoRA denemeleri, canary, otomatik geri alma.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P2 · L · Bağ: PKD-05 · Durum: açık

#### PKD-07 · EPK-31 · API ve yanıt şemaları: Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri a
- **Sorun:** [ÖNERİ] Program EPK-31 «Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri alma» iş paketi 4/10. Bağlam: Model terfisi eval kapısız; ince ayar planı kanıtsız.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P2 · M · Bağ: PKD-06 · Durum: açık

#### PKD-08 · EPK-31 · Arayüz ve erişilebilirlik: Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri a
- **Sorun:** [ÖNERİ] Program EPK-31 «Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri alma» iş paketi 5/10. Bağlam: Model terfisi eval kapısız; ince ayar planı kanıtsız.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P2 · M · Bağ: PKD-07 · Durum: açık

#### PKD-09 · EPK-31 · Birim ve sözleşme testleri: Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri a
- **Sorun:** [ÖNERİ] Program EPK-31 «Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri alma» iş paketi 6/10. Bağlam: Model terfisi eval kapısız; ince ayar planı kanıtsız.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P2 · M · Bağ: PKD-08 · Durum: açık

#### PKD-10 · EPK-31 · Hata enjeksiyonu ve dayanıklılık: Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri a
- **Sorun:** [ÖNERİ] Program EPK-31 «Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri alma» iş paketi 7/10. Bağlam: Model terfisi eval kapısız; ince ayar planı kanıtsız.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P2 · M · Bağ: PKD-09 · Durum: açık

#### PKD-11 · EPK-31 · Güvenlik ve gizlilik incelemesi: Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri a
- **Sorun:** [ÖNERİ] Program EPK-31 «Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri alma» iş paketi 8/10. Bağlam: Model terfisi eval kapısız; ince ayar planı kanıtsız.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P2 · S · Bağ: PKD-10 · Durum: açık

#### PKD-12 · EPK-31 · Uçtan uca senaryo ve eval kümesi: Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri a
- **Sorun:** [ÖNERİ] Program EPK-31 «Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri alma» iş paketi 9/10. Bağlam: Model terfisi eval kapısız; ince ayar planı kanıtsız.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P2 · M · Bağ: PKD-11 · Durum: açık

#### PKD-13 · EPK-31 · Ölçüm, belge ve runbook: Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri a
- **Sorun:** [ÖNERİ] Program EPK-31 «Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri alma» iş paketi 10/10. Bağlam: Model terfisi eval kapısız; ince ayar planı kanıtsız.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Eşik altı model terfi edemez; terfi/geri alma denetim izinde.
- **Meta:** P2 · M · Bağ: PKD-12 · Durum: açık

#### PKD-14 · EPK-32 · Tasarım belgesi ve ADR: Kullanım muhasebesi: token, süre, enerji, kota
- **Sorun:** [ÖNERİ] Program EPK-32 «Kullanım muhasebesi: token, süre, enerji, kota» iş paketi 1/10. Bağlam: Kota/maliyet muhasebesi yok.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PKD-15 · EPK-32 · Veri modeli ve göç: Kullanım muhasebesi: token, süre, enerji, kota
- **Sorun:** [ÖNERİ] Program EPK-32 «Kullanım muhasebesi: token, süre, enerji, kota» iş paketi 2/10. Bağlam: Kota/maliyet muhasebesi yok.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P2 · M · Bağ: PKD-14 · Durum: açık

#### PKD-16 · EPK-32 · Çekirdek mantık: Kullanım muhasebesi: token, süre, enerji, kota
- **Sorun:** [ÖNERİ] Program EPK-32 «Kullanım muhasebesi: token, süre, enerji, kota» iş paketi 3/10. Bağlam: Kota/maliyet muhasebesi yok.
- **Değişiklik:** Kullanıcı başına kota, enerji tahmini, raporlar, limit uyarıları.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P2 · L · Bağ: PKD-15 · Durum: açık

#### PKD-17 · EPK-32 · API ve yanıt şemaları: Kullanım muhasebesi: token, süre, enerji, kota
- **Sorun:** [ÖNERİ] Program EPK-32 «Kullanım muhasebesi: token, süre, enerji, kota» iş paketi 4/10. Bağlam: Kota/maliyet muhasebesi yok.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P2 · M · Bağ: PKD-16 · Durum: açık

#### PKD-18 · EPK-32 · Arayüz ve erişilebilirlik: Kullanım muhasebesi: token, süre, enerji, kota
- **Sorun:** [ÖNERİ] Program EPK-32 «Kullanım muhasebesi: token, süre, enerji, kota» iş paketi 5/10. Bağlam: Kota/maliyet muhasebesi yok.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P2 · M · Bağ: PKD-17 · Durum: açık

#### PKD-19 · EPK-32 · Birim ve sözleşme testleri: Kullanım muhasebesi: token, süre, enerji, kota
- **Sorun:** [ÖNERİ] Program EPK-32 «Kullanım muhasebesi: token, süre, enerji, kota» iş paketi 6/10. Bağlam: Kota/maliyet muhasebesi yok.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P2 · M · Bağ: PKD-18 · Durum: açık

#### PKD-20 · EPK-32 · Hata enjeksiyonu ve dayanıklılık: Kullanım muhasebesi: token, süre, enerji, kota
- **Sorun:** [ÖNERİ] Program EPK-32 «Kullanım muhasebesi: token, süre, enerji, kota» iş paketi 7/10. Bağlam: Kota/maliyet muhasebesi yok.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P2 · M · Bağ: PKD-19 · Durum: açık

#### PKD-21 · EPK-32 · Güvenlik ve gizlilik incelemesi: Kullanım muhasebesi: token, süre, enerji, kota
- **Sorun:** [ÖNERİ] Program EPK-32 «Kullanım muhasebesi: token, süre, enerji, kota» iş paketi 8/10. Bağlam: Kota/maliyet muhasebesi yok.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P2 · S · Bağ: PKD-20 · Durum: açık

#### PKD-22 · EPK-32 · Uçtan uca senaryo ve eval kümesi: Kullanım muhasebesi: token, süre, enerji, kota
- **Sorun:** [ÖNERİ] Program EPK-32 «Kullanım muhasebesi: token, süre, enerji, kota» iş paketi 9/10. Bağlam: Kota/maliyet muhasebesi yok.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P2 · M · Bağ: PKD-21 · Durum: açık

#### PKD-23 · EPK-32 · Ölçüm, belge ve runbook: Kullanım muhasebesi: token, süre, enerji, kota
- **Sorun:** [ÖNERİ] Program EPK-32 «Kullanım muhasebesi: token, süre, enerji, kota» iş paketi 10/10. Bağlam: Kota/maliyet muhasebesi yok.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Kullanıcı başına günlük rapor; limit aşımı net hata.
- **Meta:** P2 · M · Bağ: PKD-22 · Durum: açık

#### PKD-24 · EPK-33 · Tasarım belgesi ve ADR: Not defteri / hücre tabanlı çalışma modu
- **Sorun:** [ÖNERİ] Program EPK-33 «Not defteri / hücre tabanlı çalışma modu» iş paketi 1/10. Bağlam: Jupyter benzeri mod yok.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PKD-25 · EPK-33 · Veri modeli ve göç: Not defteri / hücre tabanlı çalışma modu
- **Sorun:** [ÖNERİ] Program EPK-33 «Not defteri / hücre tabanlı çalışma modu» iş paketi 2/10. Bağlam: Jupyter benzeri mod yok.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P2 · M · Bağ: PKD-24 · Durum: açık

#### PKD-26 · EPK-33 · Çekirdek mantık: Not defteri / hücre tabanlı çalışma modu
- **Sorun:** [ÖNERİ] Program EPK-33 «Not defteri / hücre tabanlı çalışma modu» iş paketi 3/10. Bağlam: Jupyter benzeri mod yok.
- **Değişiklik:** Hücre çalıştırma (sandbox), çıktı saklama, .ipynb dışa/içe aktarma.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P2 · L · Bağ: PKD-25 · Durum: açık

#### PKD-27 · EPK-33 · API ve yanıt şemaları: Not defteri / hücre tabanlı çalışma modu
- **Sorun:** [ÖNERİ] Program EPK-33 «Not defteri / hücre tabanlı çalışma modu» iş paketi 4/10. Bağlam: Jupyter benzeri mod yok.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P2 · M · Bağ: PKD-26 · Durum: açık

#### PKD-28 · EPK-33 · Arayüz ve erişilebilirlik: Not defteri / hücre tabanlı çalışma modu
- **Sorun:** [ÖNERİ] Program EPK-33 «Not defteri / hücre tabanlı çalışma modu» iş paketi 5/10. Bağlam: Jupyter benzeri mod yok.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P2 · M · Bağ: PKD-27 · Durum: açık

#### PKD-29 · EPK-33 · Birim ve sözleşme testleri: Not defteri / hücre tabanlı çalışma modu
- **Sorun:** [ÖNERİ] Program EPK-33 «Not defteri / hücre tabanlı çalışma modu» iş paketi 6/10. Bağlam: Jupyter benzeri mod yok.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P2 · M · Bağ: PKD-28 · Durum: açık

#### PKD-30 · EPK-33 · Hata enjeksiyonu ve dayanıklılık: Not defteri / hücre tabanlı çalışma modu
- **Sorun:** [ÖNERİ] Program EPK-33 «Not defteri / hücre tabanlı çalışma modu» iş paketi 7/10. Bağlam: Jupyter benzeri mod yok.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P2 · M · Bağ: PKD-29 · Durum: açık

#### PKD-31 · EPK-33 · Güvenlik ve gizlilik incelemesi: Not defteri / hücre tabanlı çalışma modu
- **Sorun:** [ÖNERİ] Program EPK-33 «Not defteri / hücre tabanlı çalışma modu» iş paketi 8/10. Bağlam: Jupyter benzeri mod yok.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P2 · S · Bağ: PKD-30 · Durum: açık

#### PKD-32 · EPK-33 · Uçtan uca senaryo ve eval kümesi: Not defteri / hücre tabanlı çalışma modu
- **Sorun:** [ÖNERİ] Program EPK-33 «Not defteri / hücre tabanlı çalışma modu» iş paketi 9/10. Bağlam: Jupyter benzeri mod yok.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P2 · M · Bağ: PKD-31 · Durum: açık

#### PKD-33 · EPK-33 · Ölçüm, belge ve runbook: Not defteri / hücre tabanlı çalışma modu
- **Sorun:** [ÖNERİ] Program EPK-33 «Not defteri / hücre tabanlı çalışma modu» iş paketi 10/10. Bağlam: Jupyter benzeri mod yok.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Örnek not defteri çalışır ve dışa aktarılır.
- **Meta:** P2 · M · Bağ: PKD-32 · Durum: açık

#### PKD-34 · EPK-34 · Tasarım belgesi ve ADR: Gelişmiş tarayıcı eklentisi ve kenar çubuğu
- **Sorun:** [ÖNERİ] Program EPK-34 «Gelişmiş tarayıcı eklentisi ve kenar çubuğu» iş paketi 1/10. Bağlam: Tarayıcı eklentisi yok.
- **Değişiklik:** Kapsamı, veri akışını, hata modlarını, ölçüm planını ve geri alma yolunu ADR olarak yaz.
- **Kabul:** ADR gözden geçirildi; ölçülebilir kabul ölçütleri ve riskler listelendi.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### PKD-35 · EPK-34 · Veri modeli ve göç: Gelişmiş tarayıcı eklentisi ve kenar çubuğu
- **Sorun:** [ÖNERİ] Program EPK-34 «Gelişmiş tarayıcı eklentisi ve kenar çubuğu» iş paketi 2/10. Bağlam: Tarayıcı eklentisi yok.
- **Değişiklik:** Gereken tablo/sütunları sürümlü göçle ekle; `owner_id`, saklama süresi ve silme akışını tanımla.
- **Kabul:** Sıfırdan kurulum ve yükseltme aynı şemayı üretir; sahiplik testi bu tablolarda koşar.
- **Meta:** P2 · M · Bağ: PKD-34 · Durum: açık

#### PKD-36 · EPK-34 · Çekirdek mantık: Gelişmiş tarayıcı eklentisi ve kenar çubuğu
- **Sorun:** [ÖNERİ] Program EPK-34 «Gelişmiş tarayıcı eklentisi ve kenar çubuğu» iş paketi 3/10. Bağlam: Tarayıcı eklentisi yok.
- **Değişiklik:** Sayfa özetleme, seçili metinle sohbet, yerel master'a güvenli bağlantı.
- **Kabul:** Çekirdek davranış birim testleriyle sabitlenir; hata yolları açık istisna ve günlükle ele alınır.
- **Meta:** P2 · L · Bağ: PKD-35 · Durum: açık

#### PKD-37 · EPK-34 · API ve yanıt şemaları: Gelişmiş tarayıcı eklentisi ve kenar çubuğu
- **Sorun:** [ÖNERİ] Program EPK-34 «Gelişmiş tarayıcı eklentisi ve kenar çubuğu» iş paketi 4/10. Bağlam: Tarayıcı eklentisi yok.
- **Değişiklik:** Uç noktaları, istek/yanıt Pydantic modellerini ve hata kodlarını ekle; rol matrisine işle.
- **Kabul:** Tüm yeni route'larda yanıt şeması ve rol testi var; OpenAPI güncel.
- **Meta:** P2 · M · Bağ: PKD-36 · Durum: açık

#### PKD-38 · EPK-34 · Arayüz ve erişilebilirlik: Gelişmiş tarayıcı eklentisi ve kenar çubuğu
- **Sorun:** [ÖNERİ] Program EPK-34 «Gelişmiş tarayıcı eklentisi ve kenar çubuğu» iş paketi 5/10. Bağlam: Tarayıcı eklentisi yok.
- **Değişiklik:** Arayüz bileşenlerini tasarım sistemine uygun yaz; klavye, etiket ve canlı bölge desteği ekle.
- **Kabul:** axe kritik/ciddi ihlal 0; yalnız klavye ile akış tamamlanır.
- **Meta:** P2 · M · Bağ: PKD-37 · Durum: açık

#### PKD-39 · EPK-34 · Birim ve sözleşme testleri: Gelişmiş tarayıcı eklentisi ve kenar çubuğu
- **Sorun:** [ÖNERİ] Program EPK-34 «Gelişmiş tarayıcı eklentisi ve kenar çubuğu» iş paketi 6/10. Bağlam: Tarayıcı eklentisi yok.
- **Değişiklik:** Kimliği taşıyan birim ve sözleşme testlerini yaz; sınır ve hata durumlarını kapsa.
- **Kabul:** Yeni kodun kapsamı ≥ %90; sözleşme testi alan değişince kırılır.
- **Meta:** P2 · M · Bağ: PKD-38 · Durum: açık

#### PKD-40 · EPK-34 · Hata enjeksiyonu ve dayanıklılık: Gelişmiş tarayıcı eklentisi ve kenar çubuğu
- **Sorun:** [ÖNERİ] Program EPK-34 «Gelişmiş tarayıcı eklentisi ve kenar çubuğu» iş paketi 7/10. Bağlam: Tarayıcı eklentisi yok.
- **Değişiklik:** Ağ, disk, model ve zaman aşımı hatalarını enjekte eden testler yaz; kullanıcıya nedenli mesaj göster.
- **Kabul:** Her hata türünde beklenen davranış ve mesaj doğrulanır.
- **Meta:** P2 · M · Bağ: PKD-39 · Durum: açık

#### PKD-41 · EPK-34 · Güvenlik ve gizlilik incelemesi: Gelişmiş tarayıcı eklentisi ve kenar çubuğu
- **Sorun:** [ÖNERİ] Program EPK-34 «Gelişmiş tarayıcı eklentisi ve kenar çubuğu» iş paketi 8/10. Bağlam: Tarayıcı eklentisi yok.
- **Değişiklik:** Yetki, enjeksiyon, SSRF, PII ve gizli bilgi açısından STRIDE satırı ekle ve sına.
- **Kabul:** Tehdit satırı ve ilgili güvenlik testleri geçer.
- **Meta:** P2 · S · Bağ: PKD-40 · Durum: açık

#### PKD-42 · EPK-34 · Uçtan uca senaryo ve eval kümesi: Gelişmiş tarayıcı eklentisi ve kenar çubuğu
- **Sorun:** [ÖNERİ] Program EPK-34 «Gelişmiş tarayıcı eklentisi ve kenar çubuğu» iş paketi 9/10. Bağlam: Tarayıcı eklentisi yok.
- **Değişiklik:** Playwright e2e senaryosu ve eval/ altında etiketli ölçüm kümesi ekle.
- **Kabul:** e2e CI'da koşar; eval raporu üretilir.
- **Meta:** P2 · M · Bağ: PKD-41 · Durum: açık

#### PKD-43 · EPK-34 · Ölçüm, belge ve runbook: Gelişmiş tarayıcı eklentisi ve kenar çubuğu
- **Sorun:** [ÖNERİ] Program EPK-34 «Gelişmiş tarayıcı eklentisi ve kenar çubuğu» iş paketi 10/10. Bağlam: Tarayıcı eklentisi yok.
- **Değişiklik:** Kabul ölçütünü ölç ve rapora yaz; kullanıcı belgesi ile runbook ekle.
- **Kabul:** Eklenti yalnız yerel/tailnet master'a bağlanır, içerik gönderimi onaylı.
- **Meta:** P2 · M · Bağ: PKD-42 · Durum: açık
