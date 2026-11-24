# Parça 8 — Dağıtık ajanlar/operasyon (DGT) ve veri katmanı (VRI)

## DGT · Dağıtık ajanlar, operasyon, CI ve dağıtım

#### DGT-01 · Tek komutla ajan kurulumu: Windows ve Linux (DIST-14)
- **Sorun:** [ÖNERİ] Kurulum betiği temiz makinede denenmedi.
- **Değişiklik:** Betik + Linux konteyner testi + Windows test planı.
- **Kabul:** Linux konteynerde ajan kaydolur ve heartbeat başlar (CI).
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### DGT-02 · Ajan otomatik güncelleme
- **Sorun:** [ÖNERİ] Ajan elle güncelleniyor.
- **Değişiklik:** Sürüm kontrolü ve güvenli güncelleme.
- **Kabul:** Eski ajan güncellenir ve geri alınabilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-03 · Ajan kaldırma betiği
- **Sorun:** [ÖNERİ] Kaldırma yok.
- **Değişiklik:** Servis, görev, anahtar temizliği.
- **Kabul:** Kaldırma sonrası kayıt çevrimdışı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-04 · Dağıtık hızlanma ölçümü (DIST-21)
- **Sorun:** [ÖNERİ] 1/2/4/6 ajan ölçümü yok.
- **Değişiklik:** Standart iş yükleri ve Amdahl analizi.
- **Kabul:** Hızlanma grafiği ve rapor.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-05 · Ajan başarısızlığı kaos testi (DIST-22)
- **Sorun:** [ÖNERİ] Ajan öldürme senaryosu otomatik değil.
- **Değişiklik:** Kaos betiği (ajan kes, ağ kes).
- **Kabul:** Görev yeniden atanır ve tamamlanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-06 · Görev kiralama süresi ve kalp atışı toleransı
- **Sorun:** [ÖNERİ] Zaman aşımı sabit.
- **Değişiklik:** Ayarlanabilir kira.
- **Kabul:** Yavaş ajan gereksiz yeniden atanmaz.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-07 · Yeniden atamada çift çalışma önleme (idempotency)
- **Sorun:** [ÖNERİ] Aynı görev iki ajanda çıktı verebilir.
- **Değişiklik:** Görev sürüm/jeton.
- **Kabul:** Eski ajanın geç sonucu reddedilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-08 · Ajan yetenek puanı güncelleme
- **Sorun:** [ÖNERİ] Puanlar statik.
- **Değişiklik:** Benchmark sonuçlarıyla periyodik güncelleme.
- **Kabul:** Puan değişimi seçimi etkiler.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-09 · Ajan başına kota ve adil dağıtım
- **Sorun:** [ÖNERİ] Ağır görev tek ajana yığılabilir.
- **Değişiklik:** Yük farkındalıklı dağıtım.
- **Kabul:** Yük dengesi ölçülür.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-10 · Ajan çıktı doğrulaması (master tarafı)
- **Sorun:** [ÖNERİ] Ajan çıktısı doğrudan kabul ediliyor.
- **Değişiklik:** Biçim ve içerik doğrulaması.
- **Kabul:** Bozuk çıktı reddedilir ve yeniden atanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-11 · Ağ bölünmesinde davranış (Tailscale kopması)
- **Sorun:** [ÖNERİ] Davranış belgesiz.
- **Değişiklik:** Yeniden bağlanma ve görev durumu.
- **Kabul:** Kopma sonrası görevler tutarlı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-12 · Ajan telemetrisi gerçek veri (DEF-18)
- **Sorun:** [ÖNERİ] Demo modunda sabit tablo kalabilir.
- **Değişiklik:** `/api/ps` ve `/api/show` testleri.
- **Kabul:** Demo ajanı telemetrisi Ollama'dan.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-13 · `start_agents.py` ince sarmalayıcı
- **Sorun:** [ÖNERİ] İki çalıştırıcı yol.
- **Değişiklik:** Tek çalıştırıcıya indirgeme.
- **Kabul:** İki mod testi `test_agent.py`'de.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-14 · Çakışma çözme arayüzü ve algoritması (DIST-15)
- **Sorun:** [ÖNERİ] Çakışma çözümü e2e yok.
- **Değişiklik:** Üç yollu birleştirme.
- **Kabul:** Çakışan iki çıktı birleştirilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-15 · Proje DAG kritik yol hesabı
- **Sorun:** [ÖNERİ] Kritik yol gösterimi kısmen.
- **Değişiklik:** Hesap ve vurgulama testi.
- **Kabul:** Kritik yol doğru.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-16 · Ajan sandbox: ajan tarafında kod çalıştırma güvenliği
- **Sorun:** [ÖNERİ] Ajan görev kodunu çalıştırabilir.
- **Değişiklik:** Ajan tarafı Docker/kısıt.
- **Kabul:** Ajan kodu izole çalışır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-17 · Büyük çıktıların aktarımı
- **Sorun:** [ÖNERİ] Büyük sonuç JSON'a sığmıyor.
- **Değişiklik:** Parçalı yükleme.
- **Kabul:** 50 MB çıktı aktarılır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-18 · Çoklu master/yüksek erişilebilirlik (isteğe bağlı)
- **Sorun:** [ÖNERİ] Tek master.
- **Değişiklik:** Yedek master ve DB çoğaltma.
- **Kabul:** Master düşünce ajanlar bekler ve geri döner.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-19 · `/ready` bağımlılık bazlı degraded (OPS-03)
- **Sorun:** [ÖNERİ] Her bağımlılık kapatılınca doğru bileşen test edilmedi.
- **Değişiklik:** Bağımlılık kapatma testleri.
- **Kabul:** Her bağımlılık için doğru "degraded".
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### DGT-20 · Metrikler: ana yolların süreleri (OPS-02)
- **Sorun:** [ÖNERİ] Metrik adları belgeli ve sabit mi belirsiz.
- **Değişiklik:** Metrik sözlüğü ve test.
- **Kabul:** Metrik adları belgeyle eşleşir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-21 · OpenTelemetry izleri (isteğe bağlı)
- **Sorun:** [ÖNERİ] İz yok.
- **Değişiklik:** Basit iz.
- **Kabul:** İz kimliği günlükte.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-22 · Tek komutla başlatma temiz klon testi (OPS-04)
- **Sorun:** [ÖNERİ] Temiz klonda test edilmedi.
- **Değişiklik:** CI'da temiz klon betiği.
- **Kabul:** `/ready` yeşil olur.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-23 · Windows kurulum paketi (OPS-05)
- **Sorun:** [ÖNERİ] Tek tıkla kurulum yok.
- **Değişiklik:** Kurulum betiği/paket.
- **Kabul:** Temiz Windows'ta ≤ 15 dk (belgeli test planı).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-24 · CI: Python matrisi ve parçalı işler (OPS-07)
- **Sorun:** [ÖNERİ] Matris kısmen.
- **Değişiklik:** 3.12 + güncel, ayrı raporlanan kapılar.
- **Kabul:** PR kontrolleri < 15 dk.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-25 · CI: frontend lint/tip/birim/e2e
- **Sorun:** [ÖNERİ] Frontend CI sınırlı.
- **Değişiklik:** eslint, node testleri, Playwright.
- **Kabul:** Frontend işi ayrı kapı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-26 · Kapsam politikası: diff-cover (OPS-08)
- **Sorun:** [ÖNERİ] Kapsam kapısı yok.
- **Değişiklik:** diff-cover ≥ %85.
- **Kabul:** Kapsamı düşüren PR kırmızı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-27 · Test piramidi ve işaretler (OPS-09)
- **Sorun:** [ÖNERİ] İşaretler eksik.
- **Değişiklik:** Altı işaret ve hızlı küme.
- **Kabul:** Hızlı küme < 30 sn.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-28 · Özellik bayrakları: kapalı özellik tetiklenmez (OPS-11)
- **Sorun:** [ÖNERİ] "Hiçbir yolla" testi yok.
- **Değişiklik:** Her bayrak için kapalı-yol testi.
- **Kabul:** Kapalı özellik rotası 404/403.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-29 · Bayrak değişikliği denetim izine
- **Sorun:** [ÖNERİ] Kısmen.
- **Değişiklik:** Denetim kaydı testi.
- **Kabul:** Bayrak değişince kayıt oluşur.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-30 · Kaynak koruması: 200 MB yükleme (OPS-18)
- **Sorun:** [ÖNERİ] Bellek tepe ölçümü yok.
- **Değişiklik:** `tracemalloc` testi.
- **Kabul:** Tepe < 300 MB.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-31 · Hata izleme ve uyarı (OPS-19)
- **Sorun:** [ÖNERİ] Yineleyen hata gruplama uyarısı kısmen.
- **Değişiklik:** Toplayıcı + yönetici uyarısı.
- **Kabul:** Zorlanmış istisna gruplanır ve uyarı üretir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-32 · Demo ve sunum kiti (OPS-23)
- **Sorun:** [ÖNERİ] Kontrol listesi betiği 10 dk doğrulama.
- **Değişiklik:** Betik ve test.
- **Kabul:** Eksik bağımlılık raporlanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-33 · Demo modu: tek komutla
- **Sorun:** [ÖNERİ] Demo hazırlığı elle.
- **Değişiklik:** `demo_mode.ps1`.
- **Kabul:** Tek komut demo verisini kurar.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-34 · Yedek video/ekran görüntüleri
- **Sorun:** [ÖNERİ] Çevrimdışı yedek yok.
- **Değişiklik:** Demo kaydı.
- **Kabul:** Yedek dosyalar depoda/arşivde.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-35 · Runbook'lar: tüm hata durumları
- **Sorun:** [ÖNERİ] Runbook sayısı sınırlı.
- **Değişiklik:** 10 temel arıza runbook'u.
- **Kabul:** Her `/ready` bileşeni runbook'a bağlı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-36 · Günlük döndürme ve disk koruması
- **Sorun:** [ÖNERİ] Günlük büyüyebilir.
- **Değişiklik:** Döndürme ve boyut sınırı.
- **Kabul:** Günlük boyutu sınırlı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-37 · Zamanlı yedek ve saklama (DAT-07)
- **Sorun:** [ÖNERİ] Gerçek geri yükleme turu CI'da yok.
- **Değişiklik:** CI geri yükleme turu.
- **Kabul:** Kayıt sayıları ve özetler aynı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-38 · Sürüm etiketleme ve geri alma
- **Sorun:** [ÖNERİ] Dağıtım sürümlenmiyor.
- **Değişiklik:** Sürüm etiketi ve geri alma betiği.
- **Kabul:** Önceki sürüme dönüş çalışır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-39 · Konteyner imajı küçültme ve güvenlik
- **Sorun:** [ÖNERİ] Imaj taraması kısmen.
- **Değişiklik:** Çok aşamalı imaj, root olmayan kullanıcı.
- **Kabul:** Imaj root değil, Trivy temiz.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-40 · Sağlık denetimi arayüzü
- **Sorun:** [ÖNERİ] `/ready` yalnız JSON.
- **Değişiklik:** Yönetici sağlık sayfası.
- **Kabul:** Bileşen durumları sayfada.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### DGT-41 · Sıcak yeniden başlatma: yarım kalan işler
- **Sorun:** [ÖNERİ] Yeniden başlatmada iş kaybı.
- **Değişiklik:** İş kurtarma.
- **Kabul:** Yeniden başlatmada yarım iş "kesildi" olarak işaretlenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-42 · Kaynak izleme: GPU/VRAM
- **Sorun:** [ÖNERİ] VRAM görünürlüğü sınırlı.
- **Değişiklik:** nvidia-smi/`/api/ps` panosu.
- **Kabul:** Pano VRAM gösterir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-43 · Güç yönetimi ve uyku engeli
- **Sorun:** [ÖNERİ] Uzun iş sırasında bilgisayar uyur.
- **Değişiklik:** Uyku engelleme seçeneği.
- **Kabul:** Uzun iş sırasında uyku engellenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### DGT-44 · Ajan arası model paylaşımı/önbellek
- **Sorun:** [ÖNERİ] Her ajan model indiriyor.
- **Değişiklik:** Yerel ağ model aynası.
- **Kabul:** İkinci ajan modeli ağdan alır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-45 · Kullanım kotası ve maliyet muhasebesi
- **Sorun:** [ÖNERİ] Maliyet takibi yok.
- **Değişiklik:** Token/süre/enerji tahmini.
- **Kabul:** Kullanıcı başına kullanım raporu.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DGT-46 · Çalışma zamanı yapılandırma doğrulaması
- **Sorun:** [ÖNERİ] Hatalı env değerleri geç fark ediliyor.
- **Değişiklik:** Başlangıçta şema doğrulama.
- **Kabul:** Hatalı değerde açık hata ile başlamaz.
- **Meta:** P2 · S · Bağ: - · Durum: açık

## VRI · Veri katmanı, saklama ve taşınabilirlik

#### VRI-01 · Göç şema karşılaştırması (DAT-02)
- **Sorun:** [ÖNERİ] Sıfırdan kurulum ile yükseltme aynı şemayı üretiyor mu testi yok.
- **Değişiklik:** Şema karşılaştırma testi.
- **Kabul:** İki yol aynı şemayı üretir.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### VRI-02 · Başarısız göç geri alma
- **Sorun:** [ÖNERİ] Göç yarıda kalırsa veritabanı bozulabilir.
- **Değişiklik:** Göç öncesi anlık görüntü ve geri dönüş.
- **Kabul:** Başarısız göç DB'yi eski haline döndürür.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### VRI-03 · Eşzamanlılık stres testi 60 sn (DAT-03)
- **Sorun:** [ÖNERİ] 8+8 testi kısa sürelidir.
- **Değişiklik:** 60 sn stres ve "database is locked" sayacı.
- **Kabul:** "locked" 0; WAL büyümesi sınırlı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-04 · WAL checkpoint politikası
- **Sorun:** [ÖNERİ] WAL dosyası büyüyebilir.
- **Değişiklik:** Periyodik checkpoint.
- **Kabul:** WAL boyutu eşik altı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-05 · İçerik adresli dosya deposu: çöp toplama (DAT-05)
- **Sorun:** [ÖNERİ] Test kısmen.
- **Değişiklik:** GC testi.
- **Kabul:** Referanssız blob silinir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-06 · İmzalı dosya URL'leri
- **Sorun:** [ÖNERİ] URL yetkisi.
- **Değişiklik:** İmza süresi testi.
- **Kabul:** Süresi dolan imza reddedilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-07 · Saklama süresi ve tam silme (DAT-06)
- **Sorun:** [ÖNERİ] Süresi dolan veri otomatik siliniyor mu test kısmen.
- **Değişiklik:** Zamanlı temizlik testi.
- **Kabul:** Süresi dolan veri silinir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-08 · Benzersiz dizge izlemi: silme sonrası dosya sistemi taraması
- **Sorun:** [ÖNERİ] Silme sonrası kalıntı taraması kısmen.
- **Değişiklik:** Veritabanı + dosya sistemi taraması.
- **Kabul:** Benzersiz dizge bulunmaz.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-09 · Artımlı yedek (DAT-07)
- **Sorun:** [ÖNERİ] Tam yedek; artımlı yok.
- **Değişiklik:** Artımlı yedek.
- **Kabul:** Artımlı + tam geri yükleme aynı sonuç.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-10 · Bozuk yedek reddi
- **Sorun:** [ÖNERİ] Bozuk zip davranışı.
- **Değişiklik:** Karma doğrulama.
- **Kabul:** Bozuk yedek 400.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-11 · Veri taşınabilirliği A→B (DAT-08)
- **Sorun:** [ÖNERİ] İki makine senaryosu testi yok.
- **Değişiklik:** İki ortam taklidi ile dışa/içe aktarma.
- **Kabul:** Sohbet/artefakt/koleksiyon tam.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-12 · İçe aktarmada kimlik yeniden eşleme
- **Sorun:** [ÖNERİ] Çakışan kimlik.
- **Değişiklik:** Kimlik eşleme.
- **Kabul:** Çakışmada veri kaybı yok.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-13 · Hafıza konsolidasyonu: çelişki sorma (DAT-09)
- **Sorun:** [ÖNERİ] Test kısmen.
- **Değişiklik:** Çelişki tespiti.
- **Kabul:** Çelişen tercih kullanıcıya sorulur.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-14 · Hafıza yaş/güven bozunumu
- **Sorun:** [ÖNERİ] Eski hafıza eşit ağırlıkta.
- **Değişiklik:** Bozunum işlevi.
- **Kabul:** Eski düşük güvenli hafıza az ağırlık alır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-15 · Hafıza kullanım görünürlüğü
- **Sorun:** [ÖNERİ] Hangi yanıtta hangi hafıza belli değil.
- **Değişiklik:** Yanıt meta verisinde hafıza kimlikleri.
- **Kabul:** Yanıt kullanılan hafızayı gösterir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-16 · Birleşik FTS5 arama ölçeği (DAT-10)
- **Sorun:** [ÖNERİ] 100.000 kayıtta p95 ölçülmedi.
- **Değişiklik:** Ölçek benchmark'ı.
- **Kabul:** p95 < 100 ms.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-17 · FTS Türkçe tokenizer
- **Sorun:** [ÖNERİ] Türkçe ek/ı-i.
- **Değişiklik:** Normalizasyon ve test.
- **Kabul:** Ek farklı sorgu eşleşir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-18 · Sahip filtresi arama API'sinde
- **Sorun:** [ÖNERİ] Başkasının sonuçları.
- **Değişiklik:** Sahip testi.
- **Kabul:** Arama sahibine özel.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-19 · Vektör sürüm karışımı reddi (DAT-11)
- **Sorun:** [ÖNERİ] Karışım testi kısmen.
- **Değişiklik:** Karışık sürümde ret/uyarı.
- **Kabul:** Farklı model kayıtları karışmaz.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-20 · DB doktoru: bozuk veritabanı onarımı (DAT-12)
- **Sorun:** [ÖNERİ] Tüm sorunları listeler testi.
- **Değişiklik:** Bilerek bozma testleri.
- **Kabul:** Tüm sorunlar listelenir, onarılabilenler onarılır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-21 · DB doktoru yönetici arayüzünde
- **Sorun:** [ÖNERİ] CLI.
- **Değişiklik:** Arayüz raporu.
- **Kabul:** Sayfada bulgular.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-22 · 1 milyon satır sorgu planı testi (DAT-13)
- **Sorun:** [ÖNERİ] Sentetik büyük veri testi yok.
- **Değişiklik:** 1M satırlı test ve `EXPLAIN`.
- **Kabul:** Kritik sorgular indeks kullanır, p95 < 50 ms.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-23 · Eski mesaj arşivleme
- **Sorun:** [ÖNERİ] Mesajlar sonsuz büyür.
- **Değişiklik:** Arşiv tablosu.
- **Kabul:** Eski mesajlar arşive taşınır, aranabilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-24 · Olay günlüğü filtre arayüzü (DAT-14)
- **Sorun:** [ÖNERİ] Arayüz sınırlı.
- **Değişiklik:** Filtre ve dışa aktarma.
- **Kabul:** Olay türüne göre filtre.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-25 · Olay günlüğü halka tampon
- **Sorun:** [ÖNERİ] Büyüme.
- **Değişiklik:** Saklama ve satır sınırı.
- **Kabul:** Sınır aşılınca eski silinir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-26 · Sahiplik testi tüm tablolar (DAT-15)
- **Sorun:** [ÖNERİ] Her tablo için sızıntı testi otomatik üretilmiyor.
- **Değişiklik:** Tablo başına üretilen test.
- **Kabul:** Her tablo için A→B sızıntı yok.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-27 · `owner_id` olmayan tablo lint'i
- **Sorun:** [ÖNERİ] Yeni tablo sahipliksiz eklenebilir.
- **Değişiklik:** Sınıflandırılmamış tablo CI hatası.
- **Kabul:** Yeni tablo sınıflanmadan CI kırar.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-28 · Veritabanı şifreleme seçeneği (SQLCipher)
- **Sorun:** [ÖNERİ] DB düz dosya.
- **Değişiklik:** İsteğe bağlı şifreli DB.
- **Kabul:** Şifreli DB'de düz metin yok.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-29 · Çok kullanıcı eşzamanlılığı: kilit çekişmesi metriği
- **Sorun:** [ÖNERİ] Kilit çekişmesi izlenmiyor.
- **Değişiklik:** Kilit bekleme metriği.
- **Kabul:** Metrik `/metrics`te.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-30 · PostgreSQL geçiş yolu (db_portable)
- **Sorun:** [ÖNERİ] Taşınabilirlik katmanı kısmen.
- **Değişiklik:** PostgreSQL ile test paketi (isteğe bağlı CI).
- **Kabul:** Temel tablolar PostgreSQL'de çalışır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-31 · Veritabanı boyut ve tablo raporu
- **Sorun:** [ÖNERİ] Boyut görünmüyor.
- **Değişiklik:** Yönetici raporu.
- **Kabul:** Tablo boyutları listelenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### VRI-32 · Sohbet arşivi dışa aktarma/içe aktarma biçimi
- **Sorun:** [ÖNERİ] Standart biçim yok.
- **Değişiklik:** JSON şeması.
- **Kabul:** Şemaya göre dışa/içe aktarma.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-33 · Kullanıcı hesabı silme: tüm kopyalar
- **Sorun:** [ÖNERİ] Eksik iz.
- **Değişiklik:** Silme akışı testi.
- **Kabul:** Hesap silince sahip tablolarda iz yok.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-34 · Veri sürümleri: artefakt ve belge geçmişi
- **Sorun:** [ÖNERİ] Sürüm tabloları dağınık.
- **Değişiklik:** Ortak sürüm şeması.
- **Kabul:** Sürüm geçmişi tutarlı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-35 · Tarih/saat dilimi tutarlılığı
- **Sorun:** [ÖNERİ] UTC/yerel karışabilir.
- **Değişiklik:** Tümü UTC, gösterim yerel.
- **Kabul:** Saat dilimi testi.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### VRI-36 · Uzun ömürlü kayıt şeması geriye uyum testi
- **Sorun:** [ÖNERİ] Eski sürüm veri yükleme.
- **Değişiklik:** Sürüm başına örnek DB.
- **Kabul:** Eski örnek DB yükseltilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### VRI-37 · Veri sözlüğü ve ERD güncelliği
- **Sorun:** [ÖNERİ] ERD elle.
- **Değişiklik:** ERD otomatik üretimi CI'da.
- **Kabul:** ERD şemayla uyuşur.
- **Meta:** P2 · S · Bağ: - · Durum: açık
