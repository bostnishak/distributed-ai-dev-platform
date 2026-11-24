# Parça 4 — Model/gateway/ML (MDL) ve alan uzmanlıkları (ALN)

## MDL · Model gateway, yönlendirme, niyet ve makine öğrenmesi

#### MDL-01 · Niyet sınıflandırıcı ölçümü (ORC-02)
- **Sorun:** [ÖNERİ] 600 örnekte makro-F1 ≥ 0.90 hedefi ölçülmedi.
- **Değişiklik:** Dışlanmış 600 örnek ve F1 raporu.
- **Kabul:** Makro-F1 ölçülür ve ≥ 0.90 değilse maddeyi partial bırakır.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### MDL-02 · Niyet sınıflandırma süresi ölçümü
- **Sorun:** [ÖNERİ] < 30 ms hedefi ölçülmedi.
- **Değişiklik:** Süre benchmark'ı.
- **Kabul:** Ortalama < 30 ms.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### MDL-03 · Niyet taksonomisi: her niyet için ≥ 20 örnek ve senaryo
- **Sorun:** [ÖNERİ] ORC-03 örnek sayısı kısmen.
- **Değişiklik:** Eksik niyetler için örnek ve uçtan uca test.
- **Kabul:** Her niyet ≥ 20 örnek ve 1 senaryo testi.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-04 · Taksonomi dışı isteklerin keşif günlüğü
- **Sorun:** [ÖNERİ] Genel sohbet'e düşenler kaydedilmiyor.
- **Değişiklik:** Maskeli günlük ve aylık küme analizi.
- **Kabul:** Günlük dosyası ve rapor var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-05 · Netleştirme sorusu eşiği
- **Sorun:** [ÖNERİ] Belirsiz isteklerde varsayım yapılıyor.
- **Değişiklik:** Güven < eşik → tek soru.
- **Kabul:** Belirsiz 50 istemin %80'inde soru.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-06 · Çok niyetli isteklerin ayrıştırılması ölçümü (ORC-04)
- **Sorun:** [ÖNERİ] 30 birleşik isteğin %90'ı ölçülmedi.
- **Değişiklik:** 30 isteklik set.
- **Kabul:** ≥ %90 doğru alt görev listesi ve sırası.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-07 · Planlayıcı kalite ölçümü (ORC-05)
- **Sorun:** [ÖNERİ] 40 senaryo %85 ölçülmedi.
- **Değişiklik:** 40 senaryo ve kontrol listesi.
- **Kabul:** Plan kalitesi ≥ %85.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-08 · Plan maliyet/süre tahmini doğruluğu
- **Sorun:** [ÖNERİ] Tahmin gerçekle karşılaştırılmıyor.
- **Değişiklik:** Tahmin ve gerçek farkı günlüğü.
- **Kabul:** Medyan hata ≤ %40.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-09 · Pahalı planlarda kullanıcı onayı
- **Sorun:** [ÖNERİ] Pahalı plan sessiz çalışabilir.
- **Değişiklik:** Eşik üstü maliyette onay.
- **Kabul:** Eşik üstü plan onaysız başlamaz.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-10 · DAG yürütücü: başarısız adımda yalnız bağımlıları etkilenir
- **Sorun:** [ÖNERİ] ORC-06 testi var ama gerçek hat ile bağlı mı belirsiz.
- **Değişiklik:** Gerçek hatta hata enjeksiyon testi.
- **Kabul:** Bir adım düşünce bağımsız adımlar tamamlanır.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### MDL-11 · Adım yeniden denemesi → alternatif araç → yeniden plan
- **Sorun:** [ÖNERİ] Kademeli geri dönüş kısmen.
- **Değişiklik:** Üç kademe testi.
- **Kabul:** Her kademe sırasıyla denenir (test).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-12 · Araç kayıt defteri şema doğrulaması (ORC-08)
- **Sorun:** [ÖNERİ] Şemaya uymayan çağrı reddi kısmen.
- **Değişiklik:** Tüm araçlar için girdi/çıktı şeması.
- **Kabul:** Şemaya uymayan çağrı çalıştırılmaz.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-13 · Araç belge üretimi
- **Sorun:** [ÖNERİ] Araç listesi belgelenmiyor.
- **Değişiklik:** Kayıt defterinden OpenAPI benzeri belge.
- **Kabul:** Belge yeni araçla otomatik güncellenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-14 · Dinamik `num_ctx` ve model ısınma ölçümü (GW-06)
- **Sorun:** [ÖNERİ] Peş peşe 10 istekte yeniden yükleme 0 ölçülmedi.
- **Değişiklik:** Gerçek Ollama ile ölçüm.
- **Kabul:** 10 istekte yeniden yükleme sayısı 0.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-15 · Bağlam penceresi aşımında strateji ve şeffaflık (GW-05)
- **Sorun:** [ÖNERİ] Strateji kaydı kısmen.
- **Değişiklik:** Seçilen strateji yanıt meta verisinde.
- **Kabul:** Aşım senaryosunda strateji ve `ctx_used/ctx_max` görünür.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-16 · Tokenizer doğruluğu
- **Sorun:** [ÖNERİ] Token sayacı tahmini.
- **Değişiklik:** Model ailesine göre gerçek tokenizer.
- **Kabul:** Sayım Ollama sayımından ≤ %5 sapar.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-17 · Decoding profilleri: extract şeması uyumu (GW-07)
- **Sorun:** [ÖNERİ] `extract` 20 örnekte %100 şema uyumu ölçülmedi.
- **Değişiklik:** 20 örnek şema testi.
- **Kabul:** Şema uyumu %100.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-18 · Olgusal doğruluk T=0.1 ve 0.7 karşılaştırması (DEF-09)
- **Sorun:** [ÖNERİ] Doğruluk düşmüyor kanıtı yok.
- **Değişiklik:** Aynı sette iki sıcaklık.
- **Kabul:** 0.1 sıcaklığı ≥ 0.7'ye göre doğruluk.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-19 · Aynı sorunun 5 kez tutarlılığı
- **Sorun:** [ÖNERİ] Anlamsal tutarlılık ≥ %95 ölçülmedi.
- **Değişiklik:** 5 tekrar ve gömme benzerliği.
- **Kabul:** Olgusal sorularda ≥ %95.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-20 · Zaman aşımı/yeniden deneme/devre kesici testleri (GW-08)
- **Sorun:** [ÖNERİ] Hata türlerinin her biri için test kısmen.
- **Değişiklik:** 5 hata sınıfı enjeksiyon testi.
- **Kabul:** Her hata sınıfı doğru davranış.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-21 · Ollama kapalıyken kullanıcı yönergesi
- **Sorun:** [ÖNERİ] Yanıt "Ollama'ya ulaşılamıyor, şu adımları dene" içermeli.
- **Değişiklik:** Eyleme dönük metin ve runbook bağlantısı.
- **Kabul:** Mesaj test edilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-22 · İstek kuyruğu: etkileşimli öncelik yük testi (GW-09)
- **Sorun:** [ÖNERİ] Arka planda 3 ağır iş varken ilk token < 2 sn ölçülmedi.
- **Değişiklik:** Yük testi (sahte Ollama).
- **Kabul:** İlk token < 2 sn.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-23 · İptal yayılımı: Durdur sonrası Ollama isteği 1 sn
- **Sorun:** [ÖNERİ] Ölçülmedi.
- **Değişiklik:** İptal testi.
- **Kabul:** Ollama bağlantısı 1 sn içinde kapanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-24 · Sıcak model yönlendirme testi (GW-10)
- **Sorun:** [ÖNERİ] Eşdeğer ajanda sıcak olan seçilir testi kısmen.
- **Değişiklik:** Seçim testi ve 8 GB VRAM simülasyonu.
- **Kabul:** Sıralı konsey OOM vermez (simüle).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-25 · Model registry: yeni model koda dokunmadan seçilir (DEF-10)
- **Sorun:** [ÖNERİ] Test kısmen.
- **Değişiklik:** Registry'ye model ekleyip seçim testi.
- **Kabul:** Yeni model uygun görevde seçilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-26 · Seçim gerekçesinin yanıt meta verisinde
- **Sorun:** [ÖNERİ] Gerekçe kayıtla uyumu.
- **Değişiklik:** `selection` kaydı ile gerekçe eşitliği testi.
- **Kabul:** Gerekçe kayıtla birebir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-27 · Model kalite benchmark'ı: yerel küme
- **Sorun:** [ÖNERİ] Modeller karşılaştırılmıyor.
- **Değişiklik:** Görev başına 50 soruluk set, 4B/9B/14B karşılaştırması.
- **Kabul:** Model × görev tablosu üretilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-28 · Quantization seviyesi karşılaştırması
- **Sorun:** [ÖNERİ] Q4/Q8 etkisi ölçülmedi.
- **Değişiklik:** Aynı sette farklı nicemleme.
- **Kabul:** Kalite/hız tablosu.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-29 · Model terfi kapısı: eval şartı
- **Sorun:** [ÖNERİ] Yeni model eval'siz seçilebilir.
- **Değişiklik:** Terfi için eşik.
- **Kabul:** Eşik altı model terfi edemez.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-30 · Model lisans ve kullanım notları
- **Sorun:** [ÖNERİ] Lisans bilgisi dağınık.
- **Değişiklik:** Registry'de lisans alanı.
- **Kabul:** Her model lisans alanı dolu.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### MDL-31 · Prompt şablon sürümleme ve gerileme (GW-16)
- **Sorun:** [ÖNERİ] Prompt'lar kodda gömülü kalabilir.
- **Değişiklik:** 10 satırdan uzun gömülü prompt lint'i.
- **Kabul:** Lint temiz; şablon değişikliğinde eval raporu.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-32 · Sistem istemi katman testleri (GW-17)
- **Sorun:** [ÖNERİ] Selamlama hafıza boş testi kısmen.
- **Değişiklik:** Katman sırası snapshot ve bütçe testi.
- **Kabul:** Snapshot testi var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-33 · Kullanıcı tercihi ("emoji yok") uygulanması
- **Sorun:** [ÖNERİ] Tercih bazı modlarda unutuluyor.
- **Değişiklik:** Tercihlerin tüm modlarda uygulanması testi.
- **Kabul:** Emoji yasağı 100 yanıtta %100.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-34 · Konuşma durumu: 100 turluk kısıt koruma (ORC-14)
- **Sorun:** [ÖNERİ] Ölçülmedi.
- **Değişiklik:** 100 turluk senaryo.
- **Kabul:** İlk 5 turdaki kısıt son turda uygulanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-35 · Dil algılama doğruluğu (ORC-20)
- **Sorun:** [ÖNERİ] 100 karışık örnek ölçülmedi.
- **Değişiklik:** 100 örnekli set.
- **Kabul:** Doğru dil ≥ %95.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-36 · Kod blokları ve terimlerin çeviriden korunması
- **Sorun:** [ÖNERİ] Çeviri kodu bozabilir.
- **Değişiklik:** Kod bloğu maskeleme ve geri koyma.
- **Kabul:** Kod blokları bayt bayt aynı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-37 · Zorluk tahmini (ML-02) ölçümü
- **Sorun:** [ÖNERİ] Zorluk tahmini yönlendirmeye faydası ölçülmedi.
- **Değişiklik:** Kalibre zorluk ve yönlendirme sonucu.
- **Kabul:** Basit sorularda büyük model kullanımı düşer.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-38 · Maliyet-kalite kademesi kayıtları (ORC-18)
- **Sorun:** [ÖNERİ] Karar kaydı var, analizi yok.
- **Değişiklik:** Karar dağılımı panosu.
- **Kabul:** Kademe oranları görünür.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-39 · Selamlama/hesapta doğrulama atlama testi
- **Sorun:** [ÖNERİ] Test kısmen.
- **Değişiklik:** Atlama ve yüksek risk doğrulama testi.
- **Kabul:** Selamlamada doğrulama aşaması yok.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-40 · Korumaların hat entegrasyonu: ihlal ve geçiş (ORC-19)
- **Sorun:** [ÖNERİ] Her koruma için iki test.
- **Değişiklik:** `guard_in`/`guard_out` ihlal+geçiş testleri.
- **Kabul:** Her koruma iki testli.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-41 · Engelleme nedeninin anlaşılır metni
- **Sorun:** [ÖNERİ] Engelleme mesajları teknik.
- **Değişiklik:** Mesaj sözlüğü.
- **Kabul:** Her engelleme türü için Türkçe metin.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-42 · Makine öğrenmesi modellerinin sürümlenmesi (ML-01)
- **Sorun:** [ÖNERİ] Sınıflandırıcı sürümü izlenmiyor.
- **Değişiklik:** Model kartı ve sürüm.
- **Kabul:** Her model sürüm ve veri özeti taşır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-43 · ML veri kümesi sürümleme ve veri kartı
- **Sorun:** [ÖNERİ] Veri kümeleri sürümsüz.
- **Değişiklik:** Karma, kaynak, tarih.
- **Kabul:** Veri kümesi değişince sürüm artar.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-44 · DPO/ince ayar verisi toplama onayı
- **Sorun:** [ÖNERİ] Kullanıcı verisi eğitime girmeden onay.
- **Değişiklik:** Açık onay ve maskeleme.
- **Kabul:** Onaysız veri eğitim kümesine girmez.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### MDL-45 · LoRA ince ayar hattı denemesi
- **Sorun:** [ÖNERİ] İnce ayar yalnız plan.
- **Değişiklik:** Küçük görev için LoRA denemesi (örn. kaçınma).
- **Kabul:** Kazanç ölçülür; yoksa yapılmaz.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-46 · Kalibratör (ML-03) güncelleme döngüsü
- **Sorun:** [ÖNERİ] Kalibratör bir kez eğitildi.
- **Değişiklik:** Geri bildirimle haftalık güncelleme.
- **Kabul:** Kalibratör sürümü ve ECE izlenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### MDL-47 · Çevrimdışı mod: tüm model yolu
- **Sorun:** [ÖNERİ] İnternet kesilince davranış.
- **Değişiklik:** Çevrimdışı mod testi.
- **Kabul:** Ağ yokken sohbet ve RAG çalışır.
- **Meta:** P2 · S · Bağ: - · Durum: açık

## ALN · Alan uzmanlıkları: mühendislik, hukuk, finans, sağlık, eğitim, günlük görevler

#### ALN-01 · CNC/G-kod doğrulama: 30 hatalı örnek (DOM-08)
- **Sorun:** [ÖNERİ] Yakalama oranı ölçülmedi.
- **Değişiklik:** 30 bilerek hatalı G-kod seti.
- **Kabul:** Yakalama ≥ %85; uyarı daima var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-02 · CNC fizik formülleri: 15 literatür vakası (DOM-07)
- **Sorun:** [ÖNERİ] Sapma ölçülmedi.
- **Değişiklik:** Ders kitabı vakaları.
- **Kabul:** Sapma ≤ %5; sınır dışında uyarı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-03 · Matematik araç zinciri: 200 vaka (DOM-10)
- **Sorun:** [ÖNERİ] Doğruluk ölçülmedi.
- **Değişiklik:** 200 vakalık set.
- **Kabul:** Araç doğruluğu ≥ %95.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-04 · Matematik: iki yöntemle çapraz kontrol
- **Sorun:** [ÖNERİ] Tek yöntem.
- **Değişiklik:** Sembolik + sayısal.
- **Kabul:** İki yöntem uyuşmazsa uyarı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-05 · Birim analizi ve boyut denetimi
- **Sorun:** [ÖNERİ] Birim hataları.
- **Değişiklik:** Pint benzeri birim kontrolü.
- **Kabul:** Birim uyuşmazlığı yakalanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-06 · Hukuk: sorumluluk reddi ve kaynak zorunluluğu
- **Sorun:** [ÖNERİ] Hukuk soruları kaynak göstermeyebilir.
- **Değişiklik:** Mevzuat kaynağı arama ve atıf.
- **Kabul:** Hukuk yanıtlarının %100'ünde atıf ve uyarı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-07 · Türk mevzuatı bilgi tabanı
- **Sorun:** [ÖNERİ] Mevzuat içeriği yok.
- **Değişiklik:** Mevzuat metinleri RAG koleksiyonu.
- **Kabul:** Madde numarası atıfları doğru (50 örnek).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-08 · Sözleşme risk analizi: yalnız belgeden
- **Sorun:** [ÖNERİ] Belge yokken analiz (F5).
- **Değişiklik:** Belge zorunluluğu testi.
- **Kabul:** Belgesiz istekte analiz yok.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-09 · Finans: kullanıcı verisi olmadan örnek veriyle hesap yok (F4)
- **Sorun:** [ÖNERİ] Test var; kapsam genişletme.
- **Değişiklik:** Tüm finans araçlarında girdi zorunluluğu.
- **Kabul:** Eksik girdide hesap yapılmaz.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-10 · Finans: formül doğrulaması (NPV/IRR/DCF)
- **Sorun:** [ÖNERİ] Formül testleri sınırlı.
- **Değişiklik:** Bilinen vakalarla test.
- **Kabul:** 10 vaka sonucu hesap tablosuyla eşit.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-11 · Finansal tavsiye reddi çerçevesi
- **Sorun:** [ÖNERİ] Yatırım tavsiyesi verilmemeli.
- **Değişiklik:** Tavsiye niyeti algılama ve yönlendirme.
- **Kabul:** Tavsiye isteğinde uyarı ve bilgilendirme.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-12 · Sağlık: tanı koymama ve acil yönlendirme
- **Sorun:** [ÖNERİ] Tıbbi sorularda risk.
- **Değişiklik:** Acil durum kalıpları ve yönlendirme.
- **Kabul:** Acil ifadelerde 112 yönlendirmesi.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-13 · Sağlık: kaynaklı yanıt
- **Sorun:** [ÖNERİ] Kaynaksız sağlık bilgisi.
- **Değişiklik:** Güvenilir kaynak zorunluluğu.
- **Kabul:** Sağlık yanıtlarının %100'ü atıflı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-14 · Eğitim: seviye ve müfredat uyumu
- **Sorun:** [ÖNERİ] Seviye uyarlama genel.
- **Değişiklik:** Seviye + müfredat etiketi.
- **Kabul:** Seviye değişince dil/örnek değişir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-15 · Eğitim: öğrenci ilerleme takibi
- **Sorun:** [ÖNERİ] İlerleme yok.
- **Değişiklik:** Konu bazlı ilerleme kaydı.
- **Kabul:** Zayıf konular listelenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-16 · Günlük görevler: e-posta taslağı, plan, liste
- **Sorun:** [ÖNERİ] Genel görev şablonu.
- **Değişiklik:** Görev şablonları.
- **Kabul:** 10 görevde biçim doğru.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-17 · Takvim/hatırlatma entegrasyonu (yerel)
- **Sorun:** [ÖNERİ] Yok.
- **Değişiklik:** Yerel takvim dosyası (.ics) üretimi.
- **Kabul:** .ics geçerli.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-18 · Seyahat/rota/hesap gibi güncel veri soruları
- **Sorun:** [ÖNERİ] Güncel veri sorusu web gerektirir.
- **Değişiklik:** Web zorunluluğu ve tarih damgası.
- **Kabul:** Yanıt tarih damgalı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-19 · Elektronik/devre/mimari mühendislik hesapları
- **Sorun:** [ÖNERİ] Alan araçları sınırlı.
- **Değişiklik:** Ohm, kiriş, ısı denklem araçları.
- **Kabul:** Beş hesap doğru.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-20 · CAD/DXF analiz doğruluğu
- **Sorun:** [ÖNERİ] DXF okuma kısmen.
- **Değişiklik:** DXF ölçü çıkarımı testi.
- **Kabul:** Örnek DXF ölçüleri doğru.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-21 · CNC: sapma raporu ve ölçüm entegrasyonu (CMM)
- **Sorun:** [ÖNERİ] Kapalı döngü kısmen.
- **Değişiklik:** Örnek CMM verisi ile test.
- **Kabul:** Düzeltme ofseti hesabı doğru.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-22 · ERP/MES çizelgeleme doğruluğu
- **Sorun:** [ÖNERİ] Çizelgeleyici testleri sınırlı.
- **Değişiklik:** Optimal çizelge doğrulama.
- **Kabul:** Küçük örnekte optimal çözüm.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-23 · İstatistik/ML AutoML sonuç dürüstlüğü
- **Sorun:** [ÖNERİ] AutoML başarı iddiası.
- **Değişiklik:** Çapraz doğrulama ve sızıntı denetimi.
- **Kabul:** Rapor sızıntı uyarısı verir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-24 · Veri bilimi: görselleştirme doğruluğu
- **Sorun:** [ÖNERİ] Grafik eksenleri yanıltabilir.
- **Değişiklik:** Eksen/ölçek denetimi.
- **Kabul:** Kesik eksen uyarısı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-25 · Alan sorusu yönlendirme doğruluğu
- **Sorun:** [ÖNERİ] Alan niyeti yanlış yönlenebilir.
- **Değişiklik:** Alan niyeti etiketli set.
- **Kabul:** Alan yönlendirme F1 ≥ 0.9.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-26 · Çok alanlı sorular
- **Sorun:** [ÖNERİ] Birden çok alanı kapsayan sorular.
- **Değişiklik:** Alt görevlere ayırma.
- **Kabul:** Bileşik soruda her alan için kaynak.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-27 · Alan uzman kartları ve sınırlar
- **Sorun:** [ÖNERİ] Alan kapsamı belirsiz.
- **Değişiklik:** Her alan için "yapabilir/yapamaz" kartı.
- **Kabul:** Kartlar arayüzde.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### ALN-28 · Örnek veri ile demo alan senaryoları
- **Sorun:** [ÖNERİ] Alan demoları.
- **Değişiklik:** Her alan için 1 demo.
- **Kabul:** Demo betiği çalışır.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### ALN-29 · Alan yanıtlarında birim ve standart atfı
- **Sorun:** [ÖNERİ] Standart atfı yok.
- **Değişiklik:** ISO/TS standart atıf.
- **Kabul:** Standart adı ve sürümü atıflı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### ALN-30 · Kullanıcı terim sözlüğü (ORC-20)
- **Sorun:** [ÖNERİ] Alana özgü terimler çevrilir.
- **Değişiklik:** Kullanıcı sözlüğü.
- **Kabul:** Sözlük terimleri değişmez.
- **Meta:** P1 · M · Bağ: - · Durum: açık
