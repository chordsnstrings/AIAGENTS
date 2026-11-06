import * as THREE from 'three';
import * as P from './proctex.js';
import { beamMaterial } from './volumetric.js';

const SETS = ['plaster', 'stone', 'walnut', 'oak', 'woodfloor', 'patio', 'pavers', 'sidewalk', 'asphalt', 'sand',
  'gravel', 'bark', 'velvet', 'rug', 'boucle', 'linen', 'grass', 'marble', 'travertine'];

export async function loadTextureSets(base, anisotropy, onProgress) {
  const loader = new THREE.TextureLoader();
  const out = {};
  let done = 0;
  const total = SETS.length * 3;
  await Promise.all(SETS.flatMap((name) => ['c', 'n', 'r'].map(async (s) => {
    const t = await loader.loadAsync(`${base}${name}_${s}.webp`);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.anisotropy = anisotropy;
    if (s === 'c') t.colorSpace = THREE.SRGBColorSpace;
    (out[name] ||= {})[s] = t;
    onProgress(++done / total);
  })));
  return out;
}

export const shared = {
  time: { value: 0 },
  // baked irradiance volume (see gi.js); dims of 1 keep the lookup faded out until data arrives
  gi: { uGi0: { value: null }, uGi1: { value: null }, uGiA: { value: new THREE.Vector3() }, uGiB: { value: new THREE.Vector3() }, uGiDims: { value: new THREE.Vector3(1, 1, 1) } },
};

// Indoors the env map knows nothing about walls, so where the baked volume says a point is
// enclosed, its irradiance replaces the env diffuse and the env reflections are scaled by the
// same occlusion. Outdoors (alpha 0) and outside the volume the env map stays in charge.
const GI_FRAG = /* glsl */`
  {
    vec3 gN = inverseTransformDirection(normal, viewMatrix);
    vec3 gU = (vWPos + gN * 0.22) * uGiA + uGiB;
    vec3 gL = gU * uGiDims - 0.5;
    vec3 gE = min(gL, uGiDims - 1.0 - gL);
    float gF = clamp(min(min(gE.x, gE.y), gE.z) * 2.5, 0.0, 1.0);
    if (gF > 0.0) {
      vec4 g0 = texture(uGi0, gU);
      vec3 g1 = texture(uGi1, gU).xyz;
      const vec3 LUM = vec3(0.2126, 0.7152, 0.0722);
      // non-linear L1 reconstruction (Hazel, Geomerics): no negative lobe behind strong lights
      vec3 gR = g1 / max(dot(g0.rgb, LUM), 1e-5);
      float gRl = length(gR), gX = min(0.433 * gRl, 0.95);
      float gQ = max(0.5 + 0.5 * dot(gR / max(gRl, 1e-5), gN), 1e-6), gP = 1.0 + 2.0 * gX, gA = (1.0 - gX) / (1.0 + gX);
      vec3 gIrr = g0.rgb * (gA + (1.0 - gA) * (gP + 1.0) * pow(gQ, gP));
      float gw = g0.a * gF;
      float gSo = clamp(dot(gIrr, LUM) / max(dot(iblIrradiance, LUM), 1e-4), 0.03, 1.0);
      iblIrradiance = mix(iblIrradiance, gIrr, gw);
      radiance *= mix(1.0, gSo, gw);
      #ifdef USE_CLEARCOAT
        clearcoatRadiance *= mix(1.0, gSo, gw);
      #endif
    }
  }`;

const NOISE = /* glsl */`
float vHash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vNoise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
  return mix(mix(vHash(i), vHash(i+vec2(1,0)), f.x), mix(vHash(i+vec2(0,1)), vHash(i+vec2(1,1)), f.x), f.y); }
float vFbm(vec2 p){ return vNoise(p)*0.55 + vNoise(p*2.13)*0.3 + vNoise(p*4.7)*0.15; }
`;

// One patcher for every shader tweak, keyed by feature set so materials that differ only in
// uniform values share a compiled program.
function enhance(mat, o) {
  const feats = Object.keys(o).filter((k) => o[k]).sort();
  const U = {};
  if (o.joints) {
    U.uJoint = { value: new THREE.Vector4(o.joints.size[0], o.joints.size[1], o.joints.width ?? 0.003, o.joints.shade ?? 0.55) };
  }
  if (o.macro) U.uMacro = { value: new THREE.Vector3(o.macro.scale ?? 0.02, o.macro.amount ?? 0.35, o.macro.hue ?? 0) };
  if (o.sway) { U.uTime = shared.time; U.uSway = { value: o.sway }; }
  if (o.glass) U.uGlass = { value: new THREE.Vector2(o.glass[0], o.glass[1]) };
  if (o.flat) U.uFlat = { value: new THREE.Vector4(0.5, 0.5, 0.5, 0) };
  if (o.gi) Object.assign(U, shared.gi);
  mat.userData.u = U;
  mat.userData.fx = o;
  mat.customProgramCacheKey = () => feats.join('|');
  mat.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, U);
    const head = `varying vec2 vMeters;\nvarying vec3 vWPos;\n${o.joints ? 'uniform vec4 uJoint;' : ''}\n${o.macro ? 'uniform vec3 uMacro;' + NOISE : ''}\n${o.glass ? 'uniform vec2 uGlass;' : ''}\n${o.flat ? 'uniform vec4 uFlat;' : ''}\n`;
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
    let post = '';
    // texture contrast: pull the texel towards the finish's mean albedo (painted walls read clean)
    if (o.flat) post += `\n      diffuseColor.rgb = mix(diffuseColor.rgb, uFlat.rgb, uFlat.a);`;
    if (o.macro) post += `
      float mv = vFbm(vWPos.xz * uMacro.x) ;
      float mv2 = vNoise(vWPos.xz * uMacro.x * 7.3);
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
    if (o.glass) f = f.replace('#include <opaque_fragment>', `
      float gfr = pow(1.0 - clamp(abs(dot(normalize(normal), normalize(vViewPosition))), 0.0, 1.0), 4.0);
      float ga = mix(uGlass.x, uGlass.y, gfr);
      gl_FragColor = vec4(outgoingLight + diffuseColor.rgb * ga, ga);`);
    sh.fragmentShader = f;
  };
  return mat;
}

export function createMaterials(T, { maxAniso = 8 } = {}) {
  const M = {};
  const glow = []; // { mat, day, dusk } emissive intensities driven by time of day

  const clone = (t, rx, ry) => { const c = t.clone(); c.repeat.set(rx, ry); c.anisotropy = maxAniso; return c; };
  function pbr(name, o = {}) {
    const s = T[name];
    const tile = o.tile ?? 1, rx = 1 / tile, ry = 1 / (o.tileV ?? tile);
    const r = clone(s.r, rx, ry);
    const params = {
      map: clone(s.c, rx, ry), normalMap: clone(s.n, rx, ry), roughnessMap: r, aoMap: r,
      color: new THREE.Color(o.color ?? 0xffffff), roughness: o.rough ?? 1, metalness: o.metal ?? 0,
      normalScale: new THREE.Vector2(o.normal ?? 1, o.normal ?? 1), envMapIntensity: o.env ?? 1, aoMapIntensity: o.ao ?? 1,
      side: o.side ?? THREE.FrontSide,
    };
    let m;
    if (o.physical) m = new THREE.MeshPhysicalMaterial({ ...params, ...o.physical });
    else m = new THREE.MeshStandardMaterial(params);
    if (o.joints || o.macro) enhance(m, { joints: o.joints, macro: o.macro });
    m.name = name;
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
  M.render = pbr('plaster', { tile: 3.2, color: 0xf4f0ea, normal: 0.45, rough: 1 });
  M.paint = pbr('plaster', { tile: 3.2, color: 0xf0ebe3, normal: 0.12, rough: 0.95, env: 0.25 });
  M.ceiling = pbr('plaster', { tile: 3.2, color: 0xf5f2ec, normal: 0.08, rough: 1, env: 0.22 });
  for (const m of [M.paint, M.ceiling]) enhance(m, { ...(m.userData.fx || {}), flat: true });
  M.stone = pbr('marble', { tile: 2.6, color: 0x7b7976, rough: 0.75, normal: 0.6, env: 0.7, joints: { size: [1.2, 0.6], width: 0.005, shade: 0.45 } });
  M.bronze = std({ color: 0x6f5238, metalness: 0.85, roughness: 0.38 });
  M.frame = std({ color: 0x1c1d1f, metalness: 0.6, roughness: 0.42 });
  M.glass = enhance(new THREE.MeshStandardMaterial({ color: 0x0b0d0e, roughness: 0.03, metalness: 0, transparent: true, premultipliedAlpha: true, depthWrite: false, side: THREE.DoubleSide }), { glass: [0.06, 0.75] });
  M.glass.userData.noShadow = true;
  M.glassLight = enhance(new THREE.MeshStandardMaterial({ color: 0x0e1010, roughness: 0.02, metalness: 0, transparent: true, premultipliedAlpha: true, depthWrite: false, side: THREE.DoubleSide }), { glass: [0.03, 0.5] });
  M.glassLight.userData.noShadow = true;
  M.wood = pbr('walnut', { tile: 1.6, color: 0x7a5e4b, rough: 0.75, normal: 0.6 });
  M.pavers = pbr('pavers', { tile: 2.2, color: 0xd6c8b3, rough: 1, macro: { scale: 0.05, amount: 0.12 } });
  M.sidewalk = pbr('sidewalk', { tile: 2.4, color: 0xddd1bf, rough: 1, macro: { scale: 0.03, amount: 0.15 } });
  M.asphalt = pbr('asphalt', { tile: 5, color: 0x6c6965, rough: 1, normal: 0.6, macro: { scale: 0.012, amount: 0.16 } });
  M.curb = pbr('plaster', { tile: 2, color: 0xc9c5bd, normal: 0.6, rough: 1 });
  M.grass = pbr('grass', { tile: 2.6, color: 0xc8d6a0, rough: 1, normal: 0.8, macro: { scale: 0.08, amount: 0.22, hue: 0.4 } });
  M.sand = pbr('sand', { tile: 9, color: 0xf1dfc4, rough: 1, normal: 0.9, macro: { scale: 0.012, amount: 0.2, hue: 0.5 } });
  M.base = pbr('sand', { tile: 7, color: 0xe8d9c2, rough: 1, normal: 0.7, macro: { scale: 0.02, amount: 0.18, hue: 0.4 } });
  M.base.polygonOffset = true; M.base.polygonOffsetFactor = -1; M.base.polygonOffsetUnits = -2;
  M.desert = pbr('sand', { tile: 34, color: 0xe6c696, rough: 1, normal: 1.2, macro: { scale: 0.004, amount: 0.22, hue: 0.7 } });
  M.gravel = pbr('gravel', { tile: 1.4, color: 0xe9e4da, rough: 1 });
  M.soil = pbr('gravel', { tile: 1.2, color: 0x6a5643, rough: 1 });
  M.patio = pbr('patio', { tile: 2.4, color: 0xe2dbd0, rough: 0.9, normal: 0.6 });
  M.bark = pbr('bark', { tile: 1, tileV: 1.4, color: 0x8c7f6c, rough: 1 });
  M.travertine = pbr('travertine', { tile: 1.8, color: 0xf3ebde, rough: 0.55, env: 0.3, joints: { size: [1.2, 0.6], width: 0.003, shade: 0.72 } });
  M.travertineSlab = pbr('travertine', { tile: 1.4, color: 0xf0e6d6, rough: 0.6, env: 0.3 });
  M.oakFloor = pbr('woodfloor', { tile: 2.2, color: 0xffe9cc, rough: 0.75, env: 0.25 });
  M.oak = pbr('oak', { tile: 1.4, color: 0xf6e3c8, rough: 0.7, env: 0.3 });
  M.joinery = pbr('walnut', { tile: 1.2, color: 0xc09a80, rough: 0.5, env: 0.3 }); // doors, wardrobes, kitchen runs
  M.walnut = pbr('walnut', { tile: 1.2, color: 0x8d715e, rough: 0.55, env: 0.3 });
  M.marble = pbr('marble', { tile: 1.8, color: 0xffffff, rough: 0.5, env: 0.45, physical: { clearcoat: 0.6, clearcoatRoughness: 0.08 } });
  M.marbleFloor = pbr('marble', { tile: 1.6, color: 0xf2f0ec, rough: 0.6, env: 0.35, joints: { size: [0.6, 0.6], width: 0.002, shade: 0.7 } });
  M.boucle = pbr('boucle', { tile: 0.45, color: 0xefe8dc, rough: 1, normal: 1.4, env: 0.25, physical: { sheen: 0.6, sheenRoughness: 0.75, sheenColor: new THREE.Color(0xffffff) } });
  M.linen = pbr('linen', { tile: 0.5, color: 0xf6f3ee, rough: 1, normal: 0.9, env: 0.25, physical: { sheen: 0.4, sheenRoughness: 0.8, sheenColor: new THREE.Color(0xffffff) } });
  M.linenSand = pbr('linen', { tile: 0.5, color: 0xd9c8ae, rough: 1, normal: 0.9, env: 0.25, physical: { sheen: 0.4, sheenRoughness: 0.8, sheenColor: new THREE.Color(0xfff4e6) } });
  M.linenGrey = pbr('linen', { tile: 0.5, color: 0xb9b4ac, rough: 1, normal: 0.9, env: 0.5 });
  M.velvet = pbr('velvet', { tile: 0.7, color: 0x6e4f8f, rough: 0.9, normal: 0.6, env: 0.25, physical: { sheen: 1, sheenRoughness: 0.45, sheenColor: new THREE.Color(0xc7a9e6) } });
  M.rug = pbr('rug', { tile: 0.9, color: 0xe8dfd2, rough: 1, normal: 1.1, env: 0.2 });
  M.weave = pbr('linen', { tile: 0.3, color: 0xd9c19a, rough: 0.9, normal: 1.2, env: 0.3, side: THREE.DoubleSide });
  M.sheer = new THREE.MeshStandardMaterial({ map: clone(T.linen.c, 2, 2), color: 0xfbf8f2, roughness: 1, transparent: true, opacity: 0.72, side: THREE.DoubleSide, envMapIntensity: 0.4, depthWrite: false });
  M.sheer.userData.noShadow = true;
  // backlit translucency: the panel glows with the daylight behind it, and barely at night
  M.sheer.emissive.set(0xfff4e8);
  glow.push({ mat: M.sheer, day: 0.2, dusk: 0.012 });

  M.blackSatin = std({ color: 0x141414, roughness: 0.35, metalness: 0.2, envMapIntensity: 0.6 });
  M.tv = std({ color: 0x050505, roughness: 0.12, metalness: 0.1, envMapIntensity: 0.9 });
  M.brass = std({ color: 0xc8a467, roughness: 0.28, metalness: 1, envMapIntensity: 0.8 });
  M.chrome = std({ color: 0xdedede, roughness: 0.08, metalness: 1 });
  M.ceramic = new THREE.MeshPhysicalMaterial({ color: 0xf7f6f3, roughness: 0.25, clearcoat: 1, clearcoatRoughness: 0.05, envMapIntensity: 0.6 });
  M.mirror = std({ color: 0xe6e6e6, roughness: 0.02, metalness: 1, envMapIntensity: 0.9 });
  M.concrete = pbr('plaster', { tile: 1.5, color: 0xb7b1a8, normal: 0.7, rough: 1 });
  M.charcoal = std({ color: 0x2a2826, roughness: 0.8 });

  // ---- light emitters (intensity follows time of day)
  M.lampShade = emissive(0xffd7a3, 0.25, 2.2, { base: 0xf1e7d6, params: { side: THREE.DoubleSide, roughness: 1 } });
  M.bulb = emissive(0xffcf8f, 1.5, 7, {});
  M.downlight = emissive(0xfff0dc, 1.2, 6, {});
  M.led = emissive(0xffd29c, 0.6, 5, {});
  M.fire = emissive(0xff8a3a, 0, 6, {});
  M.lampHead = emissive(0xffd9a6, 0.0, 9, { base: 0x2a2622 });
  M.roomLit = emissive(0xffdfb4, 0.08, 1.15, { base: 0x15110d, params: { map: P.roomTexture(), emissiveMap: P.roomTexture(), roughness: 0.9 } });
  M.roomDim = std({ color: 0x0b0a09, roughness: 0.9, map: P.roomTexture() });

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
  M.frond = enhance(leafMat(P.frondTexture()), { sway: 0.55 });
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
  M.lod = new THREE.MeshStandardMaterial({ map: atlas.map, emissiveMap: atlas.emissive, emissive: 0xffd9a6, emissiveIntensity: 0, roughness: 0.9 });
  glow.push({ mat: M.lod, day: 0, dusk: 1.1 });
  M.lodRoof = std({ color: 0xe9e4dc, roughness: 1 });
  const wn = P.waterNormals();
  wn.repeat.set(1 / 9, 1 / 9);
  M.water = new THREE.MeshStandardMaterial({ color: 0x154e58, roughness: 0.04, metalness: 0.0, normalMap: wn, normalScale: new THREE.Vector2(0.3, 0.3), envMapIntensity: 1.7 });
  M.water.userData.noShadow = true;
  M.poolWater = new THREE.MeshStandardMaterial({ color: 0x3fb7c4, roughness: 0.05, normalMap: wn, normalScale: new THREE.Vector2(0.25, 0.25), envMapIntensity: 1.2 });

  const blob = P.radialTexture('rgba(255,255,255,1)', 'rgba(255,255,255,0)');
  M.pool = new THREE.MeshBasicMaterial({ map: blob, color: 0xffc98a, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: true });
  M.pool.userData.noShadow = true;
  glow.push({ mat: M.pool, day: 0, dusk: 0.55, prop: 'opacity' });

  M.beam = beamMaterial(0xffcf96);
  M.beam.userData.noShadow = true;
  glow.push({ mat: M.beam, day: 0, dusk: 0.16, prop: 'uOpacity' });
  for (const [k, m] of Object.entries(M)) {
    if (m.isMeshStandardMaterial && !m.transparent && k !== 'water' && k !== 'poolWater') enhance(m, { ...(m.userData.fx || {}), gi: true });
  }
  return { M, glow, water: wn };
}
