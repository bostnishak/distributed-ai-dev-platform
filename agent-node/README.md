# Ajan Kurulum Rehberi (ekip üyeleri için)

Platformda her ekip üyesinin bilgisayarında bir **ajan** çalışır. Ajan, size atanan açık kaynak modeli (Ollama ile) bilgisayarınızda çalıştırır ve **master**'a (İshak'ın bilgisayarı) kendini kaydeder. Master, gereksinim dokümanlarını görevlere böler. İlerleyen sprintlerde bu görevleri ajanların yeteneklerine göre dağıtacak.

Bu rehber adım adım yazıldı. Takıldığınız yerde İshak'a yazın.

## Kim hangi ajanı kuruyor?

| Kim | Ajan kimliği | Model | İndirme boyutu (yaklaşık) |
|---|---|---|---|
| İshak Bostan | `uye1` | `qwen3.5:4b` (Qwen3.5 4B, Alibaba) | 3,4 GB *(master bilgisayarında, Docker ile çalışıyor)* |
| Zeynep Duru Küçük | `uye2` | `phi4-mini` (Phi-4-mini, Microsoft) | 2,5 GB |
| Furkan Kaan Özbeyli | `uye3` | `llama3.2:3b` (Llama 3.2 3B, Meta) | 2,0 GB |
| Semih Sarıca | `uye4` | `gemma4:e4b` (Gemma 4 E4B, Google) | 9,6 GB |
| Işıl Karademir | `uye5` | `qwen2.5-coder:7b` (Qwen2.5-Coder 7B, Alibaba) | 4,7 GB |
| Berfin Yiğit | `uye6` | `qwen3:1.7b` (Qwen3 1.7B, Alibaba) | 1,4 GB |

Boyutlar, master bilgisayarında `ollama list` ile ölçüldü (2026-09-27).

## Başlamadan önce İshak'tan özelden alacaklarınız

Bu üç bilgi **gizlidir**. WhatsApp veya DM gibi özel bir kanaldan alın. Repoya, Trello'ya ya da ortak bir gruba asla yazmayın.

1. **Tailscale anahtarı** (`tskey-auth-...` ile başlar). Bilgisayarınızı ekibin özel ağına bağlar.
2. **AGENT_TOKEN**. Ajanınızın master'a kaydolmasını sağlayan ortak parola.
3. **Master adresi**, örneğin `http://ishak-pc:8000`.

## Neden Tailscale?

Herkes kendi evinden çalıştığı için bilgisayarlarımız aynı ağda değil. Tailscale, ekip bilgisayarlarını birbirine bağlayan ücretsiz bir özel ağ kurar:

- Trafik uçtan uca şifrelidir (WireGuard).
- Tailscale şirketi yalnızca bağlantı bilgisini (cihaz adı, IP) görür, verilerimizi göremez.
- Ajan yalnızca master'a bağlanır, master ajana bağlanmaz. Bu yüzden sizin bilgisayarınızda port açmanız veya güvenlik duvarı ayarı yapmanız gerekmez.
- Ollama yalnızca kendi bilgisayarınızdan erişilebilir kalır.

## Kurulum

### 1. Repoyu indirin

Git biliyorsanız klonlayın. Git ile ilgili adımlar için [CONTRIBUTING.md](../CONTRIBUTING.md)'ye bakabilirsiniz.

```bash
git clone https://github.com/bostnishak/distributed-ai-dev-platform.git
cd distributed-ai-dev-platform
```

Git kullanmıyorsanız GitHub sayfasında **Code → Download ZIP** ile indirip bir klasöre açın.

### 2. Kurulum scriptini çalıştırın

Repo klasöründe bir terminal açın ve **kendi ajan kimliğinizle** çalıştırın.

**Windows** (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File agent-node\setup.ps1 -AgentId uye2
```

**macOS / Linux**:

```bash
chmod +x agent-node/setup.sh agent-node/start-agent.sh
./agent-node/setup.sh uye2
```

Script sırasıyla şunları yapar:

1. Ollama'yı kurar (kurulu değilse). Ollama'nın yalnızca bu bilgisayarı dinlemesini sağlar; eski kurulum scripti onu ağa açmışsa bu ayarı kaldırır.
2. Size atanan modeli indirir ve RAM'inizin yetip yetmediğini kontrol eder.
3. Modele kısa bir test sorusu sorar.
4. Tailscale'i kurar ve sizden **Tailscale anahtarını** ister.
5. Python'u (yoksa) ve ajanın paketlerini kurar.
6. **Master adresini** ve **AGENT_TOKEN**'ı sorup `agent/.env` dosyasına kaydeder. Bu dosya gizlidir ve git'e eklenmez.
7. Master'a ulaşılabildiğini kontrol eder.

Model indirme, internet hızınıza göre birkaç dakika sürebilir.

### 3. Ajanı başlatın

**Windows**:

```powershell
powershell -ExecutionPolicy Bypass -File agent-node\start-agent.ps1
```

**macOS / Linux**:

```bash
./agent-node/start-agent.sh
```

Şu satırı görüyorsanız ajanınız kaydolmuştur:

```
Master'a kaydolundu: uye2 (phi4-mini, bağlam 131072 token, ...)
```

Platform arayüzündeki **Ajanlar** sekmesinde adınız "Üyenin bilgisayarı" etiketiyle görünür. Pencere açık kaldığı sürece ajan çalışır. Görev yürütme Sprint 3'te eklenecek; şimdilik ajan kaydolup bekliyor.

### 4. İshak'a haber verin

Master bilgisayarında sizin modelinizin geçici bir kopyası da "staging" olarak çalışıyor. Sizin ajanınız bağlanınca İshak şu komutla kopyayı durdurur, böylece iki kopya aynı kimlikle kaydolmaz:

```bash
docker compose stop agent-uye2
```

## Sık karşılaşılan durumlar

| Mesaj | Ne yapmalı? |
|---|---|
| `Master AGENT_TOKEN'ı reddetti` | `agent/.env` içindeki `AGENT_TOKEN`'ı İshak'ın gönderdiğiyle karşılaştırın ve kurulumu tekrar çalıştırın. |
| `Master'a kayıt başarısız (ConnectError)` | Master kapalı olabilir ya da Tailscale bağlı değildir. Ajan kendisi tekrar dener. Tailscale uygulamasının açık olduğunu kontrol edin. |
| `... modeli bu bilgisayarda yüklü değil` | `ollama pull <model>` çalıştırın ya da kurulumu tekrar çalıştırın. |
| `RAM bu model için az görünüyor` | Model çalışır ama yavaş olabilir. Ekiple konuşun; Sprint Planning'de model değişikliği kararlaştırılabilir. |
| PowerShell "script çalıştırma devre dışı" diyor | Komutu yukarıdaki gibi `powershell -ExecutionPolicy Bypass -File ...` ile çalıştırın. |

**Not:** `setup.sh`, ekibin test bilgisayarı Windows olduğu için macOS/Linux'ta henüz denenmedi. İlk deneyen arkadaş sonucu ekiple paylaşsın.

## Master bilgisayarı (yalnızca İshak)

Ana sistem Docker ile çalışır. Master, LiteLLM gateway ve İshak'ın ajanı `uye1` ayağa kalkar:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-docker.ps1
docker compose up -d --build
```

- Diğer beş üyenin modellerini de geçici olarak bu bilgisayarda çalıştırmak için (staging): `docker compose --profile staging up -d --build`
- `scripts\start-docker.ps1`, Docker Desktop'ın bu bilgisayarda düzgün kapanmadığında yaşadığı soket hatasını ("The file cannot be accessed by the system") önleyerek Docker'ı başlatır.
- Tailscale'i bu bilgisayara da kurun ve kendi hesabınızla giriş yapın. Arkadaşlarınız için yönetim panelinden **Settings → Keys → Generate auth key** ile tekrar kullanılabilir (reusable) bir anahtar oluşturun.
- Master adresi, Tailscale'deki bilgisayar adınızdır: `http://<bilgisayar-adı>:8000`.
- Arkadaşlarınız bağlanamazsa Windows Güvenlik Duvarı 8000 portunu engelliyor olabilir. Bu durumda ekiple birlikte bakın.
