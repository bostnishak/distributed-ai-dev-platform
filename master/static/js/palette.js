// UX-13: command palette (Ctrl+K / Cmd+K). Every main page and action is reachable from the keyboard.
import { h } from './util.js';

const COMMANDS = [
  { label: 'Yeni proje', hint: 'Sayfa', run: () => { location.hash = '#/new'; } },
  { label: 'Projeler', hint: 'Sayfa', run: () => { location.hash = '#/projects'; } },
  { label: 'Ajanlar', hint: 'Sayfa', run: () => { location.hash = '#/agents'; } },
  { label: 'Stüdyolar ve yönetim', hint: 'Sayfa', run: () => { location.hash = '#/studios'; } },
  { label: 'Pano', hint: 'Sayfa', run: () => { location.hash = '#/dashboard'; } },
  { label: 'Asistan', hint: 'Sayfa', run: () => { location.hash = '#/assistant'; } },
  { label: 'Yeni sohbet', hint: 'Eylem', run: () => { location.hash = '#/assistant'; document.getElementById('newChatBtn')?.click(); } },
  { label: 'Temayı değiştir', hint: 'Eylem', run: () => document.getElementById('themeToggle')?.click() },
  { label: 'Kişisel alan ve ayarlar', hint: 'Eylem', run: () => document.getElementById('userCard')?.click() },
  { label: 'Hesap ve oturum', hint: 'Eylem', run: () => document.getElementById('authModalBtn')?.click() },
];

let overlay = null;
let opener = null;

function close() {
  if (!overlay) return;
  overlay.remove();
  overlay = null;
  if (opener && opener.focus) opener.focus();
}

function open() {
  if (overlay) return;
  opener = document.activeElement;
  let index = 0;
  let shown = COMMANDS;
  const input = h('input', {
    type: 'search', class: 'pal-input', placeholder: 'Komut ara…', role: 'combobox',
    'aria-expanded': 'true', 'aria-controls': 'palList', 'aria-label': 'Komut ara',
  });
  const list = h('ul', { class: 'pal-list', id: 'palList', role: 'listbox' });

  const draw = () => {
    list.replaceChildren(...shown.map((c, i) => h('li', {
      role: 'option', class: `pal-item${i === index ? ' active' : ''}`, 'aria-selected': i === index ? 'true' : 'false',
      onClick: () => { close(); c.run(); },
    }, h('span', null, c.label), h('span', { class: 'pal-hint' }, c.hint))));
    if (!shown.length) list.append(h('li', { class: 'pal-empty' }, 'Eşleşen komut yok'));
  };

  input.addEventListener('input', () => {
    const q = input.value.trim().toLocaleLowerCase('tr');
    shown = COMMANDS.filter((c) => c.label.toLocaleLowerCase('tr').includes(q));
    index = 0;
    draw();
  });
  input.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') { index = Math.min(index + 1, shown.length - 1); draw(); e.preventDefault(); }
    else if (e.key === 'ArrowUp') { index = Math.max(index - 1, 0); draw(); e.preventDefault(); }
    else if (e.key === 'Enter' && shown[index]) { const cmd = shown[index]; close(); cmd.run(); }
    else if (e.key === 'Escape') close();
  });

  overlay = h('div', { class: 'pal-overlay', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Komut paleti' },
    h('div', { class: 'pal-box' }, input, list));
  overlay.addEventListener('mousedown', (e) => { if (e.target === overlay) close(); });
  document.body.append(overlay);
  draw();
  input.focus();
}

export function initPalette() {
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      if (overlay) close(); else open();
    }
  });
}
