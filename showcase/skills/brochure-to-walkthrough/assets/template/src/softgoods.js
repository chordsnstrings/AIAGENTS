import * as THREE from 'three';

// Soft furnishings shaped procedurally: a duvet that lies on the mattress and rolls over its
// edges, pillows with a piped seam and loft, a throw across the foot, sheers with uneven pleats.
// Everything is smooth noise plus a simple drape rule; nothing is simulated at run time, so
// each piece is just another static mesh merged by the builder.

const hash = (i, j, s) => {
  let h = Math.imul(i, 374761393) + Math.imul(j, 668265263) + Math.imul(s, 2246822519);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
};
function vnoise(x, y, s) {
  const i = Math.floor(x), j = Math.floor(y), fx = x - i, fy = y - j;
  const u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy);
  const a = hash(i, j, s), b = hash(i + 1, j, s), c = hash(i, j + 1, s), d = hash(i + 1, j + 1, s);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
const fbm = (x, y, s) => vnoise(x, y, s) * 0.6 + vnoise(x * 2.1, y * 2.1, s + 7) * 0.28 + vnoise(x * 4.3, y * 4.3, s + 13) * 0.12;
const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

// an (nu+1) x (nv+1) vertex grid; fn(a, b) -> [x, y, z, u, v] with a, b in [0, 1]
function grid(nu, nv, fn) {
  const pos = [], uv = [], idx = [];
  for (let j = 0; j <= nv; j++) for (let i = 0; i <= nu; i++) {
    const r = fn(i / nu, j / nv);
    pos.push(r[0], r[1], r[2]); uv.push(r[3], r[4]);
  }
  for (let j = 0; j < nv; j++) for (let i = 0; i < nu; i++) {
    const a = j * (nu + 1) + i, b = a + 1, c = a + nu + 1, d = c + 1;
    idx.push(a, c, b, b, c, d);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

// Cloth laid on a box top (x 0..L from the head end towards the foot, z across, top at y 0):
// spare cloth beyond the top rolls over an edge of radius r and falls, with pleats that grow
// towards the hem. Corners hang lower, as real ones do. dropFoot 0 leaves the foot edge flat.
export function drape({ L, W, drop = 0.3, dropFoot = drop, r = 0.07, loft = 0.05, pleat = 0.03, seed = 1, res = 0.03 }) {
  const Lc = L + dropFoot, Wc = W + 2 * drop, arc = Math.PI * r / 2;
  const map = (a, b) => {
    const s = a * Lc, t = (b - 0.5) * Wc;
    const dx = dropFoot > 0 ? Math.max(0, s - L) : 0, dz = Math.max(0, Math.abs(t) - W / 2);
    const e = Math.hypot(dx, dz), ox = e > 0 ? dx / e : 0, oz = e > 0 ? Math.sign(t) * dz / e : 0;
    const hang = smooth(0, 0.14, e);
    // loft on top, soft creases running diagonally, both relaxing as the cloth turns down
    const puff = loft * (0.5 + 0.5 * fbm(s * 2.4, t * 2.4, seed)) * (1 - 0.5 * hang);
    const crease = 0.014 * Math.abs(Math.sin((s * 0.8 + t * 1.3) * 5 + fbm(s * 1.5, t * 1.5, seed + 5) * 6)) * (1 - hang);
    let out, y;
    if (e < arc) { const th = e / r; out = r * Math.sin(th); y = -r * (1 - Math.cos(th)); } else { out = r; y = -r - (e - arc); }
    const along = dz >= dx ? s : t;
    const wl = 0.13 + 0.1 * fbm(along * 1.7, seed * 0.37, seed + 9);
    const amp = pleat * smooth(0.05, 0.3, e) * (0.6 + 0.8 * fbm(along * 2.3, 0.5, seed + 11)) * (dx > 0 && dz > 0 ? 1.7 : 1);
    out += amp * Math.sin(along / wl * Math.PI * 2) + 0.035 * smooth(0.12, 0.35, e) + puff * hang;
    const x = Math.min(s, L) + ox * out, z = Math.sign(t) * Math.min(Math.abs(t), W / 2) + oz * out;
    return [x, y + puff * (1 - hang) - crease, z, s, t];
  };
  const g = grid(Math.ceil(Lc / res), Math.ceil(Wc / res), map);
  // the head edge, for a rolled hem
  g.userData.head = Array.from({ length: 41 }, (_, k) => new THREE.Vector3(...map(0, k / 40).slice(0, 3)));
  return g;
}

// Pillow: two faces meeting at a piped seam, loft shaped by a superellipse so corners stay thin.
export function pillow({ L = 0.7, D = 0.48, T = 0.17, seed = 1, n = 16 }) {
  const faces = [1, -1].map((side) => grid(n, n, (a, b) => {
    const u = a * 2 - 1, v = (b * 2 - 1) * side;
    const f = Math.pow(Math.max(0, (1 - Math.abs(u) ** 2.4) * (1 - Math.abs(v) ** 2.4)), 0.36);
    // uneven fill, and the soft dent along the middle a plumped cushion keeps
    const sq = (1 + (fbm(u * 1.4 + 3, v * 1.4, seed) - 0.5) * 0.35) * (1 - (side > 0 ? 0.22 : 0.08) * Math.exp(-u * u * 18) * (1 - v * v));
    return [u * L / 2 * (1 - 0.07 * (1 - v * v) * f), side * T / 2 * f * sq, v * D / 2 * (1 - 0.06 * (1 - u * u) * f), u * L / 2, v * D / 2];
  }));
  return merge(faces);
}

// Sheer panel in the x-y plane, centred: pleats of uneven pitch and depth, flaring at the hem.
export function sheer(w, h, seed = 1) {
  const nu = Math.max(24, Math.round(w / 0.025)), nv = Math.max(8, Math.round(h / 0.25));
  // integrate a varying pitch so the pleat phase stays continuous
  const phase = new Float32Array(nu + 1);
  for (let i = 1; i <= nu; i++) { const x = i / nu * w; phase[i] = phase[i - 1] + (w / nu) / (0.17 + 0.09 * vnoise(x * 2.2, 0.3, seed)) * Math.PI * 2; }
  return grid(nu, nv, (a, b) => {
    const i = Math.round(a * nu), x = a * w, yN = b;
    const amp = (0.026 + 0.022 * vnoise(x * 3.1, 1.7, seed + 3)) * (1 + 0.6 * (1 - yN) ** 2);
    const z = amp * Math.sin(phase[i]) + 0.012 * (1 - yN) ** 2 * vnoise(x * 1.3, 4.1, seed + 5);
    return [x - w / 2, (yN - 0.5) * h, z, x, yN * h];
  });
}

function merge(geos) {
  let n = 0;
  const pos = [], nor = [], uv = [], idx = [];
  for (const g of geos) {
    pos.push(...g.attributes.position.array); nor.push(...g.attributes.normal.array); uv.push(...g.attributes.uv.array);
    for (const i of g.index.array) idx.push(i + n);
    n += g.attributes.position.count;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  return g;
}
