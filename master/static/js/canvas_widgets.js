// Cluster A ([M15]-[M17]): 100% Local Interactive SVG Chart, Flowchart/Mermaid/ERD Diagram,
// Collapsible Mindmap, LaTeX Math Typography, and Live Calculator Widget Renderer.
// Zero external CDNs.

function escXml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function renderChartSvg(specJson) {
  let spec;
  try {
    spec = typeof specJson === 'string' ? JSON.parse(specJson) : specJson;
  } catch {
    return '';
  }
  const type = (spec.type || 'bar').toLowerCase();
  const title = escXml(spec.title || 'Veri Grafiği');
  const labels = Array.isArray(spec.labels) ? spec.labels : [];
  const values = Array.isArray(spec.values) ? spec.values.map((v) => Number(v) || 0) : [];
  if (!labels.length && type !== 'gantt') return '';

  const W = 680;
  const H = 330;
  const padL = 58;
  const padR = 28;
  const padT = 46;
  const padB = 52;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;
  const maxVal = Math.max(1, ...values);
  const palette = ['#4f46e5', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#38bdf8'];

  let bodySvg = '';

  if (type === 'pie') {
    const total = Math.max(1e-9, values.reduce((a, b) => a + Math.max(0, b), 0));
    const cx = 230;
    const cy = padT + plotH / 2 + 8;
    const r = Math.min(plotW, plotH) * 0.42;
    let angle = -Math.PI / 2;
    values.forEach((v, i) => {
      const slice = (Math.max(0, v) / total) * Math.PI * 2;
      const x1 = cx + r * Math.cos(angle);
      const y1 = cy + r * Math.sin(angle);
      const x2 = cx + r * Math.cos(angle + slice);
      const y2 = cy + r * Math.sin(angle + slice);
      const large = slice > Math.PI ? 1 : 0;
      const col = palette[i % palette.length];
      const pct = Math.round((Math.max(0, v) / total) * 100);
      bodySvg += `<path d="M ${cx} ${cy} L ${x1.toFixed(1)} ${y1.toFixed(1)} A ${r} ${r} 0 ${large} 1 ${x2.toFixed(1)} ${y2.toFixed(1)} Z" fill="${col}" stroke="#141418" stroke-width="2"><title>${escXml(labels[i])}: ${v} (%${pct})</title></path>`;
      const ly = padT + 22 + i * 24;
      bodySvg += `<rect x="410" y="${ly - 10}" width="12" height="12" rx="3" fill="${col}"/>`;
      bodySvg += `<text x="428" y="${ly}" fill="#e2e8f0" font-size="11.5">${escXml(labels[i]).slice(0, 22)} (${v} · %${pct})</text>`;
      angle += slice;
    });
  } else if (type === 'radar') {
    const cx = W / 2;
    const cy = padT + plotH / 2 + 10;
    const r = Math.min(plotW, plotH) * 0.42;
    const n = Math.max(3, values.length);
    for (let ring = 1; ring <= 4; ring++) {
      const rr = (r * ring) / 4;
      bodySvg += `<circle cx="${cx}" cy="${cy}" r="${rr}" fill="none" stroke="#2d2d35" stroke-width="1"/>`;
    }
    const pts = values.map((v, i) => {
      const ang = -Math.PI / 2 + (i * 2 * Math.PI) / n;
      const dist = (Math.max(0, v) / maxVal) * r;
      const x = cx + dist * Math.cos(ang);
      const y = cy + dist * Math.sin(ang);
      const lx = cx + (r + 24) * Math.cos(ang);
      const ly = cy + (r + 18) * Math.sin(ang);
      bodySvg += `<line x1="${cx}" y1="${cy}" x2="${cx + r * Math.cos(ang)}" y2="${cy + r * Math.sin(ang)}" stroke="#2d2d35"/>`;
      bodySvg += `<text x="${lx}" y="${ly}" text-anchor="middle" fill="#cbd5e1" font-size="10.5">${escXml(labels[i]).slice(0, 14)}</text>`;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    bodySvg += `<polygon points="${pts.join(' ')}" fill="rgba(99,102,241,0.28)" stroke="#6366f1" stroke-width="2.5"/>`;
  } else if (type === 'gantt' && Array.isArray(spec.tasks)) {
    const tasks = spec.tasks;
    const maxEnd = Math.max(1, ...tasks.map((t) => Number(t.end) || 10));
    const rowH = Math.min(32, Math.floor(plotH / Math.max(1, tasks.length)));
    tasks.forEach((t, i) => {
      const start = Number(t.start) || 0;
      const end = Math.max(start + 1, Number(t.end) || start + 5);
      const x = padL + 70 + (start / maxEnd) * (plotW - 70);
      const w = Math.max(6, ((end - start) / maxEnd) * (plotW - 70));
      const y = padT + i * rowH + 6;
      const col = palette[i % palette.length];
      bodySvg += `<text x="${padL + 62}" y="${y + 13}" text-anchor="end" fill="#cbd5e1" font-size="10.5">${escXml(t.label || t.id || `OP${i + 1}`).slice(0, 14)}</text>`;
      bodySvg += `<rect x="${x}" y="${y}" width="${w}" height="${Math.max(12, rowH - 8)}" rx="4" fill="${col}"><title>${escXml(t.label)}: ${start} - ${end} dk</title></rect>`;
    });
  } else {
    for (let i = 0; i <= 4; i++) {
      const y = padT + (plotH * i) / 4;
      const vLabel = Math.round(maxVal * (1 - i / 4));
      bodySvg += `<line x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}" stroke="#2d2d35" stroke-width="1"/>`;
      bodySvg += `<text x="${padL - 8}" y="${y + 4}" text-anchor="end" fill="#9ca3af" font-size="10.5">${vLabel}</text>`;
    }

    if (type === 'line' || type === 'scatter') {
      const pts = values.map((v, i) => {
        const x = padL + (plotW * i) / Math.max(1, values.length - 1);
        const y = padT + plotH - (v / maxVal) * plotH;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      });
      if (type === 'line') {
        bodySvg += `<polyline fill="none" stroke="#6366f1" stroke-width="3" points="${pts.join(' ')}"/>`;
      }
      values.forEach((v, i) => {
        const x = padL + (plotW * i) / Math.max(1, values.length - 1);
        const y = padT + plotH - (v / maxVal) * plotH;
        bodySvg += `<circle cx="${x}" cy="${y}" r="5" fill="#38bdf8"><title>${escXml(labels[i])}: ${v}</title></circle>`;
        bodySvg += `<text x="${x}" y="${H - 18}" text-anchor="middle" fill="#cbd5e1" font-size="11">${escXml(labels[i]).slice(0, 12)}</text>`;
      });
    } else {
      const barGap = 14;
      const barW = Math.max(14, (plotW - barGap * (values.length + 1)) / values.length);
      values.forEach((v, i) => {
        const bh = Math.max(2, (v / maxVal) * plotH);
        const x = padL + barGap + i * (barW + barGap);
        const y = padT + plotH - bh;
        const col = palette[i % palette.length];
        bodySvg += `<rect x="${x}" y="${y}" width="${barW}" height="${bh}" rx="4" fill="${col}"><title>${escXml(labels[i])}: ${v}</title></rect>`;
        bodySvg += `<text x="${x + barW / 2}" y="${y - 6}" text-anchor="middle" fill="#e2e8f0" font-size="10.5" font-weight="600">${v}</text>`;
        bodySvg += `<text x="${x + barW / 2}" y="${H - 18}" text-anchor="middle" fill="#cbd5e1" font-size="11">${escXml(labels[i]).slice(0, 12)}</text>`;
      });
    }
  }

  const csvRows = ['Etiket,Deger', ...labels.map((l, idx) => `"${String(l).replace(/"/g, '""')}",${values[idx] ?? 0}`)].join('\n');
  const csvUri = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csvRows);

  return `<div class="svg-diagram"><svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" style="background:#141418;border-radius:10px;border:1px solid #2b2b33;font-family:Segoe UI,sans-serif;">
    <text x="${padL}" y="26" fill="#f8fafc" font-size="13.5" font-weight="700">${title}</text>
    ${bodySvg}
  </svg><div style="display:flex;gap:10px;margin-top:4px;font-size:11px;"><a href="${csvUri}" download="grafik_veri.csv" class="download-link">CSV İndir</a></div></div>`;
}

export function renderDiagramSvg(code) {
  const lines = String(code || '')
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith('%%'));
  if (!lines.length) return '';

  const nodes = new Map();
  const edges = [];

  function ensureNode(id, label) {
    const cleanId = id.replace(/[^a-zA-Z0-9_-]/g, '') || `N${nodes.size + 1}`;
    const cleanLbl = (label || id).replace(/^["'[(]+|["'\])]+$/g, '');
    if (!nodes.has(cleanId)) {
      nodes.set(cleanId, { id: cleanId, label: cleanLbl });
    } else if (label) {
      nodes.get(cleanId).label = cleanLbl;
    }
    return cleanId;
  }

  for (const ln of lines.slice(1)) {
    // Match A[Label] --> B[Label] or EntityA ||--o{ EntityB : "rel"
    const mFlow = ln.match(/^([A-Za-z0-9_]+)(?:\["?([^"\]]+)"?\])?\s*(?:-->|->|---|==>|\|\|--o\{)\s*(?:\|([^|]+)\|)?\s*([A-Za-z0-9_]+)(?:\["?([^"\]]+)"?\])?(?:\s*:\s*"?([^"]+)"?)?/);
    if (mFlow) {
      const a = ensureNode(mFlow[1], mFlow[2]);
      const b = ensureNode(mFlow[4], mFlow[5]);
      edges.push({ from: a, to: b, label: mFlow[3] || mFlow[6] || '' });
      continue;
    }
    const mSingle = ln.match(/^([A-Za-z0-9_]+)\["?([^"\]]+)"?\]$/);
    if (mSingle) {
      ensureNode(mSingle[1], mSingle[2]);
    }
  }

  if (nodes.size === 0) {
    lines.slice(0, 6).forEach((ln, idx) => ensureNode(`S${idx + 1}`, ln.slice(0, 36)));
  }

  const nodeList = Array.from(nodes.values());
  const cols = Math.min(3, Math.max(1, nodeList.length));
  const rows = Math.ceil(nodeList.length / cols);
  const W = 680;
  const H = Math.max(150, rows * 95 + 40);
  const boxW = 175;
  const boxH = 44;

  nodeList.forEach((n, idx) => {
    const col = idx % cols;
    const row = Math.floor(idx / cols);
    n.x = 34 + col * 215;
    n.y = 26 + row * 86;
  });

  let svgBody = `<defs><marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 10 5 L 0 9 z" fill="#6366f1"/></marker></defs>`;

  for (const e of edges) {
    const src = nodes.get(e.from);
    const dst = nodes.get(e.to);
    if (!src || !dst) continue;
    const x1 = src.x + boxW / 2;
    const y1 = src.y + boxH / 2;
    const x2 = dst.x + boxW / 2;
    const y2 = dst.y + boxH / 2;
    svgBody += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#6366f1" stroke-width="2" marker-end="url(#arr)"/>`;
    if (e.label) {
      svgBody += `<text x="${(x1 + x2) / 2}" y="${(y1 + y2) / 2 - 6}" text-anchor="middle" fill="#94a3b8" font-size="10">${escXml(e.label).slice(0, 18)}</text>`;
    }
  }

  for (const n of nodeList) {
    svgBody += `<rect x="${n.x}" y="${n.y}" width="${boxW}" height="${boxH}" rx="8" fill="#1e2230" stroke="#4f46e5" stroke-width="1.6"/>`;
    svgBody += `<text x="${n.x + boxW / 2}" y="${n.y + 26}" text-anchor="middle" fill="#f1f5f9" font-size="11.5" font-weight="600">${escXml(n.label).slice(0, 22)}</text>`;
  }

  return `<div class="svg-diagram"><svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" style="background:#141418;border-radius:10px;border:1px solid #2b2b33;font-family:Segoe UI,sans-serif;">${svgBody}</svg></div>`;
}

export function renderMindmapHtml(code) {
  const lines = String(code || '').split('\n').filter((l) => l.trim());
  if (!lines.length) return '';
  const items = lines.map((l) => {
    const clean = escXml(l.replace(/^[\s\-*+]+/, ''));
    return `<li style="margin:4px 0;">${clean}</li>`;
  }).join('');
  return `<details open class="card" style="margin:8px 0;padding:10px 14px;"><summary style="cursor:pointer;font-weight:600;">Zihin Haritası / Karar Ağacı</summary><ul style="margin:8px 0 0;padding-left:18px;">${items}</ul></details>`;
}

export function renderLatexMath(htmlText) {
  const formatExpr = (expr) => expr
    .replace(/\\frac\{([^{}]+)\}\{([^{}]+)\}/g, '($1) / ($2)')
    .replace(/\\sqrt\{([^{}]+)\}/g, '√($1)')
    .replace(/\\cdot/g, '·')
    .replace(/\\times/g, '×')
    .replace(/\\pi/g, 'π')
    .replace(/\\delta/g, 'δ')
    .replace(/\\Delta/g, 'Δ')
    .replace(/\\sigma/g, 'σ')
    .replace(/\\alpha/g, 'α')
    .replace(/\\beta/g, 'β')
    .replace(/\\theta/g, 'θ')
    .replace(/\\mu/g, 'μ')
    .replace(/\\eta/g, 'η');

  let out = htmlText.replace(/\$\$([\s\S]+?)\$\$/g, (_, eq) => (
    `<div class="math-block" style="margin:8px 0;padding:8px 12px;border-radius:8px;background:var(--surface-2,#1e2230);font-family:Cambria Math,Georgia,serif;font-size:15px;">${formatExpr(eq.trim())}</div>`
  ));
  out = out.replace(/(?<!\\)\$([^$\n]{2,80})\$/g, (_, eq) => (
    `<span class="math-inline" style="font-family:Cambria Math,Georgia,serif;font-style:italic;padding:0 3px;">${formatExpr(eq.trim())}</span>`
  ));
  return out;
}
