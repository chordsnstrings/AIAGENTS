import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { SMAAPass } from 'three/addons/postprocessing/SMAAPass.js';
import { N8AOPass } from 'n8ao';
import { VolumetricPass } from './volumetric.js';

// The chain is two full-resolution passes: the scene (through N8AO's composite, or a plain
// RenderPass) and one finish pass, plus SMAA where the pixel ratio is low enough for it to
// matter. The finish pass adds the volumetric march and the bloom in linear HDR, then tone-maps,
// encodes and grades in one shader; the stock OutputPass, FinalShader, bloom blend and
// volumetric composite each cost a full read and write of the frame for the same result.
const FinishShader = {
  uniforms: {
    tDiffuse: { value: null }, tVol: { value: null }, tBloom: { value: null },
    uVol: { value: 0 }, uBloom: { value: 0 }, uSunCol: { value: new THREE.Color() }, uAmbCol: { value: new THREE.Color() },
    toneMappingExposure: { value: 1 },
    uTime: { value: 0 }, uVignette: { value: 0.32 }, uGrain: { value: 0.022 }, uRes: { value: new THREE.Vector2(1, 1) },
  },
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: /* glsl */`
    uniform sampler2D tDiffuse, tVol, tBloom; uniform float uVol, uBloom; uniform vec3 uSunCol, uAmbCol;
    uniform float uTime, uVignette, uGrain; uniform vec2 uRes; varying vec2 vUv;
    // sRGBTransferOETF comes with every ShaderMaterial's prefix; the tone-mapping functions only
    // when rendering to screen, so they are included here and the material is not toneMapped
    #include <tonemapping_pars_fragment>
    float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
    void main(){
      vec3 c = texture2D(tDiffuse, vUv).rgb;
      vec3 v = texture2D(tVol, vUv).rgb;
      c += (uSunCol * min(v.r, 6.0) + uAmbCol * v.g) * uVol;
      c += texture2D(tBloom, vUv).rgb * uBloom;
      c = ACESFilmicToneMapping(c);
      c = sRGBTransferOETF(vec4(c, 1.0)).rgb;
      // display-referred finishing: split-tone grade, vignette and fine grain
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

class FinishPass extends ShaderPass {
  constructor(volPass, bloomPass) {
    super(FinishShader);
    this.material.toneMapped = false;
    this.volPass = volPass; this.bloomPass = bloomPass;
    if (volPass) { this.uniforms.tVol.value = volPass.texture; this.uniforms.uSunCol.value = volPass.sunCol; this.uniforms.uAmbCol.value = volPass.ambCol; }
    if (bloomPass) this.uniforms.tBloom.value = bloomPass.texture;
  }
  render(renderer, writeBuffer, readBuffer, deltaTime, maskActive) {
    const u = this.uniforms;
    u.toneMappingExposure.value = renderer.toneMappingExposure;
    u.uVol.value = this.volPass && this.volPass.enabled && this.volPass.ready ? 1 : 0;
    u.uBloom.value = this.bloomPass && this.bloomPass.enabled ? 1 : 0;
    super.render(renderer, writeBuffer, readBuffer, deltaTime, maskActive);
  }
}

// UnrealBloomPass without its last step, the additive blend over the input (a full-resolution
// pass of its own); the finish pass samples the composited mips instead. The body up to that
// point is r187's, kept verbatim so the look does not move.
class BloomPass extends UnrealBloomPass {
  get texture() { return this.renderTargetsHorizontal[0].texture; }
  render(renderer, writeBuffer, readBuffer) {
    renderer.getClearColor(this._oldClearColor);
    this._oldClearAlpha = renderer.getClearAlpha();
    const oldAutoClear = renderer.autoClear;
    renderer.autoClear = false;
    renderer.setClearColor(this.clearColor, 0);
    this.highPassUniforms['tDiffuse'].value = readBuffer.texture;
    this.highPassUniforms['luminosityThreshold'].value = this.threshold;
    this._fsQuad.material = this.materialHighPassFilter;
    renderer.setRenderTarget(this.renderTargetBright);
    renderer.clear();
    this._fsQuad.render(renderer);
    let input = this.renderTargetBright;
    for (let i = 0; i < this.nMips; i++) {
      const blur = this.separableBlurMaterials[i];
      this._fsQuad.material = blur;
      blur.uniforms['colorTexture'].value = input.texture;
      blur.uniforms['direction'].value = UnrealBloomPass.BlurDirectionX;
      renderer.setRenderTarget(this.renderTargetsHorizontal[i]);
      renderer.clear();
      this._fsQuad.render(renderer);
      blur.uniforms['colorTexture'].value = this.renderTargetsHorizontal[i].texture;
      blur.uniforms['direction'].value = UnrealBloomPass.BlurDirectionY;
      renderer.setRenderTarget(this.renderTargetsVertical[i]);
      renderer.clear();
      this._fsQuad.render(renderer);
      input = this.renderTargetsVertical[i];
    }
    this._fsQuad.material = this.compositeMaterial;
    this.compositeMaterial.uniforms['bloomStrength'].value = this.strength;
    this.compositeMaterial.uniforms['bloomRadius'].value = this.radius;
    this.compositeMaterial.uniforms['bloomTintColors'].value = this.bloomTintColors;
    renderer.setRenderTarget(this.renderTargetsHorizontal[0]);
    renderer.clear();
    this._fsQuad.render(renderer);
    renderer.setClearColor(this._oldClearColor, this._oldClearAlpha);
    renderer.autoClear = oldAutoClear;
  }
}

// SMAA earns its three passes while device pixels are large; from this ratio up the pixels are
// small enough that it only costs.
const SMAA_MAX_DPR = 1.75;

export function createPost(renderer, scene, camera, { ao = true, aoQuality = 'Medium', halfRes = true, bloom = true, smaa = true, vol = true, aoZones = false, sun = null, volSteps = 28 } = {}) {
  // without renderable half-float colour buffers every HDR pass would be framebuffer-incomplete
  // and the canvas black; fall back to 8-bit targets and the passes that survive them
  const hdr = renderer.extensions.has('EXT_color_buffer_float') || renderer.extensions.has('EXT_color_buffer_half_float');
  if (!hdr) { ao = false; bloom = false; vol = false; aoZones = false; }
  const size = renderer.getDrawingBufferSize(new THREE.Vector2());
  // the composer target needs depth only where a RenderPass draws the scene into it
  const rt = new THREE.WebGLRenderTarget(size.x, size.y, { type: hdr ? THREE.HalfFloatType : THREE.UnsignedByteType, depthBuffer: !ao || aoZones });
  const composer = new EffectComposer(renderer, rt);
  let aoPass = null, renderPass = null;
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
  }
  if (!ao || aoZones) {
    renderPass = new RenderPass(scene, camera);
    renderPass.enabled = !aoPass;
    composer.addPass(renderPass);
  }
  let volPass = null;
  if (vol && aoPass && sun) {
    volPass = new VolumetricPass({ camera, sun, getDepth: () => aoPass.beautyRenderTarget && aoPass.beautyRenderTarget.depthTexture, steps: volSteps });
    composer.addPass(volPass);
  }
  let bloomPass = null;
  if (bloom) {
    bloomPass = new BloomPass(new THREE.Vector2(size.x / 2, size.y / 2), 0.2, 0.32, 9.0);
    composer.addPass(bloomPass);
  }
  const final = new FinishPass(volPass, bloomPass);
  composer.addPass(final);
  const smaaPass = smaa ? new SMAAPass() : null;
  if (smaaPass) composer.addPass(smaaPass);
  return {
    composer, aoPass, bloomPass, final, volPass, hdr,
    setSize(w, h, dpr) {
      composer.setPixelRatio(dpr);
      composer.setSize(w, h);
      final.uniforms.uRes.value.set(w * dpr, h * dpr);
      if (smaaPass) smaaPass.enabled = dpr < SMAA_MAX_DPR;
    },
    // AO per zone (phone tier): the plain RenderPass stands in where AO is off; the volumetric
    // march reads AO's depth, so it rests at the same time
    setAO(on) {
      if (!aoPass || !renderPass) return;
      aoPass.enabled = on; renderPass.enabled = !on;
      if (volPass) volPass.enabled = on;
    },
  };
}
