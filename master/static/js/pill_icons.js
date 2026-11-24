// Small stroke icons for the composer; built with createElementNS (no innerHTML).
import { svg } from './util.js';

const SHAPES = {
  tune: [['line', { x1: 4, y1: 7, x2: 20, y2: 7 }], ['line', { x1: 4, y1: 17, x2: 20, y2: 17 }], ['circle', { cx: 9, cy: 7, r: 2.2 }], ['circle', { cx: 15, cy: 17, r: 2.2 }]],
  wave: [['line', { x1: 4, y1: 10, x2: 4, y2: 14 }], ['line', { x1: 8, y1: 6, x2: 8, y2: 18 }], ['line', { x1: 12, y1: 3, x2: 12, y2: 21 }], ['line', { x1: 16, y1: 7, x2: 16, y2: 17 }], ['line', { x1: 20, y1: 10, x2: 20, y2: 14 }]],
};

export function pillIcon(name) {
  const root = svg('svg', { viewBox: '0 0 24 24', width: '16', height: '16', fill: 'none', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'aria-hidden': 'true' });
  for (const [tag, attrs] of SHAPES[name] || []) root.append(svg(tag, attrs));
  return root;
}
