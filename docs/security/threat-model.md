# Tehdit Modeli — STRIDE Analizi ve Güven Sınırları (SEC-22)

Bu belge Dağıtık YZ Yazılım Geliştirme Platformu (CM6453) için güvenlik varsayımlarını, 6 ana güven sınırını ve her sınır için STRIDE tehditleri ile somut teknik önlemleri tanımlar.

---

## Güven Sınırı 1: Tarayıcı <-> Master Web API

| STRIDE | Tehdit | Uygulanan Önlem |
|---|---|---|
| **Spoofing / CSRF** | Zararlı bir sekmenin kullanıcının tarayıcısı üzerinden `/api/studio/...` veya `/api/user/...` uç noktalarına izinsiz mutasyon göndermesi. | `SecurityHeadersAndCSRFMiddleware` (SEC-16): Cross-Origin `Origin` başlığı reddi (`403`) + `SameSite=Strict` çift gönderimli `cm6453_csrf` / `X-CSRF-Token` doğrulaması. |
| **Tampering / XSS** | Üretilen web projesi önizlemesindeki zararlı JS kodunun ana uygulamanın oturumuna veya API'lerine erişmesi. | `preview_server.py` (SEC-17): Ayrı ikinci origin (`127.0.0.1:8001`), sıfır `/api/*` route, çerez yok, `Content-Security-Policy: sandbox allow-scripts; connect-src 'none'` ve `iframe sandbox="allow-scripts allow-forms"` (`allow-same-origin` kapalı). |
| **Information Disclosure** | Üçüncü taraf kaynak yükleme veya MIME koklama ile veri sızdırma. | Sıkı yerel CSP (`default-src 'self'`, `frame-ancestors 'none'`), `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`. |

---

## Güven Sınırı 2: Master API <-> Kalıcı Depolama (SQLite, Medya, Yedekler)

| STRIDE | Tehdit | Uygulanan Önlem |
|---|---|---|
| **Information Disclosure** | Harici MCP API anahtarlarının `platform.db` içinde düz metin kalması veya yedeklerle sızması. | `secret_store.py` (SEC-11): Fernet şifreli ayrı `secrets.db`, anahtar Windows Credential Manager / `SECRET_KEY` üzerinden; `backup_manager.py` ve `export_all` gizleri hariç tutar; `rotate_master_key` desteği. |
| **Information Disclosure / Tampering** | Şifresiz yedek ZIP dosyasının çalınması veya değiştirilmiş yedeğin geri yüklenmesi. | `backup_manager.py` (SEC-12): Parolalı AES-256 ZIP (`pyzipper`), her dosya için SHA-256 `BACKUP_MANIFEST.json`, yanlış parola `400`, zip-slip koruması. |
| **Repudiation** | Silme, yedekleme, yetki reddi veya kod yürütme olaylarının izinin örtülmesi. | `audit_log.py` + `AuditTrail` (SEC-15): SHA-256 zincirli `audit_chain.jsonl`, `GET /api/admin/audit/verify` değiştirilmiş satırı tam numarasıyla raporlar. |
| **Information Disclosure (PII)** | Kullanıcı verileri silindikten sonra SQLite WAL/boş sayfalarda kalması veya loglara sızması. | `user_profile.wipe_data` (SEC-21): `PRAGMA wal_checkpoint(TRUNCATE)` + `VACUUM` + medya blob silme; `log_sanitizer.py` (SEC-23) loglarda token/TCKN/IBAN/telefon/e-posta maskeler. |

---

## Güven Sınırı 3: Master <-> Dağıtık Ajan Düğümleri

| STRIDE | Tehdit | Uygulanan Önlem |
|---|---|---|
| **Spoofing** | Ortak `AGENT_TOKEN` sızarsa bir ajanın başka ajan kimliğine bürünmesi. | `agents_api.py` (SEC-18): Kayıtta ajan başına benzersiz anahtar (`agt_...`) üretilir, veritabanında yalnızca SHA-256 özeti saklanır; iptal (`revoke-key`) ve döndürme (`rotate-key`) uç noktaları. |
| **Elevation of Privilege / Tampering** | Ajan A'nın, Ajan B'ye atanmış görevin sonucunu yazması veya kuyruğunu çekmesi. | `tasks_api.py` (SEC-18): `caller_agent_id != assigned_to` durumunda `403 Forbidden` ve denetim izine `TASK_RESULT_OWNERSHIP_DENIED` kaydı. |
| **Spoofing / Rogue Registration** | İptal edilmiş veya onaysız bir ajanın tekrar kaydolup görev alması. | `agents_api.py`: `agent_key_revoked=1` olan ajanların kayıt ve yoklaması `401` ile reddedilir; opsiyonel `REQUIRE_AGENT_APPROVAL` yönetici onayı. |

---

## Güven Sınırı 4: Master <-> Yerel Ollama Model Sunucusu

| STRIDE | Tehdit | Uygulanan Önlem |
|---|---|---|
| **Tampering (Prompt Injection)** | Yüklenen dosya veya sohbet geçmişinden gelen metinlerin aracı yetkisiz eylemlere yönlendirmesi. | Eylem tabanlı sunucu modeli (SEC-14); LLM çıktısı asla ana makinede serbest kabuğa (`shell=True`) verilmez; deterministik dosya denetimi ve sıkı sistem yönergesi. |
| **Denial of Service** | Dev bağlam veya sonsuz akışla Ollama/master kaynaklarının tüketilmesi. | Sabit zaman aşımları (`httpx` timeout), sınırlı `num_predict`/`num_ctx`, yükleme boyut sınırları (`MAX_UPLOAD_BYTES`). |
| **Information Disclosure** | Model yanıtının hata günlüklerinde ham kullanıcı istemlerini/gizlerini sızdırması. | `log_sanitizer.py` (SEC-23): `prompt`/`response` yalnızca debug kipinde kısaltılmış ve maskeli; üretim günlüklerinde `[OMITTED]`. |

---

## Güven Sınırı 5: Master <-> Kod Çalıştırma Sandbox'ı (Docker)

| STRIDE | Tehdit | Uygulanan Önlem |
|---|---|---|
| **Elevation of Privilege** | Üretilen kodun ana makinede veya konteyner içinde `root` yetkisiyle çalışması. | `master/sandbox/runner.py` + `docker/sandbox/Dockerfile` (SEC-13): `--user 10001:10001`, `--cap-drop ALL`, `--security-opt no-new-privileges:true`, özel `seccomp.json`. |
| **Information Disclosure / Lateral Movement** | Çalışan kodun ana makine dosyalarına veya yerel ağ/metadata servislerine (`curl http://host`) erişmesi. | `--network none`, `--read-only`, tek salt-okunur çalışma alanı bağlaması (`-v ws:/sandbox:ro`), Docker yoksa özellik tamamen kapalı (`503`). |
| **Denial of Service (Fork Bomb / Disk Fill)** | Kötü amaçlı kodun CPU, RAM, PID veya diski tüketmesi. | `--cpus 0.5`, `--memory 256m`, `--pids-limit 64`, `--tmpfs /tmp:rw,noexec,nosuid,size=64m`, 10 sn sert zaman aşımı. |

---

## Güven Sınırı 6: Master <-> Harici Ağ, Tailnet ve MCP Sunucuları

| STRIDE | Tehdit | Uygulanan Önlem |
|---|---|---|
| **Information Disclosure / Unauthorized Network Access** | Master'ın `0.0.0.0` ile halka açık Wi-Fi / LAN'a açılması. | `scripts/dev.ps1` + `docker-compose.yml` (SEC-24): Varsayılan `127.0.0.1`, Tailscale kipinde yalnız `tailscale ip -4`, Windows Güvenlik Duvarı yalnız `Private` + `RemoteAddress 100.64.0.0/10`. |
| **Information Disclosure (Supply Chain & Repo Leaks)** | `.env`, `AGENT_TOKEN`, `tskey-` anahtarlarının git geçmişine veya açıklı paketlerin üretime girmesi. | `.gitleaks.toml`, `.pre-commit-config.yaml` (SEC-20); CI'da `pip-audit`, Trivy, CycloneDX SBOM ve Dependabot (SEC-19). |
| **Tampering / SSRF (External MCP)** | Harici MCP sunucusunun yetkisiz eklenmesi veya kimlik anahtarının sızması. | MCP yazma/keşif/çağrı uç noktaları `require_local_or_admin` ile korunur, anahtarlar `secret_store` içinde Fernet ile şifrelenir ve her çağrı `AuditTrail`'e yazılır. |

---

## Otomatik Yetkisiz Erişim Matrisi (`pytest -m security`)
`master/tests/test_security_matrix.py`, FastAPI OpenAPI şemasından tüm rotaları tarar. Yeni eklenen ve yetki koruması olmayan herhangi bir mutasyon (`POST`/`PUT`/`DELETE`/`PATCH`) rotası CI güvenlik kapısını otomatik olarak kırar.
