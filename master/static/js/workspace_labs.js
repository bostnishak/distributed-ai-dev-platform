// Dedicated interactive visual lab panels: Notebook, SM-2 Flashcards, Memory Conflicts, Eval Benchmark, HA/Amdahl SVG.
import { safeFetchJson } from './storage.js';
import { uiToast } from './ui_dialog.js';
import { csrfHeaders, h, svg } from './util.js';

function jsonPost(url, body) {
  return safeFetchJson(url, {
    method: 'POST',
    headers: csrfHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  });
}

function buildNotebookPanel() {
  const titleInp = h('input', { type: 'text', value: 'Veri Analizi Defteri', 'aria-label': 'Not defteri başlığı' });
  const codeInp = h('textarea', { rows: 4, 'aria-label': 'Not defteri Python hücresi' }, 'x = [10, 20, 30, 40]\nprint("Ortalama:", sum(x) / len(x))');
  const outPre = h('pre', { class: 'hub-result', hidden: true });
  let lastCode = null;
  let nbId = null;

  const runBtn = h('button', {
    type: 'button',
    class: 'btn primary',
    onClick: async () => {
      runBtn.disabled = true;
      const cellCode = codeInp.value;
      if (!nbId || lastCode !== cellCode) {
        const cr = await jsonPost('/api/notebooks', {
          user_id: 'default',
          title: titleInp.value.trim() || 'Defter',
          cells: [{ cell_type: 'code', source: cellCode }],
        });
        nbId = cr.ok && cr.data ? cr.data.notebook_id : null;
        lastCode = nbId ? cellCode : null;
      }
      if (!nbId) {
        outPre.textContent = 'Not defteri oluşturulamadı.';
        outPre.hidden = false;
        runBtn.disabled = false;
        return;
      }
      const res = await jsonPost(`/api/notebooks/${encodeURIComponent(nbId)}/run`, { user_id: 'default', cell_index: 0 });
      outPre.textContent = JSON.stringify(res.data || res.error, null, 2);
      outPre.hidden = false;
      runBtn.disabled = false;
      uiToast('Hücre çalıştırıldı', res.ok ? 'ok' : 'err');
    },
  }, 'Hücreyi Çalıştır');

  return h('section', { class: 'card lab-card' },
    h('h2', null, 'Etkileşimli Not Defteri (Notebook)'),
    h('div', { class: 'hub-field' }, h('label', { class: 'hub-label' }, 'Defter Adı'), titleInp),
    h('div', { class: 'hub-field' }, h('label', { class: 'hub-label' }, 'Python Hücresi'), codeInp),
    h('div', { class: 'card-actions' }, runBtn),
    outPre);
}

function buildFlashcardPanel() {
  const frontInp = h('input', { type: 'text', placeholder: 'Soru (ör. SQLite WAL modu nedir?)', 'aria-label': 'Kart sorusu' });
  const backInp = h('input', { type: 'text', placeholder: 'Cevap (ör. Okuyucu ve yazıcıyı eşzamanlı kılar)', 'aria-label': 'Kart cevabı' });
  const deckHost = h('div', { class: 'lab-deck' });

  const renderCard = (card) => {
    let flipped = false;
    const face = h('div', { class: 'lab-flash-face' }, card.front);
    const status = h('span', { class: 'hub-status' });
    const flipBtn = h('button', {
      type: 'button',
      class: 'btn',
      onClick: () => { flipped = !flipped; face.textContent = flipped ? `Cevap: ${card.back}` : card.front; },
    }, 'Çevir');
    const gradeBtn = (q, lbl) => h('button', {
      type: 'button',
      class: 'btn',
      onClick: async () => {
        const res = await jsonPost(`/api/education/flashcards/${encodeURIComponent(card.card_id)}/review`, { quality: q });
        status.textContent = res.ok && res.data ? `Yeni aralık: ${res.data.interval_days} gün` : 'Güncellenemedi';
      },
    }, lbl);
    return h('div', { class: 'card lab-flash-card' }, face, h('div', { class: 'card-actions' }, flipBtn, gradeBtn(2, 'Zor'), gradeBtn(4, 'İyi'), gradeBtn(5, 'Kolay'), status));
  };

  const addBtn = h('button', {
    type: 'button',
    class: 'btn primary',
    onClick: async () => {
      if (!frontInp.value.trim() || !backInp.value.trim()) return;
      const res = await jsonPost('/api/education/flashcards', { user_id: 'default', topic: 'Genel', front: frontInp.value.trim(), back: backInp.value.trim() });
      if (res.ok && res.data) {
        deckHost.prepend(renderCard({ card_id: res.data.card_id, front: frontInp.value.trim(), back: backInp.value.trim() }));
        frontInp.value = '';
        backInp.value = '';
        uiToast('SM-2 bilgi kartı eklendi', 'ok');
      }
    },
  }, 'Kart Ekle');

  return h('section', { class: 'card lab-card' },
    h('h2', null, 'Eğitim SM-2 Bilgi Kartları'),
    h('div', { class: 'hub-field' }, frontInp),
    h('div', { class: 'hub-field' }, backInp),
    h('div', { class: 'card-actions' }, addBtn),
    deckHost);
}

function buildMemoryConflictPanel() {
  const listHost = h('div', { class: 'lab-conflicts' }, 'Çelişkileri görmek için Yenile düğmesine basın.');
  const loadConflicts = async () => {
    const res = await safeFetchJson('/api/memory/conflicts?user_id=default');
    const items = (res.ok && res.data && res.data.conflicts) || [];
    if (!items.length) {
      listHost.replaceChildren(h('p', { class: 'muted' }, 'Açık hafıza çelişkisi bulunmuyor.'));
      return;
    }
    listHost.replaceChildren(...items.map((c) => h('div', { class: 'card' },
      h('strong', null, `${c.fact_key}: `),
      h('span', null, `"${c.existing_value}" -> "${c.candidate_value}"`),
      h('div', { class: 'card-actions' },
        h('button', { type: 'button', class: 'btn primary', onClick: async () => { await jsonPost(`/api/memory/conflicts/${c.id}/resolve`, { decision: 'accept_new', user_id: 'default' }); loadConflicts(); } }, 'Yeniyi Kabul Et'),
        h('button', { type: 'button', class: 'btn', onClick: async () => { await jsonPost(`/api/memory/conflicts/${c.id}/resolve`, { decision: 'keep_existing', user_id: 'default' }); loadConflicts(); } }, 'Eskiyi Koru')))));
  };
  const refreshBtn = h('button', { type: 'button', class: 'btn', onClick: loadConflicts }, 'Çelişkileri Yenile');
  const consBtn = h('button', {
    type: 'button',
    class: 'btn primary',
    onClick: async () => {
      const res = await jsonPost('/api/memory/consolidate', { user_id: 'default', half_life_days: 90 });
      uiToast(res.ok ? 'Hafıza konsolidasyonu tamamlandı' : 'Konsolidasyon başarısız', res.ok ? 'ok' : 'err');
    },
  }, 'Zaman Bozunumlu Konsolidasyon');
  return h('section', { class: 'card lab-card' }, h('h2', null, 'Hafıza Çelişki Çözücü'), h('div', { class: 'card-actions' }, refreshBtn, consBtn), listHost);
}

function buildAmdahlAndEvalPanel() {
  const chartHost = h('div', { class: 'lab-chart' });
  const benchPre = h('pre', { class: 'hub-result', hidden: true });

  const loadHa = async () => {
    const res = await safeFetchJson('/api/ha/status');
    const matrix = (res.ok && res.data && res.data.speedup_matrix) || [];
    const maxS = Math.max(1, ...matrix.map((m) => Number(m.speedup || 1)));
    const chart = svg('svg', { viewBox: '0 0 360 130', width: '360', height: '130', role: 'img', 'aria-label': 'Amdahl Çoklu Ajan Hızlanma Grafiği' });
    matrix.forEach((m, i) => {
      const barH = Math.round((Number(m.speedup || 1) / maxS) * 85);
      const x = 25 + i * 82;
      chart.append(
        svg('rect', { x: String(x), y: String(100 - barH), width: '48', height: String(barH), rx: '4', fill: 'var(--accent, #4f46e5)' }),
        svg('text', { x: String(x + 24), y: '118', 'text-anchor': 'middle', fill: 'currentColor', 'font-size': '11' }, `${m.agents} Ajan`),
        svg('text', { x: String(x + 24), y: String(94 - barH), 'text-anchor': 'middle', fill: 'currentColor', 'font-size': '11' }, `${m.speedup}x`),
      );
    });
    const leaderTxt = res.ok && res.data ? `Aktif Lider: ${res.data.leader || 'Atanmadı'} (Dönem ${res.data.term || 0})` : 'HA verisi alınamadı';
    chartHost.replaceChildren(h('p', { class: 'muted' }, leaderTxt), chart);
  };

  const runBenchBtn = h('button', {
    type: 'button',
    class: 'btn primary',
    onClick: async () => {
      runBenchBtn.disabled = true;
      const res = await jsonPost('/api/eval-studio/benchmark-run', { limit: 60 });
      benchPre.textContent = JSON.stringify(res.data || res.error, null, 2);
      benchPre.hidden = false;
      runBenchBtn.disabled = false;
      uiToast('Türkçe Benchmark tamamlandı', res.ok ? 'ok' : 'err');
    },
  }, 'Türkçe Benchmark Çalıştır');

  const haBtn = h('button', { type: 'button', class: 'btn', onClick: loadHa }, 'HA & Amdahl Grafiğini Yükle');
  loadHa();
  return h('section', { class: 'card lab-card' }, h('h2', null, 'Eval Stüdyosu & Canlı Amdahl Hızlanma'), h('div', { class: 'card-actions' }, haBtn, runBenchBtn), chartHost, benchPre);
}

export function renderInteractiveLabsTab() {
  return h('div', { class: 'hub-body lab-grid' },
    buildNotebookPanel(),
    buildFlashcardPanel(),
    buildMemoryConflictPanel(),
    buildAmdahlAndEvalPanel());
}
