// The files a running change has rewritten, each with its diff, listed as they finish.
export function createChangeLog() {
  const box = document.createElement('div');
  box.className = 'ide-change-log';
  box.hidden = true;
  return {
    box,
    clear() {
      box.replaceChildren();
      box.hidden = true;
    },
    add(event) {
      if (!event.diff) return;
      const entry = document.createElement('details');
      const title = document.createElement('summary');
      title.textContent = `Değişti: ${event.path} (${event.index}/${event.total})`;
      const body = document.createElement('pre');
      body.textContent = event.diff;
      entry.append(title, body);
      box.append(entry);
      box.hidden = false;
    },
  };
}
