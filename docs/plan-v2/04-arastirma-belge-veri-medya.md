# Parça 4 — Araştırma (RES), Sunum (PPT), Belge (DOC), Veri (DS) ve Çoklu Medya (MM)

**Ortak kural:** Her stüdyo çıktısı (1) bir **artefakt** olarak saklanır (ORC-17), (2) olgusal içeriği **kaynaklıdır** (HAL-23), (3) üretildikten sonra **otomatik kalite denetiminden** geçer (açılıyor mu, taşma var mı, formül hatası var mı), (4) bir **eval seti** ile ölçülür. "Dosya üretti" demek başarı sayılmaz; "dosya açıldı, kontrol listesini geçti, kaynakları doğrulandı" başarıdır.

---

## A. RES — Derin Araştırma

> Bugünkü durum [DOĞRULANDI: F7]: `deep_research.py` internete hiç çıkmıyor; "araştırma" modelin kendi bilgisinden yazılmış metindir. Aşağıdakiler RAG-18..23 üzerine kurulur.

#### RES-01 · Araştırma planlayıcısı ve döngüsü
- **Sorun:** [DOĞRULANDI: F7] `decompose_research_questions` alt soru üretiyor ama bu sorular gerçek kaynaklarda aranmıyor.
- **Değişiklik:** Soru → alt sorular → arama sorguları → arama → okuma → not çıkarma → eksik bilgi tespiti → ek arama → sentez döngüsü; adım ve süre bütçesi; her aşama `step_start/step_end` olaylarıyla akıtılır.
- **Kabul:** "Konu X'in son 3 yıldaki gelişmeleri" isteği en az 8 farklı kaynaktan not üretir ve her alt soru için kaynak listesi gösterir; bütçe aşılınca kalan eksikler raporda belirtilir.
- **Meta:** P0 · L · Bağ: RAG-18, ORC-06 · Durum: açık

#### RES-02 · Arama ve okuma ajanı
- **Sorun:** [ÖNERİ] Tek arama sorgusu dar kalır; aynı sayfa tekrar okunur; reklam/menü gürültüsü bağlama girer.
- **Değişiklik:** Sorgu çeşitlendirme (eşanlamlı, İngilizce karşılık, uzman terimi), sonuç tekilleştirme, sayfa okuma, soruyla ilgili pasaj seçimi (RAG hibrit), kaynak başına özet notlar (alıntı + URL + tarih).
- **Kabul:** 20 konulu sette ilgisiz kaynak oranı < %15; aynı alan adı tek kaynak olarak ağırlıklandırılır (çeşitlilik ölçüsü ≥ 0.6).
- **Meta:** P0 · L · Bağ: RES-01, RAG-09 · Durum: açık

#### RES-03 · Kaynak puanlama ve çelişki matrisi
- **Sorun:** [ÖNERİ] Kaynaklar birbiriyle çeliştiğinde rapor bunu gizler veya rastgele birini seçer.
- **Değişiklik:** RAG-19 güvenilirlik puanı + iddia bazlı matris (kaynak × iddia: destekler/çürütür/belirsiz); çelişkiler raporda ayrı bölüm; çözüm önerisi (daha güvenilir/yeni kaynak).
- **Kabul:** Bilerek çelişen 15 kaynak çiftinde çelişki yakalama ≥ %85; raporda tek tarafı seçip diğerini gizleme yok.
- **Meta:** P1 · M · Bağ: RES-02, RAG-19 · Durum: açık

#### RES-04 · Atıflı sentez
- **Sorun:** [DOĞRULANDI: F7] Mevcut çıktı kaynaksız; her cümle model hafızası.
- **Değişiklik:** Bölümlü rapor: özet, bulgular, çelişkiler, belirsizlikler, sınırlılıklar, öneriler, kaynakça; her olgusal cümle `[S#]` atfı taşır; atıfsız olgusal cümle yazılmaz (MODE-04 + HAL-08).
- **Kabul:** Atıfsız olgusal cümle oranı < %3; atıfların ≥ %95'i iddiayı destekler (HAL-07 ölçümü).
- **Meta:** P0 · L · Bağ: RES-02, HAL-08 · Durum: açık

#### RES-05 · Rapor çıktı biçimleri ve kaynakça
- **Sorun:** [ÖNERİ] Araştırma sonucu yalnız sohbet metni; paylaşılabilir biçim yok.
- **Değişiklik:** Markdown, DOCX, PDF ve PPTX çıktıları (DOC/PPT hattıyla); APA/IEEE/Vancouver kaynakça; erişim tarihi; kaynak arşivi (RAG-23).
- **Kabul:** Her biçimde kaynakça numaraları metindeki atıflarla birebir eşleşir (otomatik denetim); PDF/DOCX açılır ve TOC doğru.
- **Meta:** P1 · M · Bağ: RES-04, DOC-01 · Durum: açık

#### RES-06 · Araştırma geçmişi ve güncelleme
- **Sorun:** [ÖNERİ] Aynı konuyu yeniden araştırmak sıfırdan başlar; ne değiştiği görünmez.
- **Değişiklik:** Araştırmalar artefakt olarak saklanır; "yeni kaynaklarla güncelle" yalnız değişen/yeni bulguları ekler ve fark gösterir.
- **Kabul:** İkinci çalıştırma önceki kaynakları yeniden okumaz (önbellek); fark listesi yeni/değişen iddiaları gösterir.
- **Meta:** P2 · M · Bağ: RES-04, ORC-17 · Durum: açık

#### RES-07 · Belge-merkezli araştırma ve literatür matrisi
- **Sorun:** [DOĞRULANDI: F1] `academic_expert` bağlı değil; yüklenen çok sayıda makaleden karşılaştırma çıkaran işlev gerçekte kullanılmıyor.
- **Değişiklik:** 10–50 yüklenen PDF'ten yöntem, örneklem, ölçüm, bulgu, sınırlılık çıkarımı (şema kısıtlı), yapılandırılmış matris; her hücre kaynağa sayfa atfı taşır.
- **Kabul:** 20 makalelik sette hücre doğruluğu ≥ %90 (insan kontrollü); yanlış hücre kaynağıyla birlikte hızlıca düzeltilebilir.
- **Meta:** P2 · L · Bağ: RAG-14, RAG-21 · Durum: açık

#### RES-08 · Araştırma hız modları
- **Sorun:** [ÖNERİ] Her soru derin araştırma gerektirmez; her soruya 10 dk harcanmaz.
- **Değişiklik:** Hızlı (≤ 1 dk, 3–5 kaynak), Standart (≤ 4 dk, 10 kaynak), Derin (≤ 12 dk, 25+ kaynak); kullanıcı seçer, sistem önerir; süre/kaynak bütçesi arayüzde görünür.
- **Kabul:** Her modda bütçe aşılmaz; hızlı mod kaynakları ve sınırlılığı açıkça belirtir.
- **Meta:** P2 · S · Bağ: RES-01 · Durum: açık

#### RES-09 · Alt soruların ajanlara dağıtımı
- **Sorun:** [DOĞRULANDI: F12] Araştırma master'da sıralı yürür; `map_reduce_llm` ve ajan ağı kullanılmıyor.
- **Değişiklik:** Alt sorular farklı ajanlarda paralel yürür (ORC-07), master sentezler; ajan çıktılarında "Üreten: ajan·model" atfı.
- **Kabul:** 6 ajanla 8 alt soruluk derin araştırma tek ajana göre ≥ 3x hızlı; sentez tutarlılık denetiminden geçer.
- **Meta:** P1 · M · Bağ: ORC-07, DIST-09 · Durum: açık

#### RES-10 · Sentez sonrası doğrulama
- **Sorun:** [ÖNERİ] Sentez adımı kendi başına yeni uydurma ekleyebilir.
- **Değişiklik:** Rapor iddiaları kaynak notlarına karşı denetlenir (HAL-06/07); desteklenmeyenler düzeltilir veya çıkarılır; doğrulama özeti rapora eklenir ("32 iddia, 30 doğrulandı, 2 çıkarıldı").
- **Kabul:** Doğrulama sonrası desteksiz iddia oranı < %2; özet gerçek sayılarla üretilir (elle yazılmaz).
- **Meta:** P0 · M · Bağ: RES-04, HAL-07 · Durum: açık

#### RES-11 · Telif, etik ve robots.txt
- **Sorun:** [ÖNERİ] Sayfa içeriğini olduğu gibi kopyalamak telif ve etik sorunu yaratır; robots.txt ve kullanım şartları yok sayılıyor olabilir.
- **Değişiklik:** Kısa alıntı sınırı, özetleme ve atıf; robots.txt ve hız sınırlarına uyum; ücretli duvar/giriş gerektiren sayfaları atlama; kaynak lisans bilgisi.
- **Kabul:** Rapor, tek kaynaktan uzun ardışık alıntı içermez (kural); robots.txt yasaklı sayfalar alınmaz (test).
- **Meta:** P1 · S · Bağ: RAG-18 · Durum: açık

#### RES-12 · Araştırma eval seti
- **Sorun:** [ÖNERİ] "Araştırma kalitesi" ölçülmüyor.
- **Değişiklik:** 30 konu × uzman kontrol listesi (temel olgular, önemli kaynaklar, güncellik, çelişki yönetimi); atıf doğruluğu ve kapsama skoru; eval kapısına (HAL-05) dahil.
- **Kabul:** Kapsama ≥ %80, atıf doğruluğu ≥ %95, uydurma kaynak 0.
- **Meta:** P1 · M · Bağ: RES-04, HAL-03 · Durum: açık

---

## B. PPT — Sunum Stüdyosu

> Bugünkü durum: `deep_research.build_pptx_presentation` (184 satır) tema, geçiş ve kart bileşenleri üretiyor [DOĞRULANDI]. Eksikler: içerik kaynaksız (F7), taşma/okunabilirlik denetimi yok, render doğrulaması yok.

#### PPT-01 · Anahat üretimi ve anlatı yapısı
- **Sorun:** [ÖNERİ] Slayt sayısı kadar madde üretmek akıcı bir sunum yapmaz.
- **Değişiklik:** Hedef kitle, süre, ton ve amaç alınır; slayt başına tek ana mesaj (iddia başlıkları), açılış-gelişme-kapanış akışı, her slayt için kaynak listesi; kullanıcı anahattı düzenleyebilir.
- **Kabul:** 20 konuda her slaytın başlığı bir iddia/mesaj (kural + hakem); slayt sayısı ve süre uyumu (≈ 1.5 dk/slayt) ±%20.
- **Meta:** P1 · M · Bağ: RES-04 · Durum: açık

#### PPT-02 · Tasarım sistemi ve yerleşimler
- **Sorun:** [ÖNERİ] Temalar mevcut ama tutarlı bir tasarım sistemi (ızgara, tipografi ölçeği, boşluk, bileşen kuralları) yok.
- **Değişiklik:** Tema jetonları (renk paleti, yazı tipi ölçeği, boşluk, köşe), 12 yerleşim (kapak, bölüm, tek mesaj, iki sütun, görsel+metin, tablo, grafik, alıntı, zaman çizelgesi, karşılaştırma, süreç, kapanış), WCAG AA kontrast denetimi.
- **Kabul:** Her tema–yerleşim çifti kontrast ≥ 4.5:1 ve minimum yazı boyutu kuralını geçer (otomatik test); 6 tema.
- **Meta:** P1 · L · Bağ: - · Durum: açık

#### PPT-03 · Metin sığdırma ve okunabilirlik
- **Sorun:** [ÖNERİ] Uzun metin taşar, yazı çok küçülür; kullanıcı PowerPoint'te açınca bozuk görür.
- **Değişiklik:** Yazı tipi metrikleriyle (Pillow) ölçüm; kutu taşarsa özetle/böl/yazı boyutunu kademeli düşür (alt sınır 18 pt); slayt başına ≤ 40 kelime kuralı; madde sayısı sınırı.
- **Kabul:** 50 üretilmiş slaytta taşma 0, minimum yazı ≥ 18 pt, kelime sınırı ihlali < %3.
- **Meta:** P0 · M · Bağ: PPT-02 · Durum: açık

#### PPT-04 · Görsel, diyagram ve grafik üretimi
- **Sorun:** [ÖNERİ] Slaytlar metin ağırlıklı; görseller anlamsız dekor olabilir.
- **Değişiklik:** Gerçek veriyle yerel grafik nesneleri (`python-pptx` chart), parametrik SVG diyagramlar (süreç, hiyerarşi, zaman çizelgesi), ikon seti, isteğe bağlı üretilmiş görseller (MM-05); her görselin alt metni (erişilebilirlik) ve kaynağı.
- **Kabul:** Veri içeren slaytların ≥ %80'inde gerçek grafik nesnesi vardır; görsellerin alt metni boş değil; telifsiz/üretilmiş kaynak bilgisi notlarda.
- **Meta:** P1 · L · Bağ: DS-03, MM-10 · Durum: açık

#### PPT-05 · Geçişler ve animasyonlar
- **Sorun:** [DOĞRULANDI] `_transition_xml` elle OOXML yazıyor; geçerliliği PowerPoint'te açılarak doğrulanmıyor, bozuk dosya riski var (önceki commit'lerde OOXML düzeltmeleri gerekti).
- **Değişiklik:** Sade geçiş seti (solma, itme, belirme), slayt geneli tutarlı; XML şeması doğrulaması; LibreOffice ile açılış denemesi (PPT-07); bozuk XML'de geçişsiz yedek.
- **Kabul:** Üretilen 30 dosya PowerPoint/LibreOffice'te hatasız açılır; geçişler slayt XML'inde geçerli şemaya uyar (test).
- **Meta:** P1 · S · Bağ: PPT-07 · Durum: açık

#### PPT-06 · Konuşmacı notları ve kaynak slaytı
- **Sorun:** [DOĞRULANDI: F7] Notlar ve kaynak bilgisi yok veya kaynaksız.
- **Değişiklik:** Her slayt için konuşma metni ve süre tahmini; olgusal maddelerin kaynak kimlikleri notlarda; son slaytta "Kaynaklar" (URL/DOI/belge + erişim tarihi).
- **Kabul:** Olgusal içerikli her slaytın notunda en az bir kaynak vardır (kural); kaynaklar slaytı HAL-23 doğrulamasını geçer.
- **Meta:** P0 · M · Bağ: HAL-23 · Durum: açık

#### PPT-07 · Render ve görsel kalite denetimi
- **Sorun:** [ÖNERİ] Dosya geçerli olsa da görünüm bozuk olabilir (üst üste binme, boş slayt, düşük kontrast); şu an görmeden teslim ediliyor.
- **Değişiklik:** LibreOffice başsız ile PDF/PNG render; kural denetimi (taşma, boş alan, çakışma, kontrast) + VLM ile "bu slayt düzgün mü" denetimi; sorun varsa hedefli düzeltme (en fazla 3 tur); rapor artefakta eklenir.
- **Kabul:** Eval sunumlarında render sonrası görsel hata oranı < %3; düzeltme turları sonunda kalan hatalar kullanıcıya listelenir.
- **Meta:** P0 · L · Bağ: PPT-03, SEC-13 · Durum: açık

#### PPT-08 · Önizleme, düzenleme ve sürümler
- **Sorun:** [ÖNERİ] Kullanıcı tek slaytı değiştirmek için tüm sunumu yeniden üretiyor; önizleme yok.
- **Değişiklik:** Sohbette slayt şeridi (küçük resimler), "3. slaytı kısalt/yeniden yaz/görsel ekle" hedefli düzenleme (ORC-16), sürüm geçmişi, indirme kartı, slayt sıralama.
- **Kabul:** Hedefli düzenleme dışındaki slaytlar bayt bayt aynı kalır; sürüm geri alma çalışır (e2e).
- **Meta:** P1 · L · Bağ: ORC-16, UX-11 · Durum: açık

#### PPT-09 · Şablon içe aktarma
- **Sorun:** [ÖNERİ] Kurumsal şablon (.potx/.pptx) kullanımı yok.
- **Değişiklik:** Yüklenen şablondan yerleşimler, renkler, yazı tipleri çıkarılır; içerik şablonun yerleşimlerine basılır; şablonda olmayan yerleşim için en yakın eşleme.
- **Kabul:** 5 farklı kurumsal şablonla üretilen sunumlar şablon tema/yazı tipini korur ve render denetimini geçer.
- **Meta:** P2 · L · Bağ: PPT-02, PPT-07 · Durum: açık

#### PPT-10 · Sunum eval seti
- **Sorun:** [ÖNERİ] Sunum kalitesi ölçülmüyor.
- **Değişiklik:** 20 konu × otomatik kontrol listesi: açılış (PowerPoint/LibreOffice), taşma 0, kaynaklı, notlar var, tema tutarlı, geçişli, slayt sayısı uyumu; skor ve rapor.
- **Kabul:** Kontrol listesi geçme oranı ≥ %90; sonuçlar HAL-05 kapısına bağlı.
- **Meta:** P1 · M · Bağ: PPT-07, HAL-03 · Durum: açık

---

## C. DOC — Word, Excel, PDF ve Belge İşleme

#### DOC-01 · Word (DOCX) kalitesi
- **Sorun:** [DOĞRULANDI] Önceki commit'lerde OOXML (`w:shd`) şema hatası düzeltildi; DOCX geçerliliği otomatik doğrulanmıyor.
- **Değişiklik:** Başlık stilleri, TOC alanı, numaralı başlıklar, sayfa numarası, üst/alt bilgi, tablo stilleri, şekil yazısı; çıktı doğrulama: şema denetimi + LibreOffice ile PDF'e çevirme + sayfa sayısı/TOC kontrolü.
- **Kabul:** 25 belgede açılış hatası 0; TOC bağlantıları çalışır; "Lorem/TODO" yer tutucu yok (DOC-08).
- **Meta:** P1 · M · Bağ: SEC-13 · Durum: açık

#### DOC-02 · Excel (XLSX) formülleri ve doğrulama
- **Sorun:** [ÖNERİ] Üretilen çalışma kitaplarında formüller sabit değerlere dönebilir veya `#REF!` hatası içerebilir; kimse hesaplamıyor.
- **Değişiklik:** Canlı formüller (SUM, IF, XLOOKUP, SUMIFS...), adlandırılmış aralıklar, veri doğrulama, koşullu biçimlendirme, grafikler; LibreOffice ile yeniden hesaplayıp hata hücresi taraması; formül ve beklenen değer testleri.
- **Kabul:** 25 çalışma kitabında hata hücresi 0; formül içeren hücre oranı ≥ %80 (hesaplanabilen yerlerde); açılışta "onar" iletisi yok.
- **Meta:** P0 · M · Bağ: SEC-13 · Durum: açık

#### DOC-03 · PDF düzeni
- **Sorun:** [ÖNERİ] PDF çıktıları basit; kapak, içindekiler, sayfa numarası ve bağlantılı bölümler tutarsız.
- **Değişiklik:** Kapak, bağlantılı içindekiler, başlık/altbilgi, yazı tipi gömme (Türkçe glifler), şekil/tablo yerleşimi, PDF/A seçeneği; metin seçilebilirlik denetimi.
- **Kabul:** Türkçe karakterler eksiksiz (test); TOC tıklanabilir; PDF/A doğrulayıcısından geçer (seçenek açıkken).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### DOC-04 · Belge şablon kitaplığı
- **Sorun:** [ÖNERİ] "Rapor/CV/teklif/tutanak" istekleri sıfırdan üretiliyor; tutarlılık yok.
- **Değişiklik:** Şablonlar: rapor, bilimsel makale (IEEE/APA), CV, teklif, tutanak, sözleşme taslağı, fatura, ders notu, eğitim planı; alanlar şemalı; kullanıcı şablon ekleyebilir.
- **Kabul:** Her şablon için dolu örnek üretimi doğrulama paketinden geçer; boş alan kalmaz.
- **Meta:** P2 · M · Bağ: DOC-01 · Durum: açık

#### DOC-05 · Mevcut belge üzerinde düzenleme ve izli değişiklik
- **Sorun:** [ÖNERİ] Yüklenen belgeyi bozmadan değiştirme yok; yeniden üretim biçimi/ekleri kaybeder.
- **Değişiklik:** DOCX/XLSX üzerinde yerinde hedefli düzenleme; izli değişiklik (redline) çıktısı; orijinal dosya değişmez, yeni sürüm artefakt olur.
- **Kabul:** Düzenlenmeyen bölümlerin XML'i değişmez (özet karşılaştırma); izli değişiklikler Word'de görünür.
- **Meta:** P2 · L · Bağ: ORC-16 · Durum: açık

#### DOC-06 · Biçim dönüştürme güvenilirliği
- **Sorun:** [DOĞRULANDI] `file_converter` var; dönüşümün görsel/yapısal kaybı ölçülmüyor.
- **Değişiklik:** Tur-gidiş-dönüş testleri (DOCX→PDF→metin, XLSX→CSV→XLSX, PPTX→PDF); görsel fark (SSIM) ve yapı karşılaştırması; kayıp raporu kullanıcıya gösterilir.
- **Kabul:** 40 dosyalık sette metin kaybı < %1, kritik kayıplar (tablo, resim) kullanıcıya bildirilir.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DOC-07 · Tablo çıkarma
- **Sorun:** [ÖNERİ] PDF/görsel tablolar düz metne dönüşüp yapısını kaybediyor.
- **Değişiklik:** Yapısal tablo çıkarımı (RAG-02) → JSON/CSV/XLSX; birleşik hücre/çok satırlı başlık işleme; güven skoru.
- **Kabul:** 50 tabloda hücre doğruluğu ≥ %95; düşük güvenli tablolar işaretlenir.
- **Meta:** P1 · M · Bağ: RAG-02 · Durum: açık

#### DOC-08 · Belge kalite denetimi (yazım, tutarlılık, yer tutucu)
- **Sorun:** [ÖNERİ] Üretilen belgelerde yazım hatası, tutarsız terim ve "Lorem ipsum/TODO/[...]" kalıntıları kalabiliyor.
- **Değişiklik:** Yerel Türkçe yazım/dilbilgisi denetimi (LanguageTool/Zemberek benzeri), terim tutarlılığı, yer tutucu taraması, sayfa/şekil numarası bütünlüğü; bulgular raporda.
- **Kabul:** Yer tutucu kalıntısı 0; yazım hatası oranı < 1/500 kelime (örneklem).
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### DOC-09 · Rakamlı içerikte hesap izi
- **Sorun:** [ÖNERİ] Belgedeki sayılar kaynaksız yazılabilir.
- **Değişiklik:** Sayı içeren paragraflar kaynak/hesap izi taşır (dipnot/yorum); HAL-09 denetimi belge üretiminde zorunlu.
- **Kabul:** Eval belgelerinde kaynaksız/hesapsız sayı oranı < %2.
- **Meta:** P1 · M · Bağ: HAL-09 · Durum: açık

#### DOC-10 · Belge eval seti
- **Sorun:** [ÖNERİ] Belge üretim kalitesi ölçülmüyor.
- **Değişiklik:** 25 belge × otomatik kontrol (açılıyor, TOC, formül hatası, yazım, kaynak, yer tutucu); rapor ve eşik.
- **Kabul:** Kontrol listesi geçme oranı ≥ %90.
- **Meta:** P1 · M · Bağ: DOC-01, DOC-02, HAL-03 · Durum: açık

---

## D. DS — Veri Analizi ve AutoML

#### DS-01 · Veri profili (istek üzerine)
- **Sorun:** [DOĞRULANDI: F9] Her CSV yüklemesinde otomatik model eğitimi/tahmin çalışıyor (DEF-06).
- **Değişiklik:** Tür çıkarımı, eksik/aykırı değer, dağılım, kardinalite, tarih sütunları; yalnız istek üzerine veya kısa özet olarak; veri kalite uyarıları.
- **Kabul:** 30 veri setinde tür çıkarımı doğruluğu ≥ %95; özet kısa ve sayısal değerleri araçtan gelir (LLM hesaplamaz).
- **Meta:** P1 · M · Bağ: DEF-06 · Durum: açık

#### DS-02 · Doğal dilden SQL/pandas
- **Sorun:** [DOĞRULANDI] `introspect_sqlite_and_query` ve SQL araçları var ama güvenlik/doğruluk eval'i yok.
- **Değişiklik:** Şema + örnek değerlerle sorgu üretimi, yalnız salt-okunur sandbox, sorgu doğrulama (AST/EXPLAIN), sonuç + kod + doğrulama; sayısal cevaplar yalnız sorgu sonucundan.
- **Kabul:** 100 soruluk Türkçe text-to-SQL setinde yürütme doğruluğu ≥ %80; yazma/DDL denemeleri reddedilir.
- **Meta:** P0 · L · Bağ: SEC-13, ORC-08 · Durum: açık

#### DS-03 · Görselleştirme
- **Sorun:** [DOĞRULANDI] `canvas_widgets.js` grafik çiziyor ama tür seçimi ve doğruluk denetimi yok.
- **Değişiklik:** Veri şekline göre grafik türü önerisi, eksen/birim/başlık denetimi, aldatıcı grafik (kesik eksen, 3B) uyarısı, SVG/PNG dışa aktarma.
- **Kabul:** 40 veri setinde seçilen grafik türü uzman etiketiyle ≥ %85 uyumlu; grafik veri noktaları kaynak veriyle birebir.
- **Meta:** P2 · M · Bağ: UX-11 · Durum: açık

#### DS-04 · AutoML (sızıntı ve baseline denetimli)
- **Sorun:** [DOĞRULANDI] `train_and_forecast` basit L2 Ridge; çapraz doğrulama, sızıntı kontrolü, baseline karşılaştırması belirsiz.
- **Değişiklik:** scikit-learn (opsiyonel bağımlılık): regresyon/sınıflandırma/zaman serisi; zorunlu baseline, zamansal bölme, sızıntı tespiti (hedefle yüksek korelasyonlu türev sütunlar), çapraz doğrulama metrikleri; sonuç dürüstçe "baseline'a göre" sunulur.
- **Kabul:** Sızıntılı sentetik veri setinde uyarı verilir; model baseline'ı geçmiyorsa rapor bunu açıkça söyler (test).
- **Meta:** P2 · L · Bağ: DS-01 · Durum: açık

#### DS-05 · Açıklanabilirlik ve "ne olursa"
- **Sorun:** [ÖNERİ] Model sonucu neden verdi bilinmiyor.
- **Değişiklik:** Permütasyon önemi, kısmi bağımlılık grafikleri, tek örnek açıklaması; sohbette girdi değiştirerek tahmin (ne olursa).
- **Kabul:** Bilinen sentetik veride doğru değişkenler en önemli sıralanır (≥ %90).
- **Meta:** P3 · M · Bağ: DS-04 · Durum: açık

#### DS-06 · Anomali tespiti ve nedeni
- **Sorun:** [DOĞRULANDI] `profile_dataset` anomali sayısı veriyor; neden/bağlam yok.
- **Değişiklik:** Robust z-skor/IQR + Isolation Forest; her anomali için yakın satırlarla karşılaştırma ve "hangi sütun" açıklaması; yanlış alarm oranı raporu.
- **Kabul:** Etiketli anomali setinde F1 ≥ 0.8; her anomali sütun nedeniyle açıklanır.
- **Meta:** P3 · M · Bağ: DS-01 · Durum: açık

#### DS-07 · Tahmin: belirsizlik ve geriye dönük test
- **Sorun:** [DOĞRULANDI: F9] Tahmin sonuçları kesin sayı gibi sunuluyordu.
- **Değişiklik:** Mevsimsellik/trend ayrıştırması, tahmin aralığı, geriye dönük test (backtest), yeterli veri yoksa "tahmin yapılamaz"; sonuç her zaman "tahmin, belirsizlik ±" etiketli.
- **Kabul:** Backtest hata metrikleri raporda; 4 noktadan az veride tahmin reddedilir; aralık kapsama oranı ≈ nominal (±5 puan).
- **Meta:** P1 · M · Bağ: DS-04 · Durum: açık

#### DS-08 · İstatistiksel test seçimi
- **Sorun:** [ÖNERİ] "Bu iki grup farklı mı" sorusunda yanlış test/yorum riski.
- **Değişiklik:** Varsayım kontrolü (normallik, varyans), doğru test seçimi (t, Mann-Whitney, ANOVA, ki-kare), etki büyüklüğü, çoklu karşılaştırma düzeltmesi; sonuçlar `scipy` ile hesaplanır, yorum şablonu kontrollü.
- **Kabul:** 50 vakada test seçimi uzman etiketiyle ≥ %90 uyumlu; p-değeri yorumunda "nedensellik" abartısı yok (kural).
- **Meta:** P3 · M · Bağ: ORC-08 · Durum: açık

#### DS-09 · Tekrar üretilebilir analiz çıktısı
- **Sorun:** [ÖNERİ] Analiz sonuçları kodsuz; kullanıcı doğrulayamaz.
- **Değişiklik:** Analiz kodu + sonuç + grafikler tek not defteri/HTML raporunda; kodu sandbox'ta yeniden çalıştırılabilir.
- **Kabul:** Rapordaki kod temiz ortamda aynı sayıları üretir (test).
- **Meta:** P2 · M · Bağ: SEC-13 · Durum: açık

#### DS-10 · Veri gizliliği garantisi
- **Sorun:** [ÖNERİ] Hassas veri seti dış servise gitmediği kanıtlanabilir olmalı.
- **Değişiklik:** Bulut sağlayıcılar kapalıyken ağ çıkışı denetimi, veri setlerinde PII tespiti ve maskeleme önerisi, "bu veri yerelde kaldı" durum rozeti.
- **Kabul:** Bulut kapalıyken analiz sırasında dış ağ isteği 0 (ağ yakalayıcı testi); PII içeren sütunlar uyarı alır.
- **Meta:** P1 · S · Bağ: GW-02, SEC-21 · Durum: açık

---

## E. MM — Ses, Görsel, Video ve Çoklu Medya

#### MM-01 · Konuşmadan metne (STT)
- **Sorun:** [DOĞRULANDI] `faster-whisper` yalnız çağrıda içe aktarılıyor; model boyutu/dil/zaman damgası ayarı ve uzun kayıt desteği sınırlı.
- **Değişiklik:** Model seçimi (small/medium, int8), VAD, Türkçe/İngilizce, kelime/segment zaman damgası, uzun kayıtlar için arka plan işi (ORC-13), isteğe bağlı konuşmacı ayrımı.
- **Kabul:** Türkçe temiz kayıtlarda WER ≤ %12 (etiketli 20 kayıt); 60 dk kayıt arka planda işlenir ve ilerleme gösterir.
- **Meta:** P1 · M · Bağ: ORC-13, DEF-15 · Durum: açık

#### MM-02 · Toplantı/ders özeti
- **Sorun:** [ÖNERİ] Transkriptten karar/görev çıkarımı doğrulanmıyor.
- **Değişiklik:** Karar, aksiyon (sorumlu, tarih), açık sorular tablosu; her madde zaman damgalı kanıt alıntısı taşır; uydurma sorumlu/tarih yazılmaz (yoksa "belirtilmemiş").
- **Kabul:** 10 toplantıda aksiyon yakalama recall'u ≥ %85; kanıtsız aksiyon oranı 0.
- **Meta:** P2 · M · Bağ: MM-01, HAL-08 · Durum: açık

#### MM-03 · Metinden konuşmaya (TTS)
- **Sorun:** [ÖNERİ] Sesli okuma yok.
- **Değişiklik:** Yerel Türkçe TTS (Piper); yanıtı dinleme düğmesi; kod/tablo bloklarını okumama, sayı/kısaltma normalizasyonu; ses önbelleği.
- **Kabul:** Türkçe örnek metinlerde anlaşılabilirlik ≥ 4/5 (insan ölçeği); kod blokları sese dahil edilmez (test).
- **Meta:** P3 · M · Bağ: DEF-15 · Durum: açık

#### MM-04 · Görsel anlama (VQA) ve OCR
- **Sorun:** [DOĞRULANDI: F10] Görsel yönlendirme master modeline düşüyor; grafik/diyagram okuma kalitesi ölçülmemiş.
- **Değişiklik:** VLM ile görsel soru-cevap, ekran görüntüsü/diyagram/grafik okuma, el yazısı/OCR; "okuyamadım" davranışı; belirsiz bölgelerin işaretlenmesi.
- **Kabul:** 60 görsellik sette soru doğruluğu ≥ %75 (VLM sınırı dahilinde); okunamayan metinde uydurma yerine "okunamadı" (≥ %90).
- **Meta:** P2 · M · Bağ: DEF-05 · Durum: açık

#### MM-05 · Görsel üretim
- **Sorun:** [DOĞRULANDI] Parametrik SVG/PNG motoru var; gerçek difüzyon modeli köprüsü yok veya doğrulanmamış.
- **Değişiklik:** Yerel difüzyon (ComfyUI/diffusers) köprüsü (GPU varsa), parametrik SVG yedek; kullanım koşulları, üretim meta verisi ve filigran seçeneği; üretim sonrası görsel kalite denetimi.
- **Kabul:** GPU varken fotogerçekçi/illüstrasyon isteği difüzyonla, yoksa net mesajla SVG yedeğiyle yanıtlanır; üretilen her görselde `üretildi` meta verisi var.
- **Meta:** P3 · L · Bağ: DEF-15 · Durum: açık

#### MM-06 · Görsel düzenleme
- **Sorun:** [DOĞRULANDI] Pillow/OpenCV işlemleri var; geri alınabilirlik ve kalite denetimi belirsiz.
- **Değişiklik:** Kırp, yeniden boyutlandır, döndür, arka plan kaldırma, renk/kontrast; her işlem artefakt sürümü olur (geri alınır).
- **Kabul:** İşlem sonrası orijinal korunur; 20 düzenleme isteğinde doğru işlem uygulama ≥ %95.
- **Meta:** P3 · M · Bağ: ORC-17 · Durum: açık

#### MM-07 · Video analizi
- **Sorun:** [DOĞRULANDI] `media_analyzer` bağlı değil.
- **Değişiklik:** Anahtar kare çıkarma + ses transkripti → zaman çizelgeli özet; kare açıklamaları VLM ile; uzun video için örnekleme stratejisi.
- **Kabul:** 10 videoda özetin kritik olay recall'u ≥ %75; her olay zaman damgası taşır.
- **Meta:** P3 · L · Bağ: MM-01, MM-04 · Durum: açık

#### MM-08 · Belge tarama ve temizleme
- **Sorun:** [DOĞRULANDI] `scan_and_clean_document_image` var; ölçülmemiş.
- **Değişiklik:** Perspektif düzeltme, gölge giderme, eşikleme; önce/sonra OCR doğruluğu ölçümü; başarısızlıkta orijinali koruma.
- **Kabul:** 30 eğik/gölgeli belge fotoğrafında OCR doğruluğu temizlemeyle ≥ 10 puan artar.
- **Meta:** P3 · M · Bağ: RAG-03 · Durum: açık

#### MM-09 · KVKK/PII anonimleştirme (metin + görsel)
- **Sorun:** [DOĞRULANDI: F4] PII maskeleme yalnız anahtar kelime tetiklemeli ve ölçülmemiş.
- **Değişiklik:** TCKN (algoritmik doğrulama), IBAN, telefon, e-posta, plaka, adres kalıpları + NER; görselde yüz/plaka bulanıklaştırma; ölçüm: recall ≥ %95, yanlış alarm < %5.
- **Kabul:** Etiketli 200 metin/50 görselde hedef recall sağlanır; maskelenen veri geri çıkarılamaz (orijinal saklanmaz).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MM-10 · Diyagram üretimi (Mermaid/Graphviz) ve doğrulama
- **Sorun:** [DOĞRULANDI] Sohbette mermaid bloğu çiziliyor; sözdizimi hatalı diyagram kullanıcıya bozuk gidiyor.
- **Değişiklik:** Yerel Mermaid/Graphviz render ve sözdizimi doğrulama; hatalıysa otomatik onarım (en fazla 2 tur); SVG/PNG çıktı.
- **Kabul:** 100 diyagram isteğinde render başarısı ≥ %95 (onarım dahil).
- **Meta:** P2 · M · Bağ: GW-11 · Durum: açık

#### MM-11 · Bilimsel şekil ve grafik üretimi
- **Sorun:** [ÖNERİ] Şekiller rapor/tez için vektörel ve düzenlenebilir olmalı.
- **Değişiklik:** Yerel çizim kütüphanesi ile (matplotlib benzeri) kod → SVG/PDF; eksen/birim/lejant denetimi; kod saklanır, yeniden üretilebilir.
- **Kabul:** 30 şekil isteğinde etiketli eksen/birim oranı %100; çıktı vektörel.
- **Meta:** P3 · M · Bağ: DS-03 · Durum: açık

#### MM-12 · Ses dosyası işleme ve mikrofon dayanıklılığı
- **Sorun:** [DOĞRULANDI] Mikrofon kaydı WAV ile yerel; izin ve hata durumları, büyük dosyalar sınırlı.
- **Değişiklik:** İzin reddi/cihaz yok/uzun kayıt durumları için net hatalar; dönüştürme/kırpma; ses dosyası boyut sınırı ve akışlı işleme.
- **Kabul:** İzin verilmediğinde arayüz yönlendirici mesaj gösterir (e2e); 200 MB ses belleği şişirmeden işlenir.
- **Meta:** P2 · S · Bağ: MM-01 · Durum: açık

#### MM-13 · Çok modlu mesaj işleme hattı
- **Sorun:** [DOĞRULANDI: F9] `_prepare_chat_request` dosya türüne göre uzun `if/elif` zinciri; bir işleyicinin hatası tüm isteği etkileyebilir.
- **Değişiklik:** Tür → işleyici kaydı (ek işleyicisi arayüzü); her işleyici bağımsız, zaman aşımlı, hata izolasyonlu; çoklu ek bir mesajda desteklenir; sonuçlar yapılandırılmış "ek bağlamı" olarak birleşir.
- **Kabul:** Bir işleyici çökerse diğer ekler işlenir ve kullanıcı hangi ekin başarısız olduğunu görür; yeni dosya türü eklemek tek dosyalık işleyici gerektirir.
- **Meta:** P0 · M · Bağ: ORC-01 · Durum: açık

#### MM-14 · Medya yaşam döngüsü ve yetkilendirme
- **Sorun:** [DOĞRULANDI: F20] `/api/assistant/media/{filename}` kimlik/yetki denetimi olmadan üretilmiş medyayı sunuyor; süre sonu temizliği yok.
- **Değişiklik:** İmzalı/yetkili URL'ler (kullanıcıya bağlı), kota, süreli temizlik, dosya adı tahmin edilemezliği (rastgele kimlik), türüne uygun `Content-Type` ve `Content-Disposition`.
- **Kabul:** Başka kullanıcı veya oturumsuz istek medyayı alamaz (test); süresi dolan medya silinir ve 404 döner.
- **Meta:** P1 · M · Bağ: SEC-03, DAT-05 · Durum: açık
