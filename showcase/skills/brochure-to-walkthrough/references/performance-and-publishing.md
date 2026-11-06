# Performance budgets, captures, cost and publishing

The subsystems that keep the page fast, and the steps that turn a finished build into a delivered one.
Paths are relative to the project root (the template copied from `/home/user/AIAGENTS/showcase/violet2-flythrough`);
`<skill>` is this skill's folder. Every line number and figure was read or measured from the template as
it stands; re-measure after changing the files they point at. The reasons behind the design are in
`decisions-and-pitfalls.md` (cited as "pitfall N"); the file-by-file map is `template-architecture.md`.

## Contents

1. Budgets at a glance
2. Quality tiers (`src/main.js`, `src/post.js`)
3. Render on demand and adaptive pixel ratio
4. Static shadow zones (`src/atmosphere.js`)
5. Instancing and LOD (`src/builder.js`, `src/community.js`, `src/vegetation.js`)
6. Reading the capture log line
7. Bundle composition and the npm scripts
8. Texture payload
9. Rendering a still: query parameters and the hash
10. `scripts/capture.cjs`
11. `scripts/check-path.mjs`
12. Contact sheets with `<skill>/scripts/sheet.py`
13. Measuring the session's token cost
14. Publishing to a claude.ai artifact
15. Git hygiene
16. What the README must contain

## 1. Budgets at a glance

Measured on 6 Nov 2026, after the review-and-fix passes, with `scripts/capture.cjs` at 1024 × 576 on
headless Chromium + SwiftShader (a CPU renderer: the timings are load and settle times, not GPU frame
times; say so in any report).

| Measure | Template | Limit (SKILL.md acceptance) |
| --- | --- | --- |
| Draw calls, high, interior (`p=0.655`) | 157 calls · 0.84 M tris · 120 programs · 113 textures | ~150 calls, ≤ 1.3 M tris |
| Draw calls, high, aerial (`p=0.03`) | 186 calls · 0.80 M tris · 120 programs · 113 textures | same |
| Draw calls, high, garden (`p=0.49`) | 177 calls · 0.89 M tris · 120 programs · 113 textures | same |
| Draw calls, low, interior (`p=0.655`) | 154 calls · 0.78 M tris · 118 programs · 111 textures | – |
| First frame / settled (SwiftShader) | 7–15 s / 8–29 s after script start, varying with host load | – |
| `dist/app.js` | 993,630 bytes (970 KiB), minified; 337,707 gzip | ≤ 1.5 MB |
| `assets/gi/` | 7 JSON files, 492,424 bytes; 286,455 gzip; `S` + `U` + `U2` + one `N` before the first frame | – |
| `assets/tex/` | 29 sets, 87 WebP files, 8,977,288 bytes (8.56 MiB), plus `512/` 2,930,674 bytes for the phone tier | ≤ 10 MB |
| Awaited before first frame | 11 exterior base sets (the 7 interior sets stream in behind it; a still awaits all 18) | – |
| Published artifact | `index.html`, `style.css`, `dist/app.js`, 7 GI files, 174 WebP files | 256 files, 20 MiB/file, 64 MiB/call |

The aerial frame costs more calls than the interior because nothing is frustum-culled from the air;
programs stay at 120 because every material is compiled once during warm-up (§3): 104 before the fix
passes plus the `noPoint` and `lampMap` variants of the exterior finishes. The night point-light pool
keeps a fixed count, so no light-state recompile ever happens.

## 2. Quality tiers (`src/tiers.js`, `src/post.js`)

A tier is a **pixel budget** (device pixels the post chain may process per frame) plus the passes that
run; the pixel ratio follows from the budget and the canvas size (`pixelRatioFor`), never above the
device's own, so a 13-inch retina laptop and a 4K monitor land on comparable frame costs. `detectTier(gl,
forced)`: `?q=` wins; otherwise `classifyGPU()` reads the renderer name through
`WEBGL_debug_renderer_info`: software renderers and mobile GPUs (Mali, PowerVR, Xclipse, Adreno 1xx–6xx,
`Apple GPU` on a phone) `low`; other Adreno, `Apple GPU` on a tablet, base M1/M2, Intel/Iris/UHD and
integrated Radeon `mid`; GeForce/RTX/Quadro, Radeon RX/Pro, Arc and Apple Pro/Max/Ultra `high`; unknown
desktops `mid` (the scaler climbs from there).

| Tier | budget | `shadow` | `ao` / `aoQuality` | `halfRes` | `smaa` | `bloom` | `vol` / `volSteps` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| high | 3.7 MP | 2048 | yes / `'Medium'` | yes | yes | yes | yes / 28 |
| mid | 2.1 MP | 2048 | yes / `'Performance'` | yes | yes | yes | yes / 20 |
| low | 0.6 MP | 2048 | zones only / `'Performance'` | yes | yes | yes | no |

On `low`, `aoZones` keeps AO only in the house and street zones (`post.setAO` swaps in a plain
`RenderPass` from the air) and the volumetric march is off (it reads depth from
`aoPass.beautyRenderTarget.depthTexture`); `lite` halves the street, verge and far-house planting; dust is
0.8 motes per m³ instead of 1.5; the env cache holds 6 instead of 16 and its bins are coarser; the
reflection probes are 128 px instead of 256; the styler releases style-only sets it no longer shows; the
overlay drops its backdrop blurs (`body.lowfx`); textures come from `assets/tex/512/`. The only runtime AO
knob is `aoRadius` per zone: 5 aerial, 1.4 street, 0.55 house (0.35 on `low`). Keep the tier values for a
new property; they describe devices, not the house.

## 3. Render on demand and adaptive resolution

The loop calls `update()` every frame (CPU only) but renders only while `now <= awakeUntil` and the tab is
visible. `wake()` pushes `awakeUntil` 1,600 ms ahead on scroll, resize, `visibilitychange`, a mode button,
a style change, a sky read-back landing (`atmo.onLevel`), the GI data landing, and whenever `update()`
reports it is still converging (progress, time of day or exposure still easing), so a frame is never left
half-settled. A scroll page idles most of the time; after 1.6 s the GPU stops entirely, and the idle
periods are when `atmo.prebuild()` renders the evening's environments one at a time.

`AdaptiveScale` (`tiers.js`) walks a ladder of 0.6–1.3× the budget's pixel ratio on measured frame cost:
the GPU timer (`EXT_disjoint_timer_query_webgl2`, bracketing the composer render) where the browser
offers one, else the rAF interval. Down one rung after two 30-frame windows above 19 ms; up one rung as a
probe (reverted if the next window exceeds 18 ms) after 3 s under the ceiling, only once the scroll has
settled, at most one change every 2 s, and never in the first 3 s (boot uploads and compiles are not frame
cost). A change re-runs `applySize()`: `renderer.setPixelRatio`, `renderer.setSize(w, h, false)` from the
canvas box, `post.setSize`, which also decides whether SMAA runs (under a 1.75 pixel ratio).

Warm-up awaits the GI data, runs one `update()` with the beams and dust shown and `renderer.compileAsync`,
then hides them; the other furniture sets are built and compiled when their chip is hovered or focused;
styles later swap maps and parameters, never material types, so switching compiles nothing. The
SwiftShader warning `KHR_parallel_shader_compile extension not supported` comes from this call.

## 4. Static shadow zones (`src/atmosphere.js`)

`renderer.shadowMap.autoUpdate = false`: the map renders only when `needsUpdate` is set, in `placeSun()`
and after a style change. `setShadowZone` sizes the orthographic sun camera per zone: half extents
`{ aerial: 300, street: 60, house: 18 }` m (full widths 600 / 120 / 36 m; texels 29.3 / 5.9 / 1.76 cm at
2048), near 1, far `half * 2 + 400`, target `(-40, 0, -20)` for aerial else `(3.05, 4, -9)` (roughly the
plot centre), `normalBias` 0.25 / 0.05 / 0.02, PCF `radius` 1.5 / 2.0 / 3.0; the sun sits at `target +
sunDir * (half + 200)`. `setSun` ignores moves under 0.15°, so the map re-renders during the terrace swing
and set (`story.js` `SUN`) and nowhere else; far houses and far palms cast only from the air, so a swing
redraws about 0.4 M caster triangles instead of 1.1 M. `zoneFor(c)` (`main.js`) returns `aerial` above
`y 42`, `house` inside `x 0.05–6.05, z −1.4…−15.4, y < 10.2` or the margin box `x −2…8, z 0…−18.5, y <
12`, else `street`. For a new plot change both boxes and the tighter `inHouseBox` to `x 0…PLOT.w`, `z
0…−PLOT.d`, move the house target to the new centre, and grow `house` so the square covers the plot plus
a 2–3 m margin (a 12 × 30 m villa needs about 22). Tightening `house` to 12–14 m would double texel
density, but a fragment outside the frustum renders fully lit: check the terrace and street frames for a
cut-off line before keeping it.

## 5. Instancing and LOD (`src/builder.js`, `src/community.js`, `src/vegetation.js`)

One draw call per material key is the whole strategy. `meshes(geos, mats, { order })` emits one `Mesh`
per key for the hero; `instanced(geos, mats, matrices)` one `InstancedMesh` per key with every neighbour
as an instance; `instancedFrom(geo, mat, matrices, { cast, receive })` the same for a single geometry. All
are frozen with `matrixAutoUpdate = false`.

`buildCommunity(M, heroSpots, { lite })` lays eight curving rows around `R = 260` in blocks of `BLOCK = 7`
plots of `PLOT_W = 6.1` m with `GAP = 5`, cut by two `CROSS` streets. A unit whose centre lies within 72 m
of the hero is full detail (88 on the template): the non-hero `buildShell` geometry plus `dressShell`
(roof pavers, coping, two condensers, a tank) and a copy mirrored about `x = 3.05`, so alternate units
mirror, with the `room` key split into `roomLit`/`roomDim` instances (62 % lit, `cast: false`) and the
`pool` quads dropped. Beyond 72 m `lodHouse()` stands in (163): a few boxes, four quads on the `lod`
facade atlas, flat fills and the cheap form of the rooftop kit. Lamps are four instanced meshes (pole,
arm, head, beam cone, the beams named `lampBeams` and hidden by day); the light they throw is one
`DataTexture` baked on load (`bakeLampMap`: every lamp head splatted within 15 m, every full neighbour's
car-port and strip fittings within 4–6 m, about 2048 × 1024 R8 texels at 0.24 m, a few million texel
updates) that the ground materials sample through the `lampMap` feature. Palms (530) are two
`InstancedMesh` pairs sharing the matrices: the 1,112-triangle model within 70 m of the camera, the
192-triangle one beyond, re-partitioned once the camera has moved 5 m (chunking into angular sectors was
measured and rejected: a wedge of this arc has a 120 m bounding sphere no route position can cull);
bushes are three instanced meshes from two card geometries; the desert is one 4200 m plane of 130
segments. `stats { full, lod, palms }` is returned but not logged: log it while adapting. Neighbours
follow a new hero automatically because they come from the same `buildShell`; rewrite `lodHouse()` and
`dressShell()` to the new massing, the row table to the masterplan and `PLOT_W`. Keep the 72 m radius,
which bounds the heavy instances. If calls climb, look for a new material key or a repeated object built
with `Builder.add` instead of an instance list.

## 6. Reading the capture log line

In still mode `main.js` removes the loader, applies `?cam=` and `?hide=`, waits up to 1.5 s for two sky
read-backs (pitfall 15), renders three settle frames, resets `renderer.info`, renders once more and logs

```
[t] settled · 157 calls · 0.84M tris · 120 programs · 113 textures 14.8s
```

`calls` is `renderer.info.render.calls` for that one composer render: scene draws inside the AO or
render pass plus one call per full-screen pass (AO, the march and its blur, bloom mips, finish, SMAA),
counted on a frame with no shadow-map render (a zone or style change adds one pass over every caster).
`tris` is `render.triangles` in millions. `programs` is `renderer.info.programs.length`, compiled shader
variants including shadow-depth variants; a jump means a new material variant (the `noPoint` and
`lampMap` finishes account for 16 of the 120). `textures` is `memory.textures`: loaded sets (54 base files
plus the current style's extras), procedural textures (the noise, the lamp map, the facade atlas, the
cards), render targets, the two GI 3D textures, the cached PMREM environments, the probes and the shadow
map. The trailing figure is seconds since script start; earlier marks are `textures`, `geometry`,
`compiled`, `first frame`.

Template values are in §1. Any `error:`, `pageerror:` or `warning:` other than the SwiftShader notice is
a defect; `baked light unavailable` means `assets/gi/` did not load and the interiors are env-lit only.

## 7. Bundle composition and the npm scripts

`package.json` (`"type": "module"`): `build` = `esbuild src/main.js --bundle --minify --format=esm
--target=es2020 --outfile=dist/app.js --legal-comments=none`; `dev` = `esbuild src/main.js --bundle --format=esm
--outfile=dist/app.js --sourcemap --watch` (no `--minify`, `--target` or `--legal-comments`); `serve` = `python3 -m http.server 8080`; `bake` = `node scripts/bake-gi.mjs`. Dependencies: `three
^0.187.0`, `n8ao ^2.0.1`, `esbuild ^0.28.2`, `postprocessing ^6.39.6` (n8ao's peer; nothing in `src/` imports
it, so it is not bundled); dev `three-mesh-bvh ^0.9.18` (bake only). `index.html` loads `dist/app.js`
as a module script, so the page needs an HTTP server, never `file://`.

`dist/app.js` is 993,630 bytes (337,707 gzip): `three` (core plus the SMAA, Sky, UnrealBloom and
EffectComposer addons) about 690 KB, `n8ao` about 159 KB, the template's own `src/` about 145 KB. The
baked GI is **not** in it any more: it was 423 KB of base64 (44 % of the gzipped critical path, every
style's lamps decoded at boot) and now lives in `assets/gi/` (§1), fetched by `createGI()` before the
textures and decoded per style on demand. The host refuses `.bin` (pitfall 18), so the files are JSON
with a base64 `data` string, which gzips to 58 %. A larger villa grows them as `probes × (7 + 12 + 6 ×
styles)` bytes × 4/3; at 25 × 22 × 62 probes that is about 2.2 MB in all, with about 1 MB on the
critical path: widen `SP` in `scripts/bake-gi.mjs` to 0.75 m before enlarging `DIMS`. A bake needs no
rebuild; the bundle only changes with `src/`.

## 8. Texture payload

Each set is three square WebP files, 1024 px for 21 sets and 512 px for the eight small-scale or soft ones
(bark, boucle, gravel, linen, papercord, rattan, rug, velvet; the size column of `MANIFEST` in
`<skill>/scripts/textures.py`): `<name>_c` (colour, sRGB), `_n` (normal) and `_r` (R = ambient occlusion,
G = roughness, so one texture serves as both `roughnessMap` and `aoMap`), loaded by
`loadTextureSets(base, …, { defer })` with anisotropy `min(8, max)`. `SETS` holds the 18 base sets; the 11
exterior ones are awaited before the first frame (loader 3 % to 65 %) and the 7 of `INTERIOR_SETS`
(travertine, woodfloor, oak, boucle, linen, velvet, rug) start as 1×1 placeholders and stream in behind
it, one set at a time, each adopted into every material that took a placeholder (`adoptSet`) with no
recompile; a still awaits all 18. Style extras load on first use in `createStyler().apply()` (a `pending`
map prevents double loads; a set counts as loaded only once all three maps arrived): Japandi `ash,
limewash, microcement, papercord` 1,488,080 bytes; Desert `terracotta, clayplaster, limewash, rattan`
1,417,776 (limewash shared); Luxe `nero, herringbone, smokedwalnut` 556,478. All 29 sets 8,977,288 bytes,
mean 302 KiB; largest `grass` 1,164,902 (normal map alone 551,924), smallest `travertine` 75,932. The
phone tier reads `assets/tex/512/` (2,930,674 bytes for all 29 sets, made with `textures.py --downscale
512`: Lanczos to 512 px, WebP quality 82, method 6, files already that small copied), about 58 MiB of
texture memory instead of 232 MiB, and releases the style-only sets it no longer shows. `preload(key)`
is never called; call it after `ui.ready()` if instant switching matters more than bandwidth. Normal maps
are the heavy channel (`grass_n` 552 KB, `limewash_n` 480 KB, `plaster_n` 317 KB). Add a set by adding it
to the manifest, packing it (with a `contrast` value if it must read near white), entering its mean albedo
in `SET_AVG` and its mean roughness in `SET_ROUGH` (`styles.js`; SKILL.md step 4, pitfall 6), then
regenerating the 512 tier. KTX2/Basis was considered and left: no encoder on the build machine, and the
transcoder would add 245 KB gzipped to the page.

## 9. Rendering a still: query parameters and the hash

Parsed at the top of `main.js`:

| Parameter | Effect |
| --- | --- |
| `?p=0.45` | `STILL` mode: progress fixed at `FIXED_P`, no easing, no hover (`rig.update … still: true`), loader removed, every texture set awaited, `window.__ready` then `window.__shot` |
| `&q=high\|mid\|low` | forces the tier (§2) |
| `&ui=0` | adds `body.noui`; `style.css` hides header, rail, cards, meter, pin, style buttons, toast |
| `&tod=day\|night` | fixes time of day (`mode`); anything else is `auto`, where `tod = smooth(progress, TOD.sunsetFrom, TOD.nightBy)` (`story.js`: a third into the terrace chapter to half-way through the summary), so stills before 0.9 are golden hour |
| `?style=japandi` or `#japandi` | picks the style; the hash is checked first, then `?style=`, default `minimal`, and only a `STYLES` key counts; a switch writes `#key` with `history.replaceState` |
| `&cam=x,y,z,lx,ly,lz[,fov[,shift]]` | places the camera directly (with `?p=`), to compose a shot before writing it into `src/path.js` |
| `&hide=sheer,lampBeams,dust` | hides scene objects by name (a material key for the hero's merged meshes and the instanced community meshes), to tell what a stray highlight is |

Example: `http://localhost:8080/index.html?p=0.655&q=high&ui=0&tod=night&style=luxe`. `__shot` is set only
after the sky read-back wait and three settle frames, so the still has the right baked sky level, shadow
map and exposure; `__ready` fires earlier, after the first frame, for the live page.

## 10. `scripts/capture.cjs`

```bash
nohup npm run serve > /dev/null 2>&1 &            # pitfall 17: the server dies with the worker otherwise
curl -sI http://localhost:8080/index.html | head -1
mkdir -p shots
node scripts/capture.cjs http://localhost:8080 shots high 0.45,0.02 "&ui=0"
W=390 H=844 node scripts/capture.cjs http://localhost:8080 phone low 0.30,0.66 ""
```

Arguments: base URL, output dir, tier, comma list of progress values, optional extra query (quote it;
start with `&`). Viewport from `W`/`H` (default 1024 × 576) at device scale 1 (11). Chromium runs
with `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist` (9),
waits for `window.__shot === true` up to 600 s polling every second (17), pauses 300 ms, screenshots with
a 180 s timeout (20, pitfall 16) to `<out>/p<progress>.png`, and prints one line per still (elapsed
seconds, then de-duplicated console `error`/`warning` lines and the `[t]` marks, at most 12), e.g.
`p=0.45 28.1s` followed by `log: [t] textures 0.4s` … `log: [t] settled · 158 calls · 1.26M tris · 104
programs · 105 textures 9.0s`. A still costs 20–37 s here; run two processes in parallel for a route sheet
and `pkill -f chromium` between batches. `playwright` is not in `package.json`: here it resolves from
`/opt/node-tools/node_modules/playwright` (1.63.0, through the symlink in `/usr/local/lib/node_modules_global`,
which is on `NODE_PATH`) with browsers in `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`;
elsewhere `npm i -D playwright && npx playwright install chromium`. Give a second worktree its own port
(`python3 -m http.server 8097`) so two servers never share one.

## 11. `scripts/check-path.mjs`

`node scripts/check-path.mjs [--verbose]` samples the route every 0.001 of progress and exits 1 on any
breach of `LIMITS`: clearance 0.3 m from any solid surface, authored look targets ≥ 2.4 m from the lens
(the sampled look point always sits 10 m out, since `path.js` interpolates orientation), pitch within
−35°…+40°, yaw ≤ 12° and pitch ≤ 6° per 0.005 of progress (about one wheel notch), lens shift within
±`MAX_SHIFT`, and the story table's rules (consecutive card windows at least `2 × FADE` apart, no
stretch over 0.03 uncaptioned, every rail landing inside its window). Solid geometry is the hero shell and
interior plus the two attached neighbours mirrored about `x = 3.05` at `±6.1`, minus the `SKIP` keys the
lens may pass (`pool`, `room`, `sheer`, `downlight`, `led`, `lattice`, the plant and bloom keys), in a 0.5
m cell grid; the rooftop kit (`dressShell`) is not in it, and the route clears it by metres. Chapters come
from `src/story.js`. Output: a header (`route sampled at 0.001; 142636 solid triangles; N breach
run(s)`), one line per run (kind, progress range, worst value, the material hit for clearance, the card
being read, camera position with `d = −z`) and a per-chapter table (span, yaw swing, pitch range,
authored look distance and clearance; `1000000000.00 m` means nothing solid nearby).

The template's route passes: 0 breach runs, minimum clearance 0.30 m (the stair) and 0.33 m (bedroom 4),
no authored look target under 2.6 m. `src/path.js` and the cards are rewritten for every property anyway:
rewrite them until the script exits 0 again (pitfalls 19 and 21, `camera-and-story.md`). For a new plot
change the mirror centre (`3.05`, half of `PLOT.w`) and the `±6.1` offsets (`±PLOT.w`), and extend
`SKIP` for any new non-solid key.

## 12. Contact sheets with `<skill>/scripts/sheet.py`

`python3 <skill>/scripts/sheet.py shots shots.jpg 4 500` (directory of `p*.png`, output, columns, thumb
width). Frames sort by the progress in their file name and get a yellow label; the JPEG (quality 88) is written
and its pixel size printed. Needs Pillow. Sixteen 1024 × 576 frames at 4 × 500 give a 2000 × 1124 sheet; use 256
for a 1024 × 576 sheet when you will read it yourself, since every image opened is re-read with the
conversation on each later turn (§13).

## 13. Measuring the session's token cost

Claude Code writes the transcript to `~/.claude/projects/<cwd with "/" replaced by "-">/<session-id>.jsonl`
(here `/root/.claude/projects/-home-user-AIAGENTS/3d5ceb16-….jsonl`, about 41 MB and growing) and every
subagent or workflow agent to `<same dir>/<session-id>/subagents/**/agent-*.jsonl`. Each model call is a line
with `"type":"assistant"`, `message.model`, `message.id` and `message.usage` (`input_tokens`,
`cache_read_input_tokens`, `cache_creation_input_tokens` split in `cache_creation.ephemeral_1h_input_tokens`
/ `ephemeral_5m_input_tokens`, `output_tokens`). Streaming writes one line per content block with the same
`message.id` (this session when measured: 694 usage lines for 305 ids), so de-duplicate by id or the total
roughly doubles. The transcript names two models and they are not priced alike: the build itself ran on
`claude-opus-5-5` (input $4, output $20, cache read $0.20, 1-hour cache write $8, 5-minute write $5 per
million tokens) and the workflow agents on `claude-fable-5-1` ($10 / $50 / $0.25 / $20 / $12.50), so sum per
model and price each at its own rates; one table for both misprices the Fable calls by about 2.4×. Check the
current price list before quoting money; quote tokens first. The script that produced the figures:

```python
# python3 -I cost.py <session.jsonl> [agent-*.jsonl ...]
import json, sys, collections
# USD per million tokens; cache writes cost 1.25x (5-minute) and 2x (1-hour) the input rate
RATES = {'claude-opus-5-5': {'input': 4.0, 'output': 20.0, 'cache_read': 0.20, 'cache_1h': 8.0, 'cache_5m': 5.0},
         'claude-fable-5-1': {'input': 10.0, 'output': 50.0, 'cache_read': 0.25, 'cache_1h': 20.0, 'cache_5m': 12.5}}
KEYS = ['input', 'output', 'cache_read', 'cache_1h', 'cache_5m']
best = {}  # one usage record per message id
for path in sys.argv[1:]:
    for line in open(path):
        try: d = json.loads(line)
        except ValueError: continue
        m = d.get('message')
        if not isinstance(m, dict) or 'usage' not in m: continue
        u = m['usage']; k = m.get('id') or id(m)
        if k not in best or u.get('output_tokens', 0) > best[k][1].get('output_tokens', 0): best[k] = (m.get('model', '?'), u)
tot = collections.defaultdict(collections.Counter)
for model, u in best.values():
    cc = u.get('cache_creation') or {}; t = tot[model]; t['calls'] += 1
    t['input'] += u.get('input_tokens', 0); t['output'] += u.get('output_tokens', 0); t['cache_read'] += u.get('cache_read_input_tokens', 0)
    t['cache_1h'] += cc.get('ephemeral_1h_input_tokens', 0 if cc else u.get('cache_creation_input_tokens', 0)); t['cache_5m'] += cc.get('ephemeral_5m_input_tokens', 0)
for model, t in sorted(tot.items()):
    p = RATES.get(model)
    usd = f"${sum(t[k] * p[k] / 1e6 for k in KEYS):,.2f}" if p else 'no rate for this model'
    print(f"{model:22s} calls {t['calls']:5d}  tokens {sum(t[k] for k in KEYS):>13,}  cache_read {t['cache_read']:>13,}  out {t['output']:>9,}  {usd}")
```

Run it over the main transcript plus `$(find <dir>/<session-id>/subagents -name 'agent-*.jsonl')`. Over
90 % of the tokens are cache reads of the growing conversation, which is why the reference build cost
≈ 48 M tokens (≈ $22.6) and its realism pass ≈ 24 M (≈ $10.9): keep review images small and delegate broad
reading to subagents. Report calls, total tokens, the cache-read share and the price at the stated rates.

## 14. Publishing to a claude.ai artifact

Publish from a built checkout with `mcp__claude-artifacts__publish_files`, one `{ as, path }` entry per
file with `as` the repo-relative path, because the page loads `dist/app.js`, `assets/gi/<name>.json`
(`gi.js`) and `assets/tex/<set>_<c|n|r>.webp` (`materials.js`, `styles.js`; `assets/tex/512/` on the
phone tier) by those relative URLs: `index.html`, `style.css`, `dist/app.js`, the 7 GI files and the 174
WebP files (87 per tier), 184 files and about 13.3 MB, against limits of 256 files, 20 MiB per file and
64 MiB per call. `.bin` is refused (pitfall 18), hence the GI data as `.json`; `.webp`, `.json`, `.js`,
`.css` and `.html` are accepted. On creation omit `slug` and give `title` and `icon`; the artifact starts
private (`read: owner`). To republish, call `list_files` first (required for an existing artifact unless
the list is already in the conversation), pass `version` from `get_artifact` as `base_version`, and rely
on the default `mode: "patch"`: name only the changed files (after a rebuild, just `dist/app.js`; after a
bake, the seven GI files), list dropped texture sets in `remove`, and echo `shared_live` once the page is
shared.
Query strings are not passed to the served page, so `?style=`, `?tod=`, `?p=` and `?q=` do nothing on the
artifact URL: the only deep link is the hash (`#japandi`, `#desert`, `#luxe`) and tier detection stands on
its own (phones get `low`). `history.replaceState` is wrapped in `try` (253) because sandboxed frames may
refuse it. The reference artifact is "Violet 2 · TH12-4M townhouse flythrough", slug
`91f0dcc3-c446-4575-aa72-54724e35fe9b`, 90 files, version `1793964035-d2cb`.

## 15. Git hygiene

The repository root `.gitignore` ignores `dist/` (line 8); the project `.gitignore` is three lines,
`node_modules/`, a comment and `!dist/`, which re-includes the bundle so that `dist/app.js` is tracked and a
clone, or a publish from one, serves the page without a build step (pitfall 9). Check with `git check-ignore -v dist/app.js` (no output, exit 1) and `git ls-files dist`. Commit
after every `npm run build` that changes behaviour, in the history's message shape (`Violet 2 flythrough:
route quality check and capture harness`). Capture directories (`shots/`, `rv/`, `out/`, `*.jpg`) are not
ignored by anything: keep them outside the tree or add them to the project `.gitignore` before `git add -A`.
The page carries no buyer contact, price or payment plan (nothing in `index.html` matches `AED`, `price`,
`payment`, `tel:` or `mailto`); the summary card (158–171) shows areas and the "Visualisation" disclaimer
only, and `README.md` line 27 says so. Keep it that way unless the user asked otherwise.

## 16. What the README must contain

Model it on the template's `README.md` (103 lines), section for section:

1. Title and one paragraph naming the unit (type, plot, project, city) and the route the camera flies.
2. Quick start: `npm install`, `npm run build`, `npm run serve`; module scripts need a server.
3. Real versus illustrative: which figures came from which PDF page (plot, areas, room sizes, levels,
   parking, facade language, drive times), what is invented (furniture, finishes, landscaping,
   neighbours, views), and that price and payment plan are not shown.
4. Structure: a file → role table covering every `src/` file (the template's own table misses
   `proctex.js`, `vegetation.js` and `look.js`; do not inherit the gap).
5. Interior styles: the four presets and their sources, that switching recompiles nothing, the deep
   links (`#japandi`, `#desert`, `#luxe`; `?style=` for captures).
6. Baked GI: what the bake stores, when to re-run it, `npm install && npm run bake`, about ten minutes.
7. Volumetrics: one paragraph on the raymarch and where the sun holds and swings.
8. Performance decisions, with numbers equal to the code: shadow zones 600 / 120 / 36 m, calls and
   triangles, render on demand and the 0.75–2 pixel-ratio range, tiers and the phone default, the two
   GI texture fetches, the debug parameters `?p=`, `?q=`, `?tod=`, `&ui=0`.
9. Credits: three.js (MIT), N8AO (MIT), Poly Haven and ambientCG (CC0) and "Independent visualisation;
   not produced by or affiliated with the developer." The trend sources are cited in the styles section,
   not here.

The token cost and what was verified belong in the delivery report, not the README.
