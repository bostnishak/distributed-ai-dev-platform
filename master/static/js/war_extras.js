// War room extras: the proofs behind a project and, for a branch, what differs from the original.
import { safeFetchJson } from './storage.js';

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function listBlock(title, lines) {
  const block = el('div');
  if (!lines.length) return block;
  const list = el('ul');
  list.append(...lines.map((line) => el('li', line)));
  block.append(el('strong', title), list);
  return block;
}

export async function showProofs(wsId, target) {
  const res = await safeFetchJson(`/api/runs/proof/${encodeURIComponent(wsId)}`);
  if (!res.ok) { target.replaceChildren(el('div', 'Kanıt okunamadı.')); return; }
  const data = res.data;
  const stages = Object.entries(data.stages || {}).map(([stage, [state, detail]]) => `${stage}: ${state} — ${detail}`);
  const empty = !stages.length && !data.evidence.length && !data.verified.length && !data.open.length;
  target.replaceChildren(
    ...(empty ? [el('div', 'Bu proje için kayıtlı kanıt yok.')] : []),
    listBlock('Teslim aşamaları', stages), listBlock('Biçimsel, mutasyon ve özellik denetimleri', data.evidence),
    listBlock('Doğrulanan', data.verified), listBlock('Açık', data.open),
  );
}

export async function showDiff(wsId, target) {
  const res = await safeFetchJson(`/api/runs/compare/${encodeURIComponent(wsId)}`);
  if (!res.ok) { target.replaceChildren(el('div', (res.data && res.data.detail) || 'Karşılaştırılamadı.')); return; }
  const files = res.data.files;
  target.replaceChildren(el('div', files.length ? `${files.length} dosya farklı (asıl: ${res.data.origin})` : 'Asıl projeyle fark yok.'));
  files.forEach((file) => {
    const block = el('details');
    block.append(el('summary', `${file.status}: ${file.path}`), el('pre', file.diff, 'war-diff'));
    target.append(block);
  });
}

// Two buttons for the chosen project; results are written into their own area.
export function extraButtons(wsId) {
  const output = el('div', undefined, 'war-small');
  const proofs = el('button', 'Kanıtları göster');
  proofs.type = 'button';
  proofs.addEventListener('click', () => showProofs(wsId, output));
  const diff = el('button', 'Asıl ile karşılaştır');
  diff.type = 'button';
  diff.addEventListener('click', () => showDiff(wsId, output));
  return [proofs, diff, output];
}
