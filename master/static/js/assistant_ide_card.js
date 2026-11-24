// UX-02 Modular Split: Inline IDE Workbench card controller (<= 400 lines).
import {
  buildCodePane,
  buildPreviewPane,
  buildSidebarDom,
  buildStatusBar,
  buildTitlebar,
  collectWorkspaceFiles,
  renderDiffView,
  renderFileTree,
  renderOpenTabs,
} from './assistant_ide_parts.js';
import {
  createIterationBar,
  createTerminalDrawer,
  detectLangLabel,
  highlightCodeHtml,
} from './assistant_ide_render.js';
import { setSanitizedHtml } from './sanitizer.js';
import { safeFetchJson } from './storage.js';
import { uiPrompt } from './ui_dialog.js';

function createFileController(ctx) {
  const { wsMeta, wsId, st, dom } = ctx;

  function setViewMode(mode) {
    st.viewMode = mode;
    dom.btnModeCode.classList.toggle('active', mode === 'code');
    dom.btnModePrev.classList.toggle('active', mode === 'preview');
    dom.btnModeSplit.classList.toggle('active', mode === 'split');
    dom.surface.classList.toggle('split-view', mode === 'split');
    dom.codePane.hidden = mode === 'preview';
    dom.previewPane.hidden = mode === 'code';
    if ((mode === 'preview' || mode === 'split') && !dom.iframe.getAttribute('src')) {
      dom.iframe.src = `/api/studio/workspaces/${wsId}/preview/index.html?t=${Date.now()}`;
    }
  }

  function renderCodeView(content, path) {
    st.activeContent = content || '';
    const lines = st.activeContent.split('\n');
    setSanitizedHtml(dom.gutter, lines.map((_, i) => `<div>${i + 1}</div>`).join(''));
    setSanitizedHtml(dom.codeBlock, highlightCodeHtml(st.activeContent, path));
    dom.rawTextarea.value = st.activeContent;
    dom.statusLines.textContent = `${lines.length} satır`;
    dom.statusLang.textContent = `${detectLangLabel(path)} · UTF-8`;
    setSanitizedHtml(
      dom.breadcrumb,
      `<span class="bc-root">${wsMeta.name || wsId}</span> › ` + (path || '').split('/').map((p) => `<span>${p}</span>`).join(' › '),
    );
  }

  function renderTabs() {
    renderOpenTabs(dom.tabBar, st.openTabs, st.activePath, selectFile, (p) => {
      const idx = st.openTabs.indexOf(p);
      if (idx >= 0) st.openTabs.splice(idx, 1);
      if (st.activePath === p) {
        const next = st.openTabs[st.openTabs.length - 1];
        if (next) selectFile(next);
        else { st.activePath = null; renderTabs(); renderCodeView('', ''); }
      } else renderTabs();
    });
  }

  function renderTree() {
    renderFileTree(dom.treeContainer, st.currentTree, st.activePath, st.collapsedFolders, selectFile, (dirPath, isCollapsed) => {
      if (isCollapsed) st.collapsedFolders.delete(dirPath);
      else st.collapsedFolders.add(dirPath);
      renderTree();
    });
  }

  async function selectFile(path) {
    st.activePath = path;
    if (!st.openTabs.includes(path)) st.openTabs.push(path);
    if (st.viewMode === 'preview') setViewMode('code');
    renderTabs();
    renderTree();
    if (st.fileCache.has(path)) { renderCodeView(st.fileCache.get(path), path); return; }
    renderCodeView('// Yükleniyor...', path);
    const r = await safeFetchJson(`/api/studio/workspaces/${wsId}/file?path=${encodeURIComponent(path)}`);
    if (!r.ok) { renderCodeView(`// Dosya okunamadı: ${r.error || r.status}`, path); return; }
    const text = (r.data && r.data.content) || '';
    st.fileCache.set(path, text);
    if (st.activePath === path) renderCodeView(text, path);
  }

  return { setViewMode, renderCodeView, renderTabs, renderTree, selectFile };
}

function bindInspectTools(ctx, ctrl) {
  const { wsId, st, dom } = ctx;

  dom.copyCodeBtn.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(st.editMode ? dom.rawTextarea.value : st.activeContent);
      dom.copyCodeBtn.textContent = 'Kopyalandı';
      const COPY_MS = 1400;
      setTimeout(() => { dom.copyCodeBtn.textContent = 'Kopyala'; }, COPY_MS);
    } catch { /* clipboard unavailable */ }
  });

  let diffMode = false;
  dom.diffToggleBtn.addEventListener('click', async () => {
    if (!st.activePath) return;
    diffMode = !diffMode;
    dom.diffToggleBtn.classList.toggle('primary', diffMode);
    if (!diffMode) { ctrl.renderCodeView(st.activeContent, st.activePath); return; }
    const r = await safeFetchJson(`/api/studio/workspaces/${wsId}/diff?path=${encodeURIComponent(st.activePath)}`);
    if (!r.ok || !r.data) { diffMode = false; return; }
    renderDiffView(dom.gutter, dom.codeBlock, r.data.diff || '');
  });

  dom.secScanBtn.addEventListener('click', async () => {
    dom.secScanBtn.disabled = true;
    dom.secScanBtn.textContent = 'Taranıyor...';
    try {
      const [secRes, cgRes] = await Promise.all([
        safeFetchJson(`/api/studio/workspaces/${wsId}/security-scan`),
        safeFetchJson(`/api/studio/workspaces/${wsId}/code-graph`),
      ]);
      const secData = secRes.data || {};
      const cgData = cgRes.data || {};
      const issueCount = (secData.security && secData.security.total_issues) || 0;
      const errCount = (secData.errors || []).length;
      const symCount = (cgData.symbols || []).length;
      setSanitizedHtml(
        dom.statusLeft,
        `<span>⎇ main</span><span>${errCount + issueCount === 0 ? '✓ 0 hata / SAST temiz' : `! ${errCount} hata · ${issueCount} SAST`} · ${symCount} AST sembol</span>`,
      );
    } catch { /* ignore */ } finally {
      dom.secScanBtn.disabled = false;
      dom.secScanBtn.textContent = 'Güvenlik & AST';
    }
  });
}

function bindEditTools(ctx, ctrl) {
  const { wsId, st, dom } = ctx;

  dom.editToggleBtn.addEventListener('click', () => {
    if (!st.activePath) return;
    st.editMode = !st.editMode;
    dom.codeBlock.hidden = st.editMode;
    dom.rawTextarea.hidden = !st.editMode;
    dom.saveFileBtn.hidden = !st.editMode;
    dom.editToggleBtn.textContent = st.editMode ? 'Görünüm' : 'Düzenle';
  });

  dom.saveFileBtn.addEventListener('click', async () => {
    if (!st.activePath) return;
    dom.saveFileBtn.disabled = true;
    dom.saveFileBtn.textContent = 'Kaydediliyor...';
    const res = await safeFetchJson(`/api/studio/workspaces/${wsId}/file`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: st.activePath, content: dom.rawTextarea.value }),
    });
    if (res.ok) {
      st.fileCache.set(st.activePath, dom.rawTextarea.value);
      st.editMode = false;
      dom.codeBlock.hidden = false;
      dom.rawTextarea.hidden = true;
      dom.saveFileBtn.hidden = true;
      dom.editToggleBtn.textContent = 'Düzenle';
      ctrl.renderCodeView(dom.rawTextarea.value, st.activePath);
      if (st.viewMode === 'split') dom.iframe.src = `/api/studio/workspaces/${wsId}/preview/index.html?t=${Date.now()}`;
    }
    dom.saveFileBtn.disabled = false;
    dom.saveFileBtn.textContent = 'Kaydet';
  });

  dom.newFileBtn.addEventListener('click', async () => {
    const rel = await uiPrompt('Yeni dosya yolu (ör. css/theme.css veya js/modal.js):', '', 'Yeni Dosya');
    if (!rel || !rel.trim()) return;
    const clean = rel.trim();
    await safeFetchJson(`/api/studio/workspaces/${wsId}/file`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path: clean, content: '' }),
    });
    const tRes = await safeFetchJson(`/api/studio/workspaces/${wsId}/tree`);
    st.currentTree = (tRes.data && tRes.data.tree) || st.currentTree;
    st.fileCache.set(clean, '');
    await ctrl.selectFile(clean);
  });
}

export function buildInlineWorkspaceCard(wsMeta, wsTree) {
  const wsId = wsMeta.id;
  const card = document.createElement('div');
  card.className = 'ide-workbench';

  const st = {
    currentTree: wsTree || [],
    viewMode: 'code',
    editMode: false,
    activePath: null,
    activeContent: '',
    openTabs: [],
    fileCache: new Map(),
    collapsedFolders: new Set(),
  };

  let ctrl = null;
  const tb = buildTitlebar(wsMeta, wsId, st.currentTree, card, (tree) => {
    st.currentTree = tree || st.currentTree;
    st.fileCache.clear();
    if (ctrl) {
      ctrl.renderTree();
      if (st.activePath) ctrl.selectFile(st.activePath);
    }
  });
  const sb = buildSidebarDom(wsMeta, wsId);
  const cp = buildCodePane((saveBtn) => saveBtn.click());
  const pp = buildPreviewPane(wsId);
  const status = buildStatusBar();

  const surface = document.createElement('div');
  surface.className = 'ide-surface';
  surface.append(cp.codePane, pp.previewPane);
  const mainGrid = document.createElement('div');
  mainGrid.className = 'ide-main';
  mainGrid.append(sb.sidebar, surface);
  card.append(tb.titlebar, mainGrid, createTerminalDrawer(wsId, cp.termToggleBtn, cp.gitWsBtn, cp.searchWsBtn));

  const dom = { ...tb, ...sb, ...cp, ...pp, ...status, surface };
  const ctx = { wsMeta, wsId, st, dom };
  ctrl = createFileController(ctx);

  tb.btnModeCode.addEventListener('click', () => ctrl.setViewMode('code'));
  tb.btnModePrev.addEventListener('click', () => { pp.iframe.src = `/api/studio/workspaces/${wsId}/preview/index.html?t=${Date.now()}`; ctrl.setViewMode('preview'); });
  tb.btnModeSplit.addEventListener('click', () => { pp.iframe.src = `/api/studio/workspaces/${wsId}/preview/index.html?t=${Date.now()}`; ctrl.setViewMode('split'); });
  bindInspectTools(ctx, ctrl);
  bindEditTools(ctx, ctrl);

  const iterBar = createIterationBar(wsId, async (evt) => {
    if (evt.type === 'file_done') st.fileCache.delete(evt.path);
    else if (evt.type === 'done' && evt.tree) {
      st.currentTree = evt.tree;
      ctrl.renderTree();
      if (st.activePath) { st.fileCache.delete(st.activePath); await ctrl.selectFile(st.activePath); }
      if (st.viewMode === 'preview' || st.viewMode === 'split') pp.iframe.src = `/api/studio/workspaces/${wsId}/preview/index.html?t=${Date.now()}`;
      tb.refreshVersions();
    }
  });
  card.append(iterBar, status.statusBar);

  const flatPaths = collectWorkspaceFiles(st.currentTree);
  ctrl.renderTree();
  const entry = (wsMeta.entry_point && flatPaths.includes(wsMeta.entry_point))
    ? wsMeta.entry_point
    : (flatPaths.find((p) => p === 'index.html' || p === 'main.py') || flatPaths[0]);
  if (entry) ctrl.selectFile(entry);
  return card;
}
