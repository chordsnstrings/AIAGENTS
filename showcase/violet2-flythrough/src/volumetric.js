import * as THREE from 'three';
import { Pass, FullScreenQuad } from 'three/addons/postprocessing/Pass.js';

// Volumetric light. A half-resolution raymarch through the sun's (static) shadow map gives
// physically placed shafts - through window glazing, pergola slats, palm fronds - and a
// height-weighted haze, then a separable blur. The composite happens in the finish pass
// (post.js) together with bloom, in linear light before tone mapping.

const VERT = 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }';

const MARCH = /* glsl */`
precision highp sampler2DShadow;
uniform sampler2D tDepth;
uniform sampler2DShadow tShadow;
uniform mat4 uProjInv, uViewInv, uShadowMatrix;
uniform vec3 uCamPos, uSunDir;
uniform float uDensity, uMaxDist, uG, uJitter, uHeightK, uHeightScale, uDensityIn, uSunIn, uSunOut, uAmbIn, uAmbOut;
uniform int uSteps;
uniform vec3 uBoxMin, uBoxMax, uCutMin, uCutMax;
varying vec2 vUv;
float ign(vec2 p){ return fract(52.9829189 * fract(dot(p, vec2(0.06711056, 0.00583715)))); }
float hg(float c, float g){ float g2 = g * g; return (1.0 - g2) / pow(max(1.0 + g2 - 2.0 * g * c, 1e-4), 1.5); }
void main(){
  float d = texture2D(tDepth, vUv).x;
  vec4 v = uProjInv * vec4(vUv * 2.0 - 1.0, d * 2.0 - 1.0, 1.0);
  v.xyz /= v.w;
  vec3 wp = (uViewInv * vec4(v.xyz, 1.0)).xyz;
  vec3 rd = wp - uCamPos;
  float dist = length(rd);
  rd /= max(dist, 1e-4);
  float L = d >= 0.99999 ? uMaxDist : min(dist, uMaxDist);
  float st = L / float(uSteps);
  float t = st * fract(ign(gl_FragCoord.xy) + uJitter);
  float sun = 0.0, amb = 0.0, tr = 1.0;
  // STEPS is the compile-time ceiling; uSteps lowers the count where the air is thin
  for (int i = 0; i < STEPS; i++) {
    if (i >= uSteps) break;
    vec3 p = uCamPos + rd * t;
    vec4 sc = uShadowMatrix * vec4(p, 1.0);
    float lit = 1.0;
    if (sc.x > 0.0 && sc.x < 1.0 && sc.y > 0.0 && sc.y < 1.0 && sc.z < 1.0) lit = texture(tShadow, vec3(sc.xy, sc.z - 0.0004));
    bool inside = all(greaterThan(p, uBoxMin)) && all(lessThan(p, uBoxMax)) && !(all(greaterThan(p, uCutMin)) && all(lessThan(p, uCutMax)));
    float a = (inside ? uDensityIn : uDensity * (1.0 + uHeightK * exp(-max(p.y, 0.0) / uHeightScale))) * st;
    sun += lit * a * tr * (inside ? uSunIn : uSunOut);
    amb += a * tr * (inside ? uAmbIn : uAmbOut);
    tr *= exp(-a);
    t += st;
  }
  gl_FragColor = vec4(sun * hg(dot(rd, uSunDir), uG), amb, 1.0 - tr, 1.0);
}`;

const BLUR = /* glsl */`
uniform sampler2D tIn; uniform vec2 uDir; varying vec2 vUv;
void main(){
  vec4 s = texture2D(tIn, vUv) * 0.2270270;
  s += (texture2D(tIn, vUv + uDir * 1.3846154) + texture2D(tIn, vUv - uDir * 1.3846154)) * 0.3162162;
  s += (texture2D(tIn, vUv + uDir * 3.2307692) + texture2D(tIn, vUv - uDir * 3.2307692)) * 0.0702703;
  gl_FragColor = s;
}`;

// Writes (sun, ambient, 1 - transmittance) into its own half-resolution target and leaves the
// composer's buffers alone; `texture`, `sunCol`, `ambCol` and `ready` are what the finish pass
// reads. `ready` is false until both the scene depth and the shadow map exist.
export class VolumetricPass extends Pass {
  constructor({ camera, sun, getDepth, steps = 28, scale = 0.5 }) {
    super();
    this.needsSwap = false;
    this.camera = camera; this.sun = sun; this.getDepth = getDepth; this.scale = scale;
    const opts = { type: THREE.HalfFloatType, depthBuffer: false };
    this.rtA = new THREE.WebGLRenderTarget(1, 1, opts);
    this.rtB = new THREE.WebGLRenderTarget(1, 1, opts);
    this.march = new FullScreenQuad(new THREE.ShaderMaterial({
      defines: { STEPS: steps }, vertexShader: VERT, fragmentShader: MARCH, depthTest: false, depthWrite: false,
      uniforms: {
        tDepth: { value: null }, tShadow: { value: null }, uProjInv: { value: new THREE.Matrix4() }, uViewInv: { value: new THREE.Matrix4() },
        uShadowMatrix: { value: new THREE.Matrix4() }, uCamPos: { value: new THREE.Vector3() }, uSunDir: { value: new THREE.Vector3(0, 1, 0) },
        uDensity: { value: 0.01 }, uMaxDist: { value: 60 }, uG: { value: 0.6 }, uJitter: { value: 0 }, uHeightK: { value: 2 }, uHeightScale: { value: 4 },
        uDensityIn: { value: 0.03 }, uSunIn: { value: 1 }, uSunOut: { value: 0.07 }, uAmbIn: { value: 1 }, uAmbOut: { value: 1 }, uSteps: { value: steps },
        uBoxMin: { value: new THREE.Vector3(0.1, 0.25, -14.85) }, uBoxMax: { value: new THREE.Vector3(6.0, 9.7, -3.55) },
        // the open roof terrace sits inside that box but is outdoor air: room-dense dust there,
        // looking into a low sun, washed half the sunset frame white (main.js inHouseBox cuts it too)
        uCutMin: { value: new THREE.Vector3(0.1, 6.8, -14.85) }, uCutMax: { value: new THREE.Vector3(6.0, 9.7, -11.2) },
      },
    }));
    this.blurQ = new FullScreenQuad(new THREE.ShaderMaterial({ vertexShader: VERT, fragmentShader: BLUR, depthTest: false, depthWrite: false, uniforms: { tIn: { value: null }, uDir: { value: new THREE.Vector2() } } }));
    this.u = this.march.material.uniforms;
    this.steps = steps;
    this.sunCol = new THREE.Color();
    this.ambCol = new THREE.Color();
    this.ready = false;
  }

  get texture() { return this.rtA.texture; }

  setSize(w, h) {
    const sw = Math.max(1, Math.round(w * this.scale)), sh = Math.max(1, Math.round(h * this.scale));
    this.rtA.setSize(sw, sh); this.rtB.setSize(sw, sh);
  }

  render(renderer) {
    const depth = this.getDepth(), shadow = this.sun.shadow.map && this.sun.shadow.map.depthTexture;
    const u = this.u;
    this.ready = !!(depth && shadow);
    if (!this.ready) return;
    u.tDepth.value = depth; u.tShadow.value = shadow;
    u.uProjInv.value.copy(this.camera.projectionMatrixInverse);
    u.uViewInv.value.copy(this.camera.matrixWorld);
    u.uShadowMatrix.value.copy(this.sun.shadow.matrix);
    u.uCamPos.value.setFromMatrixPosition(this.camera.matrixWorld);
    u.uSunDir.value.copy(this.sun.position).sub(this.sun.target.position).normalize();
    renderer.setRenderTarget(this.rtA); this.march.render(renderer);
    const b = this.blurQ.material.uniforms;
    b.tIn.value = this.rtA.texture; b.uDir.value.set(1 / this.rtA.width, 0);
    renderer.setRenderTarget(this.rtB); this.blurQ.render(renderer);
    b.tIn.value = this.rtB.texture; b.uDir.value.set(0, 1 / this.rtA.height);
    renderer.setRenderTarget(this.rtA); this.blurQ.render(renderer);
  }

  dispose() {
    this.rtA.dispose(); this.rtB.dispose();
    this.march.dispose(); this.blurQ.dispose();
  }
}

// Dust motes: bright only where the shadow map says the sun reaches them. A mote near the lens
// is defocused, not bigger and brighter: the sprite grows but its energy stays put, as bokeh
// does, so no mote ever reads as a blown white dot on the bedding.
export function makeDust(boxes, perCubic = 5, seed = 9) {
  let s = seed;
  const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  const pos = [], sd = [];
  for (const [x0, x1, y0, y1, d0, d1] of boxes) {
    const n = Math.round((x1 - x0) * (y1 - y0) * (d1 - d0) * perCubic);
    for (let i = 0; i < n; i++) { pos.push(x0 + r() * (x1 - x0), y0 + r() * (y1 - y0), -(d0 + r() * (d1 - d0))); sd.push(r()); }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('aSeed', new THREE.Float32BufferAttribute(sd, 1));
  const mat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    uniforms: { uTime: { value: 0 }, uShadow: { value: null }, uShadowMatrix: { value: new THREE.Matrix4() }, uSunCol: { value: new THREE.Color() }, uAmb: { value: new THREE.Color() }, uSize: { value: 9 } },
    vertexShader: /* glsl */`
      precision highp sampler2DShadow;
      attribute float aSeed; uniform float uTime, uSize; uniform mat4 uShadowMatrix; uniform sampler2DShadow uShadow; uniform vec3 uSunCol, uAmb;
      varying vec3 vCol; varying float vA;
      void main(){
        vec3 p = position + vec3(sin(uTime * 0.13 + aSeed * 61.0), sin(uTime * 0.09 + aSeed * 23.0) * 0.7, cos(uTime * 0.11 + aSeed * 37.0)) * 0.22;
        vec4 sc = uShadowMatrix * vec4(p, 1.0);
        float lit = 0.0;
        if (sc.x > 0.0 && sc.x < 1.0 && sc.y > 0.0 && sc.y < 1.0 && sc.z < 1.0) lit = texture(uShadow, vec3(sc.xy, sc.z - 0.0005));
        vCol = uSunCol * lit + uAmb;
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        float sz = uSize * (0.6 + aSeed * 0.8) / max(-mv.z, 0.1);
        gl_PointSize = sz;
        vA = smoothstep(0.15, 0.7, -mv.z) * (1.0 - smoothstep(6.0, 12.0, -mv.z)) * min(1.0, 36.0 / (sz * sz));
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: /* glsl */`
      varying vec3 vCol; varying float vA;
      void main(){ vec2 q = gl_PointCoord - 0.5; float a = exp(-dot(q, q) * 22.0) * vA; gl_FragColor = vec4(vCol * a, a); }`,
  });
  const pts = new THREE.Points(g, mat);
  pts.frustumCulled = false;
  return pts;
}

// Soft light cone below a lamp head (additive, view-dependent edge falloff). The cones are one
// InstancedMesh, and a ShaderMaterial must apply instanceMatrix itself: without it every cone
// drew at the mesh's origin, stacked into one blazing cone at the hero's front corner.
export function beamMaterial(color = 0xffcf96) {
  return new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
    uniforms: { uColor: { value: new THREE.Color(color) }, uOpacity: { value: 0 } },
    vertexShader: /* glsl */`
      varying float vH; varying vec3 vN, vV;
      void main(){
        vH = uv.y;
        vec4 lp = vec4(position, 1.0); vec3 ln = normal;
        #ifdef USE_INSTANCING
          lp = instanceMatrix * lp; ln = mat3(instanceMatrix) * ln;
        #endif
        vec4 mv = modelViewMatrix * lp;
        vN = normalize(normalMatrix * ln); vV = normalize(-mv.xyz);
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: /* glsl */`
      uniform vec3 uColor; uniform float uOpacity; varying float vH; varying vec3 vN, vV;
      void main(){
        float edge = pow(abs(dot(normalize(vN), normalize(vV))), 2.0);
        float a = uOpacity * edge * pow(vH, 1.4) * (1.0 - smoothstep(0.9, 1.0, vH));
        gl_FragColor = vec4(uColor * a, a);
      }`,
  });
}
