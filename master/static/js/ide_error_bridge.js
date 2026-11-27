// Errors thrown inside the sandboxed preview, shown in the IDE with a one-click "send to AI" action.
export function attachErrorBridge(iframe, iterBar, card) {
  const box = document.createElement('div');
  box.className = 'ide-error-box';
  box.hidden = true;
  const text = document.createElement('span');
  const fix = document.createElement('button');
  fix.type = 'button';
  fix.className = 'ide-btn primary';
  fix.textContent = 'Hatayı düzelttir';
  box.append(text, fix);
  card.insertBefore(box, iterBar);
  let errors = [];

  const onMessage = (event) => {
    if (event.source !== iframe.contentWindow || !event.data) return;
    if (event.data.type === 'preview-ready') errors = [];
    if (event.data.type === 'preview-error') errors = [...new Set([...errors, String(event.data.message).slice(0, 200)])].slice(0, 3);
    box.hidden = errors.length === 0;
    text.textContent = errors.length ? `Önizleme hatası: ${errors[0]}` : '';
  };
  addEventListener('message', onMessage);

  fix.addEventListener('click', () => {
    const input = iterBar.querySelector('input');
    input.value = `Önizlemede şu JavaScript hataları oluşuyor, düzelt: ${errors.join(' | ')}`.slice(0, 600);
    iterBar.querySelector('button').click();
    box.hidden = true;
  });
}
