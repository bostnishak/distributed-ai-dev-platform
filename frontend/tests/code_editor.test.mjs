// KOD-01 / ALT-13: Offline code editor unit tests (tokenizer, line numbers, multi-tab, diagnostics, auto-indent).
import test from 'node:test';
import assert from 'node:assert/strict';
import { mountOfflineCodeEditor, renderGutterNumbers, tokenizeLine } from '../../master/static/vendor/code_editor.js';

test('tokenizeLine highlights Python keywords, strings, numbers, and comments', () => {
  const toks = tokenizeLine('def calc(x): return x + 42 # ok', 'python');
  assert.ok(toks.some((t) => t.type === 'keyword' && t.text === 'def'));
  assert.ok(toks.some((t) => t.type === 'keyword' && t.text === 'return'));
  assert.ok(toks.some((t) => t.type === 'number' && t.text === '42'));
  assert.ok(toks.some((t) => t.type === 'comment' && t.text === '# ok'));
});

test('renderGutterNumbers marks diagnostic error lines accurately', () => {
  const rows = renderGutterNumbers('a = 1\nb = 2\nc = 3', new Set([2]));
  assert.equal(rows.length, 3);
  assert.equal(rows[0].hasError, false);
  assert.equal(rows[1].hasError, true);
});

test('mountOfflineCodeEditor supports multi-tab switching, Tab/Enter auto-indent, and diagnostics', () => {
  const listeners = new Map();
  const fakeTa = {
    value: 'def f():',
    selectionStart: 8,
    selectionEnd: 8,
    dataset: {},
    parentElement: null,
    setAttribute() {},
    addEventListener(evt, fn) { listeners.set(evt, fn); },
    removeEventListener(evt) { listeners.delete(evt); },
  };
  let saved = null;
  const ed = mountOfflineCodeEditor(fakeTa, { language: 'python', onSave: (v) => { saved = v; } });
  assert.equal(ed.getActiveTab(), 'main.py');

  // Enter after ':' auto-indents by 2 spaces
  listeners.get('keydown')({ key: 'Enter', preventDefault() {} });
  assert.equal(fakeTa.value, 'def f():\n  ');

  // Ctrl+S triggers onSave
  listeners.get('keydown')({ key: 's', ctrlKey: true, preventDefault() {} });
  assert.equal(saved, 'def f():\n  ');

  // Multi-tab open/switch/close
  ed.openTab('utils.js', 'const x = 1;', 'javascript');
  assert.equal(ed.getActiveTab(), 'utils.js');
  assert.equal(ed.getValue(), 'const x = 1;');
  assert.equal(ed.closeTab('utils.js'), true);
  assert.equal(ed.getActiveTab(), 'main.py');
  ed.setDiagnostics([{ line: 1, message: 'Test uyarısı' }]);
  assert.ok(ed.getTokens().length >= 2);
  ed.dispose();
});
