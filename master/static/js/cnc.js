// CNC Technical Drawing Ballooning View (AS9102 / ISO 2768-mK).
import { api, formatDateTime, h } from './util.js';

let currentJob = null;
let showOriginal = false;
let zoomLevel = 1.0;

function badgeClass(crit) {
  if (crit === 'Kritik') return 'cnc-badge cnc-crit';
  if (crit === 'Majör') return 'cnc-badge cnc-major';
  return 'cnc-badge cnc-minor';
}

export async function renderCnc(root) {
  root.innerHTML = '';
  const wrap = h('div', { class: 'page-inner cnc-page' });
  root.appendChild(wrap);

  const statusBox = h('div', { class: 'card note', hidden: true });
  const jobsBar = h('div', { class: 'cnc-jobs-bar' });
  const workspace = h('div', { class: 'cnc-workspace' });

  // --- Header ---
  const demoBtn = h('button', { class: 'btn btn-primary', type: 'button' }, '✨ Örnek CNC Çizimi (Demo)');
  const head = h('div', { class: 'page-head' },
    h('div', {},
      h('h1', { class: 'page-title' }, 'CNC Teknik Çizim Balonlama'),
      h('p', { class: 'page-lead' },
        'PDF, fotoğraf (PNG/JPG), Word (.docx) veya Excel (.xlsx) teknik çizimlerinden tüm CNC ölçülerini, ' +
        'ISO 286 geçmelerini (H7/h6), GD&T sembollerini ve Ra yüzey pürüzlülüklerini otomatik balonlar; ' +
        'AS9102 / FAI Excel, Word ve PDF kalite kontrol raporlarını üretir.'
      ),
    ),
    h('div', { class: 'card-actions', style: { marginTop: '0' } }, demoBtn),
  );

  // --- Upload Card ---
  const fileInput = h('input', {
    type: 'file',
    accept: '.pdf,.png,.jpg,.jpeg,.webp,.bmp,.tiff,.docx,.xlsx,.xlsm',
    style: { display: 'none' },
  });
  const fileLabel = h('span', { class: 'muted small' }, 'Dosya seçilmedi (PDF, PNG, JPG, DOCX, XLSX)');
  const pickBtn = h('button', { class: 'btn', type: 'button' }, '📎 Teknik Çizim Seç');
  const partNoIn = h('input', { class: 'cnc-input', placeholder: 'Parça No (opsiyonel, ör. FLN-2026-042)' });
  const matIn = h('input', { class: 'cnc-input', placeholder: 'Malzeme (ör. AISI 4140 / Al 6061)' });
  const stdIn = h('input', { class: 'cnc-input', value: 'ISO 2768-mK', placeholder: 'Standart' });
  const runBtn = h('button', { class: 'btn btn-primary', type: 'button', disabled: true }, '◎ Balonlamayı Başlat');

  let selectedFile = null;
  pickBtn.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => {
    selectedFile = fileInput.files[0] || null;
    fileLabel.textContent = selectedFile ? `Seçili: ${selectedFile.name}` : 'Dosya seçilmedi';
    runBtn.disabled = !selectedFile;
  });

  const uploadCard = h('div', { class: 'card cnc-upload-card' },
    h('div', { class: 'cnc-upload-row' },
      pickBtn, fileLabel, fileInput,
    ),
    h('div', { class: 'cnc-meta-grid' },
      partNoIn, matIn, stdIn, runBtn,
    ),
  );

  wrap.append(head, uploadCard, statusBox, jobsBar, workspace);

  function setStatus(msg, isError = false) {
    statusBox.hidden = !msg;
    statusBox.className = isError ? 'card error' : 'card note';
    statusBox.textContent = msg;
  }

  async function refreshJobs(selectId = null) {
    const data = await api('/api/cnc/jobs');
    const jobs = data.jobs || [];
    jobsBar.innerHTML = '';
    if (!jobs.length) {
      jobsBar.append(h('div', { class: 'muted small' }, 'Henüz balonlanmış çizim yok. Yukarıdan dosya yükleyebilir veya "Örnek CNC Çizimi" butonuna basabilirsiniz.'));
      return;
    }
    jobsBar.append(h('span', { class: 'small muted', style: { marginRight: '8px' } }, 'Kayıtlı Çizimler:'));
    for (const j of jobs) {
      const pill = h('button', {
        type: 'button',
        class: 'cnc-job-pill' + (currentJob && currentJob.id === j.id ? ' active' : ''),
        onClick: () => loadJob(j.id),
      }, `${j.metadata?.part_number || j.filename} (${j.balloon_count} balon)`);
      jobsBar.append(pill);
    }
    if (selectId) {
      await loadJob(selectId);
    } else if (!currentJob && jobs.length > 0) {
      await loadJob(jobs[0].id);
    }
  }

  async function loadJob(id) {
    setStatus('Çizim yükleniyor...');
    try {
      currentJob = await api(`/api/cnc/jobs/${id}`);
      setStatus('');
      renderJobWorkspace();
      for (const btn of jobsBar.querySelectorAll('.cnc-job-pill')) {
        btn.classList.toggle('active', btn.textContent.includes(currentJob.metadata?.part_number || currentJob.filename));
      }
    } catch (err) {
      setStatus('Yükleme hatası: ' + err.message, true);
    }
  }

  function renderJobWorkspace() {
    workspace.innerHTML = '';
    if (!currentJob) return;

    const job = currentJob;
    const ts = Date.now();
    const imgKind = showOriginal ? 'original' : 'ballooned.png';
    const imgUrl = `/api/cnc/jobs/${job.id}/file/${imgKind}?t=${ts}`;

    // Export & View Toolbar
    const toggleBtn = h('button', {
      type: 'button', class: 'btn',
      onClick: () => { showOriginal = !showOriginal; renderJobWorkspace(); },
    }, showOriginal ? '◎ Balonlu Görünümü Göster' : '👁 Orijinal Çizimi Göster');

    const zoomOut = h('button', {
      type: 'button', class: 'btn',
      onClick: () => { zoomLevel = Math.max(0.5, +(zoomLevel - 0.2).toFixed(1)); updateZoom(); },
    }, '−');
    const zoomIn = h('button', {
      type: 'button', class: 'btn',
      onClick: () => { zoomLevel = Math.min(2.4, +(zoomLevel + 0.2).toFixed(1)); updateZoom(); },
    }, '+');
    const zoomLabel = h('span', { class: 'small muted' }, `${Math.round(zoomLevel * 100)}%`);

    const imgEl = h('img', {
      src: imgUrl,
      alt: job.filename,
      class: 'cnc-drawing-img',
      style: { width: `${zoomLevel * 100}%`, cursor: 'crosshair' },
      title: 'Yeni balon eklemek için çizim üzerinde istediğiniz ölçüye tıklayın',
    });
    function updateZoom() {
      imgEl.style.width = `${zoomLevel * 100}%`;
      zoomLabel.textContent = `${Math.round(zoomLevel * 100)}%`;
    }

    const balloons = (job.balloons || []).map((b) => ({ ...b }));
    let renderRowsFn = () => {};

    imgEl.addEventListener('click', (ev) => {
      const rect = imgEl.getBoundingClientRect();
      const xPct = +(((ev.clientX - rect.left) / rect.width) * 100).toFixed(1);
      const yPct = +(((ev.clientY - rect.top) / rect.height) * 100).toFixed(1);
      const raw = prompt(`(${xPct}%, ${yPct}%) konumuna eklenecek CNC ölçüsü (ör. Ø25 H7, Ra 1.6, M8x1.25):`);
      if (!raw || !raw.trim()) return;
      balloons.push({
        raw_text: raw.trim(), category: 'Lineer Ölçü', nominal: null, unit: 'mm',
        gage: 'Dijital Kumpas', criticality: 'Majör', operation: 'OP10 · CNC İşleme',
        tooling: 'Karbür Kesici Takım', inspection_freq: 'İlk Parça + 1/10',
        x_pct: xPct, y_pct: yPct, zone: '',
      });
      renderRowsFn();
      setStatus(`Yeni balon (${raw.trim()}) eklendi. Çizime işlemek için "Kaydet ve Yeniden Balonla" butonuna basın.`);
    });

    const exportBar = h('div', { class: 'cnc-export-bar' },
      h('a', { class: 'btn btn-primary', href: `/api/cnc/jobs/${job.id}/file/report.xlsx`, download: '' }, '📊 Excel Raporu (.xlsx)'),
      h('a', { class: 'btn btn-primary', href: `/api/cnc/jobs/${job.id}/file/report.docx`, download: '' }, '📝 Word Raporu (.docx)'),
      h('a', { class: 'btn', href: `/api/cnc/jobs/${job.id}/file/ballooned.pdf`, download: '' }, '📄 Balonlu PDF'),
      h('a', { class: 'btn', href: `/api/cnc/jobs/${job.id}/file/ballooned.png`, download: `${job.id}-ballooned.png` }, '🖼 Balonlu PNG'),
    );

    const metaSummary = h('div', { class: 'cnc-meta-summary small' },
      h('span', {}, `Parça: ${job.metadata?.part_name || job.filename}`),
      h('span', {}, `Parça No: ${job.metadata?.part_number || '—'}`),
      h('span', {}, `Malzeme: ${job.metadata?.material || '—'}`),
      h('span', {}, `Standart: ${job.metadata?.standard || 'ISO 2768-mK'}`),
      h('span', {}, `Motor: ${job.engine_used || 'auto'}`),
      h('span', {}, `Tarih: ${formatDateTime(job.created_at)}`),
    );

    const viewerCard = h('div', { class: 'card cnc-viewer-card' },
      h('div', { class: 'cnc-toolbar' },
        h('div', { class: 'cnc-toolbar-left' }, toggleBtn, zoomOut, zoomLabel, zoomIn),
        exportBar,
      ),
      metaSummary,
      h('div', { class: 'cnc-canvas-wrap' }, imgEl),
    );

    // Editable Balloon Table
    const tbody = h('tbody');

    function renderRows() {
      tbody.innerHTML = '';
      balloons.forEach((b, idx) => {
        const rawIn = h('input', { class: 'cnc-cell-in', value: b.raw_text || '', onInput: (e) => { b.raw_text = e.target.value; } });
        const catIn = h('input', { class: 'cnc-cell-in', value: b.category || '', onInput: (e) => { b.category = e.target.value; } });
        const opIn = h('input', { class: 'cnc-cell-in', value: b.operation || '', onInput: (e) => { b.operation = e.target.value; } });
        const gageIn = h('input', { class: 'cnc-cell-in', value: b.gage || '', onInput: (e) => { b.gage = e.target.value; } });
        const delBtn = h('button', {
          type: 'button', class: 'btn btn-danger cnc-del-btn', title: 'Balonu sil',
          onClick: () => { balloons.splice(idx, 1); renderRows(); },
        }, '✕');

        const minMax = (b.min_limit != null && b.max_limit != null) ? `${b.min_limit} / ${b.max_limit}` : '—';
        const tr = h('tr', {},
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
        );
        tbody.appendChild(tr);
      });
    }
    renderRowsFn = renderRows;
    renderRows();

    const addBtn = h('button', {
      type: 'button', class: 'btn',
      onClick: () => {
        balloons.push({
          raw_text: 'Ø20 ±0.05', category: 'Çap (Ø)', nominal: 20, unit: 'mm',
          tol_plus: 0.05, tol_minus: -0.05, min_limit: 19.95, max_limit: 20.05,
          gage: 'Dijital Kumpas', criticality: 'Majör', x_pct: 50, y_pct: 50, zone: 'B3',
        });
        renderRows();
      },
    }, '＋ Balon Ekle');

    const saveBtn = h('button', {
      type: 'button', class: 'btn btn-primary',
      onClick: async () => {
        saveBtn.disabled = true;
        saveBtn.textContent = '⏳ Yeniden balonlanıyor...';
        try {
          currentJob = await api(`/api/cnc/jobs/${job.id}/balloons`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ metadata: job.metadata, balloons }),
          });
          setStatus('Balonlar güncellendi; PNG, PDF, Excel ve Word raporları yeniden oluşturuldu.');
          renderJobWorkspace();
        } catch (err) {
          setStatus('Güncelleme hatası: ' + err.message, true);
        } finally {
          saveBtn.disabled = false;
          saveBtn.textContent = '💾 Kaydet ve Yeniden Balonla';
        }
      },
    }, '💾 Kaydet ve Yeniden Balonla');

    const tableCard = h('div', { class: 'card cnc-table-card' },
      h('div', { class: 'cnc-toolbar' },
        h('h2', { style: { margin: 0 } }, `AS9102 / FAI Balonlama Tablosu (${balloons.length} Karakteristik)`),
        h('div', { class: 'card-actions', style: { marginTop: 0 } }, addBtn, saveBtn),
      ),
      h('div', { class: 'cnc-table-scroll' },
        h('table', { class: 'cnc-table' },
          h('thead', {},
            h('tr', {},
              h('th', {}, 'No'),
              h('th', {}, 'Bölge'),
              h('th', {}, 'Çizim İfadesi'),
              h('th', {}, 'Kategori'),
              h('th', {}, 'Min / Max'),
              h('th', {}, 'Operasyon (OP)'),
              h('th', {}, 'Önerilen Kesici Takım'),
              h('th', {}, 'Ölçüm Ekipmanı'),
              h('th', {}, 'Kontrol Sıklığı'),
              h('th', {}, 'Kritiklik'),
              h('th', {}, ''),
            ),
          ),
          tbody,
        ),
      ),
    );

    workspace.append(viewerCard, tableCard);

    // CNC Manufacturing Process Plan & DFM Risk Card
    const plan = job.manufacturing_plan;
    if (plan) {
      const cp = plan.cutting_parameters || {};
      const opRows = (plan.operations || []).map((op) =>
        h('tr', {},
          h('td', { style: { fontWeight: 700 } }, op.op),
          h('td', {}, op.name),
          h('td', {}, op.machine),
          h('td', {}, op.fixture),
          h('td', {}, (op.balloons || []).map((n) => `#${n}`).join(', ') || 'Genel'),
          h('td', { class: 'small' }, op.notes),
        )
      );
      const riskList = h('ul', { style: { margin: '8px 0 0 18px', lineHeight: 1.6 } },
        ...(plan.dfm_risks || []).map((r) => h('li', {}, r)),
      );
      const planCard = h('div', { class: 'card' },
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
            h('thead', {},
              h('tr', {},
                h('th', {}, 'OP'),
                h('th', {}, 'Operasyon Adı'),
                h('th', {}, 'Tezgâh'),
                h('th', {}, 'Bağlama / Fikstür'),
                h('th', {}, 'Kapsanan Balonlar'),
                h('th', {}, 'Setup / Mühendislik Notu'),
              ),
            ),
            h('tbody', {}, ...opRows),
          ),
        ),
        h('h3', { style: { color: '#991b1b', marginTop: '14px' } }, '⚠️ DFM & Kritik Kalite Risk Uyarıları'),
        riskList,
      );
      workspace.append(planCard);
    }
  }

  runBtn.addEventListener('click', async () => {
    if (!selectedFile) return;
    runBtn.disabled = true;
    setStatus('Teknik çizim analiz ediliyor, balonlar yerleştiriliyor ve PDF/Word/Excel raporları oluşturuluyor...');
    try {
      const fd = new FormData();
      fd.append('file', selectedFile);
      fd.append('part_number', partNoIn.value.trim());
      fd.append('material', matIn.value.trim());
      fd.append('standard', stdIn.value.trim() || 'ISO 2768-mK');
      const job = await api('/api/cnc/balloon', { method: 'POST', body: fd });
      currentJob = job;
      setStatus(`Balonlama tamamlandı: ${job.balloons.length} karakteristik tespit edildi.`);
      await refreshJobs(job.id);
    } catch (err) {
      setStatus('Balonlama hatası: ' + err.message, true);
    } finally {
      runBtn.disabled = false;
    }
  });

  demoBtn.addEventListener('click', async () => {
    demoBtn.disabled = true;
    setStatus('Örnek CNC Rulman Yatağı Flanşı (FLN-2026-042) üretiliyor ve balonlanıyor...');
    try {
      const job = await api('/api/cnc/demo', { method: 'POST' });
      currentJob = job;
      setStatus(`Örnek CNC çizimi balonlandı: ${job.balloons.length} karakteristik, PDF/Excel/Word hazır.`);
      await refreshJobs(job.id);
    } catch (err) {
      setStatus('Demo oluşturma hatası: ' + err.message, true);
    } finally {
      demoBtn.disabled = false;
    }
  });

  await refreshJobs();
}
