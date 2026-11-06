# Template architecture: `violet2-flythrough`

The per-file map of the reference build the skill copies as its template. Read `decisions-and-pitfalls.md`
(same folder) first: it says *why* the whole is shaped as it is; this file says *where* each piece lives,
what it exports and what to touch for a different property. Every path, identifier, number and line
reference was read from the code at the time of writing; re-check line numbers once your edits move things.

## Contents

[Dependency map](#dependency-map) · [Conventions](#conventions-that-cross-every-file) · [plan.js](#srcplanjs) ·
[builder.js](#srcbuilderjs) · [house.js](#srchousejs) · [interior.js](#srcinteriorjs) · [softgoods.js](#srcsoftgoodsjs) ·
[stylesets.js](#srcstylesetsjs) · [styles.js](#srcstylesjs) · [materials.js](#srcmaterialsjs) ·
[proctex.js and vegetation.js](#srcproctexjs-and-srcvegetationjs) · [community.js](#srccommunityjs) · [path.js](#srcpathjs) ·
[atmosphere.js](#srcatmospherejs) · [gi.js and gi-data.js](#srcgijs-and-srcgi-datajs) · [post.js and volumetric.js](#srcpostjs-and-srcvolumetricjs) ·
[ui.js](#srcuijs) · [main.js](#srcmainjs) · [index.html and style.css](#indexhtml-and-stylecss) · [scripts/](#scripts) ·
[package.json and the build](#packagejson-and-the-build) · [Adapting to a new property](#adapting-to-a-new-property)

## Dependency map

`src/main.js` is the only entry point (esbuild bundles it to `dist/app.js`); it imports every other
module, directly or through them, and nothing imports it.

| Module | Imports from the template | What flows out |
| --- | --- | --- |
| `plan.js` | nothing | `PLOT`, `H`, `ROOMS` → `house.js`, `interior.js`, `stylesets.js` (levels) and `ui.js` (rooms, plot) |
| `look.js` | nothing | `LOOK` (eight photographic constants: GI fill and lamp weights, white balance, indoor exposure, dust brightness) → `main.js` only |
| `builder.js` | nothing | `Builder`, `F`, `mirrorX`, `meshes`, `instanced` → every geometry module and both scripts |
| `house.js` | `plan.js` (`H`), `builder.js` (`F`) | `buildShell(B, {hero})` → `main.js` (hero), `community.js` (neighbours), both scripts |
| `interior.js` | `plan.js`, `builder.js`, `softgoods.js` | `makeKit`, `buildInterior` → `main.js`, `stylesets.js` (via the kit), both scripts |
| `stylesets.js` | `plan.js`, `vegetation.js` | `buildStyleSet(B, key, kit)` → `main.js`, `bake-gi.mjs` |
| `styles.js` | `proctex.js` (`artTexture`) | `STYLES`, `SET_AVG`, `createStyler` → `main.js`, `bake-gi.mjs` (`BASE_SETS` is also exported; nothing reads it) |
| `materials.js` | `proctex.js`, `volumetric.js` (`beamMaterial`) | `loadTextureSets`, `createMaterials` → `M`, `glow`; `shared` uniforms → `gi.js` |
| `gi.js` | `gi-data.js`, `materials.js` (`shared`) | `createGI().set(...)` fills the two 3D textures `materials.js` samples |
| `community.js` | `builder.js`, `house.js`, `vegetation.js` | `buildCommunity(M, spots, {lite})` → `{ group, stats }`; also exports `R`, `CENTER` |
| `atmosphere.js` | three addons only | `Atmosphere` (sun, sky, fog, env map, shadow zones) → the frame loop |
| `path.js` | nothing | `DronePath`, `DroneRig` → the frame loop and `check-path.mjs` |
| `post.js` | `volumetric.js` (`VolumetricPass`), n8ao | `createPost(...)` → the composer the loop renders |
| `ui.js` | `plan.js` | `initUI(...)` → DOM overlay handle |
| `scripts/bake-gi.mjs` | `builder`, `house`, `interior`, `stylesets`, `styles`; reads `materials.js` as text | writes `src/gi-data.js` |
| `scripts/check-path.mjs` | `builder`, `house`, `interior`, `path`; reads `index.html` as text | report and exit code |

Flows to hold in your head: **plan → geometry and plan → SVG** (`ROOMS` draws the mini-plans, `H`
positions floors and stairs, but walls are hand-placed in `house.js` and `interior.js` from the same
numbers, so a plan change is a three-file edit); **material keys → meshes** (geometry names a string
key, `meshes()` resolves it against `M` at the end; an unknown key is `console.warn('missing material',
k)` and the geometry is silently dropped, so grep the console after every geometry edit); **styles →
materials, not geometry** (`createStyler().apply` mutates materials in `M` in place; a style's only
geometry is its `buildStyleSet` group, toggled by visibility); **atmosphere → GI → shaders** (each
frame `atmo.update()` returns a state, `main.js` turns it into three rgb weights for `gi.set(sky,
sunBounce, lamps, style)`, which re-mixes the baked volume into two `Data3DTexture`s every opaque
material samples through `shared.gi`); **post chain** `N8AOPass` (plain `RenderPass` on `low`) →
`VolumetricPass` → `UnrealBloomPass` → `OutputPass` → `FinalShader` → `SMAAPass`.

## Conventions that cross every file

- **Plan coordinates.** `x` across the plot (0 = left party line seen from the street, `PLOT.w` 6.1
  on the right), `d` depth from the street line (0) to the rear boundary (`PLOT.d` 18.5), `y` height.
  World `z = -d`. Each geometry module defines `bx(k, x0, x1, y0, y1, d0, d1, faces)` calling
  `B.box(k, x0, x1, y0, y1, -d1, -d0, faces)` (`house.js:11`, `interior.js:17`, `community.js:19`);
  `interior.js` adds `M4(x, y, d, ry, rx, rz)`, a matrix at `(x, y, -d)` with Euler order `YXZ`.
  `path.js` keyframes are already world `z`: a camera 9.7 m from the street is written `-9.7`.
- **Metre UVs.** `Builder.box` writes UVs as metres along each face's own axes, so a wall cut around
  an opening keeps one continuous texture. `Builder.add(k, geo, m, 'box')` re-projects UVs by dominant
  normal in the geometry's *local* space × `uvScale`; `'keep'` retains the geometry's UVs. In
  `materials.js`, `pbr(name, { tile })` sets `repeat = 1 / tile`: `tile` is metres per repeat.
- **Face flags.** `F = { PX: 1, NX: 2, PY: 4, NY: 8, PZ: 16, NZ: 32, ALL: 63 }`. Floors `F.PY`,
  ceilings `F.NY`, panes `F.PZ | F.NZ`. Skipped faces are where the triangle budget is saved.
- **Material keys** name the role a surface plays (`render`, `paint`, `ceiling`, `stone`, `joinery`,
  `oakFloor`, `frame`, `glass`, `bronze`, `brass`, `led`, `downlight`, `bulb`, `lampShade`, `fire`...).
  Styles re-parameterise only the keys in `STYLES[key].roles`; the rest keep their `materials.js` definition.
- **Hero versus neighbour.** `buildShell(B, { hero })` is built twice: hero (`main.js:86`: real
  balusters, slid-open panels, open door) and non-hero (`community.js:102`: `rail` alpha cards, fake
  lit `room` quads), the latter instanced and mirrored with `mirrorX(geo, 3.05)` for alternate units.
  Both return planting spots `{ bush, flower, palm, olive, pink }` as `[x, y, d, scale]` for `community.js`.

## src/plan.js

Single source of truth (47 lines). `PLOT = { w: 6.1, d: 18.5, areaM2: 112.85 }` (line 6).
`H = { G: 0.05, F0: 0.25, C0: 3.25, F1: 3.55, C1: 6.5, F2: 6.8, C2: 9.7, R2: 10.0 }` (line 9):
plinth, ground floor and ceiling, first floor and ceiling, roof-level floor and ceiling, roof top;
slabs 0.3 m, storeys 2.9–3.0 m clear. `FACTS` (11–21): project, unit, type, beds, parking,
completion, saleable areas; nothing imports it, the cards repeat the figures by hand. `ROOMS`
(23–44): 20 entries `{ f, key, name, x: [x0, x1], d: [d0, d1], size? }` on floors 0/1/2; `key` is
what `.plan[data-room]` in `index.html` names. `STAIR = { x: [0.1, 2.95], d: [6.65, 9.45] }` (47),
also unimported; the stair in `interior.js` uses the numbers directly. Why so small: a room here only
has to be right for the mini-plan; 3D walls carry thicknesses, nibs and openings a rectangle cannot.

## src/builder.js

`class Builder`: `bucket(k)`; `box(k, x0, x1, y0, y1, z0, z1, faces = F.ALL)` (sorts corners, drops
boxes thinner than 1e-4); `add(k, geo, matrix = null, uv = 'keep' | 'box', uvScale = 1)` (flips
winding when the matrix determinant is negative); `quad(k, p0, p1, p2, p3, uv)` (counter-clockwise
from the front); `geometries()` → `Map<key, BufferGeometry>` (Uint32 index above 65 535 vertices).
`mirrorX(geo, cx)`; `meshes(geos, mats, { cast, receive })` → `Group` of one `Mesh` per key with
`matrixAutoUpdate = false`; `instanced(geos, mats, matrices, ...)` → one `InstancedMesh` per key.
A material with `userData.noShadow = true` never casts (glass, sheers, emitters, light pools).

## src/house.js

`buildShell(B, { hero = false })` → spots. Helpers in plan units: `wallX(k, x0, x1, y0, y1, d0, d1,
holes = [[x0, x1, y0, y1]])` (wall along `x`, split around openings) and `wallD(k, x0, x1, y0, y1, d0,
d1, holes = [[d0, d1, y0, y1]])` (along `d`), both duplicated verbatim in `interior.js`; `glaze(x0, x1,
y0, y1, d, panels = 1, open = null, glassKey = 'glass')` (black frame and panes in plane `d`; `open`
slides one panel behind its neighbour, hero only, written `hero ? n : null` with the panel index chosen
per opening at 140, 159, 175, 178 and 203); `glazeD(x, d0, d1, y0, y1)`
(one pane in plane `x`); `railing(alongX, a0, a1, y, at, ht = 1.1)` (`bronze` balusters when hero,
else one `rail` card); `slats(x0, x1, y0, y1, d0, d1, pitch = 0.16, w = 0.045)` (pergola);
`latticeD(x, d0, d1, y0, y1)`; `room(...)` (non-hero lit quads, lines 228–237).

Sections: site 94–113 (pavers, planters, garden walls, rear palm and shrub spots); ground floor
115–142 (party walls, kitchen window, stone recess with the walnut door at `x 1.95, d 6.62` swung 82°
when hero at 125–133, four-panel rear glazing); first floor 144–182 (slabs, balcony fronts, pergola,
lattice); roof 184–226 (bedroom 4 box, pergola, terrace railings). Every opening is a hole in
`wallX`/`wallD` *and* a `glaze` at the wall's mid-plane; `interior.js` repeats the same holes in its
12 mm `paint` linings, or a window shows a wall behind it.

## src/interior.js

`makeKit(B, spots)` (15–215) returns the placement kit shared by the fixed interior and the style sets:

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
| `bed` | `(cx, d, y, w, len, headX, cover = 'linen', head = true)` → `{ foot }` | runs along `x`, head against the wall at `headX`; duvet, rolled hem, throw, four pillows |
| `wardrobeAlongX` | `(x0, x1, y, d0, d1, h = 2.45, frontAtD1 = false)` | fluted `joinery` doors |
| `wardrobeAlongD` | `(x0, x1, y, d0, d1, faceMinusX, h = 2.45)` | |
| `chair`, `loungeChair` | `(x, d, ry, seatK = 'boucle')`, `(x, y, d, ry, k = 'velvet')` | `ry` is yaw; see pitfall 8 before placing many |
| `downlight`, `lamp`, `pendantGlobe`, `plant`, `nightstand`, `quadArt`, `quadArtX`, `M4` | | |

`buildInterior(B)` (217–510) → `{ spots, lights }`. Ground floor 222–323: floor slabs per finish,
`paint` linings with the shell's holes, kitchen door, ceilings skipping the stair void, downlight
grids, stair GF→FF (19 risers, 245–269), study nook, hall art, the shared living/dining items (the
vase at `x 4.85, d 12.7`, line 285, marks the table position every style set shares), kitchen run,
powder room. First floor 325–447: `of()` oak floors, linings, five `door` calls, ceilings, stair
FF→RF (18 risers, 354–380), master, master bath, corridor art, family bath, bedrooms 2 and 3,
balconies. Roof level 449–500: bedroom 4, bathroom, terrace with fire bowl. `lights` (503–508): four
point lights `{ type: 'point', name, pos: [x, y, d], color, day, dusk, dist }`; `main.js:113–118` negates
`d` and `main.js:230` fades them with `smooth(tod, 0.25, 1.0)`. Daylight indoors is the baked volume, not these.

## src/softgoods.js

Procedural cloth, no runtime simulation; used only by `bed`, `curtain` and `curtainD`. `drape({ L, W, drop = 0.3,
dropFoot = drop, r = 0.07, loft = 0.05, pleat = 0.03, seed = 1, res = 0.03 })` lays cloth on a box top (x 0..L
from the head, z across, top at y 0) and rolls it over the edges; `geo.userData.head` holds 41 head-edge
points for the rolled-hem tube. `pillow({ L = 0.7, D = 0.48, T = 0.17, seed = 1, n = 16 })`: two faces at a
piped seam with a plumped dent. `sheer(w, h, seed = 1)`: x-y panel with pleats of uneven pitch.

## src/stylesets.js

`buildStyleSet(B, key, K)`: furniture for the three rooms the flight dwells in, one `if (key === ...)`
block per preset: `minimal` 79–117, `japandi` 120–178, `desert` 181–226, `luxe` 229–279. Each covers
the living wall at `x 0.1`, the sofa group around `x 2.9, d 12.75`, the dining table at `x 4.85,
d 12.7` with chairs at `x ≈ 4.15 / 5.55`, `d 12.1 / 12.7 / 13.3`, and the master bed at `x ≈ 4.85,
d 5.05` with its head against the party wall (`x 5.84–5.96`), a lounge chair at `(2.95, 4.05)` and a
side table at `(2.85, 4.75)`. Extra helpers on top of the kit: `S` (matrix with scale), `ellipsoid`, `oval`,
`potPlant`, `cable`, `rug(cx, cd, w, l, y, organic)`, `arch(k, x, d0, d1, y0, straight, depth, toMinusX)`,
`crescent` (seats on an arc), `barrel` (tub chair), `lantern` (pleated paper), `dome`. `main.js:90–96`
builds each set into its own `Builder` and `Group`; all four are visible for the shader warm-up
(`main.js:239–244`), then only the current one. Switching costs no geometry work, only a shadow-map refresh.

## src/styles.js

- `SET_AVG` (6–14): mean linear albedo of the 29 texture sets' colour maps, measured with the skill's
  `scripts/textures.py --measure`. A role with `albedo: 0xRRGGBB` gets colour `albedo / SET_AVG[set]`
  so the finish *reads* as that colour whatever the scan's cast; the bake uses the same numbers.
- `STYLES` (21–142): `minimal`, `japandi`, `desert`, `luxe`, each `{ name, short, blurb, palette[6],
  sets[], art[5], inside, roles }`. `sets` are extra texture sets loaded on first use; `inside`
  multiplies indoor exposure in `main.js`; `roles` has 22 keys per style (`travertine`, `oakFloor`,
  `marbleFloor`, `paint`, `ceiling`, `travertineSlab`, `oak`, `walnut`, `joinery`, `marble`, `boucle`,
  `velvet`, `linen`, `linenSand`, `linenGrey`, `rug`, `bloom`, `brass`, `lampShade`, `concrete`,
  `weave`, `sheer`) with fields `set, tile, color | albedo (+ flat), rough, metal, normal, env, sheen,
  clearcoat, joints [sx, sy, width, shade]`.
- `createStyler({ M, T, base, anisotropy, onLoading })` → `{ apply(key), current, preload(key) }`.
  `apply` loads missing sets, then per role swaps `map`/`normalMap`/`roughnessMap` (= `aoMap`) to
  clones cached by `set|channel|tile`, sets colour (or the albedo-corrected colour plus the `uFlat`
  uniform), roughness, metalness, normal scale, env intensity (restoring `env0` when omitted), sheen,
  clearcoat (floor 0.02), the joint uniform and the lamp-shade emissive; then regenerates `art1..3`
  from `st.art`. A role absent from `M` is skipped.

Caution: a role's `set` is swapped only if loaded, and only `sets` is loaded. `minimal.roles.weave` and
`luxe.roles.weave` name `rattan`, which is neither a base set nor in their `sets`, so `M.weave` keeps its
`linen` map until `desert` (whose `sets` include `rattan`) has been shown once. List every set a preset's
roles name.

## src/materials.js

- `SETS` (5–6): the 19 base sets loaded before anything shows; style-only sets (`ash`, `herringbone`,
  `smokedwalnut`, `terracotta`, `clayplaster`, `limewash`, `microcement`, `rattan`, `papercord`,
  `nero`) load lazily. A set is three WebPs in `assets/tex/`: `<name>_c` (sRGB colour), `<name>_n`
  (OpenGL normal), `<name>_r` (R = AO, G = roughness), produced by the skill's `scripts/textures.py`.
- `loadTextureSets(base, anisotropy, onProgress)` → `T[name] = { c, n, r }`; load all, clone after
  (pitfall 1). `shared = { time, gi: { uGi0, uGi1, uGiA, uGiB, uGiDims } }`; `uGiDims` starts at
  `(1, 1, 1)` so the lookup fades out until `gi.js` fills it.
- `enhance(mat, o)` (68–130): one `onBeforeCompile` patcher keyed by feature set, so materials that
  differ only in uniform values share a program. Features: `joints { size, width, shade }` (tile
  joints by metre UV), `macro { scale, amount, hue }` (albedo variation from world xz), `sway` (palm
  fronds, anchored 7 m up), `glass [aMin, aMax]` (fresnel alpha), `flat` (`uFlat` pulls the texel
  towards a mean albedo), `gi` (`GI_FRAG` after `lights_fragment_maps`). Uniforms land in
  `mat.userData.u`, the feature list in `mat.userData.fx`.
- `createMaterials(T, { maxAniso })` → `{ M, glow, water }`. `pbr(name, { tile, tileV, color, rough,
  metal, normal, env, ao, side, physical, joints, macro })` builds a `MeshStandardMaterial` (or
  `MeshPhysicalMaterial` with `physical`) from a set. `emissive(color, day, dusk, extra)` registers a
  time-of-day glow; `glow` entries are `{ mat, day, dusk, prop? }` (`'opacity'`, a uniform name, or
  `emissiveIntensity`), lerped at `main.js:193–199` by `smooth(tod, 0.3, 0.95)`. Some seventy keys:
  architecture, interior roles, emitters, vegetation cards, decor and LOD cards, waters, lamp pools
  and beams. Lines 272–274 add `gi: true` to every opaque `MeshStandardMaterial` except the waters.

`scripts/bake-gi.mjs:35` reads albedo from this file with `M\.(\w+) = pbr\('(\w+)', \{([^}]*)`; the
capture stops at the first `}`, so keep `color:` ahead of any nested `joints`/`physical` object, and a
`pbr` call without `color:` bakes as white × the set mean. Keys made with `std(...)` or a bare
`new Mesh…Material` are not matched: give them an `ALB` entry in the bake or they trace as 0.5 grey
(`bake-gi.mjs:112`).

## src/proctex.js and src/vegetation.js

`proctex.js` draws canvas textures (needs a DOM, which is why the bake never imports `materials.js`):
`frondTexture()`, `foliageTexture({ seed, leaf, flower, flowerRatio, size, narrow })`,
`latticeTexture()`, `railTexture()`, `radialTexture(inner, outer, size)`, `artTexture(seed, palette)`,
`roomTexture()`, `facadeAtlas()` → `{ map, emissive }` (front elevation in u 0–0.5, rear in 0.5–1,
v = height / 10.2; this facade is drawn at 189–207), `waterNormals(size)`. `vegetation.js`:
`palmGeometry()` → `{ trunk, fronds }` (crown at 7 m local), `bushGeometry(cards = 14, seed = 2,
flat = 0.75)`, `instancedFrom(geo, mat, matrices, { cast, receive })`.

## src/community.js

The hero plot's frame is the world frame; the estate is laid out on arcs about `CENTER = (3.05, 0,
-R)`, `R = 260` (9–13: `SPAN 0.62` rad, `BLOCK 7` units, `GAP 5` m, `PLOT_W 6.1`, `CROSS [-0.36,
0.34]` cross-street angles). `rows` (69–72): eight rows by radius and `out` (which way fronts face),
the hero row `{ r: R, out: true, hero: true }`. Per row `step = (BLOCK * PLOT_W + GAP) / r`; blocks
near a `CROSS` angle become pocket parks; the hero's slot (`b === 0 && i === 3`) is skipped;
alternate units are mirrored. A unit whose reference point `(3.05, 0, -9)` is within 72 m of the
hero's is *full* (instanced shell), else *LOD*; the two attached neighbours (< 7 m) get no palm spots.
The non-hero shell's `room` quads are pulled out of the instanced geometry (105–112) and drawn as
`roomLit` or `roomDim` (62 % of units lit): there is no `M.room`, so a plain `meshes()` of a non-hero
shell warns `missing material room`. `lodHouse(B)` (18–36): two body boxes, four `lod` quads on the
facade atlas and flat fills (grass, pavers, pergola `wood`, `patio`, `gravel`), hard-coded to this unit
(6.1 × 15.3 m, heights 6.95 and 10.0). Streets 121–172: five ring pairs (`streets`, 123), 2.2 m
sidewalks, curbs, lamps every 6.5 m, hero frontage kept clear (`|x - 3.05| < 14`, `z` in `(-2, 14)`);
`ring()`/`curb()` write annulus sectors with world-metre UVs. Lamps 174–194: pole, arm, head, pool and
beam cone instanced, beams named `lampBeams` (hidden by day at `main.js:200`). Lagoon 196–223 at `(-260,
0, -360)` rotated −0.6, semi-axes 170 × 85 m (so roughly 340 × 170 m across), with beach and 46 palms.
Desert 225–244: a 4200 m plane, dunes from 470 m out. Returns `{ group, stats }`; `lite` (the `low`
tier) coarsens the desert mesh (130 instead of 220 segments a side) and keeps half of the street, verge
and far-house planting.

## src/path.js

`K` (7–45): 37 keyframes `[progress, [x, y, z], [lookX, lookY, lookZ], fov]`. `DronePath` builds
centripetal `CatmullRomCurve3`s for position and look target plus two monotone cubics
(`monotone(xs, ys)`, 47–65) from progress to normalised key index and to FOV, so speed changes are
smooth and a repeated key holds; `sample(p, outPos, outLook)` → fov. `DroneRig(camera).update(pos,
look, fov, dt, time, { hover, still })` adds altitude-scaled hover (0.35 m above 20 m, 0.08 above
7 m, 0.012 below), a bank of at most ±0.045 rad from yaw rate, a slerp lag `1 - exp(-dt * 9)`, and
widens the FOV in portrait (aspect < 1.25, cap 82°); `still` snaps everything for captures.

| Progress | Camera (read off `K` against `plan.js`) | Card |
| --- | --- | --- |
| 0–0.185 | aerial approach from `(140, 60, 110)`, descending over the estate | Arrival, Community, The plot |
| 0.228–0.305 | orbit down to street level in front of the facade | Facade |
| 0.34–0.42 | from the street (`d −5.5`) through the carport and front door to the hall (`d 9.7`) | Ground floor |
| 0.445–0.5 | living room, turning to the garden glazing | Living |
| 0.522–0.558 | garden, rising past the rear balcony | Garden |
| 0.578–0.655 | first floor at `y ≈ 5.1`: rear balcony → bedrooms → landing | Bedrooms |
| 0.674–0.738 | master suite to the front balcony | Master suite |
| 0.758–0.805 | out over the front, up to `y 11.8`, across the roof | (transit) |
| 0.825–0.866 | roof level `y 8.75`: bedroom 4, then the terrace | Bedroom 4, Roof terrace |
| 0.888–0.902 | terrace facing the sunset (`look (-18, 9.6, -32)`) | Roof terrace |
| 0.93–1 | blue-hour climb to `(80, 64, 70)` | Summary |

Rules the route is held to (`scripts/check-path.mjs` `LIMITS`): lens ≥ 0.3 m from any solid, look
target ≥ 2.4 m from the lens, pitch −35°..+40°, yaw ≤ 12° and pitch ≤ 6° per 0.005 of progress.
Interpolate orientation through look *targets* far from the lens, never a point it passes (pitfall 19).
The template as checked out does **not** yet meet them: `node scripts/check-path.mjs` exits 1 with 30
breach runs, the worst in Living (0.452–0.495: yaw 167° per 0.005, pitch −80°, look target 0.8 m from
the lens) and in the uncaptioned roof transit (0.802–0.825: pitch −86°, yaw −164° per 0.005). The skill's
eval `route-polish-on-template` exists to fix exactly these; treat the limits as the target, not as
something the copied `K` already satisfies. When reading the report, note its `worst` column keeps the
largest magnitude, so for clearance and look distance read the minima in the per-chapter table instead.

## src/atmosphere.js

`STATES` (13–17): `t 0` golden hour, `0.5` sunset, `1` blue hour, each `{ elev, turb, ray, mie, mieG,
gain, sun, sunCol, fog, fogD, exp, env, ground, disc }`; `stateAt(t)` lerps and darkens fog with
`smoothstep(t, 0.55, 0.92)` towards `TWILIGHT.horizon`. `makeSky(scale)`: three's Preetham `Sky`
with a patched fragment shader (twilight gradient `uTwK`, horizon melt `uHz`/`uFog`, gain, sun disc 25
not 760) and cloud uniforms `cloudCoverage 0.22, cloudDensity 0.32, cloudElevation 0.55, cloudScale
0.00016`. Main sky 9000, env sky 400, stars 3600; camera far is 9000 (pitfall 3).

`Atmosphere(renderer, scene, { shadowMapSize })`: `sun` (`DirectionalLight`, target `(3.05, 0, -9)`,
line 72), `FogExp2`, a PMREM environment from a small sky plus ground disc cached by quantised key
`${round(t*20)/20}|${round(az/6)*6}|${round(el)}` (≤ 8 entries), `skyLevel` (mean radiance per env,
read back asynchronously via `LightProbeGenerator`, `onLevel` callback). `setShadowZone(zone)`:
shadow half-size `{ aerial: 300, street: 60, house: 18 }`, target `(-40, 0, -20)` aerial else
`(3.05, 4, -9)` (114), per-zone bias and radius; the map re-renders only on zone or sun change
(`renderer.shadowMap.autoUpdate = false` at `main.js:72`; `applyStyle` requests one more at `main.js:251`).
`setSun(az, el)` has a 0.15° deadband; `update(t, time, az, el)` → state, or `null` when nothing changed
(`main.js` keeps `atmo.last`). `skyRatio()` divides the current env level by the one at `BAKE_KEY =
'0|-54|18'` (the bake's −55° quantised to 6°), with a fitted curve until both read-backs land (pitfall
15). Azimuth runs from `+z` towards `+x`: −55° is south-west of a house whose street is at `+z`.

## src/gi.js and src/gi-data.js

`gi-data.js` is generated (`// Generated by scripts/bake-gi.mjs - do not edit.`): `GI = { spacing:
0.5, min: [0, 0, -15.6], dims: [13, 22, 30], S, U, N: { minimal, japandi, desert, luxe } }`, base64 at
6 bytes per probe (7 for `S`, which adds the open-sky fraction): rgb DC as `2^(v/255*20 - 14)` then a
luminance gradient relative to the DC. About 423 KB of the 1.39 MB bundle; JS rather than `.bin`
because of pitfall 18. `createGI()` decodes once, derives `inside = 1 - smoothstep(open, 0.2, 0.4)`,
creates two `HalfFloat` `Data3DTexture`s and sets `shared.gi.uGi0/uGi1/uGiA/uGiB`; `uGiDims` is written
on the first `set` (64), which is what un-fades the shader lookup. `set(kS, kU, kN,
style)` re-mixes `kS·S + kU·U + kN·N[style]` on the CPU (alpha of texture 0 = `inside`), skipping
when weights are unchanged to three decimals; `N.minimal` stands in for a style with no lamp set.
The shader half (`GI_FRAG`, `materials.js:33–57`) samples at `vWPos + normal * 0.22`, fades near the
volume edge, reconstructs the L1 lobe non-linearly (pitfall 14), replaces `iblIrradiance` where
`inside` and scales reflections by the same occlusion.

## src/post.js and src/volumetric.js

`createPost(renderer, scene, camera, { ao, aoQuality, halfRes, bloom, smaa, sun, volSteps })` → `{ composer,
aoPass, bloomPass, final, volPass, setSize(w, h, dpr) }`. N8AO `aoRadius 0.6` (per-zone override 5 / 1.4 /
0.55 at `main.js:192`), `intensity 3.0`; lines 42–45 patch the `depthDownsampleTarget.texture` getter
(pitfall 2). The volumetric pass exists only with AO (it reads `aoPass.beautyRenderTarget.depthTexture`), so
`low` has haze from dust points only. Bloom half-res, strength 0.2, radius 0.32, threshold 9.0 (pitfall 4).
`FinalShader`: split-tone grade, `uVignette 0.32`, `uGrain 0.022`.

`VolumetricPass({ camera, sun, getDepth, steps = 28, scale = 0.5 })` raymarches the sun's shadow map;
uniforms are exposed as `pass.u` (`uDensity`, `uDensityIn`, `uMaxDist`, `uG 0.6`, `uHeightK`,
`uHeightScale`, `uSunIn/Out`, `uAmbIn/Out`) and composite colours as `pass.sunCol`, `pass.ambCol`.
`uBoxMin (0.1, 0.25, -14.85)` / `uBoxMax (6.0, 9.7, -3.55)` (line 80) is the house envelope in which
air is dusty and beam-forming: **this plot's numbers**. `makeDust(boxes [[x0, x1, y0, y1, d0, d1]...],
perCubic, seed)` scatters motes lit only where the shadow map says sun reaches; `beamMaterial(color)`
is the lamp cone.

## src/ui.js

`planSVG(floor, highlight)` (9–29) draws that floor's `ROOMS` at 10 px/m, street on the left (`d`
horizontal, `x` flipped so `x = PLOT.w` is at the top), highlighted rooms as `room on`, a rotated
`STREET` label at `x -6`; viewBox `-14 -4 (PLOT.d*10 + 28) (PLOT.w*10 + 8)` resizes with the plot.
`initUI({ onMode, onJump, onStyle, styles })` reads the DOM once → `{ progress(f, text), setStyle(k),
styleLoading(b), ready(), fatal(msg), update(p, camera, pinWorld, w, h) }`. Cards are every `.card`:
`data-from`/`data-to` give the progress window; `data-rail` (optional) adds a rail button that scrolls
to the window's midpoint; a child `.plan[data-floor][data-room="key,key"]` receives a `planSVG`;
`[data-style-line]` is filled with the style's swatches and blurb. In `update`, opacity fades over
±0.012 around each edge (line 100); `from ≤ 0` is visible from the start and `to ≥ 1` never fades
out; the rail button is `on` within ±0.01; the plot pin is projected from
`pinWorld` and shown between 0.045–0.07 (in) and 0.17–0.215 (out) (line 116).

## src/main.js

Query parameters: `?p=0.42` renders one still at that progress (`STILL`, `FIXED_P`), `?q=high|mid|low`
forces a tier, `?tod=day|night` forces time of day, `?ui=0` adds `body.noui`, `?style=` or `#japandi` picks
the style (hash wins). `detectTier()` (22–29): `low` for coarse pointers, `deviceMemory ≤ 4` or a screen
under 600 px, else `high`; `mid` only by query. `Q` (31–35): `high { dprMax 2, shadow 4096, ao 'Medium',
halfRes, smaa, bloom }`, `mid { 1.5, 2048, 'Performance' }`, `low { 1.3, 2048, no ao, no smaa }`;
`volSteps` 20 on `mid` else 28; dust `perCubic` 2.5 on `low` else 5. The photographic constants are not in
this file: `src/look.js` (13 lines) exports `LOOK = { giFill 3.0, giLamp 0.45, giLampDay 0.12,
giWhiteBalance [1.0, 1.0, 0.97], insideExposureDay 5.5, insideExposureNight 1.3, dustSun 0.4,
dustAmbient 0.012 }`, kept apart from the loop so a new property can be re-tuned without touching `update`.

Start-up 44–136, loader fractions: textures to 0.65, `Building plot XJ407B` 0.68 (83; hero shell and
interior into one `Builder`, one `Builder` per style set), community 0.76, point lights, `Atmosphere`
then `atmo.envFor(0, -55, 18)` (121) to seed the GI reference env, `createGI`, `createPost`, dust boxes
(125–128, plan units `[x0, x1, y0, y1, d0, d1]`), `pinWorld (3.05, 11.5, -9)` (136). `zoneFor(c)` (161–166):
`aerial` above `y 42`, `house` inside the plot box or its margin, else `street`; `inHouse` (184) is a tighter
box (`x 0.1–6.0`, `z -3.5…-14.85`, `y < 9.7`, minus the terrace where `y > 6.8 && z < -11.2`) driving
exposure and dust.

`update(dt, time)` (168–236): eased progress; auto `tod = smooth(progress, 0.79, 0.975)`; sun `swing =
smooth(progress, 0.735, 0.83)`, azimuth `lerp(-55, -128, swing)`, elevation `lerp(lerp(18, 11.5, swing), 4,
smooth(progress, 0.868, 0.89))` (178–180); exposure `st.exp * lerp(1, lerp(LOOK.insideExposureDay,
LOOK.insideExposureNight, tod) * STYLES[styleKey].inside, inside)` (189); glow lerps; `gi.set(sky =
skyRatio × st.env × LOOK.giFill × LOOK.giWhiteBalance, sunBounce = sunColour / (1, 0.81, 0.6) ×
intensity / 4.3 × LOOK.giFill, lamps = LOOK.giLamp × lerp(LOOK.giLampDay, 1, lamp))` (202–205); volumetric
and dust uniforms per zone (densities 0.0024 / 0.0013 air / 0.03 inside, max distance 55 / 280 / 20 m);
returns whether anything is still converging. Warm-up 238–263: all style groups visible, one `update`,
`renderer.compileAsync`, then only the chosen style; `applyStyle` re-parameterises, toggles groups,
refreshes shadows and writes `#style` to the URL; `window.__ready` is set after the first frame. `STILL`
265–277: removes the loader, waits up to 1.5 s for two sky read-backs, renders three settle frames, logs
`[t] settled · calls · tris · programs · textures`, sets `window.__shot = true` (what `capture.cjs` waits
for) and stops. Loop 279–305: render only while `awakeUntil` (1.6 s after any scroll, resize, visibility
or UI event) or while converging; every 40 frames move `dpr` by −0.2 when the mean frame exceeds 26 ms
(floor 0.75) or +0.1 under 13 ms (cap `Q.dprMax`).

## index.html and style.css

`index.html` (178 lines): `canvas#scene`; `#loader` with `.bar i`, `.label`, `.pct`; `header.top` with
the brand and `[data-mode]` Auto/Day/Night buttons; `.styles#styles` (buttons appended by `ui.js`);
`#toast`; `nav#rail`; `.meter`; `#pin`; `#cards` with twelve `section.card`s (36–171): the hero card
`data-from="0" data-to="0.058"`, ten chapters, the `outro` summary `0.945–1`. Chapter cards carry
`.eyebrow` with a number, `h3`, copy, optional `dl.figs`/`dl.times`, optional
`p.style-line[data-style-line]`, and an optional `.plan` (`data-floor`, `data-room` keys from `ROOMS`).
`main#scroll` is the scroll spacer; the module script is `dist/app.js`. `check-path.mjs` parses cards
with `data-from="…" data-to="…" data-rail="…"`, so keep those attributes in that order. As checked out,
three stretches break the 0.03 no-card rule (pitfall 21): 0.33–0.372, 0.742–0.83 (the roof transit) and
0.9–0.945; `check-path.mjs` lists them but does not fail on them.

`style.css` (141 lines): `#scroll { height: 1700vh }` (12) is the scroll length, sixteen screens of
travel; progress is `scrollY / (scrollHeight - innerHeight)`. Brand accent `--violet`/`--violet-deep`
(rail, pin, plan highlight, loader). Cards sit bottom-left at 420 px; hero and outro are centred;
`.plan-svg .plot / .room / .room.on / .street` style the mini-plans; `body.ready` reveals the chrome,
`body.noui` hides it; the 720 px breakpoint hides the rail and the plans.

## scripts/

`bake-gi.mjs` (Node, `three-mesh-bvh`): `RAYS` from the environment (default 256), `PASSES 3`, probe
grid `SP 0.5`, `MIN [0, 0, -15.6]`, `DIMS [13, 22, 30]` (19), i.e. x 0–6, y 0–10.5, depth 1.1–15.6 m:
this house and nothing else. `ALB` (29–32) gives albedo for untextured keys; textured keys come from
`materials.js` text; `albedoFor(style)` applies the roles. `SKIP` (51) lists keys that do not block
light. `LAMP` (53): `downlight 18` (downward cos² lobe), `bulb 4`, `lampShade 6`, `led 1.2` per 0.6 m,
`fire 8`, each with a softening radius. Scene 89–102: hero shell and interior; non-hero shells at
`x ± 6.1` (mirrored about 3.05) and `± 12.2`; two opposite rows rotated 180° at `z -37` and `z +12`
for the same five offsets (straight stand-ins for the community rows `R - 37` and `R + 12`); a ground
quad. `sunDir` (22), `SUN` (23, `4.3 × sunCol`) and `SKY` (122) must match `atmosphere.js` `STATES[0]`
and the golden-hour sun `(-55, 18)`.
`maskFor` marks probes with > 25 % back-face hits, `fill` refills them from neighbours, `pass` traces
one bounce lit by the previous pass's probes, `bake` runs `S` and `U` once (minimal scene) and `N` per
style, `encode` writes `src/gi-data.js`. `npm run bake` takes about ten minutes at 256 rays
(`RAYS=64 npm run bake` for a quick look); then `npm run build`.

`check-path.mjs`: `LIMITS` (12–19); hero plus the two attached neighbours (41–43); a 0.5 m cell grid;
samples every 0.001 of progress; prints breach runs named by chapter, a per-chapter table (span, yaw
swing, pitch range, look distance, clearance) and uncaptioned stretches over 0.03; exits 1 on any
breach. `node scripts/check-path.mjs [--verbose]`.

`capture.cjs`: `node scripts/capture.cjs <baseUrl> <outDir> <q> <p1,p2,...> ["&ui=0"]`, `W`/`H` env
(default 1024 × 576); headless Chromium on SwiftShader, waits for `window.__shot` (600 s), screenshots
with a 180 s timeout (pitfall 16), writes `out/p<p>.png`, prints `[t]` timings and console errors. Serve
first (`npm run serve` under `nohup`, pitfall 17). `playwright` is not in `package.json`: here it resolves
from the global install (1.63.0); elsewhere install it and run `npx playwright install chromium`. Tile
stills with the skill's `scripts/sheet.py <dir> <out.jpg> <columns> <thumb-width>`.

## package.json and the build

`"type": "module"`. Scripts: `build` (`esbuild src/main.js --bundle --minify --format=esm --target=es2020
--outfile=dist/app.js --legal-comments=none`), `dev` (unminified, sourcemap, `--watch`), `serve` (`python3 -m http.server 8080`),
`bake`. Dependencies `three ^0.187.0`, `n8ao ^2.0.1`, `postprocessing ^6.39.6` (n8ao's peer), `esbuild
^0.28.2`; dev `three-mesh-bvh ^0.9.18`. `dist/app.js` (1.39 MB) is committed and `.gitignore` re-includes it
with `!dist/` because the published page serves the bundle (pitfall 9). Module scripts need a server, not `file://`.

## Adapting to a new property

Work in this order, rendering a still (`?p=`) after each step: `plan.js` → `house.js` → `interior.js` (watch
for `missing material`) → `stylesets.js` → `community.js` → `path.js` with `check-path.mjs` → `index.html`
cards → `volumetric.js`/`main.js` boxes → `bake-gi.mjs` → `npm run build` → contact sheets at every card midpoint.

| File | Change? | What exactly |
| --- | --- | --- |
| `src/plan.js` | must | `PLOT`, `H` levels (add or drop a floor), `FACTS`, every `ROOMS` entry (`key`, `name`, `x`, `d`, `size`), `STAIR` |
| `src/house.js` | must | every wall, slab, parapet and planter in the four sections; each `wallX`/`wallD` hole with its `glaze`; door position and swing (125–133); railings, slats, lattice; the non-hero `room` quads (228–237); spots |
| `src/interior.js` | must | floor slabs per finish, `paint` linings with the shell's holes, doors, ceilings and downlight grids, both stairs (riser counts, run, landing), kitchen, bathrooms, fixed joinery (`wardrobeAlong*`), decor (`print`, `vase`, `rug`, `curtain`), the four `lights` |
| `src/stylesets.js` | must | furniture positions in all four blocks to the new living, dining and master rooms; keep one table position shared by every style |
| `src/community.js` | usually | `PLOT_W`, `BLOCK`, `GAP`, `rows`, `streets`, `CROSS`, the `(3.05, 0, -9)` hero reference and `mirrorX(…, 3.05)` (half the new width), `lodHouse` footprint and heights, lagoon and desert placement; or replace the arc layout for a different estate |
| `src/path.js` | must | every row of `K`; keep ≥ 2.4 m look distance and ≥ 0.3 m clearance; re-run `check-path.mjs` until it exits 0 (the copied `K` does not: 30 breach runs) |
| `src/main.js` | must | `zoneFor` and `inHouse` boxes (161–166, 184), dust boxes (125–128), `pinWorld` (136), the sun schedule (178–180) if the terrace faces elsewhere, loader copy (83); `Q` only if the new scale demands |
| `src/look.js` | usually | `LOOK`, after the first bake and stills: `giFill`/`giLamp` if interiors read dark or lamps loud, `insideExposureDay/Night` for the indoor stop, `dustSun`/`dustAmbient` |
| `src/volumetric.js` | must | `uBoxMin`/`uBoxMax` (80) to the new interior envelope |
| `src/atmosphere.js` | usually | `sun.target` and the house-zone target (72, 114) to the new plot centre; `STATES`, `BAKE_KEY` and the default `-55 / 18` sun (75; seeded again at `main.js:121`, swung at `main.js:178–180`) only if the orientation changes (then the bake's `sunDir`, `SUN` and `SKY` too) |
| `src/styles.js` | usually | palettes, blurbs, `art`, role colours per brief; `SET_AVG` entries for new texture sets; `roles` keys only if `materials.js` gains or loses a role |
| `src/materials.js` | usually | add sets to `SETS` and one-line `pbr` entries for new finishes; facade palette (`render`, `stone`, `bronze`, `frame`) |
| `src/proctex.js` | usually | `facadeAtlas()` elevations (189–207) to the new facade |
| `src/ui.js` | leave alone | reads `PLOT` and `ROOMS`; only the pin window (116) if the aerial timing moves |
| `src/gi.js`, `src/gi-data.js` | regenerate | never hand-edit; `npm run bake` after any wall, furniture or lamp change |
| `src/builder.js`, `src/softgoods.js`, `src/vegetation.js`, `src/post.js` | leave alone | generic |
| `index.html` | must | `<title>`, meta, loader and brand copy, every card's `data-from`/`data-to`/`data-rail`, eyebrows, copy, `dl.figs` figures, `.plan[data-floor][data-room]` keys, the summary table and fine print; no gap over 0.03 without a card (the template still has three) |
| `style.css` | usually | `#scroll` height if the route is much longer or shorter; `--violet` accent to the brand |
| `scripts/bake-gi.mjs` | must | `MIN`/`DIMS` to cover the new envelope at `SP 0.5` (probe count drives bake time), the neighbour layout and `mirrorX(g, 3.05)` centre (94–100), `ALB` for new untextured keys, `LAMP` for new emitter keys, `sunDir`/`SUN`/`SKY` if the sun moves |
| `scripts/check-path.mjs` | usually | attached-neighbour offsets and `mirrorX(g, 3.05)` centre (42–43) to the new plot width; `LIMITS` stay |
| `scripts/capture.cjs`, `package.json` | leave alone | `name` and `description` only |
| `assets/tex/` | usually | add sets with the skill's `scripts/textures.py`, then `SET_AVG` |
