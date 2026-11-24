// CNC Workspace cards: drawing viewer, AS9102/FAI balloon table, and DFM process plan.
import { uiPrompt, uiToast } from './ui_dialog.js';
import { api, formatDateTime, h } from './util.js';

function badgeClass(crit) {
  if (crit === 'Kritik') return 'cnc-badge cnc-crit';
  if (crit === 'Majör') return 'cnc-badge cnc-major';
  return 'cnc-badge cnc-minor';
}

function buildExportBar(job, balloons, setStatus) {
  const evalBtn = h('button', {
    type: 'button', class: 'btn',
    onClick: async () => {
      const sample = balloons.slice(0, 10).map((b, i) => ({ balloon: i + 1, measured: b.nominal ?? 0 }));
      try {
        const res = await api(`/api/cnc/jobs/${encodeURIComponent(job.id)}/evaluate-measurements`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ measurements: sample }),
        });
        setStatus(`Ölçüm değerlendirmesi tamamlandı (${res.evaluated ?? sample.length} karakteristik).`);
        uiToast('CNC ölçüm değerlendirmesi tamamlandı', 'ok');
      } catch (err) {
        setStatus(`Ölçüm değerlendirme hatası: ${err.message}`, true);
      }
    },
  }, 'Ölçümleri Değerlendir');

  return h('div', { class: 'cnc-export-bar' },
    evalBtn,
    h('a', { class: 'btn btn-primary', href: `/api/cnc/jobs/${job.id}/file/report.xlsx`, download: '' }, 'Excel Raporu (.xlsx)'),
    h('a', { class: 'btn btn-primary', href: `/api/cnc/jobs/${job.id}/file/report.docx`, download: '' }, 'Word Raporu (.docx)'),
    h('a', { class: 'btn', href: `/api/cnc/jobs/${job.id}/file/ballooned.pdf`, download: '' }, 'Balonlu PDF'),
    h('a', { class: 'btn', href: `/api/cnc/jobs/${job.id}/file/ballooned.png`, download: `${job.id}-ballooned.png` }, 'Balonlu PNG'),
  );
}

function buildViewerCard(job, balloons, state, hooks) {
  const imgKind = state.showOriginal ? 'original' : 'ballooned.png';
  const imgUrl = `/api/cnc/jobs/${job.id}/file/${imgKind}?t=${Date.now()}`;

  const toggleBtn = h('button', {
    type: 'button', class: 'btn',
    onClick: () => { state.showOriginal = !state.showOriginal; hooks.rerender(); },
  }, state.showOriginal ? '◎ Balonlu Görünümü Göster' : 'Orijinal Çizimi Göster');

  const zoomLabel = h('span', { class: 'small muted' }, `${Math.round(state.zoomLevel * 100)}%`);
  const imgEl = h('img', {
    src: imgUrl,
    alt: job.filename,
    class: 'cnc-drawing-img',
    style: { width: `${state.zoomLevel * 100}%`, cursor: 'crosshair' },
    title: 'Yeni balon eklemek için çizim üzerinde istediğiniz ölçüye tıklayın',
  });
  const updateZoom = () => {
    imgEl.style.width = `${state.zoomLevel * 100}%`;
    zoomLabel.textContent = `${Math.round(state.zoomLevel * 100)}%`;
  };
  const zoomOut = h('button', {
    type: 'button', class: 'btn',
    onClick: () => { state.zoomLevel = Math.max(0.5, +(state.zoomLevel - 0.2).toFixed(1)); updateZoom(); },
  }, '−');
  const zoomIn = h('button', {
    type: 'button', class: 'btn',
    onClick: () => { state.zoomLevel = Math.min(2.4, +(state.zoomLevel + 0.2).toFixed(1)); updateZoom(); },
  }, '+');

  imgEl.addEventListener('click', async (ev) => {
    const rect = imgEl.getBoundingClientRect();
    const xPct = +(((ev.clientX - rect.left) / rect.width) * 100).toFixed(1);
    const yPct = +(((ev.clientY - rect.top) / rect.height) * 100).toFixed(1);
    const raw = await uiPrompt(`(${xPct}%, ${yPct}%) konumuna eklenecek CNC ölçüsü (ör. Ø25 H7, Ra 1.6, M8x1.25):`, '', 'Yeni CNC Balonu');
    if (!raw || !raw.trim()) return;
    balloons.push({
      raw_text: raw.trim(), category: 'Lineer Ölçü', nominal: null, unit: 'mm',
      gage: 'Dijital Kumpas', criticality: 'Majör', operation: 'OP10 · CNC İşleme',
      tooling: 'Karbür Kesici Takım', inspection_freq: 'İlk Parça + 1/10',
      x_pct: xPct, y_pct: yPct, zone: '',
    });
    hooks.onRowsChanged();
    hooks.setStatus(`Yeni balon (${raw.trim()}) eklendi. Çizime işlemek için "Kaydet ve Yeniden Balonla" butonuna basın.`);
  });

  const metaSummary = h('div', { class: 'cnc-meta-summary small' },
    h('span', {}, `Parça: ${job.metadata?.part_name || job.filename}`),
    h('span', {}, `Parça No: ${job.metadata?.part_number || '—'}`),
    h('span', {}, `Malzeme: ${job.metadata?.material || '—'}`),
    h('span', {}, `Standart: ${job.metadata?.standard || 'ISO 2768-mK'}`),
    h('span', {}, `Motor: ${job.engine_used || 'auto'}`),
    h('span', {}, `Tarih: ${formatDateTime(job.created_at)}`),
  );

  return h('div', { class: 'card cnc-viewer-card' },
    h('div', { class: 'cnc-toolbar' },
      h('div', { class: 'cnc-toolbar-left' }, toggleBtn, zoomOut, zoomLabel, zoomIn),
      buildExportBar(job, balloons, hooks.setStatus),
    ),
    metaSummary,
    h('div', { class: 'cnc-canvas-wrap' }, imgEl),
  );
}

function renderBalloonRows(tbody, balloons) {
  tbody.replaceChildren();
  balloons.forEach((b, idx) => {
    const rawIn = h('input', { class: 'cnc-cell-in', value: b.raw_text || '', onInput: (e) => { b.raw_text = e.target.value; } });
    const catIn = h('input', { class: 'cnc-cell-in', value: b.category || '', onInput: (e) => { b.category = e.target.value; } });
    const opIn = h('input', { class: 'cnc-cell-in', value: b.operation || '', onInput: (e) => { b.operation = e.target.value; } });
    const gageIn = h('input', { class: 'cnc-cell-in', value: b.gage || '', onInput: (e) => { b.gage = e.target.value; } });
    const delBtn = h('button', {
      type: 'button', class: 'btn btn-danger cnc-del-btn', title: 'Balonu sil',
      onClick: () => { balloons.splice(idx, 1); renderBalloonRows(tbody, balloons); },
    }, '✕');

    const hasLimits = b.min_limit !== null && b.min_limit !== undefined && b.max_limit !== null && b.max_limit !== undefined;
    const minMax = hasLimits ? `${b.min_limit} / ${b.max_limit}` : '—';
    tbody.appendChild(h('tr', {},
      h('td', { class: 'cnc-num-cell' }, h('span', { class: 'cnc-balloon-dot' }, String(idx + 1))),
      h('td', {}, b.zone || '—'),
      h('td', {}, rawIn),
      h('td', {}, catIn),
      h('td', {}, minMax),
      h('td', {}, opIn),
      h('td', { class: 'small' }, b.tooling || '—'),
      h('td', {}, gageIn),
      h('td', { class: 'small' }, b.inspection_freq || '—'),
      h('td', {}, h('span', { class: badgeClass(b.criticality) }, b.criticality || 'Majör')),
      h('td', {}, delBtn),
    ));
  });
}

function buildBalloonTableCard(job, balloons, hooks) {
  const tbody = h('tbody');
  const redraw = () => renderBalloonRows(tbody, balloons);
  redraw();

  const addBtn = h('button', {
    type: 'button', class: 'btn',
    onClick: () => {
      balloons.push({
        raw_text: 'Ø20 ±0.05', category: 'Çap (Ø)', nominal: 20, unit: 'mm',
        tol_plus: 0.05, tol_minus: -0.05, min_limit: 19.95, max_limit: 20.05,
        gage: 'Dijital Kumpas', criticality: 'Majör', x_pct: 50, y_pct: 50, zone: 'B3',
      });
      redraw();
    },
  }, '＋ Balon Ekle');

  const saveBtn = h('button', {
    type: 'button', class: 'btn btn-primary',
    onClick: async () => {
      saveBtn.disabled = true;
      saveBtn.textContent = 'Yeniden balonlanıyor...';
      try {
        const updated = await api(`/api/cnc/jobs/${job.id}/balloons`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ metadata: job.metadata, balloons }),
        });
        hooks.setStatus('Balonlar güncellendi; PNG, PDF, Excel ve Word raporları yeniden oluşturuldu.');
        hooks.onJobUpdated(updated);
      } catch (err) {
        hooks.setStatus('Güncelleme hatası: ' + err.message, true);
      } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = 'Kaydet ve Yeniden Balonla';
      }
    },
  }, 'Kaydet ve Yeniden Balonla');

  const headers = ['No', 'Bölge', 'Çizim İfadesi', 'Kategori', 'Min / Max', 'Operasyon (OP)', 'Önerilen Kesici Takım', 'Ölçüm Ekipmanı', 'Kontrol Sıklığı', 'Kritiklik', ''];
  const card = h('div', { class: 'card cnc-table-card' },
    h('div', { class: 'cnc-toolbar' },
      h('h2', { style: { margin: 0 } }, `AS9102 / FAI Balonlama Tablosu (${balloons.length} Karakteristik)`),
      h('div', { class: 'card-actions', style: { marginTop: 0 } }, addBtn, saveBtn),
    ),
    h('div', { class: 'cnc-table-scroll' },
      h('table', { class: 'cnc-table' },
        h('thead', {}, h('tr', {}, ...headers.map((t) => h('th', {}, t)))),
        tbody,
      ),
    ),
  );
  return { card, redraw };
}

function buildManufacturingPlanCard(plan) {
  const cp = plan.cutting_parameters || {};
  const opRows = (plan.operations || []).map((op) =>
    h('tr', {},
      h('td', { style: { fontWeight: 700 } }, op.op),
      h('td', {}, op.name),
      h('td', {}, op.machine),
      h('td', {}, op.fixture),
      h('td', {}, (op.balloons || []).map((n) => `#${n}`).join(', ') || 'Genel'),
      h('td', { class: 'small' }, op.notes),
    ));
  const riskList = h('ul', { style: { margin: '8px 0 0 18px', lineHeight: 1.6 } },
    ...(plan.dfm_risks || []).map((r) => h('li', {}, r)));
  const cols = ['OP', 'Operasyon Adı', 'Tezgâh', 'Bağlama / Fikstür', 'Kapsanan Balonlar', 'Setup / Mühendislik Notu'];
  return h('div', { class: 'card' },
    h('h2', {}, 'CNC İmalat Proses Rotası (OP10–OP50), Kesme Parametreleri & DFM Risk Analizi'),
    h('div', { class: 'cnc-meta-summary small' },
      h('span', {}, `Grup: ${cp.group || '—'}`),
      h('span', {}, `Torna Vc: ${cp.vc_turn || '—'}`),
      h('span', {}, `Freze Vc: ${cp.vc_mill || '—'}`),
      h('span', {}, `İlerleme: ${cp.feed || '—'}`),
      h('span', {}, `Soğutma: ${cp.coolant || '—'}`),
    ),
    h('div', { class: 'cnc-table-scroll' },
      h('table', { class: 'cnc-table' },
        h('thead', {}, h('tr', {}, ...cols.map((t) => h('th', {}, t)))),
        h('tbody', {}, ...opRows),
      ),
    ),
    h('h3', { style: { color: '#991b1b', marginTop: '14px' } }, '! DFM & Kritik Kalite Risk Uyarıları'),
    riskList,
  );
}

export function renderJobWorkspace(workspace, state, hooks) {
  workspace.replaceChildren();
  if (!state.currentJob) return;
  const job = state.currentJob;
  const balloons = (job.balloons || []).map((b) => ({ ...b }));
  const { card: tableCard, redraw } = buildBalloonTableCard(job, balloons, hooks);
  const viewerCard = buildViewerCard(job, balloons, state, { ...hooks, onRowsChanged: redraw });
  workspace.append(viewerCard, tableCard);
  if (job.manufacturing_plan) workspace.append(buildManufacturingPlanCard(job.manufacturing_plan));
}
