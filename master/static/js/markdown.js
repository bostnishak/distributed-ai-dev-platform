// A small, self-contained Markdown -> HTML renderer for assistant answers (no CDN library,
// so the system stays fully local). Supports headings, bold/italic, lists, inline code,
// code blocks, GFM tables, ```svg blocks rendered as sanitized inline diagrams, and a "Run"
// button under Python code blocks (see assistant.js for the click handler).

// A block gets the Run button when its fence is explicitly tagged python/py, when another
// language is explicitly tagged we never run it as Python, and with no tag we fall back to a
// content heuristic.
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

// Models often emit <svg width=".." height=".."> without a viewBox. Such an SVG is clipped
// instead of scaled when CSS shrinks it to fit the bubble, so derive the viewBox from its size.
function ensureSvgViewBox(svgText) {
  return svgText.replace(/<svg\b[^>]*>/i, (tag) => {
    if (/\bviewBox\s*=/i.test(tag)) return tag;
    const w = tag.match(/\bwidth\s*=\s*["']?(\d+(?:\.\d+)?)(?:px)?["']?/i);
    const h = tag.match(/\bheight\s*=\s*["']?(\d+(?:\.\d+)?)(?:px)?["']?/i);
    if (!w || !h) return tag;
    return tag.replace(/<svg\b/i, `<svg viewBox="0 0 ${w[1]} ${h[1]}"`);
  });
}

// Strips scripts, inline event handlers and javascript: links before the SVG is inserted.
export function sanitizeSvg(svgText) {
  return ensureSvgViewBox(svgText
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/\son\w+\s*=\s*"[^"]*"/gi, '')
    .replace(/\son\w+\s*=\s*'[^']*'/gi, '')
    .replace(/(xlink:href|href)\s*=\s*"javascript:[^"]*"/gi, '')
    .replace(/(xlink:href|href)\s*=\s*'javascript:[^']*'/gi, ''));
}

export function renderMarkdown(raw) {
  const codeBlocks = [];
  let text = raw.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    codeBlocks.push({ lang: lang.trim().toLowerCase(), code });
    return `\u0000CODEBLOCK${codeBlocks.length - 1}\u0000`;
  });

  text = escapeHtml(text);

  text = text.replace(/^### (.*)$/gm, '<h3>$1</h3>');
  text = text.replace(/^## (.*)$/gm, '<h2>$1</h2>');
  text = text.replace(/^# (.*)$/gm, '<h1>$1</h1>');
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  text = text.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, '<em>$1</em>');
  text = text.replace(/`([^`\n]+)`/g, '<code>$1</code>');

  // GFM tables: | head | head |\n|---|---|\n| cell | cell |
  text = text.replace(
    /(^|\n)(\|.+\|)\n(\|[ \t:|-]+\|)\n((?:\|.*\|\n?)*)/g,
    (_match, pre, headerLine, _sepLine, bodyLines) => {
      const parseRow = (line) => line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
      const headers = parseRow(headerLine);
      const rows = bodyLines.split('\n').filter((l) => l.trim()).map(parseRow);
      let html = '<table><thead><tr>' + headers.map((h) => `<th>${h}</th>`).join('') + '</tr></thead><tbody>';
      for (const row of rows) {
        html += '<tr>' + row.map((c) => `<td>${c}</td>`).join('') + '</tr>';
      }
      html += '</tbody></table>';
      return pre + html;
    }
  );

  // Consecutive "- "/"* " lines become <ul>, "1. " lines become <ol>.
  text = text.replace(/(^|\n)((?:[-*] .*(?:\n|$))+)/g, (m, pre, block) => {
    const items = block.trim().split('\n').map((l) => `<li>${l.replace(/^[-*]\s+/, '')}</li>`).join('');
    return `${pre}<ul>${items}</ul>`;
  });
  text = text.replace(/(^|\n)((?:\d+\. .*(?:\n|$))+)/g, (m, pre, block) => {
    const items = block.trim().split('\n').map((l) => `<li>${l.replace(/^\d+\.\s+/, '')}</li>`).join('');
    return `${pre}<ol>${items}</ol>`;
  });

  text = text.split(/\n{2,}/).map((p) => {
    if (/^<(h1|h2|h3|ul|ol|table)/.test(p.trim())) return p;
    return `<p>${p.replace(/\n/g, '<br>')}</p>`;
  }).join('');

  text = text.replace(/\u0000CODEBLOCK(\d+)\u0000/g, (_, i) => {
    const block = codeBlocks[i];
    if (block.lang === 'svg' && /^\s*<svg[\s>]/i.test(block.code)) {
      return `<div class="svg-diagram">${sanitizeSvg(block.code)}</div>`;
    }
    const escaped = escapeHtml(block.code);
    if (!looksLikePython(block.lang, block.code)) {
      return `<pre><code>${escaped}</code></pre>`;
    }
    return (
      `<div class="code-block"><pre><code>${escaped}</code></pre>` +
      `<button class="run-code-btn" type="button">▶ Çalıştır</button>` +
      `<div class="run-output" hidden></div></div>`
    );
  });
  return text;
}
