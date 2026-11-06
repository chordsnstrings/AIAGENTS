import * as THREE from 'three';
import { artTexture } from './proctex.js';

// Mean linear albedo of each texture set's colour map (every texel linearised first, then averaged:
// the skill's scripts/textures.py --measure), so a role can name the colour a finish should read as
// and the GI bake can use the same albedo. A tint multiplied over a photo-scan applies the scan's
// own cast twice; dividing the scan's mean out is what lets a "white" duvet render white.
export const SET_AVG = {
  ash: [0.412, 0.3, 0.204], boucle: [0.438, 0.437, 0.438], clayplaster: [0.715, 0.715, 0.715], herringbone: [0.294, 0.164, 0.075],
  limewash: [0.731, 0.731, 0.731], linen: [0.408, 0.408, 0.408], marble: [0.42, 0.427, 0.474], microcement: [0.674, 0.674, 0.674],
  nero: [0.055, 0.057, 0.056], oak: [0.279, 0.193, 0.124], papercord: [0.585, 0.585, 0.585], plaster: [0.409, 0.367, 0.351],
  rattan: [0.136, 0.071, 0.038], rug: [0.5, 0.437, 0.295], smokedwalnut: [0.499, 0.327, 0.21], stone: [0.099, 0.093, 0.078],
  terracotta: [0.076, 0.02, 0.01], travertine: [0.741, 0.602, 0.414], velvet: [0.461, 0.461, 0.461], walnut: [0.256, 0.143, 0.081],
  woodfloor: [0.217, 0.118, 0.055], patio: [0.184, 0.188, 0.175], pavers: [0.55, 0.55, 0.55], sidewalk: [0.523, 0.523, 0.523],
  asphalt: [0.058, 0.063, 0.062], sand: [0.51, 0.51, 0.51], gravel: [0.417, 0.398, 0.342], bark: [0.346, 0.292, 0.232], grass: [0.06, 0.109, 0.023],
};

// Mean of each set's roughness channel (G of the packed ORM map). three multiplies the material's
// roughness by that texel, so a polished scan (travertine 0.037) would turn any authored roughness
// into a mirror; dividing the mean out makes a role's rough: the finish's real mean roughness.
export const SET_ROUGH = {
  ash: 0.62, asphalt: 0.661, bark: 0.7, boucle: 0.532, clayplaster: 0.924, grass: 0.545, gravel: 0.474, herringbone: 0.099,
  limewash: 0.84, linen: 0.819, marble: 0.067, microcement: 0.517, nero: 0.115, oak: 0.734, papercord: 0.603, patio: 0.837,
  pavers: 0.875, plaster: 0.92, rattan: 0.604, rug: 0.649, sand: 0.911, sidewalk: 0.695, smokedwalnut: 0.707, stone: 0.935,
  terracotta: 0.752, travertine: 0.037, velvet: 0.727, walnut: 0.577, woodfloor: 0.473,
};

// Four researched interior presets (Dezeen 2026, 1stDibs 2026 survey, Khaleej Times on Dubai
// "restrained luxury", Bayut UAE trends, Domus Academy, paint colours of the year). A preset
// re-parameterises the shared material roles and shows its own furniture set; material types
// and feature flags never change, so switching never recompiles a shader. Every textured role
// names its finish by albedo (the perceived sRGB colour); walls stay light, joinery carries the
// contrast, and velvet adds flat so the sheen gradient rather than the scan's crush reads as velvet.

export const STYLES = {
  minimal: {
    name: 'Warm Minimal', short: 'Minimal',
    blurb: 'Honed travertine, pale oak and ivory bouclé, with lavender as the only colour.',
    palette: ['#EEE8DF', '#F0EEE9', '#D8C8AF', '#C9A97F', '#E3D9CA', '#B7A3CF'],
    sets: [], art: ['#efe8dc', '#cdb89a', '#9d86c0', '#e6d8c3', '#c9b8de'], inside: 1.0,
    roles: {
      travertine: { set: 'travertine', tile: 1.8, albedo: 0xd8c8af, rough: 0.55, joints: [1.2, 0.6, 0.003, 0.72] },
      oakFloor: { set: 'woodfloor', tile: 2.2, albedo: 0xc8a684, rough: 0.75 },
      marbleFloor: { set: 'marble', tile: 1.6, albedo: 0xe6e3dd, rough: 0.6, joints: [0.6, 0.6, 0.002, 0.7] },
      paint: { set: 'plaster', tile: 3.2, albedo: 0xe8e2d9, flat: 0.7, normal: 0.12, rough: 0.95 },
      ceiling: { set: 'plaster', tile: 3.2, albedo: 0xf0ede8, flat: 0.8, normal: 0.08, rough: 1 },
      travertineSlab: { set: 'travertine', tile: 1.4, albedo: 0xd8c8af, rough: 0.6 },
      oak: { set: 'oak', tile: 1.4, albedo: 0xc9a882, rough: 0.7 },
      walnut: { set: 'walnut', tile: 1.2, albedo: 0x5a4030, rough: 0.55 },
      joinery: { set: 'walnut', tile: 1.2, albedo: 0x5a4030, rough: 0.5 },
      marble: { set: 'marble', tile: 1.8, albedo: 0xe6e3dd, rough: 0.5, clearcoat: 0.6 },
      boucle: { set: 'boucle', tile: 0.45, albedo: 0xe3d9ca, normal: 1.4, sheen: 0xffffff },
      velvet: { set: 'velvet', tile: 0.7, albedo: 0xa892c4, flat: 0.5, rough: 0.9, normal: 0.2, sheen: 0xc9b8de },
      linen: { set: 'linen', tile: 0.22, albedo: 0xe9e4db, normal: 0.35, sheen: 0xffffff },
      linenSand: { set: 'linen', tile: 0.3, albedo: 0xd8ccb8, normal: 0.5, sheen: 0xfff4e6 },
      linenGrey: { set: 'linen', tile: 0.5, albedo: 0xbcb6ad },
      rug: { set: 'rug', tile: 0.9, albedo: 0xd9cebd },
      bloom: { color: 0xc3b1de },
      brass: { color: 0xc8a467, rough: 0.28, metal: 1 },
      lampShade: { color: 0xf1e7d6 },
      concrete: { set: 'plaster', tile: 1.5, albedo: 0x9a948c },
      weave: { set: 'rattan', tile: 0.35, albedo: 0xb48f62 },
      sheer: { color: 0xfbf8f2 },
    },
  },
  japandi: {
    name: 'Japandi Calm', short: 'Japandi',
    blurb: 'Oiled oak, oat limewash, black-stained ash and paper light, with a muted heather accent.',
    palette: ['#D9D0C3', '#EAE5DC', '#B3946D', '#3D3833', '#A69D90', '#85788F'],
    sets: ['ash', 'limewash', 'microcement', 'papercord'], art: ['#e9e4da', '#2f2c29', '#a99c8a', '#cfc6b6', '#85788f'], inside: 1.05,
    roles: {
      travertine: { set: 'woodfloor', tile: 2.2, albedo: 0xcfb18d, rough: 0.7, joints: [1, 1, 0, 1] },
      oakFloor: { set: 'woodfloor', tile: 2.2, albedo: 0xcfb18d, rough: 0.7 },
      marbleFloor: { set: 'microcement', tile: 2.0, albedo: 0xb8b1a5, rough: 0.75, joints: [1, 1, 0, 1] },
      paint: { set: 'limewash', tile: 2.4, albedo: 0xe6ded2, flat: 0.35, normal: 0.3, rough: 0.97 },
      ceiling: { set: 'limewash', tile: 3.0, albedo: 0xeeebe4, flat: 0.6, normal: 0.2, rough: 1 },
      travertineSlab: { set: 'microcement', tile: 1.5, albedo: 0xb0a99d, rough: 0.8 },
      oak: { set: 'ash', tile: 1.4, albedo: 0xbf9a6e, rough: 0.65 },
      walnut: { set: 'ash', tile: 1.2, albedo: 0x3d3530, rough: 0.6 },
      joinery: { set: 'ash', tile: 1.4, albedo: 0x453b33, rough: 0.6 },
      marble: { set: 'microcement', tile: 1.6, albedo: 0xaea69a, rough: 0.6, clearcoat: 0.05 },
      boucle: { set: 'linen', tile: 0.5, albedo: 0xbdb3a4, normal: 0.9, sheen: 0xe8e0d4 },
      velvet: { set: 'boucle', tile: 0.45, albedo: 0x8a7d94, flat: 0.5, rough: 0.9, normal: 0.6, sheen: 0xaea2b8 },
      linen: { set: 'linen', tile: 0.22, albedo: 0xe4ded3, normal: 0.35, sheen: 0xffffff },
      linenSand: { set: 'linen', tile: 0.3, albedo: 0xb9ae9c, normal: 0.5, sheen: 0xeee4d6 },
      linenGrey: { set: 'linen', tile: 0.5, albedo: 0x8f877d },
      rug: { set: 'rug', tile: 0.9, albedo: 0xbfb3a0 },
      bloom: { color: 0xf4f1ea },
      brass: { color: 0x2c2a27, rough: 0.5, metal: 0.7 },
      lampShade: { color: 0xf7f2e8 },
      concrete: { set: 'plaster', tile: 1.5, albedo: 0x55504a },
      weave: { set: 'papercord', tile: 0.22, albedo: 0xd2c3a3 },
      sheer: { color: 0xf2ede4 },
    },
  },
  desert: {
    name: 'Desert Organic', short: 'Desert',
    blurb: 'Sun-baked curves in lime plaster, terracotta, rattan and caramel elm, with dusty mauve.',
    palette: ['#E4D2BB', '#F3ECE1', '#B5704F', '#8F6440', '#D6C3A5', '#A77B8C'],
    sets: ['terracotta', 'clayplaster', 'limewash', 'rattan'], art: ['#efe2cf', '#b5704f', '#d6c3a5', '#a77b8c', '#8f6440'], inside: 1.0,
    roles: {
      travertine: { set: 'terracotta', tile: 1.2, albedo: 0xc28f72, rough: 0.85, joints: [1, 1, 0, 1] },
      oakFloor: { set: 'woodfloor', tile: 2.2, albedo: 0xb98a64, rough: 0.72 },
      marbleFloor: { set: 'terracotta', tile: 0.9, albedo: 0xc28f72, rough: 0.8, joints: [1, 1, 0, 1] },
      paint: { set: 'clayplaster', tile: 2.2, albedo: 0xeee0cd, flat: 0.3, normal: 0.3, rough: 0.97 },
      ceiling: { set: 'limewash', tile: 3.0, albedo: 0xf3ece2, flat: 0.6, normal: 0.25, rough: 1 },
      travertineSlab: { set: 'travertine', tile: 1.4, albedo: 0xdcc6a4, rough: 0.65 },
      oak: { set: 'oak', tile: 1.4, albedo: 0xb98a5e, rough: 0.7 },
      walnut: { set: 'oak', tile: 1.2, albedo: 0x8a5a36, rough: 0.6 },
      joinery: { set: 'oak', tile: 1.4, albedo: 0x9c6a42, rough: 0.6 },
      marble: { set: 'travertine', tile: 1.6, albedo: 0xdfcbaa, rough: 0.5, clearcoat: 0.1 },
      boucle: { set: 'linen', tile: 0.5, albedo: 0xd6c3a5, normal: 1.0, sheen: 0xfff1dc },
      velvet: { set: 'velvet', tile: 0.7, albedo: 0xa77b8c, flat: 0.5, rough: 0.9, normal: 0.2, sheen: 0xc9a3b2 },
      linen: { set: 'linen', tile: 0.22, albedo: 0xe8e2d8, normal: 0.35, sheen: 0xffffff },
      linenSand: { set: 'linen', tile: 0.3, albedo: 0xcbb89a, normal: 0.5, sheen: 0xfff1dc },
      linenGrey: { set: 'linen', tile: 0.5, albedo: 0xb39e84 },
      rug: { set: 'rug', tile: 0.9, albedo: 0xd9c9ad },
      bloom: { color: 0xd99577 },
      brass: { color: 0xb08d57, rough: 0.4, metal: 1 },
      lampShade: { color: 0xf0e2cd },
      concrete: { set: 'clayplaster', tile: 1.2, albedo: 0xb0744f },
      weave: { set: 'rattan', tile: 0.35, albedo: 0xb48f62 },
      sheer: { color: 0xf7efe3 },
    },
  },
  luxe: {
    name: 'Aubergine Luxe', short: 'Luxe',
    blurb: 'Walnut, dark marble, mocha Venetian plaster and aubergine velvet, with antique brass.',
    palette: ['#7B6A5F', '#DCD2C6', '#3B3534', '#5C3F2E', '#4A2740', '#A8884F'],
    sets: ['nero', 'herringbone', 'smokedwalnut'], art: ['#d8cbbd', '#4a2740', '#a8884f', '#7b6a5f', '#2b2523'], inside: 1.0,
    roles: {
      travertine: { set: 'nero', tile: 2.4, albedo: 0x3d3935, rough: 0.42, joints: [1.2, 1.2, 0.003, 0.75] },
      oakFloor: { set: 'herringbone', tile: 1.6, albedo: 0x8f6d55, rough: 0.5 },
      marbleFloor: { set: 'nero', tile: 1.2, albedo: 0x3f3b37, rough: 0.35, joints: [0.6, 0.6, 0.002, 0.8] },
      paint: { set: 'plaster', tile: 2.4, albedo: 0xe4dcd2, flat: 0.6, normal: 0.15, rough: 0.9 },
      ceiling: { set: 'plaster', tile: 3.2, albedo: 0xece6de, flat: 0.8, normal: 0.08, rough: 0.95 },
      travertineSlab: { set: 'nero', tile: 1.2, albedo: 0x3e3a36, rough: 0.45, env: 0.2 },
      oak: { set: 'smokedwalnut', tile: 1.4, albedo: 0x8a5d3d, rough: 0.45 },
      walnut: { set: 'smokedwalnut', tile: 1.2, albedo: 0x5c3f2e, rough: 0.42 },
      joinery: { set: 'smokedwalnut', tile: 1.2, albedo: 0x66463a, rough: 0.4 },
      marble: { set: 'marble', tile: 1.6, albedo: 0xc9bcc4, rough: 0.35, clearcoat: 0.8 },
      boucle: { set: 'velvet', tile: 0.7, albedo: 0x4a2740, flat: 0.65, rough: 0.85, normal: 0.2, sheen: 0x6e4a64 },
      velvet: { set: 'velvet', tile: 0.7, albedo: 0x6a4a3c, flat: 0.65, rough: 0.8, normal: 0.2, sheen: 0x8e6e5e },
      linen: { set: 'linen', tile: 0.22, albedo: 0xe4d9cc, normal: 0.35, sheen: 0xffffff },
      linenSand: { set: 'velvet', tile: 0.7, albedo: 0x7b6a5f, flat: 0.5, normal: 0.2, sheen: 0xa08e82 },
      linenGrey: { set: 'linen', tile: 0.5, albedo: 0x5f544d },
      rug: { set: 'rug', tile: 0.9, albedo: 0x6e6259 },
      bloom: { color: 0x7a2e5c },
      brass: { color: 0xa8884f, rough: 0.32, metal: 1 },
      lampShade: { color: 0xf3e3c9 },
      concrete: { set: 'plaster', tile: 1.5, albedo: 0x4a423c },
      weave: { set: 'rattan', tile: 0.35, albedo: 0xb48f62 },
      sheer: { color: 0xe9e0d4 },
    },
  },
};

const BASE = ['travertine', 'woodfloor', 'marble', 'plaster', 'oak', 'walnut', 'boucle', 'velvet', 'linen', 'rug', 'rattan'];

// A role's colour and roughness in material terms: the albedo divided by the set's mean (or a plain
// tint), and the mean roughness divided by the roughness map's own mean. Shared with materials.js so
// the defaults a page starts with agree with what the styler applies.
export function roleColor(o, set) {
  const c = new THREE.Color();
  if (o.albedo === undefined) return c.set(o.color ?? 0xffffff);
  const a = new THREE.Color(o.albedo), g = (set && SET_AVG[set]) || [1, 1, 1];
  return c.setRGB(a.r / g[0], a.g / g[1], a.b / g[2], THREE.LinearSRGBColorSpace);
}
export function roleRoughness(rough, set, hasMap) { return hasMap ? rough / ((set && SET_ROUGH[set]) || 1) : rough; }

export function createStyler({ M, T, base, anisotropy, onLoading, releaseUnused = false }) {
  const loader = new THREE.TextureLoader();
  const pending = new Map();
  const clones = new Map();
  // a set becomes visible in T only once all three maps have arrived, so a failed map never leaves a
  // truthy but incomplete entry; a rejected load is forgotten so the next click can retry it
  const loadSet = (name) => {
    if (T[name]) return Promise.resolve();
    if (!pending.has(name)) {
      const p = Promise.all(['c', 'n', 'r'].map((s) => loader.loadAsync(`${base}${name}_${s}.webp`).then((t) => {
        t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = anisotropy;
        if (s === 'c') t.colorSpace = THREE.SRGBColorSpace;
        return t;
      }))).then(([c, n, r]) => { T[name] = { c, n, r }; pending.delete(name); })
        .catch((e) => { pending.delete(name); throw e; });
      pending.set(name, p);
    }
    return pending.get(name);
  };
  const tex = (set, s, tile) => {
    const key = `${set}|${s}|${tile}`;
    if (!clones.has(key)) { const c = T[set][s].clone(); c.repeat.set(1 / tile, 1 / tile); clones.set(key, c); }
    return clones.get(key);
  };
  // style-only sets no style on screen references any more: the per-tile clones are what reached the
  // GPU, so they go too; the shared maps follow and are re-fetched (from the browser cache) on return
  const release = (keep) => {
    for (const name of Object.keys(T)) {
      if (BASE.includes(name) || keep.has(name)) continue;
      for (const [key, c] of clones) if (key.startsWith(`${name}|`)) { c.dispose(); clones.delete(key); }
      for (const s of ['c', 'n', 'r']) T[name][s].dispose();
      delete T[name];
    }
  };
  let current = null, req = 0, loading = 0;
  async function apply(key) {
    const st = STYLES[key];
    if (!st) return;
    const id = ++req; // the last click wins, whatever order the downloads finish in
    const missing = st.sets.filter((n) => !T[n]);
    if (missing.length) {
      if (loading++ === 0) onLoading(true);
      try { await Promise.all(missing.map(loadSet)); } finally { if (--loading === 0) onLoading(false); }
    }
    if (id !== req) return;
    // every texture resolved before any material changes, so a switch is all or nothing
    const maps = new Map();
    for (const [role, o] of Object.entries(st.roles)) {
      const m = M[role];
      if (!m || !o.set || !T[o.set] || !m.map) continue;
      maps.set(role, { c: tex(o.set, 'c', o.tile), n: m.normalMap && tex(o.set, 'n', o.tile), r: m.roughnessMap && tex(o.set, 'r', o.tile) });
    }
    for (const [role, o] of Object.entries(st.roles)) {
      const m = M[role];
      if (!m) continue;
      if (m.userData.env0 === undefined) m.userData.env0 = m.envMapIntensity;
      const swap = maps.get(role);
      if (swap) {
        m.map = swap.c;
        if (m.normalMap) m.normalMap = swap.n;
        if (m.roughnessMap) { m.roughnessMap = swap.r; m.aoMap = m.roughnessMap; }
        m.userData.set = o.set;
      }
      const set = m.userData.set;
      m.color.copy(roleColor(o, set));
      if (m.userData.u && m.userData.u.uFlat) { const a = new THREE.Color(o.albedo ?? o.color); m.userData.u.uFlat.value.set(a.r, a.g, a.b, o.albedo !== undefined ? o.flat || 0 : 0); }
      if (o.rough !== undefined) m.roughness = roleRoughness(o.rough, set, !!m.roughnessMap);
      if (o.metal !== undefined) m.metalness = o.metal;
      if (o.normal !== undefined && m.normalScale) m.normalScale.set(o.normal, o.normal);
      // the atmosphere scales envMapIntensity by the sky's intensity (envScale); the role sets the authored part
      m.userData.envK = o.env !== undefined ? o.env : m.userData.env0;
      m.envMapIntensity = m.userData.envK * (m.userData.envScale ?? 1);
      if (o.sheen !== undefined && m.sheenColor) m.sheenColor.set(o.sheen);
      if (o.clearcoat !== undefined && m.clearcoat !== undefined) m.clearcoat = Math.max(0.02, o.clearcoat);
      if (o.joints && m.userData.u && m.userData.u.uJoint) m.userData.u.uJoint.value.set(...o.joints);
      if (role === 'lampShade') m.emissive.set(o.color).lerp(new THREE.Color(0xffc98a), 0.55);
    }
    ['art1', 'art2', 'art3'].forEach((k, i) => {
      const old = M[k].map;
      M[k].map = artTexture([21, 42, 77][i], st.art.slice(i % 2, i % 2 + 4).concat(st.art[0]));
      if (old) old.dispose();
    });
    current = key;
    if (releaseUnused) release(new Set(Object.values(st.roles).map((o) => o.set).filter(Boolean)));
  }
  return { apply, get current() { return current; }, preload: (key) => Promise.all(STYLES[key].sets.map(loadSet)) };
}
export const BASE_SETS = BASE;
