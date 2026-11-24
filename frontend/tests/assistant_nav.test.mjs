import assert from 'node:assert/strict';
import { test } from 'node:test';
import { matchPageRequest, pageLinkMessage } from '../../master/static/js/assistant_nav.js';

test('hidden pages open from the assistant on request', () => {
  assert.equal(matchPageRequest('CNC balonlamayı aç').hash, '#/cnc');
  assert.equal(matchPageRequest('Kod stüdyosuna git').hash, '#/studio');
  assert.equal(matchPageRequest('dosyalar sayfasını göster').hash, '#/files');
  assert.equal(matchPageRequest('artefaktları aç').hash, '#/artifacts');
  assert.match(pageLinkMessage(matchPageRequest('stüdyoları aç')), /\(#\/studios\)/);
});

test('ordinary questions are not hijacked', () => {
  assert.equal(matchPageRequest('CNC tornada tolerans nasıl verilir ve bunu detaylı anlat lütfen'), null);
  assert.equal(matchPageRequest('Kısa bir şiir yaz'), null);
  assert.equal(matchPageRequest('dosya nedir'), null);
});
