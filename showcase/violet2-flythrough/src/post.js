import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { SMAAPass } from 'three/addons/postprocessing/SMAAPass.js';
import { N8AOPass } from 'n8ao';

// Display-referred finishing: split-tone grade, vignette and fine grain.
const FinalShader = {
  uniforms: { tDiffuse: { value: null }, uTime: { value: 0 }, uVignette: { value: 0.32 }, uGrain: { value: 0.022 }, uRes: { value: new THREE.Vector2(1, 1) } },
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: /* glsl */`
    uniform sampler2D tDiffuse; uniform float uTime, uVignette, uGrain; uniform vec2 uRes; varying vec2 vUv;
    float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
    void main(){
      vec3 c = texture2D(tDiffuse, vUv).rgb;
      float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
      c = mix(c, c * vec3(0.97, 0.985, 1.03), (1.0 - smoothstep(0.0, 0.4, l)) * 0.35);
      c = mix(c, c * vec3(1.045, 1.0, 0.93), smoothstep(0.3, 1.0, l) * 0.4);
      c = mix(c, c * c * (3.0 - 2.0 * c), 0.18);
      vec2 q = vUv - 0.5; q.x *= uRes.x / uRes.y;
      c *= mix(1.0, smoothstep(1.15, 0.25, length(q)), uVignette);
      c += (h(vUv * uRes + fract(uTime * 7.13) * 91.7) - 0.5) * uGrain;
      gl_FragColor = vec4(c, 1.0);
    }`,
};

export function createPost(renderer, scene, camera, { ao = true, aoQuality = 'Medium', halfRes = true, bloom = true, smaa = true } = {}) {
  const size = renderer.getDrawingBufferSize(new THREE.Vector2());
  const rt = new THREE.WebGLRenderTarget(size.x, size.y, { type: THREE.HalfFloatType });
  const composer = new EffectComposer(renderer, rt);
  let aoPass = null;
  if (ao) {
    aoPass = new N8AOPass(scene, camera, size.x, size.y);
    aoPass.setQualityMode(aoQuality);
    Object.assign(aoPass.configuration, { halfRes, aoRadius: 0.6, distanceFalloff: 1.0, intensity: 3.0, gammaCorrection: false, transparencyAware: false });
    // n8ao's multi-target shim returns the whole texture array from .texture, which r187's
    // setupRenderTarget reads as a single texture; n8ao itself only uses .textures on r162+.
    const t = aoPass.depthDownsampleTarget;
    if (t && Array.isArray(t.texture)) {
      Object.defineProperty(Object.getPrototypeOf(t), 'texture', { get() { return this.textures[0]; }, set(v) { this.textures[0] = v; }, configurable: true });
    }
    composer.addPass(aoPass);
  } else composer.addPass(new RenderPass(scene, camera));
  let bloomPass = null;
  if (bloom) {
    bloomPass = new UnrealBloomPass(new THREE.Vector2(size.x / 2, size.y / 2), 0.2, 0.42, 6.0);
    composer.addPass(bloomPass);
  }
  composer.addPass(new OutputPass());
  const final = new ShaderPass(FinalShader);
  composer.addPass(final);
  if (smaa) composer.addPass(new SMAAPass());
  return {
    composer, aoPass, bloomPass, final,
    setSize(w, h, dpr) {
      composer.setPixelRatio(dpr);
      composer.setSize(w, h);
      final.uniforms.uRes.value.set(w * dpr, h * dpr);
    },
  };
}
