# Parça 2 — Gerçek istek başarısızlıkları, arayüz taraması ve sistem bulguları

## DAV · Gerçek sohbet isteğinde başarısız davranışlar

#### DAV-01 · talimat: fmt-02 isteği başarısız
- **Sorun:** [DOĞRULANDI: F205] `fmt-02` (talimat) gerçek sohbet isteğinde başarısız: 37 kelime (> 20). Yanıt başı: «Bulut, uzay boşluğunda yer alan ve atmosferin dışındaki ortamı kapsayan devasa bir gaz küresidir. Yerçekimi etkisiyle birlikte yıldızlar, ge».
- **Değişiklik:** Kök nedeni bul (yönlendirme, istem, araç, doğrulayıcı), düzelt ve bu isteği eval kümesine kalıcı olarak ekle.
- **Kabul:** `python scripts/audit/battery.py fmt-02` bu istek için OK verir; eval kümesinde regresyon testi var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DAV-02 · talimat: fmt-13 isteği başarısız
- **Sorun:** [DOĞRULANDI: F205] `fmt-13` (talimat) gerçek sohbet isteğinde başarısız: istenmeyen desen var: deniz. Yanıt başı: «Deniz feneri uzakta yanar, Gemi izleri sulara karışır, Rüzgar eserken gemiler durur.».
- **Değişiklik:** Kök nedeni bul (yönlendirme, istem, araç, doğrulayıcı), düzelt ve bu isteği eval kümesine kalıcı olarak ekle.
- **Kabul:** `python scripts/audit/battery.py fmt-13` bu istek için OK verir; eval kümesinde regresyon testi var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DAV-03 · kod: code-10 isteği başarısız
- **Sorun:** [DOĞRULANDI: F205] `code-10` (kod) gerçek sohbet isteğinde başarısız: koddan başka 43 kelime var. Yanıt başı: «```python for i in range(1, 11): print(i) ``` Bu kod, `range` fonksiyonunu kullanarak 1'den 10'a kadar olan sayıları sırayla ekrana yaz».
- **Değişiklik:** Kök nedeni bul (yönlendirme, istem, araç, doğrulayıcı), düzelt ve bu isteği eval kümesine kalıcı olarak ekle.
- **Kabul:** `python scripts/audit/battery.py code-10` bu istek için OK verir; eval kümesinde regresyon testi var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DAV-04 · kod: code-14 isteği başarısız
- **Sorun:** [DOĞRULANDI: F205] `code-14` (kod) gerçek sohbet isteğinde başarısız: beklenen desen yok: sözdizimi|syntax|eksik|operand|ikinci|tamam. Yanıt başı: «Bu kodda hata var. Fonksiyonunun sonuna bir değer döndürmeyi unuttuğunuz için hata veriyor. Örneğin, `return x + 5` veya başka bir değer dön».
- **Değişiklik:** Kök nedeni bul (yönlendirme, istem, araç, doğrulayıcı), düzelt ve bu isteği eval kümesine kalıcı olarak ekle.
- **Kabul:** `python scripts/audit/battery.py code-14` bu istek için OK verir; eval kümesinde regresyon testi var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DAV-05 · kod: code-19 isteği başarısız
- **Sorun:** [DOĞRULANDI: F205] `code-19` (kod) gerçek sohbet isteğinde başarısız: Temp\tmpq4czqr71\t.py", line 21, in <module> assert count_vowels('merhaba')==3 and count_vowels('Ã¶ÄŸrenci')==3 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ AssertionError. Yanıt başı: «Tabii ki, audit! İşte `count_vowels(s)` fonksiyonu: ```python def count_vowels(s): """ Verilen metindeki sesli harf sayısını döndür».
- **Değişiklik:** Kök nedeni bul (yönlendirme, istem, araç, doğrulayıcı), düzelt ve bu isteği eval kümesine kalıcı olarak ekle.
- **Kabul:** `python scripts/audit/battery.py code-19` bu istek için OK verir; eval kümesinde regresyon testi var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DAV-06 · dosya: file-04 isteği başarısız
- **Sorun:** [DOĞRULANDI: F205] `file-04` (dosya) gerçek sohbet isteğinde başarısız: soru yalnızca bütçeyi soruyordu ama yanıt istenmeyen 'Deterministik Dosya Denetim Raporu' bloğuyla başlıyor. Yanıt başı: «### Deterministik Dosya Denetim Raporu (not.txt) - **Durum:** Temiz (0 kritik/yuksek hata) | **Boyut:** 65 bayt - Sozdizimi, JSON/HTML yapis».
- **Değişiklik:** Kök nedeni bul (yönlendirme, istem, araç, doğrulayıcı), düzelt ve bu isteği eval kümesine kalıcı olarak ekle.
- **Kabul:** `python scripts/audit/battery.py file-04` bu istek için OK verir; eval kümesinde regresyon testi var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DAV-07 · üretim: make-doc isteği başarısız
- **Sorun:** [DOĞRULANDI: F205] `make-doc` (üretim) gerçek sohbet isteğinde başarısız: docx çıktısı yok. Yanıt başı: «Audit, aşağıda yer alan motivasyon mektubunu bulabilirsiniz. Bu metin, genel iş başvuruları için profesyonel bir şablondur; parantez içindek».
- **Değişiklik:** Kök nedeni bul (yönlendirme, istem, araç, doğrulayıcı), düzelt ve bu isteği eval kümesine kalıcı olarak ekle.
- **Kabul:** `python scripts/audit/battery.py make-doc` bu istek için OK verir; eval kümesinde regresyon testi var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DAV-08 · üretim: make-project isteği başarısız
- **Sorun:** [DOĞRULANDI: F205] `make-project` (üretim) gerçek sohbet isteğinde başarısız: hata: {'type': 'error', 'content': "[WinError 183] Halen varolan bir dosya oluşturulamaz: 'C:\\\\Users\\\\bosta\\\\OneDrive\\\\Desktop\\\\projects\\\\Okul projeleri\\\\Distributed AI Software Development Platform CM6453\\\\.audit_tmp\\\\data\\\\workspaces\\\\not-kaydetme-uygulamasi-1124050347\\\\app'"}. Yanıt başı: «Mimari plan hazırlanıyor (qwen2.5-coder:7b)... ### Proje Planı: **Not Kaydetme Uygulaması** (16 dosya) - `main.py` - Uygulamanın ana giriş».
- **Değişiklik:** Kök nedeni bul (yönlendirme, istem, araç, doğrulayıcı), düzelt ve bu isteği eval kümesine kalıcı olarak ekle.
- **Kabul:** `python scripts/audit/battery.py make-project` bu istek için OK verir; eval kümesinde regresyon testi var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DAV-09 · üretim: make-research isteği başarısız
- **Sorun:** [DOĞRULANDI: F205] `make-research` (üretim) gerçek sohbet isteğinde başarısız: kaynak/atıf yok. Yanıt başı: «Kuantum bilgisayarları konu alan kapsamlı ve kanıt dayalı bir özet aşağıdadır: **Temel Prensip:** Klasik bilgisayarlar, bilgiyi 0 veya 1 de».
- **Değişiklik:** Kök nedeni bul (yönlendirme, istem, araç, doğrulayıcı), düzelt ve bu isteği eval kümesine kalıcı olarak ekle.
- **Kabul:** `python scripts/audit/battery.py make-research` bu istek için OK verir; eval kümesinde regresyon testi var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DAV-10 · üretim: make-chart isteği başarısız
- **Sorun:** [DOĞRULANDI: F205] `make-chart` (üretim) gerçek sohbet isteğinde başarısız: grafik çıktısı yok. Yanıt başı: «Verilen verilere dayanarak aşağıda Python kütüphanesi (matplotlib) kullanılarak oluşturulmuş çubuk grafiği kodu yer almaktadır. Bu kodu çalı».
- **Değişiklik:** Kök nedeni bul (yönlendirme, istem, araç, doğrulayıcı), düzelt ve bu isteği eval kümesine kalıcı olarak ekle.
- **Kabul:** `python scripts/audit/battery.py make-chart` bu istek için OK verir; eval kümesinde regresyon testi var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DAV-11 · üretim: make-image isteği başarısız
- **Sorun:** [DOĞRULANDI: F205] `make-image` (üretim) gerçek sohbet isteğinde başarısız: görsel üretilmedi. Yanıt başı: «Deniz kıyısında, gün batımı sahnelerini betimleyen detaylı bir görsel taslak aşağıda sunulmaktadır: ```python import matplotlib.pyplot as p».
- **Değişiklik:** Kök nedeni bul (yönlendirme, istem, araç, doğrulayıcı), düzelt ve bu isteği eval kümesine kalıcı olarak ekle.
- **Kabul:** `python scripts/audit/battery.py make-image` bu istek için OK verir; eval kümesinde regresyon testi var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DAV-12 · araç: tool-03 isteği başarısız
- **Sorun:** [DOĞRULANDI: F205] `tool-03` (araç) gerçek sohbet isteğinde başarısız: beklenen desen yok: 83[ .,]?810[ .,]?205. Yanıt başı: «12345 ile 6789'un çarpımı aşağıdadır: ```python sonuc = 12345 * 6789 print(sonuc) # Çıkan sonuç: 83800205 ```».
- **Değişiklik:** Kök nedeni bul (yönlendirme, istem, araç, doğrulayıcı), düzelt ve bu isteği eval kümesine kalıcı olarak ekle.
- **Kabul:** `python scripts/audit/battery.py tool-03` bu istek için OK verir; eval kümesinde regresyon testi var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DAV-13 · araç: tool-07 isteği başarısız
- **Sorun:** [DOĞRULANDI: F205] `tool-07` (araç) gerçek sohbet isteğinde başarısız: beklenen desen yok: 31[ .,]?556[ .,]?926. Yanıt başı: «Verilen süre bir yılı ifade eder ve toplam saniye sayısını hesaplamak için her zaman birimini saniyeye çevirmemiz gerekir. Hesaplama adımlar».
- **Değişiklik:** Kök nedeni bul (yönlendirme, istem, araç, doğrulayıcı), düzelt ve bu isteği eval kümesine kalıcı olarak ekle.
- **Kabul:** `python scripts/audit/battery.py tool-07` bu istek için OK verir; eval kümesinde regresyon testi var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

## ARY · Tarayıcı taraması: arayüz ve erişilebilirlik

#### ARY-01 · Tüm sayfaların başlığı aynı
- **Sorun:** [DOĞRULANDI: F206] 8 rotanın tamamında `document.title` 'Dağıtık YZ Yazılım Geliştirme Platformu'; ekran okuyucu ve sekme geçmişi sayfayı ayıramıyor.
- **Değişiklik:** Rota başına başlık ve sayfa değişiminde duyuru.
- **Kabul:** Her rotada başlık farklı ve anlamlı (e2e).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### ARY-02 · 6 sayfada birden çok <h1>
- **Sorun:** [DOĞRULANDI: F206] #/new, #/projects, #/agents, #/studios, #/artifacts, #/files rotalarında 2 adet h1 var.
- **Değişiklik:** Kabuk başlığını h1 olmaktan çıkar, sayfa başlığı tek h1 olsun.
- **Kabul:** Her sayfada tam 1 h1 (axe).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### ARY-03 · Stüdyolar sayfasında 341 etiketsiz form kontrolü
- **Sorun:** [DOĞRULANDI: F206] #/studios sayfasında etiketi (label/aria-label) olmayan 341 input/select/textarea var.
- **Değişiklik:** `hub.js` form üreticisi her kontrole `label for` veya `aria-label` versin.
- **Kabul:** axe `label` kuralı 0 ihlal.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### ARY-04 · Asistan ana mesaj kutusunun erişilebilir adı yok
- **Sorun:** [DOĞRULANDI: F206] `#promptInput` textarea'sının label/aria-label'ı yok; ekran okuyucu 'düzenleme alanı' diyor.
- **Değişiklik:** aria-label ekle ve gizli label kullan.
- **Kabul:** Kutu 'Mesajınızı yazın' adıyla duyurulur.
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### ARY-05 · Kabukta 2 etiketsiz dosya girdisi
- **Sorun:** [DOĞRULANDI: F206] Tüm sayfalarda yükleme için 2 gizli `input[type=file]` etiketsiz.
- **Değişiklik:** aria-label ekle veya düğmeye bağla.
- **Kabul:** axe `label` ihlali 0.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### ARY-06 · Dar ekranda küçük dokunma hedefleri
- **Sorun:** [DOĞRULANDI: F206] 375px'te her sayfada 2–11 öğe 32px'den küçük (Stüdyolar: 11, Asistan: 8).
- **Değişiklik:** Dokunma hedeflerini ≥ 40px yap.
- **Kabul:** Mobil denetimde 32px altı hedef 0.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### ARY-07 · Sayfa değişiminde odak yönetimi belirsiz
- **Sorun:** [DOĞRULANDI: F206] Hash rotası değişince odak ana içeriğe taşınmıyor.
- **Değişiklik:** Rota değişince `main` odaklansın ve başlık duyurulsun.
- **Kabul:** Klavye kullanıcısı rota değişiminde bağlamını kaybetmez (e2e).
- **Meta:** P2 · S · Bağ: - · Durum: açık

## ALT · Doğrulanmış sistem ve altyapı bulguları

#### ALT-01 · OCR motoru kurulu değil
- **Sorun:** [DOĞRULANDI: F207] `/api/assistant/config`: ocr.available=false ('Kurulu değil (pip install pytesseract)'); taranmış belgeler okunamıyor.
- **Değişiklik:** Tesseract/PaddleOCR'ı kurulum betiğine ve sağlık sihirbazına ekle, kurulmamışsa yükleme anında uyar.
- **Kabul:** Taranmış PDF örneği metne çevrilir; OCR yokken kullanıcıya eyleme dönük mesaj çıkar.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### ALT-02 · Web araması yapılandırılmamış
- **Sorun:** [DOĞRULANDI: F207] `/api/ux/health-wizard` 4/6: web_search ok=false; SEARXNG_URL tanımlı değil, araştırma internetsiz çalışıyor.
- **Değişiklik:** SearXNG'yi kurulum betiğine dahil et, varsayılan açık yap, kapalıysa yanıtta tarih/kaynak uyarısı.
- **Kabul:** Güncel bir soruda kaynaklı yanıt gelir; arama yokken uyarı çıkar.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### ALT-03 · Hiç ajan bağlı değil durumunun yönlendirmesi
- **Sorun:** [DOĞRULANDI: F207] Sağlık sihirbazı: agents ok=false; sohbet tek düğümde çalışıyor ama kullanıcıya dağıtık özelliğin kapalı olduğu yanıtta söylenmiyor.
- **Değişiklik:** Yanıt meta verisine 'yerel yürütme' rozeti ve ajan ekleme önerisi ekle.
- **Kabul:** Ajan yokken yanıtta nedeni gösteren rozet var.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### ALT-04 · Frontend araç zinciri yok
- **Sorun:** [DOĞRULANDI: F207] frontend/package.json `lint`, `typecheck`, `build`, `e2e` betikleri tanımlı ama devDependencies, eslint/tsconfig/vite/playwright yapılandırması ve node_modules yok; betikler çalışmaz.
- **Değişiklik:** Bağımlılıkları ve yapılandırmayı ekle, CI'da çalıştır.
- **Kabul:** `npm run lint`, `typecheck`, `e2e` temiz klonda çalışır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALT-05 · `npm test` yalnız 1 test dosyasını koşuyor
- **Sorun:** [DOĞRULANDI: F207] package.json `test` betiği yalnız `ui_modules.test.mjs`; `message_tools` ve `undefined_names` testleri çalışmıyor.
- **Değişiklik:** Betiği `node --test tests/` yap.
- **Kabul:** `npm test` 3 dosyanın tamamını koşar.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### ALT-06 · Kapsam aracı dev bağımlılığı değil
- **Sorun:** [DOĞRULANDI: F207] `requirements-dev.txt` yalnız pytest ve ruff; CI `pytest-cov`'u ad hoc kuruyor, yerelde kapsam ölçülemiyor.
- **Değişiklik:** `pytest-cov` ve `diff-cover`'ı dev bağımlılığı yap.
- **Kabul:** Yerelde `pytest --cov` çalışır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### ALT-07 · Oturumsuz kullanıcı profili oluşturma/üzerine yazma (IDOR)
- **Sorun:** [DOĞRULANDI: F207] `PUT /api/user/zzz-nonexistent/profile` oturumsuz 200 verip profil oluşturdu; `GET /api/user/profiles` tüm kullanıcı kimliklerini listeledi.
- **Değişiklik:** Kimliği oturumdan türet, liste rotasını yöneticiye kısıtla.
- **Kabul:** Oturumsuz çağrı 401; başka kimliğe yazma 403 (otomatik üretilmiş test).
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### ALT-08 · Oturumsuz 8 /api/user/* rotası veri döndürüyor
- **Sorun:** [DOĞRULANDI: F207] profile, stats, memories, conversations, history/search, personalization-preview rotaları oturumsuz 200 verdi.
- **Değişiklik:** Hepsine oturum ve sahiplik bağımlılığı ekle.
- **Kabul:** Her rota için A→B sızıntı testi 404/403.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### ALT-09 · enterprise-status yerel dosya yolu sızdırıyor
- **Sorun:** [DOĞRULANDI: F207] `GET /api/assistant/enterprise-status` yanıtı `llmops.dpo_file` alanında tam yerel yol (C:\Users\...) içeriyor.
- **Değişiklik:** Yolları göreli yap veya yöneticiye göster.
- **Kabul:** Yanıtta mutlak yol yok.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### ALT-10 · GET /api/gateway/models 3 sn sürüyor
- **Sorun:** [DOĞRULANDI: F207] İlk çağrı 3.1 sn; her açılışta model listesi arayüzü yavaşlatıyor.
- **Değişiklik:** Sonucu önbellekle ve arka planda yenile.
- **Kabul:** Önbellekli çağrı < 100 ms.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### ALT-11 · İki sanal ortam (`venv` ve `.venv`) master içinde
- **Sorun:** [DOĞRULANDI: F207] `master/venv` ve `master/.venv` birlikte var; hangi Python'un kullanıldığı belirsiz (sunucu sistem Python'uyla başladı).
- **Değişiklik:** Tek ortam kullan, `.gitignore` ve betikler aynı yolu göstersin.
- **Kabul:** Tek sanal ortam; betikler ve launch.json aynısını kullanır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### ALT-12 · Plan v2 UX-05: prefers-reduced-motion yok
- **Sorun:** [DOĞRULANDI: F207] Plan 'done' dedi ama CSS/JS'de `prefers-reduced-motion` eşleşmesi yok.
- **Değişiklik:** Medya sorgusu ve ayar ekle, testle sabitle.
- **Kabul:** Azaltılmış hareketle animasyon yok (test).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALT-13 · Plan v2 IDE-10: Monaco yerel paketi yok
- **Sorun:** [DOĞRULANDI: F207] Plan 'done' dedi ama `static/vendor` yok, Monaco/CodeMirror eşleşmesi yok.
- **Değişiklik:** Çevrimdışı Monaco paketi ekle.
- **Kabul:** IDE Monaco ile açılır (e2e).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALT-14 · Plan v2 SEC-04: rol matrisi route'lara bağlı değil
- **Sorun:** [DOĞRULANDI: F207] `auth/policy.py` bu oturumda yazıldı; route bağımlılığı olarak uygulanmıyor.
- **Değişiklik:** Router düzeyinde `require_role` uygula.
- **Kabul:** Her mutasyon rotası rol testinden geçer.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALT-15 · Plan v2 OPS-09: pytest işaretleri eksik
- **Sorun:** [DOĞRULANDI: F207] `pytest.ini` yalnız `security` işaretini tanımlıyor; unit/contract/integration/e2e/slow yok.
- **Değişiklik:** Altı işareti tanımla, her teste ata.
- **Kabul:** İşaretsiz test CI'ı kırar; hızlı küme < 30 sn.
- **Meta:** P1 · M · Bağ: - · Durum: açık
