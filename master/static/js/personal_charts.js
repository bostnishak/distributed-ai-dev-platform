// UX-02 Modular Split: Personal Space usage charts and Overview section (<= 500 lines).
import { api, formatNumber, h, svg } from './util.js';

const TASK_LABELS = {
  genel: 'Genel sohbet', kod: 'Kod', analiz: 'Dosya analizi', cnc: 'CNC 2B',
  cad3d: 'CNC 3B CAD/CAM', proje: 'Proje üretimi', gorsel: 'Görsel',
  dokuman: 'Doküman', hesaplama: 'Hesaplama', engellendi: 'Engellenen',
};

export function dailyChart(daily, compact) {
  if (!Array.isArray(daily) || !daily.length) return h('div', { class: 'sp-empty' }, 'Günlük veri yok.');
  const W = 720; const H = 190; const padL = 36; const padB = 22; const padT = 8;
  const max = Math.max(1, ...daily.map((d) => d.tokens));
  const niceMax = Math.ceil(max / 10 ** Math.max(0, String(max).length - 1)) * 10 ** Math.max(0, String(max).length - 1);
  const plotW = W - padL - 6; const plotH = H - padB - padT;
  const bw = plotW / daily.length;
  const root = svg('svg', { class: 'sp-chart', viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Günlük token kullanımı' });
  for (let i = 0; i <= 4; i += 1) {
    const y = padT + plotH - (plotH * i) / 4;
    root.append(svg('line', { class: 'grid', x1: padL, x2: W - 6, y1: y, y2: y }));
    root.append(svg('text', { x: padL - 5, y: y + 3, 'text-anchor': 'end' }, compact(Math.round((niceMax * i) / 4))));
  }
  daily.forEach((d, i) => {
    const bh = (plotH * d.tokens) / niceMax;
    const rect = svg('rect', { class: 'sp-bar', x: padL + i * bw + bw * 0.14, y: padT + plotH - bh, width: Math.max(1, bw * 0.72), height: Math.max(d.tokens ? 2 : 0, bh), rx: 2 });
    rect.append(svg('title', null, `${new Date(d.date).toLocaleDateString('tr-TR', { day: 'numeric', month: 'long' })}: ${formatNumber(d.tokens)} token, ${d.messages} mesaj`));
    root.append(rect);
    const step = Math.ceil(daily.length / 7);
    if (i % step === 0) {
      root.append(svg('text', { x: padL + i * bw + bw / 2, y: H - 6, 'text-anchor': 'middle' }, new Date(d.date).toLocaleDateString('tr-TR', { day: 'numeric', month: 'short' })));
    }
  });
  return root;
}

export function hbars(items, nameKey, valueKey, valueLabel) {
  const max = Math.max(1, ...items.map((i) => i[valueKey]));
  return h('div', null, ...items.map((it) => h('div', { class: 'sp-hbar' },
    h('div', { class: 'sp-hbar-name', title: it[nameKey] }, it[nameKey]),
    h('div', { class: 'sp-hbar-track' }, h('div', { class: 'sp-hbar-fill', style: { width: `${(it[valueKey] / max) * 100}%` } })),
    h('div', { class: 'sp-hbar-val' }, valueLabel(it)))));
}

export function hourStrip(byHour) {
  const max = Math.max(1, ...byHour);
  return h('div', null,
    h('div', { class: 'sp-hours' }, ...byHour.map((c, hr) => h('div', { class: 'sp-hour', title: `${String(hr).padStart(2, '0')}:00 - ${c} mesaj`, style: { opacity: c ? 0.18 + (0.82 * c) / max : 0.07 } }))),
    h('div', { class: 'sp-hours-axis' }, h('span', null, '00'), h('span', null, '06'), h('span', null, '12'), h('span', null, '18'), h('span', null, '23')));
}

export async function renderSectionOverview(body, state, ctx) {
  const { activeUserId, setMonthTokens, renderCard, seg, compact } = ctx;
  body.replaceChildren(h('div', { class: 'loading' }, h('span', { class: 'spinner' }), 'İstatistikler yükleniyor…'));
  const s = await api(`/api/user/${activeUserId}/stats?days=${state.days}`);
  setMonthTokens(s.budget.month_tokens);
  renderCard();
  const t = s.totals;

  const range = seg([[7, 'Son 7 gün'], [30, 'Son 30 gün'], [90, 'Son 90 gün']], state.days, (v) => { state.days = Number(v); renderSectionOverview(body, state, ctx); });
  range.style.marginBottom = '14px';

  if (!t.messages) {
    body.replaceChildren(range, h('div', { class: 'sp-card' }, h('div', { class: 'sp-empty' },
      'Bu dönemde henüz kullanım kaydı yok.', h('br'), 'Asistan ile sohbet ettikçe token, yanıt süresi ve model istatistikleri burada görünecek.')));
    return;
  }

  const kpi = (num, lbl, sub) => h('div', { class: 'sp-kpi' }, h('div', { class: 'sp-kpi-num' }, num), h('div', { class: 'sp-kpi-lbl' }, lbl), sub && h('div', { class: 'sp-kpi-sub' }, sub));
  const kpis = h('div', { class: 'sp-kpis' },
    kpi(formatNumber(t.total_tokens), 'Toplam token', `${formatNumber(t.prompt_tokens)} giriş · ${formatNumber(t.completion_tokens)} çıkış`),
    kpi(formatNumber(t.messages), 'Mesaj', `${formatNumber(t.conversations)} sohbet`),
    kpi(formatNumber(t.avg_tokens_per_message), 'Mesaj başına token'),
    kpi(`${(t.avg_latency_ms / 1000).toFixed(1).replace('.', ',')} sn`, 'Ort. yanıt süresi'),
    kpi(`${t.streak_days} gün`, 'Kesintisiz kullanım', `${t.active_days} aktif gün`));

  const cards = [range, kpis];
  const b = s.budget;
  if (b.monthly_token_budget > 0) {
    const cls = b.percent >= 100 ? 'danger' : b.percent >= 80 ? 'warn' : '';
    cards.push(h('div', { class: 'sp-card' },
      h('h3', null, 'Aylık token bütçesi', h('small', null, `%${String(b.percent).replace('.', ',')}`)),
      h('div', { class: 'small muted' }, `${formatNumber(b.month_tokens)} / ${formatNumber(b.monthly_token_budget)} token kullanıldı (bu takvim ayı)`),
      h('div', { class: `sp-progress ${cls}` }, h('div', { style: { width: `${Math.min(100, b.percent)}%` } }))));
  }

  cards.push(h('div', { class: 'sp-card' }, h('h3', null, 'Günlük token kullanımı', h('small', null, `${s.days} gün`)), dailyChart(s.daily, compact)));
  cards.push(h('div', { class: 'sp-grid-2' },
    h('div', { class: 'sp-card' }, h('h3', null, 'Modele göre kullanım'),
      hbars(s.by_model.slice(0, 7), 'model', 'tokens', (i) => `${compact(i.tokens)} tok · ${i.messages}`)),
    h('div', { class: 'sp-card' }, h('h3', null, 'İş türüne göre dağılım'),
      hbars(s.by_task.slice(0, 7).map((x) => ({ ...x, label: TASK_LABELS[x.task_type] || x.task_type })), 'label', 'messages', (i) => `${i.messages} mesaj`))));
  cards.push(h('div', { class: 'sp-card' }, h('h3', null, 'Günün hangi saatlerinde çalışıyorsunuz', h('small', null, 'yerel saat')), hourStrip(s.by_hour)));
  cards.push(h('div', { class: 'sp-note' }, `Bu sistem tamamen yerel çalışır; kullanım ücretsizdir. Karşılaştırma için: aynı hacim ücretli bir bulut API'sinde (varsayım: 1 USD / 1 Mn giriş, 4 USD / 1 Mn çıkış token) yaklaşık ${String(s.cloud_equivalent_usd).replace('.', ',')} USD tutardı.`));
  body.replaceChildren(...cards);
}

export async function renderSectionProfile(body, ctx) {
  const { activeUserId, profile, avatar, avatarColors, setAvatarColors, switchProfile, confirmButton, setStatus, textField, swatches, savePatch, group, groupTitle } = ctx;
  const list = h('div');
  async function renderProfiles() {
    const data = await api('/api/user/profiles');
    if (data.avatar_colors) setAvatarColors(data.avatar_colors);
    list.replaceChildren(...data.profiles.map((p) => h('div', { class: 'sp-list-item' },
      avatar(p, 'sm'),
      h('div', { class: 'sp-list-main' }, h('div', { class: 'sp-list-title' }, p.display_name, p.user_id === activeUserId && h('span', { class: 'sp-tag', style: { marginLeft: '8px' } }, 'Aktif')), h('div', { class: 'sp-list-sub' }, p.role_title || p.user_id)),
      p.user_id !== activeUserId && h('button', { type: 'button', class: 'sp-btn sm', onClick: () => switchProfile(p.user_id) }, 'Geç'),
      p.user_id !== 'default' && confirmButton('Sil', async () => {
        await api(`/api/user/${p.user_id}`, { method: 'DELETE' });
        if (p.user_id === activeUserId) switchProfile('default'); else renderProfiles();
      }))));
  }
  const newName = h('input', { class: 'sp-input', type: 'text', maxlength: 40, placeholder: 'Yeni profil adı (ör. Ayşe, Kalite Birimi)' });
  const addBtn = h('button', {
    type: 'button',
    class: 'sp-btn primary',
    onClick: async () => {
      if (!newName.value.trim()) { setStatus('Lütfen bir profil adı girin.'); return; }
      try {
        const created = await api('/api/user/profiles', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ display_name: newName.value }) });
        switchProfile(created.user_id);
      } catch (err) { setStatus(`Profil oluşturulamadı: ${err.message}`); }
    },
  }, 'Profil oluştur');

  body.replaceChildren(
    h('div', { class: 'sp-inline', style: { marginBottom: '16px' } }, avatar(profile, 'lg'),
      h('div', null, h('div', { style: { fontWeight: 600, fontSize: '16px' } }, profile.display_name), h('div', { class: 'small muted' }, `Profil kimliği: ${profile.user_id}`))),
    h('div', { class: 'sp-grid-2' },
      textField('Görünen ad', profile.display_name, { max: 40, onInput: (v) => savePatch({ display_name: v }) }),
      textField('Unvan / rol', profile.role_title, { max: 60, placeholder: 'ör. Yazılım Geliştirici, Araştırmacı, Öğrenci', onInput: (v) => savePatch({ role_title: v }) })),
    textField('Hakkında', profile.bio, { multiline: true, max: 400, hint: 'Asistan bu bilgiyi sizi daha iyi tanımak için kullanmaz; yalnızca profil kartınızda görünür.', onInput: (v) => savePatch({ bio: v }) }),
    h('div', { class: 'sp-field' }, h('label', null, 'Avatar rengi'), swatches(avatarColors.map((c) => [c, c]), profile.avatar_color, async (c) => { await savePatch({ avatar_color: c }, true); renderSectionProfile(body, ctx); })),
    groupTitle('Profiller'),
    h('div', { class: 'sp-note' }, 'Her profilin kendi sohbet geçmişi, ayarları, hafızası ve istatistikleri vardır. Ortak bilgisayarda herkes kendi alanını kullanabilir.'),
    group(list),
    h('div', { class: 'sp-inline' }, newName, addBtn));
  await renderProfiles();
}

export function renderSectionAppearance(body, ctx) {
  const { profile, ACCENTS, ACCENT_LABELS, savePatch, group, groupTitle, settingRow, swatches, seg, toggleRow } = ctx;
  const s = profile.settings;
  const themeCard = (val, label, cls) => {
    const btn = h('button', { type: 'button', class: `sp-theme-card${s.theme === val ? ' active' : ''}` },
      h('div', { class: `sp-prev ${cls}` }, h('div', { class: 'side' }), h('div', { class: 'main' }, h('i'), h('i'))), h('span', null, label));
    btn.addEventListener('click', () => { savePatch({ settings: { theme: val } }, true); renderSectionAppearance(body, ctx); });
    return btn;
  };
  body.replaceChildren(
    h('div', { class: 'sp-group-title', style: { marginTop: 0 } }, 'Tema'),
    h('div', { class: 'sp-theme-cards', style: { marginBottom: '16px' } }, themeCard('light', 'Açık', 'light'), themeCard('dark', 'Koyu', 'dark'), themeCard('high-contrast', 'Yüksek Kontrast', 'dark'), themeCard('system', 'Sistem', 'auto')),
    group(
      settingRow('Vurgu rengi', 'Düğmeler, bağlantılar ve seçili öğeler', swatches(Object.entries(ACCENTS), s.accent, (k) => savePatch({ settings: { accent: k } }, true), ACCENT_LABELS)),
      settingRow('Yazı boyutu', 'Sohbet ve sayfa metinleri', seg([['small', 'Küçük'], ['medium', 'Orta'], ['large', 'Büyük']], s.font_size, (v) => savePatch({ settings: { font_size: v } }, true))),
      settingRow('Yoğunluk', 'Boşlukları sıkılaştırarak ekrana daha çok içerik sığdırır', seg([['comfortable', 'Rahat'], ['compact', 'Sıkı']], s.density, (v) => savePatch({ settings: { density: v } }, true))),
      toggleRow('Animasyonları azalt', 'Geçiş ve hareket efektlerini kapatır', s.reduce_motion, (v) => savePatch({ settings: { reduce_motion: v } }, true))),
    groupTitle('Sohbet davranışı'),
    group(
      toggleRow('Enter ile gönder', 'Kapalıysa mesaj Ctrl+Enter ile gönderilir, Enter yeni satır ekler', s.send_with_enter, (v) => savePatch({ settings: { send_with_enter: v } }, true)),
      toggleRow('Token ve süre bilgisini göster', 'Her yanıtın altında kullanılan token sayısı ve yanıt süresi', s.show_token_counter, (v) => savePatch({ settings: { show_token_counter: v } }, true)),
      toggleRow('Model rozetini göster', 'Yanıtı üreten modelin adı', s.show_model_badge, (v) => savePatch({ settings: { show_model_badge: v } }, true))));
}

export async function renderSectionAssistant(body, ctx) {
  const { activeUserId, profile, savePatch, flushSave, group, groupTitle, settingRow, seg, textField } = ctx;
  const s = profile.settings;
  const preview = h('pre', { class: 'sp-preview-pre' }, '…');
  let previewTimer = null;
  async function refreshPreview() {
    try { preview.textContent = (await api(`/api/user/${activeUserId}/personalization-preview`)).system_note; } catch { preview.textContent = 'Önizleme alınamadı.'; }
  }
  function patch(p, immediate = false) {
    savePatch({ settings: p }, immediate);
    clearTimeout(previewTimer);
    previewTimer = setTimeout(async () => { await flushSave(); refreshPreview(); }, immediate ? 150 : 650);
  }
  const budget = h('input', { class: 'sp-input', type: 'number', min: 0, step: 10000, style: { width: '170px' } });
  budget.value = s.monthly_token_budget || 0;
  budget.addEventListener('input', () => patch({ monthly_token_budget: Math.max(0, parseInt(budget.value || '0', 10) || 0) }));

  body.replaceChildren(
    h('div', { class: 'sp-note' }, 'Bu tercihler asistanın her yanıtına gizli bir yönerge olarak eklenir. Yanıt biçimini ve dilini size göre ayarlar.'),
    group(
      settingRow('Yanıt uzunluğu', null, seg([['concise', 'Kısa'], ['balanced', 'Dengeli'], ['detailed', 'Ayrıntılı']], s.response_style, (v) => patch({ response_style: v }, true))),
      settingRow('Üslup', null, seg([['professional', 'Profesyonel'], ['friendly', 'Samimi'], ['technical', 'Teknik']], s.tone, (v) => patch({ tone: v }, true))),
      settingRow('Deneyim seviyesi', 'Açıklamaların derinliğini belirler', seg([['beginner', 'Başlangıç'], ['intermediate', 'Orta'], ['expert', 'Uzman']], s.expertise_level, (v) => patch({ expertise_level: v }, true)))),
    textField('İlgi alanları ve çalışma bağlamı', s.interests, { max: 400, placeholder: 'ör. Yazılım geliştirme, veri analizi, akademik araştırma, tasarım', hint: 'Asistan örnekleri ve önerileri bu alanlara göre seçer.', onInput: (v) => patch({ interests: v }) }),
    textField('Özel talimatlar', s.custom_instructions, { multiline: true, max: 1500, placeholder: 'ör. Ölçüleri her zaman mm cinsinden ver. Tabloları tercih et. Önce kısa özet, sonra detay.', hint: 'Her yeni sohbette geçerli olan kalıcı kurallarınız.', onInput: (v) => patch({ custom_instructions: v }) }),
    groupTitle('Kullanım bütçesi'),
    group(settingRow('Aylık token bütçesi', '0 = sınırsız. Aşıldığında istatistik sayfasında uyarı gösterilir; kullanım engellenmez.', budget)),
    groupTitle('Asistana giden kişiselleştirme notu'),
    preview);
  refreshPreview();
}
