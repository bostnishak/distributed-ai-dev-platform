# v1-v4 şartnameleri: özet durum (27.11.2026)

Kalan alt eksikler: [eksik-listesi.md](eksik-listesi.md).

Madde madde liste: [sartname-madde-listesi.md](sartname-madde-listesi.md). Komutlar: [komutlar.md](komutlar.md).
Makine: Windows 11, RTX 4060 Laptop 8 GB, 32 GB RAM. Ücretli servis ve anahtar kullanılmaz.

| Durum | Sayı | Anlamı |
|---|---|---|
| canlı | 84 | gerçek modellerle çalışan sistemde denendi ve geçti |
| test | 64 | yalnız otomatik testle doğrulandı |
| kısmi / yok | 0 | |
| dışarıda | 8 | kullanıcı onayıyla kapsam dışı |
| teknik engel | 3 | bu araçlarla yapılamıyor |
| **toplam** | **159** | |

## Yapılamayanlar

**Teknik engel (Ollama bu denetimi vermiyor):**
- Logprob/entropi ile büyük modele yükseltme
- Radix KV önbellek havuzu
- GBNF/XGrammar sözdizimi maskeleri

**Kapsam dışı:**
- Çoklu bilgisayar (LAN) çıkarım ağı
- Spekülatif çözme
- Yerel model eğitimi (LoRA/DPO/GRPO), PRM eğitimi, çoklu LoRA birleştirme, bilgi damıtma (yalnız veri ve betik hazırlanır)
- gVisor/Firecracker (Windows'ta yok)
- Ücretli buluta yükseltme (istenmedi; hiçbir yere veri gönderilmez)

## Bilinmesi gerekenler

- "test" durumundaki 64 madde canlı modelle ayrıca denenmedi.
- 7 boşluk testi `scripts/gap_suite.py` ile canlı çalışır; yerel modeller her koşuda aynı yanıtı vermez.
- Soğuk açılış 3,2 sn ve boşta 214 MB ölçüldü.
- Türkçe ses verisinin lisansı (CC BY-NC-SA 4.0) ticari kullanıma kapalıdır.
- Küçük modeller hata yapabilir; üretilen kodu, sayıları ve belgeleri kullanmadan önce gözden geçirin.
