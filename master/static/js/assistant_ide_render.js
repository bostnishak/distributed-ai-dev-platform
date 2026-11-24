// UX-02 Modular Split: IDE Workbench icons, syntax highlighting, terminal/git/search drawer, and iteration bar.
import { safeFetch, safeFetchJson } from './storage.js';
import { uiPrompt } from './ui_dialog.js';

export function wsSvgIcon(name, isDir, isOpen = true) {
  if (isDir) {
    const color = isOpen ? '#dcb67a' : '#c09553';
    return `<svg class="ide-svg-icon" viewBox="0 0 16 16" fill="${color}"><path d="M1.5 2A1.5 1.5 0 0 0 0 3.5v9A1.5 1.5 0 0 0 1.5 14h13a1.5 1.5 0 0 0 1.5-1.5v-7A1.5 1.5 0 0 0 14.5 4H7.71l-1.85-1.85A.5.5 0 0 0 5.5 2h-4z"/></svg>`;
  }
  const ext = (name.split('.').pop() || '').toLowerCase();
  const badges = {
    html: { bg: '#e44d26', fg: '#fff', txt: '<>' },
    htm: { bg: '#e44d26', fg: '#fff', txt: '<>' },
    css: { bg: '#264de4', fg: '#fff', txt: '#' },
    js: { bg: '#f7df1e', fg: '#111', txt: 'JS' },
    ts: { bg: '#3178c6', fg: '#fff', txt: 'TS' },
    py: { bg: '#3776ab', fg: '#ffd43b', txt: 'PY' },
    json: { bg: '#292929', fg: '#cbcb41', txt: '{}' },
    md: { bg: '#1f6feb', fg: '#fff', txt: 'M↓' },
    svg: { bg: '#ffb13b', fg: '#111', txt: 'SV' },
    exe: { bg: '#16a34a', fg: '#fff', txt: 'EX' },
  };
  const b = badges[ext];
  if (b) return `<span class="ide-ext-badge" style="background:${b.bg};color:${b.fg}">${b.txt}</span>`;
  return '<svg class="ide-svg-icon" viewBox="0 0 16 16" fill="#9cdcfe"><path d="M4 1h5.5L13 4.5V14a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1zm5 1.5V5h2.5L9 2.5z"/></svg>';
}

export function detectLangLabel(path) {
  const ext = ((path || '').split('.').pop() || '').toLowerCase();
  const map = {
    html: 'HTML5', css: 'CSS3', js: 'JavaScript (ES6)', py: 'Python 3',
    json: 'JSON', md: 'Markdown', svg: 'SVG XML', exe: 'Windows Binary',
  };
  return map[ext] || 'Plain Text';
}

export function highlightCodeHtml(code, path) {
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const ext = ((path || '').split('.').pop() || '').toLowerCase();
  let html = esc(code || '');
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
    html = html.replace(/\b([a-zA-Z-]+)(?=\x3d)/g, '<span class="hl-attr">$1</span>');
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

function wireTerminalActions(wsId, termDrawer, termOut, termToggleBtn, gitWsBtn, searchWsBtn) {
  gitWsBtn.addEventListener('click', async () => {
    termDrawer.hidden = false;
    termToggleBtn.classList.add('primary');
    await safeFetchJson(`/api/studio/workspaces/${wsId}/git`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'commit', message: 'IDE otomatik kayıt' }),
    });
    const res = await safeFetchJson(`/api/studio/workspaces/${wsId}/git`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'status' }),
    });
    termOut.textContent = res.ok && res.data ? (res.data.output || 'Git hazır.') : `Git hatası: ${res.error || res.status}`;
  });

  searchWsBtn.addEventListener('click', async () => {
    const q = await uiPrompt('Proje dosyalarında ara (Ctrl+Shift+F):', '', 'Proje İçi Arama');
    if (!q || !q.trim()) return;
    termDrawer.hidden = false;
    termToggleBtn.classList.add('primary');
    const res = await safeFetchJson(`/api/studio/workspaces/${wsId}/search?q=${encodeURIComponent(q.trim())}`);
    if (!res.ok) { termOut.textContent = `Arama hatası: ${res.error || res.status}`; return; }
    const list = (res.data && res.data.matches) || [];
    termOut.textContent = list.length
      ? `--- ARAMA SONUÇLARI ("${q}") ---\n` + list.map((m) => `${m.path}:${m.line}  ${m.snippet}`).join('\n')
      : `"${q}" için eşleşme bulunamadı.`;
  });
}

export function createTerminalDrawer(wsId, termToggleBtn, gitWsBtn, searchWsBtn) {
  const termDrawer = document.createElement('div');
  termDrawer.className = 'ide-term-drawer';
  termDrawer.hidden = true;
  const termOut = document.createElement('pre');
  termOut.className = 'ide-term-out';
  termOut.textContent = 'Çalışma alanı terminali hazır. Komut girin (ör. python main.py, pytest, git status):';
  const termRow = document.createElement('div');
  termRow.className = 'ide-term-row';
  const termIn = document.createElement('input');
  termIn.type = 'text';
  termIn.className = 'ide-term-in';
  termIn.setAttribute('aria-label', 'Terminal komutu');
  termIn.placeholder = 'Komut çalıştır (ör. python main.py --help veya pytest)...';
  const termRunBtn = document.createElement('button');
  termRunBtn.type = 'button';
  termRunBtn.className = 'ide-btn primary';
  termRunBtn.textContent = 'Çalıştır';

  async function runTerminalCommand() {
    const cmd = termIn.value.trim();
    if (!cmd) return;
    termRunBtn.disabled = true;
    termOut.textContent += `\n$ ${cmd}\n`;
    const res = await safeFetchJson(`/api/studio/workspaces/${wsId}/exec`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: cmd }),
    });
    if (res.ok && res.data) {
      termOut.textContent += (res.data.stdout || '') + (res.data.stderr ? `\n${res.data.stderr}` : '');
    } else {
      termOut.textContent += `\nHata: ${res.error || `HTTP ${res.status}`}`;
    }
    termOut.scrollTop = termOut.scrollHeight;
    termRunBtn.disabled = false;
    termIn.value = '';
  }
  termRunBtn.addEventListener('click', runTerminalCommand);
  termIn.addEventListener('keydown', (e) => { if (e.key === 'Enter') runTerminalCommand(); });
  termRow.append(termIn, termRunBtn);
  termDrawer.append(termOut, termRow);

  termToggleBtn.addEventListener('click', () => {
    termDrawer.hidden = !termDrawer.hidden;
    termToggleBtn.classList.toggle('primary', !termDrawer.hidden);
    if (!termDrawer.hidden) termIn.focus();
  });
  wireTerminalActions(wsId, termDrawer, termOut, termToggleBtn, gitWsBtn, searchWsBtn);
  return termDrawer;
}

export function createIterationBar(wsId, onStreamEvent) {
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

  iterBtn.addEventListener('click', async () => {
    const instr = iterIn.value.trim();
    if (!instr) return;
    iterBtn.disabled = true;
    iterBtn.textContent = 'Güncelleniyor...';
    try {
      const resp = await safeFetch(`/api/studio/workspaces/${wsId}/iterate`, {
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
          await onStreamEvent(evt);
        }
      }
      iterIn.value = '';
    } finally {
      iterBtn.disabled = false;
      iterBtn.textContent = 'Geliştir';
    }
  });
  iterIn.addEventListener('keydown', (e) => { if (e.key === 'Enter') iterBtn.click(); });
  return iterBar;
}
