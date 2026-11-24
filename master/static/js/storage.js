// Centralized offline storage and safe fetch helpers (eliminates scattered localStorage/fetch lint hits).

export function storageGet(key, fallback = null) {
  try {
    const val = window.localStorage.getItem(key);
    return val === null ? fallback : val;
  } catch {
    return fallback;
  }
}

export function storageSet(key, value) {
  try {
    window.localStorage.setItem(key, String(value));
    return true;
  } catch {
    return false;
  }
}

export function storageRemove(key) {
  try {
    window.localStorage.removeItem(key);
  } catch { /* ignore private browsing quota errors */ }
}

export async function safeFetchJson(url, init = {}) {
  try {
    const resp = await fetch(url, init);
    const text = await resp.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch { data = { raw: text }; }
    return { ok: resp.ok, status: resp.status, data };
  } catch (err) {
    return { ok: false, status: 0, error: err.message, data: null };
  }
}
