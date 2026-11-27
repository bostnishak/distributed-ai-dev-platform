// Inline IDE Workbench DOM builders and tree/tab/diff rendering helpers.
import { wsSvgIcon } from './assistant_ide_render.js';
import { setSanitizedHtml } from './sanitizer.js';
import { safeFetchJson } from './storage.js';
import { mountOfflineCodeEditor } from '../vendor/code_editor.js';

function appendExeButtons(actions, wsId, exeName) {
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

function buildExeActions(actions, wsMeta, wsId, currentTree, typeBadge) {
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
        appendExeButtons(actions, wsId, r.data.exe_name);
      } else { exeBtn.textContent = 'Hata'; }
    });
    actions.appendChild(exeBtn);
  }
  if (wsMeta.has_exe) appendExeButtons(actions, wsId, wsMeta.exe_name);
}

function buildVersionSelector(wsId, onRestore) {
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
    if (r.ok && r.data) onRestore(r.data.tree);
  });
  return { verSelect, refreshVersions };
}

export function buildTitlebar(wsMeta, wsId, currentTree, card, onRestore) {
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
  buildExeActions(actions, wsMeta, wsId, currentTree, typeBadge);

  const zipLink = document.createElement('a');
  zipLink.className = 'ide-btn';
  zipLink.href = `/api/studio/workspaces/${wsId}/download.zip`;
  zipLink.download = '';
  zipLink.textContent = 'ZIP İndir';
  actions.appendChild(zipLink);

  const { verSelect, refreshVersions } = buildVersionSelector(wsId, onRestore);
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
  return { titlebar, btnModeCode, btnModePrev, btnModeSplit, refreshVersions };
}

export function buildSidebarDom(wsMeta, wsId) {
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
  return { sidebar, newFileBtn, treeContainer };
}

export function buildCodePane(onSaveShortcut) {
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
  mountOfflineCodeEditor(rawTextarea, { onSave: () => onSaveShortcut(saveFileBtn) });
  codeScroll.append(gutter, codeBlock, rawTextarea);
  codePane.append(tabBar, subBar, codeScroll);

  return {
    codePane, tabBar, breadcrumb, gutter, codeBlock, rawTextarea,
    copyCodeBtn, diffToggleBtn, secScanBtn, searchWsBtn, gitWsBtn, termToggleBtn, editToggleBtn, saveFileBtn,
  };
}

export function buildPreviewPane(wsId) {
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
  iframe.setAttribute('sandbox', 'allow-scripts allow-forms allow-modals');
  refreshBtn.addEventListener('click', () => { iframe.src = `/api/studio/workspaces/${wsId}/preview/index.html?t=${Date.now()}`; });
  previewPane.append(browserBar, iframe);
  return { previewPane, iframe };
}

export function buildStatusBar() {
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
  return { statusBar, statusLeft, statusLines, statusLang };
}

export function renderFileTree(treeContainer, currentTree, activePath, collapsedFolders, onSelectFile, onToggleDir) {
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
      row.addEventListener('click', () => (isDir ? onToggleDir(node.path, isCollapsed) : onSelectFile(node.path)));
      treeContainer.appendChild(row);
      if (isDir && !isCollapsed && node.children) walk(node.children, depth + 1);
    }
  }
  walk(currentTree, 0);
}

export function renderOpenTabs(tabBar, openTabs, activePath, onSelectFile, onCloseTab) {
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
    closeSpan.addEventListener('click', (e) => { e.stopPropagation(); onCloseTab(p); });
    tab.append(iconSpan, nameSpan, closeSpan);
    tab.addEventListener('click', () => onSelectFile(p));
    tabBar.appendChild(tab);
  }
}

export function renderDiffView(gutter, codeBlock, diffText) {
  const lines = (diffText || '').split('\n');
  setSanitizedHtml(gutter, lines.map((_, i) => `<div>${i + 1}</div>`).join(''));
  setSanitizedHtml(codeBlock, lines.map((ln) => {
    const esc = ln.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    if (ln.startsWith('+') && !ln.startsWith('+++')) return `<div class="diff-add">${esc}</div>`;
    if (ln.startsWith('-') && !ln.startsWith('---')) return `<div class="diff-del">${esc}</div>`;
    if (ln.startsWith('@@')) return `<div class="diff-hunk">${esc}</div>`;
    return `<div>${esc}</div>`;
  }).join(''));
}

export function collectWorkspaceFiles(nodes, out = []) {
  for (const n of nodes || []) {
    if (n.type === 'file' && !n.name.endsWith('.exe')) out.push(n.path);
    else if (n.children) collectWorkspaceFiles(n.children, out);
  }
  return out;
}
