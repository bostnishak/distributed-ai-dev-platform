// Assistant tab: the chat assistant. History is stored per browser in localStorage.
import { escapeHtml, renderMarkdown } from './markdown.js';
import { getActiveUserId, getPrefs } from './personal.js';
import { closeSidebar } from './util.js';

// Each profile keeps its own chat list; the default profile keeps the original key.
const STORAGE_KEY = getActiveUserId() === 'default' ? 'coklu_llm_chats' : `coklu_llm_chats:${getActiveUserId()}`;
const LAST_CHAT_KEY = `cm6453_last_chat:${getActiveUserId()}`;

const MODEL_LABELS = {
  'uye1-qwen': 'Üye-1 (İshak Bostan) · Qwen3.5 4B',
  'uye2-phi4mini': 'Üye-2 (Zeynep Duru Küçük) · Phi-4-mini',
  'uye3-llama': 'Üye-3 (Furkan Kaan Özbeyli) · Llama 3.2',
  'uye4-gemma': 'Üye-4 (Semih Sarıca) · Gemma 4',
  'uye5-coder': 'Üye-5 (Işıl Karademir) · Qwen2.5-Coder',
  'uye6-qwen-light': 'Üye-6 (Berfin Yiğit) · Qwen3 1.7B',
  'cnc-ballooner': 'CNC Balonlama Motoru (AS9102 / ISO 2768)',
  'qwen2.5-coder:7b': 'Proje Üretici · Qwen2.5-Coder 7B',
  'moderation': 'İçerik denetimi',
  'hesaplama': 'Hesap makinesi (anında, model kullanılmadı)',
};

function wsSvgIcon(name, isDir, isOpen = true) {
  if (isDir) {
    const color = isOpen ? '#dcb67a' : '#c09553';
    return `<svg class="ide-svg-icon" viewBox="0 0 16 16" fill="${color}"><path d="M1.5 2A1.5 1.5 0 0 0 0 3.5v9A1.5 1.5 0 0 0 1.5 14h13a1.5 1.5 0 0 0 1.5-1.5v-7A1.5 1.5 0 0 0 14.5 4H7.71l-1.85-1.85A.5.5 0 0 0 5.5 2h-4z"/></svg>`;
  }
  const ext = (name.split('.').pop() || '').toLowerCase();
  const badges = {
    html: { bg: '#e44d26', fg: '#fff', txt: '<>' },
    htm:  { bg: '#e44d26', fg: '#fff', txt: '<>' },
    css:  { bg: '#264de4', fg: '#fff', txt: '#' },
    js:   { bg: '#f7df1e', fg: '#111', txt: 'JS' },
    ts:   { bg: '#3178c6', fg: '#fff', txt: 'TS' },
    py:   { bg: '#3776ab', fg: '#ffd43b', txt: 'PY' },
    json: { bg: '#292929', fg: '#cbcb41', txt: '{}' },
    md:   { bg: '#1f6feb', fg: '#fff', txt: 'M↓' },
    svg:  { bg: '#ffb13b', fg: '#111', txt: 'SV' },
    exe:  { bg: '#16a34a', fg: '#fff', txt: 'EX' },
  };
  const b = badges[ext];
  if (b) {
    return `<span class="ide-ext-badge" style="background:${b.bg};color:${b.fg}">${b.txt}</span>`;
  }
  return `<svg class="ide-svg-icon" viewBox="0 0 16 16" fill="#9cdcfe"><path d="M4 1h5.5L13 4.5V14a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1zm5 1.5V5h2.5L9 2.5z"/></svg>`;
}

function detectLangLabel(path) {
  const ext = ((path || '').split('.').pop() || '').toLowerCase();
  const map = {
    html: 'HTML5', css: 'CSS3', js: 'JavaScript (ES6)', py: 'Python 3',
    json: 'JSON', md: 'Markdown', svg: 'SVG XML', exe: 'Windows Binary',
  };
  return map[ext] || 'Plain Text';
}

function highlightCodeHtml(code, path) {
  const esc = (s) => s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  const ext = ((path || '').split('.').pop() || '').toLowerCase();
  let html = esc(code || '');

  // Tokenize strings & comments first into placeholders so regexes don't collide
  const tokens = [];
  const stash = (cls, text) => {
    const id = `\u0000T${tokens.length}\u0000`;
    tokens.push(`<span class="${cls}">${text}</span>`);
    return id;
  };

  if (ext === 'html' || ext === 'htm' || ext === 'svg') {
    html = html.replace(/(&lt;!--[\s\S]*?--&gt;)/g, (m) => stash('hl-comment', m));
    html = html.replace(/("[^"\n]*"|'[^'\n]*')/g, (m) => stash('hl-str', m));
    html = html.replace(/(&lt;\/?[a-zA-Z0-9:-]+)/g, '<span class="hl-tag">$1</span>');
    html = html.replace(/\b([a-zA-Z-]+)(?==)/g, '<span class="hl-attr">$1</span>');
  } else {
    html = html.replace(/(\/\/[^\n]*|#[^\n]*|\/\*[\s\S]*?\*\/)/g, (m) => stash('hl-comment', m));
    html = html.replace(/("[^"\n]*"|'[^'\n]*'|`[^`\n]*`)/g, (m) => stash('hl-str', m));
    html = html.replace(
      /\b(def|class|import|from|return|if|elif|else|for|while|try|except|finally|with|as|async|await|True|False|None|self|function|const|let|var|export|default|new|this|document|window|console)\b/g,
      '<span class="hl-kw">$1</span>',
    );
    html = html.replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="hl-num">$1</span>');
  }

  return html.replace(/\u0000T(\d+)\u0000/g, (_, i) => tokens[Number(i)]);
}

function buildInlineWorkspaceCard(wsMeta, wsTree) {
  const wsId = wsMeta.id;
  const card = document.createElement('div');
  card.className = 'ide-workbench';

  // State
  let currentTree = wsTree || [];
  let viewMode = 'code'; // 'code' | 'preview' | 'split'
  let editMode = false;
  let activePath = null;
  let activeContent = '';
  const openTabs = []; // array of file paths
  const fileCache = new Map();
  const collapsedFolders = new Set();

  // --- 1. TOP WINDOW TITLEBAR ---
  const titlebar = document.createElement('div');
  titlebar.className = 'ide-titlebar';

  const titleLeft = document.createElement('div');
  titleLeft.className = 'ide-title-left';
  const dots = document.createElement('div');
  dots.className = 'ide-window-dots';
  dots.innerHTML = '<span class="dot-r"></span><span class="dot-y"></span><span class="dot-g"></span>';

  const projTitle = document.createElement('span');
  projTitle.className = 'ide-proj-name';
  projTitle.textContent = wsMeta.name || wsId;

  const typeBadge = document.createElement('span');
  typeBadge.className = 'ide-type-badge';
  typeBadge.textContent = wsMeta.has_exe ? 'WINDOWS .EXE' : (wsMeta.has_web_preview ? 'WEB APP' : (wsMeta.project_type || 'PROJECT').toUpperCase());
  titleLeft.append(dots, projTitle, typeBadge);

  // Center Segmented Switcher (Code | Preview | Split)
  const modeGroup = document.createElement('div');
  modeGroup.className = 'ide-mode-group';
  const btnModeCode = document.createElement('button');
  btnModeCode.type = 'button';
  btnModeCode.className = 'ide-mode-btn active';
  btnModeCode.textContent = '</> Kod';

  const btnModePrev = document.createElement('button');
  btnModePrev.type = 'button';
  btnModePrev.className = 'ide-mode-btn';
  btnModePrev.textContent = '▶ Önizleme';

  const btnModeSplit = document.createElement('button');
  btnModeSplit.type = 'button';
  btnModeSplit.className = 'ide-mode-btn';
  btnModeSplit.textContent = '◫ Bölünmüş';

  if (wsMeta.has_web_preview) {
    modeGroup.append(btnModeCode, btnModePrev, btnModeSplit);
  }

  // Right Actions (EXE, ZIP, Fullscreen)
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
      try {
        const r = await fetch(`/api/studio/workspaces/${wsId}/launch-exe`, { method: 'POST' });
        launchBtn.textContent = r.ok ? 'Açıldı' : 'Açılamadı';
      } catch {
        launchBtn.textContent = 'Hata';
      } finally {
        setTimeout(() => { launchBtn.disabled = false; launchBtn.textContent = 'EXE Çalıştır'; }, 1800);
      }
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
      try {
        const resp = await fetch(`/api/studio/workspaces/${wsId}/build-exe`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: '{}',
        });
        const res = await resp.json();
        if (res.ok) {
          exeBtn.remove();
          typeBadge.textContent = 'WINDOWS .EXE';
          appendExeButtons(res.exe_name);
        } else {
          exeBtn.textContent = 'Hata';
        }
      } catch {
        exeBtn.textContent = 'Hata';
      }
    });
    actions.appendChild(exeBtn);
  }
  if (wsMeta.has_exe) {
    appendExeButtons(wsMeta.exe_name);
  }

  const zipLink = document.createElement('a');
  zipLink.className = 'ide-btn';
  zipLink.href = `/api/studio/workspaces/${wsId}/download.zip`;
  zipLink.download = '';
  zipLink.textContent = 'ZIP İndir';
  actions.appendChild(zipLink);

  // Version History (v1, v2, v3...) Rollback Selector
  const verSelect = document.createElement('select');
  verSelect.className = 'ide-btn';
  verSelect.title = 'Sürüm Geçmişi (Geri Al)';
  verSelect.hidden = true;

  async function refreshVersions() {
    try {
      const r = await fetch(`/api/studio/workspaces/${wsId}/history`);
      if (!r.ok) return;
      const d = await r.json();
      const vers = d.versions || [];
      if (vers.length > 0) {
        verSelect.innerHTML = '';
        for (const v of vers) {
          const opt = document.createElement('option');
          opt.value = v.version;
          opt.textContent = `${v.version}: ${(v.label || '').slice(0, 22)}`;
          verSelect.appendChild(opt);
        }
        verSelect.hidden = false;
      }
    } catch { /* ignore */ }
  }
  verSelect.addEventListener('change', async () => {
    const v = verSelect.value;
    if (!v) return;
    const r = await fetch(`/api/studio/workspaces/${wsId}/restore/${v}`, { method: 'POST' });
    if (r.ok) {
      const d = await r.json();
      currentTree = d.tree || currentTree;
      fileCache.clear();
      renderTree();
      if (activePath) selectFile(activePath);
    }
  });
  actions.appendChild(verSelect);
  refreshVersions();

  // Live Backend Server Runner for Full-Stack / Python Web Apps
  if (hasPy && !wsMeta.has_web_preview) {
    const srvBtn = document.createElement('button');
    srvBtn.type = 'button';
    srvBtn.className = 'ide-btn';
    srvBtn.textContent = 'Canlı Sunucu';
    srvBtn.addEventListener('click', async () => {
      srvBtn.disabled = true;
      srvBtn.textContent = 'Başlatılıyor...';
      try {
        const r = await fetch(`/api/studio/workspaces/${wsId}/start-server`, { method: 'POST' });
        const d = await r.json();
        if (d.ok && d.url) {
          modeGroup.innerHTML = '';
          modeGroup.append(btnModeCode, btnModePrev, btnModeSplit);
          urlPill.textContent = d.url;
          extLink.href = d.url;
          iframe.src = d.url;
          setViewMode('split');
          srvBtn.textContent = `Port :${d.port}`;
        } else {
          srvBtn.textContent = 'Hata';
        }
      } catch {
        srvBtn.textContent = 'Hata';
      } finally {
        srvBtn.disabled = false;
      }
    });
    actions.appendChild(srvBtn);
  }

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

  // --- 2. MAIN WORKBENCH GRID (Explorer + Editor/Preview) ---
  const mainGrid = document.createElement('div');
  mainGrid.className = 'ide-main';

  // Left: Explorer Sidebar
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
  rootHeader.innerHTML = `<span class="ide-chev">▾</span> <span>${(wsMeta.name || wsId).toUpperCase()}</span>`;

  const treeContainer = document.createElement('div');
  treeContainer.className = 'ide-tree';
  sidebar.append(sideHeader, rootHeader, treeContainer);

  // Center/Right: Editor & Preview Panes
  const surface = document.createElement('div');
  surface.className = 'ide-surface';

  // Code Pane
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

  const copyCodeBtn = document.createElement('button');
  copyCodeBtn.type = 'button';
  copyCodeBtn.className = 'ide-tool-btn';
  copyCodeBtn.textContent = 'Kopyala';
  copyCodeBtn.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(editMode ? rawTextarea.value : activeContent);
      copyCodeBtn.textContent = 'Kopyalandı';
      setTimeout(() => { copyCodeBtn.textContent = 'Kopyala'; }, 1400);
    } catch { /* clipboard unavailable */ }
  });

  const diffToggleBtn = document.createElement('button');
  diffToggleBtn.type = 'button';
  diffToggleBtn.className = 'ide-tool-btn';
  diffToggleBtn.textContent = 'Diff';

  const secScanBtn = document.createElement('button');
  secScanBtn.type = 'button';
  secScanBtn.className = 'ide-tool-btn';
  secScanBtn.textContent = 'Güvenlik & AST';

  const searchWsBtn = document.createElement('button');
  searchWsBtn.type = 'button';
  searchWsBtn.className = 'ide-tool-btn';
  searchWsBtn.textContent = 'Ara';

  const gitWsBtn = document.createElement('button');
  gitWsBtn.type = 'button';
  gitWsBtn.className = 'ide-tool-btn';
  gitWsBtn.textContent = 'Git';

  const termToggleBtn = document.createElement('button');
  termToggleBtn.type = 'button';
  termToggleBtn.className = 'ide-tool-btn';
  termToggleBtn.textContent = 'Terminal';

  const editToggleBtn = document.createElement('button');
  editToggleBtn.type = 'button';
  editToggleBtn.className = 'ide-tool-btn';
  editToggleBtn.textContent = 'Düzenle';

  const saveFileBtn = document.createElement('button');
  saveFileBtn.type = 'button';
  saveFileBtn.className = 'ide-tool-btn primary';
  saveFileBtn.hidden = true;
  saveFileBtn.textContent = 'Kaydet';

  editorTools.append(copyCodeBtn, diffToggleBtn, secScanBtn, searchWsBtn, gitWsBtn, termToggleBtn, editToggleBtn, saveFileBtn);
  subBar.append(breadcrumb, editorTools);

  // Code Viewport (Gutter + Highlighted Code / Editable Textarea)
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

  codeScroll.append(gutter, codeBlock, rawTextarea);
  codePane.append(tabBar, subBar, codeScroll);

  // Live Preview Pane (with Mini Browser Chrome!)
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
  iframe.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-forms allow-modals');
  refreshBtn.addEventListener('click', () => {
    iframe.src = `/api/studio/workspaces/${wsId}/preview/index.html?t=${Date.now()}`;
  });
  previewPane.append(browserBar, iframe);

  surface.append(codePane, previewPane);
  mainGrid.append(sidebar, surface);
  card.appendChild(mainGrid);

  // Embedded Interactive Workspace Terminal & Git/Search Console Drawer ([M28]/[M29])
  const termDrawer = document.createElement('div');
  termDrawer.style.cssText = 'background:#0d1017;border-top:1px solid #2b2b36;padding:8px 12px;font-family:Consolas,monospace;font-size:12px;color:#e2e8f0;';
  termDrawer.hidden = true;
  const termOut = document.createElement('pre');
  termOut.style.cssText = 'margin:0 0 6px;max-height:150px;overflow-y:auto;white-space:pre-wrap;color:#a7f3d0;';
  termOut.textContent = 'Çalışma alanı terminali hazır. Komut girin (ör. python main.py, pytest, git status):';
  const termRow = document.createElement('div');
  termRow.style.cssText = 'display:flex;gap:6px;align-items:center;';
  const termIn = document.createElement('input');
  termIn.type = 'text';
  termIn.placeholder = 'Komut çalıştır (ör. python main.py --help veya pytest)...';
  termIn.style.cssText = 'flex:1;background:#161b26;border:1px solid #334155;color:#f8fafc;border-radius:6px;padding:5px 8px;font-family:Consolas,monospace;font-size:12px;';
  const termRunBtn = document.createElement('button');
  termRunBtn.type = 'button';
  termRunBtn.className = 'ide-btn primary';
  termRunBtn.textContent = 'Çalıştır';
  async function runTerminalCommand() {
    const cmd = termIn.value.trim();
    if (!cmd) return;
    termRunBtn.disabled = true;
    termOut.textContent += `\n$ ${cmd}\n`;
    try {
      const r = await fetch(`/api/studio/workspaces/${wsId}/exec`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd }),
      });
      const d = await r.json();
      termOut.textContent += (d.stdout || '') + (d.stderr ? `\n${d.stderr}` : '');
      termOut.scrollTop = termOut.scrollHeight;
    } catch (e) {
      termOut.textContent += `\nHata: ${e.message}`;
    } finally {
      termRunBtn.disabled = false;
      termIn.value = '';
    }
  }
  termRunBtn.addEventListener('click', runTerminalCommand);
  termIn.addEventListener('keydown', (e) => { if (e.key === 'Enter') runTerminalCommand(); });
  termRow.append(termIn, termRunBtn);
  termDrawer.append(termOut, termRow);
  card.appendChild(termDrawer);

  termToggleBtn.addEventListener('click', () => {
    termDrawer.hidden = !termDrawer.hidden;
    termToggleBtn.classList.toggle('primary', !termDrawer.hidden);
    if (!termDrawer.hidden) termIn.focus();
  });

  gitWsBtn.addEventListener('click', async () => {
    termDrawer.hidden = false;
    termToggleBtn.classList.add('primary');
    try {
      await fetch(`/api/studio/workspaces/${wsId}/git`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'commit', message: 'IDE otomatik kayıt' }),
      });
      const r = await fetch(`/api/studio/workspaces/${wsId}/git`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'status' }),
      });
      const d = await r.json();
      termOut.textContent = d.output || 'Git hazır.';
    } catch (e) {
      termOut.textContent = `Git hatası: ${e.message}`;
    }
  });

  searchWsBtn.addEventListener('click', async () => {
    const q = prompt('Proje dosyalarında ara (Ctrl+Shift+F):');
    if (!q || !q.trim()) return;
    termDrawer.hidden = false;
    termToggleBtn.classList.add('primary');
    try {
      const r = await fetch(`/api/studio/workspaces/${wsId}/search?q=${encodeURIComponent(q.trim())}`);
      const d = await r.json();
      const list = d.matches || [];
      termOut.textContent = list.length
        ? `--- ARAMA SONUÇLARI ("${q}") ---\n` + list.map((m) => `${m.path}:${m.line}  ${m.snippet}`).join('\n')
        : `"${q}" için eşleşme bulunamadı.`;
    } catch (e) {
      termOut.textContent = `Arama hatası: ${e.message}`;
    }
  });

  // --- 3. AI ITERATION BAR & VS CODE STATUS BAR ---
  const iterBar = document.createElement('div');
  iterBar.className = 'ide-iter-bar';
  const iterIn = document.createElement('input');
  iterIn.type = 'text';
  iterIn.placeholder = 'AI ile bu projeyi geliştir (ör. "Karanlık mod ekle", "Yeni sayfa/özellik ekle")...';
  const iterBtn = document.createElement('button');
  iterBtn.type = 'button';
  iterBtn.className = 'ide-btn primary';
  iterBtn.textContent = 'Geliştir';
  iterBar.append(iterIn, iterBtn);

  const statusBar = document.createElement('div');
  statusBar.className = 'ide-statusbar';
  const statusLeft = document.createElement('div');
  statusLeft.className = 'ide-status-side';
  statusLeft.innerHTML = '<span>⎇ main</span><span>✓ 0 hata</span>';
  const statusRight = document.createElement('div');
  statusRight.className = 'ide-status-side';
  const statusLines = document.createElement('span');
  statusLines.textContent = '0 satır';
  const statusLang = document.createElement('span');
  statusLang.textContent = 'UTF-8';
  statusRight.append(statusLines, statusLang);
  statusBar.append(statusLeft, statusRight);

  card.append(iterBar, statusBar);

  // --- LOGIC FUNCTIONS ---
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
  btnModePrev.addEventListener('click', () => {
    iframe.src = `/api/studio/workspaces/${wsId}/preview/index.html?t=${Date.now()}`;
    setViewMode('preview');
  });
  btnModeSplit.addEventListener('click', () => {
    iframe.src = `/api/studio/workspaces/${wsId}/preview/index.html?t=${Date.now()}`;
    setViewMode('split');
  });

  function renderCodeView(content, path) {
    activeContent = content || '';
    const lines = activeContent.split('\n');
    gutter.innerHTML = lines.map((_, i) => `<div>${i + 1}</div>`).join('');
    codeBlock.innerHTML = highlightCodeHtml(activeContent, path);
    rawTextarea.value = activeContent;
    statusLines.textContent = `${lines.length} satır`;
    statusLang.textContent = `${detectLangLabel(path)} · UTF-8`;
    breadcrumb.innerHTML = `<span class="bc-root">${wsMeta.name || wsId}</span> › ` +
      (path || '').split('/').map((p) => `<span>${p}</span>`).join(' › ');
  }

  function renderTabs() {
    tabBar.innerHTML = '';
    for (const p of openTabs) {
      const fname = p.split('/').pop();
      const tab = document.createElement('div');
      tab.className = 'ide-tab' + (p === activePath ? ' active' : '');
      const iconSpan = document.createElement('span');
      iconSpan.innerHTML = wsSvgIcon(fname, false);
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
          else {
            activePath = null;
            renderTabs();
            renderCodeView('', '');
          }
        } else {
          renderTabs();
        }
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

    if (fileCache.has(path)) {
      renderCodeView(fileCache.get(path), path);
      return;
    }
    renderCodeView('// Yükleniyor...', path);
    try {
      const resp = await fetch(`/api/studio/workspaces/${wsId}/file?path=${encodeURIComponent(path)}`);
      const data = await resp.json();
      const text = data.content || '';
      fileCache.set(path, text);
      if (activePath === path) renderCodeView(text, path);
    } catch (err) {
      renderCodeView(`// Dosya okunamadı: ${err.message}`, path);
    }
  }

  function renderTree() {
    treeContainer.innerHTML = '';
    function walk(nodes, depth = 0) {
      for (const node of nodes || []) {
        const isDir = node.type === 'dir';
        const isCollapsed = collapsedFolders.has(node.path);
        const row = document.createElement('div');
        row.className = 'ide-tree-row' + (!isDir && node.path === activePath ? ' active' : '');
        row.style.paddingLeft = `${10 + depth * 14}px`;

        const chev = isDir ? `<span class="ide-chev">${isCollapsed ? '▸' : '▾'}</span>` : '<span class="ide-chev"></span>';
        row.innerHTML = `${chev}${wsSvgIcon(node.name, isDir, !isCollapsed)}<span class="ide-node-name">${node.name}</span>`;

        row.addEventListener('click', () => {
          if (isDir) {
            if (isCollapsed) collapsedFolders.delete(node.path);
            else collapsedFolders.add(node.path);
            renderTree();
          } else {
            selectFile(node.path);
          }
        });
        treeContainer.appendChild(row);
        if (isDir && !isCollapsed && node.children) {
          walk(node.children, depth + 1);
        }
      }
    }
    walk(currentTree, 0);
  }

  let diffMode = false;
  diffToggleBtn.addEventListener('click', async () => {
    if (!activePath) return;
    diffMode = !diffMode;
    diffToggleBtn.classList.toggle('primary', diffMode);
    if (!diffMode) {
      renderCodeView(activeContent, activePath);
      return;
    }
    try {
      const r = await fetch(`/api/studio/workspaces/${wsId}/diff?path=${encodeURIComponent(activePath)}`);
      const d = await r.json();
      const lines = (d.diff || '').split('\n');
      gutter.innerHTML = lines.map((_, i) => `<div>${i + 1}</div>`).join('');
      codeBlock.innerHTML = lines.map((ln) => {
        const esc = ln.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        if (ln.startsWith('+') && !ln.startsWith('+++')) return `<div class="diff-add">${esc}</div>`;
        if (ln.startsWith('-') && !ln.startsWith('---')) return `<div class="diff-del">${esc}</div>`;
        if (ln.startsWith('@@')) return `<div class="diff-hunk">${esc}</div>`;
        return `<div>${esc}</div>`;
      }).join('');
    } catch {
      diffMode = false;
    }
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
      statusLeft.innerHTML = `<span>⎇ main</span><span>${errCount + issueCount === 0 ? '✓ 0 hata / SAST temiz' : `! ${errCount} hata · ${issueCount} SAST`} · ${symCount} AST sembol</span>`;
    } catch {
      /* ignore */
    } finally {
      secScanBtn.disabled = false;
      secScanBtn.textContent = 'Güvenlik & AST';
    }
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
    try {
      await fetch(`/api/studio/workspaces/${wsId}/file`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: activePath, content: rawTextarea.value }),
      });
      fileCache.set(activePath, rawTextarea.value);
      editMode = false;
      codeBlock.hidden = false;
      rawTextarea.hidden = true;
      saveFileBtn.hidden = true;
      editToggleBtn.textContent = 'Düzenle';
      renderCodeView(rawTextarea.value, activePath);
      if (viewMode === 'split') {
        iframe.src = `/api/studio/workspaces/${wsId}/preview/index.html?t=${Date.now()}`;
      }
    } finally {
      saveFileBtn.disabled = false;
      saveFileBtn.textContent = 'Kaydet';
    }
  });

  newFileBtn.addEventListener('click', async () => {
    const rel = prompt('Yeni dosya yolu (ör. css/theme.css veya js/modal.js):');
    if (!rel || !rel.trim()) return;
    const clean = rel.trim();
    await fetch(`/api/studio/workspaces/${wsId}/file`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: clean, content: '' }),
    });
    const tResp = await fetch(`/api/studio/workspaces/${wsId}/tree`);
    const tData = await tResp.json();
    currentTree = tData.tree || currentTree;
    fileCache.set(clean, '');
    await selectFile(clean);
  });

  iterBtn.addEventListener('click', async () => {
    const instr = iterIn.value.trim();
    if (!instr) return;
    iterBtn.disabled = true;
    iterBtn.textContent = 'Güncelleniyor...';
    try {
      const resp = await fetch(`/api/studio/workspaces/${wsId}/iterate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruction: instr }),
      });
      const reader = resp.body.getReader();
      const dec = new TextDecoder();
      let buf = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop();
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          let evt;
          try { evt = JSON.parse(line.slice(6)); } catch { continue; }
          if (evt.type === 'file_done') {
            fileCache.delete(evt.path);
          } else if (evt.type === 'done' && evt.tree) {
            currentTree = evt.tree;
            renderTree();
            if (activePath) {
              fileCache.delete(activePath);
              await selectFile(activePath);
            }
            if (viewMode === 'preview' || viewMode === 'split') {
              iframe.src = `/api/studio/workspaces/${wsId}/preview/index.html?t=${Date.now()}`;
            }
            refreshVersions();
          }
        }
      }
      iterIn.value = '';
    } finally {
      iterBtn.disabled = false;
      iterBtn.textContent = 'Geliştir';
    }
  });
  iterIn.addEventListener('keydown', (e) => { if (e.key === 'Enter') iterBtn.click(); });

  // Auto-open entry point (index.html / main.py) or first text file
  const flatPaths = [];
  function collectFiles(nodes) {
    for (const n of nodes || []) {
      if (n.type === 'file' && !n.name.endsWith('.exe')) flatPaths.push(n.path);
      else if (n.children) collectFiles(n.children);
    }
  }
  collectFiles(currentTree);
  renderTree();
  const entry = (wsMeta.entry_point && flatPaths.includes(wsMeta.entry_point))
    ? wsMeta.entry_point
    : (flatPaths.find((p) => p === 'index.html' || p === 'main.py') || flatPaths[0]);
  if (entry) {
    selectFile(entry);
  }

  return card;
}

let els;
let selectedFile = null;
let started = false;
let currentChatId = null;
let currentMessages = []; // {role: 'user'|'assistant', text, modelBadge?, fileName?}
let pendingDeleteId = null;

function loadChats() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
  } catch {
    return {};
  }
}

function saveChats(chats) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chats));
  } catch { /* storage may be full or unavailable; history is a convenience only */ }
}

function persistCurrentChat() {
  if (!currentChatId || currentMessages.length === 0) return;
  const chats = loadChats();
  const firstUserMsg = currentMessages.find((m) => m.role === 'user');
  const title = firstUserMsg ? firstUserMsg.text.slice(0, 40) : 'Yeni sohbet';
  const updatedAt = Date.now();
  const record = { title, updatedAt, messages: currentMessages };
  chats[currentChatId] = record;
  saveChats(chats);
  try { localStorage.setItem(LAST_CHAT_KEY, currentChatId); } catch { /* ignore */ }
  renderChatList();
  // Persist to local SQLite server disk so chats never disappear across restarts or browsers
  const uid = getActiveUserId();
  const cid = currentChatId;
  fetch(`/api/user/${encodeURIComponent(uid)}/chats/${encodeURIComponent(cid)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(record),
  }).catch(() => { /* offline fallback already in localStorage */ });
}

function deleteChat(id) {
  const chats = loadChats();
  delete chats[id];
  saveChats(chats);
  pendingDeleteId = null;
  const uid = getActiveUserId();
  fetch(`/api/user/${encodeURIComponent(uid)}/chats/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  }).catch(() => { /* ignore */ });
  if (id === currentChatId) startNewChat();
  else renderChatList();
}

async function syncChatsWithServer() {
  const uid = getActiveUserId();
  const localChats = loadChats();
  try {
    const resp = await fetch(`/api/user/${encodeURIComponent(uid)}/chats`);
    if (!resp.ok) return;
    const data = await resp.json();
    const serverChats = (data && data.chats) || {};
    const merged = { ...serverChats };
    const toUpload = [];
    for (const [cid, lchat] of Object.entries(localChats)) {
      if (!lchat || !Array.isArray(lchat.messages) || lchat.messages.length === 0) continue;
      const schat = serverChats[cid];
      if (!schat || (lchat.updatedAt || 0) > (schat.updatedAt || 0)) {
        merged[cid] = lchat;
        toUpload.push([cid, lchat]);
      }
    }
    saveChats(merged);
    renderChatList();
    for (const [cid, chatObj] of toUpload) {
      fetch(`/api/user/${encodeURIComponent(uid)}/chats/${encodeURIComponent(cid)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chatObj),
      }).catch(() => { /* ignore */ });
    }
    // If the user has not typed anything yet, restore their last active chat if one exists
    if (!started && currentMessages.length === 0) {
      const lastId = localStorage.getItem(LAST_CHAT_KEY);
      if (lastId && merged[lastId] && merged[lastId].messages && merged[lastId].messages.length > 0) {
        openChat(lastId);
      }
    }
  } catch {
    /* keep localStorage chats if server is unreachable */
  }
}

function renderChatList() {
  const chats = loadChats();
  els.chatList.innerHTML = '';
  const q = (els.chatSearchInput ? els.chatSearchInput.value : '').trim().toLowerCase();
  const sorted = Object.entries(chats).sort((a, b) => b[1].updatedAt - a[1].updatedAt);
  for (const [id, chat] of sorted) {
    if (q) {
      const inTitle = (chat.title || '').toLowerCase().includes(q);
      const inMsgs = (chat.messages || []).some((m) => (m.text || '').toLowerCase().includes(q));
      if (!inTitle && !inMsgs) continue;
    }
    const item = document.createElement('div');
    item.className = 'chat-item' + (id === currentChatId ? ' active' : '');

    if (pendingDeleteId === id) {
      // In-page confirmation instead of the native confirm() dialog.
      item.classList.add('confirm-mode');
      const label = document.createElement('span');
      label.textContent = 'Silinsin mi?';
      label.style.fontSize = '12px';
      item.appendChild(label);

      const yes = document.createElement('span');
      yes.className = 'confirm-yes';
      yes.textContent = 'Evet';
      yes.addEventListener('click', (e) => { e.stopPropagation(); deleteChat(id); });
      item.appendChild(yes);

      const no = document.createElement('span');
      no.className = 'confirm-no';
      no.textContent = 'Vazgeç';
      no.addEventListener('click', (e) => { e.stopPropagation(); pendingDeleteId = null; renderChatList(); });
      item.appendChild(no);
    } else {
      const titleSpan = document.createElement('span');
      titleSpan.textContent = chat.title || 'Sohbet';
      item.appendChild(titleSpan);

      const del = document.createElement('span');
      del.className = 'del';
      del.textContent = '✕';
      del.title = 'Sohbeti sil';
      del.addEventListener('click', (e) => {
        e.stopPropagation();
        pendingDeleteId = id;
        renderChatList();
      });
      item.appendChild(del);
      item.addEventListener('click', () => openChat(id));
    }

    els.chatList.appendChild(item);
  }
}

function openChat(id) {
  const chat = loadChats()[id];
  if (!chat) return;
  currentChatId = id;
  try { localStorage.setItem(LAST_CHAT_KEY, id); } catch { /* ignore */ }
  currentMessages = chat.messages.slice();
  els.messages.innerHTML = '';
  ensureStarted();
  for (const m of currentMessages) {
    if (m.role === 'user') addUserMessage(m.text, m.fileName, false);
    else {
      const row = addAssistantMessage(m.text, m.modelBadge, m.isError, false, false);
      if (m.workspace) {
        row.querySelector('.msg-wrap').appendChild(buildInlineWorkspaceCard(m.workspace.workspace, m.workspace.tree));
      }
    }
  }
  renderChatList();
  closeSidebar();
}

function startNewChat(clearLastActive = false) {
  if (clearLastActive) {
    try { localStorage.removeItem(LAST_CHAT_KEY); } catch { /* ignore */ }
  }
  currentChatId = 'chat_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
  currentMessages = [];
  els.messages.innerHTML = '';
  els.messages.classList.remove('active');
  els.centerStage.style.display = 'flex';
  started = false;
  renderChatList();
  closeSidebar();
}

function updateSendState() {
  els.sendBtn.classList.toggle('ready', els.promptInput.value.trim().length > 0);
}

function ensureStarted() {
  if (!started) {
    started = true;
    els.centerStage.style.display = 'none';
    els.messages.classList.add('active');
  }
}

function addUserMessage(text, fileName, record = true) {
  const msgIdx = currentMessages.length;
  const row = document.createElement('div');
  row.className = 'msg-row user';
  const wrap = document.createElement('div');
  wrap.style.cssText = 'display:flex;flex-direction:column;align-items:flex-end;max-width:65%;';
  const bubble = document.createElement('div');
  bubble.className = 'msg user';
  bubble.style.maxWidth = '100%';
  bubble.textContent = fileName ? `[Dosya: ${fileName}]\n${text}` : text;

  const branchBtn = document.createElement('span');
  branchBtn.className = 'download-link sp-branch-link';
  branchBtn.style.marginTop = '3px';
  branchBtn.textContent = 'Düzenle & Dallandır';
  branchBtn.title = 'Bu mesajı düzenleyerek sohbeti buradan yeni bir dala ayır';
  branchBtn.addEventListener('click', () => {
    els.promptInput.value = text;
    els.promptInput.style.height = 'auto';
    els.promptInput.style.height = Math.min(els.promptInput.scrollHeight, 160) + 'px';
    currentMessages = currentMessages.slice(0, msgIdx);
    while (row.nextSibling) row.nextSibling.remove();
    row.remove();
    updateSendState();
    els.promptInput.focus();
  });

  wrap.append(bubble, branchBtn);
  row.appendChild(wrap);
  els.messages.appendChild(row);
  els.messages.scrollTop = els.messages.scrollHeight;
  if (record) currentMessages.push({ role: 'user', text, fileName });
}

function addAssistantMessage(text, modelBadge, isError, isThinking, record = true) {
  const row = document.createElement('div');
  row.className = 'msg-row assistant';
  const wrap = document.createElement('div');
  wrap.className = 'msg-wrap';

  if (modelBadge) {
    const badgeRow = document.createElement('div');
    badgeRow.className = 'badge-row';
    const badge = document.createElement('span');
    badge.className = 'badge';
    badge.textContent = modelBadge;
    badgeRow.appendChild(badge);
    wrap.appendChild(badgeRow);
  }

  const bubble = document.createElement('div');
  bubble.className = 'msg assistant' + (isError ? ' error' : '') + (isThinking ? ' thinking' : '');
  if (isError || isThinking) {
    bubble.textContent = text;
  } else {
    bubble.innerHTML = renderMarkdown(text);
  }
  wrap.appendChild(bubble);

  if (!isError && !isThinking) {
    wrap.appendChild(createMessageActions(text));
  }

  row.appendChild(wrap);
  els.messages.appendChild(row);
  els.messages.scrollTop = els.messages.scrollHeight;
  if (record && !isThinking) currentMessages.push({ role: 'assistant', text, modelBadge, isError });
  return row;
}

function createMessageActions(text) {
  const bar = document.createElement('div');
  bar.style.display = 'flex';
  bar.style.gap = '12px';
  bar.style.marginTop = '5px';

  const copyBtn = document.createElement('span');
  copyBtn.className = 'download-link';
  copyBtn.textContent = 'Kopyala';
  copyBtn.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(text);
      copyBtn.textContent = 'Kopyalandı';
      setTimeout(() => { copyBtn.textContent = 'Kopyala'; }, 1600);
    } catch {
      copyBtn.textContent = 'Kopyalanamadı';
    }
  });

  const dl = document.createElement('span');
  dl.className = 'download-link';
  dl.textContent = 'Dosya olarak indir';
  dl.addEventListener('click', () => downloadAsFile(text));

  const ttsBtn = document.createElement('span');
  ttsBtn.className = 'download-link';
  ttsBtn.textContent = 'Sesli oku';
  ttsBtn.addEventListener('click', () => {
    if (!('speechSynthesis' in window)) return;
    if (window.speechSynthesis.speaking) {
      window.speechSynthesis.cancel();
      ttsBtn.textContent = 'Sesli oku';
      return;
    }
    const clean = String(text || '').replace(/```[\s\S]*?```/g, '').replace(/[#*|`_~]/g, ' ').slice(0, 1800);
    const utt = new SpeechSynthesisUtterance(clean);
    utt.lang = 'tr-TR';
    utt.onend = () => { ttsBtn.textContent = 'Sesli oku'; };
    utt.onerror = () => { ttsBtn.textContent = 'Sesli oku'; };
    ttsBtn.textContent = 'Durdur';
    window.speechSynthesis.speak(utt);
  });

  bar.append(copyBtn, ttsBtn, dl);
  return bar;
}

function downloadAsFile(text) {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'yanit.txt';
  a.click();
  URL.revokeObjectURL(url);
}

let activeStreamAbortController = null;

async function sendMessage() {
  if (activeStreamAbortController) {
    activeStreamAbortController.abort();
    activeStreamAbortController = null;
    return;
  }
  const prompt = els.promptInput.value.trim();
  if (!prompt) return;

  ensureStarted();
  addUserMessage(prompt, selectedFile ? selectedFile.name : null);

  const fileToSend = selectedFile;
  els.promptInput.value = '';
  els.promptInput.style.height = 'auto';
  selectedFile = null;
  els.fileInput.value = '';
  els.fileChip.classList.remove('active');
  activeStreamAbortController = new AbortController();
  els.sendBtn.textContent = '■';
  els.sendBtn.title = 'Yanıtı durdur';
  els.sendBtn.classList.add('ready');

  // Create an animated thinking + streaming bubble with spinning wheel, stages, and live timer
  const row = document.createElement('div');
  row.className = 'msg-row assistant';
  const wrap = document.createElement('div');
  wrap.className = 'msg-wrap';

  const streamBar = document.createElement('div');
  streamBar.className = 'sp-stream-bar';
  streamBar.hidden = true;
  streamBar.innerHTML = '<span class="sp-think-ring sm"></span><span class="sp-stream-text">Yanıt yazılıyor...</span>';

  const bubble = document.createElement('div');
  bubble.className = 'msg assistant thinking';
  const stages = fileToSend
    ? ['Dosya okunuyor ve denetleniyor', 'Bağlam ve hafıza taranıyor', 'Düşünüyor ve analiz ediyor', 'Yanıt hazırlanıyor']
    : ['Düşünüyor', 'Hafıza ve bilgi bankası taranıyor', 'Yanıt hazırlanıyor'];
  bubble.innerHTML = `
    <div class="sp-think-head">
      <span class="sp-think-ring"></span>
      <span class="sp-think-label">${stages[0]}<span class="sp-think-dots"><i></i><i></i><i></i></span></span>
      <span class="sp-think-timer">0 sn</span>
    </div>
    <div class="sp-think-skel"><span></span><span></span><span></span></div>
  `;
  const thinkLabelEl = bubble.querySelector('.sp-think-label');
  const thinkTimerEl = bubble.querySelector('.sp-think-timer');
  const streamTextEl = streamBar.querySelector('.sp-stream-text');
  const startedAt = performance.now();
  let stageIdx = 0;
  const thinkTicker = setInterval(() => {
    const sec = (performance.now() - startedAt) / 1000;
    const secStr = `${Math.floor(sec)} sn`;
    if (!streaming) {
      if (thinkTimerEl) thinkTimerEl.textContent = secStr;
      const nextIdx = Math.min(stages.length - 1, Math.floor(sec / 2.2));
      if (nextIdx !== stageIdx && thinkLabelEl) {
        stageIdx = nextIdx;
        thinkLabelEl.innerHTML = `${stages[stageIdx]}<span class="sp-think-dots"><i></i><i></i><i></i></span>`;
      }
    } else if (streamTextEl) {
      streamTextEl.textContent = `Yanıt yazılıyor · ${secStr}`;
    }
  }, 250);

  wrap.append(streamBar, bubble);
  row.appendChild(wrap);
  els.messages.appendChild(row);
  els.messages.scrollTop = els.messages.scrollHeight;

  let fullText = '';
  let usedModel = '';
  let taskType = '';
  let streaming = false;
  let builtWorkspace = null;
  let usageInfo = null;
  let latencyMs = 0;
  let councilTrace = null;
  const reqStartMs = performance.now();
  let ttftMs = 0;

  try {
    const formData = new FormData();
    formData.append('prompt', prompt);
    formData.append('history', JSON.stringify(currentMessages.slice(-11, -1)));
    formData.append('user_id', getActiveUserId());
    formData.append('conversation_id', currentChatId || '');
    if (fileToSend) formData.append('file', fileToSend);

    const resp = await fetch('/api/assistant/chat/stream', {
      method: 'POST',
      body: formData,
      signal: activeStreamAbortController.signal,
    });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      row.remove();
      addAssistantMessage(data.detail || 'Bilinmeyen hata', null, true, false);
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep incomplete line

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        let evt;
        try { evt = JSON.parse(line.slice(6)); } catch { continue; }

        if (evt.type === 'token') {
          if (!streaming) {
            streaming = true;
            ttftMs = Math.max(1, Math.round(performance.now() - reqStartMs));
            bubble.classList.remove('thinking');
            bubble.classList.add('streaming');
            bubble.textContent = '';
            streamBar.hidden = false;
          }
          fullText += evt.content;
          bubble.innerHTML = renderMarkdown(fullText);
          els.messages.scrollTop = els.messages.scrollHeight;
        } else if (evt.type === 'council') {
          councilTrace = evt.council;
        } else if (evt.type === 'workspace') {
          builtWorkspace = { workspace: evt.workspace, tree: evt.tree };
        } else if (evt.type === 'done') {
          usedModel = evt.model || '';
          taskType = evt.task_type || '';
          usageInfo = evt.usage || null;
          latencyMs = evt.latency_ms || 0;
        } else if (evt.type === 'error') {
          row.remove();
          addAssistantMessage('Model hatası: ' + evt.content, null, true, false);
          return;
        }
      }
    }

    // Finalise the bubble: add badge, inline workspace explorer (if built), and download link
    if (fullText || builtWorkspace) {
      bubble.innerHTML = renderMarkdown(fullText);
      if (builtWorkspace) {
        wrap.appendChild(buildInlineWorkspaceCard(builtWorkspace.workspace, builtWorkspace.tree));
      }
      const label = MODEL_LABELS[usedModel] || usedModel;
      if (label && getPrefs().show_model_badge) {
        const badgeRow = document.createElement('div');
        badgeRow.className = 'badge-row';
        const badge = document.createElement('span');
        badge.className = 'badge';
        badge.textContent = label;
        badgeRow.appendChild(badge);
        wrap.insertBefore(badgeRow, bubble);
      }
      if (councilTrace) {
        const det = document.createElement('details');
        det.className = 'sp-card';
        det.style.marginBottom = '6px';
        det.innerHTML = `<summary style="cursor:pointer;font-weight:600;font-size:12.5px;">Ajan Konseyi Düşünce Zinciri ve Hakem Sentezi</summary><pre class="sp-preview-pre" style="margin-top:8px;">${escapeHtml(JSON.stringify(councilTrace, null, 2))}</pre>`;
        wrap.insertBefore(det, bubble);
      }
      if (usageInfo && getPrefs().show_token_counter) {
        const meta = document.createElement('div');
        meta.className = 'sp-meta';
        const approx = usageInfo.estimated ? '~' : '';
        const total = (usageInfo.prompt_tokens || 0) + (usageInfo.completion_tokens || 0);
        const parts = [
          `${approx}${total.toLocaleString('tr-TR')} token`,
          `${approx}${(usageInfo.prompt_tokens || 0).toLocaleString('tr-TR')} giriş / ${approx}${(usageInfo.completion_tokens || 0).toLocaleString('tr-TR')} çıkış`,
        ];
        if (ttftMs) parts.push(`TTFT ${ttftMs} ms`);
        if (latencyMs) {
          parts.push(`${(latencyMs / 1000).toFixed(1).replace('.', ',')} sn`);
          const tokPerSec = ((usageInfo.completion_tokens || 1) / Math.max(0.1, latencyMs / 1000)).toFixed(1).replace('.', ',');
          parts.push(`${tokPerSec} tok/sn`);
        }
        for (const p of parts) {
          const s = document.createElement('span');
          s.textContent = p;
          meta.appendChild(s);
        }
        wrap.appendChild(meta);
      }
      wrap.appendChild(createMessageActions(fullText));

      currentMessages.push({ role: 'assistant', text: fullText, modelBadge: MODEL_LABELS[usedModel] || usedModel, isError: false, workspace: builtWorkspace });
    }
  } catch (err) {
    if (err && err.name === 'AbortError') {
      fullText += '\n\n*[Yanıt kullanıcı tarafından durduruldu]*';
      bubble.classList.remove('thinking');
      bubble.innerHTML = renderMarkdown(fullText);
      wrap.appendChild(createMessageActions(fullText));
      currentMessages.push({ role: 'assistant', text: fullText, modelBadge: MODEL_LABELS[usedModel] || usedModel, isError: false });
    } else {
      row.remove();
      addAssistantMessage('Bağlantı hatası: ' + err.message, null, true, false);
    }
  } finally {
    clearInterval(thinkTicker);
    bubble.classList.remove('thinking', 'streaming');
    streamBar.remove();
    activeStreamAbortController = null;
    els.sendBtn.textContent = '↑';
    els.sendBtn.title = '';
    els.sendBtn.disabled = false;
    updateSendState();
    els.promptInput.focus();
    persistCurrentChat();
    document.dispatchEvent(new CustomEvent('usage-updated'));
  }
}

export function initAssistant() {
  const byId = (id) => document.getElementById(id);
  els = {
    messages: byId('messages'),
    centerStage: byId('centerStage'),
    promptInput: byId('promptInput'),
    sendBtn: byId('sendBtn'),
    micBtn: byId('micBtn'),
    attachBtn: byId('attachBtn'),
    fileInput: byId('fileInput'),
    fileChip: byId('fileChip'),
    fileChipName: byId('fileChipName'),
    removeFile: byId('removeFile'),
    chatList: byId('chatList'),
    chatSearchInput: byId('chatSearchInput'),
    heroCards: byId('heroCards'),
    newChatBtn: byId('newChatBtn'),
  };

  if (els.chatSearchInput) {
    els.chatSearchInput.addEventListener('input', renderChatList);
  }
  renderHeroCards();

  els.promptInput.addEventListener('input', () => {
    els.promptInput.style.height = 'auto';
    els.promptInput.style.height = Math.min(els.promptInput.scrollHeight, 160) + 'px';
    updateSendState();
  });
  els.attachBtn.addEventListener('click', () => els.fileInput.click());
  els.fileInput.addEventListener('change', () => {
    if (els.fileInput.files.length > 0) {
      selectedFile = els.fileInput.files[0];
      els.fileChipName.textContent = selectedFile.name;
      els.fileChip.classList.add('active');
    }
  });
  els.removeFile.addEventListener('click', () => {
    selectedFile = null;
    els.fileInput.value = '';
    els.fileChip.classList.remove('active');
  });
  els.sendBtn.addEventListener('click', sendMessage);
  els.promptInput.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' || e.shiftKey) return;
    const enterSends = getPrefs().send_with_enter !== false;
    if (enterSends || e.ctrlKey || e.metaKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  els.newChatBtn.addEventListener('click', () => {
    persistCurrentChat();
    startNewChat(true);
  });
  const brandHomeLink = document.getElementById('brandHomeLink');
  if (brandHomeLink) {
    brandHomeLink.addEventListener('click', (e) => {
      e.preventDefault();
      persistCurrentChat();
      startNewChat(true);
      if (location.hash !== '#/assistant') {
        location.hash = '#/assistant';
      }
    });
  }
  els.messages.addEventListener('click', handleRunCodeClick);
  initVoiceRecognition();
  showRunButtonsIfEnabled();

  startNewChat(false);
  syncChatsWithServer();
}

function renderHeroCards() {
  if (!els || !els.heroCards) return;
  const cards = [
    {
      title: 'Kod, Web ve Masaüstü Proje Geliştirme',
      tag: 'IDE · Web · .EXE',
      desc: 'Çok klasörlü web sitesi, masaüstü uygulaması veya oyun oluşturun; gömülü kod editöründe canlı önizleyin, düzenleyin ve .EXE olarak derleyin.',
      prompt: 'Modern karanlık arayüzlü, arama ve filtreleme özellikli bir görev ve proje takip web uygulaması oluştur.',
    },
    {
      title: 'Doküman, Sunum ve Tablo Üretimi',
      tag: '.XLSX · .DOCX · .PPTX · .PDF',
      desc: 'İstediğiniz herhangi bir konuda formüllü ve grafikli Excel tablosu, Word raporu, PowerPoint sunumu veya Türkçe karakter uyumlu PDF oluşturun.',
      prompt: 'Aylık kişisel bütçe ve harcama takibi için formüllü, grafikli ve kategorili bir Excel (.xlsx) tablosu oluştur.',
    },
    {
      title: 'Görsel Tasarım ve Fotoğraf Düzenleme',
      tag: 'Görsel · Filtre · Tarayıcı',
      desc: 'Metin komutundan görsel, logo veya afiş üretin; yüklediğiniz fotoğrafları düzenleyin, arka planı temizleyin veya belge gölgelerini giderin.',
      prompt: 'Minimalist ve modern bir teknoloji markası için yüksek çözünürlüklü kurumsal bir logo ve görsel tasarım üret.',
    },
    {
      title: 'Dosya Analizi ve Hata Denetimi',
      tag: 'Kod · PDF · Excel · CSV',
      desc: 'Herhangi bir kod, PDF, Word, Excel, CSV veya JSON dosyası yükleyin; sözdizimi, formül ve veri hatalarını satır satır yakalayın.',
      prompt: 'Yüklediğim dosyayı satır satır incele, bulduğun tüm hataları ve iyileştirme önerilerini listele.',
      attach: true,
    },
    {
      title: 'Veri Bilimi, Tahminleme ve SQL',
      tag: 'AutoML · Grafik · SQL',
      desc: 'Veri setlerindeki trendleri ve anormallikleri analiz edin, gelecek dönem tahminleri yapın, veritabanlarını doğal dille sorgulayın.',
      prompt: '12 aylık örnek satış ve maliyet verisi üzerinden trend analizi, gelecek 3 ay tahmini ve özet grafik raporu hazırla.',
    },
    {
      title: 'Araştırma, Hukuk, Finans ve Teknik Analiz',
      tag: 'Konsey · Analiz · Rapor',
      desc: 'Sözleşme risk incelemesi, finansal değerleme, derin araştırma, akademik özetleme veya 2B/3B teknik çizim analizi yapın.',
      prompt: 'Yeni bir yazılım girişimi için 5 yıllık finansal değerleme (DCF) ve yatırım risk analizi raporu hazırla.',
    },
  ];
  els.heroCards.innerHTML = '';
  for (const c of cards) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'sp-hero-card';
    btn.innerHTML = `
      <div class="sp-hero-card-top">
        <span class="sp-hero-card-title">${c.title}</span>
        <span class="sp-hero-card-tag">${c.tag}</span>
      </div>
      <div class="sp-hero-card-desc">${c.desc}</div>
    `;
    btn.addEventListener('click', () => {
      els.promptInput.value = c.prompt;
      els.promptInput.style.height = 'auto';
      els.promptInput.style.height = Math.min(els.promptInput.scrollHeight, 160) + 'px';
      updateSendState();
      if (c.attach) els.fileInput.click();
      else els.promptInput.focus();
    });
    els.heroCards.appendChild(btn);
  }
}

function encodeMonoWav16k(chunks, inputSampleRate) {
  let totalLen = 0;
  for (const c of chunks) totalLen += c.length;
  const merged = new Float32Array(totalLen);
  let offset = 0;
  for (const c of chunks) { merged.set(c, offset); offset += c.length; }

  const targetRate = 16000;
  const ratio = inputSampleRate / targetRate;
  const outLen = Math.max(1, Math.floor(merged.length / ratio));
  const pcm = new Int16Array(outLen);
  for (let i = 0; i < outLen; i++) {
    const s = Math.max(-1, Math.min(1, merged[Math.floor(i * ratio)] || 0));
    pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }

  const buf = new ArrayBuffer(44 + pcm.length * 2);
  const view = new DataView(buf);
  const writeStr = (pos, str) => { for (let i = 0; i < str.length; i++) view.setUint8(pos + i, str.charCodeAt(i)); };
  writeStr(0, 'RIFF');
  view.setUint32(4, 36 + pcm.length * 2, true);
  writeStr(8, 'WAVE');
  writeStr(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, targetRate, true);
  view.setUint32(28, targetRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, 'data');
  view.setUint32(40, pcm.length * 2, true);
  for (let i = 0; i < pcm.length; i++) view.setInt16(44 + i * 2, pcm[i], true);
  return new Blob([buf], { type: 'audio/wav' });
}

function initVoiceRecognition() {
  if (!els.micBtn) return;

  const statusPill = document.createElement('div');
  statusPill.className = 'sp-voice-status';
  statusPill.hidden = true;
  const inputWrap = document.getElementById('inputWrap');
  if (inputWrap) inputWrap.insertBefore(statusPill, document.getElementById('inputPill'));

  let recording = false;
  let mediaStream = null;
  let audioCtx = null;
  let processor = null;
  let pcmChunks = [];
  let recTimer = null;
  let recStart = 0;

  function showVoiceStatus(text, isLive = false) {
    statusPill.hidden = false;
    statusPill.innerHTML = isLive
      ? `<span class="sp-voice-dot"></span><span>${text}</span>`
      : `<span>${text}</span>`;
  }

  function hideVoiceStatus(delayMs = 0) {
    if (delayMs > 0) setTimeout(() => { if (!recording) statusPill.hidden = true; }, delayMs);
    else statusPill.hidden = true;
  }

  async function stopAndTranscribe() {
    recording = false;
    clearInterval(recTimer);
    els.micBtn.classList.remove('recording');
    els.micBtn.title = 'Sesli mesajı metne çevir';

    const sampleRate = (audioCtx && audioCtx.sampleRate) || 48000;
    try { if (processor) processor.disconnect(); } catch { /* ignore */ }
    try { if (audioCtx) await audioCtx.close(); } catch { /* ignore */ }
    try { if (mediaStream) mediaStream.getTracks().forEach((t) => t.stop()); } catch { /* ignore */ }
    mediaStream = null; audioCtx = null; processor = null;

    if (!pcmChunks.length) {
      hideVoiceStatus();
      return;
    }

    showVoiceStatus('Ses metne çevriliyor (yerel STT)...', false);
    const wavBlob = encodeMonoWav16k(pcmChunks, sampleRate);
    pcmChunks = [];

    try {
      const fd = new FormData();
      fd.append('file', wavBlob, 'mikrofon.wav');
      const resp = await fetch('/api/assistant/transcribe', { method: 'POST', body: fd });
      const data = await resp.json();
      if (resp.ok && data.transcript) {
        const prefix = els.promptInput.value.trim() ? els.promptInput.value.trim() + ' ' : '';
        els.promptInput.value = prefix + data.transcript;
        els.promptInput.style.height = 'auto';
        els.promptInput.style.height = Math.min(els.promptInput.scrollHeight, 160) + 'px';
        updateSendState();
        els.promptInput.focus();
        showVoiceStatus(`Metne çevrildi (${data.duration_sec || 0} sn)`, false);
        hideVoiceStatus(2200);
      } else {
        showVoiceStatus('Konuşma algılanamadı, tekrar deneyin.', false);
        hideVoiceStatus(2800);
      }
    } catch (err) {
      showVoiceStatus(`Ses çevirme hatası: ${err.message}`, false);
      hideVoiceStatus(3200);
    }
  }

  async function startRecording() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showVoiceStatus('Tarayıcı mikrofon erişimini desteklemiyor.', false);
      hideVoiceStatus(3200);
      return;
    }
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      audioCtx = new AudioCtx();
      const source = audioCtx.createMediaStreamSource(mediaStream);
      processor = audioCtx.createScriptProcessor(4096, 1, 1);
      pcmChunks = [];
      processor.onaudioprocess = (e) => {
        if (!recording) return;
        pcmChunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
      };
      source.connect(processor);
      processor.connect(audioCtx.destination);

      recording = true;
      recStart = Date.now();
      els.micBtn.classList.add('recording');
      els.micBtn.title = 'Kayıt yapılıyor... Durdurmak için tıklayın';
      showVoiceStatus('Dinleniyor · 0 sn (Bitirmek için mikrofona tekrar basın)', true);
      recTimer = setInterval(() => {
        const sec = Math.floor((Date.now() - recStart) / 1000);
        showVoiceStatus(`Dinleniyor · ${sec} sn (Bitirmek için mikrofona tekrar basın)`, true);
      }, 400);
    } catch (err) {
      showVoiceStatus(`Mikrofon izni alınamadı: ${err.name === 'NotAllowedError' ? 'Adres çubuğundan mikrofon iznini açın.' : err.message}`, false);
      hideVoiceStatus(4000);
    }
  }

  els.micBtn.addEventListener('click', () => {
    if (recording) stopAndTranscribe();
    else startRecording();
  });
}

// The master keeps code running off unless CODE_RUN_ENABLED is set, so the Run buttons stay
// hidden (body class) until the master confirms the feature is on.
async function showRunButtonsIfEnabled() {
  document.body.classList.add('code-run-disabled');
  try {
    const resp = await fetch('/api/assistant/config');
    const data = await resp.json();
    if (data.code_run_enabled) document.body.classList.remove('code-run-disabled');
  } catch {
    // Leave the buttons hidden when the master cannot be asked.
  }
}

// Delegated on the messages container: messages (including ones restored from chat history)
// are inserted via innerHTML, so a single listener here covers every "Run" button rather than
// binding one per code block.
async function handleRunCodeClick(e) {
  const btn = e.target.closest('.run-code-btn');
  if (!btn) return;
  const block = btn.closest('.code-block');
  const code = block.querySelector('pre code').textContent;
  const outputEl = block.querySelector('.run-output');

  btn.disabled = true;
  btn.textContent = 'Çalışıyor...';
  outputEl.hidden = false;
  outputEl.classList.remove('run-error');
  outputEl.textContent = '';

  try {
    const resp = await fetch('/api/assistant/run-code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      outputEl.textContent = data.detail || 'Kod çalıştırılamadı.';
      outputEl.classList.add('run-error');
    } else {
      const parts = [];
      if (data.stdout) parts.push(data.stdout);
      if (data.stderr) parts.push(data.stderr);
      outputEl.textContent = parts.join('\n') || '(çıktı yok)';
      outputEl.classList.toggle('run-error', data.exit_code !== 0);
    }
  } catch (err) {
    outputEl.textContent = 'Bağlantı hatası: ' + err.message;
    outputEl.classList.add('run-error');
  } finally {
    btn.disabled = false;
    btn.textContent = '▶ Çalıştır';
  }
}

export function focusAssistant() {
  els.promptInput.focus();
}
