# v1-v4 şartnameleri: yapılanlar ve yapılamayanlar

Durum sözcükleri: **canlı** = gerçek modellerle çalışan sunucuda denendi ve geçti; **test** = yalnız otomatik testle
doğrulandı; **kısmi** = bir bölümü var; **yok** = yapılmadı. Makine: RTX 4060 Laptop 8 GB, 31 GB RAM.

## Yapılanlar

| Konu | Durum | Nerede |
|---|---|---|
| Tek dosya web uygulaması, renk ve etiket uyumu | canlı | `workspace_batches.py`, `spec_contract.py` |
| Sohbetten revizyon; basit renk/yazı değişikliği modelsiz | canlı | `revise_chat.py`, `tier0_edit.py` |
| Akış şeması (listelenen her adım zorunlu), PDF, görsel | canlı | `flowchart_studio.py` |
| FastAPI + SQLite küçük API, gerçek isteklerle sınanmış | canlı (3 başarısız denemeden sonra) | `workspace_batches.fixed_plan` |
| Uzun belgede ilgili bölümü satır numarasıyla seçme | canlı | `long_doc.py` |
| Belge içindeki talimatları ayırma | canlı | `untrusted.py` |
| İmzalı köken kaydı ve bağımlılık listesi | canlı | `provenance.py` |
| Aşama süreleri, başarı oranı, yörünge kaydı | canlı | `run_trace.py`, `/api/studio/runs/summary` |
| Tarayıcı kapısı (ekleme, filtre, yer tutucu), onarım döngüsü | test + canlı üretimde | `workspace_smoke.py` |
| Gerçek tarayıcıda taşma, kontrast, çakışma denetimi | test (Edge) | `visual_audit.py` |
| Güvenlik ve gizli anahtar taraması | test | `security_scan.py` |
| Nokta atışı yama, Intake ve Mimar ajanları, API istek testi | test | `patch_edit.py`, `agent_contracts.py` |
| Orantılılık freni (`@fast`, `@deep`) | test | `complexity_governor.py` |
| Şablon tasarım uyarıları | test | `design_slop.py` |
| IDE hata köprüsü | test (Node); gerçek tarayıcıda denenmedi | `ide_error_bridge.js` |
| Donanım doktoru, başlatma, GPU belleği boşaltma | `doctor` canlı; `up`, `unload` denenmedi | `scripts/ai_os.py` |

## İndirmelerden sonra eklenenler

| Konu | Durum | Nerede |
|---|---|---|
| Excel, Word, sunum dosyalarını LibreOffice ile açıp yeniden hesaplama | canlı (Excel) | `office_verify.py` |
| Sayısal sorularda Z3 doğrulaması | canlı | `z3_math.py` |
| CSV sorularında DuckDB ile gerçek SQL | canlı | `data_lab.py` |
| Görsel modelle ekran görüntüsü eleştirisi (`@derin`) | canlı; bozuk sayfada kusurun bir kısmını kaçırdı | `vlm_critique.py` |
| CPU'da gömme, tek model GPU kilidi | canlı | `gateway/local_gpu.py` |
| Zamanlı bellek, doğrulanmış beceri kütüphanesi, yayın istatistikleri | test | `memory_timeline.py`, `skill_library.py`, `eval_stats.py` |
| Windows iş nesnesi ve WASM izolasyonu (henüz hatta bağlı değil) | test | `isolation.py` |
| Bulut eğitim paketi ve GGUF içe aktarma | dışa aktarma çalıştı; içe aktarma gerçek GGUF ile denenmedi | `training_pack.py` |

Güncel ve madde madde liste: [sartname-madde-listesi.md](sartname-madde-listesi.md). Aşağıdaki tablolar ilk turun özetidir.

## Bu makinede yapılmayacaklar (kullanıcı onayladı)

Çoklu makine dağıtımı; 32B-70B modeller ve spekülatif çözme; yerel model eğitimi ve GRPO; gVisor ve Firecracker.

## Sınırlar

- Yerel 7-9B modeller aynı istekte farklı sonuç üretir; bir senaryonun bir kez geçmesi her zaman geçeceğini göstermez.
- Tek bir proje üretimi 3-7 dakika sürüyor; en uzun aşama çalıştırma testi ve onarım turlarıdır.

## Yeniden doğrulama

```powershell
python scripts/e2e_stress.py
```

```powershell
python scripts/e2e_features.py
```
