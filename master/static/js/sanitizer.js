/**
 * UX-20 & UX-21: Offline HTML/SVG XSS Sanitizer & Zero-Emoji UI Policy Checker.
 * Strips scripts, event handlers (on*), javascript:/data:text/html URIs, and disallowed tags.
 */

const ALLOWED_SVG_TAGS = new Set([
  'svg', 'g', 'path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon',
  'text', 'tspan', 'defs', 'lineargradient', 'radialgradient', 'stop', 'title', 'desc', 'metadata',
]);

const FORBIDDEN_TAGS_RE = /<\s*(script|iframe|object|embed|foreignobject|link|meta|base|form|input|style)\b[^>]*>[\s\S]*?<\/\s*\1\s*>|<\s*(script|iframe|object|embed|foreignobject|link|meta|base|input)\b[^>]*\/?>/gi;
const EVENT_ATTR_RE = /\s+on[a-z]+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)/gi;
const JS_URI_RE = /(href|xlink:href|src|action)\s*=\s*(?:"\s*(?:javascript|vbscript|data:text\/html)[^"]*"|'\s*(?:javascript|vbscript|data:text\/html)[^']*')/gi;
const EMOJI_RANGE_RE = /[\u{1F300}-\u{1F9FF}\u{2600}-\u{27BF}\u{1FA70}-\u{1FAFF}]/gu;

export function sanitizeHtmlOrSvg(input) {
  let out = String(input || '');
  out = out.replace(FORBIDDEN_TAGS_RE, '');
  out = out.replace(EVENT_ATTR_RE, '');
  out = out.replace(JS_URI_RE, '');
  out = out.replace(/javascript\s*:/gi, '');
  return out;
}

export function sanitizeSvgStrict(svgText) {
  const cleaned = sanitizeHtmlOrSvg(svgText);
  return cleaned.replace(/<\/?([a-zA-Z0-9:-]+)([^>]*)>/g, (match, tag) => {
    const lower = String(tag).toLowerCase();
    return ALLOWED_SVG_TAGS.has(lower) ? match : '';
  });
}

export function containsUiEmoji(text) {
  return EMOJI_RANGE_RE.test(String(text || ''));
}

export function stripUiEmojis(text) {
  return String(text || '').replace(EMOJI_RANGE_RE, '');
}
