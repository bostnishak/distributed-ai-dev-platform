// Reusable UI widget primitives and icon helpers for Personal Space.
import { h, svg } from './util.js';

const ICONS = {
  chart: 'M4 20V10M10 20V4M16 20v-8M22 20H2',
  user: 'M12 12a4 4 0 100-8 4 4 0 000 8zM4 21c0-4 4-6 8-6s8 2 8 6',
  sun: 'M12 16a4 4 0 100-8 4 4 0 000 8zM12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4',
  moon: 'M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z',
  spark: 'M12 3l2 5 5 2-5 2-2 5-2-5-5-2 5-2z',
  memory: 'M4 6c0-1.5 3.5-3 8-3s8 1.5 8 3-3.5 3-8 3-8-1.5-8-3zM4 6v6c0 1.5 3.5 3 8 3s8-1.5 8-3V6M4 12v6c0 1.5 3.5 3 8 3s8-1.5 8-3v-6',
  shield: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z',
  plug: 'M12 22v-5M9 8V2M15 8V2M18 8v5a6 6 0 01-12 0V8z',
  close: 'M6 6l12 12M18 6L6 18',
  gear: 'M12 15a3 3 0 100-6 3 3 0 000 6zM19.4 15a1.7 1.7 0 00.3 1.9l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.9-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.9.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.9 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.9l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.9.3h.1a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.9-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.9v.1a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z',
};

export function icon(name) {
  const el = svg('svg', { class: 'sp-ico', viewBox: '0 0 24 24', 'aria-hidden': 'true' });
  el.append(svg('path', { d: ICONS[name] }));
  return el;
}

export function initials(name) {
  const parts = (name || '?').trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] || '?') + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toLocaleUpperCase('tr-TR');
}

export function avatar(p, size = '') {
  return h('span', { class: `sp-avatar ${size}`, style: { background: p.avatar_color } }, initials(p.display_name));
}

export function compact(n) {
  if (n === null || n === undefined) return '—';
  if (n >= 1e6) return `${(n / 1e6).toFixed(1).replace('.', ',')} Mn`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1).replace('.', ',')} B`;
  return String(n);
}

export function seg(options, value, onChange) {
  const box = h('div', { class: 'sp-seg', role: 'group' });
  for (const [val, label] of options) {
    const btn = h('button', { type: 'button', class: val === value ? 'active' : '' }, label);
    btn.addEventListener('click', () => {
      box.querySelectorAll('button').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      onChange(val);
    });
    box.append(btn);
  }
  return box;
}

export function toggleRow(label, desc, value, onChange) {
  const input = h('input', { type: 'checkbox', 'aria-label': label });
  input.checked = Boolean(value);
  input.addEventListener('change', () => onChange(input.checked));
  return h('div', { class: 'sp-row' },
    h('div', { class: 'sp-row-text' }, h('div', { class: 'sp-row-label' }, label), desc && h('div', { class: 'sp-row-desc' }, desc)),
    h('label', { class: 'sp-switch' }, input, h('span', { class: 'sp-switch-track' })));
}

export function settingRow(label, desc, control) {
  return h('div', { class: 'sp-row' },
    h('div', { class: 'sp-row-text' }, h('div', { class: 'sp-row-label' }, label), desc && h('div', { class: 'sp-row-desc' }, desc)),
    control);
}

export function textField(label, value, { multiline = false, max = 400, hint = '', onInput, placeholder = '' }) {
  const control = multiline
    ? h('textarea', { class: 'sp-textarea', maxlength: max, placeholder })
    : h('input', { class: 'sp-input', type: 'text', maxlength: max, placeholder });
  control.value = value || '';
  const counter = multiline ? h('div', { class: 'sp-counter' }, `${control.value.length}/${max}`) : null;
  control.addEventListener('input', () => {
    if (counter) counter.textContent = `${control.value.length}/${max}`;
    onInput(control.value);
  });
  return h('div', { class: 'sp-field' }, h('label', null, label), control, counter, hint && h('div', { class: 'sp-hint' }, hint));
}

export function swatches(colors, current, onPick, labels = null) {
  const box = h('div', { class: 'sp-swatches' });
  for (const [key, color] of colors) {
    const label = labels ? labels[key] : color;
    const b = h('button', { type: 'button', class: `sp-swatch${key === current ? ' active' : ''}`, style: { background: color }, title: label, 'aria-label': label });
    b.addEventListener('click', () => {
      box.querySelectorAll('.sp-swatch').forEach((x) => x.classList.remove('active'));
      b.classList.add('active');
      onPick(key);
    });
    box.append(b);
  }
  return box;
}

export function group(...children) { return h('div', { class: 'sp-group' }, ...children); }
export function groupTitle(text) { return h('div', { class: 'sp-group-title' }, text); }

export function confirmButton(label, onConfirm, cls = 'danger', onError = null) {
  const holder = h('span', { class: 'sp-inline' });
  const reset = () => {
    holder.replaceChildren(h('button', { type: 'button', class: `sp-btn ${cls} sm`, onClick: ask }, label));
  };
  const ask = () => {
    holder.replaceChildren(
      h('span', { class: 'muted small' }, 'Emin misiniz?'),
      h('button', {
        type: 'button',
        class: `sp-btn ${cls} sm`,
        onClick: async () => {
          try {
            await onConfirm();
          } catch (err) {
            if (onError) onError(err);
          } finally {
            reset();
          }
        },
      }, 'Evet'),
      h('button', { type: 'button', class: 'sp-btn sm', onClick: reset }, 'Vazgeç'));
  };
  reset();
  return holder;
}
