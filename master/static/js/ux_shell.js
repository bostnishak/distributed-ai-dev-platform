/**
 * UX-05, 09, 10, 13, 14, 17, 27: Accessible Command Palette, Slash Commands, Citations/Confidence, Health Wizard & Feedback.
 */

import { sanitizeHtmlOrSvg } from './sanitizer.js';
import { translate } from './i18n.js';

export const SLASH_COMMAND_MAP = Object.freeze({
  '/sunum': { intent: 'presentation', mode: 'presentation' },
  '/araştır': { intent: 'research', mode: 'research' },
  '/kod': { intent: 'code_only', mode: 'code_only' },
  '/özet': { intent: 'summarize', mode: 'short' },
});

export function parseSlashAndMentions(text) {
  const trimmed = String(text || '').trim();
  let matchedSlash = null;
  let body = trimmed;
  for (const [cmd, meta] of Object.entries(SLASH_COMMAND_MAP)) {
    if (trimmed.toLowerCase().startsWith(cmd)) {
      matchedSlash = { command: cmd, ...meta };
      body = trimmed.slice(cmd.length).trim();
      break;
    }
  }
  const mentions = Array.from(trimmed.matchAll(/@(dosya|bilgi|web)\b/gi)).map((m) => m[1].toLowerCase());
  return { slash: matchedSlash, mentions, cleanPrompt: body };
}

export function renderConfidenceBadgeHtml(label, score, lang = 'tr') {
  const safeLabel = sanitizeHtmlOrSvg(label || translate('status.unverified', lang));
  const pct = Math.round(Number(score || 0) * 100);
  return `<span class="conf-badge" role="status" aria-label="Güven: ${safeLabel} (%${pct})">${safeLabel} (%${pct})</span>`;
}

export function announceAriaLive(message) {
  let region = document.getElementById('ux-aria-live');
  if (!region) {
    region = document.createElement('div');
    region.id = 'ux-aria-live';
    region.setAttribute('aria-live', 'polite');
    region.setAttribute('aria-atomic', 'true');
    region.style.position = 'absolute';
    region.style.left = '-9999px';
    document.body.appendChild(region);
  }
  region.textContent = String(message || '');
}

export async function submitRunFeedback({ runId, rating, reasonTags = [], note = '' }) {
  const resp = await fetch('/api/orchestrator/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ run_id: runId, rating, reason_tags: reasonTags, note }),
  });
  return resp.ok ? resp.json() : null;
}

export async function fetchHealthWizardStatus() {
  const resp = await fetch('/api/ux/health-wizard');
  return resp.ok ? resp.json() : null;
}
