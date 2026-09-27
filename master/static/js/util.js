// Small DOM and formatting helpers shared by the views. No framework, no CDN: the UI must
// work fully offline, like the rest of the system.

const SVG_NS = 'http://www.w3.org/2000/svg';

function applyProps(el, props) {
  for (const [key, value] of Object.entries(props || {})) {
    if (value == null || value === false) continue;
    if (key === 'class') el.setAttribute('class', value);
    else if (key === 'dataset') Object.assign(el.dataset, value);
    else if (key.startsWith('on') && typeof value === 'function') el.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key === 'style' && typeof value === 'object') Object.assign(el.style, value);
    else if (value === true) el.setAttribute(key, '');
    else el.setAttribute(key, value);
  }
}

function appendChildren(el, children) {
  for (const child of children.flat(Infinity)) {
    if (child == null || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

// Text is always inserted as text nodes, so model output can never inject markup here.
export function h(tag, props, ...children) {
  const el = document.createElement(tag);
  applyProps(el, props);
  appendChildren(el, children);
  return el;
}

export function svg(tag, props, ...children) {
  const el = document.createElementNS(SVG_NS, tag);
  applyProps(el, props);
  appendChildren(el, children);
  return el;
}

export async function api(path, options = {}) {
  const resp = await fetch(path, options);
  const text = await resp.text();
  let data = null;
  if (text) {
    try { data = JSON.parse(text); } catch { data = text; }
  }
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    if (data && data.detail) {
      detail = Array.isArray(data.detail)
        ? data.detail.map((e) => e.msg).join('; ')
        : String(data.detail);
    }
    throw new Error(detail);
  }
  return data;
}

export function formatDateTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('tr-TR', { dateStyle: 'medium', timeStyle: 'short' });
}

export function formatSeconds(seconds) {
  if (seconds == null) return '—';
  if (seconds < 60) return `${Math.round(seconds)} sn`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes} dk ${Math.round(seconds % 60)} sn`;
}

export function formatNumber(value) {
  return value == null ? '—' : Number(value).toLocaleString('tr-TR');
}

// Auto-focusing inputs on phones pops up the keyboard, so only do it on wide screens.
export function isDesktop() {
  return window.matchMedia('(min-width: 861px)').matches;
}

export function loading(text = 'Yükleniyor…') {
  return h('div', { class: 'loading' }, h('span', { class: 'spinner' }), text);
}

// On phones and tablets the sidebar is a drawer (see the 860px media query). On desktop these
// classes have no visual effect, so calling them unconditionally is harmless.
export function openSidebar() {
  document.getElementById('sidebar').classList.add('open');
  document.getElementById('sidebarOverlay').classList.add('active');
}

export function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('sidebarOverlay').classList.remove('active');
}
