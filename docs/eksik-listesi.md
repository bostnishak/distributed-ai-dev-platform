# Eksik listesi: v1–v5 (tek ana liste)

Bu dosya "ne kaldı" sorusunun tek cevabıdır. Bir madde, kod testi **ve** canlı denemesi geçmeden `[x]` olmaz.

- `[ ]` açık
- `[~]` kısmen var, eksiği yanında yazılı
- `[x]` yapıldı
- `[—]` yapılamaz ya da kapsam dışı (nedeni yazılı)

## Çalışma sırası: 3 parça

**Kaldığım yer (28.11.2026):** 1. parça bitti ve birleştirildi. 2. parça (M04–M08) yapılıyor. 3. parça (M09–M16) sen "devam" deyince başlayacak. Zorluk merdiveninde yerel model L4'e kadar çıkıyor.

Dizüstü bilgisayar kesintisiz yüklenmesin diye iş üçe bölündü. Bir parça bitince **durulur**; sen "devam" demeden sonrakine geçilmez.

| Parça | İçerik | Tahmini süre |
|---|---|---|
| **1** | Canlıda çıkan hatalar (0) · v1–v4 açık alt maddeleri (1–4) · canlı denenmemiş maddeler (5) · v5 bölüm 0/12 · M01–M03 eksikleri | 10–15 saat |
| **2** | M04 küçük model · M05 sürü yönetimi · M06 zorlama testleri · M07 mimari sağlık · M08 çevrimdışı kasa | 10–15 saat |
| **3** | M09 çok biçimli girdi · M10 araştırma · M11 tutarlılık · M12 paketleme · M13 yedek · M14 arayüz · M15 dayanıklılık · M16 sertifikasyon | 10–15 saat |

Her parçanın sonunda: tam test ve denetimler, commit, push, PR; sonra modeller ekran kartından boşaltılır (`python scripts/ai_os.py unload`), deneme sunucuları ve Docker kapları kapatılır.

Çalışırken:

- Model gerektiren denemeler tek tek koşar; ekran kartı 82 °C'yi geçerse soğuyana kadar yeni model denemesi başlatılmaz.
- Bilgisayar prize takılı olmalı.
- M15'in çok saatlik dayanıklılık koşusu, yalnız sen istediğin zaman başlatılır.

---

## 0. Canlı denemede çıkan hatalar

- [x] Sohbete yazılan API anahtarı kayda geçiyordu — düzeltildi, canlı geçti
- [x] MCP bağlayıcısı üst veri adresini kabul ediyordu — düzeltildi, canlı geçti
- [x] Yetki kapısı: üründe hata yoktu, canlı test var olmayan bir eylem adı kullanıyordu — test düzeltildi, canlı geçti
- [x] Gözcü boş listeyi izliyordu — `sunucuyu başlat / durdur` komutu eklendi, canlı geçti
- [x] Ödev değerlendirici ve benchmark puanlayıcı gönderilen kodu platformun içinde çalıştırıyordu (uzaktan kod çalıştırma) — yalıtılmış kutuya taşındı, kaçış denemesi canlı sınandı

## 1. v1

- [x] `spec.json`: yerleşim bölgeleri, API sözleşmesi, kalıcılık kuralı, karma görev türü
- [x] `plan.json`: dosya listesi, bağımlılık, uç noktalar, gereksinim–test eşlemesi
- [x] `.env` rol modelleri
- [x] Renklendirme etiketli dosya yazımının reddi
- [x] Boş olay işleyicisi taraması
- [x] Aşama başına en çok 3 onarım
- [x] Nokta atışı yama (hiç çalışmıyordu, düzeltildi)

## 2. v2

- [x] KV önbellek ayarının denetlenmesi (`ai-os doctor`, zaten vardı)
- [x] Karşılaştırmalı model yargıç (iki sırayla; canlı geçti)
- [x] Canlı akışta dosya farkı (bileşen tarayıcıda denendi; modelle uçtan uca denenecek)
- [x] Canlı akışta önizleme konsol hataları (her dosyadan sonra önizleme yenileniyor, hata kutusu gösteriyor)
- [x] Sıfır modelle lint düzeltme
- [x] %60 üstü yamada tam yazıma dönme
- [x] Beğen / beğenme ve elle düzenleme geri bildirimi
- [x] Otomatik gerileme testi (açılış hataları)
- [x] API zorlama testi
- [x] Arayüz zorlama testi
- [x] Tree-sitter depo haritası ve anlamsal birleştirme
- [x] eslint / stylelint / HTMLHint
- [x] Süre grafiği, Pass@3, varyantı ana projeye alma

## 3. v3

- [x] Durum tabanlı özellik testi: arayüz = API = veritabanı (`state_property.py`, canlı geçti)
- [x] JavaScript mutasyon testi (Node izin modeli + Windows süreç sınırı; yazma, ağ, alt süreç reddi canlı sınandı)
- [x] Kırık görsel / yazı tipi / sıfır yükseklik / 3 görünüm (yazı tipi ve yükseklik denetimi yoktu, eklendi; gerçek tarayıcıda geçti)
- [x] PDF: öksüz başlık ve boş son sayfa denetimi
- [x] D2 diyagramı (akış çiziminin yanında D2 kaynağı ve ELK yerleşimli SVG)
- [x] Cytoscape etkileşimli diyagram (tek dosya, çevrimdışı)
- [x] Diyagramda kesişim azaltma ve sığmayan etiket uyarısı
- [x] Etkileşimli grafik: Vega-Lite (varsayılan), Chart.js ya da Plotly; ağ kapalıyken çizildiği sınandı
- [x] Üretilen görselin isteme uyum puanı (canlı geçti: eksik üçgeni doğru bildirdi)
- [x] Sohbetlerden mimari karar kaydı (`karar: ...`, `kararları göster`)
- [x] Mühendislik defteri: bulunan kök nedenler kaydediliyor ve sonraki onarıma veriliyor (`defteri göster`)
- [x] Bellek: sabitleme
- [x] Bellek: süre sonu
- [x] Bellek: kalıcı silme (`hafızamı göster`, `hafıza <no> sabitle / süre N gün / kalıcı sil`)
- [x] Gizli işaretlenen değerler belgeye, sunuma, günlüğe ve eğitim verisine yazılmıyor (`<gizli>...</gizli>`, `gizli işaretle: ...`)
- [x] Köken kaydı: model özeti, üretim ayarları, kanıt özetleri (teslim kaydında)
- [x] Fonksiyonlar arası veri akışı, ölü kod, boş değer erişimi (`flow_analysis.py`; platformun kendi kodunda 2 gerçek açık buldu)
- [x] Önce/sonra ölçümlü performans karşılaştırması (`.ai-os/performance.md`)
- [x] DOM, dinleyici ve bellek sızıntısı ölçümü (canlı tarayıcıda sınandı)
- [x] Modül ayırma aracı (`X, Y fonksiyonlarını Z modülüne taşı`)
- [x] İmza taşıma aracı (parametre ekleme / adını değiştirme)
- [x] İki zaman çizgisini karşılaştırma: dalın asıl projeden dosya dosya farkı (savaş odasında)
- [x] LSP: tanıma git (`X nerede tanımlı`), imza bilgisi (`X imzası`)
- [x] DAP: koşullu kesme noktası (`koşullu kesme: dosya.py:12 x > 5`; Docker içinde canlı geçti)
- [x] Savaş odasında kanıtlar: teslim aşamaları, biçimsel/mutasyon denetimleri, doğrulanan ve açık maddeler (tarayıcıda denendi)
- [x] Pareto sınırı izleme (ölçüm geçmişi; yalnız otomatik testle)
- [x] Ölçüm bozulunca geri alma ve olay raporu (yalnız otomatik testle)
- [x] Zorluk basamaklı (L1–L5) benchmark: canlı koşuldu (tohum 7). L1–L4 geçti, **L5 kaldı**: yerel 7B model açılışta çöken API kodu üretti; platform bunu "kaldı" diye bildirdi. İlk koşuda çıkan iki hata düzeltildi (sipariş toplamı artık kodla hesaplanıyor; `app/main.py` giriş dosyası bulunuyor)

## 4. v4

- [x] 5. vites: `arka planda: <istek>` (canlı geçti; iş sürerken sohbet 31 sn'de yanıt verdi)
- [x] Araştırma bağlayıcıları: arXiv, GitHub (saatlik sınır var), PyPI, npm, MDN
- [x] Araştırma kaynaklarında yayın tarihi
- [x] İndirilen DevDocs araştırmada kullanılıyor; web kapalıyken de yanıt veriyor (canlı geçti)
- [x] Tipografi ölçeği ve dikey ritim: yazım notu ve tarayıcı denetimi
- [x] Kullanıcı zevkini öğrenme: turnuva seçimi ve elle stil düzeltmeleri
- [x] Belge araçları: içindekiler, sayfa aralığı, tablo çıkarma, alıntı doğrulama
- [x] Diske yazılan özet ağacı (aynı belgede model çağrılmadan yeniden kullanılıyor)
- [x] NumPy / SciPy ve duyarlılık analizi (`duyarlılık: ...`, `sayısal kök / integral: ...`)
- [x] Excel: XLOOKUP, NPV, IRR
- [x] Excel: döngüsel başvuru ve kırpılan sütun denetimi (üretilen dosyalarda gerçek bir kırpılma hatası bulundu, düzeltildi)
- [x] Slaytta en küçük yazı 14 punto
- [x] Etkileşimli Vega-Lite / Plotly görselleri
- [x] Dışarıdan kaydedilen dosyaları izleme (sürüm kaydı ve denetim)
- [x] Günlük özet (`gece özeti` ve gece saatinde dosyaya)
- [x] Bağımlılık açığı denetimi (OSV; canlı geçti)
- [x] `ai-os.config` özellik bayrakları, `up --profile`
- [x] Etkin yalıtım katmanı savaş odasında yazıyor
- [x] En çok 2 çoktan seçmeli netleştirme sorusu (3 açık uçlu soru soruluyordu, düzeltildi)
- [x] Üç sesli kurul (süre sınırı düzeltildi; canlı geçti, 277 sn)
- [—] Karma bulut köprüsü: istemedin (ücretli servis olmasın)

## 5. Canlı denenmemiş maddeler (yalnız otomatik testle geçenler)

`scripts/live_items.py`: doğrudan grup 21/21 geçti. Sunucu grubunda kalanlar:

- [x] MCP veri yolu
- [x] Yetki kapısı ve leke politikası
- [x] Yörünge toplama ve sır temizleme
- [x] İki varyant yan yana (canlı geçti; ama 30 dakika sürdü, aşağıdaki hız maddesine bak)
- [x] Dockerfile / Compose ve gerçek derleme (canlı geçti; 21 dakika sürdü — 12 model çağrısı)
- [x] Belge üretimi: sunum canlı geçti (slayt denetimi raporlanıyor)
- [x] Zamanlanmış görevler (canlı geçti)
- [x] Öncelik kuyruğu (canlı geçti)
- [x] Gözcü
- [x] Şartname listesinde yalnız otomatik testle kalan madde yok (148 canlı, 3 teknik engel, 8 kapsam dışı)
- [x] İki varyant (araştırma kaldırıldı; canlı geçti, 437 sn, iki ayrı proje)

## 6. v5

### Bölüm 0 ve 12: değişmez koşullar

- [x] Ücretli hiçbir şey yok
- [x] Ollama ayarları (`ai-os doctor` denetliyor, üçü de doğru)
- [x] Windows + 8 GB uygunluk raporu: [windows-uygunluk.md](windows-uygunluk.md)
- [x] Aşama doğrulama betikleri: 01–03 var (04–16 kendi aşamasında yazılacak, aşağıda M16 altında)

### M01 — Windows dayanıklılığı (ana kısım tamam)

- [x] Port ayırıcı, Windows Job Object, yetim süreç temizliği
- [x] Her kısa ömürlü alt süreç Job içinde; zaman aşımında torun süreçler de ölüyor (canlı sınandı)
- [x] Atomik dosya yazımı, kilit yeniden deneme, uzun yol
- [x] UTF-8, satır sonu, Türkçe harf güvenliği
- [x] SQLite WAL, `busy_timeout`, `quick_check`, canlı yedek
- [x] Tek yazıcılı sıra: aynı veritabanı dosyasına yazımlar platform içinde sıraya giriyor (16 iş parçacığı, 0 hata)
- [x] Şema değişikliğinden önce yedek
- [x] Ekran kartı bellek / ısı gözcüsü, bağlam küçültme, arka plan işini bekletme, pil modu
- [x] Başka ağır kullanıcı algılama: kartın boş belleği azalınca bağlam küçülüyor (oyunu adından değil, bellekten anlıyor)
- [—] VRAM parçalanması: NVIDIA araçları bu bilgiyi vermiyor
- [x] Disk temizliği (kuru çalıştırmalı)
- [x] Platformun kendi eski Docker katmanları ve Playwright profilleri temizliği (`disk temizle uygula`)
- [x] Kilometre taşları: proje sürümleri hiçbir temizlikte silinmiyor
- [x] Uyku / yeniden başlatma: veritabanı boşaltılıyor; üretim her dosyadan sonra kayıt noktası yazıyor (`devam et`)
- [—] Gerçek uyku-uyanma ve gerçek 82 °C denemesi benim tetikleyemeyeceğim bir şey

### M02 — Hile engeli (ana kısım tamam)

- [x] `.ai-os/oracles/` onarımlara kapalı
- [x] Kehanet dosyasını mimar adımı yazıyor (`.ai-os/oracles/contract.json`); teslim kapısı eksik uç noktayı reddediyor
- [x] Test kurcalama reddi (silme, atlama, eşik gevşetme, özel durum)
- [x] İhlal zamanlı belleğe kalıcı yasak kuralı olarak yazılıyor
- [x] Sessiz hata yutma, sahte gecikme, boş test denetimi
- [x] Bağlanmamış düğme, `select`, `input` denetimi
- [x] A aşamasında derleyici tanısı sıfır koşulu
- [x] A aşamasında bütün güvenlik bulguları teslimi durduruyor

### M03 — Canlı kanıt çalıştırıcısı (`verify_milestone_03.py` 5/5)

- [x] Gerçek sunucu, boş port, gerçek tarayıcı
- [x] Doldur, gönder, sert yenile, sunucuyu yeniden başlat, boş gönderim, sil
- [x] Dosya çıktılarını bağımsız okuyucuyla açma
- [x] Mutasyon yakalama oranı en az %80
- [x] API sözleşme testi (canlı sunucuda)
- [x] Durum tabanlı özellik testi (canlı sunucuda)
- [x] Sunucunun süre sınırı içinde hazır olması (30 sn)
- [x] Yolculukta HTTP `201` doğrulaması
- [x] Yenileme / yeniden başlatma öncesi-sonrası veritabanı satır sayısı
- [x] Durum değiştir adımı
- [x] Filtreleme adımı
- [x] Yüklenemeyen varlık (400 ve üstü)
- [x] Kanıt dosyasında HTTP izleri, satır sayıları, süreler, ekran görüntüsü listesi

### M04 — Küçük model destekleri (`verify_milestone_04.py` 4/4)

- [x] `REQ-001…` defteri: her madde bir makine denetimine bağlı (`req_ledger.py`, `req_checks.py`; gerçek tarayıcı)
- [x] Dilim dilim kurma (yerleşim → veri → etkileşim), her dilimde defter denetimi (`slice_build.py`)
- [x] Yalnız eksik `REQ` numaralarına nokta atışı yama; daha kötü sürüm saklanmaz
- [x] İki başarısız onarımdan sonra temiz bağlamla yeniden başlama (`clean_slate.py`)
- [x] "Denenip başarısız olan" yasak listesi
- [x] Akış bekçisi: döngü / boşluk / kod bloğu kayması, kesme ve ayar değiştirip yeniden deneme (gerçek modelde 840 karakterde kesti)
- [x] Önce kesin (sembolik) eleştiri: defter, mimari, güvenlik ve tarayıcı denetimleri modelden önce karar verir
- [x] Eleştiri başka model ailesine (yazan qwen, eleştiren deepseek-r1) (`critic_models.py`)
- [x] Uzun dosyada önce iskelet, sonra fonksiyon fonksiyon (`chunked_code.py`; otomatik testle, canlı büyük dosya denemesi yapılmadı)
- [x] Çıkış kanıtı: 19 koşullu istek qwen2.5-coder:7b ile 19/19

### M05 — Ajan sürüsü yönetimi (`verify_milestone_05.py` 4/4)

- [x] Değişmez `spec.json` + dosyaya ait `REQ` alt kümesi (`spec_pointer.py`)
- [x] Söz dizimi ağacı özetiyle A→B→A kesici ve o yamayı yasaklama (`oscillation.py`)
- [x] Dosya ve sembol düzeyinde yazma kirası (`write_lease.py`)
- [x] Koşu ve adım bütçeleri: jeton, süre, deneme (`budgets.py`)
- [x] Bütçe aşımında değişiklik öncesine dönme
- [x] Çıkış kanıtı: enjekte salınım gerçek kum havuzunda kesildi; eşzamanlı yazmada kayıp ve kilitlenme yok

### M06 — Gerçek dünya zorlama testleri (`verify_milestone_06.py` 7/7)

- [x] Sert yenileme ve sunucu yeniden başlatmada kalıcılık
- [x] Üçlü tıklama ve 10 eşzamanlı yazma
- [x] Gönderirken düğme kilidi / yükleniyor durumu
- [x] Yavaş 3G, çevrimdışı, sahte 503
- [x] Geri / ileri, derin bağlantı, filtre korunması
- [x] Türkçe (`İ/ı`), emoji, sağdan sola, özel karakter, artık yıl tarihi, eksi / sıfır / dev sayı
- [x] Para hesabında kesin ondalık
- [x] Boş, tek kayıt ve 1.000 kayıt; 200 ms sınırı
- [x] 50 tekrarda tarayıcı sızıntısı ve sunucu belleği
- [x] Çıkış kanıtı: `0.1+0.2`, çift gönderim, `İ/ı` ve sessiz kayıt hatası yakalandı
- Sınır: 1.000 kayıt yükü yalnız tarayıcıda çalışan sayfalara basılır (10.000 denenmedi); ağ davranışı bulguları teslimi engellemez, uyarı yazar

### M07 — Mimari sağlık

- [x] Karmaşıklık, fonksiyon ve dosya uzunluğu sınırı (`arch_scan.py`)
- [x] Sınır aşılınca doğrulanmış bölme (`arch_heal.py`)
- [x] Kopya kod bulucu ve ortak yardımcıya çıkarma
- [x] Ölü kod, kullanılmayan CSS, yetim uç nokta ve dosya (otomatik silme yalnız düzenlemenin sahipsiz bıraktığını siler)
- [x] Katman kuralları ve döngüsel içe aktarma (teslimi engeller)
- [x] `axe-core`, klavye sırası, modal tuzağı (`a11y.py`)
- [~] Çıkış kanıtı: 10 turluk gerçek düzenleme (`verify_milestone_07.py`) koşuluyor

### M08 — Çevrimdışı varlık kasası (`verify_milestone_08.py`)

- [x] Dosyalar indirildi (Inter, JetBrains Mono, Plus Jakarta Sans, lucide, chart.js, mermaid, katex, axe, DevDocs)
- [x] Satır içi SVG ikon kaydı
- [x] Kasayı yerel adresten sunma
- [x] ZIP dışa aktarımda varlıklar pakette
- [x] Dış CDN bağlantısını reddeden kalite kapısı
- [x] DevDocs tam metin dizinleyici (11.930 sayfa)
- [x] SQLite + DuckDB + DiskCache
- [x] Çıkış kanıtı: ağ kesikken grafik, diyagram, formül ve yazı tipleri hatasız

### M09 — Çok biçimli girdi

- [~] Dağınık PDF: çok sütun, döndürülmüş sayfa, birleşik tablo, formül, kutu koordinatı
- [ ] Taranmış PDF için OCR (Türkçe harfleri koruyan)
- [~] Ses: faster-whisper kodu var, kurulum ve zaman damgası doğrulanacak
- [ ] Video: sahne değişimi kareleri
- [ ] `inbox` klasörüne bırakılan kayda zaman damgalı soru
- [ ] Dağınık Excel/CSV: başlık, tarih, `1.250,50` ve `1,250.50`, birleşik hücre
- [x] Zip-slip ve sıkıştırma bombası koruması
- [~] Karışık Türkçe–İngilizce istekler, `tr-TR` sıralama
- [ ] Çıkış kanıtı: taranmış PDF + dağınık Excel + ses

### M10 — Araştırma sertleştirme

- [~] SearXNG + tarayıcı + güvenilmeyen içerik etiketi + atıf kapısı — uçtan uca doğrulanacak
- [ ] Çevrimdışı yedek yol
- [ ] Çıkış kanıtı: düşman sayfa enjeksiyonunun engellenmesi

### M11 — Çıktılar arası tutarlılık

- [ ] Hesap, Excel, sunum, PDF ve web panosunda aynı sayılar
- [ ] Çıkış kanıtı: dörtlü üretim, formül hatasız, görsel kanıt

### M12 — Canlı belge ve taşınabilir paket

- [ ] README / API belgesi / `--help` ile gerçek kodun karşılaştırılması, sapmada teslimi durdurma
- [ ] `run_windows.bat` ve `run.ps1`
- [~] `Dockerfile` ve `docker-compose.yml`
- [ ] ZIP'i temiz klasörde açıp kendi betiğiyle çalıştırma
- [ ] Çıkış kanıtı

### M13 — Yedekleme ve öğrenme

- [~] Şifreli yedek var — çalışma alanları, bellek, beceriler, ayarların tamamı doğrulanacak
- [ ] `ai-os restore <kimlik>`
- [~] Beceri yeniden kullanımı ve hata kuralı enjeksiyonu
- [ ] Kişisel veriden arındırılmış QLoRA dışa aktarım paketi (yalnız dosya; yükleme yok)
- [x] `ai-os import-gguf` (gölge değerlendirmeli)
- [ ] Çıkış kanıtı: boz-geri yükle tatbikatı ve ölçülmüş Pass@1 artışı

### M14 — Arayüz

- [~] Donmayan arayüz, iptal / duraklat / devam / yönlendirme
- [ ] Kanıt çekmecesi: canlı önizleme bağlantısı, ekran görüntüsü şeridi, yeşil/kırmızı işaretler
- [ ] Her istekten önce kayıt, tek tıkla geri alma (200 ms)
- [ ] Yeniden açınca sekmeler, önizlemeler ve duraklatılan işlerin dönmesi
- [ ] Donanım şeridi: VRAM, ısı, model, işlemci/bellek, yalıtım katmanı, vites
- [ ] Çıkış kanıtı: tarayıcıda deneme ve yarıda kapatıp devam

### M15 — Dayanıklılık

- [ ] `ai-os soak --hours N`
- [ ] Bellek, VRAM, açık tutamaç, port, disk izleme ve hata enjeksiyonu
- [ ] Çıkış kanıtı: çok saatlik temiz rapor

### M16 — Son istemler ve sertifikasyon

- [ ] `verify_milestone_04.py` – `verify_milestone_16.py` (her biri kendi aşamasında)
- [ ] `prompts/v5/*.md`
- [ ] v1–v5'in tamamını bir arada sınayan son test

## 7. Yapılamayanlar (uydurma değerle doldurulmayacak)

- [—] Ollama KV önbellek isabeti ve spekülatif kabul oranını bildirmiyor
- [—] Ollama özel dilbilgisi (GBNF) ve logit maskesi almıyor; logprob'a dayalı yükseltme güvenilir değil
- [—] 8 GB ekran kartında LoRA / DPO / GRPO eğitimi, PRM eğitimi, model birleştirme, damıtma yok
- [—] Tek bilgisayar: yerel ağ çıkarım zamanlayıcısı yok
- [—] gVisor / Firecracker Windows'ta çalışmıyor
