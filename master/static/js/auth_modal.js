// SEC-01 UI: Accessible Turkish Login / Initial Admin Setup / Session Indicator Modal (zero CDN, zero emojis).

let authModalEl = null;

function buildModalDom() {
  if (authModalEl) return authModalEl;
  const overlay = document.createElement('div');
  overlay.id = 'authModalOverlay';
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-modal', 'true');
  overlay.setAttribute('aria-labelledby', 'authModalTitle');
  overlay.hidden = true;
  overlay.style.cssText =
    'position:fixed;inset:0;background:rgba(15,23,42,.62);display:flex;align-items:center;justify-content:center;z-index:9999;padding:16px;';

  overlay.innerHTML = `
    <div style="background:var(--surface,#ffffff);color:var(--text,#0f172a);border:1px solid var(--border,#e2e8f0);border-radius:14px;max-width:400px;width:100%;padding:22px;box-shadow:0 20px 45px rgba(0,0,0,.28);">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h2 id="authModalTitle" style="margin:0;font-size:17px;font-weight:700;">Hesap ve Oturum</h2>
        <button id="authCloseBtn" type="button" aria-label="Kapat" style="background:none;border:none;font-size:18px;cursor:pointer;color:inherit;">x</button>
      </div>
      <p id="authSubtitle" style="margin:0 0 14px;font-size:13px;opacity:.8;"></p>
      <form id="authForm" style="display:flex;flex-direction:column;gap:10px;">
        <label style="font-size:12.5px;font-weight:600;">Kullanıcı adı
          <input id="authUsername" type="text" required minlength="3" autocomplete="username"
            style="width:100%;margin-top:4px;padding:8px 10px;border:1px solid var(--input-border,#cbd5e1);border-radius:8px;background:var(--surface,#fff);color:inherit;box-sizing:border-box;">
        </label>
        <label style="font-size:12.5px;font-weight:600;">Parola (en az 8 karakter)
          <input id="authPassword" type="password" required minlength="8" autocomplete="current-password"
            style="width:100%;margin-top:4px;padding:8px 10px;border:1px solid var(--input-border,#cbd5e1);border-radius:8px;background:var(--surface,#fff);color:inherit;box-sizing:border-box;">
        </label>
        <div id="authError" role="alert" style="color:#dc2626;font-size:12.5px;min-height:16px;"></div>
        <button id="authSubmitBtn" type="submit" class="btn primary" style="padding:9px 14px;border-radius:8px;font-weight:600;cursor:pointer;">Giriş Yap</button>
      </form>
      <div id="authSignedInBox" hidden style="display:flex;flex-direction:column;gap:10px;">
        <div id="authUserInfo" style="font-size:13.5px;padding:10px;border-radius:8px;background:var(--surface-2);border:1px solid var(--border,#e2e8f0);"></div>
        <button id="authLogoutBtn" type="button" class="btn" style="padding:8px 12px;border-radius:8px;cursor:pointer;">Oturumu Kapat</button>
      </div>
    </div>
  `;

  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.hidden = true; });
  overlay.querySelector('#authCloseBtn').addEventListener('click', () => { overlay.hidden = true; });
  document.body.appendChild(overlay);
  authModalEl = overlay;
  return overlay;
}

export async function refreshAuthBadge(btn) {
  try {
    const resp = await fetch('/api/auth/status');
    if (!resp.ok) return null;
    const st = await resp.json();
    if (btn) {
      btn.title = st.authenticated
        ? `Oturum açık: ${st.user.username} (${st.user.role})`
        : (st.initialized ? 'Oturum aç' : 'İlk yönetici hesabını oluştur');
      btn.dataset.authState = st.authenticated ? 'signed-in' : 'signed-out';
    }
    return st;
  } catch {
    return null;
  }
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
    try {
      const r = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) {
        errEl.textContent = d.detail || 'İşlem başarısız.';
        return;
      }
      await refreshAuthBadge(badgeBtn);
      modal.hidden = true;
    } catch (err) {
      errEl.textContent = `Bağlantı hatası: ${err.message}`;
    }
  };

  modal.querySelector('#authLogoutBtn').onclick = async () => {
    await fetch('/api/auth/logout', { method: 'POST' }).catch(() => {});
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
  btn.setAttribute('aria-label', 'Hesap ve oturum yönetimi');
  btn.innerHTML =
    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>';
  btn.addEventListener('click', () => openAuthModal(btn));
  themeBtn.parentElement.appendChild(btn);
  refreshAuthBadge(btn);
}
