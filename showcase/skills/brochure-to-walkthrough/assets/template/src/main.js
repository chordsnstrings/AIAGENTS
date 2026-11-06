import * as THREE from 'three';
import { Builder, meshes } from './builder.js';
import { buildShell } from './house.js';
import { buildInterior, makeKit } from './interior.js';
import { buildStyleSet } from './stylesets.js';
import { STYLES, createStyler } from './styles.js';
import { buildCommunity } from './community.js';
import { loadTextureSets, createMaterials, shared } from './materials.js';
import { Atmosphere } from './atmosphere.js';
import { DronePath, DroneRig } from './path.js';
import { createPost } from './post.js';
import { initUI } from './ui.js';
import { makeDust } from './volumetric.js';
import { createGI } from './gi.js';
import { LOOK } from './look.js';

const params = new URLSearchParams(location.search);
const STILL = params.has('p');
const FIXED_P = parseFloat(params.get('p') || '0');
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

function detectTier() {
  const q = params.get('q');
  if (q) return q;
  const coarse = matchMedia('(pointer: coarse)').matches;
  const mem = navigator.deviceMemory || 8;
  if (coarse || mem <= 4 || Math.min(screen.width, screen.height) < 600) return 'low';
  return 'high';
}
const TIER = detectTier();
const Q = {
  high: { dprMax: 2, shadow: 4096, ao: true, aoQuality: 'Medium', halfRes: true, smaa: true, bloom: true },
  mid: { dprMax: 1.5, shadow: 2048, ao: true, aoQuality: 'Performance', halfRes: true, smaa: true, bloom: true },
  low: { dprMax: 1.3, shadow: 2048, ao: false, smaa: false, bloom: true },
}[TIER] || { dprMax: 2, shadow: 4096, ao: true, aoQuality: 'Medium', halfRes: true, smaa: true, bloom: true };

const nextFrame = () => new Promise((r) => requestAnimationFrame(() => r()));
const smooth = THREE.MathUtils.smoothstep;
const lerp = THREE.MathUtils.lerp;

const T0 = performance.now();
const mark = (s) => { if (STILL) console.log(`[t] ${s} ${((performance.now() - T0) / 1000).toFixed(1)}s`); };

async function main() {
  const canvas = document.getElementById('scene');
  if (params.get('ui') === '0') document.body.classList.add('noui');
  let mode = params.get('tod') || 'auto';
  let jumpTo = null;
  let applyStyle = () => {};
  const ui = initUI({
    styles: STYLES,
    onStyle: (k) => applyStyle(k),
    onMode: (m) => { mode = m; wake(); },
    onJump: (p) => { const max = document.documentElement.scrollHeight - innerHeight; scrollTo({ top: p * max, behavior: reduceMotion ? 'auto' : 'smooth' }); },
  });
  document.querySelectorAll('[data-mode]').forEach((b) => b.classList.toggle('on', b.dataset.mode === mode));

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance', stencil: false });
  } catch (e) {
    ui.fatal('WebGL is not available in this browser.');
    return;
  }
  let dpr = Math.min(devicePixelRatio || 1, Q.dprMax);
  renderer.setPixelRatio(dpr);
  renderer.setSize(innerWidth, innerHeight, false);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.6;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.shadowMap.autoUpdate = false;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(50, innerWidth / innerHeight, 0.08, 9000);

  ui.progress(0.03, 'Loading photo-scanned materials');
  const maxAniso = renderer.capabilities.getMaxAnisotropy();
  const T = await loadTextureSets('assets/tex/', Math.min(8, maxAniso), (f) => ui.progress(0.03 + f * 0.62));
  const { M, glow } = createMaterials(T, { maxAniso: Math.min(8, maxAniso) });
  mark('textures');

  ui.progress(0.68, 'Building plot XJ407B');
  await nextFrame();
  const HB = new Builder();
  const shellSpots = buildShell(HB, { hero: true });
  const { spots: inSpots, lights: lightDefs } = buildInterior(HB);
  scene.add(meshes(HB.geometries(), M));
  // switchable furniture sets for living, dining and master (one visible at a time)
  const styleGroups = {};
  for (const key of Object.keys(STYLES)) {
    const SB = new Builder();
    buildStyleSet(SB, key, makeKit(SB, { bush: [], flower: [], olive: [], pink: [] }));
    styleGroups[key] = meshes(SB.geometries(), M);
    scene.add(styleGroups[key]);
  }
  const styler = createStyler({ M, T, base: 'assets/tex/', anisotropy: Math.min(8, maxAniso), onLoading: (b) => ui.styleLoading(b) });
  const fromHash = location.hash.slice(1);
  let styleKey = STYLES[fromHash] ? fromHash : (params.get('style') || 'minimal');
  await styler.apply(styleKey);
  const heroSpots = { ...shellSpots };
  for (const [k, v] of Object.entries(inSpots)) heroSpots[k] = [...(heroSpots[k] || []), ...v];

  ui.progress(0.76, 'Laying out the community');
  await nextFrame();
  const { group: community } = buildCommunity(M, heroSpots, { lite: TIER === 'low' });
  scene.add(community);
  mark('geometry');

  // daylight and lamp light indoors come from the baked volume (gi.js); these few point lights
  // only add the glints and the terrace fire's warmth
  const lights = [];
  for (const L of lightDefs) {
    const l = new THREE.PointLight(L.color, L.day, L.dist, 2);
    l.position.set(L.pos[0], L.pos[1], -L.pos[2]);
    scene.add(l);
    lights.push({ l, day: L.day, dusk: L.dusk });
  }

  const atmo = new Atmosphere(renderer, scene, { shadowMapSize: Q.shadow });
  atmo.envFor(0, -55, 18); // reference sky for the GI volume
  atmo.onLevel = () => wake();
  const gi = createGI();
  const post = createPost(renderer, scene, camera, { ...Q, sun: atmo.sun, volSteps: TIER === 'mid' ? 20 : 28 });
  const dust = makeDust([
    [0.3, 5.8, 0.4, 3.0, 10.8, 14.6], [2.0, 3.1, 0.4, 3.0, 6.8, 10.5], [2.6, 5.9, 3.7, 6.3, 3.6, 6.5],
    [0.4, 5.6, 3.65, 6.3, 1.6, 3.3], [3.1, 5.9, 3.7, 6.3, 10.8, 14.0], [0.3, 5.8, 6.9, 9.4, 11.3, 14.0], [3.0, 5.9, 6.9, 9.5, 8.1, 11.0],
  ], TIER === 'low' ? 2.5 : 5);
  scene.add(dust);
  const beams = community.getObjectByName('lampBeams');
  post.setSize(innerWidth, innerHeight, dpr);

  const path = new DronePath();
  const rig = new DroneRig(camera);
  const pos = new THREE.Vector3(), look = new THREE.Vector3();
  const pinWorld = new THREE.Vector3(3.05, 11.5, -9);

  // ---- scroll state
  const root = document.documentElement;
  let target = STILL ? FIXED_P : 0, progress = target;
  const readScroll = () => {
    if (STILL) return;
    const max = root.scrollHeight - innerHeight;
    target = max > 0 ? THREE.MathUtils.clamp(scrollY / max, 0, 1) : 0;
  };
  readScroll();
  progress = target;
  let awakeUntil = 0;
  const wake = () => { awakeUntil = performance.now() + 1600; };
  addEventListener('scroll', () => { readScroll(); wake(); }, { passive: true });
  addEventListener('resize', () => {
    renderer.setSize(innerWidth, innerHeight, false);
    camera.aspect = innerWidth / innerHeight;
    camera.updateProjectionMatrix();
    post.setSize(innerWidth, innerHeight, dpr);
    wake();
  });
  document.addEventListener('visibilitychange', wake);

  let tod = mode === 'night' ? 1 : 0, exposure = 0.6, inside = 0;
  const zoneFor = (c) => {
    const inHouse = c.x > 0.05 && c.x < 6.05 && c.z < -1.4 && c.z > -15.4 && c.y < 10.2;
    if (c.y > 42) return 'aerial';
    if (inHouse || (c.x > -2 && c.x < 8 && c.z < 0 && c.z > -18.5 && c.y < 12)) return 'house';
    return 'street';
  };

  function update(dt, time) {
    progress = STILL ? FIXED_P : progress + (target - progress) * (1 - Math.exp(-dt * (reduceMotion ? 8 : 2.2)));
    if (Math.abs(target - progress) < 1e-6) progress = target;
    const fov = path.sample(progress, pos, look);
    rig.update(pos, look, fov, dt, time, { hover: reduceMotion ? 0 : 1, still: STILL });
    camera.updateMatrixWorld();

    const todTarget = mode === 'day' ? 0 : mode === 'night' ? 1 : smooth(progress, 0.79, 0.975);
    tod = STILL ? todTarget : tod + (todTarget - tod) * (1 - Math.exp(-dt * 2.5));
    // sun holds south-west through the master suite, swings north-west for the terrace, then sets
    const swing = smooth(progress, 0.735, 0.83);
    const sunEl = lerp(lerp(18, 11.5, swing), 4, smooth(progress, 0.868, 0.89));
    const s = atmo.update(tod, time, lerp(-55, -128, swing), sunEl);
    const zone = zoneFor(camera.position);
    atmo.setShadowZone(zone);
    const c = camera.position;
    const inHouse = c.x > 0.1 && c.x < 6.0 && c.z < -3.5 && c.z > -14.85 && c.y < 9.7 && !(c.y > 6.8 && c.z < -11.2) ? 1 : 0;
    inside = STILL ? inHouse : inside + (inHouse - inside) * (1 - Math.exp(-dt * 2.2));
    const st = s || atmo.last;
    if (s) atmo.last = s;
    // indoors the camera opens up, as an interiors photographer would: ~2 stops by day, less at night
    const expTarget = st.exp * lerp(1, lerp(LOOK.insideExposureDay, LOOK.insideExposureNight, tod) * STYLES[styleKey].inside, inside);
    exposure = STILL ? expTarget : exposure + (expTarget - exposure) * (1 - Math.exp(-dt * 2.0));
    renderer.toneMappingExposure = exposure;
    if (post.aoPass) post.aoPass.configuration.aoRadius = zone === 'aerial' ? 5 : zone === 'street' ? 1.4 : 0.55;
    const lamp = smooth(tod, 0.3, 0.95);
    for (const g of glow) {
      const v = lerp(g.day, g.dusk, lamp);
      if (g.prop === 'opacity') g.mat.opacity = v;
      else if (g.prop) g.mat.uniforms[g.prop].value = v;
      else g.mat.emissiveIntensity = v;
    }
    if (beams) beams.visible = M.beam.uniforms.uOpacity.value > 0.003;
    // baked light for this moment: sky as the env map sees it, sun bounce as the sun shines, lamps at dusk
    const sr = atmo.skyRatio(), sk = atmo.sun.intensity / 4.3, sc = atmo.sun.color;
    const fk = sk * LOOK.giFill;
    const lk = LOOK.giLamp * lerp(LOOK.giLampDay, 1, lamp);
    gi.set(sr.map((v, c) => v * st.env * LOOK.giFill * LOOK.giWhiteBalance[c]), [sc.r * fk, sc.g / 0.81 * fk, sc.b / 0.6 * fk], [lk, lk, lk], styleKey);
    // volumetrics: dusty air indoors, thin height haze outside, long thin haze from the air
    const sunK = atmo.sun.intensity;
    const sm = atmo.sun.shadow;
    const du = dust.material.uniforms;
    du.uTime.value = time;
    du.uShadow.value = sm.map ? sm.map.depthTexture : null;
    du.uShadowMatrix.value.copy(sm.matrix);
    du.uSunCol.value.copy(atmo.sun.color).multiplyScalar(sunK * LOOK.dustSun * inside);
    du.uAmb.value.setRGB(1, 0.92, 0.83).multiplyScalar(LOOK.dustAmbient * inside * (1 - tod * 0.6));
    dust.visible = inside > 0.02 && !!sm.map;
    if (post.volPass) {
      // dusty, beam-forming air inside the house volume; thin height haze outside
      const u = post.volPass.u;
      const air = zone === 'aerial' ? 1 : 0;
      u.uDensity.value = lerp(0.0024, 0.0013, air);
      u.uDensityIn.value = 0.03;
      u.uHeightK.value = lerp(2.0, 4.0, air);
      u.uHeightScale.value = lerp(5, 18, air);
      u.uMaxDist.value = lerp(lerp(55, 280, air), 20, inside);
      u.uSunIn.value = 1.0; u.uSunOut.value = lerp(0.08, 0.1, air);
      u.uAmbIn.value = 0.6; u.uAmbOut.value = 1.0;
      post.volPass.sunCol.copy(atmo.sun.color).multiplyScalar(sunK * 0.16);
      post.volPass.ambCol.copy(scene.fog.color).multiplyScalar(0.14 * (0.6 + tod * 0.8));
    }
    for (const L of lights) L.l.intensity = lerp(L.day, L.dusk, smooth(tod, 0.25, 1.0));
    shared.time.value = time;
    M.water.normalMap.offset.set(time * 0.004, time * 0.0025);
    post.final.uniforms.uTime.value = time;
    ui.update(progress, camera, pinWorld, innerWidth, innerHeight);
    return Math.abs(target - progress) > 1e-5 || Math.abs(todTarget - tod) > 1e-4 || Math.abs(expTarget - exposure) > 1e-3;
  }

  // ---- warm up: compile every program before revealing
  for (const g of Object.values(styleGroups)) g.visible = true;
  ui.progress(0.86, 'Compiling shaders');
  update(0.016, 0);
  await nextFrame();
  try { await renderer.compileAsync(scene, camera); } catch (e) { /* older drivers: compile lazily */ }
  for (const [k, g] of Object.entries(styleGroups)) g.visible = k === styleKey;
  ui.setStyle(styleKey);
  applyStyle = async (k) => {
    if (!STYLES[k] || k === styler.current) return;
    await styler.apply(k);
    styleKey = k;
    for (const [key, g] of Object.entries(styleGroups)) g.visible = key === k;
    renderer.shadowMap.needsUpdate = true;
    ui.setStyle(k);
    try { history.replaceState(null, '', '#' + k); } catch (e) { /* sandboxed frames may refuse */ }
    wake();
  };
  mark('compiled');
  ui.progress(0.95, 'Lighting the scene');
  await nextFrame();
  post.composer.render(0.016);
  mark('first frame');
  ui.progress(1, 'Ready');
  ui.ready();
  window.__ready = true;

  if (STILL) {
    document.getElementById('loader')?.remove();
    // the sky level behind the baked light is read back asynchronously; give it a moment
    for (let i = 0; i < 15 && atmo.skyLevel.size < 2; i++) await new Promise((r) => setTimeout(r, 100));
    // render a few frames so shadow and AO settle, then signal the capture harness
    for (let i = 0; i < 3; i++) { update(0.016, 1 + i * 0.016); post.composer.render(0.016); await nextFrame(); }
    renderer.info.autoReset = false; renderer.info.reset();
    post.composer.render(0.016);
    renderer.info.autoReset = true;
    mark(`settled · ${renderer.info.render.calls} calls · ${(renderer.info.render.triangles / 1e6).toFixed(2)}M tris · ${renderer.info.programs.length} programs · ${renderer.info.memory.textures} textures`);
    window.__shot = true;
    return;
  }

  // ---- loop with idle sleep and adaptive resolution
  let last = performance.now(), frames = 0, acc = 0;
  wake();
  function frame(now) {
    requestAnimationFrame(frame);
    const dt = Math.min(0.1, (now - last) / 1000);
    last = now;
    const busy = update(dt, now / 1000);
    if (busy) wake();
    if (now > awakeUntil || document.hidden) return;
    post.composer.render(dt);
    acc += dt; frames++;
    if (frames >= 40) {
      const avg = acc / frames * 1000;
      frames = 0; acc = 0;
      let next = dpr;
      if (avg > 26 && dpr > 0.75) next = Math.max(0.75, dpr - 0.2);
      else if (avg < 13 && dpr < Math.min(devicePixelRatio || 1, Q.dprMax)) next = Math.min(Math.min(devicePixelRatio || 1, Q.dprMax), dpr + 0.1);
      if (next !== dpr) {
        dpr = next;
        renderer.setPixelRatio(dpr);
        renderer.setSize(innerWidth, innerHeight, false);
        post.setSize(innerWidth, innerHeight, dpr);
      }
    }
  }
  requestAnimationFrame(frame);
}

main().catch((e) => {
  console.error(e);
  const l = document.querySelector('#loader .label');
  if (l) l.textContent = 'Something went wrong: ' + e.message;
});
