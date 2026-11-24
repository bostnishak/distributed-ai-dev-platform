import { sanitizeHtmlOrSvg as s, setSanitizedHtml } from '/master/static/js/sanitizer.js';
const { bad, good } = await (await fetch('./xss_payloads.json')).json();
const rows = []; let fails = 0;
const RISK = /\son[a-z]+\s*=|javascript:|<script|srcdoc|<iframe|<object|<style|<form|@import|data:text|<set|<animate|foreignobject/i;
for (const p of bad) { const o = s(p); const host = document.createElement('div'); setSanitizedHtml(host, p);
  const risky = RISK.test(o + host.innerHTML); if (risky) fails++; rows.push((risky ? 'BYPASS ' : 'ok     ') + JSON.stringify(p) + ' -> ' + JSON.stringify(o)); }
for (const p of good) { const o = s(p); const keep = o.length > 10; if (!keep) fails++; rows.push((keep ? 'keep   ' : 'LOST   ') + JSON.stringify(p) + ' -> ' + JSON.stringify(o)); }
document.getElementById('out').textContent = 'FAILS=' + fails + '\n' + rows.join('\n');
