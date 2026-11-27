# Sohbet komutları

Hepsi bu bilgisayarda çalışır; ücretli servis ya da anahtar gerekmez. Normal soru ve isteklerini düz cümleyle yazabilirsin; aşağıdakiler özel işler içindir.

## Proje üretimi ve düzenleme

| Yaz | Ne yapar |
|---|---|
| `... web uygulaması yap` | Proje üretir. Sağ alttaki **Ajan grafiği** düğmesinden canlı izlenir, duraklatılır, talimat eklenir, bekleyen adım değiştirilir ya da atlanır; sürümden dal açılır. |
| `devam et` / `devam et ama ...` | Yarım kalan projeyi sürdürür |
| `geri al`, `v2'ye dön` | Önceki sürüme döner |
| `paralel ajanlar: görev 1 ; görev 2` | Her görev ayrı git çalışma kopyasında yapılır, anlamca birleştirilir, testler geçmezse proje değişmez |
| `yük testi yap` | Projenin API'sini ağsız kutuda yükler |
| `X nerede kullanılıyor`, `projede ... nerede` | Kod araması |

## Karar ve karşılaştırma

| Yaz | Ne yapar |
|---|---|
| `en iyi 3 seçenek: <karar>` | Üç farklı tasarım, puan tablosu ve öneri |
| `iki varyant ... tasarla` | Aynı isteğin iki görsel tasarımı |
| `turnuva: <web isteği>` | Aynı isteği iki modelle üretir, süre ve denetimleri yan yana gösterir. Model seçmek için `turnuva (model1, model2): ...` |
| `kazanan: <model>` | Seçimini kalıcı tercih yapar |
| `model kapısı: aday, taban` | İki modeli çalıştırılarak doğrulanan görevlerle ölçer |

## Doğrulama ve analiz

| Yaz | Ne yapar |
|---|---|
| `durum makinesi: yeni -onayla-> onaylı; ...; son: kapalı` | Çıkmaz, döngü, yetim durum ve yarış taraması (projede `TRANSITIONS` tablosu da okunur) |
| `sözleşme bağla: proje1, proje2` | Ortak veri sözleşmesi olan projeleri bağlar |
| `alan değiştir: tablo.eski -> yeni` | Etkilenen yerleri ve göç kanıtını gösterir, dosyaya dokunmaz |
| `alan değiştir uygula: tablo.eski -> yeni` | Tüm bağlı projeleri birlikte değiştirir; biri başarısızsa hepsi geri döner |
| Dosya ekleyip `belgenin tamamını ...` | Belgeyi baştan sona okur, sayfa ya da satır numarasıyla alıntı verir |
| `@tarayıcı <adres> <görev>` | Web sayfasında işlem yapar; geri alınamaz düğmeler için `onay: <düğme adı>` ister |

## Ses

| Yaz | Ne yapar |
|---|---|
| `sesli oku: <metin>` ya da yalnız `bunu sesli oku` | Türkçe ses dosyası üretir (Piper) |

Ses dosyası `master/data/voices/` içindedir (`tr_TR-dfki-medium`). Veri seti lisansı CC BY-NC-SA 4.0: **ticari kullanılamaz**.

## Sistem

| Yaz | Ne yapar |
|---|---|
| `kalite durumu`, `performans durumu`, `servis durumu` | Ölçüm sonuçları, süreler, açık ağır servisler |
| `kendi kendine alıştırma: 3` | Yeni görev üretip çözmeyi dener |
| `tercihlerimi göster` / `tercihlerimi sil` | Kalıcı tercihler |
| `buluta hazırla: <metin>` | Metindeki kişisel bilgileri gizler. Hiçbir yere göndermez |

## İsteğe bağlı gece işleri

Sunucuyu başlatmadan önce ortam değişkeni verilirse, bilgisayar boştayken o saatte çalışır:

- `SELF_EVAL_HOUR=3` kalite ölçümü
- `SELF_PLAY_HOUR=4` kendi kendine alıştırma

GGUF model içe aktarma (ölçüm kapısından geçmezse yayımlanmaz):

```powershell
master\venv\Scripts\python.exe scripts\ai_os.py import-gguf C:\yol\model.gguf --baseline qwen2.5-coder:7b
```
