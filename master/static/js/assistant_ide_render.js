// UX-02 Modular Split: IDE Workbench icons, syntax highlighting, terminal/git/search drawer, and iteration bar.

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

export function createTerminalDrawer(wsId, termToggleBtn, gitWsBtn, searchWsBtn) {
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
