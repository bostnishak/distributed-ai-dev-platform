# Parça 5 — Yazılım Fabrikası ve IDE (IDE), Oyun Stüdyosu (GAME), Alan Motorları (DOM)

**Ortak kural:** "Proje üretti" başarı sayılmaz. Başarı: **kuruldu, testler geçti, uygulama başladı, temel kullanıcı akışı çalıştı** ve bu kanıt kullanıcıya gösterildi. Üretim, doğrulama ve onarım döngüsü her proje türü için aynı hattan geçer.

---

## A. IDE — Otonom Yazılım Fabrikası ve Çalışma Alanı

> Bugünkü durum: Canlı yol `workspace_builder.py` (759 satır) + `studio_api.py`; ayrı bir "fabrika" yolu (`software_factory`, `self_healing_runner`, `visual_verifier`, `build_pipelines`, `project_archetypes`) **erişilemez** durumda [DOĞRULANDI: F19]. İki paralel uygulama var ve hiçbiri diğerinin doğrulama yeteneklerini kullanmıyor.

#### IDE-01 · İki üretim hattının tek pakette birleştirilmesi
- **Sorun:** [DOĞRULANDI: F19] Canlı `workspace_builder` ile erişilemez fabrika modülleri aynı işi iki yolla yapıyor; öz-tamir, tarayıcı doğrulama ve paketleme yeteneklerinin hiçbiri canlı yola bağlı değil.
- **Değişiklik:** `master/factory/` paketi: `plan` (PRD+mimari) → `scaffold` (şablon) → `generate` (dosya başına) → `verify` (kur/derle/test/duman/tarayıcı) → `repair` → `package`; `workspace_builder` canlı davranışı bu hatta taşınır; eski modüller silinir/bağlanır (DEF-02).
- **Kabul:** `plan_tool.py wiring` fabrika modüllerini erişilebilir gösterir; mevcut `test_studio.py` testleri geçer; yeni tek hatla 5 örnek proje uçtan uca üretilir.
- **Meta:** P0 · XL · Bağ: DEF-02, GW-01 · Durum: açık

#### IDE-02 · Gereksinimden mimariye: onaylı plan
- **Sorun:** [ÖNERİ] Kullanıcının isteği doğrudan koda dönüştürülüyor; yanlış anlaşılan gereksinim ancak sonunda fark ediliyor.
- **Değişiklik:** Kısa PRD (kapsam, kullanıcı akışları, kabul kriterleri), teknoloji seçimi gerekçesi, dosya ağacı, API sözleşmesi (OpenAPI) ve veri modeli üretilir; kullanıcıya özet olarak sunulur, "onayla/değiştir" sonrası üretim başlar (hızlı mod: otomatik onay).
- **Kabul:** PRD'deki her kabul kriteri en az bir test/senaryoya eşlenir (otomatik denetim); kullanıcı değişikliği planı günceller ve yalnız etkilenen dosyalar yeniden üretilir.
- **Meta:** P0 · L · Bağ: IDE-01, ORC-15 · Durum: açık

#### IDE-03 · Bağımlılık grafı bilgili dosya üretimi
- **Sorun:** [DOĞRULANDI] `code_graph.py` (AST sembol/bağımlılık) var ve çalışma alanı akışında kısmen kullanılıyor; sözleşme tutarsızlıkları (olmayan import, tanımsız fonksiyon) hâlâ çıkabiliyor.
- **Değişiklik:** Dosyalar topolojik sırada üretilir; her dosya üretilirken bağımlı olduğu dosyaların **gerçek imzaları** bağlama verilir; üretim sonrası import/çağrı çözümü doğrulanır.
- **Kabul:** 20 projede "ImportError/NameError/tanımsız fonksiyon" ilk doğrulama turunda ≤ %10; kalanlar onarımda giderilir.
- **Meta:** P0 · L · Bağ: IDE-01 · Durum: açık

#### IDE-04 · Test odaklı üretim
- **Sorun:** [ÖNERİ] Testler çoğu zaman sonradan ve yüzeysel; PRD kabul kriterleriyle bağlantısız.
- **Değişiklik:** Kabul kriterlerinden test iskeleti (API için `pytest` + `httpx`, ön yüz için senaryo), modül başına birim testi; testler üretim ve onarım döngüsünün başarı ölçütüdür.
- **Kabul:** Üretilen projelerin ≥ %80'inde kabul kriteri başına bir test vardır ve test geçerli kod üzerinde geçer; testsiz proje "doğrulanmamış" etiketiyle sunulur.
- **Meta:** P0 · L · Bağ: IDE-02 · Durum: açık

#### IDE-05 · Çalıştırma doğrulama ve onarım döngüsü
- **Sorun:** [DOĞRULANDI: F19] `self_healing_runner` (378 satır) bağlı değil; canlı yol esas olarak sözdizimi denetimi yapıyor.
- **Değişiklik:** Kur → derle/lint → test → duman testi → sunucuyu başlat → `/health` yoklaması; hata çıktısı ve ilgili dosya modele verilir, hedefli yama (en fazla 5 tur), her turun özeti kullanıcıya akar; kalıcı hatada açık rapor.
- **Kabul:** 20 proje isteminde "çalışan proje" oranı ≥ %80 (IDE-24 metriği); başarısız projede hangi adımda neden takıldığı raporda.
- **Meta:** P0 · XL · Bağ: SEC-13, IDE-01 · Durum: açık

#### IDE-06 · Tarayıcı tabanlı doğrulama (Playwright)
- **Sorun:** [DOĞRULANDI: F19] `visual_verifier` bağlı değil; web arayüzleri hiç tarayıcıda açılmadan teslim ediliyor.
- **Değişiklik:** Sandbox içinde Playwright: sayfa yükleme, konsol hataları, kırık kaynak, PRD senaryolarından üretilen tıklama akışları, ekran görüntüsü + VLM "düzgün mü" denetimi; bulgular hedefli onarıma gider.
- **Kabul:** Bilerek bozulan 20 projede (kırık JS yolu, boş sayfa, çalışmayan düğme) hata yakalama ≥ %85; doğru projelerde yanlış alarm < %5.
- **Meta:** P1 · L · Bağ: IDE-05, SEC-17 · Durum: açık

#### IDE-07 · Bağımlılık yönetimi ve paket güvenliği
- **Sorun:** [ÖNERİ] Üretilen `requirements`/`package.json` uydurma veya güvensiz paket içerebilir; kurulum doğrulanmıyor.
- **Değişiklik:** Sandbox'ta sanal ortam/npm kurulumu, sürüm kilidi, paket varlığı denetimi (HAL-13), lisans ve bilinen açık taraması; kurulum başarısızsa onarım.
- **Kabul:** Uydurma paket içeren örneklerde kurulum öncesi yakalama ≥ %90; üretilen projelerde kilit dosyası bulunur.
- **Meta:** P1 · M · Bağ: HAL-13, SEC-13 · Durum: açık

#### IDE-08 · Gerçek etkileşimli terminal (PTY)
- **Sorun:** [DOĞRULANDI: F2] `/exec` tek seferlik `subprocess.run` (12 sn zaman aşımı); etkileşimli program, uzun çalışan süreç ve renkli çıktı yok.
- **Değişiklik:** Sandbox içinde PTY (Windows ConPTY/`pywinpty` veya konteyner içi `pty`) + xterm.js (yerel paket) + WebSocket; çalışma alanıyla sınırlı, kaynak limitli; oturum yeniden bağlanma.
- **Kabul:** `python`, `npm run dev`, `pytest -x` etkileşimli çalışır; sandbox dışına çıkış denemeleri engellenir; kapatınca süreç ağacı temizlenir.
- **Meta:** P1 · L · Bağ: SEC-13, SEC-14, UX-01 · Durum: açık

#### IDE-09 · Dil sunucusu (LSP) entegrasyonu
- **Sorun:** [ÖNERİ] Editörde gerçek tamamlama, tanıma git, hata altı çizgisi yok.
- **Değişiklik:** Python için pyright/jedi, TS/JS için tsserver; WebSocket köprüsü ve sandbox içinde çalıştırma; tanılama paneli.
- **Kabul:** Üretilen projede tanıma gitme ve tür hatası altı çizgisi çalışır (e2e); LSP kapalıyken editör yine kullanılabilir.
- **Meta:** P2 · L · Bağ: IDE-10 · Durum: açık

#### IDE-10 · Editör: Monaco (çevrimdışı paket)
- **Sorun:** [DOĞRULANDI: F15] Elle yazılmış vurgulayıcı ve sekme sistemi `assistant.js` (1952 satır) içinde; bakım yükü yüksek, çok imleç/bul-değiştir/minimap yok.
- **Değişiklik:** Monaco Editor yerel paket olarak (CDN yok), tema ve dil eşlemesi, diff editörü, minimap; mevcut IDE bileşeni ayrı modüle taşınır (UX-02).
- **Kabul:** Mevcut IDE özellikleri (sekme, diff, önizleme, durum çubuğu) regresyonsuz çalışır (e2e); `assistant.js` küçülür; paket boyutu bütçesi (UX-19) içinde lazy-load.
- **Meta:** P1 · L · Bağ: UX-01, UX-02 · Durum: açık

#### IDE-11 · Hunk bazlı diff ve satır içi öneri incelemesi
- **Sorun:** [DOĞRULANDI] Birleşik diff var; yama bazında kabul/ret ve yorum yok.
- **Değişiklik:** Yan yana diff, hunk başına kabul/ret, satır içi AI önerileri, yorum, "tümünü uygula/geri al"; reddedilen hunk modele geri bildirim olur (ML-07 adayı).
- **Kabul:** Hunk reddi yalnız o parçayı geri alır, dosya bütünlüğü korunur (test); sürüm geçmişi tutarlı.
- **Meta:** P1 · M · Bağ: IDE-10 · Durum: açık

#### IDE-12 · Gerçek git ile sürüm yönetimi
- **Sorun:** [DOĞRULANDI] `studio_api` git komutları (`init/status/commit/log/branch`) sınırlı; snapshot sistemi (v1/v2) ayrı bir mekanizma.
- **Değişiklik:** Çalışma alanı gerçek git deposudur; her yapay zekâ değişikliği anlamlı mesajlı commit, dallanma/birleştirme, çakışma çözümü arayüzü, geçmiş grafiği; snapshot'lar git etiketlerine eşlenir.
- **Kabul:** Rastgele bir sürüme dönüp ileri geri gitme veri kaybı olmadan çalışır; çakışmalı birleştirme arayüzden çözülür.
- **Meta:** P1 · L · Bağ: SEC-14 · Durum: açık

#### IDE-13 · Çok dosyalı düzenleme ajanı
- **Sorun:** [ÖNERİ] "Şu özelliği ekle/şu hatayı düzelt" istekleri proje büyüdükçe tüm dosyaları yeniden üretmeye yöneliyor.
- **Değişiklik:** İlgili dosyaları bulma (RAG-28), değişiklik planı, patch seti (birden çok dosya), test çalıştırma, tek geri alınabilir değişiklik grubu; kullanıcıya diff özeti.
- **Kabul:** 30 değişiklik isteğinde yalnız ilgili dosyalar değişir (kapsam sızıntısı < %10); testler değişiklik sonrası geçer.
- **Meta:** P1 · L · Bağ: RAG-28, ORC-16 · Durum: açık

#### IDE-14 · Hata ayıklama (DAP) ve yığın izi yardımı
- **Sorun:** [ÖNERİ] Hata ayıklama yalnız konsol çıktısı.
- **Değişiklik:** `debugpy` ile kesme noktası, adım adım, değişken inceleme (sandbox içinde); yığın izinden otomatik açıklama ve düzeltme önerisi.
- **Kabul:** Basit bir hata senaryosunda kesme noktasında durup değişken görülür (e2e); yığın izi açıklaması doğru dosya:satıra atıf yapar.
- **Meta:** P3 · L · Bağ: IDE-08 · Durum: açık

#### IDE-15 · Önizleme ve çalışan sunucu yönetimi
- **Sorun:** [DOĞRULANDI: F2] Önizleme aynı origin'den; çalışan sunucuların port/yaşam döngüsü (`_RUNNING_SERVERS`) bellekte, yeniden başlatmada kaybolur.
- **Değişiklik:** Ayrı origin/port'tan önizleme (SEC-17), sunucu kayıt tablosu, otomatik durdurma (boşta), port çakışması yönetimi, canlı yenileme.
- **Kabul:** Master yeniden başlayınca yetim süreç kalmaz; aynı anda 5 önizleme port çakışmasız çalışır.
- **Meta:** P1 · M · Bağ: SEC-17 · Durum: açık

#### IDE-16 · Paketleme (EXE, PWA, Docker)
- **Sorun:** [DOĞRULANDI: F19] `build_pipelines` bağlı değil; canlı yolda yalnız PyInstaller akışı var, Docker/PWA/kurulum paketi yok.
- **Değişiklik:** Hedefler: tek dosya `.exe` (PyInstaller), PWA (`manifest` + `service worker`), Dockerfile + compose, ZIP; sürüm numarası, simge, imzasız uyarı notu, antivirüs yanlış-pozitif bilgilendirmesi; paket çıktısı duman testinden geçer.
- **Kabul:** Her hedef için üretilen paket temiz ortamda açılır/çalışır (örnek proje); paket kaydı artefakt sürümüne bağlı.
- **Meta:** P2 · L · Bağ: IDE-01, SEC-13 · Durum: açık

#### IDE-17 · Test edilmiş proje şablon deposu
- **Sorun:** [DOĞRULANDI: F19] `project_archetypes.py` 6 arketip tanımlıyor ama erişilemez; şablonlar LLM'in sıfırdan yazdığı metinler, çalıştığı kanıtlı iskelet değil.
- **Değişiklik:** 8 çalışan, testli başlangıç şablonu (FastAPI+SQLite, SPA, CLI, Tkinter/PySide masaüstü, veri uygulaması, Chrome eklentisi, REST+ön yüz, oyun iskeleti); LLM şablonu **özelleştirir**, sıfırdan yazmaz; şablonların kendi CI testleri.
- **Kabul:** Her şablon boş özelleştirmeyle kurulur ve testleri geçer (CI işi); şablon tabanlı üretimde çalışan proje oranı sıfırdan üretime göre ≥ 15 puan yüksek.
- **Meta:** P0 · L · Bağ: IDE-01 · Durum: açık

#### IDE-18 · Yerleşik güvenlik taraması
- **Sorun:** [DOĞRULANDI: F19] `security_scanner` bağlı değil; ayrıca `/security-scan` yalnız sınırlı kural içeriyor.
- **Değişiklik:** SAST (bandit/semgrep kural seti), sır tarama, bağımlılık açığı taraması; bulgular IDE panelinde dosya:satır ile, "otomatik düzelt" önerisi (onaylı).
- **Kabul:** Bilerek açık içeren 30 örnekte (SQL enjeksiyonu, sabit sır, `eval`, yol geçişi) yakalama ≥ %85; üretilen projelerde yüksek önemli bulgu teslimden önce giderilir.
- **Meta:** P1 · M · Bağ: IDE-05 · Durum: açık

#### IDE-19 · Kod kalitesi ve CI dosyası üretimi
- **Sorun:** [ÖNERİ] Üretilen projelerde biçimlendirme/lint/tip denetimi ve CI yok.
- **Değişiklik:** ruff/eslint/prettier yapılandırması ve otomatik çalıştırma, tip denetimi (mypy/pyright/tsc), üretilen projeye GitHub Actions iş akışı; karmaşıklık uyarıları.
- **Kabul:** Üretilen projede lint temiz; CI iş akışı yerelde `act` ya da komut dizisiyle çalışır.
- **Meta:** P2 · M · Bağ: IDE-05 · Durum: açık

#### IDE-20 · Doğrulanmış belgelendirme
- **Sorun:** [ÖNERİ] README'deki kurulum/çalıştırma komutları test edilmeden yazılıyor.
- **Değişiklik:** README, API belgesi, mimari diyagram (Mermaid); README'deki komutlar sandbox'ta gerçekten çalıştırılarak doğrulanır; çalışmayan komut düzeltilir.
- **Kabul:** README'deki "kur ve çalıştır" adımları temiz ortamda başarıyla çalışır (otomatik).
- **Meta:** P2 · M · Bağ: IDE-05 · Durum: açık

#### IDE-21 · Mevcut proje içe aktarma ve analiz
- **Sorun:** [DOĞRULANDI] ZIP içe aktarma var; "bu proje ne yapıyor, nasıl çalıştırılır, nerede açık var" analizi sınırlı ve güvenlik sınırı yok (SEC-07).
- **Değişiklik:** ZIP/Git URL içe aktarma (güvenli), yapı ve bağımlılık analizi, testleri çalıştırma, açıklama raporu, kalite/güvenlik özeti.
- **Kabul:** 10 açık kaynak projede özet doğruluğu uzman kontrol listesine göre ≥ %85; zip-slip/bomba örnekleri reddedilir.
- **Meta:** P2 · M · Bağ: SEC-07, RAG-28 · Durum: açık

#### IDE-22 · Çalışma alanı kotası ve temizlik
- **Sorun:** [ÖNERİ] Disk, sürüm sayısı ve süreç sınırı yok; silinen çalışma alanı artığı kalabilir.
- **Değişiklik:** Kullanıcı başına disk/çalışma alanı kotası, eski sürüm budama, boşta kalan sunucuların kapatılması, silmede tam temizlik ve (isteğe bağlı) yedek.
- **Kabul:** Kota aşımında net hata; silme sonrası dizin ve veritabanı kaydı kalmaz (test).
- **Meta:** P2 · S · Bağ: DAT-06 · Durum: açık

#### IDE-23 · Ekip içi birlikte çalışma
- **Sorun:** [ÖNERİ] Takım arkadaşları aynı çalışma alanını göremiyor/yorumlayamıyor.
- **Değişiklik:** Tailscale içinde salt-okunur/yorumlu paylaşım, dosya başına kilit/uyarı, değişiklik akışı; isteğe bağlı gerçek zamanlı ortak düzenleme (CRDT) sonraki aşama.
- **Kabul:** İkinci kullanıcı yetkisine göre görüntüleyebilir/yorumlayabilir; yetkisiz kullanıcı göremez (SEC-04).
- **Meta:** P3 · L · Bağ: SEC-04, UX-26 · Durum: açık

#### IDE-24 · Üretim kalitesi eval seti ve model karşılaştırma
- **Sorun:** [ÖNERİ] "Proje üretimi iyi mi?" bilinmiyor; hangi model/ajan için daha iyi olduğu ölçülmüyor.
- **Değişiklik:** 20 istem × (kurulur, testler geçer, duman testi, kullanıcı akışı, güvenlik bulgusu 0) otomatik puan; model/ajan/şablon başına karşılaştırma; "çalışan proje oranı" birincil metrik.
- **Kabul:** Hedef: çalışan proje oranı ≥ %80, test geçme ≥ %85; sonuçlar HAL-05 kapısına ve DIST-19 model karşılaştırmasına bağlı.
- **Meta:** P0 · M · Bağ: IDE-05, HAL-03 · Durum: açık

---

## B. GAME — Oyun Stüdyosu

> "Oyun istiyorsa basit bir şekilde oyun yapsın." Hedef: istemden **oynanabilir, test edilmiş, paketlenmiş** küçük oyun. Karmaşık 3B motor kapsam dışıdır (08-yol-haritasi, Yapılmayacaklar).

#### GAME-01 · Oyun motoru şablonu (Canvas2D)
- **Sorun:** [ÖNERİ] Oyunlar her seferinde sıfırdan yazılıyor; oyun döngüsü, girdi, çarpışma hataları yinelenen sorun.
- **Değişiklik:** ES modül motoru: sabit zaman adımlı döngü, sahne yöneticisi, girdi (klavye/fare/dokunma/gamepad), kamera, çarpışma (AABB/daire/SAT), parçacıklar, WebAudio; testli ve çevrimdışı çalışır.
- **Kabul:** Motorun birim testleri (çarpışma, zaman adımı) geçer; 60 FPS'te bellek sızıntısı yok (10 dk soak testi).
- **Meta:** P1 · L · Bağ: IDE-17 · Durum: açık

#### GAME-02 · Tür şablonları
- **Sorun:** [ÖNERİ] "Oyun yap" isteği yapılandırılmamış.
- **Değişiklik:** 10 tür şablonu (platform, uzay atıcı, eşleştirme bulmacası, yukarıdan yarış, kule savunması, hafıza, snake/pong klasikleri, kart oyunu, kelime oyunu, basit RPG); her şablon çalışır ve LLM'in özelleştirebileceği veri dosyasına ayrılmış.
- **Kabul:** Her şablon kutudan çıktığı gibi oynanır ve bot testini geçer (GAME-05); özelleştirme yalnız veri/kural dosyalarını değiştirir.
- **Meta:** P1 · L · Bağ: GAME-01 · Durum: açık

#### GAME-03 · Kısa oyun tasarım belgesi
- **Sorun:** [ÖNERİ] Çekirdek döngü, kazanma/kaybetme koşulu belirsiz oyunlar üretiliyor.
- **Değişiklik:** İstemden kısa GDD (çekirdek döngü, kontroller, kazanma/kaybetme, zorluk eğrisi, varlık listesi); kullanıcı onayı veya hızlı modda otomatik.
- **Kabul:** Üretilen her oyunda GDD'deki kazanma ve kaybetme koşulları tetiklenebilir (GAME-05 doğrular).
- **Meta:** P2 · S · Bağ: GAME-02 · Durum: açık

#### GAME-04 · Varlık üretimi (görsel ve ses)
- **Sorun:** [ÖNERİ] Oyunlar dikdörtgen/yer tutucu görsellerle geliyor; ses yok.
- **Değişiklik:** Parametrik piksel-sanat/SVG sprite üreteci, arka plan ve arayüz öğeleri; prosedürel ses efektleri ve basit müzik (WebAudio); lisans sorunsuz, kaynak notu.
- **Kabul:** Üretilen oyunda yer tutucu dikdörtgen kalmaz (görsel denetim); ses açma/kapama çalışır.
- **Meta:** P2 · M · Bağ: GAME-02 · Durum: açık

#### GAME-05 · Bot ile otomatik oynanış testi
- **Sorun:** [ÖNERİ] Oyunun gerçekten oynanabildiği doğrulanmıyor.
- **Değişiklik:** Playwright + oyun içi test kancaları: bot N saniye oynar (rastgele + sezgisel), çökme/NaN/takılma/sonsuz döngü, skor ilerlemesi, kazanma/kaybetme tetiklenmesi, FPS ölçümü.
- **Kabul:** Bilerek bozulan 10 oyunda (donan döngü, çalışmayan tuş) hata yakalama ≥ %85; sağlam oyunlarda 30 sn botla çökme 0, FPS ≥ 55.
- **Meta:** P0 · L · Bağ: IDE-06, GAME-01 · Durum: açık

#### GAME-06 · Denge parametreleri ve seviye doğrulaması
- **Sorun:** [ÖNERİ] LLM'in ürettiği seviyeler çözülemez veya aşırı kolay olabilir.
- **Değişiklik:** Denge değerleri `balance.json` güvenli bölgesinde; seviye üreteci doğrulanabilir (çözülebilirlik/ulaşılabilirlik denetimi); zorluk eğrisi grafiği.
- **Kabul:** Üretilen 50 seviyede çözülemez seviye oranı 0 (bot/çözücü).
- **Meta:** P3 · M · Bağ: GAME-05 · Durum: açık

#### GAME-07 · Kayıt, ayarlar ve mobil kontroller
- **Sorun:** [ÖNERİ] Yüksek skor, duraklatma, ayar menüsü ve dokunmatik kontrol tutarsız.
- **Değişiklik:** Ortak oyun kabuğu: yüksek skor (localStorage/IndexedDB), duraklat, ses/zorluk ayarı, dokunmatik düğmeler, tam ekran, kontrast/erişilebilirlik seçenekleri.
- **Kabul:** Tüm şablonlarda duraklat ve yüksek skor çalışır (bot testi); telefon boyutunda kontroller kullanılabilir (e2e).
- **Meta:** P2 · M · Bağ: GAME-01 · Durum: açık

#### GAME-08 · Oyun paketleme
- **Sorun:** [ÖNERİ] Oyunu paylaşmak/çalıştırmak için tek tıkla paket yok.
- **Değişiklik:** Tek HTML, PWA, masaüstü `.exe` (pywebview + PyInstaller) ve ZIP (itch.io uyumlu); kapak görseli ve README otomatik.
- **Kabul:** Her paket temiz ortamda açılır ve ilk sahnede takılmadan oynanır.
- **Meta:** P2 · M · Bağ: IDE-16 · Durum: açık

#### GAME-09 · Basit 3B şablon (yerel three.js)
- **Sorun:** [ÖNERİ] "3B oyun" isteği karşılanmıyor.
- **Değişiklik:** three.js yerel paket (CDN yok) ile sahne, ışık, WASD, çarpışma, performans bütçesi (çizim çağrısı/üçgen limiti); yalnız basit düşük-poligon oyunlar.
- **Kabul:** Şablon 55+ FPS çalışır (orta seviye entegre GPU); bot testi çökmesiz geçer.
- **Meta:** P3 · L · Bağ: GAME-05 · Durum: açık

#### GAME-10 · Oyun eval seti
- **Sorun:** [ÖNERİ] Oyun üretim kalitesi ölçülmüyor.
- **Değişiklik:** 15 istem × (açılıyor, kontrol çalışıyor, kazanma/kaybetme tetikleniyor, 30 sn bot sorunsuz, FPS ≥ 55) otomatik puan.
- **Kabul:** Geçme oranı ≥ %85; sonuçlar IDE-24 ile aynı raporlamaya girer.
- **Meta:** P1 · M · Bağ: GAME-05, HAL-03 · Durum: açık

---

## C. DOM — Alan Motorları ve "Her Alanda Cevap" Çerçevesi

> **Gerçekçilik notu:** Her alan için elle yazılmış motor yazmak ölçeklenmez ve "örnek veriyle sahte sonuç" hatasına yol açtı [DOĞRULANDI: F4/F5]. "Her alanda cevap" hedefinin gerçekçi yolu: **genel amaçlı çekirdek (RAG + araçlar + doğrulama) + az sayıda gerçekten doğrulanmış uzman motor + yeni alanı kod yazmadan ekleme çerçevesi (DOM-12).**

#### DOM-01 · Alan motoru sözleşmesi: varsayılan değer yok
- **Sorun:** [DOĞRULANDI: F4] `run_cfo_financial_analysis` gelir/FAVÖK vb. için varsayılan örnek değerlerle çalışıyordu; sohbet bu sonucu kullanıcının sayıları gibi sundu (düzeltildi, ama tüm motorlar bu kalıbı taşıyabilir).
- **Değişiklik:** Alan motorları pydantic girdi şemasıyla çalışır; **varsayılan değer yok**, eksik girdide `MissingInputs` hatası → netleştirme sorusu (ORC-15); çıktı = sonuç + varsayımlar + formül kaynağı + birimler.
- **Kabul:** Eksik girdiyle çağrılan hiçbir motor sonuç üretmez (parametrik test: tüm motorlar); sonuç nesnesi `assumptions` ve `sources` alanlarını taşır.
- **Meta:** P0 · M · Bağ: ORC-15 · Durum: açık

#### DOM-02 · Finans: gerçek girdili DCF, rasyo, Monte Carlo
- **Sorun:** [DOĞRULANDI: F4] Mevcut motor örnek verilerle; gerçek şirket verisi alma/çıkarma yok.
- **Değişiklik:** Bilanço/gelir tablosu belgelerinden (RAG-16) girdi çıkarma + kullanıcı onayı; DCF, WACC, duyarlılık, Monte Carlo (tohumlu, varsayımlar açık); "yatırım tavsiyesi değildir" notu; sonuç tablo+grafik+varsayım listesi.
- **Kabul:** Ders kitabı vakalarında (≥ 10) sonuçlar bilinen değerle ±%0.5; girdi tablosu belgeden çıkarılan değerlerin kaynağını gösterir.
- **Meta:** P2 · L · Bağ: DOM-01, RAG-16 · Durum: açık

#### DOM-03 · Hukuk: madde analizi (kural + LLM + insan gözden geçirme)
- **Sorun:** [DOĞRULANDI: F5] Mevcut analiz anahtar kelime/regex tabanlı; belge yokken prompt metnini "sözleşme" gibi taradı (düzeltildi); mevzuat atıfları kaynaksız olabilir.
- **Değişiklik:** Madde sınırlandırma + sınıflandırma (LLM, şema kısıtlı) + risk gerekçesi + ilgili mevzuat (mevzuat.gov.tr RAG-18 ile, madde numarası doğrulanmış); redline önerileri "taslak, avukat incelemesi gerekir" notuyla.
- **Kabul:** 20 sözleşmede kritik madde yakalama recall'u ≥ %85 (hukukçu etiketi); atıf yapılan her mevzuat maddesi kaynakta doğrulanmış.
- **Meta:** P2 · L · Bağ: DOM-01, RAG-18, HAL-17 · Durum: açık

#### DOM-04 · Sağlık: genel bilgi ve güvenlik politikası
- **Sorun:** [ÖNERİ] Sağlık sorularında uydurma bilgi zarar verir; teşhis/doz üretimi kabul edilemez.
- **Değişiklik:** Yalnız güvenilir kurum kaynaklarından (WHO, ilgili sağlık bakanlığı, kılavuzlar) atıflı genel bilgi; teşhis/ilaç dozu/tedavi planı üretimi yok; acil belirtilerde yönlendirme; zorunlu uyarı.
- **Kabul:** 100 sağlık isteminde kaynaksız yanıt 0, dozaj/teşhis üretimi 0; acil vakalarda yönlendirme ≥ %95.
- **Meta:** P1 · M · Bağ: HAL-19, RAG-18 · Durum: açık

#### DOM-05 · Mühendislik hesapları: birim güvenli kütüphane
- **Sorun:** [ÖNERİ] Birim dönüşümü ve formül kullanımı modele bırakılıyor.
- **Değişiklik:** `pint` ile birim güvenli hesap, formül deposu (kaynak standart/ders kitabı), sayısal doğrulama testleri; çıktıda formül ve birimler.
- **Kabul:** 100 mühendislik hesabında doğruluk %100; birim uyuşmazlığı hata verir, sessizce dönüştürmez.
- **Meta:** P1 · M · Bağ: DEF-22, ORC-08 · Durum: açık

#### DOM-06 · CNC balonlama doğruluk eval'i
- **Sorun:** [DOĞRULANDI: F18] CNC balonlama için yalnız birim testleri var; gerçek çizimlerde balon/tolerans okuma doğruluğu ölçülmemiş.
- **Değişiklik:** 30 etiketli teknik çizim; balon recall/precision, ölçü ve tolerans okuma doğruluğu, ISO 2768/286 tablo eşleşmesi; hata raporu.
- **Kabul:** Balon recall ≥ %90, ölçü değeri doğruluğu ≥ %95; rapor eval kapısında.
- **Meta:** P2 · L · Bağ: HAL-03 · Durum: açık

#### DOM-07 · CNC fizik ve FEA formüllerinin doğrulanması
- **Sorun:** [DOĞRULANDI] `cad_cam_physics.py` (785 satır) Kienzle, sehim, ovalleşme hesapları yapıyor; literatür vakalarıyla doğrulanmamış, "tahmin" etiketi yok.
- **Değişiklik:** Ders kitabı/literatür örnekleriyle birim testleri, uygulanabilirlik sınırları, "yaklaşık/tahmini" etiketi ve belirsizlik notu.
- **Kabul:** 15 literatür vakasında sonuç sapması ≤ %5; sınır dışı girdide uyarı.
- **Meta:** P3 · M · Bağ: DOM-01 · Durum: açık

#### DOM-08 · G-kod doğrulama ve güvenlik uyarısı
- **Sorun:** [DOĞRULANDI] `cam_postprocessor` G-kod üretiyor; simülasyonla doğrulanmıyor, hatalı G-kod tezgâhta çarpışma riski taşır.
- **Değişiklik:** Denetleyici sözdizimi doğrulayıcı, yol simülasyonu/yazılımsal çarpışma kontrolü (ör. CAMotics benzeri), "gerçek tezgâhta denemeden önce simüle edin" zorunlu uyarısı.
- **Kabul:** Bilerek hatalı 30 G-kod örneğinde yakalama ≥ %85; çıktıda uyarı daima bulunur.
- **Meta:** P3 · L · Bağ: DOM-07 · Durum: açık

#### DOM-09 · Eğitim: müfredat, anlatım ve doğrulanmış alıştırma
- **Sorun:** [ÖNERİ] Konu anlatımı kaynaksız ve seviyeye duyarsız olabiliyor.
- **Değişiklik:** Öğrenme hedefi şablonları, kaynaklı anlatım, sorular + **otomatik doğrulanmış** çözümler (matematik/kod araçla), seviye uyarlama.
- **Kabul:** Üretilen alıştırma çözümlerinin %100'ü araçla doğrulanır; yanlış çözümlü alıştırma yayınlanmaz.
- **Meta:** P2 · M · Bağ: MODE-03, DOM-10 · Durum: açık

#### DOM-10 · Matematik ve bilim araç zinciri
- **Sorun:** [DOĞRULANDI] `tools_math_science` yalnız ince sarmalayıcı (19 satır); `tool_executor` SymPy adımlarını sınırlı sunuyor.
- **Değişiklik:** SymPy ile adım adım çözüm, iki yöntemle sayısal çapraz kontrol, birim analizi, grafik çizimi; hata durumunda "çözemedim" dürüstlüğü.
- **Kabul:** 200 vakalık analiz/lineer cebir/olasılık setinde doğruluk ≥ %95 (araç), sonuç model yorumuyla çelişmez.
- **Meta:** P1 · M · Bağ: ORC-08 · Durum: açık

#### DOM-11 · Programlama öğretmeni
- **Sorun:** [ÖNERİ] Kod açıklamaları doğrulanmadan veriliyor.
- **Değişiklik:** Kod parçasını çalıştırıp çıktıyla açıklama, hata tanısı, adım adım izleme (trace), seviye uyarlama.
- **Kabul:** Açıklamadaki "çıktı şu olur" iddiaları sandbox çıktısıyla %100 uyumlu.
- **Meta:** P3 · M · Bağ: HAL-12, MODE-03 · Durum: açık

#### DOM-12 · Yeni alan ekleme çerçevesi (kod yazmadan)
- **Sorun:** [ÖNERİ] Her yeni alan için Python modülü yazmak "her alanda cevap" hedefini ölçeklemez.
- **Değişiklik:** Alan tanımı = YAML (adı, niyetler, risk seviyesi, bilgi koleksiyonları, araçlar, çıktı sözleşmesi, uyarı metni, eval seti); yeni alan eklemek koda dokunmaz; şablon + doğrulayıcı betik.
- **Kabul:** Örnek yeni alan (ör. "mimari/inşaat") YAML + bilgi koleksiyonu + 20 soruluk eval ile 1 günde devreye alınır ve eval kapısını geçer.
- **Meta:** P1 · L · Bağ: ORC-03, RAG-12, HAL-03 · Durum: açık
