import assert from 'node:assert/strict';
import test from 'node:test';

import { sanitizeHtmlOrSvg } from '../../master/static/js/sanitizer.js';
import { translate } from '../../master/static/js/i18n.js';
import { createReactiveStore, migrateState } from '../../master/static/js/store.js';
import { parseSlashAndMentions, renderConfidenceBadgeHtml } from '../../master/static/js/ux_shell.js';

test('sanitizer strips script tags, event handlers, and javascript URIs', () => {
  const dirty = '<svg onload="alert(1)"><script>evil()</script><a href="javascript:alert(2)">ok</a><circle r="5"/></svg>';
  const clean = sanitizeHtmlOrSvg(dirty);
  assert.ok(!clean.includes('<script'));
  assert.ok(!clean.includes('onload='));
  assert.ok(!clean.includes('javascript:'));
  assert.ok(clean.includes('<circle r="5"/>'));
});

test('i18n translates Turkish and English status keys cleanly', () => {
  assert.ok(translate('status.unverified', 'tr').length > 0);
  assert.ok(translate('status.unverified', 'en').length > 0);
});

test('store migrates legacy schema and notifies subscribers on settings updates', () => {
  const migrated = migrateState({ schemaVersion: 1, theme: 'light' });
  assert.equal(migrated.schemaVersion, 2);
  assert.equal(migrated.settings.showConfidenceBadges, true);

  const store = createReactiveStore();
  const seen = [];
  const unsub = store.subscribe((s) => seen.push(s.settings.language));
  store.updateSettings({ language: 'en' });
  store.updateSettings({ language: 'tr' });
  unsub();
  store.updateSettings({ language: 'en' });
  assert.deepEqual(seen, ['en', 'tr']);
  assert.equal(store.getState().settings.language, 'en');
});

test('ux_shell parses slash commands, @mentions, and renders sanitized confidence badge', () => {
  const parsed = parseSlashAndMentions('/araştır @web @dosya kuantum hesaplama');
  assert.equal(parsed.slash.command, '/araştır');
  assert.equal(parsed.slash.mode, 'research');
  assert.deepEqual(parsed.mentions, ['web', 'dosya']);
  assert.equal(parsed.cleanPrompt, '@web @dosya kuantum hesaplama');

  const badge = renderConfidenceBadgeHtml('yüksek', 0.92, 'tr');
  assert.ok(badge.includes('role="status"'));
  assert.ok(badge.includes('%92'));
});
