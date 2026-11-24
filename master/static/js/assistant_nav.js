// Pages that are not in the sidebar but open from the assistant when the user asks for them.
const PAGES = [
  { hash: '#/cnc', label: 'CNC Balonlama', re: /\bcnc\b|balonlama|ballooning/ },
  { hash: '#/studio', label: 'Kod Stüdyosu', dock: true, re: /kod\s*st[üu]dyo|\bide\b|code\s*studio/ },
  { hash: '#/studios', label: 'Stüdyolar', re: /st[üu]dyolar|studios/ },
  { hash: '#/artifacts', label: 'Artefaktlar', re: /artefakt|artifact/ },
  { hash: '#/files', label: 'Dosyalar ve Bilgi Bankası', re: /dosyalar|bilgi\s*bankas|files/ },
];
const OPEN_RE = /(?<![\p{L}])(a[çc]|a[çc]ar m[ıi]s[ıi]n|git|g[öo]ster|g[öo]t[üu]r|open|show)(?![\p{L}])|sayfas[ıi]/u;

/** Returns the page when a short message asks to open one of the hidden pages; otherwise null. */
export function matchPageRequest(prompt) {
  const text = String(prompt || '').toLocaleLowerCase('tr-TR').trim();
  if (!text || text.length > 40 || !OPEN_RE.test(text)) return null;
  return PAGES.find((p) => p.re.test(text)) || null;
}

export function pageLinkMessage(page) {
  if (page.dock) return `**${page.label}** sağ tarafta açıldı. Tam sayfa için: [tam sayfada aç](${page.hash})`;
  return `**${page.label}** sayfasını açabilirsin: [${page.label} sayfasına git](${page.hash})`;
}

export const HIDDEN_PAGES = PAGES;
