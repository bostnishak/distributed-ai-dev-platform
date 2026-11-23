/**
 * UX-06: TR/EN Localization Dictionary & Intl Number/Date Formatters (zero missing keys).
 */

export const MESSAGES = {
  tr: {
    'nav.new_project': 'Yeni Proje',
    'nav.projects': 'Projeler',
    'nav.agents': 'Ajanlar',
    'nav.dashboard': 'Pano',
    'nav.assistant': 'Asistan',
    'chat.placeholder': 'Mesajını yaz veya /sunum, /araştır, /kod kullan...',
    'chat.regenerate': 'Yeniden Üret',
    'chat.edit_branch': 'Düzenle ve Dallandır',
    'chat.share': 'Paylaş',
    'chat.export': 'Dışa Aktar',
    'chat.report_wrong': 'Yanlış Bilgi Bildir',
    'status.verified': 'Doğrulandı',
    'status.unverified': 'Doğrulanamadı',
    'status.offline': 'Çevrimdışı',
    'status.online': 'Çevrimiçi',
    'wizard.title': 'Sistem Sağlık Sihirbazı',
    'palette.placeholder': 'Komut, sohbet veya ayar ara (Ctrl+K)...',
    'settings.title': 'Ayarlar',
    'slo.title': 'Kalite ve Performans Göstergeleri',
  },
  en: {
    'nav.new_project': 'New Project',
    'nav.projects': 'Projects',
    'nav.agents': 'Agents',
    'nav.dashboard': 'Dashboard',
    'nav.assistant': 'Assistant',
    'chat.placeholder': 'Type a message or use /sunum, /araştır, /kod...',
    'chat.regenerate': 'Regenerate',
    'chat.edit_branch': 'Edit & Branch',
    'chat.share': 'Share',
    'chat.export': 'Export',
    'chat.report_wrong': 'Report Incorrect Info',
    'status.verified': 'Verified',
    'status.unverified': 'Unverified',
    'status.offline': 'Offline',
    'status.online': 'Online',
    'wizard.title': 'System Health Wizard',
    'palette.placeholder': 'Search commands, chats, or settings (Ctrl+K)...',
    'settings.title': 'Settings',
    'slo.title': 'Quality & Performance Indicators',
  },
};

export function translate(key, lang = 'tr') {
  const table = MESSAGES[lang] || MESSAGES.tr;
  return table[key] || MESSAGES.tr[key] || key;
}

export function formatNumber(value, lang = 'tr') {
  return new Intl.NumberFormat(lang === 'en' ? 'en-US' : 'tr-TR').format(value);
}

export function formatDate(isoDate, lang = 'tr') {
  return new Intl.DateTimeFormat(lang === 'en' ? 'en-US' : 'tr-TR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(isoDate));
}
