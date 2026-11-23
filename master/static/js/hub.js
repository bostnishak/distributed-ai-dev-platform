// "Stüdyolar" view: one screen for every backend capability (RAG, doğrulama, stüdyolar, fabrika, oyun,
// dağıtık, ML, yönetim). The forms are generated from the server's own OpenAPI document, so a new endpoint
// shows up here without touching the UI and no endpoint can be left without a screen (F17, UX-16/24).
import { csrfHeaders, h, loading } from './util.js';

const GROUP_LABELS = {
  orchestrator: 'Orkestratör', rag: 'Bilgi tabanı (RAG)', hallucination: 'Doğrulama ve güvenilirlik',
  studios: 'Araştırma, sunum, belge, veri, medya', factory: 'Yazılım fabrikası', games: 'Oyun stüdyosu',
  domains: 'Alan motorları', distributed: 'Dağıtık yürütme', ml: 'Makine öğrenmesi', gateway: 'LLM geçidi',
  admin: 'Yönetim ve operasyon', auth: 'Hesap', memory: 'Hafıza', ux: 'Arayüz servisleri', tasks: 'Görevler',
  perf: 'Başarım', events: 'Olaylar', assistant: 'Asistan',
};
const TOKEN_KEY = 'cm6453_admin_token';
const DANGEROUS = /restore|delete|cancel|reset-password|purge/i;

let spec = null;

function readToken() {
  try { return sessionStorage.getItem(TOKEN_KEY) || ''; } catch { return ''; }
}

function writeToken(value) {
  try { sessionStorage.setItem(TOKEN_KEY, value); } catch { /* private mode: token lives only in the field */ }
}

function resolve(schema) {
  let node = schema;
  for (let i = 0; node && node.$ref && i < 8; i += 1) {
    node = node.$ref.replace('#/', '').split('/').reduce((o, k) => (o ? o[k] : null), spec);
  }
  if (node && (node.anyOf || node.oneOf)) {
    const options = (node.anyOf || node.oneOf).filter((o) => o.type !== 'null');
    if (options.length) return resolve({ ...node, ...resolve(options[0]), anyOf: undefined, oneOf: undefined });
  }
  return node || {};
}

function inputFor(name, schema, required) {
  const s = resolve(schema);
  const label = h('label', { class: 'hub-label' }, name, required ? h('span', { class: 'hub-req' }, ' *') : null);
  let control;
  if (s.enum) {
    control = h('select', { name }, !required ? h('option', { value: '' }, '(boş)') : null,
      ...s.enum.map((v) => h('option', { value: String(v) }, String(v))));
  } else if (s.type === 'boolean') {
    control = h('input', { type: 'checkbox', name });
  } else if (s.type === 'integer' || s.type === 'number') {
    control = h('input', { type: 'number', name, step: s.type === 'integer' ? '1' : 'any', value: s.default ?? '' });
  } else if (s.format === 'binary') {
    control = h('input', { type: 'file', name });
  } else if (s.type === 'array' || s.type === 'object') {
    control = h('textarea', { name, rows: 3, placeholder: s.type === 'array' ? '["a", "b"]' : '{ }', dataset: { json: '1' } });
  } else {
    control = h('textarea', { name, rows: 2, placeholder: s.description || '' });
    if (s.default != null) control.value = String(s.default);
  }
  control.dataset.type = s.type || 'string';
  return h('div', { class: 'hub-field' }, label, control);
}

function collect(form) {
  const out = {};
  for (const el of form.querySelectorAll('[name]')) {
    const { name } = el;
    if (el.type === 'file') { if (el.files[0]) out[name] = el.files[0]; continue; }
    if (el.type === 'checkbox') { out[name] = el.checked; continue; }
    const raw = el.value.trim();
    if (raw === '') continue;
    if (el.dataset.json) out[name] = JSON.parse(raw);
    else if (el.type === 'number') out[name] = Number(raw);
    else out[name] = raw;
  }
  return out;
}

function endpointCard(path, method, op) {
  const params = (op.parameters || []).filter((p) => p.in === 'path' || p.in === 'query');
  const bodyContent = op.requestBody && op.requestBody.content;
  const isForm = bodyContent && bodyContent['multipart/form-data'];
  const bodySchema = bodyContent && resolve((bodyContent['application/json'] || bodyContent['multipart/form-data'] || {}).schema);
  const form = h('form', { class: 'hub-form' });
  for (const p of params) form.append(inputFor(p.name, p.schema || {}, p.required));
  const required = new Set((bodySchema && bodySchema.required) || []);
  for (const [name, schema] of Object.entries((bodySchema && bodySchema.properties) || {})) form.append(inputFor(name, schema, required.has(name)));

  const result = h('pre', { class: 'hub-result', hidden: true });
  const status = h('span', { class: 'hub-status' });
  const run = h('button', { class: 'btn', type: 'submit' }, 'Çalıştır');
  form.append(h('div', { class: 'card-actions' }, run, status));

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (DANGEROUS.test(path) || method === 'DELETE') {
      if (!window.confirm(`${method} ${path} kalıcı bir değişiklik yapabilir. Devam edilsin mi?`)) return;
    }
    let values;
    try { values = collect(form); } catch (err) { status.textContent = `Geçersiz JSON: ${err.message}`; return; }
    let url = path;
    const query = new URLSearchParams();
    for (const p of params) {
      const v = values[p.name];
      delete values[p.name];
      if (p.in === 'path') url = url.replace(`{${p.name}}`, encodeURIComponent(v ?? ''));
      else if (v !== undefined && v !== '') query.set(p.name, v);
    }
    if (query.toString()) url += `?${query}`;
    const headers = {};
    const token = readToken();
    if (token) headers['X-Admin-Token'] = token;
    const init = { method: method.toUpperCase(), headers };
    if (method !== 'get' && method !== 'delete' && Object.keys(values).length) {
      if (isForm) {
        const fd = new FormData();
        for (const [k, v] of Object.entries(values)) fd.append(k, v);
        init.body = fd;
      } else {
        init.body = JSON.stringify(values);
        headers['Content-Type'] = 'application/json';
      }
    }
    init.headers = csrfHeaders(headers);
    run.disabled = true;
    status.textContent = 'Çalışıyor…';
    const started = performance.now();
    try {
      const resp = await fetch(url, init);
      const text = await resp.text();
      let shown = text;
      try { shown = JSON.stringify(JSON.parse(text), null, 2); } catch { /* not JSON */ }
      result.textContent = shown.length > 20000 ? `${shown.slice(0, 20000)}\n… (kısaltıldı)` : shown;
      result.hidden = false;
      status.textContent = `HTTP ${resp.status} · ${Math.round(performance.now() - started)} ms`;
      status.className = `hub-status ${resp.ok ? 'ok' : 'err'}`;
    } catch (err) {
      status.textContent = `Ağ hatası: ${err.message}`;
      status.className = 'hub-status err';
    } finally {
      run.disabled = false;
    }
  });

  return h('details', { class: 'card hub-endpoint' },
    h('summary', null, h('span', { class: `hub-method m-${method}` }, method.toUpperCase()), h('code', null, path),
      op.summary ? h('span', { class: 'hub-sum' }, op.summary) : null),
    op.description ? h('p', { class: 'hub-desc' }, op.description.split('\n')[0]) : null,
    form, result);
}

function groupEndpoints() {
  const groups = new Map();
  for (const [path, ops] of Object.entries(spec.paths)) {
    if (!path.startsWith('/api/')) continue;
    const key = path.split('/')[2];
    if (!groups.has(key)) groups.set(key, []);
    for (const [method, op] of Object.entries(ops)) {
      if (['get', 'post', 'put', 'delete', 'patch'].includes(method)) groups.get(key).push({ path, method, op });
    }
  }
  return groups;
}

export async function renderHub(root, ctx) {
  root.replaceChildren(loading('Uç noktalar yükleniyor…'));
  try {
    if (!spec) spec = await (await fetch('/openapi.json')).json();
  } catch (err) {
    root.replaceChildren(h('div', { class: 'card error' }, `Şema alınamadı: ${err.message}`));
    return;
  }
  if (!ctx.isCurrent()) return;
  const groups = groupEndpoints();
  const filter = h('input', { type: 'search', class: 'hub-filter', placeholder: 'Uç nokta ara (ör. rag, sunum, doctor)', 'aria-label': 'Uç nokta ara' });
  const token = h('input', { type: 'password', class: 'hub-token', placeholder: 'Yönetici anahtarı (yalnız bu oturum)', value: readToken(), 'aria-label': 'Yönetici anahtarı' });
  token.addEventListener('change', () => writeToken(token.value));
  const body = h('div', { class: 'hub-body' });

  const draw = () => {
    const needle = filter.value.trim().toLowerCase();
    body.replaceChildren();
    for (const [key, endpoints] of [...groups.entries()].sort()) {
      const shown = endpoints.filter((e) => !needle || `${e.path} ${e.op.summary || ''} ${GROUP_LABELS[key] || key}`.toLowerCase().includes(needle));
      if (!shown.length) continue;
      body.append(h('section', { class: 'hub-group' },
        h('h2', null, GROUP_LABELS[key] || key, h('span', { class: 'hub-count' }, ` ${shown.length}`)),
        ...shown.map((e) => endpointCard(e.path, e.method, e.op))));
    }
    if (!body.childElementCount) body.append(h('div', { class: 'card' }, 'Eşleşen uç nokta yok.'));
  };
  filter.addEventListener('input', draw);
  draw();

  root.replaceChildren(
    h('h1', null, 'Stüdyolar ve yönetim'),
    h('div', { class: 'card note' }, 'Platformun her yeteneği burada bir formdur. Formlar sunucunun kendi şemasından üretilir; '
      + 'yönetim uç noktaları yalnız yerel makineden veya yönetici anahtarıyla çalışır. Anahtar tarayıcıda kalıcı saklanmaz.'),
    h('div', { class: 'hub-toolbar' }, filter, token),
    body);
}
