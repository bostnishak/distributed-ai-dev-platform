// "Yeni Proje" and "Projeler" views: submit a requirements document and inspect the
// specification and task graph the master agent produced.
import { api, formatDateTime, formatNumber, formatSeconds, h, isDesktop, loading, svg } from './util.js';

export const TASK_TYPES = {
  requirements: { label: 'Gereksinim analizi', color: '#6366f1' },
  database: { label: 'Veritabanı', color: '#0ea5e9' },
  backend: { label: 'Backend', color: '#8b5cf6' },
  frontend: { label: 'Frontend', color: '#db2777' },
  testing: { label: 'Test', color: '#d97706' },
  review: { label: 'Kod incelemesi', color: '#0d9488' },
  integration: { label: 'Entegrasyon', color: '#16a34a' },
  documentation: { label: 'Dokümantasyon', color: '#64748b' },
};

const PROJECT_STATUS = {
  analyzing: { label: 'Analiz ediliyor', cls: 'warn' },
  decomposed: { label: 'Görevlere ayrıldı', cls: 'ok' },
  failed: { label: 'Başarısız', cls: 'danger' },
};

const TASK_STATUS = {
  done: { label: 'Tamamlandı', cls: 'ok' },
  planned: { label: 'Planlandı', cls: 'gray' },
};

function statusBadge(map, status) {
  const info = map[status] || { label: status, cls: 'gray' };
  return h('span', { class: `badge ${info.cls}` }, info.label);
}

function typeBadge(type) {
  const info = TASK_TYPES[type] || { label: type, color: '#555' };
  return h('span', { class: 'type-badge', style: { background: info.color } }, info.label);
}

function masterStatusLine(status) {
  if (!status.reachable) {
    return h('span', { class: 'badge danger' }, `Master modeline ulaşılamıyor (${status.model}) — Ollama çalışıyor mu?`);
  }
  if (!status.model_available) {
    return h('span', { class: 'badge danger' }, `${status.model} modeli yüklü değil`);
  }
  return h('span', { class: 'badge ok' }, `Master modeli hazır: ${status.model}`);
}

// --- New project ---------------------------------------------------------------------------

export function renderNewProject(root) {
  let mode = 'text';
  let file = null;

  const statusSlot = h('div', { class: 'small' }, loading('Master durumu kontrol ediliyor…'));
  api('/api/master/status')
    .then((status) => statusSlot.replaceChildren(masterStatusLine(status)))
    .catch(() => statusSlot.replaceChildren(h('span', { class: 'badge danger' }, 'Master durumu alınamadı')));

  const nameInput = h('input', {
    type: 'text', id: 'projectName', maxlength: 120, placeholder: 'ör. Kütüphane Yönetim Sistemi', autocomplete: 'off',
  });
  const textArea = h('textarea', { id: 'projectText', placeholder: 'Gereksinim dokümanını buraya yapıştırın…' });
  const counter = h('span', { class: 'muted small' }, '0 karakter');
  textArea.addEventListener('input', () => {
    counter.textContent = `${formatNumber(textArea.value.length)} karakter`;
  });

  const fileInput = h('input', { type: 'file', accept: '.pdf,.docx,.txt,.md', hidden: true });
  const fileNameEl = h('div', { class: 'file-name' });
  const dropzone = h('div', { class: 'dropzone', tabindex: 0, role: 'button' },
    h('div', null, 'Dosya seçmek için tıklayın veya buraya sürükleyin'),
    h('div', { class: 'muted small' }, 'PDF, DOCX, TXT veya MD · en fazla 5 MB'),
    fileNameEl);
  const pickFile = (f) => {
    file = f || null;
    fileNameEl.textContent = file ? `📎 ${file.name}` : '';
  };
  dropzone.addEventListener('click', () => fileInput.click());
  dropzone.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') fileInput.click(); });
  dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('drag'); });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag'));
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('drag');
    pickFile(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener('change', () => pickFile(fileInput.files[0]));

  const textPane = h('div', null, textArea, h('div', { class: 'form-row', style: { marginTop: '6px' } }, counter));
  const filePane = h('div', { hidden: true }, dropzone, fileInput);
  const segText = h('button', { type: 'button', class: 'seg-btn active' }, 'Metin yapıştır');
  const segFile = h('button', { type: 'button', class: 'seg-btn' }, 'Dosya yükle');
  const setMode = (next) => {
    mode = next;
    segText.classList.toggle('active', mode === 'text');
    segFile.classList.toggle('active', mode === 'file');
    textPane.hidden = mode !== 'text';
    filePane.hidden = mode !== 'file';
  };
  segText.addEventListener('click', () => setMode('text'));
  segFile.addEventListener('click', () => setMode('file'));

  const errorBox = h('div', { class: 'form-error', hidden: true });
  const submit = h('button', { type: 'submit', class: 'btn btn-primary' }, 'Analiz et');
  const showError = (message) => {
    errorBox.textContent = message;
    errorBox.hidden = false;
  };

  const form = h('form', { class: 'card form' },
    h('div', { class: 'field' }, h('label', { for: 'projectName' }, 'Proje adı'), nameInput),
    h('div', { class: 'field' },
      h('label', null, 'Gereksinim dokümanı'),
      h('div', { class: 'seg' }, segText, segFile),
      textPane, filePane),
    errorBox,
    h('div', { class: 'form-row' }, statusSlot, submit));

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorBox.hidden = true;
    const name = nameInput.value.trim();
    if (!name) return showError('Proje adı girin.');
    const body = new FormData();
    body.append('name', name);
    if (mode === 'text') {
      if (!textArea.value.trim()) return showError('Doküman metni boş.');
      body.append('text', textArea.value);
    } else {
      if (!file) return showError('Bir dosya seçin.');
      body.append('file', file);
    }
    submit.disabled = true;
    submit.textContent = 'Gönderiliyor…';
    try {
      const created = await api('/api/projects', { method: 'POST', body });
      location.hash = `#/projects/${created.id}`;
    } catch (err) {
      showError(err.message);
      submit.disabled = false;
      submit.textContent = 'Analiz et';
    }
  });

  root.replaceChildren(h('div', { class: 'page-inner' },
    h('div', { class: 'page-head' }, h('div', null,
      h('h1', { class: 'page-title' }, 'Yeni proje'),
      h('p', { class: 'page-lead' },
        'Yazılım gereksinim dokümanını yapıştırın veya yükleyin. Master ajan dokümanı analiz eder, ' +
        'yapılandırılmış bir spesifikasyon çıkarır ve işi bağımlılıklarıyla birlikte görevlere ayırır.'))),
    h('div', { class: 'card note' },
      'Sprint 1: görevler şimdilik yalnızca planlanır. Görevlerin ajanların ölçülen yeteneklerine göre ' +
      'dağıtılması Sprint 2\'de, ajanların görevleri yürütmesi Sprint 3\'te eklenecek.'),
    form));
  if (isDesktop()) nameInput.focus();
}

// --- Project list --------------------------------------------------------------------------

export async function renderProjects(root) {
  root.replaceChildren(h('div', { class: 'page-inner' }, loading()));
  let projects;
  try {
    projects = await api('/api/projects');
  } catch (err) {
    root.replaceChildren(h('div', { class: 'page-inner' }, h('div', { class: 'card error' }, err.message)));
    return;
  }

  const head = h('div', { class: 'page-head' },
    h('div', null,
      h('h1', { class: 'page-title' }, 'Projeler'),
      h('p', { class: 'page-lead' }, 'Master ajanın analiz ettiği gereksinim dokümanları ve çıkardığı görev planları.')),
    h('a', { class: 'btn btn-primary', href: '#/new' }, '＋ Yeni proje'));

  if (projects.length === 0) {
    root.replaceChildren(h('div', { class: 'page-inner' }, head,
      h('div', { class: 'card' }, 'Henüz proje yok. ', h('a', { href: '#/new' }, 'İlk gereksinim dokümanını yükleyin.'))));
    return;
  }

  const rows = projects.map((p) => h('tr', { class: 'clickable', onclick: () => { location.hash = `#/projects/${p.id}`; } },
    h('td', null, h('strong', null, p.name), p.source_filename ? h('div', { class: 'muted small' }, p.source_filename) : null),
    h('td', null, statusBadge(PROJECT_STATUS, p.status)),
    h('td', null, p.status === 'decomposed' ? String(p.task_count) : '—'),
    h('td', null, formatSeconds(p.analysis_seconds)),
    h('td', null, formatDateTime(p.created_at))));

  root.replaceChildren(h('div', { class: 'page-inner' }, head,
    h('div', { class: 'card table-wrap' }, h('table', { class: 'data-table' },
      h('thead', null, h('tr', null, h('th', null, 'Proje'), h('th', null, 'Durum'), h('th', null, 'Görev'),
        h('th', null, 'Analiz süresi'), h('th', null, 'Oluşturulma'))),
      h('tbody', null, rows)))));
}

// --- Project detail ------------------------------------------------------------------------

function scrollToTask(key) {
  const el = document.getElementById(`task-${key}`);
  if (!el) return;
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  el.classList.remove('flash');
  void el.offsetWidth; // restart the highlight animation
  el.classList.add('flash');
}

function renderDag(tasks) {
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

function renderTaskList(tasks) {
  const stages = [...new Set(tasks.map((t) => t.stage))].sort((a, b) => a - b);
  return stages.map((stage) => [
    h('div', { class: 'stage-title' }, `Aşama ${stage}`),
    tasks.filter((t) => t.stage === stage).map((task) => h('div', {
      class: 'task', id: `task-${task.key}`, style: { borderLeftColor: (TASK_TYPES[task.type] || {}).color || '#555' },
    },
      h('div', { class: 'task-head' },
        h('span', { class: 'task-key' }, task.key),
        h('span', { class: 'task-title' }, task.title),
        typeBadge(task.type),
        statusBadge(TASK_STATUS, task.status),
        task.performed_by === 'master' ? h('span', { class: 'badge' }, 'master ajan yaptı') : null),
      h('div', { class: 'task-desc' }, task.description),
      task.depends_on.length
        ? h('div', { class: 'task-deps' }, 'Bağımlı olduğu görevler: ',
          task.depends_on.map((k) => h('span', { class: 'chip chip-link', onclick: () => scrollToTask(k) }, k)))
        : h('div', { class: 'task-deps' }, 'Bağımlılık yok (başlangıç görevi)'),
      taskDetails(task))),
  ]);
}

function renderSpec(spec) {
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

function sourceDocument(project) {
  return h('details', { class: 'card source' },
    h('summary', null, `Kaynak doküman (${formatNumber(project.document.length)} karakter)`),
    h('pre', null, project.document));
}

function elapsedSince(iso) {
  return (Date.now() - Date.parse(iso)) / 1000;
}

export async function renderProjectDetail(root, id, ctx) {
  root.replaceChildren(h('div', { class: 'page-inner' }, loading()));
  let project;
  try {
    project = await api(`/api/projects/${id}`);
  } catch (err) {
    root.replaceChildren(h('div', { class: 'page-inner' },
      h('a', { class: 'back-link', href: '#/projects' }, '← Projeler'),
      h('div', { class: 'card error' }, err.message)));
    return;
  }
  if (!ctx.isCurrent()) return;

  const draw = (p) => {
    let confirmDelete = false;
    const actions = h('div', { class: 'card-actions' });

    const drawActions = () => {
      const reanalyze = h('button', { class: 'btn', onclick: async () => {
        reanalyze.disabled = true;
        try {
          await api(`/api/projects/${p.id}/reanalyze`, { method: 'POST' });
          renderProjectDetail(root, id, ctx);
        } catch (err) {
          reanalyze.disabled = false;
          alertBox.replaceChildren(h('div', { class: 'card error' }, err.message));
        }
      } }, '↻ Yeniden analiz et');
      const remove = confirmDelete
        ? [h('span', { class: 'small', style: { alignSelf: 'center' } }, 'Proje silinsin mi?'),
          h('button', { class: 'btn btn-danger-solid', onclick: async () => {
            try {
              await api(`/api/projects/${p.id}`, { method: 'DELETE' });
              location.hash = '#/projects';
            } catch (err) {
              alertBox.replaceChildren(h('div', { class: 'card error' }, err.message));
            }
          } }, 'Evet, sil'),
          h('button', { class: 'btn', onclick: () => { confirmDelete = false; drawActions(); } }, 'Vazgeç')]
        : h('button', { class: 'btn btn-danger', onclick: () => { confirmDelete = true; drawActions(); } }, 'Sil');
      actions.replaceChildren(...(p.status === 'analyzing' ? [] : [reanalyze, remove].flat()));
    };
    const alertBox = h('div');
    drawActions();

    const meta = [
      p.source_filename ? `Kaynak: ${p.source_filename}` : 'Kaynak: yapıştırılan metin',
      `Oluşturulma: ${formatDateTime(p.created_at)}`,
    ];
    if (p.status === 'decomposed') {
      meta.push(`Analiz: ${p.analysis_model}, ${formatSeconds(p.analysis_seconds)}` +
        (p.chunk_count > 1 ? `, ${p.chunk_count} parça` : ''));
    }

    const head = h('div', null,
      h('a', { class: 'back-link', href: '#/projects' }, '← Projeler'),
      h('div', { class: 'page-head' },
        h('div', null,
          h('h1', { class: 'page-title' }, p.name, ' ', statusBadge(PROJECT_STATUS, p.status)),
          h('p', { class: 'page-lead' }, meta.join(' · '))),
        actions),
      alertBox);

    const body = [];
    if (p.status === 'analyzing') {
      const elapsed = h('span', null, formatSeconds(elapsedSince(p.updated_at)));
      body.push(h('div', { class: 'card' },
        h('div', { class: 'loading', style: { padding: '6px 0' } }, h('span', { class: 'spinner' }),
          h('span', null, 'Master ajan dokümanı analiz ediyor… geçen süre: ', elapsed)),
        h('p', { class: 'muted small' },
          'Yerel model CPU üzerinde çalıştığı için bu işlem birkaç dakika sürebilir. Sayfa kendini yeniler.')));
      ctx.poll(async () => {
        elapsed.textContent = formatSeconds(elapsedSince(p.updated_at));
        const latest = await api(`/api/projects/${id}`);
        if (latest.status !== 'analyzing') {
          ctx.stopPoll();
          draw(latest);
        }
      }, 2500);
    } else if (p.status === 'failed') {
      body.push(h('div', { class: 'card error' }, h('strong', null, 'Analiz başarısız oldu. '), p.error || ''));
    } else {
      const spec = p.spec;
      body.push(h('div', { class: 'card' },
        h('h2', null, spec.project_name || p.name),
        spec.summary ? h('p', { class: 'page-lead', style: { color: '#333' } }, spec.summary) : null,
        spec.actors.length ? h('div', { style: { marginTop: '8px' } }, h('span', { class: 'muted small' }, 'Aktörler: '),
          spec.actors.map((a) => h('span', { class: 'chip' }, a))) : null,
        h('div', { class: 'stats' },
          [['Varlık', spec.entities.length], ['API ucu', spec.api_endpoints.length], ['Sayfa', spec.pages.length],
            ['Görev', p.tasks.length], ['Açık soru', spec.open_questions.length]]
            .map(([label, n]) => h('div', { class: 'stat' }, h('div', { class: 'num' }, String(n)), h('div', { class: 'lbl' }, label))))));

      body.push(h('div', { class: spec.open_questions.length ? 'card warn' : 'card' },
        h('h2', null, `Açık sorular (${spec.open_questions.length})`),
        h('p', { class: 'muted small', style: { marginTop: 0 } },
          'Master ajan, dokümanda belirsiz veya eksik bulduğu noktaları tahminle doldurmak yerine buraya yazar. ' +
          'Bunların Product Owner ile netleştirilmesi gerekir.'),
        spec.open_questions.length
          ? h('ul', { class: 'plain' }, spec.open_questions.map((q) => h('li', null, q)))
          : h('p', { class: 'small' }, 'Model belirsiz bir nokta bildirmedi.')));

      const legendTypes = [...new Set(p.tasks.map((t) => t.type))];
      body.push(h('div', { class: 'card' },
        h('h2', null, `Görev planı (${p.tasks.length} görev)`),
        h('p', { class: 'muted small', style: { marginTop: 0 } },
          'Oklar bağımlılıkları gösterir: bir görev, ok aldığı görevler bitmeden başlayamaz. ' +
          'Aynı sütundaki görevler paralel yürütülebilir. Bir kutuya tıklayınca görevin ayrıntısına gidilir.'),
        h('div', { class: 'legend' }, legendTypes.map(typeBadge)),
        renderDag(p.tasks),
        renderTaskList(p.tasks)));

      body.push(renderSpec(spec));
    }
    body.push(sourceDocument(p));
    root.replaceChildren(h('div', { class: 'page-inner' }, head, body));
  };

  draw(project);
}
