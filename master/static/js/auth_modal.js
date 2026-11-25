// SEC-01 UI: Accessible Turkish Login / Initial Admin Setup / Session Indicator Modal (zero CDN, zero emojis).
import { safeFetchJson } from './storage.js';
import { h, svg } from './util.js';

let authModalEl = null;

function buildModalDom() {
  if (authModalEl) return authModalEl;
  const closeBtn = h('button', { id: 'authCloseBtn', type: 'button', 'aria-label': 'Kapat', class: 'auth-modal-close' }, 'x');
  const form = h('form', { id: 'authForm', class: 'auth-modal-form' },
    h('label', { class: 'auth-modal-label' }, 'Kullanıcı adı',
      h('input', { id: 'authUsername', type: 'text', required: true, minlength: '3', autocomplete: 'username', class: 'auth-modal-input' })),
    h('label', { class: 'auth-modal-label' }, 'Parola (en az 8 karakter)',
      h('input', { id: 'authPassword', type: 'password', required: true, minlength: '8', autocomplete: 'current-password', class: 'auth-modal-input' })),
    h('div', { id: 'authError', role: 'alert', class: 'auth-modal-error' }),
    h('button', { id: 'authSubmitBtn', type: 'submit', class: 'btn primary auth-modal-submit' }, 'Giriş Yap'),
  );
  const signedBox = h('div', { id: 'authSignedInBox', hidden: true, class: 'auth-modal-signed' },
    h('div', { id: 'authUserInfo', class: 'auth-modal-userinfo' }),
    h('button', { id: 'authLogoutBtn', type: 'button', class: 'btn auth-modal-logout' }, 'Oturumu Kapat'),
  );
  const box = h('div', { class: 'auth-modal-box' },
    h('div', { class: 'auth-modal-head' }, h('h2', { id: 'authModalTitle', class: 'auth-modal-title' }, 'Hesap ve Oturum'), closeBtn),
    h('p', { id: 'authSubtitle', class: 'auth-modal-sub' }),
    form,
    signedBox,
  );
  const overlay = h('div', {
    id: 'authModalOverlay',
    class: 'auth-modal-overlay',
    role: 'dialog',
    'aria-modal': 'true',
    'aria-labelledby': 'authModalTitle',
    hidden: true,
  }, box);

  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.hidden = true; });
  closeBtn.addEventListener('click', () => { overlay.hidden = true; });
  document.body.appendChild(overlay);
  authModalEl = overlay;
  return overlay;
}

export async function refreshAuthBadge(btn) {
  const res = await safeFetchJson('/api/auth/status');
  if (!res.ok || !res.data) return null;
  const st = res.data;
  if (btn) {
    btn.title = st.authenticated
      ? `Oturum açık: ${st.user.username} (${st.user.role})`
      : (st.initialized ? 'Oturum aç' : 'İlk yönetici hesabını oluştur');
    btn.dataset.authState = st.authenticated ? 'signed-in' : 'signed-out';
  }
  return st;
}

export async function openAuthModal(badgeBtn = null) {
  const modal = buildModalDom();
  const status = (await refreshAuthBadge(badgeBtn)) || { initialized: false, authenticated: false, user: null };
  const title = modal.querySelector('#authModalTitle');
  const sub = modal.querySelector('#authSubtitle');
  const form = modal.querySelector('#authForm');
  const signedBox = modal.querySelector('#authSignedInBox');
  const userInfo = modal.querySelector('#authUserInfo');
  const submitBtn = modal.querySelector('#authSubmitBtn');
  const errEl = modal.querySelector('#authError');
  errEl.textContent = '';

  if (status.authenticated && status.user) {
    title.textContent = 'Aktif Oturum';
    sub.textContent = 'Yerel oturum çerezi (HttpOnly, imzalı) aktif.';
    form.hidden = true;
    signedBox.hidden = false;
    userInfo.textContent = `Kullanıcı: ${status.user.username} · Rol: ${status.user.role}`;
  } else {
    signedBox.hidden = true;
    form.hidden = false;
    if (!status.initialized) {
      title.textContent = 'İlk Yönetici Kurulumu';
      sub.textContent = 'Bu sunucuda henüz hesap yok. İlk yönetici hesabını oluşturabilirsiniz.';
      submitBtn.textContent = 'Yönetici Hesabı Oluştur';
    } else {
      title.textContent = 'Oturum Aç';
      sub.textContent = 'Yerel hesap bilgilerinizle giriş yapın.';
      submitBtn.textContent = 'Giriş Yap';
    }
  }

  form.onsubmit = async (e) => {
    e.preventDefault();
    errEl.textContent = '';
    const username = modal.querySelector('#authUsername').value.trim();
    const password = modal.querySelector('#authPassword').value;
    const endpoint = status.initialized ? '/api/auth/login' : '/api/auth/setup';
    const res = await safeFetchJson(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      errEl.textContent = (res.data && res.data.detail) || res.error || 'İşlem başarısız.';
      return;
    }
    await refreshAuthBadge(badgeBtn);
    modal.hidden = true;
  };

  modal.querySelector('#authLogoutBtn').onclick = async () => {
    await safeFetchJson('/api/auth/logout', { method: 'POST' });
    await refreshAuthBadge(badgeBtn);
    modal.hidden = true;
  };

  modal.hidden = false;
}

export function initAuthUi() {
  const themeBtn = document.getElementById('themeToggle');
  if (!themeBtn || !themeBtn.parentElement || document.getElementById('authModalBtn')) return;
  const btn = document.createElement('button');
  btn.id = 'authModalBtn';
  btn.type = 'button';
  btn.className = 'sp-icon-btn';
  btn.hidden = true; // kept in the DOM so the command palette can still open the account dialog
  btn.setAttribute('aria-label', 'Hesap ve oturum yönetimi');
  const lockIcon = svg('svg', {
    viewBox: '0 0 24 24', width: '16', height: '16', fill: 'none',
    stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round',
  }, svg('rect', { x: '3', y: '11', width: '18', height: '11', rx: '2' }), svg('path', { d: 'M7 11V7a5 5 0 0 1 10 0v4' }));
  btn.appendChild(lockIcon);
  btn.addEventListener('click', () => openAuthModal(btn));
  themeBtn.parentElement.appendChild(btn);
  refreshAuthBadge(btn);
}
