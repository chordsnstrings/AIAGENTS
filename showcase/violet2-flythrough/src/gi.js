import * as THREE from 'three';
import { GI } from './gi-data.js';
import { shared } from './materials.js';

const LUM = [0.2126, 0.7152, 0.0722];
const { dims: DIMS, spacing: SP, min: MIN } = GI;
const NP = DIMS[0] * DIMS[1] * DIMS[2];

// The bake (scripts/bake-gi.mjs) stores each light source separately, so the page can mix them
// for the moment: sky and sun bounce follow the atmosphere, lamps follow the style and the dusk.
// Mixing happens on the CPU into two small 3D textures, only when the inputs actually move.
function decode(b64, hasOpen) {
  const u8 = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0)), st = hasOpen ? 7 : 6;
  const dc = new Float32Array(NP * 3), gr = new Float32Array(NP * 3), open = hasOpen ? new Float32Array(NP) : null;
  for (let i = 0; i < NP; i++) {
    const o = i * st;
    let l = 0;
    for (let c = 0; c < 3; c++) { const v = u8[o + c] ? 2 ** (u8[o + c] / 255 * 20 - 14) : 0; dc[i * 3 + c] = v; l += LUM[c] * v; }
    for (let k = 0; k < 3; k++) gr[i * 3 + k] = (u8[o + 3 + k] - 127.5) / 255 * 4 * l;
    if (open) open[i] = u8[o + 6] / 255;
  }
  return { dc, gr, open };
}

export function createGI() {
  const S = decode(GI.S, true), U = decode(GI.U, false), N = {};
  for (const k of Object.keys(GI.N)) N[k] = decode(GI.N[k], false);
  // where the sky is mostly hidden the volume takes over from the env map
  const inside = new Float32Array(NP);
  for (let i = 0; i < NP; i++) inside[i] = 1 - THREE.MathUtils.smoothstep(S.open[i], 0.2, 0.4);

  const mk = () => {
    const t = new THREE.Data3DTexture(new Uint16Array(NP * 4), DIMS[0], DIMS[1], DIMS[2]);
    t.format = THREE.RGBAFormat; t.type = THREE.HalfFloatType;
    t.minFilter = t.magFilter = THREE.LinearFilter;
    t.wrapS = t.wrapT = t.wrapR = THREE.ClampToEdgeWrapping;
    t.unpackAlignment = 1;
    return t;
  };
  const t0 = mk(), t1 = mk();
  const g = shared.gi;
  g.uGi0.value = t0; g.uGi1.value = t1;
  g.uGiA.value.set(1 / (SP * DIMS[0]), 1 / (SP * DIMS[1]), 1 / (SP * DIMS[2]));
  g.uGiB.value.set(0.5 / DIMS[0] - MIN[0] / (SP * DIMS[0]), 0.5 / DIMS[1] - MIN[1] / (SP * DIMS[1]), 0.5 / DIMS[2] - MIN[2] / (SP * DIMS[2]));

  const h = THREE.DataUtils.toHalfFloat;
  const insideH = Uint16Array.from(inside, h);
  // A weight is quantised to 1/128 so an easing light remixes a few times, not every frame, and
  // sanitised: a NaN or Inf from a sky read-back would otherwise fill every probe (toHalfFloat
  // turns NaN into a NaN half and Inf into 65504) and bloom would spread it over the frame.
  const weight = (v) => (Number.isFinite(v) ? Math.round(Math.min(Math.max(v, 0), 64) * 128) / 128 : 0);
  let last = '';
  // kS, kU, kN: rgb weights for sky, sun bounce and lamps
  function set(kS, kU, kN, style) {
    kS = kS.map(weight); kU = kU.map(weight); kN = kN.map(weight);
    const key = [...kS, ...kU, ...kN].join() + '|' + style;
    if (key === last) return false;
    last = key;
    const n = N[style] || N.minimal, a = t0.image.data, b = t1.image.data;
    const lS = LUM[0] * kS[0] + LUM[1] * kS[1] + LUM[2] * kS[2];
    const lU = LUM[0] * kU[0] + LUM[1] * kU[1] + LUM[2] * kU[2];
    const lN = LUM[0] * kN[0] + LUM[1] * kN[1] + LUM[2] * kN[2];
    for (let i = 0; i < NP; i++) {
      const o = i * 3, q = i * 4;
      for (let c = 0; c < 3; c++) a[q + c] = h(kS[c] * S.dc[o + c] + kU[c] * U.dc[o + c] + kN[c] * n.dc[o + c]);
      a[q + 3] = insideH[i];
      for (let k = 0; k < 3; k++) b[q + k] = h(lS * S.gr[o + k] + lU * U.gr[o + k] + lN * n.gr[o + k]);
    }
    t0.needsUpdate = true; t1.needsUpdate = true;
    g.uGiDims.value.set(...DIMS);
    return true;
  }
  return { set };
}
