// UX-02 Modular Split: Inline IDE Workbench card builder (<= 500 lines).
import {
  createIterationBar,
  createTerminalDrawer,
  detectLangLabel,
  highlightCodeHtml,
  wsSvgIcon,
} from './assistant_ide_render.js';
import { setSanitizedHtml } from './sanitizer.js';
import { safeFetchJson } from './storage.js';
import { uiPrompt } from './ui_dialog.js';
import { mountOfflineCodeEditor } from '../vendor/code_editor.js';

export function buildInlineWorkspaceCard(wsMeta, wsTree) {
  const wsId = wsMeta.id;
  const card = document.createElement('div');
  card.className = 'ide-workbench';

  let currentTree = wsTree || [];
  let viewMode = 'code';
  let editMode = false;
  let activePath = null;
  let activeContent = '';
  const openTabs = [];
  const fileCache = new Map();
  const collapsedFolders = new Set();

  const titlebar = document.createElement('div');
  titlebar.className = 'ide-titlebar';
  const titleLeft = document.createElement('div');
  titleLeft.className = 'ide-title-left';
  const dots = document.createElement('div');
  dots.className = 'ide-window-dots';
  setSanitizedHtml(dots, '<span class="dot-r"></span><span class="dot-y"></span><span class="dot-g"></span>');
  const projTitle = document.createElement('span');
  projTitle.className = 'ide-proj-name';
  projTitle.textContent = wsMeta.name || wsId;
  const typeBadge = document.createElement('span');
  typeBadge.className = 'ide-type-badge';
  typeBadge.textContent = wsMeta.has_exe ? 'WINDOWS .EXE' : (wsMeta.has_web_preview ? 'WEB APP' : (wsMeta.project_type || 'PROJECT').toUpperCase());
  titleLeft.append(dots, projTitle, typeBadge);

  const modeGroup = document.createElement('div');
  modeGroup.className = 'ide-mode-group';
  const mkMode = (txt, active = false) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'ide-mode-btn' + (active ? ' active' : '');
    b.textContent = txt;
    return b;
  };
  const btnModeCode = mkMode('</> Kod', true);
  const btnModePrev = mkMode('▶ Önizleme');
  const btnModeSplit = mkMode('◫ Bölünmüş');
  if (wsMeta.has_web_preview) modeGroup.append(btnModeCode, btnModePrev, btnModeSplit);

  const actions = document.createElement('div');
  actions.className = 'ide-actions';

  function appendExeButtons(exeName) {
    const launchBtn = document.createElement('button');
    launchBtn.type = 'button';
    launchBtn.className = 'ide-btn exe';
    launchBtn.textContent = 'EXE Çalıştır';
    launchBtn.addEventListener('click', async () => {
      launchBtn.disabled = true;
      launchBtn.textContent = 'Açılıyor...';
      const r = await safeFetchJson(`/api/studio/workspaces/${wsId}/launch-exe`, { method: 'POST' });
      launchBtn.textContent = r.ok ? 'Açıldı' : 'Açılamadı';
      const RESET_MS = 1800;
      setTimeout(() => { launchBtn.disabled = false; launchBtn.textContent = 'EXE Çalıştır'; }, RESET_MS);
    });
    const dlExe = document.createElement('a');
    dlExe.className = 'ide-btn';
    dlExe.href = `/api/studio/workspaces/${wsId}/download-exe`;
    dlExe.download = '';
    dlExe.textContent = `${exeName || 'App.exe'} İndir`;
    actions.prepend(dlExe);
    actions.prepend(launchBtn);
  }

  const hasPy = currentTree.some((n) => n.name && n.name.endsWith('.py')) || wsMeta.project_type === 'game' || wsMeta.project_type === 'desktop';
  if (hasPy && !wsMeta.has_exe) {
    const exeBtn = document.createElement('button');
    exeBtn.type = 'button';
    exeBtn.className = 'ide-btn primary';
    exeBtn.textContent = 'EXE Derle';
    exeBtn.addEventListener('click', async () => {
      exeBtn.disabled = true;
      exeBtn.textContent = 'Derleniyor...';
      const r = await safeFetchJson(`/api/studio/workspaces/${wsId}/build-exe`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
      });
      if (r.ok && r.data && r.data.ok) {
        exeBtn.remove();
        typeBadge.textContent = 'WINDOWS .EXE';
        appendExeButtons(r.data.exe_name);
      } else { exeBtn.textContent = 'Hata'; }
    });
    actions.appendChild(exeBtn);
  }
  if (wsMeta.has_exe) appendExeButtons(wsMeta.exe_name);

  const zipLink = document.createElement('a');
  zipLink.className = 'ide-btn';
  zipLink.href = `/api/studio/workspaces/${wsId}/download.zip`;
  zipLink.download = '';
  zipLink.textContent = 'ZIP İndir';
  actions.appendChild(zipLink);

  const verSelect = document.createElement('select');
  verSelect.className = 'ide-btn';
  verSelect.title = 'Sürüm Geçmişi (Geri Al)';
  verSelect.hidden = true;
  async function refreshVersions() {
    const r = await safeFetchJson(`/api/studio/workspaces/${wsId}/history`);
    if (!r.ok || !r.data) return;
    const vers = r.data.versions || [];
    if (vers.length > 0) {
      verSelect.replaceChildren();
      for (const v of vers) {
        const opt = document.createElement('option');
        opt.value = v.version;
        opt.textContent = `${v.version}: ${(v.label || '').slice(0, 22)}`;
        verSelect.appendChild(opt);
      }
      verSelect.hidden = false;
    }
  }
  verSelect.addEventListener('change', async () => {
    const v = verSelect.value;
    if (!v) return;
    const r = await safeFetchJson(`/api/studio/workspaces/${wsId}/restore/${v}`, { method: 'POST' });
    if (r.ok && r.data) {
      currentTree = r.data.tree || currentTree;
      fileCache.clear();
      renderTree();
      if (activePath) selectFile(activePath);
    }
  });
  actions.appendChild(verSelect);
  refreshVersions();

  const expandBtn = document.createElement('button');
  expandBtn.type = 'button';
  expandBtn.className = 'ide-btn icon-only';
  expandBtn.title = 'Tam Ekran IDE Görünümü';
  expandBtn.textContent = '⤢';
  expandBtn.addEventListener('click', () => {
    const isMax = card.classList.toggle('ide-fullscreen');
    expandBtn.textContent = isMax ? '✕ Kapat' : '⤢';
  });
  actions.appendChild(expandBtn);
  titlebar.append(titleLeft, modeGroup, actions);
  card.appendChild(titlebar);

  const mainGrid = document.createElement('div');
  mainGrid.className = 'ide-main';
  const sidebar = document.createElement('aside');
  sidebar.className = 'ide-sidebar';
  const sideHeader = document.createElement('div');
  sideHeader.className = 'ide-side-header';
  const sideTitle = document.createElement('span');
  sideTitle.textContent = 'EXPLORER';
  const newFileBtn = document.createElement('button');
  newFileBtn.type = 'button';
  newFileBtn.className = 'ide-icon-btn';
  newFileBtn.title = 'Yeni Dosya Oluştur';
  newFileBtn.textContent = '＋';
  sideHeader.append(sideTitle, newFileBtn);
  const rootHeader = document.createElement('div');
  rootHeader.className = 'ide-root-label';
  setSanitizedHtml(rootHeader, `<span class="ide-chev">▾</span> <span>${(wsMeta.name || wsId).toUpperCase()}</span>`);
  const treeContainer = document.createElement('div');
  treeContainer.className = 'ide-tree';
  sidebar.append(sideHeader, rootHeader, treeContainer);

  const surface = document.createElement('div');
  surface.className = 'ide-surface';
  const codePane = document.createElement('div');
  codePane.className = 'ide-code-pane';
  const tabBar = document.createElement('div');
  tabBar.className = 'ide-tabbar';
  const subBar = document.createElement('div');
  subBar.className = 'ide-subbar';
  const breadcrumb = document.createElement('div');
  breadcrumb.className = 'ide-breadcrumb';
  const editorTools = document.createElement('div');
  editorTools.className = 'ide-editor-tools';

  const mkTool = (txt, cls = 'ide-tool-btn') => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = cls;
    b.textContent = txt;
    return b;
  };
  const copyCodeBtn = mkTool('Kopyala');
  const diffToggleBtn = mkTool('Diff');
  const secScanBtn = mkTool('Güvenlik & AST');
  const searchWsBtn = mkTool('Ara');
  const gitWsBtn = mkTool('Git');
  const termToggleBtn = mkTool('Terminal');
  const editToggleBtn = mkTool('Düzenle');
  const saveFileBtn = mkTool('Kaydet', 'ide-tool-btn primary');
  saveFileBtn.hidden = true;
  editorTools.append(copyCodeBtn, diffToggleBtn, secScanBtn, searchWsBtn, gitWsBtn, termToggleBtn, editToggleBtn, saveFileBtn);
  subBar.append(breadcrumb, editorTools);

  const codeScroll = document.createElement('div');
  codeScroll.className = 'ide-code-scroll';
  const gutter = document.createElement('div');
  gutter.className = 'ide-gutter';
  const codeBlock = document.createElement('pre');
  codeBlock.className = 'ide-code-content';
  const rawTextarea = document.createElement('textarea');
  rawTextarea.className = 'ide-raw-editor';
  rawTextarea.spellcheck = false;
  rawTextarea.hidden = true;
  mountOfflineCodeEditor(rawTextarea, { onSave: () => saveFileBtn.click() });
  codeScroll.append(gutter, codeBlock, rawTextarea);
  codePane.append(tabBar, subBar, codeScroll);

  const previewPane = document.createElement('div');
  previewPane.className = 'ide-preview-pane';
  previewPane.hidden = true;
  const browserBar = document.createElement('div');
  browserBar.className = 'ide-browser-bar';
  const refreshBtn = document.createElement('button');
  refreshBtn.type = 'button';
  refreshBtn.className = 'ide-browser-btn';
  refreshBtn.title = 'Önizlemeyi Yenile';
  refreshBtn.textContent = '↻';
  const urlPill = document.createElement('div');
  urlPill.className = 'ide-url-pill';
  urlPill.textContent = `localhost:8000/workspaces/${wsId}/preview/index.html`;
  const extLink = document.createElement('a');
  extLink.className = 'ide-browser-btn';
  extLink.href = `/api/studio/workspaces/${wsId}/preview/index.html`;
  extLink.target = '_blank';
  extLink.title = 'Yeni Sekmede Aç';
  extLink.textContent = '↗';
  browserBar.append(refreshBtn, urlPill, extLink);

  const iframe = document.createElement('iframe');
  iframe.className = 'ide-preview-iframe';
  iframe.setAttribute('sandbox', 'allow-scripts allow-forms');
  refreshBtn.addEventListener('click', () => { iframe.src = `/api/studio/workspaces/${wsId}/preview/index.html?t=${Date.now()}`; });
  previewPane.append(browserBar, iframe);
  surface.append(codePane, previewPane);
  mainGrid.append(sidebar, surface);
  card.appendChild(mainGrid);

  card.appendChild(createTerminalDrawer(wsId, termToggleBtn, gitWsBtn, searchWsBtn));

  const statusBar = document.createElement('div');
  statusBar.className = 'ide-statusbar';
  const statusLeft = document.createElement('div');
  statusLeft.className = 'ide-status-side';
  setSanitizedHtml(statusLeft, '<span>⎇ main</span><span>✓ 0 hata</span>');
  const statusRight = document.createElement('div');
  statusRight.className = 'ide-status-side';
  const statusLines = document.createElement('span');
  statusLines.textContent = '0 satır';
  const statusLang = document.createElement('span');
  statusLang.textContent = 'UTF-8';
  statusRight.append(statusLines, statusLang);
  statusBar.append(statusLeft, statusRight);

  function setViewMode(mode) {
    viewMode = mode;
    btnModeCode.classList.toggle('active', mode === 'code');
    btnModePrev.classList.toggle('active', mode === 'preview');
    btnModeSplit.classList.toggle('active', mode === 'split');
    surface.classList.toggle('split-view', mode === 'split');
    codePane.hidden = mode === 'preview';
    previewPane.hidden = mode === 'code';
    if ((mode === 'preview' || mode === 'split') && !iframe.getAttribute('src')) {
      iframe.src = `/api/studio/workspaces/${wsId}/preview/index.html?t=${Date.now()}`;
    }
  }
  btnModeCode.addEventListener('click', () => setViewMode('code'));
  btnModePrev.addEventListener('click', () => { iframe.src = `/api/studio/workspaces/${wsId}/preview/index.html?t=${Date.now()}`; setViewMode('preview'); });
  btnModeSplit.addEventListener('click', () => { iframe.src = `/api/studio/workspaces/${wsId}/preview/index.html?t=${Date.now()}`; setViewMode('split'); });

  function renderCodeView(content, path) {
    activeContent = content || '';
    const lines = activeContent.split('\n');
    setSanitizedHtml(gutter, lines.map((_, i) => `<div>${i + 1}</div>`).join(''));
    setSanitizedHtml(codeBlock, highlightCodeHtml(activeContent, path));
    rawTextarea.value = activeContent;
    statusLines.textContent = `${lines.length} satır`;
    statusLang.textContent = `${detectLangLabel(path)} · UTF-8`;
    setSanitizedHtml(breadcrumb, `<span class="bc-root">${wsMeta.name || wsId}</span> › ` + (path || '').split('/').map((p) => `<span>${p}</span>`).join(' › '));
  }

  function renderTabs() {
    tabBar.replaceChildren();
    for (const p of openTabs) {
      const fname = p.split('/').pop();
      const tab = document.createElement('div');
      tab.className = 'ide-tab' + (p === activePath ? ' active' : '');
      const iconSpan = document.createElement('span');
      setSanitizedHtml(iconSpan, wsSvgIcon(fname, false));
      const nameSpan = document.createElement('span');
      nameSpan.textContent = fname;
      const closeSpan = document.createElement('span');
      closeSpan.className = 'ide-tab-close';
      closeSpan.textContent = '×';
      closeSpan.addEventListener('click', (e) => {
        e.stopPropagation();
        const idx = openTabs.indexOf(p);
        if (idx >= 0) openTabs.splice(idx, 1);
        if (activePath === p) {
          const next = openTabs[openTabs.length - 1];
          if (next) selectFile(next);
          else { activePath = null; renderTabs(); renderCodeView('', ''); }
        } else renderTabs();
      });
      tab.append(iconSpan, nameSpan, closeSpan);
      tab.addEventListener('click', () => selectFile(p));
      tabBar.appendChild(tab);
    }
  }

  async function selectFile(path) {
    activePath = path;
    if (!openTabs.includes(path)) openTabs.push(path);
    if (viewMode === 'preview') setViewMode('code');
    renderTabs();
    renderTree();
    if (fileCache.has(path)) { renderCodeView(fileCache.get(path), path); return; }
    renderCodeView('// Yükleniyor...', path);
    const r = await safeFetchJson(`/api/studio/workspaces/${wsId}/file?path=${encodeURIComponent(path)}`);
    if (!r.ok) { renderCodeView(`// Dosya okunamadı: ${r.error || r.status}`, path); return; }
    const text = (r.data && r.data.content) || '';
    fileCache.set(path, text);
    if (activePath === path) renderCodeView(text, path);
  }

  function renderTree() {
    treeContainer.replaceChildren();
    function walk(nodes, depth = 0) {
      for (const node of nodes || []) {
        const isDir = node.type === 'dir';
        const isCollapsed = collapsedFolders.has(node.path);
        const row = document.createElement('div');
        row.className = 'ide-tree-row' + (!isDir && node.path === activePath ? ' active' : '');
        row.style.paddingLeft = `${10 + depth * 14}px`;
        const chev = isDir ? `<span class="ide-chev">${isCollapsed ? '▸' : '▾'}</span>` : '<span class="ide-chev"></span>';
        setSanitizedHtml(row, `${chev}${wsSvgIcon(node.name, isDir, !isCollapsed)}<span class="ide-node-name">${node.name}</span>`);
        row.addEventListener('click', () => {
          if (isDir) {
            if (isCollapsed) collapsedFolders.delete(node.path);
            else collapsedFolders.add(node.path);
            renderTree();
          } else selectFile(node.path);
        });
        treeContainer.appendChild(row);
        if (isDir && !isCollapsed && node.children) walk(node.children, depth + 1);
      }
    }
    walk(currentTree, 0);
  }

  copyCodeBtn.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(editMode ? rawTextarea.value : activeContent);
      copyCodeBtn.textContent = 'Kopyalandı';
      const COPY_MS = 1400;
      setTimeout(() => { copyCodeBtn.textContent = 'Kopyala'; }, COPY_MS);
    } catch { /* clipboard unavailable */ }
  });

  let diffMode = false;
  diffToggleBtn.addEventListener('click', async () => {
    if (!activePath) return;
    diffMode = !diffMode;
    diffToggleBtn.classList.toggle('primary', diffMode);
    if (!diffMode) { renderCodeView(activeContent, activePath); return; }
    const r = await safeFetchJson(`/api/studio/workspaces/${wsId}/diff?path=${encodeURIComponent(activePath)}`);
    if (!r.ok || !r.data) { diffMode = false; return; }
    const lines = (r.data.diff || '').split('\n');
    setSanitizedHtml(gutter, lines.map((_, i) => `<div>${i + 1}</div>`).join(''));
    setSanitizedHtml(codeBlock, lines.map((ln) => {
      const esc = ln.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      if (ln.startsWith('+') && !ln.startsWith('+++')) return `<div class="diff-add">${esc}</div>`;
      if (ln.startsWith('-') && !ln.startsWith('---')) return `<div class="diff-del">${esc}</div>`;
      if (ln.startsWith('@@')) return `<div class="diff-hunk">${esc}</div>`;
      return `<div>${esc}</div>`;
    }).join(''));
  });

  secScanBtn.addEventListener('click', async () => {
    secScanBtn.disabled = true;
    secScanBtn.textContent = 'Taranıyor...';
    try {
      const [secResp, cgResp] = await Promise.all([
        fetch(`/api/studio/workspaces/${wsId}/security-scan`),
        fetch(`/api/studio/workspaces/${wsId}/code-graph`),
      ]);
      const secData = await secResp.json();
      const cgData = await cgResp.json();
      const issueCount = (secData.security && secData.security.total_issues) || 0;
      const errCount = (secData.errors || []).length;
      const symCount = (cgData.symbols || []).length;
      setSanitizedHtml(statusLeft, `<span>⎇ main</span><span>${errCount + issueCount === 0 ? '✓ 0 hata / SAST temiz' : `! ${errCount} hata · ${issueCount} SAST`} · ${symCount} AST sembol</span>`);
    } catch { /* ignore */ } finally { secScanBtn.disabled = false; secScanBtn.textContent = 'Güvenlik & AST'; }
  });

  editToggleBtn.addEventListener('click', () => {
    if (!activePath) return;
    editMode = !editMode;
    codeBlock.hidden = editMode;
    rawTextarea.hidden = !editMode;
    saveFileBtn.hidden = !editMode;
    editToggleBtn.textContent = editMode ? 'Görünüm' : 'Düzenle';
  });

  saveFileBtn.addEventListener('click', async () => {
    if (!activePath) return;
    saveFileBtn.disabled = true;
    saveFileBtn.textContent = 'Kaydediliyor...';
    const res = await safeFetchJson(`/api/studio/workspaces/${wsId}/file`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: activePath, content: rawTextarea.value }),
    });
    if (res.ok) {
      fileCache.set(activePath, rawTextarea.value);
      editMode = false; codeBlock.hidden = false; rawTextarea.hidden = true; saveFileBtn.hidden = true;
      editToggleBtn.textContent = 'Düzenle';
      renderCodeView(rawTextarea.value, activePath);
      if (viewMode === 'split') iframe.src = `/api/studio/workspaces/${wsId}/preview/index.html?t=${Date.now()}`;
    }
    saveFileBtn.disabled = false; saveFileBtn.textContent = 'Kaydet';
  });

  newFileBtn.addEventListener('click', async () => {
    const rel = await uiPrompt('Yeni dosya yolu (ör. css/theme.css veya js/modal.js):', '', 'Yeni Dosya');
    if (!rel || !rel.trim()) return;
    const clean = rel.trim();
    await safeFetchJson(`/api/studio/workspaces/${wsId}/file`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path: clean, content: '' }),
    });
    const tRes = await safeFetchJson(`/api/studio/workspaces/${wsId}/tree`);
    currentTree = (tRes.data && tRes.data.tree) || currentTree;
    fileCache.set(clean, '');
    await selectFile(clean);
  });

  const iterBar = createIterationBar(wsId, async (evt) => {
    if (evt.type === 'file_done') fileCache.delete(evt.path);
    else if (evt.type === 'done' && evt.tree) {
      currentTree = evt.tree;
      renderTree();
      if (activePath) { fileCache.delete(activePath); await selectFile(activePath); }
      if (viewMode === 'preview' || viewMode === 'split') iframe.src = `/api/studio/workspaces/${wsId}/preview/index.html?t=${Date.now()}`;
      refreshVersions();
    }
  });
  card.append(iterBar, statusBar);

  const flatPaths = [];
  const collectFiles = (nodes) => {
    for (const n of nodes || []) {
      if (n.type === 'file' && !n.name.endsWith('.exe')) flatPaths.push(n.path);
      else if (n.children) collectFiles(n.children);
    }
  };
  collectFiles(currentTree);
  renderTree();
  const entry = (wsMeta.entry_point && flatPaths.includes(wsMeta.entry_point))
    ? wsMeta.entry_point
    : (flatPaths.find((p) => p === 'index.html' || p === 'main.py') || flatPaths[0]);
  if (entry) selectFile(entry);

  return card;
}
