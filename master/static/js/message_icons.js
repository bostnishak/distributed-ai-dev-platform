// Small icon buttons for the actions under a chat message. The label shows instantly on hover or keyboard focus.
import { h, svg } from './util.js';

const ICONS = {
  copy: ['M9 9h10a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V10a1 1 0 0 1 1-1z', 'M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1'],
  check: ['M5 12.5l4.5 4.5L19 7.5'],
  speak: ['M11 5L6 9H3v6h3l5 4z', 'M15.5 8.5a5 5 0 0 1 0 7', 'M18.5 5.5a9 9 0 0 1 0 13'],
  stop: ['M7 7h10v10H7z'],
  download: ['M12 3v12', 'M7 10l5 5 5-5', 'M4 20h16'],
  sparkles: ['M12 3l1.8 4.7 4.7 1.8-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z', 'M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z'],
  refresh: ['M20 11a8 8 0 1 0-2.3 5.7', 'M20 4v7h-7'],
  document: ['M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z', 'M14 3v5h5', 'M9 13h6', 'M9 17h6'],
  share: ['M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7', 'M16 6l-4-4-4 4', 'M12 2v13'],
  edit: ['M4 20h4L19 9l-4-4L4 16z', 'M13.5 6.5l4 4'],
};

export function actionIcon(name) {
  return svg('svg', { viewBox: '0 0 24 24', width: '16', height: '16', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.8', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true' },
    ...(ICONS[name] || ICONS.copy).map((d) => svg('path', { d })));
}

/** An icon-only button. `label` is the tooltip and the accessible name; `setState(icon, label)` swaps both. */
export function iconButton(icon, label, onClick) {
  const btn = h('button', { type: 'button', class: 'msg-act', 'data-tip': label, 'aria-label': label });
  btn.append(actionIcon(icon));
  btn.setState = (nextIcon, nextLabel) => {
    btn.replaceChildren(actionIcon(nextIcon));
    btn.dataset.tip = nextLabel;
    btn.setAttribute('aria-label', nextLabel);
  };
  btn.addEventListener('click', onClick);
  return btn;
}
