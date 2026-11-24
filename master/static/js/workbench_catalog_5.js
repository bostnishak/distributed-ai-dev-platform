// Interactive Workbench Catalog Part 5: Custom Agents, Webhooks/Cron, MCP Server, OTel, Notifications, Marketplace & OpenAI v1.

export const ECOSYSTEM_TOOLS = [
  // EPK-11: Sürümlü Özel Asistanlar
  { id: 'cag-list', group: 'Özel Asistanlar & Otomasyon', title: 'Sürümlü Özel Asistanları Listele', method: 'GET', path: '/api/custom-agents' },
  { id: 'cag-upsert', group: 'Özel Asistanlar & Otomasyon', title: 'Özel Asistan Oluştur / Yeni Sürüm', method: 'POST', path: '/api/custom-agents',
    body: { user_id: 'default', name: 'Kod Denetçisi', instructions: 'Kodu OWASP ve PEP8 açısından incele.', allowed_tools: ['lint'] } },
  { id: 'cag-rb', group: 'Özel Asistanlar & Otomasyon', title: 'Özel Asistan Sürümünü Geri Al', method: 'POST', path: '/api/custom-agents/{agent_id}/rollback',
    params: { agent_id: 'ag_demo' }, body: { user_id: 'default', target_version: 1 } },

  // EPK-12: İmzalı Webhook & Cron
  { id: 'wh-sign', group: 'Özel Asistanlar & Otomasyon', title: 'HMAC-SHA256 Webhook İmzala', method: 'POST', path: '/api/automation/webhooks/sign',
    body: { event_type: 'task.done', target_url: '', payload: '{"ok":true}', secret: 'demo-secret-key' } },
  { id: 'wh-ver', group: 'Özel Asistanlar & Otomasyon', title: 'Webhook İmzasını Doğrula', method: 'POST', path: '/api/automation/webhooks/verify',
    body: { payload: '{"ok":true}', secret: 'demo-secret-key', signature: 'sha256=...' } },
  { id: 'cron-val', group: 'Özel Asistanlar & Otomasyon', title: 'Cron İfadesi Doğrula', method: 'POST', path: '/api/automation/cron/validate',
    body: { expression: '*/15 9-18 * * 1-5' } },

  // EPK-13: MCP Sunucu & Yerel Bağlayıcılar
  { id: 'mcps-rpc', group: 'MCP Sunucu, OTel & Güncelleme', title: 'MCP Sunucu JSON-RPC 2.0 Çağrısı', method: 'POST', path: '/api/mcp-server/rpc',
    body: { jsonrpc: '2.0', id: 1, method: 'tools/list', params: {} } },
  { id: 'mcps-conn', group: 'MCP Sunucu, OTel & Güncelleme', title: 'Yerel Bağlayıcı Yetenekleri', method: 'GET', path: '/api/mcp-server/connectors' },

  // EPK-17: OpenTelemetry
  { id: 'otel-get', group: 'MCP Sunucu, OTel & Güncelleme', title: 'OTLP İzleme (Span) Dışa Aktar', method: 'GET', path: '/api/telemetry/otel/spans' },
  { id: 'otel-post', group: 'MCP Sunucu, OTel & Güncelleme', title: 'Yeni OTel Span Kaydet', method: 'POST', path: '/api/telemetry/otel/spans',
    body: { name: 'assistant.chat', duration_ms: 42.5, status: 'OK' } },

  // EPK-24: Güncelleme & Doğrulama
  { id: 'upd-st', group: 'MCP Sunucu, OTel & Güncelleme', title: 'Sürüm ve Güncelleme Durumu', method: 'GET', path: '/api/admin/update/status' },
  { id: 'upd-ver', group: 'MCP Sunucu, OTel & Güncelleme', title: 'Sürüm Paketi SHA-256 Doğrula', method: 'POST', path: '/api/admin/update/verify-release',
    body: { payload: 'release-v2.5.0', expected_sha256: '0000000000000000000000000000000000000000000000000000000000000000' } },

  // EPK-28: Bildirim Kanalları
  { id: 'ntf-list', group: 'Bildirimler & İmzalı Mağaza', title: 'Bildirim Kanallarını Listele', method: 'GET', path: '/api/notifications/channels' },
  { id: 'ntf-add', group: 'Bildirimler & İmzalı Mağaza', title: 'Bildirim Kanalı Ekle', method: 'POST', path: '/api/notifications/channels',
    body: { kind: 'webhook', name: 'Ekip Uyarıları', quiet_start_hour: 23, quiet_end_hour: 7 } },
  { id: 'ntf-send', group: 'Bildirimler & İmzalı Mağaza', title: 'Test Bildirimi Gönder', method: 'POST', path: '/api/notifications/dispatch',
    body: { channel_id: 'ch_demo', title: 'Uyarı', message: 'Test bildirimi', hour_utc: 12 } },

  // EPK-29: İmzalı Mağaza
  { id: 'mkt-list', group: 'Bildirimler & İmzalı Mağaza', title: 'Mağaza Paketlerini Listele', method: 'GET', path: '/api/marketplace/items' },
  { id: 'mkt-pub', group: 'Bildirimler & İmzalı Mağaza', title: 'İmzalı Paket Yayınla', method: 'POST', path: '/api/marketplace/publish',
    body: { package_id: 'tpl-fastapi-pro', name: 'FastAPI Pro Şablonu', version: '1.0.0', kind: 'template', permissions: ['workspace.read'] } },
  { id: 'mkt-inst', group: 'Bildirimler & İmzalı Mağaza', title: 'Paketi İzin Onayıyla Kur', method: 'POST', path: '/api/marketplace/install',
    body: { package_id: 'tpl-fastapi-pro', approved_permissions: true } },
  { id: 'mkt-del', group: 'Bildirimler & İmzalı Mağaza', title: 'Mağaza Paketini Kaldır', method: 'DELETE', path: '/api/marketplace/items/{package_id}',
    params: { package_id: 'tpl-fastapi-pro' }, dangerous: true },

  // EPK-23: OpenAI Uyumlu /v1 API
  { id: 'oai-models', group: 'OpenAI Uyumlu (/v1) API', title: 'OpenAI /v1/models Listesi', method: 'GET', path: '/v1/models' },
  { id: 'oai-chat', group: 'OpenAI Uyumlu (/v1) API', title: 'OpenAI /v1/chat/completions', method: 'POST', path: '/v1/chat/completions',
    body: { model: 'dadp-local', messages: [{ role: 'user', content: '25 * 4' }] } },
  { id: 'oai-emb', group: 'OpenAI Uyumlu (/v1) API', title: 'OpenAI /v1/embeddings', method: 'POST', path: '/v1/embeddings',
    body: { model: 'dadp-embed-local', input: ['Yerel yapay zeka'] } },
];
