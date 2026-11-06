import * as THREE from 'three';
import { artTexture } from './proctex.js';

// Four researched interior presets (Dezeen 2026, 1stDibs 2026 survey, Khaleej Times on Dubai
// "restrained luxury", Bayut UAE trends, Domus Academy, paint colours of the year). A preset
// re-parameterises the shared material roles and shows its own furniture set; material types
// and feature flags never change, so switching never recompiles a shader.

export const STYLES = {
  minimal: {
    name: 'Warm Minimal', short: 'Minimal',
    blurb: 'Honed travertine, pale oak and ivory bouclé, with lavender as the only colour.',
    palette: ['#EEE8DF', '#F0EEE9', '#D8C8AF', '#C9A97F', '#E3D9CA', '#B7A3CF'],
    sets: [], art: ['#efe8dc', '#cdb89a', '#9d86c0', '#e6d8c3', '#c9b8de'], inside: 1.0,
    roles: {
      travertine: { set: 'travertine', tile: 1.8, color: 0xf3ebde, rough: 0.55, joints: [1.2, 0.6, 0.003, 0.72] },
      oakFloor: { set: 'woodfloor', tile: 2.2, color: 0xffe9cc, rough: 0.75 },
      marbleFloor: { set: 'marble', tile: 1.6, color: 0xf2f0ec, rough: 0.6, joints: [0.6, 0.6, 0.002, 0.7] },
      paint: { set: 'plaster', tile: 3.2, color: 0xf0ebe3, normal: 0.12, rough: 0.95, env: 0.25 },
      ceiling: { set: 'plaster', tile: 3.2, color: 0xf5f2ec, normal: 0.08, rough: 1, env: 0.22 },
      travertineSlab: { set: 'travertine', tile: 1.4, color: 0xf0e6d6, rough: 0.6 },
      oak: { set: 'oak', tile: 1.4, color: 0xf6e3c8, rough: 0.7 },
      walnut: { set: 'walnut', tile: 1.2, color: 0x8d715e, rough: 0.55 },
      marble: { set: 'marble', tile: 1.8, color: 0xffffff, rough: 0.5, clearcoat: 0.6 },
      boucle: { set: 'boucle', tile: 0.45, color: 0xefe8dc, normal: 1.4, sheen: 0xffffff },
      velvet: { set: 'velvet', tile: 0.7, color: 0x9d86c0, sheen: 0xd9c7f0 },
      linen: { set: 'linen', tile: 0.5, color: 0xf6f3ee, sheen: 0xffffff },
      linenSand: { set: 'linen', tile: 0.5, color: 0xd9c8ae, sheen: 0xfff4e6 },
      linenGrey: { set: 'linen', tile: 0.5, color: 0xb9b4ac },
      rug: { set: 'rug', tile: 0.9, color: 0xe8dfd2 },
      brass: { color: 0xc8a467, rough: 0.28, metal: 1 },
      lampShade: { color: 0xf1e7d6 },
      concrete: { set: 'plaster', tile: 1.5, color: 0xb7b1a8 },
      weave: { set: 'rattan', tile: 0.35, color: 0xffffff },
      sheer: { color: 0xfbf8f2 },
    },
  },
  japandi: {
    name: 'Japandi Calm', short: 'Japandi',
    blurb: 'Oiled oak, oat limewash, black-stained ash and paper light, with a muted heather accent.',
    palette: ['#D9D0C3', '#EAE5DC', '#B3946D', '#3D3833', '#A69D90', '#85788F'],
    sets: ['ash', 'limewash', 'microcement', 'papercord'], art: ['#e9e4da', '#2f2c29', '#a99c8a', '#cfc6b6', '#85788f'], inside: 1.05,
    roles: {
      travertine: { set: 'woodfloor', tile: 2.2, color: 0xe6c49a, rough: 0.7, joints: [1, 1, 0, 1] },
      oakFloor: { set: 'woodfloor', tile: 2.2, color: 0xe6c49a, rough: 0.7 },
      marbleFloor: { set: 'microcement', tile: 2.0, color: 0xd6cdbf, rough: 0.75, joints: [1, 1, 0, 1] },
      paint: { set: 'limewash', tile: 2.4, color: 0xe6dccd, normal: 0.3, rough: 0.97, env: 0.22 },
      ceiling: { set: 'limewash', tile: 3.0, color: 0xefeae2, normal: 0.2, rough: 1, env: 0.2 },
      travertineSlab: { set: 'microcement', tile: 1.5, color: 0xcfc6b8, rough: 0.8 },
      oak: { set: 'ash', tile: 1.4, color: 0xf0d6b0, rough: 0.65 },
      walnut: { set: 'ash', tile: 1.2, color: 0x4a443e, rough: 0.6 },
      marble: { set: 'microcement', tile: 1.6, color: 0xcbc1b2, rough: 0.6, clearcoat: 0.05 },
      boucle: { set: 'linen', tile: 0.5, color: 0xb5ab9d, normal: 0.9, sheen: 0xe8e0d4 },
      velvet: { set: 'boucle', tile: 0.45, color: 0x8b7e96, normal: 1.2, sheen: 0xc7b9d6 },
      linen: { set: 'linen', tile: 0.5, color: 0xefe9df, sheen: 0xffffff },
      linenSand: { set: 'linen', tile: 0.5, color: 0xbdb2a2, sheen: 0xeee4d6 },
      linenGrey: { set: 'linen', tile: 0.5, color: 0x8f877d },
      rug: { set: 'rug', tile: 0.9, color: 0xc4b8a8 },
      brass: { color: 0x2c2a27, rough: 0.5, metal: 0.7 },
      lampShade: { color: 0xf7f2e8 },
      concrete: { set: 'plaster', tile: 1.5, color: 0x4f4a45 },
      weave: { set: 'papercord', tile: 0.22, color: 0xd9c19a },
      sheer: { color: 0xf2ede4 },
    },
  },
  desert: {
    name: 'Desert Organic', short: 'Desert',
    blurb: 'Sun-baked curves in lime plaster, terracotta, rattan and caramel elm, with dusty mauve.',
    palette: ['#E4D2BB', '#F3ECE1', '#B5704F', '#8F6440', '#D6C3A5', '#A77B8C'],
    sets: ['terracotta', 'clayplaster', 'limewash', 'rattan'], art: ['#efe2cf', '#b5704f', '#d6c3a5', '#a77b8c', '#8f6440'], inside: 1.0,
    roles: {
      travertine: { set: 'terracotta', tile: 1.2, color: 0xffd9c0, rough: 0.85, joints: [1, 1, 0, 1] },
      oakFloor: { set: 'woodfloor', tile: 2.2, color: 0xe2ad80, rough: 0.72 },
      marbleFloor: { set: 'terracotta', tile: 0.9, color: 0xffd9c0, rough: 0.8, joints: [1, 1, 0, 1] },
      paint: { set: 'clayplaster', tile: 2.2, color: 0xf1dcc2, normal: 0.3, rough: 0.97, env: 0.22 },
      ceiling: { set: 'limewash', tile: 3.0, color: 0xf6efe4, normal: 0.25, rough: 1, env: 0.2 },
      travertineSlab: { set: 'travertine', tile: 1.4, color: 0xf6ede0, rough: 0.65 },
      oak: { set: 'oak', tile: 1.4, color: 0xf2dcc0, rough: 0.7 },
      walnut: { set: 'oak', tile: 1.2, color: 0xb98256, rough: 0.6 },
      marble: { set: 'travertine', tile: 1.6, color: 0xf3e9da, rough: 0.5, clearcoat: 0.1 },
      boucle: { set: 'linen', tile: 0.5, color: 0xdcc9ab, normal: 1.0, sheen: 0xfff1dc },
      velvet: { set: 'velvet', tile: 0.7, color: 0xac7f91, sheen: 0xe2bccb },
      linen: { set: 'linen', tile: 0.5, color: 0xf6f0e6, sheen: 0xffffff },
      linenSand: { set: 'linen', tile: 0.5, color: 0xd6c3a5, sheen: 0xfff1dc },
      linenGrey: { set: 'linen', tile: 0.5, color: 0xc4ae92 },
      rug: { set: 'rug', tile: 0.9, color: 0xeadbc5 },
      brass: { color: 0xb08d57, rough: 0.4, metal: 1 },
      lampShade: { color: 0xf0e2cd },
      concrete: { set: 'clayplaster', tile: 1.2, color: 0xc77a55 },
      weave: { set: 'rattan', tile: 0.35, color: 0xffffff },
      sheer: { color: 0xf7efe3 },
    },
  },
  luxe: {
    name: 'Aubergine Luxe', short: 'Luxe',
    blurb: 'Walnut, dark marble, mocha Venetian plaster and aubergine velvet, with antique brass.',
    palette: ['#7B6A5F', '#DCD2C6', '#3B3534', '#5C3F2E', '#4A2740', '#A8884F'],
    sets: ['nero', 'herringbone', 'smokedwalnut'], art: ['#d8cbbd', '#4a2740', '#a8884f', '#7b6a5f', '#2b2523'], inside: 1.3,
    roles: {
      travertine: { set: 'nero', tile: 2.4, color: 0xe4d2c2, rough: 0.42, joints: [1.2, 1.2, 0.003, 0.75] },
      oakFloor: { set: 'herringbone', tile: 1.6, color: 0x9c7d66, rough: 0.5 },
      marbleFloor: { set: 'nero', tile: 1.2, color: 0xe8d6c6, rough: 0.35, joints: [0.6, 0.6, 0.002, 0.8] },
      paint: { set: 'plaster', tile: 2.4, color: 0x8f7a6c, normal: 0.25, rough: 0.5, env: 0.4 },
      ceiling: { set: 'plaster', tile: 3.2, color: 0xe2d8cc, normal: 0.08, rough: 0.95, env: 0.22 },
      travertineSlab: { set: 'nero', tile: 1.2, color: 0xe6d3c3, rough: 0.45, env: 0.35 },
      oak: { set: 'smokedwalnut', tile: 1.4, color: 0xa88468, rough: 0.45 },
      walnut: { set: 'smokedwalnut', tile: 1.2, color: 0x7a5a45, rough: 0.42 },
      marble: { set: 'marble', tile: 1.6, color: 0xf2e0ee, rough: 0.35, clearcoat: 0.8 },
      boucle: { set: 'velvet', tile: 0.7, color: 0x3d1b35, rough: 0.85, normal: 0.6, sheen: 0x5e3a55 },
      velvet: { set: 'velvet', tile: 0.7, color: 0x5a3a2a, rough: 0.8, normal: 0.6, sheen: 0x8a6650 },
      linen: { set: 'linen', tile: 0.5, color: 0xe8ddcf, sheen: 0xffffff },
      linenSand: { set: 'velvet', tile: 0.7, color: 0x7c5c4a, normal: 0.6, sheen: 0xa98470 },
      linenGrey: { set: 'linen', tile: 0.5, color: 0x5f524b },
      rug: { set: 'rug', tile: 0.9, color: 0x6a5f58 },
      brass: { color: 0xa8884f, rough: 0.32, metal: 1 },
      lampShade: { color: 0xf3e3c9 },
      concrete: { set: 'plaster', tile: 1.5, color: 0x47403a },
      weave: { set: 'rattan', tile: 0.35, color: 0xffffff },
      sheer: { color: 0xe9e0d4 },
    },
  },
};

const BASE = ['travertine', 'woodfloor', 'marble', 'plaster', 'oak', 'walnut', 'boucle', 'velvet', 'linen', 'rug', 'rattan'];

export function createStyler({ M, T, base, anisotropy, onLoading }) {
  const loader = new THREE.TextureLoader();
  const pending = new Map();
  const clones = new Map();
  const loadSet = (name) => {
    if (T[name]) return Promise.resolve();
    if (!pending.has(name)) {
      pending.set(name, Promise.all(['c', 'n', 'r'].map((s) => loader.loadAsync(`${base}${name}_${s}.webp`).then((t) => {
        t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = anisotropy;
        if (s === 'c') t.colorSpace = THREE.SRGBColorSpace;
        (T[name] ||= {})[s] = t;
      }))));
    }
    return pending.get(name);
  };
  const tex = (set, s, tile) => {
    const key = `${set}|${s}|${tile}`;
    if (!clones.has(key)) { const c = T[set][s].clone(); c.repeat.set(1 / tile, 1 / tile); clones.set(key, c); }
    return clones.get(key);
  };
  let current = null;
  async function apply(key) {
    const st = STYLES[key];
    if (!st) return;
    const missing = st.sets.filter((n) => !T[n]);
    if (missing.length) { onLoading(true); await Promise.all(missing.map(loadSet)); onLoading(false); }
    for (const [role, o] of Object.entries(st.roles)) {
      const m = M[role];
      if (!m) continue;
      if (m.userData.env0 === undefined) m.userData.env0 = m.envMapIntensity;
      if (o.set && T[o.set] && m.map) {
        m.map = tex(o.set, 'c', o.tile);
        if (m.normalMap) m.normalMap = tex(o.set, 'n', o.tile);
        if (m.roughnessMap) { m.roughnessMap = tex(o.set, 'r', o.tile); m.aoMap = m.roughnessMap; }
      }
      m.color.set(o.color);
      if (o.rough !== undefined) m.roughness = o.rough;
      if (o.metal !== undefined) m.metalness = o.metal;
      if (o.normal !== undefined && m.normalScale) m.normalScale.set(o.normal, o.normal);
      if (o.env !== undefined) m.envMapIntensity = o.env;
      else if (m.userData.env0 !== undefined) m.envMapIntensity = m.userData.env0;
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
  }
  return { apply, get current() { return current; }, preload: (key) => Promise.all(STYLES[key].sets.map(loadSet)) };
}
export const BASE_SETS = BASE;
