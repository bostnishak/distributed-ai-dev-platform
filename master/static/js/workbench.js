// Interactive Turkish Studio Workbench: renders all categorized backend tools with live forms & outputs.
import { uiConfirm, uiToast } from './ui_dialog.js';
import { api, h } from './util.js';
import { PRODUCTIVITY_TOOLS } from './workbench_catalog_1.js';
import { DOMAIN_AND_EDU_TOOLS, SECURITY_AND_MEMORY_TOOLS } from './workbench_catalog_2.js';
import { OPS_AND_AI_TOOLS } from './workbench_catalog_3.js';
import { PLATFORM_EXT_TOOLS } from './workbench_catalog_4.js';
import { ECOSYSTEM_TOOLS } from './workbench_catalog_5.js';

export const WORKBENCH_TABS = [
  { id: 'productivity', label: 'Üretkenlik, Veri & Stüdyolar', tools: PRODUCTIVITY_TOOLS },
  { id: 'domains', label: 'Eğitim & Alan Motorları', tools: DOMAIN_AND_EDU_TOOLS },
  { id: 'security', label: 'Güvenlik, 2FA & Hafıza', tools: SECURITY_AND_MEMORY_TOOLS },
  { id: 'ops', label: 'Yönetim, ML & Ajanlar', tools: OPS_AND_AI_TOOLS },
  { id: 'platform_ext', label: 'Fabrika, IDE, HA & Stüdyolar', tools: PLATFORM_EXT_TOOLS },
  { id: 'ecosystem', label: 'Ekosistem, MCP, Mağaza & v1', tools: ECOSYSTEM_TOOLS },
];

function buildUrl(tool, paramInputs, queryInputs) {
  let url = tool.path;
  for (const [k, el] of Object.entries(paramInputs)) {
    url = url.replace(`{${k}}`, encodeURIComponent(el.value.trim() || 'demo'));
  }
  const qs = new URLSearchParams();
  for (const [k, el] of Object.entries(queryInputs || {})) {
    const val = el.value.trim();
    if (val !== '') qs.set(k, val);
  }
  if (qs.toString()) url += (url.includes('?') ? '&' : '?') + qs.toString();
  return url;
}

function renderResult(box, data) {
  box.replaceChildren();
  if (data && typeof data === 'object' && typeof data.svg === 'string' && data.svg.startsWith('<svg')) {
    const img = h('img', {
      alt: 'Üretilen görsel',
      src: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(data.svg)}`,
      class: 'wb-preview-img',
    });
    box.append(img);
  }
  const text = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
  box.append(h('pre', { class: 'hub-result' }, text.slice(0, 20000)));
  box.hidden = false;
}

function createToolCard(tool, getAdminToken) {
  const paramInputs = {};
  const paramFields = Object.entries(tool.params || {}).map(([k, val]) => {
    const inp = h('input', { type: 'text', value: String(val), 'aria-label': `${tool.title} - ${k}` });
    paramInputs[k] = inp;
    return h('div', { class: 'hub-field' }, h('label', { class: 'hub-label' }, k), inp);
  });
  const queryInputs = {};
  const queryFields = Object.entries(tool.query || {}).map(([k, val]) => {
    const inp = h('input', { type: 'text', value: String(val), 'aria-label': `${tool.title} sorgu - ${k}` });
    queryInputs[k] = inp;
    return h('div', { class: 'hub-field' }, h('label', { class: 'hub-label' }, `sorgu: ${k}`), inp);
  });

  let bodyArea = null;
  if (tool.method !== 'GET' && tool.method !== 'DELETE' && tool.body !== undefined) {
    bodyArea = h('textarea', { rows: 4, 'aria-label': `${tool.title} veri gövdesi` });
    bodyArea.value = JSON.stringify(tool.body || {}, null, 2);
  }

  const status = h('span', { class: 'hub-status' });
  const resultBox = h('div', { class: 'wb-result', hidden: true });
  const runBtn = h('button', { type: 'button', class: 'btn primary' }, 'Çalıştır');

  runBtn.addEventListener('click', async () => {
    if (tool.dangerous) {
      const ok = await uiConfirm(`${tool.title} (${tool.method} ${tool.path}) kalıcı değişiklik yapabilir. Devam edilsin mi?`);
      if (!ok) return;
    }
    const headers = {};
    const tok = getAdminToken();
    if (tok) headers['X-Admin-Token'] = tok;
    const opts = { method: tool.method, headers };
    if (bodyArea) {
      let parsed;
      try { parsed = JSON.parse(bodyArea.value); } catch (err) {
        status.textContent = `Geçersiz JSON: ${err.message}`;
        status.className = 'hub-status err';
        return;
      }
      if (tool.form) {
        const fd = new FormData();
        for (const [k, v] of Object.entries(parsed)) fd.append(k, String(v));
        opts.body = fd;
      } else {
        headers['Content-Type'] = 'application/json';
        opts.body = bodyArea.value;
      }
    }
    runBtn.disabled = true;
    status.textContent = 'Çalıştırılıyor...';
    status.className = 'hub-status';
    const t0 = performance.now();
    try {
      const data = await api(buildUrl(tool, paramInputs, queryInputs), opts);
      renderResult(resultBox, data);
      status.textContent = `Başarılı · ${Math.round(performance.now() - t0)} ms`;
      status.className = 'hub-status ok';
      uiToast(`${tool.title} tamamlandı`, 'ok');
    } catch (err) {
      status.textContent = `Hata: ${err.message}`;
      status.className = 'hub-status err';
      uiToast(`${tool.title}: ${err.message}`, 'err');
    } finally {
      runBtn.disabled = false;
    }
  });

  return h('details', { class: 'card hub-endpoint wb-card', dataset: { toolId: tool.id } },
    h('summary', null,
      h('span', { class: `hub-method m-${tool.method.toLowerCase()}` }, tool.method),
      h('strong', null, tool.title),
      h('code', { class: 'wb-path' }, tool.path)),
    ...paramFields,
    ...queryFields,
    bodyArea ? h('div', { class: 'hub-field' }, h('label', { class: 'hub-label' }, tool.form ? 'Form Alanları (JSON)' : 'İstek Verisi (JSON)'), bodyArea) : null,
    h('div', { class: 'card-actions' }, runBtn, status),
    resultBox);
}

export function renderWorkbenchTab(tab, query, getAdminToken) {
  const needle = (query || '').trim().toLowerCase();
  const grouped = new Map();
  for (const tool of tab.tools) {
    const hay = `${tool.title} ${tool.group} ${tool.path}`.toLowerCase();
    if (needle && !hay.includes(needle)) continue;
    if (!grouped.has(tool.group)) grouped.set(tool.group, []);
    grouped.get(tool.group).push(tool);
  }
  const wrap = h('div', { class: 'hub-body' });
  for (const [grp, tools] of grouped.entries()) {
    wrap.append(h('section', { class: 'hub-group' },
      h('h2', null, grp, h('span', { class: 'hub-count' }, ` ${tools.length}`)),
      ...tools.map((t) => createToolCard(t, getAdminToken))));
  }
  if (!wrap.childElementCount) {
    wrap.append(h('div', { class: 'card' }, 'Aramanızla eşleşen araç bulunamadı.'));
  }
  return wrap;
}
