# Hand-off from the performance pass

Changes the performance findings need in files this pass did not own. Each item names the
finding, the file, and the exact change; the measurements behind them are in the findings record.

## src/atmosphere.js — dusk-regeneration, sky-ratio-nan, mobile-gpu-memory, shadow-swing

1. **Coarser environment key.** `PMREMGenerator._setSize` clamps to `MIN_SIZE = 256`, so `{ size: 128 }`
   changes nothing: every env costs 4.2 MB and about 38 M texture samples. Make the key coarse enough
   that a read-through builds about a dozen envs instead of 45 (290 while scrubbing):
   `envFor(t, az, el)`: `q = Math.round(t * 10) / 10`, `qa = Math.round((az + 55) / 36.5)` (three bins
   over the −55° → −128° swing), `qe = Math.round(el / 4) * 4`. On the `low` tier (pass an option from
   `main.js`, e.g. `new Atmosphere(renderer, scene, { shadowMapSize, envBins: 'coarse' })`) use
   `t` in 0.2 steps and two azimuth bins. Build `BAKE_KEY` with the same key function instead of the
   literal `'0|-54|18'`, and use the same key for `skyLevel`.
2. **LRU, not FIFO.** On a cache hit `delete` then `set` the key so it moves to the back; cap at 24
   entries (8 on `low`); dispose the evicted target's texture (the env-cache-leak fix already keeps
   the render target to dispose).
3. **Prebuild during idle.** Add `prebuild(list)` taking `[t, az, el]` triples, and build at most one env
   per idle period while the page is not scrolling: `requestIdleCallback` with a `setTimeout(…, 120)`
   fallback, skipping while `performance.now() < awakeUntil` (expose a `busy()` callback or pass the
   check in). `main.js` should call it after `ui.ready()` with the sun schedule sampled at p 0.72 → 1.0
   in steps of 0.01 — the schedule lines (`todTarget`, `swing`, `sunEl`) belong to the route pass, so
   the cleanest form is a `sunAt(p)` helper exported from that hunk and reused by `update()`.
4. **Guard the read-back** (`measure` / `skyRatio`): keep a level only if all three channels are finite
   and > 1e-6, otherwise leave the key unmeasured; clamp each ratio in `skyRatio()` to [0, 4]; skip
   `measure()` while `renderer.getContext().isContextLost()`; while a key is pending, return the last
   measured ratio rather than the fitted curve, so interiors do not jump when a read-back lands.
   `gi.set` now sanitises and clamps every weight (`src/gi.js`), which contains the damage but does not
   remove the cause.
5. **Shadow extents.** The map is now 2048 on every tier (`src/tiers.js`), which at `house: 18` gives
   1.76 cm per texel. Tightening `house` to about 12–14 m and `street` to 30–40 m doubles the texel
   density, but fragments outside the shadow frustum render fully lit, so check the terrace frames
   (p 0.86–0.90) and the street frames (p 0.24–0.33) for a cut-off line before and after.

## src/look.js — dust-dead-pixels

The motes are now smaller (`uSize` 18 → 9), sparser (1.5 per m³, 0.8 on `low`) and energy-conserving
(a near sprite grows but does not brighten; `src/volumetric.js`). Their brightness constants are yours:
propose `dustSun: 0.05` (was 0.4; at interior exposure the old value clipped to white) and
`dustAmbient: 0` (unlit motes vanish; 0.003 if a hint of them in shadow is wanted).

## src/materials.js (below the SETS block) — draw-order-overdraw, sheer-glass-sorting

- `M.glass` and `M.glassLight`: `side: THREE.FrontSide`. The panes are thin boxes, so DoubleSide drew
  each one twice (back faces then front faces). With one layer the Fresnel alpha needs retuning to keep
  the same coverage: two layers at `[0.06, 0.75]` composite to about `[0.12, 0.94]`; start there and
  judge the glazing in p 0.46 and p 0.52.
- `M.sheer`: `forceSinglePass: true` (the pleated panel is the one place a single pass of a DoubleSide
  material pays). For the static sort order the hero meshes now carry `renderOrder` sheer 1, glass 2
  (`src/builder.js` `meshes(…, { order })`, set in `main.js`); it only works fully if `M.sheer` gets
  `depthWrite: true`, so glass behind a curtain is depth-rejected from inside. Caveat: the curtains then
  appear in the depth buffer N8AO and the volumetric march read.

## style.css — backdrop-filter-cost

`main.js` adds `body.lowfx` on the `low` tier. Give the glass panels a pre-darkened solid fill there,
e.g. `body.lowfx .card, body.lowfx .tod, body.lowfx .styles, body.lowfx #pin span, body.lowfx #toast
{ backdrop-filter: none; -webkit-backdrop-filter: none; background: rgba(28, 22, 18, .82); }`.

## src/ui.js — lazy-style-sets (optional)

`main.js` builds the other furniture sets when a style chip is hovered or focused, and finds the chips
with `document.querySelectorAll('#styles button')` in `Object.keys(STYLES)` order, which is the order
`initUI` appends them. An `onStyleIntent(key)` callback on `initUI` (fired on `pointerenter` and
`focus`) would remove that coupling.

## src/house.js — phone-tier-ao-aa (optional)

The neighbours' `rail` alpha cards shimmer on phones even with SMAA on. Instanced box balusters, or a
fade-out by distance, would resolve them.

## src/styles.js — mobile-gpu-memory (optional)

Every visited style keeps its extra sets and their clones for the session. When releasing a style,
dispose the entries of the styler's `clones` map that belong to it (those are the textures actually
uploaded; disposing `T[name][s]` alone frees nothing) and drop the set from `T`.

## README.md structure table (outside the performance section)

Add a row for `src/tiers.js` (pixel budgets, GPU classification, adaptive scaler); the table also
lacks `proctex.js`, `vegetation.js` and `look.js`.

## Skill references and scripts

- `references/template-architecture.md` and `performance-and-publishing.md` describe the old chain:
  update for `src/tiers.js` (pixel budgets, GPU classes, rung scaler), the two-pass post chain
  (`FinishPass`, `BloomPass`, `VolumetricPass` without a composite), the palm LOD pairs in
  `community.js`, `SETS` of 18 (no `stone`), `INTERIOR_SETS` streaming, and `assets/tex/512/`.
- `scripts/textures.py`: add a `--downscale 512` mode with the logic used here (Lanczos to 512,
  WebP quality 82 method 6, files already ≤ 512 copied) so the 512 tier regenerates with the sets.
- KTX2/Basis was not done: no encoder (`toktx`, `basisu`) is installed here, and the transcoder would
  add 245 KB gzipped to the page.
