/**
 * UX-06 & EPK-27: 5-Language Localization Dictionary (TR, EN, DE, FR, AR + RTL) & Intl Formatters.
 */

export const SUPPORTED_LANGS = ['tr', 'en', 'de', 'fr', 'ar'];
export const RTL_LANGS = new Set(['ar']);

const LOCALE_MAP = { tr: 'tr-TR', en: 'en-US', de: 'de-DE', fr: 'fr-FR', ar: 'ar-SA' };

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
  de: {
    'nav.new_project': 'Neues Projekt',
    'nav.projects': 'Projekte',
    'nav.agents': 'Agenten',
    'nav.dashboard': 'Übersicht',
    'nav.assistant': 'Assistent',
    'chat.placeholder': 'Nachricht eingeben oder /sunum, /araştır, /kod nutzen...',
    'chat.regenerate': 'Neu generieren',
    'chat.edit_branch': 'Bearbeiten & Verzweigen',
    'chat.share': 'Teilen',
    'chat.export': 'Exportieren',
    'chat.report_wrong': 'Fehler melden',
    'status.verified': 'Verifiziert',
    'status.unverified': 'Nicht verifiziert',
    'status.offline': 'Offline',
    'status.online': 'Online',
    'wizard.title': 'System-Gesundheitsassistent',
    'palette.placeholder': 'Befehle, Chats oder Einstellungen suchen (Ctrl+K)...',
    'settings.title': 'Einstellungen',
    'slo.title': 'Qualitäts- und Leistungskennzahlen',
  },
  fr: {
    'nav.new_project': 'Nouveau Projet',
    'nav.projects': 'Projets',
    'nav.agents': 'Agents',
    'nav.dashboard': 'Tableau de bord',
    'nav.assistant': 'Assistant',
    'chat.placeholder': 'Écrivez un message ou utilisez /sunum, /araştır, /kod...',
    'chat.regenerate': 'Régénérer',
    'chat.edit_branch': 'Modifier et bifurquer',
    'chat.share': 'Partager',
    'chat.export': 'Exporter',
    'chat.report_wrong': 'Signaler une erreur',
    'status.verified': 'Vérifié',
    'status.unverified': 'Non vérifié',
    'status.offline': 'Hors ligne',
    'status.online': 'En ligne',
    'wizard.title': 'Assistant de santé système',
    'palette.placeholder': 'Rechercher commandes, discussions ou paramètres (Ctrl+K)...',
    'settings.title': 'Paramètres',
    'slo.title': 'Indicateurs de qualité et de performance',
  },
  ar: {
    'nav.new_project': 'مشروع جديد',
    'nav.projects': 'المشاريع',
    'nav.agents': 'الوكلاء',
    'nav.dashboard': 'لوحة التحكم',
    'nav.assistant': 'المساعد',
    'chat.placeholder': 'اكتب رسالتك أو استخدم /sunum أو /kod...',
    'chat.regenerate': 'إعادة التوليد',
    'chat.edit_branch': 'تعديل وتفريع',
    'chat.share': 'مشاركة',
    'chat.export': 'تصدير',
    'chat.report_wrong': 'الإبلاغ عن خطأ',
    'status.verified': 'تم التحقق',
    'status.unverified': 'غير متحقق',
    'status.offline': 'غير متصل',
    'status.online': 'متصل',
    'wizard.title': 'معالج صحة النظام',
    'palette.placeholder': 'ابحث في الأوامر أو المحادثات أو الإعدادات (Ctrl+K)...',
    'settings.title': 'الإعدادات',
    'slo.title': 'مؤشرات الجودة والأداء',
  },
};

export function getTextDirection(lang = 'tr') {
  return RTL_LANGS.has(lang) ? 'rtl' : 'ltr';
}

export function translate(key, lang = 'tr') {
  const table = MESSAGES[lang] || MESSAGES.tr;
  return table[key] || MESSAGES.tr[key] || key;
}

export function formatNumber(value, lang = 'tr') {
  return new Intl.NumberFormat(LOCALE_MAP[lang] || 'tr-TR').format(value);
}

export function formatDate(isoDate, lang = 'tr') {
  return new Intl.DateTimeFormat(LOCALE_MAP[lang] || 'tr-TR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(isoDate));
}
