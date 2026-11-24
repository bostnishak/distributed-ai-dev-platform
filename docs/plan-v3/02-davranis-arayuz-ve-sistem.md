# Parça 2 — Gerçek istek başarısızlıkları, arayüz taraması ve sistem bulguları

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
