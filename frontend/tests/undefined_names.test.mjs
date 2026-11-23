// Guards against the bug where a module calls a helper it never imported (e.g. svg() in personal.js),
// which silently killed the sidebar user card and theme toggle at runtime.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const dir = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..', 'master', 'static', 'js');
const HELPERS = ['svg', 'h', 'api', 'formatDateTime', 'formatNumber', 'formatSeconds', 'loading', 'csrfHeaders', 'getCsrfToken'];

function strip(code) {
  return code.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:'"`\\])\/\/.*$/gm, '$1');
}

test('every helper a module calls is imported or defined there', () => {
  const problems = [];
  for (const file of fs.readdirSync(dir).filter((f) => f.endsWith('.js'))) {
    const code = strip(fs.readFileSync(path.join(dir, file), 'utf8'));
    for (const name of HELPERS) {
      const called = new RegExp(`(^|[^\\w.$])${name}\\(`).test(code);
      if (!called) continue;
      const defined = new RegExp(`(function\\s+${name}\\b|(const|let|var)\\s+${name}\\b|import\\s*\\{[^}]*\\b${name}\\b[^}]*\\}|\\b${name}\\s*[,)]\\s*=>|\\(\\s*${name}\\b[^)]*\\)\\s*=>)`).test(code);
      if (!defined) problems.push(`${file}: ${name}`);
    }
  }
  assert.deepEqual(problems, []);
});
