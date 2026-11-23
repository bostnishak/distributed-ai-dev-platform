# Halüsinasyon Mimarisi ve Güvenilirlik Sınırları (HAL-30)

Bu sistemde güvenilirlik modelin "uydurmaması" temennisiyle değil, katmanlı doğrulama mimarisiyle sağlanır:

1. **Kaynaklı Bilgi Alma (`master/rag/`):** Yapı korumalı ayrıştırma (`pymupdf4llm`), FTS5 Türkçe kök normalizasyonu, vektör ANN araması, mutlak alaka eşiği (`RAG-08`) ve `[S1]..[Sn]` atıf standardı. Gömme modeli (`bge-m3`) yoksa üretimde sessiz karma yedeğe düşülmez; bilgi bankası açıkça devre dışı bildirilir (`RAG-05`).
2. **İddia ve Araç Doğrulama (`master/hallucination/`):** Atomik iddia çıkarımı (`HAL-06`), NLI destek/çelişki denetimi (`HAL-07`), sayısal köken ve tablo toplam kontrolü (`HAL-09`), Python AST import/imza denetimi (`HAL-13`), yanıltıcı öncül tespiti (`HAL-16`) ve yüksek riskli alan korumaları (`HAL-19`).
3. **Kalibre Güven ve Kaçınma (`HAL-14`, `HAL-15`, `ML-03`):** Kaynak yoksa ve risk yüksekse veya güven düşükse sistem tahminde bulunmak yerine açıkça kaçınır.
4. **Dürüst Sınırlar:**
   - 4B-9B yerel modeller dünya bilgisinde bulut öncü modellerine ulaşamaz; olgusal doğruluk RAG ve deterministik araçlara dayanır.
   - Web araması kapalıyken (çevrimdışı mod) güncel olaylar doğrulanamaz ve yanıt açık uyarı taşır.
   - Canlı metrikler elle yazılmaz; `/api/hallucination/reliability` uç noktası en son `eval/reports/eval_*.json` raporunu doğrudan okur.
