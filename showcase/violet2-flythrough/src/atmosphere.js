import * as THREE from 'three';
import { Sky } from 'three/addons/objects/Sky.js';

// The sun direction is fixed so the (expensive) shadow map is rendered once per zone; time of
// day changes the sky, light colour/intensity, fog, exposure and the environment map.

const D2R = Math.PI / 180;
const dirFrom = (az, el, v = new THREE.Vector3()) => v.set(Math.sin(az * D2R) * Math.cos(el * D2R), Math.sin(el * D2R), Math.cos(az * D2R) * Math.cos(el * D2R));

const STATES = [
  { t: 0.0, elev: 17, turb: 5.0, ray: 1.6, mie: 0.0035, mieG: 0.8, gain: 0.82, sun: 4.3, sunCol: [1.0, 0.81, 0.6], fog: [0.84, 0.78, 0.71], fogD: 0.0009, exp: 0.7, env: 0.55, ground: [0.55, 0.5, 0.44], disc: 1 },
  { t: 0.5, elev: 3.0, turb: 6.0, ray: 2.4, mie: 0.0045, mieG: 0.82, gain: 0.95, sun: 2.2, sunCol: [1.0, 0.62, 0.4], fog: [0.84, 0.66, 0.55], fogD: 0.0011, exp: 0.88, env: 0.6, ground: [0.42, 0.34, 0.28], disc: 1 },
  { t: 1.0, elev: 0.4, turb: 2.0, ray: 4.2, mie: 0.002, mieG: 0.75, gain: 0.6, sun: 0.0, sunCol: [0.55, 0.6, 0.85], fog: [0.2, 0.23, 0.34], fogD: 0.0009, exp: 2.0, env: 1.4, ground: [0.06, 0.065, 0.085], disc: 0 },
];
const lerp = THREE.MathUtils.lerp;
function stateAt(t) {
  let a = STATES[0], b = STATES[1];
  if (t > STATES[1].t) { a = STATES[1]; b = STATES[2]; }
  const k = THREE.MathUtils.clamp((t - a.t) / (b.t - a.t), 0, 1);
  const o = {};
  for (const key of Object.keys(a)) o[key] = Array.isArray(a[key]) ? a[key].map((v, i) => lerp(v, b[key][i], k)) : lerp(a[key], b[key], k);
  return o;
}

function makeSky(scale) {
  const sky = new Sky();
  sky.scale.setScalar(scale);
  const m = sky.material;
  m.uniforms.uGain = { value: 1 };
  m.fragmentShader = 'uniform float uGain;\n' + m.fragmentShader
    .replace('gl_FragColor = vec4( texColor, 1.0 );', 'gl_FragColor = vec4( texColor * uGain, 1.0 );')
    .replace('( 760.0 * sundisc )', '( 25.0 * sundisc )');
  m.uniforms.cloudCoverage.value = 0.22;
  m.uniforms.cloudDensity.value = 0.32;
  m.uniforms.cloudElevation.value = 0.55;
  m.uniforms.cloudScale.value = 0.00016;
  sky.frustumCulled = false;
  return sky;
}

export class Atmosphere {
  constructor(renderer, scene, { shadowMapSize = 4096 } = {}) {
    this.renderer = renderer;
    this.scene = scene;
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
    this.envCache = new Map();

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

  applySky(sky, s, az, el) {
    const u = sky.material.uniforms;
    dirFrom(az, el, u.sunPosition.value);
    u.turbidity.value = s.turb; u.rayleigh.value = s.ray; u.mieCoefficient.value = s.mie; u.mieDirectionalG.value = s.mieG;
    u.uGain.value = s.gain;
    u.showSunDisc.value = s.disc;
  }

  envFor(t, az, el) {
    const q = Math.round(t * 20) / 20, qa = Math.round(az / 6) * 6, qe = Math.round(el);
    const key = `${q}|${qa}|${qe}`;
    if (this.envCache.has(key)) return this.envCache.get(key);
    const s = stateAt(q);
    this.applySky(this.envSky, s, qa, this.skyElev(q, qe, s));
    this.envGround.material.color.setRGB(...s.ground);
    const rt = this.pmrem.fromScene(this.envScene, 0, 0.1, 1000, { size: 256 });
    this.envCache.set(key, rt.texture);
    if (this.envCache.size > 8) {
      const first = this.envCache.keys().next().value;
      if (first !== key) { this.envCache.get(first).dispose(); this.envCache.delete(first); }
    }
    return rt.texture;
  }

  skyElev(t, el, s) { return THREE.MathUtils.lerp(el, Math.min(el, s.elev), THREE.MathUtils.smoothstep(t, 0.0, 0.5)); }

  // t: 0 golden hour, 0.5 sunset, 1 blue hour; az/el: shadow-casting sun
  update(t, time, az, el) {
    this.sky.material.uniforms.time.value = time;
    const moved = this.setSun(az, el);
    if (Math.abs(t - this.t) < 1e-4 && !moved) return null;
    this.t = t;
    const s = stateAt(t);
    this.applySky(this.sky, s, az, this.skyElev(t, el, s));
    this.sun.color.setRGB(...s.sunCol);
    this.sun.intensity = s.sun;
    this.scene.fog.color.setRGB(...s.fog);
    this.scene.fog.density = s.fogD;
    this.scene.environment = this.envFor(t, az, el);
    this.scene.environmentIntensity = s.env;
    this.stars.material.opacity = THREE.MathUtils.smoothstep(t, 0.75, 1.0) * 0.85;
    return s;
  }
}
