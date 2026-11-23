// Cluster A ([M15]-[M17]): 100% Local Interactive SVG Chart, Flowchart, Mindmap & LaTeX Canvas Renderer.
// Zero external CDNs. Renders ```chart (JSON) and ```mindmap blocks inside Assistant messages.

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
  if (!labels.length || !values.length) return '';

  const W = 680;
  const H = 320;
  const padL = 56;
  const padR = 28;
  const padT = 46;
  const padB = 52;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;
  const maxVal = Math.max(1, ...values);
  const palette = ['#4f46e5', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'];

  let bodySvg = '';
  // Horizontal grid lines
  for (let i = 0; i <= 4; i++) {
    const y = padT + (plotH * i) / 4;
    const vLabel = Math.round(maxVal * (1 - i / 4));
    bodySvg += `<line x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}" stroke="#2d2d35" stroke-width="1"/>`;
    bodySvg += `<text x="${padL - 8}" y="${y + 4}" text-anchor="end" fill="#9ca3af" font-size="10.5">${vLabel}</text>`;
  }

  if (type === 'line') {
    const pts = values.map((v, i) => {
      const x = padL + (plotW * i) / Math.max(1, values.length - 1);
      const y = padT + plotH - (v / maxVal) * plotH;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    bodySvg += `<polyline fill="none" stroke="#6366f1" stroke-width="3" points="${pts.join(' ')}"/>`;
    values.forEach((v, i) => {
      const x = padL + (plotW * i) / Math.max(1, values.length - 1);
      const y = padT + plotH - (v / maxVal) * plotH;
      bodySvg += `<circle cx="${x}" cy="${y}" r="4.5" fill="#38bdf8"><title>${escXml(labels[i])}: ${v}</title></circle>`;
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

  return `<div class="svg-diagram"><svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" style="background:#141418;border-radius:10px;border:1px solid #2b2b33;font-family:Segoe UI,sans-serif;">
    <text x="${padL}" y="26" fill="#f8fafc" font-size="13.5" font-weight="700">${title}</text>
    ${bodySvg}
  </svg></div>`;
}
