# CNC Teknik Çizim Balonlama — Model Özelleştirme ve Eğitim Kiti

Bu klasör, şirketteki CNC parça işleme (talaşlı imalat / kalite kontrol / AS9102 FAI) süreçleri için yapay zekâyı uzmanlaştırma araçlarını içerir.

## 1. Hızlı Kurulum: Ollama Özel Model (`cnc-ballooner`)
`qwen3.5:9b` üzerine ISO 2768-mK, ISO 286 geçmeler ve GD&T kurallarını gömen özel Ollama modelini oluşturun:

```powershell
ollama create cnc-ballooner -f training/cnc_ballooning/Modelfile.cnc-ballooner
```

Platform otomatik olarak `cnc-ballooner` modelini algılayıp teknik çizim görsellerinde öncelikli olarak kullanır.

## 2. Sentetik CNC Eğitim Veri Seti Üretimi
Farklı çap, geçme (`H7`, `g6`, `h6`), diş (`M6..M12`), yüzey pürüzlülüğü (`Ra`) ve GD&T sembolleriyle etiketli veri seti üretmek için:

```powershell
master\venv\Scripts\python.exe training/cnc_ballooning/generate_synthetic_dataset.py --count 100
```

## 3. Şirket Verileriyle Gerçek QLoRA Fine-Tuning
Şirketin gerçek teknik çizimlerini (PDF/PNG + düzeltilmiş balon JSON çıktıları) `dataset.jsonl` dosyasına ekleyip GPU üzerinde QLoRA eğitimi başlatabilirsiniz:

```powershell
python training/cnc_ballooning/finetune_lora.py --dataset training/cnc_ballooning/data/dataset.jsonl --epochs 3
```
