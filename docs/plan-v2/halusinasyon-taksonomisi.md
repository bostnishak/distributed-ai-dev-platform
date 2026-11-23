# Halüsinasyon Taksonomisi (HAL-01)

Bu belge platform genelinde kullanılan 8 resmi halüsinasyon sınıfını, otomatik algılama yöntemlerini ve sorumlu mimari katmanları tanımlar. Tüm `eval/golden/*.jsonl` ve `eval/reports/*.json` çıktıları bu taksonomi anahtarlarını kullanır.

| Sınıf Kodu | Türkçe Adı | Tanım ve Örnek | Otomatik Algılama | Sorumlu Hat |
|---|---|---|---|---|
| `fabricated_fact` | Uydurma olgu | Kaynakta veya gerçekte olmayan olgusal beyan (ör. yanlış kuruluş tarihi, sahte biyografi) | `HAL-07` NLI iddia-kaynak kontrolü + `HAL-15` kaçınma kapısı | `rag` + `hallucination` |
| `fabricated_citation` | Uydurma kaynak/atıf | Var olmayan `[S9]` etiketi, uydurma DOI veya yanlış sayfa/URL atfı | `RAG-11` atıf çözümleyici + `RAG-21` Crossref DOI doğrulayıcı | `rag` |
| `numeric_error` | Yanlış sayı/hesap | Kaynakla uyuşmayan sayı, yanlış aritmetik veya toplamı tutmayan tablo satırı | `HAL-09` sayısal köken ve tablo toplam denetimi + `ORC-08` hesap aracı | `hallucination` + `orchestrator` |
| `fabricated_code_api` | Uydurma kod API'si | Var olmayan Python/npm paketi (slopsquatting) veya olmayan işlev/parametre çağrısı | `HAL-12` sandbox yürütme + `HAL-13` AST import/imza denetimi | `hallucination` + `sandbox` |
| `out_of_context` | Bağlam dışı bilgi | "Yalnızca bu belgeye göre" istendiğinde veya ilgisiz parçayla dış bilgi eklenmesi | `RAG-08` mutlak alaka eşiği + `HAL-22` sıkı temellendirme modu | `rag` + `hallucination` |
| `instruction_violation` | Talimat ihlali | "Sadece kod", "kısa tut", "tablo ver", "emojisiz" gibi açık sözleşme kurallarının çiğnenmesi | `MODE-01..08` programatik sözleşme + `HAL-20` doğrulayıcı | `orchestrator` |
| `self_contradiction` | Kendi kendine çelişki | Aynı sohbette önceki doğrulanmış beyanla çelişen yeni yanıt üretilmesi | `HAL-21` sohbet içi NLI tutarlılık denetimi | `hallucination` |
| `overconfidence` | Aşırı özgüven | Cevaplanamayan veya kaynaksız soruda kaçınmak yerine kesin dille tahminde bulunma | `HAL-14` kalibre güven skoru + `ML-03` isotonic kalibratör | `hallucination` + `ml_ops` |
