// "Stüdyolar" view: categorized Turkish Workbench + auto-generated OpenAPI explorer (zero unwired routes).
import { safeFetchJson } from './storage.js';
import { uiConfirm } from './ui_dialog.js';
import { csrfHeaders, h, loading } from './util.js';
import { renderWorkbenchTab, WORKBENCH_TABS } from './workbench.js';
import { renderInteractiveLabsTab } from './workspace_labs.js';

const GROUP_LABELS = {
  orchestrator: 'Orkestratör', rag: 'Bilgi tabanı (RAG)', hallucination: 'Doğrulama ve güvenilirlik',
  studios: 'Araştırma, sunum, belge, veri, medya', factory: 'Yazılım fabrikası', games: 'Oyun stüdyosu',
  domains: 'Alan motorları', distributed: 'Dağıtık yürütme', ml: 'Makine öğrenmesi', gateway: 'LLM geçidi',
  admin: 'Yönetim ve operasyon', auth: 'Hesap', memory: 'Hafıza', ux: 'Arayüz servisleri', tasks: 'Görevler',
  perf: 'Başarım', events: 'Olaylar', assistant: 'Asistan', productivity: 'Üretkenlik',
  security: 'Güvenlik ve 2FA', tools: 'Eğitim ve alan araçları',
};
const TOKEN_KEY = 'cm6453_admin_token';
const DANGEROUS = /restore|delete|cancel|reset-password|purge|revoke/i;

let spec = null;
let fieldSeq = 0;

function readToken() {
  try { return sessionStorage.getItem(TOKEN_KEY) || ''; } catch { return ''; }
}

function writeToken(value) {
  try { sessionStorage.setItem(TOKEN_KEY, value); } catch { /* private mode */ }
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
  const fid = `hub-f-${++fieldSeq}`;
  const labelText = s.title || name;
  const label = h('label', { class: 'hub-label', for: fid }, name, required ? h('span', { class: 'hub-req' }, ' *') : null);
  let control;
  if (s.enum) {
    control = h('select', { id: fid, name, 'aria-label': labelText }, !required ? h('option', { value: '' }, '(boş)') : null,
      ...s.enum.map((v) => h('option', { value: String(v) }, String(v))));
  } else if (s.type === 'boolean') {
    control = h('input', { id: fid, type: 'checkbox', name, 'aria-label': labelText });
  } else if (s.type === 'integer' || s.type === 'number') {
    control = h('input', { id: fid, type: 'number', name, 'aria-label': labelText, step: s.type === 'integer' ? '1' : 'any', value: s.default ?? '' });
  } else if (s.format === 'binary') {
    control = h('input', { id: fid, type: 'file', name, 'aria-label': labelText });
  } else if (s.type === 'array' || s.type === 'object') {
    control = h('textarea', { id: fid, name, 'aria-label': labelText, rows: 3, placeholder: s.type === 'array' ? '["a", "b"]' : '{ }', dataset: { json: '1' } });
  } else {
    control = h('textarea', { id: fid, name, 'aria-label': labelText, rows: 2, placeholder: s.description || '' });
    if (s.default !== null && s.default !== undefined) control.value = String(s.default);
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

function buildRequest(path, method, params, values, isForm) {
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
  return { url, init };
}

function endpointCard(path, method, op) {
  const params = (op.parameters || []).filter((p) => p.in === 'path' || p.in === 'query');
  const bodyContent = op.requestBody && op.requestBody.content;
  const isForm = Boolean(bodyContent && bodyContent['multipart/form-data']);
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
    if ((DANGEROUS.test(path) || method === 'delete') && !(await uiConfirm(`${method.toUpperCase()} ${path} kalıcı değişiklik yapabilir. Devam edilsin mi?`))) return;
    let values;
    try { values = collect(form); } catch (err) { status.textContent = `Geçersiz JSON: ${err.message}`; return; }
    const { url, init } = buildRequest(path, method, params, values, isForm);
    run.disabled = true;
    status.textContent = 'Çalışıyor…';
    const started = performance.now();
    const res = await safeFetchJson(url, init);
    run.disabled = false;
    if (res.status === 0) {
      status.textContent = `Ağ hatası: ${res.error || 'Bağlantı yok'}`;
      status.className = 'hub-status err';
      return;
    }
    const shown = typeof res.data === 'string' ? res.data : JSON.stringify(res.data, null, 2);
    result.textContent = shown.length > 20000 ? `${shown.slice(0, 20000)}\n… (kısaltıldı)` : shown;
    result.hidden = false;
    status.textContent = `HTTP ${res.status} · ${Math.round(performance.now() - started)} ms`;
    status.className = `hub-status ${res.ok ? 'ok' : 'err'}`;
  });

  return h('details', { class: 'card hub-endpoint' },
    h('summary', null, h('span', { class: `hub-method m-${method}` }, method.toUpperCase()), h('code', null, path),
      op.summary ? h('span', { class: 'hub-sum' }, op.summary) : null),
    op.description ? h('p', { class: 'hub-desc' }, op.description.split('\n')[0]) : null,
    form, result);
}

function renderOpenApiTab(groups, needle) {
  const wrap = h('div', { class: 'hub-body' });
  for (const [key, endpoints] of [...groups.entries()].sort()) {
    const shown = endpoints.filter((e) => !needle || `${e.path} ${e.op.summary || ''} ${GROUP_LABELS[key] || key}`.toLowerCase().includes(needle));
    if (!shown.length) continue;
    wrap.append(h('section', { class: 'hub-group' },
      h('h2', null, GROUP_LABELS[key] || key, h('span', { class: 'hub-count' }, ` ${shown.length}`)),
      ...shown.map((e) => endpointCard(e.path, e.method, e.op))));
  }
  if (!wrap.childElementCount) wrap.append(h('div', { class: 'card' }, 'Eşleşen uç nokta yok.'));
  return wrap;
}

function groupEndpoints() {
  const groups = new Map();
  for (const [path, ops] of Object.entries((spec && spec.paths) || {})) {
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
  root.replaceChildren(loading('Stüdyolar ve uç noktalar yükleniyor…'));
  if (!spec) {
    const res = await safeFetchJson('/openapi.json');
    if (res.ok && res.data) spec = res.data;
  }
  if (!ctx.isCurrent()) return;
  const groups = groupEndpoints();
  let activeTab = 'labs';
  const filter = h('input', { type: 'search', class: 'hub-filter', placeholder: 'Araç veya uç nokta ara (ör. 2FA, quiz, CNC, RAG, vergi)', 'aria-label': 'Araç ara' });
  const token = h('input', { type: 'password', class: 'hub-token', placeholder: 'Yönetici anahtarı (yalnız bu oturum)', value: readToken(), 'aria-label': 'Yönetici anahtarı' });
  token.addEventListener('change', () => writeToken(token.value));

  const tabBar = h('div', { class: 'wb-tabs', role: 'tablist', 'aria-label': 'Stüdyo kategorileri' });
  const bodySlot = h('div', { class: 'wb-slot' });
  const allTabs = [{ id: 'labs', label: 'Etkileşimli Laboratuvarlar' }, ...WORKBENCH_TABS, { id: 'openapi', label: 'Tüm OpenAPI Gezgini' }];

  const draw = () => {
    const needle = filter.value.trim().toLowerCase();
    tabBar.replaceChildren(...allTabs.map((t) => h('button', {
      type: 'button', role: 'tab', 'aria-selected': String(t.id === activeTab),
      class: `wb-tab${t.id === activeTab ? ' active' : ''}`,
      onClick: () => { activeTab = t.id; draw(); },
    }, t.label)));
    if (activeTab === 'labs') bodySlot.replaceChildren(renderInteractiveLabsTab());
    else if (activeTab === 'openapi') bodySlot.replaceChildren(renderOpenApiTab(groups, needle));
    else {
      const tab = WORKBENCH_TABS.find((t) => t.id === activeTab) || WORKBENCH_TABS[0];
      bodySlot.replaceChildren(renderWorkbenchTab(tab, needle, readToken));
    }
  };
  filter.addEventListener('input', draw);
  draw();

  root.replaceChildren(
    h('h1', null, 'Stüdyolar, Araçlar ve Yönetim'),
    h('div', { class: 'card note' }, 'Üretkenlik, eğitim, mühendislik, 2FA güvenlik, halüsinasyon doğrulama, ML Ops ve dağıtık ajan araçlarının tamamı burada doğrudan arka uç API servislerine bağlıdır.'),
    tabBar,
    h('div', { class: 'hub-toolbar' }, filter, token),
    bodySlot);
}
