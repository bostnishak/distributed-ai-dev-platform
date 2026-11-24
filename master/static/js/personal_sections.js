// UX-02 Modular Split: Personal Space Memory, Data/Privacy & MCP Connector sections (<= 500 lines).
import { uiPrompt } from './ui_dialog.js';
import { api, formatDateTime, h } from './util.js';

async function loadMemoryFacts(factsBox, ctx) {
  const { activeUserId, setStatus, setMemoryCount, renderCard } = ctx;
  const { memories } = await api(`/api/user/${activeUserId}/memories`);
  setMemoryCount(memories.length);
  renderCard();
  factsBox.replaceChildren(...(memories.length ? memories.map((m) => h('div', { class: 'sp-list-item' },
    h('div', { class: 'sp-list-main' }, h('div', { class: 'sp-list-title' }, h('span', { class: 'sp-tag' }, m.category), m.fact_value), h('div', { class: 'sp-list-sub' }, formatDateTime(m.updated_at))),
    h('button', {
      type: 'button', class: 'sp-btn danger sm',
      onClick: async () => {
        try { await api(`/api/user/${activeUserId}/memories/${m.id}`, { method: 'DELETE' }); setStatus('Bilgi unutuldu', true); loadMemoryFacts(factsBox, ctx); }
        catch (err) { setStatus(`Silinemedi: ${err.message}`); }
      },
    }, 'Unut'))) : [h('div', { class: 'sp-empty' }, 'Henüz öğrenilmiş bilgi yok. Sohbet ettikçe tercihleriniz burada birikir.')]));
}

export async function renderSectionMemory(body, ctx) {
  const { activeUserId, profile, setStatus, closePanel, group, groupTitle, toggleRow, savePatch } = ctx;
  const s = profile.settings;
  const factsBox = h('div');
  const convBox = h('div');
  const searchOut = h('div');
  const renderConvs = async () => {
    const { conversations } = await api(`/api/user/${activeUserId}/conversations`);
    convBox.replaceChildren(...(conversations.length ? conversations.slice(0, 12).map((c) => h('div', {
      class: 'sp-list-item', style: { cursor: 'pointer' }, title: 'Bu sohbeti aç',
      onClick: () => { closePanel(); document.dispatchEvent(new CustomEvent('open-saved-chat', { detail: { chatId: c.id } })); },
    }, h('div', { class: 'sp-list-main' }, h('div', { class: 'sp-list-title' }, c.title), h('div', { class: 'sp-list-sub' }, `${c.message_count} mesaj · ${formatDateTime(c.updated_at)}`)))) : [h('div', { class: 'sp-empty' }, 'Kayıtlı sohbet yok.')]));
  };
  const addInput = h('input', { class: 'sp-input', type: 'text', maxlength: 300, placeholder: 'Asistanın hatırlamasını istediğiniz bilgi' });
  const addBtn = h('button', {
    type: 'button', class: 'sp-btn primary',
    onClick: async () => {
      if (!addInput.value.trim()) { setStatus('Hatırlanacak bilgi boş olamaz.'); return; }
      try {
        await api(`/api/user/${activeUserId}/memories`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ category: 'preference', fact_value: addInput.value }) });
        addInput.value = ''; setStatus('Hafızaya kaydedildi', true); loadMemoryFacts(factsBox, ctx);
      } catch (err) { setStatus(`Kaydedilemedi: ${err.message}`); }
    },
  }, 'Hatırla');
  const searchInput = h('input', { class: 'sp-input', type: 'text', placeholder: 'Geçmiş sohbetlerde ara' });
  let searchTimer = null;
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(async () => {
      if (!searchInput.value.trim()) { searchOut.replaceChildren(); return; }
      try {
        const { results } = await api(`/api/user/${activeUserId}/history/search?q=${encodeURIComponent(searchInput.value)}`);
        searchOut.replaceChildren(...(results.length ? results.map((r) => h('div', {
          class: 'sp-list-item', style: { cursor: 'pointer' }, title: 'Bu sohbeti aç',
          onClick: () => { closePanel(); document.dispatchEvent(new CustomEvent('open-saved-chat', { detail: { chatId: r.conversation_id } })); },
        }, h('div', { class: 'sp-list-main' }, h('div', { class: 'sp-list-title' }, r.title), h('div', { class: 'sp-list-sub' }, `${r.role === 'user' ? 'Siz' : 'Asistan'}: ${r.snippet}`)))) : [h('div', { class: 'sp-empty' }, 'Eşleşen kayıt bulunamadı.')]));
      } catch (err) { searchOut.replaceChildren(h('div', { class: 'sp-empty' }, `Arama hatası: ${err.message}`)); }
    }, 350);
  });
  body.replaceChildren(
    group(
      toggleRow('Diğer sohbetlerden bilgi al', 'İlgili eski sohbetleriniz taranıp bağlama eklenir.', s.cross_chat_memory, (v) => savePatch({ settings: { cross_chat_memory: v } }, true)),
      toggleRow('Tercihleri otomatik öğren', 'Mesajlarınızdan kalıcı tercihler çıkarılır.', s.auto_learn_facts, (v) => savePatch({ settings: { auto_learn_facts: v } }, true))),
    groupTitle('Öğrenilen bilgiler'), group(factsBox),
    h('div', { class: 'sp-inline', style: { marginBottom: '8px' } }, addInput, addBtn),
    groupTitle('Sohbet geçmişinde ara'), searchInput, searchOut, groupTitle('Son sohbetler'), group(convBox));
  addInput.style.flex = '1';
  await Promise.all([loadMemoryFacts(factsBox, ctx), renderConvs()]);
}

export function renderSectionData(body, ctx) {
  const { activeUserId, profile, setStatus, resetCounters, renderCard, group, groupTitle, settingRow, seg, savePatch, confirmButton } = ctx;
  const s = profile.settings;
  const auditBox = h('div', { class: 'sp-note', style: { marginTop: '8px' } }, 'AS9100 SHA-256 denetim izi doğrulanmadı.');
  const verifyAuditBtn = h('button', {
    type: 'button',
    class: 'sp-btn sm',
    onClick: async () => {
      try {
        const res = await api('/api/admin/audit/verify');
        auditBox.textContent = res.valid
          ? `Denetim zinciri doğrulandı (${res.total_entries} kayıt, bütünlük sağlam).`
          : `UYARI: Zincir bozuk! Satır ${res.corrupted_line}: ${res.reason}`;
        setStatus(res.valid ? 'Denetim izi sağlam' : 'Denetim izi bozuk!', Boolean(res.valid));
      } catch (err) { auditBox.textContent = `Doğrulama hatası: ${err.message}`; }
    },
  }, 'Zinciri Doğrula');

  const encBackupBtn = h('button', {
    type: 'button',
    class: 'sp-btn',
    onClick: async () => {
      const pwd = await uiPrompt('Şifreli AES-256 yedek için parola belirleyin (boş bırakırsanız yerel anahtar kullanılır):', '', 'Şifreli Yedek');
      if (pwd === null) return;
      const q = pwd.trim() ? `?password=${encodeURIComponent(pwd.trim())}` : '';
      window.location.href = `/api/admin/backup.zip${q}`;
    },
  }, 'Şifreli Yedek (.ZIP)');

  const wipe = (scope, label, desc) => settingRow(label, desc, confirmButton('Sil', async () => {
    await api(`/api/user/${activeUserId}/data?scope=${scope}`, { method: 'DELETE' });
    resetCounters(scope);
    renderCard();
    if (scope === 'conversations' || scope === 'all') document.dispatchEvent(new CustomEvent('chats-wiped'));
    setStatus('Silindi (WAL + VACUUM temizlendi)', true);
  }));
  body.replaceChildren(
    h('div', { class: 'sp-note' }, 'Tüm veriler yalnızca bu bilgisayardaki sunucuda tutulur; gizli anahtarlar Fernet ile şifrelenir ve yedeklere dahil edilmez.'),
    group(
      settingRow('Otomatik saklama süresi', 'Sohbet ve kullanım kayıtlarının saklanacağı gün sayısı (0 = sınırsız)',
        seg([[0, 'Sınırsız'], [7, '7 gün'], [30, '30 gün'], [90, '90 gün']], Number(s.retention_days || 0), (v) => savePatch({ settings: { retention_days: Number(v) } }, true))),
      settingRow('Verilerimi dışa aktar', 'Profil, ayarlar, öğrenilen bilgiler, istatistikler ve sohbetler JSON olarak iner (gizli anahtarlar hariç).',
        h('a', { class: 'sp-btn primary', href: `/api/user/${activeUserId}/export`, download: '' }, 'JSON indir')),
      settingRow('Şifreli sistem yedeği (AES-256 ZIP)', 'Parola korumalı ve SHA-256 manifestli tam veri yedeği indirir (secrets.db hariç).', encBackupBtn),
      settingRow('AS9100 Denetim İzi Bütünlüğü', 'Tüm güvenlik olaylarının SHA-256 özet zincirini doğrular.', verifyAuditBtn)),
    auditBox,
    groupTitle('Verileri sil (Kalıcı VACUUM + WAL temizliği)'),
    group(
      wipe('usage', 'Kullanım istatistikleri', 'Token ve yanıt süresi kayıtlarını kalıcı olarak siler.'),
      wipe('memories', 'Öğrenilen bilgiler', 'Asistanın sizin hakkınızda öğrendiği her şeyi kalıcı olarak siler.'),
      wipe('conversations', 'Sunucudaki sohbet kayıtları', 'Sohbetler, FTS dizini ve ilgili medya dosyalarını kalıcı olarak siler.'),
      wipe('all', 'Hepsi', 'Yukarıdakilerin tamamını fiziksel olarak temizler. Profil ve ayarlar kalır.')));
}

export async function renderSectionMcp(body, ctx) {
  const { setStatus, group, groupTitle, confirmButton } = ctx;
  const listBox = h('div');
  const outPre = h('pre', { class: 'sp-preview-pre', hidden: true });

  async function renderConnectors() {
    const { connectors } = await api('/api/mcp/connectors');
    if (!connectors.length) {
      listBox.replaceChildren(h('div', { class: 'sp-empty' }, 'Henüz harici MCP bağlayıcısı eklenmedi. Yukarıdaki formdan herhangi bir MCP sunucu URL\'si ve API anahtarı ile bağlanabilirsiniz.'));
      return;
    }
    listBox.replaceChildren(...connectors.map((c) => {
      const toolsRow = c.tools && c.tools.length
        ? h('div', { style: { marginTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '6px' } },
          ...c.tools.map((t) => h('button', {
            type: 'button',
            class: 'sp-btn sm',
            title: t.description || t.name,
            onClick: async () => {
              const rawArgs = await uiPrompt(`"${t.name}" aracı için JSON argümanları (boş bırakabilirsiniz):`, '{}', 'MCP Araç Argümanı');
              if (rawArgs === null) return;
              let parsed = {};
              try { parsed = rawArgs.trim() ? JSON.parse(rawArgs) : {}; } catch { setStatus('Geçersiz JSON argümanı.'); return; }
              setStatus(`${t.name} çalıştırılıyor...`);
              try {
                const res = await api(`/api/mcp/connectors/${c.id}/call`, {
                  method: 'POST', headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ tool_name: t.name, arguments: parsed }),
                });
                outPre.hidden = false;
                outPre.textContent = JSON.stringify(res, null, 2);
                setStatus(`${t.name} tamamlandı`, true);
              } catch (err) {
                outPre.hidden = false;
                outPre.textContent = String(err.message);
                setStatus('MCP çağrısı başarısız');
              }
            },
          }, `Çalıştır: ${t.name}`)))
        : null;

      return h('div', { class: 'sp-list-item', style: { flexDirection: 'column', alignItems: 'stretch' } },
        h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'space-between', flexWrap: 'wrap' } },
          h('div', { class: 'sp-list-main' },
            h('div', { class: 'sp-list-title' }, c.name, h('span', { class: 'sp-tag', style: { marginLeft: '8px' } }, c.enabled ? 'Aktif' : 'Pasif')),
            h('div', { class: 'sp-list-sub' }, `${c.url} · ${c.last_status}${c.has_api_key ? ` · Anahtar: ${c.api_key_masked}` : ''}`)),
          h('div', { class: 'sp-inline' },
            h('button', {
              type: 'button', class: 'sp-btn sm primary',
              onClick: async () => {
                setStatus(`${c.name} keşfediliyor...`);
                const res = await api(`/api/mcp/connectors/${c.id}/discover`, { method: 'POST' });
                setStatus(res.ok ? 'Araçlar keşfedildi' : (res.error || 'Bağlantı hatası'), Boolean(res.ok));
                renderConnectors();
              },
            }, 'Araçları Keşfet'),
            h('button', {
              type: 'button', class: 'sp-btn sm',
              onClick: async () => {
                await api(`/api/mcp/connectors/${c.id}`, {
                  method: 'PUT', headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ enabled: !c.enabled }),
                });
                renderConnectors();
              },
            }, c.enabled ? 'Pasifleştir' : 'Aktifleştir'),
            confirmButton('Sil', async () => {
              await api(`/api/mcp/connectors/${c.id}`, { method: 'DELETE' });
              renderConnectors();
            }))),
        toolsRow);
    }));
  }

  const nameIn = h('input', { class: 'sp-input', type: 'text', placeholder: 'Bağlayıcı adı (ör. GitHub MCP, Notion, Özel API)' });
  const urlIn = h('input', { class: 'sp-input', type: 'url', placeholder: 'MCP Sunucu URL (ör. mcp.example.local/mcp)' });
  const keyIn = h('input', { class: 'sp-input', type: 'password', placeholder: 'MCP Connector API Key / Bearer Token (opsiyonel)' });
  const hdrIn = h('input', { class: 'sp-input', type: 'text', value: 'Authorization', placeholder: 'Başlık (Authorization veya X-API-Key)' });
  const addBtn = h('button', {
    type: 'button',
    class: 'sp-btn primary',
    onClick: async () => {
      if (!nameIn.value.trim() || !urlIn.value.trim()) { setStatus('Ad ve geçerli URL zorunludur.'); return; }
      const hdr = hdrIn.value.trim() || 'Authorization';
      const prefix = hdr.toLowerCase() === 'authorization' ? 'Bearer ' : '';
      try {
        await api('/api/mcp/connectors', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: nameIn.value, url: urlIn.value, api_key: keyIn.value, auth_header: hdr, auth_prefix: prefix }),
        });
        nameIn.value = ''; urlIn.value = ''; keyIn.value = '';
        setStatus('MCP bağlayıcısı eklendi', true);
        renderConnectors();
      } catch (err) { setStatus(err.message); }
    },
  }, 'MCP Bağlayıcı Ekle');

  body.replaceChildren(
    h('div', { class: 'sp-note' }, 'Dışarıdaki herhangi bir MCP (Model Context Protocol) sunucusuna URL ve API anahtarı ile bağlanın. Keşfedilen araçları buradan veya doğrudan sohbet ekranından çalıştırabilirsiniz.'),
    h('div', { class: 'sp-grid-2' },
      h('div', { class: 'sp-field' }, h('label', null, 'Bağlayıcı Adı'), nameIn),
      h('div', { class: 'sp-field' }, h('label', null, 'MCP Sunucu URL'), urlIn)),
    h('div', { class: 'sp-grid-2' },
      h('div', { class: 'sp-field' }, h('label', null, 'API Anahtarı / Connector Key'), keyIn),
      h('div', { class: 'sp-field' }, h('label', null, 'Yetki Başlığı'), hdrIn)),
    h('div', { class: 'sp-inline', style: { marginBottom: '14px' } }, addBtn),
    groupTitle('Kayıtlı MCP Bağlayıcıları'),
    group(listBox),
    outPre);
  await renderConnectors();
}
