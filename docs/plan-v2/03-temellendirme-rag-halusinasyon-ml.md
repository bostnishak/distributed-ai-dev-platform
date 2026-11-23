# Parça 3 — Temellendirme (RAG), Halüsinasyon Kontrolü (HAL) ve Makine Öğrenmesi (ML)

## Halüsinasyon neden oluyor ve ne çözer? (dürüst çerçeve)

"Makine öğrenmesi mi gerekiyor, LLM gateway, guardrail, RAG?" sorusunun cevabı: **hepsi, ama sırası ve ağırlığı önemli.**

| Hata kaynağı | Asıl çözüm | İnce ayar/ML yardımı |
|---|---|---|
| Model bilmediği olguyu uyduruyor | **Kaynaklı getirme (RAG) + atıf zorunluluğu + "bilmiyorum" davranışı** | Küçük: kaçınma davranışı öğretilebilir |
| Güncel/olgusal bilgi eski | **Web erişimi (şu an yok, F7)** + tarih araçları | Yok |
| Sayı/hesap yanlış | **Deterministik araçlar** (SymPy, SQL, pandas, birim) | Yok |
| Kod uyduruyor (olmayan API) | **Çalıştırıp doğrulama + paket/API varlık denetimi** | Küçük (kod uzmanı adaptör) |
| Bağlam dışı/alakasız bilgi ekliyor | **Alaka eşiği, kapsamlı bağlam, sıkı temellendirme modu** | Reranker ince ayarı |
| Talimata uymuyor (biçim, emoji, dil) | **Çıktı sözleşmesi + otomatik doğrulama** | DPO ile iyileşir |
| Kendinden emin yanlış cevap | **Güven kalibrasyonu + öz-tutarlılık + çapraz doğrulama** | Kalibratör (ML-03) |
| Niyeti yanlış anlıyor | **Gömme tabanlı sınıflandırıcı + netleştirme soruları** | Sınıflandırıcı eğitimi (ML-01) |

**Dürüst sınır:** 4B–9B yerel modeller geniş dünya bilgisinde Claude/GPT/Gemini seviyesine *ulaşamaz*; ince ayar olgusal bilgiyi güvenilir biçimde artırmaz, çoğu zaman davranışı (biçim, araç kullanımı, kaçınma) iyileştirir. Güvenilirlik **mimariyle** sağlanır: bilmediğinde kaynak bulur, bulamazsa söyler, hesaplanabileni hesaplar, doğrulanabileni doğrular. Yüksek zorluktaki işleri büyük ajana/konseye veya (isteğe bağlı, varsayılan kapalı) bulut sağlayıcıya yükseltmek bir seçenektir (karar D1).

**Ölçüm olmadan ilke yok:** Bu parçadaki hiçbir prompt/kural "halüsinasyonu azaltır" diye eklenmez; HAL-02/03 eval düzeneği kurulduktan sonra etkisi A/B ile kanıtlanarak eklenir (HAL-29).

---

## A. RAG — Bilgi Alma, Temellendirme ve Web Araştırması

#### RAG-01 · Belge alma (ingestion) hattı
- **Sorun:** [DOĞRULANDI: F8] `HybridGraphRAG.add_document` modül dışından hiç çağrılmıyor; kullanıcı belgeleri hiçbir zaman dizine girmiyor, dolayısıyla "kendi belgelerimden cevap ver" yeteneği yok.
- **Değişiklik:** `rag/ingest.py`: yükleme → tür algılama → ayrıştırma → temizleme → parçalama → gömme → dizinleme; `ingest_jobs` tablosu (durum, hata, yeniden deneme), arka plan yürütme, ilerleme olayları.
- **Kabul:** Yüklenen PDF/DOCX/MD birkaç dakika içinde aranabilir olur; kesilen işlem yeniden başlatılınca kaldığı yerden sürer; `test_ingest.py` 8 senaryo.
- **Meta:** P0 · L · Bağ: DAT-04, GW-01 · Durum: açık

#### RAG-02 · Yapı korumalı ayrıştırma
- **Sorun:** [DOĞRULANDI: F8] Mevcut metin çıkarımı düz metin; başlık hiyerarşisi, tablo ve sütun düzeni kayboluyor (`pymupdf4llm` kurulu ama kullanılmıyor).
- **Değişiklik:** PDF → Markdown (başlıklar, tablolar, liste; `pymupdf4llm`), DOCX/PPTX/XLSX/HTML yapısal çıkarım; sayfa/bölüm/satır konum bilgisi korunur.
- **Kabul:** 30 belgelik altın sette tablo hücre doğruluğu ≥ %95, başlık hiyerarşisi doğruluğu ≥ %90.
- **Meta:** P0 · M · Bağ: RAG-01 · Durum: açık

#### RAG-03 · OCR ve düşük kalite taramalar
- **Sorun:** [ÖNERİ] Taranmış PDF ve fotoğraf belgeleri metin olarak boş çıkar; sessizce "bilgi yok" olur.
- **Değişiklik:** Metin katmanı yoksa OCR (Tesseract tr+en veya VLM), kelime güven skoru, düşük güvenli bölgeler işaretlenir ve kullanıcıya bildirilir; OCR metni kaynakta "OCR" etiketli.
- **Kabul:** 20 taranmış belgede karakter doğruluğu ≥ %95 (temiz), düşük kalitede uyarı üretilir; OCR'sız yapılandırmada net hata mesajı (DEF-15).
- **Meta:** P1 · M · Bağ: RAG-02 · Durum: açık

#### RAG-04 · Yapı farkında parçalama
- **Sorun:** [ÖNERİ] Sabit uzunluklu kesme cümle/tablo/kod bloğunu böler; getirilen parça bağlamsız kalır.
- **Değişiklik:** Başlık hiyerarşisine, paragraf/tablo/kod sınırlarına göre 300–800 token parçalar, hafif örtüşme, üst başlık zinciri parçaya eklenir; her parça `{doc, page, section, offset, hash}` taşır.
- **Kabul:** Hiçbir tablo/kod bloğu ortadan bölünmez (test); retrieval eval'de recall@5 sabit uzunluklu kesmeye göre ≥ 5 puan yüksek.
- **Meta:** P0 · M · Bağ: RAG-02 · Durum: açık

#### RAG-05 · Gömme modeli ve sessiz yedeğin kaldırılması
- **Sorun:** [DOĞRULANDI: F8] `hybrid_graph_rag._embed` Ollama yoksa sessizce 256 boyutlu **n-gram karma gömmeye** düşüyor; bu anlamsal değildir ve kullanıcı bilmeden kalitesiz arama yapılır.
- **Değişiklik:** Varsayılan `bge-m3` (Ollama); yedek yalnız test ortamında; üretimde gömme yoksa RAG "devre dışı" durumuna geçer ve arayüz uyarır; her vektör `embedding_model/dim/version` taşır.
- **Kabul:** Ollama gömme modeli yokken arayüz "Bilgi bankası devre dışı: bge-m3 çekilmedi" der (sessiz yedek yok); yedek gömme üretimde kullanılırsa test başarısız olur.
- **Meta:** P0 · S · Bağ: GW-01 · Durum: açık

#### RAG-06 · Vektör dizini (ANN)
- **Sorun:** [DOĞRULANDI: F8] `HybridGraphRAG.search` her sorguda tüm `rag_documents` satırlarını okuyup Python'da BM25 ve kosinüs hesaplıyor (O(N)); birkaç bin parçada yavaşlar.
- **Değişiklik:** `sqlite-vec` (veya HNSW) ile yaklaşık en yakın komşu; ön filtre (koleksiyon, kullanıcı); toplu güncelleme; karar D5.
- **Kabul:** 100.000 parçalık dizinde sorgu p95 < 150 ms (benchmark); doğruluk kaybı recall@10'da < 1 puan.
- **Meta:** P1 · L · Bağ: RAG-05, DAT-11 · Durum: açık

#### RAG-07 · FTS5 BM25 ve Türkçe metin normalizasyonu
- **Sorun:** [DOĞRULANDI: F8] BM25 elle Python'da hesaplanıyor; Türkçe çekim ekleri ve `I/İ/ı/i` büyük-küçük harf farkı işlenmiyor ("sözleşmeler" ile "sözleşme" eşleşmiyor).
- **Değişiklik:** SQLite FTS5 `bm25()`, özel tokenizer/ön işleme: Unicode normalize, Türkçe küçük harf kuralları, kök bulma (Snowball tr / Zemberek benzeri), eşanlamlı sözlüğü.
- **Kabul:** "sözleşmeler/sözleşmenin/sözleşmede" aynı belgeyi bulur; Türkçe sorgu setinde MRR, mevcut yönteme göre ≥ 10 puan yüksek.
- **Meta:** P0 · M · Bağ: RAG-01 · Durum: açık

#### RAG-08 · Hibrit birleştirme ve mutlak alaka eşiği
- **Sorun:** [DOĞRULANDI: F8] RRF her zaman bir sıralama döndürür; en alakasız belge bile "ilk" olabilir. Sohbet hattı bunları eşiksiz bağlama ekleyecekti (şimdilik yalnız `bm25 > 0` kapısı eklendi).
- **Değişiklik:** RRF yalnız sıralama için; ayrıca mutlak sinyaller (normalize BM25, kosinüs, reranker skoru) için eşikler; eşik altında "bağlam yok" döner; eşik eval ile ayarlanır (HAL-05).
- **Kabul:** 100 alakasız soruda bağlama giren parça oranı < %5; alakalı sorularda recall@3 ≥ %90.
- **Meta:** P0 · M · Bağ: RAG-05, RAG-07 · Durum: açık

#### RAG-09 · Yeniden sıralama (reranker)
- **Sorun:** [ÖNERİ] Bi-encoder gömme tek başına ince ayrımda zayıf.
- **Değişiklik:** İlk 30 aday → cross-encoder (`bge-reranker-v2-m3`, ONNX/Ollama) → ilk 5; gecikme bütçeli; kapatma seçeneği.
- **Kabul:** nDCG@5 hibrit tek başına göre ≥ 5 puan yüksek; ek gecikme p95 < 400 ms.
- **Meta:** P1 · M · Bağ: RAG-08 · Durum: açık

#### RAG-10 · Sorgu yeniden yazma
- **Sorun:** [ÖNERİ] Çok turlu sohbette "peki ya onun fiyatı?" gibi zamirli sorgular arama için anlamsız.
- **Değişiklik:** Sohbet bağlamıyla bağımsız sorguya çevirme (küçük model, şema çıktı), çoklu alt sorgu, isteğe bağlı HyDE; her biri eval ile kapı.
- **Kabul:** Zamirli 50 sorguda retrieval recall@5, yeniden yazmasız yönteme göre ≥ 15 puan yüksek; kullanıcı mesajı değiştirilmez, yalnız arama sorgusu.
- **Meta:** P1 · M · Bağ: RAG-08, GW-11 · Durum: açık

#### RAG-11 · Atıf standardı
- **Sorun:** [DOĞRULANDI: F11] Yanıtlarda kaynak parça kimliği/sayfa bilgisi yok; kullanıcı doğrulayamıyor.
- **Değişiklik:** Bağlamda her parça `[S1]…[Sn]` etiketiyle verilir; model atıf kuralıyla yazar; doğrulama (HAL-07) etiketleri parçaya eşler; yanıtta `citation` olayı `{id, doc, page, quote}`.
- **Kabul:** RAG yanıtlarında atıflı olgusal cümle oranı ≥ %97; her atıf gerçek bir parçaya çözülür (olmayan `[S9]` yok).
- **Meta:** P0 · M · Bağ: RAG-04 · Durum: açık

#### RAG-12 · Bilgi bankası yönetimi
- **Sorun:** [ÖNERİ] Kullanıcı hangi belgelerin dizinde olduğunu göremez, silemez, güncelleyemez.
- **Değişiklik:** Koleksiyonlar (kişisel/proje/ekip), izinler (SEC-04), belge listesi, yeniden dizinleme, silme (gömme+FTS dahil), kota, sürümleme; "Bilgi" sekmesi (UX-12).
- **Kabul:** Belge silinince arama sonuçlarından anında çıkar (test); yetkisiz kullanıcı koleksiyonu göremez.
- **Meta:** P0 · L · Bağ: RAG-01, SEC-04 · Durum: açık

#### RAG-13 · Sabit kodlu "şirket bilgi bankası"nın taşınması
- **Sorun:** [DOĞRULANDI: F8] `company_rag.COMPANY_KNOWLEDGE_DOCS` koda gömülü birkaç belge; anahtar kelime puanlamasıyla çalışıyor; kullanıcı düzenleyemiyor, örnek içerik gerçek bilgi gibi sunuluyor.
- **Değişiklik:** İçerik veri dosyasına/koleksiyona taşınır, "örnek içerik" etiketi taşır; kullanıcı kendi bilgisiyle değiştirir; motor ortak RAG hattına geçer.
- **Kabul:** Koda gömülü belge kalmaz; örnek koleksiyonun yanıtlarında kaynak etiketi "örnek" görünür.
- **Meta:** P1 · S · Bağ: RAG-12 · Durum: açık

#### RAG-14 · Sohbet eklerinin geçici RAG'i
- **Sorun:** [DOĞRULANDI: F9] Ek 16.000 karakterde kesiliyor (DEF-07); büyük belgeler soruya göre taranmıyor.
- **Değişiklik:** Ek, oturuma bağlı geçici koleksiyona ingest edilir; soruya göre parçalar getirilir; belge küçükse tamamı bağlama konur; kullanıcıya "N sayfa okundu" bilgisi.
- **Kabul:** 300 sayfalık PDF'te rastgele 20 olgu sorusunun ≥ %85'i doğru ve doğru sayfa atıflı yanıtlanır.
- **Meta:** P0 · M · Bağ: RAG-01, RAG-11 · Durum: açık

#### RAG-15 · Çok belgeli karşılaştırma ve çelişki bulma
- **Sorun:** [ÖNERİ] "Bu iki sözleşme arasındaki farklar" gibi sorular tek bağlamda sığmıyor ve model farkları uyduruyor.
- **Değişiklik:** Belge çiftleri için hizalı bölüm eşleme, farkların deterministik hesaplanması (metin diff) + LLM yorumu yalnız fark listesi üzerine; çelişki matrisi.
- **Kabul:** Bilerek değiştirilmiş 20 belge çiftinde fark yakalama recall'u ≥ %90, uydurma fark oranı < %3.
- **Meta:** P2 · L · Bağ: RAG-14, DIST-09 · Durum: açık

#### RAG-16 · Tablo ve sayısal soru-cevap
- **Sorun:** [ÖNERİ] Tablolardaki sayılar düz metin olarak modele veriliyor; toplama/karşılaştırma modele kalıyor.
- **Değişiklik:** Tablolar yapılandırılmış saklanır (hücre/başlık); sayısal sorular SQL/pandas aracına yönlenir (DS-02), sonuç ve izlenen hücreler atıf olarak verilir.
- **Kabul:** 50 tablo sorusunda sayısal doğruluk ≥ %98 (model hesaplamıyor, araç hesaplıyor); atıf hücre aralığını gösterir.
- **Meta:** P1 · M · Bağ: RAG-02, DS-02 · Durum: açık

#### RAG-17 · Bilgi grafı (GraphRAG) değerlendirmesi
- **Sorun:** [DOĞRULANDI: F8] `extract_and_store_triples` ve alt-graf sorgusu var ama dizin boş ve değeri ölçülmemiş.
- **Değişiklik:** Varlık/ilişki çıkarımı (şema kısıtlı LLM), güven skoru ve kaynak parça bağı; GraphRAG yalnız çok adımlı ilişkisel soruda (ORC-03 işareti) devreye girer; değer kanıtlanamazsa kaldırılır.
- **Kabul:** 40 ilişkisel soruluk sette GraphRAG'li yol düz RAG'e göre doğruluğu ≥ 5 puan artırır; artırmazsa özellik kapatılır.
- **Meta:** P2 · L · Bağ: RAG-08, HAL-03 · Durum: açık

#### RAG-18 · Web araması ve sayfa okuma (internet erişimi)
- **Sorun:** [DOĞRULANDI: F7] `deep_research.py` yalnız yerel Ollama'ya istek atıyor; sistemde internet araması/sayfa alma yok. "Bir konuyu araştır, sunum yap" bugün modelin parametrik hafızasından yazması demek; kaynak veremez, güncel bilgi veremez, uydurma riski yüksek.
- **Değişiklik:** `web/` paketi: arama sağlayıcı arayüzü (varsayılan self-host **SearXNG**, isteğe bağlı Brave/Tavily; karar D2), `safe_fetch` (SEC-10), okunabilir içerik çıkarımı (`trafilatura`), robots.txt ve hız sınırı, kaynak URL/tarih/başlık meta verisi; yerel kapalı mod.
- **Kabul:** "Bugün X hakkında son gelişmeler" isteğinde gerçek sayfalardan alıntı ve URL'lerle cevap gelir; internet yokken açıkça "web erişimi yok" der; SSRF testleri geçer.
- **Meta:** P0 · L · Bağ: SEC-10, GW-01 · Durum: açık

#### RAG-19 · Web kaynak güvenilirliği ve çapraz doğrulama
- **Sorun:** [ÖNERİ] Her web sayfası eşit güvenilir değil; tek bir forum yazısı olgu sayılır.
- **Değişiklik:** Alan adı sınıfı (resmi/akademik/haber/blog/forum), yayın tarihi, yazar/kurum; önemli iddialar için ≥ 2 bağımsız kaynak şartı; güvenilirlik rozeti.
- **Kabul:** 30 tartışmalı iddiada tek forum kaynağına dayanan cevap "doğrulanamadı" etiketi alır; resmi+akademik çift kaynaklı cevaplar "doğrulandı" olur.
- **Meta:** P1 · M · Bağ: RAG-18 · Durum: açık

#### RAG-20 · Güncellik ve bilgi kesim tarihi politikası
- **Sorun:** [ÖNERİ] Model "bugün", "son", "şu anki" ifadelerinde eski bilgiyi güncelmiş gibi verir.
- **Değişiklik:** Güncellik sinyali içeren sorularda arama zorunlu; sistem saati aracı; yanıtta kaynak tarihleri; bilgi kesim tarihi uyarısı (web kapalıysa).
- **Kabul:** 50 "güncel" soruda web açıkken ≥ %90 kaynaklı ve tarihli; web kapalıyken tamamının cevabı "güncel veriye erişemiyorum" uyarısı taşır.
- **Meta:** P1 · S · Bağ: RAG-18, HAL-18 · Durum: açık

#### RAG-21 · Akademik ve açık veri kaynakları
- **Sorun:** [DOĞRULANDI: F1] `academic_expert` bağlı değil ve gerçek kaynaklara erişmiyor.
- **Değişiklik:** arXiv, Crossref, OpenAlex, PubMed, Semantic Scholar API bağlayıcıları (anahtarsız/ücretsiz); DOI çözümleme; APA/IEEE/Vancouver atıf üretimi; özet + bibliyografik doğrulama.
- **Kabul:** Verilen DOI'nin başlık/yazar/yıl bilgisi gerçek kayıtla eşleşir; uydurma kaynakça üretilemez (olmayan DOI çözümlenemez → reddedilir).
- **Meta:** P2 · M · Bağ: RAG-18 · Durum: açık

#### RAG-22 · Wikipedia/Wikidata ile varlık doğrulama
- **Sorun:** [ÖNERİ] Kişi, kurum, kitap, yasa, standart adlarında uydurma sık görülür.
- **Değişiklik:** Wikipedia/Wikidata bağlayıcıları (CC lisans, atıflı); varlık bulunamazsa uyarı; olgusal kimlik sorularında önce varlık araması.
- **Kabul:** 50 gerçek + 50 uydurma varlık adıyla test: uydurmaları "bulamadım" diye işaretleme ≥ %90, gerçekleri yanlış reddetme < %5.
- **Meta:** P2 · M · Bağ: RAG-18 · Durum: açık

#### RAG-23 · Web önbelleği ve çevrimdışı mod
- **Sorun:** [ÖNERİ] Tekrarlayan aramalar yavaş ve kota tüketir; internet yokken davranış belirsiz.
- **Değişiklik:** Sürümlü sayfa/sonuç önbelleği (zaman damgalı); çevrimdışı moda geçişte yalnız önbellek ve yerel RAG; yanıtlar "model hafızası" etiketiyle işaretlenir.
- **Kabul:** Aynı sorgu önbellekten < 50 ms; çevrimdışıyken arayüz modu açıkça gösterir.
- **Meta:** P2 · S · Bağ: RAG-18 · Durum: açık

#### RAG-24 · Dizin hattında güvenlik
- **Sorun:** [ÖNERİ] Dizine giren kötü niyetli belge, sonradan başka kullanıcıların sorgularında prompt injection kaynağı olur.
- **Değişiklik:** Dizinlemeden önce enjeksiyon dedektörü, aktif içerik taraması (SEC-08), PII sınıflandırma; şüpheli parçalar "karantina" etiketiyle bağlamda daha düşük güvenle ve sınırlayıcılı verilir.
- **Kabul:** Enjeksiyon içeren belgeyle yapılan 30 saldırı denemesinde başarı < %5 (SEC-09 seti).
- **Meta:** P1 · M · Bağ: SEC-09 · Durum: açık

#### RAG-25 · Dizin sağlığı ve yeniden gömme
- **Sorun:** [ÖNERİ] Model değişince eski vektörler anlamsız olur; yinelenen/yetim parçalar birikir.
- **Değişiklik:** `scripts/rag_doctor.py`: yinelenen parça, boş gömme, yetim kayıt, gömme modeli uyuşmazlığı tespiti ve onarımı; model değişince arka planda yeniden gömme.
- **Kabul:** Elle bozulmuş dizin üzerinde doctor tüm sorunları bulur ve onarır (test); yeniden gömme sırasında arama kesintisiz çalışır.
- **Meta:** P2 · M · Bağ: DAT-11 · Durum: açık

#### RAG-26 · Retrieval değerlendirme seti
- **Sorun:** [DOĞRULANDI: F18] Arama kalitesini ölçen veri yok; "RAG çalışıyor" iddiası kanıtsız.
- **Değişiklik:** `eval/retrieval/`: belge + soru + beklenen parça çiftleri (en az 200), recall@k, MRR, nDCG, "yanıtsız" sorular için yanlış-pozitif oranı; CI eşikleri.
- **Kabul:** Eşiklerin altına düşen değişiklik CI'ı kırar; rapor `eval/reports/`'a yazılır.
- **Meta:** P0 · M · Bağ: RAG-01, HAL-03 · Durum: açık

#### RAG-27 · Kaynak görüntüleyici
- **Sorun:** [ÖNERİ] Atıf yalnız etiket olursa kullanıcı doğrulamaz.
- **Değişiklik:** Yan panelde belge/sayfa görüntüleme, alıntının vurgulanması, "bu cümle hangi kaynağa dayanıyor" tıklaması; web kaynağı için arşivlenmiş metin.
- **Kabul:** Her atıf tek tıkla ilgili alıntıyı gösterir (e2e); kaynak silinmişse "kaynak artık yok" uyarısı.
- **Meta:** P1 · M · Bağ: RAG-11, UX-10 · Durum: açık

#### RAG-28 · Kod tabanı bilgi bankası
- **Sorun:** [DOĞRULANDI: F19] `code_graph` AST grafı çalışma alanı içinde var ama kod sorularında RAG olarak kullanılmıyor.
- **Değişiklik:** Depo/çalışma alanı AST tabanlı parçalanır (fonksiyon/sınıf), sembol grafı + gömme; "bu işlev nerede kullanılıyor", "şu hatayı nasıl düzeltirim" sorularında getirme.
- **Kabul:** 40 kod sorusunda doğru dosya/işlev bulma ≥ %90; yanıtlar dosya:satır atfı taşır.
- **Meta:** P1 · M · Bağ: RAG-06 · Durum: açık

#### RAG-29 · Kişisel hafıza ile belge bilgisinin ayrımı
- **Sorun:** [ÖNERİ] Kullanıcının tercihleri (kısa olgular) ile belge bilgisi aynı yoldan karışabilir; çelişkili/eskimiş hafıza kalır.
- **Değişiklik:** İki ayrı depo ve enjeksiyon yolu; hafıza kayıtlarına kaynak mesaj, güven, yaş; çelişkide son kullanıcı onaylı değer; unutma komutu.
- **Kabul:** Çelişen iki tercihte sistem kullanıcıya sorar; silinen hafıza hiçbir sonraki bağlamda görünmez (test).
- **Meta:** P2 · M · Bağ: DAT-09 · Durum: açık

#### RAG-30 · Kaynak bulunamayınca davranış politikası
- **Sorun:** [ÖNERİ] Getirme boş döndüğünde model genel hafızasından cevap verip bunu belirtmiyor.
- **Değişiklik:** Üç durum: (a) kaynak var → atıflı; (b) kaynak yok + düşük risk → "kaynak bulamadım; genel bilgiyle (doğrulanmamış)" etiketi; (c) kaynak yok + yüksek risk → kaçın (HAL-15).
- **Kabul:** 100 soruluk karma sette her yanıt üç durumdan birini açıkça işaretler (kural tabanlı doğrulama).
- **Meta:** P0 · S · Bağ: RAG-08, HAL-15 · Durum: açık

---

## B. HAL — Halüsinasyon Ölçümü, Doğrulama ve Kaçınma

#### HAL-01 · Halüsinasyon taksonomisi
- **Sorun:** [ÖNERİ] "Halüsinasyon" tek kelime; ölçülemez ve tek çözümle düzeltilemez.
- **Değişiklik:** Sınıflar: uydurma olgu, uydurma kaynak/atıf, yanlış sayı/hesap, uydurma kod API'si, bağlam dışı bilgi, talimat ihlali, kendi kendine çelişki, aşırı özgüven; her sınıf için tanım, örnek, otomatik algılama yöntemi ve sorumlu hat parçası.
- **Kabul:** Belge `docs/plan-v2/halusinasyon-taksonomisi.md`; eval şeması her hatayı bir sınıfa etiketler.
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### HAL-02 · Altın değerlendirme veri seti
- **Sorun:** [DOĞRULANDI: F18] Hiçbir test modelin doğruluğunu ölçmüyor; 280 test deterministik sahte LLM ile çalışıyor.
- **Değişiklik:** `eval/golden/*.jsonl`: ≥ 300 Türkçe+İngilizce örnek; kategoriler: cevaplanabilir olgusal, **cevaplanamaz** (bilgi yok), yanıltıcı öncül, sayısal/hesap, kod, kaynak gerekli, talimat uyumu; her örnekte beklenen davranış (cevapla/kaçın/düzelt) ve kabul kriteri; sürümlü, sızıntı önlemli (eğitime girmez).
- **Kabul:** 300 örnek, kategori başına ≥ 25; her örneğin beklenen davranışı bir hakem kuralıyla makine tarafından kontrol edilebilir; veri seti hash'i raporlara yazılır.
- **Meta:** P0 · L · Bağ: HAL-01 · Durum: açık

#### HAL-03 · Eval koşucusu
- **Sorun:** [ÖNERİ] Model/prompt/RAG değişikliklerinin kalite etkisi bilinmiyor.
- **Değişiklik:** `eval/run.py --suite golden --config X`: yapılandırma (model, profil, RAG açık/kapalı, doğrulama açık/kapalı) başına skor; kategori kırılımı; JSON/HTML rapor; önceki koşuyla fark; sahte LLM yerine gerçek Ollama (isteğe bağlı iş).
- **Kabul:** Tek komutla rapor üretir; iki yapılandırma yan yana karşılaştırılır; rapor halüsinasyon sınıfı başına oranları içerir.
- **Meta:** P0 · L · Bağ: HAL-02, GW-01 · Durum: açık

#### HAL-04 · Hakem mimarisi ve kalibrasyonu
- **Sorun:** [ÖNERİ] Otomatik puanlama için LLM hakem tek başına güvenilmez; hakemin kendisi halüsinasyon yapar.
- **Değişiklik:** Katmanlı hakem: kesin kurallar (regex, sayı eşleşmesi, kaynakta arama) → NLI modeli → LLM hakem (yalnız belirsiz vakalar); hakem 100 insan etiketli örnekle kalibre edilir ve uyuşma ölçülür.
- **Kabul:** Hakem ile insan etiketi arasında Cohen κ ≥ 0.7; hakem sürümü raporlara yazılır; hakem değişince tüm geçmiş skorlar yeniden hesaplanabilir.
- **Meta:** P0 · L · Bağ: HAL-02, ML-05 · Durum: açık

#### HAL-05 · CI eval kapısı ve regresyon kuralı
- **Sorun:** [ÖNERİ] Kalite gerilemeleri fark edilmeden birikir; "halüsinasyonlar arttı" ancak kullanıcı şikâyetiyle anlaşılır.
- **Değişiklik:** PR'da hızlı eval (50 örnek, < 5 dk), gece tam eval; metrik eşikleri (olgusal doğruluk, doğru kaçınma, atıf doğruluğu, uydurma kaynak oranı) ve ≥ 2 puan gerileme kuralı; prompt/model/eşik değişikliği PR'ına otomatik rapor yorumu.
- **Kabul:** Bilerek bozulan bir prompt değişikliği CI'ı kırmızı yapar (deneme PR'ı); gece raporu `eval/reports/` altında saklanır.
- **Meta:** P0 · M · Bağ: HAL-03 · Durum: açık

#### HAL-06 · İddia çıkarma (claim extraction)
- **Sorun:** [ÖNERİ] Yanıtı bütün olarak denetlemek zor; denetim iddia düzeyinde olmalı.
- **Değişiklik:** Yanıtı atomik iddialara ayıran şema kısıtlı çıkarıcı (küçük model): `{text, type: olgu|sayı|tarih|varlık|kaynak|kod_api, span}`; kod blokları ve açıkça görüş olan cümleler hariç.
- **Kabul:** 100 yanıtlık insan etiketli sette iddia recall'u ≥ %90, hatalı iddia üretme oranı < %5.
- **Meta:** P0 · M · Bağ: GW-11 · Durum: açık

#### HAL-07 · İddia–kaynak ilişkilendirme (NLI tabanlı)
- **Sorun:** [DOĞRULANDI: F11] `citation_guard` bağlı değil ve yalnız sayısal eşleşme yapıyor; iddianın kaynak tarafından *desteklendiği* kontrol edilmiyor.
- **Değişiklik:** Her iddia için en iyi kaynak parçası seçilir; NLI (entailment / neutral / contradiction) ile destek ölçülür; sonuç `supported | unsupported | contradicted | no_source` olarak iddiaya yazılır.
- **Kabul:** Etiketli 300 iddia–kaynak çiftinde makro-F1 ≥ 0.85; `contradicted` iddialar yanıtta düzeltilir veya kaldırılır.
- **Meta:** P0 · L · Bağ: HAL-06, ML-05, RAG-11 · Durum: açık

#### HAL-08 · Atıf zorunluluğu ve onarım politikası
- **Sorun:** [DOĞRULANDI: F11] Hiçbir hat atıfsız olgusal iddiayı engellemiyor.
- **Değişiklik:** RAG/araştırma/yüksek risk modlarında `unsupported/no_source` iddialar: (1) bir kez kaynakla yeniden yazma, (2) başarısızsa cümleyi çıkar veya "doğrulanamadı" etiketle; kullanıcı bunu görür (rozet).
- **Kabul:** Eval'de yanıttaki desteklenmeyen iddia oranı doğrulamasız yola göre ≥ %60 düşer; yeniden yazma sonrası ek halüsinasyon eklenmez (HAL-07 yeniden çalışır).
- **Meta:** P0 · M · Bağ: HAL-07 · Durum: açık

#### HAL-09 · Sayısal doğrulama
- **Sorun:** [DOĞRULANDI: F4] Sayısal çıktı güvenilirliği kanıtsız; uzman motorlar örnek veriyle sahte sayı üretiyordu (düzeltildi).
- **Değişiklik:** Yanıttaki her sayı kaynaktan, araç çıktısından veya açık hesaptan türemeli; türetilemeyen sayı işaretlenir; toplam/oran tutarlılığı ve birim denetimi (`pint`); yuvarlama kuralları.
- **Kabul:** 200 sayısal iddialı yanıtta kaynaksız/hesapsız sayı oranı < %2; toplamı tutmayan tablolar yakalanır (test).
- **Meta:** P0 · M · Bağ: HAL-06, ORC-08 · Durum: açık

#### HAL-10 · Doğrulama zinciri (Chain-of-Verification)
- **Sorun:** [ÖNERİ] Tek geçişli üretim kendi yanlışını fark etmez.
- **Değişiklik:** Taslak → doğrulama soruları üret → soruları taslaktan **bağımsız** (kaynaklarla) yanıtla → çelişkileri düzelt; yalnız yüksek riskli veya düşük güvenli yanıtlarda (ORC-18).
- **Kabul:** Zor olgusal alt kümede CoVe'li yol, çıplak yola göre uydurma olgu oranını ≥ %25 azaltır (yoksa varsayılan kapalı).
- **Meta:** P1 · M · Bağ: HAL-03, ORC-18 · Durum: açık

#### HAL-11 · Öz-tutarlılık (self-consistency)
- **Sorun:** [ÖNERİ] Sayısal/kısa olgusal sorularda tek örnek yanlış olabilir.
- **Değişiklik:** n=3–5 bağımsız örnek (farklı tohum/model), çoğunluk ve uyuşmazlık analizi; uyuşmazlıkta güven düşürülür veya kaçınılır; yalnız kısa, doğrulanabilir cevaplı sorularda ve maliyet bütçesiyle.
- **Kabul:** Aritmetik/kısa olgu setinde doğruluk ≥ 5 puan artar; uyuşmazlık oranı güven skoruyla korelasyon gösterir (ECE iyileşir).
- **Meta:** P2 · M · Bağ: HAL-03 · Durum: açık

#### HAL-12 · Üretilen kodun çalıştırılarak doğrulanması
- **Sorun:** [ÖNERİ] Kod yanıtları çalıştırılmadan veriliyor; sözdizimi/çalışma hatası kullanıcıya kalır.
- **Değişiklik:** Sandbox'ta (SEC-13) derleme/çalıştırma, model veya şablondan üretilen küçük test girdileri; sonuç yanıtta "çalıştırıldı: geçti/başarısız" ve hata varsa otomatik onarım (en fazla 3 tur).
- **Kabul:** 100 Python/JS isteminde yanıtlanan kodun çalışma oranı doğrulamasız yola göre ≥ 15 puan yüksek; başarısız kod "doğrulanamadı" etiketiyle gelir, sessiz verilmez.
- **Meta:** P0 · L · Bağ: SEC-13, ORC-08 · Durum: açık

#### HAL-13 · Paket ve API varlık denetimi
- **Sorun:** [ÖNERİ] Küçük modeller var olmayan paket/fonksiyon/parametre uydurur (ayrıca "slopsquatting" riski).
- **Değişiklik:** AST ile import ve çağrı çıkarılır; paket adı PyPI/npm/yerel kurulu listesiyle doğrulanır, işlev imzası kurulu sürümden (`inspect`/tür çıkarımı) denetlenir; uydurma bulunursa düzeltme isteği veya uyarı.
- **Kabul:** 50 bilinçli uydurma paket/işlevli kod örneğinde yakalama ≥ %90; yanlış alarm < %3.
- **Meta:** P1 · M · Bağ: HAL-12 · Durum: açık

#### HAL-14 · Güven skoru ve kalibrasyon
- **Sorun:** [ÖNERİ] Küçük modellerin kendi özgüveni güvenilmezdir; arayüzde güven gösterilmiyor.
- **Değişiklik:** Sinyaller: destek oranı (HAL-07), RAG skoru, öz-tutarlılık uyuşması, araç doğrulaması, soru zorluğu; tek skora birleştirme (lojistik) ve isotonic kalibrasyon; "yüksek/orta/düşük" etiketi.
- **Kabul:** Eval'de ECE ≤ 0.08; "yüksek" etiketli yanıtların doğruluğu ≥ %95, "düşük" etiketlilerin ≥ %60'ı gerçekten hatalı.
- **Meta:** P0 · L · Bağ: HAL-07, HAL-11, ML-03 · Durum: açık

#### HAL-15 · Kaçınma (abstention) politikası
- **Sorun:** [ÖNERİ] Modeller cevap vermeyi tercih eder; bilmediğinde bile akıcı yanıt üretir.
- **Değişiklik:** Karar kuralı: kaynak yok + düşük güven + olgusal/yüksek risk → "Bu konuda güvenilir kaynak bulamadım / doğrulayamadım" + ne gerektiği (kaynak yükleyin, web aramasını açın); aşırı kaçınmayı önlemek için eşik eval ile.
- **Kabul:** Cevaplanamaz sorularda doğru kaçınma ≥ %85; cevaplanabilir sorularda gereksiz kaçınma ≤ %7.
- **Meta:** P0 · M · Bağ: HAL-14 · Durum: açık

#### HAL-16 · Yanıltıcı öncül tespiti
- **Sorun:** [ÖNERİ] "Atatürk'ün 1950'de yazdığı kitap" gibi yanlış öncüllü sorulara model öncülü kabul edip cevap uydurur.
- **Değişiklik:** Soru öncüllerini çıkarıp doğrulama (kaynak/varlık denetimi); yanlışsa önce öncülü düzeltir.
- **Kabul:** 60 yanlış öncüllü soruda öncülü düzeltme oranı ≥ %80; doğru öncüllü sorularda yanlış düzeltme < %3.
- **Meta:** P1 · M · Bağ: HAL-17, RAG-22 · Durum: açık

#### HAL-17 · Varlık ve belge numarası doğrulama
- **Sorun:** [ÖNERİ] Yasa maddeleri, ISO/DIN/TS standart numaraları, kitap/makale adları sık uydurulur.
- **Değişiklik:** Desen tabanlı çıkarma + kaynak/KB/Wikidata/mevzuat arama ile doğrulama; bulunamayanlar "doğrulanamadı" etiketi alır, yasa/standart numaraları kaynaksız verilmez.
- **Kabul:** 100 yasa/standart atıflı yanıtta doğrulanmamış numara görünürlük oranı < %2 (etiketli veya çıkarılmış).
- **Meta:** P1 · M · Bağ: RAG-22, RAG-18 · Durum: açık

#### HAL-18 · Zaman bağımlı bilgiler için araçlar
- **Sorun:** [ÖNERİ] Model "bugün", "kaç gün kaldı", güncel kur/fiyat gibi bilgileri tahmin eder.
- **Değişiklik:** Sistem saati/tarih aracı, tarih aritmetiği; kur/fiyat/hava gibi canlı veri için web aracı (RAG-18) veya "güncel veri yok" yanıtı.
- **Kabul:** Tarih hesabı sorularında doğruluk %100 (araç); canlı veri sorusunda model tahmini yerine kaynaklı değer veya açık reddetme.
- **Meta:** P1 · S · Bağ: ORC-08 · Durum: açık

#### HAL-19 · Yüksek riskli alanlar için ek koruma
- **Sorun:** [ÖNERİ] Sağlık, hukuk, finans, güvenlikte yanlış bilgi zarar verir.
- **Değişiklik:** Bu niyetlerde atıf zorunlu (kaynaksız yanıt yok), "bu bilgi profesyonel tavsiye yerine geçmez" notu, teşhis/dozaj/yatırım tavsiyesi üretmeme, acil durumlarda yönlendirme.
- **Kabul:** 100 yüksek riskli istekte kaynaksız yanıt oranı 0; yasaklı içerik (dozaj/teşhis) üretimi 0 (kural + hakem).
- **Meta:** P0 · M · Bağ: HAL-08 · Durum: açık

#### HAL-20 · Talimat ve çıktı sözleşmesi uyum denetimi
- **Sorun:** [ÖNERİ] "Emoji kullanma", "yalnız kod", "tablo ver" gibi talimatlar uygulanmıyor ve ihlal fark edilmiyor.
- **Değişiklik:** Kural tabanlı uyum denetleyici (MODE-01 sözleşmesi); ihlalde bir kez yeniden üretim (sözleşme + ihlal bilgisiyle); ikinci ihlalde kullanıcıya uyarı.
- **Kabul:** 200 talimatlı istekte uyum ≥ %95; yeniden üretim yanıtın içeriğini bozmaz (kaynak/atıf kaybı olmaz).
- **Meta:** P1 · M · Bağ: MODE-01 · Durum: açık

#### HAL-21 · Sohbet içi tutarlılık denetimi
- **Sorun:** [ÖNERİ] Aynı sohbette önceki yanıtla çelişen cevap verilebiliyor.
- **Değişiklik:** Yeni yanıtın iddiaları, konuşma durumu/özetiyle ve önceki doğrulanmış iddialarla NLI ile karşılaştırılır; çelişki varsa açıkça belirtilir ("daha önce X dedim, düzeltiyorum").
- **Kabul:** 40 çelişki tuzaklı sohbette çelişkiyi yakalama ≥ %80.
- **Meta:** P2 · M · Bağ: ORC-14, HAL-07 · Durum: açık

#### HAL-22 · Sıkı temellendirme (strict grounding) modu
- **Sorun:** [ÖNERİ] "Yalnız bu belgeye göre cevapla" isteğinde model dış bilgi katıyor.
- **Değişiklik:** Yalnız verilen kaynaklardan; dışına çıkan her iddia kırpılır; yanıt "belgede bulunmuyor" demeyi bilir; kullanıcı modu seçer veya "bu belgeye göre" ifadesiyle tetiklenir.
- **Kabul:** Belgede olmayan bilgi soran 60 soruda "belgede yok" diyen oran ≥ %90; dış bilgi sızması < %3.
- **Meta:** P0 · M · Bağ: HAL-07, RAG-14 · Durum: açık

#### HAL-23 · Sunum ve raporlarda kaynaklı içerik
- **Sorun:** [DOĞRULANDI: F7] Sunum içeriği kaynaksız model çıktısı.
- **Değişiklik:** Her olgusal slayt maddesi bir kaynak kimliği taşır (konuşmacı notlarına ve "Kaynaklar" slaydına yazılır); kaynaksız madde slaytta işaretlenir veya çıkarılır.
- **Kabul:** Eval sunumlarında olgusal maddelerin ≥ %95'i doğrulanmış kaynağa bağlı; kaynak slaytı gerçek URL/belge içerir.
- **Meta:** P0 · M · Bağ: RES-04 · Durum: açık

#### HAL-24 · Hafıza zehirlenmesi (memory poisoning) koruması
- **Sorun:** [ÖNERİ] Sohbetten otomatik çıkarılan "kullanıcı olgusu" yanlışsa kalıcı olarak sonraki yanıtlara girer; kötü niyetli içerik de hafızaya yazılabilir.
- **Değişiklik:** Hafızaya yazılacak olgular kullanıcı sözünden gelmeli (belge/web içeriğinden değil), güven eşiği ve kullanıcı onayı/geri alma; kaynak mesaj bağlantısı.
- **Kabul:** Yüklenen belgedeki "kullanıcının tercihi X" metni hafızaya yazılmaz (test); her hafıza kaydı düzenlenebilir ve kaynağı görünür.
- **Meta:** P1 · M · Bağ: SEC-09 · Durum: açık

#### HAL-25 · "Bu yanlış" bildirimi ve doğrulama kuyruğu
- **Sorun:** [ÖNERİ] Kullanıcılar hatayı görür ama sisteme geri dönüş yok.
- **Değişiklik:** Yanıt başına "yanlış bilgi" düğmesi + doğru cevap/kaynak; kuyrukta yönetici onayı; onaylananlar eval havuzuna (HAL-02) ve DPO adaylarına eklenir.
- **Kabul:** Bildirimden eval örneğine dönüşüm uçtan uca çalışır; onaylanmayan bildirim eğitim verisine girmez (test).
- **Meta:** P1 · M · Bağ: ORC-22 · Durum: açık

#### HAL-26 · Üretim telemetri ve eşik uyarıları
- **Sorun:** [ÖNERİ] Canlı kullanımda kalite izlenmiyor.
- **Değişiklik:** Her yanıt için destek oranı, atıf kapsamı, güven, kaçınma, doğrulama süresi; pano trendleri (UX-24); eşik aşımında uyarı.
- **Kabul:** Pano son 7 günlük halüsinasyon göstergelerini gösterir; yapay olarak bozulan bir yapılandırma uyarı üretir.
- **Meta:** P1 · M · Bağ: GW-15 · Durum: açık

#### HAL-27 · Kırmızı takım (red-team) seti
- **Sorun:** [ÖNERİ] Sistem yalnız "iyi niyetli" girdilerle sınanıyor.
- **Değişiklik:** `eval/redteam/`: jailbreak, prompt injection, sahte kaynak talebi ("şu makaleden alıntı yap"), aşırı özgüven tuzakları, kişisel veri çıkarma; çeyreklik güncelleme; sonuçlar HAL-05'e dahil.
- **Kabul:** ≥ 150 saldırı örneği; saldırı başarı oranı hedefi < %5; her yeni açık bir test olarak kalıcılaşır.
- **Meta:** P1 · M · Bağ: SEC-09, HAL-03 · Durum: açık

#### HAL-28 · Model/ajan başına halüsinasyon profili
- **Sorun:** [ÖNERİ] Yönlendirme yalnız hız/kod/akıl yürütme puanına bakıyor; hangi modelin hangi görevde daha az uydurduğu bilinmiyor.
- **Değişiklik:** Eval sonuçları model × görev türü matrisine yazılır; yönlendirmede ceza/ödül; pano (DIST-19) model karşılaştırmasına eklenir.
- **Kabul:** Registry her model için `halusinasyon_orani[gorev_turu]` tutar; en az uydurma yapan model olgusal görevlerde tercih edilir (test).
- **Meta:** P1 · M · Bağ: HAL-03, GW-04, DIST-19 · Durum: açık

#### HAL-29 · Prompt müdahalelerinin kanıtlanması
- **Sorun:** [ÖNERİ] "Emin değilsen söyle", "uydurma" gibi cümleler eklemek sezgisel; küçük modellerde etkisi belirsiz, bazen zararlı.
- **Değişiklik:** Her prompt/ayar değişikliği HAL-03 ile A/B edilir; yalnız anlamlı ve tekrarlanan kazanç gösterenler kalır; sonuçlar `docs/plan-v2/prompt-deneyleri.md`'ye yazılır.
- **Kabul:** Kodda eval kanıtı olmayan "halüsinasyon önleyici" prompt satırı kalmaz (inceleme kontrol listesi maddesi); her şablonun son eval raporu bağlantısı var.
- **Meta:** P1 · S · Bağ: GW-16, HAL-05 · Durum: açık

#### HAL-30 · Sınırların şeffaf belgelenmesi
- **Sorun:** [ÖNERİ] Kullanıcı sistemin neyi güvenilir yapabildiğini bilmeden güvenir veya hiç güvenmez.
- **Değişiklik:** `docs/plan-v2/halusinasyon-mimarisi.md` ve arayüzdeki "Güvenilirlik nasıl sağlanıyor / sınırlar" sayfası: hangi hata türü neyle azaltılıyor, ölçülen oranlar (eval raporundan otomatik), çözülemeyen vakalar.
- **Kabul:** Sayfadaki sayılar son eval raporundan otomatik gelir (elle yazılmaz); belge her hata sınıfı için ölçülen oranı içerir.
- **Meta:** P2 · S · Bağ: HAL-03, UX-24 · Durum: açık

---

## C. ML — Makine Öğrenmesi ve LLMOps (yalnız ölçülmüş kazanç varsa)

> İlke: **Ölçülmemiş model eğitimi yok.** Her ML maddesi bir eval kapısıyla biter; kazanç kanıtlanmazsa özellik varsayılan kapalı kalır.

#### ML-01 · Niyet sınıflandırıcı eğitimi
- **Sorun:** [DOĞRULANDI: F9] Anahtar kelime + LLM sınıflandırıcı kırılgan (ORC-02).
- **Değişiklik:** bge-m3 gömme + lojistik regresyon/SVM, ~2.000 etiketli örnek (sentetik + gerçek, elle onaylı), sınıf dengesi, belirsizlik eşiği; model dosyası sürümlü ve açıklanabilir (en yakın örnekler).
- **Kabul:** Dışlanmış sette makro-F1 ≥ 0.90; her sınıf için F1 ≥ 0.80; yeniden eğitim betiği tek komut.
- **Meta:** P0 · M · Bağ: ORC-03, RAG-05 · Durum: açık

#### ML-02 · Soru zorluğu/karmaşıklığı tahmini
- **Sorun:** [ÖNERİ] Maliyet-kalite kademesi (ORC-18) zorluk bilgisini gerektirir.
- **Değişiklik:** Sorgu → {kolay, orta, zor} sınıflandırıcısı; etiketler eval sonuçlarından (küçük model yanlış yaptıysa zor).
- **Kabul:** Zor sınıfı yakalama recall'u ≥ %80; kademe kullanımı ortalama gecikmeyi ≥ %25 düşürür, doğruluğu ≤ 1 puan etkiler (GW-19).
- **Meta:** P1 · M · Bağ: HAL-03, ML-01 · Durum: açık

#### ML-03 · Güven kalibratörü
- **Sorun:** [ÖNERİ] HAL-14 skoru kalibrasyon verisi gerektirir.
- **Değişiklik:** Eval ve onaylı geri bildirimlerden (özellikler, doğru/yanlış) lojistik + isotonic kalibratör; periyodik yeniden eğitim; model sürümü değişince geçerlilik kontrolü.
- **Kabul:** ECE ≤ 0.08, Brier skoru güvensiz yönteme göre iyileşir; kalibratör eski modelle üretilmiş skorları kullanmaz (sürüm uyuşmazlığı hatası).
- **Meta:** P1 · M · Bağ: HAL-03 · Durum: açık

#### ML-04 · Reranker ince ayarı
- **Sorun:** [ÖNERİ] Genel amaçlı reranker alan jargonunda zayıf kalabilir.
- **Değişiklik:** Kullanıcı atıf/tıklama sinyalleri ve zor negatifler ile ince ayar (yalnız RAG eval'de kazanç varsa); sürümleme.
- **Kabul:** nDCG@5 genel reranker'a göre ≥ 3 puan artar; aksi halde yayına alınmaz.
- **Meta:** P3 · L · Bağ: RAG-09, RAG-26 · Durum: açık

#### ML-05 · NLI / atıf doğrulama modeli seçimi
- **Sorun:** [ÖNERİ] HAL-07 için Türkçe'de iyi çalışan hafif NLI modeli gerekli; seçim ölçülmeden yapılmamalı.
- **Değişiklik:** Aday modelleri (çok dilli NLI, küçük LLM-hakem) Türkçe etiketli sette karşılaştırma; ONNX/Ollama ile hızlı çıkarım; gecikme bütçesi.
- **Kabul:** Seçilen model 300 çiftlik sette makro-F1 ≥ 0.85, çıkarım < 200 ms/iddia.
- **Meta:** P0 · M · Bağ: HAL-02 · Durum: açık

#### ML-06 · Gömme modeli ince ayarı
- **Sorun:** [ÖNERİ] Alan jargonunda bge-m3 yeterli olmayabilir.
- **Değişiklik:** Yalnız RAG eval'de belirgin açık varsa; çift/üçlü eşleştirme verisiyle hafif ince ayar; model sürümü ve yeniden gömme planı (RAG-25).
- **Kabul:** recall@5 ≥ 4 puan artar ve genel alan performansı düşmez; aksi halde yapılmaz.
- **Meta:** P3 · L · Bağ: RAG-26 · Durum: açık

#### ML-07 · DPO/tercih verisi hattı
- **Sorun:** [DOĞRULANDI: F1] `feedback_collector`, `llmops_pipeline` bağlı değil; tercih çifti toplama gerçekte çalışmıyor.
- **Değişiklik:** Yalnız insan onaylı (HAL-25, düzeltme) `(prompt, chosen, rejected)` çiftleri; veri sızıntısı kontrolü (eval ile örtüşme yasak); PII temizliği; veri kümesi sürüm hash'i.
- **Kabul:** Eval örnekleriyle örtüşen çift eğitim kümesine giremez (test); veri kümesi her dışa aktarımda hash'lenir.
- **Meta:** P2 · M · Bağ: HAL-25, SEC-21 · Durum: açık

#### ML-08 · QLoRA alan adaptörleri ve eval kapılı terfi
- **Sorun:** [DOĞRULANDI: F1] `model_gate` sarmalayıcısı ve `training/` hattı bağlı değil; "gece otomatik eğitim" iddiası doğrulanmamış.
- **Değişiklik:** Adaptör başına (kod, Türkçe üslup, belirli alan) eğitim, altın eval + regresyon kapısı, kanarya (trafik %10), otomatik geri alma; GGUF/Ollama modeli kaydı.
- **Kabul:** Eval'de kazanmayan adaptör yayına çıkmaz; kanarya kötüleşirse otomatik geri alınır (test); her yayın model kaydı ve rapor bağlantısı taşır.
- **Meta:** P3 · XL · Bağ: ML-07, GW-03, HAL-05 · Durum: açık

#### ML-09 · Doğrulanmış sentetik veri fabrikası
- **Sorun:** [ÖNERİ] Sentetik veri kalitesizse modeli bozar.
- **Değişiklik:** Yalnız doğrulanabilir üretim: çalışan kod + geçen test, hesaplanabilir cevap, kaynakla desteklenen soru-cevap; çeşitlilik ve yinelenme ölçüleri; insan örneklemi.
- **Kabul:** Veri kümesinde doğrulama geçme oranı %100; yinelenen örnek < %2.
- **Meta:** P3 · L · Bağ: HAL-12 · Durum: açık

#### ML-10 · Model kayıt ve yeniden üretilebilirlik
- **Sorun:** [ÖNERİ] Hangi modelin hangi veriyle, hangi ayarla eğitildiği takip edilmiyor.
- **Değişiklik:** Model kayıt tablosu: veri hash'i, hiperparametre, taban model, eval raporu, artefakt yolu, sorumlu; "bu modeli yeniden üret" betiği.
- **Kabul:** Kayıttaki bilgilerle model yeniden üretilince eval skoru ±1 puan içinde (veya sebep belgelenir).
- **Meta:** P3 · M · Bağ: ML-08 · Durum: açık

#### ML-11 · Dağılım kayması (drift) izleme
- **Sorun:** [ÖNERİ] Kullanım değiştikçe sınıflandırıcı ve eşikler eskir.
- **Değişiklik:** Niyet dağılımı, güven dağılımı, kaçınma oranı, geri bildirim oranı haftalık izlenir; kayma uyarısı ve yeniden eğitim önerisi.
- **Kabul:** Sentetik kaymalı veride uyarı üretilir; uyarı pano ve günlükte görünür.
- **Meta:** P3 · M · Bağ: HAL-26 · Durum: açık

#### ML-12 · Aktif öğrenme kuyruğu
- **Sorun:** [ÖNERİ] Etiketleme kaynağı kıt; hangi örneklerin etiketleneceği rastgele olmamalı.
- **Değişiklik:** Düşük güven + kullanıcı düzeltmesi + sınıflandırıcı belirsizliği yüksek örnekler etiketleme kuyruğuna; etiketleme arayüzü (yönetici).
- **Kabul:** Aktif örneklemeyle aynı etiket sayısında sınıflandırıcı F1'i rastgele örneklemeye göre ≥ 2 puan yüksek.
- **Meta:** P3 · M · Bağ: ML-01 · Durum: açık

#### ML-13 · Damıtma (distillation)
- **Sorun:** [ÖNERİ] Büyük model çıktılarından küçük modele davranış aktarımı fayda sağlayabilir (lisans şartlarına tabi).
- **Değişiklik:** Yalnız lisansı izin veren öğretmen model çıktıları (kendi yerel 9B veya açık lisanslı), doğrulanmış çıktılar (ML-09); eval kapısı.
- **Kabul:** Öğrenci model hedef görev setinde öğretmen performansının ≥ %90'ını yakalar; lisans denetimi belgelidir (PROC-08).
- **Meta:** P3 · L · Bağ: ML-09, PROC-08 · Durum: açık

#### ML-14 · İnce ayarın sınırları (dürüstlük notu)
- **Sorun:** [ÖNERİ] "Eğitirsek halüsinasyon biter" beklentisi gerçekçi değil ve emek israfına yol açar.
- **Değişiklik:** `docs/plan-v2/ince-ayar-sinirlari.md`: hangi sorunların ince ayarla (biçim, araç kullanımı, kaçınma tonu), hangilerinin yalnız mimariyle (olgusal doğruluk, güncellik) çözüldüğü; ölçülen deney sonuçlarıyla beslenir.
- **Kabul:** Belge her ML deneyinden sonra güncellenir (PR kontrol listesi); yanlış beklenti oluşturan iddia içermez (inceleme).
- **Meta:** P2 · S · Bağ: HAL-30 · Durum: açık
