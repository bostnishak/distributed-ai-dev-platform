// Artifact panel (UX-11), file and knowledge manager (UX-12) and read-only share viewer (UX-26).
import { getActiveUserId } from './personal.js';
import { api, formatDateTime, h, loading } from './util.js';

export function downloadText(name, text, type = 'text/markdown') {
  const url = URL.createObjectURL(new Blob([text], { type: `${type};charset=utf-8` }));
  const a = h('a', { href: url, download: name });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

const safeName = (s) => String(s || 'artefakt').replace(/[^\w.-]+/g, '_').slice(0, 60);

// ---------------------------------------------------------------- artifacts

function versionBlock(art, versions) {
  if (!versions.length) return h('p', { class: 'muted' }, 'Henüz eski sürüm yok; bir bölüm düzenlenince önceki hali burada saklanır.');
  const view = h('pre', { class: 'hub-result' });
  const select = h('select', { 'aria-label': 'Sürüm seç' },
    h('option', { value: '' }, `Güncel (v${art.version})`),
    ...versions.map((v) => h('option', { value: String(v.version) }, `v${v.version} · ${formatDateTime(v.saved_at)}`)));
  select.addEventListener('change', () => {
    const v = versions.find((x) => String(x.version) === select.value);
    view.textContent = v ? v.content : '';
    view.hidden = !v;
  });
  view.hidden = true;
  return h('div', null, select, view);
}

async function openArtifact(art, slot) {
  slot.replaceChildren(loading());
  let versions = [];
  try { versions = (await api(`/api/orchestrator/artifacts/${encodeURIComponent(art.artifact_id)}/versions`)).versions; } catch { /* versions are optional */ }
  const status = h('span', { class: 'hub-status' });
  const sections = art.sections.length ? art.sections : [art.content];
  const rows = sections.map((text, index) => {
    const area = h('textarea', { rows: Math.min(12, Math.max(3, text.split('\n').length + 1)), 'aria-label': `Bölüm ${index + 1}` });
    area.value = text;
    const save = h('button', { class: 'btn', type: 'button' }, 'Bu bölümü kaydet');
    save.addEventListener('click', async () => {
      save.disabled = true;
      try {
        const updated = await api(`/api/orchestrator/artifacts/${encodeURIComponent(art.artifact_id)}/edit`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ section_index: index, content: area.value }),
        });
        status.textContent = `Kaydedildi (v${updated.version})`;
        status.className = 'hub-status ok';
        Object.assign(art, updated);
        await openArtifact(art, slot);
      } catch (err) {
        status.textContent = err.message;
        status.className = 'hub-status err';
        save.disabled = false;
      }
    });
    return h('div', { class: 'hub-field' }, h('label', { class: 'hub-label' }, `Bölüm ${index + 1}`), area, h('div', { class: 'card-actions' }, save));
  });
  const exportBtn = h('button', { class: 'btn', type: 'button', onClick: () => downloadText(`${safeName(art.title)}.md`, art.content || sections.join('\n\n')) }, 'Markdown olarak indir');
  slot.replaceChildren(
    h('h2', null, art.title, h('span', { class: 'hub-count' }, ` v${art.version} · ${art.kind}`)),
    h('div', { class: 'card-actions' }, exportBtn, status),
    ...rows,
    h('h3', null, 'Sürüm geçmişi'), versionBlock(art, versions));
}

export async function renderArtifacts(root, ctx) {
  root.replaceChildren(loading());
  let list = [];
  try { list = (await api(`/api/orchestrator/artifacts?user_id=${encodeURIComponent(getActiveUserId())}`)).artifacts; } catch (err) {
    root.replaceChildren(h('div', { class: 'card error' }, `Artefaktlar alınamadı: ${err.message}`));
    return;
  }
  if (!ctx.isCurrent()) return;
  const detail = h('div', { class: 'card' }, h('p', { class: 'muted' }, 'Soldan bir artefakt seçin.'));
  const items = list.map((a) => h('button', { type: 'button', class: 'hub-art-item', onClick: () => openArtifact(a, detail) },
    h('strong', null, a.title), h('span', { class: 'muted' }, ` ${a.kind} · v${a.version} · ${formatDateTime(a.updated_at)}`)));
  root.replaceChildren(
    h('h1', null, 'Artefaktlar'),
    h('div', { class: 'card note' }, 'Asistanın ürettiği belgeler, sunumlar ve raporlar. Sohbeti silseniz de burada kalır; her düzenleme önceki sürümü saklar.'),
    list.length ? h('div', { class: 'hub-split' }, h('div', { class: 'hub-art-list' }, ...items), detail)
      : h('div', { class: 'card' }, 'Henüz artefakt yok. Asistandan bir belge veya sunum isteyin.'));
}

// ---------------------------------------------------------------- files

async function uploadOne(file, collectionId, userId) {
  const body = new FormData();
  body.append('file', file);
  body.append('collection_id', collectionId);
  body.append('user_id', userId);
  const resp = await fetch('/api/rag/ingest-file', { method: 'POST', body });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `HTTP ${resp.status}`);
  return data;
}

export async function renderFiles(root, ctx) {
  const userId = getActiveUserId();
  root.replaceChildren(loading());
  const state = { collections: [], current: 'default' };
  try { state.collections = (await api(`/api/rag/collections?user_id=${encodeURIComponent(userId)}`)).collections || []; } catch { /* empty list */ }
  if (!ctx.isCurrent()) return;
  const select = h('select', { 'aria-label': 'Koleksiyon' });
  const docs = h('div', { class: 'hub-docs' });
  const queue = h('div', { class: 'hub-queue' });
  const overall = h('progress', { max: 1, value: 0, hidden: true, 'aria-label': 'Toplam yükleme ilerlemesi' });

  const fillSelect = () => {
    const ids = new Set(['default', ...state.collections.map((c) => c.collection_id)]);
    select.replaceChildren(...[...ids].map((id) => h('option', { value: id }, id)));
    select.value = state.current;
  };
  const loadDocs = async () => {
    docs.replaceChildren(loading());
    try {
      const { documents } = await api(`/api/rag/collections/${encodeURIComponent(state.current)}/documents?user_id=${encodeURIComponent(userId)}`);
      docs.replaceChildren(...(documents.length ? documents.map((d) => h('div', { class: 'hub-doc' },
        h('span', null, d.title || d.doc_id), d.chunk_count != null ? h('span', { class: 'muted' }, ` ${d.chunk_count} parça`) : null,
        h('button', { class: 'btn', type: 'button', onClick: async () => {
          if (!window.confirm(`${d.title || d.doc_id} silinsin mi?`)) return;
          await api(`/api/rag/documents/${encodeURIComponent(d.doc_id)}`, { method: 'DELETE' });
          loadDocs();
        } }, 'Sil'))) : [h('p', { class: 'muted' }, 'Bu koleksiyonda belge yok.')]));
    } catch (err) {
      docs.replaceChildren(h('div', { class: 'card error' }, err.message));
    }
  };
  select.addEventListener('change', () => { state.current = select.value; loadDocs(); });

  const picker = h('input', { type: 'file', multiple: true, accept: '.pdf,.docx,.pptx,.xlsx,.html,.htm,.md,.txt,.csv,.json', 'aria-label': 'Dosya seç' });
  picker.addEventListener('change', async () => {
    const files = [...picker.files];
    if (!files.length) return;
    overall.hidden = false;
    overall.value = 0;
    queue.replaceChildren();
    let done = 0;
    for (const file of files) {
      const status = h('span', { class: 'hub-status' }, 'yükleniyor…');
      queue.append(h('div', { class: 'hub-doc' }, h('span', null, file.name), status));
      try {
        await uploadOne(file, state.current, userId);
        status.textContent = 'dizinlendi';
        status.className = 'hub-status ok';
      } catch (err) {
        status.textContent = `hata: ${err.message}`;
        status.className = 'hub-status err';
      }
      done += 1;
      overall.value = done / files.length;
    }
    picker.value = '';
    loadDocs();
  });

  const newName = h('input', { type: 'text', placeholder: 'Yeni koleksiyon adı', 'aria-label': 'Yeni koleksiyon adı' });
  const create = h('button', { class: 'btn', type: 'button' }, 'Koleksiyon oluştur');
  create.addEventListener('click', async () => {
    const id = newName.value.trim().toLowerCase().replace(/[^a-z0-9_-]+/g, '-').slice(0, 60);
    if (!id) return;
    await api('/api/rag/collections', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ collection_id: id, name: newName.value.trim(), user_id: userId }) });
    state.collections.push({ collection_id: id });
    state.current = id;
    newName.value = '';
    fillSelect();
    loadDocs();
  });

  fillSelect();
  loadDocs();
  root.replaceChildren(
    h('h1', null, 'Dosyalar ve bilgi tabanı'),
    h('div', { class: 'card note' }, 'Yüklediğiniz belgeler yerelde dizinlenir ve asistan yanıtlarında kaynak olarak kullanılır. PDF, DOCX, PPTX, XLSX, HTML ve metin dosyaları desteklenir (en fazla 25 MB).'),
    h('div', { class: 'card' }, h('div', { class: 'hub-toolbar' }, select, newName, create), picker, overall, queue),
    h('div', { class: 'card' }, h('h2', null, 'Belgeler'), docs));
}

// ---------------------------------------------------------------- share viewer

export async function renderShare(root, shareId) {
  root.replaceChildren(loading());
  try {
    const share = await api(`/api/ux/shares/${encodeURIComponent(shareId)}?user_id=${encodeURIComponent(getActiveUserId())}`);
    root.replaceChildren(h('h1', null, share.title), h('div', { class: 'card note' }, 'Salt okunur paylaşım. Gizli bilgiler paylaşılmadan önce maskelenmiştir.'),
      h('pre', { class: 'hub-result' }, share.content));
  } catch (err) {
    root.replaceChildren(h('div', { class: 'card error' }, err.message));
  }
}
