// Studio UI panes, explorer tree helpers, and SSE generation stream consumer.
import { h } from './util.js';

export function fileIcon(name, isDir) {
  if (isDir) return '[DIR]';
  const ext = (name.split('.').pop() || '').toLowerCase();
  const map = {
    py: 'PY', html: 'WEB', htm: 'WEB', css: 'CSS', js: '!', ts: 'TS',
    json: 'JSON', md: '', txt: '', exe: 'CFG', yml: 'CFG', yaml: 'CFG',
    sql: '', svg: '', png: '', jpg: '',
  };
  return map[ext] || '';
}

export function formatSize(bytes) {
  if (bytes === null || bytes === undefined) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function buildStudioTopbar() {
  const wsSelect = h('select', { class: 'studio-select' });
  const newFileBtn = h('button', { type: 'button', class: 'btn studio-btn-sm' }, '＋ Dosya');
  const saveBtn = h('button', { type: 'button', class: 'btn studio-btn-sm', disabled: true }, 'Kaydet');
  const previewBtn = h('button', { type: 'button', class: 'btn studio-btn-sm', hidden: true }, '▶ Canlı Önizleme');
  const buildExeBtn = h('button', { type: 'button', class: 'btn btn-primary studio-btn-sm', hidden: true }, '.EXE Oluştur');
  const downloadExeLink = h('a', { class: 'btn studio-btn-exe studio-btn-sm', hidden: true, download: '' }, '⬇ .EXE İndir');
  const downloadZipLink = h('a', { class: 'btn studio-btn-sm', hidden: true, download: '' }, '⬇ ZIP İndir');
  const breadcrumb = h('span', { class: 'studio-breadcrumb' }, 'Bir çalışma alanı seçin veya yeni proje oluşturun');

  const topbar = h('div', { class: 'studio-topbar' },
    h('div', { class: 'studio-topbar-left' },
      h('h1', { class: 'studio-brand', style: { margin: 0, fontSize: 'inherit' } }, '</> Kod Stüdyosu'),
      wsSelect,
      newFileBtn,
    ),
    h('div', { class: 'studio-topbar-right' },
      saveBtn, previewBtn, buildExeBtn, downloadExeLink, downloadZipLink,
    ),
  );
  return { topbar, wsSelect, newFileBtn, saveBtn, previewBtn, buildExeBtn, downloadExeLink, downloadZipLink, breadcrumb };
}

function buildAiPane() {
  const typeSelect = h('select', { class: 'studio-select', style: { width: '100%' } },
    h('option', { value: 'auto' }, 'Proje Türü: Otomatik Algıla'),
    h('option', { value: 'web' }, 'Web Sitesi / E-Ticaret (HTML/CSS/JS)'),
    h('option', { value: 'game' }, 'Python Oyunu (.EXE Derlenebilir)'),
    h('option', { value: 'desktop' }, 'Masaüstü Uygulaması (.EXE)'),
    h('option', { value: 'cli' }, 'Python Otomasyon / CLI Aracı'),
  );
  const promptBox = h('textarea', {
    class: 'studio-prompt',
    rows: 6,
    placeholder: 'Kapsamlı proje isteğini yaz...\nÖrnek: "CNC yedek parçaları satan modern koyu temalı bir e-ticaret sitesi yap. Kategori filtresi, arama, ürün kartları, canlı sepet çekmecesi ve sipariş özeti olsun."\nveya: "Python ile oynanabilir bir uzay gemisi arcade oyunu yap, skor, seviye ve can sistemi olsun."',
  });
  const genBtn = h('button', { type: 'button', class: 'btn btn-primary', style: { flex: 1 } }, 'Yeni Proje Oluştur');
  const iterBtn = h('button', { type: 'button', class: 'btn', style: { flex: 1 }, disabled: true }, 'Mevcut Projeyi Geliştir');
  const consoleLog = h('div', { class: 'studio-console' }, 'Hazır. Bir proje seçin veya AI ile sıfırdan oluşturun.');

  const quickPresets = h('div', { class: 'studio-presets' },
    h('button', {
      type: 'button', class: 'studio-preset-chip',
      onClick: () => {
        typeSelect.value = 'web';
        promptBox.value = 'Modern, profesyonel bir e-ticaret sitesi oluştur: ürün kataloğu, kategori filtreleme, anlık arama, sepet çekmecesi (ekle/çıkar/adet güncelle), indirim kuponu ve ödeme özeti modalı olsun.';
      },
    }, ' E-Ticaret Promptu'),
    h('button', {
      type: 'button', class: 'studio-preset-chip',
      onClick: () => {
        typeSelect.value = 'game';
        promptBox.value = 'Python tkinter Canvas ile neon temalı, akıcı oynanabilir bir Arcade Yılan / Uzay Oyunu yap. Başlangıç ekranı, skor, en yüksek skor, hızlanan seviyeler, duraklatma (P) ve yeniden başlatma olsun. PyInstaller ile .exe derlemeye uygun modüler dosya yapısında olsun.';
      },
    }, ' Oyun (.EXE) Promptu'),
  );

  const aiPane = h('aside', { class: 'studio-ai-pane' },
    h('div', { class: 'studio-pane-title' }, 'AI PROJE OLUŞTURUCU'),
    h('div', { class: 'studio-ai-body' },
      typeSelect,
      quickPresets,
      promptBox,
      h('div', { class: 'studio-ai-actions' }, genBtn, iterBtn),
      h('div', { class: 'studio-pane-title', style: { marginTop: '12px', padding: '6px 0' } }, 'DERLEME & OLUŞTURMA GÜNLÜĞÜ'),
      consoleLog,
    ),
  );
  return { aiPane, typeSelect, promptBox, genBtn, iterBtn, consoleLog };
}

export function buildStudioPanes(breadcrumb) {
  const explorerPane = h('aside', { class: 'studio-explorer' },
    h('div', { class: 'studio-pane-title' }, 'EXPLORER'),
    h('div', { class: 'studio-tree', id: 'studioTree' }),
  );
  const treeEl = explorerPane.querySelector('#studioTree');

  const codeArea = h('textarea', {
    class: 'studio-editor',
    spellcheck: 'false',
    placeholder: 'Soldaki dosya gezgininden bir dosya seçin veya sağdaki AI panelinden eksiksiz bir proje oluşturun...',
  });
  const previewFrame = h('iframe', {
    class: 'studio-preview-frame',
    hidden: true,
    sandbox: 'allow-scripts allow-same-origin allow-forms allow-modals',
  });
  const centerPane = h('section', { class: 'studio-center' },
    h('div', { class: 'studio-editor-bar' }, breadcrumb),
    codeArea,
    previewFrame,
  );

  const ai = buildAiPane();
  const bodyGrid = h('div', { class: 'studio-body' }, explorerPane, centerPane, ai.aiPane);
  return { bodyGrid, treeEl, codeArea, previewFrame, ...ai };
}

export function renderStudioTreeNodes(nodes, state, onToggleDir, onOpenFile, depth = 0) {
  const frag = document.createDocumentFragment();
  for (const node of nodes) {
    const isDir = node.type === 'dir';
    const isCollapsed = state.collapsedDirs.has(node.path);
    const item = h('div', {
      class: 'studio-tree-item' + (node.path === state.activeFilePath ? ' active' : ''),
      style: { paddingLeft: `${10 + depth * 14}px` },
      onClick: () => (isDir ? onToggleDir(node.path, isCollapsed) : onOpenFile(node.path)),
    },
      h('span', { class: 'tree-chevron' }, isDir ? (isCollapsed ? '▸' : '▾') : ''),
      h('span', { class: 'tree-icon' }, fileIcon(node.name, isDir)),
      h('span', { class: 'tree-name' }, node.name),
      !isDir ? h('span', { class: 'tree-size' }, formatSize(node.size)) : null,
    );
    frag.appendChild(item);
    if (isDir && !isCollapsed && node.children?.length) {
      frag.appendChild(renderStudioTreeNodes(node.children, state, onToggleDir, onOpenFile, depth + 1));
    }
  }
  return frag;
}

export function collectStudioFiles(nodes, out = []) {
  for (const n of nodes) {
    if (n.type === 'file' && !n.name.endsWith('.exe')) out.push(n.path);
    else if (n.children) collectStudioFiles(n.children, out);
  }
  return out;
}

export async function consumeStudioStream(resp, state, hooks) {
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${resp.status}`);
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  let finalWsId = state.activeWsId;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split('\n');
    buf = lines.pop();
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      let evt;
      try { evt = JSON.parse(line.slice(6)); } catch { continue; }
      if (evt.type === 'status') {
        hooks.appendLog(`... ${evt.message}`);
      } else if (evt.type === 'plan') {
        finalWsId = evt.workspace.id;
        hooks.appendLog(`Plan hazır: ${evt.workspace.name} (${evt.files.length} dosya)`, 'ok');
      } else if (evt.type === 'file_start') {
        hooks.appendLog(`Yazılıyor [${evt.index}/${evt.total}]: ${evt.path}...`);
      } else if (evt.type === 'file_done') {
        hooks.appendLog(`✓ Oluşturuldu: ${evt.path} (${formatSize(evt.size)})`, 'ok');
      } else if (evt.type === 'done') {
        finalWsId = evt.workspace.id;
        if (evt.warnings?.length) {
          for (const w of evt.warnings) hooks.appendLog(`! ${w}`, 'err');
        }
        hooks.appendLog('Proje hazır! Dosyalar soldaki Explorer ağacında.', 'ok');
      } else if (evt.type === 'error') {
        hooks.appendLog(`✗ Hata: ${evt.message}`, 'err');
      }
    }
  }
  if (finalWsId) await hooks.refreshWorkspaces(finalWsId);
}
