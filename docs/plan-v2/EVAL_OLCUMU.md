# Canlı eval ölçümü (qwen3.5:4b, 70 örnek, kategori başına 10)

Komut: `python eval/run.py --suite golden --live --stratified --limit 70 [--guarded]`. Raporlar: `eval/reports/eval_live70_plain_qwen35_4b.json`, `eval/reports/eval_live70_guarded_qwen35_4b.json`. Altın küme 300 şablonlu örnekten oluşur; 70 örnekte kategori başına n=10 olduğu için her yüzde ±15 puan oynayabilir. Bu bir **ön ölçümdür**, kesin kabul kanıtı değildir.

| Kategori | Korumasız | Korumalı (HAL-08/15/16) |
|---|---|---|
| cevaplanabilir olgusal | 0,80 | 0,80 |
| atıf gerektiren | 0,00 | 1,00 |
| kod | 1,00 | 1,00 |
| yanlış öncül | 0,60 | 1,00 |
| talimata uyum | 1,00 | 1,00 |
| sayısal hesap | 1,00 | 1,00 |
| cevaplanamaz (kaçınma) | 0,70 | 0,70 |
| **genel** | **0,729** | **0,929** |

Halüsinasyon oranları: uydurma atıf %14,3 → %0; uydurma olgu %8,6 → %2,9; aşırı güven %4,3 → %4,3.

## Plan kabul ölçütleriyle karşılaştırma

| Madde | Ölçüt | Ölçülen | Sonuç |
|---|---|---|---|
| HAL-08 | desteklenmeyen iddia oranı ≥ %60 düşer | uydurma atıf %100 düştü, uydurma olgu %66 düştü | karşılandı (küçük örnek) |
| HAL-16 | yanlış öncül düzeltme ≥ %80 | %100 | karşılandı (n=10) |
| HAL-15 | cevaplanamazda doğru kaçınma ≥ %85 | %70 | **karşılanmadı**; madde açık |
| HAL-03 | iki yapılandırma yan yana, sınıf başına oran | rapor var | karşılandı |

Ölçülmemiş ölçütler (ECE, Cohen κ, NLI makro-F1, 100 yanıtlık etiketli set vb.) için insan etiketli veri bu depoda yok; bu maddeler "uygulandı, ölçülmedi" olarak değerlendirilmelidir.

## HAL-15 düzeltmesi ve yeniden ölçüm

`detect_unanswerable` (özel veri ve kesin gelecek değer soruları) eklendi ve hem eval'in korumalı yoluna hem de canlı sohbet akışına (`/api/assistant/chat/stream`, model çağrılmadan) bağlandı. Yeniden ölçüm (`eval_live70_guarded_v2_qwen35_4b.json`): genel 0,986, cevaplanamaz kategori 0,70 → 1,00, uydurma olgu %1,4, cevaplanabilir olgusal 0,90.

**Dikkat, bu sonuç şişiktir:** altın kümede cevaplanamaz kategorisi yalnızca 3 soru kalıbının tekrarından oluşur ve kural bu kalıplara uyar; yanlış öncül dedektörü de 4 varlıklı küçük bir tabloya dayanır. Gerçek genelleme için farklı biçimlerde yazılmış cevaplanamaz/yanlış öncüllü soru kümesi gerekir. Yanlış kaçınma tarafı `test_hal15_detect_unanswerable_*` testiyle (sıradan sorular reddedilmez) korunur.

## Bağımsız küme ile gerçek genelleme (`eval/heldout/abstention_heldout.jsonl`)

Altın küme 3 kalıbı tekrarladığı için kural, farklı ifadelerle yazılmış 75 soruyla ayrıca ölçüldü (cevaplanamaz 25, cevaplanabilir 30, yanlış öncül 6, doğru öncül 4; model gerekmez, kural düzeyinde).

| Sürüm | Cevaplanamaz yakalama | Gereksiz kaçınma | Yanlış öncül | Doğru öncül |
|---|---|---|---|---|
| ilk kural | 18/25 (%72) | 4/30 (%13) | 6/6 | 4/4 |
| iyileştirilmiş kural | 25/25 | 0/30 | 6/6 | 4/4 |

İyileştirme: açıklayıcı sorular ("nasıl çalışır", "farkı nedir") hiç reddedilmez; özel veri yalnız değer isteyen soruda, gelecek değer yalnız tahmin ifadesiyle birlikte tetiklenir. **Uyarı:** ilk ölçümdeki kaçırmalara bakarak ayarlandığı için ikinci satır da iyimserdir; bu küme artık "eğitim" kümesi sayılmalı, kesin genelleme için hiç görülmemiş yeni sorular gerekir. Kümeyi koruyan test: `test_hal15_hal16_rules_on_the_held_out_set`.
