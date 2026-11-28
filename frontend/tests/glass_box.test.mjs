import assert from 'node:assert/strict';
import { test } from 'node:test';

import { ribbonText, savedTabs } from '../../master/static/js/glass_box.js';

const data = { vram_used_gb: 5.3, vram_total_gb: 8, temperature_c: 61, models: ['qwen3.5:9b'], cpu_percent: 12.4, ram_used_gb: 14.2, ram_total_gb: 31.7, isolation: 'Yalıtım: Docker', gear: 'GEAR_2', waiting: '' };

test('ribbon shows card, model, processor, memory, isolation and gear', () => {
  assert.deepEqual(ribbonText(data), ['VRAM 5.3 / 8 GB', 'GPU 61 °C', 'Model: qwen3.5:9b', 'CPU %12', 'RAM 14.2 / 31.7 GB', 'Yalıtım: Docker', 'Vites: GEAR_2']);
});

test('a machine without a card or model says so and shows why work waits', () => {
  const parts = ribbonText({ ...data, vram_total_gb: null, models: [], waiting: 'pil düşük' });
  assert.equal(parts[0], 'Model: yüklü değil');
  assert.equal(parts.at(-1), 'Bekliyor: pil düşük');
});

test('saved tabs are ignored when there are none or they are unreadable', () => {
  assert.equal(savedTabs('yok', ['index.html']), null);
});
