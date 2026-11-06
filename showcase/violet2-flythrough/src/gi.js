import * as THREE from 'three';
import { shared } from './materials.js';

const LUM = [0.2126, 0.7152, 0.0722];

// The bake (scripts/bake-gi.mjs) stores each light source separately in assets/gi/<name>.json, so
// the page can mix them for the moment: sky and sun bounce follow the atmosphere, lamps follow the
// style and the dusk. The data lives beside the textures rather than in the bundle: it downloads
// in parallel with them instead of ahead of the first texture request, only the style on screen is
// decoded, and the host serves .json where it refuses raw binaries. Mixing happens on the CPU into
// two small 3D textures, only when the inputs actually move.
//
// Components: S sky (with the open-sky fraction), U sun bounce for the held sun, U2 sun bounce for
// the swung sun the terrace chapters use, N.<style> that style's lamps.

// base64 -> bytes through the browser's own decoder (a data: URL fetch), which runs off the main
// thread; atob stands in where a sandbox refuses data: URLs
async function bytes(b64) {
  try {
    return new Uint8Array(await (await fetch('data:application/octet-stream;base64,' + b64)).arrayBuffer());
  } catch (e) {
    const s = atob(b64), u8 = new Uint8Array(s.length);
    for (let i = 0; i < s.length; i++) u8[i] = s.charCodeAt(i);
    return u8;
  }
}

function decode(u8, np, hasOpen) {
  const st = hasOpen ? 7 : 6;
  const dc = new Float32Array(np * 3), gr = new Float32Array(np * 3), open = hasOpen ? new Float32Array(np) : null;
  for (let i = 0; i < np; i++) {
    const o = i * st;
    let l = 0;
    for (let c = 0; c < 3; c++) { const v = u8[o + c] ? 2 ** (u8[o + c] / 255 * 20 - 14) : 0; dc[i * 3 + c] = v; l += LUM[c] * v; }
    for (let k = 0; k < 3; k++) gr[i * 3 + k] = (u8[o + 3 + k] - 127.5) / 255 * 4 * l;
    if (open) open[i] = u8[o + 6] / 255;
  }
  return { dc, gr, open };
}

// base: folder of the baked files; style: the lamp set needed before the first frame.
// Returns { ready, set, prepare }: ready resolves once the boot components are in the textures'
// reach; set(kS, kU, kU2, kN, style) re-mixes; prepare(style) fetches a lamp set ahead of a switch.
export function createGI({ base = 'assets/gi/', style = 'minimal' } = {}) {
  const g = shared.gi;
  let meta = null, S = null, U = null, U2 = null, t0 = null, t1 = null, insideH = null, last = '';
  const N = {}, pending = {};
  const h = THREE.DataUtils.toHalfFloat;

  const load = async (name) => {
    const r = await fetch(`${base}${name}.json`);
    if (!r.ok) throw new Error(`${name}.json ${r.status}`);
    const j = await r.json();
    if (!meta) meta = { dims: j.dims, spacing: j.spacing, min: j.min, np: j.dims[0] * j.dims[1] * j.dims[2] };
    return decode(await bytes(j.data), meta.np, j.stride === 7);
  };
  // a lamp set arrives once, whatever order the clicks come in; a failed fetch is forgotten so the
  // next switch can retry it
  function prepare(key) {
    if (N[key]) return Promise.resolve();
    if (!pending[key]) {
      pending[key] = load(`N-${key}`).then((n) => { N[key] = n; last = ''; }).finally(() => { delete pending[key]; });
    }
    return pending[key];
  }

  const mk = () => {
    const { dims } = meta;
    const t = new THREE.Data3DTexture(new Uint16Array(meta.np * 4), dims[0], dims[1], dims[2]);
    t.format = THREE.RGBAFormat; t.type = THREE.HalfFloatType;
    t.minFilter = t.magFilter = THREE.LinearFilter;
    t.wrapS = t.wrapT = t.wrapR = THREE.ClampToEdgeWrapping;
    t.unpackAlignment = 1;
    return t;
  };

  const ready = (async () => {
    [S, U, U2] = await Promise.all([load('S'), load('U'), load('U2'), prepare(style)]);
    const { dims, spacing: SP, min: MIN, np } = meta;
    // where the sky is mostly hidden the volume takes over from the env map
    insideH = new Uint16Array(np);
    for (let i = 0; i < np; i++) insideH[i] = h(1 - THREE.MathUtils.smoothstep(S.open[i], 0.2, 0.4));
    t0 = mk(); t1 = mk();
    g.uGi0.value = t0; g.uGi1.value = t1;
    g.uGiA.value.set(1 / (SP * dims[0]), 1 / (SP * dims[1]), 1 / (SP * dims[2]));
    g.uGiB.value.set(0.5 / dims[0] - MIN[0] / (SP * dims[0]), 0.5 / dims[1] - MIN[1] / (SP * dims[1]), 0.5 / dims[2] - MIN[2] / (SP * dims[2]));
  })();

  // A weight is quantised to 1/128 so an easing light remixes a few times, not every frame, and
  // sanitised: a NaN or Inf from a sky read-back would otherwise fill every probe (toHalfFloat
  // turns NaN into a NaN half and Inf into 65504) and bloom would spread it over the frame.
  const weight = (v) => (Number.isFinite(v) ? Math.round(Math.min(Math.max(v, 0), 64) * 128) / 128 : 0);
  // kS, kU, kU2, kN: rgb weights for sky, held-sun bounce, swung-sun bounce and lamps. A style
  // whose lamps have not arrived borrows the first set loaded until they do.
  function set(kS, kU, kU2, kN, style) {
    if (!t0) return false;
    kS = kS.map(weight); kU = kU.map(weight); kU2 = kU2.map(weight); kN = kN.map(weight);
    if (!N[style]) prepare(style).catch(() => {});
    const n = N[style] || Object.values(N)[0];
    const key = [...kS, ...kU, ...kU2, ...kN].join() + '|' + (N[style] ? style : '*');
    if (key === last) return false;
    last = key;
    const a = t0.image.data, b = t1.image.data, np = meta.np;
    const lum = (k) => LUM[0] * k[0] + LUM[1] * k[1] + LUM[2] * k[2];
    const lS = lum(kS), lU = lum(kU), lU2 = lum(kU2), lN = lum(kN);
    for (let i = 0; i < np; i++) {
      const o = i * 3, q = i * 4;
      for (let c = 0; c < 3; c++) a[q + c] = h(kS[c] * S.dc[o + c] + kU[c] * U.dc[o + c] + kU2[c] * U2.dc[o + c] + kN[c] * n.dc[o + c]);
      a[q + 3] = insideH[i];
      for (let k = 0; k < 3; k++) b[q + k] = h(lS * S.gr[o + k] + lU * U.gr[o + k] + lU2 * U2.gr[o + k] + lN * n.gr[o + k]);
      // the open-sky fraction rides in the gradient's alpha: the shader's specular occlusion
      b[q + 3] = h(S.open[i]);
    }
    t0.needsUpdate = true; t1.needsUpdate = true;
    g.uGiDims.value.set(...meta.dims);
    return true;
  }
  return { ready, set, prepare };
}
