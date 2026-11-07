// Quality tiers describe devices, not the house. A tier is a pixel budget (device pixels the
// post chain may process per frame) plus the passes that run; the pixel ratio follows from the
// budget and the canvas size instead of a DPR cap, so a 13-inch retina laptop and a 4K monitor
// land on comparable frame costs. The budget feeds a rung ladder the adaptive scaler walks.

export const TIERS = {
  high: { budget: 3.7e6, shadow: 2048, ao: true, aoQuality: 'Medium', halfRes: true, smaa: true, bloom: true, vol: true, volSteps: 28 },
  mid: { budget: 2.1e6, shadow: 2048, ao: true, aoQuality: 'Performance', halfRes: true, smaa: true, bloom: true, vol: true, volSteps: 20 },
  // phones: AO only where it grounds furniture (house and street zones), no volumetric march
  low: { budget: 0.6e6, shadow: 2048, ao: true, aoQuality: 'Performance', halfRes: true, smaa: true, bloom: true, vol: false, aoZones: true },
};

// The GPU name is the only signal that separates an integrated laptop GPU from a discrete one.
// Chrome and Firefox expose it through WEBGL_debug_renderer_info; Safari masks it as 'Apple GPU',
// so there the screen decides. Unknown desktops start on mid: the scaler can climb from there.
export function classifyGPU(gl) {
  let r = '';
  try {
    const ext = gl.getExtension('WEBGL_debug_renderer_info');
    r = String(gl.getParameter(ext ? ext.UNMASKED_RENDERER_WEBGL : gl.RENDERER) || '');
  } catch (e) { /* masked */ }
  const coarse = matchMedia('(pointer: coarse)').matches;
  const phone = coarse && Math.min(screen.width, screen.height) < 700;
  if (/SwiftShader|llvmpipe|Software/i.test(r)) return 'low';
  if (/Mali|PowerVR|Xclipse|Adreno(?: \(TM\))? [1-6]\d\d\b/i.test(r)) return 'low';
  if (/Adreno/i.test(r)) return 'mid';
  if (/Apple GPU/.test(r)) return phone ? 'low' : 'mid';
  if (/Apple M[12]\b(?!\s*(Pro|Max|Ultra))/.test(r)) return 'mid';
  if (/Apple M\d/.test(r)) return 'high';
  if (/GeForce|RTX|GTX|Quadro|Radeon (?:\(TM\) )?(?:RX|Pro)\b|Arc\s*[AB]\d/i.test(r)) return 'high';
  if (/Intel|Iris|UHD Graphics|HD Graphics|Radeon(?: \(TM\))? Graphics|Radeon \d{3}M|Vega/i.test(r)) return 'mid';
  if (phone || (navigator.deviceMemory || 8) <= 4) return 'low';
  return 'mid';
}

export function detectTier(gl, forced) {
  if (forced && Object.hasOwn(TIERS, forced)) return forced;
  return classifyGPU(gl);
}

// Largest pixel ratio that keeps w*h CSS pixels within the budget, never above the device's own.
export function pixelRatioFor(budget, w, h) {
  return Math.min(devicePixelRatio || 1, Math.sqrt(budget / Math.max(1, w * h)));
}

// Walks a ladder of scale factors on the budget's pixel ratio. Frame time comes from the GPU
// timer where the browser offers one, else from the rAF interval. Down one rung after two
// 30-frame windows above 19 ms; up one rung (as a probe, reverted if the next window exceeds
// 18 ms) after 3 s under the ceiling, at most one change every 2 s. A 60 Hz interval can never
// read under 13 ms, which is why the step up is a probe rather than a threshold.
export class AdaptiveScale {
  constructor(renderer, { ladder = [0.6, 0.75, 0.9, 1.0, 1.15, 1.3], window = 30 } = {}) {
    this.ladder = ladder; this.i = ladder.indexOf(1.0); this.window = window;
    this.gl = renderer.getContext();
    this.ext = this.gl.getExtension('EXT_disjoint_timer_query_webgl2');
    this.query = null; this.open = false; this.gpuMs = null;
    this.n = 0; this.acc = 0; this.hot = 0; this.coolSince = null;
    this.start = performance.now(); this.lastChange = this.start; this.probe = false; this.failedAt = -Infinity;
  }
  get scale() { return this.ladder[this.i]; }
  // bracket the composer render so the GPU timer measures only what resolution scales
  begin() {
    if (!this.ext || this.query) return;
    this.query = this.gl.createQuery();
    this.gl.beginQuery(this.ext.TIME_ELAPSED_EXT, this.query);
    this.open = true;
  }
  end() {
    if (!this.open) return;
    this.gl.endQuery(this.ext.TIME_ELAPSED_EXT);
    this.open = false;
  }
  poll() {
    if (!this.query || this.open) return;
    const gl = this.gl;
    if (!gl.getQueryParameter(this.query, gl.QUERY_RESULT_AVAILABLE)) return;
    if (!gl.getParameter(this.ext.GPU_DISJOINT_EXT)) this.gpuMs = gl.getQueryParameter(this.query, gl.QUERY_RESULT) / 1e6;
    gl.deleteQuery(this.query);
    this.query = null;
  }
  // one rendered frame; returns true when the rung changed and targets must be resized
  frame(dtMs, now, settled) {
    this.poll();
    if (now - this.start < 3000) return false; // boot uploads and compiles are not frame cost
    this.acc += this.ext && this.gpuMs !== null ? this.gpuMs : dtMs;
    if (++this.n < this.window) return false;
    const avg = this.acc / this.n;
    this.n = 0; this.acc = 0;
    const top = this.ladder.length - 1;
    if (this.probe) {
      this.probe = false;
      if (avg > 18 && this.i > 0) { this.i--; this.failedAt = now; this.lastChange = now; return true; }
    }
    if (avg > 19) {
      this.coolSince = null;
      if (++this.hot >= 2 && this.i > 0 && now - this.lastChange >= 2000) {
        this.i--; this.hot = 0; this.lastChange = now;
        return true;
      }
      return false;
    }
    this.hot = 0;
    const ceiling = this.ext && this.gpuMs !== null ? 13 : 17.5;
    if (avg >= ceiling) { this.coolSince = null; return false; }
    if (this.coolSince === null) this.coolSince = now;
    if (settled && this.i < top && now - this.coolSince >= 3000 && now - this.lastChange >= 2000 && now - this.failedAt >= 10000) {
      this.i++; this.probe = true; this.coolSince = null; this.lastChange = now;
      return true;
    }
    return false;
  }
}
