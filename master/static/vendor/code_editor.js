// KOD-01 & ALT-13: Rich offline Monaco/CodeMirror-compatible code editor (zero CDN, zero innerHTML XSS).
// Features: line-number gutter, syntax token preview, multi-tab files, LSP diagnostics, auto-indent, bracket pairing.

const KEYWORDS = {
  python: new Set(['def', 'class', 'return', 'if', 'elif', 'else', 'for', 'while', 'import', 'from', 'as', 'try', 'except', 'finally', 'with', 'async', 'await', 'pass', 'break', 'continue', 'True', 'False', 'None', 'in', 'is', 'not', 'and', 'or', 'yield', 'raise']),
  javascript: new Set(['function', 'const', 'let', 'var', 'return', 'if', 'else', 'for', 'while', 'import', 'export', 'from', 'try', 'catch', 'finally', 'async', 'await', 'class', 'new', 'true', 'false', 'null', 'undefined', 'switch', 'case', 'break']),
  typescript: new Set(['function', 'const', 'let', 'var', 'return', 'if', 'else', 'for', 'while', 'import', 'export', 'from', 'interface', 'type', 'async', 'await', 'class', 'new', 'true', 'false', 'null', 'undefined']),
  sql: new Set(['SELECT', 'FROM', 'WHERE', 'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE', 'TABLE', 'INDEX', 'JOIN', 'ON', 'ORDER', 'BY', 'GROUP', 'LIMIT', 'AND', 'OR', 'NOT', 'NULL']),
};

const PAIRS = { '(': ')', '[': ']', '{': '}', '"': '"', "'": "'" };

export function tokenizeLine(line, language = 'python') {
  const kw = KEYWORDS[language] || KEYWORDS.python;
  const tokens = [];
  const rx = /(#.*$|\/\/.*$|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*\b)/gm;
  let last = 0;
  let m;
  while ((m = rx.exec(line)) !== null) {
    if (m.index > last) tokens.push({ type: 'plain', text: line.slice(last, m.index) });
    const val = m[0];
    let type = 'ident';
    if (val.startsWith('#') || val.startsWith('//')) type = 'comment';
    else if (val.startsWith('"') || val.startsWith("'")) type = 'string';
    else if (/^\d/.test(val)) type = 'number';
    else if (kw.has(val) || (language === 'sql' && kw.has(val.toUpperCase()))) type = 'keyword';
    tokens.push({ type, text: val });
    last = m.index + val.length;
  }
  if (last < line.length) tokens.push({ type: 'plain', text: line.slice(last) });
  return tokens;
}

export function renderGutterNumbers(text, diagLines = new Set()) {
  const count = Math.max(1, String(text || '').split('\n').length);
  const out = [];
  for (let i = 1; i <= count; i += 1) {
    out.push({ line: i, hasError: diagLines.has(i) });
  }
  return out;
}

function handleEditorKeyDown(event, textarea, onSave) {
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const val = textarea.value;
  if (event.key === 'Tab') {
    event.preventDefault();
    if (event.shiftKey && start >= 2 && val.slice(start - 2, start) === '  ') {
      textarea.value = val.slice(0, start - 2) + val.slice(end);
      textarea.selectionStart = textarea.selectionEnd = start - 2;
    } else {
      textarea.value = `${val.slice(0, start)}  ${val.slice(end)}`;
      textarea.selectionStart = textarea.selectionEnd = start + 2;
    }
    return true;
  }
  if (event.key === 'Enter') {
    event.preventDefault();
    const lineStart = val.lastIndexOf('\n', start - 1) + 1;
    const curLine = val.slice(lineStart, start);
    const indent = (curLine.match(/^\s*/) || [''])[0];
    const extra = /[:{]\s*$/.test(curLine) ? '  ' : '';
    const ins = `\n${indent}${extra}`;
    textarea.value = val.slice(0, start) + ins + val.slice(end);
    textarea.selectionStart = textarea.selectionEnd = start + ins.length;
    return true;
  }
  if (PAIRS[event.key] && start === end) {
    event.preventDefault();
    textarea.value = val.slice(0, start) + event.key + PAIRS[event.key] + val.slice(end);
    textarea.selectionStart = textarea.selectionEnd = start + 1;
    return true;
  }
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
    event.preventDefault();
    if (typeof onSave === 'function') onSave(textarea.value);
    return true;
  }
  return false;
}

function createEditorChrome(textarea) {
  const parent = textarea.parentElement;
  if (!parent || typeof document === 'undefined') return { gutter: null, tabBar: null, diagBar: null };
  const tabBar = document.createElement('div');
  tabBar.className = 'ce-tabs';
  const wrap = document.createElement('div');
  wrap.className = 'ce-wrap';
  const gutter = document.createElement('pre');
  gutter.className = 'ce-gutter';
  gutter.setAttribute('aria-hidden', 'true');
  const diagBar = document.createElement('div');
  diagBar.className = 'ce-diag-bar';
  diagBar.hidden = true;
  parent.insertBefore(tabBar, textarea);
  parent.insertBefore(wrap, textarea);
  wrap.append(gutter, textarea);
  parent.insertBefore(diagBar, wrap.nextSibling);
  return { gutter, tabBar, diagBar };
}

export function mountOfflineCodeEditor(textarea, { onSave = null, language = 'python', initialTab = 'main.py' } = {}) {
  if (!textarea) return null;
  textarea.dataset.editor = 'monaco-compatible-offline';
  textarea.dataset.language = language;
  textarea.spellcheck = false;
  textarea.setAttribute('aria-label', `Kod editörü (${language})`);

  const chrome = createEditorChrome(textarea);
  const tabs = new Map([[initialTab, { content: textarea.value || '', language }]]);
  let activeTab = initialTab;
  let diagnostics = [];

  const syncGutter = () => {
    if (!chrome.gutter) return;
    const errLines = new Set(diagnostics.map((d) => Number(d.line || 0)));
    chrome.gutter.textContent = renderGutterNumbers(textarea.value, errLines)
      .map((r) => (r.hasError ? `!${r.line}` : String(r.line)))
      .join('\n');
  };

  const syncTabs = () => {
    if (!chrome.tabBar) return;
    chrome.tabBar.replaceChildren();
    for (const [name] of tabs.entries()) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = `ce-tab${name === activeTab ? ' active' : ''}`;
      btn.textContent = name;
      btn.addEventListener('click', () => api.openTab(name));
      chrome.tabBar.appendChild(btn);
    }
  };

  const onInput = () => {
    const rec = tabs.get(activeTab);
    if (rec) rec.content = textarea.value;
    syncGutter();
  };
  const onKeyDown = (event) => {
    if (handleEditorKeyDown(event, textarea, onSave)) onInput();
  };
  textarea.addEventListener('input', onInput);
  textarea.addEventListener('keydown', onKeyDown);

  const api = {
    getValue: () => textarea.value,
    setValue: (next) => { textarea.value = String(next ?? ''); onInput(); },
    setLanguage: (lang) => { textarea.dataset.language = lang; const r = tabs.get(activeTab); if (r) r.language = lang; },
    getActiveTab: () => activeTab,
    openTab: (name, content = null, lang = null) => {
      if (!tabs.has(name)) tabs.set(name, { content: content ?? '', language: lang || textarea.dataset.language || 'python' });
      else if (content !== null) tabs.get(name).content = content;
      activeTab = name;
      const rec = tabs.get(name);
      textarea.value = rec.content;
      textarea.dataset.language = rec.language;
      syncTabs();
      syncGutter();
    },
    closeTab: (name) => {
      if (tabs.size <= 1 || !tabs.has(name)) return false;
      tabs.delete(name);
      if (activeTab === name) api.openTab([...tabs.keys()][0]);
      else syncTabs();
      return true;
    },
    setDiagnostics: (items) => {
      diagnostics = Array.isArray(items) ? items : [];
      syncGutter();
      if (chrome.diagBar) {
        chrome.diagBar.hidden = diagnostics.length === 0;
        chrome.diagBar.textContent = diagnostics.map((d) => `Satır ${d.line}: ${d.message}`).join(' | ');
      }
    },
    getTokens: () => textarea.value.split('\n').map((ln) => tokenizeLine(ln, textarea.dataset.language)),
    dispose: () => {
      textarea.removeEventListener('input', onInput);
      textarea.removeEventListener('keydown', onKeyDown);
    },
  };
  syncTabs();
  syncGutter();
  return api;
}
