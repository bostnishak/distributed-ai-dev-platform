// Dashboard: live platform overview — agent load, recent events, perf stats (PB-51/52/53).
import { api, formatDateTime, formatSeconds, h, loading } from './util.js';

const AGENT_LABELS = {
  uye1: 'İshak', uye2: 'Duru', uye3: 'Furkan',
  uye4: 'Semih', uye5: 'Işıl', uye6: 'Berfin',
};
const MODEL_COLORS = {
  'qwen3.5:4b': '#6366f1', 'phi4-mini': '#0ea5e9', 'llama3.2:3b': '#8b5cf6',
  'gemma2:9b': '#db2777', 'qwen2.5:7b': '#d97706', 'qwen3.1:7b': '#16a34a',
};

const EVENT_ICONS = {
  task_assigned: '→',
  task_done: '✓',
  task_validation_failed: '✗',
  conflict_detected: '!',
};

function agentLabel(id) {
  const base = id ? id.replace(/-.*/, '') : '';
  return AGENT_LABELS[base] || id || '?';
}

function statCard(label, value, sub) {
  return h('div', { class: 'dash-stat' },
    h('div', { class: 'dash-stat-value' }, String(value)),
    h('div', { class: 'dash-stat-label' }, label),
    sub ? h('div', { class: 'muted small' }, sub) : null,
  );
}

function agentTable(agents) {
  if (!agents || !agents.length) return h('p', { class: 'muted' }, 'Kayıtlı ajan yok.');
  const rows = agents.map((a) => {
    const statusCls = a.online ? (a.heartbeat_status === 'busy' ? 'warn' : 'ok') : 'danger';
    const statusLabel = a.online ? (a.heartbeat_status === 'busy' ? 'Meşgul' : 'Çevrimiçi') : 'Çevrimdışı';
    const color = MODEL_COLORS[a.model] || '#555';
    return h('tr', null,
      h('td', null, h('strong', null, agentLabel(a.agent_id)), h('span', { class: 'muted small' }, ` (${a.agent_id})`)),
      h('td', null, h('span', { class: 'type-badge', style: { background: color } }, a.model)),
      h('td', null, h('span', { class: `badge ${statusCls}` }, statusLabel)),
      h('td', { class: 'muted small' }, a.last_seen_at ? formatDateTime(a.last_seen_at) : '—'),
    );
  });
  return h('table', { class: 'dash-table' },
    h('thead', null, h('tr', null,
      h('th', null, 'Üye'), h('th', null, 'Model'), h('th', null, 'Durum'), h('th', null, 'Son görülme'),
    )),
    h('tbody', null, ...rows),
  );
}

function eventList(events) {
  if (!events || !events.length) return h('p', { class: 'muted' }, 'Henüz olay yok.');
  const items = events.map((e) => {
    const icon = EVENT_ICONS[e.event_type] || '·';
    const agentName = e.agent_id ? agentLabel(e.agent_id) : '—';
    return h('div', { class: 'event-row' },
      h('span', { class: 'event-icon' }, icon),
      h('span', { class: 'event-type' }, e.event_type.replace(/_/g, ' ')),
      h('span', { class: 'muted small' }, ` · ${agentName} · ${formatDateTime(e.created_at)}`),
    );
  });
  return h('div', { class: 'event-list' }, ...items);
}

function perfSection(perf) {
  if (!perf || !perf.total_tasks) return h('p', { class: 'muted' }, 'Henüz tamamlanan görev yok.');
  const avgSec = perf.avg_ms / 1000;
  const cards = [
    statCard('Tamamlanan görev', perf.total_tasks),
    statCard('Ort. süre', formatSeconds(avgSec)),
    statCard('En hızlı', perf.min_ms != null ? formatSeconds(perf.min_ms / 1000) : '—'),
    statCard('En yavaş', perf.max_ms != null ? formatSeconds(perf.max_ms / 1000) : '—'),
  ];
  const byType = (perf.by_type || []).map((r) =>
    h('div', { class: 'perf-row' },
      h('span', { class: 'perf-type' }, r.type),
      h('span', { class: 'muted small' }, ` ${r.cnt} görev · ort. ${formatSeconds(r.avg_ms / 1000)}`),
    )
  );
  return h('div', null,
    h('div', { class: 'stat-grid' }, ...cards),
    byType.length ? h('div', { class: 'perf-breakdown' }, h('div', { class: 'section-label' }, 'Görev tipine göre'), ...byType) : null,
  );
}

function eloArenaTable(entries) {
  if (!entries || !entries.length) return h('p', { class: 'muted' }, 'Henüz ELO değerlendirme kaydı yok.');
  const rows = entries.map((e, idx) => h('tr', null,
    h('td', null, `#${idx + 1}`),
    h('td', null, h('strong', null, e.model)),
    h('td', null, h('span', { class: 'badge' }, `${e.elo} ELO`)),
    h('td', { class: 'muted small' }, e.discipline === 'overall' ? '12 Disiplin Ortalaması' : e.discipline),
  ));
  return h('table', { class: 'dash-table' },
    h('thead', null, h('tr', null,
      h('th', null, 'Sıra'), h('th', null, 'Yerel Model'), h('th', null, 'ELO Puanı'), h('th', null, 'Kapsam'),
    )),
    h('tbody', null, ...rows),
  );
}

export function renderDashboard(root, ctx) {
  root.replaceChildren(loading('Pano yükleniyor…'));

  async function load() {
    const [dash, agentsRaw, entStatus] = await Promise.all([
      api('/api/dashboard'),
      api('/api/agents'),
      api('/api/assistant/enterprise-status').catch(() => null),
    ]);

    const { agents: agentStats, projects: projStats, recent_events, perf } = dash;
    const agentDetails = agentsRaw.map((a) => ({
      ...a,
      online: a.online ?? false,
    }));
    const tele = entStatus?.telemetry || {};
    const llmops = entStatus?.llmops || {};
    const eloBoard = entStatus?.elo_leaderboard || [];

    const content = h('div', { class: 'dash-root' },
      h('h2', null, 'Pano'),

      h('div', { class: 'stat-grid' },
        statCard('Toplam ajan', agentStats.total),
        statCard('Çevrimiçi', agentStats.online, `${agentStats.busy} meşgul`),
        statCard('Toplam proje', projStats.total, `${projStats.active} aktif`),
        entStatus ? statCard('RAM / CPU', `%${tele.ram_percent ?? 0}`, `CPU %${tele.cpu_percent ?? 0}`) : null,
        entStatus ? statCard('AS9100 Denetim İzi', entStatus.audit_chain_valid ? 'Doğrulandı' : 'Hata', `DPO: ${llmops.total_pairs ?? 0} çift`) : null,
      ),

      h('h3', null, 'Ajanlar'),
      agentTable(agentDetails),

      h('h3', null, '12 Disiplinli Bilişsel Model ELO Arenası'),
      eloArenaTable(eloBoard),

      h('h3', null, 'Performans'),
      perfSection(perf),

      h('h3', null, 'Son Olaylar'),
      eventList(recent_events),
    );

    root.replaceChildren(content);
  }

  load().catch((e) => {
    root.replaceChildren(h('p', { class: 'badge danger' }, `Pano yüklenemedi: ${e.message}`));
  });

  // Auto-refresh every 10 s
  if (ctx?.poll) {
    ctx.poll(load, 10_000);
  }
}
