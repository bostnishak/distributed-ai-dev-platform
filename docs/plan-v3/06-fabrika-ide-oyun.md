# Parça 6 — Yazılım fabrikası, IDE, oyun (FAB)

## FAB · Yazılım fabrikası, IDE, oyun ve kod doğrulama

#### FAB-01 · Proje üretiminde "çalışan proje" oranı ölçümü (IDE-05)
- **Sorun:** [ÖNERİ] 20 proje isteminde ≥ %80 çalışan proje ölçülmedi.
- **Değişiklik:** 20 istemlik set, kur-derle-test-çalıştır-sağlık döngüsü.
- **Kabul:** Çalışan proje oranı raporlanır, ≥ %80 değilse partial.
- **Meta:** P0 · L · Bağ: - · Durum: açık

#### FAB-02 · Onarım döngüsü: 5 tur ve rapor
- **Sorun:** [ÖNERİ] Onarım turları ve hata raporu kısmen.
- **Değişiklik:** Hata çıktısı + dosya ile hedefli yama, tur özeti.
- **Kabul:** Kalıcı hatada hangi adımda neden takıldığı raporlanır.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### FAB-03 · Tarayıcı doğrulaması (Playwright) (IDE-06)
- **Sorun:** [ÖNERİ] Bilerek bozulan 20 projede yakalama ölçülmedi.
- **Değişiklik:** Kırık JS yolu, boş sayfa, çalışmayan düğme senaryoları.
- **Kabul:** Yakalama ≥ %85, yanlış alarm < %5.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-04 · Ekran görüntüsü + VLM düzgün mü denetimi
- **Sorun:** [ÖNERİ] VLM kullanılmıyor.
- **Değişiklik:** Görsel denetim ve sorun listesi.
- **Kabul:** Boş sayfa ekran görüntüsünde işaretlenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-05 · Bağımlılık paket varlığı denetimi (IDE-07)
- **Sorun:** [ÖNERİ] Uydurma paket yakalama ölçülmedi.
- **Değişiklik:** Kurulum öncesi paket listesi denetimi.
- **Kabul:** Uydurma paketlerde ≥ %90.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-06 · Kilit dosyası üretimi
- **Sorun:** [ÖNERİ] Üretilen projede kilit dosyası yok.
- **Değişiklik:** `requirements.txt` karmalı / `package-lock.json`.
- **Kabul:** Üretilen projede kilit dosyası var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-07 · Gerçek etkileşimli terminal (PTY) (IDE-08)
- **Sorun:** [ÖNERİ] Terminal komut-yanıt, gerçek PTY değil.
- **Değişiklik:** ConPTY/`pty` + xterm.js + WebSocket.
- **Kabul:** `python`, `pytest -x` etkileşimli çalışır.
- **Meta:** P1 · L · Bağ: - · Durum: açık

#### FAB-08 · Terminal oturum yeniden bağlanma
- **Sorun:** [ÖNERİ] Sayfa yenilenince oturum kaybı.
- **Değişiklik:** Oturum kimliği ve geri yükleme.
- **Kabul:** Yenilemede oturum sürer.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-09 · Süreç ağacı temizliği
- **Sorun:** [ÖNERİ] Kapatınca alt süreçler kalabilir.
- **Değişiklik:** Süreç grubu sonlandırma.
- **Kabul:** Terminal kapanınca süreç ağacı temizlenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-10 · LSP entegrasyonu (IDE-09)
- **Sorun:** [ÖNERİ] Tanıma gitme/tanılama yok.
- **Değişiklik:** pyright/tsserver köprüsü.
- **Kabul:** Tür hatası altı çizilir (e2e).
- **Meta:** P1 · L · Bağ: - · Durum: açık

#### FAB-11 · Monaco editörü ve diff (IDE-10)
- **Sorun:** [ÖNERİ] Basit editör.
- **Değişiklik:** Monaco yerel paket, diff editör, minimap.
- **Kabul:** Mevcut IDE özellikleri regresyonsuz.
- **Meta:** P1 · L · Bağ: - · Durum: açık

#### FAB-12 · IDE bileşeninin ayrı modüle taşınması
- **Sorun:** [ÖNERİ] `assistant.js` 492 satır, sınırda.
- **Değişiklik:** IDE kodunun ayrı modüle bölünmesi.
- **Kabul:** `assistant.js` < 400 satır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-13 · Gerçek git ile sürüm yönetimi (IDE-12)
- **Sorun:** [ÖNERİ] Çalışma alanı git deposu değil.
- **Değişiklik:** `git init`, anlamlı commit, dallanma, çakışma arayüzü.
- **Kabul:** Sürüme dönüp ileri geri veri kaybı yok.
- **Meta:** P1 · L · Bağ: - · Durum: açık

#### FAB-14 · Çok dosyalı düzenleme ajanı (IDE-13)
- **Sorun:** [ÖNERİ] 30 değişiklik isteğinde kapsam sızıntısı ölçülmedi.
- **Değişiklik:** İlgili dosya bulma, patch seti, test, geri alınabilir grup.
- **Kabul:** Kapsam sızıntısı < %10.
- **Meta:** P1 · L · Bağ: - · Durum: açık

#### FAB-15 · Hata ayıklama DAP (IDE-14)
- **Sorun:** [ÖNERİ] Kesme noktası yok.
- **Değişiklik:** debugpy köprüsü.
- **Kabul:** Kesme noktasında değişken görülür (e2e).
- **Meta:** P1 · L · Bağ: - · Durum: açık

#### FAB-16 · Yığın izi açıklaması doğru dosya:satır
- **Sorun:** [ÖNERİ] Açıklama satıra atıf yapmıyor.
- **Değişiklik:** İz ayrıştırma ve kaynakla eşleme.
- **Kabul:** Atıf doğru dosya:satır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-17 · 8 testli proje şablonu (IDE-17)
- **Sorun:** [DOĞRULANDI: F107] `templates/` yok.
- **Değişiklik:** FastAPI+SQLite, SPA, CLI, masaüstü, veri, Chrome eklentisi, REST+ön yüz, oyun iskeleti.
- **Kabul:** Her şablon kurulur, testi geçer, CI işi var.
- **Meta:** P0 · L · Bağ: - · Durum: açık

#### FAB-18 · Şablon tabanlı üretim A/B
- **Sorun:** [ÖNERİ] Şablon kazancı ölçülmedi.
- **Değişiklik:** Şablonlu ve şablonsuz 20 istem.
- **Kabul:** Şablonlu ≥ 15 puan fazla çalışan proje.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-19 · Üretilen projede lint/tip/CI dosyası (IDE-19)
- **Sorun:** [ÖNERİ] CI dosyası üretimi kısmen.
- **Değişiklik:** ruff/eslint, mypy, GitHub Actions.
- **Kabul:** Üretilen proje lint temiz.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-20 · README komutlarının sandbox'ta doğrulanması (IDE-20)
- **Sorun:** [ÖNERİ] README komutları denenmiyor.
- **Değişiklik:** Komut çıkarma ve çalıştırma.
- **Kabul:** README "kur ve çalıştır" temiz ortamda geçer.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-21 · Çalışma alanı kotası ve temizlik (IDE-22)
- **Sorun:** [ÖNERİ] Kota yok.
- **Değişiklik:** Kullanıcı başına kota, eski sürüm budama.
- **Kabul:** Kota aşımında net hata; silme tam temizlik.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-22 · Ekip içi paylaşım yetkisi (IDE-23)
- **Sorun:** [ÖNERİ] İzinler testli değil.
- **Değişiklik:** Salt-okunur/yorumlu paylaşım, yetki testi.
- **Kabul:** Yetkisiz kullanıcı göremez.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-23 · Proje PRD üretimi ve kullanıcı onayı
- **Sorun:** [ÖNERİ] Gereksinim belirsizse doğrudan üretim.
- **Değişiklik:** Kısa PRD ve onay adımı.
- **Kabul:** Belirsiz istekte PRD onayı istenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-24 · Mimari karar kaydı üretimi
- **Sorun:** [ÖNERİ] Üretilen projede ADR yok.
- **Değişiklik:** Kısa ADR ve mimari diyagram (Mermaid).
- **Kabul:** Projede `docs/ARCHITECTURE.md` var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-25 · Üretilen proje testleri: kapsam eşiği
- **Sorun:** [ÖNERİ] Üretilen testler yüzeysel.
- **Değişiklik:** Kapsam %60 hedefi.
- **Kabul:** Üretilen projenin kapsamı ölçülür.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-26 · Veritabanı şeması üretimi ve göç
- **Sorun:** [ÖNERİ] Projede göç yok.
- **Değişiklik:** Alembic benzeri göç.
- **Kabul:** Şema değişikliği göçle yapılır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-27 · Üretilen projede güvenlik taraması
- **Sorun:** [ÖNERİ] Bandit/npm audit yok.
- **Değişiklik:** Güvenlik taraması adımı.
- **Kabul:** Bilinen açık desenleri yakalanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-28 · Docker/compose dosyası üretimi ve doğrulama
- **Sorun:** [ÖNERİ] Dockerfile üretimi sınırlı.
- **Değişiklik:** Docker varsa derleme denemesi.
- **Kabul:** Dockerfile derlenir (varsa).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-29 · Değişiklik isteği: mevcut projeyi anlama
- **Sorun:** [ÖNERİ] Var olan projeyi değiştirme zayıf.
- **Değişiklik:** Depo haritası ve ilgili dosya seçimi.
- **Kabul:** İstek yalnız ilgili dosyaları değiştirir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-30 · Geri alınabilir değişiklik grubu
- **Sorun:** [ÖNERİ] Tek tek geri alma.
- **Değişiklik:** Değişiklik grubu geri alma.
- **Kabul:** Tek tıkla tüm grup geri alınır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-31 · Provenance: dosya→görev→ajan→model (DIST-20)
- **Sorun:** [ÖNERİ] ZIP'te her dosya kayıtlı testi yok.
- **Değişiklik:** `PROVENANCE.json` doğrulama testi.
- **Kabul:** ZIP'teki her dosya kayıtlı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-32 · Oyun şablonları: 10 tür, bot testi (GAME-02)
- **Sorun:** [ÖNERİ] Şablonlar bot testinden geçmiyor olabilir.
- **Değişiklik:** Her şablon için bot testi.
- **Kabul:** Her şablon oynanır ve bot testini geçer.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-33 · GDD ve kazan/kaybet tetiklenebilirliği (GAME-03)
- **Sorun:** [ÖNERİ] Koşullar tetiklenebilir mi denenmiyor.
- **Değişiklik:** GDD koşullarını bot doğrular.
- **Kabul:** Kazan ve kayıp koşulu tetiklenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-34 · Varlık üretimi: yer tutucu kalmaması (GAME-04)
- **Sorun:** [ÖNERİ] Görsel denetim yok.
- **Değişiklik:** Sprite üretici ve denetim.
- **Kabul:** Yer tutucu dikdörtgen kalmaz.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-35 · Oyun kabuğu: duraklat, yüksek skor, mobil kontrol (GAME-07)
- **Sorun:** [ÖNERİ] Tüm şablonlarda bot testi yok.
- **Değişiklik:** Ortak kabuk ve bot testi.
- **Kabul:** Tüm şablonlarda duraklat ve skor çalışır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-36 · Yerel three.js 3B şablon (GAME-09)
- **Sorun:** [ÖNERİ] three.js yerel değil.
- **Değişiklik:** Yerel paket ve FPS ölçümü.
- **Kabul:** 55+ FPS ve bot testi.
- **Meta:** P1 · L · Bağ: - · Durum: açık

#### FAB-37 · Oyun ses: WebAudio efektleri
- **Sorun:** [ÖNERİ] Ses basit.
- **Değişiklik:** Prosedürel efekt ve müzik.
- **Kabul:** Ses aç/kapa çalışır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-38 · Oyun dengesi: zorluk eğrisi testi
- **Sorun:** [ÖNERİ] Zorluk elle.
- **Değişiklik:** Bot beceri seviyeleri ile kazanma oranı.
- **Kabul:** Orta zorlukta bot kazanma oranı %30-70.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-39 · Çoklu dosya oyun üretimi (tek HTML dışı)
- **Sorun:** [ÖNERİ] Yalnız tek dosya.
- **Değişiklik:** Çok dosyalı yapı seçeneği.
- **Kabul:** Oyun varlıkları ayrı dosyada.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-40 · Oyun yayınlama: ZIP ve tek dosya dışa aktarma
- **Sorun:** [ÖNERİ] Paylaşım zor.
- **Değişiklik:** Tek HTML ve ZIP indirme.
- **Kabul:** Çevrimdışı açılır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-41 · Kod incelemesi ajanı kalitesi (DIST-16)
- **Sorun:** [ÖNERİ] 40 kodda recall ölçülmedi.
- **Değişiklik:** Bilerek hatalı 40 kod.
- **Kabul:** Recall ≥ %70, uydurma bulgu < %15.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-42 · Bulgu → düzeltme görevi → yeniden inceleme döngüsü
- **Sorun:** [ÖNERİ] Döngü kısmen.
- **Değişiklik:** Bulgudan görev üretimi.
- **Kabul:** Döngü e2e çalışır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-43 · Üretimde kod stili ve proje kurallarına uyum
- **Sorun:** [ÖNERİ] Kullanıcı kod stili tercihi yok.
- **Değişiklik:** Proje kural dosyası (`.editorconfig`, stil).
- **Kabul:** Üretilen kod stil kontrolünden geçer.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-44 · Hata mesajlarında Türkçe açıklama
- **Sorun:** [ÖNERİ] Araç hataları İngilizce.
- **Değişiklik:** Hata sözlüğü.
- **Kabul:** Sık 20 hata Türkçe açıklanır.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### FAB-45 · Yerel çalıştırma önizleme sunucusu izolasyon testi
- **Sorun:** [ÖNERİ] Önizleme porta bağlı.
- **Değişiklik:** Port çakışma ve temizlik.
- **Kabul:** Önizleme kapanınca port boşalır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-46 · Uzun süren derlemeler için iş kuyruğu ve ilerleme
- **Sorun:** [ÖNERİ] Derleme bloklayabilir.
- **Değişiklik:** Arka plan iş, ilerleme akışı.
- **Kabul:** Derleme sırasında arayüz akıcı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### FAB-47 · Üretilen proje için lisans dosyası
- **Sorun:** [ÖNERİ] Lisans yok.
- **Değişiklik:** Seçilebilir lisans.
- **Kabul:** ZIP'te LICENSE var.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### FAB-48 · Dil kapsamı: Java, Go, Rust, C# şablonları
- **Sorun:** [ÖNERİ] Python/JS ağırlıklı.
- **Değişiklik:** En az Go ve Java iskeleti (Docker ile).
- **Kabul:** Her biri derlenir (Docker varsa).
- **Meta:** P1 · M · Bağ: - · Durum: açık
