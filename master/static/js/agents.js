// "Ajanlar" view: agents that registered with the master and what their models can do.
import { api, formatDateTime, formatNumber, h, loading } from './util.js';

const CAPABILITY_LABELS = {
  completion: 'Metin üretimi',
  vision: 'Görsel',
  thinking: 'Düşünme',
  tools: 'Araç kullanımı',
  audio: 'Ses',
  insert: 'Kod ekleme',
  embedding: 'Embedding',
};

function modeBadge(agent) {
  return agent.mode === 'staging'
    ? h('span', { class: 'badge warn', title: 'Üyenin bilgisayarı bağlanana kadar master bilgisayarında çalışan kopya' },
      "Staging · İshak'ın bilgisayarı")
    : h('span', { class: 'badge ok' }, 'Üyenin bilgisayarı');
}

function runtimeLabel(agent) {
  if (agent.runtime === 'docker') return 'Docker konteyneri (RAM, CPU ve işletim sistemi Docker sanal makinesine aittir)';
  if (agent.runtime === 'native') return 'Doğrudan bilgisayarda';
  return null;
}

function agentCard(agent) {
  const rows = [
    ['Çalışma ortamı', runtimeLabel(agent)],
    ['Model ailesi', agent.model_family],
    ['Parametre', agent.parameter_size],
    ['Quantization', agent.quantization],
    ['Bağlam penceresi', agent.context_length ? `${formatNumber(agent.context_length)} token` : null],
    ['RAM', agent.ram_gb != null ? `${agent.ram_gb} GB` : null],
    ['CPU', agent.cpu_count ? `${agent.cpu_count} çekirdek` : null],
    ['İşletim sistemi', agent.os],
    ['Bilgisayar adı', agent.hostname],
    ['İlk kayıt', formatDateTime(agent.registered_at)],
    ['Son kayıt', formatDateTime(agent.last_seen_at)],
  ];
  return h('div', { class: 'agent-card' },
    h('div', { class: 'who' }, agent.member_name),
    h('div', { class: 'sub' }, h('span', { class: 'mono' }, agent.agent_id), ' · ', h('span', { class: 'mono' }, agent.model)),
    h('div', null, modeBadge(agent)),
    h('div', { style: { marginTop: '8px' } },
      agent.capabilities.map((c) => h('span', { class: 'chip' }, CAPABILITY_LABELS[c] || c))),
    h('dl', { class: 'kv' }, rows.map(([k, v]) => [h('dt', null, k), h('dd', null, v ?? '—')])));
}

export async function renderAgents(root) {
  root.replaceChildren(h('div', { class: 'page-inner' }, loading()));
  let agents;
  let status;
  try {
    [agents, status] = await Promise.all([api('/api/agents'), api('/api/master/status')]);
  } catch (err) {
    root.replaceChildren(h('div', { class: 'page-inner' }, h('div', { class: 'card error' }, err.message)));
    return;
  }

  const head = h('div', { class: 'page-head' },
    h('div', null,
      h('h1', { class: 'page-title' }, 'Ajanlar'),
      h('p', { class: 'page-lead' },
        'Her ekip üyesinin bilgisayarında çalışan ajan, açılışta master\'a kaydolur ve modelinin ' +
        'yeteneklerini (bağlam penceresi, görsel/düşünme desteği) ve donanımını bildirir.')),
    h('button', { class: 'btn', onclick: () => renderAgents(root) }, '↻ Yenile'));

  const masterCard = h('div', { class: 'card' },
    h('h2', null, 'Master ajan'),
    h('dl', { class: 'kv' },
      h('dt', null, 'Model'), h('dd', null, h('span', { class: 'mono' }, status.model)),
      h('dt', null, 'Ollama'), h('dd', null, status.reachable
        ? h('span', { class: 'badge ok' }, 'erişilebilir') : h('span', { class: 'badge danger' }, 'erişilemiyor')),
      h('dt', null, 'Model yüklü'), h('dd', null, status.model_available
        ? h('span', { class: 'badge ok' }, 'evet') : h('span', { class: 'badge danger' }, 'hayır'))),
    h('p', { class: 'muted small', style: { marginBottom: 0 } },
      'Master, gereksinim dokümanlarını kendi bilgisayarındaki bu modelle analiz eder.'));

  const note = h('div', { class: 'card note' },
    'Canlı çevrimiçi/çevrimdışı durumu (heartbeat) Sprint 2\'de eklenecek. Şimdilik "Son kayıt", ajanın ' +
    'master\'a en son ne zaman kaydolduğunu gösterir.');

  const list = agents.length
    ? h('div', { class: 'agent-grid' }, agents.map(agentCard))
    : h('div', { class: 'card' },
      h('p', { style: { marginTop: 0 } }, 'Henüz kayıtlı ajan yok.'),
      h('ul', { class: 'plain' },
        h('li', null, 'Staging (6 ajan master bilgisayarında): ', h('code', null, 'docker compose --profile staging up -d')),
        h('li', null, 'Üyeler kendi bilgisayarında: ', h('code', null, 'agent-node/README.md'), ' adımları')));

  root.replaceChildren(h('div', { class: 'page-inner' }, head, masterCard, note,
    h('h2', { style: { fontSize: '16px', margin: '6px 0 12px' } }, `Kayıtlı ajanlar (${agents.length})`), list));
}
