# Parça 7 — Yol haritası programları (öneri)

## EPK · Çok aylık programlar

#### EPK-01 · Yerel web arama ve tarama altyapısı
- **Sorun:** [ÖNERİ] Web araması yapılandırılmamış (SEARXNG_URL yok, sağlık sihirbazı 4/6): araştırma modelin hafızasından yazıyor.
- **Değişiklik:** SearXNG'yi kurulumla birlikte getir, çok sağlayıcılı yedek, kibar tarayıcı (robots, hız sınırı), sayfa arşivi, tekilleştirme, kaynak puanlama, çevrimdışı mod.
- **Kabul:** Temiz kurulumda tek komutla çalışan arama; 50 güncel soruda kaynaklı yanıt oranı ≥ %90; ağ yokken net uyarı.
- **Meta:** P0 · XL · Bağ: - · Durum: açık

#### EPK-02 · Etiketli Türkçe değerlendirme veri kümeleri programı
- **Sorun:** [ÖNERİ] ECE, κ, NLI F1, VQA ve olgusallık ölçümleri insan etiketli veri istiyor; depoda yok.
- **Değişiklik:** Etiketleme arayüzü, iki etiketleyici, uyum ölçümü, sürümlü veri kümeleri (olgusallık, atıf, NLI, niyet, görsel, ses).
- **Kabul:** Her küme ≥ 300 örnek, κ ≥ 0.7, sürüm ve veri kartı; eval raporları bu kümelere bağlı.
- **Meta:** P0 · XL · Bağ: - · Durum: açık

#### EPK-03 · Gerçek çok kullanıcılı kimlik ve yetki mimarisi
- **Sorun:** [ÖNERİ] Kullanıcı kimliği sorgu parametresinden geliyor; 8 /api/user/* rotası oturumsuz 200 veriyor; roller route'a bağlı değil.
- **Değişiklik:** Oturumdan türeyen kimlik, rol matrisinin route bağımlılığı olması, organizasyon/ekip kavramı, davet akışı, yönetici arayüzü.
- **Kabul:** Her route için A→B sızıntı testi otomatik üretilir; oturumsuz hiçbir kullanıcı verisi okunamaz.
- **Meta:** P0 · XL · Bağ: - · Durum: açık

#### EPK-04 · Sözleşme-öncelikli API: tam yanıt şemaları
- **Sorun:** [ÖNERİ] 188 işlemin hiçbirinin 200 yanıtı için şeması yok; arayüz-API uyumu ve sözleşme testi yazılamıyor.
- **Değişiklik:** Tüm route'lara Pydantic yanıt modeli, OpenAPI'den TypeScript tipi, arayüz çağrılarının tip denetimi, schemathesis fuzz.
- **Kabul:** 188/188 route yanıt şemalı; alan adı değişince derleme kırılır.
- **Meta:** P0 · XL · Bağ: - · Durum: açık

#### EPK-05 · Üretim kalitesinde kod üretim fabrikası
- **Sorun:** [ÖNERİ] Proje üretiminde 'çalışan proje' oranı ölçülmedi; şablon deposu yok; tarayıcı doğrulama yok.
- **Değişiklik:** 8 testli şablon, kur-derle-test-çalıştır-sağlık döngüsü, Playwright doğrulama, hedefli onarım, kalite panosu.
- **Kabul:** 20 istemde çalışan proje ≥ %80; kırık projelerin ≥ %85'i yakalanır.
- **Meta:** P0 · XL · Bağ: - · Durum: açık

#### EPK-06 · Tam IDE deneyimi
- **Sorun:** [ÖNERİ] Monaco yok, terminal komut-yanıt, LSP/DAP yok, gerçek git geçmişi yok.
- **Değişiklik:** Monaco (yerel), PTY terminal, LSP köprüsü, DAP, git grafiği, çok dosyalı düzenleme, birleşik diff.
- **Kabul:** Python/JS projesinde tanıma gitme, kesme noktası, etkileşimli terminal ve git geçmişi çalışır (e2e).
- **Meta:** P0 · XL · Bağ: - · Durum: açık

#### EPK-07 · Doğrulama katmanı: atıf, sayı, kod ve çıktı sözleşmesi
- **Sorun:** [ÖNERİ] Halüsinasyon ölçümleri küçük/şablonlu kümeyle; atıf doğruluğu ve kod doğrulama ölçülmedi.
- **Değişiklik:** Cümle düzeyinde iddia-atıf eşleme, NLI hakemi, sayısal/birim denetimi, kodu sandbox'ta çalıştırma, çıktı sözleşmesi denetleyicisi.
- **Kabul:** Etiketli kümede atıf doğruluğu ≥ %90, uydurma sayı yakalama ≥ %90, kod çalışma oranı +15 puan.
- **Meta:** P0 · XL · Bağ: - · Durum: açık

#### EPK-08 · Sunum ve belge fabrikası: render, görsel kalite, şablonlar
- **Sorun:** [ÖNERİ] PPTX'te gerçek grafik oranı, geçiş geçerliliği ve render denetimi ölçülmedi; DOCX şablon yüklemesi yok.
- **Değişiklik:** LibreOffice başsız render, taşma/çakışma/kontrast denetimi, şablon/tema kitaplığı, slayt başına yeniden üretme, kaynak slaytı.
- **Kabul:** Eval sunumlarında görsel hata < %3; 30 dosya PowerPoint ve LibreOffice'te hatasız açılır.
- **Meta:** P0 · XL · Bağ: - · Durum: açık

#### EPK-09 · Çok modlu anlama: görsel, ses, video, OCR
- **Sorun:** [ÖNERİ] OCR kurulu değil; VLM/VQA, video ve ses ölçümleri yok.
- **Değişiklik:** Tesseract/PaddleOCR kurulumu, VLM hattı, ses→metin (WER ölçümü), video anahtar kare özeti, 'okunamadı' dürüstlüğü.
- **Kabul:** 60 görselde VQA ≥ %75; Türkçe WER ölçülür; OCR yokken kullanıcıya net uyarı.
- **Meta:** P0 · XL · Bağ: - · Durum: açık

#### EPK-10 · Dağıtık yürütme: ölçülmüş hızlanma ve kaos dayanıklılığı
- **Sorun:** [ÖNERİ] 6 ajanla 3x hızlanma ve ajan düşme senaryoları otomatik ölçülmedi.
- **Değişiklik:** Standart iş yükleri, 1/2/4/6 ajan ölçümü, Amdahl analizi, kaos betikleri, idempotent sonuç kabulü.
- **Kabul:** Hızlanma raporu otomatik; ajan düşünce görev yeniden atanır ve çift sonuç oluşmaz.
- **Meta:** P0 · XL · Bağ: - · Durum: açık

#### EPK-11 · Kullanıcı tanımlı asistan/ajan oluşturucu
- **Sorun:** [ÖNERİ] GPT/Gem benzeri özel asistan tanımlama yok.
- **Değişiklik:** Talimat, bilgi koleksiyonu, araç izni, model seçimi ve paylaşım içeren asistan tanımı; sürümleme.
- **Kabul:** Kullanıcı kod yazmadan özel asistan oluşturur, paylaşır ve sürümünü geri alır.
- **Meta:** P1 · XL · Bağ: - · Durum: açık

#### EPK-12 · Zamanlanmış ve olay tetiklemeli görevler
- **Sorun:** [ÖNERİ] Cron/webhook yok; 'her sabah rapor' yapılamıyor.
- **Değişiklik:** Zamanlayıcı, webhook alıcı/gönderici, görev geçmişi, başarısızlık uyarısı.
- **Kabul:** Zamanlanmış görev çalışır, sonucu bildirir, hata yeniden denenir.
- **Meta:** P1 · XL · Bağ: - · Durum: açık

#### EPK-13 · Harici bağlayıcılar: Drive, OneDrive, GitHub, takvim, e-posta
- **Sorun:** [ÖNERİ] Bağlayıcılar yok; MCP yalnız istemci.
- **Değişiklik:** OAuth'suz yerel öncelikli bağlayıcılar, MCP sunucusu olarak dışa açma, izin kapsamları, onay kapısı.
- **Kabul:** Her bağlayıcı için izinli/izinsiz senaryo testi; onaysız yan etki yok.
- **Meta:** P1 · XL · Bağ: - · Durum: açık

#### EPK-14 · Gelişmiş RAG: ANN dizin, reranker, parent-child, çok dilli
- **Sorun:** [ÖNERİ] Vektör arama ölçeği ve reranker kazancı ölçülmedi.
- **Değişiklik:** sqlite-vec/HNSW, cross-encoder, parent-child getirme, sorgu yeniden yazma, çok dilli gömme, retrieval eval.
- **Kabul:** 100.000 parçada p95 < 150 ms; nDCG@5 +5 puan; çapraz dil recall ≥ %70.
- **Meta:** P1 · XL · Bağ: - · Durum: açık

#### EPK-15 · Hafıza sistemi: konsolidasyon, çelişki, yaş bozunumu, görünürlük
- **Sorun:** [ÖNERİ] Hafıza düzenleme/zaman çizelgesi/dışa aktarma eksik.
- **Değişiklik:** Hafıza düzenleyici, çelişki çözümü, bozunum, hangi yanıtta kullanıldığı, dışa/içe aktarma.
- **Kabul:** Çelişen tercih kullanıcıya sorulur; silinen hafıza hiçbir bağlamda görünmez.
- **Meta:** P1 · XL · Bağ: - · Durum: açık

#### EPK-16 · Erişilebilirlik ve tasarım sistemi (WCAG 2.2 AA)
- **Sorun:** [ÖNERİ] Studios sayfasında 341 etiketsiz kontrol; prefers-reduced-motion yok; sayfa başlıkları aynı.
- **Değişiklik:** Bileşen kitaplığı, jetonlar, üç tema, axe CI, klavye e2e, ekran okuyucu testleri.
- **Kabul:** axe kritik/ciddi 0; yalnız klavye ile sohbet, yükleme ve ayarlar kullanılabilir.
- **Meta:** P1 · XL · Bağ: - · Durum: açık

#### EPK-17 · Performans bütçesi ve gözlemlenebilirlik
- **Sorun:** [ÖNERİ] Lighthouse/paket boyutu/yük testi yok; yavaş uç noktalar var.
- **Değişiklik:** Sanal liste, worker, kod bölme, yük/soak testleri, OpenTelemetry, SLO panoları.
- **Kabul:** 1.000 mesajda ≥ 50 FPS; 20 eşzamanlı kullanıcıda hata < %1.
- **Meta:** P1 · XL · Bağ: - · Durum: açık

#### EPK-18 · Veri analizi stüdyosu: pandas/duckdb, grafik, tahmin, ML
- **Sorun:** [ÖNERİ] Veri kütüphaneleri sohbetten kullanılamıyor.
- **Değişiklik:** DuckDB/Polars motoru, otomatik grafik, istatistik testleri, ARIMA/Prophet, AutoML, sızıntı denetimi, pano üretimi.
- **Kabul:** 200 vakalık set ≥ %95 doğruluk; AutoML sızıntı uyarısı.
- **Meta:** P1 · XL · Bağ: - · Durum: açık

#### EPK-19 · Eğitim modu: ders planı, alıştırma, ilerleme, ödev değerlendirme
- **Sorun:** [ÖNERİ] Quiz/flashcard/ilerleme takibi yok.
- **Değişiklik:** Müfredat uyumlu ders planı, alıştırma ve cevap anahtarı, aralıklı tekrar, ödev otomatik değerlendirme.
- **Kabul:** Üretilen 20 sınavda cevap anahtarı doğruluğu ≥ %95.
- **Meta:** P1 · XL · Bağ: - · Durum: açık

#### EPK-20 · Hukuk, sağlık, finans bilgi tabanları (kaynaklı)
- **Sorun:** [ÖNERİ] Mevzuat, ilaç ve kur veri tabanları yok.
- **Değişiklik:** Mevzuat koleksiyonu madde atıflı, ilaç etkileşimi, TCMB kuru, sorumluluk reddi ve acil yönlendirme.
- **Kabul:** Bu alan yanıtlarının %100'ü atıflı ve uyarılı.
- **Meta:** P1 · XL · Bağ: - · Durum: açık

#### EPK-21 · Mühendislik araç zinciri: CNC, CAD, devre, malzeme, metraj
- **Sorun:** [ÖNERİ] Alan formülleri literatür vakasıyla sınanmadı; malzeme/Spice/metraj yok.
- **Değişiklik:** Doğrulanmış formül kitaplığı, malzeme veri tabanı, ngspice, DXF ölçü çıkarımı, G-kod simülasyonu.
- **Kabul:** 15 literatür vakasında sapma ≤ %5; 30 hatalı G-kodun ≥ %85'i yakalanır.
- **Meta:** P1 · XL · Bağ: - · Durum: açık

#### EPK-22 · Medya üretimi: görsel, ses, video, 3B
- **Sorun:** [ÖNERİ] Yerel görsel/TTS/video üretimi yok veya doğrulanmadı.
- **Değişiklik:** ComfyUI/SD köprüsü, yerel TTS, SRT, moviepy montaj, three.js 3B şablon.
- **Kabul:** Her üretici için kapalıysa net mesaj, açıksa örnek çıktı testi.
- **Meta:** P1 · XL · Bağ: - · Durum: açık

#### EPK-23 · Taşınabilirlik: PWA, masaüstü paket, CLI, SDK, OpenAI uyumlu API
- **Sorun:** [ÖNERİ] OpenAI uyumlu uç nokta, CLI, SDK, masaüstü paket yok.
- **Değişiklik:** /v1/chat/completions uyumluluk katmanı, Python/JS SDK, CLI, Tauri/Electron paketi, tam PWA çevrimdışı.
- **Kabul:** Bir OpenAI SDK örneği platforma karşı çalışır; CLI ile sohbet edilir.
- **Meta:** P1 · XL · Bağ: - · Durum: açık

#### EPK-24 · Kurulum, güncelleme ve yedekleme ürünleşmesi
- **Sorun:** [ÖNERİ] Windows kurulum paketi, otomatik güncelleme ve zamanlı yedek arayüzü yok.
- **Değişiklik:** Tek tıkla kurulum, sürüm kontrolü, güncelleme/geri alma, yedek zamanlama arayüzü, geri yükleme turu CI'da.
- **Kabul:** Temiz Windows 11'de kurulum ≤ 15 dk; yedek→geri yükleme kayıt sayıları aynı.
- **Meta:** P1 · XL · Bağ: - · Durum: açık

#### EPK-25 · Gizlilik mühendisliği: PII, silme hakkı, şifreleme
- **Sorun:** [ÖNERİ] TOTP, hesap kilidi, oturum listesi, antivirüs ve sır taraması yok.
- **Değişiklik:** TOTP, kilitleme, oturum yönetimi, alan şifreleme, antivirüs, silme akışı kanıtı, gizlilik sayfası.
- **Kabul:** Silme sonrası benzersiz dizge hiçbir yerde bulunmaz; 2FA'sız yönetici işlemi reddedilir (açıksa).
- **Meta:** P1 · XL · Bağ: - · Durum: açık

#### EPK-26 · Test mühendisliği: e2e, özellik tabanlı, mutasyon, kapsam
- **Sorun:** [ÖNERİ] Coverage dev bağımlılığı değil; e2e/eslint/tsc/playwright yapılandırması yok.
- **Değişiklik:** Playwright, eslint, tsc, hypothesis, mutmut, diff-cover, görsel gerileme, flaky tespiti.
- **Kabul:** Kritik paketlerde mutant öldürme ≥ %70; kapsam ≥ %90; e2e CI'da.
- **Meta:** P1 · XL · Bağ: - · Durum: açık

#### EPK-27 · Çok dilli arayüz ve içerik (en az 5 dil)
- **Sorun:** [ÖNERİ] Yalnız TR/EN anahtarları var.
- **Değişiklik:** i18n altyapısı, çeviri iş akışı, RTL, yerel tarih/sayı biçimi, dil algılama.
- **Kabul:** 5 dilde tam çeviri; eksik anahtar 0.
- **Meta:** P2 · XL · Bağ: - · Durum: açık

#### EPK-28 · Uyarı ve entegrasyon kanalları
- **Sorun:** [ÖNERİ] E-posta/Telegram/Discord uyarısı yok.
- **Değişiklik:** Olay → kanal eşleme, şablonlar, sessiz saatler, hız sınırı.
- **Kabul:** Kritik olay ayarlı kanala 1 dk içinde ulaşır.
- **Meta:** P2 · XL · Bağ: - · Durum: açık

#### EPK-29 · Pazaryeri: şablon, araç ve ajan galerisi
- **Sorun:** [ÖNERİ] Araç/şablon galerisi yok.
- **Değişiklik:** İmzalı paket biçimi, kurulum/kaldırma, izin gösterimi, derecelendirme.
- **Kabul:** Galeriden kurulan araç izin onayıyla çalışır.
- **Meta:** P2 · XL · Bağ: - · Durum: açık

#### EPK-30 · Yüksek erişilebilirlik ve çoklu master
- **Sorun:** [ÖNERİ] Tek master, çoğaltma yok.
- **Değişiklik:** DB çoğaltma, lider seçimi, ajan yeniden bağlanma, rolling update.
- **Kabul:** Master düşünce ajanlar bekler ve geri dönünce görevler tutarlı.
- **Meta:** P2 · XL · Bağ: - · Durum: açık

#### EPK-31 · Model yaşam döngüsü: değerlendirme, ince ayar, terfi, geri alma
- **Sorun:** [ÖNERİ] Model terfisi eval kapısız; ince ayar planı kanıtsız.
- **Değişiklik:** Model kartı, eval kapısı, LoRA denemeleri, canary, otomatik geri alma.
- **Kabul:** Eşik altı model terfi edemez; terfi/geri alma denetim izinde.
- **Meta:** P2 · XL · Bağ: - · Durum: açık

#### EPK-32 · Kullanım muhasebesi: token, süre, enerji, kota
- **Sorun:** [ÖNERİ] Kota/maliyet muhasebesi yok.
- **Değişiklik:** Kullanıcı başına kota, enerji tahmini, raporlar, limit uyarıları.
- **Kabul:** Kullanıcı başına günlük rapor; limit aşımı net hata.
- **Meta:** P2 · XL · Bağ: - · Durum: açık

#### EPK-33 · Not defteri / hücre tabanlı çalışma modu
- **Sorun:** [ÖNERİ] Jupyter benzeri mod yok.
- **Değişiklik:** Hücre çalıştırma (sandbox), çıktı saklama, .ipynb dışa/içe aktarma.
- **Kabul:** Örnek not defteri çalışır ve dışa aktarılır.
- **Meta:** P2 · XL · Bağ: - · Durum: açık

#### EPK-34 · Gelişmiş tarayıcı eklentisi ve kenar çubuğu
- **Sorun:** [ÖNERİ] Tarayıcı eklentisi yok.
- **Değişiklik:** Sayfa özetleme, seçili metinle sohbet, yerel master'a güvenli bağlantı.
- **Kabul:** Eklenti yalnız yerel/tailnet master'a bağlanır, içerik gönderimi onaylı.
- **Meta:** P2 · XL · Bağ: - · Durum: açık
