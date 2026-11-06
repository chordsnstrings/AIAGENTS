import * as THREE from 'three';
import { Builder, meshes } from './builder.js';
import { buildShell } from './house.js';
import { buildInterior, makeKit } from './interior.js';
import { buildStyleSet } from './stylesets.js';
import { STYLES, createStyler } from './styles.js';
import { buildCommunity } from './community.js';
import { loadTextureSets, loadSet, adoptSet, createMaterials, shared, INTERIOR_SETS } from './materials.js';
import { Atmosphere } from './atmosphere.js';
import { DronePath, DroneRig } from './path.js';
import { createPost } from './post.js';
import { initUI } from './ui.js';
import { makeDust } from './volumetric.js';
import { createGI } from './gi.js';
import { LOOK } from './look.js';
import { TIERS, detectTier, pixelRatioFor, AdaptiveScale } from './tiers.js';

const params = new URLSearchParams(location.search);
const STILL = params.has('p');
const FIXED_P = parseFloat(params.get('p') || '0');
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

const nextFrame = () => new Promise((r) => requestAnimationFrame(() => r()));
const smooth = THREE.MathUtils.smoothstep;
const lerp = THREE.MathUtils.lerp;

const T0 = performance.now();
const mark = (s) => { if (STILL) console.log(`[t] ${s} ${((performance.now() - T0) / 1000).toFixed(1)}s`); };

// the hero's transparent meshes draw in a fixed order, sheer under glass, whatever the view
const ORDER = { sheer: 1, glass: 2, glassLight: 2 };

// a style named in the hash or query counts only as one of STYLES' own keys: '#constructor'
// and '?style=Luxe' both fall through
const pickStyle = (k) => { k = (k || '').toLowerCase(); return Object.hasOwn(STYLES, k) ? k : null; };

async function main() {
  const canvas = document.getElementById('scene');
  if (params.get('ui') === '0') document.body.classList.add('noui');
  let mode = params.get('tod') || 'auto';
  let applyStyle = () => {};
  let awakeUntil = 0;
  const wake = () => { awakeUntil = performance.now() + 1600; };
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
  const TIER = detectTier(renderer.getContext(), params.get('q'));
  const Q = TIERS[TIER];
  if (TIER === 'low') document.body.classList.add('lowfx'); // the overlay drops its backdrop blurs
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.6;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.shadowMap.autoUpdate = false;

  // three restores its own GL state after a context loss, but the cached environments, the
  // shadow map and the GI textures do not come back; for a marketing page a reload is the safe
  // recovery, and the scroll position survives it
  let lost = false;
  const toast = document.getElementById('toast');
  canvas.addEventListener('webglcontextlost', (e) => {
    e.preventDefault();
    lost = true;
    if (toast) { toast.innerHTML = '<b>Graphics paused</b><span>The 3D view reloads when the device is ready.</span>'; toast.classList.add('show'); }
  });
  canvas.addEventListener('webglcontextrestored', () => location.reload());

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(50, 1, 0.08, 9000);

  // ---- size: the canvas box (100vw x 100vh, the large viewport) sizes the drawing buffer, the
  // camera and the overlay, so a phone's toolbar showing or hiding changes nothing; the pixel
  // ratio follows the tier's pixel budget times the scaler's rung
  const scaler = new AdaptiveScale(renderer);
  const view = { w: 0, h: 0, dpr: 1 };
  let post = null;
  const applySize = () => {
    const w = canvas.clientWidth || innerWidth, h = canvas.clientHeight || innerHeight;
    const dpr = pixelRatioFor(Q.budget, w, h) * scaler.scale;
    if (w === view.w && h === view.h && Math.abs(dpr - view.dpr) < 1e-3) return false;
    view.w = w; view.h = h; view.dpr = dpr;
    renderer.setPixelRatio(dpr);
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    if (post) post.setSize(w, h, dpr);
    return true;
  };
  applySize();
  let resizeT = 0;
  new ResizeObserver(() => {
    clearTimeout(resizeT);
    resizeT = setTimeout(() => { if (applySize()) wake(); }, 150);
  }).observe(canvas);

  ui.progress(0.03, 'Loading photo-scanned materials');
  const aniso = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  const texBase = TIER === 'low' ? 'assets/tex/512/' : 'assets/tex/';
  // a still must be complete; the live page streams the interior sets behind the first frame,
  // since the camera starts in the air
  const deferred = STILL ? [] : INTERIOR_SETS;
  const T = await loadTextureSets(texBase, aniso, (f) => ui.progress(0.03 + f * 0.62), { defer: deferred });
  const { M, glow } = createMaterials(T, { maxAniso: aniso });
  // the styler clones whatever it is handed and caches the clones, so it only ever sees real textures
  const TS = {};
  for (const k of Object.keys(T)) if (!deferred.includes(k)) TS[k] = T[k];
  mark('textures');

  ui.progress(0.68, 'Building plot XJ407B');
  await nextFrame();
  const HB = new Builder();
  const shellSpots = buildShell(HB, { hero: true });
  const { spots: inSpots, lights: lightDefs } = buildInterior(HB);
  scene.add(meshes(HB.geometries(), M, { order: ORDER }));
  const fromHash = location.hash.slice(1);
  let styleKey = pickStyle(fromHash) || pickStyle(params.get('style')) || 'minimal';
  // switchable furniture sets for living, dining and master: only the chosen one is built now;
  // the others when their chip is hovered or focused, and compiled before they can show
  const styleGroups = {}, stylePending = {};
  const buildStyle = (key) => {
    const SB = new Builder();
    buildStyleSet(SB, key, makeKit(SB, { bush: [], flower: [], olive: [], pink: [] }));
    return meshes(SB.geometries(), M, { order: ORDER });
  };
  styleGroups[styleKey] = buildStyle(styleKey);
  scene.add(styleGroups[styleKey]);
  const ensureStyle = (key) => {
    if (styleGroups[key]) return Promise.resolve(styleGroups[key]);
    if (!stylePending[key]) {
      stylePending[key] = (async () => {
        const g = buildStyle(key);
        try { await renderer.compileAsync(g, camera, scene); } catch (e) { /* older drivers: compile lazily */ }
        g.visible = false;
        scene.add(g);
        styleGroups[key] = g;
        return g;
      })();
    }
    return stylePending[key];
  };
  const keys = Object.keys(STYLES); // ui.js appends one chip per style in this order
  document.querySelectorAll('#styles button').forEach((b, i) => {
    if (keys[i]) for (const ev of ['pointerenter', 'focus']) b.addEventListener(ev, () => ensureStyle(keys[i]));
  });
  const styler = createStyler({ M, T: TS, base: texBase, anisotropy: aniso, onLoading: (b) => ui.styleLoading(b) });
  await styler.apply(styleKey);
  const heroSpots = { ...shellSpots };
  for (const [k, v] of Object.entries(inSpots)) heroSpots[k] = [...(heroSpots[k] || []), ...v];

  ui.progress(0.76, 'Laying out the community');
  await nextFrame();
  const community = buildCommunity(M, heroSpots, { lite: TIER === 'low' });
  scene.add(community.group);
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
  post = createPost(renderer, scene, camera, { ...Q, sun: atmo.sun });
  post.setSize(view.w, view.h, view.dpr);
  const dust = makeDust([
    [0.3, 5.8, 0.4, 3.0, 10.8, 14.6], [2.0, 3.1, 0.4, 3.0, 6.8, 10.5], [2.6, 5.9, 3.7, 6.3, 3.6, 6.5],
    [0.4, 5.6, 3.65, 6.3, 1.6, 3.3], [3.1, 5.9, 3.7, 6.3, 10.8, 14.0], [0.3, 5.8, 6.9, 9.4, 11.3, 14.0], [3.0, 5.9, 6.9, 9.5, 8.1, 11.0],
  ], TIER === 'low' ? 0.8 : 1.5);
  scene.add(dust);
  const beams = community.group.getObjectByName('lampBeams');

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
  addEventListener('scroll', () => { readScroll(); wake(); }, { passive: true });
  document.addEventListener('visibilitychange', wake);

  let tod = mode === 'night' ? 1 : 0, exposure = 0.6, inside = 0, giTick = 0;
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
    community.setShadowZone(zone);
    community.update(camera.position);
    const c = camera.position;
    const inHouse = c.x > 0.1 && c.x < 6.0 && c.z < -3.5 && c.z > -14.85 && c.y < 9.7 && !(c.y > 6.8 && c.z < -11.2) ? 1 : 0;
    inside = STILL ? inHouse : inside + (inHouse - inside) * (1 - Math.exp(-dt * 2.2));
    const st = s || atmo.last;
    if (s) atmo.last = s;
    // indoors the camera opens up, as an interiors photographer would: ~2 stops by day, less at night
    const expTarget = st.exp * lerp(1, lerp(LOOK.insideExposureDay, LOOK.insideExposureNight, tod) * STYLES[styleKey].inside, inside);
    exposure = STILL ? expTarget : exposure + (expTarget - exposure) * (1 - Math.exp(-dt * 2.0));
    renderer.toneMappingExposure = exposure;
    // the phone tier's AO has fewer samples, so it keeps a tighter radius indoors
    if (post.aoPass) post.aoPass.configuration.aoRadius = zone === 'aerial' ? 5 : zone === 'street' ? 1.4 : Q.aoZones ? 0.35 : 0.55;
    if (Q.aoZones) post.setAO(zone !== 'aerial');
    const lamp = smooth(tod, 0.3, 0.95);
    for (const g of glow) {
      const v = lerp(g.day, g.dusk, lamp);
      if (g.prop === 'opacity') g.mat.opacity = v;
      else if (g.prop) g.mat.uniforms[g.prop].value = v;
      else g.mat.emissiveIntensity = v;
    }
    if (beams) beams.visible = M.beam.uniforms.uOpacity.value > 0.003;
    // baked light for this moment: sky as the env map sees it, sun bounce as the sun shines, lamps
    // at dusk. The remix is CPU work plus two 3D uploads, so while the light eases it runs every
    // third frame; once settled, every frame (gi.set itself skips unchanged weights).
    const sr = atmo.skyRatio(), sk = atmo.sun.intensity / 4.3, sc = atmo.sun.color;
    const fk = sk * LOOK.giFill;
    const lk = LOOK.giLamp * lerp(LOOK.giLampDay, 1, lamp);
    if (STILL || Math.abs(todTarget - tod) < 1e-4 || giTick++ % 3 === 0) {
      gi.set(sr.map((v, ch) => v * st.env * LOOK.giFill * LOOK.giWhiteBalance[ch]), [sc.r * fk, sc.g / 0.81 * fk, sc.b / 0.6 * fk], [lk, lk, lk], styleKey);
    }
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
      // dusty, beam-forming air inside the house volume; thin height haze outside, where a
      // dozen steps resolve it
      const u = post.volPass.u;
      const air = zone === 'aerial' ? 1 : 0;
      u.uDensity.value = lerp(0.0024, 0.0013, air);
      u.uDensityIn.value = 0.03;
      u.uHeightK.value = lerp(2.0, 4.0, air);
      u.uHeightScale.value = lerp(5, 18, air);
      u.uMaxDist.value = lerp(lerp(55, 280, air), 20, inside);
      u.uSteps.value = Math.round(lerp(12, post.volPass.steps, inside));
      u.uSunIn.value = 1.0; u.uSunOut.value = lerp(0.08, 0.1, air);
      u.uAmbIn.value = 0.6; u.uAmbOut.value = 1.0;
      post.volPass.sunCol.copy(atmo.sun.color).multiplyScalar(sunK * 0.16);
      post.volPass.ambCol.copy(scene.fog.color).multiplyScalar(0.14 * (0.6 + tod * 0.8));
    }
    for (const L of lights) L.l.intensity = lerp(L.day, L.dusk, smooth(tod, 0.25, 1.0));
    shared.time.value = time;
    M.water.normalMap.offset.set(time * 0.004, time * 0.0025);
    post.final.uniforms.uTime.value = time;
    ui.update(progress, camera, pinWorld, view.w, view.h);
    return Math.abs(target - progress) > 1e-5 || Math.abs(todTarget - tod) > 1e-4 || Math.abs(expTarget - exposure) > 1e-3;
  }

  // ---- warm up: compile every program before revealing. The lamp beams and the dust are hidden
  // by day, and compileAsync only visits what is visible, so they are shown for the compile.
  ui.progress(0.86, 'Compiling shaders');
  update(0.016, 0);
  const warm = [beams, dust].filter(Boolean);
  for (const o of warm) o.visible = true;
  await nextFrame();
  try { await renderer.compileAsync(scene, camera); } catch (e) { /* older drivers: compile lazily */ }
  for (const o of warm) o.visible = false;
  ui.setStyle(styleKey);
  applyStyle = async (k) => {
    if (!Object.hasOwn(STYLES, k) || k === styler.current) return;
    await Promise.all([styler.apply(k), ensureStyle(k)]);
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

  // ---- the interior sets arrive now, one set at a time; each lands in every material that
  // took a placeholder from it, then the style re-applies on top
  if (deferred.length) {
    (async () => {
      for (const name of deferred) {
        const set = await loadSet(texBase, name, aniso);
        T[name] = set; TS[name] = set;
        adoptSet(M, name, set);
        wake();
      }
      await styler.apply(styler.current || styleKey);
      wake();
    })().catch((e) => console.warn('interior textures', e));
  }

  // ---- loop with idle sleep and adaptive resolution
  let last = performance.now();
  wake();
  function frame(now) {
    requestAnimationFrame(frame);
    if (lost) { last = now; return; }
    const dt = Math.min(0.1, (now - last) / 1000);
    last = now;
    const busy = update(dt, now / 1000);
    if (busy) wake();
    if (now > awakeUntil || document.hidden) return;
    scaler.begin();
    post.composer.render(dt);
    scaler.end();
    // resolution follows the measured frame cost; a step up waits for the scroll to settle so
    // the reallocation never lands mid-gesture
    if (scaler.frame(dt * 1000, now, !busy)) applySize();
  }
  requestAnimationFrame(frame);
}

main().catch((e) => {
  console.error(e);
  const l = document.querySelector('#loader .label');
  if (l) l.textContent = 'Something went wrong: ' + e.message;
});
