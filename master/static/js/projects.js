// "Yeni Proje" and "Projeler" views: submit a requirements document and inspect the
// specification and task graph the master agent produced.
import { renderDag as _renderDag, renderSpec, renderTaskList as _renderTaskList, sourceDocument } from './projects_dag.js';
import { api, formatDateTime, formatNumber, formatSeconds, h, isDesktop, loading } from './util.js';

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
  blocked: { label: 'Bekliyor', cls: 'warn' },
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

// Friendly short name for an agent id ("uye1" → "İshak", otherwise the raw id).
function agentLabel(agentId) {
  const MAP = {
    uye1: 'İshak', uye2: 'Duru', uye3: 'Furkan',
    uye4: 'Semih', uye5: 'Işıl', uye6: 'Berfin',
  };
  const base = agentId ? agentId.replace(/-.*/, '') : '';
  return MAP[base] || agentId || '?';
}

const AGENT_INFO = {
  uye1: { name: 'İshak Bostan', model: 'qwen3.5:4b' },
  uye2: { name: 'Zeynep Duru Küçük', model: 'phi4-mini' },
  uye3: { name: 'Furkan Kaan Özbeyli', model: 'llama3.2:3b' },
  uye4: { name: 'Semih Sarıca', model: 'qwen2.5-coder:7b' },
  uye5: { name: 'Işıl Karademir', model: 'qwen3.5:9b' },
  uye6: { name: 'Berfin Yiğit', model: 'qwen3:1.7b' },
};

// --- New project ---------------------------------------------------------------------------

function buildFileDropzone(onPick) {
  const fileInput = h('input', { type: 'file', accept: '.pdf,.docx,.txt,.md,.zip', hidden: true, 'aria-label': 'Proje gereksinim dosyası yükle' });
  const fileNameEl = h('div', { class: 'file-name' });
  const dropzone = h('div', { class: 'dropzone', tabindex: 0, role: 'button' },
    h('div', null, 'Dosya seçmek için tıklayın veya buraya sürükleyin'),
    h('div', { class: 'muted small' }, 'PDF, DOCX, TXT, MD veya ZIP · en fazla 5 MB'),
    fileNameEl);
  const pick = (f) => { onPick(f || null); fileNameEl.textContent = f ? `Dosya: ${f.name}` : ''; };
  dropzone.addEventListener('click', () => fileInput.click());
  dropzone.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') fileInput.click(); });
  dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('drag'); });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag'));
  dropzone.addEventListener('drop', (e) => { e.preventDefault(); dropzone.classList.remove('drag'); pick(e.dataTransfer.files[0]); });
  fileInput.addEventListener('change', () => pick(fileInput.files[0]));
  return h('div', { hidden: true }, dropzone, fileInput);
}

export function renderNewProject(root) {
  let mode = 'text';
  let file = null;
  const statusSlot = h('div', { class: 'small' }, loading('Master durumu kontrol ediliyor…'));
  api('/api/master/status')
    .then((status) => statusSlot.replaceChildren(masterStatusLine(status)))
    .catch(() => statusSlot.replaceChildren(h('span', { class: 'badge danger' }, 'Master durumu alınamadı')));
  const nameInput = h('input', { type: 'text', id: 'projectName', maxlength: 120, placeholder: 'ör. Kütüphane Yönetim Sistemi', autocomplete: 'off' });
  const textArea = h('textarea', { id: 'projectText', placeholder: 'Gereksinim dokümanını buraya yapıştırın…' });
  const counter = h('span', { class: 'muted small' }, '0 karakter');
  textArea.addEventListener('input', () => { counter.textContent = `${formatNumber(textArea.value.length)} karakter`; });
  const textPane = h('div', null, textArea, h('div', { class: 'form-row', style: { marginTop: '6px' } }, counter));
  const filePane = buildFileDropzone((f) => { file = f; });
  const segText = h('button', { type: 'button', class: 'seg-btn active' }, 'Metin yapıştır');
  const segFile = h('button', { type: 'button', class: 'seg-btn' }, 'Dosya yükle');
  const setMode = (next) => {
    mode = next; segText.classList.toggle('active', mode === 'text'); segFile.classList.toggle('active', mode === 'file');
    textPane.hidden = mode !== 'text'; filePane.hidden = mode !== 'file';
  };
  segText.addEventListener('click', () => setMode('text'));
  segFile.addEventListener('click', () => setMode('file'));
  const errorBox = h('div', { class: 'form-error', hidden: true });
  const submit = h('button', { type: 'submit', class: 'btn btn-primary' }, 'Analiz et');
  const showError = (message) => { errorBox.textContent = message; errorBox.hidden = false; };
  const form = h('form', { class: 'card form' },
    h('div', { class: 'field' }, h('label', { for: 'projectName' }, 'Proje adı'), nameInput),
    h('div', { class: 'field' }, h('label', null, 'Gereksinim dokümanı'), h('div', { class: 'seg' }, segText, segFile), textPane, filePane),
    errorBox, h('div', { class: 'form-row' }, statusSlot, submit));
  form.addEventListener('submit', async (e) => {
    e.preventDefault(); errorBox.hidden = true;
    const name = nameInput.value.trim();
    if (!name) return showError('Proje adı girin.');
    const body = new FormData(); body.append('name', name);
    if (mode === 'text') { if (!textArea.value.trim()) return showError('Doküman metni boş.'); body.append('text', textArea.value); }
    else { if (!file) return showError('Bir dosya seçin.'); body.append('file', file); }
    submit.disabled = true; submit.textContent = 'Gönderiliyor…';
    try { const created = await api('/api/projects', { method: 'POST', body }); location.hash = `#/projects/${created.id}`; }
    catch (err) { showError(err.message); submit.disabled = false; submit.textContent = 'Analiz et'; }
  });
  root.replaceChildren(h('div', { class: 'page-inner' },
    h('div', { class: 'page-head' }, h('div', null, h('h1', { class: 'page-title' }, 'Yeni proje'),
      h('p', { class: 'page-lead' }, 'Yazılım gereksinim dokümanını yapıştırın veya yükleyin.'))),
    h('div', { class: 'card note' }, 'Gereksinim dokümanını gönder. Master analiz eder, görevlere böler ve ajanlar çalıştırır.'), form));
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

// --- Project detail (delegated to projects_dag.js for UX-02 <= 500 lines) -----------------

function renderDag(tasks) {
  return _renderDag(tasks, TASK_TYPES);
}

function renderTaskList(tasks) {
  return _renderTaskList(tasks, { TASK_TYPES, TASK_STATUS, AGENT_INFO, typeBadge, statusBadge, agentLabel });
}

function elapsedSince(iso) {
  return (Date.now() - Date.parse(iso)) / 1000;
}

function buildDecomposedBody(p, id, ctx, draw) {
  const spec = p.spec;
  const nonReq = p.tasks.filter((t) => t.type !== 'requirements');
  const doneCount = nonReq.filter((t) => t.status === 'done').length;
  const inProgressCount = nonReq.filter((t) => t.assigned_to && t.status === 'planned').length;
  const blockedCount = nonReq.filter((t) => t.status === 'blocked').length;
  const progressBar = nonReq.length > 0 ? h('div', { class: 'task-progress' },
    h('div', { class: 'task-progress-bar-wrap' }, h('div', { class: 'task-progress-bar', style: { width: `${Math.round(doneCount / nonReq.length * 100)}%` } })),
    h('span', { class: 'task-progress-label' }, `${doneCount}/${nonReq.length} tamamlandı${inProgressCount ? ` · ${inProgressCount} çalışıyor` : ''}${blockedCount ? ` · ${blockedCount} bekliyor` : ''}`)) : null;
  const downloadBtn = doneCount > 0 ? h('a', { class: 'btn btn-primary', href: `/api/projects/${p.id}/output.zip`, download: '', style: { textDecoration: 'none' } }, '⬇ Çıktıları indir (.zip)') : null;
  const legendTypes = [...new Set(p.tasks.map((t) => t.type))];
  if (doneCount < nonReq.length && inProgressCount > 0) {
    ctx.poll(async () => {
      const latest = await api(`/api/projects/${id}`);
      if (!ctx.isCurrent()) { ctx.stopPoll(); return; }
      const lp = (latest.tasks || []).filter((t) => t.assigned_to && t.status === 'planned').length;
      const ld = (latest.tasks || []).filter((t) => t.status === 'done').length;
      if (ld !== doneCount || lp !== inProgressCount) { ctx.stopPoll(); draw(latest); }
    }, 5000);
  }
  return [
    h('div', { class: 'card' },
      h('h2', null, spec.project_name || p.name),
      spec.summary ? h('p', { class: 'page-lead', style: { color: '#333' } }, spec.summary) : null,
      spec.actors.length ? h('div', { style: { marginTop: '8px' } }, h('span', { class: 'muted small' }, 'Aktörler: '), spec.actors.map((a) => h('span', { class: 'chip' }, a))) : null,
      h('div', { class: 'stats' }, [['Varlık', spec.entities.length], ['API ucu', spec.api_endpoints.length], ['Sayfa', spec.pages.length], ['Görev', p.tasks.length], ['Açık soru', spec.open_questions.length]]
        .map(([label, n]) => h('div', { class: 'stat' }, h('div', { class: 'num' }, String(n)), h('div', { class: 'lbl' }, label))))),
    h('div', { class: spec.open_questions.length ? 'card warn' : 'card' },
      h('h2', null, `Açık sorular (${spec.open_questions.length})`),
      spec.open_questions.length ? h('ul', { class: 'plain' }, spec.open_questions.map((q) => h('li', null, q))) : h('p', { class: 'small' }, 'Model belirsiz bir nokta bildirmedi.')),
    h('div', { class: 'card' },
      h('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' } }, h('h2', null, `Görev planı (${p.tasks.length} görev)`), downloadBtn),
      progressBar, h('div', { class: 'legend' }, legendTypes.map(typeBadge)), renderDag(p.tasks), renderTaskList(p.tasks)),
    renderSpec(spec),
  ];
}

function buildProjectHead(p, root, id, ctx) {
  let confirmDelete = false;
  const actions = h('div', { class: 'card-actions' });
  const alertBox = h('div');
  const drawActions = () => {
    const reanalyze = h('button', { class: 'btn', onclick: async () => {
      reanalyze.disabled = true;
      try { await api(`/api/projects/${p.id}/reanalyze`, { method: 'POST' }); renderProjectDetail(root, id, ctx); }
      catch (err) { reanalyze.disabled = false; alertBox.replaceChildren(h('div', { class: 'card error' }, err.message)); }
    } }, '↻ Yeniden analiz et');
    const remove = confirmDelete
      ? [h('span', { class: 'small', style: { alignSelf: 'center' } }, 'Proje silinsin mi?'),
        h('button', { class: 'btn btn-danger-solid', onclick: async () => { try { await api(`/api/projects/${p.id}`, { method: 'DELETE' }); location.hash = '#/projects'; } catch (err) { alertBox.replaceChildren(h('div', { class: 'card error' }, err.message)); } } }, 'Evet, sil'),
        h('button', { class: 'btn', onclick: () => { confirmDelete = false; drawActions(); } }, 'Vazgeç')]
      : h('button', { class: 'btn btn-danger', onclick: () => { confirmDelete = true; drawActions(); } }, 'Sil');
    actions.replaceChildren(...(p.status === 'analyzing' ? [] : [reanalyze, remove].flat()));
  };
  drawActions();
  const meta = [p.source_filename ? `Kaynak: ${p.source_filename}` : 'Kaynak: yapıştırılan metin', `Oluşturulma: ${formatDateTime(p.created_at)}`];
  if (p.status === 'decomposed') meta.push(`Analiz: ${p.analysis_model}, ${formatSeconds(p.analysis_seconds)}${p.chunk_count > 1 ? `, ${p.chunk_count} parça` : ''}`);
  return h('div', null, h('a', { class: 'back-link', href: '#/projects' }, '← Projeler'),
    h('div', { class: 'page-head' }, h('div', null, h('h1', { class: 'page-title' }, p.name, ' ', statusBadge(PROJECT_STATUS, p.status)), h('p', { class: 'page-lead' }, meta.join(' · '))), actions), alertBox);
}

export async function renderProjectDetail(root, id, ctx) {
  root.replaceChildren(h('div', { class: 'page-inner' }, loading()));
  let project;
  try { project = await api(`/api/projects/${id}`); }
  catch (err) { root.replaceChildren(h('div', { class: 'page-inner' }, h('a', { class: 'back-link', href: '#/projects' }, '← Projeler'), h('div', { class: 'card error' }, err.message))); return; }
  if (!ctx.isCurrent()) return;
  const draw = (p) => {
    const head = buildProjectHead(p, root, id, ctx);
    let body = [];
    if (p.status === 'analyzing') {
      const elapsed = h('span', null, formatSeconds(elapsedSince(p.updated_at)));
      body = [h('div', { class: 'card' }, h('div', { class: 'loading', style: { padding: '6px 0' } }, h('span', { class: 'spinner' }), h('span', null, 'Master ajan dokümanı analiz ediyor… geçen süre: ', elapsed)))];
      ctx.poll(async () => {
        elapsed.textContent = formatSeconds(elapsedSince(p.updated_at));
        const latest = await api(`/api/projects/${id}`);
        if (latest.status !== 'analyzing') { ctx.stopPoll(); draw(latest); }
      }, 2500);
    } else if (p.status === 'failed') {
      body = [h('div', { class: 'card error' }, h('strong', null, 'Analiz başarısız oldu. '), p.error || '')];
    } else {
      body = buildDecomposedBody(p, id, ctx, draw);
    }
    body.push(sourceDocument(p));
    root.replaceChildren(h('div', { class: 'page-inner' }, head, body));
  };
  draw(project);
}
