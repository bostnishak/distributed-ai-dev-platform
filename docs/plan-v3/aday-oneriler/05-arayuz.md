# Parça 5 — Arayüz, erişilebilirlik ve deneyim (ARY)

## ARY · Arayüz, tasarım, erişilebilirlik ve kullanıcı deneyimi

#### ARY-01 · Tüm sayfalar için "Failed to fetch" tarayıcı taraması
- **Sorun:** [ÖNERİ] Kişisel panelde toplu "Failed to fetch" görüldü; her sayfa elle denenmedi.
- **Değişiklik:** Playwright ile tüm rota ve panel gezinmesi, ağ hatası ve konsol hatası denetimi.
- **Kabul:** Tüm sayfalarda ağ hatası ve konsol hatası 0.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### ARY-02 · Tanımsız ad koruması tüm modüllere
- **Sorun:** [ÖNERİ] Eksik import tek modülde yakalandı.
- **Değişiklik:** `undefined_names` testi tüm `static/js` için ve `eslint no-undef`.
- **Kabul:** Yeni modül eksik import ile CI'ı kırar.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### ARY-03 · Arayüz–API sözleşme testi (DEF-17)
- **Sorun:** [ÖNERİ] Alan yeniden adlandırması arayüzü kırar.
- **Değişiklik:** OpenAPI'den tip üretimi ve arayüz çağrı denetimi.
- **Kabul:** Alan adı değişince derleme/test kırılır.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### ARY-04 · Arayüz bileşen kitaplığı ve renk jetonları (UX-04)
- **Sorun:** [ÖNERİ] Stil dağınık, kontrast otomatik denetlenmiyor.
- **Değişiklik:** Üç temada kontrast ≥ AA otomatik test.
- **Kabul:** Tüm bileşen çiftlerinde AA.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-05 · Yüksek kontrast teması
- **Sorun:** [ÖNERİ] Yalnız aydınlık/karanlık.
- **Değişiklik:** Üçüncü tema ve ayar.
- **Kabul:** Yüksek kontrast WCAG AAA metin.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-06 · Klavye ile tam gezinme e2e (UX-05)
- **Sorun:** [ÖNERİ] Yalnız klavye ile sohbet/yükleme/ayar ölçülmedi.
- **Değişiklik:** Playwright klavye testi.
- **Kabul:** Üç akış yalnız klavye ile tamamlanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-07 · axe-core CI denetimi
- **Sorun:** [ÖNERİ] Erişilebilirlik otomatik denetlenmiyor.
- **Değişiklik:** axe-core Playwright'ta.
- **Kabul:** Kritik/ciddi ihlal 0.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-08 · Odak yönetimi: modal ve çekmece
- **Sorun:** [ÖNERİ] Odak tuzağı kısmen.
- **Değişiklik:** Odak tuzağı ve geri dönüş.
- **Kabul:** Modal kapanınca odak tetikleyiciye döner.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### ARY-09 · Canlı bölgeler: akış ilerlemesi
- **Sorun:** [ÖNERİ] Ekran okuyucu akışı duymuyor.
- **Değişiklik:** `aria-live` ile adım bildirimi.
- **Kabul:** Akış sırasında ekran okuyucu duyurusu.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### ARY-10 · `prefers-reduced-motion` uyumu
- **Sorun:** [ÖNERİ] Animasyonlar azaltılmıyor.
- **Değişiklik:** Medya sorgusu ve test.
- **Kabul:** Azaltılmış hareketle animasyon yok.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### ARY-11 · Durum yönetimi ve depolama şeması göçü (UX-03)
- **Sorun:** [ÖNERİ] Eski depolama şeması göçü testi.
- **Değişiklik:** Şema sürümü ve göç.
- **Kabul:** Eski şemalı veri yeni sürümde göç eder.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-12 · Depolama kapalıyken uygulama
- **Sorun:** [ÖNERİ] Gizli pencere/engelli depolama.
- **Değişiklik:** Try/catch ve bellek içi yedek.
- **Kabul:** localStorage kapalıyken uygulama çalışır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### ARY-13 · Akış zaman çizelgesi gerçek olaylardan (UX-09)
- **Sorun:** [ÖNERİ] Sahte animasyon olmadığı kanıtlı değil.
- **Değişiklik:** Her adım SSE olayına bağlı test.
- **Kabul:** Olaysız adım gösterilmez.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-14 · İptal düğmesi tüm adımları durdurur
- **Sorun:** [ÖNERİ] e2e yok.
- **Değişiklik:** İptal e2e.
- **Kabul:** İptal sonrası olay akışı durur.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-15 · Atıf arayüzü: üst simge, kaynak paneli, rozet (UX-10)
- **Sorun:** [ÖNERİ] Atıf sayısı olaylarla eşleşme testi.
- **Değişiklik:** Atıf sayısı = `citation` olayları testi.
- **Kabul:** Eşleşme testi ve metin eşdeğeri.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-16 · Güven göstergesi renk körü uyumu
- **Sorun:** [ÖNERİ] Yalnız renk olmamalı.
- **Değişiklik:** Metin + simge.
- **Kabul:** Güven etiketi metin içerir.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### ARY-17 · Komut paleti kapsamı (UX-13)
- **Sorun:** [ÖNERİ] Sohbet arama, model seçimi, artefakt açma yok.
- **Değişiklik:** Palete sohbet arama, model/mod, artefakt, ajan durumu.
- **Kabul:** Her ana eylem paletten erişilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-18 · Kısayol haritası ekranı
- **Sorun:** [ÖNERİ] Kısayollar belgesiz.
- **Değişiklik:** `?` ile kısayol listesi.
- **Kabul:** Liste tüm kısayolları içerir.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### ARY-19 · Slash komutları ve @-bahsetmeler (UX-14)
- **Sorun:** [ÖNERİ] Slash komutu niyet seçimi yok.
- **Değişiklik:** `/sunum /araştır /kod /özet`, `@dosya @bilgi @web`.
- **Kabul:** Slash niyet sınıflandırmasını atlar ve meta veride görünür.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-20 · Kullanıcı istem kitaplığı
- **Sorun:** [ÖNERİ] Şablon istemleri kaydedilemiyor.
- **Değişiklik:** Kaydet/çağır arayüzü.
- **Kabul:** Kayıtlı istem slash ile çağrılır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-21 · Model/ajan seçici ve gerekçe (UX-15)
- **Sorun:** [ÖNERİ] Elle seçim meta veriye yansımıyor olabilir.
- **Değişiklik:** Seçici ve gerekçe metni.
- **Kabul:** Elle seçim yanıt meta verisinde.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-22 · Boş/hata/yükleniyor durumları sözlüğü (UX-18)
- **Sorun:** [ÖNERİ] Hata metinleri dağınık.
- **Değişiklik:** Hata türü başına metin sözlüğü.
- **Kabul:** Her hata türü "ne oldu/ne yap" içerir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-23 · SSE kopma ve yeniden bağlanma
- **Sorun:** [ÖNERİ] Ağ kesilince iş kaybı.
- **Değişiklik:** Yeniden bağlanma ve kaldığı yerden izleme.
- **Kabul:** Ağ dönünce akış devam eder (e2e).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-24 · Çevrimdışı göstergesi
- **Sorun:** [ÖNERİ] Ağ durumu görünmüyor.
- **Değişiklik:** Üst çubukta çevrimdışı rozeti.
- **Kabul:** Ağ kesilince rozet çıkar.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### ARY-25 · Sanal liste ve 1.000 mesaj performansı (UX-19)
- **Sorun:** [ÖNERİ] Uzun sohbet yavaşlayabilir.
- **Değişiklik:** Sanal kaydırma ve profil testi.
- **Kabul:** 1.000 mesajda ≥ 50 FPS, ilk boyama < 1.5 sn.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-26 · Markdown/vurgulama Web Worker'da
- **Sorun:** [ÖNERİ] Ana iş parçacığı bloklanıyor.
- **Değişiklik:** Worker.
- **Kabul:** Uzun yanıtta kare düşmez.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-27 · Paket boyutu bütçesi ve CI kapısı
- **Sorun:** [ÖNERİ] Boyut ölçülmüyor.
- **Değişiklik:** Çekirdek ≤ 300 KB gz bütçesi.
- **Kabul:** Aşım CI'ı kırar.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-28 · Lighthouse performansı
- **Sorun:** [ÖNERİ] Ölçülmedi.
- **Değişiklik:** Lighthouse CI.
- **Kabul:** Performans ≥ 90.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-29 · Güvenli içerik işleme: 40 saldırı örneği (UX-20)
- **Sorun:** [ÖNERİ] Sanitizer var, 40 örnek testi yok.
- **Değişiklik:** XSS örnek seti ve test.
- **Kabul:** 40 örnek çalışmaz; zararsız SVG çizilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-30 · DOMPurify yerel paket
- **Sorun:** [ÖNERİ] Özel sanitizer kullanılıyor.
- **Değişiklik:** DOMPurify yerel vendor.
- **Kabul:** Sanitizer testi DOMPurify ile geçer.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-31 · Ajanlar sayfası: yük, geçmiş, benchmark (UX-22)
- **Sorun:** [ÖNERİ] Kart verisi API ile birebir testi yok.
- **Değişiklik:** Kart veri eşitliği testi.
- **Kabul:** Kart verileri API ile birebir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-32 · Ajan ekleme sihirbazı komut üretimi
- **Sorun:** [ÖNERİ] Komut ajanı kaydediyor mu denenmedi.
- **Değişiklik:** Sihirbaz komutu test ortamında çalışır.
- **Kabul:** Üretilen komutla ajan kaydolur.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-33 · Projeler sayfası: çakışma çözme ve yeniden atama e2e (UX-23)
- **Sorun:** [ÖNERİ] e2e yok.
- **Değişiklik:** e2e akışı.
- **Kabul:** Çakışma çözme ve yeniden atama arayüzden uçtan uca.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-34 · Canlı ilerleme SSE
- **Sorun:** [ÖNERİ] Sayfa yenilemeden ilerleme.
- **Değişiklik:** SSE akışı.
- **Kabul:** İlerleme sayfa yenilemeden akar.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-35 · Çıktı karşılaştırma ekranı
- **Sorun:** [ÖNERİ] Ajan çıktısı karşılaştırması sınırlı.
- **Değişiklik:** Yan yana fark görünümü.
- **Kabul:** İki ajan çıktısı fark vurgulu görünür.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-36 · Geri bildirim akışı (UX-27)
- **Sorun:** [ÖNERİ] Beğen/beğenme ve "yanlış bilgi bildir" kısmen.
- **Değişiklik:** Neden etiketi, doğru cevap alanı, silme.
- **Kabul:** Geri bildirim `run_id` ile kaydedilir ve silinebilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-37 · Paylaşım ve yorumlar (UX-26)
- **Sorun:** [ÖNERİ] Yorum yok.
- **Değişiklik:** Yorum, yetki, süre sonu.
- **Kabul:** Yetkisiz erişim 403/404; süresi dolan 404.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-38 · Onboarding / ilk çalıştırma sihirbazı (UX-17)
- **Sorun:** [ÖNERİ] Yeni kullanıcı yönlendirilmiyor.
- **Değişiklik:** Ollama/model/ajan kontrolü sihirbazı.
- **Kabul:** Sihirbaz eksik bağımlılığı gösterir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-39 · Ayarlar sayfası birleştirme
- **Sorun:** [ÖNERİ] Ayarlar dağınık.
- **Değişiklik:** Tek ayarlar sayfası: tema, dil, mod, gizlilik, veri.
- **Kabul:** Tüm ayarlar tek yerden.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-40 · Dil seçimi (TR/EN) tam çeviri
- **Sorun:** [ÖNERİ] i18n kısmen.
- **Değişiklik:** Eksik anahtar testi.
- **Kabul:** Eksik çeviri anahtarı 0.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### ARY-41 · Mobil/dar ekran düzeni testleri
- **Sorun:** [ÖNERİ] Mobil düzen elle denendi.
- **Değişiklik:** Playwright 375/768 px.
- **Kabul:** Yatay kaydırma yok; kontroller kullanılır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-42 · Sohbet geçmişi arama ve etiket
- **Sorun:** [ÖNERİ] Geçmişte arama sınırlı.
- **Değişiklik:** FTS5 arama arayüzü.
- **Kabul:** Sohbet araması sonuç ve vurgulama verir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-43 · Sohbet dışa aktarma biçimleri
- **Sorun:** [ÖNERİ] Yalnız Markdown.
- **Değişiklik:** PDF, JSON, HTML.
- **Kabul:** Dört biçimde dışa aktarma.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-44 · Dosya sürükle-bırak ve yapıştırma
- **Sorun:** [ÖNERİ] Yükleme düğmesiyle.
- **Değişiklik:** Sürükle-bırak, panodan görsel yapıştırma.
- **Kabul:** Sürükle-bırak çalışır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-45 · Yükleme ilerleme ve iptal
- **Sorun:** [ÖNERİ] İptal yok.
- **Değişiklik:** İptal düğmesi.
- **Kabul:** İptal edilen yükleme dizinlenmez.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### ARY-46 · Artefakt paneli: önizleme ve karşılaştırma
- **Sorun:** [ÖNERİ] Sürüm farkı yok.
- **Değişiklik:** İki sürüm fark görünümü.
- **Kabul:** Fark satır düzeyinde görünür.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-47 · Yanıt içinde tablo/grafik bileşenleri
- **Sorun:** [ÖNERİ] Tablo ham Markdown.
- **Değişiklik:** Sıralanabilir tablo, grafik çizimi.
- **Kabul:** Tablo sıralanır, CSV indirilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-48 · Kod blokları: kopyala, çalıştır, dosyaya ekle
- **Sorun:** [ÖNERİ] Eylemler sınırlı.
- **Değişiklik:** Kod bloğu eylemleri.
- **Kabul:** Kopyala/çalıştır çalışır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-49 · Ses girişi/çıkışı dayanıklılığı (MM-12)
- **Sorun:** [ÖNERİ] İzin reddi mesajı e2e yok.
- **Değişiklik:** İzin yönlendirme mesajı, 200 MB ses.
- **Kabul:** İzin reddinde mesaj çıkar (e2e).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-50 · Bildirimler: iş bitti, ajan düştü
- **Sorun:** [ÖNERİ] Yalnız yanıt hazır.
- **Değişiklik:** Bildirim türleri ve ayar.
- **Kabul:** Ajan çevrimdışı bildirimi çıkar.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-51 · Boş durum illüstrasyonları ve ipuçları
- **Sorun:** [ÖNERİ] Boş sayfalar sade.
- **Değişiklik:** İpucu metinleri.
- **Kabul:** Her boş durumda eylem önerisi.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### ARY-52 · Mikro etkileşimler: yükleme iskeletleri
- **Sorun:** [ÖNERİ] Dönen simge yaygın.
- **Değişiklik:** İskelet yükleme.
- **Kabul:** Ana listelerde iskelet.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### ARY-53 · Tasarım tutarlılığı denetimi: görsel gerileme testi
- **Sorun:** [ÖNERİ] Stil değişince bozulma fark edilmiyor.
- **Değişiklik:** Ekran görüntüsü karşılaştırma.
- **Kabul:** Ana sayfalarda görsel fark eşiği.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-54 · Ölü CSS temizliği (UX-04)
- **Sorun:** [ÖNERİ] Ölü CSS oranı ölçülmedi.
- **Değişiklik:** Kullanılmayan CSS raporu.
- **Kabul:** Ölü CSS < %5.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### ARY-55 · Favicon, başlık ve meta etiketleri
- **Sorun:** [ÖNERİ] Sayfa başlıkları sabit.
- **Değişiklik:** Rota başına başlık.
- **Kabul:** Her rota başlığı değişir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### ARY-56 · Yazdırma stilleri
- **Sorun:** [ÖNERİ] Rapor yazdırılamıyor.
- **Değişiklik:** Yazdırma CSS.
- **Kabul:** Artefakt sayfası yazdırılabilir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### ARY-57 · Sürüm ve "hakkında" sayfası
- **Sorun:** [ÖNERİ] Sürüm bilgisi yok.
- **Değişiklik:** Sürüm, model, ajan sayısı, lisans.
- **Kabul:** Sayfa gerçek veriyle dolu.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-58 · Kullanım istatistikleri paneli doğruluğu
- **Sorun:** [ÖNERİ] Panel sayıları örnek veri olabilir.
- **Değişiklik:** Sayıların API/DB ile eşitliği testi.
- **Kabul:** Panel = veritabanı sayıları.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ARY-59 · Tema geçişi titremesi
- **Sorun:** [ÖNERİ] Tema yüklenirken beyaz parlama.
- **Değişiklik:** Erken tema uygulama.
- **Kabul:** İlk boyamada doğru tema.
- **Meta:** P2 · S · Bağ: - · Durum: açık
