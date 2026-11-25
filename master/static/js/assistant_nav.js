// Pages that are not in the sidebar but open from the assistant when the user asks for them.
const PAGES = [
  { key: 'cnc', hash: '#/cnc', label: 'CNC Balonlama', re: /\bcnc\b|balonlama|ballooning/ },
  { key: 'studio', hash: '#/studio', label: 'Kod Stüdyosu', re: /kod\s*st[üu]dyo|\bide\b|code\s*studio/ },
  { key: 'studios', hash: '#/studios', label: 'Stüdyolar', re: /st[üu]dyolar|studios/ },
  { key: 'artifacts', hash: '#/artifacts', label: 'Artefaktlar', re: /artefakt|artifact/ },
  { key: 'files', hash: '#/files', label: 'Dosyalar ve Bilgi Bankası', re: /dosyalar|bilgi\s*bankas|files/ },
];
const OPEN_RE = /(?<![\p{L}])(a[çc]|a[çc]ar m[ıi]s[ıi]n|git|g[öo]ster|g[öo]t[üu]r|open|show)(?![\p{L}])|sayfas[ıi]/u;

/** Returns the page when a short message asks to open one of the hidden pages; otherwise null. */
export function matchPageRequest(prompt) {
  const text = String(prompt || '').toLocaleLowerCase('tr-TR').trim();
  if (!text || text.length > 40 || !OPEN_RE.test(text)) return null;
  return PAGES.find((p) => p.re.test(text)) || null;
}

export function pageLinkMessage(page) {
  return `**${page.label}** sağ tarafta açıldı. Tam sayfa için: [tam sayfada aç](${page.hash})`;
}

export const HIDDEN_PAGES = PAGES;
