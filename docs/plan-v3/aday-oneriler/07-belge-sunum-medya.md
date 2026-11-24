# Parça 7 — Araştırma, sunum, belge, veri, medya (BEL)

## BEL · Araştırma, sunum, belge, veri analizi ve medya

#### BEL-01 · Araştırma: ilgisiz kaynak oranı ölçümü (RES-02)
- **Sorun:** [ÖNERİ] 20 konulu sette ilgisiz kaynak < %15 ölçülmedi.
- **Değişiklik:** 20 konu ve el etiketli alaka.
- **Kabul:** İlgisiz kaynak oranı raporlanır (< %15 hedef).
- **Meta:** P0 · L · Bağ: - · Durum: açık

#### BEL-02 · Araştırma çelişki yakalama (RES-03)
- **Sorun:** [ÖNERİ] 15 çelişkili çift ölçülmedi.
- **Değişiklik:** Bilerek çelişen kaynak çiftleri.
- **Kabul:** Çelişki yakalama ≥ %85.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-03 · Atıflı sentez: atıfsız olgusal cümle (RES-04)
- **Sorun:** [ÖNERİ] Oran ölçülmedi.
- **Değişiklik:** Rapor cümle denetimi.
- **Kabul:** Atıfsız olgusal cümle < %3.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-04 · Rapor biçimleri: kaynakça numara eşleşmesi (RES-05)
- **Sorun:** [ÖNERİ] Her biçimde otomatik denetim yok.
- **Değişiklik:** MD/DOCX/PDF/PPTX atıf-kaynakça eşleşme testi.
- **Kabul:** Numaralar metinle birebir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-05 · APA/IEEE/Vancouver kaynakça
- **Sorun:** [ÖNERİ] Yalnız APA.
- **Değişiklik:** IEEE ve Vancouver biçimleri.
- **Kabul:** Üç biçim testli.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-06 · Araştırma hız modları bütçesi (RES-08)
- **Sorun:** [ÖNERİ] Süre bütçesi aşımı ölçülmedi.
- **Değişiklik:** Hızlı/Standart/Derin ölçümü.
- **Kabul:** Hiçbir mod bütçeyi aşmaz.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-07 · Alt soruların ajanlarda hızlanması (RES-09)
- **Sorun:** [ÖNERİ] 3x hızlanma ölçülmedi.
- **Değişiklik:** 6 ajan, 8 alt soru.
- **Kabul:** ≥ 3x veya serisel kısım belgeli.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-08 · Sentez sonrası doğrulama özeti (RES-10)
- **Sorun:** [ÖNERİ] "32 iddia, 30 doğrulandı" gerçek sayıdan mı belirsiz.
- **Değişiklik:** Özet sayıları doğrulayıcıdan üretilir.
- **Kabul:** Elle yazılmış sayı yok.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-09 · Araştırma: kaynak arşivleme ve erişim tarihi
- **Sorun:** [ÖNERİ] Tarih/arşiv eksik.
- **Değişiklik:** Erişim tarihi ve arşiv metni.
- **Kabul:** Her kaynak erişim tarihli.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-10 · Araştırma: kullanıcı kapsam sorusu
- **Sorun:** [ÖNERİ] Geniş konuda doğrudan arama.
- **Değişiklik:** Kapsam/derinlik sorusu.
- **Kabul:** Belirsiz konuda 1 soru.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-11 · Araştırma: çok dilli kaynak
- **Sorun:** [ÖNERİ] Yalnız Türkçe/İngilizce.
- **Değişiklik:** Sorgu çeşitlendirme ve çeviri notu.
- **Kabul:** İngilizce kaynak Türkçe özetlenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-12 · Sunum: gerçek grafik nesneleri (PPT-04)
- **Sorun:** [ÖNERİ] Veri slaytlarında gerçek grafik oranı ölçülmedi.
- **Değişiklik:** python-pptx chart ve oran testi.
- **Kabul:** Veri slaytlarının ≥ %80'i gerçek grafik.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-13 · Sunum: alt metin ve kaynak notu
- **Sorun:** [ÖNERİ] Alt metin boş olabilir.
- **Değişiklik:** Alt metin üretimi ve denetim.
- **Kabul:** Boş alt metin yok.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-14 · Sunum geçişleri XML şeması (PPT-05)
- **Sorun:** [ÖNERİ] 30 dosya açılış testi yok.
- **Değişiklik:** Şema doğrulama ve LibreOffice açma.
- **Kabul:** 30 dosya hatasız açılır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-15 · Konuşmacı notları ve kaynak slaytı (PPT-06)
- **Sorun:** [ÖNERİ] Olgusal slaytta kaynak kuralı.
- **Değişiklik:** Kural denetimi.
- **Kabul:** Her olgusal slaytta kaynak notu.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-16 · Render ve görsel kalite denetimi (PPT-07)
- **Sorun:** [ÖNERİ] LibreOffice render yok.
- **Değişiklik:** Başsız render, taşma/çakışma/kontrast kuralları.
- **Kabul:** Görsel hata oranı < %3.
- **Meta:** P1 · L · Bağ: - · Durum: açık

#### BEL-17 · Slayt düzeni: taşma ve metin sığdırma
- **Sorun:** [ÖNERİ] Uzun metin taşabilir.
- **Değişiklik:** Otomatik yazı boyutu/böl.
- **Kabul:** Taşan slayt 0 (render denetimi).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-18 · Sunum teması ve marka tutarlılığı
- **Sorun:** [ÖNERİ] Tema seçeneği sınırlı.
- **Değişiklik:** Tema kitaplığı ve renk uyumu.
- **Kabul:** Tüm slaytlar tema renklerini kullanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-19 · Sunum görselleri: SVG diyagramlar
- **Sorun:** [ÖNERİ] Diyagram azlığı.
- **Değişiklik:** Süreç/hiyerarşi/zaman çizelgesi üreteci.
- **Kabul:** Diyagram slaytı doğru çizilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-20 · Sunumun düzenlenebilir çıktısı
- **Sorun:** [ÖNERİ] Yalnız dosya.
- **Değişiklik:** Yeniden üretmeden slayt düzenleme.
- **Kabul:** Tek slayt yeniden üretilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-21 · Belge şablon kitaplığı (DOC-04)
- **Sorun:** [ÖNERİ] Şablonlar kısmen.
- **Değişiklik:** 9 şablon ve alan şeması.
- **Kabul:** Her şablon doğrulama paketinden geçer.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-22 · DOCX içindekiler, başlık stilleri, sayfa numarası
- **Sorun:** [ÖNERİ] Biçimlendirme temel.
- **Değişiklik:** Stil, TOC, alt bilgi.
- **Kabul:** DOCX açılır ve TOC doğru.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-23 · PDF çıktısı: Türkçe karakter ve yazı tipi
- **Sorun:** [ÖNERİ] Türkçe karakter bozulabilir.
- **Değişiklik:** Gömülü yazı tipi testi.
- **Kabul:** ğüşıöç doğru görünür.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-24 · Rakamlı içerikte hesap izi (DOC-09)
- **Sorun:** [ÖNERİ] Kaynaksız sayı oranı ölçülmedi.
- **Değişiklik:** Dipnot/yorum ve HAL-09.
- **Kabul:** Kaynaksız/hesapsız sayı < %2.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-25 · Belgeler arası karşılaştırma/özetleme
- **Sorun:** [ÖNERİ] Çoklu belge karşılaştırma zayıf.
- **Değişiklik:** Fark tablosu.
- **Kabul:** İki belgenin farkı listelenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-26 · Veri analizi: tahmin yalnız istenince (DEF-06)
- **Sorun:** [ÖNERİ] Test kısmen.
- **Değişiklik:** Niyet testi.
- **Kabul:** Özet isteğinde tahmin satırı yok.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-27 · Veri analizi: belirsizlik aralığı
- **Sorun:** [ÖNERİ] Tahmin aralığı yok.
- **Değişiklik:** Tahmin aralığı ve yöntem notu.
- **Kabul:** Tahmin çıktısı aralık içerir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-28 · Veri analizi: grafik çizimi ve veri doğrulama
- **Sorun:** [ÖNERİ] Grafik kısmen.
- **Değişiklik:** Otomatik grafik, eksik değer raporu.
- **Kabul:** CSV'de eksik değer raporu.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-29 · Büyük CSV akışlı işleme
- **Sorun:** [ÖNERİ] Bellek şişebilir.
- **Değişiklik:** Parçalı okuma.
- **Kabul:** 500 MB CSV işlenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-30 · SQL aracı: yalnız okuma ve şema farkındalığı
- **Sorun:** [ÖNERİ] SQL güvenliği kısmen.
- **Değişiklik:** Salt-okunur bağlantı, sorgu doğrulama.
- **Kabul:** Yazma sorgusu reddedilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-31 · Tablo çıkarımı: PDF/görsel tablolar (DOC-07)
- **Sorun:** [ÖNERİ] 50 tablo doğruluk ölçülmedi.
- **Değişiklik:** Etiketli tablo seti.
- **Kabul:** Hücre doğruluğu ≥ %95.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-32 · Görsel anlama VQA ve OCR (MM-04)
- **Sorun:** [ÖNERİ] 60 görselde doğruluk ölçülmedi.
- **Değişiklik:** 60 görsellik set.
- **Kabul:** Doğruluk ≥ %75; okunamayanda "okunamadı" ≥ %90.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-33 · Görsel üretim: yerel difüzyon
- **Sorun:** [ÖNERİ] Görsel üretimi yok/zayıf.
- **Değişiklik:** Opsiyonel ComfyUI/SD bağlantısı.
- **Kabul:** Üretim kapalıysa net mesaj.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-34 · Video analizi (MM-07)
- **Sorun:** [ÖNERİ] 10 videoda recall ölçülmedi.
- **Değişiklik:** Anahtar kare + transkript.
- **Kabul:** Kritik olay recall ≥ %75.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-35 · Ses: konuşma→metin doğruluğu (WER)
- **Sorun:** [ÖNERİ] WER ölçülmedi.
- **Değişiklik:** Türkçe 30 klip WER.
- **Kabul:** WER raporlanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-36 · Metin→ses (TTS) Türkçe
- **Sorun:** [ÖNERİ] TTS ölçülmedi.
- **Değişiklik:** Yerel TTS seçeneği.
- **Kabul:** Türkçe cümle okunur.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-37 · 200 MB ses akışlı işleme (MM-12)
- **Sorun:** [ÖNERİ] Bellek şişirmeden işleme ölçülmedi.
- **Değişiklik:** Akışlı dönüştürme.
- **Kabul:** Bellek tepe < 300 MB.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-38 · Dosya dönüştürme doğruluğu
- **Sorun:** [ÖNERİ] Dönüştürme kalitesi ölçülmedi.
- **Değişiklik:** Çift yönlü dönüştürme seti.
- **Kabul:** Biçim kaybı raporlanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-39 · Çeviri aracı: belge biçimini koruma
- **Sorun:** [ÖNERİ] Çeviri biçimi bozar.
- **Değişiklik:** DOCX/PPTX biçim korumalı çeviri.
- **Kabul:** Biçim korunur (10 örnek).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-40 · Özet türleri: yönetici özeti, madde, tablo
- **Sorun:** [ÖNERİ] Tek özet türü.
- **Değişiklik:** Özet profilleri.
- **Kabul:** Seçilen profil çıktı biçimini belirler.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-41 · Ders anlatımı/konu anlatma modu
- **Sorun:** [ÖNERİ] Konu anlatımı genel.
- **Değişiklik:** Seviye uyarlama, örnek, alıştırma.
- **Kabul:** Seviye seçimi çıktıyı değiştirir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-42 · Alıştırma ve test üretimi + cevap anahtarı
- **Sorun:** [ÖNERİ] Sınav üretimi yok.
- **Değişiklik:** Soru, şık, anahtar, açıklama.
- **Kabul:** Cevap anahtarı doğru (örnek 20).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-43 · Programlama öğretmeni: çıktıyla uyum (DOM-11)
- **Sorun:** [ÖNERİ] Açıklamadaki çıktı sandbox'la uyumu ölçülmedi.
- **Değişiklik:** Çalıştırıp karşılaştırma.
- **Kabul:** "Çıktı şu olur" iddiaları sandbox çıktısıyla %100.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-44 · Konu haritası/zihin haritası çıktısı
- **Sorun:** [ÖNERİ] Görsel özet yok.
- **Değişiklik:** Mermaid zihin haritası.
- **Kabul:** Harita geçerli Mermaid.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-45 · Not/ders belgesinden bilgi kartı üretimi
- **Sorun:** [ÖNERİ] Çalışma kartı yok.
- **Değişiklik:** Soru-cevap kartları.
- **Kabul:** Kart sayısı ve doğruluk örneklemi.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-46 · CV/dilekçe/mektup biçimleri
- **Sorun:** [ÖNERİ] Belge şablonu kısmen.
- **Değişiklik:** Resmi yazı şablonları.
- **Kabul:** Şablon dolu örnek.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-47 · E-tablo üretimi: formüller çalışır
- **Sorun:** [ÖNERİ] XLSX formül doğrulama yok.
- **Değişiklik:** Formül hesaplama testi.
- **Kabul:** Üretilen XLSX formülleri hesaplanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-48 · Çok adımlı görev: araştırma → tablo → sunum zinciri
- **Sorun:** [ÖNERİ] Zincir e2e testi yok.
- **Değişiklik:** ORC-04 zinciri e2e.
- **Kabul:** Zincir çıktıları bağlantılı artefakt.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### BEL-49 · Çıktı adlandırma ve dosya düzeni
- **Sorun:** [ÖNERİ] Dosya adları rastgele.
- **Değişiklik:** Anlamlı ad ve tarih.
- **Kabul:** Dosya adı içerikten türetilir.
- **Meta:** P2 · S · Bağ: - · Durum: açık
