# Parça 1 — Plan v2 kanıt kapanışı (AUD) ve test/süreç (TST)

## AUD · Plan v2 kanıt kapanışı: "tamam" denen ama kabul ölçütü sınanmamış maddeler

#### AUD-01 · Madde bazlı kanıt testi: 116 maddenin hiçbirinde kimliği geçen test yok
- **Sorun:** [DOĞRULANDI: F101] KANIT_DENETIMI'nde 150, kimlik taramasında 116 madde hiçbir test dosyasında anılmıyor; "tamam" kanıtı toplu senaryo testine dayanıyor.
- **Değişiklik:** Her madde için kimliğini taşıyan ve kabul ölçütünün küçük bir kopyasını sınayan test yazılır; `plan_tool` kimliksiz done'ı reddeder.
- **Kabul:** `plan_tool.py status` her done maddede kimlik geçen test bulur; bulamazsa hata verir.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### AUD-02 · Kanıt dosyası eşlemesinin gerçek test konumuna çekilmesi
- **Sorun:** [DOĞRULANDI: F101] SEC-11..SEC-24 testleri `test_security_hardening.py` içinde ama PROGRESS kanıtı başka dosyaları gösteriyor.
- **Değişiklik:** `scripts/sync_evidence.py` kimliği geçen test dosyalarını tarar ve PROGRESS.json kanıtını günceller.
- **Kabul:** 34 maddenin kanıtı gerçek test dosyasına işaret eder; tarama betiği CI'da koşar.
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### AUD-03 · "partial" durumu ve boşluk alanı
- **Sorun:** [DOĞRULANDI: F101] PROGRESS yalnız open/done bilir; kabulü kısmen karşılanan madde done görünüyor.
- **Değişiklik:** Durum `partial` + `gap` metni kabul edilir; render tablosu partial'ı ayrı sayar.
- **Kabul:** Kabulü karşılanmayan her madde partial ve gap taşır; özet satırında done/partial/open sayıları ayrı.
- **Meta:** P0 · M · Bağ: AUD-01 · Durum: açık

#### AUD-04 · Enjeksiyon dedektörü ölçümü: 40 saldırıda 5 yakalama
- **Sorun:** [DOĞRULANDI: F102] SEC-09 "saldırı başarısı < %5" diyordu; ölçüm 35/40 saldırı kaçırdı (%87 başarı).
- **Değişiklik:** Ağırlıklı dedektör ve `eval/security/injection.jsonl` (40 saldırı, 40 zararsız).
- **Kabul:** Saldırı başarısı < %5 ve yanlış alarm < %2; kümeler eğitimden ayrı tutulur.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### AUD-05 · Enjeksiyon ölçümü için dışlanmış küme
- **Sorun:** [DOĞRULANDI: F102] Dedektör kendi kaçırdıklarına bakılarak ayarlandı; sonuç iyimser.
- **Değişiklik:** Dedektörün hiç görmediği 100 yeni örnek (3 kişi yazar) ayrı dosyada tutulur.
- **Kabul:** Dışlanmış kümede saldırı başarısı < %10 raporlanır; fark dürüstçe belgelenir.
- **Meta:** P0 · M · Bağ: AUD-04 · Durum: açık

#### AUD-06 · Güvenlik: `safe_archive` modülü yoktu
- **Sorun:** [DOĞRULANDI: F103] SEC-07 "ortak safe_archive" diyordu; modül yoktu, ZIP doğrudan açılıyordu.
- **Değişiklik:** `safe_archive.inspect_zip` boyut/oran/derinlik/yol/sembolik bağ sınırı; tüm yükleme yollarına bağlanır.
- **Kabul:** Bomba, zip-slip, sembolik bağ örnekleri reddedilir; normal arşiv geçer.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### AUD-07 · RBAC rol matrisi tek dosyada
- **Sorun:** [DOĞRULANDI: F103] SEC-04 `auth/policy.py` ve 4 rol istiyordu; yalnız admin/member vardı.
- **Değişiklik:** `auth/policy.py` rol-eylem matrisi, `require_role`; OpenAPI'den her route sınıflanır.
- **Kabul:** Matriste olmayan route testi kırar; viewer yazamaz, analyst çalıştıramaz.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### AUD-08 · Rol matrisinin tüm route'lara bağlanması
- **Sorun:** [DOĞRULANDI: F103] Matris yazılsa da route bağımlılığı olarak uygulanmıyor.
- **Değişiklik:** Router düzeyinde `require_role` bağımlılığı; eski admin token yalnız betikler için.
- **Kabul:** Her mutasyon route'u rol testinden geçer; yetkisiz 403.
- **Meta:** P0 · M · Bağ: AUD-07 · Durum: açık

#### AUD-09 · `eval/security` ve `eval/latency` dizinleri yoktu
- **Sorun:** [DOĞRULANDI: F104] Plan bu eval kümelerine atıf yapıyor; dizinler yok.
- **Değişiklik:** İki dizin ve çalıştırıcı komutları eklenir.
- **Kabul:** `python eval/run.py --suite security` ve `--suite latency` rapor üretir.
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### AUD-10 · pytest işaretleri eksik
- **Sorun:** [DOĞRULANDI: F105] OPS-09 altı işaret istiyor; pytest.ini yalnız `security` tanımlıyor.
- **Değişiklik:** `unit, contract, integration, e2e, slow` işaretleri tanımlanır, her test işaret alır.
- **Kabul:** İşaretsiz test CI kontrolünü kırar; hızlı küme < 30 sn.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AUD-11 · Monaco yerel paketi yok
- **Sorun:** [DOĞRULANDI: F106] IDE-10 "Monaco yerel paket" diyordu; `static/vendor` yok.
- **Değişiklik:** Monaco çevrimdışı vendor olarak eklenir, tembel yüklenir.
- **Kabul:** Çevrimdışı IDE açılır; paket boyutu bütçesi ölçülür.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### AUD-12 · Test edilmiş proje şablon deposu yok
- **Sorun:** [DOĞRULANDI: F107] IDE-17 8 şablon istiyor; `templates/` dizini yok, `factory/templates.py` kod içi.
- **Değişiklik:** 8 şablon dizini ve kendi testleri eklenir.
- **Kabul:** Her şablon boş özelleştirmeyle kurulur ve testleri geçer.
- **Meta:** P1 · L · Bağ: - · Durum: açık

#### AUD-13 · Kullanıcı kimliği sorgu parametresinden geliyor
- **Sorun:** [DOĞRULANDI: F108] Birçok route `user_id=default` alıyor; SEC-03 "yalnız oturumdan" diyordu.
- **Değişiklik:** `current_user` bağımlılığı; `user_id` parametresi yok sayılır veya yalnız admin için.
- **Kabul:** A kullanıcısı B'nin verisini kimlik parametresiyle okuyamaz (otomatik test).
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### AUD-14 · Tüm /api/user/* rotaları için üretilmiş izolasyon testi
- **Sorun:** [DOĞRULANDI: F108] SEC-03 "otomatik üretilmiş test" istiyor; yok.
- **Değişiklik:** OpenAPI'den rota listesi çıkarılır, iki kullanıcıyla sızıntı testi üretilir.
- **Kabul:** Her kullanıcı rotası için A→B okuma/silme 404 doğrulanır.
- **Meta:** P0 · M · Bağ: AUD-12 · Durum: açık

#### AUD-15 · Artefakt okumada sahip denetimi yok
- **Sorun:** [DOĞRULANDI: F109] `GET /api/orchestrator/artifacts/{id}` sahip denetlemiyor.
- **Değişiklik:** Sahip filtresi eklenir.
- **Kabul:** Başkasının artefaktı 404.
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### AUD-16 · Hafıza sıkıştırmada sahip denetimi yok
- **Sorun:** [DOĞRULANDI: F109] `POST /api/memory/compact/{id}` sahipliği doğrulamıyor.
- **Değişiklik:** Sahip denetimi eklenir.
- **Kabul:** Başkasının hafızasını sıkıştırmak 403.
- **Meta:** P0 · S · Bağ: - · Durum: açık

#### AUD-17 · Ayrı SQLite dosyaları ortak kayıt dışında
- **Sorun:** [DOĞRULANDI: F110] rag.db, hallucination.db, ml_ops.db, ux_shares.db sahiplik kaydı ve ortak `connect()` dışında.
- **Değişiklik:** Hepsi `dbconn.database_file` ve `ownership.OWNED` kapsamına alınır.
- **Kabul:** Sahiplik testi bu tablolarda koşar; bağlantılar WAL ayarlı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### AUD-18 · Cevaplanamaz altın küme 3 kalıba dayanıyor
- **Sorun:** [DOĞRULANDI: F111] Altın kümedeki cevaplanamaz örnekler 3 kalıbın tekrarı; ölçüm şişik.
- **Değişiklik:** Elle yazılmış, çeşitli 150 cevaplanamaz soru eklenir.
- **Kabul:** Kalıp çeşitliliği (benzersiz şablon sayısı) raporlanır.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### AUD-19 · Yanlış öncül tablosu 4 varlıklı
- **Sorun:** [DOĞRULANDI: F111] `detect_false_premise` 4 varlık biliyor.
- **Değişiklik:** Genişletilebilir bilgi tabanı (kişi, tarih, ürün) ve kaynakla doğrulama.
- **Kabul:** Dışlanmış 100 yanlış-öncül sorusunda yakalama ≥ %70.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### AUD-20 · İnsan etiketli veri yok: ECE, κ, NLI F1 ölçülemiyor
- **Sorun:** [DOĞRULANDI: F112] Birçok kabul ölçütü etiketli veri istiyor; depoda yok.
- **Değişiklik:** Etiketleme arayüzü ve 300 çiftlik Türkçe etiketli küme toplanır.
- **Kabul:** ECE, Cohen κ ve NLI makro-F1 gerçek veriyle raporlanır.
- **Meta:** P1 · L · Bağ: - · Durum: açık

#### AUD-21 · Hız sınırı yalnız girişte
- **Sorun:** [DOĞRULANDI: F113] SEC-06 token-bucket istiyordu; yalnız giriş denemesi sınırlı.
- **Değişiklik:** `ratelimit.TokenBucket` orta katman olarak pahalı rotalara bağlanır; 429 + Retry-After.
- **Kabul:** Pahalı rotada 20 hızlı istek 429 verir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### AUD-22 · Eşzamanlı iş sınırının kullanıcı bazlı bağlanması
- **Sorun:** [DOĞRULANDI: F113] `JobLimiter` yalnız proje analizinde.
- **Değişiklik:** Araştırma, sunum, oyun üretimine bağlanır.
- **Kabul:** Bir kullanıcının 4. işi kuyrukta bekler, diğer kullanıcı bloklanmaz.
- **Meta:** P1 · S · Bağ: AUD-13 · Durum: açık

#### AUD-23 · Aktif içerik taraması yükleme yanıtında
- **Sorun:** [ÖNERİ] SEC-08 uyarıyı yanıt meta verisine istiyor.
- **Değişiklik:** `scan_active_content` sonucu sohbet ekinde de gösterilir.
- **Kabul:** Makrolu XLSM ve JS'li PDF uyarılır; metin çıkarımı çalışır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AUD-24 · Dosya türü sahteciliği reddi
- **Sorun:** [ÖNERİ] Uzantı ile içerik uyuşmazlığı kabul ediliyordu.
- **Değişiklik:** `declared_matches_content` her yükleme yoluna bağlanır.
- **Kabul:** exe'yi pdf diye yüklemek 415.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AUD-25 · Kimlik taşıyan test adlandırma kuralı
- **Sorun:** [ÖNERİ] Test adlarında madde kimliği tutarsız (sec11, SEC-11).
- **Değişiklik:** `test_<alan><no>_...` kuralı lint ile zorlanır.
- **Kabul:** Kural dışı adlı test uyarı verir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### AUD-26 · Kabul ölçütlerinin makine okunur hale getirilmesi
- **Sorun:** [ÖNERİ] Kabul satırları serbest metin.
- **Değişiklik:** Her kabul için `metric`, `threshold`, `command` alanları (YAML).
- **Kabul:** `plan_tool` eşiği olan maddeleri çalıştırıp sonucu PROGRESS'e yazar.
- **Meta:** P2 · M · Bağ: AUD-01 · Durum: açık

#### AUD-27 · PROGRESS'te ölçüm alanı
- **Sorun:** [ÖNERİ] `eval_report` boş string.
- **Değişiklik:** `measured` {değer, eşik, tarih} alanı.
- **Kabul:** Eşik tutmazsa done reddedilir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### AUD-28 · Plan v2 maddelerinin yeniden denetim takvimi
- **Sorun:** [ÖNERİ] Tek seferlik denetim eskir.
- **Değişiklik:** Haftalık otomatik denetim işi.
- **Kabul:** Denetim raporu CI artefaktı olarak yüklenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### AUD-29 · Denetim raporunda dürüstlük bölümü
- **Sorun:** [ÖNERİ] Başarılar öne çıkıyor, boşluklar gömülü.
- **Değişiklik:** Rapor "kanıtlanamayanlar" tablosuyla başlar.
- **Kabul:** Tablo boş değilse özet satırında uyarı çıkar.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### AUD-30 · Tüm "done" maddeler için sürümlü kanıt commit'i
- **Sorun:** [ÖNERİ] Commit kanıtı sonradan değişen koda işaret ediyor.
- **Değişiklik:** Kanıt commit'inde dosyaların hâlâ var olduğu doğrulanır.
- **Kabul:** Silinmiş kanıt dosyası done'ı partial'a çevirir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### AUD-31 · Kullanılmayan modüllerin eylem listesi
- **Sorun:** [ÖNERİ] Bağlantı kapısı allowlist'i uzuyor.
- **Değişiklik:** Allowlist her girişe gerekçe ve bitiş tarihi ister.
- **Kabul:** Süresi dolan giriş CI'ı kırar.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### AUD-32 · Test yürütme sürelerinin raporu
- **Sorun:** [ÖNERİ] Hangi testin yavaş olduğu bilinmiyor.
- **Değişiklik:** `--durations` çıktısı raporlanır.
- **Kabul:** 10 en yavaş test listelenir.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### AUD-33 · Sahte (mock) test oranının ölçülmesi
- **Sorun:** [ÖNERİ] Bazı testler gerçek davranış yerine yalnız çağrı sayısını sınıyor.
- **Değişiklik:** Sahte nesne kullanımı sayılır; kritik paketlerde eşik konur.
- **Kabul:** Eşik aşan test dosyası inceleme listesine girer.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### AUD-34 · Test kapsamında "kabul kopyası" etiketi
- **Sorun:** [ÖNERİ] Hangi testin kabul ölçütünü sınadığı belli değil.
- **Değişiklik:** `@acceptance("SEC-07")` işareti.
- **Kabul:** İşaretli test sayısı madde başına raporlanır.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### AUD-35 · Antigravity/başka araç değişikliklerinin birleştirme denetimi
- **Sorun:** [ÖNERİ] Aynı dalda paralel çalışan araçlar çakışma yaratıyor.
- **Değişiklik:** Birleştirmeden önce `plan_tool check` ve test kapısı zorunlu.
- **Kabul:** Kapısız birleştirme dal korumasıyla engellenir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### AUD-36 · PR şablonunda "kanıt" bölümü
- **Sorun:** [ÖNERİ] Şablon kontrol listesi var, kanıt alanı serbest.
- **Değişiklik:** Kanıt alanı test adı ve komut ister.
- **Kabul:** Boş kanıtlı PR CI'da uyarılır.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### AUD-37 · Ölçülemeyen kabul ölçütlerinin yeniden yazılması
- **Sorun:** [ÖNERİ] "Gerçek tezgâhta", "temiz Windows 11" gibi ölçütler CI'da koşmaz.
- **Değişiklik:** Ölçülebilir proxy ölçütü ve ayrı manuel kontrol listesi yazılır.
- **Kabul:** Her maddede otomatik ve manuel kısım ayrı.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### AUD-38 · Plan v2 madde numaralarının kalıcılığı
- **Sorun:** [ÖNERİ] Madde silinince numaralar kayıyor.
- **Değişiklik:** Numaralar yeniden kullanılmaz; silinen madde "kaldırıldı" olarak kalır.
- **Kabul:** Kimlik çakışması testi geçer.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### AUD-39 · Eval raporlarında veri sızıntısı denetimi
- **Sorun:** [ÖNERİ] Eğitim ve ölçüm kümesi karışabilir.
- **Değişiklik:** Küme dosyalarına hash ve `split` alanı; çakışma testi.
- **Kabul:** Ölçüm kümesi örneği eğitimde görülürse test kırar.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### AUD-40 · Eval raporu şeması doğrulaması
- **Sorun:** [ÖNERİ] Rapor alanları tutarsız.
- **Değişiklik:** JSON şeması ve doğrulama.
- **Kabul:** Şemaya uymayan rapor yazılmaz.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### AUD-41 · Tüm sayısal iddiaların rapora izlenebilirliği
- **Sorun:** [ÖNERİ] README'deki sayılar elle yazıldı.
- **Değişiklik:** Sayılar `plan_tool render` ile PROGRESS/eval raporlarından üretilir.
- **Kabul:** Elle yazılmış sayı farkı CI'ı kırar.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### AUD-42 · Gerileme (regression) panosu
- **Sorun:** [ÖNERİ] Skorlar zamanla düşebilir.
- **Değişiklik:** Eval skorlarının zaman serisi ve gerileme uyarısı.
- **Kabul:** Skor 2 puan düşerse uyarı.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### AUD-43 · Test izolasyonu: testler izlenen dosyaları yazmamalı
- **Sorun:** [ÖNERİ] Eval raporları test sırasında yeniden yazılıyordu.
- **Değişiklik:** Tüm testler geçici dizine yazar; `git status` temiz kalır.
- **Kabul:** Test sonrası `git status` temiz (CI kontrolü).
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### AUD-44 · Sürüm ve değişiklik günlüğü otomasyonu
- **Sorun:** [ÖNERİ] Değişiklik günlüğü elle tutuluyor.
- **Değişiklik:** Commit türlerinden CHANGELOG üretimi.
- **Kabul:** Sürümde CHANGELOG bölümü otomatik.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### AUD-45 · Demo ve gerçek durum ayrımı rozeti
- **Sorun:** [ÖNERİ] Demo veri ile gerçek veri karışabilir.
- **Değişiklik:** Arayüzde "örnek veri" rozeti.
- **Kabul:** Örnek veri hiçbir zaman gerçek gibi görünmez.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### AUD-46 · Dış bağımlılıkların bulunmadığında dürüst hata
- **Sorun:** [ÖNERİ] Docker/Ollama/VLM yokken bazı özellikler sessiz kapanıyor.
- **Değişiklik:** Her bağımlılık için ready durumu ve eyleme dönük mesaj.
- **Kabul:** Bağımlılık kapalıyken özellik nedenini söyler.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### AUD-47 · Kabul testlerinin tek komutla koşması
- **Sorun:** [ÖNERİ] Testler dağınık.
- **Değişiklik:** `make acceptance` / `scripts/acceptance.ps1`.
- **Kabul:** Tek komut tüm kabul kopyalarını koşar.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### AUD-48 · Kabul sonuçlarının madde bazında HTML raporu
- **Sorun:** [ÖNERİ] Sonuçlar terminalde.
- **Değişiklik:** Madde × sonuç tablosu artefakt olarak üretilir.
- **Kabul:** Rapor partial ve başarısızları üstte gösterir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### AUD-49 · Plan dosyası dil ve yazım denetimi
- **Sorun:** [ÖNERİ] Plan metinlerinde tutarsız terim.
- **Değişiklik:** Terim sözlüğü ve lint.
- **Kabul:** Yasak terim kullanımı uyarılır.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### AUD-50 · Plan v2→v3 madde eşleme tablosu
- **Sorun:** [ÖNERİ] Hangi v3 maddesi hangi v2 maddesini düzeltiyor belli değil.
- **Değişiklik:** `yerine_gecer` alanı.
- **Kabul:** Her v3 AUD maddesi bir v2 kimliğine bağlı.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### AUD-51 · Dış denetçi için kanıt paketi
- **Sorun:** [ÖNERİ] Hoca/dış kişi doğrulayamıyor.
- **Değişiklik:** Tek zip: rapor, test çıktıları, ölçümler.
- **Kabul:** Paket temiz makinede tekrar üretilir.
- **Meta:** P2 · M · Bağ: - · Durum: açık

#### AUD-52 · Eski eval raporlarının geçerlilik tarihi
- **Sorun:** [ÖNERİ] Eski rapor güncel koda ait değil.
- **Değişiklik:** Rapor commit'i ve model sürümü yazılır; eskiyse uyarı.
- **Kabul:** Güncel kodla uyuşmayan rapor "eski" etiketli.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### AUD-53 · Hata enjekte testleri için ortak yardımcı
- **Sorun:** [ÖNERİ] Her test kendi sahtesini yazıyor.
- **Değişiklik:** `faults.py` hata enjeksiyon yardımcıları.
- **Kabul:** Yeni testler ortak yardımcıyı kullanır.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### AUD-54 · Planlanan ama hiç dokunulmamış madde listesi
- **Sorun:** [ÖNERİ] Hangi alan sessiz kaldı bilinmiyor.
- **Değişiklik:** Alan bazında son commit tarihi.
- **Kabul:** 90 gündür dokunulmayan alan raporlanır.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### AUD-55 · Kanıt commit'lerinin birleşmiş dala ait olduğu doğrulaması
- **Sorun:** [ÖNERİ] Kanıt yan dalda kalmış olabilir.
- **Değişiklik:** `git merge-base --is-ancestor` ile ana dal kontrolü.
- **Kabul:** Ana dalda olmayan kanıt uyarı verir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### AUD-56 · Rastgele madde örnekleme denetimi
- **Sorun:** [ÖNERİ] Tüm kanıtlar elle denetlenemez.
- **Değişiklik:** Her hafta 10 rastgele madde yeniden çalıştırılır.
- **Kabul:** Örnekleme sonucu raporlanır.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### AUD-57 · Denetim sonuçlarının hoca sunumuna özeti
- **Sorun:** [ÖNERİ] Ders teslimi için net görünüm yok.
- **Değişiklik:** Tek sayfa durum özeti.
- **Kabul:** Özet PROGRESS'ten otomatik üretilir.
- **Meta:** P3 · S · Bağ: - · Durum: açık

## TST · Test, kalite kapıları, süreç ve teslim

#### TST-01 · Uçtan uca (e2e) test altyapısı
- **Sorun:** [ÖNERİ] Tarayıcı e2e testi yok.
- **Değişiklik:** Playwright, sahte Ollama ile deterministik akışlar.
- **Kabul:** Sohbet, yükleme, ajan sayfası e2e geçer.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### TST-02 · Sahte Ollama ile deterministik sohbet testleri
- **Sorun:** [ÖNERİ] Testler gerçek modele ihtiyaç duyabiliyor.
- **Değişiklik:** `gateway/fake_ollama` senaryoları genişletilir.
- **Kabul:** Hızlı küme modelsiz koşar.
- **Meta:** P0 · M · Bağ: - · Durum: açık

#### TST-03 · Gerçek Ollama entegrasyon işi (isteğe bağlı)
- **Sorun:** [ÖNERİ] Gerçek model testi elle.
- **Değişiklik:** `integration` işaretli, isteğe bağlı iş.
- **Kabul:** Gerçek modelle 10 duman testi.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-04 · Özellik tabanlı testler (Hypothesis)
- **Sorun:** [ÖNERİ] Özellik testi yok.
- **Değişiklik:** Ayrıştırıcı, sanitizer, token sayacı.
- **Kabul:** Üç alanda özellik testi.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-05 · Mutation testi (kritik paketler)
- **Sorun:** [ÖNERİ] Test kalitesi ölçülmüyor.
- **Değişiklik:** mutmut ile `injection`, `safe_archive`, `policy`.
- **Kabul:** Öldürülen mutant ≥ %70.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-06 · Kritik paket kapsamı ≥ %90
- **Sorun:** [ÖNERİ] Kapsam ölçülmüyor.
- **Değişiklik:** coverage raporu ve eşik.
- **Kabul:** gateway/hallucination/auth ≥ %90.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-07 · Kontrat testleri: OpenAPI ve şema
- **Sorun:** [ÖNERİ] Şema doğrulama kısmen.
- **Değişiklik:** Tüm route yanıtları şemaya karşı doğrulanır.
- **Kabul:** 89+ route için şema testi.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-08 · Yük testi: eşzamanlı kullanıcılar
- **Sorun:** [ÖNERİ] Yük testi yok.
- **Değişiklik:** Locust senaryosu.
- **Kabul:** 20 eşzamanlı kullanıcıda hata < %1.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-09 · Soak testi: 1 saat sürekli
- **Sorun:** [ÖNERİ] Bellek sızıntısı bilinmiyor.
- **Değişiklik:** Uzun koşu ve bellek izleme.
- **Kabul:** 1 saatte bellek artışı < %20.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-10 · Windows ve Linux CI matrisi
- **Sorun:** [ÖNERİ] Yalnız tek ortam.
- **Değişiklik:** İki işletim sistemi.
- **Kabul:** İki OS'ta testler geçer.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-11 · Frontend birim testleri kapsamı
- **Sorun:** [ÖNERİ] 8 test var.
- **Değişiklik:** Kritik modüller için test.
- **Kabul:** Modüllerin ≥ %70'inde test.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-12 · Erişilebilirlik testi CI'da
- **Sorun:** [ÖNERİ] a11y otomatik değil.
- **Değişiklik:** axe testi.
- **Kabul:** Kritik ihlal 0.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-13 · Görsel gerileme testi
- **Sorun:** [ÖNERİ] Stil kırılması fark edilmiyor.
- **Değişiklik:** Ekran görüntüsü karşılaştırma.
- **Kabul:** Fark eşiği aşılırsa CI kırar.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-14 · Eval hızlı kümesi CI'da (HAL-05)
- **Sorun:** [ÖNERİ] Eval PR'da koşmuyor olabilir.
- **Değişiklik:** 30 örnek hızlı eval.
- **Kabul:** PR'da eval raporu yorumu.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-15 · Gece: tam eval + fuzz + yavaş testler
- **Sorun:** [ÖNERİ] Gece işi yok.
- **Değişiklik:** Zamanlanmış iş.
- **Kabul:** Gece raporu artefakt.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-16 · Flaky test tespiti
- **Sorun:** [ÖNERİ] Kararsız testler gizli.
- **Değişiklik:** Yeniden koşma ve işaretleme.
- **Kabul:** Flaky liste raporu.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-17 · Test verisi üreticileri (factory)
- **Sorun:** [ÖNERİ] Test verisi dağınık.
- **Değişiklik:** Ortak üretici.
- **Kabul:** Yeni testler üreticiyi kullanır.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### TST-18 · Hata enjeksiyon kitaplığı
- **Sorun:** [ÖNERİ] Hata testi tek tek.
- **Değişiklik:** Ortak hata enjekte araçları.
- **Kabul:** Ağ/disk/model hatası enjekte edilir.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-19 · Saat ve rastgelelik sabitleme
- **Sorun:** [ÖNERİ] Zaman bağımlı testler.
- **Değişiklik:** Saat sahtesi.
- **Kabul:** Zamana bağlı testler deterministik.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-20 · Dokümantasyon testleri: komut örnekleri çalışır
- **Sorun:** [ÖNERİ] Docs'taki komutlar çürüyor.
- **Değişiklik:** Kod bloklarını çalıştıran test.
- **Kabul:** Belgedeki `powershell` komutları geçerli.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-21 · Bağlantı kapısı (wiring) sıkılaştırma
- **Sorun:** [ÖNERİ] Allowlist uzuyor.
- **Değişiklik:** Allowlist'i azalt ve gerekçe iste.
- **Kabul:** Allowlist boyutu ≤ mevcut.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-22 · `plan_tool` kendi testleri
- **Sorun:** [ÖNERİ] Plan aracı testleri sınırlı.
- **Değişiklik:** Kimlik/kanıt/partial testleri.
- **Kabul:** Araç %90 kapsam.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-23 · Commit mesajı ve PR kuralı denetimi
- **Sorun:** [ÖNERİ] Kurallar elle.
- **Değişiklik:** commitlint benzeri.
- **Kabul:** Kural dışı mesaj CI uyarı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-24 · Pre-commit: ruff, format, gitleaks, JS lint
- **Sorun:** [ÖNERİ] Pre-commit kısmen.
- **Değişiklik:** Tam hook seti.
- **Kabul:** Hook'lar yerelde çalışır.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### TST-25 · Branch koruma ve zorunlu kontroller
- **Sorun:** [ÖNERİ] Ana dal korumasız olabilir.
- **Değişiklik:** Zorunlu CI ve inceleme.
- **Kabul:** Kontrolsüz birleştirme engelli.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-26 · Antigravity-Claude çakışma protokolü
- **Sorun:** [ÖNERİ] İki araç aynı dalda.
- **Değişiklik:** Dal sahipliği ve yeniden temellendirme kuralı.
- **Kabul:** Protokol CONTRIBUTING'de.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-27 · Ders gereksinimleri izlenebilirlik matrisi (PROC-01)
- **Sorun:** [ÖNERİ] Gereksinim-test eşlemesi kısmen.
- **Değişiklik:** Matris ve test bağlantısı.
- **Kabul:** Her ders gereksinimi bir teste bağlı.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-28 · MVP kesme çizgisi denetimi (PROC-10)
- **Sorun:** [ÖNERİ] MVP ders gereksinimini örtüyor mu belgesiz.
- **Değişiklik:** Çakışma kontrolü.
- **Kabul:** Eksik gereksinim 0.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-29 · Risk kaydı haftalık güncelleme (PROC-10)
- **Sorun:** [ÖNERİ] Güncelleme kanıtı yok.
- **Değişiklik:** Risk tablosu tarihli.
- **Kabul:** Son güncelleme ≤ 7 gün.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-30 · Demo senaryosu iki kez baştan sona (PROC-06)
- **Sorun:** [ÖNERİ] Senaryo oynatma kanıtı yok.
- **Değişiklik:** Betik ve kayıt.
- **Kabul:** İki kez sorunsuz çalıştırma günlüğü.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-31 · DoD kontrol listesi PR'da (PROC-04)
- **Sorun:** [ÖNERİ] Maddesiz PR birleşebilir.
- **Değişiklik:** Zorunlu liste.
- **Kabul:** Maddesiz PR birleşemez.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-32 · CONTRIBUTING: yapay zekâ aracı kuralları (PROC-05)
- **Sorun:** [ÖNERİ] Kanıt bölümü zorunlu mu kontrolsüz.
- **Değişiklik:** Kural ve şablon.
- **Kabul:** PR'da kanıt bölümü zorunlu.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-33 · Sprint raporlarının gerçek veriden üretimi
- **Sorun:** [ÖNERİ] Sprint raporu elle.
- **Değişiklik:** PROGRESS ve commit'ten üretim.
- **Kabul:** Rapor sayıları otomatik.
- **Meta:** P1 · M · Bağ: - · Durum: açık

#### TST-34 · Sözlük: terimler ve kısaltmalar
- **Sorun:** [ÖNERİ] Terim tutarsız.
- **Değişiklik:** Sözlük belgesi.
- **Kabul:** Sözlük README'den bağlı.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### TST-35 · Öğrenilen dersler günlüğü
- **Sorun:** [ÖNERİ] Geçmiş hatalar unutuluyor.
- **Değişiklik:** Kısa ders kayıtları.
- **Kabul:** Her olay sonrası kayıt.
- **Meta:** P2 · S · Bağ: - · Durum: açık
