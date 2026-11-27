// A small, self-contained Markdown -> HTML renderer for assistant answers (no CDN library,
// so the system stays fully local). Supports headings, bold/italic, lists, inline code,
// code blocks, GFM tables, ```svg blocks, ```chart blocks, ```mermaid/diagram blocks,
// ```mindmap blocks, LaTeX math ($...$ / $$...$$), and a "Run" button under Python code blocks.

import { renderChartSvg, renderDiagramSvg, renderLatexMath, renderMindmapHtml } from './canvas_widgets.js';
import { sanitizeHtmlOrSvg } from './sanitizer.js';

function looksLikePython(lang, code) {
  if (lang === 'python' || lang === 'py') return true;
  if (lang) return false;
  return /^\s*(def |import |from |print\(|class |if __name__)/m.test(code);
}

export function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function ensureSvgViewBox(svgText) {
  return svgText.replace(/<svg\b[^>]*>/i, (tag) => {
    if (/\bviewBox\s*=/i.test(tag)) return tag;
    const w = tag.match(/\bwidth\s*=\s*["']?(\d+(?:\.\d+)?)(?:px)?["']?/i);
    const h = tag.match(/\bheight\s*=\s*["']?(\d+(?:\.\d+)?)(?:px)?["']?/i);
    if (!w || !h) return tag;
    return tag.replace(/<svg\b/i, `<svg viewBox="0 0 ${w[1]} ${h[1]}"`);
  });
}

export function sanitizeSvg(svgText) {
  return ensureSvgViewBox(sanitizeHtmlOrSvg(svgText));
}

function renderCodeBlockHtml(block) {
  if ((block.lang === 'svg' || block.lang === 'xml' || block.lang === 'html' || !block.lang) && /^\s*(?:<\?xml[^>]*>\s*)?<svg[\s>]/i.test(block.code)) {
    return `<div class="svg-diagram">${sanitizeSvg(block.code.replace(/^\s*<\?xml[^>]*>\s*/i, ''))}</div>`;
  }
  if (block.lang === 'chart') { const ch = renderChartSvg(block.code); if (ch) return ch; }
  if (block.lang === 'mermaid' || block.lang === 'diagram') { const dg = renderDiagramSvg(block.code); if (dg) return dg; }
  if (block.lang === 'mindmap') { const mm = renderMindmapHtml(block.code); if (mm) return mm; }
  const escaped = escapeHtml(block.code);
  const langLabel = escapeHtml(block.lang || 'kod');
  const header = `<div class="sp-code-head"><span class="sp-code-lang">${langLabel}</span><button class="sp-code-copy" type="button" title="Bu kod bloğunu kopyala">Kopyala</button></div>`;
  if (!looksLikePython(block.lang, block.code)) {
    return `<div class="code-block sp-code-wrap">${header}<pre><code>${escaped}</code></pre></div>`;
  }
  return `<div class="code-block sp-code-wrap">${header}<pre><code>${escaped}</code></pre><button class="run-code-btn" type="button">▶ Çalıştır</button><div class="run-output" hidden></div></div>`;
}

export function renderMarkdown(raw) {
  const codeBlocks = [];
  let text = raw.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    codeBlocks.push({ lang: lang.trim().toLowerCase(), code });
    return `\u0000CODEBLOCK${codeBlocks.length - 1}\u0000`;
  });
  text = renderLatexMath(escapeHtml(text))
    .replace(/^#### (.*)$/gm, '<h4>$1</h4>')
    .replace(/^### (.*)$/gm, '<h3>$1</h3>')
    .replace(/^## (.*)$/gm, '<h2>$1</h2>')
    .replace(/^# (.*)$/gm, '<h1>$1</h1>')
    .replace(/!\[([^\]]*)\]\((\/api\/[a-zA-Z0-9_./?=&%-]+)\)/g, '<img src="$2" alt="$1" style="max-width:100%;border-radius:8px;border:1px solid #e2e8f0;margin:8px 0;">')
    .replace(/\[([^\]]+)\]\((\/api\/assistant\/media\/[a-zA-Z0-9_.-]+\.wav)\)/g, '<div>$1</div><audio controls preload="metadata" src="$2" style="width:100%;max-width:420px;"></audio>')
    .replace(/\[([^\]]+)\]\(((?:\/api\/|#\/)[a-zA-Z0-9_./?=&%-]+)\)/g, '<a href="$2" style="font-weight:600;">$1</a>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, '<em>$1</em>')
    .replace(/`([^`\n]+)`/g, '<code>$1</code>')
    .replace(/(^|\n)(\|.+\|)\n(\|[ \t:|-]+\|)\n((?:\|.*\|\n?)*)/g, (_m, pre, hdr, _sep, bdy) => {
      const row = (l) => l.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
      const ths = row(hdr).map((c) => `<th>${c}</th>`).join('');
      const trs = bdy.split('\n').filter((l) => l.trim()).map((l) => `<tr>${row(l).map((c) => `<td>${c}</td>`).join('')}</tr>`).join('');
      return `${pre}<table><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table>`;
    })
    .replace(/(^|\n)((?:[-*] .*(?:\n|$))+)/g, (_m, pre, blk) => `${pre}<ul>${blk.trim().split('\n').map((l) => `<li>${l.replace(/^[-*]\s+/, '')}</li>`).join('')}</ul>`)
    .replace(/(^|\n)((?:\d+\. .*(?:\n|$))+)/g, (_m, pre, blk) => `${pre}<ol>${blk.trim().split('\n').map((l) => `<li>${l.replace(/^\d+\.\s+/, '')}</li>`).join('')}</ol>`);
  text = text.split(/\n{2,}/).map((p) => (/^<(h1|h2|h3|ul|ol|table|div|details)/.test(p.trim()) ? p : `<p>${p.replace(/\n/g, '<br>')}</p>`)).join('');
  return text.replace(/\u0000CODEBLOCK(\d+)\u0000/g, (_, i) => renderCodeBlockHtml(codeBlocks[i]));
}
