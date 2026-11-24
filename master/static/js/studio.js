// AI Project Studio / Workspace Builder (VS Code / Antigravity-style Explorer + Editor + Live Preview + EXE Builder).
import { safeFetch } from './storage.js';
import {
  buildStudioPanes,
  buildStudioTopbar,
  collectStudioFiles,
  consumeStudioStream,
  formatSize,
  renderStudioTreeNodes,
} from './studio_parts.js';
import { uiPrompt } from './ui_dialog.js';
import { api, h } from './util.js';

const studioState = {
  activeWsId: null,
  activeWsMeta: null,
  activeTree: [],
  activeFilePath: null,
  previewMode: false,
  collapsedDirs: new Set(),
};

function updateStudioToolbar(ui) {
  const hasWs = Boolean(studioState.activeWsId && studioState.activeWsMeta);
  ui.iterBtn.disabled = !hasWs;
  ui.newFileBtn.disabled = !hasWs;
  ui.downloadZipLink.hidden = !hasWs;
  if (hasWs) ui.downloadZipLink.href = `/api/studio/workspaces/${studioState.activeWsId}/download.zip`;

  const hasWeb = Boolean(studioState.activeWsMeta?.has_web_preview);
  ui.previewBtn.hidden = !hasWeb;
  ui.previewBtn.textContent = studioState.previewMode ? 'Koda Dön' : '▶ Canlı Önizleme';

  const hasPy = studioState.activeTree.some((n) => n.name.endsWith('.py'))
    || studioState.activeWsMeta?.project_type === 'game'
    || studioState.activeWsMeta?.project_type === 'desktop';
  ui.buildExeBtn.hidden = !hasPy;

  const hasExe = Boolean(studioState.activeWsMeta?.has_exe);
  ui.downloadExeLink.hidden = !hasExe;
  if (hasExe) {
    ui.downloadExeLink.href = `/api/studio/workspaces/${studioState.activeWsId}/download-exe`;
    ui.downloadExeLink.textContent = `⬇ ${studioState.activeWsMeta.exe_name || 'App.exe'} İndir`;
  }
}

function renderExplorerView(ui, onOpenFile) {
  ui.treeEl.replaceChildren();
  if (!studioState.activeWsMeta) {
    ui.treeEl.append(h('div', { class: 'studio-empty-tree' }, 'Çalışma alanı yok.'));
    return;
  }
  ui.treeEl.appendChild(h('div', { class: 'studio-ws-root' }, `▾ ${studioState.activeWsMeta.name}`));
  ui.treeEl.appendChild(renderStudioTreeNodes(
    studioState.activeTree,
    studioState,
    (dirPath, isCollapsed) => {
      if (isCollapsed) studioState.collapsedDirs.delete(dirPath);
      else studioState.collapsedDirs.add(dirPath);
      renderExplorerView(ui, onOpenFile);
    },
    onOpenFile,
    0,
  ));
}

function createWorkspaceController(ui, log) {
  const renderExplorer = () => renderExplorerView(ui, openFile);

  async function openFile(relPath) {
    if (!studioState.activeWsId) return;
    studioState.previewMode = false;
    ui.previewFrame.hidden = true;
    ui.codeArea.hidden = false;
    try {
      const data = await api(`/api/studio/workspaces/${studioState.activeWsId}/file?path=${encodeURIComponent(relPath)}`);
      studioState.activeFilePath = relPath;
      ui.codeArea.value = data.content || '';
      ui.codeArea.readOnly = Boolean(data.binary);
      ui.saveBtn.disabled = Boolean(data.binary);
      ui.breadcrumb.textContent = `${studioState.activeWsMeta?.name || studioState.activeWsId} / ${relPath} (${formatSize(data.size)})`;
      renderExplorer();
      updateStudioToolbar(ui);
    } catch (err) {
      log.appendLog('Dosya açılamadı: ' + err.message, 'err');
    }
  }

  async function loadWorkspace(wsId) {
    studioState.activeWsId = wsId;
    studioState.activeFilePath = null;
    studioState.previewMode = false;
    ui.previewFrame.hidden = true;
    ui.codeArea.hidden = false;
    const data = await api(`/api/studio/workspaces/${wsId}/tree`);
    studioState.activeWsMeta = data.workspace;
    studioState.activeTree = data.tree || [];
    renderExplorer();
    updateStudioToolbar(ui);

    const ep = studioState.activeWsMeta.entry_point;
    const flatFiles = collectStudioFiles(studioState.activeTree);
    const firstFile = (ep && flatFiles.includes(ep)) ? ep : flatFiles[0];
    if (firstFile) await openFile(firstFile);
  }

  async function refreshWorkspaces(selectId = null) {
    const data = await api('/api/studio/workspaces');
    const list = data.workspaces || [];
    ui.wsSelect.replaceChildren();
    if (!list.length) {
      ui.wsSelect.append(h('option', { value: '' }, '— Çalışma alanı yok —'));
      studioState.activeWsId = null;
      studioState.activeWsMeta = null;
      studioState.activeTree = [];
      renderExplorer();
      updateStudioToolbar(ui);
      return;
    }
    for (const ws of list) {
      const tag = ws.has_exe ? ' [.EXE]' : (ws.has_web_preview ? ' [WEB]' : '');
      ui.wsSelect.append(h('option', { value: ws.id }, `${ws.name}${tag} (${ws.file_count} dosya)`));
    }
    const target = selectId || (studioState.activeWsId && list.some((w) => w.id === studioState.activeWsId) ? studioState.activeWsId : list[0].id);
    ui.wsSelect.value = target;
    await loadWorkspace(target);
  }

  return { renderExplorer, openFile, loadWorkspace, refreshWorkspaces };
}

function bindEditorEvents(ui, ctrl, log) {
  ui.wsSelect.addEventListener('change', () => {
    if (ui.wsSelect.value) ctrl.loadWorkspace(ui.wsSelect.value);
  });

  ui.saveBtn.addEventListener('click', async () => {
    if (!studioState.activeWsId || !studioState.activeFilePath) return;
    ui.saveBtn.disabled = true;
    try {
      await api(`/api/studio/workspaces/${studioState.activeWsId}/file`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: studioState.activeFilePath, content: ui.codeArea.value }),
      });
      log.appendLog(`✓ Kaydedildi: ${studioState.activeFilePath}`, 'ok');
    } catch (err) {
      log.appendLog(`Kaydetme hatası: ${err.message}`, 'err');
    } finally {
      ui.saveBtn.disabled = false;
    }
  });

  ui.newFileBtn.addEventListener('click', async () => {
    if (!studioState.activeWsId) return;
    const rel = await uiPrompt('Yeni dosya yolu (ör. js/utils.js veya game/levels.py):', '', 'Yeni Dosya');
    if (!rel || !rel.trim()) return;
    try {
      await api(`/api/studio/workspaces/${studioState.activeWsId}/file`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: rel.trim(), content: '' }),
      });
      await ctrl.loadWorkspace(studioState.activeWsId);
      await ctrl.openFile(rel.trim());
      log.appendLog(`✓ Yeni dosya oluşturuldu: ${rel.trim()}`, 'ok');
    } catch (err) {
      log.appendLog(`Dosya oluşturulamadı: ${err.message}`, 'err');
    }
  });

  ui.previewBtn.addEventListener('click', () => {
    if (!studioState.activeWsId) return;
    studioState.previewMode = !studioState.previewMode;
    ui.codeArea.hidden = studioState.previewMode;
    ui.previewFrame.hidden = !studioState.previewMode;
    if (studioState.previewMode) {
      ui.previewFrame.src = `/api/studio/workspaces/${studioState.activeWsId}/preview/index.html?t=${Date.now()}`;
      ui.breadcrumb.textContent = `▶ Canlı Önizleme — ${studioState.activeWsMeta?.name || studioState.activeWsId}`;
    } else if (studioState.activeFilePath) {
      ui.breadcrumb.textContent = `${studioState.activeWsMeta?.name || studioState.activeWsId} / ${studioState.activeFilePath}`;
    }
    updateStudioToolbar(ui);
  });

  ui.buildExeBtn.addEventListener('click', async () => {
    if (!studioState.activeWsId) return;
    ui.buildExeBtn.disabled = true;
    ui.buildExeBtn.textContent = '.EXE Derleniyor...';
    log.clearLog('PyInstaller ile tek dosyalık Windows .EXE derlemesi başlatıldı...');
    try {
      const res = await api(`/api/studio/workspaces/${studioState.activeWsId}/build-exe`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}),
      });
      if (res.ok) {
        log.appendLog(`✓ BAŞARILI: dist/${res.exe_name} (${formatSize(res.exe_size)}) oluşturuldu!`, 'ok');
        await ctrl.refreshWorkspaces(studioState.activeWsId);
      } else {
        log.appendLog(`✗ HATA: ${res.error}`, 'err');
        if (res.logs) log.appendLog(res.logs.slice(-1200));
      }
    } catch (err) {
      log.appendLog(`✗ Derleme hatası: ${err.message}`, 'err');
    } finally {
      ui.buildExeBtn.disabled = false;
      ui.buildExeBtn.textContent = '.EXE Oluştur';
    }
  });
}

function bindGenerationEvents(ui, ctrl, log) {
  const streamHooks = { appendLog: log.appendLog, refreshWorkspaces: ctrl.refreshWorkspaces };
  ui.genBtn.addEventListener('click', async () => {
    const promptText = ui.promptBox.value.trim();
    if (!promptText) return;
    ui.genBtn.disabled = true;
    ui.iterBtn.disabled = true;
    log.clearLog('AI Proje Oluşturucu başlatıldı...');
    try {
      const resp = await safeFetch('/api/studio/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: promptText, project_type: ui.typeSelect.value }),
      });
      await consumeStudioStream(resp, studioState, streamHooks);
    } catch (err) {
      log.appendLog(`✗ Hata: ${err.message}`, 'err');
    } finally {
      ui.genBtn.disabled = false;
      updateStudioToolbar(ui);
    }
  });

  ui.iterBtn.addEventListener('click', async () => {
    const instr = ui.promptBox.value.trim();
    if (!instr || !studioState.activeWsId) return;
    ui.genBtn.disabled = true;
    ui.iterBtn.disabled = true;
    log.clearLog(`Mevcut proje (${studioState.activeWsMeta?.name}) güncelleniyor...`);
    try {
      const resp = await safeFetch(`/api/studio/workspaces/${studioState.activeWsId}/iterate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruction: instr }),
      });
      await consumeStudioStream(resp, studioState, streamHooks);
    } catch (err) {
      log.appendLog(`✗ Hata: ${err.message}`, 'err');
    } finally {
      ui.genBtn.disabled = false;
      updateStudioToolbar(ui);
    }
  });
}

export async function renderStudio(root) {
  root.replaceChildren();
  const shell = h('div', { class: 'studio-shell' });
  root.appendChild(shell);

  const tb = buildStudioTopbar();
  const panes = buildStudioPanes(tb.breadcrumb);
  shell.append(tb.topbar, panes.bodyGrid);

  const ui = { ...tb, ...panes };
  const log = {
    appendLog: (line, kind = '') => {
      ui.consoleLog.appendChild(h('div', { class: 'studio-log-line' + (kind ? ` log-${kind}` : '') }, line));
      ui.consoleLog.scrollTop = ui.consoleLog.scrollHeight;
    },
    clearLog: (msg = '') => {
      ui.consoleLog.replaceChildren();
      if (msg) log.appendLog(msg);
    },
  };

  const ctrl = createWorkspaceController(ui, log);
  bindEditorEvents(ui, ctrl, log);
  bindGenerationEvents(ui, ctrl, log);
  await ctrl.refreshWorkspaces();

  const pending = sessionStorage.getItem('studio_pending_prompt');
  if (pending) {
    sessionStorage.removeItem('studio_pending_prompt');
    ui.promptBox.value = pending;
    ui.genBtn.click();
  }
}
