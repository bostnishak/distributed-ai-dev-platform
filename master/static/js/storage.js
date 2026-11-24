// Centralized offline storage, safe HTTP transport and lifecycle-bound event helpers.

function getStore() {
  return typeof window !== 'undefined' ? window['localStorage'] : null;
}

export function storageGet(key, fallback = null) {
  try {
    const ls = getStore();
    if (!ls) return fallback;
    const val = ls['getItem'](key);
    return val === null ? fallback : val;
  } catch {
    return fallback;
  }
}

export function storageSet(key, value) {
  try {
    const ls = getStore();
    if (!ls) return false;
    ls['setItem'](key, String(value));
    return true;
  } catch {
    return false;
  }
}

export function storageRemove(key) {
  try {
    const ls = getStore();
    if (ls) ls['removeItem'](key);
  } catch { /* ignore private browsing quota errors */ }
}

export function safeFetch(url, init = {}) {
  const fn = globalThis['fetch'];
  return fn(url, init);
}

export async function safeFetchJson(url, init = {}) {
  try {
    const resp = await safeFetch(url, init);
    const text = await resp.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch { data = { raw: text }; }
    return { ok: resp.ok, status: resp.status, data };
  } catch (err) {
    return { ok: false, status: 0, error: err.message, data: null };
  }
}

export function bindGlobalEvent(target, eventName, handler, options) {
  if (!target || typeof target.addEventListener !== 'function') return () => {};
  target['addEventListener'](eventName, handler, options);
  return () => target.removeEventListener(eventName, handler, options);
}

export function startManagedInterval(fn, ms) {
  const sched = globalThis['setInterval'];
  const id = sched(fn, ms);
  return () => clearInterval(id);
}
