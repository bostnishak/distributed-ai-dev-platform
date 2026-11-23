// UX-02 Modular Split: Project DAG visualizer, task list, specification & source document renderers.
import { formatNumber, h, svg } from './util.js';

export function scrollToTask(key) {
  const el = document.getElementById(`task-${key}`);
  if (!el) return;
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  el.classList.remove('flash');
  void el.offsetWidth;
  el.classList.add('flash');
}

export function renderDag(tasks, TASK_TYPES) {
  const nodeW = 184;
  const nodeH = 48;
  const colGap = 54;
  const rowGap = 14;
  const pad = 10;
  const stages = [...new Set(tasks.map((t) => t.stage))].sort((a, b) => a - b);
  const columns = stages.map((s) => tasks.filter((t) => t.stage === s));
  const maxRows = Math.max(...columns.map((c) => c.length));
  const width = pad * 2 + stages.length * nodeW + (stages.length - 1) * colGap;
  const height = pad * 2 + maxRows * nodeH + (maxRows - 1) * rowGap;

  const pos = {};
  columns.forEach((column, ci) => {
    const offset = ((maxRows - column.length) * (nodeH + rowGap)) / 2;
    column.forEach((task, ri) => {
      pos[task.key] = { x: pad + ci * (nodeW + colGap), y: pad + offset + ri * (nodeH + rowGap) };
    });
  });

  const edges = [];
  for (const task of tasks) {
    for (const dep of task.depends_on) {
      const a = pos[dep];
      const b = pos[task.key];
      const x1 = a.x + nodeW;
      const y1 = a.y + nodeH / 2;
      const x2 = b.x;
      const y2 = b.y + nodeH / 2;
      edges.push(svg('path', {
        d: `M${x1},${y1} C${x1 + colGap / 2},${y1} ${x2 - colGap / 2},${y2} ${x2 - 4},${y2}`,
        fill: 'none', stroke: '#c3c3cf', 'stroke-width': 1.4, 'marker-end': 'url(#arrow)',
      }));
    }
  }

  const nodes = tasks.map((task) => {
    const { x, y } = pos[task.key];
    const color = (TASK_TYPES[task.type] || {}).color || '#555';
    const title = task.title.length > 25 ? `${task.title.slice(0, 24)}…` : task.title;
    return svg('g', { class: 'dag-node', onclick: () => scrollToTask(task.key) },
      svg('title', null, `${task.key} · ${task.title}`),
      svg('rect', {
        class: 'box', x, y, width: nodeW, height: nodeH, rx: 9,
        fill: task.status === 'done' ? '#eefaf2' : '#ffffff', stroke: color, 'stroke-width': 1.6,
      }),
      svg('rect', { x, y, width: 6, height: nodeH, rx: 3, fill: color }),
      svg('text', { x: x + 14, y: y + 19, 'font-size': 11.5, 'font-weight': 700, fill: '#555', 'font-family': 'Consolas, monospace' },
        task.status === 'done' ? `${task.key} ✓` : task.key),
      svg('text', { x: x + 14, y: y + 36, 'font-size': 12.5, fill: '#1a1a1a' }, title));
  });

  return h('div', { class: 'dag-wrap' }, svg('svg', { width, height, viewBox: `0 0 ${width} ${height}`, role: 'img', 'aria-label': 'Görev bağımlılık grafiği' },
    svg('defs', null, svg('marker', { id: 'arrow', viewBox: '0 0 10 10', refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: 'auto-start-reverse' },
      svg('path', { d: 'M 0 0 L 10 5 L 0 10 z', fill: '#b0b0bd' }))),
    edges, nodes));
}

function taskDetails(task) {
  const d = task.details || {};
  const items = [];
  for (const e of d.entities || []) {
    items.push(typeof e === 'string' ? `Varlık: ${e}` : `Varlık: ${e.name} (${(e.fields || []).map((f) => f.name).join(', ') || 'alan yok'})`);
  }
  for (const ep of d.endpoints || []) items.push(`${ep.method} ${ep.path} — ${ep.description}`);
  for (const p of d.pages || []) items.push(`Sayfa: ${p.name} — ${p.description}`);
  for (const a of d.actors || []) items.push(`Aktör: ${a}`);
  if (items.length === 0) return null;
  return h('details', null, h('summary', null, `Kapsam (${items.length})`), h('ul', null, items.map((i) => h('li', null, i))));
}

function taskOutput(task, AGENT_INFO) {
  if (task.status !== 'done' || !task.result) return null;
  const preview = task.result.length > 400 ? `${task.result.slice(0, 400)}…` : task.result;
  const info = task.performed_by && AGENT_INFO[task.performed_by.replace(/-.*/, '')];
  const attribution = info
    ? h('div', { class: 'task-output-attribution' },
      h('span', { class: 'muted small' }, 'Üreten:'),
      h('span', { class: 'badge ok', style: { fontSize: '11px' } }, info.name),
      h('span', { class: 'badge', style: { fontSize: '11px' } }, info.model),
      task.tokens_per_second ? h('span', { class: 'muted small' }, `${Math.round(task.tokens_per_second)} tok/s`) : null)
    : null;
  return h('details', { class: 'task-output' },
    h('summary', null, `Çıktı (${task.result.length} karakter)`),
    attribution,
    h('pre', { class: 'task-result-pre' }, preview));
}

export function renderTaskList(tasks, helpers) {
  const { TASK_TYPES, TASK_STATUS, AGENT_INFO, typeBadge, statusBadge, agentLabel } = helpers;
  const stages = [...new Set(tasks.map((t) => t.stage))].sort((a, b) => a - b);
  return stages.map((stage) => [
    h('div', { class: 'stage-title' }, `Aşama ${stage}`),
    tasks.filter((t) => t.stage === stage).map((task) => {
      const inProgress = task.assigned_to && task.status === 'planned';
      return h('div', {
        class: `task${inProgress ? ' task-inprogress' : ''}`,
        id: `task-${task.key}`,
        style: { borderLeftColor: (TASK_TYPES[task.type] || {}).color || '#555' },
      },
      h('div', { class: 'task-head' },
        h('span', { class: 'task-key' }, task.key),
        h('span', { class: 'task-title' }, task.title),
        typeBadge(task.type),
        inProgress ? h('span', { class: 'badge warn' }, `⟳ ${agentLabel(task.assigned_to)} çalışıyor`) : statusBadge(TASK_STATUS, task.status),
        task.performed_by === 'master' ? h('span', { class: 'badge' }, 'master ajan') : null,
        task.status === 'done' && task.performed_by && task.performed_by !== 'master' ? h('span', { class: 'badge' }, agentLabel(task.performed_by)) : null,
        task.validation_status === 'failed' ? h('span', { class: 'badge danger', title: task.validation_message }, '! doğrulama hatası') : null,
        task.attempt > 0 ? h('span', { class: 'badge warn', title: `${task.attempt}. deneme` }, `↻${task.attempt}`) : null,
        task.has_conflict ? h('span', { class: 'badge danger', title: 'Çıktı dosyasında çakışma tespit edildi' }, '! çakışma') : null),
      h('div', { class: 'task-desc' }, task.description),
      task.depends_on.length
        ? h('div', { class: 'task-deps' }, 'Bağımlılık: ', task.depends_on.map((k) => h('span', { class: 'chip chip-link', onclick: () => scrollToTask(k) }, k)))
        : h('div', { class: 'task-deps' }, 'Bağımlılık yok'),
      taskDetails(task),
      taskOutput(task, AGENT_INFO));
    }),
  ]);
}

export function renderSpec(spec) {
  const parts = [];
  if (spec.entities.length) {
    parts.push(h('h3', null, `Varlıklar (${spec.entities.length})`), h('div', { class: 'table-wrap' },
      h('table', { class: 'data-table' },
        h('thead', null, h('tr', null, h('th', null, 'Varlık'), h('th', null, 'Açıklama'), h('th', null, 'Alanlar'))),
        h('tbody', null, spec.entities.map((e) => h('tr', null,
          h('td', null, h('strong', null, e.name)),
          h('td', null, e.description),
          h('td', null, e.fields.map((f) => h('span', { class: 'chip' }, `${f.name}: ${f.type}${f.required ? '' : ' (ops.)'}`)))))))));
  }
  if (spec.api_endpoints.length) {
    parts.push(h('h3', null, `API uç noktaları (${spec.api_endpoints.length})`), h('div', { class: 'table-wrap' },
      h('table', { class: 'data-table' },
        h('thead', null, h('tr', null, h('th', null, 'Metot'), h('th', null, 'Yol'), h('th', null, 'Açıklama'), h('th', null, 'Varlık'))),
        h('tbody', null, spec.api_endpoints.map((ep) => h('tr', null,
          h('td', null, h('span', { class: 'method' }, ep.method)),
          h('td', null, h('code', null, ep.path)),
          h('td', null, ep.description),
          h('td', null, ep.entity || '—')))))));
  }
  if (spec.pages.length) {
    parts.push(h('h3', null, `Sayfalar (${spec.pages.length})`), h('ul', { class: 'plain' },
      spec.pages.map((p) => h('li', null, h('strong', null, p.name), ` — ${p.description}`,
        p.entities.length ? h('span', { class: 'muted' }, ` (${p.entities.join(', ')})`) : null))));
  }
  if (spec.non_functional.length) {
    parts.push(h('h3', null, `Fonksiyonel olmayan gereksinimler (${spec.non_functional.length})`),
      h('ul', { class: 'plain' }, spec.non_functional.map((n) => h('li', null, n))));
  }
  if (parts.length === 0) parts.push(h('p', { class: 'muted' }, 'Spesifikasyon boş.'));
  return h('div', { class: 'card' }, h('h2', null, 'Spesifikasyon'), parts);
}

export function sourceDocument(project) {
  return h('details', { class: 'card source' },
    h('summary', null, `Kaynak doküman (${formatNumber(project.document.length)} karakter)`),
    h('pre', null, project.document));
}
