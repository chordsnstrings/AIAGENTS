import * as THREE from 'three';
import { Sky } from 'three/addons/objects/Sky.js';
import { LightProbeGenerator } from 'three/addons/lights/LightProbeGenerator.js';

// The sun direction is fixed so the (expensive) shadow map is rendered once per zone; time of
// day changes the sky, light colour/intensity, fog, exposure and the environment map.

const D2R = Math.PI / 180;
const dirFrom = (az, el, v = new THREE.Vector3()) => v.set(Math.sin(az * D2R) * Math.cos(el * D2R), Math.sin(el * D2R), Math.cos(az * D2R) * Math.cos(el * D2R));
// Environments are binned coarsely enough that the whole evening builds about a dozen of them,
// not forty: time of day in tenths, the -55 -> -128 degree swing in three azimuth bins, elevation
// in 4 degree steps anchored on the bake's 18 degrees. PMREMGenerator clamps its size to 256, so
// each costs about 4 MB and tens of millions of samples whatever size is asked. The coarse set
// (phones) halves the time steps and takes the swing in two.
function envBin(t, az, el, coarse) {
  const q = coarse ? Math.round(t * 5) / 5 : Math.round(t * 10) / 10;
  const step = coarse ? 73 : 36.5, qa = Math.round((az + 55) / step);
  const qe = Math.round((el - 18) / 4) * 4 + 18;
  return { q, az: -55 + qa * step, el: qe, key: `${q}|${qa}|${qe}` };
}

const TWILIGHT = { horizon: [0.042, 0.038, 0.062], zenith: [0.006, 0.009, 0.026], glow: [0.11, 0.05, 0.03] };
// A Gulf evening is dust-hazed rather than deep blue: high turbidity, little Rayleigh, a wide Mie glow.
// The golden-hour row must match SKY in scripts/bake-gi.mjs.
const STATES = [
  { t: 0.0, elev: 17, turb: 8.0, ray: 1.1, mie: 0.004, mieG: 0.72, gain: 0.82, sun: 4.3, sunCol: [1.0, 0.81, 0.6], fog: [0.84, 0.78, 0.71], fogD: 0.0009, exp: 0.7, env: 0.55, ground: [0.55, 0.5, 0.44], disc: 1 },
  { t: 0.5, elev: 3.0, turb: 7.5, ray: 2.0, mie: 0.004, mieG: 0.76, gain: 0.95, sun: 2.2, sunCol: [1.0, 0.62, 0.4], fog: [0.84, 0.66, 0.55], fogD: 0.0011, exp: 0.88, env: 0.6, ground: [0.42, 0.34, 0.28], disc: 1 },
  { t: 1.0, elev: 0.4, turb: 2.0, ray: 4.2, mie: 0.002, mieG: 0.75, gain: 0.6, sun: 0.0, sunCol: [0.55, 0.6, 0.85], fog: TWILIGHT.horizon, fogD: 0.0011, exp: 2.0, env: 1.4, ground: [0.06, 0.065, 0.085], disc: 0 },
];
const lerp = THREE.MathUtils.lerp;
function stateAt(t) {
  let a = STATES[0], b = STATES[1];
  if (t > STATES[1].t) { a = STATES[1]; b = STATES[2]; }
  const k = THREE.MathUtils.clamp((t - a.t) / (b.t - a.t), 0, 1);
  const o = {};
  for (const key of Object.keys(a)) o[key] = Array.isArray(a[key]) ? a[key].map((v, i) => lerp(v, b[key][i], k)) : lerp(a[key], b[key], k);
  // the haze must darken with the twilight sky, not linearly, or it glows at the horizon
  const tw = THREE.MathUtils.smoothstep(t, 0.55, 0.92);
  o.fog = o.fog.map((v, i) => lerp(v, TWILIGHT.horizon[i], tw));
  return o;
}

function makeSky(scale) {
  const sky = new Sky();
  sky.scale.setScalar(scale);
  const m = sky.material;
  Object.assign(m.uniforms, {
    uGain: { value: 1 }, uTwK: { value: 0 }, uHz: { value: 0.04 }, uFog: { value: new THREE.Vector3(0.8, 0.75, 0.7) },
    uTwH: { value: new THREE.Vector3(...TWILIGHT.horizon) }, uTwZ: { value: new THREE.Vector3(...TWILIGHT.zenith) }, uTwG: { value: new THREE.Vector3(...TWILIGHT.glow) },
  });
  // Preetham has no twilight: past sunset blend to an analytic gradient (afterglow towards the
  // sun's azimuth, deep blue overhead), then melt the horizon into the fog colour so distant
  // terrain and sky meet without a seam.
  m.fragmentShader = 'uniform float uGain, uTwK, uHz; uniform vec3 uFog, uTwH, uTwZ, uTwG;\n' + m.fragmentShader
    .replace('gl_FragColor = vec4( texColor, 1.0 );', `
      float hh = max(direction.y, 0.0);
      float sa = max(dot(normalize(direction.xz + 1e-5), normalize(vSunDirection.xz + 1e-5)), 0.0);
      vec3 tw = mix(uTwH, uTwZ, pow(hh, 0.5)) + uTwG * pow(sa, 5.0) * exp(-hh * 7.0);
      vec3 col = mix(texColor * uGain, tw, uTwK);
      col = mix(uFog, col, smoothstep(-0.015, uHz, direction.y));
      gl_FragColor = vec4(col, 1.0);`)
    .replace('( 760.0 * sundisc )', '( 25.0 * sundisc )');
  // a few small high wisps rather than one soft blob: a large scale with low density read as a smudge
  m.uniforms.cloudCoverage.value = 0.08;
  m.uniforms.cloudDensity.value = 0.7;
  m.uniforms.cloudElevation.value = 0.55;
  m.uniforms.cloudScale.value = 0.0012;
  sky.frustumCulled = false;
  return sky;
}

export class Atmosphere {
  // envCacheSize: PMREM environments kept (about 4 MiB each; fewer on phones). probeSize: the
  // reflection probes' cube face size (128 on phones). envBins: 'fine' | 'coarse' (see envBin).
  constructor(renderer, scene, { shadowMapSize = 4096, envCacheSize = 16, probeSize = 256, envBins = 'fine' } = {}) {
    this.renderer = renderer;
    this.scene = scene;
    this.coarse = envBins === 'coarse';
    this.bakeKey = envBin(0, -55, 18, this.coarse).key; // the golden-hour env scripts/bake-gi.mjs lit the GI volume with
    this.sky = makeSky(9000);
    scene.add(this.sky);

    this.sun = new THREE.DirectionalLight(0xffffff, 3);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(shadowMapSize, shadowMapSize);
    this.sun.shadow.radius = 2.5;
    this.sun.shadow.bias = -0.00025;
    this.sun.shadow.normalBias = 0.025;
    this.sun.target.position.set(3.05, 0, -9);
    scene.add(this.sun, this.sun.target);
    this.zone = null;
    this.sunDir = dirFrom(-55, 18);
    this.az = null; this.el = null;

    scene.fog = new THREE.FogExp2(0xd6c8b8, 0.001);

    // environment: a small copy of the sky plus warm ground bounce
    this.envScene = new THREE.Scene();
    this.envSky = makeSky(400);
    this.envGround = new THREE.Mesh(new THREE.CircleGeometry(300, 32).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x806040 }));
    this.envGround.position.y = -8;
    this.envScene.add(this.envSky, this.envGround);
    this.pmrem = new THREE.PMREMGenerator(renderer);
    this.envCache = new Map(); // key -> PMREM render target, least recently used first
    this.envCacheSize = envCacheSize;
    this.skyLevel = new Map();
    this.pendingLevel = new Set();
    this.lastRatio = null;
    this.envKey = null;
    this.litMats = null;
    this.probedMats = [];

    // local reflection probes for the glazing: what the street-front and garden-facing panes mirror.
    // Materials opt in with userData.probe = 'front' | 'rear' (materials.js); the sky env map alone
    // has no facades or street in it, so windows read as holes without them.
    this.probes = { front: this.makeProbe(3.05, 1.6, 4, probeSize), rear: this.makeProbe(3.05, 1.6, -17, probeSize) };
    this.probeKey = null;

    // stars for blue hour
    const n = 1400, p = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const u = Math.random(), v = Math.random() * 0.92 + 0.08;
      const th = u * Math.PI * 2, y = v, r = Math.sqrt(1 - y * y);
      p.set([Math.cos(th) * r * 3600, y * 3600, Math.sin(th) * r * 3600], i * 3);
    }
    const sg = new THREE.BufferGeometry();
    sg.setAttribute('position', new THREE.BufferAttribute(p, 3));
    this.stars = new THREE.Points(sg, new THREE.PointsMaterial({ color: 0xffffff, size: 1.6, sizeAttenuation: false, transparent: true, opacity: 0, fog: false, depthWrite: false }));
    this.stars.frustumCulled = false;
    scene.add(this.stars);
    this.t = -1;
  }

  setShadowZone(zone) {
    if (zone === this.zone) return;
    this.zone = zone;
    this.half = { aerial: 300, street: 60, house: 18 }[zone];
    const c = this.sun.shadow.camera;
    c.left = -this.half; c.right = this.half; c.top = this.half; c.bottom = -this.half;
    c.near = 1; c.far = this.half * 2 + 400;
    c.updateProjectionMatrix();
    this.sun.target.position.copy(zone === 'aerial' ? new THREE.Vector3(-40, 0, -20) : new THREE.Vector3(3.05, 4, -9));
    this.sun.shadow.normalBias = { aerial: 0.25, street: 0.05, house: 0.02 }[zone];
    this.sun.shadow.radius = { aerial: 1.5, street: 2.0, house: 3.0 }[zone];
    this.placeSun();
  }

  // Shadow-casting sun direction (degrees; azimuth from +z towards +x).
  setSun(az, el) {
    if (this.az !== null && Math.abs(az - this.az) < 0.15 && Math.abs(el - this.el) < 0.15) return false;
    this.az = az; this.el = el;
    dirFrom(az, el, this.sunDir);
    this.placeSun();
    return true;
  }

  placeSun() {
    this.sun.target.updateMatrixWorld();
    this.sun.position.copy(this.sun.target.position).addScaledVector(this.sunDir, (this.half || 60) + 200);
    this.sun.updateMatrixWorld();
    this.renderer.shadowMap.needsUpdate = true;
  }

  applySky(sky, s, az, el, t = 0) {
    const u = sky.material.uniforms;
    dirFrom(az, el, u.sunPosition.value);
    u.uTwK.value = THREE.MathUtils.smoothstep(t, 0.55, 0.92);
    u.uHz.value = lerp(0.035, 0.1, THREE.MathUtils.smoothstep(t, 0.5, 1.0));
    u.uFog.value.set(...s.fog);
    u.turbidity.value = s.turb; u.rayleigh.value = s.ray; u.mieCoefficient.value = s.mie; u.mieDirectionalG.value = s.mieG;
    u.uGain.value = s.gain;
    u.showSunDisc.value = s.disc;
  }

  // the environment for this moment, made current for skyRatio
  envFor(t, az, el) {
    const b = envBin(t, az, el, this.coarse);
    this.envKey = b.key;
    return this.build(b);
  }

  build(b) {
    const key = b.key;
    let rt = this.envCache.get(key);
    if (rt) { // a hit moves to the back of the eviction order
      this.envCache.delete(key); this.envCache.set(key, rt);
      return rt.texture;
    }
    const s = stateAt(b.q);
    this.applySky(this.envSky, s, b.az, this.skyElev(b.q, b.el, s), b.q);
    this.envGround.material.color.setRGB(...s.ground);
    rt = this.pmrem.fromScene(this.envScene, 0, 0.1, 1000, { size: 256 });
    if (!this.skyLevel.has(key) && !this.pendingLevel.has(key)) this.measure(key);
    this.envCache.set(key, rt);
    // The target is cached, not its texture: disposing a PMREM texture frees nothing in three (no
    // dispose listener is ever registered for a render-target texture), while rt.dispose() frees the
    // texture and all 36 face framebuffers. The bake's reference env and the one on screen are
    // pinned, because the first three quarters of the route use the former and the ending alone
    // would otherwise evict and rebuild it.
    for (const k of this.envCache.keys()) {
      if (this.envCache.size <= this.envCacheSize) break;
      if (k === this.bakeKey || k === key || k === this.envKey) continue;
      this.envCache.get(k).dispose();
      this.envCache.delete(k);
    }
    return rt.texture;
  }

  // Build the environments of a schedule of [t, az, el] moments ahead of time, one per idle
  // period and never while the page is busy (scrolling, easing), so a sunset reached by scrolling
  // finds its skies ready instead of stalling on a PMREM render. The current key is untouched.
  prebuild(list, busy = () => false) {
    const seen = new Set(this.envCache.keys()), queue = [];
    for (const [t, az, el] of list) { const b = envBin(t, az, el, this.coarse); if (!seen.has(b.key)) { seen.add(b.key); queue.push(b); } }
    const later = (fn, ms) => (ms === undefined && typeof requestIdleCallback === 'function' ? requestIdleCallback(fn, { timeout: 600 }) : setTimeout(fn, ms ?? 120));
    const step = () => {
      if (!queue.length || this.renderer.getContext().isContextLost()) return;
      if (busy()) { later(step, 300); return; }
      this.build(queue.shift());
      later(step);
    };
    later(step, 800);
  }

  // mean radiance of each environment (the L0 term of an 8px cube read back), so the baked sky
  // light indoors can follow the real sky through the evening
  measure(key) {
    if (this.renderer.getContext().isContextLost()) return;
    this.pendingLevel.add(key);
    const rt = new THREE.WebGLCubeRenderTarget(8, { type: THREE.HalfFloatType });
    new THREE.CubeCamera(0.1, 1000, rt).update(this.renderer, this.envScene);
    LightProbeGenerator.fromCubeRenderTarget(this.renderer, rt).then((lp) => {
      // a zero or non-finite read-back (a lost context, a driver refusing the half-float read)
      // would turn the whole GI volume into NaN; such a key stays unmeasured and the curve stands in
      const c = lp.sh.coefficients[0];
      if ([c.x, c.y, c.z].every((v) => Number.isFinite(v) && v > 1e-6)) this.skyLevel.set(key, c.clone());
      if (this.onLevel) this.onLevel();
    }).catch(() => {}).finally(() => { rt.dispose(); this.pendingLevel.delete(key); });
  }

  // rgb ratio of the current env to the one the bake used, clamped to [0, 4]
  skyRatio() {
    const a = this.skyLevel.get(this.envKey), b = this.skyLevel.get(this.bakeKey);
    if (a && b) {
      this.lastRatio = [a.x / b.x, a.y / b.y, a.z / b.z].map((v) => Number.isFinite(v) ? THREE.MathUtils.clamp(v, 0, 4) : 0);
      return this.lastRatio;
    }
    // while this env's read-back is in flight hold the last measured ratio rather than flicking to the
    // fitted curve and back; the curve (an evening sky) stands in only where nothing has been measured
    if (this.lastRatio && this.pendingLevel.has(this.envKey)) return this.lastRatio;
    const t = Math.max(0, this.t), n = THREE.MathUtils.smoothstep(t, 0.5, 1);
    const k = THREE.MathUtils.lerp(1, 0.55, THREE.MathUtils.smoothstep(t, 0, 0.5)) * THREE.MathUtils.lerp(1, 0.05, n);
    return [k * (1 - 0.3 * n), k, k * (1 + 0.4 * n)];
  }

  skyElev(t, el, s) { return THREE.MathUtils.lerp(el, Math.min(el, s.elev), THREE.MathUtils.smoothstep(t, 0.0, 0.5)); }

  // Every lit material in the scene, split into those that mirror a local probe and the rest. Call
  // again after adding objects to the scene; update() refreshes it whenever the env map changes.
  refreshMaterials() {
    const seen = new Set(), lit = [], probed = [];
    this.scene.traverse((o) => {
      if (!o.material) return;
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
        if (seen.has(m) || !m.isMeshStandardMaterial) continue;
        seen.add(m);
        (m.userData.probe ? probed : lit).push(m);
      }
    });
    this.litMats = lit; this.probedMats = probed;
  }

  makeProbe(x, y, z, size) {
    const rt = new THREE.WebGLCubeRenderTarget(size, { type: THREE.HalfFloatType });
    const cam = new THREE.CubeCamera(0.3, 10000, rt);
    cam.position.set(x, y, z);
    return { rt, cam };
  }

  // Re-render both probes: twelve small passes over the scene, so only on load and when the sky or
  // the sun has moved a good step (updateProbes). The probed materials look at the sky env while
  // their own target is being written, or the render would read the texture it writes.
  renderProbes() {
    for (const m of this.probedMats) m.envMap = this.scene.environment;
    for (const p of Object.values(this.probes)) p.cam.update(this.renderer, this.scene);
    for (const m of this.probedMats) {
      const p = this.probes[m.userData.probe];
      m.envMap = p ? p.rt.texture : this.scene.environment;
      // a probe is a real render of the lit scene, so it needs no sky-intensity scaling
      m.envMapIntensity = m.userData.envK ?? (m.userData.env0 ??= m.envMapIntensity);
    }
  }
  updateProbes(t, az, el) {
    const key = `${Math.round(t * 10)}|${Math.round(az / 12)}|${Math.round(el / 4)}`;
    if (key === this.probeKey) return;
    this.probeKey = key;
    this.renderProbes();
  }

  // t: 0 golden hour, 0.5 sunset, 1 blue hour; az/el: shadow-casting sun
  update(t, time, az, el) {
    this.sky.material.uniforms.time.value = time;
    const moved = this.setSun(az, el);
    if (Math.abs(t - this.t) < 1e-4 && !moved) return null;
    this.t = t;
    const s = stateAt(t);
    this.applySky(this.sky, s, az, this.skyElev(t, el, s), t);
    this.sun.color.setRGB(...s.sunCol);
    this.sun.intensity = s.sun;
    this.scene.fog.color.setRGB(...s.fog);
    this.scene.fog.density = s.fogD;
    const env = this.envFor(t, az, el);
    if (env !== this.scene.environment || !this.litMats) this.refreshMaterials();
    this.scene.environment = env;
    this.scene.environmentIntensity = s.env;
    // With only scene.environment set, three writes the scene's intensity over every material's
    // envMapIntensity, so the per-material and per-style values would be inert. Each lit material
    // gets the map itself (same PMREM size, so no recompile) and its authored intensity times the
    // sky's; the styler reads envScale back to keep a style's env overrides in step.
    for (const m of this.litMats) {
      if (m.userData.env0 === undefined) m.userData.env0 = m.envMapIntensity;
      m.envMap = env;
      m.userData.envScale = s.env;
      m.envMapIntensity = (m.userData.envK ?? m.userData.env0) * s.env;
    }
    this.updateProbes(t, az, el);
    this.stars.material.opacity = THREE.MathUtils.smoothstep(t, 0.75, 1.0) * 0.85;
    return s;
  }
}
