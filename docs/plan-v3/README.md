# Plan v3 — doğrulanmış eksikler ve yol haritası

**1418 madde.** Bunların **1044'i doğrulanmış bulgu** (çalıştırılmış bir yoklama, tarama veya gerçek istek ürettiği kanıta bağlı), **374'i yol haritası** (34 program ve 340 iş paketi; `[ÖNERİ]`, 07 ve 08 numaralı dosyalarda).

Önceki taslak (566 aday öneri) `aday-oneriler/` altında duruyor; orada çoğu madde henüz doğrulanmadı ve sayıya dahil değildir.

## 1. Bu plan nasıl üretildi

Proje bu oturumda izole bir sunucuda (port 8099, geçici veri) gerçekten çalıştırıldı ve beş yolla incelendi:

1. **HTTP yoklaması:** 162 route'a istek, başlık/CORS/hız sınırı/bozuk JSON/yol geçişi/şema kontrolleri.
2. **Gerçek sohbet bataryası:** 148 istek gerçek modele (qwen3.5) gönderildi, yanıtlar makinece denetlendi (olgusal, hesap, talimat, kod çalıştırma, dosya, güvenlik, üretim istekleri).
3. **Eksik yetenek taraması:** ChatGPT/Claude/Gemini sınıfı asistanların sunduğu 197 yetenek için kodda ve OpenAPI'de iz arandı; **hiç iz bulunmayanlar** madde yapıldı.
4. **Statik analiz:** ruff (güvenlik, karmaşıklık, hata yutma, dinamik SQL) ve arayüz kaynak taraması.
5. **Tarayıcı taraması:** 8 sayfa açılıp konsol/ağ/erişilebilirlik ve mobil denetimi yapıldı.

Kanıt dosyaları `kanit/` altındadır; yoklama betikleri `scripts/audit/` altındadır ve yeniden çalıştırılabilir.

## 2. Denetim bulguları (yeniden üretilebilir)

Komutlar repo kökünde çalıştırılır. Sunucu: `$env:DB_PATH="$PWD\.audit_tmp\data\platform.db"; masterenv\Scripts\python.exe -m uvicorn app:app --app-dir master --port 8099`.

| Kod | Bulgu | Yeniden üretme | Durum |
|---|---|---|---|
| F201 | 378 Python statik analiz bulgusu (kapsamsız except, karmaşık/uzun fonksiyon, dinamik SQL, alt süreç) | `masterenv\Scripts\python.exe -m ruff check master --isolated --select C901,PLR0912,PLR0915,PLR0913,BLE001,S110,S608,S603,S607` | Açık |
| F202 | 157 arayüz kaynak bulgusu (innerHTML, hata yolu olmayan fetch, uzun fonksiyon, odak halkası) | `masterenv\Scripts\python.exe scripts/audit/scan_js.py out.json` | Açık |
| F203 | 332 HTTP bulgusu: 188 route'un 200 yanıtında şema yok, 138'inde açıklama yok, eksik güvenlik başlıkları, hız sınırı yok | `masterenv\Scripts\python.exe scripts/audit/probe_http.py out.json` | Açık |
| F204 | 93 yetenek için kodda ve OpenAPI'de hiç iz yok | `masterenv\Scripts\python.exe scripts/audit/features.py out.json` | Açık |
| F205 | 13 gerçek sohbet isteği başarısız | `masterenv\Scripts\python.exe scripts/audit/battery.py` | Açık |
| F206 | 7 tarayıcı bulgusu (aynı başlık, çoklu h1, 341 etiketsiz kontrol, küçük hedefler) | Tarayıcıda 8 rota gezilir (bkz. kanit/ui.md) | Açık |
| F208 | 49 Python kaynak bulgusu (gömülü uzun prompt/metin, 600 satırı aşan modül) | `masterenv\Scripts\python.exe scripts/audit/scan_py.py out.json` | Açık |
| F207 | 15 sistem bulgusu (OCR yok, web araması yok, IDOR, frontend araç zinciri yok, plan v2 iddiaları) | Her maddenin 'Sorun' satırındaki komut/endpoint | Açık |

## 3. Dürüstlük notları

- **F204** "bulunamadı", kod okunarak değil desen aranarak belirlendi. Desen 0 eşleşme verdiyse özellik yoktur; ancak özellik farklı adla yazılmışsa yanlış negatif olabilir. Her maddenin Kabul satırı bu yüzden *davranışı* sınayan testi ister.
- **F201/F202** araç bulgularıdır: gerçek ve konumludur, ama her biri hata değildir (ör. bir `innerHTML` sabit metin olabilir). Kabul satırı bunu ayırt etmek için inceleme ister.
- Yoklama izole sunucuda yapıldı; üretim verisine dokunulmadı.
- Sayı, kalite değil kapsamdır. Öncelik: P0 ve P1 maddeleri önce.

## 4. Kurallar

1. `python scripts/plan_tool.py --plan-dir docs/plan-v3 check` yapıyı doğrular.
2. Plan dosyaları yalnız "Durum: açık" der; ilerleme `PROGRESS.json`'dadır.
3. `done` için testin madde kimliğini taşıması, commit ve kabul ölçütünün ölçülmesi gerekir.
4. Düzeltme sonrası ilgili yoklama betiği yeniden çalıştırılır; bulgu kaybolmalıdır.
