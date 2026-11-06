// Samples the drone route finely and reports what a viewer would feel: how fast the view turns,
// how far down it pitches, how close the look target comes to the lens, and how near the camera
// passes to the hero and neighbouring geometry. Exit code 1 on any limit breach, so it can gate
// a build. Usage: node scripts/check-path.mjs [--verbose]
import * as THREE from 'three';
import { readFileSync } from 'node:fs';
import { Builder, mirrorX } from '../src/builder.js';
import { buildShell } from '../src/house.js';
import { buildInterior } from '../src/interior.js';
import { DronePath } from '../src/path.js';

const LIMITS = {
  clearance: 0.3,   // m between the lens and any solid surface
  lookDist: 2.4,    // m from the lens to the look target
  pitchDown: -35,   // degrees
  pitchUp: 40,
  yawRate: 12,      // degrees per 0.005 of progress (about one wheel notch)
  pitchRate: 6,
};
const STEP = 0.001, WIN = 5; // samples; WIN * STEP = the 0.005 window
const verbose = process.argv.includes('--verbose');

// chapters from index.html so breaches can be named by the card the viewer is reading
const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const chapters = [...html.matchAll(/data-from="([\d.]+)" data-to="([\d.]+)" data-rail="([^"]+)"/g)].map((m) => ({ from: +m[1], to: +m[2], name: m[3] }));
const chapterAt = (p) => (chapters.find((c) => p >= c.from && p <= c.to) || { name: '(no card)' }).name;

// ---- solid geometry: hero shell + interior, and the two attached neighbours
const tris = [];
const SKIP = new Set(['pool', 'room', 'sheer', 'downlight', 'led', 'lattice', 'leaf', 'leafOlive', 'flower', 'flowerPink', 'frond', 'stem', 'bloom', 'bloomB']);
function addGeos(geos, mat) {
  const v = new THREE.Vector3();
  for (const [k, g] of geos) {
    if (SKIP.has(k)) continue;
    const p = g.attributes.position, idx = g.index.array, pts = [];
    for (let i = 0; i < p.count; i++) { v.fromBufferAttribute(p, i); if (mat) v.applyMatrix4(mat); pts.push(v.clone()); }
    for (let i = 0; i < idx.length; i += 3) tris.push([pts[idx[i]], pts[idx[i + 1]], pts[idx[i + 2]], k]);
  }
}
const H = new Builder(); buildShell(H, { hero: true }); buildInterior(H); addGeos(H.geometries());
const N = new Builder(); buildShell(N, { hero: false });
const NM = new Map([...N.geometries()].map(([k, g]) => [k, mirrorX(g, 3.05)]));
for (const ox of [-6.1, 6.1]) addGeos(NM, new THREE.Matrix4().makeTranslation(ox, 0, 0));
const CELL = 0.5, grid = new Map(), cellKey = (x, y, z) => `${x},${y},${z}`;
for (const t of tris) {
  const b = new THREE.Box3().setFromPoints(t.slice(0, 3)).expandByScalar(LIMITS.clearance + 0.05);
  for (let x = Math.floor(b.min.x / CELL); x <= Math.floor(b.max.x / CELL); x++)
    for (let y = Math.floor(b.min.y / CELL); y <= Math.floor(b.max.y / CELL); y++)
      for (let z = Math.floor(b.min.z / CELL); z <= Math.floor(b.max.z / CELL); z++) {
        const k = cellKey(x, y, z); if (!grid.has(k)) grid.set(k, []); grid.get(k).push(t);
      }
}
const tri = new THREE.Triangle(), cp = new THREE.Vector3();
function clearance(q) {
  const cell = grid.get(cellKey(Math.floor(q.x / CELL), Math.floor(q.y / CELL), Math.floor(q.z / CELL)));
  let best = 1e9, what = '';
  if (cell) for (const t of cell) { tri.set(t[0], t[1], t[2]); tri.closestPointToPoint(q, cp); const d = cp.distanceTo(q); if (d < best) { best = d; what = t[3]; } }
  return [best, what];
}

// ---- sample the route
const path = new DronePath(), pos = new THREE.Vector3(), look = new THREE.Vector3();
const n = Math.round(1 / STEP), S = [];
for (let i = 0; i <= n; i++) {
  const p = i * STEP;
  const fov = path.sample(p, pos, look);
  const d = look.clone().sub(pos), dist = d.length();
  const yaw = THREE.MathUtils.radToDeg(Math.atan2(d.x, d.z));
  const pitch = THREE.MathUtils.radToDeg(Math.asin(THREE.MathUtils.clamp(d.y / Math.max(dist, 1e-6), -1, 1)));
  const [clear, what] = clearance(pos);
  S.push({ p, pos: pos.clone(), dist, yaw, pitch, fov, clear, what });
}
const wrap = (a) => ((a + 540) % 360) - 180;

// ---- breaches, grouped into consecutive runs so the report stays readable
const runs = [], open = new Map();
function breach(kind, s, value, note) {
  const last = open.get(kind);
  if (last && s.p - last.end <= STEP * 1.5) { last.end = s.p; if (Math.abs(value) > Math.abs(last.worst)) { last.worst = value; last.at = s; last.note = note; } }
  else { const r = { kind, start: s.p, end: s.p, worst: value, at: s, note }; runs.push(r); open.set(kind, r); }
}
for (let i = 0; i < S.length; i++) {
  const s = S[i];
  if (s.clear < LIMITS.clearance) breach('clearance', s, s.clear, s.what);
  if (s.dist < LIMITS.lookDist) breach('look distance', s, s.dist, '');
  if (s.pitch < LIMITS.pitchDown) breach('pitch down', s, s.pitch, '');
  if (s.pitch > LIMITS.pitchUp) breach('pitch up', s, s.pitch, '');
  if (i >= WIN) {
    const dy = wrap(s.yaw - S[i - WIN].yaw), dp = s.pitch - S[i - WIN].pitch;
    if (Math.abs(dy) > LIMITS.yawRate) breach('yaw rate', s, dy, '');
    if (Math.abs(dp) > LIMITS.pitchRate) breach('pitch rate', s, dp, '');
  }
}
const fmt = (s) => `(${s.pos.x.toFixed(2)}, ${s.pos.y.toFixed(2)}, d ${(-s.pos.z).toFixed(2)})`;
const unit = { clearance: 'm', 'look distance': 'm', 'pitch down': 'deg', 'pitch up': 'deg', 'yaw rate': 'deg/0.005', 'pitch rate': 'deg/0.005' };
console.log(`route sampled at ${STEP}; ${tris.length} solid triangles; ${runs.length} breach run(s)`);
for (const r of runs) {
  console.log(`  ${r.kind.padEnd(13)} p ${r.start.toFixed(3)}-${r.end.toFixed(3)}  worst ${r.worst.toFixed(2)} ${unit[r.kind]}  ${r.note}  ${chapterAt(r.at.p)}  at ${fmt(r.at)}`);
}

// ---- per-chapter summary: where the viewer's time goes
console.log('\nchapter            span   yaw swing  pitch range     look dist  min clear');
const all = [...chapters, { from: 0, to: 1, name: '(whole route)' }];
for (const c of all) {
  const seg = S.filter((s) => s.p >= c.from && s.p <= c.to);
  if (!seg.length) continue;
  let swing = 0; for (let i = 1; i < seg.length; i++) swing += Math.abs(wrap(seg[i].yaw - seg[i - 1].yaw));
  const pi = seg.map((s) => s.pitch), ld = seg.map((s) => s.dist), cl = seg.map((s) => s.clear);
  console.log(`${c.name.padEnd(18)} ${(c.to - c.from).toFixed(3)}  ${swing.toFixed(0).padStart(6)} deg  ${Math.min(...pi).toFixed(0).padStart(4)}..${Math.max(...pi).toFixed(0).padStart(3)} deg  ${Math.min(...ld).toFixed(1).padStart(6)} m  ${Math.min(...cl).toFixed(2).padStart(7)} m`);
}
const gaps = [];
for (let i = 1; i < chapters.length; i++) if (chapters[i].from - chapters[i - 1].to > 0.03) gaps.push(`${chapters[i - 1].to}-${chapters[i].from} (${chapters[i - 1].name} -> ${chapters[i].name})`);
if (gaps.length) console.log(`\nstretches longer than 0.03 with no card: ${gaps.join('; ')}`);
if (verbose) for (const s of S) if (Math.round(s.p * 1000) % 5 === 0) console.log(`${s.p.toFixed(3)} yaw ${s.yaw.toFixed(0).padStart(5)} pitch ${s.pitch.toFixed(0).padStart(4)} dist ${s.dist.toFixed(1).padStart(5)} clear ${s.clear.toFixed(2)} fov ${s.fov.toFixed(0)}`);
process.exit(runs.length ? 1 : 0);
