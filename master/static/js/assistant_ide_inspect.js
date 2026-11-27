// IDE drawers: the signed proof card, an API console for the project, and picking an element in the preview to edit.
import { safeFetchJson } from './storage.js';

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function button(text) {
  const b = el('button', 'ide-tool-btn', text);
  b.type = 'button';
  return b;
}

function section(title, lines) {
  const box = el('div', 'ide-drawer-section');
  box.append(el('strong', '', title));
  (lines.length ? lines : ['—']).forEach((line) => box.append(el('div', '', line)));
  return box;
}

async function showProof(wsId, body) {
  body.replaceChildren(el('div', '', 'Yükleniyor...'));
  const res = await safeFetchJson(`/api/studio/workspaces/${wsId}/proof`);
  const data = res.data;
  if (!res.ok || !data) {
    body.replaceChildren(el('div', '', 'Kanıt kaydı okunamadı.'));
    return;
  }
  let state = 'Bu proje için imzalı kayıt yok.';
  if (data.recorded) {
    state = data.signed ? `İmza geçerli (${data.created}), ${data.files} dosya` : 'İmza DOĞRULANAMADI';
  }
  body.replaceChildren(
    section('Kayıt', [state]),
    section('Teslimden sonra değişen dosyalar', data.changed),
    section('Doğrulandı (denetim çalıştı, sorun yok)', (data.ledger && data.ledger.verified) || []),
    section('Varsayım (doğrulanmadı)', (data.ledger && data.ledger.assumed) || []),
    section('Açık kalan', (data.ledger && data.ledger.open) || []),
    section('Denetim uyarıları', data.warnings),
    section('Bağımlılıklar', data.dependencies),
    section('Olay kaydı', (data.events || []).map((e) => `${e.at.replace('T', ' ')} · ${e.kind} · ${e.detail}`)),
    section('Zaman çizelgesi', data.timeline.map((t) => `${t.version} · ${t.label} · ${t.at.slice(0, 19).replace('T', ' ')}`)),
  );
}

async function showMemory(_wsId, body) {
  body.replaceChildren(el('div', '', 'Yükleniyor...'));
  const res = await safeFetchJson('/api/studio/memory-view');
  const data = res.data || {};
  body.replaceChildren(
    section('Kalıcı tercihlerin', (data.preferences || []).map((p) => `${p.text} (${p.at})`)),
    section('Öğrenilen bilgiler', (data.facts || []).map((f) => `[${f.category}] ${f.value}`)),
    el('div', '', 'Tercihleri silmek için sohbete "tercihlerimi sil" yaz.'),
  );
}

function showConsole(wsId, body) {
  const input = el('textarea', 'ide-api-input');
  input.rows = 4;
  input.value = 'GET /';
  input.placeholder = 'GET /yol\nPOST /yol {"alan": "değer"}';
  const run = button('İstekleri çalıştır');
  const out = el('pre', 'ide-api-output');
  run.addEventListener('click', async () => {
    run.disabled = true;
    out.textContent = 'Yalıtılmış kutuda çalıştırılıyor...';
    const res = await safeFetchJson(`/api/studio/workspaces/${wsId}/api-console`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ requests: input.value }),
    });
    const data = res.data || {};
    out.textContent = res.ok && data.responses
      ? data.responses.map((r) => `${r.method} ${r.path} → ${r.status}\n${r.body}`).join('\n\n')
      : (data.detail || 'İstek çalıştırılamadı.');
    run.disabled = false;
  });
  body.replaceChildren(el('div', '', 'Her çalıştırma projenin temiz bir kopyasında, ağ kapalı yapılır.'), input, run, out);
}

function bindPicker(card, iframe, iterBar, pick, openPreview) {
  let active = false;
  const send = () => iframe.contentWindow && iframe.contentWindow.postMessage({ type: 'preview-pick-mode', on: active }, '*');
  const set = (value) => {
    active = value;
    pick.classList.toggle('primary', active);
    send();
  };
  pick.addEventListener('click', () => {
    if (!active) openPreview();
    set(!active);
  });
  iframe.addEventListener('load', send);
  addEventListener('message', (event) => {
    if (event.source !== iframe.contentWindow || !event.data || event.data.type !== 'preview-pick') return;
    let found = {};
    try { found = JSON.parse(event.data.message); } catch { return; }
    const input = iterBar.querySelector('input');
    const label = found.text ? ` (metni: "${String(found.text).slice(0, 60)}")` : '';
    input.value = `\`${String(found.selector).slice(0, 120)}\` öğesinde${label}: `;
    set(false);
    input.focus();
  });
}

export function attachInspector(card, ctx) {
  const { wsId, iframe, iterBar, toolbar, openPreview, hasPreview } = ctx;
  const drawer = el('div', 'ide-drawer');
  drawer.hidden = true;
  const head = el('div', 'ide-drawer-head');
  const title = el('span', '');
  const close = button('Kapat');
  const body = el('div', 'ide-drawer-body');
  head.append(title, close);
  drawer.append(head, body);
  card.insertBefore(drawer, iterBar);
  close.addEventListener('click', () => { drawer.hidden = true; });

  const open = (name, render) => {
    title.textContent = name;
    drawer.hidden = false;
    render(wsId, body);
  };
  const proof = button('Kanıt');
  proof.addEventListener('click', () => open('Doğrulama kanıtı', showProof));
  const api = button('API dene');
  api.addEventListener('click', () => open('API deneme konsolu', showConsole));
  const memory = button('Bellek');
  memory.addEventListener('click', () => open('Bellek', showMemory));
  toolbar.append(proof, api, memory);

  if (hasPreview) {
    const pick = button('Öğe seç');
    pick.title = 'Önizlemede bir öğeye tıklayıp onun için değişiklik iste';
    toolbar.append(pick);
    bindPicker(card, iframe, iterBar, pick, openPreview);
  }
}
