# Sprint 2 — Sprint Review

| | |
|---|---|
| Sprint | 2 (22 Ekim – 4 Kasım 2026) |
| Tarih | 4 Kasım 2026 |
| Katılımcılar | İshak Bostan, Zeynep Duru Küçük, Furkan Kaan Özbeyli, Semih Sarıca, Işıl Karademir, Berfin Yiğit |
| Scrum Master | Zeynep Duru Küçük |
| Toplantı yeri | Online (Discord) |

## Sprint Hedefi Değerlendirmesi

**Hedef:** Platformun yetenek ölçümü ve ajan seçim katmanını teslim etmek — master, kayıtlı ajanları puanlayabilmeli ve her görevi en uygun ajana atayabilmeli.

**Sonuç: Hedef tam olarak karşılandı.** 7 backlog öğesinin tamamı Definition of Done'ı geçti.

## Tamamlanan Backlog Öğeleri

| ID | Öğe | Durum |
|---|---|---|
| PB-20 | Ajan durum izleme (heartbeat) | ✅ Tamamlandı |
| PB-21 | Model başına yetenek profili — benchmark soruları | ✅ Tamamlandı |
| PB-22 | Yetenek değerlendirme koşucusu | ✅ Tamamlandı |
| PB-23 | Görev tipi ağırlık vektörleri | ✅ Tamamlandı |
| PB-24 | Ajan seçim algoritması | ✅ Tamamlandı |
| PB-25 | Görev dağıtımı (kuyruk, çekme, kiralama) | ✅ Tamamlandı |
| PB-26 | Ajan durum arayüzü | ✅ Tamamlandı |

Tamamlanmayan öğe: **Yok.**

## Yapılan Demo

Demo, `localhost:8000` üzerinde çalışan platform ile gerçekleştirildi.

### Demo Senaryosu 1 — Ajan Kaydı ve Heartbeat
- Farklı modelli (qwen3.5:4b, phi4-mini, llama3.2:3b) 3 ajan aynı anda başlatıldı.
- Master'ın Ajanlar sekmesinde canlı durum rozetleri (Çevrimiçi / Meşgul / Çevrimdışı) gözlemlendi.
- Bir ajan kapatıldı; 30 saniye içinde "Çevrimdışı" rozeti göründü.

### Demo Senaryosu 2 — Yetenek Değerlendirmesi
- "Tümünü Değerlendir" butonu tetiklendi.
- Master, her online ajana 25 benchmark görevi gönderdi.
- Ajanlar sonuçları gönderince puan çubukları (0–100, 5 boyut) güncellendi.
- Yüksek bağlam penceresi olan ajan `context` boyutunda öne çıktı.

### Demo Senaryosu 3 — Akıllı Görev Atama
- Farklı tiplerde görevler (backend, frontend, testing) manuel olarak oluşturuldu.
- Seçim algoritmasının her görev tipi için farklı ajanı seçtiği gösterildi.
- Atama gerekçesi (hangi ajan, hangi skor, neden) veritabanında kaydedildi ve API üzerinden okundu.

## Ürün Sahibi / Hoca Geri Bildirimleri

- Seçim gerekçesinin API yanıtında görünür olması olumlu bulundu.
- Sprint 3 için gerçek görev yürütme (ajan kodu üretmeli) önceliklendirildi.
- Benchmark sorularının daha gerçekçi proje görevlerini yansıtması için genişletilebileceği belirtildi.

## Backlog Güncellemeleri

Sprint 3 kapsamı gözden geçirildi ve nihai hale getirildi (bkz. [sprint-3/sprint-backlog.md](../sprint-3/sprint-backlog.md)):
- PB-30–PB-37 sıralaması onaylandı.
- LiteLLM gateway'inin kaldırılması (PB-37) Sprint 3'e eklendi.

## Metrikler

| Metrik | Değer |
|---|---|
| Planlanan / Tamamlanan öğe | 7 / 7 |
| Tahmini / Gerçekleşen süre | 104 h / 104 h |
| Toplam birim testi | 112 |
| Yeni dosyalar | 4 (benchmarks.py, task\_weights.py, selection.py, tasks\_api.py) |
| Benchmark sorusu sayısı | 25 |
