# Lighting and the look: how the image is made and how to recalibrate it

The lighting half of the template at `violet2-flythrough/`: everything between the geometry and the pixels, for
a session adapting it to a new property. Read `decisions-and-pitfalls.md` first; it holds the "why" of the big
choices and is only cited here. Functions are named rather than line-numbered (the lines moved in every fix
pass); `grep -n` finds them.

## Contents

1 The pipeline at a glance · 2 `atmosphere.js` · 3 `post.js` · 4 `volumetric.js` · 5 `materials.js` · 6
`styles.js` · 7 `gi.js` and `bake-gi.mjs` · 8 the exposure model in `main.js`, the night lights · 9
`softgoods.js` and decor helpers · 10 constants that must agree · 11 calibration procedure

## 1. The pipeline at a glance

Light reaches a pixel from four places; knowing which one is wrong is most of calibration:

| Source | Outdoors | Indoors |
| --- | --- | --- |
| Direct sun | `DirectionalLight` + one PCF shadow map per zone, 2048² on every tier (`atmosphere.js`) | same, through the openings |
| Diffuse ambient | PMREM of the sky, assigned per material with the authored intensity × the sky's (`envK × envScale`) | baked volume replaces the env diffuse where `inside` > 0 (`GI_FRAG`) |
| Specular | env map; the glazing mirrors two local probes instead | env map dimmed by the probe's open-sky fraction and tinted by the room's bounce |
| Lamps | emissive heads, the baked lamp irradiance map on the ground, `M.beam` cones | baked `N` component + the night point-light pool + four fixed `PointLight`s + emissive fixtures |

Per frame, `update()` in `main.js` drives, in order: camera, `tod` and the sun (`sunAt`), `atmo.update()`,
shadow zone, the exposure model (`inside`, `lookOut`, `shade`), bloom threshold, AO radius, the glow list,
the lamp pool, the lamp-map colour, `gi.set()`, dust, volumetric uniforms, the fixed point lights. The
composer then runs N8AO (beauty + AO) → the volumetric march (its own half-size target) → the bloom mips →
the finish pass (march and bloom added in linear light, ACES, sRGB, grade) → SMAA while the pixel ratio is
under 1.75. Rendering is on demand; `?p=<progress>` renders one still.

## 2. `src/atmosphere.js`

### `STATES` and `stateAt()`

Three keyframes over `t` (0 golden hour, 0.5 sunset, 1 blue hour) in `STATES`, linearly interpolated field
by field in `stateAt(t)`:

| Field | t=0 | t=0.5 | t=1 | Drives |
| --- | --- | --- | --- | --- |
| `elev` | 17 | 3.0 | 0.4 | the *sky's* sun elevation cap, via `skyElev()` |
| `turb`, `ray`, `mie`, `mieG` | 8.0, 1.1, 0.004, 0.72 | 7.5, 2.0, 0.004, 0.76 | 2.0, 4.2, 0.002, 0.75 | Preetham uniforms: a dust-hazed Gulf sky, little Rayleigh |
| `gain` | 0.82 | 0.95 | 0.6 | `uGain`, a plain multiplier on the Preetham colour |
| `sun`, `sunCol` | 4.3, (1, 0.81, 0.6) | 2.2, (1, 0.62, 0.4) | 0, (0.55, 0.6, 0.85) | `DirectionalLight` |
| `fog`, `fogD` | (0.84, 0.78, 0.71), 0.0009 | (0.84, 0.66, 0.55), 0.0011 | `TWILIGHT.horizon`, 0.0011 | `FogExp2` |
| `exp` | 0.7 | 0.88 | 2.0 | base tone-mapping exposure |
| `env` | 0.55 | 0.6 | 1.4 | the sky's intensity on every lit material and the sky weight of the GI mix |
| `ground` | (0.55, 0.5, 0.44) | (0.42, 0.34, 0.28) | (0.06, 0.065, 0.085) | the env scene's ground disc |
| `disc` | 1 | 1 | 0 | `showSunDisc` |

After interpolation the fog colour is pulled towards `TWILIGHT.horizon` by `smoothstep(t, 0.55, 0.92)`; a
linear blend glows at the horizon (pitfall 12). `skyElev(t, el, s)` lets the sky's sun sink to `s.elev`
while the shadow-casting sun stays where the route put it, because the shadow map cannot follow. The t=0 row
is also the bake's `SKY`.

### The Preetham patches in `makeSky()`

`makeSky(scale)` takes three's `Sky` and rewrites its fragment output: `uGain` scales the Preetham colour;
`uTwK` (= `smoothstep(t, 0.55, 0.92)`) blends to an analytic twilight (horizon `TWILIGHT.horizon`, zenith
`TWILIGHT.zenith`, afterglow `TWILIGHT.glow` towards the sun's azimuth); then the band from `direction.y =
-0.015` to `uHz` (0.035 by day → 0.1 at night) melts into `uFog` so terrain and sky meet without a seam.
The sun disc multiplier `760.0 * sundisc` is replaced by `25.0` so the disc does not drive bloom. Clouds are
a few small high wisps (coverage 0.08, density 0.7, elevation 0.55, scale 0.0012): a large scale with low
density read as a smudge. The main dome is scaled 9000 (camera far is 9000; pitfall 3), the env copy 400,
stars at radius 3600.

### Sun and shadow zones

`dirFrom(az, el)`: azimuth measured from +z (the street side, since world z = −d) towards +x. The default
`sunDir = dirFrom(-55, 18)` lights the front facade from the left. `setShadowZone(zone)` sizes the
orthographic shadow camera to `half` = {aerial 300, street 60, house 18} m, re-aims the target (aerial:
(−40, 0, −20); otherwise the plot centre (3.05, 4, −9)) and sets `normalBias` {0.25, 0.05, 0.02} and
`radius` {1.5, 2.0, 3.0} per zone; `placeSun()` parks the light at `target + sunDir * (half + 200)` and
flags `renderer.shadowMap.needsUpdate` (auto-update is off). `setSun(az, el)` ignores moves under 0.15° so
the map is not re-rendered for noise; it is re-rendered through the terrace swing and set (`story.js` `SUN`),
and far houses and far palms cast only from the air. `main.js` chooses the zone in `zoneFor()`: above y 42
aerial; inside the plot box house; otherwise street.

### Environment maps, the cache and the sky-level read-back

Environments are keyed by `envBin(t, az, el, coarse)`: time of day in tenths, the −55° → −128° swing in
three azimuth bins, elevation in 4° steps anchored on the bake's 18° (the `coarse` set of the phone tier:
fifths and two azimuth bins). PMREMGenerator clamps its size to 256, so each env costs about 4 MB and tens
of millions of samples whatever size is asked; the bins keep the whole evening to about a dozen.
`envFor(t, az, el)` makes a bin current and `build(bin)` renders it (`pmrem.fromScene(envScene, 0, 0.1,
1000, { size: 256 })`) over a 400-scale sky and a 300 m ground disc at y −8 coloured by `STATES.ground`.
The cache is LRU, capped at `envCacheSize` (16; 6 on `low`); an evicted *render target* is disposed (its
texture alone frees nothing), and `bakeKey` (the bake's env, `envBin(0, -55, 18)`) and the env on screen are
never evicted. `prebuild(list, busy)` builds the environments of a `[t, az, el]` schedule one per idle
period while `busy()` is false; `main.js` feeds it the sun schedule from p 0.72 to 1.0 after the loader
goes, so a sunset reached by scrolling finds its skies ready.

The first time a key is built, `measure(key)` renders an 8 px half-float cube and resolves its L0 term
through `LightProbeGenerator`; the read-back is asynchronous (pitfall 15), so `onLevel` wakes the render
loop when it lands, and a level is kept only when all three channels are finite and positive (a lost context
or a driver refusing the read would otherwise turn the whole volume into NaN). `skyRatio()` returns the rgb
ratio of the current env's L0 to the bake's, clamped to [0, 4]; while a read-back is pending it holds the
last measured ratio, and only where nothing is measured yet does a fitted curve stand in (1 → 0.55 over t
0–0.5, then falling to 0.05 by t 1, tinted bluer). `update()` assigns the env map and `envK × env` to
every lit material (`refreshMaterials()` collects them; call it after adding objects), and `updateProbes()`
re-renders the two reflection probes (`front` at (3.05, 1.6, 4), `rear` at (3.05, 1.6, −17), `probeSize`
256 or 128) at steps of the evening; materials with `userData.probe` mirror those instead of the sky.

If you move the golden-hour sun, change `sunDir`, the −55/18 anchor in `envBin`, `main.js`'s `envFor(0,
-55, 18)` and `sunAt`, and every entry in section 10. Leave `STATES` alone until the exterior is otherwise
right; then adjust `exp` and `env` first, colour second.

## 3. `src/post.js`

### Pass order and constants

`createPost(renderer, scene, camera, { ao, aoQuality, halfRes, bloom, smaa, vol, aoZones, sun, volSteps })`
builds an `EffectComposer` on a `HalfFloatType` target; without renderable half-float buffers (`hdr` false)
AO, bloom and the march are dropped and the chain runs on 8-bit targets. With `ao`, `N8AOPass` renders the
beauty pass and AO together (`Medium` on `high`, `Performance` on `mid` and `low`); its configuration is
`halfRes`, `aoRadius 0.6` (overridden per zone in `main.js`: 5 aerial, 1.4 street, 0.55 house, 0.35 on the
phone tier), `distanceFalloff 1.0`, `intensity 3.0`. The `low` tier swaps AO for a plain `RenderPass` in the
aerial zone (`setAO`). The volumetric pass reads `aoPass.beautyRenderTarget.depthTexture`, so there are **no
volumetrics on `?q=low`**; calibrate on `high`. `BloomPass` is `UnrealBloomPass` without its final blend
(half size, radius 0.32; strength and threshold are set each frame from `LOOK`: `threshold = bloomThresholdK
/ exposure`, `strength = bloomStrength`, so lamps halo at night and sunlit render by day does not; a
threshold of `1 / exposure` would pass every sunlit patch whole). `FinishPass` samples the march's target
and the bloom mips, adds them in linear light, applies ACES and sRGB, then the grade; `SMAAPass` is last
and enabled while the pixel ratio is under `SMAA_MAX_DPR = 1.75`.

### The n8ao patch

n8ao 2.0.1 on three r187 crashes because its multi-target shim returns an array from
`depthDownsampleTarget.texture` (pitfall 2). `createPost` redefines the getter on the target's prototype to
return `textures[0]`. After upgrading either package, re-test before removing it.

### The grade in `FinishShader`

Display-referred finishing after the tone map: shadows (luminance < 0.4) cooled by `(0.97, 0.985, 1.03)`
at 35 %, highlights (0.3 → 1) warmed by `(1.045, 1.0, 0.93)` at 40 %, an S-curve mixed at 0.18, a vignette
`uVignette 0.32` and hashed grain `uGrain 0.022` scrolled by `uTime`. Tune these last; they cannot fix a
lighting problem, only hide one.

## 4. `src/volumetric.js`

### What the parameters mean, and what `main.js` sets

`VolumetricPass` raymarches at `scale 0.5` resolution through the sun's shadow depth texture with `STEPS`
(28; 20 on `mid`) and a 5-tap separable blur, writing (sun, ambient, 1 − transmittance) to its own target
for the finish pass. Per sample: `inside` = point within `uBoxMin..uBoxMax` (the house volume, (0.1,
0.25, −14.85)–(6.0, 9.7, −3.55)); density is `uDensityIn` inside, otherwise `uDensity * (1 + uHeightK *
exp(-y / uHeightScale))`; the lit term is weighted `uSunIn`/`uSunOut`, the ambient term `uAmbIn`/`uAmbOut`;
`uG 0.6` is the Henyey–Greenstein anisotropy; the composite clamps the sun term at 6. `main.js` sets, with
`air` = 1 in the aerial zone:

| Uniform | Value | Why |
| --- | --- | --- |
| `uDensity` | lerp(0.0024, 0.0013, air) | thin haze at street level, thinner from the air |
| `uDensityIn` | 0.03 | dusty room air that forms shafts |
| `uHeightK`, `uHeightScale` | lerp(2, 4, air), lerp(5, 18, air) | haze hugs the ground |
| `uMaxDist` | lerp(lerp(55, 280, air), 20, inside) | march length in metres |
| `uSteps` | lerp(12, STEPS, inside) | a dozen steps resolve thin haze |
| `uSunIn`, `uSunOut` | 1.0, lerp(0.08, 0.1, air) | shafts indoors, a hint outdoors |
| `uAmbIn`, `uAmbOut` | 0.6, 1.0 | |
| `sunCol` | sun colour × intensity × 0.16 | zero at night |
| `ambCol` | fog colour × 0.14 × (0.6 + 0.8 tod) | haze brightens relative to the scene at night |

A white veil over window views is almost never the volumetrics (pitfall 10): render the still with
`?q=low` (no march) and compare before touching densities. A bright cone or blob that survives on `low` is
geometry or baked light, not the march.

### Dust and lamp beams

`makeDust(boxes, perCubic, seed)` fills plan-space boxes `[x0, x1, y0, y1, d0, d1]` (negating d) with
motes lit only where the shadow map says the sun reaches (`main.js`: seven boxes in the sunlit rooms; 1.5
per m³, 0.8 on `low`); the sprites are small (`uSize 9`) and energy-conserving: a near mote grows but does
not brighten, so none reads as a blown white dot on the bedding. `main.js` feeds the shadow matrix and
colours (`uSunCol` = sun × `LOOK.dustSun` × inside, `uAmb` ≈ `LOOK.dustAmbient` × inside × (1 − 0.6 tod))
and shows them only while `inside > 0.02`. `beamMaterial(0xffcf96)` is the additive cone under street-lamp
heads (`community.js`, `lampBeams`), driven by the glow list; its vertex shader applies `instanceMatrix`
itself, which a `ShaderMaterial` on an `InstancedMesh` must do (without it every cone drew at the origin,
stacked into one blazing cone at the hero's front corner). Move the dust boxes to your sunlit rooms; redo
`uBoxMin/uBoxMax`.

## 5. `src/materials.js`

### `loadTextureSets()` and the c/n/r packing

`SETS` lists the 18 base sets; `INTERIOR_SETS` the seven seen only indoors, which the live page loads as
1×1 placeholders (`placeholderSet`) and streams behind the first frame (`adoptSet` swaps every placeholder
clone for a real one, no recompile); a still awaits everything. `loadTextureSets(base, anisotropy,
onProgress, { defer })` loads `<name>_c.webp` (sRGB colour), `_n` (OpenGL normal) and `_r` (R = ambient
occlusion, G = roughness) with `RepeatWrapping`; the phone tier reads `assets/tex/512/`. One `_r` texture
serves as both `roughnessMap` and `aoMap` because three reads roughness from G and AO from R. Style-only sets
load on first use through the styler. Pack new sets with the skill's `scripts/textures.py` and measure
their mean albedo with `--measure` (a `contrast` column compresses a scan that would clip when divided up to
a near-white albedo; `linen` 0.4, `boucle` 0.6); never clone a texture before it has loaded (pitfall 1).

### `pbr(name, o)` options

`tile` metres per repeat (`repeat = 1 / tile`), `tileV` for a different vertical tile, `albedo` (the
colour the finish should read as: `roleColor` divides the set's `SET_AVG` out of it) **or** `color` (a plain
tint over the scan), `flat` (texture contrast: `true` gives the role the `uFlat` control, a number uses it),
`rough` (the finish's mean roughness: `roleRoughness` divides the set's `SET_ROUGH` out), `metal`, `normal`
(normal scale), `env` (`envMapIntensity`, kept as `userData.env0`), `ao`, `side`, `physical` (switches to
`MeshPhysicalMaterial` and spreads its keys: clearcoat, sheen…), `joints`, `macro`, `noPoint`, `lampMap`.
Textures are cloned per material with the repeat baked in. Keep new textured materials in the shape `M.key =
pbr('set', { ..., albedo: 0x..., ... })` with `albedo`/`color` before any nested object: `bake-gi.mjs` parses
`materials.js` with `/M\.(\w+) = pbr\('(\w+)', \{([^}]*)/` to learn each key's set and colour (section 7),
and a set without a `SET_AVG` entry is skipped and bakes as 0.5 grey.

### `enhance(mat, o)` features

One patcher for every shader tweak; `customProgramCacheKey` is the sorted feature list, so materials
differing only in uniform values share a program. All features get the varyings `vMeters` (box UVs in
metres) and `vWPos` (world position); `cloneEnhanced(m)` is the clone that keeps them.

- `joints: { size: [sx, sy], width 0.003, shade 0.55 }` → `uJoint`; darkens a groove of `width` metres on a
  `size` grid in `vMeters` and raises roughness to 0.85 in it. Stone, travertine and marble floors.
- `macro: { scale 0.02, amount 0.35, hue 0 }` → `uMacro` and `shared.noise`, a 256 px tiling value-noise
  texture (fbm in R, one octave in G) sampled twice: albedo varies by `[1 − amount, 1 + 0.6 amount]`, a
  finer noise ±6–8 %, and `hue` warms by `(1.06, 1.0, 0.9)`. Ground materials, so large areas do not tile;
  the mips fade the variation out at distance instead of aliasing.
- `flat` → `uFlat = (rgb, amount)`; `diffuseColor = mix(texel, uFlat.rgb, amount)` pulls a photo-scan towards
  the finish's mean so painted walls read clean and a crushed velvet scan reads as velvet through its sheen.
- `glass: [a0, a1]` → fresnel alpha from `a0` at normal incidence to `a1` grazing (`pow 4`), written straight
  into `gl_FragColor` with premultiplied alpha. The panes are thin boxes drawn `FrontSide` (one layer per
  face): `M.glass`/`M.glassRear` (0.12, 0.94), `M.glassLight` (0.06, 0.75).
- `sway: k` → vertex displacement growing with distance from (0, 7, 0) in object space, phased by instance
  position (`M.frond`).
- `shade` → a lamp drum's glow grades from the rim to the top and burns 1.6× hotter on the inside; `opal` → a
  globe darkens towards its rim. Neither reads as a flat disc of light.
- `gi: true` → the `shared.gi` uniforms and `GI_FRAG` after `lights_fragment_maps`. Applied by the last loop
  of `createMaterials` to every non-transparent `MeshStandardMaterial`/`MeshPhysicalMaterial` except the
  waters.
- `lampMap: true` → `shared.lampMap` (`uLampMap`, `uLampXf`, `uLampCol`); the baked street-lamp irradiance,
  looked up by world xz, squared back from its sqrt encoding, faded out above head height (the map is a
  plan: a balcony over a lit car port must stay dark), added as Lambert diffuse. Ground materials and
  `patio`.
- `noPoint: true` → `#include <lights_fragment_begin>` is replaced by a copy whose point-light loop runs
  zero times. The light uniforms stay declared, so a light count change recompiles nothing; the exterior
  finishes skip four to seven GGX lobes per pixel. Ground, far houses, bark and fronds carry it; `leaf`,
  `flower`, `patio`, `render` and `wood` keep the fire's and the terrace lanterns' light.

### `GI_FRAG`: lookup, non-linear L1 reconstruction, inside mask

The sample point is the world position pushed 0.22 m along the normal (just under half the 0.5 m probe
spacing, so a wall samples the room-side probe, not the one in the wall). `uGiA`/`uGiB` map world to
texture coordinates; `gF` fades to zero over the outer 0.4 texels so the volume edge never shows. `g0.rgb`
is DC irradiance, `g0.a` the inside mask, `g1.rgb` the luminance gradient, `g1.a` the probe's open-sky
fraction. The reconstruction is the Geomerics/Hazel non-linear form: `gR = g1 / lum(g0)`, `x = min(0.5 |gR|,
0.98)` (0.5, not 0.433, because the stored ratio is irradiance-premultiplied), `q = ½(1 + n·ĝR)`, `p = 1 +
2x`, `a = (1 − x)/(1 + x)`, `E = DC (a + (1 − a)(p + 1) q^p)`: no negative lobe, so strong lamps do not ring
dark behind themselves (pitfall 14). Then `gw = g0.a * gF` mixes `iblIrradiance` towards `E`, and `radiance`
(and `clearcoatRadiance`) is replaced by its luminance × `gSo` × the room's bounce tint, where `gSo =
clamp(open × 2.5, 0.03, 1)` (or the irradiance ratio where the alpha is 0): a dark room has no bright sky in
its marble, and a glossy floor in a lamp-lit room reflects the room.

### Emitters and the glow list

`emissive(color, day, dusk, extra)` makes a non-shadow-casting emissive material and pushes `{ mat, day,
dusk }` onto `glow`, which `createMaterials` returns; `main.js` lerps each entry by `lamp = smoothstep(tod,
0.3, 0.95)`, writing `emissiveIntensity`, or `opacity` / a shader uniform when `prop` is set.

| Entry | day → dusk | Role |
| --- | --- | --- |
| `lampShade` 0xffd7a3 | 0.07 → 1.5 | table and pendant drums (linen over the bulb: the map modulates the glow, `shade` grades it) |
| `bulb` 0xffcf8f | 1.5 → 4.5 | pendant globes, terrace lanterns (`opal`) |
| `downlight` 0xfff0dc | 1.2 → 6 | ceiling spots, car port |
| `led` 0xffd29c | 0.6 → 5 | cove and shelf strips |
| `fire` 0xff8a3a | 0 → 6 | terrace fire bowl |
| `lampHead` 0xffd9a6 | 0 → 9 | street-lamp heads |
| `roomLit` 0xffdfb4 | 0.08 → 1.15 | neighbours' lit windows (`P.roomTexture()`; `roomDim` for the unlit ones) |
| `sheer` 0xfff4e8 | 0.05 → 0.012 | backlit translucency: a hint by day, nothing at night; the panel takes the baked light like everything else |
| `lod` 0xffd9a6 | 0 → 1.1 | facade-atlas windows of distant blocks |
| `beam` (`uOpacity`) | 0 → 0.16 | street-lamp cones |

(`M.pool`, the additive blobs under lamps, is no longer drawn: the ground takes the lamp map instead.)
Fixture day values are non-zero on purpose (an unlit fixture in a daylit room reads as a black disc); match
any change with the bake's `LAMP` table (section 7) or fixture and pool disagree.

## 6. `src/styles.js`

### Roles, albedo naming and roughness

`SET_AVG` holds the measured mean linear albedo of every packed colour map, `SET_ROUGH` the mean of every
roughness channel. A style (`STYLES.<key>`) has `name`, `short`, `blurb`, `palette`, `sets` (extra
textures to load), `art` (palette for the three generated artworks), `inside` (indoor exposure factor:
japandi 1.05, the rest 1.0) and `roles`. A role is a key of `M` and may set `set`, `tile`, `color` **or**
`albedo`, `flat`, `rough`, `metal`, `normal`, `env`, `sheen`, `clearcoat`, `joints` `[sx, sy, width,
shade]`. `albedo` means "read as this colour": `roleColor` divides it by `SET_AVG[set]`, and the bake uses
the same number, so bounce light matches the picture (decision "Finishes named by the albedo"); a white duvet
renders white rather than the scan's grey times a tint. `rough` is the finish's real mean roughness:
`roleRoughness` divides `SET_ROUGH[set]` out, so honed stone no longer turns into a mirror of the sky.
`color` is a plain tint for finishes whose scan colour is wanted. Walls (`paint`, `ceiling`) stay light in
every style; `joinery` carries the contrast; velvet roles add `flat`.

### How `apply()` avoids recompiles; adding a style or a finish

Material types and `enhance` features are fixed at `createMaterials`; `apply(key)` resolves every clone
first (a set enters `T` only when all three maps arrived, a failed load is forgotten so the next click can
retry, and a request token lets the last click win), then per role swaps `map`/`normalMap`/`roughnessMap`
(+`aoMap`) to cached clones keyed `set|channel|tile`, and writes colour, roughness, metalness, normal scale,
the authored env intensity `userData.envK` (the atmosphere multiplies it by the sky's `envScale` each
frame), `sheenColor`, `clearcoat` (never below 0.02, because 0 would drop `USE_CLEARCOAT` and recompile),
`uJoint`, `uFlat` and the `lampShade` emissive (role colour lerped 55 % towards 0xffc98a). Artworks are
regenerated with `artTexture()` and the old maps disposed. With `releaseUnused` (the phone tier) the
style-only sets no role on screen names are disposed, their clones included. A texture swap never changes a
define as long as the map stays non-null, so a style switch costs one frame.

Add the set to `textures.py` `MANIFEST`, pack, `--measure`, add the mean to `SET_AVG` and `SET_ROUGH`; add
a `STYLES` entry with every role present (missing roles keep the previous style's value); add a furniture
set in `stylesets.js`, recording its lamps through the kit; re-bake, because `N` is per style and
`albedoFor()` reads the roles. Then capture the four interiors in that style (`&style=<key>`).

## 7. `src/gi.js` and `scripts/bake-gi.mjs`

### The probe box and the components

`SP = 0.5`, `MIN = [0, 0, -15.6]`, `DIMS = [13, 22, 30]`: 8 580 probes covering x 0–6.0, y 0–10.5, z
−15.6 to −1.1: the full plot width, 0.5 m above the roof top (`H.R2 = 10.0`), and in depth just clear of
the front piers (d 1.4) and the rear pier (d 15.38). In z and y every interior surface sits ≥ 0.5 m inside
the edge, which the 0.22 m normal offset plus the edge fade in `GI_FRAG` need. In x the volume ends at the
party walls because the neighbours are attached. For a detached house add that margin in x too. Four
linear components are stored separately so the page can relight without re-baking: `S` sky light (Preetham,
golden-hour constants `SKY` identical to `STATES[0]`, no clouds, no twilight) plus the **open-sky
fraction** per probe; `U` sunlight bounced off surfaces for the held sun (−55°, 18°) and `U2` the same for
the swung sun (−128°, 11.5°, `SUN_DIRS`), so the bounce pattern follows the real sun across the terrace
chapters; `N-<style>` each style's lamps. `S`, `U` and `U2` are baked once with the `minimal` furniture,
`N` once per style. Note that semi-open spaces inside the box (the car port, the balconies) read as
`inside` too: their open-sky fraction is low because rays hit the opposite row, so the volume, fill
included, lights them.

### Passes, lamp table and the mask

The scene is the hero shell and interior, the neighbours (`buildShell(hero: false)` at ±6.1 and ±12.2 m,
mirrored at ±6.1, plus the opposite rows at z −37 and 12) and a ground quad; `SKIP` drops glass, sheers,
lattice, rails, foliage cards, the `pool` quads and the neighbours' `room` window quads so they do not block
rays. Per-triangle albedo comes from `albedoFor(style)`: `ALB` by hand for untextured keys, set mean ×
tint (or the albedo) for every `pbr()` line parsed from `materials.js`, then the style's roles on top. A
key missing from both gets 0.5 grey, so add new untextured materials to `ALB`. `PASSES = 3`: pass 1 is
light arriving directly (sky radiance on a miss for `S`; sun × cos × albedo/π on a lit hit for `U`/`U2`;
analytic fixture light in `addDirect()` for `N`), and each later pass lights every ray hit with the
previous pass's trilinearly interpolated probes (`evalProbes`), so two bounces need no per-surface
sampling. Rays: a Fibonacci sphere of `RAYS` (256; `RAYS=16` for a draft), randomly rotated per probe.

Lamps: emitter triangles of the keys in `LAMP` are clustered within 0.35 m (0.6 m for `led`) into
fixtures; `finishLamps()` turns strips into points every 0.6 m and lets a larger fixture shine up to 3× its
base. `LAMP = { downlight: 18 cd with a downward cos² lobe, r 0.12; bulb 4, r 0.15; lampShade 6, r 0.25; led
1.2 per 0.6 m, r 0.3; fire 8, r 0.3 }`, colour `WARM = (1, 0.72, 0.45)`, irradiance `I·lobe / (d² + r²)`
within 9 m when the fixture is visible (pitfall 13 explains why this is analytic); a probe closer than half a
cell to a fixture sees it no nearer than that. `maskFor()` flags probes whose 48 test rays hit more than 25
% back faces (inside walls or furniture) and `fill()` refills them from their six neighbours over 8
iterations.

### Encoding, the files and the CPU mix in `set()`

`encode()` writes per probe: DC rgb as `log2` over 20 stops from 2⁻¹⁴ (byte 0 = black), the luminance
gradient `(x, y, z)` relative to DC in [−2, 2] as three bytes, and for `S` the open fraction; `write()`
puts each component in `assets/gi/<name>.json` as `{ spacing, min, dims, stride, data }` with `data`
base64 (about 80 KB for `S`, 69 KB for the rest; 490 KB in all, gzip about 55 %). The page fetches them:
`createGI({ base, style })` starts the requests before the textures, decodes through the browser's own
base64 decoder (a `data:` fetch; `atob` where a sandbox refuses it), derives `inside = 1 − smoothstep(open,
0.2, 0.4)` and sets `uGiA`/`uGiB`; `ready` resolves once `S`, `U`, `U2` and the boot style's `N` are in;
`prepare(style)` fetches another lamp set ahead of a switch (chip hover, and `applyStyle` awaits it).

`set(kS, kU, kU2, kN, style)` skips when the quantised weights (1/128) have not moved, then writes two
`Data3DTexture`s of half floats: `t0.rgb = kS·S + kU·U + kU2·U2 + kN·N[style]`, `t0.a = inside`, `t1.rgb
= lum(kS)·S.gr + lum(kU)·U.gr + lum(kU2)·U2.gr + lum(kN)·N.gr` (the gradient is luminance-only, so colour
weights collapse to their luminance), `t1.a = open`. Weights are sanitised (finite, clamped to [0, 64]).
`main.js` passes:

- `kS = skyRatio() × STATES.env × LOOK.giFill × LOOK.giWhiteBalance` — the baked sky follows the live env
  map's measured brightness and the same intensity the exterior uses;
- `kU = (sun colour ÷ (1, 0.81, 0.6)) × (sun intensity ÷ 4.3) × LOOK.giFill × LOOK.giSunBalance × (1 −
  swing)` and `kU2` the same × `swing` — the bake's sun colour and intensity divided out, so the bounce
  scales with the real sun as it swings and sets, and the golden cast is balanced so white walls read light
  rather than tan;
- `kN = LOOK.giLamp × lerp(LOOK.giLampDay, 1, lamp)` — lamps on at 12 % by day, full at dusk.

## 8. The exposure model in `src/main.js`

### Indoor factor, the look-in, look-out and shade blends, and the `LOOK` weights

The renderer uses `ACESFilmicToneMapping` with exposure driven per frame:

`expIn = STATES.exp × lerp(1, lerp(insideExposureDay, insideExposureNight, tod) × STYLES[style].inside, inside)`
`expTarget = lerp(expIn, STATES.exp, lookOut) × lerp(1, gardenShadeExposure, shade)`

`inside` eases (rate 2.2) towards `max(camIn, lookIn)`: `camIn` is 1 when the camera is within the rooms
proper (`inHouseBox`: x 0.1–6.0, z −14.85 to −3.5, y < 9.7, excluding the roof terrace), and `lookIn` is
`LOOK.lookInExposure` (0.35, about a stop) when, from outside, the view enters the rooms within 7.5 m
(`viewCrossing`, which walks the view ray: the route interpolates orientation, so the look point itself
always sits 10 m out and says nothing). `lookOut` eases towards `camIn × LOOK.lookOutExposure` (0.6) when
the view leaves the rooms through a front, rear or roof face within 7.5 m (party walls never count), giving
part of the indoor lift back so the sunlit garden or terrace keeps its highlights. `shade` eases to 1
behind the house (x −1..7, z −15..−21.5, y < 7.5), where the rear elevation is in the sun's shade and the
sunlit-street exposure would read as dusk: `gardenShadeExposure` 2.5 exposes for the shade as a photographer
would. By day an interior is therefore exposed 4.2× (0.7 → 2.94), at night 0.9× (2.0 → 1.8): the
photographer's two stops by day, and lamp-lit rooms darker than day with pools near the lamps (decision
"Interiors exposed like a photograph"). `giFill` 3.4 multiplies the baked daylight; `giWhiteBalance` (1.0,
1.0, 0.97) trims the baked sky's blue, `giSunBalance` (0.92, 1.0, 1.12) the bounce's gold; `giLamp` 0.22
scales the lamp component to page units. Tune in that order: exposure sets the level and the headroom
(the sheers and the sun patches clip first), `giFill` where the bedding and the walls sit under it,
the balances the wall tint, `giLamp` how much a lamp lights its room against how bright the fixture looks.

### The night lights

`buildInterior()` returns `lights` (four fixed point lights: `hall`, `livingWarm`, `ff`, `fire`, day 0,
dusk 1.5–7, distance 7–9 m) and `lamps` (the bulb position of every fixture placed through the kit); each
style kit records its own `lamps`. `main.js` makes the four fixed lights `PointLight(color, day, dist,
decay 2)` at `(x, y, −d)`, faded by `smoothstep(tod, 0.25, 1)`, and a **pool** of `LOOK.lampPool` (3)
point lights (`lampReach` 2.5 m, decay 2, no shadows, colour 0xffd2a0) that `placeLamps()` parks each frame
on the three bulbs nearest the camera among the fixed fixtures and the current style's, cross-fading a
slot over about 0.4 s when it moves so a lamp never pops. The count is constant, so no program ever
recompiles; intensity is `lampIntensity` (1.2) × the lamp factor × the slot's weight. They add the pool
under each shade and the glints; room light comes from the baked volume (`giLamp`), so raise one against the
other, never both: a shade with a pool from both reads double-lit. Exterior finishes carry `noPoint` and
pay for none of this.

### Night mode and the glow list

`mode` is `auto` unless `?tod=day|night` or a `[data-mode]` button says otherwise. In auto, `todTarget =
smoothstep(progress, TOD.sunsetFrom, TOD.nightBy)` (`story.js`: from a third into the terrace chapter to
half-way through the summary); `tod` eases at rate 2.5. The sun swings azimuth −55 → −128 and elevation 18
→ 11.5 over the stair chapter (`SUN.swing`), then down to 4° over the terrace (`SUN.set`), so the sunset view
sees the disc; `U2` carries the bounce for the swung sun. The rest of night is the glow list (section 5),
the lamp map on the ground (`shared.lampMap.uLampCol = (1, 0.79, 0.54) × LOOK.streetLamp × lamp`), the
point lights, `kN`, stars (`smoothstep(t, 0.75, 1) × 0.85`), fog and `STATES[2]`; lamps stage in by
`smoothstep(tod, 0.3, 0.95)`, so they are on while the sky is still warm, and the bloom threshold falls with
the exposure so their shades halo.

## 9. `src/softgoods.js` and the decor helpers

### `drape`, `pillow`, `sheer` and the `makeKit()` helpers

Procedural cloth, no simulation (decision "Soft goods are procedural"). `drape({ L, W, drop 0.3, dropFoot =
drop, dropL = drop, dropR = drop, r 0.07, loft 0.05, pleat 0.03, crease 0.028, fold 0, hem 0, under null,
seed, res 0.03 })` lays cloth on a box top of `L × W` (x from the head, z across, top at y 0): spare cloth
rolls over an edge of radius `r`, falls `drop` at the sides (or `dropL`/`dropR` unequally, as a thrown throw
does) and `dropFoot` at the foot (0 = flat foot), with `loft` puff and diagonal creases on top, pleats of
amplitude `pleat` growing towards the hem, a corner `fold`, an uneven `hem`, and `under(s, t)` to lie on a
lofted layer beneath (`loftAt` is exported for that); `g.userData.head` is the head edge for a rolled hem.
`pillow({ L 0.7, D 0.48, T 0.17, seed, n 16 })`: two faces meeting at a piped seam, loft shaped by a
superellipse so corners stay thin, a plumped dent along the middle. `sheer(w, h, seed)`: a panel in the x–y
plane with pleats of uneven pitch, flaring towards the hem. `bed()` in `interior.js` assembles the duvet
turned down below the pillows, a `TubeGeometry` roll along the head edge, a velvet throw dropped across the
foot (long on one side, short on the other), two sleeping pillows and two cushions.

Decor helpers: `downlight(x, y, d)` a disc of radius 45 mm, 4 mm below the ceiling; `shade(...)` an open
linen drum with unit UVs (the `shade` shader grades it), `lamp(x, y, d, h 0.55, shadeR 0.17)` ceramic base
plus a drum, `pendantGlobe(x, y, d, drop 0.9, r 0.11)` rod plus an opal `bulb`, each recording its bulb for
the pool; `nightstand(x, y, d, { lamp, books, flowers, seed })` a walnut cube carrying a lamp, a lamp pushed
to the wall with books in front, or flowers under a pendant; `books()` a short stack with a cup; `tray()` a
brass tray with a carafe and a glass; `vase(x, y, d, { h, r, stems 7, spread, height, bloom, k 'ceramic',
seed })` lathe profile, stems, deformed-icosahedron blooms (`bloom`/`bloomB`, the first follows the style)
and leaves; `print(k, x, d0, d1, y0, y1, plusX)` frame, `ceiling`-coloured mat and an `art1..3` quad inset
13 %; `frameArt`/`frameArtX` walnut-framed art; `rug(cx, y, d, sx, sz, edge 'linenGrey')` bound edge in a
second tone; `plant()` concrete pot, soil, bark trunk and a foliage spot that `community.js` instances with
a `vegetation.js` canopy; `chair`, `loungeChair`, `wardrobeAlongX/D` (`joinery` carcass with 24 mm fluted
slats every 50 mm and brass `pulls()` at the meeting lines). Every helper writes material keys, never
materials, so styles restyle decor for free.

## 10. Constants that must agree

| Quantity | Where it appears |
| --- | --- |
| Golden-hour sun az −55°, el 18° | `atmosphere.js` `sunDir`, the anchor in `envBin`; `main.js` `envFor(0, -55, 18)`, `sunAt`; `bake-gi.mjs` `sunDir` |
| Swung sun az −128°, el 11.5° | `main.js` `sunAt` (through `story.js` `SUN`); `bake-gi.mjs` `SUN_DIRS.U2` |
| Sun intensity 4.3, colour (1, 0.81, 0.6) | `STATES[0]`; `bake-gi.mjs` `SUN`; `main.js` `kU` (`/ 4.3`, `/ 0.81`, `/ 0.6`) |
| Sky constants 8.0 / 1.1 / 0.004 / 0.72 / 0.82 | `STATES[0]`; `bake-gi.mjs` `SKY` |
| House box x 0.1–6.0, y 0.25–9.7, z −14.85 to −3.55 | `volumetric.js` `uBoxMin/uBoxMax`; `main.js` `inHouseBox` (z to −3.5); `zoneFor` (deliberately padded: x 0.05–6.05, z −15.4 to −1.4, y < 10.2) |
| Probe box | `bake-gi.mjs` `SP`/`MIN`/`DIMS`; read by the page from `assets/gi/*.json` |
| House centre (3.05, −9), neighbour pitch 6.1 | `atmosphere.js` sun target; `main.js` `pinWorld`; `bake-gi.mjs` (mirror about x 3.05, offsets ±6.1, ±12.2); `community.js` `mirrorX(g, 3.05)` |
| Lamp brightness | `materials.js` emissive dusk values; `bake-gi.mjs` `LAMP`; `LOOK.giLamp`, `lampIntensity` |
| Street fittings | `community.js` lamp map `fit` list (downlights at (1.5, −3.6), (4.6, −3.6) at h 3.19; strips at −6.13 and −15.22) must match `house.js`'s emitters |
| Finish albedo | `SET_AVG`; roles `albedo`; `bake-gi.mjs` `albedoFor()` |

## 11. Calibration procedure after a geometry change

### Order of operations

1. Change geometry (`plan.js`, `house.js`, `interior.js`, `stylesets.js`), then every row of section 10 that
   mentions the plot, the house box or the probe box. Set `MIN` to the volume's minimum corner (x 0, y 0 and
   the rear z, since world z = −d) and `DIMS` so every interior surface sits ≥ 0.5 m inside the volume in z
   and y, and in x too for a detached house (section 7 explains the party-wall exception).
2. `npm run build` and `node scripts/check-path.mjs`; fix the route first, every still depends on it.
3. Draft bake: `RAYS=16 npm run bake` (about 2 min on the reference build; 256 rays about 12 min). Per
   component it prints `mean`, `indoor mean` (unmasked probes under 15 % open sky; `-` for `S`, which
   produces that mask) and `max`. Reference figures at 256 rays: `S` mean 0.64, max 2.8; `U` mean 0.22,
   indoor 0.14; `U2` mean 0.08, indoor 0.05 (the swung sun reaches fewer floor patches); `N` indoor mean
   3.8–4.3, max about 63 (91–96 lamp points per style; 268–280 k triangles). An `N` max ten times that, or a
   `U` indoor mean near zero, means a misclassified emitter, a wrong `LAMP` entry or a sealed room.
4. No rebuild is needed: the page fetches `assets/gi/*.json`. Capture (below) and tune.
5. When the look holds on the draft, `npm run bake` at 256 rays, recapture the same frames and a 16-still
   route sheet.

### Capture commands

```bash
cd violet2-flythrough
nohup npm run serve > /dev/null 2>&1 &          # python3 -m http.server 8080 (pitfall 17)
curl -sI http://localhost:8080/index.html | head -1
mkdir -p out/day out/night
# four interiors by day: living, bedroom 2, master, bedroom 4 (each chapter's jump in story.js)
node scripts/capture.cjs http://localhost:8080 out/day high 0.385,0.56,0.655,0.85 "&ui=0"
node scripts/capture.cjs http://localhost:8080 out/night high 0.385,0.56,0.655,0.85 "&ui=0&tod=night"
# one style at a time: append &style=japandi (desert, luxe); defaults to minimal
# a stray highlight: &hide=sheer,lampBeams,dust names what it is; &cam=x,y,z,lx,ly,lz looks from anywhere
python3 ../skills/brochure-to-walkthrough/scripts/sheet.py out/day out/day.jpg 4 512
python3 ../skills/brochure-to-walkthrough/scripts/sheet.py out/night out/night.jpg 4 512
```

For a new property take each interior chapter's `jump` from `story.js`. `capture.cjs` renders at 1024 ×
576 (`W`, `H` env), waits for `window.__shot` (the still mode waits up to 1.5 s for the sky read-back and
settles three frames), uses a 180 s screenshot timeout (pitfall 16) and prints console errors; kill stray
Chromium between batches. It needs `playwright`, which is not in `package.json` and resolves from the global
install (`npm root -g`); on a fresh machine run `npm i -g playwright && npx playwright install chromium`.
`sheet.py` needs Pillow. Review contact sheets, not frames, and measure rather than eyeball: a downscaled
still reads as clipped long before it is (crop the bedding at full size and take the mean of a region).

### What to tune, in which order, and the target look

1. **Geometry and volume sanity.** Black or banded patches on walls: probes inside walls that the mask missed
   (lower the 25 % threshold in `maskFor()` or move the probe grid half a step) or a volume edge inside the
   house (`DIMS`). Light leaking through a wall: a gap in the shell (rays escape) or a wall thinner than the
   0.22 m normal offset in `GI_FRAG`.
2. **Exposure.** Day interiors: a white duvet at about 0.85 of the range with its weave visible, walls a
   light neutral-warm with a gradient towards the window, the window view bright but still coloured sky,
   nothing clipped except the sun disc and the first texels of a sun-struck sheer. Set `insideExposureDay`
   for the headroom first (the sheers and sun patches clip first), then `giFill` for where the bedding and
   walls sit under it.
3. **Balances.** `giSunBalance` until a white wall under the golden-hour bounce reads light, not tan;
   `giWhiteBalance` until the sky-lit side is neutral, not blue.
4. **Lamps.** Night interiors: each fixture should show a pool on the surface it faces and the fixture
   itself should not be the brightest thing by more than two stops. Raise `LAMP.I` for a type whose pool is
   missing, lower its emissive `dusk` if the fixture blows out; `giLamp` moves all baked pools together,
   `lampIntensity` the three point lights near the camera; `insideExposureNight` keeps night darker than day.
   Outside, `streetLamp` sets the ground pools of the lamp map against the lamp heads.
5. **Volumetrics.** With the sun through a window there should be a soft shaft, not a wall of white; compare
   with `?q=low` before changing `uDensityIn` or the 0.16 sun factor.
6. **Exterior.** Only now adjust `STATES.exp`/`env`, fog colour and density, and the twilight constants,
   checking the facade still (progress 0.19) and the aerials (0.03, 0.98).
7. **Grade.** Vignette, grain and split-tone last, on a full route sheet.

Done means: the eight interior stills read as one house photographed at two times of day, the four styles
differ in finish but not in exposure, and nothing was changed in only one of the places listed in section 10.
