# Prompt Deneyleri ve A/B Kanıt Kaydı (HAL-29)

İlke: **Ölçüm olmadan halüsinasyon önleyici prompt kuralı eklenmez.** Her şablon değişikliği `eval/run.py --suite golden` koşusu ile taban yapılandırmaya karşı A/B testinden geçirilir ve yalnız tekrarlanabilir kazanç gösteren değişiklikler korunur.

| Tarih | Şablon ve Sürüm | Değişiklik Özeti | Taban Skor | Aday Skor | Karar | Rapor |
|---|---|---|---|---|---|---|
| 2026-11-23 | `base_identity@v1.0` + `mode_contracts@v1.0` | Katmanlı sistem promptu + selamlamada hafıza izolasyonu (`GW-17`) + programatik sözleşme (`MODE-01..08`) | 0.7200 | 0.9600+ | Kabul (eval kapısı geçti) | `eval/reports/eval_baseline.json` |
| 2026-11-23 | `qwen3.5:4b` canlı GPU + `HAL-08/15/16` doğrulama katmanı | 7 kategorili tabakalı canlı GPU kıyaslaması (ham `qwen3.5:4b` vs doğrulama korumalı platform) | 0.6667 | 0.9524 | Kabul (+0.2857 gerçek GPU kazancı) | `eval/reports/eval_live_guarded_qwen35_4b.json` |
