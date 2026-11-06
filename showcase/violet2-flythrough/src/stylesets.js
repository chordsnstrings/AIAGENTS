import * as THREE from 'three';
import { H } from './plan.js';
import { bushGeometry } from './vegetation.js';

// Switchable furnishing for the three rooms the flight dwells in (living, dining, master).
// Everything else is shared and restyled through materials (styles.js). Each set is built
// once and toggled, so switching costs no geometry work.

export function buildStyleSet(B, key, K) {
  const { F0, C0, F1, C1 } = H;
  const yG = F0 + 0.012, yF = F1 + 0.012;
  const { M4, bx, rb, cyl, sphere, chair, loungeChair, bed, frameArtX } = K;
  const add = (k, geo, m, uv = 'box') => B.add(k, geo, m, uv);
  const S = (x, y, d, sx, sy, sz, ry = 0) => new THREE.Matrix4().compose(new THREE.Vector3(x, y, -d), new THREE.Quaternion().setFromEuler(new THREE.Euler(0, ry, 0)), new THREE.Vector3(sx, sy, sz));
  const ellipsoid = (k, x, y, d, rx, ry, rz) => add(k, new THREE.SphereGeometry(1, 40, 20), S(x, y, d, rx, ry, rz));
  const oval = (k, x, y, d, rx, rz, h) => add(k, new THREE.CylinderGeometry(1, 1, h, 64), S(x, y, d, rx, 1, rz));
  const potPlant = (leaf, x, y, d, s = 1, pot = 'concrete', h = 1.25) => {
    cyl(pot, x, y + 0.27 * s, d, 0.26 * s, 0.2 * s, 0.54 * s, 28);
    cyl('soil', x, y + 0.53 * s, d, 0.24 * s, 0.24 * s, 0.02, 20);
    cyl('bark', x, y + (0.54 + h * 0.4) * s, d, 0.022 * s, 0.035 * s, h * 0.8 * s, 8);
    add(leaf, bushGeometry(18, 4 + Math.round(x * 13 + d), 1.0), S(x, y + h * s, d, 0.8 * s, 0.8 * s, 0.8 * s), 'keep');
  };
  const cable = (x, d, yTop, yBot) => cyl('frame', x, (yTop + yBot) / 2, d, 0.003, 0.003, yTop - yBot, 6);
  const rug = (cx, cd, w, l, y = yG + 0.008, organic = false) => {
    if (!organic) return rb('rug', cx, y, cd, w, 0.016, l, 0.008);
    const sh = new THREE.Shape();
    for (let i = 0; i <= 48; i++) {
      const a = i / 48 * Math.PI * 2, r = 1 + 0.07 * Math.sin(a * 3 + 0.6) + 0.04 * Math.sin(a * 5);
      const px = Math.cos(a) * w / 2 * r, pz = Math.sin(a) * l / 2 * r;
      if (i === 0) sh.moveTo(px, pz); else sh.lineTo(px, pz);
    }
    const g = new THREE.ExtrudeGeometry(sh, { depth: 0.014, bevelEnabled: false, curveSegments: 4 });
    g.rotateX(Math.PI / 2);
    add('rug', g, new THREE.Matrix4().makeTranslation(cx, y + 0.007, -cd));
  };
  // arch outline in the (along-d, up) plane, extruded towards the room from a wall at x
  const arch = (k, x, d0, d1, y0, straight, depth, toMinusX = true) => {
    const w = d1 - d0, r = w / 2, sh = new THREE.Shape();
    sh.moveTo(-r, 0); sh.lineTo(r, 0); sh.lineTo(r, straight); sh.absarc(0, straight, r, 0, Math.PI, false); sh.lineTo(-r, 0);
    const g = new THREE.ExtrudeGeometry(sh, { depth, bevelEnabled: true, bevelThickness: Math.min(0.03, depth / 3), bevelSize: 0.025, bevelSegments: 3, curveSegments: 36 });
    const m = new THREE.Matrix4().makeTranslation(x, y0, -(d0 + d1) / 2).multiply(new THREE.Matrix4().makeRotationY(toMinusX ? -Math.PI / 2 : Math.PI / 2));
    add(k, g, m);
  };
  // seats on an arc around (cx, cd), facing the centre
  const crescent = (k, cx, cd, R, a0, a1, n) => {
    for (let i = 0; i < n; i++) {
      const a = a0 + (a1 - a0) * (i + 0.5) / n;
      const x = cx + Math.cos(a) * R, d = cd + Math.sin(a) * R;
      const P = M4(x, yG, d, Math.atan2(-Math.cos(a), Math.sin(a)));
      const w = 2 * R * Math.sin((a1 - a0) / n / 2) + 0.06;
      rb(k, 0, 0.21, 0, w, 0.42, 0.88, 0.07, 0, P);
      rb(k, 0, 0.47, -0.05, w - 0.03, 0.12, 0.74, 0.06, 0, P);
      rb(k, 0, 0.66, 0.36, w + 0.04, 0.46, 0.2, 0.09, 0, P);
    }
  };
  const barrel = (k, x, y, d, ry, cushion) => { // tub/barrel chair: drum seat + arced back
    const P = M4(x, y, d, ry);
    cyl(k, x, y + 0.21, d, 0.34, 0.32, 0.42, 32);
    if (cushion) cyl(cushion, x, y + 0.46, d, 0.3, 0.3, 0.09, 32);
    for (let i = 0; i < 7; i++) {
      const a = -Math.PI / 2 + (i / 6 - 0.5) * 3.4;
      rb(k, Math.cos(a) * 0.3, 0.55, -Math.sin(a) * 0.3, 0.17, 0.42, 0.1, 0.04, Math.PI / 2 - a, P);
    }
  };
  const lantern = (x, y, d, r, h) => { // pleated paper drum
    const g = new THREE.CylinderGeometry(r, r, h, 64, 6, true);
    const p = g.attributes.position;
    for (let i = 0; i < p.count; i++) {
      const vx = p.getX(i), vz = p.getZ(i), a = Math.atan2(vz, vx), seg = Math.round(a / (Math.PI * 2) * 64);
      const k = (seg % 2 ? 1.05 : 0.97) * (1 - 0.12 * Math.pow(p.getY(i) / (h / 2), 2));
      p.setX(i, vx * k); p.setZ(i, vz * k);
    }
    g.computeVertexNormals();
    add('lampShade', g, M4(x, y, d), 'keep');
  };
  const dome = (k, x, y, d, r) => add(k, new THREE.SphereGeometry(r, 40, 14, 0, Math.PI * 2, 0, Math.PI / 2), M4(x, y, d), 'box');

  // ------------------------------------------------------------------ WARM MINIMAL
  if (key === 'minimal') {
    bx('travertineSlab', 0.1, 0.14, F0, C0, 11.0, 14.45);
    bx('tv', 0.14, 0.18, F0 + 1.05, F0 + 2.0, 11.95, 13.65);
    rb('walnut', 0.37, F0 + 0.36, 12.8, 0.44, 0.34, 2.7, 0.015);
    rb('ceramic', 0.33, F0 + 0.64, 11.75, 0.12, 0.22, 0.12, 0.05);
    rb('linenSand', 0.36, F0 + 0.56, 13.6, 0.26, 0.06, 0.34, 0.01);
    rug(1.75, 12.75, 3.0, 3.5);
    rb('blackSatin', 2.92, yG + 0.04, 12.75, 0.86, 0.08, 2.4, 0.01);
    rb('boucle', 2.9, yG + 0.23, 12.75, 1.02, 0.3, 2.56, 0.06);
    for (const d of [12.06, 12.75, 13.44]) rb('boucle', 2.8, yG + 0.45, d, 0.84, 0.16, 0.67, 0.07);
    for (const d of [12.06, 12.75, 13.44]) rb('boucle', 3.27, yG + 0.68, d, 0.24, 0.44, 0.67, 0.1);
    rb('boucle', 2.9, yG + 0.47, 11.6, 1.02, 0.5, 0.22, 0.09);
    rb('boucle', 2.9, yG + 0.47, 13.9, 1.02, 0.5, 0.22, 0.09);
    rb('velvet', 3.05, yG + 0.72, 12.0, 0.14, 0.42, 0.42, 0.07, 0.25);
    rb('linenSand', 3.05, yG + 0.7, 13.5, 0.14, 0.4, 0.4, 0.07, -0.2);
    cyl('travertineSlab', 1.55, F0 + 0.18, 12.55, 0.5, 0.5, 0.34, 48);
    cyl('walnut', 1.85, F0 + 0.13, 13.4, 0.3, 0.3, 0.24, 40);
    rb('linenSand', 1.45, F0 + 0.38, 12.45, 0.32, 0.05, 0.24, 0.01);
    rb('velvet', 1.45, F0 + 0.42, 12.45, 0.28, 0.03, 0.2, 0.01);
    sphere('ceramic', 1.72, F0 + 0.4, 12.7, 0.07);
    barrel('boucle', 1.0, yG, 11.25, Math.PI * 0.88, 'boucle');
    cyl('brass', 0.45, yG + 0.8, 14.25, 0.012, 0.012, 1.55, 8);
    cyl('brass', 0.45, yG + 0.01, 14.25, 0.14, 0.14, 0.02, 24);
    cyl('lampShade', 0.45, yG + 1.65, 14.25, 0.2, 0.22, 0.3, 32, null, true);
    potPlant('leafOlive', 5.5, yG, 14.3, 1.25);
    // oval oak pedestal table, globe cluster
    oval('oak', 4.85, yG + 0.75, 12.7, 0.5, 1.0, 0.045);
    for (const d of [12.25, 13.15]) { cyl('oak', 4.85, yG + 0.37, d, 0.09, 0.15, 0.72, 24); cyl('oak', 4.85, yG + 0.02, d, 0.24, 0.24, 0.03, 32); }
    for (const d of [12.1, 12.7, 13.3]) { chair(4.15, d, Math.PI / 2, 'boucle'); chair(5.55, d, -Math.PI / 2, 'boucle'); }
    for (const [d, drop, r] of [[12.25, 0.7, 0.13], [12.7, 0.95, 0.16], [13.15, 0.78, 0.12]]) { cable(4.85, d, C0, C0 - drop); sphere('bulb', 4.85, C0 - drop - r * 0.9, d, r); }
    // master: fluted oak wall, padded headboard
    for (let d = 3.62; d < 6.55; d += 0.06) bx('oak', 5.965, 6.0, F1, F1 + 2.55, d - 0.022, d + 0.022);
    bx('led', 5.95, 5.97, F1 + 2.55, F1 + 2.57, 3.6, 6.55);
    bed(4.9, 5.05, yF, 1.8, 2.05, 5.96);
    rug(4.5, 5.05, 3.0, 3.0, yF + 0.008);
    rb('velvet', 3.42, yF + 0.23, 5.05, 0.42, 0.44, 1.5, 0.06);
    barrel('boucle', 2.95, yF, 4.05, Math.PI * 0.75, 'boucle');
    cyl('travertineSlab', 2.85, yF + 0.27, 4.75, 0.2, 0.2, 0.55, 32);
  }

  // ------------------------------------------------------------------ JAPANDI CALM
  if (key === 'japandi') {
    bx('blackSatin', 0.1, 0.11, F0, C0, 10.9, 14.5);
    for (let d = 10.94; d < 14.48; d += 0.075) bx('oak', 0.11, 0.16, F0, C0, d - 0.022, d + 0.022);
    bx('tv', 0.17, 0.2, F0 + 1.0, F0 + 1.9, 12.0, 13.6);
    rb('oak', 0.45, yG + 0.16, 12.8, 0.5, 0.3, 3.1, 0.01);
    rb('ceramic', 0.42, yG + 0.42, 11.55, 0.16, 0.22, 0.16, 0.07);
    cyl('bark', 0.42, yG + 0.78, 11.55, 0.005, 0.009, 0.55, 6);
    rug(1.8, 12.75, 2.9, 3.3);
    rb('oak', 2.95, yG + 0.09, 12.75, 1.06, 0.18, 2.75, 0.012);
    for (const d of [12.0, 12.75, 13.5]) rb('boucle', 2.86, yG + 0.26, d, 0.86, 0.16, 0.73, 0.06);
    for (const d of [12.0, 12.75, 13.5]) rb('boucle', 3.3, yG + 0.5, d, 0.2, 0.42, 0.73, 0.09);
    rb('oak', 2.95, yG + 0.3, 11.36, 1.02, 0.26, 0.05, 0.01);
    rb('oak', 2.95, yG + 0.3, 14.14, 1.02, 0.26, 0.05, 0.01);
    rb('velvet', 3.1, yG + 0.5, 12.25, 0.12, 0.32, 0.32, 0.06, 0.2);
    rb('linenSand', 2.6, yG + 0.36, 13.7, 0.5, 0.04, 0.4, 0.01, 0.3);
    rb('oak', 1.6, yG + 0.16, 12.75, 0.75, 0.32, 1.2, 0.03);
    rb('ceramic', 1.55, yG + 0.36, 12.4, 0.2, 0.08, 0.2, 0.04);
    rb('linenSand', 1.65, yG + 0.34, 13.05, 0.24, 0.04, 0.3, 0.01);
    { // black-ash lounge chair with paper-cord seat and back
      const P = M4(1.0, yG, 11.25, Math.PI * 0.88);
      for (const [lx, lz] of [[-0.3, -0.3], [0.3, -0.3], [-0.3, 0.3], [0.3, 0.3]]) rb('walnut', lx, 0.2, lz, 0.04, 0.4, 0.04, 0.008, 0, P);
      for (const lx of [-0.3, 0.3]) rb('walnut', lx, 0.5, 0.0, 0.04, 0.04, 0.66, 0.008, 0, P);
      rb('weave', 0, 0.36, 0.02, 0.56, 0.04, 0.56, 0.01, 0, P);
      rb('weave', 0, 0.62, 0.3, 0.56, 0.46, 0.04, 0.01, 0, P, -0.28);
      rb('velvet', 0, 0.42, 0.02, 0.5, 0.06, 0.5, 0.03, 0, P);
    }
    cyl('brass', 0.45, yG + 0.75, 14.25, 0.009, 0.009, 1.5, 8);
    cyl('brass', 0.45, yG + 0.01, 14.25, 0.13, 0.13, 0.02, 24);
    sphere('lampShade', 0.45, yG + 1.62, 14.25, 0.2);
    rb('travertineSlab', 5.5, yG + 0.21, 14.25, 0.5, 0.42, 0.5, 0.01);
    potPlant('leaf', 5.5, yG + 0.42, 14.25, 0.95, 'concrete', 1.4);
    // trestle table, spindle chairs, bench, pleated paper lantern
    rb('oak', 4.85, yG + 0.74, 12.7, 0.92, 0.05, 2.0, 0.008);
    for (const d of [11.95, 13.45]) { rb('walnut', 4.85, yG + 0.36, d, 0.66, 0.68, 0.06, 0.005); rb('walnut', 4.85, yG + 0.03, d, 0.82, 0.06, 0.09, 0.005); }
    rb('walnut', 4.85, yG + 0.28, 12.7, 0.05, 0.05, 1.5, 0.004);
    for (const d of [12.1, 12.7, 13.3]) {
      const P = M4(4.15, yG, d, Math.PI / 2);
      rb('weave', 0, 0.45, 0, 0.46, 0.04, 0.44, 0.01, 0, P);
      for (const [lx, lz] of [[-0.2, -0.19], [0.2, -0.19], [-0.2, 0.19], [0.2, 0.19]]) rb('walnut', lx, 0.22, lz, 0.03, 0.45, 0.03, 0.005, 0, P);
      rb('walnut', 0, 0.86, 0.21, 0.46, 0.05, 0.03, 0.01, 0, P);
      for (let i = -2; i <= 2; i++) rb('walnut', i * 0.085, 0.66, 0.21, 0.016, 0.38, 0.016, 0.006, 0, P);
    }
    rb('oak', 5.5, yG + 0.43, 12.7, 0.36, 0.05, 1.7, 0.008);
    for (const d of [11.95, 13.45]) rb('walnut', 5.5, yG + 0.21, d, 0.3, 0.42, 0.05, 0.004);
    cable(4.85, 12.7, C0, C0 - 0.6);
    lantern(4.85, C0 - 0.85, 12.7, 0.38, 0.5);
    // master: floor-level platform bed, slatted oak headboard
    rb('oak', 4.85, yF + 0.08, 5.05, 2.25, 0.16, 2.1, 0.01);
    for (let d = 4.05; d < 6.07; d += 0.07) bx('oak', 5.9, 5.96, yF, yF + 1.05, d - 0.024, d + 0.024);
    bed(4.85, 5.05, yF - 0.08, 1.8, 2.0, 5.86, 'linen', false);
    rug(4.4, 5.05, 2.8, 2.9, yF + 0.008);
    rb('oak', 3.45, yF + 0.2, 5.05, 0.38, 0.06, 1.2, 0.01);
    for (const d of [4.55, 5.55]) rb('walnut', 3.45, yF + 0.09, d, 0.32, 0.18, 0.05, 0.004);
    { const P = M4(2.95, yF, 4.05, Math.PI * 0.75);
      for (const [lx, lz] of [[-0.3, -0.3], [0.3, -0.3], [-0.3, 0.3], [0.3, 0.3]]) rb('walnut', lx, 0.2, lz, 0.04, 0.4, 0.04, 0.008, 0, P);
      rb('weave', 0, 0.36, 0.02, 0.56, 0.04, 0.56, 0.01, 0, P);
      rb('weave', 0, 0.62, 0.3, 0.56, 0.46, 0.04, 0.01, 0, P, -0.28); }
    cyl('travertineSlab', 2.85, yF + 0.2, 4.75, 0.22, 0.22, 0.4, 32);
  }

  // ------------------------------------------------------------------ DESERT ORGANIC
  if (key === 'desert') {
    bx('paint', 0.1, 0.3, F0, C0, 10.85, 14.55);
    for (const [d0, d1] of [[11.25, 12.25], [13.25, 14.25]]) {
      arch('travertineSlab', 0.3, d0, d1, yG + 0.75, 0.75, 0.02, false);
      bx('led', 0.3, 0.33, yG + 1.75, yG + 1.77, d0 + 0.2, d1 - 0.2);
      bx('travertineSlab', 0.3, 0.42, yG + 1.0, yG + 1.03, d0 + 0.05, d1 - 0.05);
    }
    cyl('concrete', 0.36, yG + 1.16, 11.6, 0.07, 0.05, 0.26, 20);
    sphere('ceramic', 0.36, yG + 1.09, 11.95, 0.06);
    cyl('concrete', 0.36, yG + 1.2, 13.75, 0.08, 0.06, 0.34, 20);
    rb('paint', 0.62, yG + 0.2, 12.75, 0.62, 0.4, 3.3, 0.14);
    rb('linenSand', 0.64, yG + 0.45, 12.75, 0.54, 0.1, 3.1, 0.05);
    rb('velvet', 0.45, yG + 0.66, 12.1, 0.12, 0.34, 0.34, 0.07, 0.15);
    rb('linenSand', 0.45, yG + 0.66, 13.4, 0.12, 0.34, 0.34, 0.07, -0.1);
    rug(1.7, 12.75, 2.7, 3.1, yG + 0.008, true);
    crescent('boucle', 1.0, 12.75, 2.15, -0.92, 0.92, 6);
    rb('velvet', 2.75, yG + 0.68, 12.25, 0.12, 0.36, 0.36, 0.07, 0.4);
    rb('velvet', 2.8, yG + 0.66, 13.35, 0.12, 0.32, 0.32, 0.06, -0.3);
    ellipsoid('travertineSlab', 1.6, yG + 0.16, 12.55, 0.55, 0.17, 0.42);
    ellipsoid('travertineSlab', 1.75, yG + 0.11, 13.45, 0.3, 0.12, 0.25);
    sphere('ceramic', 1.5, yG + 0.36, 12.45, 0.07);
    cyl('paint', 1.4, yG + 0.5, 14.42, 0.09, 0.14, 1.0, 24);
    sphere('paint', 1.4, yG + 1.06, 14.42, 0.13);
    sphere('lampShade', 1.4, yG + 1.33, 14.42, 0.16);
    potPlant('leafOlive', 5.5, yG, 14.3, 1.2, 'concrete');
    // oval elm pedestal table, cane-back chairs, rattan dome
    oval('walnut', 4.85, yG + 0.75, 12.7, 0.5, 0.98, 0.045);
    for (const d of [12.3, 13.1]) { cyl('walnut', 4.85, yG + 0.37, d, 0.08, 0.15, 0.72, 24); cyl('walnut', 4.85, yG + 0.02, d, 0.26, 0.26, 0.03, 32); }
    for (const [x, ry] of [[4.15, Math.PI / 2], [5.55, -Math.PI / 2]]) for (const d of [12.1, 12.7, 13.3]) {
      const P = M4(x, yG, d, ry);
      rb('weave', 0, 0.46, 0, 0.46, 0.05, 0.44, 0.015, 0, P);
      for (const [lx, lz] of [[-0.2, -0.19], [0.2, -0.19], [-0.2, 0.19], [0.2, 0.19]]) rb('walnut', lx, 0.22, lz, 0.035, 0.45, 0.035, 0.008, 0, P);
      rb('walnut', 0, 0.78, 0.2, 0.46, 0.4, 0.04, 0.02, 0, P, -0.1);
      rb('weave', 0, 0.78, 0.17, 0.38, 0.32, 0.02, 0.005, 0, P, -0.1);
    }
    cable(4.85, 12.7, C0, C0 - 0.55);
    dome('weave', 4.85, C0 - 0.95, 12.7, 0.46);
    sphere('bulb', 4.85, C0 - 0.82, 12.7, 0.07);
    // master: arched mauve headboard, rattan barrel chair, rattan bench
    arch('velvet', 5.96, 4.1, 6.0, yF + 0.2, 0.7, 0.1, true);
    bed(4.85, 5.05, yF, 1.8, 2.0, 5.84, 'linen', false);
    rug(4.35, 5.05, 2.9, 3.0, yF + 0.008, true);
    rb('weave', 3.4, yF + 0.22, 5.05, 0.4, 0.44, 1.35, 0.05);
    barrel('weave', 2.95, yF, 4.05, Math.PI * 0.75, 'velvet');
    potPlant('leafOlive', 2.75, yF, 6.25, 0.9, 'concrete');
  }

  // ------------------------------------------------------------------ AUBERGINE LUXE
  if (key === 'luxe') {
    for (let d = 10.93; d < 14.47; d += 0.06) bx('walnut', 0.1, 0.15, F0, C0, d - 0.024, d + 0.024);
    for (const d of [11.68, 13.82]) bx('brass', 0.1, 0.153, F0, C0, d - 0.008, d + 0.008);
    bx('travertineSlab', 0.15, 0.56, F0, F0 + 0.62, 11.75, 13.75);
    bx('charcoal', 0.42, 0.562, F0 + 0.17, F0 + 0.5, 12.1, 13.4);
    bx('fire', 0.44, 0.52, F0 + 0.18, F0 + 0.23, 12.2, 13.3);
    bx('travertineSlab', 0.15, 0.64, F0 + 0.62, F0 + 0.67, 11.7, 13.8);
    frameArtX('art1', 0.16, 12.1, 13.4, F0 + 1.15, F0 + 2.3, true);
    bx('brass', 0.16, 0.25, F0 + 2.38, F0 + 2.42, 12.35, 13.15);
    rug(1.85, 12.75, 2.9, 3.4);
    rb('blackSatin', 2.95, yG + 0.04, 12.75, 0.9, 0.08, 2.5, 0.01);
    rb('boucle', 2.92, yG + 0.24, 12.75, 1.08, 0.32, 2.7, 0.05);
    rb('boucle', 2.84, yG + 0.45, 12.75, 0.9, 0.12, 2.32, 0.05);
    rb('boucle', 3.34, yG + 0.66, 12.75, 0.24, 0.54, 2.7, 0.06);
    rb('boucle', 2.92, yG + 0.47, 11.46, 1.08, 0.46, 0.18, 0.06);
    rb('boucle', 2.92, yG + 0.47, 14.04, 1.08, 0.46, 0.18, 0.06);
    rb('linenSand', 3.15, yG + 0.68, 11.9, 0.14, 0.4, 0.4, 0.07, 0.2);
    rb('linenSand', 3.15, yG + 0.68, 13.6, 0.14, 0.4, 0.4, 0.07, -0.2);
    rb('travertineSlab', 1.6, yG + 0.17, 12.75, 0.85, 0.34, 1.4, 0.008);
    for (const [x0, x1, d0, d1] of [[1.17, 2.03, 12.04, 12.06], [1.17, 2.03, 13.44, 13.46], [1.17, 1.19, 12.05, 13.45], [2.01, 2.03, 12.05, 13.45]]) bx('brass', x0, x1, yG + 0.335, yG + 0.345, d0, d1);
    sphere('brass', 1.5, yG + 0.42, 12.45, 0.075);
    rb('brass', 1.72, yG + 0.36, 13.05, 0.2, 0.04, 0.14, 0.01);
    loungeChair(1.0, yG, 11.25, Math.PI * 0.88, 'velvet');
    rb('velvet', 1.55, yG + 0.2, 10.95, 0.5, 0.36, 0.42, 0.05);
    cyl('brass', 0.5, yG + 0.85, 14.25, 0.012, 0.018, 1.7, 8);
    cyl('brass', 0.5, yG + 0.012, 14.25, 0.15, 0.17, 0.025, 24);
    cyl('brass', 0.5, yG + 1.74, 14.25, 0.2, 0.06, 0.12, 32, null, true);
    cyl('bulb', 0.5, yG + 1.79, 14.25, 0.17, 0.17, 0.006, 24);
    potPlant('leaf', 5.5, yG, 14.3, 1.15, 'concrete', 1.5);
    add('leaf', bushGeometry(16, 31, 1.0), S(5.45, yG + 2.05, 14.25, 0.7, 0.7, 0.7), 'keep');
    // racetrack walnut table, velvet barrel chairs, Murano-glass chandelier
    oval('walnut', 4.85, yG + 0.755, 12.7, 0.5, 1.02, 0.05);
    for (const d of [12.3, 13.1]) { cyl('walnut', 4.85, yG + 0.37, d, 0.1, 0.14, 0.72, 24); cyl('brass', 4.85, yG + 0.02, d, 0.24, 0.24, 0.03, 32); }
    for (const [x, ry] of [[4.12, Math.PI / 2], [5.58, -Math.PI / 2]]) for (const d of [12.1, 12.7, 13.3]) barrel('linenSand', x, yG, d, ry, null);
    cyl('brass', 4.85, C0 - 0.35, 12.7, 0.012, 0.012, 0.7, 8);
    add('brass', new THREE.TorusGeometry(0.34, 0.012, 8, 48), new THREE.Matrix4().makeTranslation(4.85, C0 - 0.72, -12.7).multiply(new THREE.Matrix4().makeRotationX(Math.PI / 2)));
    for (let i = 0; i < 12; i++) {
      const a = i / 12 * Math.PI * 2, r = i % 2 ? 0.34 : 0.22, drop = i % 2 ? 0.16 : 0.3;
      const x = 4.85 + Math.cos(a) * r, d = 12.7 + Math.sin(a) * r;
      cable(x, d, C0 - 0.72, C0 - 0.72 - drop);
      sphere('bulb', x, C0 - 0.78 - drop, d, 0.06);
    }
    // master: wall-to-wall channelled aubergine headboard
    for (let d = 3.7; d < 6.52; d += 0.2) rb('boucle', 5.9, yF + 0.95, d, 0.12, 1.5, 0.19, 0.05);
    bx('brass', 5.84, 5.98, yF + 1.7, yF + 1.72, 3.62, 6.55);
    bed(4.85, 5.05, yF, 1.8, 2.05, 5.84, 'linen', false);
    rug(4.45, 5.05, 3.0, 3.0, yF + 0.008);
    rb('velvet', 3.4, yF + 0.23, 5.05, 0.44, 0.44, 1.5, 0.06);
    loungeChair(2.95, yF, 4.05, Math.PI * 0.75, 'velvet');
    cyl('travertineSlab', 2.85, yF + 0.27, 4.75, 0.2, 0.2, 0.55, 32);
  }
}
