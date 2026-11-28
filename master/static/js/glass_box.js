// The glass box: hardware ribbon, proof drawer with screenshots, one-click undo, unfinished builds, restored tabs.
import { safeFetchJson, startManagedInterval, storageGet, storageSet } from './storage.js';

const RIBBON_MS = 3000;
const STATE_MARK = { geçti: '✔', kaldı: '✘' };
const FRAMES = { '1-ilk-acilis.png': 'İlk açılış', '2-dolu-form.png': 'Dolu form', '3-gonderim-sonrasi.png': 'Gönderim sonrası', '4-yenileme-sonrasi.png': 'Yenileme sonrası', '5-bos-girdi.png': 'Boş girdi' };

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

export function ribbonText(data) {
  const parts = [];
  if (data.vram_total_gb) parts.push(`VRAM ${data.vram_used_gb} / ${data.vram_total_gb} GB`, `GPU ${data.temperature_c} °C`);
  parts.push(`Model: ${data.models.length ? data.models.join(', ') : 'yüklü değil'}`);
  parts.push(`CPU %${Math.round(data.cpu_percent)}`, `RAM ${data.ram_used_gb} / ${data.ram_total_gb} GB`);
  parts.push(data.isolation, `Vites: ${data.gear}`);
  if (data.waiting) parts.push(`Bekliyor: ${data.waiting}`);
  return parts;
}

function startRibbon() {
  const bar = el('footer', 'hw-ribbon');
  bar.setAttribute('aria-label', 'Donanım göstergesi');
  document.body.append(bar);
  const refresh = async () => {
    if (document.hidden) return;
    const res = await safeFetchJson('/api/glass/hardware');
    bar.hidden = !res.ok;
    if (res.ok) bar.replaceChildren(...ribbonText(res.data).map((text) => el('span', 'hw-item', text)));
  };
  refresh();
  startManagedInterval(refresh, RIBBON_MS);
}

async function showUnfinished() {
  const res = await safeFetchJson('/api/glass/unfinished');
  const waiting = res.ok ? res.data.unfinished : [];
  if (!waiting.length) return;
  const banner = el('div', 'resume-banner');
  banner.setAttribute('role', 'status');
  const first = waiting[0];
  banner.append(el('span', '', `Yarım kalan proje: ${first.name} (${first.done}/${first.total} dosya).`));
  const resume = el('button', 'resume-btn', 'Devam et');
  resume.type = 'button';
  resume.addEventListener('click', () => {
    location.hash = '#/';
    const input = document.getElementById('promptInput');
    if (!input) return;
    input.value = 'devam et';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    document.getElementById('sendBtn')?.click();
    banner.remove();
  });
  const close = el('button', 'resume-close', 'Kapat');
  close.type = 'button';
  close.addEventListener('click', () => banner.remove());
  banner.append(resume, close);
  document.body.append(banner);
}

function renderProof(drawer, wsId, data) {
  const list = el('ul', 'proof-marks');
  for (const mark of data.marks) {
    const row = el('li', mark.state === 'geçti' ? 'ok' : 'bad', `${STATE_MARK[mark.state] || '?'} ${mark.name}: ${mark.state}`);
    row.title = mark.detail;
    list.append(row);
  }
  if (!data.marks.length) list.append(el('li', '', 'Bu proje için henüz kanıt kaydı yok.'));
  const film = el('div', 'proof-film');
  for (const name of data.film) {
    const figure = el('figure');
    const image = el('img');
    image.src = `/api/glass/film/${wsId}/${name}`;
    image.alt = FRAMES[name] || name.replace(/\.png$/, '');
    image.loading = 'lazy';
    figure.append(image, el('figcaption', '', image.alt));
    film.append(figure);
  }
  const parts = [list, film];
  if (data.preview) {
    const link = el('a', 'proof-link', 'Canlı önizlemeyi yeni sekmede aç');
    link.href = data.preview;
    link.target = '_blank';
    link.rel = 'noopener';
    parts.push(link);
  }
  if (data.open.length) parts.push(el('p', 'proof-open', `Açık kalan: ${data.open.join(' · ')}`));
  drawer.replaceChildren(...parts);
}

export function attachGlassTools(card, wsId, onChanged) {
  const bar = el('div', 'glass-bar');
  const proofButton = el('button', 'ide-mode-btn', 'Canlı kanıt');
  const undoButton = el('button', 'ide-mode-btn', 'Geri al');
  const note = el('span', 'glass-note');
  note.setAttribute('role', 'status');
  proofButton.type = 'button';
  undoButton.type = 'button';
  const drawer = el('div', 'proof-drawer');
  drawer.hidden = true;
  proofButton.addEventListener('click', async () => {
    drawer.hidden = !drawer.hidden;
    proofButton.setAttribute('aria-expanded', String(!drawer.hidden));
    if (drawer.hidden) return;
    const res = await safeFetchJson(`/api/glass/proof/${wsId}`);
    if (res.ok) renderProof(drawer, wsId, res.data);
    else drawer.replaceChildren(el('p', '', 'Kanıt okunamadı.'));
  });
  undoButton.addEventListener('click', async () => {
    undoButton.disabled = true;
    const res = await safeFetchJson(`/api/glass/undo/${wsId}`, { method: 'POST' });
    undoButton.disabled = false;
    note.textContent = res.ok ? `Geri alındı: ${res.data.undone} (${res.data.ms} ms)` : (res.data?.detail || 'Geri alınamadı.');
    if (res.ok) await onChanged();
  });
  bar.append(proofButton, undoButton, note);
  card.append(bar, drawer);
}

export function rememberTabs(wsId, state) {
  storageSet(`ide-tabs:${wsId}`, JSON.stringify({ tabs: state.openTabs.slice(0, 12), active: state.activePath, view: state.viewMode }));
}

export function savedTabs(wsId, paths) {
  try {
    const saved = JSON.parse(storageGet(`ide-tabs:${wsId}`) || 'null');
    if (!saved) return null;
    return { tabs: saved.tabs.filter((p) => paths.includes(p)), active: paths.includes(saved.active) ? saved.active : '', view: saved.view };
  } catch {
    return null;
  }
}

export function initGlassBox() {
  startRibbon();
  showUnfinished();
}
