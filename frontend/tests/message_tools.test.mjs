import assert from 'node:assert/strict';
import test from 'node:test';

globalThis.document = { cookie: '', createElement: () => ({ setAttribute() {}, append() {}, addEventListener() {} }), addEventListener() {}, documentElement: { dataset: {} }, getElementById: () => null, hidden: true, title: 'x' };
globalThis.localStorage = { getItem: () => null, setItem() {} };
globalThis.window = { matchMedia: () => ({ matches: false, addEventListener() {} }), addEventListener() {} };

const { chatToMarkdown, notifyAnswerReady } = await import('../../master/static/js/message_tools.js');

test('UX-08: exported chat keeps roles, text and model badge', () => {
  const md = chatToMarkdown([{ role: 'user', text: 'Merhaba' }, { role: 'assistant', text: 'Selam [S1]', modelBadge: 'qwen' }], 'T');
  assert.match(md, /^# T/);
  assert.match(md, /## Kullanıcı\n\nMerhaba/);
  assert.match(md, /## Asistan \(qwen\)\n\nSelam \[S1\]/);
});

test('UX-25: without notification permission the tab title is the fallback indicator', () => {
  globalThis.Notification = { permission: 'denied' };
  globalThis.window.Notification = globalThis.Notification;
  notifyAnswerReady('uzun iş bitti');
  assert.equal(globalThis.document.title, '(1) Yanıt hazır');
});
