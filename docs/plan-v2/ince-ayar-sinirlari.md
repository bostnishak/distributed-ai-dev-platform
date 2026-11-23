# İnce Ayarın Sınırları ve ML İlkeleri (ML-14)

**"Eğitirsek halüsinasyon biter" varsayımı yanlıştır.** Bu platformda makine öğrenmesi ve ince ayar yalnızca ölçülebilir kazanç kanıtlandığında kullanılır:

| Sorun Alanı | İnce Ayar / ML İşe Yarar mı? | Asıl Çözüm |
|---|---|---|
| Olgusal doğruluk ve güncel olaylar | **Hayır** (küçük modelde bilgi ezberletme güvenilmezdir) | `RAG-01..23` (belge + web + atıf) ve `HAL-15` kaçınma |
| Matematik, tablo toplamı, tarih | **Hayır** | Deterministik araçlar (`calculator`, tablo sorgusu, sistem saati) |
| Yanıt biçimi, kaçınma tonu, araç çağrısı | **Evet** (DPO / QLoRA adaptörleri ile iyileşir) | `MODE-01..08` + onaylı `ML-07` DPO + `ML-08` eval kapılı adaptör |
| Niyet sınıflandırma ve güven kalibrasyonu | **Evet** (yüksek kazanç, düşük maliyet) | `ML-01` gömme sınıflandırıcı + `ML-03` isotonic kalibratör |

**Zorunlu Kapılar:**
- Hiçbir adaptör, reranker veya gömme modeli altın eval setinde (`eval/golden/`) taban skoru geçmeden yayına alınmaz (`check_ml_promotion_gate`).
- Altın eval sorularıyla örtüşen hiçbir kayıt DPO eğitim kümesine alınmaz (`build_dpo_dataset` sızıntı kontrolü).
- Kanarya trafiğinde (%10) hata oranı artan her model otomatik geri alınır (`evaluate_canary_health`).
