# Parça 3 — API sözleşmesi, başlıklar ve güvenlik yoklaması

## HDR · HTTP başlıkları, hız sınırı ve önbellek

#### HDR-01 · GET / header-missing
- **Sorun:** [DOĞRULANDI: F203] GET /: strict-transport-security yok.
- **Değişiklik:** Eksik güvenlik başlığını orta katmanda ekle.
- **Kabul:** Başlık testi bu başlığı doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### HDR-02 · GET / header-missing
- **Sorun:** [DOĞRULANDI: F203] GET /: cross-origin-opener-policy yok.
- **Değişiklik:** Eksik güvenlik başlığını orta katmanda ekle.
- **Kabul:** Başlık testi bu başlığı doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### HDR-03 · GET / header-missing
- **Sorun:** [DOĞRULANDI: F203] GET /: cross-origin-resource-policy yok.
- **Değişiklik:** Eksik güvenlik başlığını orta katmanda ekle.
- **Kabul:** Başlık testi bu başlığı doğrular.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### HDR-04 · GET / csp-unsafe-inline
- **Sorun:** [DOĞRULANDI: F203] GET /: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; .
- **Değişiklik:** Satır içi betik/stilleri taşı, nonce kullan, `unsafe-inline`'ı kaldır.
- **Kabul:** CSP `unsafe-inline` içermez; arayüz çalışır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### HDR-05 · GET /api/agents api-no-cache-control
- **Sorun:** [DOĞRULANDI: F203] GET /api/agents: Cache-Control başlığı yok.
- **Değişiklik:** Hassas ve dinamik API yanıtlarına `Cache-Control: no-store` ekle.
- **Kabul:** Başlık testi geçer.
- **Meta:** P2 · S · Bağ: - · Durum: açık

#### HDR-06 · GET /api/agents no-rate-limit
- **Sorun:** [DOĞRULANDI: F203] GET /api/agents: 120 istek 2.1 sn içinde, hiçbiri 429 değil.
- **Değişiklik:** Token-bucket orta katmanını (`ratelimit.TokenBucket`) tüm API'ye bağla.
- **Kabul:** 120 hızlı istekte 429 ve Retry-After döner.
- **Meta:** P1 · S · Bağ: - · Durum: açık

## SMA · Yanıt şeması eksik route'lar (1)

#### SMA-01 · GET /ready yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /ready: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-02 · GET /metrics yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /metrics: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-03 · GET /api/admin/errors yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/admin/errors: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-04 · GET /api/admin/features yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/admin/features: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-05 · PUT /api/admin/features/{name} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] PUT /api/admin/features/{name}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-06 · GET /api/admin/events yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/admin/events: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-07 · GET /api/admin/maintenance yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/admin/maintenance: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-08 · GET /api/admin/db-doctor yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/admin/db-doctor: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-09 · GET /api/admin/erd yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/admin/erd: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-10 · GET /api/admin/data-services yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/admin/data-services: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-11 · POST /api/agents/register yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/agents/register: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-12 · POST /api/agents/{agent_id}/heartbeat yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/agents/{agent_id}/heartbeat: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-13 · POST /api/agents/{agent_id}/revoke-key yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/agents/{agent_id}/revoke-key: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-14 · POST /api/agents/{agent_id}/rotate-key yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/agents/{agent_id}/rotate-key: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-15 · POST /api/agents/{agent_id}/approve yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/agents/{agent_id}/approve: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-16 · GET /api/agents/{agent_id}/scores yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/agents/{agent_id}/scores: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-17 · GET /api/agents yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/agents: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-18 · GET /api/auth/status yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/auth/status: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-19 · POST /api/auth/setup yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/auth/setup: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-20 · POST /api/auth/login yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/auth/login: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-21 · POST /api/auth/logout yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/auth/logout: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-22 · GET /api/auth/me yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/auth/me: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-23 · POST /api/auth/users yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/auth/users: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-24 · POST /api/auth/reset-password yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/auth/reset-password: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-25 · GET /api/auth/tailscale-me yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/auth/tailscale-me: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-26 · GET /api/projects yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/projects: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-27 · POST /api/projects yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/projects: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-28 · GET /api/projects/{project_id} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/projects/{project_id}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-29 · DELETE /api/projects/{project_id} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] DELETE /api/projects/{project_id}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-30 · POST /api/projects/{project_id}/reanalyze yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/projects/{project_id}/reanalyze: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-31 · GET /api/assistant/media/{filename} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/assistant/media/{filename}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-32 · POST /api/assistant/chat/stream yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/assistant/chat/stream: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-33 · GET /api/assistant/config yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/assistant/config: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-34 · POST /api/assistant/transcribe yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/assistant/transcribe: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-35 · GET /api/assistant/enterprise-status yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/assistant/enterprise-status: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-36 · GET /api/agents/{agent_id}/tasks/next yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/agents/{agent_id}/tasks/next: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-37 · POST /api/tasks/{task_id}/result yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/tasks/{task_id}/result: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-38 · POST /api/tasks/{task_id}/fix-tasks yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/tasks/{task_id}/fix-tasks: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-39 · POST /api/tasks/{task_id}/cancel yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/tasks/{task_id}/cancel: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-40 · POST /api/eval/start yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/eval/start: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-41 · GET /api/projects/{project_id}/output.zip yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/projects/{project_id}/output.zip: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-42 · GET /api/projects/{project_id}/output yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/projects/{project_id}/output: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-43 · GET /api/perf/stats yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/perf/stats: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-44 · GET /api/dashboard yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/dashboard: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-45 · GET /api/projects/{project_id}/conflicts yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/projects/{project_id}/conflicts: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-46 · POST /api/projects/{project_id}/conflicts/{conflict_id}/resolve yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/projects/{project_id}/conflicts/{conflict_id}/resolve: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-47 · GET /api/events yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/events: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-48 · GET /api/cnc/jobs yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/cnc/jobs: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-49 · GET /api/cnc/jobs/{id} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/cnc/jobs/{id}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-50 · POST /api/cnc/balloon yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/cnc/balloon: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-51 · PUT /api/cnc/jobs/{id}/balloons yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] PUT /api/cnc/jobs/{id}/balloons: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-52 · GET /api/cnc/jobs/{id}/file/{kind} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/cnc/jobs/{id}/file/{kind}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-53 · POST /api/cnc/demo yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/cnc/demo: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-54 · POST /api/cnc/jobs/{id}/evaluate-measurements yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/cnc/jobs/{id}/evaluate-measurements: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-55 · GET /api/studio/workspaces yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/studio/workspaces: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-56 · POST /api/studio/generate yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studio/generate: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-57 · POST /api/studio/workspaces/{id}/iterate yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studio/workspaces/{id}/iterate: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-58 · GET /api/studio/workspaces/{id}/tree yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/studio/workspaces/{id}/tree: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-59 · GET /api/studio/workspaces/{id}/file yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/studio/workspaces/{id}/file: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-60 · PUT /api/studio/workspaces/{id}/file yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] PUT /api/studio/workspaces/{id}/file: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-61 · DELETE /api/studio/workspaces/{id}/file yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] DELETE /api/studio/workspaces/{id}/file: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-62 · DELETE /api/studio/workspaces/{id} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] DELETE /api/studio/workspaces/{id}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-63 · POST /api/studio/workspaces/{id}/build-exe yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studio/workspaces/{id}/build-exe: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-64 · POST /api/studio/workspaces/{id}/launch-exe yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studio/workspaces/{id}/launch-exe: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-65 · GET /api/studio/workspaces/{id}/download-exe yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/studio/workspaces/{id}/download-exe: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-66 · GET /api/studio/workspaces/{id}/download.zip yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/studio/workspaces/{id}/download.zip: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-67 · GET /api/studio/workspaces/{id}/preview/{filepath} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/studio/workspaces/{id}/preview/{filepath}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-68 · GET /api/studio/workspaces/{id}/history yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/studio/workspaces/{id}/history: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-69 · POST /api/studio/workspaces/{id}/restore/{version} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studio/workspaces/{id}/restore/{version}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-70 · POST /api/studio/workspaces/{id}/start-server yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studio/workspaces/{id}/start-server: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-71 · GET /api/studio/workspaces/{id}/diff yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/studio/workspaces/{id}/diff: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-72 · POST /api/studio/workspaces/{id}/actions yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studio/workspaces/{id}/actions: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-73 · POST /api/studio/workspaces/{id}/exec yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studio/workspaces/{id}/exec: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-74 · POST /api/studio/workspaces/{id}/git yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studio/workspaces/{id}/git: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-75 · GET /api/studio/workspaces/{id}/search yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/studio/workspaces/{id}/search: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-76 · GET /api/studio/workspaces/{id}/code-graph yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/studio/workspaces/{id}/code-graph: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-77 · GET /api/studio/workspaces/{id}/security-scan yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/studio/workspaces/{id}/security-scan: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-78 · GET /api/user/profiles yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/user/profiles: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-79 · POST /api/user/profiles yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/user/profiles: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-80 · GET /api/user/{user_id}/profile yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/user/{user_id}/profile: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-81 · PUT /api/user/{user_id}/profile yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] PUT /api/user/{user_id}/profile: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-82 · DELETE /api/user/{user_id} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] DELETE /api/user/{user_id}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-83 · GET /api/user/{user_id}/stats yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/user/{user_id}/stats: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-84 · GET /api/user/{user_id}/personalization-preview yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/user/{user_id}/personalization-preview: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-85 · GET /api/user/{user_id}/memories yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/user/{user_id}/memories: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-86 · POST /api/user/{user_id}/memories yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/user/{user_id}/memories: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-87 · DELETE /api/user/{user_id}/memories/{fact_id} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] DELETE /api/user/{user_id}/memories/{fact_id}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-88 · GET /api/user/{user_id}/conversations yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/user/{user_id}/conversations: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-89 · GET /api/user/{user_id}/chats yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/user/{user_id}/chats: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-90 · PUT /api/user/{user_id}/chats/{chat_id} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] PUT /api/user/{user_id}/chats/{chat_id}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-91 · DELETE /api/user/{user_id}/chats/{chat_id} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] DELETE /api/user/{user_id}/chats/{chat_id}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-92 · GET /api/user/{user_id}/history/search yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/user/{user_id}/history/search: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-93 · GET /api/user/{user_id}/export yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/user/{user_id}/export: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-94 · DELETE /api/user/{user_id}/data yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] DELETE /api/user/{user_id}/data: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-95 · GET /api/mcp/connectors yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/mcp/connectors: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-96 · POST /api/mcp/connectors yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/mcp/connectors: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-97 · PUT /api/mcp/connectors/{connector_id} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] PUT /api/mcp/connectors/{connector_id}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-98 · DELETE /api/mcp/connectors/{connector_id} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] DELETE /api/mcp/connectors/{connector_id}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMA-99 · POST /api/mcp/connectors/{connector_id}/discover yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/mcp/connectors/{connector_id}/discover: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

## SMB · Yanıt şeması eksik route'lar (2)

#### SMB-01 · POST /api/mcp/connectors/{connector_id}/call yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/mcp/connectors/{connector_id}/call: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-02 · GET /api/admin/backup.zip yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/admin/backup.zip: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-03 · POST /api/admin/backup/restore yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/admin/backup/restore: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-04 · GET /api/admin/audit/verify yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/admin/audit/verify: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-05 · GET /api/admin/audit/events yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/admin/audit/events: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-06 · GET /api/gateway/status yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/gateway/status: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-07 · GET /api/gateway/models yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/gateway/models: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-08 · GET /api/gateway/traces/{run_id} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/gateway/traces/{run_id}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-09 · GET /api/orchestrator/intents yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/orchestrator/intents: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-10 · GET /api/orchestrator/tools yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/orchestrator/tools: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-11 · POST /api/orchestrator/run yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/orchestrator/run: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-12 · GET /api/orchestrator/runs/{run_id} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/orchestrator/runs/{run_id}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-13 · POST /api/orchestrator/runs/{run_id}/replay yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/orchestrator/runs/{run_id}/replay: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-14 · GET /api/orchestrator/jobs/{job_id} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/orchestrator/jobs/{job_id}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-15 · GET /api/orchestrator/artifacts yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/orchestrator/artifacts: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-16 · GET /api/orchestrator/artifacts/{artifact_id} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/orchestrator/artifacts/{artifact_id}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-17 · GET /api/orchestrator/artifacts/{artifact_id}/versions yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/orchestrator/artifacts/{artifact_id}/versions: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-18 · POST /api/orchestrator/artifacts/{artifact_id}/edit yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/orchestrator/artifacts/{artifact_id}/edit: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-19 · POST /api/orchestrator/feedback yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/orchestrator/feedback: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-20 · GET /api/orchestrator/feedback/summary yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/orchestrator/feedback/summary: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-21 · GET /api/rag/collections yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/rag/collections: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-22 · POST /api/rag/collections yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/rag/collections: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-23 · POST /api/rag/ingest yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/rag/ingest: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-24 · POST /api/rag/ingest-file yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/rag/ingest-file: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-25 · GET /api/rag/collections/{collection_id}/documents yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/rag/collections/{collection_id}/documents: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-26 · DELETE /api/rag/documents/{doc_id} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] DELETE /api/rag/documents/{doc_id}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-27 · POST /api/rag/search yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/rag/search: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-28 · GET /api/rag/chunks/{chunk_id} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/rag/chunks/{chunk_id}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-29 · GET /api/rag/jobs/{job_id} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/rag/jobs/{job_id}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-30 · GET /api/rag/web/search yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/rag/web/search: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-31 · POST /api/rag/doctor yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/rag/doctor: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-32 · GET /api/hallucination/taxonomy yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/hallucination/taxonomy: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-33 · POST /api/hallucination/verify yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/hallucination/verify: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-34 · GET /api/hallucination/telemetry yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/hallucination/telemetry: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-35 · GET /api/hallucination/profiles yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/hallucination/profiles: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-36 · POST /api/hallucination/reports yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/hallucination/reports: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-37 · POST /api/hallucination/reports/{report_id}/approve yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/hallucination/reports/{report_id}/approve: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-38 · GET /api/hallucination/reliability yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/hallucination/reliability: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-39 · GET /api/ml/models yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/ml/models: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-40 · POST /api/ml/models/register yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/ml/models/register: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-41 · POST /api/ml/models/{model_id}/canary-check yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/ml/models/{model_id}/canary-check: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-42 · POST /api/ml/drift yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/ml/drift: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-43 · GET /api/ml/active-learning yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/ml/active-learning: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-44 · POST /api/ml/dpo/export yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/ml/dpo/export: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-45 · GET /api/studios/capabilities yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/studios/capabilities: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-46 · POST /api/studios/research yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studios/research: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-47 · POST /api/studios/presentation/outline yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studios/presentation/outline: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-48 · POST /api/studios/documents/audit yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studios/documents/audit: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-49 · POST /api/studios/data/profile yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studios/data/profile: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-50 · POST /api/studios/data/forecast yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studios/data/forecast: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-51 · POST /api/studios/data/stat-test yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studios/data/stat-test: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-52 · POST /api/studios/media/anonymize yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studios/media/anonymize: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-53 · POST /api/studios/media/diagram/validate yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studios/media/diagram/validate: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-54 · GET /api/studios/media/{media_id} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/studios/media/{media_id}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-55 · GET /api/factory/templates yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/factory/templates: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-56 · POST /api/factory/plan yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/factory/plan: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-57 · POST /api/factory/build yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/factory/build: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-58 · POST /api/factory/hunk-diff yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/factory/hunk-diff: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-59 · POST /api/factory/workspaces/{plan_id}/package yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/factory/workspaces/{plan_id}/package: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-60 · POST /api/factory/workspaces/{plan_id}/sast yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/factory/workspaces/{plan_id}/sast: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-61 · GET /api/games/genres yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/games/genres: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-62 · POST /api/games/build yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/games/build: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-63 · POST /api/games/level/validate yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/games/level/validate: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-64 · GET /api/domains/specs yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/domains/specs: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-65 · POST /api/domains/finance/dcf yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/domains/finance/dcf: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-66 · POST /api/domains/legal/analyze yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/domains/legal/analyze: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-67 · POST /api/domains/health/info yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/domains/health/info: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-68 · POST /api/domains/engineering/convert yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/domains/engineering/convert: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-69 · POST /api/domains/cnc/kienzle yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/domains/cnc/kienzle: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-70 · POST /api/domains/cnc/gcode/validate yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/domains/cnc/gcode/validate: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-71 · GET /api/distributed/taxonomy yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/distributed/taxonomy: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-72 · GET /api/distributed/benchmarks/tasks yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/distributed/benchmarks/tasks: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-73 · GET /api/distributed/agents/stream yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/distributed/agents/stream: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-74 · GET /api/distributed/performance yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/distributed/performance: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-75 · GET /api/distributed/performance.csv yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/distributed/performance.csv: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-76 · GET /api/distributed/setup-command yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/distributed/setup-command: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-77 · POST /api/distributed/select yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/distributed/select: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-78 · POST /api/distributed/conflicts/merge yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/distributed/conflicts/merge: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-79 · POST /api/distributed/diagnose/tailscale yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/distributed/diagnose/tailscale: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-80 · GET /api/ux/health-wizard yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/ux/health-wizard: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-81 · GET /api/ux/settings/schema yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/ux/settings/schema: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-82 · POST /api/ux/settings/validate yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/ux/settings/validate: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-83 · POST /api/ux/shares yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] POST /api/ux/shares: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-84 · GET /api/ux/shares/{share_id} yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/ux/shares/{share_id}: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-85 · GET /api/ux/slo yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/ux/slo: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-86 · GET /api/admin/contract-check yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/admin/contract-check: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-87 · GET /health yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /health: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-88 · GET /api/master/status yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /api/master/status: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

#### SMB-89 · GET / yanıt şeması
- **Sorun:** [DOĞRULANDI: F203] GET /: OpenAPI'de 200 yanıtı için şema yok; arayüz–API sözleşme testi yazılamıyor.
- **Değişiklik:** Pydantic `response_model` ekle ve alanları belgele.
- **Kabul:** OpenAPI bu route için şema içerir; sözleşme testi alan adı değişince kırılır.
- **Meta:** P1 · S · Bağ: - · Durum: açık

## ACK · Açıklaması eksik route'lar (1)

#### ACK-01 · GET /metrics açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /metrics: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-02 · GET /api/admin/errors açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/admin/errors: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-03 · GET /api/admin/features açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/admin/features: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-04 · PUT /api/admin/features/{name} açıklaması
- **Sorun:** [DOĞRULANDI: F203] PUT /api/admin/features/{name}: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-05 · GET /api/admin/events açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/admin/events: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-06 · GET /api/admin/maintenance açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/admin/maintenance: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-07 · GET /api/admin/db-doctor açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/admin/db-doctor: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-08 · GET /api/admin/erd açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/admin/erd: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-09 · GET /api/admin/data-services açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/admin/data-services: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-10 · POST /api/agents/register açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/agents/register: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-11 · POST /api/agents/{agent_id}/heartbeat açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/agents/{agent_id}/heartbeat: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-12 · GET /api/agents/{agent_id}/scores açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/agents/{agent_id}/scores: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-13 · GET /api/agents açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/agents: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-14 · GET /api/auth/status açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/auth/status: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-15 · POST /api/auth/setup açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/auth/setup: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-16 · POST /api/auth/login açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/auth/login: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-17 · POST /api/auth/logout açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/auth/logout: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-18 · GET /api/auth/me açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/auth/me: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-19 · POST /api/auth/users açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/auth/users: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-20 · POST /api/auth/reset-password açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/auth/reset-password: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-21 · GET /api/auth/tailscale-me açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/auth/tailscale-me: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-22 · GET /api/projects açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/projects: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-23 · POST /api/projects açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/projects: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-24 · GET /api/projects/{project_id} açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/projects/{project_id}: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-25 · DELETE /api/projects/{project_id} açıklaması
- **Sorun:** [DOĞRULANDI: F203] DELETE /api/projects/{project_id}: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-26 · POST /api/projects/{project_id}/reanalyze açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/projects/{project_id}/reanalyze: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-27 · POST /api/assistant/chat açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/assistant/chat: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-28 · GET /api/studio/workspaces açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/studio/workspaces: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-29 · POST /api/studio/generate açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studio/generate: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-30 · POST /api/studio/workspaces/{id}/iterate açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studio/workspaces/{id}/iterate: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-31 · GET /api/studio/workspaces/{id}/tree açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/studio/workspaces/{id}/tree: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-32 · GET /api/studio/workspaces/{id}/file açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/studio/workspaces/{id}/file: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-33 · PUT /api/studio/workspaces/{id}/file açıklaması
- **Sorun:** [DOĞRULANDI: F203] PUT /api/studio/workspaces/{id}/file: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-34 · DELETE /api/studio/workspaces/{id}/file açıklaması
- **Sorun:** [DOĞRULANDI: F203] DELETE /api/studio/workspaces/{id}/file: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-35 · DELETE /api/studio/workspaces/{id} açıklaması
- **Sorun:** [DOĞRULANDI: F203] DELETE /api/studio/workspaces/{id}: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-36 · POST /api/studio/workspaces/{id}/build-exe açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studio/workspaces/{id}/build-exe: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-37 · GET /api/studio/workspaces/{id}/download-exe açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/studio/workspaces/{id}/download-exe: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-38 · GET /api/studio/workspaces/{id}/download.zip açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/studio/workspaces/{id}/download.zip: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-39 · GET /api/studio/workspaces/{id}/history açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/studio/workspaces/{id}/history: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-40 · POST /api/studio/workspaces/{id}/restore/{version} açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studio/workspaces/{id}/restore/{version}: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-41 · GET /api/user/profiles açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/user/profiles: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-42 · POST /api/user/profiles açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/user/profiles: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-43 · GET /api/user/{user_id}/profile açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/user/{user_id}/profile: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-44 · PUT /api/user/{user_id}/profile açıklaması
- **Sorun:** [DOĞRULANDI: F203] PUT /api/user/{user_id}/profile: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-45 · DELETE /api/user/{user_id} açıklaması
- **Sorun:** [DOĞRULANDI: F203] DELETE /api/user/{user_id}: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-46 · GET /api/user/{user_id}/stats açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/user/{user_id}/stats: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-47 · GET /api/user/{user_id}/personalization-preview açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/user/{user_id}/personalization-preview: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-48 · GET /api/user/{user_id}/memories açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/user/{user_id}/memories: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-49 · POST /api/user/{user_id}/memories açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/user/{user_id}/memories: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-50 · DELETE /api/user/{user_id}/memories/{fact_id} açıklaması
- **Sorun:** [DOĞRULANDI: F203] DELETE /api/user/{user_id}/memories/{fact_id}: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-51 · GET /api/user/{user_id}/conversations açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/user/{user_id}/conversations: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-52 · GET /api/user/{user_id}/chats açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/user/{user_id}/chats: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-53 · PUT /api/user/{user_id}/chats/{chat_id} açıklaması
- **Sorun:** [DOĞRULANDI: F203] PUT /api/user/{user_id}/chats/{chat_id}: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-54 · DELETE /api/user/{user_id}/chats/{chat_id} açıklaması
- **Sorun:** [DOĞRULANDI: F203] DELETE /api/user/{user_id}/chats/{chat_id}: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-55 · GET /api/user/{user_id}/history/search açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/user/{user_id}/history/search: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-56 · GET /api/user/{user_id}/export açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/user/{user_id}/export: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-57 · DELETE /api/user/{user_id}/data açıklaması
- **Sorun:** [DOĞRULANDI: F203] DELETE /api/user/{user_id}/data: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-58 · GET /api/mcp/connectors açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/mcp/connectors: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-59 · POST /api/mcp/connectors açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/mcp/connectors: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-60 · PUT /api/mcp/connectors/{connector_id} açıklaması
- **Sorun:** [DOĞRULANDI: F203] PUT /api/mcp/connectors/{connector_id}: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-61 · DELETE /api/mcp/connectors/{connector_id} açıklaması
- **Sorun:** [DOĞRULANDI: F203] DELETE /api/mcp/connectors/{connector_id}: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-62 · POST /api/mcp/connectors/{connector_id}/discover açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/mcp/connectors/{connector_id}/discover: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-63 · POST /api/mcp/connectors/{connector_id}/call açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/mcp/connectors/{connector_id}/call: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-64 · GET /api/gateway/status açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/gateway/status: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-65 · GET /api/gateway/models açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/gateway/models: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-66 · GET /api/gateway/traces/{run_id} açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/gateway/traces/{run_id}: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-67 · GET /api/orchestrator/intents açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/orchestrator/intents: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-68 · GET /api/orchestrator/tools açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/orchestrator/tools: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-69 · POST /api/orchestrator/run açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/orchestrator/run: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-70 · GET /api/orchestrator/jobs/{job_id} açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/orchestrator/jobs/{job_id}: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-71 · GET /api/orchestrator/artifacts açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/orchestrator/artifacts: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-72 · GET /api/orchestrator/artifacts/{artifact_id} açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/orchestrator/artifacts/{artifact_id}: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-73 · GET /api/orchestrator/artifacts/{artifact_id}/versions açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/orchestrator/artifacts/{artifact_id}/versions: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-74 · POST /api/orchestrator/artifacts/{artifact_id}/edit açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/orchestrator/artifacts/{artifact_id}/edit: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-75 · POST /api/orchestrator/feedback açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/orchestrator/feedback: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-76 · GET /api/orchestrator/feedback/summary açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/orchestrator/feedback/summary: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-77 · GET /api/rag/collections açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/rag/collections: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-78 · POST /api/rag/collections açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/rag/collections: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-79 · POST /api/rag/ingest açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/rag/ingest: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-80 · GET /api/rag/collections/{collection_id}/documents açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/rag/collections/{collection_id}/documents: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-81 · DELETE /api/rag/documents/{doc_id} açıklaması
- **Sorun:** [DOĞRULANDI: F203] DELETE /api/rag/documents/{doc_id}: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-82 · POST /api/rag/search açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/rag/search: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-83 · GET /api/rag/jobs/{job_id} açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/rag/jobs/{job_id}: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-84 · GET /api/rag/web/search açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/rag/web/search: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-85 · POST /api/rag/doctor açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/rag/doctor: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-86 · GET /api/hallucination/taxonomy açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/hallucination/taxonomy: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-87 · POST /api/hallucination/verify açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/hallucination/verify: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-88 · GET /api/hallucination/telemetry açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/hallucination/telemetry: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-89 · GET /api/hallucination/profiles açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/hallucination/profiles: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-90 · POST /api/hallucination/reports açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/hallucination/reports: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-91 · POST /api/hallucination/reports/{report_id}/approve açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/hallucination/reports/{report_id}/approve: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-92 · GET /api/ml/models açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/ml/models: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-93 · POST /api/ml/models/register açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/ml/models/register: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-94 · POST /api/ml/models/{model_id}/canary-check açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/ml/models/{model_id}/canary-check: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-95 · POST /api/ml/drift açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/ml/drift: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-96 · GET /api/ml/active-learning açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/ml/active-learning: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-97 · POST /api/ml/dpo/export açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/ml/dpo/export: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-98 · GET /api/studios/capabilities açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/studios/capabilities: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACK-99 · POST /api/studios/research açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studios/research: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

## ACL · Açıklaması eksik route'lar (2)

#### ACL-01 · POST /api/studios/presentation/outline açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studios/presentation/outline: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-02 · POST /api/studios/documents/audit açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studios/documents/audit: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-03 · POST /api/studios/data/profile açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studios/data/profile: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-04 · POST /api/studios/data/forecast açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studios/data/forecast: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-05 · POST /api/studios/data/stat-test açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studios/data/stat-test: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-06 · POST /api/studios/media/anonymize açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studios/media/anonymize: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-07 · POST /api/studios/media/diagram/validate açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/studios/media/diagram/validate: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-08 · GET /api/factory/templates açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/factory/templates: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-09 · POST /api/factory/plan açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/factory/plan: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-10 · POST /api/factory/build açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/factory/build: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-11 · POST /api/factory/hunk-diff açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/factory/hunk-diff: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-12 · POST /api/factory/workspaces/{plan_id}/package açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/factory/workspaces/{plan_id}/package: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-13 · POST /api/factory/workspaces/{plan_id}/sast açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/factory/workspaces/{plan_id}/sast: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-14 · GET /api/games/genres açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/games/genres: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-15 · POST /api/games/build açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/games/build: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-16 · POST /api/games/level/validate açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/games/level/validate: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-17 · GET /api/domains/specs açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/domains/specs: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-18 · POST /api/domains/finance/dcf açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/domains/finance/dcf: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-19 · POST /api/domains/legal/analyze açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/domains/legal/analyze: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-20 · POST /api/domains/health/info açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/domains/health/info: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-21 · POST /api/domains/engineering/convert açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/domains/engineering/convert: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-22 · POST /api/domains/cnc/kienzle açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/domains/cnc/kienzle: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-23 · POST /api/domains/cnc/gcode/validate açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/domains/cnc/gcode/validate: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-24 · GET /api/distributed/taxonomy açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/distributed/taxonomy: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-25 · GET /api/distributed/benchmarks/tasks açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/distributed/benchmarks/tasks: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-26 · GET /api/distributed/performance açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/distributed/performance: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-27 · GET /api/distributed/performance.csv açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/distributed/performance.csv: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-28 · GET /api/distributed/setup-command açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/distributed/setup-command: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-29 · POST /api/distributed/select açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/distributed/select: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-30 · POST /api/distributed/conflicts/merge açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/distributed/conflicts/merge: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-31 · POST /api/distributed/diagnose/tailscale açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/distributed/diagnose/tailscale: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-32 · GET /api/ux/health-wizard açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/ux/health-wizard: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-33 · GET /api/ux/settings/schema açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/ux/settings/schema: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-34 · POST /api/ux/settings/validate açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/ux/settings/validate: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-35 · POST /api/ux/shares açıklaması
- **Sorun:** [DOĞRULANDI: F203] POST /api/ux/shares: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-36 · GET /api/ux/shares/{share_id} açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/ux/shares/{share_id}: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-37 · GET /health açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /health: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-38 · GET /api/master/status açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /api/master/status: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık

#### ACL-39 · GET / açıklaması
- **Sorun:** [DOĞRULANDI: F203] GET /: docstring/açıklama yok; yönetici arayüzü ve geliştiriciler amacı göremiyor.
- **Değişiklik:** Kısa amaç, yetki ve hata durumlarını docstring'e yaz.
- **Kabul:** OpenAPI `description` dolu.
- **Meta:** P3 · S · Bağ: - · Durum: açık
