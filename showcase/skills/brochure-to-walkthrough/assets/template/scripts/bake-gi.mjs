// Offline GI bake: an irradiance volume (L1 spherical harmonics) around the hero unit.
// Linear components, so the page can relight by time of day and style without re-baking:
//   S - sky light (golden-hour Preetham sky, same model and gain as the page), plus how open
//       each probe is to the sky, which tells the page where "indoors" is
//   U - sunlight bounced off surfaces (direct sun stays real-time, with its shadow map)
//   N - each style's night lamps, as soft point emitters
// Pass 1 is the light arriving directly; every later pass lights each ray hit with the previous
// pass's interpolated probes, so two bounces need no per-surface light sampling at all.
import * as THREE from 'three';
import { MeshBVH } from 'three-mesh-bvh';
import { readFileSync, writeFileSync } from 'node:fs';
import { Builder, mirrorX } from '../src/builder.js';
import { buildShell } from '../src/house.js';
import { buildInterior, makeKit } from '../src/interior.js';
import { buildStyleSet } from '../src/stylesets.js';
import { STYLES, SET_AVG } from '../src/styles.js';

const RAYS = +(process.env.RAYS || 256), PASSES = 3;
const SP = 0.5, MIN = [0.0, 0.0, -15.6], DIMS = [13, 22, 30];
const NP = DIMS[0] * DIMS[1] * DIMS[2];
const D2R = Math.PI / 180;
const sunDir = new THREE.Vector3(Math.sin(-55 * D2R) * Math.cos(18 * D2R), Math.sin(18 * D2R), Math.cos(-55 * D2R) * Math.cos(18 * D2R));
const SUN = [4.3 * 1.0, 4.3 * 0.81, 4.3 * 0.6];
const LUM = [0.2126, 0.7152, 0.0722];
const lin = (h) => { const c = new THREE.Color(h); return [c.r, c.g, c.b]; };

// ---------- albedo per material key: untextured materials by hand, textured ones as set mean x
// tint read straight from materials.js, then each style's roles on top (as the page's styler does)
const ALB = {
  frame: lin(0x1c1c1c), tv: lin(0x101010), blackSatin: lin(0x151515), brass: lin(0xb9975c), chrome: lin(0xbbbbbb), mirror: lin(0xaaaaaa),
  ceramic: lin(0xeeeeec), charcoal: lin(0x2a2826), soil: lin(0x5a4a3a), bronze: lin(0x5a4430), ground: lin(0xb59f82), poolWater: lin(0x5aa8b0),
};
const BASESET = {};
const matSrc = readFileSync(new URL('../src/materials.js', import.meta.url), 'utf8');
for (const m of matSrc.matchAll(/M\.(\w+) = pbr\('(\w+)', \{([^}]*)/g)) {
  const c = /color: (0x[0-9a-f]+)/i.exec(m[3]), a = SET_AVG[m[2]];
  if (!a) continue;
  BASESET[m[1]] = m[2];
  ALB[m[1]] = lin(c ? +c[1] : 0xffffff).map((v, i) => v * a[i]);
}
function albedoFor(style) {
  const out = { ...ALB };
  for (const [k, o] of Object.entries(STYLES[style].roles)) {
    if (o.albedo !== undefined) { out[k] = lin(o.albedo); continue; }
    if (o.color === undefined) continue;
    const set = BASESET[k] ? (o.set || BASESET[k]) : null;
    out[k] = lin(o.color).map((v, i) => v * (set ? SET_AVG[set][i] : 1));
  }
  return out;
}
const SKIP = new Set(['glass', 'glassLight', 'sheer', 'lattice', 'rail', 'pool', 'room', 'leaf', 'leafOlive', 'flower', 'flowerPink', 'frond']);
// night fixtures: intensity (candela-like, page units), softening radius, and a downward lobe
const LAMP = { downlight: { I: 18, r: 0.12, lobe: true }, bulb: { I: 4, r: 0.15 }, lampShade: { I: 6, r: 0.25 }, led: { I: 1.2, r: 0.3 }, fire: { I: 8, r: 0.3 } };
const WARM = [1, 0.72, 0.45];

// ---------- triangles: neighbours, ground and the hero shell + interior are shared by all styles
function collect(geos, m, out, lamps) {
  const v = new THREE.Vector3();
  for (const [k, g] of geos) {
    if (SKIP.has(k)) continue;
    const p = g.attributes.position, idx = g.index.array;
    for (let i = 0; i < idx.length; i++) { v.fromBufferAttribute(p, idx[i]); if (m) v.applyMatrix4(m); out.pos.push(v.x, v.y, v.z); }
    for (let i = 0; i < idx.length; i += 3) out.key.push(k);
    if (!lamps || !LAMP[k]) continue;
    const thr = k === 'led' ? 0.6 : 0.35, box = new THREE.Box3(), c = new THREE.Vector3();
    for (let i = 0; i < idx.length; i += 3) { // cluster emitter triangles into fixtures
      box.makeEmpty();
      for (let j = 0; j < 3; j++) box.expandByPoint(v.fromBufferAttribute(p, idx[i + j]));
      box.getCenter(c);
      const near = lamps.find((l) => l.k === k && l.box.distanceToPoint(c) < thr);
      if (near) near.box.union(box); else lamps.push({ k, box: box.clone() });
    }
  }
}
function finishLamps(raw) { // long strips become a row of points; bigger clusters shine harder
  const out = [];
  for (const l of raw) {
    const T = LAMP[l.k], size = l.box.getSize(new THREE.Vector3()), axis = size.x > size.z ? 'x' : 'z';
    const n = l.k === 'led' ? Math.max(1, Math.ceil(size[axis] / 0.6)) : 1;
    for (let i = 0; i < n; i++) {
      const p = l.box.getCenter(new THREE.Vector3());
      if (n > 1) p[axis] = l.box.min[axis] + (i + 0.5) / n * size[axis];
      const rad = n > 1 ? 0.3 : size.length() / 2;
      out.push({ k: l.k, p, rad, r: Math.max(T.r, rad), I: T.I * (n > 1 ? 1 : Math.min(3, Math.max(1, rad / T.r))) });
    }
  }
  return out;
}
const base = { pos: [], key: [] }, heroLamps = [];
const HB = new Builder();
buildShell(HB, { hero: true });
buildInterior(HB);
collect(HB.geometries(), null, base, heroLamps);
const NB = new Builder();
buildShell(NB, { hero: false });
const ng = NB.geometries(), ngM = new Map([...ng].map(([k, g]) => [k, mirrorX(g, 3.05)]));
for (const ox of [-12.2, -6.1, 6.1, 12.2]) collect(Math.abs(ox) === 6.1 ? ngM : ng, new THREE.Matrix4().makeTranslation(ox, 0, 0), base);
for (const ox of [-12.2, -6.1, 0, 6.1, 12.2]) for (const z of [-37, 12]) {
  collect(ng, new THREE.Matrix4().makeTranslation(6.1 + ox, 0, z).multiply(new THREE.Matrix4().makeRotationY(Math.PI)), base);
}
for (const [x, z] of [[-80, -80], [80, -80], [80, 60], [-80, -80], [80, 60], [-80, 60]]) base.pos.push(x, -0.01, z);
base.key.push('ground', 'ground');

function sceneFor(style) {
  const sb = { pos: [], key: [] }, raw = heroLamps.map((l) => ({ k: l.k, box: l.box.clone() }));
  const SB = new Builder();
  buildStyleSet(SB, style, makeKit(SB, { bush: [], flower: [], olive: [], pink: [] }));
  collect(SB.geometries(), null, sb, raw);
  const pos = new Float32Array(base.pos.length + sb.pos.length);
  pos.set(base.pos); pos.set(sb.pos, base.pos.length);
  const alb = albedoFor(style), keys = base.key.concat(sb.key), col = new Float32Array(pos.length);
  keys.forEach((k, t) => { const a = alb[k] || [0.5, 0.5, 0.5]; for (let j = 0; j < 3; j++) col.set(a, (t * 3 + j) * 3); });
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const lamps = finishLamps(raw);
  console.log(`${style}: ${pos.length / 9} triangles, ${lamps.length} lamp points`);
  return { bvh: new MeshBVH(geo), col: geo.attributes.color, lamps };
}

// ---------- Preetham sky, ported from three/examples/jsm/objects/Sky.js (golden-hour state)
const SKY = { turbidity: 5.0, rayleigh: 1.6, mie: 0.0024, mieG: 0.72, gain: 0.82 };
const totalRayleigh = [5.804542996261093e-6, 1.3562911419845635e-5, 3.0265902468824876e-5];
const MieConst = [1.8399918514433978e14, 2.7798023919660528e14, 4.0790479543861094e14];
const sunE = (() => { const z = Math.max(-1, Math.min(1, sunDir.y)); return 1000 * Math.max(0, 1 - Math.exp(-((1.6110731556870734 - Math.acos(z)) / 1.5))); })();
const betaR = totalRayleigh.map((v) => v * SKY.rayleigh);
const betaM = MieConst.map((v) => 0.434 * (0.2 * SKY.turbidity * 10e-18) * v * SKY.mie);
function sky(d) {
  const zen = Math.acos(Math.max(0, d.y));
  const inv = 1 / (Math.cos(zen) + 0.15 * Math.pow(93.885 - zen * 180 / Math.PI, -1.253));
  const sR = 8.4e3 * inv, sM = 1.25e3 * inv;
  const ct = d.dot(sunDir);
  const rP = 0.05968310365946075 * (1 + Math.pow(ct * 0.5 + 0.5, 2));
  const g = SKY.mieG, mP = 0.07957747154594767 * (1 - g * g) / Math.pow(1 - 2 * g * ct + g * g, 1.5);
  const out = [0, 0, 0];
  for (let c = 0; c < 3; c++) {
    const Fex = Math.exp(-(betaR[c] * sR + betaM[c] * sM));
    const ratio = (betaR[c] * rP + betaM[c] * mP) / (betaR[c] + betaM[c]);
    let Lin = Math.pow(sunE * ratio * (1 - Fex), 1.5);
    Lin *= 1 + (Math.pow(sunE * ratio * Fex, 0.5) - 1) * Math.min(1, Math.max(0, Math.pow(1 - sunDir.y, 5)));
    out[c] = ((Lin + 0.1 * Fex) * 0.04 + [0, 0.0003, 0.00075][c]) * SKY.gain;
  }
  return out;
}

// ---------- probes
const probePos = (i) => { const x = i % DIMS[0], y = Math.floor(i / DIMS[0]) % DIMS[1], z = Math.floor(i / (DIMS[0] * DIMS[1])); return new THREE.Vector3(MIN[0] + x * SP, MIN[1] + y * SP, MIN[2] + z * SP); };
const dirsFor = (n) => { // Fibonacci sphere
  const out = [];
  for (let i = 0; i < n; i++) { const y = 1 - (i + 0.5) / n * 2, r = Math.sqrt(1 - y * y), a = i * 2.399963229728653; out.push(new THREE.Vector3(Math.cos(a) * r, y, Math.sin(a) * r)); }
  return out;
};
const DIRS = dirsFor(RAYS), DIRS_MASK = dirsFor(48);
// premultiplied L1 irradiance: E(n) = c0 + c.(y,z,x) gives pi*Y00^2 = 0.25 and 2pi/3*Y1^2 = 0.5
const K0 = Math.PI * 0.282095 * 0.282095, K1 = 2 * Math.PI / 3 * 0.488603 * 0.488603;
const ray = new THREE.Ray(), tmp = new THREE.Vector3(), nrm = new THREE.Vector3();
const visible = (bvh, from, dir, maxD) => { ray.origin.copy(from); ray.direction.copy(dir); return !bvh.raycastFirst(ray, THREE.DoubleSide, 0.002, maxD); };
function evalProbes(C, p, n) { // trilinear interpolation of baked irradiance at p for normal n
  const g = [(p.x - MIN[0]) / SP, (p.y - MIN[1]) / SP, (p.z - MIN[2]) / SP];
  const i0 = g.map((v, k) => Math.max(0, Math.min(DIMS[k] - 2, Math.floor(v))));
  const f = g.map((v, k) => Math.max(0, Math.min(1, v - i0[k])));
  const out = [0, 0, 0];
  for (let dz = 0; dz < 2; dz++) for (let dy = 0; dy < 2; dy++) for (let dx = 0; dx < 2; dx++) {
    const w = (dx ? f[0] : 1 - f[0]) * (dy ? f[1] : 1 - f[1]) * (dz ? f[2] : 1 - f[2]);
    const idx = ((i0[2] + dz) * DIMS[1] + (i0[1] + dy)) * DIMS[0] + (i0[0] + dx);
    for (let c = 0; c < 3; c++) { const o = idx * 12 + c * 4; out[c] += w * Math.max(0, C[o] + C[o + 1] * n.y + C[o + 2] * n.z + C[o + 3] * n.x); }
  }
  return out;
}
let seed = 1; const rnd = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);
const rotFor = (m) => m.makeRotationFromQuaternion(new THREE.Quaternion().setFromEuler(new THREE.Euler(rnd() * 6.28, rnd() * 6.28, rnd() * 6.28)));

// probes sunk in walls or furniture see mostly back faces; they are refilled from neighbours
function maskFor({ bvh }) {
  const bad = new Uint8Array(NP), rot = new THREE.Matrix4(), d = new THREE.Vector3();
  for (let i = 0; i < NP; i++) {
    const p = probePos(i); rotFor(rot);
    let back = 0;
    for (const d0 of DIRS_MASK) {
      d.copy(d0).applyMatrix4(rot); ray.origin.copy(p); ray.direction.copy(d);
      const h = bvh.raycastFirst(ray, THREE.DoubleSide, 0, 200);
      if (h && h.face.normal.dot(d) > 0) back++;
    }
    bad[i] = back / DIRS_MASK.length > 0.25 ? 1 : 0;
  }
  return bad;
}
function fill(C, open, bad0) {
  const bad = bad0.slice(), acc = new Float32Array(13);
  for (let it = 0; it < 8; it++) {
    const done = [];
    for (let i = 0; i < NP; i++) {
      if (!bad[i]) continue;
      const x = i % DIMS[0], y = Math.floor(i / DIMS[0]) % DIMS[1], z = Math.floor(i / (DIMS[0] * DIMS[1]));
      acc.fill(0); let n = 0;
      for (const [dx, dy, dz] of [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]]) {
        const X = x + dx, Y = y + dy, Z = z + dz;
        if (X < 0 || Y < 0 || Z < 0 || X >= DIMS[0] || Y >= DIMS[1] || Z >= DIMS[2]) continue;
        const j = (Z * DIMS[1] + Y) * DIMS[0] + X;
        if (bad[j]) continue;
        for (let k = 0; k < 12; k++) acc[k] += C[j * 12 + k];
        if (open) acc[12] += open[j];
        n++;
      }
      if (!n) continue;
      for (let k = 0; k < 12; k++) C[i * 12 + k] = acc[k] / n;
      if (open) open[i] = acc[12] / n;
      done.push(i);
    }
    for (const i of done) bad[i] = 0;
  }
}
function addDirect(C, i, p, { bvh, lamps }) {
  for (const l of lamps) {
    tmp.copy(l.p).sub(p);
    const dist = tmp.length();
    if (dist > 9) continue;
    tmp.multiplyScalar(1 / Math.max(dist, 1e-4));
    const reach = dist - l.rad - 0.03;
    if (reach > 0.01 && !visible(bvh, p, tmp, reach)) continue;
    const lobe = LAMP[l.k].lobe ? Math.max(0, tmp.y) ** 2 : 1;
    const e = l.I * lobe / (dist * dist + l.r * l.r);
    for (let c = 0; c < 3; c++) {
      const ec = e * WARM[c], o = i * 12 + c * 4;
      C[o] += K0 * ec; C[o + 1] += K1 * ec * tmp.y; C[o + 2] += K1 * ec * tmp.z; C[o + 3] += K1 * ec * tmp.x;
    }
  }
}
function pass(ctx, comp, prev, bad) {
  const { bvh, col } = ctx;
  const C = new Float32Array(NP * 12), open = comp === 'S' && !prev ? new Float32Array(NP) : null;
  const rot = new THREE.Matrix4(), d = new THREE.Vector3(), hp = new THREE.Vector3();
  const dw = 4 * Math.PI / RAYS;
  for (let i = 0; i < NP; i++) {
    const p = probePos(i);
    if (comp !== 'N' || prev) {
      rotFor(rot);
      const L = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
      let miss = 0;
      for (const d0 of DIRS) {
        d.copy(d0).applyMatrix4(rot);
        ray.origin.copy(p); ray.direction.copy(d);
        const h = bvh.raycastFirst(ray, THREE.DoubleSide, 0, 200);
        let rad = null;
        if (!h) { miss++; if (comp === 'S') rad = sky(d); }
        else {
          nrm.copy(h.face.normal);
          if (nrm.dot(d) > 0) nrm.negate();
          const fi = h.face.a;
          hp.copy(h.point).addScaledVector(nrm, 0.01);
          let E = [0, 0, 0];
          if (comp === 'U') { const c = nrm.dot(sunDir); if (c > 0 && visible(bvh, hp, sunDir, 300)) E = SUN.map((s) => s * c); }
          if (prev) { const ep = evalProbes(prev, hp.clone().addScaledVector(nrm, 0.2), nrm); E = E.map((v, k) => v + ep[k]); }
          rad = [col.getX(fi) / Math.PI * E[0], col.getY(fi) / Math.PI * E[1], col.getZ(fi) / Math.PI * E[2]];
        }
        if (!rad) continue;
        for (let c = 0; c < 3; c++) { L[c * 4] += rad[c]; L[c * 4 + 1] += rad[c] * d.y; L[c * 4 + 2] += rad[c] * d.z; L[c * 4 + 3] += rad[c] * d.x; }
      }
      for (let c = 0; c < 3; c++) {
        C[i * 12 + c * 4] = K0 * L[c * 4] * dw;
        for (let k = 1; k < 4; k++) C[i * 12 + c * 4 + k] = K1 * L[c * 4 + k] * dw;
      }
      if (open) open[i] = miss / RAYS;
    }
    if (comp === 'N') addDirect(C, i, p, ctx);
  }
  fill(C, open, bad);
  return { C, open };
}
function bake(ctx, comp, bad) {
  const t0 = Date.now();
  let r = pass(ctx, comp, null, bad);
  const open = r.open;
  for (let k = 1; k < PASSES; k++) r = pass(ctx, comp, r.C, bad);
  let mx = 0, sum = 0, inS = 0, inN = 0;
  for (let i = 0; i < NP; i++) {
    const v = r.C[i * 12]; sum += v; mx = Math.max(mx, v);
    if (globalThis.OPEN && globalThis.OPEN[i] < 0.15 && !bad[i]) { inS += v; inN++; }
  }
  console.log(`  ${comp}: ${((Date.now() - t0) / 1000).toFixed(1)}s, mean ${(sum / NP).toFixed(3)}, indoor mean ${inN ? (inS / inN).toFixed(3) : '-'}, max ${mx.toFixed(2)}`);
  return { C: r.C, open };
}
// 8-bit encoding per probe: DC rgb as log2 over 20 stops (0 = black), the luminance gradient
// relative to the DC in [-2, 2], and for the sky component the open-sky fraction
function encode(C, open) {
  const st = open ? 7 : 6, out = new Uint8Array(NP * st);
  for (let i = 0; i < NP; i++) {
    const o = i * 12, b = i * st, g = [0, 0, 0];
    let l = 0;
    for (let c = 0; c < 3; c++) {
      const v = Math.max(0, C[o + c * 4]);
      out[b + c] = v > 2 ** -14 ? Math.round(Math.min(255, Math.max(1, (Math.log2(v) + 14) / 20 * 255))) : 0;
      l += LUM[c] * v;
      g[0] += LUM[c] * C[o + c * 4 + 3]; g[1] += LUM[c] * C[o + c * 4 + 1]; g[2] += LUM[c] * C[o + c * 4 + 2];
    }
    for (let k = 0; k < 3; k++) out[b + 3 + k] = Math.round(Math.max(0, Math.min(255, (l > 1e-6 ? g[k] / l : 0) / 4 * 255 + 127.5)));
    if (open) out[b + 6] = Math.round(Math.max(0, Math.min(1, open[i])) * 255);
  }
  return Buffer.from(out).toString('base64');
}

const res = { N: {} };
for (const style of Object.keys(STYLES)) {
  const ctx = sceneFor(style), bad = maskFor(ctx);
  if (style === 'minimal') {
    const s = bake(ctx, 'S', bad);
    globalThis.OPEN = s.open;
    res.S = encode(s.C, s.open);
    res.U = encode(bake(ctx, 'U', bad).C);
  }
  res.N[style] = encode(bake(ctx, 'N', bad).C);
}
writeFileSync(new URL('../src/gi-data.js', import.meta.url), `// Generated by scripts/bake-gi.mjs - do not edit.\nexport const GI = ${JSON.stringify({ spacing: SP, min: MIN, dims: DIMS, ...res })};\n`);
console.log('wrote src/gi-data.js');
