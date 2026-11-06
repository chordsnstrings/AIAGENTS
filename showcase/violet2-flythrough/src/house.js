import * as THREE from 'three';
import { H } from './plan.js';
import { F } from './builder.js';

// Exterior shell of one TH12-4M townhouse in house-local metres (see plan.js). The same shell
// is used for the hero unit (with real railings and open doors) and, instanced, for every
// neighbour (cheaper railing cards and fake interiors behind the glass).

export function buildShell(B, { hero = false } = {}) {
  const { F0, C0, F1, C1, F2, C2, R2 } = H;
  const bx = (k, x0, x1, y0, y1, d0, d1, f) => B.box(k, x0, x1, y0, y1, -d1, -d0, f);
  const spots = { bush: [], flower: [], palm: [], olive: [], pink: [] };

  function wallX(k, x0, x1, y0, y1, d0, d1, holes = []) {
    const xs = [...new Set([x0, x1, ...holes.flatMap((h) => [h[0], h[1]])])].sort((a, b) => a - b);
    for (let i = 0; i < xs.length - 1; i++) {
      const a = xs[i], b = xs[i + 1];
      let segs = [[y0, y1]];
      for (const h of holes) {
        if (h[0] > a + 1e-6 || h[1] < b - 1e-6) continue;
        segs = segs.flatMap(([s, e]) => [[s, Math.min(e, h[2])], [Math.max(s, h[3]), e]]).filter(([s, e]) => e - s > 1e-4);
      }
      for (const [s, e] of segs) bx(k, a, b, s, e, d0, d1);
    }
  }

  function wallD(k, x0, x1, y0, y1, d0, d1, holes = []) {
    const ds = [...new Set([d0, d1, ...holes.flatMap((h) => [h[0], h[1]])])].sort((a, b) => a - b);
    for (let i = 0; i < ds.length - 1; i++) {
      const a = ds[i], b = ds[i + 1];
      let segs = [[y0, y1]];
      for (const h of holes) {
        if (h[0] > a + 1e-6 || h[1] < b - 1e-6) continue;
        segs = segs.flatMap(([s, e]) => [[s, Math.min(e, h[2])], [Math.max(s, h[3]), e]]).filter(([s, e]) => e - s > 1e-4);
      }
      for (const [s, e] of segs) bx(k, x0, x1, s, e, a, b);
    }
  }
  function glazeD(x, d0, d1, y0, y1) {
    const t = 0.055, h = 0.045;
    bx('frame', x - h, x + h, y1 - t, y1, d0, d1);
    bx('frame', x - h, x + h, y0, y0 + 0.03, d0, d1);
    bx('frame', x - h, x + h, y0, y1, d0, d0 + t);
    bx('frame', x - h, x + h, y0, y1, d1 - t, d1);
    bx('glass', x - 0.005, x + 0.005, y0 + 0.03, y1 - t, d0 + t, d1 - t, F.PX | F.NX);
  }

  // Black aluminium frame with glass panes in the plane d. open: index of a slid-open panel.
  function glaze(x0, x1, y0, y1, d, panels = 1, open = null, glassKey = 'glass') {
    const t = 0.055, h = 0.045;
    bx('frame', x0, x1, y1 - t, y1, d - h, d + h);
    bx('frame', x0, x1, y0, y0 + 0.03, d - h, d + h);
    bx('frame', x0, x0 + t, y0, y1, d - h, d + h);
    bx('frame', x1 - t, x1, y0, y1, d - h, d + h);
    const w = (x1 - x0) / panels;
    for (let i = 1; i < panels; i++) { const xm = x0 + i * w; bx('frame', xm - t * 0.5, xm + t * 0.5, y0, y1, d - h, d + h); }
    for (let i = 0; i < panels; i++) {
      const a = x0 + i * w + t * (i ? 0.5 : 1), b = x0 + (i + 1) * w - t * (i === panels - 1 ? 1 : 0.5);
      if (i === open) {
        // panel slid behind its neighbour, on the inner track
        const j = i + 1 < panels ? i + 1 : i - 1;
        const a2 = x0 + j * w + t * 0.5, b2 = x0 + (j + 1) * w - t * 0.5;
        bx(glassKey, a2, b2, y0 + 0.03, y1 - t, d - 0.075, d - 0.065, F.PZ | F.NZ);
        bx('frame', a2 - 0.035, a2, y0, y1, d - 0.09, d - 0.05);
        bx('frame', b2, b2 + 0.035, y0, y1, d - 0.09, d - 0.05);
        continue;
      }
      bx(glassKey, a, b, y0 + 0.03, y1 - t, d - 0.005, d + 0.005, F.PZ | F.NZ);
    }
  }

  // Bronze vertical-baluster railing along x (plane d) or along d (plane x).
  function railing(alongX, a0, a1, y, at, ht = 1.1) {
    const seg = (k, p0, p1, y0, y1, w) => alongX ? bx(k, p0, p1, y0, y1, at - w, at + w) : bx(k, at - w, at + w, y0, y1, p0, p1);
    if (hero) {
      seg('bronze', a0, a1, y + ht - 0.045, y + ht, 0.03);
      seg('bronze', a0, a1, y + 0.07, y + 0.1, 0.015);
      for (let p = a0 + 0.055; p < a1 - 0.02; p += 0.11) seg('bronze', p - 0.011, p + 0.011, y + 0.1, y + ht - 0.045, 0.011);
    } else if (alongX) {
      B.quad('rail', [a0, y, -at], [a1, y, -at], [a1, y + ht, -at], [a0, y + ht, -at], [[a0, 0], [a1, 0], [a1, 1], [a0, 1]]);
    } else {
      B.quad('rail', [at, y, -a0], [at, y, -a1], [at, y + ht, -a1], [at, y + ht, -a0], [[a0, 0], [a1, 0], [a1, 1], [a0, 1]]);
    }
  }

  const slats = (x0, x1, y0, y1, d0, d1, pitch = 0.16, w = 0.045) => {
    for (let x = x0 + pitch / 2; x < x1 - 0.02; x += pitch) bx('wood', x - w / 2, x + w / 2, y0, y1, d0, d1);
  };
  const latticeD = (x, d0, d1, y0, y1) => B.quad('lattice', [x, y0, -d0], [x, y0, -d1], [x, y1, -d1], [x, y1, -d0], [[d0, y0], [d1, y0], [d1, y1], [d0, y1]]);
  const room = (x0, x1, y0, y1, d, facingStreet) => facingStreet
    ? B.quad('room', [x0, y0, -d], [x1, y0, -d], [x1, y1, -d], [x0, y1, -d])
    : B.quad('room', [x1, y0, -d], [x0, y0, -d], [x0, y1, -d], [x1, y1, -d]);

  // ---------- site
  bx('pavers', 0, 6.1, 0, 0.06, 0, 6.75, F.PY | F.PZ);
  for (const [a, b] of [[0.1, 0.75], [5.35, 6.0]]) {
    bx('render', a, b, 0.06, 0.48, 0.15, 1.3);
    bx('soil', a + 0.05, b - 0.05, 0.48, 0.5, 0.2, 1.25, F.PY);
    spots.flower.push([(a + b) / 2, 0.5, 0.72, 0.75]);
  }
  bx('render', 3.15, 6.0, 0, F0, 6.0, 15.0, F.PX | F.NX);
  bx('render', 0.1, 3.15, 0, F0, 6.75, 15.0, F.NX);
  bx('stone', 1.8, 3.2, 0.06, 0.17, 6.25, 6.5);
  bx('patio', 0.1, 6.0, 0, 0.2, 15.0, 16.45, F.PY | F.NZ);
  bx('grass', 0.1, 6.0, 0, 0.12, 16.45, 17.75, F.PY);
  bx('render', 0.1, 6.0, 0, 0.45, 17.75, 18.4);
  bx('soil', 0.15, 5.95, 0.45, 0.47, 17.8, 18.35, F.PY);
  bx('render', 0, 6.1, 0, 2.0, 18.4, 18.5);
  bx('render', 0, 0.1, 0, 2.0, 15.0, 18.4);
  bx('render', 6.0, 6.1, 0, 2.0, 15.0, 18.4);
  spots.palm.push([0.75, 0.45, 18.05, 0.74]);
  spots.bush.push([1.6, 0.45, 18.05, 0.8], [2.5, 0.45, 18.1, 0.7], [4.4, 0.45, 18.05, 0.85], [5.4, 0.45, 18.05, 0.9]);
  spots.flower.push([3.4, 0.45, 18.05, 0.9], [0.4, 0.12, 16.9, 0.7], [5.75, 0.12, 17.0, 0.6]);

  // ---------- ground floor
  bx('paint', 0, 0.1, 0, F1, 6.0, 15.0);
  bx('paint', 6.0, 6.1, 0, F1, 6.0, 15.0);
  bx('render', 0, 0.1, 0.06, C0, 1.85, 6.0);
  bx('render', 6.0, 6.1, 0.06, C0, 1.85, 6.0);
  wallX('render', 3.15, 6.0, 0.06, C0, 5.75, 6.0, [[3.9, 5.65, F0 + 1.05, F0 + 2.35]]);
  glaze(3.9, 5.65, F0 + 1.05, F0 + 2.35, 5.875, 2);
  bx('stone', 3.15, 3.3, 0.06, C0, 5.75, 6.5);
  wallX('stone', 0.1, 3.15, 0.06, C0, 6.5, 6.75, [[1.95, 3.05, F0, F0 + 2.6], [0.3, 1.75, F0 + 0.6, F0 + 1.2]]);
  glaze(0.3, 1.75, F0 + 0.6, F0 + 1.2, 6.625, 2);
  {
    const door = new THREE.BoxGeometry(1.1, 2.6, 0.06);
    const m = new THREE.Matrix4().makeTranslation(1.95, F0, -6.62)
      .multiply(new THREE.Matrix4().makeRotationY(hero ? THREE.MathUtils.degToRad(82) : 0))
      .multiply(new THREE.Matrix4().makeTranslation(0.55, 1.3, 0));
    B.add('walnut', door, m, 'box');
    const pull = new THREE.BoxGeometry(0.03, 1.2, 0.05);
    B.add('bronze', pull, m.clone().multiply(new THREE.Matrix4().makeTranslation(0.4, 0, 0.06)), 'box');
  }
  for (const x of [1.5, 4.6]) {
    B.add('downlight', new THREE.CylinderGeometry(0.07, 0.07, 0.01, 20), new THREE.Matrix4().makeTranslation(x, C0 - 0.004, -3.6));
    B.quad('pool', [x - 1.6, 0.075, -2.0], [x + 1.6, 0.075, -2.0], [x + 1.6, 0.075, -5.2], [x - 1.6, 0.075, -5.2]);
  }
  B.quad('pool', [1.4, 0.075, -5.9], [3.6, 0.075, -5.9], [3.6, 0.075, -7.0], [1.4, 0.075, -7.0]);
  bx('led', 1.9, 3.1, C0 - 0.02, C0 - 0.005, 6.1, 6.16);
  glaze(0.1, 6.0, F0, C0, 14.9, 4, hero ? 2 : null);
  bx('led', 0.3, 5.8, C0 - 0.03, C0 - 0.01, 15.2, 15.24);
  B.quad('pool', [0.3, 0.205, -15.0], [5.8, 0.205, -15.0], [5.8, 0.205, -16.6], [0.3, 0.205, -16.6]);

  // ---------- first floor
  bx('render', 0.1, 6.0, C0, F1, 1.5, 6.65);
  bx('render', 2.95, 6.0, C0, F1, 6.65, 9.45);
  bx('render', 0.1, 6.0, C0, F1, 9.45, 15.28);
  bx('render', 0, 0.3, 0, F2 + 0.15, 1.4, 1.85);
  bx('render', 5.8, 6.1, 0, F2 + 0.15, 1.4, 1.85);
  bx('render', 0.3, 5.8, C1, F2 + 0.15, 1.4, 1.85);
  bx('render', 0, 0.1, F1, C1, 1.85, 3.4);
  bx('render', 6.0, 6.1, F1, C1, 1.85, 3.4);
  bx('paint', 0, 0.1, F1, C1, 3.4, 13.44);
  bx('paint', 6.0, 6.1, F1, C1, 3.4, 14.26);
  bx('patio', 0.1, 6.0, F1, F1 + 0.02, 1.5, 3.4, F.PY);
  bx('patio', 0.1, 2.45, F1, F1 + 0.02, 3.4, 4.85, F.PY);
  railing(true, 0.3, 5.8, F1, 1.55);
  bx('render', 2.45, 6.0, C1 - 0.12, C1, 3.4, 3.55);
  glaze(2.45, 6.0, F1, C1 - 0.12, 3.475, 3, hero ? 1 : null);
  wallX('stone', 0.1, 2.45, F1, C1, 4.85, 5.0, [[0.55, 1.95, F1 + 1.55, F1 + 2.45]]);
  glaze(0.55, 1.95, F1 + 1.55, F1 + 2.45, 4.925, 2);
  bx('stone', 2.35, 2.45, F1, C1, 3.4, 4.85);
  latticeD(5.62, 1.9, 3.35, F1, C1 - 0.05);
  slats(0.3, 5.8, C1 + 0.1, F2, 1.85, 3.4);
  // rear
  bx('render', 0, 0.3, C0 - 0.35, F2 + 0.15, 14.93, 15.38);
  bx('render', 5.8, 6.1, C0 - 0.35, F2 + 0.15, 14.93, 15.38);
  bx('render', 0.3, 5.8, C1, F2 + 0.15, 14.93, 15.38);
  bx('render', 0, 0.1, F1, C1, 13.44, 14.93);
  bx('render', 6.0, 6.1, F1, C1, 14.26, 14.93);
  bx('patio', 0.1, 2.95, F1, F1 + 0.02, 13.44, 15.28, F.PY);
  bx('patio', 2.95, 6.0, F1, F1 + 0.02, 14.26, 15.28, F.PY);
  railing(true, 0.3, 5.8, F1, 15.2);
  wallX('stone', 0.1, 2.95, F1, C1, 13.29, 13.44, [[0.35, 2.6, F1, F1 + 2.7]]);
  glaze(0.35, 2.6, F1, F1 + 2.7, 13.365, 2, hero ? 1 : null);
  bx('stone', 2.95, 3.05, F1, C1, 13.29, 14.26);
  wallX('stone', 3.05, 6.0, F1, C1, 14.11, 14.26, [[3.3, 5.75, F1, F1 + 2.7]]);
  glaze(3.3, 5.75, F1, F1 + 2.7, 14.185, 2, hero ? 0 : null);
  latticeD(0.38, 13.5, 14.9, F1, C1 - 0.05);
  slats(0.3, 2.95, C1 + 0.1, F2, 13.44, 14.93);
  slats(3.05, 5.8, C1 + 0.1, F2, 14.26, 14.93);
  spots.flower.push([0.6, F1, 2.0, 0.55], [5.2, F1 + 0.02, 14.8, 0.5]);

  // ---------- roof
  bx('render', 0.1, 6.0, C1, F2, 3.4, 6.65);
  bx('render', 2.95, 6.0, C1, F2, 6.65, 9.45);
  bx('render', 0.1, 6.0, C1, F2, 9.45, 13.44);
  bx('render', 2.95, 6.0, C1, F2, 13.44, 14.26);
  bx('gravel', 0.1, 6.0, F2, F2 + 0.04, 3.6, 6.6, F.PY);
  bx('render', 0, 6.1, F2, F2 + 0.55, 3.4, 3.6);
  bx('render', 0, 0.1, F2, F2 + 0.55, 3.6, 6.6);
  bx('render', 6.0, 6.1, F2, F2 + 0.55, 3.6, 7.95);
  bx('gravel', 4.5, 6.0, F2, F2 + 0.04, 6.6, 7.95, F.PY);
  wallX('render', 0.1, 4.5, F2, C2, 6.6, 6.75, [[1.15, 1.65, F2 + 0.45, C2 - 0.35]]);
  glaze(1.15, 1.65, F2 + 0.45, C2 - 0.35, 6.675, 1);
  wallD('render', 4.4, 4.5, F2, C2, 6.75, 7.95, [[6.95, 7.85, F2, F2 + 2.4]]);
  glazeD(4.45, 6.95, 7.85, F2, F2 + 2.4);
  wallX('render', 4.4, 6.0, F2, C2, 7.95, 8.1, [[4.85, 5.65, F2 + 0.9, F2 + 2.4]]);
  glaze(4.85, 5.65, F2 + 0.9, F2 + 2.4, 8.025, 1);
  wallX('stone', 0.1, 2.9, F2, C2, 11.05, 11.2, [[0.5, 1.6, F2 + 1.4, F2 + 2.4]]);
  glaze(0.5, 1.6, F2 + 1.4, F2 + 2.4, 11.125, 1);
  wallX('render', 2.9, 6.0, F2, C2, 11.05, 11.2, [[2.9, 5.65, F2, F2 + 2.75]]);
  glaze(2.9, 5.65, F2, F2 + 2.75, 11.125, 2, hero ? 1 : null);
  bx('paint', 0, 0.1, F2, C2, 6.6, 11.2);
  bx('paint', 6.0, 6.1, F2, C2, 7.95, 11.2);
  bx('render', 0, 4.5, C2, R2, 6.3, 11.2);
  bx('render', 4.5, 6.1, C2, R2, 7.65, 11.2);
  bx('wood', 0, 4.5, C2 + 0.06, R2 - 0.06, 6.27, 6.3);
  bx('wood', 4.5, 6.1, C2 + 0.06, R2 - 0.06, 7.62, 7.65);
  bx('wood', 4.5, 4.53, C2 + 0.06, R2 - 0.06, 6.3, 7.65);
  bx('render', 0, 0.25, C2, R2, 11.2, 12.95);
  bx('render', 5.85, 6.1, C2, R2, 11.2, 12.95);
  bx('render', 0.25, 5.85, C2, R2, 12.7, 12.95);
  bx('wood', 0, 6.1, C2 + 0.06, R2 - 0.06, 12.95, 12.98);
  slats(0.25, 5.85, C2 + 0.06, R2 - 0.04, 11.2, 12.7, 0.15, 0.04);
  bx('led', 0.3, 5.8, C2 - 0.02, C2, 12.6, 12.66);
  bx('patio', 0.1, 6.0, F2, F2 + 0.02, 11.2, 13.29, F.PY);
  bx('patio', 3.05, 6.0, F2, F2 + 0.02, 13.29, 14.11, F.PY);
  bx('render', 0.1, 2.95, F2, F2 + 0.15, 13.29, 13.44);
  bx('render', 2.95, 6.0, F2, F2 + 0.15, 14.11, 14.26);
  bx('render', 2.95, 3.05, F2, F2 + 0.15, 13.29, 14.26);
  railing(true, 0.1, 2.95, F2 + 0.15, 13.365, 0.95);
  railing(true, 3.05, 6.0, F2 + 0.15, 14.185, 0.95);
  railing(false, 13.44, 14.11, F2 + 0.15, 3.0, 0.95);
  bx('render', 0, 0.1, F2, F2 + 1.7, 11.2, 13.44);
  bx('render', 6.0, 6.1, F2, F2 + 1.7, 11.2, 14.26);

  if (!hero) {
    room(0.1, 6.0, F0, C0, 13.4, false);
    room(3.3, 6.0, F0, C0, 7.6, true);
    room(2.45, 6.0, F1, C1, 5.4, true);
    room(0.1, 2.95, F1, C1, 11.6, false);
    room(3.05, 6.0, F1, C1, 12.4, false);
    room(2.9, 6.0, F2, C2, 9.4, false);
    room(4.6, 5.9, F2 + 0.3, C2, 8.7, true);
    B.quad('room', [4.25, F2, -6.95], [4.25, F2, -7.85], [4.25, F2 + 2.4, -7.85], [4.25, F2 + 2.4, -6.95]);
  }
  return spots;
}
