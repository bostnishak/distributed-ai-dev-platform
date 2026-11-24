// CNC Technical Drawing Ballooning View (AS9102 / ISO 2768-mK).
import { renderJobWorkspace } from './cnc_workspace.js';
import { api, h } from './util.js';

const cncState = {
  currentJob: null,
  showOriginal: false,
  zoomLevel: 1.0,
};

function buildCncHeaderAndUpload(onFileSelected) {
  const demoBtn = h('button', { class: 'btn btn-primary', type: 'button' }, 'Örnek CNC Çizimi (Demo)');
  const head = h('div', { class: 'page-head' },
    h('div', {},
      h('h1', { class: 'page-title' }, 'CNC Teknik Çizim Balonlama'),
      h('p', { class: 'page-lead' },
        'PDF, fotoğraf (PNG/JPG), Word (.docx) veya Excel (.xlsx) teknik çizimlerinden tüm CNC ölçülerini, ' +
        'ISO 286 geçmelerini (H7/h6), GD&T sembollerini ve Ra yüzey pürüzlülüklerini otomatik balonlar; ' +
        'AS9102 / FAI Excel, Word ve PDF kalite kontrol raporlarını üretir.',
      ),
    ),
    h('div', { class: 'card-actions', style: { marginTop: '0' } }, demoBtn),
  );

  const fileInput = h('input', {
    type: 'file',
    accept: '.pdf,.png,.jpg,.jpeg,.webp,.bmp,.tiff,.docx,.xlsx,.xlsm',
    class: 'sr-only-file',
    'aria-label': 'CNC teknik çizim dosyası seç',
  });
  const fileLabel = h('span', { class: 'muted small' }, 'Dosya seçilmedi (PDF, PNG, JPG, DOCX, XLSX)');
  const pickBtn = h('button', { class: 'btn', type: 'button' }, 'Dosya: Teknik Çizim Seç');
  const partNoIn = h('input', { class: 'cnc-input', 'aria-label': 'Parça numarası', placeholder: 'Parça No (opsiyonel, ör. FLN-2026-042)' });
  const matIn = h('input', { class: 'cnc-input', 'aria-label': 'Malzeme', placeholder: 'Malzeme (ör. AISI 4140 / Al 6061)' });
  const stdIn = h('input', { class: 'cnc-input', 'aria-label': 'Standart', value: 'ISO 2768-mK', placeholder: 'Standart' });
  const runBtn = h('button', { class: 'btn btn-primary', type: 'button', disabled: true }, '◎ Balonlamayı Başlat');

  pickBtn.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => {
    const file = fileInput.files[0] || null;
    fileLabel.textContent = file ? `Seçili: ${file.name}` : 'Dosya seçilmedi';
    runBtn.disabled = !file;
    onFileSelected(file);
  });

  const uploadCard = h('div', { class: 'card cnc-upload-card' },
    h('div', { class: 'cnc-upload-row' }, pickBtn, fileLabel, fileInput),
    h('div', { class: 'cnc-meta-grid' }, partNoIn, matIn, stdIn, runBtn),
  );
  return { head, uploadCard, demoBtn, partNoIn, matIn, stdIn, runBtn };
}

function bindCncUploadActions(controls, getSelectedFile, hooks) {
  const { runBtn, demoBtn, partNoIn, matIn, stdIn } = controls;
  runBtn.addEventListener('click', async () => {
    const selectedFile = getSelectedFile();
    if (!selectedFile) return;
    runBtn.disabled = true;
    hooks.setStatus('Teknik çizim analiz ediliyor, balonlar yerleştiriliyor ve PDF/Word/Excel raporları oluşturuluyor...');
    try {
      const fd = new FormData();
      fd.append('file', selectedFile);
      fd.append('part_number', partNoIn.value.trim());
      fd.append('material', matIn.value.trim());
      fd.append('standard', stdIn.value.trim() || 'ISO 2768-mK');
      const job = await api('/api/cnc/balloon', { method: 'POST', body: fd });
      cncState.currentJob = job;
      hooks.setStatus(`Balonlama tamamlandı: ${job.balloons.length} karakteristik tespit edildi.`);
      await hooks.refreshJobs(job.id);
    } catch (err) {
      hooks.setStatus('Balonlama hatası: ' + err.message, true);
    } finally {
      runBtn.disabled = false;
    }
  });

  demoBtn.addEventListener('click', async () => {
    demoBtn.disabled = true;
    hooks.setStatus('Örnek CNC Rulman Yatağı Flanşı (FLN-2026-042) üretiliyor ve balonlanıyor...');
    try {
      const job = await api('/api/cnc/demo', { method: 'POST' });
      cncState.currentJob = job;
      hooks.setStatus(`Örnek CNC çizimi balonlandı: ${job.balloons.length} karakteristik, PDF/Excel/Word hazır.`);
      await hooks.refreshJobs(job.id);
    } catch (err) {
      hooks.setStatus('Demo oluşturma hatası: ' + err.message, true);
    } finally {
      demoBtn.disabled = false;
    }
  });
}

export async function renderCnc(root) {
  root.replaceChildren();
  const wrap = h('div', { class: 'page-inner cnc-page' });
  root.appendChild(wrap);

  const statusBox = h('div', { class: 'card note', hidden: true });
  const jobsBar = h('div', { class: 'cnc-jobs-bar' });
  const workspace = h('div', { class: 'cnc-workspace' });
  let selectedFile = null;

  const controls = buildCncHeaderAndUpload((f) => { selectedFile = f; });
  wrap.append(controls.head, controls.uploadCard, statusBox, jobsBar, workspace);

  function setStatus(msg, isError = false) {
    statusBox.hidden = !msg;
    statusBox.className = isError ? 'card error' : 'card note';
    statusBox.textContent = msg;
  }

  function redrawWorkspace() {
    renderJobWorkspace(workspace, cncState, {
      setStatus,
      rerender: redrawWorkspace,
      onJobUpdated: (updated) => { cncState.currentJob = updated; redrawWorkspace(); },
    });
  }

  async function loadJob(id) {
    setStatus('Çizim yükleniyor...');
    try {
      cncState.currentJob = await api(`/api/cnc/jobs/${id}`);
      setStatus('');
      redrawWorkspace();
      for (const btn of jobsBar.querySelectorAll('.cnc-job-pill')) {
        btn.classList.toggle('active', btn.textContent.includes(cncState.currentJob.metadata?.part_number || cncState.currentJob.filename));
      }
    } catch (err) {
      setStatus('Yükleme hatası: ' + err.message, true);
    }
  }

  async function refreshJobs(selectId = null) {
    const data = await api('/api/cnc/jobs');
    const jobs = data.jobs || [];
    jobsBar.replaceChildren();
    if (!jobs.length) {
      jobsBar.append(h('div', { class: 'muted small' }, 'Henüz balonlanmış çizim yok. Yukarıdan dosya yükleyebilir veya "Örnek CNC Çizimi" butonuna basabilirsiniz.'));
      return;
    }
    jobsBar.append(h('span', { class: 'small muted', style: { marginRight: '8px' } }, 'Kayıtlı Çizimler:'));
    for (const j of jobs) {
      jobsBar.append(h('button', {
        type: 'button',
        class: 'cnc-job-pill' + (cncState.currentJob && cncState.currentJob.id === j.id ? ' active' : ''),
        onClick: () => loadJob(j.id),
      }, `${j.metadata?.part_number || j.filename} (${j.balloon_count} balon)`));
    }
    if (selectId) await loadJob(selectId);
    else if (!cncState.currentJob && jobs.length > 0) await loadJob(jobs[0].id);
  }

  bindCncUploadActions(controls, () => selectedFile, { setStatus, refreshJobs });
  await refreshJobs();
}
