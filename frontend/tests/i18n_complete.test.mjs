import test from 'node:test';
import assert from 'node:assert/strict';
import { MESSAGES, SUPPORTED_LANGS, getTextDirection, translate } from '../../master/static/js/i18n.js';

test('EPK-27: all 5 languages (tr, en, de, fr, ar) have zero missing keys and RTL for Arabic', () => {
  assert.deepEqual(SUPPORTED_LANGS, ['tr', 'en', 'de', 'fr', 'ar']);
  const baseKeys = Object.keys(MESSAGES.tr).sort();
  for (const lang of SUPPORTED_LANGS) {
    assert.deepEqual(Object.keys(MESSAGES[lang]).sort(), baseKeys, `Missing keys in ${lang}`);
    for (const k of baseKeys) {
      assert.ok(translate(k, lang).length > 0, `Empty translation for ${lang}:${k}`);
    }
  }
  assert.equal(getTextDirection('ar'), 'rtl');
  assert.equal(getTextDirection('tr'), 'ltr');
});
