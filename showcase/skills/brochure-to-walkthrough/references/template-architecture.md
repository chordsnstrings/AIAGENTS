# Template architecture: `violet2-flythrough`

The per-file map of the reference build the skill copies as its template. Read `decisions-and-pitfalls.md`
(same folder) first: it says *why* the whole is shaped as it is; this file says *where* each piece lives,
what it exports and what to touch for a different property. Identifiers, numbers and signatures were read
from the code after the review-and-fix passes; functions are named rather than line-numbered because the
lines moved in every pass (`grep -n` finds them).

## Contents

[Dependency map](#dependency-map) · [Conventions](#conventions-that-cross-every-file) · [plan.js](#srcplanjs) ·
[story.js](#srcstoryjs) · [look.js](#srclookjs) · [tiers.js](#srctiersjs) · [builder.js](#srcbuilderjs) ·
[house.js](#srchousejs) · [interior.js](#srcinteriorjs) · [softgoods.js](#srcsoftgoodsjs) ·
[stylesets.js](#srcstylesetsjs) · [styles.js](#srcstylesjs) · [materials.js](#srcmaterialsjs) ·
[proctex.js and vegetation.js](#srcproctexjs-and-srcvegetationjs) · [community.js](#srccommunityjs) · [path.js](#srcpathjs) ·
[atmosphere.js](#srcatmospherejs) · [gi.js and assets/gi](#srcgijs-and-assetsgi) · [post.js and volumetric.js](#srcpostjs-and-srcvolumetricjs) ·
[ui.js](#srcuijs) · [main.js](#srcmainjs) · [index.html and style.css](#indexhtml-and-stylecss) · [scripts/](#scripts) ·
[package.json and the build](#packagejson-and-the-build) · [Adapting to a new property](#adapting-to-a-new-property)

## Dependency map

`src/main.js` is the only entry point (esbuild bundles it to `dist/app.js`); it imports every other
module, directly or through them, and nothing imports it.

| Module | Imports from the template | What flows out |
| --- | --- | --- |
| `plan.js` | nothing | `PLOT`, `H`, `FACTS`, `ROOMS`, `STAIR` → `house.js`, `interior.js`, `stylesets.js`, `community.js` (levels), `ui.js` (rooms, plot, facts) |
| `story.js` | nothing | `CHAPTERS`, `FADE`, `chapter()`, `chapterAt()`, `TOD`, `SUN`, `PIN`, `STYLE_PILL` → `main.js`, `ui.js`, `scripts/check-path.mjs` |
| `look.js` | nothing | `LOOK` (the photographic constants) → `main.js` only |
| `tiers.js` | nothing | `TIERS`, `detectTier`, `pixelRatioFor`, `AdaptiveScale` → `main.js` |
| `builder.js` | nothing | `Builder`, `F`, `mirrorX`, `meshes`, `instanced` → every geometry module and both scripts |
| `house.js` | `plan.js` (`H`), `builder.js` (`F`) | `buildShell(B, {hero})` → `main.js` (hero), `community.js` (neighbours), both scripts |
| `interior.js` | `plan.js`, `builder.js`, `softgoods.js` | `makeKit`, `buildInterior` → `main.js`, `stylesets.js` (via the kit), both scripts |
| `softgoods.js` | nothing | `drape`, `loftAt`, `pillow`, `sheer` → `interior.js` |
| `stylesets.js` | `plan.js`, `vegetation.js` | `buildStyleSet(B, key, kit)` → `main.js`, `bake-gi.mjs` |
| `styles.js` | `proctex.js` (`artTexture`) | `STYLES`, `SET_AVG`, `SET_ROUGH`, `roleColor`, `roleRoughness`, `createStyler` → `main.js`, `materials.js`, `bake-gi.mjs` |
| `materials.js` | `proctex.js`, `volumetric.js` (`beamMaterial`), `styles.js` | `SETS`, `INTERIOR_SETS`, `loadSet`, `placeholderSet`, `loadTextureSets`, `adoptSet`, `shared`, `cloneEnhanced`, `createMaterials` |
| `gi.js` | `materials.js` (`shared`); fetches `assets/gi/*.json` | `createGI({base, style})` → `{ ready, set, prepare }` filling the two 3D textures `materials.js` samples |
| `community.js` | `builder.js`, `house.js`, `plan.js`, `vegetation.js`, `materials.js` (`shared`, `cloneEnhanced`) | `buildCommunity(M, spots, {lite})` → `{ group, stats, update, setShadowZone }`; `dressShell(B, {lod})`; `R`, `CENTER` |
| `atmosphere.js` | three addons only | `Atmosphere` (sun, sky, fog, env maps, probes, shadow zones) → the frame loop |
| `path.js` | nothing | `KEYS`, `MAX_SHIFT`, `DronePath`, `DroneRig` → the frame loop and `check-path.mjs` |
| `post.js` | `volumetric.js` (`VolumetricPass`), n8ao | `createPost(...)` → the composer the loop renders |
| `volumetric.js` | three addons only | `VolumetricPass`, `makeDust`, `beamMaterial` |
| `ui.js` | `plan.js`, `story.js` | `initUI(...)` → DOM overlay handle |
| `scripts/bake-gi.mjs` | `builder`, `house`, `interior`, `stylesets`, `styles`; reads `materials.js` as text | writes `assets/gi/S.json`, `U.json`, `U2.json`, `N-<style>.json` |
| `scripts/check-path.mjs` | `builder`, `house`, `interior`, `path`, `story` | report and exit code |

Flows to hold in your head: **plan → geometry and plan → SVG** (`ROOMS` draws the mini-plans, `H`
positions floors and stairs, but walls are hand-placed in `house.js` and `interior.js` from the same
numbers, so a plan change is a three-file edit); **story → everything timed** (`CHAPTERS` gives the cards
their windows, the rail its stops, the sunset and the sun swing their progress, and `path.js` is authored to
the same numbers); **material keys → meshes** (geometry names a string key, `meshes()` resolves it against
`M` at the end; an unknown key is `console.warn('missing material', k)` and the geometry is silently
dropped, so grep the console after every geometry edit); **styles → materials, not geometry**
(`createStyler().apply` mutates materials in `M` in place; a style's only geometry is its `buildStyleSet`
group, toggled by visibility); **atmosphere → GI → shaders** (each frame `atmo.update()` returns a state,
`main.js` turns it into rgb weights for `gi.set(sky, sunHeld, sunSwung, lamps, style)`, which re-mixes the
baked volume into two `Data3DTexture`s every opaque material samples through `shared.gi`); **post chain**
`N8AOPass` (beauty + AO; a plain `RenderPass` where AO is off) → `VolumetricPass` (its own half-size target)
→ `BloomPass` (mips only) → `FinishPass` (march and bloom composited in linear light, ACES, sRGB, grade) →
`SMAAPass` while the pixel ratio is under 1.75.

## Conventions that cross every file

- **Plan coordinates.** `x` across the plot (0 = left party line seen from the street, `PLOT.w` 6.1
  on the right), `d` depth from the street line (0) to the rear boundary (`PLOT.d` 18.5), `y` height.
  World `z = -d`. Each geometry module defines `bx(k, x0, x1, y0, y1, d0, d1, faces)` calling
  `B.box(k, x0, x1, y0, y1, -d1, -d0, faces)`; `interior.js` adds `M4(x, y, d, ry, rx, rz)`, a matrix at
  `(x, y, -d)` with Euler order `YXZ`. `path.js` keyframes are already world `z`: a camera 9.7 m from
  the street is written `-9.7`. Recorded lamp bulbs (`kit.lamps`, `interior.lamps`) are `[x, y, d]`.
- **Metre UVs.** `Builder.box` writes UVs as metres along each face's own axes, so a wall cut around
  an opening keeps one continuous texture. `Builder.add(k, geo, m, 'box')` re-projects UVs by dominant
  normal in the geometry's *local* space × `uvScale`; `'keep'` retains the geometry's UVs. In
  `materials.js`, `pbr(name, { tile })` sets `repeat = 1 / tile`: `tile` is metres per repeat.
- **Face flags.** `F = { PX: 1, NX: 2, PY: 4, NY: 8, PZ: 16, NZ: 32, ALL: 63 }`. Floors `F.PY`,
  ceilings `F.NY`, panes `F.PZ | F.NZ`. Skipped faces are where the triangle budget is saved.
- **Material keys** name the role a surface plays (`render`, `paint`, `ceiling`, `stone`, `joinery`,
  `oakFloor`, `frame`, `glass`, `glassRear`, `bronze`, `brass`, `led`, `downlight`, `bulb`, `lampShade`,
  `fire`, `curb`, `equipment`...). Styles re-parameterise only the keys in `STYLES[key].roles`; the rest
  keep their `materials.js` definition.
- **Hero versus neighbour.** `buildShell(B, { hero })` is built twice: hero (`main.js`: real
  balusters, slid-open panels, open door) and non-hero (`community.js`: `rail` alpha cards, fake
  lit `room` quads), the latter instanced and mirrored with `mirrorX(geo, 3.05)` for alternate units.
  Both return planting spots `{ bush, flower, palm, olive, pink }` as `[x, y, d, scale]` for `community.js`,
  and both get `dressShell()` (roof pavers, coping, condensers, a tank) on top.

## src/plan.js

Single source of truth (47 lines). `PLOT = { w: 6.1, d: 18.5, areaM2: 112.85 }`.
`H = { G: 0.05, F0: 0.25, C0: 3.25, F1: 3.55, C1: 6.5, F2: 6.8, C2: 9.7, R2: 10.0 }`:
plinth, ground floor and ceiling, first floor and ceiling, roof-level floor and ceiling, roof top;
slabs 0.3 m, storeys 2.9–3.0 m clear. `FACTS`: project, unit, type, beds, parking, completion, saleable
areas; `ui.js` prints them on the plan sheet and on the no-WebGL page. `ROOMS`: 20 entries `{ f, key, name,
x: [x0, x1], d: [d0, d1], size? }` on floors 0/1/2; `key` is what `.plan[data-room]` in `index.html` names.
`STAIR = { x: [0.1, 2.95], d: [6.65, 9.45] }` draws the stair on the plans; the stair in `interior.js` uses
the numbers directly. Why so small: a room here only has to be right for the mini-plan; 3D walls carry
thicknesses, nibs and openings a rectangle cannot.

## src/story.js

The one chapter table. `CHAPTERS` is thirteen `{ key, rail, from, to, jump }` rows (hero 0–0.04 …
summary 0.96–1): `from`/`to` is the card's window, `rail` the label on the chapter rail, `jump` where a
rail click or an arrow key lands. `FADE = 0.008` is the half-width of a card's fade. Derived from the
table: `TOD = { sunsetFrom, nightBy }` (auto time of day), `SUN = { swing: [from, to], set: [from, to] }`
(the sun's azimuth swing and its drop), `PIN.windows` (the plot pin's in and out ramps) and `STYLE_PILL`
(where the style switcher shows). `chapter(key)` and `chapterAt(p)` are the lookups. `check-path.mjs`
asserts the table's own rules: consecutive windows at least `2 * FADE` apart, no stretch over 0.03
uncaptioned, every `jump` inside its window. Retiming a chapter is this table plus `path.js`.

## src/look.js

The photographic constants, in page units, kept out of the loop so a property is re-tuned here:
`giFill` (fill on the baked daylight), `giLamp` and `giLampDay` (the baked lamp set at dusk and by day),
`giWhiteBalance` (on the baked sky), `giSunBalance` (on the baked sun bounce, which is golden-hour warm),
`insideExposureDay` / `insideExposureNight` (the indoor lift), `lookInExposure` (looking in through glazing
from outside), `lookOutExposure` (looking out from inside), `gardenShadeExposure` (behind the house, in the
sun's shade), `streetLamp` (the ground pools of the lamp map), `lampPool` / `lampReach` / `lampIntensity`
(the night point-light pool), `bloomThresholdK` / `bloomStrength` (bloom rides with exposure), `dustSun` /
`dustAmbient`. `lighting-and-look.md` says what each does to the picture and in which order to tune them.

## src/tiers.js

Quality tiers as **pixel budgets**, not DPR caps: `TIERS.high` 3.7 MP, `mid` 2.1 MP, `low` 0.6 MP of
device pixels per frame, each with its passes (`ao`, `aoQuality`, `halfRes`, `smaa`, `bloom`, `vol`,
`volSteps`; `low` has `aoZones: true`, AO only in the house and street zones, and no volumetric march).
`classifyGPU(gl)` reads the renderer name through `WEBGL_debug_renderer_info`: software renderers and
mobile GPUs `low`, integrated laptop GPUs and base M1/M2 `mid`, discrete GPUs and Apple Pro/Max `high`,
unknown desktops `mid`. `detectTier(gl, forced)` honours `?q=`. `pixelRatioFor(budget, w, h)` is the
largest pixel ratio within the budget, never above the device's. `AdaptiveScale` walks a ladder of
0.6–1.3× that ratio on measured frame cost (the GPU timer where `EXT_disjoint_timer_query_webgl2` exists,
else the rAF interval): down a rung after two 30-frame windows over 19 ms, up a rung as a probe once the
scroll has settled for 3 s under the ceiling.

## src/builder.js

`class Builder`: `bucket(k)`; `box(k, x0, x1, y0, y1, z0, z1, faces = F.ALL)` (sorts corners, drops
boxes thinner than 1e-4); `add(k, geo, matrix = null, uv = 'keep' | 'box', uvScale = 1)` (flips
winding when the matrix determinant is negative); `quad(k, p0, p1, p2, p3, uv)` (counter-clockwise
from the front); `geometries()` → `Map<key, BufferGeometry>` (Uint32 index above 65 535 vertices).
`mirrorX(geo, cx)`; `meshes(geos, mats, { cast, receive, order })` → `Group` of one `Mesh` per key with
`matrixAutoUpdate = false` and `renderOrder` from `order[key]` (the hero's sheer draws under its glass from
every view); `instanced(geos, mats, matrices, ...)` → one `InstancedMesh` per key.
A material with `userData.noShadow = true` never casts (glass, sheers, emitters).

## src/house.js

`buildShell(B, { hero = false })` → spots. Helpers in plan units: `wallX(k, x0, x1, y0, y1, d0, d1,
holes = [[x0, x1, y0, y1]])` (wall along `x`, split around openings) and `wallD(k, x0, x1, y0, y1, d0,
d1, holes = [[d0, d1, y0, y1]])` (along `d`), both duplicated verbatim in `interior.js`; `glaze(x0, x1,
y0, y1, d, panels = 1, open = null, glassKey = 'glass')` (black frame and panes in plane `d`; `open`
slides one panel behind its neighbour, hero only, written `hero ? n : null`; garden-facing openings pass
`'glassRear'` so their panes mirror the rear reflection probe); `glazeD(x, d0, d1, y0, y1)` (one pane in
plane `x`); `railing(alongX, a0, a1, y, at, ht = 1.1)` (`bronze` balusters when hero, else one `rail`
card); `slats(...)` (pergola); `latticeD(...)`; `room(...)` (non-hero lit quads).

Sections: site (pavers, planters, garden walls, rear palm and shrub spots); ground floor (party walls,
kitchen window, stone recess with the walnut door at `x 1.95, d 6.62` swung 82° when hero, four-panel
rear glazing); first floor (slabs, balcony fronts, pergola, lattice); roof (bedroom 4 box, pergola,
terrace railings). Every opening is a hole in `wallX`/`wallD` *and* a `glaze` at the wall's mid-plane;
`interior.js` repeats the same holes in its 12 mm `paint` linings, or a window shows a wall behind it.
The three `B.quad('pool', ...)` emitters (car-port downlights, door strip, patio strip) are no longer
drawn: `main.js` and `community.js` drop the `pool` bucket, since the fittings now live in the lamp
irradiance map (`community.js`) and, for the hero, in the baked volume.

## src/interior.js

`makeKit(B, spots)` returns the placement kit shared by the fixed interior and the style sets:

| Helper | Signature | Notes |
| --- | --- | --- |
| `bx` | `(k, x0, x1, y0, y1, d0, d1, faces?)` | plan-unit box |
| `rb` | `(k, x, y, d, sx, sy, sz, r = 0.03, ry = 0, parent = null, rx = 0)` | rounded box *centred* at `(x, y, d)`; with `parent` the position is local to it |
| `cyl` | `(k, x, y, d, r0, r1, h, seg = 28, parent = null, open = false)` | UVs kept, ×2 |
| `sphere`, `wallX`, `wallD` | `(k, x, y, d, r, parent = null)`; walls as in `house.js` | |
| `door` | `(hx, hd, y, w, ang, alongX = true, h = 2.4)` | `joinery` leaf hinged at `(hx, hd)`, `brass` pull; `ang` 0 = closed |
| `print` | `(k, x, d0, d1, y0, y1, plusX, fk = 'frame')` | framed print on a wall in plane `x`, white mat, art inset 13 % |
| `frameArt`, `frameArtX` | `(k, x0, x1, y0, y1, d, 'street' \| 'rear')`, `(k, x, d0, d1, y0, y1, facingPlusX)` | walnut-framed canvas |
| `rug` | `(cx, y, d, sx, sz, edge = 'linenGrey')` | bound edge in a second tone |
| `vase` | `(x, y, d, { h, r, stems, spread, height, bloom, k = 'ceramic', seed })` | lathe vase, stems, two bloom tones |
| `curtain`, `curtainD` | `(x0, x1, y0, y1, d)`, `(x, d0, d1, y0, y1)` | pleated `sheer` from `softgoods.sheer` |
| `shade`, `lamp`, `pendantGlobe` | `(x, y, d, r0, r1, h)`, `(x, y, d, h = 0.55, shadeR = 0.17)`, `(x, y, d, drop = 0.9, r = 0.11)` | every one records its bulb in `kit.lamps` through `lampAt(x, y, d)` |
| `bed` | `(cx, d, y, w, len, headX, cover = 'linen', head = true)` → `{ foot }` | runs along `x`, head against the wall at `headX`; duvet with a rolled hem, throw, four pillows |
| `nightstand` | `(x, y, d, { lamp = true, books = false, flowers = false, seed })` | walnut cube with a lamp, a lamp and books, or flowers under a pendant |
| `books`, `tray` | `(x, y, d, ry = 0, n = 3)`, `(x, y, d)` | a stack with a cup; a brass tray with a carafe and a glass |
| `wardrobeAlongX`, `wardrobeAlongD` | `(x0, x1, y, d0, d1, h = 2.45, frontAtD1 = false)`, `(x0, x1, y, d0, d1, faceMinusX, h = 2.45)` | fluted `joinery` doors with brass `pulls()` at the meeting lines |
| `chair`, `loungeChair`, `plant`, `downlight`, `quadArt`, `quadArtX`, `M4` | | see pitfall 8 before placing many chairs |

`buildInterior(B)` → `{ spots, lights, lamps }`. Ground floor: floor slabs per finish, `paint` linings
with the shell's holes, kitchen door, ceilings skipping the stair void, downlight grids, stair GF→FF (19
risers), study nook, hall art, the shared living/dining items (the vase at `x 4.85, d 12.7` marks the
table position every style set shares), kitchen run, powder room. First floor: `of()` oak floors,
linings, five `door` calls, ceilings, stair FF→RF (18 risers), master (a lamp and books one side, flowers
under a pendant the other), master bath, corridor art, family bath, bedrooms 2 and 3, balconies. Roof
level: bedroom 4 (its door swung 1.45 rad flat to the wall so the route passes it straight), bathroom,
the potted tree on the gravel roof outside the landing glazing, terrace with fire bowl and two lanterns.
`lights`: four point lights `{ type: 'point', name, pos: [x, y, d], color, day, dusk, dist }` (hall,
livingWarm, ff, fire) that `main.js` fades with `smooth(tod, 0.25, 1.0)`; `lamps`: the bulb positions
the night pool parks its point lights on. Daylight indoors is the baked volume, not these.

## src/softgoods.js

Procedural cloth, no runtime simulation; used only by `bed`, `curtain` and `curtainD`. `drape({ L, W,
drop = 0.3, dropFoot = drop, dropL = drop, dropR = drop, r = 0.07, loft = 0.05, pleat = 0.03, crease =
0.028, fold = 0, hem = 0, under = null, seed = 1, res = 0.03 })` lays cloth on a box top (x 0..L from the
head, z across, top at y 0) and rolls it over the edges: `dropL`/`dropR` hang the two sides unequally (a
thrown throw), `fold` adds a corner fold, `hem` an uneven hem, `under(s, t)` lets a layer follow the lofted
surface beneath it (`loftAt` is exported for that); `geo.userData.head` holds the head-edge points for the
rolled-hem tube. `pillow({ L = 0.7, D = 0.48, T = 0.17, seed = 1, n = 16 })`: two faces at a piped seam with
a plumped dent. `sheer(w, h, seed = 1)`: x-y panel with pleats of uneven pitch.

## src/stylesets.js

`buildStyleSet(B, key, K)`: furniture for the three rooms the flight dwells in, one `if (key === ...)`
block per preset: `minimal`, `japandi`, `desert`, `luxe`. Each covers the living wall at `x 0.1`, the
sofa group around `x 2.9, d 12.75`, the dining table at `x 4.85, d 12.7` with chairs at `x ≈ 4.15 / 5.55`,
`d 12.1 / 12.7 / 13.3`, and the master bed at `x ≈ 4.85, d 5.05` with its head against the party wall
(`x 5.84–5.96`), a lounge chair at `(2.95, 4.05)` and a side table at `(2.85, 4.75)`. Extra helpers on top
of the kit: `S` (matrix with scale), `ellipsoid`, `oval`, `potPlant`, `cable`, `rug(cx, cd, w, l, y,
organic)`, `arch(...)`, `crescent` (seats on an arc), `barrel` (tub chair), `lantern` (pleated paper),
`dome`. `main.js` builds the chosen set at boot and the others when their chip is hovered or focused,
compiling each before it can show; a set's lamps go to `kitLamps[key]` for the night pool.

## src/styles.js

- `SET_AVG`: mean linear albedo of the 29 texture sets' colour maps, measured with the skill's
  `scripts/textures.py --measure`. A role with `albedo: 0xRRGGBB` gets colour `albedo / SET_AVG[set]`
  (`roleColor(o, set)`) so the finish *reads* as that colour whatever the scan's cast; the bake uses the
  same numbers. `SET_ROUGH`: mean of each set's roughness channel; `roleRoughness(rough, set, hasMap)`
  divides it out so a role's `rough` is the finish's real mean roughness (a polished scan at 0.037 would
  otherwise turn any authored roughness into a mirror). `materials.js` imports both helpers so the page's
  first frame and the styler agree.
- `STYLES`: `minimal`, `japandi`, `desert`, `luxe`, each `{ name, short, blurb, palette[6], sets[],
  art[5], inside, roles }`. `sets` are extra texture sets loaded on first use; `inside` multiplies indoor
  exposure in `main.js`; `roles` has 22 keys per style with fields `set, tile, color | albedo (+ flat),
  rough, metal, normal, env, sheen, clearcoat, joints [sx, sy, width, shade]`.
- `createStyler({ M, T, base, anisotropy, onLoading, releaseUnused = false })` → `{ apply(key), current,
  preload(key) }`. `apply` loads missing sets (a set enters `T` only once all three maps arrived; a
  failed load is forgotten so the next click retries), resolves every clone first so a switch is all or
  nothing, then per role swaps `map`/`normalMap`/`roughnessMap` (= `aoMap`) to clones cached by
  `set|channel|tile`, sets colour (or the albedo-corrected colour plus the `uFlat` uniform), roughness,
  metalness, normal scale, the authored env intensity `userData.envK` (the atmosphere multiplies it by
  the sky's `envScale`), sheen, clearcoat (floor 0.02), the joint uniform and the lamp-shade emissive;
  then regenerates `art1..3` from `st.art`. A request token makes the last click win. With
  `releaseUnused` (the `low` tier) the style-only sets no role on screen names are disposed, clones
  included. A role absent from `M` is skipped.

Caution: a role's `set` is swapped only if loaded, and only `sets` is loaded. List every set a preset's
roles name.

## src/materials.js

- `SETS`: the 18 base sets (`stone` is gone; `M.stone` is a dark marble); `INTERIOR_SETS` the seven seen
  only indoors (`travertine`, `woodfloor`, `oak`, `boucle`, `linen`, `velvet`, `rug`), which the live page
  loads as 1×1 placeholders (`placeholderSet`) and streams behind the first frame (`loadSet` then
  `adoptSet(M, name, set)`, which swaps every placeholder clone for a real one without a recompile).
  Style-only sets load lazily through the styler. A set is three WebPs in `assets/tex/` (`assets/tex/512/`
  on the phone tier): `<name>_c` (sRGB colour), `<name>_n` (OpenGL normal), `<name>_r` (R = AO, G =
  roughness), produced by the skill's `scripts/textures.py`.
- `loadTextureSets(base, anisotropy, onProgress, { defer })` → `T[name] = { c, n, r }`; load all, clone
  after (pitfall 1). `shared = { time, gi: { uGi0, uGi1, uGiA, uGiB, uGiDims }, lampMap: { uLampMap,
  uLampXf, uLampCol }, noise }`; `uGiDims` starts at `(1, 1, 1)` so the GI lookup fades out until `gi.js`
  fills it; `noise` is a 256 px tiling value-noise texture (`noiseTexture()`) the macro feature samples.
- `enhance(mat, o)`: one `onBeforeCompile` patcher keyed by feature set, so materials that differ only in
  uniform values share a program. Features: `joints { size, width, shade }` (tile joints by metre UV),
  `macro { scale, amount, hue }` (albedo variation from world xz, two fetches of the noise texture),
  `sway` (palm fronds), `glass [aMin, aMax]` (fresnel alpha), `flat` (`uFlat` pulls the texel towards a
  mean albedo), `shade` and `opal` (a lamp drum's rim-to-top gradient and hotter inside; an opal globe's
  darker rim), `gi` (`GI_FRAG` after `lights_fragment_maps`), `lampMap` (the baked street-lamp irradiance
  as Lambert diffuse, faded out above head height), `noPoint` (the point-light loop replaced by a
  zero-iteration copy of `lights_fragment_begin`, for finishes no interior light reaches: light count
  changes still recompile nothing). Uniforms land in `mat.userData.u`, the feature list in
  `mat.userData.fx`; `cloneEnhanced(m)` is the clone that keeps them (`Material.clone()` does not).
- `createMaterials(T, { maxAniso })` → `{ M, glow, water }`. `pbr(name, { tile, tileV, albedo | color,
  flat, rough, metal, normal, env, ao, side, physical, joints, macro, noPoint, lampMap })` builds a
  `MeshStandardMaterial` (or `MeshPhysicalMaterial` with `physical`) from a set, with `userData.set`
  and `userData.env0`. `emissive(color, day, dusk, extra)` registers a time-of-day glow; `glow` entries
  are `{ mat, day, dusk, prop? }`, lerped in `main.js` by `smooth(tod, 0.3, 0.95)`. Keys: architecture
  (`render`, `paint`, `ceiling`, `stone`, `bronze`, `frame`, `glass` and `glassRear` with their probes,
  `glassLight`, `wood`, `curb`, `equipment`), ground (`pavers`, `sidewalk`, `asphalt`, `grass`, `sand`,
  `base`, `desert`, `gravel`, `soil`, `patio`, `bark`), interior roles, emitters, vegetation cards, decor
  and LOD cards, waters, the beam cone. The last loop adds `gi: true` to every opaque
  `MeshStandardMaterial` except the waters.

`scripts/bake-gi.mjs` reads albedo from this file with `M\.(\w+) = pbr\('(\w+)', \{([^}]*)`; the
capture stops at the first `}`, so keep `albedo:`/`color:` ahead of any nested `joints`/`macro`/`physical`
object. Keys made with `std(...)` or a bare `new Mesh…Material` are not matched: give them an `ALB` entry
in the bake or they trace as 0.5 grey.

## src/proctex.js and src/vegetation.js

`proctex.js` draws canvas textures (needs a DOM, which is why the bake never imports `materials.js`):
`frondTexture()`, `foliageTexture({ seed, leaf, flower, flowerRatio, size, narrow })`,
`latticeTexture()`, `railTexture()`, `radialTexture(inner, outer, size)` (now unused), `artTexture(seed,
palette)`, `roomTexture()`, `roomDimTexture()`, `facadeAtlas()` → `{ map, emissive }` (front elevation in
u 0–0.5, rear in 0.5–1, v = height / 10.2), `waterNormals(size)`. `vegetation.js`: `palmGeometry({ radial,
rings, segs, every, flat })` → `{ trunk, fronds }` (crown at 7 m local; the defaults give the 1.1 k-triangle
model, `{ radial: 8, rings: 6, segs: 4, every: 2, flat: true }` the 190-triangle one), `bushGeometry(cards
= 14, seed = 2, flat = 0.75)`, `instancedFrom(geo, mat, matrices, { cast, receive })`.

## src/community.js

The hero plot's frame is the world frame; the estate is laid out on arcs about `CENTER = (3.05, 0,
-R)`, `R = 260` (`SPAN 0.62` rad, `BLOCK 7` units, `GAP 5` m, `PLOT_W 6.1`, `CROSS [-0.36, 0.34]`
cross-street angles). `rows`: eight rows by radius and `out` (which way fronts face), the hero row
`{ r: R, out: true, hero: true }`. Per row `step = (BLOCK * PLOT_W + GAP) / r`; blocks near a `CROSS`
angle become pocket parks; the hero's slot (`b === 0 && i === 3`) is skipped; alternate units are
mirrored. A unit whose reference point `(3.05, 0, -9)` is within 72 m of the hero's is *full* (instanced
shell plus `dressShell`), else *LOD*; the two attached neighbours (< 7 m) get no palm spots. The
non-hero shell's `room` quads are pulled out of the instanced geometry and drawn as `roomLit` or
`roomDim` (62 % of units lit); its `pool` quads are dropped. `dressShell(B, { lod })` is the rooftop kit
(pavers over the top slab, `curb`-coloured coping on parapets, planter and garden walls, two `equipment`
condensers with `frame` grilles, a `lodRoof` tank); `lodHouse(B)`: two body boxes, four `lod` quads on the
facade atlas, flat fills and the cheap form of the kit, hard-coded to this unit. Streets: five ring pairs
(`streets`), 2.2 m sidewalks, curbs, lamps every 26 m staggered per kerb, hero frontage kept clear; `ring()`
/ `curb()` write annulus sectors with world-metre UVs. Lamps: pole, arm, head and beam cone instanced,
beams named `lampBeams` (hidden by day). **`bakeLampMap(emitters)`** replaces the old additive pool
quads: every lamp head (h 5.0, within 15 m) and every full neighbour's car-port downlights, door strip and
patio strip (the hero contributes only its patio strip; its car port is in the baked volume) are splatted
on the CPU as `I cos³θ / d²`, windowed to zero, into an R8 `DataTexture` over the footprint (0.24 m per
texel, sqrt-encoded) that `shared.lampMap` hands to the ground materials; `main.js` sets `uLampCol` by the
lamp factor. Lagoon at `(-260, 0, -360)` rotated −0.6, semi-axes 170 × 85 m, with a beach
(`cloneEnhanced(M.sand)`) and 46 palms. Desert: a 4200 m plane of 130 segments, dunes from 470 m out.
Palms: `palmLOD()` keeps two `InstancedMesh` pairs (full model within 70 m of the camera, the light one
beyond), re-partitioned once the camera has moved 5 m; far palms and far houses cast shadows only from
the air (`setShadowZone`). Returns `{ group, stats, update(camPos), setShadowZone(zone) }`; `lite` (the
`low` tier) keeps half of the street, verge and far-house planting. Opaque community meshes get
`renderOrder 1` so the hero draws first.

## src/path.js

`KEYS`: keyframes `[progress, [x, y, z], [lookX, lookY, lookZ], fov, lensShift?]`, authored to the
`story.js` windows. `DronePath` builds a centripetal `CatmullRomCurve3` for position and interpolates
**orientation** as unwrapped yaw and pitch (never a look point: pitfall 19) plus monotone cubics
(`monotone(xs, ys)`) from progress to key index, fov and lens shift, so speed changes are smooth and a
repeated key holds. `sample(p, outPos, outLook)` → fov, with `outLook` a point 10 m along the view and
`path.shift` the lens shift for the rig; `override(pose)` fixes a pose for `?cam=` stills. `MAX_SHIFT =
0.5` (fractions of frame height). `DroneRig(camera).update(pos, look, fov, dt, time, { hover, still,
shift })` adds altitude-scaled hover, a bank of at most ±0.045 rad from yaw rate, a slerp lag, widens the
FOV in portrait and applies the shift through `camera.setViewOffset`, so a bed framed low keeps straight
verticals; `still` snaps everything for captures.

| Chapter (`story.js`) | Progress | Shot |
| --- | --- | --- |
| Arrival, The community | 0–0.13 | aerial, the house centred and pinned, descent over the lakes and terraces |
| Facade | 0.146–0.215 | orbit down to the street in front of the house |
| Ground floor | 0.235–0.31 | carport, front door, a glance at the kitchen, the hall |
| Living | 0.335–0.452 | an arc along the living room: sofa, table, glazing, back to the room |
| Garden | 0.474–0.505 | reverse pull-out through the open panel to a hold over the rear wall |
| Bedrooms | 0.521–0.58 | in from the rear balcony to a hold just inside bedroom 2's glazing |
| Master suite | 0.602–0.664 | through the door to a 3/4 view from the foot of the bed |
| Front balcony | 0.68–0.712 | out through the open panel to the balustrade, then a reverse dolly back |
| The stair | 0.728–0.784 | up the stair well to the roof landing and its window (the sun swings here) |
| Bedroom 4 | 0.80–0.866 | through the doorway past the open leaf to a hold inside |
| Roof terrace | 0.882–0.944 | out through the glazing, round to the sofa and fire bowl at sunset |
| Summary | 0.96–1 | rise and pull back to the right; the lit rear elevation at blue hour |

Rules the route is held to (`scripts/check-path.mjs` `LIMITS`): lens ≥ 0.3 m from any solid, authored
look targets ≥ 2.4 m from the lens, pitch −35°..+40°, yaw ≤ 12° and pitch ≤ 6° per 0.005 of progress,
lens shift within ±`MAX_SHIFT`, plus the story table's own rules. The template as checked out meets them:
`node scripts/check-path.mjs` exits 0 with no breach run. Keep it so after every key or wall change.

## src/atmosphere.js

`STATES`: `t 0` golden hour, `0.5` sunset, `1` blue hour, each `{ elev, turb, ray, mie, mieG, gain,
sun, sunCol, fog, fogD, exp, env, ground, disc }` (golden hour: turbidity 8.0, Rayleigh 1.1, Mie 0.004,
g 0.72, gain 0.82, sun 4.3 × (1, 0.81, 0.6), exposure 0.7, env 0.55; the same row is `SKY` in the bake);
`stateAt(t)` lerps and darkens fog with `smoothstep(t, 0.55, 0.92)` towards `TWILIGHT.horizon`.
`makeSky(scale)`: three's Preetham `Sky` with a patched fragment shader (twilight gradient, horizon melt,
gain, sun disc 25 not 760) and a few high wisps (`cloudCoverage 0.08`, `cloudDensity 0.7`). Main sky 9000,
env sky 400, stars 3600; camera far is 9000 (pitfall 3).

`Atmosphere(renderer, scene, { shadowMapSize, envCacheSize = 16, probeSize = 256, envBins = 'fine' })`:
`sun` (`DirectionalLight`, target `(3.05, 0, -9)`), `FogExp2`, environments from a small sky plus a ground
disc, built by `envFor(t, az, el)` → `build(bin)` and cached as PMREM render targets under the key of
`envBin()`: time of day in tenths, the −55° → −128° swing in three azimuth bins, elevation in 4° steps
anchored on the bake's 18° (`coarse`, the phone tier: fifths and two azimuth bins), about a dozen envs for
the whole evening. The cache is LRU, capped at `envCacheSize`, and never evicts `bakeKey` (the bake's
env, `envBin(0, -55, 18)`) or the env on screen; an evicted target is disposed. `prebuild(list, busy)`
builds the environments of a `[t, az, el]` schedule one per idle period while `busy()` is false, so a
sunset reached by scrolling finds its skies ready. `measure(key)` reads each env's mean radiance back
through `LightProbeGenerator` (asynchronous, pitfall 15; `onLevel` fires when it lands) and keeps it only
if finite and positive; `skyRatio()` is the current env's level over the bake's, clamped to [0, 4], the
last measured ratio while a read-back is pending, a fitted curve where nothing is measured yet.
`setShadowZone(zone)`: shadow half-size `{ aerial: 300, street: 60, house: 18 }`, target `(-40, 0, -20)`
aerial else `(3.05, 4, -9)`, per-zone bias and radius; the map re-renders only on zone or sun change
(`renderer.shadowMap.autoUpdate = false` in `main.js`). `setSun(az, el)` has a 0.15° deadband.
`update(t, time, az, el)` → state, or `null` when nothing changed: it assigns the env map and the authored
intensity times the sky's (`userData.envK × envScale`) to every lit material (`refreshMaterials()`
rebuilds that list; call it after adding objects), renders the two reflection probes (`front` and `rear`
cube cameras the glazing mirrors through `userData.probe`) at steps of the evening, and fades the stars.
Azimuth runs from `+z` towards `+x`: −55° is south-west of a house whose street is at `+z`.

## src/gi.js and assets/gi

`scripts/bake-gi.mjs` writes one JSON per component, `{ spacing: 0.5, min: [0, 0, -15.6], dims: [13,
22, 30], stride, data }` with `data` base64 at 6 bytes per probe (7 for `S`, which adds the open-sky
fraction): rgb DC as `2^(v/255*20 - 14)` then a luminance gradient relative to the DC. Components: `S`
sky, `U` sun bounce for the held sun (−55°, 18°), `U2` sun bounce for the swung sun (−128°, 11.5°),
`N-<style>` that style's lamps. They live beside the textures because the artifact host refuses `.bin`
(pitfall 18) and so that the bundle carries no data only one style needs. `createGI({ base, style })`
starts the fetches at once (`main.js` calls it before the textures): `ready` resolves when `S`, `U`, `U2`
and the boot style's `N` are decoded (the browser's own base64 decoder through a `data:` fetch, `atob`
where a sandbox refuses it), the two `HalfFloat` `Data3DTexture`s exist and `shared.gi.uGiA/uGiB` are set;
`prepare(style)` fetches another lamp set ahead of a switch; `set(kS, kU, kU2, kN, style)` re-mixes
`kS·S + kU·U + kU2·U2 + kN·N[style]` on the CPU (texture 0 alpha = `inside`, texture 1 alpha = the
open-sky fraction the shader uses for specular occlusion), skipping when the quantised weights are
unchanged, and writes `uGiDims`, which un-fades the shader lookup; a style whose lamps have not arrived
borrows the first set loaded. The shader half (`GI_FRAG` in `materials.js`) samples at `vWPos + normal *
0.22`, fades near the volume edge, reconstructs the L1 lobe non-linearly (pitfall 14), replaces
`iblIrradiance` where `inside` and dims reflections by the open-sky fraction (or the irradiance ratio where
the alpha is 0).

## src/post.js and src/volumetric.js

`createPost(renderer, scene, camera, { ao, aoQuality, halfRes, bloom, smaa, vol, aoZones, sun, volSteps })`
→ `{ composer, aoPass, bloomPass, final, volPass, hdr, setSize(w, h, dpr), setAO(on) }`. Without
renderable half-float buffers (`hdr` false) AO, bloom and the march are dropped and the chain runs on
8-bit targets. The chain is two full-resolution passes: `N8AOPass` (beauty + AO; `aoRadius 0.6`
overridden per zone in `main.js`, `intensity 3.0`; the `depthDownsampleTarget.texture` getter patched for
r187, pitfall 2) or a plain `RenderPass` (the `low` tier swaps between them per zone through `setAO`),
then `FinishPass`, which samples the march's half-size target and the bloom mips, adds them in linear
light, tone-maps (ACES), encodes, and grades (split tone, `uVignette 0.32`, `uGrain 0.022`). `BloomPass`
is `UnrealBloomPass` without its final blend (strength 0.2, radius 0.32, threshold 9.0 at construction;
`main.js` drives threshold and strength each frame from `LOOK`). `SMAAPass` is last and enabled while the
pixel ratio is under `SMAA_MAX_DPR = 1.75`.

`VolumetricPass({ camera, sun, getDepth, steps = 28, scale = 0.5 })` raymarches the sun's shadow map into
its own target (sun term, ambient term, 1 − transmittance), blurred; uniforms are exposed as `pass.u`
(`uDensity`, `uDensityIn`, `uMaxDist`, `uG 0.6`, `uHeightK`, `uHeightScale`, `uSunIn/Out`, `uAmbIn/Out`,
`uSteps`) and composite colours as `pass.sunCol`, `pass.ambCol`. `uBoxMin (0.1, 0.25, -14.85)` / `uBoxMax
(6.0, 9.7, -3.55)` is the house envelope in which air is dusty and beam-forming: **this plot's numbers**.
`makeDust(boxes [[x0, x1, y0, y1, d0, d1]...], perCubic, seed)` scatters motes lit only where the shadow
map says sun reaches, energy-conserving (a near sprite grows but does not brighten); `beamMaterial(color)`
is the lamp cone.

## src/ui.js

`planSVG(floor, highlight, { stair, labels })` draws that floor's `ROOMS` at 10 px/m, street on the left
(`d` horizontal, `x` flipped so `x = PLOT.w` is at the top). `printSheet()` appends a print-only section
with the three floors labelled and sized from `plan.js` and `FACTS`. `initUI({ onMode, onJump, onStyle,
styles })` reads the DOM once → `{ progress(f, text), setStyle(k), styleLoading(b), ready(), fatal(msg),
update(p, camera, pinWorld, w, h) }`. Cards are every `.card` with `data-chapter="<key>"` (an unknown key
throws); a child `.plan[data-floor][data-room="key,key"]` receives a `planSVG`, `[data-style-line]` the
style's swatches and blurb, `.eyebrow .n` the chapter's number. The rail is one button per `CHAPTERS` row
landing on `jump`; arrow, page, space, Home and End keys step between chapters; a live region announces the
chapter once the visitor settles on it. In `update`, one chapter is active (`chapterAt`), each card fades
over ±`FADE` around its window, the style pill shows within `STYLE_PILL`, a toast explains the sunset once
in auto mode, and the plot pin is projected from `pinWorld` within `PIN.windows`. `fatal()` keeps the loader
as a page with the poster and the facts when WebGL is missing. The style chip's click keeps the promise
`onStyle` returns and swallows its rejection; `main.js` reports failures itself.

## src/main.js

Query parameters: `?p=0.42` renders one still at that progress (`STILL`, `FIXED_P`), `?q=high|mid|low`
forces a tier, `?tod=day|night` forces time of day, `?ui=0` adds `body.noui`, `?style=` or `#japandi`
picks the style (hash wins; `pickStyle` admits only `STYLES` keys), `?cam=x,y,z,lx,ly,lz[,fov[,shift]]`
places the camera for a still, `?hide=name,name` hides scene objects by name in a still (`sheer`,
`lampBeams`, `dust`, any material key).

Start-up: `initUI`, the renderer (a `fatal()` page without WebGL; a context loss shows a notice and
reloads on restore), `detectTier` and `TIERS[TIER]` (the `low` tier adds `body.lowfx`), the size from the
canvas box through `pixelRatioFor` × `AdaptiveScale` and a debounced `ResizeObserver`; `createGI()` starts
the GI fetches **before** the textures; `loadTextureSets` (loader 0.03–0.65; `INTERIOR_SETS` deferred on
the live page, awaited for a still), `createMaterials`; the hero shell, interior and `dressShell` into one
`Builder` (the `pool` bucket dropped, `renderOrder` sheer 1 / glass 2); the chosen style set now, the
others on chip hover or focus (`ensureStyle`, compiled before they can show), each kit's lamps kept in
`kitLamps`; the styler (`releaseUnused` on `low`, the boot `apply` falling back to `minimal`);
`buildCommunity`; the four fixed point lights and the night **lamp pool** (`LOOK.lampPool` point lights,
`placeLamps()` parks them each frame on the bulbs nearest the camera among `interior.lamps` and the current
kit's, cross-fading over about 0.4 s; the count never changes, so no program recompiles); `Atmosphere`
with `envCacheSize`, `probeSize` and `envBins` per tier, then `atmo.envFor(0, -55, 18)` to seed the GI
reference env; `createPost`; `makeDust` (plan-unit boxes; `dust.name = 'dust'`); `pinWorld (3.05, 11.5, -9)`.
Helpers: `zoneFor(c)` (`aerial` above `y 42`, `house` inside the plot box or its margin, else `street`),
`inHouseBox(v)` (the rooms proper: `x 0.1–6.0`, `z -3.5…-14.85`, `y < 9.7`, minus the terrace),
`viewCrossing(c)` (how far along the view the rooms begin, from outside, or end through a front, rear or
roof face, from inside; party walls never count), `todAt(p)`, `sunAt(p)` → `{ swing, az, el }` from
`story.js`'s `SUN`.

`update(dt, time)`: eased progress; `tod = todAt(progress)` eased; the sun from `sunAt`; `atmo.update`;
zones; the exposure model: `inside` eases to `max(camIn, lookIn)` where `lookIn = LOOK.lookInExposure`
when the view enters the rooms within 7.5 m, `lookOut` eases to `camIn × LOOK.lookOutExposure` when the
view leaves them through glazing, `shade` to 1 behind the house; `expIn = st.exp × lerp(1,
lerp(insideExposureDay, insideExposureNight, tod) × STYLES[style].inside, inside)`; `expTarget =
lerp(expIn, st.exp, lookOut) × lerp(1, gardenShadeExposure, shade)`; bloom `threshold = bloomThresholdK /
exposure`, `strength = bloomStrength`; AO radius per zone; the glow list by `lamp = smooth(tod, 0.3,
0.95)`; `placeLamps`; `shared.lampMap.uLampCol = (1, 0.79, 0.54) × streetLamp × lamp`; `gi.set(sky =
skyRatio × st.env × giFill × giWhiteBalance, sunHeld = sunColour / (1, 0.81, 0.6) × intensity / 4.3 ×
giFill × giSunBalance × (1 − swing), sunSwung = the same × swing, lamps = giLamp × lerp(giLampDay, 1,
lamp), style)` every third frame while the light eases; dust and volumetric uniforms per zone; the fixed
point lights; returns whether anything is still converging. Warm-up: `await` the GI, one `update`, beams
and dust shown for `renderer.compileAsync`, then hidden. `applyStyle(k)` awaits the styler, the furniture
group and the style's lamp set together, shows a toast and keeps the old style if any fails, skips if a
later click superseded it, else toggles groups, refreshes shadows and writes `#style`. After `ui.ready()`
the evening's environments are prebuilt in idle time (`atmo.prebuild` over p 0.72–1.0 in auto mode).
`STILL`: removes the loader, applies `?cam=` and `?hide=`, waits up to 1.5 s for two sky read-backs,
renders three settle frames, logs `[t] settled · calls · tris · programs · textures`, sets `window.__shot`.
The live page then streams the deferred sets and runs the loop: render only while `awakeUntil` (1.6 s
after any scroll, resize, visibility or UI event) or while converging; `AdaptiveScale.frame()` decides the
rung and `applySize()` re-allocates.

## index.html and style.css

`index.html`: `canvas#scene`; `#loader` with `.bar i`, `.label`, `.pct` and the poster; `header.top` with
the brand and `[data-mode]` Auto/Day/Night buttons; `.styles#styles` (buttons appended by `ui.js`);
`#toast`; `#live` (screen-reader status); `nav#rail`; `.meter`; `#pin`; `#cards` with thirteen
`section.card`s, each `data-chapter="<story.js key>"`: the hero card, eleven chapters, the `outro`
summary. Chapter cards carry `.eyebrow` with an empty `.n` (filled from the table), `h3`, copy, a
`button.more` that opens `.detail` on phones (`dl.figs`, `dl.times`, the `.plan[data-floor][data-room]`),
and optionally `p.style-line[data-style-line]`. `main#scroll` is the scroll spacer; the module script is
`dist/app.js`. The summary card holds the areas table, the three actions (replay, copy link, print) and the
disclaimer; it names no price or payment plan.

`style.css`: `#scroll { height }` is the scroll length; progress is `scrollY / (scrollHeight -
innerHeight)`. Brand accent `--violet`; cards bottom-left; `.plan-svg` classes style the mini-plans;
`body.ready` reveals the chrome, `body.noui` hides it, `body.lowfx` and `@media (pointer: coarse)` swap
the overlay's backdrop blur for solid glass; `#print-plans` shows only in print.

## scripts/

`bake-gi.mjs` (Node, `three-mesh-bvh`): `RAYS` from the environment (default 256), `PASSES 3`, probe
grid `SP 0.5`, `MIN [0, 0, -15.6]`, `DIMS [13, 22, 30]`, i.e. x 0–6, y 0–10.5, depth 1.1–15.6 m: this
house and nothing else. `ALB` gives albedo for untextured keys (`equipment`, `lodRoof`, `charcoal`...);
textured keys come from `materials.js` text; `albedoFor(style)` applies the roles. `SKIP` lists keys that
do not block light. `LAMP`: `downlight 18` (downward cos² lobe), `bulb 4`, `lampShade 6`, `led 1.2` per
0.6 m, `fire 8`, each with a softening radius. Scene: hero shell and interior; non-hero shells at `x ± 6.1`
(mirrored about 3.05) and `± 12.2`; two opposite rows rotated 180° at `z -37` and `z +12`; a ground quad.
`sunDir` (−55°, 18°) lights the sky and `U`; `SUN_DIRS.U2` (−128°, 11.5°) lights `U2`; `SUN` (`4.3 ×
sunCol`) and `SKY` must match `atmosphere.js` `STATES[0]`. `maskFor` marks probes with > 25 % back-face
hits, `fill` refills them from neighbours, `pass` traces one bounce lit by the previous pass's probes,
`bake` runs `S`, `U` and `U2` once (minimal scene) and `N` per style, `write` emits `assets/gi/<name>.json`.
`npm run bake` takes about twelve minutes at 256 rays (`RAYS=16 npm run bake` for a quick look); no
rebuild is needed afterwards, the page fetches the files.

`check-path.mjs`: `LIMITS` (clearance, look distance, pitch, yaw and pitch rates, lens shift, caption
gap); solids from the hero shell, its interior and the two attached neighbours mirrored at `±6.1` (the roof
kit is not in it); a 0.5 m cell grid; samples every 0.001 of progress; prints breach runs named by the
chapter being read, a per-chapter table (span, yaw swing, pitch range, authored look distance, clearance)
and checks the story table; exits 1 on any breach. `node scripts/check-path.mjs [--verbose]`.

`capture.cjs`: `node scripts/capture.cjs <baseUrl> <outDir> <q> <p1,p2,...> ["&ui=0"]`, `W`/`H` env
(default 1024 × 576); headless Chromium on SwiftShader, waits for `window.__shot` (600 s), screenshots
with a 180 s timeout (pitfall 16), writes `out/p<p>.png`, prints `[t]` timings and console errors. Serve
first (`npm run serve` under `nohup`, pitfall 17). `playwright` is not in `package.json`: here it resolves
from the global install; elsewhere install it and run `npx playwright install chromium`. Tile stills with
the skill's `scripts/sheet.py <dir> <out.jpg> <columns> <thumb-width>`.

## package.json and the build

`"type": "module"`. Scripts: `build` (`esbuild src/main.js --bundle --minify --format=esm --target=es2020
--outfile=dist/app.js --legal-comments=none`), `dev` (unminified, sourcemap, `--watch`), `serve`
(`python3 -m http.server 8080`), `bake`. Dependencies `three ^0.187.0`, `n8ao ^2.0.1`, `postprocessing
^6.39.6` (n8ao's peer), `esbuild ^0.28.2`; dev `three-mesh-bvh ^0.9.18` (bake only). `dist/app.js`
(994 KB minified, 338 KB gzip, no GI data) is committed and `.gitignore` re-includes it with
`!dist/` because the published page serves the bundle (pitfall 9); `assets/gi/*.json` (about 490 KB in
seven files) are committed for the same reason. Module scripts need a server, not `file://`.

## Adapting to a new property

Work in this order, rendering a still (`?p=`) after each step: `plan.js` → `house.js` → `interior.js`
(watch for `missing material`) → `stylesets.js` → `community.js` → `story.js` and `path.js` with
`check-path.mjs` → `index.html` cards → `volumetric.js`/`main.js` boxes → `bake-gi.mjs` → `npm run build` →
contact sheets at every chapter's `jump`.

| File | Change? | What exactly |
| --- | --- | --- |
| `src/plan.js` | must | `PLOT`, `H` levels (add or drop a floor), `FACTS`, every `ROOMS` entry (`key`, `name`, `x`, `d`, `size`), `STAIR` |
| `src/story.js` | must | every `CHAPTERS` row (`key`, `rail`, `from`, `to`, `jump`); `TOD`, `SUN`, `PIN` and `STYLE_PILL` follow from the rows they name |
| `src/house.js` | must | every wall, slab, parapet and planter in the four sections; each `wallX`/`wallD` hole with its `glaze` (and `'glassRear'` where it faces the garden); door position and swing; railings, slats, lattice; the non-hero `room` quads; spots |
| `src/interior.js` | must | floor slabs per finish, `paint` linings with the shell's holes, doors, ceilings and downlight grids, both stairs, kitchen, bathrooms, fixed joinery, decor, the four `lights`; keep every lamp going through the kit so `lamps` stays complete |
| `src/stylesets.js` | must | furniture positions in all four blocks to the new living, dining and master rooms; keep one table position shared by every style |
| `src/community.js` | usually | `PLOT_W`, `BLOCK`, `GAP`, `rows`, `streets`, `CROSS`, the `(3.05, 0, -9)` hero reference and `mirrorX(…, 3.05)` (half the new width), `dressShell` and `lodHouse` to the new massing, the fittings list in the lamp map, lagoon and desert placement; or replace the arc layout for a different estate |
| `src/path.js` | must | every row of `KEYS`; keep ≥ 2.4 m look distance and ≥ 0.3 m clearance; re-run `check-path.mjs` until it exits 0 |
| `src/main.js` | must | `zoneFor`, `inHouseBox` and the garden-shade box, dust boxes, `pinWorld`, the sun schedule in `sunAt` if the terrace faces elsewhere, loader copy; the tiers only if the new scale demands |
| `src/look.js` | usually | `LOOK`, after the first bake and stills: `giFill`/`giSunBalance` if interiors read dark or tan, `insideExposureDay/Night` for the indoor stop, `giLamp`/`streetLamp` for the night |
| `src/volumetric.js` | must | `uBoxMin`/`uBoxMax` to the new interior envelope |
| `src/atmosphere.js` | usually | `sun.target` and the house-zone target to the new plot centre; `STATES`, the `-55 / 18` sun in `envBin`'s anchor, `main.js`'s `envFor(0, -55, 18)` and `sunAt` only if the orientation changes (then the bake's `sunDir`, `SUN_DIRS`, `SUN` and `SKY` too) |
| `src/styles.js` | usually | palettes, blurbs, `art`, role colours per brief; `SET_AVG` and `SET_ROUGH` entries for new texture sets; `roles` keys only if `materials.js` gains or loses a role |
| `src/materials.js` | usually | add sets to `SETS` and one-line `pbr` entries for new finishes (with `noPoint`/`lampMap` for exterior ground); facade palette (`render`, `stone`, `bronze`, `frame`) |
| `src/proctex.js` | usually | `facadeAtlas()` elevations to the new facade |
| `src/tiers.js`, `src/ui.js` | leave alone | tiers describe devices; `ui.js` reads `plan.js` and `story.js` |
| `src/gi.js`, `assets/gi/` | regenerate | never hand-edit; `npm run bake` after any wall, furniture or lamp change |
| `src/builder.js`, `src/softgoods.js`, `src/vegetation.js`, `src/post.js` | leave alone | generic |
| `index.html` | must | `<title>`, meta, loader and brand copy, every card's `data-chapter`, eyebrows, copy, `dl.figs` figures, `.plan[data-floor][data-room]` keys, the summary table and fine print |
| `style.css` | usually | `#scroll` height if the route is much longer or shorter; `--violet` accent to the brand |
| `scripts/bake-gi.mjs` | must | `MIN`/`DIMS` to cover the new envelope at `SP 0.5` (probe count drives bake time), the neighbour layout and `mirrorX(g, 3.05)` centre, `ALB` for new untextured keys, `LAMP` for new emitter keys, `sunDir`/`SUN_DIRS`/`SUN`/`SKY` if the sun moves |
| `scripts/check-path.mjs` | usually | attached-neighbour offsets and `mirrorX(g, 3.05)` centre to the new plot width; `LIMITS` stay |
| `scripts/capture.cjs`, `package.json` | leave alone | `name` and `description` only |
| `assets/tex/` | usually | add sets with the skill's `scripts/textures.py` (then `--downscale 512` for the phone tier), then `SET_AVG` and `SET_ROUGH` |
