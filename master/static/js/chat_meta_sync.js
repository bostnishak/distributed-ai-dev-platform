// Backs up pins, titles, folders and section state to the server and restores them in a fresh browser.
import { getActiveUserId } from './personal.js';
import { safeFetchJson, storageGet, storageSet } from './storage.js';

const NAMES = ['chat_meta', 'chat_folders', 'chat_sections'];
const PUSH_DELAY_MS = 1500;
let timer = null;

function key(name) { return `cm6453_${name}:${getActiveUserId()}`; }
function url() { return `/api/user/${encodeURIComponent(getActiveUserId())}/chat-meta`; }

async function pushMeta() {
  const body = {};
  for (const name of NAMES) {
    const value = storageGet(key(name), null);
    if (value !== null) body[name] = value;
  }
  await safeFetchJson(url(), { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}

export function scheduleMetaPush() {
  clearTimeout(timer);
  timer = setTimeout(pushMeta, PUSH_DELAY_MS);
}

/** Fill in whatever this browser does not have yet from the server copy; returns true when something was restored. */
export async function pullMeta() {
  const res = await safeFetchJson(url());
  if (!res.ok || !res.data) return false;
  let restored = false;
  for (const name of NAMES) {
    if (typeof res.data[name] === 'string' && storageGet(key(name), null) === null) {
      storageSet(key(name), res.data[name]);
      restored = true;
    }
  }
  return restored;
}
