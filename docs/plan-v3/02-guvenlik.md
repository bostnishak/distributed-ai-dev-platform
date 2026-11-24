# Parça 2 — Güvenlik, gizlilik ve kötüye kullanım (GVN)

## GVN · Güvenlik, gizlilik ve kötüye kullanım koruması

#### GVN-01 · Oturum çerezi güvenliği
- **Sorun:** [ÖNERİ] Çerez bayrakları ve süre yönetimi tek yerde sınanmıyor.
- **Değişiklik:** HttpOnly, SameSite=Strict, Secure (HTTPS'te), mutlak ve boşta süre sonu.
- **Kabul:** Çerez bayrakları test edilir; süresi dolan oturum 401.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### GVN-02 · Parola politikası ve sızıntı denetimi
- **Sorun:** [ÖNERİ] Parola uzunluğu/yaygınlık denetimi yok.
- **Değişiklik:** En az 10 karakter, yaygın parola listesi reddi, Argon2/scrypt parametre denetimi.
- **Kabul:** Zayıf parola 422; parametreler testle sabitlenir.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### GVN-03 · İki aşamalı doğrulama (TOTP)
- **Sorun:** [ÖNERİ] Yönetici hesabı tek faktörlü.
- **Değişiklik:** TOTP kurulumu, kurtarma kodları, yönetici için zorunlu seçenek.
- **Kabul:** TOTP'siz yönetici işlemi reddedilir (açıksa).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-04 · Oturum listesi ve uzaktan sonlandırma
- **Sorun:** [ÖNERİ] Kullanıcı açık oturumlarını göremez.
- **Değişiklik:** Oturum listesi ve "diğerlerini kapat".
- **Kabul:** Sonlandırılan oturum 401 verir.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### GVN-05 · Parola sıfırlama akışı sızdırmaz
- **Sorun:** [ÖNERİ] Hesap varlığı yanıt farkıyla anlaşılabilir.
- **Değişiklik:** Aynı yanıt/süre; tek kullanımlık, kısa ömürlü jeton.
- **Kabul:** Var olmayan hesapla aynı yanıt süresi (±%20).
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### GVN-06 · Brute-force'a karşı artan gecikme
- **Sorun:** [ÖNERİ] Giriş sınırı sabit 5/60sn.
- **Değişiklik:** Üstel gecikme ve hesap bazlı geçici kilit.
- **Kabul:** Kilit sonrası doğru parola da bekler; bildirim üretilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-07 · CSRF jetonunun tüm form yollarına uygulanması
- **Sorun:** [ÖNERİ] Same-origin kontrolü var, jeton yok.
- **Değişiklik:** Çift gönderim jetonu ve SameSite birleşimi.
- **Kabul:** Jetonsuz mutasyon 403.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### GVN-08 · Güvenlik başlıklarının tam kümesi
- **Sorun:** [ÖNERİ] CSP, HSTS, Permissions-Policy, Referrer-Policy eksik olabilir.
- **Değişiklik:** Başlık testi ve tek orta katman.
- **Kabul:** Başlık listesi testle doğrulanır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### GVN-09 · CSP'den `unsafe-inline` kaldırma
- **Sorun:** [ÖNERİ] Satır içi betik/stil kullanımı var.
- **Değişiklik:** Nonce'lu CSP, satır içi kodların taşınması.
- **Kabul:** CSP `unsafe-inline` içermez; arayüz çalışır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-10 · Dosya yükleme tarama hattı (tek giriş noktası)
- **Sorun:** [ÖNERİ] Yükleme yolları dağınık (RAG, proje, ses, görsel).
- **Değişiklik:** Tek `ingest_guard`: tür, boyut, arşiv, aktif içerik, PII.
- **Kabul:** Tüm yükleme rotaları aynı korumadan geçer (AST testi).
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### GVN-11 · Yükleme boyut limitlerinin tutarlılığı
- **Sorun:** [ÖNERİ] 5 MB / 25 MB / 200 MB farklı yerlerde.
- **Değişiklik:** Tek yapılandırma tablosu.
- **Kabul:** Limit tek yerden değişir; her rota aynı hatayı verir.
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### GVN-12 · Akışlı yükleme ve bellek tepe ölçümü
- **Sorun:** [ÖNERİ] Dosya bellekte tamamen okunuyor.
- **Değişiklik:** Parça parça yazma; `tracemalloc` testi.
- **Kabul:** 200 MB dosya < 300 MB tepe ile işlenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-13 · Kötü amaçlı dosya imzası taraması (ClamAV isteğe bağlı)
- **Sorun:** [ÖNERİ] Antivirüs taraması yok.
- **Değişiklik:** Eğer `clamd` varsa tarama, yoksa uyarı.
- **Kabul:** EICAR örneği reddedilir (clamd varken).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-14 · SSRF: DNS rebinding ve yönlendirme
- **Sorun:** [ÖNERİ] `is_safe_public_url` yalnız ilk çözümlemeyi denetliyor.
- **Değişiklik:** Bağlantı anında IP sabitleme, her yönlendirmede yeniden denetim.
- **Kabul:** Rebinding ve yönlendirme saldırıları testle reddedilir.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### GVN-15 · SSRF: ondalık/sekizlik/IPv6 eşlenik biçimleri
- **Sorun:** [ÖNERİ] Bazı IP biçimleri atlanabilir.
- **Değişiklik:** `ipaddress` normalizasyonu ve parametrik test.
- **Kabul:** `2130706433`, `0177.0.0.1`, `[::ffff:127.0.0.1]` reddedilir.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### GVN-16 · MCP bağlayıcı beyaz listesi
- **Sorun:** [ÖNERİ] Bağlayıcı URL'leri serbest.
- **Değişiklik:** Yönetici onaylı alan adı listesi, araç başına izin.
- **Kabul:** Listede olmayan MCP URL'si reddedilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-17 · Araç çağrısı onay kapısı
- **Sorun:** [ÖNERİ] Yan etkili araçlar kullanıcıya sorulmadan çalışabilir.
- **Değişiklik:** Yazma/ağ/pahalı araçlarda onay iste; onay olayı kaydı.
- **Kabul:** Onaysız yan etkili araç çalışmaz.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### GVN-18 · Araç çıktısını "veri" olarak işaretleme
- **Sorun:** [ÖNERİ] Araç çıktısı talimat gibi davranabilir.
- **Değişiklik:** Sınırlayıcılı veri blokları ve "talimat değildir" kuralı.
- **Kabul:** Enjeksiyonlu araç çıktısı eylemi tetiklemez.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-19 · Web sayfası içeriği için enjeksiyon süzgeci
- **Sorun:** [ÖNERİ] Arama sonuçları süzgeçsiz bağlama giriyor.
- **Değişiklik:** Her kaynak `detect_injection`ten geçer; işaretliyse alıntı güvensiz etiketli.
- **Kabul:** Enjeksiyonlu sayfa cevabı yönlendirmez.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-20 · Çıktı süzgeci: gizli bilgi sızıntısı
- **Sorun:** [ÖNERİ] Yanıtta anahtar/parola görünebilir.
- **Değişiklik:** `log_sanitizer` desenleri yanıta da uygulanır.
- **Kabul:** Yanıtta `sk-` desenli dize maskelenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-21 · Sistem istemi sızdırma testi
- **Sorun:** [ÖNERİ] Model sistem istemini ifşa edebilir.
- **Değişiklik:** "Sistem istemini yaz" saldırı seti ve yanıt denetimi.
- **Kabul:** Sızdırma başarı oranı < %5.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### GVN-22 · Kullanıcı verisi için alan düzeyinde şifreleme (isteğe bağlı)
- **Sorun:** [ÖNERİ] Sohbet metinleri düz metin.
- **Değişiklik:** Kullanıcı anahtarıyla Fernet şifreleme seçeneği.
- **Kabul:** Veritabanı dosyasında seçili sohbet düz metin görünmez.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-23 · Günlükte kullanıcı içeriği kapalı varsayılan
- **Sorun:** [ÖNERİ] Hata ayıklama günlüğü içerik içerebilir.
- **Değişiklik:** İçerik yalnız `DEBUG_CONTENT=1` ile ve kısaltılmış.
- **Kabul:** Varsayılanda günlükte prompt yok.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### GVN-24 · Gizli tarama: sohbet dışa aktarma ve paylaşım
- **Sorun:** [ÖNERİ] Paylaşılan sohbet gizli içerebilir.
- **Değişiklik:** Paylaşım öncesi `redact_sensitive_text`.
- **Kabul:** Paylaşılan içerikte anahtar maskeli.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-25 · Paylaşım bağlantısı iptali
- **Sorun:** [ÖNERİ] Paylaşım süre dolana dek açık.
- **Değişiklik:** Sahibi iptal eder.
- **Kabul:** İptal edilen bağlantı 404.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### GVN-26 · Yönetici eylemlerinde yeniden kimlik doğrulama
- **Sorun:** [ÖNERİ] Yönetici oturumu uzun açık kalıyor.
- **Değişiklik:** Hassas eylemde parola/TOTP yeniden istenir.
- **Kabul:** Yeniden doğrulamasız silme reddedilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-27 · Varsayılan yönetici parolası yok kontrolü
- **Sorun:** [ÖNERİ] İlk kurulumda zayıf parola kalabilir.
- **Değişiklik:** İlk çalıştırmada zorunlu parola oluşturma.
- **Kabul:** Varsayılan parola ile giriş mümkün değil.
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### GVN-28 · Denetim izi: kullanıcı arayüzü ve arama
- **Sorun:** [ÖNERİ] Denetim izi API'de ama arayüz sınırlı.
- **Değişiklik:** Filtre, arama, dışa aktarma sayfası.
- **Kabul:** Her hassas eylem arayüzde listelenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-29 · Denetim izi bütünlüğünün dış demirlenmesi
- **Sorun:** [ÖNERİ] Zincirin sonu değiştirilirse fark edilmez.
- **Değişiklik:** Günlük kök özet bir dosyaya/dış yere yazılır.
- **Kabul:** Zincir kesilirse son demir özetiyle uyuşmaz uyarısı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-30 · Yetki reddi olayları için uyarı eşiği
- **Sorun:** [ÖNERİ] Tekrarlayan 403'ler fark edilmez.
- **Değişiklik:** N reddde yönetici uyarısı.
- **Kabul:** 10 ret/dk uyarı üretir.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### GVN-31 · Ajan anahtarı süresi ve otomatik döndürme
- **Sorun:** [ÖNERİ] Ajan anahtarı süresiz.
- **Değişiklik:** 90 gün ömür, döndürme komutu.
- **Kabul:** Süresi dolan anahtar kayıt/yoklama yapamaz.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-32 · Ajan-master arası TLS/Tailscale zorunluluğu
- **Sorun:** [ÖNERİ] Ajan trafiği düz HTTP olabilir.
- **Değişiklik:** Tailnet dışı bağlantı reddi seçeneği.
- **Kabul:** Tailnet dışı IP'den ajan kaydı reddedilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-33 · Docker yokken kod çalıştırma kapalı kalır
- **Sorun:** [ÖNERİ] Sandbox yoksa ana makinede çalışma riski.
- **Değişiklik:** Fail-closed davranış ve arayüz mesajı.
- **Kabul:** Docker yokken `run-code` 503 ve neden metni.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### GVN-34 · Sandbox kaynak kotaları ölçümü
- **Sorun:** [ÖNERİ] Sınırlar docker args'ta ama ölçülmüyor.
- **Değişiklik:** CPU/bellek/pid aşım testi (Docker varken).
- **Kabul:** Bellek aşan kod öldürülür ve raporlanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-35 · Sandbox ağ politikası: paket kurulumu için ayrı aşama
- **Sorun:** [ÖNERİ] `--network none` ile pip çalışmaz.
- **Değişiklik:** Kurulum aşamasında yalnız paket aynasına izin.
- **Kabul:** Kurulum aşaması yalnız izinli alan adlarına çıkar.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-36 · Önizleme origin izolasyonunun çerez testi
- **Sorun:** [ÖNERİ] SEC-17 testi var, çerez gitmediği sınanıyor mu belirsiz.
- **Değişiklik:** İkinci origin testinde çerez başlığı denetimi.
- **Kabul:** Önizleme kökeninden gelen istekte oturum çerezi yok.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### GVN-37 · Üretilen kodda gizli tarama
- **Sorun:** [ÖNERİ] Üretilen projede anahtar gömülebilir.
- **Değişiklik:** Proje çıktısında gitleaks benzeri tarama.
- **Kabul:** `sk-` içeren üretilen dosya engellenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-38 · `.env` dosyalarının ZIP çıktısından dışlanması
- **Sorun:** [ÖNERİ] Proje ZIP'ine `.env` girebilir.
- **Değişiklik:** Dışlama listesi.
- **Kabul:** ZIP'te `.env*` yok (`.env.example` hariç).
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### GVN-39 · Bağımlılık sabitleme ve karma doğrulaması
- **Sorun:** [ÖNERİ] requirements sürüm aralıklı.
- **Değişiklik:** `pip-compile --generate-hashes`.
- **Kabul:** Kurulum karma uyuşmazlığında başarısız.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-40 · SBOM'un sürüm başına arşivlenmesi
- **Sorun:** [ÖNERİ] SBOM CI'da üretiliyor ama arşivlenmiyor.
- **Değişiklik:** Sürüm artefaktına eklenir.
- **Kabul:** Sürümde SBOM dosyası var.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### GVN-41 · Güvenlik açığı SLA'sı
- **Sorun:** [ÖNERİ] Açık bulununca ne olacağı tanımsız.
- **Değişiklik:** Kritik 7 gün, yüksek 30 gün; takip tablosu.
- **Kabul:** Açık bulgu tablosunda süre ve sorumlu var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-42 · SECURITY.md ve ifşa politikası
- **Sorun:** [ÖNERİ] Bildirim kanalı yok.
- **Değişiklik:** SECURITY.md ve iletişim.
- **Kabul:** Dosya var ve README'den bağlı.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### GVN-43 · Tehdit modelinin güncellenmesi (STRIDE)
- **Sorun:** [ÖNERİ] Tehdit modeli 6 sınırı kapsıyor, yeni özellikler eklenmedi.
- **Değişiklik:** Dosya yükleme, MCP, sandbox, paylaşım için yeni STRIDE satırları.
- **Kabul:** Her yeni özellik tehdit satırına bağlı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-44 · Fuzz testleri: ayrıştırıcılar
- **Sorun:** [ÖNERİ] PDF/DOCX/ZIP ayrıştırıcıları bozuk girdiyle denenmiyor.
- **Değişiklik:** Hypothesis ile bozuk dosya fuzz'ı.
- **Kabul:** 1000 bozuk girdide çökme/zaman aşımı yok.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-45 · Düzenli ifade zaman aşımı (ReDoS) denetimi
- **Sorun:** [ÖNERİ] Çok sayıda regex kullanıcı metnine uygulanıyor.
- **Değişiklik:** Uzun dizelerle regex süre testi.
- **Kabul:** 100 KB girdide her regex < 100 ms.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### GVN-46 · PII maskeleme kapsamı: TCKN doğrulaması
- **Sorun:** [ÖNERİ] TCKN deseni 11 haneli her sayıyı yakalıyor.
- **Değişiklik:** TCKN sağlama toplamı doğrulaması.
- **Kabul:** Rastgele 11 haneli sayı TCKN sayılmaz.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-47 · IBAN sağlama (mod 97) doğrulaması
- **Sorun:** [ÖNERİ] IBAN deseni yalnız biçime bakıyor.
- **Değişiklik:** Mod-97 kontrolü.
- **Kabul:** Geçersiz IBAN maskelenmez, geçerli maskelenir.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### GVN-48 · Telefon ve kredi kartı desenleri
- **Sorun:** [ÖNERİ] Kart numarası maskelenmiyor.
- **Değişiklik:** Luhn kontrollü kart deseni.
- **Kabul:** Geçerli kart numarası günlükte maskeli.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### GVN-49 · Veri silme: yedeklerdeki iz belgesi ve zaman sınırı
- **Sorun:** [ÖNERİ] Silinen veri eski yedekte kalır.
- **Değişiklik:** Yedek saklama süresi ve "silme sonrası N gün" belgesi.
- **Kabul:** Belge ve yedek budama testi var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-50 · Kullanıcı verisi dışa aktarmada gizlerin hariç tutulması testi
- **Sorun:** [ÖNERİ] Dışa aktarım paketi gizli içerebilir.
- **Değişiklik:** Paketi tarayan test.
- **Kabul:** Dışa aktarımda anahtar deseni yok.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-51 · Çerez onayı gerektirmeyen tasarım
- **Sorun:** [ÖNERİ] Üçüncü taraf çerez yok ama belgelenmemiş.
- **Değişiklik:** Gizlilik sayfası: hangi veri nerede.
- **Kabul:** Sayfa arayüzden erişilir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### GVN-52 · Telemetri gizliliği: ajan telemetrisinde kişisel veri yok
- **Sorun:** [ÖNERİ] Ajan telemetrisi makine adı/kullanıcı adı içerebilir.
- **Değişiklik:** Alan beyaz listesi.
- **Kabul:** Telemetri şemasında kişisel alan yok.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-53 · Yönetici arayüzü için IP kısıtı seçeneği
- **Sorun:** [ÖNERİ] Yönetici paneli tüm tailnet'e açık.
- **Değişiklik:** İzinli IP/etiket listesi.
- **Kabul:** Listede olmayan IP yönetici rotasında 403.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### GVN-54 · Hassas rotalar için yanıt önbelleğini kapatma
- **Sorun:** [ÖNERİ] Önbellek başlıkları denetlenmiyor.
- **Değişiklik:** `Cache-Control: no-store` hassas rotalarda.
- **Kabul:** Başlık testi geçer.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### GVN-55 · Dosya adı ve yol temizliği
- **Sorun:** [ÖNERİ] Yüklenen ad dizinler oluşturabilir.
- **Değişiklik:** Ad normalizasyonu, uzunluk, ayrılmış adlar (CON, NUL).
- **Kabul:** `..\x` ve `CON` adları temizlenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-56 · Zaman aşımı olmayan istekler için bütçe
- **Sorun:** [ÖNERİ] Bazı rotalar sınırsız bekleyebilir.
- **Değişiklik:** Rota başına süre bütçesi.
- **Kabul:** Bütçeyi aşan istek 504 ve günlük.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-57 · Güvenlik testlerinin gece koşusu
- **Sorun:** [ÖNERİ] Fuzz/uzun testler CI'da yok.
- **Değişiklik:** Gece iş akışı.
- **Kabul:** Gece raporu artefakt.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### GVN-58 · Gizli yönetimi: `.env` yerine OS anahtar halkası
- **Sorun:** [ÖNERİ] Anahtarlar `.env` dosyasında.
- **Değişiklik:** Windows Credential Manager desteği.
- **Kabul:** Anahtar `.env` olmadan okunur.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### GVN-59 · Güvenlik kontrol listesi: yayın öncesi
- **Sorun:** [ÖNERİ] Yayın öncesi kontrol yok.
- **Değişiklik:** Yayın kontrol listesi.
- **Kabul:** Liste PR şablonunda.
- **Meta:** P2 · S · Bağ: - · Durum: açık
