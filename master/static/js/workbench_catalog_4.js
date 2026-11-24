// Interactive Workbench Catalog Part 4: Factory Templates, IDE Bridge, HA, ML Promotion, Accounting & Notebooks.

export const PLATFORM_EXT_TOOLS = [
  // EPK-05: Doğrulanmış Yazılım Fabrikası Şablonları
  { id: 'fac-vtpl', group: 'Yazılım Fabrikası & IDE', title: '8 Doğrulanmış Şablonu Listele', method: 'GET', path: '/api/factory/verified-templates' },
  { id: 'fac-vchk', group: 'Yazılım Fabrikası & IDE', title: 'Şablonu Sözdizimi & Güvenlik Doğrula', method: 'POST', path: '/api/factory/verified-templates/{template_id}/verify',
    params: { template_id: 'fastapi_service' }, body: { errors: [] } },

  // EPK-06: IDE LSP / DAP / Çoklu Diff
  { id: 'ide-lsp', group: 'Yazılım Fabrikası & IDE', title: 'IDE LSP Tanılama & Semboller', method: 'POST', path: '/api/ide/lsp/diagnostics',
    body: { language: 'python', code: 'def hesapla(x):\n    return x * 2\n' } },
  { id: 'ide-dap', group: 'Yazılım Fabrikası & IDE', title: 'IDE DAP Hata Ayıklama Oturumu', method: 'POST', path: '/api/ide/dap/session',
    body: { code: 'x = 1\ny = x + 2\n', breakpoints: [1, 2] } },
  { id: 'ide-diff', group: 'Yazılım Fabrikası & IDE', title: 'Çoklu Dosya Unified Diff', method: 'POST', path: '/api/ide/diff/multi',
    body: { files: [{ path: 'app.py', before: 'a = 1\n', after: 'a = 2\n' }] } },

  // EPK-10 & EPK-30: Yüksek Erişilebilirlik & İdempotency
  { id: 'ha-lease', group: 'Yüksek Erişilebilirlik (HA)', title: 'HA Lider Kirası Al / Yenile', method: 'POST', path: '/api/ha/lease',
    body: { node_id: 'master-1', lease_key: 'master-primary', ttl_s: 15 } },
  { id: 'ha-status', group: 'Yüksek Erişilebilirlik (HA)', title: 'HA Lider & Amdahl Hızlanma Durumu', method: 'GET', path: '/api/ha/status' },
  { id: 'ha-drain', group: 'Yüksek Erişilebilirlik (HA)', title: 'Düğümü Rolling Upgrade için Tahliye Et', method: 'POST', path: '/api/ha/drain/{node_id}',
    params: { node_id: 'master-1' }, body: {} },
  { id: 'ha-idem', group: 'Yüksek Erişilebilirlik (HA)', title: 'İdempotent Görev Sonucu Kaydet', method: 'POST', path: '/api/ha/idempotency/commit',
    body: { idempotency_key: 'task-101-v1', task_id: '101', agent_id: 'uye1', payload: 'ok' } },

  // EPK-31: ML Model Terfi Kapısı & Rollback
  { id: 'ml-promote', group: 'Model Terfisi & Kullanım Kotası', title: 'ML Model Terfi Kapısı (Eval Gate)', method: 'POST', path: '/api/ml/models/{model_id}/promote',
    params: { model_id: 'qwen3.5-tr-v1' }, body: { eval_score: 0.91, min_threshold: 0.80, canary_pct: 20 } },
  { id: 'ml-rollback', group: 'Model Terfisi & Kullanım Kotası', title: 'ML Model Geri Al (Rollback)', method: 'POST', path: '/api/ml/models/{model_id}/rollback',
    params: { model_id: 'qwen3.5-tr-v1' }, body: { reason: 'canary_regression' }, dangerous: true },

  // EPK-32: Token, Enerji (Wh) & Günlük Kota Muhasebesi
  { id: 'acc-rec', group: 'Model Terfisi & Kullanım Kotası', title: 'Kullanım & Enerji (Wh) Kaydet', method: 'POST', path: '/api/accounting/record',
    body: { user_id: 'default', model: 'qwen3.5:4b', tokens_in: 120, tokens_out: 240, latency_ms: 850 } },
  { id: 'acc-quota', group: 'Model Terfisi & Kullanım Kotası', title: 'Günlük Kullanıcı Kotasını Güncelle', method: 'PUT', path: '/api/accounting/quotas/{user_id}',
    params: { user_id: 'default' }, body: { daily_token_limit: 250000, daily_energy_wh_limit: 500, hard_enforce: true } },
  { id: 'acc-rep', group: 'Model Terfisi & Kullanım Kotası', title: 'Günlük Token & Enerji Raporu', method: 'GET', path: '/api/accounting/report/{user_id}',
    params: { user_id: 'default' } },

  // EPK-33: Hücre Tabanlı Defter (.ipynb)
  { id: 'nb-list', group: 'Hücre Tabanlı Defter (.ipynb)', title: 'Defterleri Listele', method: 'GET', path: '/api/notebooks' },
  { id: 'nb-create', group: 'Hücre Tabanlı Defter (.ipynb)', title: 'Yeni Defter Oluştur', method: 'POST', path: '/api/notebooks',
    body: { user_id: 'default', title: 'Analiz Defteri', cells: [{ cell_type: 'code', source: 'x = 21\nprint(x * 2)\nx * 2' }] } },
  { id: 'nb-run', group: 'Hücre Tabanlı Defter (.ipynb)', title: 'Defter Hücresini Çalıştır', method: 'POST', path: '/api/notebooks/{notebook_id}/run',
    params: { notebook_id: 'nb_demo' }, body: { user_id: 'default', cell_index: 0 } },
  { id: 'nb-exp', group: 'Hücre Tabanlı Defter (.ipynb)', title: 'Jupyter .ipynb Dışa Aktar', method: 'GET', path: '/api/notebooks/{notebook_id}/export.ipynb',
    params: { notebook_id: 'nb_demo' } },
  { id: 'nb-imp', group: 'Hücre Tabanlı Defter (.ipynb)', title: 'Jupyter .ipynb İçe Aktar', method: 'POST', path: '/api/notebooks/import-ipynb',
    body: { user_id: 'default', ipynb: { nbformat: 4, nbformat_minor: 5, metadata: { title: 'Ornek' }, cells: [{ cell_type: 'code', source: ['1 + 1'] }] } } },

  // Wave 3D: Görsel Kalite, VQA, Veri Sızıntısı, SM-2 Eğitim, Kaynaklı KB, Mühendislik & Medya
  { id: 'pres-vqa', group: 'Stüdyolar, VQA & Veri Sızıntısı', title: 'Sunum Görsel Kalite & WCAG Denetimi', method: 'POST', path: '/api/studios/presentation/visual-qa',
    body: { theme_id: 'corporate_navy', slides: [{ title: 'Özet', bullets: ['Madde 1', 'Madde 2'], source: 'Dahili Rapor' }] } },
  { id: 'mm-vqa', group: 'Stüdyolar, VQA & Veri Sızıntısı', title: 'Yerel Görsel VQA Analizi', method: 'POST', path: '/api/studios/media/vqa',
    body: { image_b64: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', question: 'Görsel tonu nedir?' } },
  { id: 'mm-vid', group: 'Stüdyolar, VQA & Veri Sızıntısı', title: 'Video Anahtar Kare (Keyframe) Tespiti', method: 'POST', path: '/api/studios/media/video-analyze',
    body: { frames_b64: ['iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='], fps: 1.0 } },
  { id: 'mm-wer', group: 'Stüdyolar, VQA & Veri Sızıntısı', title: 'Türkçe ASR WER Ölçümü', method: 'POST', path: '/api/studios/media/asr-wer',
    body: { reference: 'merhaba dünya nasılsın', hypothesis: 'merhaba dünya nasılsın' } },
  { id: 'ds-leak', group: 'Stüdyolar, VQA & Veri Sızıntısı', title: 'Eğitim/Test Veri Sızıntı Koruması', method: 'POST', path: '/api/studios/data/leakage-check',
    body: { train_rows: [{ x: 1, y: 2 }, { x: 2, y: 4 }, { x: 3, y: 6 }], test_rows: [{ x: 4, y: 8 }], target_col: 'y' } },
  { id: 'ds-sql', group: 'Stüdyolar, VQA & Veri Sızıntısı', title: 'Bellek İçi SQL Veri Analizi', method: 'POST', path: '/api/studios/data/sql-query',
    body: { rows: [{ urun: 'A', adet: 10 }, { urun: 'B', adet: 25 }], sql: 'SELECT SUM(adet) AS toplam FROM data' } },
  { id: 'edu-fc-list', group: 'Eğitim (SM-2) & Kaynaklı Alanlar', title: 'SM-2 Çalışma Kartlarını Listele', method: 'GET', path: '/api/education/flashcards' },
  { id: 'edu-fc-add', group: 'Eğitim (SM-2) & Kaynaklı Alanlar', title: 'Yeni SM-2 Kartı Oluştur', method: 'POST', path: '/api/education/flashcards',
    body: { user_id: 'default', topic: 'Algoritmalar', front: 'Binary search karmaşıklığı?', back: 'O(log n)' } },
  { id: 'edu-fc-rev', group: 'Eğitim (SM-2) & Kaynaklı Alanlar', title: 'SM-2 Tekrar Puanla (0..5)', method: 'POST', path: '/api/education/flashcards/{card_id}/review',
    params: { card_id: 'card_demo' }, body: { user_id: 'default', quality: 5 } },
  { id: 'edu-exam', group: 'Eğitim (SM-2) & Kaynaklı Alanlar', title: 'Rubrik Tabanlı Sınav Notlandırma', method: 'POST', path: '/api/education/grade-exam',
    body: { questions: [{ points: 50, expected_key: 'b', student_answer: 'B' }, { points: 50, rubric_keywords: ['hash', 'o(1)'], student_answer: 'Hash tablosu ortalama O(1) arama sağlar' }] } },
  { id: 'dom-kb', group: 'Eğitim (SM-2) & Kaynaklı Alanlar', title: 'Kaynaklı Hukuk / Sağlık / Finans KB', method: 'POST', path: '/api/domains/kb/query',
    body: { domain: 'legal', query: 'KVKK kişisel veri silme maddesi' } },
  { id: 'eng-bench', group: 'Eğitim (SM-2) & Kaynaklı Alanlar', title: '15 Mühendislik Formül Kıyaslaması', method: 'GET', path: '/api/domains/engineering/benchmarks' },
  { id: 'eng-gcode', group: 'Eğitim (SM-2) & Kaynaklı Alanlar', title: 'CNC G-Code Güvenlik & Çarpışma Denetimi', method: 'POST', path: '/api/domains/engineering/gcode-audit',
    body: { gcode: 'G21 G90\nG00 Z50\nM03 S1200\nG01 Z-2 F200\nM05\nM30' } },
  { id: 'med-srt', group: 'Medya Üreticileri (SRT / 3B)', title: 'SRT Altyazı Dosyası Üret', method: 'POST', path: '/api/media/srt',
    body: { segments: [{ start_s: 0.0, end_s: 2.5, text: 'Merhaba, DADP platformuna hoş geldiniz.' }] } },
  { id: 'med-3d', group: 'Medya Üreticileri (SRT / 3B)', title: 'Three.js 3B Sahne Spesifikasyonu', method: 'POST', path: '/api/media/scene-3d',
    body: { prompt: 'Mavi metalik flanş halkası 3B modeli' } },
  { id: 'med-be', group: 'Medya Üreticileri (SRT / 3B)', title: 'Yerel Medya Arka Uç Durumu', method: 'GET', path: '/api/media/backends' },
];
