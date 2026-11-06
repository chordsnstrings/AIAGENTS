# Lighting and the look: how the image is made and how to recalibrate it

The lighting half of the template at `violet2-flythrough/`: everything between the geometry and the pixels, for
a session adapting it to a new property. Read `decisions-and-pitfalls.md` first; it holds the "why" of the big
choices and is only cited here. Line numbers are as the files stand now; re-check them with `grep -n`.

## Contents

1 The pipeline at a glance · 2 `atmosphere.js` · 3 `post.js` · 4 `volumetric.js` · 5 `materials.js` · 6
`styles.js` · 7 `gi.js` and `bake-gi.mjs` · 8 exposure model in `main.js`, point lights, night mode · 9
`softgoods.js` and decor helpers · 10 constants that must agree · 11 calibration procedure

## 1. The pipeline at a glance

Light reaches a pixel from four places; knowing which one is wrong is most of calibration:

| Source | Outdoors | Indoors |
| --- | --- | --- |
| Direct sun | `DirectionalLight` + one PCF shadow map per zone, 4096² on `high` (`atmosphere.js`) | same, through the openings |
| Diffuse ambient | PMREM of the sky (`scene.environment`, `environmentIntensity = STATES.env`) | baked volume replaces the env diffuse where `inside` > 0 (`GI_FRAG`) |
| Specular | env map | env map scaled by the baked/env irradiance ratio (`gSo`) |
| Lamps | emissive materials + `M.pool` blobs + `M.beam` cones | baked `N` component + four `PointLight`s + emissive fixtures |

Per frame, `update()` in `main.js` (lines 170–238) drives, in order: camera, `tod` and the sun swing,
`atmo.update()`, shadow zone, `inside`, exposure, AO radius, the glow list, `gi.set()`, dust, volumetric
uniforms, point lights. The composer then runs N8AO (beauty + AO) → volumetric → bloom → `OutputPass` (ACES,
sRGB) → `FinalShader` → SMAA. Rendering is on demand; `?p=<progress>` renders one still.

## 2. `src/atmosphere.js`

### `STATES` and `stateAt()`

Three keyframes over `t` (0 golden hour, 0.5 sunset, 1 blue hour) in `STATES` (lines 13–17), linearly
interpolated field by field in `stateAt(t)` (lines 19–29):

| Field | t=0 | t=0.5 | t=1 | Drives |
| --- | --- | --- | --- | --- |
| `elev` | 17 | 3.0 | 0.4 | the *sky's* sun elevation cap, via `skyElev()` |
| `turb`, `ray`, `mie`, `mieG` | 5.0, 1.6, 0.0024, 0.72 | 6.0, 2.4, 0.0034, 0.76 | 2.0, 4.2, 0.002, 0.75 | Preetham uniforms |
| `gain` | 0.82 | 0.95 | 0.6 | `uGain`, a plain multiplier on the Preetham colour |
| `sun`, `sunCol` | 4.3, (1, 0.81, 0.6) | 2.2, (1, 0.62, 0.4) | 0, (0.55, 0.6, 0.85) | `DirectionalLight` |
| `fog`, `fogD` | (0.84, 0.78, 0.71), 0.0009 | (0.84, 0.66, 0.55), 0.0011 | `TWILIGHT.horizon`, 0.0011 | `FogExp2` |
| `exp` | 0.7 | 0.88 | 2.0 | base tone-mapping exposure |
| `env` | 0.55 | 0.6 | 1.4 | `scene.environmentIntensity` and the sky weight of the GI mix |
| `ground` | (0.55, 0.5, 0.44) | (0.42, 0.34, 0.28) | (0.06, 0.065, 0.085) | the env scene's ground disc |
| `disc` | 1 | 1 | 0 | `showSunDisc` |

After interpolation the fog colour is pulled towards `TWILIGHT.horizon` by `smoothstep(t, 0.55, 0.92)` (lines
26–27); a linear blend glows at the horizon (pitfall 12). `skyElev(t, el, s)` (line 187) lets the sky's sun sink to
`s.elev` while the shadow-casting sun stays where the route put it, because the shadow map cannot follow.

### The Preetham patches in `makeSky()`

`makeSky(scale)` (lines 31–57) takes three's `Sky` and rewrites its fragment output: `uGain` scales the Preetham
colour; `uTwK` (= `smoothstep(t, 0.55, 0.92)`) blends to an analytic twilight (horizon `TWILIGHT.horizon`,
zenith `TWILIGHT.zenith`, afterglow `TWILIGHT.glow` towards the sun's azimuth, `pow(sa, 5) * exp(-7 h)`); then
the band from `direction.y = -0.015` to `uHz` (0.035 by day → 0.1 at night, line 140) melts into `uFog` so
terrain and sky meet without a seam. The sun disc multiplier `760.0 * sundisc` is replaced by `25.0` so the disc
does not drive bloom. Clouds use three's own uniforms: coverage 0.22, density 0.32, elevation 0.55, scale
0.00016. The main dome is scaled 9000 (camera far is 9000 in `main.js` line 77; pitfall 3), the env copy 400,
stars at radius 3600.

### Sun and shadow zones

`dirFrom(az, el)` (line 10): azimuth measured from +z (the street side, since world z = −d) towards +x. The
default `sunDir = dirFrom(-55, 18)` lights the front facade from the left. `setShadowZone(zone)` (lines 106–118)
sizes the orthographic shadow camera to `half` = {aerial 300, street 60, house 18} m, re-aims the target
(aerial: (−40, 0, −20); otherwise the plot centre (3.05, 4, −9)) and sets `normalBias` {0.25, 0.05, 0.02} and
`radius` {1.5, 2.0, 3.0} per zone; `placeSun()` parks the light at `target + sunDir * (half + 200)` and flags
`renderer.shadowMap.needsUpdate` (auto-update is off in `main.js` line 74). `setSun(az, el)` ignores moves under
0.15° so the map is not re-rendered for noise. `main.js` chooses the zone in `zoneFor()` (lines 163–168): above
y 42 aerial; inside the plot box house; otherwise street.

### Environment map, cache and sky-level read-back

`envFor(t, az, el)` (lines 147–163) quantises to `t` 0.05, azimuth 6°, elevation 1° and keys a `Map` of PMREM
textures (`pmrem.fromScene(envScene, 0, 0.1, 1000, { size: 256 })`), keeping the last 8 and disposing the
oldest. `envScene` is a 400-scale sky over a 300 m-radius ground disc at y −8 coloured by `STATES.ground` (warm
bounce from below). The first time a key is built, `measure(key)` renders an 8 px half-float cube and resolves its L0
term through `LightProbeGenerator`, storing it in `skyLevel`; the read-back is asynchronous (pitfall 15), so
`onLevel` wakes the render loop when it lands. `skyRatio()` (lines 178–185) returns the rgb ratio of the current
env's L0 to the one under `BAKE_KEY = '0|-54|18'` (the quantised key of the golden-hour env the bake used; `-54`
because −55 rounds to the nearest 6°). Until both are measured, or where read-back fails, a fitted curve stands
in: 1 → 0.55 over t 0–0.5, then multiplied by a factor falling to 0.05 by t 1 (0.0275 overall), tinted bluer.

The sun target (line 72 at construction, line 114 per zone) is the house centre (3.05, 4, −9): `PLOT.w / 2`
across and the middle of the house box in depth (not `-PLOT.d / 2`, which would be −9.25). Set it to the
centre of your house box; the `house` zone's 18 m half-size is measured from it. Zone half-sizes (line 109)
only grow if the house or community is larger. If you move the golden-hour sun, change `sunDir` (line
75), `BAKE_KEY` (line 9), and every entry in section 10. Leave `STATES` alone until the exterior is otherwise
right; then adjust `exp` and `env` first, colour second.

## 3. `src/post.js`

### Pass order and constants

`createPost(renderer, scene, camera, { ao = true, aoQuality = 'Medium', halfRes = true, bloom = true, smaa =
true, sun = null, volSteps = 28 })` builds an `EffectComposer` on a `HalfFloatType` target (line 33). With `ao`,
`N8AOPass` renders the beauty pass and AO together; `setQualityMode(aoQuality)` (line 38) gets `Medium` on
`high` and `Performance` on `mid` (`Q` in `main.js` lines 33–37); its configuration (line 39) is `halfRes`, `aoRadius 0.6`
(overridden per zone in `main.js` line 194: 5 aerial, 1.4 street, 0.55 house), `distanceFalloff 1.0`, `intensity
3.0`, `gammaCorrection false`, `transparencyAware false`. Without `ao` a plain `RenderPass` runs and, because
the volumetric pass reads `aoPass.beautyRenderTarget.depthTexture`, there are **no volumetrics on `?q=low`**;
calibrate on `high`. Bloom is `UnrealBloomPass` at half size with strength 0.2, radius 0.32, threshold 9.0 (line
55; pitfall 4). `OutputPass` applies ACES and sRGB; `SMAAPass` is last; `setSize(w, h, dpr)` also feeds the
grain resolution.

### The n8ao patch

n8ao 2.0.1 on three r187 crashes because its multi-target shim returns an array from
`depthDownsampleTarget.texture` (pitfall 2). Lines 42–45 redefine the getter on the target's prototype to return
`textures[0]`. After upgrading either package, re-test before removing it.

### The `FinalShader`

Display-referred finishing after `OutputPass` (lines 12–29): shadows (luminance < 0.4) cooled by `(0.97, 0.985,
1.03)` at 35 %, highlights (0.3 → 1) warmed by `(1.045, 1.0, 0.93)` at 40 %, an S-curve mixed at 0.18, a
vignette `uVignette 0.32` (`smoothstep(1.15, 0.25, |q|)` in aspect-corrected coordinates) and hashed grain
`uGrain 0.022` scrolled by `uTime`. Tune these last; they cannot fix a lighting problem, only hide one.

## 4. `src/volumetric.js`

### What the parameters mean, and what `main.js` sets

`VolumetricPass` raymarches at `scale 0.5` resolution through the sun's shadow depth texture
(`sun.shadow.map.depthTexture`, a comparison sampler in r187) with `STEPS` (28; 20 on `mid`), a 5-tap separable
blur, and an additive composite. Per sample: `inside` = point within `uBoxMin..uBoxMax` (the house volume,
defaults line 80: (0.1, 0.25, −14.85)–(6.0, 9.7, −3.55)); density is `uDensityIn` inside, otherwise `uDensity *
(1 + uHeightK * exp(-y / uHeightScale))`; the lit term is weighted `uSunIn`/`uSunOut`, the ambient term
`uAmbIn`/`uAmbOut`; the shadow comparison bias is 0.0004; `uG 0.6` is the Henyey–Greenstein anisotropy; the
composite clamps the sun term at 6. `main.js` (lines 218–231) sets, with `air` = 1 in the aerial zone:

| Uniform | Value | Why |
| --- | --- | --- |
| `uDensity` | lerp(0.0024, 0.0013, air) | thin haze at street level, thinner from the air |
| `uDensityIn` | 0.03 | dusty room air that forms shafts |
| `uHeightK`, `uHeightScale` | lerp(2, 4, air), lerp(5, 18, air) | haze hugs the ground |
| `uMaxDist` | lerp(lerp(55, 280, air), 20, inside) | march length in metres |
| `uSunIn`, `uSunOut` | 1.0, lerp(0.08, 0.1, air) | shafts indoors, a hint outdoors |
| `uAmbIn`, `uAmbOut` | 0.6, 1.0 | |
| `sunCol` | sun colour × intensity × 0.16 | |
| `ambCol` | fog colour × 0.14 × (0.6 + 0.8 tod) | haze brightens relative to the scene at night |

A white veil over window views is almost never the volumetrics (pitfall 10): before touching densities, add
`volPass.enabled = false;` after `post.js` line 50, rebuild and recapture the same still to compare.

### Dust and lamp beams

`makeDust(boxes, perCubic = 5, seed = 9)` fills plan-space boxes `[x0, x1, y0, y1, d0, d1]` (negating d) with
motes lit only where the shadow map says the sun reaches (`main.js` lines 127–131: seven boxes in the sunlit
rooms; 2.5 per m³ on `low`); lines 211–217 feed its shadow matrix and colours (`uSunCol` = sun × 0.4 × inside,
`uAmb` ≈ 0.012 × inside × (1 − 0.6 tod)) and hide it outside. `beamMaterial(0xffcf96)` is the additive cone under street-lamp
heads (`community.js` lines 189–193, `lampBeams`), driven by the glow list and toggled at `main.js` line 202.
Move the dust boxes to your sunlit rooms; redo `uBoxMin/uBoxMax`.

## 5. `src/materials.js`

### `loadTextureSets()` and the c/n/r packing

`SETS` (lines 5–6) lists the 19 sets every page needs; `loadTextureSets(base, anisotropy, onProgress)` loads
`<name>_c.webp` (sRGB colour), `_n` (OpenGL normal) and `_r` (R = ambient occlusion, G = roughness) with
`RepeatWrapping`. One `_r` texture serves as both `roughnessMap` and `aoMap` because three reads roughness from
G and AO from R. Style-only sets (ash, limewash, microcement, papercord, terracotta, clayplaster, rattan, nero,
herringbone, smokedwalnut) load on first use through the styler. Pack new sets with the skill's
`scripts/textures.py` and measure their mean albedo with `--measure`; never clone a texture before it has loaded
(pitfall 1).

### `pbr(name, o)` options (lines 137–153)

`tile` metres per repeat (`repeat = 1 / tile`), `tileV` for a different vertical tile, `color` (a tint over the
scan), `rough`, `metal`, `normal` (normal scale), `env` (`envMapIntensity`), `ao`, `side`, `physical` (switches
to `MeshPhysicalMaterial` and spreads its keys: clearcoat, sheen…), `joints`, `macro`. Textures are cloned per
material with the repeat baked in. Keep new textured materials in the shape `M.key = pbr('set', { ..., color:
0x..., ... })`: `bake-gi.mjs` (line 35) parses `materials.js` with `/M\.(\w+) = pbr\('(\w+)', \{([^}]*)/` to learn
each key's set and tint (section 7). The capture stops at the first `}`, so write `color` as a hex literal
before any nested option object (`joints`, `macro`, `physical`), and give the set a `SET_AVG` entry, or the key
is skipped (line 37) and bakes as 0.5 grey.

### `enhance(mat, o)` features (lines 68–130)

One patcher for every shader tweak; `customProgramCacheKey` is the sorted feature list, so materials differing
only in uniform values share a program. All features get the varyings `vMeters` (box UVs in metres) and `vWPos`
(world position).

- `joints: { size: [sx, sy], width 0.003, shade 0.55 }` → `uJoint`; darkens a groove of `width` metres on a
  `size` grid in `vMeters` and raises roughness to 0.85 in it. Used by stone, travertine and marble floors.
- `macro: { scale 0.02, amount 0.35, hue 0 }` → `uMacro`; low-frequency fBm on `vWPos.xz` varies albedo by `[1 −
  amount, 1 + 0.6 amount]`, a finer noise ±6–8 %, and `hue` warms by `(1.06, 1.0, 0.9)`. Used by ground
  materials so large areas do not tile.
- `flat: true` → `uFlat = (rgb, amount)`; `diffuseColor = mix(texel, uFlat.rgb, amount)` pulls a photo-scan
  towards the finish's mean so painted walls read clean. Only `paint` and `ceiling` carry it (line 166); the
  styler sets its value.
- `glass: [a0, a1]` → fresnel alpha from `a0` at normal incidence to `a1` grazing (`pow 4`), written straight
  into `gl_FragColor` with premultiplied alpha. `M.glass` (0.06, 0.75), `M.glassLight` (0.03, 0.5).
- `sway: k` → vertex displacement growing with distance from (0, 7, 0) in object space, phased by instance
  position (`M.frond`).
- `gi: true` → the `shared.gi` uniforms and `GI_FRAG` after `lights_fragment_maps`. Applied at lines 272–274 to
  every non-transparent `MeshStandardMaterial`/`MeshPhysicalMaterial` except `water` and `poolWater`.

### `GI_FRAG`: lookup, non-linear L1 reconstruction, inside mask (lines 33–57)

The sample point is the world position pushed 0.22 m along the normal (just under half the 0.5 m probe
spacing, so a wall samples the room-side probe, not the one in the wall). `uGiA`/`uGiB` map world to texture coordinates; `gF` fades to
zero over the outer 0.4 texels so the volume edge never shows. `g0.rgb` is DC irradiance, `g0.a` the inside
mask, `g1` the luminance gradient. The reconstruction is the Geomerics/Hazel non-linear form: `gR = g1 /
lum(g0)`, `x = min(0.433 |gR|, 0.95)`, `q = ½(1 + n·ĝR)`, `p = 1 + 2x`, `a = (1 − x)/(1 + x)`, `E = DC (a + (1 −
a)(p + 1) q^p)`. The 0.433 converts the stored ratio (irradiance-premultiplied L1 over DC, range ±2) to the
paper's `|R1|/R0`; the cap keeps `a` above zero. This has no negative lobe, so strong lamps no longer ring dark
behind themselves (pitfall 14). Then `gw = g0.a * gF` mixes `iblIrradiance` towards `E`, and `radiance` (and
`clearcoatRadiance`) is scaled by `gSo = clamp(lum(E) / lum(iblIrradiance), 0.03, 1)`: reflections dim with the
diffuse so a dark room has no bright sky in its marble.

### Emitters and the glow list

`emissive(color, day, dusk, extra)` (lines 155–160) makes a non-shadow-casting emissive material and pushes `{
mat, day, dusk }` onto `glow`, which `createMaterials` returns; `main.js` lines 195–201 lerp each entry by `lamp
= smoothstep(tod, 0.3, 0.95)`, writing `emissiveIntensity`, or `opacity` / a shader uniform when `prop` is set.

| Entry | day → dusk | Role |
| --- | --- | --- |
| `lampShade` 0xffd7a3 | 0.25 → 2.2 | table and pendant drums (base 0xf1e7d6, double-sided) |
| `bulb` 0xffcf8f | 1.5 → 7 | pendant globes, terrace lanterns |
| `downlight` 0xfff0dc | 1.2 → 6 | ceiling spots, porch |
| `led` 0xffd29c | 0.6 → 5 | cove and shelf strips |
| `fire` 0xff8a3a | 0 → 6 | terrace fire bowl |
| `lampHead` 0xffd9a6 | 0 → 9 | street-lamp heads |
| `roomLit` 0xffdfb4 | 0.08 → 1.15 | neighbours' lit windows (`P.roomTexture()`) |
| `sheer` 0xfff4e8 | 0.2 → 0.012 | backlit translucency, inverted: bright by day |
| `lod` 0xffd9a6 | 0 → 1.1 | facade-atlas windows of distant blocks |
| `pool` (opacity) | 0 → 0.55 | additive light blobs under lamps and the porch |
| `beam` (`uOpacity`) | 0 → 0.16 | street-lamp cones |

Fixture day values are non-zero on purpose (an unlit fixture in a daylit room reads as a black disc); match any
change with the bake's `LAMP` table (section 7) or fixture and light pool disagree.

## 6. `src/styles.js`

### Roles and albedo naming

`SET_AVG` (lines 6–14) holds the measured mean linear albedo of every packed colour map. A style
(`STYLES.<key>`, lines 21–142) has `name`, `short`, `blurb`, `palette`, `sets` (extra textures to load), `art`
(palette for the three generated artworks), `inside` (indoor exposure factor: minimal 1.0, japandi 1.05, desert
1.0, luxe 1.0) and `roles`. A role is a key of `M` and may set `set`, `tile`, `color` **or** `albedo`, `flat`,
`rough`, `metal`, `normal`, `env`, `sheen`, `clearcoat`, `joints` `[sx, sy, width, shade]`. `albedo` means "read
as this colour": the styler divides it by `SET_AVG[set]` (line 183), and the bake uses the same number, so
bounce light matches the picture (decision "Finishes named by the albedo"). `color` is a plain tint for finishes
whose scan colour is wanted (marble, velvet). Walls (`paint`, `ceiling`) stay light in every style; `joinery`
carries the contrast.

### How `apply()` avoids recompiles; adding a style or a finish

Material types and `enhance` features are fixed at `createMaterials`; `apply(key)` (lines 167–202) only swaps
`map`/`normalMap`/`roughnessMap` (+`aoMap`) to cached clones keyed `set|channel|tile`, and writes colour,
roughness, metalness, normal scale, `envMapIntensity` (restoring the material's original `env0` when a role
omits `env`), `sheenColor`, `clearcoat` (never below 0.02, because 0 would drop `USE_CLEARCOAT` and recompile),
`uJoint`, `uFlat` (only through `albedo`: rgb = the albedo, amount = the role's `flat`, line 184), and the
`lampShade` emissive (role colour lerped 55 % towards 0xffc98a). Artworks
are regenerated with `artTexture()` and the old maps disposed. A texture swap never changes a define as long as
the map stays non-null, so a style switch costs one frame.

Add the set to `textures.py` `MANIFEST`, pack, `--measure`, add the mean to `SET_AVG`; add a `STYLES` entry with
every role present (missing roles keep the previous style's value); add a furniture set in `stylesets.js`;
re-bake, because `N` is per style and `albedoFor()` reads the roles. Then capture the four interiors in that
style (`&style=<key>`).

## 7. `src/gi.js` and `scripts/bake-gi.mjs`

### The probe box and the components

`SP = 0.5`, `MIN = [0, 0, -15.6]`, `DIMS = [13, 22, 30]` (bake line 19): 8 580 probes covering x 0–6.0, y
0–10.5, z −15.6 to −1.1: the full plot width, 0.5 m above the roof top (`H.R2 = 10.0`), and in depth just clear
of the front piers (d 1.4) and the rear pier (d 15.38). In z and y every interior surface sits ≥ 0.5 m inside
the edge, which the 0.22 m normal offset plus the 0.2 m edge fade in `GI_FRAG` need. In x the volume ends at the
party walls because the neighbours are attached: a wall's own sample point (0.22 m into the room) still reads
the full volume, but floor and ceiling within ~0.2 m of a party wall fade back to the env map. For a detached
house add that margin in x too. Three linear components are stored separately so
the page can relight without re-baking: `S` sky light (Preetham, golden-hour constants `SKY` line 122 identical
to `STATES[0]`, no clouds, no twilight) plus the **open-sky fraction** per probe; `U` sunlight bounced off
surfaces (direct sun stays real-time); `N` each style's lamps. `S` and `U` are baked once with the `minimal`
furniture, `N` once per style (lines 302–312).

### Passes, lamp table and the mask

The scene is the hero shell and interior, the neighbours (`buildShell(hero: false)` at ±6.1 and ±12.2 m,
mirrored at ±6.1, plus the opposite rows at z −37 and 12, lines 94–100) and a ground quad; `SKIP` (line 51)
drops glass, sheers, lattice, rails, foliage cards, the `pool` light blobs and the neighbours' `room` window
quads so they do not block rays. Per-triangle albedo comes from
`albedoFor(style)`: `ALB` by hand for untextured keys (line 29), set mean × tint for every `pbr()` line parsed
from `materials.js`, then the style's roles on top. A key missing from both gets 0.5 grey, so add new untextured
materials to `ALB`. `PASSES = 3`: pass 1 is light arriving directly (sky radiance on a miss for `S`; sun × cos ×
albedo/π on a lit hit for `U`; analytic fixture light in `addDirect()` for `N`), and each later pass lights
every ray hit with the previous pass's trilinearly interpolated probes (`evalProbes`), so two bounces need no
per-surface sampling. Rays: a Fibonacci sphere of `RAYS` (256; `RAYS=16` for a draft), randomly rotated per
probe.

Lamps: emitter triangles of the keys in `LAMP` (line 53) are clustered within 0.35 m (0.6 m for `led`) into
fixtures; `finishLamps()` turns strips into points every 0.6 m and lets a larger fixture shine up to 3× its
base. `LAMP = { downlight: 18 cd with a downward cos² lobe, r 0.12; bulb 4, r 0.15; lampShade 6, r 0.25; led 1.2
per 0.6 m, r 0.3; fire 8, r 0.3 }`, colour `WARM = (1, 0.72, 0.45)`, irradiance `I·lobe / (d² + r²)` within 9 m
when the fixture is visible (pitfall 13 explains why this is analytic). `maskFor()` flags probes whose 48 test
rays hit more than 25 % back faces (inside walls or furniture) and `fill()` refills them from their six
neighbours over 8 iterations.

### Encoding, decoding and the CPU mix in `set()`

`encode()` (lines 285–300) writes per probe: DC rgb as `log2` over 20 stops from 2⁻¹⁴ (byte 0 = black), the
luminance gradient `(x, y, z)` relative to DC in [−2, 2] as three bytes, and for `S` the open fraction; base64
into `src/gi-data.js` (~423 kB, bundled). `decode()` in `gi.js` (lines 12–23) inverts it. `createGI()` derives
`inside = 1 − smoothstep(open, 0.2, 0.4)` and sets `uGiA`/`uGiB` from `GI.spacing/min/dims`.

`set(kS, kU, kN, style)` (lines 49–66) skips when the inputs (3 decimals) have not moved, then writes two
`Data3DTexture`s of half floats: `t0.rgb = kS·S + kU·U + kN·N[style]`, `t0.a = inside`, `t1 = lum(kS)·S.gr +
lum(kU)·U.gr + lum(kN)·N.gr` (the gradient is luminance-only, so colour weights collapse to their luminance).
`main.js` (lines 204–207) passes:

- `kS = skyRatio() × STATES.env × GI_FILL × GI_WB` — the baked sky follows the live env map's measured
  brightness and the same intensity the exterior uses;
- `kU = (sun colour ÷ (1, 0.81, 0.6)) × (sun intensity ÷ 4.3) × GI_FILL` — the bake's sun colour and intensity
  divided out, so `U` scales with the real sun as it swings and sets;
- `kN = GI_LAMP × lerp(0.12, 1, lamp)` — lamps on at 12 % by day, full at dusk.

## 8. The exposure model in `src/main.js`

### Indoor factor, `GI_FILL`, `GI_LAMP`, `GI_WB`

The renderer uses `ACESFilmicToneMapping` with exposure driven per frame (line 191):

`exposure = STATES.exp × lerp(1, lerp(5.5, 1.3, tod) × STYLES[style].inside, inside)`

`inside` (line 186) is 1 when the camera is within the house box x 0.1–6.0, z −14.85 to −3.5, y < 9.7, excluding
the roof terrace (`y > 6.8 && z < -11.2`), smoothed at rate 2.2. By day an interior is therefore exposed 5.5×
(0.7 → 3.85), at night 1.3× (2.0 → 2.6): the photographer's two-and-a-half stops (decision "Interiors exposed
like a photograph"). `GI_FILL = 3.0` (line 21) multiplies the baked daylight for the bounces past the two the
bake traces; `GI_WB = (1.0, 1.0, 0.97)` trims the baked sky's blue; `GI_LAMP = 0.45` scales the lamp component
to page units. Tune in that order: exposure sets the level, `GI_FILL` how deep the corners fall relative to the
window wall, `GI_WB` the wall tint, `GI_LAMP` how much a lamp lights its room against how bright the fixture
looks (glow list).

### The point lights that remain

`buildInterior()` returns `lights` (`interior.js` lines 503–508); `main.js` lines 114–120 make each a
`PointLight(color, day, dist, decay 2)` at `(x, y, −d)` and line 232 lerps intensity by `smoothstep(tod, 0.25,
1)`:

| Name | Position (plan) | Colour | day → dusk | dist |
| --- | --- | --- | --- | --- |
| `hall` | (2.6, C0 − 0.4, 8.2) | 0xffd9a8 | 0 → 1.5 | 7 |
| `livingWarm` | (3.0, C0 − 0.5, 12.6) | 0xffd2a0 | 0 → 2.2 | 9 |
| `ff` | (3.8, C1 − 0.4, 8.5) | 0xffd9a8 | 0 → 1.8 | 8 |
| `fire` | (1.95, F2 + 0.9, 12.3) | 0xff9a4a | 0 → 7 | 7 |

They add glints and the fire's warmth only; room light comes from the volume. Keep the count near four: each is
a per-pixel cost on every GI material.

### Night mode and the glow list

`mode` is `auto` unless `?tod=day|night` or a `[data-mode]` button (`index.html` line 25, wired in `ui.js` lines
54–58) says otherwise. In auto, `todTarget = smoothstep(progress, 0.79, 0.975)` (line 177): evening starts as
the camera reaches the roof and is blue hour for the final aerial; `tod` eases at rate 2.5. The sun swings
azimuth −55 → −128 and elevation 18 → 11.5 over progress 0.735–0.83, then down to 4° over 0.868–0.89 (lines
180–182), so the terrace sunset view sees the disc. The rest of night is the glow list (section 5), the point
lights, `kN`, stars (`smoothstep(t, 0.75, 1) × 0.85`), fog and `STATES[2]`; lamps stage in by `smoothstep(tod,
0.3, 0.95)`, so they are on while the sky is still warm.

## 9. `src/softgoods.js` and the decor helpers

### `drape`, `pillow`, `sheer` and the `makeKit()` helpers (`interior.js` lines 15–215)

Procedural cloth, no simulation (decision "Soft goods are procedural"). `drape({ L, W, drop 0.3, dropFoot =
drop, r 0.07, loft 0.05, pleat 0.03, seed, res 0.03 })` lays cloth on a box top of `L × W` (x from the head, z
across, top at y 0): spare cloth rolls over an edge of radius `r`, falls `drop` at the sides and `dropFoot` at
the foot (0 = flat foot), with `loft` puff and diagonal creases on top and pleats of amplitude `pleat` growing
towards the hem, 1.7× deeper at the corners (line 58), which also hang lower because the diagonal overhang is
longer; `g.userData.head` is the head edge for a rolled hem. `pillow({ L
0.7, D 0.48, T 0.17, seed, n 16 })`: two faces meeting at a piped seam, loft shaped by a superellipse so corners
stay thin, a plumped dent along the middle. `sheer(w, h, seed)`: a panel in the x–y plane with pleat pitch 0.17
+ 0.09·noise m, depth 0.026 + 0.022·noise, flaring towards the hem. `bed()` in `interior.js` (from line 174)
assembles duvet (`L = len − 0.65`, drop 0.3, foot 0.27), a `TubeGeometry` roll of radius 0.032 along the head
edge, a velvet throw (`L 0.48`, `r 0.1`, `pleat 0.04`), two pillows at 1.0 rad and two cushions.

Decor helpers: `downlight(x, y, d)` a disc of radius 45 mm, 4 mm below the ceiling; `lamp(x, y, d, h 0.55,
shadeR 0.17)` ceramic base plus an open `lampShade` drum; `pendantGlobe(x, y, d, drop 0.9, r 0.11)` rod plus
`bulb`; `vase(x, y, d, { h, r, stems 7, spread, height, bloom, k 'ceramic', seed })` lathe profile, stems,
deformed-icosahedron blooms (`bloom`/`bloomB`, the first follows the style) and leaves; `print(k, x, d0, d1, y0,
y1, plusX)` frame, `ceiling`-coloured mat and an `art1..3` quad inset 13 %; `frameArt`/`frameArtX` walnut-framed
art; `rug(cx, y, d, sx, sz, edge 'linenGrey')` bound edge in a second tone; `plant()` concrete pot, soil, bark
trunk and a foliage spot that `community.js` instances with a `vegetation.js` canopy; `chair`, `loungeChair`, `nightstand` (with a small lamp),
`wardrobeAlongX/D` (`joinery` carcass with 24 mm fluted slats every 50 mm). Every helper writes material keys,
never materials, so styles restyle decor for free.

## 10. Constants that must agree

| Quantity | Where it appears |
| --- | --- |
| Golden-hour sun az −55°, el 18° | `atmosphere.js` 75 (`sunDir`), 9 (`BAKE_KEY '0\|-54\|18'`); `main.js` 123 (`envFor(0, -55, 18)`), 181–182 (route lerps); `bake-gi.mjs` 22 |
| Sun intensity 4.3, colour (1, 0.81, 0.6) | `STATES[0]`; `bake-gi.mjs` 23 (`SUN`); `main.js` 204–207 (`/ 4.3`, `/ 0.81`, `/ 0.6`) |
| Sky constants 5.0 / 1.6 / 0.0024 / 0.72 / 0.82 | `STATES[0]`; `bake-gi.mjs` 122 (`SKY`) |
| House box x 0.1–6.0, y 0.25–9.7, z −14.85 to −3.55 | `volumetric.js` 80; `main.js` 186 (`inHouse`, z to −3.5); 164 (`zoneFor`, deliberately padded: x 0.05–6.05, z −15.4 to −1.4, y < 10.2) |
| Probe box | `bake-gi.mjs` 19; read by the page from `gi-data.js` |
| House centre (3.05, −9), neighbour pitch 6.1 | `atmosphere.js` 72, 114 (sun target); `main.js` 138 (`pinWorld`); `bake-gi.mjs` 96–100 (mirror about x 3.05, offsets ±6.1, ±12.2) |
| Lamp brightness | `materials.js` 223–228 (emissive dusk); `bake-gi.mjs` 53 (`LAMP`); `GI_LAMP` |
| Finish albedo | `SET_AVG`; roles `albedo`; `bake-gi.mjs` `albedoFor()` |

## 11. Calibration procedure after a geometry change

### Order of operations

1. Change geometry (`plan.js`, `house.js`, `interior.js`, `stylesets.js`), then every row of section 10 that
   mentions the plot, the house box or the probe box. Set `MIN` to the volume's minimum corner (x 0, y 0 and the rear
   z, since world z = −d) and `DIMS` so every interior surface sits ≥ 0.5 m inside the volume in z and y, and
   in x too for a detached house (section 7 explains the party-wall exception).
2. `npm run build` and `node scripts/check-path.mjs`; fix the route first, every still depends on it.
3. Draft bake: `RAYS=16 npm run bake` (≈ 2 min 20 s on the reference build; 256 rays ≈ 10 min). Per component
   it prints `mean`, `indoor mean` (unmasked probes under 15 % open sky; `-` for `S`, which produces that mask)
   and `max`. Reference figures at 16 rays: `S` mean 0.351, max 2.93; `U` mean 0.094, indoor 0.058, max 0.88;
   `N` indoor mean 3.65–3.99, max ≈ 62 (94–99 lamp points per style; ~250–264 k triangles). An `N` max ten times that, or a `U` indoor mean near zero, means a
   misclassified emitter, a wrong `LAMP` entry or a sealed room.
4. `npm run build` again (`gi-data.js` is bundled), then capture (below) and tune.
5. When the look holds on the draft, `npm run bake` at 256 rays, rebuild, recapture the same frames and a
   16-still route sheet.

### Capture commands

```bash
cd violet2-flythrough
nohup npm run serve > /dev/null 2>&1 &          # python3 -m http.server 8080 (pitfall 17)
curl -sI http://localhost:8080/index.html | head -1
mkdir -p out/day out/night
# four interiors by day: ground floor (study/kitchen), living, bedrooms, master (mid progress of each card)
node scripts/capture.cjs http://localhost:8080 out/day high 0.40,0.47,0.62,0.70 "&ui=0"
node scripts/capture.cjs http://localhost:8080 out/night high 0.40,0.47,0.62,0.70 "&ui=0&tod=night"
# one style at a time: append &style=japandi (desert, luxe); defaults to minimal
python3 ../skills/brochure-to-walkthrough/scripts/sheet.py out/day out/day.jpg 4 512
python3 ../skills/brochure-to-walkthrough/scripts/sheet.py out/night out/night.jpg 4 512
```

For a new property take the mid progress of each interior card's `data-from`/`data-to` in `index.html`.
`capture.cjs` renders at 1024 × 576 (`W`, `H` env), waits for `window.__shot` (the still mode, `main.js` lines
267–278, waits up to 1.5 s for the sky read-back and settles three frames), uses a 180 s screenshot timeout
(pitfall 16) and prints console errors; kill stray Chromium between batches. It needs `playwright`, which is not
in `package.json` and resolves from the global install (`npm root -g`); on a fresh machine run `npm i -g
playwright && npx playwright install chromium`. `sheet.py` needs Pillow. Review contact sheets, not frames.

### What to tune, in which order, and the target look

1. **Geometry and volume sanity.** Black or banded patches on walls: probes inside walls that the mask missed
   (lower the 25 % threshold in `maskFor()` or move the probe grid half a step) or a volume edge inside the
   house (`DIMS`). Light leaking through a wall: a gap in the shell (rays escape) or a wall thinner than the
   0.22 m normal offset in `GI_FRAG`.
2. **Exposure.** Day interiors: walls a light warm grey with a visible gradient towards the window, the floor
   under the window the brightest surface, the window view bright but still coloured sky, nothing clipped except
   the sun disc. Adjust the 5.5 (line 191) by ±0.5 steps; use a style's `inside` only for a style that is darker
   overall (japandi 1.05).
3. **`GI_FILL`** until corners and ceilings are dark but legible (no black ceiling in a daylit room); then
   **`GI_WB`** until a white wall is neutral-warm, not blue.
4. **Lamps.** Night interiors: each fixture should show a pool on the surface it faces and the fixture itself
   should not be the brightest thing by more than two stops. Raise `LAMP.I` for a type whose pool is missing,
   lower its emissive `dusk` if the fixture blows out; `GI_LAMP` moves all pools together; the 0.12 day stage
   keeps fixtures from reading black.
5. **Volumetrics.** With the sun through a window there should be a soft shaft, not a wall of white; compare
   with the pass disabled before changing `uDensityIn` or the 0.16 sun factor.
6. **Exterior.** Only now adjust `STATES.exp`/`env`, fog colour and density, and the twilight constants,
   checking the facade still (progress ≈ 0.30) and the aerials (0.03, 0.98).
7. **Grade.** Vignette, grain and split-tone last, on a full route sheet.

Done means: the eight interior stills read as one house photographed at two times of day, the four styles differ
in finish but not in exposure, and nothing was changed in only one of the places listed in section 10.
