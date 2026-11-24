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

const DIMENSION_LABELS = {
  coding: 'Kodlama',
  reasoning: 'Muhakeme',
  context: 'Bağlam',
  structured_output: 'Yapılandırılmış Çıktı',
  speed: 'Hız',
};

function statusBadge(agent) {
  const online = agent.online;
  const busy = agent.heartbeat_status === 'busy';
  if (!online) return h('span', { class: 'badge offline agent-status-badge' }, 'Çevrimdışı');
  if (busy) return h('span', { class: 'badge busy agent-status-badge' }, 'Meşgul');
  return h('span', { class: 'badge ok agent-status-badge' }, 'Çevrimiçi');
}

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

function scoreBar(label, score) {
  const pct = Math.max(0, Math.min(100, score));
  return h('div', { class: 'score-bar-row' },
    h('span', { class: 'score-bar-label' }, label),
    h('div', { class: 'score-bar-container' },
      h('div', { class: 'score-bar-fill', style: { width: `${pct}%` } })),
    h('span', { class: 'score-bar-value' }, `${Math.round(pct)}`));
}

function scoreBars(scores) {
  if (!scores || Object.keys(scores).length === 0) return null;
  const dims = ['coding', 'reasoning', 'context', 'structured_output', 'speed'];
  return h('div', { class: 'score-bars', style: { marginTop: '10px' } },
    h('div', { class: 'score-bars-title' }, 'Yetenek Puanları'),
    ...dims.filter(d => scores[d] != null).map(d =>
      scoreBar(DIMENSION_LABELS[d] || d, scores[d].score)));
}

async function fetchScores(agentId) {
  try {
    const data = await api(`/api/agents/${agentId}/scores`);
    return data.latest || {};
  } catch {
    return {};
  }
}

async function agentCard(agent) {
  const latestScores = await fetchScores(agent.agent_id);

  // These elements are updated in-place by the live-poll loop
  const statusEl = statusBadge(agent);
  const lastSeenDd = h('dd', { class: 'agent-lastseen' }, formatDateTime(agent.last_seen_at));

  const staticRows = [
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
  ];

  const barsEl = scoreBars(latestScores);

  const evalBtn = h('button', {
    class: 'btn',
    type: 'button',
    disabled: !agent.online,
    title: agent.online ? 'Bu ajan için değerlendirme başlat' : 'Ajan çevrimdışı — değerlendirme için çevrimiçi olmalı',
    style: { marginTop: '8px', fontSize: '12px' },
    onclick: async (e) => {
      e.target.disabled = true;
      e.target.textContent = 'Değerlendiriliyor…';
      try {
        await api('/api/eval/start', { method: 'POST', body: JSON.stringify({ agent_id: agent.agent_id }), headers: { 'Content-Type': 'application/json' } });
        e.target.textContent = 'Değerlendirme başlatıldı';
      } catch (err) {
        e.target.textContent = 'Hata: ' + err.message;
        e.target.disabled = false;
      }
    },
  }, 'Yeniden Değerlendir');

  const dl = h('dl', { class: 'kv' },
    ...staticRows.map(([k, v]) => [h('dt', null, k), h('dd', null, v ?? '—')]),
    h('dt', null, 'Son görülme'), lastSeenDd,
  );

  return h('div', { class: 'agent-card', 'data-agent-id': agent.agent_id },
    h('div', { class: 'who' }, agent.member_name),
    h('div', { class: 'sub' }, h('span', { class: 'mono' }, agent.agent_id), ' · ', h('span', { class: 'mono' }, agent.model)),
    h('div', { style: { display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '4px' } },
      statusEl,
      modeBadge(agent)),
    h('div', { style: { marginTop: '8px' } },
      agent.capabilities.map((c) => h('span', { class: 'chip' }, CAPABILITY_LABELS[c] || c))),
    barsEl,
    dl,
    evalBtn);
}

function startAgentsLivePoll(root, ctx, liveIndicator) {
  if (!ctx) return;
  ctx.poll(async () => {
    const fresh = await api('/api/agents');
    for (const a of fresh) {
      const card = root.querySelector(`[data-agent-id="${a.agent_id}"]`);
      if (!card) continue;
      const badgeEl = card.querySelector('.agent-status-badge');
      if (badgeEl) {
        const online = a.online;
        const busy = a.heartbeat_status === 'busy';
        badgeEl.className = 'badge ' + (online ? (busy ? 'busy' : 'ok') : 'offline') + ' agent-status-badge';
        badgeEl.textContent = online ? (busy ? 'Meşgul' : 'Çevrimiçi') : 'Çevrimdışı';
      }
      const lastSeenEl = card.querySelector('.agent-lastseen');
      if (lastSeenEl) lastSeenEl.textContent = formatDateTime(a.last_seen_at);
    }
    liveIndicator.style.opacity = '0.4';
    setTimeout(() => { liveIndicator.style.opacity = '1'; }, 300);
  }, 10_000);
}

function buildMasterCard(status) {
  return h('div', { class: 'card' },
    h('h2', null, 'Master ajan'),
    h('dl', { class: 'kv' },
      h('dt', null, 'Model'), h('dd', null, h('span', { class: 'mono' }, status.model)),
      h('dt', null, 'Ollama'), h('dd', null, status.reachable
        ? h('span', { class: 'badge ok' }, 'erişilebilir') : h('span', { class: 'badge danger' }, 'erişilemiyor')),
      h('dt', null, 'Model yüklü'), h('dd', null, status.model_available
        ? h('span', { class: 'badge ok' }, 'evet') : h('span', { class: 'badge danger' }, 'hayır'))),
    h('p', { class: 'muted small', style: { marginBottom: 0 } },
      'Master, gereksinim dokümanlarını kendi bilgisayarındaki bu modelle analiz eder.'));
}

export async function renderAgents(root, ctx) {
  root.replaceChildren(h('div', { class: 'page-inner' }, loading()));
  let agents;
  let status;
  try {
    [agents, status] = await Promise.all([api('/api/agents'), api('/api/master/status')]);
  } catch (err) {
    if (ctx && !ctx.isCurrent()) return;
    root.replaceChildren(h('div', { class: 'page-inner' }, h('div', { class: 'card error' }, err.message)));
    return;
  }
  if (ctx && !ctx.isCurrent()) return;

  const hasOnlineAgent = agents.some((a) => a.online);
  const evalAllBtn = h('button', {
    class: 'btn btn-primary',
    type: 'button',
    disabled: !hasOnlineAgent,
    title: hasOnlineAgent ? 'Çevrimiçi tüm ajanları değerlendir' : 'Çevrimiçi ajan bulunmadığı için değerlendirme devre dışı',
    onclick: async (e) => {
      e.target.disabled = true;
      e.target.textContent = 'Değerlendiriliyor…';
      try {
        const result = await api('/api/eval/start', { method: 'POST', body: JSON.stringify({}), headers: { 'Content-Type': 'application/json' } });
        e.target.textContent = `${result.tasks_created} görev oluşturuldu`;
      } catch (err) {
        e.target.textContent = 'Hata: ' + err.message;
        e.target.disabled = false;
      }
    },
  }, 'Tümünü Değerlendir');

  const liveIndicator = h('span', { class: 'badge ok', style: { fontSize: '11px', padding: '2px 7px', alignSelf: 'center' } }, '● Canlı');
  const head = h('div', { class: 'page-head' },
    h('div', null,
      h('h1', { class: 'page-title' }, 'Ajanlar'),
      h('p', { class: 'page-lead' }, 'Her ekip üyesinin bilgisayarında çalışan ajan, açılışta master\'a kaydolur ve yeteneklerini bildirir.')),
    h('div', { style: { display: 'flex', gap: '8px', alignItems: 'center' } },
      evalAllBtn, h('button', { class: 'btn', onclick: () => renderAgents(root, ctx) }, '↻ Yenile'), liveIndicator));

  const cardContainer = h('div', { class: 'agent-grid' });
  const listSection = agents.length ? cardContainer : h('div', { class: 'card' },
    h('p', { style: { marginTop: 0 } }, 'Henüz kayıtlı ajan yok.'),
    h('ul', { class: 'plain' },
      h('li', null, 'Staging: ', h('code', null, 'docker compose --profile staging up -d')),
      h('li', null, 'Üye bilgisayarları: ', h('code', null, 'agent-node/README.md'))));

  root.replaceChildren(h('div', { class: 'page-inner' }, head, buildMasterCard(status),
    h('h2', { style: { fontSize: '16px', margin: '6px 0 12px' } }, `Kayıtlı ajanlar (${agents.length})`), listSection));
  for (const agent of agents) {
    const card = await agentCard(agent);
    if (ctx && !ctx.isCurrent()) return;
    cardContainer.appendChild(card);
  }
  if (ctx && !ctx.isCurrent()) return;
  startAgentsLivePoll(root, ctx, liveIndicator);
}
