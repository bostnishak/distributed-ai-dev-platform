# Plan v3 — kanıt kapanışı ve derinleştirme planı

**566 madde**, 12 alan. Plan v2'nin (376 madde) "tamam" dediği işlerin **gerçekten** kabul ölçütünü karşılayıp karşılamadığını sınamak, karşılamayanları kapatmak ve yeni zaaflara (güvenlik, ölçüm, arayüz, alan uzmanlığı, operasyon) girmek için yazıldı.

## 1. Neden v3

Plan v2'nin 376 maddesi `PROGRESS.json`'da `done`. Bu oturumda maddeler tek tek kabul ölçütüne karşı sınandı ve şu görüldü: birçok madde "kod var" anlamında tamamdı, ölçütü ("saldırı başarısı < %5", "6 ajanla 3x hızlanma", `safe_archive` modülü, 4 rol...) karşılamıyordu. v3 bu farkı kapatır. Kural: **bir madde kabul ölçütü ölçülmeden `done` olmaz**; ölçülemiyorsa `partial` ve `gap` yazılır.

Madde etiketi: `[DOĞRULANDI: F#]` aşağıdaki tabloda yeniden üretilebilen bir bulguya dayanır; `[ÖNERİ]` henüz ölçülmemiş bir tasarım kararıdır. Dürüst sınır: ÖNERİ maddeleri kanıtlanmış zaaf değil, aday iyileştirmedir.

## 2. Denetim bulguları (yeniden üretilebilir)

Komutlar repo kökünde, `master\venv\Scripts\python.exe` ile çalıştırılır.

| Kod | Bulgu | Yeniden üretme | Durum |
|---|---|---|---|
| F101 | Plan v2'de 150 maddenin kanıt testinde madde kimliği geçmiyor; kimlik taramasında 116 madde hiçbir test dosyasında anılmıyor | `python scripts/scan_ids.py` (bkz. `KANIT_DENETIMI.md` v2) | Açık |
| F102 | SEC-09 enjeksiyon dedektörü 40 saldırıdan 5'ini yakalıyordu (%87 saldırı başarısı; hedef < %5). Ağırlıklı dedektör 40/40, 0/40 yanlış alarm verdi ama kendi kaçırdıklarına bakılarak ayarlandı: iyimser | `python eval/security/make_set.py` ve `eval/security/injection.jsonl` | Kısmen düzeltildi, dışlanmış küme gerekli |
| F103 | `safe_archive` modülü ve `auth/policy.py` yoktu; yalnız admin/member rolü vardı | `Test-Path master/safe_archive.py`, `master/auth/policy.py` | Modüller eklendi, tam bağlama açık |
| F104 | `eval/security` ve `eval/latency` dizinleri yoktu | `Test-Path eval/security` | `eval/security` eklendi, `latency` açık |
| F105 | `pytest.ini` yalnız `security` işaretini tanımlıyor (OPS-09 altı işaret ister) | `pytest.ini` | Açık |
| F106 | Monaco yerel paketi yok (`master/static/vendor` yok) | `Test-Path master/static/vendor` | Açık |
| F107 | `templates/` proje şablon deposu yok (IDE-17) | `Test-Path templates` | Açık |
| F108 | Birçok rota `user_id` değerini sorgu parametresinden alıyor, oturumdan değil (SEC-03) | `grep -rn "user_id: str = \"default\"" master` | Açık |
| F109 | `GET /api/orchestrator/artifacts/{id}` ve `POST /api/memory/compact/{id}` sahip denetimi yapmıyor | `master/tests/test_ux_panels_backend.py` ile deneme | Açık |
| F110 | rag.db, hallucination.db, ml_ops.db, ux_shares.db ortak bağlantı ve sahiplik kaydı dışında | `grep -rn "sqlite3.connect" master` | Açık |
| F111 | Altın kümedeki cevaplanamaz örnekler 3 kalıbın tekrarı; `detect_false_premise` 4 varlıklı | `eval/golden`, `master/hallucination/verifier.py` | Açık |
| F112 | İnsan etiketli veri yok: ECE, Cohen κ, NLI makro-F1 ölçülemiyor | `docs/plan-v2/EVAL_OLCUMU.md` | Açık |
| F113 | Hız sınırı yalnız giriş denemesinde; pahalı rotalarda token-bucket yok | `master/auth/service.py` | `ratelimit.py` eklendi, orta katman açık |

## 3. Alanlar

| Alan | Konu | Dosya |
|---|---|---|
| AUD | Plan v2 kanıt kapanışı | 01 |
| TST | Test, kalite kapıları, süreç | 01 |
| GVN | Güvenlik ve gizlilik | 02 |
| HLC | Halüsinasyon ölçümü | 03 |
| RGX | RAG ve arama | 03 |
| MDL | Model, gateway, niyet, ML | 04 |
| ALN | Alan uzmanlıkları | 04 |
| ARY | Arayüz ve erişilebilirlik | 05 |
| FAB | Yazılım fabrikası, IDE, oyun | 06 |
| BEL | Araştırma, sunum, belge, veri, medya | 07 |
| DGT | Dağıtık ajanlar ve operasyon | 08 |
| VRI | Veri katmanı | 08 |

## 4. Kurallar

1. `python scripts/plan_tool.py check --plan-dir docs/plan-v3` yapıyı doğrular; `status --plan-dir docs/plan-v3` ilerleme dosyasını yazar.
2. Plan dosyaları yalnız "Durum: açık" der; ilerleme `PROGRESS.json`'dadır.
3. `done` için: testi madde kimliğini taşır, commit vardır, **ve** kabul ölçütü ölçülmüştür. Sayısal hedefler `measured` alanı olmadan ölçülmüş sayılmaz.
4. Kabul ölçütü karşılanmıyorsa durum `partial` ve `gap` açıklaması yazılır; `done` denmez.
5. Etiketli veri, dışlanmış küme ve gerçek donanım (Docker, GPU, Windows temiz kurulum) isteyen maddeler bu kaynaklar olmadan kapatılamaz; sahte veriyle kapatmak yasaktır.

## 5. "Hiçbir eksik yok" iddiası hakkında

Bu planın amacı eksiksizliği *kanıtlamak* değil, eksikleri görünür ve sınanabilir kılmaktır. Hiçbir yazılım için "eksiksiz" doğrulanamaz; doğrulanabilen şey "şu ölçütler bu veriyle ölçüldü ve geçti"dir. v3 her madde için o ölçütü yazar. Bittiğinde elde edilecek şey: her iddianın yanında ölçüm, veri kümesi ve komut.
