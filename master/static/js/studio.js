// AI Project Studio / Workspace Builder (VS Code / Antigravity-style Explorer + Editor + Live Preview + EXE Builder).
import { api, h } from './util.js';

let activeWsId = null;
let activeWsMeta = null;
let activeTree = [];
let activeFilePath = null;
let previewMode = false;
const collapsedDirs = new Set();

function fileIcon(name, isDir) {
  if (isDir) return '[DIR]';
  const ext = (name.split('.').pop() || '').toLowerCase();
  const map = {
    py: 'PY', html: 'WEB', htm: 'WEB', css: 'CSS', js: '!', ts: 'TS',
    json: 'JSON', md: '', txt: '', exe: 'CFG', yml: 'CFG', yaml: 'CFG',
    sql: '', svg: '', png: '', jpg: '',
  };
  return map[ext] || '';
}

function formatSize(bytes) {
  if (bytes === null || bytes === undefined) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export async function renderStudio(root) {
  root.replaceChildren();
  const shell = h('div', { class: 'studio-shell' });
  root.appendChild(shell);

  // --- Top Bar ---
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
      h('span', { class: 'studio-brand' }, '</> Kod Stüdyosu'),
      wsSelect,
      newFileBtn,
    ),
    h('div', { class: 'studio-topbar-right' },
      saveBtn, previewBtn, buildExeBtn, downloadExeLink, downloadZipLink,
    ),
  );

  // --- 3-Pane IDE Body ---
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
  const previewFrame = h('iframe', { class: 'studio-preview-frame', hidden: true, sandbox: 'allow-scripts allow-same-origin allow-forms allow-modals' });

  const centerPane = h('section', { class: 'studio-center' },
    h('div', { class: 'studio-editor-bar' }, breadcrumb),
    codeArea,
    previewFrame,
  );

  // --- Right AI Prompt & Build Console Pane ---
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

  const bodyGrid = h('div', { class: 'studio-body' }, explorerPane, centerPane, aiPane);
  shell.append(topbar, bodyGrid);

  function appendLog(line, kind = '') {
    const row = h('div', { class: 'studio-log-line' + (kind ? ` log-${kind}` : '') }, line);
    consoleLog.appendChild(row);
    consoleLog.scrollTop = consoleLog.scrollHeight;
  }

  function clearLog(msg = '') {
    consoleLog.replaceChildren();
    if (msg) appendLog(msg);
  }

  function updateToolbar() {
    const hasWs = Boolean(activeWsId && activeWsMeta);
    iterBtn.disabled = !hasWs;
    newFileBtn.disabled = !hasWs;
    downloadZipLink.hidden = !hasWs;
    if (hasWs) {
      downloadZipLink.href = `/api/studio/workspaces/${activeWsId}/download.zip`;
    }
    const hasWeb = Boolean(activeWsMeta?.has_web_preview);
    previewBtn.hidden = !hasWeb;
    previewBtn.textContent = previewMode ? 'Koda Dön' : '▶ Canlı Önizleme';

    const hasPy = activeTree.some((n) => n.name.endsWith('.py')) || activeWsMeta?.project_type === 'game' || activeWsMeta?.project_type === 'desktop';
    buildExeBtn.hidden = !hasPy;

    const hasExe = Boolean(activeWsMeta?.has_exe);
    downloadExeLink.hidden = !hasExe;
    if (hasExe) {
      downloadExeLink.href = `/api/studio/workspaces/${activeWsId}/download-exe`;
      downloadExeLink.textContent = `⬇ ${activeWsMeta.exe_name || 'App.exe'} İndir`;
    }
  }

  function renderTreeNodes(nodes, depth = 0) {
    const frag = document.createDocumentFragment();
    for (const node of nodes) {
      const isDir = node.type === 'dir';
      const isCollapsed = collapsedDirs.has(node.path);
      const item = h('div', {
        class: 'studio-tree-item' + (node.path === activeFilePath ? ' active' : ''),
        style: { paddingLeft: `${10 + depth * 14}px` },
        onClick: () => {
          if (isDir) {
            if (isCollapsed) collapsedDirs.delete(node.path);
            else collapsedDirs.add(node.path);
            renderExplorer();
          } else {
            openFile(node.path);
          }
        },
      },
        h('span', { class: 'tree-chevron' }, isDir ? (isCollapsed ? '▸' : '▾') : ''),
        h('span', { class: 'tree-icon' }, fileIcon(node.name, isDir)),
        h('span', { class: 'tree-name' }, node.name),
        !isDir ? h('span', { class: 'tree-size' }, formatSize(node.size)) : null,
      );
      frag.appendChild(item);
      if (isDir && !isCollapsed && node.children?.length) {
        frag.appendChild(renderTreeNodes(node.children, depth + 1));
      }
    }
    return frag;
  }

  function renderExplorer() {
    treeEl.replaceChildren();
    if (!activeWsMeta) {
      treeEl.append(h('div', { class: 'studio-empty-tree' }, 'Çalışma alanı yok.'));
      return;
    }
    const header = h('div', { class: 'studio-ws-root' }, `▾ ${activeWsMeta.name}`);
    treeEl.appendChild(header);
    treeEl.appendChild(renderTreeNodes(activeTree, 0));
  }

  async function openFile(relPath) {
    if (!activeWsId) return;
    previewMode = false;
    previewFrame.hidden = true;
    codeArea.hidden = false;
    try {
      const data = await api(`/api/studio/workspaces/${activeWsId}/file?path=${encodeURIComponent(relPath)}`);
      activeFilePath = relPath;
      codeArea.value = data.content || '';
      codeArea.readOnly = Boolean(data.binary);
      saveBtn.disabled = Boolean(data.binary);
      breadcrumb.textContent = `${activeWsMeta?.name || activeWsId} / ${relPath} (${formatSize(data.size)})`;
      renderExplorer();
      updateToolbar();
    } catch (err) {
      appendLog('Dosya açılamadı: ' + err.message, 'err');
    }
  }

  async function loadWorkspace(wsId) {
    activeWsId = wsId;
    activeFilePath = null;
    previewMode = false;
    previewFrame.hidden = true;
    codeArea.hidden = false;
    const data = await api(`/api/studio/workspaces/${wsId}/tree`);
    activeWsMeta = data.workspace;
    activeTree = data.tree || [];
    renderExplorer();
    updateToolbar();

    // Auto-open entry point or first text file
    const ep = activeWsMeta.entry_point;
    const flatFiles = [];
    const collect = (nodes) => {
      for (const n of nodes) {
        if (n.type === 'file' && !n.name.endsWith('.exe')) flatFiles.push(n.path);
        else if (n.children) collect(n.children);
      }
    };
    collect(activeTree);
    const firstFile = (ep && flatFiles.includes(ep)) ? ep : flatFiles[0];
    if (firstFile) await openFile(firstFile);
  }

  async function refreshWorkspaces(selectId = null) {
    const data = await api('/api/studio/workspaces');
    const list = data.workspaces || [];
    wsSelect.replaceChildren();
    if (!list.length) {
      wsSelect.append(h('option', { value: '' }, '— Çalışma alanı yok —'));
      activeWsId = null;
      activeWsMeta = null;
      activeTree = [];
      renderExplorer();
      updateToolbar();
      return;
    }
    for (const ws of list) {
      const tag = ws.has_exe ? ' [.EXE]' : (ws.has_web_preview ? ' [WEB]' : '');
      wsSelect.append(h('option', { value: ws.id }, `${ws.name}${tag} (${ws.file_count} dosya)`));
    }
    const target = selectId || (activeWsId && list.some((w) => w.id === activeWsId) ? activeWsId : list[0].id);
    wsSelect.value = target;
    await loadWorkspace(target);
  }

  wsSelect.addEventListener('change', () => {
    if (wsSelect.value) loadWorkspace(wsSelect.value);
  });

  saveBtn.addEventListener('click', async () => {
    if (!activeWsId || !activeFilePath) return;
    saveBtn.disabled = true;
    try {
      await api(`/api/studio/workspaces/${activeWsId}/file`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: activeFilePath, content: codeArea.value }),
      });
      appendLog(`✓ Kaydedildi: ${activeFilePath}`, 'ok');
    } catch (err) {
      appendLog(`Kaydetme hatası: ${err.message}`, 'err');
    } finally {
      saveBtn.disabled = false;
    }
  });

  newFileBtn.addEventListener('click', async () => {
    if (!activeWsId) return;
    const rel = prompt('Yeni dosya yolu (ör. js/utils.js veya game/levels.py):');
    if (!rel || !rel.trim()) return;
    try {
      await api(`/api/studio/workspaces/${activeWsId}/file`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: rel.trim(), content: '' }),
      });
      await loadWorkspace(activeWsId);
      await openFile(rel.trim());
      appendLog(`✓ Yeni dosya oluşturuldu: ${rel.trim()}`, 'ok');
    } catch (err) {
      appendLog(`Dosya oluşturulamadı: ${err.message}`, 'err');
    }
  });

  previewBtn.addEventListener('click', () => {
    if (!activeWsId) return;
    previewMode = !previewMode;
    codeArea.hidden = previewMode;
    previewFrame.hidden = !previewMode;
    if (previewMode) {
      previewFrame.src = `/api/studio/workspaces/${activeWsId}/preview/index.html?t=${Date.now()}`;
      breadcrumb.textContent = `▶ Canlı Önizleme — ${activeWsMeta?.name || activeWsId}`;
    } else if (activeFilePath) {
      breadcrumb.textContent = `${activeWsMeta?.name || activeWsId} / ${activeFilePath}`;
    }
    updateToolbar();
  });

  buildExeBtn.addEventListener('click', async () => {
    if (!activeWsId) return;
    buildExeBtn.disabled = true;
    buildExeBtn.textContent = '⏳ .EXE Derleniyor...';
    clearLog('PyInstaller ile tek dosyalık Windows .EXE derlemesi başlatıldı...');
    try {
      const res = await api(`/api/studio/workspaces/${activeWsId}/build-exe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (res.ok) {
        appendLog(`✓ BAŞARILI: dist/${res.exe_name} (${formatSize(res.exe_size)}) oluşturuldu!`, 'ok');
        await refreshWorkspaces(activeWsId);
      } else {
        appendLog(`✗ HATA: ${res.error}`, 'err');
        if (res.logs) appendLog(res.logs.slice(-1200));
      }
    } catch (err) {
      appendLog(`✗ Derleme hatası: ${err.message}`, 'err');
    } finally {
      buildExeBtn.disabled = false;
      buildExeBtn.textContent = '.EXE Oluştur';
    }
  });

  async function consumeStudioStream(resp) {
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      throw new Error(data.detail || `HTTP ${resp.status}`);
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    let finalWsId = activeWsId;

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
          appendLog(`⏳ ${evt.message}`);
        } else if (evt.type === 'plan') {
          finalWsId = evt.workspace.id;
          appendLog(` Plan hazır: ${evt.workspace.name} (${evt.files.length} dosya)`, 'ok');
        } else if (evt.type === 'file_start') {
          appendLog(`✍ Yazılıyor [${evt.index}/${evt.total}]: ${evt.path}...`);
        } else if (evt.type === 'file_done') {
          appendLog(`✓ Oluşturuldu: ${evt.path} (${formatSize(evt.size)})`, 'ok');
        } else if (evt.type === 'done') {
          finalWsId = evt.workspace.id;
          if (evt.warnings?.length) {
            for (const w of evt.warnings) appendLog(`! ${w}`, 'err');
          }
          appendLog(` Proje hazır! Dosyalar soldaki Explorer ağacında.`, 'ok');
        } else if (evt.type === 'error') {
          appendLog(`✗ Hata: ${evt.message}`, 'err');
        }
      }
    }
    if (finalWsId) await refreshWorkspaces(finalWsId);
  }

  genBtn.addEventListener('click', async () => {
    const promptText = promptBox.value.trim();
    if (!promptText) return;
    genBtn.disabled = true;
    iterBtn.disabled = true;
    clearLog('AI Proje Oluşturucu başlatıldı...');
    try {
      const resp = await fetch('/api/studio/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: promptText, project_type: typeSelect.value }),
      });
      await consumeStudioStream(resp);
    } catch (err) {
      appendLog(`✗ Hata: ${err.message}`, 'err');
    } finally {
      genBtn.disabled = false;
      updateToolbar();
    }
  });

  iterBtn.addEventListener('click', async () => {
    const instr = promptBox.value.trim();
    if (!instr || !activeWsId) return;
    genBtn.disabled = true;
    iterBtn.disabled = true;
    clearLog(`Mevcut proje (${activeWsMeta?.name}) güncelleniyor...`);
    try {
      const resp = await fetch(`/api/studio/workspaces/${activeWsId}/iterate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruction: instr }),
      });
      await consumeStudioStream(resp);
    } catch (err) {
      appendLog(`✗ Hata: ${err.message}`, 'err');
    } finally {
      genBtn.disabled = false;
      updateToolbar();
    }
  });

  await refreshWorkspaces();

  // If launched from the Assistant chat with a project prompt, pre-fill and start automatically!
  const pending = sessionStorage.getItem('studio_pending_prompt');
  if (pending) {
    sessionStorage.removeItem('studio_pending_prompt');
    promptBox.value = pending;
    genBtn.click();
  }
}
