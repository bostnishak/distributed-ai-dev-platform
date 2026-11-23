# Model Lisansları, Gizlilik ve Etik Beyanı (PROC-08)

Bu belge platformun model kayıt defterindeki (`master/gateway/registry.py`, `GW-03`) yerel açık modellerin lisans koşullarını, KVKK / veri gizliliği politikasını ve ince ayar / damıtma (`ML-13`) etik sınırlarını tanımlar.

## 1. Model Lisans Matrisi

| Model | Sağlayıcı | Lisans | Akademik Kullanım | Ticari Kullanım | Kısıtlar ve Notlar |
|---|---|---|---|---|---|
| `qwen3.5:4b` | Alibaba (Qwen) | Apache-2.0 | İzinli | İzinli | Telif/NOTICE koruması gerekir; açık ağırlıklı yerel çıkarım. |
| `qwen2.5-coder:7b` | Alibaba (Qwen) | Apache-2.0 | İzinli | İzinli | Telif/NOTICE koruması gerekir; kod üretimi için optimize. |
| `qwen3:1.7b` | Alibaba (Qwen) | Apache-2.0 | İzinli | İzinli | Hafif yönlendirme/sınıflandırma için uygun. |
| `phi4-mini` | Microsoft | MIT | İzinli | İzinli | Telif bildirimi korunmalıdır. |
| `llama3.2:3b` | Meta | Llama 3.2 Community License | İzinli | Koşullu | "Built with Llama" atfı ve 700M MAU üst sınırı geçerlidir; çıktıların başka temel model eğitiminde kullanımı kısıtlıdır. |
| `gemma4:e4b` | Google | Gemma Terms of Use | İzinli | Koşullu | Yasaklı kullanım politikasına (Prohibited Use Policy) tabidir; dağıtım sırasında lisans bildirimi eklenmelidir. |
| `bge-m3` | BAAI | MIT | İzinli | İzinli | Çok dilli (Türkçe/İngilizce) gömme modeli. |

## 2. Veri Gizliliği ve KVKK Uyumu

- **Yerel-önce işleme:** Varsayılan yapılandırmada (`CLOUD_PROVIDERS_ENABLED=false`) hiçbir sohbet, belge, kod parçası veya kullanıcı hafızası harici bulut API'lerine gönderilmez (`SEC-11`).
- **Veri minimizasyonu ve unutulma hakkı:** Kullanıcılar verilerini dışa aktarabilir (`DAT-08`), saklama süresi belirleyebilir ve tam silme (`DAT-06`, `VACUUM` + blob temizliği) talep edebilir.
- **Günlük maskeleme:** Yapılandırılmış günlüklerde PII (e-posta, TC kimlik, telefon, token) otomatik maskelenir (`SEC-23`, `OPS-01`).
- **Şifreleme:** Harici bağlantı anahtarları Fernet ile şifrelenir (`SEC-11`) ve yedekler parola ile şifrelenip gizli anahtarları hariç tutar (`SEC-12`).

## 3. Etik Sınırlar ve Damıtma/İnce Ayar Politikası

- **Yüksek riskli alanlar:** Platform tıbbi teşhis, ilaç dozu, hukuki vekâlet veya yatırım tavsiyesi üretmez; bu istekler güvenlik sınırları gereği açık uyarı ile reddedilir veya sınırlandırılır (`HAL-19`, `DOM-04`).
- **Üretilen içerik sorumluluğu:** Tüm kod, belge ve araştırma çıktıları "yardımcı taslak" niteliğindedir; kritik üretim/mühendislik kararları insan onayına tabidir.
- **Damıtma ve ince ayar lisans denetimi (`ML-13`):** Kapalı bulut modellerinin veya kısıtlayıcı lisanslı modellerin çıktıları, lisans izin vermedikçe yerel adaptör eğitim veri setine eklenmez; yalnızca kendi lisansına uygun ve doğrulanmış veriler kullanılır.
