// XSS-01..39: the sanitizer must be DOM/allowlist based. Node has no DOMParser, so here we verify the
// fail-closed path and that no regex blacklist remains; the browser run uses the same xss_payloads.json.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { sanitizeHtmlOrSvg } from '../../master/static/js/sanitizer.js';

const { bad, good } = JSON.parse(readFileSync(new URL('./xss_payloads.json', import.meta.url), 'utf8'));
const source = readFileSync(new URL('../../master/static/js/sanitizer.js', import.meta.url), 'utf8');

test('payload corpus is non-trivial', () => {
  assert.ok(bad.length >= 25);
  assert.ok(good.length >= 4);
});

test('no regex blacklist of tags or event attributes remains', () => {
  assert.doesNotMatch(source, /FORBIDDEN_TAGS_RE|EVENT_ATTR_RE|JS_URI_RE/);
  assert.match(source, /DOMParser/);
});

test('without a DOM the sanitizer fails closed (no raw markup survives)', { skip: typeof DOMParser !== 'undefined' }, () => {
  for (const payload of [...bad, ...good]) {
    assert.doesNotMatch(sanitizeHtmlOrSvg(payload), /[<>]/);
  }
});
