/**
 * UX-20 & UX-21: HTML/SVG sanitizer (allowlist, DOM based) and zero-emoji UI policy helpers.
 *
 * The input is parsed by the browser's own HTML parser and every node is rebuilt from an allowlist of
 * tags and attributes, so malformed markup (`<img/onerror=...>`, split tags, entity-encoded URLs) cannot
 * slip past the way it does with regex blacklists. URLs are checked after the parser has decoded them.
 */

const HTML_TAGS = new Set([
  'a', 'abbr', 'b', 'blockquote', 'br', 'caption', 'code', 'dd', 'del', 'details', 'div', 'dl', 'dt', 'em',
  'figcaption', 'figure', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'kbd', 'li', 'mark', 'ol',
  'p', 'pre', 'q', 's', 'small', 'span', 'strong', 'sub', 'summary', 'sup', 'table', 'tbody', 'td', 'tfoot',
  'th', 'thead', 'tr', 'u', 'ul', 'button', 'label', 'select', 'option', 'textarea', 'input',
]);
const ALLOWED_SVG_TAGS = new Set([
  'svg', 'g', 'path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon',
  'text', 'tspan', 'defs', 'lineargradient', 'radialgradient', 'stop', 'title', 'desc', 'metadata',
  'marker', 'clippath', 'mask', 'pattern', 'symbol',
]);
// `input`/`textarea`/`select` are kept for generated forms but never keep a script-capable attribute.
const GLOBAL_ATTRS = new Set([
  'class', 'id', 'title', 'role', 'lang', 'dir', 'tabindex', 'type', 'name', 'value', 'placeholder', 'disabled',
  'checked', 'open', 'colspan', 'rowspan', 'width', 'height', 'alt', 'target', 'rel', 'for', 'rows', 'cols',
  'min', 'max', 'step', 'readonly', 'required', 'selected',
]);
const SVG_ATTRS = new Set([
  'viewbox', 'xmlns', 'd', 'x', 'y', 'x1', 'y1', 'x2', 'y2', 'cx', 'cy', 'r', 'rx', 'ry', 'points', 'fill',
  'stroke', 'stroke-width', 'stroke-linecap', 'stroke-linejoin', 'stroke-dasharray', 'opacity', 'fill-opacity',
  'stroke-opacity', 'transform', 'font-size', 'font-family', 'font-weight', 'text-anchor', 'dominant-baseline',
  'offset', 'stop-color', 'stop-opacity', 'gradientunits', 'gradienttransform', 'preserveaspectratio',
  'marker-end', 'marker-start', 'marker-mid', 'markerwidth', 'markerheight', 'refx', 'refy', 'orient',
  'dx', 'dy', 'clip-path', 'mask', 'patternunits', 'xml:space', 'fill-rule', 'clip-rule', 'letter-spacing',
]);
const URL_ATTRS = new Set(['href', 'src', 'xlink:href']);
const SAFE_URL_RE = /^(?:https?:|mailto:|tel:|#|\/(?!\/)|\.{0,2}\/|[^:/?#]*(?:[/?#]|$))/i;
const SAFE_DATA_IMAGE_RE = /^data:image\/(?:png|jpe?g|gif|webp);base64,[a-z0-9+/=\s]+$/i;
const EMOJI_RANGE_RE = /[\u{1F300}-\u{1F9FF}\u{2600}-\u{27BF}\u{1FA70}-\u{1FAFF}]/gu;

function isSafeUrl(value, attr) {
  // Control characters and whitespace inside the scheme are ignored by browsers, so strip them first.
  const v = String(value).replace(/[\u0000- \u007f-\u009f]+/g, '');
  if (v === '') return true;
  if (attr === 'src' && SAFE_DATA_IMAGE_RE.test(v)) return true;
  if (/^data:/i.test(v)) return false;
  return SAFE_URL_RE.test(v);
}

function cleanStyle(value) {
  return String(value)
    .split(';')
    .filter((decl) => decl.trim() && !/url\s*\(|expression|javascript|behavior|@import|-moz-binding/i.test(decl))
    .join(';');
}

function cleanElement(el) {
  for (const attr of Array.from(el.attributes)) {
    const name = attr.name.toLowerCase();
    const value = attr.value;
    let keep = false;
    if (name === 'style') {
      const css = cleanStyle(value);
      if (css) el.setAttribute('style', css);
      else el.removeAttribute('style');
      continue;
    }
    if (URL_ATTRS.has(name)) keep = isSafeUrl(value, name);
    else if (name.startsWith('aria-') || name.startsWith('data-')) keep = /^[a-z0-9_.:-]+$/.test(name);
    else if (name.startsWith('on')) keep = false;
    else keep = GLOBAL_ATTRS.has(name) || SVG_ATTRS.has(name);
    if (!keep) el.removeAttribute(attr.name);
  }
  if (el.tagName.toLowerCase() === 'a' && el.getAttribute('target') === '_blank') {
    el.setAttribute('rel', 'noopener noreferrer');
  }
}

function cleanChildren(parent) {
  for (const node of Array.from(parent.childNodes)) {
    if (node.nodeType === 3) continue; // text
    if (node.nodeType !== 1) {
      node.remove(); // comments, processing instructions, CDATA
      continue;
    }
    const tag = node.localName.toLowerCase();
    const inSvg = node.namespaceURI === 'http://www.w3.org/2000/svg';
    const allowed = inSvg ? ALLOWED_SVG_TAGS.has(tag) : HTML_TAGS.has(tag);
    if (!allowed) {
      node.remove(); // drop the element together with its content (script, style, iframe, math, ...)
      continue;
    }
    cleanElement(node);
    cleanChildren(node);
  }
}

function parseClean(input) {
  const doc = new DOMParser().parseFromString(`<!doctype html><body>${String(input ?? '')}`, 'text/html');
  cleanChildren(doc.body);
  return doc.body;
}

/** Returns sanitized markup as a string. */
export function sanitizeHtmlOrSvg(input) {
  if (typeof DOMParser === 'undefined') {
    // No DOM available (non-browser runtime): fail closed by escaping everything.
    return String(input ?? '').replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
  }
  return parseClean(input).innerHTML;
}

export function sanitizeSvgStrict(svgText) {
  return sanitizeHtmlOrSvg(svgText);
}

export function containsUiEmoji(text) {
  EMOJI_RANGE_RE.lastIndex = 0;
  return EMOJI_RANGE_RE.test(String(text || ''));
}

export function stripUiEmojis(text) {
  return String(text || '').replace(EMOJI_RANGE_RE, '');
}

export function setSanitizedHtml(el, html) {
  if (!el) return;
  if (typeof DOMParser === 'undefined') {
    el.textContent = String(html ?? '');
    return;
  }
  el.replaceChildren(...parseClean(html).childNodes);
}

export function appendSanitizedHtml(el, html) {
  if (!el) return;
  if (typeof DOMParser === 'undefined') {
    el.append(String(html ?? ''));
    return;
  }
  el.append(...parseClean(html).childNodes);
}
