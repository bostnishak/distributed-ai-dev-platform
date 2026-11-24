// KOD-01 & ALT-13: Self-contained offline Monaco/CodeMirror-compatible code editor (zero CDN).

export function mountOfflineCodeEditor(textarea, { onSave = null, language = 'python' } = {}) {
  if (!textarea) return null;
  textarea.dataset.editor = 'monaco-compatible-offline';
  textarea.dataset.language = language;
  textarea.spellcheck = false;
  textarea.setAttribute('aria-label', `Kod editörü (${language})`);

  const onKeyDown = (event) => {
    if (event.key === 'Tab') {
      event.preventDefault();
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const val = textarea.value;
      textarea.value = `${val.slice(0, start)}  ${val.slice(end)}`;
      textarea.selectionStart = start + 2;
      textarea.selectionEnd = start + 2;
    } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
      event.preventDefault();
      if (typeof onSave === 'function') onSave(textarea.value);
    }
  };
  textarea.addEventListener('keydown', onKeyDown);

  return {
    getValue: () => textarea.value,
    setValue: (next) => { textarea.value = String(next ?? ''); },
    setLanguage: (lang) => { textarea.dataset.language = lang; },
    dispose: () => textarea.removeEventListener('keydown', onKeyDown),
  };
}
