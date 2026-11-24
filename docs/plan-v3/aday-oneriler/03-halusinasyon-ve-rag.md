# Parça 3 — Halüsinasyon ölçümü (HLC) ve RAG/arama (RGX)

## HLC · Halüsinasyon azaltma ve ölçüm

#### HLC-01 · Türkçe etiketli olgusallık veri kümesi
- **Sorun:** [DOĞRULANDI: F112] Ölçümlerin çoğu şablon/sentetik; gerçek etiketli küme yok.
- **Değişiklik:** En az 500 soru-yanıt-kaynak üçlüsü, iki etiketleyici, uyum ölçümü.
- **Kabul:** Cohen κ ≥ 0.7; küme dosyası ve etiketleme kılavuzu depoda.
- **Meta:** P0 · L · Bağ: - · Durum: açık

#### HLC-02 · Etiketleyici uyumu (κ) hesaplayıcısı
- **Sorun:** [DOĞRULANDI: F112] κ hesaplayıcı yok.
- **Değişiklik:** `eval/agreement.py`; iki etiketleyici çıktısından κ.
- **Kabul:** Bilinen örnekte κ doğru hesaplanır (test).
- **Meta:** P0 · M · Bağ: HLC-01 · Durum: açık

#### HLC-03 · ECE ve güvenilirlik diyagramı
- **Sorun:** [DOĞRULANDI: F112] Kalibrasyon ECE'si gerçek veriyle ölçülmedi.
- **Değişiklik:** Etiketli kümede ECE ve 10 kutulu diyagram.
- **Kabul:** ECE raporlanır; hedef ≤ 0.08.
- **Meta:** P0 · M · Bağ: HLC-01 · Durum: açık

#### HLC-04 · NLI/atıf doğrulama modeli karşılaştırması
- **Sorun:** [ÖNERİ] ML-05 modelleri karşılaştırmadı.
- **Değişiklik:** 3 aday (çok dilli NLI, küçük LLM hakem, kural) etiketli çiftlerde karşılaştırılır.
- **Kabul:** Makro-F1 ve gecikme tablosu; seçim gerekçeli.
- **Meta:** P1 · M · Bağ: HLC-01 · Durum: açık

#### HLC-05 · Halüsinasyon türleri başına ayrı oran
- **Sorun:** [ÖNERİ] Tek "halüsinasyon oranı" türleri gizliyor.
- **Değişiklik:** Uydurma atıf, uydurma sayı, uydurma API, yanlış öncül, bağlam dışı türleri ayrı sayılır.
- **Kabul:** Rapor 5 tür için ayrı oran verir.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### HLC-06 · Düz model ile korumalı hat A/B karşılaştırması
- **Sorun:** [ÖNERİ] Karşılaştırma var ama 70 örnek ve tek model.
- **Değişiklik:** 300 örnek, üç model, güven aralıkları.
- **Kabul:** Her fark için %95 güven aralığı raporlanır.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### HLC-07 · Bootstrap güven aralıkları
- **Sorun:** [ÖNERİ] Yalnız nokta tahmin var.
- **Değişiklik:** Eval çalıştırıcısına bootstrap.
- **Kabul:** Her metrik ± aralık ile gösterilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-08 · Gerçek zamanlı kullanıcı geri bildirimiyle halüsinasyon ölçümü
- **Sorun:** [ÖNERİ] Üretimde gerçek oran bilinmiyor.
- **Değişiklik:** Geri bildirim "yanlış bilgi" oranı panoda.
- **Kabul:** Haftalık yanlış bilgi bildirimi oranı görünür.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-09 · Kaynaksız olgusal cümle denetimi
- **Sorun:** [ÖNERİ] Her olgusal cümle atıf taşımalı kuralı kısmen.
- **Değişiklik:** Cümle düzeyinde iddia çıkarımı ve atıf eşlemesi.
- **Kabul:** Atıfsız olgusal cümle oranı < %3 (eval).
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### HLC-10 · İddia çıkarma kalitesi
- **Sorun:** [ÖNERİ] İddia ayrıştırıcı basit.
- **Değişiklik:** Bağlaç/zamir çözümü, çok iddialı cümle bölme.
- **Kabul:** 100 cümlede iddia sayısı el sayımıyla ±%10.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-11 · Atıf doğruluğu: alıntı gerçekten kaynakta mı
- **Sorun:** [ÖNERİ] Alıntının kaynakta bire bir geçtiği her zaman denetlenmiyor.
- **Değişiklik:** Kaynak metinde bulanık eşleşme ve eşik.
- **Kabul:** Uydurma alıntı yakalama ≥ %90.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-12 · Sayısal iddia doğrulaması: birim ve büyüklük
- **Sorun:** [ÖNERİ] Sayı kaynakta var ama birim farklı olabilir.
- **Değişiklik:** Birim normalizasyonu ve büyüklük kontrolü.
- **Kabul:** 1,2 milyon ile 1200 bin eşleşir; 12 milyon eşleşmez.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-13 · Tarih ve zaman ifadesi doğrulaması
- **Sorun:** [ÖNERİ] Göreli tarihler ("geçen yıl") yanlış çözülebilir.
- **Değişiklik:** Referans tarihli çözümleme.
- **Kabul:** Tarih ifadeleri doğru yılla eşleşir (50 örnek).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-14 · Varlık doğrulaması: kişi/kurum/ürün
- **Sorun:** [ÖNERİ] Uydurma kişi/kurum yakalanmıyor.
- **Değişiklik:** Wikidata benzeri yerel varlık listesi ve web doğrulaması.
- **Kabul:** Uydurma kişiler ≥ %70 yakalanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-15 · Uydurma kaynak/URL tespiti
- **Sorun:** [ÖNERİ] Model olmayan URL yazabilir.
- **Değişiklik:** URL HEAD denetimi (SSRF korumalı) ve DOI çözümleme.
- **Kabul:** Uydurma DOI/URL'ler işaretlenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-16 · Kendi kendine tutarlılık (self-consistency) örneklemi
- **Sorun:** [ÖNERİ] Pahalı olduğu için kapalı.
- **Değişiklik:** Yalnız yüksek riskte 3 örnek ve anlamsal uyum.
- **Kabul:** Uyumsuz yanıtlarda güven düşer ve uyarı çıkar.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-17 · Belirsizlik ifadesi eşlemesi
- **Sorun:** [ÖNERİ] Güven puanı ile dilsel ifade eşleşmiyor.
- **Değişiklik:** Düşük güvende "emin değilim" kalıbı zorunlu.
- **Kabul:** Güven < 0.4 yanıtların %90'ı belirsizlik ifadesi taşır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-18 · Kaçınma kalibrasyonu: aşırı ret oranı
- **Sorun:** [ÖNERİ] Kaçınma eşiği fazla ret üretebilir.
- **Değişiklik:** Cevaplanabilir sorularda ret oranı ölçülür ve izlenir.
- **Kabul:** Cevaplanabilir sorularda ret < %3.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### HLC-19 · "Bilmiyorum" yanıtının yararlı olması
- **Sorun:** [ÖNERİ] Ret yanıtı yol göstermiyor.
- **Değişiklik:** Ret + nedeni + sonraki adım önerisi.
- **Kabul:** Ret yanıtlarının %90'ı öneri içerir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-20 · Güncel bilgi sorularında web zorunluluğu
- **Sorun:** [ÖNERİ] Güncel soruda model hafızadan yanıtlıyor.
- **Değişiklik:** `needs_fresh_web_data` olumluysa web yoksa uyarı.
- **Kabul:** Güncel soruda kaynaksız yanıt uyarı taşır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-21 · Bilgi kesim tarihi beyanı
- **Sorun:** [ÖNERİ] Model kesim tarihini söylemiyor.
- **Değişiklik:** Yanıt meta verisinde model kesim tarihi.
- **Kabul:** Zamana duyarlı soruda tarih uyarısı.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### HLC-22 · Çok turlu sohbette olgu tutarlılığı
- **Sorun:** [ÖNERİ] Önceki turdaki olguyla çelişebilir.
- **Değişiklik:** Sohbet olgu belleği ve çelişki denetimi.
- **Kabul:** Çelişen cevap işaretlenir (30 senaryo).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-23 · Alıntılanan belgede olmayan şeyi "belgeye göre" deme
- **Sorun:** [ÖNERİ] Bağlam dışı iddia belgeye atfediliyor.
- **Değişiklik:** "Belgeye göre" ifadeli cümlelerin kaynakla denetimi.
- **Kabul:** Belge dışı iddia atfı < %3.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-24 · Kod halüsinasyonu: olmayan paket/API tespiti
- **Sorun:** [ÖNERİ] HAL-13 var ama kapsamı dar.
- **Değişiklik:** PyPI/npm ad listesi çevrimdışı önbelleği ve içe aktarma doğrulaması.
- **Kabul:** Uydurma paket ≥ %90 yakalanır (kurulum öncesi).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-25 · Kod halüsinasyonu: olmayan işlev/yöntem
- **Sorun:** [ÖNERİ] Var olan pakette olmayan yöntem çağrısı.
- **Değişiklik:** AST + `inspect` ile imza doğrulama (sandbox).
- **Kabul:** Olmayan yöntem çağrılarının ≥ %70'i yakalanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-26 · Üretilen kodun çalıştırılarak doğrulanması (HAL-12)
- **Sorun:** [ÖNERİ] HAL-12 100 istemde ölçülmedi.
- **Değişiklik:** Docker sandbox'ta 100 Python/JS isteminde çalışma oranı.
- **Kabul:** Doğrulamalı yol doğrulamasıza göre ≥ 15 puan.
- **Meta:** P1 · L · Bağ: - · Durum: açık

#### HLC-27 · Matematik/hesap yanıtlarının araçla çapraz kontrolü
- **Sorun:** [ÖNERİ] Sayısal yanıt model hesabından gelebilir.
- **Değişiklik:** Hesap niyetinde SymPy sonucu zorunlu.
- **Kabul:** Hesap sorularında doğruluk ≥ %98.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-28 · Tablo/özet sayılarının toplam tutarlılığı
- **Sorun:** [ÖNERİ] Özetteki sayılar kaynakla toplamıyor olabilir.
- **Değişiklik:** Toplam/oran tutarlılık denetimi.
- **Kabul:** Tutarsız özet işaretlenir.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### HLC-29 · Çeviri sadakati denetimi
- **Sorun:** [ÖNERİ] Çeviri anlam kaydırabilir.
- **Değişiklik:** Geri çeviri benzerliği ve sayı/özel ad korunumu.
- **Kabul:** Sayılar ve özel adlar çeviride korunur (100 örnek).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-30 · Özetleme sadakati (faithfulness)
- **Sorun:** [ÖNERİ] Özet kaynakta olmayan şey ekleyebilir.
- **Değişiklik:** Özet cümlelerinin kaynakla NLI denetimi.
- **Kabul:** Desteklenmeyen özet cümlesi < %5.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-31 · Uzun belge soru-cevapta konum atfı
- **Sorun:** [ÖNERİ] Sayfa/bölüm atfı yanlış olabilir.
- **Değişiklik:** Atıf konumunun gerçek parça konumuyla eşleşmesi.
- **Kabul:** 300 sayfalık PDF'te sayfa atfı doğruluğu ≥ %85.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-32 · Çelişkili kaynaklarda dürüst sunum
- **Sorun:** [ÖNERİ] Kaynaklar çelişince biri seçiliyor.
- **Değişiklik:** Çelişki matrisi ve "kaynaklar çelişiyor" cümlesi.
- **Kabul:** 15 çelişkili çiftte ≥ %85 yakalama.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-33 · Önyargı ve kalıp yargı kontrolü
- **Sorun:** [ÖNERİ] Önyargılı içerik denetlenmiyor.
- **Değişiklik:** Küçük önyargı denetim seti ve uyarı.
- **Kabul:** 50 örnekte ağır önyargı işaretleme ≥ %70.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### HLC-34 · Tıbbi/hukuki/finansal güvenlik çerçevesi
- **Sorun:** [ÖNERİ] Yüksek riskli alanlarda uyarı tutarsız.
- **Değişiklik:** Alan algılama, kaynak zorunluluğu, sorumluluk reddi.
- **Kabul:** Bu alan sorularının %100'ünde uyarı ve atıf.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-35 · Yönlendirici sorulara dayanıklılık (sycophancy)
- **Sorun:** [ÖNERİ] Kullanıcı yanlış öncül dayatınca model uyuyor.
- **Değişiklik:** Dayatmalı 60 soruluk küme.
- **Kabul:** Yanlış öncüle uyma oranı < %10.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-36 · Direnç: kullanıcı itirazında doğru yanıttan dönme
- **Sorun:** [ÖNERİ] "Yanılıyorsun" deyince doğru cevabı bırakıyor.
- **Değişiklik:** İtiraz senaryoları seti.
- **Kabul:** Doğru yanıttan dönme < %10.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-37 · Uzun bağlamda ortadaki bilgiyi kaçırma
- **Sorun:** [ÖNERİ] "Lost in the middle" etkisi.
- **Değişiklik:** İğne-samanlık testi (bağlam konumları).
- **Kabul:** Orta konumda geri çağırma ≥ %85.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-38 · Bağlam sıkıştırma sonrası olgu kaybı
- **Sorun:** [ÖNERİ] Özetleme olguları düşürüyor.
- **Değişiklik:** Sıkıştırma öncesi/sonrası olgu soru seti.
- **Kabul:** Sıkıştırma sonrası olgu kaybı < %10.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-39 · Yanıt dili ve biçimi talimatına uyum (HAL-20)
- **Sorun:** [ÖNERİ] 200 talimatlı ölçüm yok.
- **Değişiklik:** Biçim/dil/emoji/uzunluk kuralları ve 200 istemlik küme.
- **Kabul:** Uyum ≥ %95 (ölçülmüş).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-40 · Yeniden üretimde içerik koruması
- **Sorun:** [ÖNERİ] Uyum yeniden üretimi atıfı kaybedebilir.
- **Değişiklik:** Yeniden üretim sonrası atıf sayısı eşitliği.
- **Kabul:** Atıf kaybı yok (test).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### HLC-41 · Halüsinasyon kök neden analizi panosu
- **Sorun:** [ÖNERİ] Hatalar sınıflandırılmıyor.
- **Değişiklik:** Hata türü, model, mod kırılımı.
- **Kabul:** Panoda 5 türde dağılım.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-42 · Gerileme kapısı: halüsinasyon oranı artarsa birleştirme engeli
- **Sorun:** [ÖNERİ] Eval PR'da ölçüt olarak sert değil.
- **Değişiklik:** Eşik aşılırsa CI kırmızı.
- **Kabul:** Eval gerilemesi CI'ı kırar.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-43 · Eval maliyet/süre bütçesi
- **Sorun:** [ÖNERİ] Canlı eval uzun sürüyor.
- **Değişiklik:** Hızlı alt küme (30 örnek) ve tam küme.
- **Kabul:** Hızlı küme < 3 dk.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### HLC-44 · Model sürümü değişince otomatik yeniden değerlendirme
- **Sorun:** [ÖNERİ] Model güncellenince eski skor geçerli kalıyor.
- **Değişiklik:** Model özeti değişince eval tetiklenir.
- **Kabul:** Yeni model skoru olmadan terfi edemez.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-45 · Halüsinasyon raporu kullanıcıya şeffaflık
- **Sorun:** [ÖNERİ] Kullanıcı yanıtın doğrulandığını bilmiyor.
- **Değişiklik:** Yanıt sonunda "X iddia, Y doğrulandı".
- **Kabul:** Rozet gerçek sayılarla üretilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-46 · Kaynak kalitesi puanı (RAG-19) doğrulaması
- **Sorun:** [ÖNERİ] Alan adı sezgisi kaba.
- **Değişiklik:** Etiketli 200 kaynakla puan kalibrasyonu.
- **Kabul:** Güvenilir/güvensiz sınıflandırma F1 ≥ 0.75.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-47 · Yanlış öncül bilgi tabanı genişletme
- **Sorun:** [ÖNERİ] Dört varlıklı tablo.
- **Değişiklik:** Çevrimdışı olgu tabanı (örn. ülke, başkent, yıl, kişi) 5.000 kayıt.
- **Kabul:** Yanlış-öncül yakalama ≥ %70 (dışlanmış küme).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-48 · Cevaplanamaz soru sınıflandırıcısı (öğrenilmiş)
- **Sorun:** [ÖNERİ] Kural tabanlı; dışlanmış kümede iyimser.
- **Değişiklik:** Etiketli 400 örnekle lojistik regresyon.
- **Kabul:** Dışlanmış kümede F1 ≥ 0.85.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-49 · Halüsinasyon örnek günlüğü
- **Sorun:** [ÖNERİ] Yakalanan örnekler saklanmıyor.
- **Değişiklik:** Yakalanan vakalar (maskeli) kurtarma kümesine aday.
- **Kabul:** Aylık aday listesi çıkar.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### HLC-50 · Konsey (çok model) yolunun kanıtı (GW-18)
- **Sorun:** [ÖNERİ] Konsey yolu kanıtlanmadan açılmamalı.
- **Değişiklik:** Zor soru alt kümesinde tek model karşılaştırması.
- **Kabul:** ≥ 5 puan artış yoksa kapalı kalır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-51 · Cascade yönlendirme kanıtı (GW-19)
- **Sorun:** [ÖNERİ] Gecikme/doğruluk hedefleri ölçülmedi.
- **Değişiklik:** Karma sette ölçüm.
- **Kabul:** Gecikme ≥ %30 düşük, doğruluk farkı ≤ 1 puan veya kapalı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-52 · Eval sorularının sızıntı denetimi
- **Sorun:** [ÖNERİ] Eval soruları modele eğitim verisi olarak geçmiş olabilir.
- **Değişiklik:** Yeni sorular tarih damgalı ve gizli tutulur.
- **Kabul:** Sızıntı denetim raporu.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### HLC-53 · Eş zamanlı çok dilli eval (TR/EN)
- **Sorun:** [ÖNERİ] Çoğunlukla Türkçe/İngilizce ayrı değil.
- **Değişiklik:** İki dilde eşdeğer küme.
- **Kabul:** Dil bazlı skorlar ayrı raporlanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### HLC-54 · Kullanıcıya "bu yanıta ne kadar güvenmeliyim" açıklaması
- **Sorun:** [ÖNERİ] Güven yalnız renk.
- **Değişiklik:** Metinli açıklama ve nedenler.
- **Kabul:** Açıklama puanın bileşenlerini listeler.
- **Meta:** P2 · S · Bağ: - · Durum: açık

## RGX · RAG, arama ve bilgi tabanı

#### RGX-01 · Vektör dizini (ANN) ve ölçek ölçümü
- **Sorun:** [ÖNERİ] RAG-06: 100.000 parçada p95 ölçülmedi; arama tam tarama olabilir.
- **Değişiklik:** sqlite-vec veya HNSW; benchmark betiği.
- **Kabul:** 100.000 parçada p95 < 150 ms; recall@10 kaybı < 1 puan.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### RGX-02 · Reranker (cross-encoder) ölçümü
- **Sorun:** [ÖNERİ] RAG-09 nDCG kazancı ölçülmedi.
- **Değişiklik:** bge-reranker ONNX/Ollama; etiketli retrieval setinde nDCG@5.
- **Kabul:** Hibrite göre ≥ 5 puan; p95 ek gecikme < 400 ms.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### RGX-03 · Retrieval eval seti genişletme
- **Sorun:** [ÖNERİ] `eval/retrieval` küçük.
- **Değişiklik:** 300 sorulu, belgeli, Türkçe/İngilizce set.
- **Kabul:** recall@5, MRR, nDCG raporlanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-04 · Parçalama stratejisi karşılaştırması
- **Sorun:** [ÖNERİ] Tek parçalama (300-750 token).
- **Değişiklik:** Başlık-farkında, cümle pencereli, parent-child karşılaştırması.
- **Kabul:** En iyi strateji retrieval setinde seçilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-05 · Parent-child (küçük arama, büyük bağlam) getirme
- **Sorun:** [ÖNERİ] Parçalar bağlamdan kopuk.
- **Değişiklik:** Küçük parçada ara, üst bölümü bağlama koy.
- **Kabul:** Bağlam bütünlüğü sorularında doğruluk ≥ 5 puan artar.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-06 · Sorgu yeniden yazma ve çok sorgu (multi-query)
- **Sorun:** [ÖNERİ] Tek sorgu ile arama.
- **Değişiklik:** Sorgu genişletme, HyDE seçeneği.
- **Kabul:** recall@5 ≥ 3 puan artış veya kapalı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-07 · Türkçe morfoloji: kök bulma
- **Sorun:** [ÖNERİ] Türkçe normalizasyon var, kök/ek analizi sınırlı.
- **Değişiklik:** Zeyrek veya basit kök bulucu seçeneği.
- **Kabul:** Ek farkı olan sorgu-belge eşleşmesi recall'u artar.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-08 · Sohbet ekleri için geçici RAG ölçümü (RAG-14)
- **Sorun:** [ÖNERİ] 300 sayfalık PDF'te 20 olgu sorusu ölçülmedi.
- **Değişiklik:** 300 sayfalık örnek PDF ve 20 soru.
- **Kabul:** ≥ %85 doğru ve doğru sayfa atıflı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-09 · Sayfa atfı doğrulaması
- **Sorun:** [ÖNERİ] Parça-sayfa eşlemesi kayabilir.
- **Değişiklik:** Parça başına sayfa aralığı ve test.
- **Kabul:** Atıf sayfası gerçek sayfayla eşleşir (50 örnek).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-10 · Kaynak görüntüleyici (RAG-27) uçtan uca
- **Sorun:** [ÖNERİ] Atıf tıklaması e2e ölçülmedi.
- **Değişiklik:** Yan panel, vurgulama, silinmiş kaynak uyarısı.
- **Kabul:** Playwright testinde her atıf kaynağı açar.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-11 · Silinmiş kaynak atıfı davranışı
- **Sorun:** [ÖNERİ] Silinen belgeye atıf kırık kalabilir.
- **Değişiklik:** "Kaynak artık yok" uyarısı.
- **Kabul:** Silinmiş kaynak uyarı gösterir.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### RGX-12 · Hafıza–belge ayrımı: çelişki sorusu (RAG-29)
- **Sorun:** [ÖNERİ] Çelişen tercihte sormuyor olabilir.
- **Değişiklik:** Çelişki tespiti ve kullanıcıya sorma.
- **Kabul:** Çelişen iki tercihte soru üretilir (test).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-13 · Silinen hafızanın bağlamdan kesin çıkışı
- **Sorun:** [ÖNERİ] Önbellekte kalabilir.
- **Değişiklik:** Silmede önbellek/gömme temizliği.
- **Kabul:** Silinen hafıza hiçbir bağlamda görünmez.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-14 · Gömme model değişiminde yeniden gömme işi
- **Sorun:** [ÖNERİ] Model değişince karışık sürüm.
- **Değişiklik:** Arka plan yeniden gömme ve ilerleme.
- **Kabul:** Yeniden gömme sırasında arama kesintisiz.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-15 · Gömme önbelleği
- **Sorun:** [ÖNERİ] Aynı metin tekrar gömülüyor.
- **Değişiklik:** İçerik karmalı önbellek.
- **Kabul:** Tekrar eden metin gömme çağrısı sıfır.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### RGX-16 · Gömme modeli ince ayarı gerekliliği analizi (ML-06)
- **Sorun:** [ÖNERİ] İnce ayar kararı kanıtsız.
- **Değişiklik:** Açık analizi: recall@5 farkı; yalnız ≥ 4 puan açık varsa.
- **Kabul:** Karar raporu eval'e dayanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-17 · Belge tablo çıkarımı doğruluğu (DOC-07)
- **Sorun:** [ÖNERİ] 50 tabloda hücre doğruluğu ölçülmedi.
- **Değişiklik:** 50 tablolu etiketli küme.
- **Kabul:** Hücre doğruluğu ≥ %95; düşük güven işaretli.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-18 · Taranmış PDF için OCR hattı
- **Sorun:** [ÖNERİ] OCR isteğe bağlı ve sessiz kapanabilir.
- **Değişiklik:** Tesseract algılama, kurulum yönergesi, güven puanı.
- **Kabul:** OCR yokken kullanıcıya net uyarı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-19 · Çok sütunlu PDF okuma sırası
- **Sorun:** [ÖNERİ] Sütunlu metin karışabilir.
- **Değişiklik:** Düzen analizi ve okuma sırası testi.
- **Kabul:** İki sütunlu örnekte metin sırası doğru.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-20 · Başlık/içindekiler çıkarımı
- **Sorun:** [ÖNERİ] Belge yapısı kayıp.
- **Değişiklik:** Başlık hiyerarşisi parça meta verisinde.
- **Kabul:** Başlık yolu her parçada var.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-21 · Yinelenen belge tespiti
- **Sorun:** [ÖNERİ] Aynı belge iki kez dizinleniyor.
- **Değişiklik:** İçerik karması ile tekilleştirme.
- **Kabul:** Aynı dosya tek kez dizinlenir.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### RGX-22 · Belge güncelleme (yeni sürüm yükleme)
- **Sorun:** [ÖNERİ] Güncel sürüm eskisini nasıl değiştirir belirsiz.
- **Değişiklik:** Sürümlü belge ve eski parça temizliği.
- **Kabul:** Yeni sürümde eski parçalar aramada çıkmaz.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-23 · Koleksiyon bazlı erişim ve paylaşım
- **Sorun:** [ÖNERİ] Koleksiyon paylaşımı yok.
- **Değişiklik:** Sahip, okuyucu rolü, paylaşım listesi.
- **Kabul:** Yetkisiz kullanıcı koleksiyonu göremez.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-24 · Bilgi tabanı sağlık raporu (rag_doctor) arayüzde
- **Sorun:** [ÖNERİ] Doktor betiği yalnız CLI.
- **Değişiklik:** Yönetici sayfasında sağlık raporu.
- **Kabul:** Yetim parça/eski gömme sayısı görünür.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-25 · Kod belgeleri için kod-farkında parçalama
- **Sorun:** [ÖNERİ] Kod parçalanırken işlev ortasından kesiliyor.
- **Değişiklik:** Dil gramerine göre işlev/sınıf parçalama.
- **Kabul:** Parça sınırları işlev sınırlarıyla uyuşur.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-26 · Depo (repo) dizinleme ve kod arama
- **Sorun:** [ÖNERİ] Projeler arası kod araması yok.
- **Değişiklik:** Çalışma alanı kod dizini (RAG-28).
- **Kabul:** Sembol ve anlamsal arama sonuç verir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-27 · E-posta/not/markdown içe aktarma
- **Sorun:** [ÖNERİ] Yalnız belge türleri.
- **Değişiklik:** Markdown vault, .eml içe aktarma.
- **Kabul:** Örnek vault dizinlenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-28 · Web sayfası arşivleme ve sürümleme
- **Sorun:** [ÖNERİ] Web kaynakları değişebilir.
- **Değişiklik:** Alıntı anında arşivlenmiş metin.
- **Kabul:** Kaynak değişse bile arşiv metni gösterilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-29 · Web arama sağlayıcısı yedekleri
- **Sorun:** [ÖNERİ] Tek SearXNG örneği.
- **Değişiklik:** Çoklu sağlayıcı ve çevrimdışı mod.
- **Kabul:** Sağlayıcı kapalıyken yedeğe düşer, uyarı verir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-30 · Web arama önbelleği ve tazelik
- **Sorun:** [ÖNERİ] Önbellek TTL sabit.
- **Değişiklik:** Konuya göre TTL.
- **Kabul:** Güncel soruda eski önbellek kullanılmaz.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-31 · Arama sonucu tekilleştirme ve çeşitlilik
- **Sorun:** [ÖNERİ] Aynı alan adı baskın olabilir.
- **Değişiklik:** Alan adı başına üst sınır.
- **Kabul:** Çeşitlilik ölçüsü ≥ 0.6 (RES-02).
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-32 · Arama sorgusu günlüğü maskeleme
- **Sorun:** [ÖNERİ] Sorgular kişisel veri içerebilir.
- **Değişiklik:** Sorgu günlüğü maskeli.
- **Kabul:** Günlükte TCKN deseni yok.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### RGX-33 · Hibrit arama ağırlık öğrenmesi
- **Sorun:** [ÖNERİ] BM25/vektör ağırlığı sabit.
- **Değişiklik:** Etiketli sette ızgara arama.
- **Kabul:** Ağırlık seçimi eval'e dayanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-34 · Alaka eşiği kalibrasyonu
- **Sorun:** [ÖNERİ] Eşik elle seçildi.
- **Değişiklik:** ROC ile eşik seçimi.
- **Kabul:** Yanlış getirme oranı raporlanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-35 · Boş getirme davranışı
- **Sorun:** [ÖNERİ] Hiçbir şey bulunamadığında model uyduruyor.
- **Değişiklik:** Boş getirmede kaçınma ve açıklama.
- **Kabul:** Boş getirmede uyduran yanıt oranı < %5.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-36 · Getirilen bağlamın bütçelenmesi
- **Sorun:** [ÖNERİ] Bağlam penceresini aşabilir.
- **Değişiklik:** Token bütçeli seçim ve sıkıştırma.
- **Kabul:** Getirilen bağlam pencereyi aşmaz.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-37 · Bağlamda çelişen parçalar
- **Sorun:** [ÖNERİ] Çelişen parçalar birlikte verilir.
- **Değişiklik:** Çelişki bayrağı ve model uyarısı.
- **Kabul:** Çelişki bayraklı parça işaretlenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-38 · Parça düzenleme/silme arayüzü
- **Sorun:** [ÖNERİ] Yanlış parça düzeltilemiyor.
- **Değişiklik:** Parça görüntüleme ve silme.
- **Kabul:** Silinen parça aramada çıkmaz.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### RGX-39 · Bilgi grafiği (GraphRAG) kalite ölçümü
- **Sorun:** [ÖNERİ] GraphRAG'in kazancı ölçülmedi.
- **Değişiklik:** Çok adımlı sorularda A/B.
- **Kabul:** Kazanç yoksa varsayılan kapalı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-40 · Varlık çıkarımı kalitesi
- **Sorun:** [ÖNERİ] Varlık çıkarımı basit.
- **Değişiklik:** Etiketli küçük set ve F1.
- **Kabul:** Varlık F1 raporlanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-41 · Şirket RAG: kaynak ve yetki
- **Sorun:** [ÖNERİ] Şirket belgeleri yetki ayrımı.
- **Değişiklik:** Belge düzeyinde izin.
- **Kabul:** Yetkisiz belge aramada çıkmaz.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-42 · Dizin yedek/geri yükleme
- **Sorun:** [ÖNERİ] Dizin kaybolursa yeniden üretim uzun.
- **Değişiklik:** Dizin yedeği.
- **Kabul:** Geri yükleme sonrası arama aynı sonuç verir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### RGX-43 · Çok dilli arama (TR sorgu, EN belge)
- **Sorun:** [ÖNERİ] Diller arası eşleşme zayıf olabilir.
- **Değişiklik:** Çok dilli gömme (bge-m3) ölçümü.
- **Kabul:** Çapraz dil recall@5 ≥ %70.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-44 · Sorgu niyeti: getirme gerekli mi
- **Sorun:** [ÖNERİ] Gereksiz getirme gecikme ve gürültü.
- **Değişiklik:** Selamlama/hesapta getirme atlanır.
- **Kabul:** Getirme çağrısı bu niyetlerde sıfır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### RGX-45 · Retrieval gecikme metriği
- **Sorun:** [ÖNERİ] Arama süresi metriklerde yok.
- **Değişiklik:** `metrics.observe` ile süre.
- **Kabul:** `/metrics`te arama süresi görünür.
- **Meta:** P2 · S · Bağ: - · Durum: açık
