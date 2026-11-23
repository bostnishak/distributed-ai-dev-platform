/**
 * UX-03 & UX-16: Versioned Reactive Store with localStorage Migration & Private-Window Fallback.
 */

export const STORAGE_SCHEMA_VERSION = 2;
const STORAGE_KEY = 'platform_ui_state_v2';

export const DEFAULT_SETTINGS = Object.freeze({
  language: 'tr',
  theme: 'dark',
  responseLength: 'balanced',
  tone: 'professional',
  showConfidenceBadges: true,
  webSearchEnabled: false,
  reducedMotion: false,
});

function safeReadStorage(key) {
  try {
    return window.localStorage.getItem(key);
  } catch (_) {
    return null;
  }
}

function safeWriteStorage(key, value) {
  try {
    window.localStorage.setItem(key, value);
    return true;
  } catch (_) {
    return false;
  }
}

export function migrateState(rawObj) {
  if (!rawObj || typeof rawObj !== 'object') {
    return { schemaVersion: STORAGE_SCHEMA_VERSION, settings: { ...DEFAULT_SETTINGS } };
  }
  const v = Number(rawObj.schemaVersion || 1);
  const merged = { ...DEFAULT_SETTINGS, ...(rawObj.settings || rawObj) };
  if (v < 2 && typeof merged.showConfidenceBadges !== 'boolean') {
    merged.showConfidenceBadges = true;
  }
  return { schemaVersion: STORAGE_SCHEMA_VERSION, settings: merged };
}

export function createReactiveStore() {
  let state = migrateState(JSON.parse(safeReadStorage(STORAGE_KEY) || 'null'));
  const listeners = new Set();

  return {
    getState: () => state,
    updateSettings(patch) {
      state = {
        schemaVersion: STORAGE_SCHEMA_VERSION,
        settings: { ...state.settings, ...patch },
      };
      safeWriteStorage(STORAGE_KEY, JSON.stringify(state));
      listeners.forEach((fn) => fn(state));
    },
    subscribe(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
  };
}
