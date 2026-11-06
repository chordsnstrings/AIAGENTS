import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { H } from './plan.js';
import { F } from './builder.js';
import { drape, pillow, sheer } from './softgoods.js';

// Interior of the hero unit only: finishes, stair, doors, kitchen, bathrooms and a minimal
// warm-modern furniture scheme at true sizes. Everything is placed in plan coordinates.

const _q = new THREE.Quaternion(), _e = new THREE.Euler(), _s = new THREE.Vector3(1, 1, 1), _p = new THREE.Vector3();
const M4 = (x, y, d, ry = 0, rx = 0, rz = 0) =>
  new THREE.Matrix4().compose(_p.set(x, y, -d), _q.setFromEuler(_e.set(rx, ry, rz, 'YXZ')), _s);

// Placement helpers shared by the base interior and the switchable style sets.
export function makeKit(B, spots) {
  const { F0, C0, F1, C1, F2, C2 } = H;
  const bx = (k, x0, x1, y0, y1, d0, d1, f) => B.box(k, x0, x1, y0, y1, -d1, -d0, f);
  const rbCache = new Map();
  const rbGeo = (sx, sy, sz, r) => {
    const key = [sx, sy, sz, r].map((v) => v.toFixed(3)).join();
    if (!rbCache.has(key)) rbCache.set(key, new RoundedBoxGeometry(sx, sy, sz, 3, Math.max(0.002, Math.min(r, sx / 2 - 1e-3, sy / 2 - 1e-3, sz / 2 - 1e-3))));
    return rbCache.get(key);
  };
  // rounded box centred at (x, y, d); with a parent matrix the position is local to it
  const rb = (k, x, y, d, sx, sy, sz, r = 0.03, ry = 0, parent = null, rx = 0) => {
    const m = M4(x, y, d, ry, rx);
    B.add(k, rbGeo(sx, sy, sz, r), parent ? parent.clone().multiply(m) : m, 'box');
  };
  const cyl = (k, x, y, d, r0, r1, h, seg = 28, parent = null, open = false) => {
    const m = M4(x, y, d);
    B.add(k, new THREE.CylinderGeometry(r0, r1, h, seg, 1, open), parent ? parent.clone().multiply(m) : m, 'keep', 2);
  };
  const sphere = (k, x, y, d, r, parent = null) => {
    const m = M4(x, y, d);
    B.add(k, new THREE.SphereGeometry(r, 20, 14), parent ? parent.clone().multiply(m) : m);
  };
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
  // flush oak door leaf hinged at (hx, hd); ang 0 = closed along +x (alongX) or +d
  function door(hx, hd, y, w, ang, alongX = true, h = 2.4) {
    const base = alongX ? 0 : Math.PI / 2;
    const m = M4(hx, y, hd, base + ang).multiply(M4(w / 2, h / 2, 0));
    B.add('joinery', new THREE.BoxGeometry(w, h, 0.04), m, 'box');
    B.add('brass', new THREE.BoxGeometry(0.02, 0.18, 0.06), m.clone().multiply(M4(w / 2 - 0.08, -0.15, 0)), 'box');
  }
  const quadArt = (k, x0, x1, y0, y1, d, facing) => { // facing: 'street' (+z) or 'rear' (-z) or '+x' / '-x'
    if (facing === 'rear') B.quad(k, [x1, y0, -d], [x0, y0, -d], [x0, y1, -d], [x1, y1, -d]);
    else if (facing === 'street') B.quad(k, [x0, y0, -d], [x1, y0, -d], [x1, y1, -d], [x0, y1, -d]);
  };
  const quadArtX = (k, x, d0, d1, y0, y1, facingPlusX) => facingPlusX
    ? B.quad(k, [x, y0, -d0], [x, y0, -d1], [x, y1, -d1], [x, y1, -d0])
    : B.quad(k, [x, y0, -d1], [x, y0, -d0], [x, y1, -d0], [x, y1, -d1]);
  function frameArt(k, x0, x1, y0, y1, d, facing) {
    const s = facing === 'rear' ? 1 : -1;
    bx('walnut', x0 - 0.025, x1 + 0.025, y0 - 0.025, y1 + 0.025, d - 0.005 * s, d + 0.025 * s);
    quadArt(k, x0, x1, y0, y1, d + 0.027 * s, facing);
  }
  function frameArtX(k, x, d0, d1, y0, y1, facingPlusX) {
    const s = facingPlusX ? 1 : -1;
    bx('walnut', x - 0.005 * s, x + 0.025 * s, y0 - 0.025, y1 + 0.025, d0 - 0.025, d1 + 0.025);
    quadArtX(k, x + 0.027 * s, d0, d1, y0, y1, facingPlusX);
  }
  // pleated sheer curtain hanging in plane d between x0..x1
  function curtain(x0, x1, y0, y1, d) {
    B.add('sheer', sheer(x1 - x0, y1 - y0, Math.round(x0 * 13 + d * 7)), M4((x0 + x1) / 2, (y0 + y1) / 2, d), 'keep');
    bx('frame', x0 - 0.05, x1 + 0.05, y1, y1 + 0.03, d - 0.02, d + 0.02);
  }
  function curtainD(x, d0, d1, y0, y1) {
    B.add('sheer', sheer(d1 - d0, y1 - y0, Math.round(x * 13 + d0 * 7)), M4(x, (y0 + y1) / 2, (d0 + d1) / 2, Math.PI / 2), 'keep');
  }
  const downlight = (x, y, d) => B.add('downlight', new THREE.CylinderGeometry(0.045, 0.045, 0.01, 18), M4(x, y - 0.004, d));
  function lamp(x, y, d, h = 0.55, shadeR = 0.17) { // table lamp: ceramic base + linen drum
    cyl('ceramic', x, y + h * 0.3, d, 0.07, 0.09, h * 0.6, 20);
    cyl('lampShade', x, y + h * 0.8, d, shadeR * 0.9, shadeR, h * 0.4, 28, null, true);
  }
  function pendantGlobe(x, y, d, drop = 0.9, r = 0.11) {
    cyl('frame', x, y - drop / 2, d, 0.003, 0.003, drop, 6);
    sphere('bulb', x, y - drop - r * 0.8, d, r);
  }
  function chair(x, d, ry, seatK = 'boucle') {
    const P = M4(x, F0, d, ry);
    rb(seatK, 0, 0.47, 0, 0.47, 0.08, 0.46, 0.03, 0, P);
    rb('walnut', 0, 0.78, 0.21, 0.45, 0.36, 0.04, 0.02, 0, P, -0.12);
    for (const [lx, lz] of [[-0.19, -0.18], [0.19, -0.18], [-0.19, 0.18], [0.19, 0.18]]) rb('walnut', lx, 0.215, lz, 0.03, 0.43, 0.03, 0.008, 0, P);
  }
  function loungeChair(x, y, d, ry, k = 'velvet') {
    const P = M4(x, y, d, ry);
    rb(k, 0, 0.2, 0.02, 0.78, 0.22, 0.74, 0.08, 0, P);
    rb(k, 0, 0.36, 0.0, 0.62, 0.12, 0.62, 0.05, 0, P);
    rb(k, 0, 0.55, 0.32, 0.78, 0.5, 0.16, 0.08, 0, P, -0.18);
    rb(k, -0.35, 0.42, 0.02, 0.12, 0.3, 0.7, 0.05, 0, P);
    rb(k, 0.35, 0.42, 0.02, 0.12, 0.3, 0.7, 0.05, 0, P);
    rb('walnut', 0, 0.045, 0.02, 0.7, 0.09, 0.66, 0.02, 0, P);
  }
  function plant(x, y, d, s = 1, k = 'leafOlive') {
    cyl('concrete', x, y + 0.27 * s, d, 0.26 * s, 0.21 * s, 0.54 * s, 28);
    cyl('soil', x, y + 0.53 * s, d, 0.24 * s, 0.24 * s, 0.02, 20);
    cyl('bark', x, y + 0.95 * s, d, 0.025 * s, 0.04 * s, 0.85 * s, 8);
    spots[k === 'leafOlive' ? 'olive' : 'bush'].push([x, y + 1.25 * s, d, 0.85 * s]);
  }
  function bed(cx, d, y, w, len, headX, cover = 'linen', head = true) { // headboard against wall at headX (bed runs along x)
    const dir = headX > cx ? 1 : -1;
    const hx = headX - dir * 0.06;
    if (head) rb('boucle', hx, y + 0.62, d, 0.1, 1.15, w + 0.25, 0.045);
    const mid = headX - dir * (len / 2 + 0.11);
    rb('linenGrey', mid, y + 0.17, d, len, 0.28, w + 0.06, 0.04);
    rb('linen', mid, y + 0.41, d, len - 0.05, 0.22, w - 0.02, 0.07);
    // bed frame: local +x runs from the mattress head towards the foot, y 0 on the mattress top
    const top = y + 0.52, head0 = headX - dir * 0.11, seed = Math.round(cx * 31 + d * 17 + y * 7);
    const base = M4(head0, top, d, dir > 0 ? Math.PI : 0);
    const put = (k, g, x, yy, z, tilt = 0, uv = 'keep') => B.add(k, g, base.clone().multiply(new THREE.Matrix4().makeTranslation(x, yy, z)
      .multiply(new THREE.Matrix4().makeRotationZ(-tilt)).multiply(new THREE.Matrix4().makeRotationY(-Math.PI / 2))), uv);
    // duvet turned down below the pillows, with a rolled top edge; a throw across the foot
    const s0 = 0.6, dv = drape({ L: len - 0.05 - s0, W: w - 0.02, drop: 0.3, dropFoot: 0.27, seed });
    B.add(cover, dv, base.clone().multiply(new THREE.Matrix4().makeTranslation(s0, 0.004, 0)), 'keep');
    B.add(cover, new THREE.TubeGeometry(new THREE.CatmullRomCurve3(dv.userData.head), 60, 0.032, 8), base.clone().multiply(new THREE.Matrix4().makeTranslation(s0 + 0.012, 0.02, 0)), 'box');
    B.add('velvet', drape({ L: 0.48, W: w + 0.1, drop: 0.27, dropFoot: 0, r: 0.1, loft: 0.012, pleat: 0.04, seed: seed + 2 }),
      base.clone().multiply(new THREE.Matrix4().makeTranslation(len - 0.75, 0.055, 0)), 'keep');
    // two sleeping pillows leaning on the headboard, a pair of cushions in front
    const pl = Math.min(0.72, w * 0.44);
    for (const [i, o] of [-0.26, 0.26].entries()) put('linen', pillow({ L: pl, D: 0.5, T: 0.17, seed: seed + i }), 0.22, 0.25, o * w / 1.6 * 1.05, 1.0);
    put('velvet', pillow({ L: 0.47, D: 0.47, T: 0.21, seed: seed + 5 }), 0.44, 0.22, -0.17, 1.12);
    put('linenSand', pillow({ L: 0.45, D: 0.45, T: 0.2, seed: seed + 6 }), 0.47, 0.21, 0.21, 1.18);
    return { foot: headX - dir * (len + 0.11) };
  }
  function nightstand(x, y, d) {
    rb('walnut', x, y + 0.27, d, 0.42, 0.42, 0.42, 0.02);
    rb('blackSatin', x, y + 0.03, d, 0.36, 0.06, 0.36, 0.005);
    lamp(x, y + 0.48, d, 0.42, 0.13);
  }
  function wardrobeAlongX(x0, x1, y, d0, d1, h = 2.45, frontAtD1 = false) { // fluted oak doors on one long face
    bx('joinery', x0, x1, y, y + h, d0, d1);
    const a = frontAtD1 ? d1 : d0 - 0.012, b = frontAtD1 ? d1 + 0.012 : d0;
    for (let x = x0 + 0.03; x < x1 - 0.01; x += 0.05) bx('joinery', x - 0.012, x + 0.012, y + 0.02, y + h - 0.02, a, b);
  }
  function wardrobeAlongD(x0, x1, y, d0, d1, faceMinusX, h = 2.45) {
    bx('joinery', x0, x1, y, y + h, d0, d1);
    const xf = faceMinusX ? x0 : x1;
    for (let d = d0 + 0.03; d < d1 - 0.01; d += 0.05) bx('joinery', faceMinusX ? xf - 0.012 : xf, faceMinusX ? xf : xf + 0.012, y + 0.02, y + h - 0.02, d - 0.012, d + 0.012);
  }
  return { M4, bx, rb, cyl, sphere, wallX, wallD, door, quadArt, quadArtX, frameArt, frameArtX, curtain, curtainD, downlight, lamp, pendantGlobe, chair, loungeChair, plant, bed, nightstand, wardrobeAlongX, wardrobeAlongD };
}

export function buildInterior(B) {
  const { F0, C0, F1, C1, F2, C2 } = H;
  const spots = { bush: [], flower: [], olive: [], pink: [] };
  const { bx, rb, cyl, sphere, wallX, wallD, door, frameArt, frameArtX, curtain, downlight, lamp, pendantGlobe, chair, loungeChair, plant, bed, nightstand, wardrobeAlongX, wardrobeAlongD } = makeKit(B, spots);

  // ======================================================= GROUND FLOOR
  bx('travertine', 0.1, 6.0, F0, F0 + 0.012, 6.75, 9.05, F.PY);
  bx('travertine', 3.3, 6.0, F0, F0 + 0.012, 6.0, 6.75, F.PY);
  bx('travertine', 0.1, 3.15, F0, F0 + 0.012, 9.05, 10.65, F.PY);
  bx('travertine', 0.1, 6.0, F0, F0 + 0.012, 10.65, 14.85, F.PY);
  bx('marbleFloor', 3.3, 6.0, F0, F0 + 0.012, 9.05, 10.55, F.PY);
  // walls
  wallD('paint', 3.15, 3.3, F0, C0, 6.5, 8.95, [[7.05, 8.25, F0, F0 + 2.45]]);
  bx('paint', 3.15, 6.0, F0, C0, 8.95, 9.05);
  wallD('paint', 3.15, 3.3, F0, C0, 9.05, 10.65, [[9.25, 10.05, F0, F0 + 2.4]]);
  bx('paint', 4.85, 4.95, F0, C0, 9.05, 10.55);
  bx('paint', 3.3, 6.0, F0, C0, 10.55, 10.65);
  wallX('paint', 3.3, 6.0, F0, C0, 6.0, 6.012, [[3.9, 5.65, F0 + 1.05, F0 + 2.35]]);
  wallX('paint', 0.1, 3.15, F0, C0, 6.75, 6.762, [[1.95, 3.05, F0, F0 + 2.6], [0.3, 1.75, F0 + 0.6, F0 + 1.2]]);
  door(3.3, 9.25, F0, 0.8, -0.5, false);
  // ceilings (skip stair void)
  bx('ceiling', 0.1, 6.0, C0 - 0.012, C0, 6.0, 6.65, F.NY);
  bx('ceiling', 2.95, 6.0, C0 - 0.012, C0, 6.65, 9.45, F.NY);
  bx('ceiling', 0.1, 6.0, C0 - 0.012, C0, 9.45, 14.85, F.NY);
  bx('ceiling', 0.1, 6.0, C0 - 0.09, C0 - 0.012, 14.45, 14.5);
  bx('led', 0.15, 5.95, C0 - 0.03, C0 - 0.015, 14.52, 14.6);
  for (const [x, d] of [[1.1, 11.4], [3.0, 11.4], [5.0, 11.4], [1.1, 13.8], [3.0, 13.8], [5.0, 13.8], [2.6, 7.2], [2.6, 9.9], [4.6, 7.0], [4.6, 8.2]]) downlight(x, C0 - 0.012, d);

  // ---- stair GF -> FF (19 risers): rear flight leftwards, L-landing, front flight rightwards
  {
    const r = (F1 - F0) / 19;
    for (let i = 1; i <= 6; i++) {
      const xa = 2.25 - i * 0.2167, y = F0 + i * r;
      bx('oakFloor', xa, xa + 0.2167 + 0.02, y - 0.045, y, 8.6, 9.45);
      bx('paint', xa, xa + 0.2167, F0, y - 0.045, 8.6, 9.45);
    }
    const yl = F0 + 7 * r;
    bx('oakFloor', 0.1, 0.95, yl - 0.05, yl, 7.5, 9.45);
    bx('paint', 0.1, 0.95, F0, yl - 0.05, 7.5, 9.45);
    for (let j = 8; j <= 18; j++) {
      const xa = 0.1 + (j - 8) * 0.259, y = F0 + j * r;
      bx('oakFloor', xa - 0.02, xa + 0.259, y - 0.045, y, 6.76, 7.5);
      bx('oakFloor', xa - 0.02, xa, y - r, y - 0.045, 6.76, 7.5);
    }
    // soffit under the front flight
    const run = 2.85, rise = 18 * r - 7 * r, ang = Math.atan2(rise, run), len = Math.hypot(run, rise);
    B.add('paint', new THREE.BoxGeometry(len, 0.12, 0.74), M4(0.1 + run / 2, yl + rise / 2 - 0.17, 7.13, 0, 0, ang), 'box');
    // glass balustrade + oak rail on the well side of the front flight
    const gl = 2.0 / Math.cos(ang), gy = yl + (1.95 - 0.1) / run * rise;
    B.add('glassLight', new THREE.BoxGeometry(gl, 0.95, 0.012), M4(1.95, gy + 0.5, 7.51, 0, 0, ang), 'box');
    B.add('oak', new THREE.BoxGeometry(gl, 0.04, 0.06), M4(1.95, gy + 1.0, 7.51, 0, 0, ang), 'box');
    bx('led', 0.12, 0.14, yl + 0.05, yl + 0.09, 7.5, 9.4);
  }
  // ---- study nook under the stair
  rb('oak', 1.35, F0 + 0.74, 7.08, 1.25, 0.04, 0.55, 0.01);
  rb('oak', 0.76, F0 + 0.36, 7.08, 0.04, 0.72, 0.55, 0.005);
  rb('oak', 1.94, F0 + 0.36, 7.08, 0.04, 0.72, 0.55, 0.005);
  chair(1.35, 7.62, 0, 'velvet');
  cyl('brass', 1.0, F0 + 0.78, 7.05, 0.07, 0.07, 0.015, 20);
  cyl('brass', 1.0, F0 + 0.98, 7.05, 0.008, 0.008, 0.4, 8);
  cyl('lampShade', 1.0, F0 + 1.2, 7.05, 0.06, 0.11, 0.12, 20, null, true);
  rb('linenSand', 1.6, F0 + 0.79, 7.0, 0.3, 0.05, 0.22, 0.01);
  // ---- hall art + console
  frameArtX('art2', 0.11, 9.6, 10.4, F0 + 1.1, F0 + 2.1, true);

  // ---- living & dining: style sets (stylesets.js)
  curtain(0.15, 0.85, F0 + 0.02, C0 - 0.1, 14.68);
  curtain(5.25, 5.95, F0 + 0.02, C0 - 0.1, 14.68);
  rb('walnut', 4.6, F0 + 0.48, 10.9, 2.1, 0.62, 0.46, 0.015);
  for (let x = 3.6; x < 5.62; x += 0.045) bx('walnut', x - 0.01, x + 0.01, F0 + 0.2, F0 + 0.76, 11.13, 11.145);
  frameArt('art1', 4.0, 5.2, F0 + 1.3, F0 + 2.25, 10.665, 'rear');
  lamp(5.35, F0 + 0.79, 10.9, 0.5, 0.15);
  rb('ceramic', 3.95, F0 + 0.92, 10.9, 0.16, 0.26, 0.16, 0.07);

  // ---- kitchen
  bx('blackSatin', 5.45, 6.0, F0, F0 + 0.1, 6.0, 8.95);
  bx('joinery', 5.4, 6.0, F0 + 0.1, F0 + 0.88, 6.0, 8.95);
  for (let d = 6.6; d < 8.9; d += 0.6) bx('blackSatin', 5.397, 5.4, F0 + 0.1, F0 + 0.88, d, d + 0.004);
  bx('marble', 5.36, 6.0, F0 + 0.88, F0 + 0.92, 6.0, 8.95);
  bx('marble', 5.98, 6.0, F0 + 0.92, F0 + 1.6, 6.0, 8.95);
  bx('blackSatin', 5.52, 5.88, F0 + 0.921, F0 + 0.924, 7.15, 7.75);
  cyl('brass', 5.9, F0 + 1.07, 7.45, 0.012, 0.012, 0.3, 12);
  rb('brass', 5.8, F0 + 1.21, 7.45, 0.2, 0.025, 0.025, 0.01);
  bx('joinery', 5.72, 6.0, F0 + 1.82, F0 + 1.86, 6.3, 8.6);
  bx('led', 5.75, 5.98, F0 + 1.814, F0 + 1.82, 6.35, 8.55);
  for (const [d, h] of [[6.6, 0.22], [6.85, 0.16], [7.9, 0.28]]) cyl('ceramic', 5.86, F0 + 1.86 + h / 2, d, 0.06, 0.06, h, 18);
  bx('blackSatin', 3.3, 5.4, F0, F0 + 0.1, 6.05, 6.6);
  bx('oak', 3.3, 5.4, F0 + 0.1, F0 + 0.88, 6.0, 6.6);
  bx('marble', 3.3, 5.4, F0 + 0.88, F0 + 0.92, 6.0, 6.64);
  bx('tv', 4.25, 4.85, F0 + 0.921, F0 + 0.925, 6.08, 6.55);
  bx('joinery', 3.3, 5.0, F0, F0 + 2.45, 8.35, 8.95);
  for (const x of [3.87, 4.44]) bx('blackSatin', x - 0.002, x + 0.002, F0 + 0.05, F0 + 2.4, 8.346, 8.35);
  bx('tv', 3.95, 4.4, F0 + 0.95, F0 + 1.55, 8.344, 8.35);
  rb('walnut', 4.6, F0 + 0.95, 6.3, 0.35, 0.03, 0.22, 0.01);
  sphere('ceramic', 3.7, F0 + 0.98, 6.35, 0.06);

  // ---- powder room
  for (const [x0, x1, d0, d1] of [[3.3, 4.85, 9.05, 9.062], [3.3, 4.85, 10.538, 10.55]]) bx('marble', x0, x1, F0, C0 - 0.4, d0, d1);
  bx('marble', 4.838, 4.85, F0, C0 - 0.4, 9.06, 10.54);
  rb('walnut', 4.6, F0 + 0.7, 9.8, 0.45, 0.2, 0.9, 0.01);
  rb('ceramic', 4.58, F0 + 0.84, 9.8, 0.36, 0.08, 0.46, 0.04);
  cyl('mirror', 4.83, F0 + 1.55, 9.8, 0.36, 0.36, 0.02, 40);
  rb('ceramic', 3.62, F0 + 0.38, 10.25, 0.4, 0.4, 0.36, 0.12);

  // ======================================================= FIRST FLOOR
  const of = (x0, x1, d0, d1) => bx('oakFloor', x0, x1, F1, F1 + 0.012, d0, d1, F.PY);
  of(2.45, 6.0, 3.55, 6.6); of(2.95, 4.3, 6.6, 10.7); of(4.3, 6.0, 6.6, 7.8); of(4.3, 6.0, 10.0, 10.7);
  of(0.1, 2.95, 9.45, 13.29); of(2.95, 6.0, 10.7, 14.11);
  bx('marbleFloor', 0.1, 2.35, F1, F1 + 0.012, 5.0, 6.6, F.PY);
  bx('marbleFloor', 4.3, 6.0, F1, F1 + 0.012, 7.8, 10.0, F.PY);
  // walls
  bx('paint', 0.1, 2.45, F1, C1, 6.6, 6.7);
  wallD('paint', 2.35, 2.45, F1, C1, 5.0, 6.6, [[5.75, 6.5, F1, F1 + 2.4]]);
  wallX('paint', 2.45, 6.0, F1, C1, 6.6, 6.7, [[3.3, 4.15, F1, F1 + 2.4], [4.5, 5.3, F1, F1 + 2.4]]);
  wallD('paint', 4.2, 4.3, F1, C1, 6.7, 10.0, [[8.6, 9.4, F1, F1 + 2.4]]);
  bx('paint', 4.3, 6.0, F1, C1, 7.7, 7.8);
  bx('paint', 4.3, 6.0, F1, C1, 10.0, 10.1);
  wallX('paint', 3.05, 6.0, F1, C1, 10.6, 10.7, [[3.15, 4.05, F1, F1 + 2.4]]);
  bx('paint', 0.1, 2.95, F1, C1, 9.45, 9.55);
  wallD('paint', 2.95, 3.05, F1, C1, 9.55, 13.29, [[9.6, 10.45, F1, F1 + 2.4]]);
  wallX('paint', 0.1, 2.95, F1, C1, 13.278, 13.29, [[0.35, 2.6, F1, F1 + 2.7]]);
  wallX('paint', 3.05, 6.0, F1, C1, 14.098, 14.11, [[3.3, 5.75, F1, F1 + 2.7]]);
  bx('paint', 2.45, 2.462, F1, C1, 3.55, 4.85);
  wallX('marble', 0.1, 2.35, F1, C1 - 0.3, 5.0, 5.012, [[0.55, 1.95, F1 + 1.55, F1 + 2.45]]);
  door(2.45, 5.75, F1, 0.75, -0.6, false);
  door(3.3, 6.65, F1, 0.85, -1.45, true);
  door(4.3, 8.6, F1, 0.8, -0.35, false);
  door(3.15, 10.65, F1, 0.9, 1.45, true);
  door(2.95, 9.6, F1, 0.85, 1.2, false);
  bx('ceiling', 0.1, 6.0, C1 - 0.012, C1, 3.55, 6.65, F.NY);
  bx('ceiling', 2.95, 6.0, C1 - 0.012, C1, 6.65, 9.45, F.NY);
  bx('ceiling', 0.1, 6.0, C1 - 0.012, C1, 9.45, 14.26, F.NY);
  for (const [x, d] of [[3.6, 7.5], [3.6, 9.6], [3.3, 4.4], [3.3, 5.8], [1.5, 10.6], [1.5, 12.4], [4.0, 11.4], [4.0, 13.3]]) downlight(x, C1 - 0.012, d);
  // ---- stair FF -> RF (18 risers)
  {
    const r = (F2 - F1) / 18;
    for (let i = 1; i <= 8; i++) {
      const xa = 2.95 - i * 0.25, y = F1 + i * r;
      bx('oakFloor', xa, xa + 0.27, y - 0.045, y, 8.6, 9.45);
      bx('oakFloor', xa + 0.25, xa + 0.27, y - r, y - 0.045, 8.6, 9.45);
    }
    const yl = F1 + 9 * r;
    bx('oakFloor', 0.1, 0.95, yl - 0.06, yl, 6.76, 9.45);
    bx('paint', 0.1, 0.95, yl - 0.3, yl - 0.06, 6.76, 9.45);
    for (let j = 10; j <= 17; j++) {
      const xa = 0.95 + (j - 10) * 0.25, y = F1 + j * r;
      bx('oakFloor', xa - 0.02, xa + 0.25, y - 0.045, y, 6.76, 7.5);
      bx('oakFloor', xa - 0.02, xa, y - r, y - 0.045, 6.76, 7.5);
    }
    const run = 2.0, rise = 8.5 * r;
    const ang = Math.atan2(rise, run), len = Math.hypot(run, rise);
    B.add('paint', new THREE.BoxGeometry(len, 0.12, 0.85), M4(1.95, F1 + 4.5 * r - 0.17, 9.03, 0, 0, -ang), 'box');
    B.add('paint', new THREE.BoxGeometry(len, 0.12, 0.74), M4(1.95, yl + rise / 2 - 0.17, 7.13, 0, 0, ang), 'box');
    B.add('glassLight', new THREE.BoxGeometry(len, 0.95, 0.012), M4(1.95, F1 + 4.5 * r + 0.47, 8.59, 0, 0, -ang), 'box');
    B.add('oak', new THREE.BoxGeometry(len, 0.04, 0.06), M4(1.95, F1 + 4.5 * r + 0.97, 8.59, 0, 0, -ang), 'box');
    B.add('glassLight', new THREE.BoxGeometry(len, 0.95, 0.012), M4(1.95, yl + rise / 2 + 0.47, 7.51, 0, 0, ang), 'box');
    B.add('oak', new THREE.BoxGeometry(len, 0.04, 0.06), M4(1.95, yl + rise / 2 + 0.97, 7.51, 0, 0, ang), 'box');
    bx('glassLight', 2.94, 2.952, F1, F1 + 1.0, 7.5, 8.6);
    bx('oak', 2.92, 2.98, F1 + 1.0, F1 + 1.04, 7.5, 8.6);
  }
  // ---- master bedroom
  nightstand(5.68, F1, 3.85);
  nightstand(5.68, F1, 6.25);
  pendantGlobe(5.45, C1, 3.85, 1.0, 0.1);
  pendantGlobe(5.45, C1, 6.25, 1.0, 0.1);
  curtain(2.55, 3.15, F1 + 0.02, C1 - 0.15, 3.65);
  curtain(5.35, 5.95, F1 + 0.02, C1 - 0.15, 3.65);
  wardrobeAlongD(5.4, 6.0, F1, 6.75, 7.65, true, 2.5);
  wardrobeAlongX(4.35, 5.35, F1, 7.1, 7.65, 2.5);
  // master bath
  rb('walnut', 0.4, F1 + 0.72, 5.8, 0.5, 0.25, 1.3, 0.01);
  rb('marble', 0.4, F1 + 0.86, 5.8, 0.52, 0.03, 1.32, 0.005);
  rb('ceramic', 0.42, F1 + 0.92, 5.55, 0.36, 0.1, 0.42, 0.04);
  rb('ceramic', 0.42, F1 + 0.92, 6.1, 0.36, 0.1, 0.42, 0.04);
  bx('mirror', 0.1, 0.12, F1 + 1.15, F1 + 2.2, 5.15, 6.45);
  bx('led', 0.12, 0.14, F1 + 2.2, F1 + 2.23, 5.15, 6.45);
  bx('marble', 0.1, 0.112, F1, C1 - 0.3, 5.0, 6.6);
  bx('glassLight', 1.3, 1.312, F1, F1 + 2.1, 5.0, 5.9);
  cyl('chrome', 1.75, C1 - 0.35, 5.45, 0.13, 0.13, 0.01, 24);
  // corridor art
  frameArtX('art3', 4.195, 7.0, 8.2, F1 + 0.95, F1 + 2.05, false);
  // family bathroom
  rb('ceramic', 5.15, F1 + 0.3, 8.22, 1.65, 0.56, 0.74, 0.08);
  bx('poolWater', 4.45, 5.85, F1 + 0.5, F1 + 0.51, 7.92, 8.5);
  bx('marble', 4.3, 6.0, F1, C1 - 0.3, 7.8, 7.812);
  bx('marble', 5.988, 6.0, F1, C1 - 0.3, 7.8, 10.0);
  rb('walnut', 5.75, F1 + 0.72, 9.3, 0.45, 0.22, 0.9, 0.01);
  rb('ceramic', 5.73, F1 + 0.86, 9.3, 0.36, 0.08, 0.46, 0.04);
  bx('mirror', 5.975, 5.988, F1 + 1.1, F1 + 2.0, 8.9, 9.7);
  rb('ceramic', 5.7, F1 + 0.38, 9.8, 0.36, 0.4, 0.36, 0.12);
  // ---- bedroom 2
  bed(4.95, 12.75, F1 + 0.012, 1.6, 2.0, 5.98, 'linenSand');
  nightstand(5.7, F1, 11.68);
  nightstand(5.7, F1, 13.82);
  pendantGlobe(5.45, C1, 11.68, 1.05, 0.09);
  pendantGlobe(5.45, C1, 13.82, 1.05, 0.09);
  wardrobeAlongX(4.15, 6.0, F1, 10.7, 11.3, 2.45, true);
  rb('rug', 4.6, F1 + 0.02, 12.75, 2.6, 0.014, 2.6, 0.007);
  curtain(3.35, 3.85, F1 + 0.02, C1 - 0.15, 13.98);
  curtain(5.3, 5.85, F1 + 0.02, C1 - 0.15, 13.98);
  // ---- bedroom 3
  bed(1.15, 11.45, F1 + 0.012, 1.6, 2.0, 0.12, 'linen');
  nightstand(0.4, F1, 10.4);
  nightstand(0.4, F1, 12.5);
  wardrobeAlongX(0.15, 1.95, F1, 9.55, 10.12, 2.45, true);
  loungeChair(2.45, F1 + 0.012, 12.6, -Math.PI * 0.7, 'velvet');
  curtain(0.4, 0.95, F1 + 0.02, C1 - 0.15, 13.15);
  curtain(2.05, 2.6, F1 + 0.02, C1 - 0.15, 13.15);
  pendantGlobe(1.2, C1, 11.45, 0.7, 0.16);
  // ---- balconies
  for (const [x, ry] of [[3.6, 0.2], [4.6, -0.2]]) loungeChair(x, F1 + 0.02, 2.35, ry, 'linenGrey');
  cyl('travertineSlab', 4.1, F1 + 0.25, 2.1, 0.22, 0.22, 0.45, 30);
  bx('stone', 0.2, 2.3, F1, F1 + 0.55, 4.3, 4.75);
  spots.flower.push([0.7, F1 + 0.6, 4.5, 0.6], [1.5, F1 + 0.6, 4.55, 0.55], [2.0, F1 + 0.6, 4.45, 0.5]);
  rb('wood', 4.6, F1 + 0.38, 14.75, 0.7, 0.04, 0.7, 0.01);
  cyl('frame', 4.6, F1 + 0.19, 14.75, 0.02, 0.02, 0.36, 8);
  loungeChair(3.6, F1 + 0.02, 14.75, Math.PI / 2, 'linenGrey');

  // ======================================================= ROOF LEVEL
  bx('oakFloor', 2.95, 4.4, F2, F2 + 0.012, 6.75, 8.05, F.PY);
  bx('oakFloor', 2.95, 6.0, F2, F2 + 0.012, 8.05, 9.45, F.PY);
  bx('oakFloor', 2.25, 6.0, F2, F2 + 0.012, 9.45, 11.05, F.PY);
  bx('marbleFloor', 0.1, 2.15, F2, F2 + 0.012, 9.6, 11.05, F.PY);
  wallX('paint', 2.95, 4.4, F2, C2, 7.95, 8.05, [[3.3, 4.15, F2, F2 + 2.4]]);
  bx('paint', 2.95, 3.05, F2, C2, 8.05, 9.45);
  bx('paint', 0.1, 2.25, F2, C2, 9.45, 9.6);
  wallD('paint', 2.15, 2.25, F2, C2, 9.6, 11.05, [[10.25, 10.95, F2, F2 + 2.35]]);
  wallX('paint', 0.1, 4.5, F2, C2, 6.75, 6.762);
  wallX('paint', 2.9, 6.0, F2, C2, 11.038, 11.05, [[2.9, 5.65, F2, F2 + 2.75]]);
  wallX('marble', 0.1, 2.15, F2, C2 - 0.3, 11.038, 11.05, [[0.5, 1.6, F2 + 1.4, F2 + 2.4]]);
  bx('glassLight', 2.94, 2.952, F2, F2 + 1.0, 7.5, 7.95);
  door(3.3, 8.0, F2, 0.85, 1.0, true);
  bx('ceiling', 0.1, 4.5, C2 - 0.012, C2, 6.75, 11.05, F.NY);
  bx('ceiling', 4.5, 6.0, C2 - 0.012, C2, 8.1, 11.05, F.NY);
  for (const [x, d] of [[3.7, 7.3], [4.0, 9.0], [4.0, 10.4], [1.4, 8.0]]) downlight(x, C2 - 0.012, d);
  bed(4.95, 9.55, F2 + 0.012, 1.6, 2.0, 5.98, 'linen');
  nightstand(5.7, F2, 8.48);
  nightstand(5.7, F2, 10.62);
  rb('rug', 4.5, F2 + 0.02, 9.55, 2.6, 0.014, 2.4, 0.007);
  curtain(2.95, 3.45, F2 + 0.02, C2 - 0.15, 10.92);
  curtain(5.1, 5.6, F2 + 0.02, C2 - 0.15, 10.92);
  frameArtX('art3', 3.051, 8.35, 9.25, F2 + 1.0, F2 + 1.9, true);
  rb('walnut', 2.65, F2 + 0.74, 10.6, 0.7, 0.04, 0.5, 0.01);
  plant(4.1, F2, 7.4, 0.9, 'leaf');
  // roof bathroom
  rb('walnut', 0.4, F2 + 0.72, 10.35, 0.45, 0.22, 0.9, 0.01);
  rb('ceramic', 0.4, F2 + 0.86, 10.35, 0.36, 0.08, 0.46, 0.04);
  bx('mirror', 0.1, 0.112, F2 + 1.1, F2 + 2.0, 9.95, 10.75);
  // ---- roof terrace
  {
    const y = F2 + 0.02;
    rb('wood', 0.62, y + 0.15, 12.25, 0.86, 0.3, 1.9, 0.02);
    rb('linenGrey', 0.6, y + 0.36, 12.25, 0.78, 0.14, 1.82, 0.05);
    rb('linenGrey', 0.24, y + 0.6, 12.25, 0.16, 0.42, 1.82, 0.07);
    rb('velvet', 0.36, y + 0.62, 11.75, 0.14, 0.38, 0.38, 0.07, 0.3);
    rb('linenSand', 0.36, y + 0.62, 12.75, 0.14, 0.38, 0.38, 0.07, -0.2);
    rb('rug', 1.9, y + 0.006, 12.25, 2.2, 0.012, 2.0, 0.006);
    cyl('concrete', 1.95, y + 0.2, 12.3, 0.5, 0.46, 0.4, 40);
    cyl('charcoal', 1.95, y + 0.405, 12.3, 0.36, 0.36, 0.012, 32);
    cyl('fire', 1.95, y + 0.42, 12.3, 0.22, 0.26, 0.03, 24);
    for (const [x, d, ry] of [[3.35, 12.15, -Math.PI / 2], [3.25, 13.15, -Math.PI * 0.32]]) loungeChair(x, y, d, ry, 'linenGrey');
    bx('stone', 5.5, 5.95, F2, F2 + 0.6, 11.4, 13.95);
    bx('soil', 5.55, 5.9, F2 + 0.6, F2 + 0.62, 11.45, 13.9, F.PY);
    spots.flower.push([5.72, F2 + 0.62, 11.9, 0.75], [5.72, F2 + 0.62, 12.7, 0.8], [5.72, F2 + 0.62, 13.5, 0.7]);
    plant(5.6, F2, 13.75, 0.95);
    for (const [x, d] of [[1.3, 13.0], [2.6, 11.45]]) { rb('frame', x, y + 0.2, d, 0.18, 0.4, 0.18, 0.01); sphere('bulb', x, y + 0.2, d, 0.05); }
  }

  // ---------- lights (hero only); intensities are scaled by time of day in main.js
  const lights = [
    { type: 'point', name: 'hall', pos: [2.6, C0 - 0.4, 8.2], color: 0xffd9a8, day: 0, dusk: 1.5, dist: 7 },
    { type: 'point', name: 'livingWarm', pos: [3.0, C0 - 0.5, 12.6], color: 0xffd2a0, day: 0, dusk: 2.2, dist: 9 },
    { type: 'point', name: 'ff', pos: [3.8, C1 - 0.4, 8.5], color: 0xffd9a8, day: 0, dusk: 1.8, dist: 8 },
    { type: 'point', name: 'fire', pos: [1.95, F2 + 0.9, 12.3], color: 0xff9a4a, day: 0, dusk: 7, dist: 7 },
  ];
  return { spots, lights };
}
