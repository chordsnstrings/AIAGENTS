import * as THREE from 'three';
import * as P from './proctex.js';
import { beamMaterial } from './volumetric.js';
import { SET_AVG, roleColor, roleRoughness } from './styles.js';

// The base sets every material is built from (style-only sets load on first use). The seven in
// INTERIOR_SETS are seen only indoors, so the page can start on the exterior ones and stream
// the rest behind the first frame; the phone tier reads the same files from assets/tex/512/.
export const SETS = ['plaster', 'walnut', 'oak', 'woodfloor', 'patio', 'pavers', 'sidewalk', 'asphalt', 'sand',
  'gravel', 'bark', 'velvet', 'rug', 'boucle', 'linen', 'grass', 'marble', 'travertine'];
export const INTERIOR_SETS = ['travertine', 'woodfloor', 'oak', 'boucle', 'linen', 'velvet', 'rug'];

const prep = (t, s, anisotropy) => {
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.anisotropy = anisotropy;
  if (s === 'c') t.colorSpace = THREE.SRGBColorSpace;
  return t;
};

export async function loadSet(base, name, anisotropy, onEach = () => {}) {
  const loader = new THREE.TextureLoader();
  const set = {};
  await Promise.all(['c', 'n', 'r'].map(async (s) => {
    set[s] = prep(await loader.loadAsync(`${base}${name}_${s}.webp`), s, anisotropy);
    onEach();
  }));
  return set;
}

// A deferred set is three 1x1 textures with the channel's neutral value (mid grey, flat normal,
// full AO at half roughness), tagged so adoptSet can find every clone a material took from them.
// r187 allocates texture storage immutably, so a placeholder is never grown in place.
export function placeholderSet(name, anisotropy) {
  const px = { c: [128, 128, 128, 255], n: [128, 128, 255, 255], r: [255, 128, 0, 255] };
  const set = {};
  for (const s of ['c', 'n', 'r']) {
    const t = prep(new THREE.DataTexture(new Uint8Array(px[s]), 1, 1), s, anisotropy);
    t.userData.placeholder = name; t.userData.ch = s;
    t.needsUpdate = true;
    set[s] = t;
  }
  return set;
}

// load, then clone: a texture cloned before it has loaded renders black (pitfall 1)
export async function loadTextureSets(base, anisotropy, onProgress, { defer = [] } = {}) {
  const out = {};
  const names = SETS.filter((n) => !defer.includes(n));
  let done = 0;
  const total = names.length * 3;
  await Promise.all(names.map(async (name) => { out[name] = await loadSet(base, name, anisotropy, () => onProgress(++done / total)); }));
  for (const name of defer) out[name] = placeholderSet(name, anisotropy);
  return out;
}

// Replace every placeholder clone of `name` in the materials with a fresh clone of the real
// texture, keeping the repeat each material chose. Map presence does not change, so no
// program recompiles; the renderer picks the new texture up on the next frame.
export function adoptSet(M, name, set) {
  const fresh = new Map();
  const swap = (old) => {
    if (!old || old.userData.placeholder !== name) return old;
    if (!fresh.has(old)) {
      const t = set[old.userData.ch].clone();
      t.repeat.copy(old.repeat); t.anisotropy = old.anisotropy;
      fresh.set(old, t);
    }
    return fresh.get(old);
  };
  for (const m of Object.values(M)) {
    for (const slot of ['map', 'normalMap', 'roughnessMap', 'aoMap', 'emissiveMap']) if (m[slot]) m[slot] = swap(m[slot]);
  }
  for (const old of fresh.keys()) old.dispose();
}

export const shared = {
  time: { value: 0 },
  // baked irradiance volume (see gi.js); dims of 1 keep the lookup faded out until data arrives
  gi: { uGi0: { value: null }, uGi1: { value: null }, uGiA: { value: new THREE.Vector3() }, uGiB: { value: new THREE.Vector3() }, uGiDims: { value: new THREE.Vector3(1, 1, 1) } },
  // night lamp irradiance over the community ground, baked by community.js: the map (R8, sqrt
  // encoded), world xz -> uv as xy * scale + offset, and the lamps' colour times their level
  lampMap: { uLampMap: { value: null }, uLampXf: { value: new THREE.Vector4(0, 0, 0, 0) }, uLampCol: { value: new THREE.Vector3() } },
  noise: { value: null },
};

// Value noise for the macro feature as a 256 px tiling texture (fbm in R, one octave in G) rather
// than sixteen sin hashes per pixel: two fetches, and the mips fade the variation out at distance
// instead of aliasing. The lattice wraps every CELLS cells, so the texture repeats seamlessly.
function noiseTexture(size = 256, cells = 16) {
  const hash = (x, y, s) => { const v = Math.sin(x * 127.1 + y * 311.7 + s * 74.7) * 43758.5453; return v - Math.floor(v); };
  const sm = (t) => t * t * (3 - 2 * t);
  const noise = (x, y, per, s) => {
    const ix = Math.floor(x), iy = Math.floor(y), fx = sm(x - ix), fy = sm(y - iy);
    const h = (a, b) => hash(((a % per) + per) % per, ((b % per) + per) % per, s);
    const a = h(ix, iy) + (h(ix + 1, iy) - h(ix, iy)) * fx, b = h(ix, iy + 1) + (h(ix + 1, iy + 1) - h(ix, iy + 1)) * fx;
    return a + (b - a) * fy;
  };
  const data = new Uint8Array(size * size * 2);
  for (let j = 0; j < size; j++) for (let i = 0; i < size; i++) {
    const x = (i + 0.5) / size * cells, y = (j + 0.5) / size * cells, o = (j * size + i) * 2;
    data[o] = Math.round((noise(x, y, cells, 1) * 0.55 + noise(x * 2, y * 2, cells * 2, 2) * 0.3 + noise(x * 4, y * 4, cells * 4, 3) * 0.15) * 255);
    data[o + 1] = Math.round(noise(x, y, cells, 4) * 255);
  }
  const t = new THREE.DataTexture(data, size, size, THREE.RGFormat, THREE.UnsignedByteType);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.minFilter = THREE.LinearMipmapLinearFilter; t.magFilter = THREE.LinearFilter;
  t.generateMipmaps = true; t.anisotropy = 4;
  t.needsUpdate = true;
  return t;
}
const NOISE_CELLS = 16;

// Indoors the env map knows nothing about walls, so where the baked volume says a point is
// enclosed, its irradiance replaces the env diffuse, and the env reflections are dimmed by how
// much sky the probe sees and tinted by the room's own bounce colour (a glossy floor in a lamp-lit
// room reflects the room, not the zenith). Outdoors (alpha 0) and outside the volume the env map
// stays in charge. The occlusion reads the probe's open-sky fraction from the gradient texture's
// alpha; where the volume carries none (alpha 0) the irradiance ratio stands in.
const GI_FRAG = /* glsl */`
  {
    vec3 gN = inverseTransformDirection(normal, viewMatrix);
    vec3 gU = (vWPos + gN * 0.22) * uGiA + uGiB;
    vec3 gL = gU * uGiDims - 0.5;
    vec3 gE = min(gL, uGiDims - 1.0 - gL);
    float gF = clamp(min(min(gE.x, gE.y), gE.z) * 2.5, 0.0, 1.0);
    if (gF > 0.0) {
      vec4 g0 = texture(uGi0, gU);
      vec4 g1 = texture(uGi1, gU);
      const vec3 LUM = vec3(0.2126, 0.7152, 0.0722);
      // non-linear L1 reconstruction (Hazel, Geomerics): no negative lobe behind strong lights.
      // The stored ratio is irradiance-premultiplied (c1 = 0.5 * integral of L * w over c0), so a
      // delta light reaches |R1|/R0 = 1 at 0.5 * ratio, not the 0.433 of normalised radiance SH.
      vec3 gR = g1.xyz / max(dot(g0.rgb, LUM), 1e-5);
      float gRl = length(gR), gX = min(0.5 * gRl, 0.98);
      float gQ = max(0.5 + 0.5 * dot(gR / max(gRl, 1e-5), gN), 1e-6), gP = 1.0 + 2.0 * gX, gA = (1.0 - gX) / (1.0 + gX);
      vec3 gIrr = g0.rgb * (gA + (1.0 - gA) * (gP + 1.0) * pow(gQ, gP));
      float gw = g0.a * gF;
      float gLum = max(dot(gIrr, LUM), 1e-4);
      float gSo = g1.a > 0.0 ? clamp(g1.a * 2.5, 0.03, 1.0) : clamp(gLum / max(dot(iblIrradiance, LUM), 1e-4), 0.03, 1.0);
      vec3 gT = gIrr / gLum;
      iblIrradiance = mix(iblIrradiance, gIrr, gw);
      radiance = mix(radiance, dot(radiance, LUM) * gSo * gT, gw);
      #ifdef USE_CLEARCOAT
        clearcoatRadiance = mix(clearcoatRadiance, dot(clearcoatRadiance, LUM) * gSo * gT, gw);
      #endif
    }
  }`;

// The point-light loop with zero iterations. WebGLProgram substitutes the light counts textually
// after onBeforeCompile, so the count itself cannot be redefined; a loop bound of 0 unrolls to
// nothing while the uniform arrays stay declared, and a light count change recompiles nothing.
const NO_POINT = THREE.ShaderChunk.lights_fragment_begin.replace('i < NUM_POINT_LIGHTS;', 'i < 0;');

// One patcher for every shader tweak, keyed by feature set so materials that differ only in
// uniform values share a compiled program. Re-running it on a material (to add a feature) keeps
// the uniform objects it already has, so values set earlier survive.
// noPoint: exterior materials no interior point light reaches skip the per-light GGX lobes.
// lampMap: the ground takes the baked night lamp irradiance as direct diffuse light.
function enhance(mat, o) {
  const feats = Object.keys(o).filter((k) => o[k]).sort();
  const old = mat.userData.u || {}, U = {};
  if (o.joints) {
    U.uJoint = old.uJoint || { value: new THREE.Vector4(o.joints.size[0], o.joints.size[1], o.joints.width ?? 0.003, o.joints.shade ?? 0.55) };
  }
  if (o.macro) { U.uMacro = old.uMacro || { value: new THREE.Vector3(o.macro.scale ?? 0.02, o.macro.amount ?? 0.35, o.macro.hue ?? 0) }; U.uNoise = shared.noise; }
  if (o.sway) { U.uTime = shared.time; U.uSway = old.uSway || { value: o.sway }; }
  if (o.glass) U.uGlass = old.uGlass || { value: new THREE.Vector2(o.glass[0], o.glass[1]) };
  if (o.flat) U.uFlat = old.uFlat || { value: new THREE.Vector4(0.5, 0.5, 0.5, 0) };
  if (o.gi) Object.assign(U, shared.gi);
  if (o.lampMap) Object.assign(U, shared.lampMap);
  mat.userData.u = U;
  mat.userData.fx = o;
  mat.customProgramCacheKey = () => feats.join('|');
  mat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, U);
    const head = `varying vec2 vMeters;\nvarying vec3 vWPos;\n${o.joints ? 'uniform vec4 uJoint;' : ''}\n${o.macro ? 'uniform vec3 uMacro; uniform sampler2D uNoise;' : ''}\n${o.glass ? 'uniform vec2 uGlass;' : ''}\n${o.flat ? 'uniform vec4 uFlat;' : ''}\n${o.lampMap ? 'uniform sampler2D uLampMap; uniform vec4 uLampXf; uniform vec3 uLampCol;' : ''}\n`;
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', `#include <common>\n${head}\n${o.sway ? 'uniform float uTime; uniform float uSway;' : ''}`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>\n${o.sway ? `
        vec3 ip = vec3(0.0);
        #ifdef USE_INSTANCING
          ip = instanceMatrix[3].xyz;
        #endif
        float hh = length(transformed - vec3(0.0, 7.0, 0.0));
        float ph = uTime * 1.25 + ip.x * 0.37 + ip.z * 0.23;
        transformed.x += sin(ph) * uSway * hh * hh * 0.02;
        transformed.z += cos(ph * 0.83) * uSway * hh * hh * 0.015;
        transformed.y += sin(ph * 1.7) * uSway * hh * hh * 0.006;` : ''}`)
      .replace('#include <project_vertex>', `#include <project_vertex>
        vMeters = uv;
        vec4 wpx = vec4(transformed, 1.0);
        #ifdef USE_INSTANCING
          wpx = instanceMatrix * wpx;
        #endif
        vWPos = (modelMatrix * wpx).xyz;`);
    const giHead = o.gi ? 'uniform highp sampler3D uGi0;\nuniform highp sampler3D uGi1;\nuniform vec3 uGiA;\nuniform vec3 uGiB;\nuniform vec3 uGiDims;\n' : '';
    let f = sh.fragmentShader.replace('#include <common>', `#include <common>\n${head}${giHead}`);
    if (o.gi) f = f.replace('#include <lights_fragment_maps>', `#include <lights_fragment_maps>\n${GI_FRAG}`);
    // the lamp map stores sqrt(E / Emax) so its dark tail survives eight bits; the receiver is the
    // ground, whose cosine the bake already holds, so the irradiance lands as plain Lambert diffuse.
    // The map is a plan: it fades out above head height so a balcony over a lit car port stays dark.
    const lampLight = o.lampMap ? `
      {
        float lE = texture(uLampMap, vWPos.xz * uLampXf.xy + uLampXf.zw).r * (1.0 - smoothstep(1.0, 2.5, vWPos.y));
        reflectedLight.directDiffuse += lE * lE * uLampCol * BRDF_Lambert(material.diffuseContribution);
      }` : '';
    if (o.noPoint || o.lampMap) f = f.replace('#include <lights_fragment_begin>', `${o.noPoint ? NO_POINT : '#include <lights_fragment_begin>'}${lampLight}`);
    let post = '';
    // texture contrast: pull the texel towards the finish's mean albedo (painted walls read clean)
    if (o.flat) post += `\n      diffuseColor.rgb = mix(diffuseColor.rgb, uFlat.rgb, uFlat.a);`;
    if (o.macro) post += `
      float mv = texture(uNoise, vWPos.xz * (uMacro.x / ${NOISE_CELLS.toFixed(1)})).r;
      float mv2 = texture(uNoise, vWPos.xz * (uMacro.x * 7.3 / ${NOISE_CELLS.toFixed(1)})).g;
      diffuseColor.rgb *= mix(1.0 - uMacro.y, 1.0 + uMacro.y * 0.6, mv) * mix(0.92, 1.06, mv2);
      diffuseColor.rgb = mix(diffuseColor.rgb, diffuseColor.rgb * vec3(1.06, 1.0, 0.9), uMacro.z * mv);`;
    if (o.joints) post += `
      vec2 jg = abs(fract(vMeters / uJoint.xy + 0.5) - 0.5) * uJoint.xy;
      float jd = min(jg.x, jg.y);
      float jw = fwidth(jd) + 1e-4;
      float joint = 1.0 - smoothstep(uJoint.z * 0.5, uJoint.z * 0.5 + jw * 1.5, jd);
      diffuseColor.rgb *= mix(1.0, uJoint.w, joint);`;
    f = f.replace('#include <map_fragment>', `#include <map_fragment>\n${post}`);
    if (o.joints) f = f.replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>\n roughnessFactor = mix(roughnessFactor, 0.85, joint);`);
    // a lamp shade glows hotter at its lower rim and on the inside, where the bulb is; an opal
    // globe darkens towards its rim, so neither reads as a flat disc of light
    let glow = '';
    if (o.shade) glow += `\n      totalEmissiveRadiance *= mix(1.0, 0.55, clamp(vMeters.y, 0.0, 1.0)) * (gl_FrontFacing ? 1.0 : 1.6);`;
    if (o.opal) glow += `\n      totalEmissiveRadiance *= mix(0.5, 1.1, pow(abs(dot(normalize(normal), normalize(vViewPosition))), 0.7));`;
    if (glow) f = f.replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>${glow}`);
    if (o.glass) f = f.replace('#include <opaque_fragment>', `
      float gfr = pow(1.0 - clamp(abs(dot(normalize(normal), normalize(vViewPosition))), 0.0, 1.0), 4.0);
      float ga = mix(uGlass.x, uGlass.y, gfr);
      gl_FragColor = vec4(outgoingLight + diffuseColor.rgb * ga, ga);`);
    sh.fragmentShader = f;
  };
  return mat;
}

// Material.clone() copies neither the shader patch nor the uniform objects (userData survives only
// as JSON), so a clone of an enhanced material silently loses its features. This re-applies them.
export function cloneEnhanced(m) {
  const c = m.clone();
  c.userData = { ...m.userData, u: undefined };
  if (m.userData.fx) {
    enhance(c, m.userData.fx);
    for (const [k, u] of Object.entries(m.userData.u)) {
      // shared uniform objects (the GI volume, the lamp map, the noise, the clock) are the same
      // object on the clone already
      if (!c.userData.u[k] || c.userData.u[k] === u) continue;
      if (u.value && u.value.copy) c.userData.u[k].value.copy(u.value); else c.userData.u[k].value = u.value;
    }
  }
  return c;
}

export function createMaterials(T, { maxAniso = 8 } = {}) {
  const M = {};
  const glow = []; // { mat, day, dusk } emissive intensities driven by time of day
  if (!shared.noise.value) shared.noise.value = noiseTexture();

  const clone = (t, rx, ry) => { const c = t.clone(); c.repeat.set(rx, ry); c.anisotropy = maxAniso; return c; };
  // A finish from a packed set. albedo: names the colour it should read as (the set's mean is divided
  // out, as the styler does, and the GI bake reads the same number); color: is a plain tint for the
  // few scans whose own colour is wanted. rough: is the finish's mean roughness whatever the map's
  // own mean; flat: true gives a role the contrast control without using it. Keep one call per line with albedo/color before any nested option: bake-gi.mjs parses it.
  function pbr(name, o = {}) {
    const s = T[name];
    const tile = o.tile ?? 1, rx = 1 / tile, ry = 1 / (o.tileV ?? tile);
    const r = clone(s.r, rx, ry);
    const params = {
      map: clone(s.c, rx, ry), normalMap: clone(s.n, rx, ry), roughnessMap: r, aoMap: r,
      color: roleColor(o, name), roughness: roleRoughness(o.rough ?? 1, name, true), metalness: o.metal ?? 0,
      normalScale: new THREE.Vector2(o.normal ?? 1, o.normal ?? 1), envMapIntensity: o.env ?? 1, aoMapIntensity: o.ao ?? 1,
      side: o.side ?? THREE.FrontSide,
    };
    let m;
    if (o.physical) m = new THREE.MeshPhysicalMaterial({ ...params, ...o.physical });
    else m = new THREE.MeshStandardMaterial(params);
    if (o.joints || o.macro || o.flat || o.noPoint || o.lampMap) enhance(m, { joints: o.joints, macro: o.macro, flat: o.flat, noPoint: o.noPoint, lampMap: o.lampMap });
    if (o.flat) { const a = new THREE.Color(o.albedo); m.userData.u.uFlat.value.set(a.r, a.g, a.b, typeof o.flat === 'number' ? o.flat : 0); }
    m.name = name;
    m.userData.set = name;
    m.userData.env0 = m.envMapIntensity;
    return m;
  }
  const std = (o) => new THREE.MeshStandardMaterial(o);
  function emissive(color, day, dusk, extra = {}) {
    const m = new THREE.MeshStandardMaterial({ color: extra.base ?? 0x111111, emissive: new THREE.Color(color), emissiveIntensity: day, roughness: 0.6, ...extra.params });
    m.userData.noShadow = extra.noShadow ?? true;
    glow.push({ mat: m, day, dusk });
    return m;
  }

  // ---- architecture
  M.render = pbr('plaster', { tile: 3.2, albedo: 0xe6e1d7, normal: 0.45, rough: 1 });
  M.paint = pbr('plaster', { tile: 3.2, albedo: 0xe8e2d9, flat: 0.7, normal: 0.12, rough: 0.95, env: 0.25 });
  M.ceiling = pbr('plaster', { tile: 3.2, albedo: 0xf0ede8, flat: 0.8, normal: 0.08, rough: 1, env: 0.22 });
  M.stone = pbr('marble', { tile: 2.6, albedo: 0x6a6765, rough: 0.75, normal: 0.6, env: 0.7, joints: { size: [1.2, 0.6], width: 0.005, shade: 0.45 } });
  M.bronze = std({ color: 0x6f5238, metalness: 0.85, roughness: 0.38 });
  M.frame = std({ color: 0x1c1d1f, metalness: 0.6, roughness: 0.42 });
  // exterior glazing reflects a local probe of the street or the garden (atmosphere.js renders
  // them); front and rear panes are separate keys so each face mirrors what is really outside it
  // The panes are thin boxes, so one side suffices: with both, each pane drew twice (its far face
  // through its near one) and the Fresnel alpha below is the single-layer equivalent of that pair.
  const glass = (probe) => {
    const m = enhance(new THREE.MeshStandardMaterial({ color: 0x0b0d0e, roughness: 0.03, metalness: 0, transparent: true, premultipliedAlpha: true, depthWrite: false, side: THREE.FrontSide }), { glass: [0.12, 0.94] });
    m.userData.noShadow = true;
    m.userData.probe = probe;
    return m;
  };
  M.glass = glass('front');
  M.glassRear = glass('rear');
  M.frame.userData.probe = 'front';
  M.bronze.userData.probe = 'front';
  M.glassLight = enhance(new THREE.MeshStandardMaterial({ color: 0x0e1010, roughness: 0.02, metalness: 0, transparent: true, premultipliedAlpha: true, depthWrite: false, side: THREE.FrontSide }), { glass: [0.06, 0.75] });
  M.glassLight.userData.noShadow = true;
  M.wood = pbr('walnut', { tile: 1.6, albedo: 0x8a6a4e, rough: 0.75, normal: 0.6 });
  // ground and far-house finishes: no interior point light reaches them (noPoint), and the ones
  // the street lamps shine on take the baked lamp map
  M.pavers = pbr('pavers', { tile: 2.2, albedo: 0xb8ac99, rough: 1, noPoint: true, lampMap: true, macro: { scale: 0.05, amount: 0.12 } });
  M.sidewalk = pbr('sidewalk', { tile: 2.4, albedo: 0xbdb4a6, rough: 1, noPoint: true, lampMap: true, macro: { scale: 0.03, amount: 0.15 } });
  M.asphalt = pbr('asphalt', { tile: 5, albedo: 0x4a4845, rough: 1, normal: 0.6, noPoint: true, lampMap: true, macro: { scale: 0.012, amount: 0.25 } });
  M.curb = pbr('plaster', { tile: 2, albedo: 0xcfcac2, normal: 0.6, rough: 1, noPoint: true, lampMap: true });
  M.grass = pbr('grass', { tile: 2.6, albedo: 0x4a7030, rough: 1, normal: 0.8, noPoint: true, lampMap: true, macro: { scale: 0.08, amount: 0.22, hue: 0.4 } });
  // the sand scan's AO channel is weave-scale occlusion that means nothing at 7-34 m tiling
  M.sand = pbr('sand', { tile: 9, albedo: 0xd8c3a2, rough: 1, normal: 0.9, ao: 0, noPoint: true, macro: { scale: 0.012, amount: 0.2, hue: 0.5 } });
  M.base = pbr('sand', { tile: 7, albedo: 0xd8c3a2, rough: 1, normal: 0.7, ao: 0, noPoint: true, lampMap: true, macro: { scale: 0.02, amount: 0.18, hue: 0.4 } });
  M.base.polygonOffset = true; M.base.polygonOffsetFactor = -1; M.base.polygonOffsetUnits = -2;
  M.desert = pbr('sand', { tile: 34, albedo: 0xcaa982, rough: 1, normal: 1.2, ao: 0, noPoint: true, macro: { scale: 0.004, amount: 0.22, hue: 0.7 } });
  M.gravel = pbr('gravel', { tile: 1.4, albedo: 0xbdb6a9, rough: 1, noPoint: true });
  M.soil = pbr('gravel', { tile: 1.2, albedo: 0x4a3a2a, rough: 1, noPoint: true });
  // the terrace floor keeps the fire's point light; the lamp map lights the car ports and patios
  M.patio = pbr('patio', { tile: 2.4, albedo: 0xc9c3b8, rough: 0.9, normal: 0.6, lampMap: true });
  M.bark = pbr('bark', { tile: 1, tileV: 1.4, albedo: 0x6b5a46, rough: 1, noPoint: true });
  // rooftop plant: split-unit condensers and tanks in light grey, read from the air and the roof
  M.equipment = enhance(std({ color: 0xb4b7b6, roughness: 0.55, metalness: 0.15 }), { noPoint: true });
  // interior roles: the Warm Minimal values, so the first frame and the bake agree with the styler
  M.travertine = pbr('travertine', { tile: 1.8, albedo: 0xd8c8af, rough: 0.55, env: 0.3, joints: { size: [1.2, 0.6], width: 0.003, shade: 0.72 } });
  M.travertineSlab = pbr('travertine', { tile: 1.4, albedo: 0xd8c8af, rough: 0.6, env: 0.3 });
  M.oakFloor = pbr('woodfloor', { tile: 2.2, albedo: 0xc8a684, rough: 0.75, env: 0.25 });
  M.oak = pbr('oak', { tile: 1.4, albedo: 0xc9a882, rough: 0.7, env: 0.3 });
  M.joinery = pbr('walnut', { tile: 1.2, albedo: 0x5a4030, rough: 0.5, env: 0.3 }); // doors, wardrobes, kitchen runs
  M.walnut = pbr('walnut', { tile: 1.2, albedo: 0x5a4030, rough: 0.55, env: 0.3 });
  M.marble = pbr('marble', { tile: 1.8, albedo: 0xe6e3dd, rough: 0.5, env: 0.45, physical: { clearcoat: 0.6, clearcoatRoughness: 0.08 } });
  M.marbleFloor = pbr('marble', { tile: 1.6, albedo: 0xe6e3dd, rough: 0.6, env: 0.35, joints: { size: [0.6, 0.6], width: 0.002, shade: 0.7 } });
  // fabrics: the AO in these scans is at weave scale, so it is kept faint; flat lets a style pull a
  // crushed velvet scan towards its colour so the sheen, not the noise, carries the velvet read
  M.boucle = pbr('boucle', { tile: 0.45, albedo: 0xe3d9ca, rough: 1, normal: 1.4, env: 0.25, ao: 0.3, flat: true, physical: { sheen: 0.6, sheenRoughness: 0.75, sheenColor: new THREE.Color(0xffffff) } });
  M.linen = pbr('linen', { tile: 0.22, albedo: 0xe9e4db, rough: 1, normal: 0.35, env: 0.25, ao: 0.3, physical: { sheen: 0.4, sheenRoughness: 0.8, sheenColor: new THREE.Color(0xffffff) } });
  M.linenSand = pbr('linen', { tile: 0.3, albedo: 0xd8ccb8, rough: 1, normal: 0.5, env: 0.25, ao: 0.3, flat: true, physical: { sheen: 0.4, sheenRoughness: 0.8, sheenColor: new THREE.Color(0xfff4e6) } });
  M.linenGrey = pbr('linen', { tile: 0.5, albedo: 0xbcb6ad, rough: 1, normal: 0.9, env: 0.5, ao: 0.3 });
  M.velvet = pbr('velvet', { tile: 0.7, albedo: 0xa892c4, rough: 0.9, normal: 0.2, env: 0.25, ao: 0.3, flat: 0.5, physical: { sheen: 1, sheenRoughness: 0.3, sheenColor: new THREE.Color(0xc9b8de) } });
  M.rug = pbr('rug', { tile: 0.9, albedo: 0xd9cebd, rough: 1, normal: 1.1, env: 0.2 });
  M.weave = pbr('linen', { tile: 0.3, albedo: 0xb8946a, rough: 0.9, normal: 1.2, env: 0.3, side: THREE.DoubleSide });
  // the pleated panel is the one DoubleSide material worth a single pass; it writes depth so the
  // glazing behind a drawn curtain is rejected rather than composited (the hero's renderOrder keeps
  // sheer under glass), at the price of the curtain showing in the depth AO and the march read
  // a voile in direct sun must not clip: lighter weave colour than white and a little more open
  M.sheer = new THREE.MeshStandardMaterial({ map: clone(T.linen.c, 2, 2), color: 0xe9e5df, roughness: 1, transparent: true, opacity: 0.6, side: THREE.DoubleSide, envMapIntensity: 0.4, depthWrite: true, forceSinglePass: true });
  M.sheer.userData.noShadow = true;
  // backlit translucency: a hint of the daylight behind it by day, barely anything at night; the
  // panel takes the room's baked light like everything else, so a shaded window does not glow
  M.sheer.emissive.set(0xfff4e8);
  glow.push({ mat: M.sheer, day: 0.05, dusk: 0.012 });
  enhance(M.sheer, { gi: true });

  M.blackSatin = std({ color: 0x141414, roughness: 0.35, metalness: 0.2, envMapIntensity: 0.6 });
  M.tv = std({ color: 0x050505, roughness: 0.12, metalness: 0.1, envMapIntensity: 0.9 });
  M.brass = std({ color: 0xc8a467, roughness: 0.28, metalness: 1, envMapIntensity: 0.8 });
  M.chrome = std({ color: 0xdedede, roughness: 0.08, metalness: 1 });
  // cut flowers: two bloom tones (the first follows the style) and a shared green
  M.bloom = new THREE.MeshPhysicalMaterial({ color: 0xc3b1de, roughness: 0.65, sheen: 0.6, sheenRoughness: 0.5, sheenColor: new THREE.Color(0xffffff) });
  M.bloomB = new THREE.MeshPhysicalMaterial({ color: 0xf3eee6, roughness: 0.65, sheen: 0.5, sheenRoughness: 0.5, sheenColor: new THREE.Color(0xffffff) });
  M.stem = std({ color: 0x4d6a3a, roughness: 0.6 });
  M.ceramic = new THREE.MeshPhysicalMaterial({ color: 0xe0ddd7, roughness: 0.25, clearcoat: 1, clearcoatRoughness: 0.05, envMapIntensity: 0.6 });
  M.mirror = std({ color: 0xe6e6e6, roughness: 0.02, metalness: 1, envMapIntensity: 0.9 });
  M.concrete = pbr('plaster', { tile: 1.5, albedo: 0x9a948c, normal: 0.7, rough: 1 });
  M.charcoal = std({ color: 0x2a2826, roughness: 0.8 });

  // ---- light emitters (intensity follows time of day)
  // the shade is linen over the bulb: its weave modulates the glow (the map's mean of 0.41 is folded
  // into the intensities), the shader adds the rim-to-top gradient and the hotter inside
  const shadeMap = clone(T.linen.c, 5, 1);
  M.lampShade = emissive(0xffd7a3, 0.07, 1.5, { base: 0xf1e7d6, params: { side: THREE.DoubleSide, roughness: 1, map: shadeMap, emissiveMap: shadeMap } });
  M.lampShade.color.copy(roleColor({ albedo: 0xf1e7d6 }, 'linen'));
  M.lampShade.userData.set = 'linen';
  enhance(M.lampShade, { shade: true });
  M.bulb = enhance(emissive(0xffcf8f, 1.5, 4.5, {}), { opal: true });
  M.downlight = emissive(0xfff0dc, 1.2, 6, {});
  M.led = emissive(0xffd29c, 0.6, 5, {});
  M.fire = emissive(0xff8a3a, 0, 6, {});
  M.lampHead = emissive(0xffd9a6, 0.0, 9, { base: 0x2a2622 });
  M.roomLit = emissive(0xffdfb4, 0.08, 1.15, { base: 0x15110d, params: { map: P.roomTexture(), emissiveMap: P.roomTexture(), roughness: 0.9 } });
  // an unlit neighbour's room: a dim interior with curtain folds rather than a black hole
  M.roomDim = std({ color: 0xf0f0f0, roughness: 0.9, map: P.roomDimTexture() });

  // ---- vegetation (alpha-tested cards)
  const leafMat = (tex, color = 0xffffff) => {
    const m = new THREE.MeshStandardMaterial({ map: tex, color, alphaTest: 0.45, side: THREE.DoubleSide, roughness: 0.85, envMapIntensity: 0.7 });
    m.shadowSide = THREE.DoubleSide;
    return m;
  };
  M.leaf = leafMat(P.foliageTexture({ seed: 3 }));
  M.leafOlive = leafMat(P.foliageTexture({ seed: 5, leaf: ['#7f8c6c', '#98a585', '#6b7a5c', '#aab69a'], narrow: true }));
  M.flower = leafMat(P.foliageTexture({ seed: 9, leaf: ['#3f5f2c', '#4f6e36'], flower: ['#8e3c96', '#a24aa4', '#6f3c8c', '#b45bb0', '#7a4ba0'], flowerRatio: 0.75 }));
  M.flowerPink = leafMat(P.foliageTexture({ seed: 13, leaf: ['#3f5f2c', '#4f6e36'], flower: ['#c2457f', '#d0589a', '#a83a78'], flowerRatio: 0.7 }));
  M.frond = enhance(leafMat(P.frondTexture()), { sway: 0.55, noPoint: true });
  M.bark2 = M.bark;

  // ---- detail cards and decor
  const lattice = P.latticeTexture();
  lattice.repeat.set(2.2, 2.2);
  M.lattice = new THREE.MeshStandardMaterial({ color: 0x6f5238, metalness: 0.85, roughness: 0.4, alphaMap: lattice, alphaTest: 0.5, side: THREE.DoubleSide });
  const rail = P.railTexture();
  M.rail = new THREE.MeshStandardMaterial({ color: 0x6f5238, metalness: 0.8, roughness: 0.45, alphaMap: rail, alphaTest: 0.5, side: THREE.DoubleSide });
  M.art1 = std({ map: P.artTexture(21, ['#efe8dc', '#cdb89a', '#8d6fae', '#e6d8c3', '#b9a3d0']), roughness: 0.9, envMapIntensity: 0.3 });
  M.art2 = std({ map: P.artTexture(42, ['#ece4d6', '#3d3a40', '#c9a77f', '#d9cbb8']), roughness: 0.9, envMapIntensity: 0.3 });
  M.art3 = std({ map: P.artTexture(77, ['#e9e1d6', '#7d5f9c', '#d2c2ad', '#a58bc4']), roughness: 0.9, envMapIntensity: 0.3 });
  const atlas = P.facadeAtlas();
  M.lod = enhance(new THREE.MeshStandardMaterial({ map: atlas.map, emissiveMap: atlas.emissive, emissive: 0xffd9a6, emissiveIntensity: 0, roughness: 0.9 }), { noPoint: true });
  glow.push({ mat: M.lod, day: 0, dusk: 1.1 });
  M.lodRoof = enhance(std({ color: 0xe9e4dc, roughness: 1 }), { noPoint: true });
  const wn = P.waterNormals();
  wn.repeat.set(1 / 9, 1 / 9);
  M.water = new THREE.MeshStandardMaterial({ color: 0x154e58, roughness: 0.04, metalness: 0.0, normalMap: wn, normalScale: new THREE.Vector2(0.3, 0.3), envMapIntensity: 1.7 });
  M.water.userData.noShadow = true;
  M.poolWater = new THREE.MeshStandardMaterial({ color: 0x3fb7c4, roughness: 0.05, normalMap: wn, normalScale: new THREE.Vector2(0.25, 0.25), envMapIntensity: 1.2 });


  M.beam = beamMaterial(0xffcf96);
  M.beam.userData.noShadow = true;
  glow.push({ mat: M.beam, day: 0, dusk: 0.16, prop: 'uOpacity' });
  for (const [k, m] of Object.entries(M)) {
    if (m.isMeshStandardMaterial && !m.transparent && k !== 'water' && k !== 'poolWater') enhance(m, { ...(m.userData.fx || {}), gi: true });
  }
  return { M, glow, water: wn };
}
