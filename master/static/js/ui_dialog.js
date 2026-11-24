// Accessible offline modal dialogs & non-blocking toast helper (replaces native alert/confirm/prompt).
import { h } from './util.js';

function ensureToastRoot() {
  let root = document.getElementById('dadpToastRoot');
  if (!root) {
    root = h('div', { id: 'dadpToastRoot', class: 'dadp-toast-root', 'aria-live': 'polite' });
    document.body.append(root);
  }
  return root;
}

export function uiToast(message, kind = 'info') {
  if (typeof document === 'undefined') return;
  const root = ensureToastRoot();
  const item = h('div', { class: `dadp-toast dadp-toast-${kind}`, role: 'status' }, String(message || ''));
  root.append(item);
  const TOAST_MS = 3500;
  setTimeout(() => item.remove(), TOAST_MS);
}

export function uiConfirm(message, title = 'Onay Gerekli') {
  if (typeof document === 'undefined') return Promise.resolve(true);
  return new Promise((resolve) => {
    const dlg = h('dialog', { class: 'dadp-dialog', 'aria-label': title });
    const okBtn = h('button', { type: 'button', class: 'btn primary' }, 'Evet, devam et');
    const cancelBtn = h('button', { type: 'button', class: 'btn' }, 'Vazgeç');
    const finish = (val) => {
      if (dlg.open) dlg.close();
      dlg.remove();
      resolve(val);
    };
    okBtn.addEventListener('click', () => finish(true));
    cancelBtn.addEventListener('click', () => finish(false));
    dlg.addEventListener('cancel', () => finish(false));
    dlg.append(
      h('h3', { class: 'dadp-dialog-title' }, title),
      h('p', { class: 'dadp-dialog-msg' }, String(message || '')),
      h('div', { class: 'dadp-dialog-actions' }, cancelBtn, okBtn),
    );
    document.body.append(dlg);
    if (typeof dlg.showModal === 'function') dlg.showModal();
    else dlg.setAttribute('open', '');
    okBtn.focus();
  });
}

export function uiPrompt(message, defaultValue = '', title = 'Değer Girin') {
  if (typeof document === 'undefined') return Promise.resolve(defaultValue);
  return new Promise((resolve) => {
    const dlg = h('dialog', { class: 'dadp-dialog', 'aria-label': title });
    const input = h('input', { type: 'text', class: 'dadp-dialog-input', value: String(defaultValue || ''), 'aria-label': message });
    const okBtn = h('button', { type: 'submit', class: 'btn primary' }, 'Tamam');
    const cancelBtn = h('button', { type: 'button', class: 'btn' }, 'Vazgeç');
    const form = h('form', { class: 'dadp-dialog-form' },
      h('h3', { class: 'dadp-dialog-title' }, title),
      h('p', { class: 'dadp-dialog-msg' }, String(message || '')),
      input,
      h('div', { class: 'dadp-dialog-actions' }, cancelBtn, okBtn),
    );
    const finish = (val) => {
      if (dlg.open) dlg.close();
      dlg.remove();
      resolve(val);
    };
    form.addEventListener('submit', (e) => { e.preventDefault(); finish(input.value); });
    cancelBtn.addEventListener('click', () => finish(null));
    dlg.addEventListener('cancel', () => finish(null));
    dlg.append(form);
    document.body.append(dlg);
    if (typeof dlg.showModal === 'function') dlg.showModal();
    else dlg.setAttribute('open', '');
    input.focus();
    input.select();
  });
}
