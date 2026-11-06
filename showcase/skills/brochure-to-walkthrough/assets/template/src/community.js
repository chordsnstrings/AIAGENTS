import * as THREE from 'three';
import { Builder, F, mirrorX, instanced } from './builder.js';
import { buildShell } from './house.js';
import { palmGeometry, bushGeometry, instancedFrom } from './vegetation.js';

// Violet 2 sits in a cluster of curving streets lined with back-to-back townhouse rows. The
// hero unit (XJ407B) is the middle of a seven-unit block; its frame is the world frame.

export const R = 260;
export const CENTER = new THREE.Vector3(3.05, 0, -R);
const SPAN = 0.62;
const BLOCK = 7, GAP = 5, PLOT_W = 6.1;
const CROSS = [-0.36, 0.34];

function rng(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
const v3 = new THREE.Vector3();

function lodHouse(B) {
  const bx = (k, x0, x1, y0, y1, d0, d1, f) => B.box(k, x0, x1, y0, y1, -d1, -d0, f);
  bx('lodRoof', 0, 6.1, 0, 6.95, 1.5, 15.3, F.PY | F.PX | F.NX);
  bx('lodRoof', 0.1, 6.0, 6.95, 10.0, 6.6, 11.2, F.PY | F.PX | F.NX);
  const v = (y) => y / 10.2;
  B.quad('lod', [0, 0, -1.5], [6.1, 0, -1.5], [6.1, 6.95, -1.5], [0, 6.95, -1.5], [[0, 0], [0.5, 0], [0.5, v(6.95)], [0, v(6.95)]]);
  B.quad('lod', [0.1, 6.95, -6.6], [6.0, 6.95, -6.6], [6.0, 10.0, -6.6], [0.1, 10.0, -6.6], [[0.008, v(6.95)], [0.492, v(6.95)], [0.492, v(10)], [0.008, v(10)]]);
  B.quad('lod', [6.1, 0, -15.3], [0, 0, -15.3], [0, 6.95, -15.3], [6.1, 6.95, -15.3], [[0.5, 0], [1, 0], [1, v(6.95)], [0.5, v(6.95)]]);
  B.quad('lod', [6.0, 6.95, -11.2], [0.1, 6.95, -11.2], [0.1, 10.0, -11.2], [6.0, 10.0, -11.2], [[0.508, v(6.95)], [0.992, v(6.95)], [0.992, v(10)], [0.508, v(10)]]);
  bx('grass', 0.1, 6.0, 0, 0.12, 15.3, 18.4, F.PY);
  bx('lodRoof', 0, 6.1, 0, 2.0, 18.4, 18.5, F.PY | F.PZ | F.NZ);
  bx('lodRoof', 0, 0.1, 0, 2.0, 15.3, 18.4, F.PY | F.PX | F.NX);
  bx('pavers', 0, 6.1, 0, 0.06, 0, 1.5, F.PY);
  bx('wood', 0.25, 5.85, 10.0, 10.08, 11.2, 12.8, F.PY);
  bx('lodRoof', 0, 6.1, 10.0, 10.3, 6.3, 6.6, F.PY | F.PZ);
  bx('wood', 0.3, 5.8, 6.95, 7.0, 1.6, 3.4, F.PY);
  bx('patio', 0.1, 6.0, 6.95, 6.97, 11.2, 14.2, F.PY);
  bx('gravel', 0.1, 6.0, 6.95, 6.97, 3.6, 6.6, F.PY);
}

// Flat annulus sector around CENTER; uv = world metres.
function ring(B, k, r0, r1, a0, a1, y, seg = 160) {
  const b = B.bucket(k), base = b.count;
  for (let i = 0; i <= seg; i++) {
    const a = a0 + (a1 - a0) * i / seg, s = Math.sin(a), c = Math.cos(a);
    for (const r of [r0, r1]) {
      const x = CENTER.x + s * r, z = CENTER.z + c * r;
      b.p.push(x, y, z); b.n.push(0, 1, 0); b.u.push(x, -z);
    }
  }
  for (let i = 0; i < seg; i++) { const a = base + i * 2; b.i.push(a, a + 1, a + 3, a, a + 3, a + 2); }
}
// vertical curb face along an arc (normal pointing to larger radius if outward)
function curb(B, k, r, a0, a1, y0, y1, outward, seg = 160) {
  const b = B.bucket(k), base = b.count;
  for (let i = 0; i <= seg; i++) {
    const a = a0 + (a1 - a0) * i / seg, s = Math.sin(a), c = Math.cos(a);
    const x = CENTER.x + s * r, z = CENTER.z + c * r, n = outward ? 1 : -1;
    for (const y of [y0, y1]) { b.p.push(x, y, z); b.n.push(s * n, 0, c * n); b.u.push(a * r, y); }
  }
  for (let i = 0; i < seg; i++) {
    const a = base + i * 2;
    if (outward) b.i.push(a, a + 2, a + 1, a + 2, a + 3, a + 1); else b.i.push(a, a + 1, a + 2, a + 2, a + 1, a + 3);
  }
}

export function buildCommunity(M, heroSpots, { lite = false } = {}) {
  const group = new THREE.Group();
  const rand = rng(17);

  // ---- house transforms
  const rows = [
    { r: R, out: true, hero: true }, { r: R - 37, out: false }, { r: R + 12, out: false }, { r: R + 49, out: true },
    { r: R - 49, out: true }, { r: R - 86, out: false }, { r: R + 61, out: false }, { r: R + 98, out: true },
  ];
  const full = { n: [], m: [] }, lod = { n: [], m: [] };
  const fullSpots = []; // [matrix, mirrored]
  const lodPalms = [];
  const parks = [];
  for (const row of rows) {
    const step = (BLOCK * PLOT_W + GAP) / row.r;
    const nb = Math.floor(SPAN / step);
    const off = row.hero ? 0 : (rand() - 0.5) * step * 0.6;
    for (let b = -nb; b <= nb; b++) {
      const th = b * step + off;
      if (CROSS.some((c) => Math.abs(th - c) < step * 0.55)) { parks.push([row, th]); continue; }
      for (let i = 0; i < BLOCK; i++) {
        if (row.hero && b === 0 && i === 3) continue;
        const ox = (i - (BLOCK - 1) / 2) * PLOT_W;
        const m = new THREE.Matrix4().makeTranslation(CENTER.x, 0, CENTER.z)
          .multiply(new THREE.Matrix4().makeRotationY(row.out ? th : th + Math.PI))
          .multiply(new THREE.Matrix4().makeTranslation(ox - 3.05, 0, row.out ? row.r : -row.r));
        const mirrored = row.hero ? i % 2 === 0 : i % 2 === 1;
        v3.set(3.05, 0, -9).applyMatrix4(m);
        const isFull = v3.distanceTo(new THREE.Vector3(3.05, 0, -9)) < 72;
        (isFull ? full : lod)[mirrored ? 'm' : 'n'].push(m);
        if (isFull) fullSpots.push([m, mirrored, v3.distanceTo(new THREE.Vector3(3.05, 0, -9)) < 7]);
        else if (rand() < 0.55) lodPalms.push(new THREE.Vector3(mirrored ? 6.1 - 0.9 : 0.9, 0.3, -17.9).applyMatrix4(m));
      }
    }
  }

  // ---- full-detail neighbours (instanced shell)
  const SB = new Builder();
  const shellSpots = buildShell(SB, { hero: false });
  const geos = SB.geometries();
  const geosM = new Map([...geos].map(([k, g]) => [k, mirrorX(g, 3.05)]));
  const roomN = geos.get('room'), roomM = geosM.get('room');
  geos.delete('room'); geosM.delete('room');
  group.add(instanced(geos, M, full.n), instanced(geosM, M, full.m));
  const split = (list) => { const a = [], b = []; list.forEach((m) => (rand() < 0.62 ? a : b).push(m)); return [a, b]; };
  const [nLit, nDim] = split(full.n), [mLit, mDim] = split(full.m);
  for (const [g, list, mat] of [[roomN, nLit, M.roomLit], [roomN, nDim, M.roomDim], [roomM, mLit, M.roomLit], [roomM, mDim, M.roomDim]]) {
    if (list.length) group.add(instancedFrom(g, mat, list, { cast: false }));
  }

  // ---- far houses
  const LB = new Builder();
  lodHouse(LB);
  const lg = LB.geometries();
  const lgM = new Map([...lg].map(([k, g]) => [k, mirrorX(g, 3.05)]));
  group.add(instanced(lg, M, lod.n), instanced(lgM, M, lod.m));

  // ---- streets, sidewalks, curbs
  const SBk = new Builder();
  const streets = [[R, R + 12], [R - 49, R - 37], [R + 49, R + 61], [R - 98, R - 86], [R + 98, R + 110]];
  const a0 = -SPAN - 0.06, a1 = SPAN + 0.06;
  const lamps = [], streetPalms = [], vergeBushes = [];
  for (const [s0, s1] of streets) {
    ring(SBk, 'sidewalk', s0, s0 + 2.2, a0, a1, 0.15);
    ring(SBk, 'sidewalk', s1 - 2.2, s1, a0, a1, 0.15);
    ring(SBk, 'asphalt', s0 + 2.2, s1 - 2.2, a0, a1, 0.02);
    curb(SBk, 'curb', s0 + 2.2, a0, a1, 0.02, 0.15, true);
    curb(SBk, 'curb', s1 - 2.2, a0, a1, 0.02, 0.15, false);
    for (const [rr, phase] of [[s0 + 0.8, 0], [s1 - 0.8, 0.5]]) {
      const n = Math.floor((a1 - a0) * rr / 6.5);
      for (let i = 0; i < n; i++) {
        const a = a0 + (i + phase) * 6.5 / rr;
        const p = new THREE.Vector3(CENTER.x + Math.sin(a) * rr, 0.15, CENTER.z + Math.cos(a) * rr);
        if (Math.abs(p.x - 3.05) < 14 && p.z > -2 && p.z < 14) continue; // keep the hero frontage clear
        if (i % 4 === 0) streetPalms.push(p);
        else if (i % 4 === 2) lamps.push([p, a, rr === s0 + 0.8]);
        else vergeBushes.push(p);
      }
    }
  }
  // cross streets and pocket parks where blocks were left out
  for (const c of CROSS) {
    const g = new THREE.PlaneGeometry(11, 230);
    g.rotateX(-Math.PI / 2);
    const m = new THREE.Matrix4().makeTranslation(CENTER.x, 0.025, CENTER.z).multiply(new THREE.Matrix4().makeRotationY(c)).multiply(new THREE.Matrix4().makeTranslation(0, 0, R - 5));
    SBk.add('asphalt', g, m, 'box');
  }
  for (const [row, th] of parks) {
    const g = new THREE.CircleGeometry(15, 40);
    g.rotateX(-Math.PI / 2);
    const rr = row.r + (row.out ? -10 : 10);
    for (const side of [-1, 1]) {
      const a = th + side * 22 / rr;
      const m = new THREE.Matrix4().makeTranslation(CENTER.x + Math.sin(a) * rr, 0.03, CENTER.z + Math.cos(a) * rr);
      SBk.add('grass', g, m, 'box');
      for (let k = 0; k < 4; k++) {
        const aa = a + (rand() - 0.5) * 20 / rr, r2 = rr + (rand() - 0.5) * 18;
        streetPalms.push(new THREE.Vector3(CENTER.x + Math.sin(aa) * r2, 0.03, CENTER.z + Math.cos(aa) * r2));
      }
    }
  }
  ring(SBk, 'base', R - 112, R + 124, -SPAN - 0.1, SPAN + 0.1, 0.004, 120);
  const sg = SBk.geometries();
  for (const [k, g] of sg) {
    const mesh = new THREE.Mesh(g, M[k]);
    mesh.receiveShadow = true;
    mesh.matrixAutoUpdate = false;
    group.add(mesh);
  }

  // ---- lamps (pole + head + light pool)
  {
    const pole = new THREE.CylinderGeometry(0.045, 0.07, 5.2, 8); pole.translate(0, 2.6, 0);
    const arm = new THREE.BoxGeometry(0.05, 0.05, 0.9); arm.translate(0, 5.1, 0.42);
    const head = new THREE.BoxGeometry(0.22, 0.08, 0.5); head.translate(0, 5.06, 0.78);
    const poolG = new THREE.PlaneGeometry(9, 9); poolG.rotateX(-Math.PI / 2); poolG.translate(0, 0.04, 1.6);
    const pm = [], hm = [], lm = [];
    for (const [p, a, inner] of lamps) {
      const m = new THREE.Matrix4().makeTranslation(p.x, p.y, p.z).multiply(new THREE.Matrix4().makeRotationY(a + (inner ? 0 : Math.PI)));
      pm.push(m); hm.push(m); lm.push(m);
    }
    group.add(instancedFrom(pole, M.frame, pm));
    group.add(instancedFrom(arm, M.frame, pm));
    group.add(instancedFrom(head, M.lampHead, hm, { cast: false }));
    group.add(instancedFrom(poolG, M.pool, lm, { cast: false, receive: false }));
    const cone = new THREE.CylinderGeometry(0.12, 2.4, 5.0, 24, 1, true);
    cone.translate(0, 2.52, 0.78);
    const beams = instancedFrom(cone, M.beam, lm, { cast: false, receive: false });
    beams.name = 'lampBeams';
    group.add(beams);
  }

  // ---- lagoon toward the sunset, with a beach
  {
    const shape = new THREE.Shape();
    const r2 = rng(3);
    const pts = 64;
    for (let i = 0; i <= pts; i++) {
      const a = i / pts * Math.PI * 2;
      const rr = 1 + 0.12 * Math.sin(a * 3 + 1) + 0.07 * Math.sin(a * 7) + (r2() - 0.5) * 0.02;
      const x = Math.cos(a) * 170 * rr, y = Math.sin(a) * 85 * rr;
      if (i === 0) shape.moveTo(x, y); else shape.lineTo(x, y);
    }
    const water = new THREE.ShapeGeometry(shape, 4);
    water.rotateX(-Math.PI / 2);
    const beach = new THREE.ShapeGeometry(shape, 4);
    beach.rotateX(-Math.PI / 2);
    beach.scale(1.12, 1, 1.22);
    const place = new THREE.Matrix4().makeTranslation(-260, 0, -360).multiply(new THREE.Matrix4().makeRotationY(-0.6));
    const wm = new THREE.Mesh(water, M.water); wm.applyMatrix4(place); wm.position.y = 0.06; wm.receiveShadow = true;
    const sandMat = M.sand.clone(); sandMat.color.set(0xfbe7cb); sandMat.polygonOffset = true; sandMat.polygonOffsetFactor = -1; sandMat.polygonOffsetUnits = -2;
    const bm = new THREE.Mesh(beach, sandMat); bm.applyMatrix4(place); bm.position.y = 0.03; bm.receiveShadow = true;
    M.water.polygonOffset = true; M.water.polygonOffsetFactor = -2; M.water.polygonOffsetUnits = -4;
    group.add(wm, bm);
    for (let i = 0; i < 46; i++) {
      const a = r2() * Math.PI * 2, k = 1.05 + r2() * 0.1;
      const p = new THREE.Vector3(Math.cos(a) * 170 * k, 0.05, Math.sin(a) * 85 * k * 1.08).applyMatrix4(place);
      streetPalms.push(p);
    }
  }

  // ---- desert ground with dunes beyond the community
  {
    const size = 4200, seg = lite ? 130 : 220;
    const g = new THREE.PlaneGeometry(size, size, seg, seg);
    g.rotateX(-Math.PI / 2);
    const pa = g.attributes.position;
    const n2 = (x, z) => Math.sin(x * 0.0061 + Math.sin(z * 0.0043) * 1.7) * Math.cos(z * 0.0052 + Math.sin(x * 0.0031) * 1.3);
    for (let i = 0; i < pa.count; i++) {
      const x = pa.getX(i), z = pa.getZ(i);
      const d = Math.hypot(x + 60, z + 60);
      const k = THREE.MathUtils.smoothstep(d, 470, 1100);
      const dune = (Math.abs(n2(x, z)) * 26 + Math.abs(n2(x * 2.3 + 40, z * 2.1)) * 9 + n2(x * 5.1, z * 4.7) * 2.2);
      pa.setY(i, k * dune - 0.02);
    }
    g.computeVertexNormals();
    const ground = new THREE.Mesh(g, M.desert);
    ground.receiveShadow = true;
    ground.matrixAutoUpdate = false;
    group.add(ground);
  }

  // ---- vegetation instances
  const palm = palmGeometry();
  const bush = bushGeometry(14, 2, 0.75);
  const canopy = bushGeometry(18, 4, 1.0);
  const lists = { palm: [], bush: [], flower: [], pink: [], olive: [] };
  const addSpot = (type, p, s, m) => {
    const q = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), rand() * Math.PI * 2);
    const local = new THREE.Matrix4().compose(p, q, new THREE.Vector3(s, s * (type === 'palm' ? 1 : 0.9), s));
    lists[type].push(m ? m.clone().multiply(local) : local);
  };
  const spotTypes = (spots, m, mirrored, noPalms = false) => {
    for (const [type, arr] of Object.entries(spots)) for (const [x, y, d, s] of arr) {
      if (noPalms && type === 'palm') continue;
      const p = new THREE.Vector3(mirrored ? 6.1 - x : x, y, -d);
      let t = type;
      if (type === 'flower' && rand() < 0.22) t = 'pink';
      addSpot(t, p, s * (type === 'palm' ? 1 : 1.25), m);
    }
  };
  for (const [m, mir, adjacent] of fullSpots) spotTypes(shellSpots, m, mir, adjacent);
  spotTypes(heroSpots, null, false);
  const keep = () => !lite || rand() < 0.5;
  for (const p of lodPalms) if (keep()) addSpot('palm', p, 0.75 + rand() * 0.35, null);
  for (const p of streetPalms) if (keep()) addSpot('palm', p, 0.85 + rand() * 0.4, null);
  for (const p of vergeBushes) if (keep()) addSpot(rand() < 0.3 ? 'flower' : 'bush', p, 0.7 + rand() * 0.3, null);
  group.add(instancedFrom(palm.trunk, M.bark, lists.palm));
  group.add(instancedFrom(palm.fronds, M.frond, lists.palm));
  group.add(instancedFrom(bush, M.leaf, lists.bush));
  group.add(instancedFrom(bush, M.flower, lists.flower));
  group.add(instancedFrom(bush, M.flowerPink, lists.pink));
  group.add(instancedFrom(canopy, M.leafOlive, lists.olive));
  group.traverse((o) => { if (o.isMesh) { o.updateMatrix(); o.matrixAutoUpdate = false; } });
  return { group, stats: { full: full.n.length + full.m.length, lod: lod.n.length + lod.m.length, palms: lists.palm.length } };
}
