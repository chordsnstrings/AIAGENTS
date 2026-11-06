# Performance budgets, captures, cost and publishing

This file covers the subsystems that keep the page fast and the steps that turn a finished build
into a delivered one. Paths are relative to the project root (the template copied from
`/home/user/AIAGENTS/showcase/violet2-flythrough`); `<skill>` is this skill's folder. Every line
number and figure below was read or measured from the template as it stands; re-measure after you
change the files they point at. Decisions and the wrong turns behind them are in
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

Measured on 6 Nov 2026 with `scripts/capture.cjs` at 1024 × 576 on headless Chromium + SwiftShader
(a CPU renderer: the timings are load and settle times, not GPU frame times; say so in any report).

| Measure | Template | Limit (SKILL.md acceptance) |
| --- | --- | --- |
| Draw calls, high, interior (`p=0.45`) | 158 calls · 1.26 M tris · 104 programs · 105 textures | ~150 calls, ≤ 1.3 M tris |
| Draw calls, high, aerial (`p=0.02`) | 180 calls · 1.27 M tris · 104 programs · 106 textures | same |
| Draw calls, low, interior (`p=0.45`) | 145 calls · 0.96 M tris · 93 programs · 91 textures | – |
| First frame / settled (SwiftShader) | 6.6–8.2 s / 8.2–9.8 s after script start | – |
| `dist/app.js` | 1,386,198 bytes (1.32 MiB), minified, uncompressed | ≤ 1.5 MB |
| `assets/tex/` | 29 sets, 87 WebP files, 8,977,288 bytes (8.56 MiB) | ≤ 10 MB |
| Awaited before first frame | 19 base sets, 6,254,334 bytes (5.96 MiB) | – |
| Published artifact | 90 files, 10,386,034 bytes (9.9 MiB) | 256 files, 20 MiB/file, 64 MiB/call |

The aerial frame costs more calls than the interior because nothing is frustum-culled from the air;
programs stay at 104 because every material is compiled once during warm-up (§3).

## 2. Quality tiers (`src/main.js`, `src/post.js`)

`detectTier()` (`main.js` 24–31): `?q=` wins; otherwise `low` when `(pointer: coarse)` matches,
`navigator.deviceMemory <= 4` (8 assumed when the API is absent) or the smaller screen side is under
600 px; else `high`. `mid` is never chosen automatically (no browser signal separates an integrated
GPU from a discrete one); offer `?q=mid` in the README for laptops that stutter. `Q` (33–37):

| Tier | `dprMax` | `shadow` | `ao` / `aoQuality` | `halfRes` | `smaa` | `bloom` |
| --- | --- | --- | --- | --- | --- | --- |
| high | 2 | 4096 | yes / `'Medium'` | yes | yes | yes |
| mid | 1.5 | 2048 | yes / `'Performance'` | yes | yes | yes |
| low | 1.3 | 2048 | no | – | no | yes |

An unknown `?q=` value gets the `high` settings through the `||` fallback on line 37 but `TIER` keeps the
string, so none of the `TIER === 'low'`/`'mid'` switches fire; treat it as `high`.

What each tier drops, traced through `createPost()` (`post.js` 31–61): with `ao` false the composer opens
with a plain `RenderPass` instead of `N8AOPass` (47), and because `VolumetricPass` is only added when
`aoPass && sun` (49–52, it reads depth from `aoPass.beautyRenderTarget.depthTexture`) the light shafts and
haze go with it. `UnrealBloomPass` runs on every tier at half resolution (`size / 2`, strength 0.2, radius
0.32, threshold 9; 55). `SMAAPass` is last and off on `low` (61). Other tier switches in `main.js`:
`buildCommunity(M, heroSpots, { lite: TIER === 'low' })` (108) halves the LOD palms, street palms and
verge bushes and uses 130 instead of 220 desert segments; `volSteps: TIER === 'mid' ? 20 : 28` (126);
dust density 2.5 instead of 5 (130); `Atmosphere` takes `shadowMapSize: Q.shadow` (122). The one AO knob
that moves at runtime is `aoRadius` per zone (194): 5 aerial, 1.4 street, 0.55 house. Keep the tier
values for a new property; they describe devices, not the house.

## 3. Render on demand and adaptive pixel ratio

The loop (`main.js` 282–307) calls `update()` every frame (CPU only) but renders only while
`now <= awakeUntil` and the tab is visible (290). `wake()` (151) pushes `awakeUntil` 1,600 ms ahead and
is called on scroll (152), resize (153–159), `visibilitychange` (160), a mode button (55), a style
change (256), a sky read-back landing (`atmo.onLevel`, 124) and whenever `update()` reports it is still
converging (289). `update()` returns true (237) while progress, time of day or exposure are still
easing (thresholds 1e-5, 1e-4, 1e-3), so a frame is never left half-settled. Why: a scroll page idles
most of the time; after 1.6 s the GPU stops entirely, which is what keeps laptops quiet and phones cool.

Pixel ratio starts at `min(devicePixelRatio, Q.dprMax)` (67). Every 40 rendered frames (293) the mean
frame time decides: above 26 ms, `dpr -= 0.2` down to 0.75; below 13 ms, `dpr += 0.1` up to the cap
(297–298). A change re-applies `renderer.setPixelRatio`, `renderer.setSize(innerWidth, innerHeight,
false)` (CSS size untouched) and `post.setSize` (300–303), which resizes the composer and the grain
`uRes` (`post.js` 64–68). Frames are only counted while rendering, so idle time does not skew the mean,
and the drop is faster than the recovery on purpose.

Warm-up (240–246): every style group is made visible, one `update()`, then `renderer.compileAsync`,
then only the chosen style stays visible. Styles later swap maps and parameters, never material types,
so switching compiles nothing (`styles.js` `apply()`). The SwiftShader warning
`KHR_parallel_shader_compile extension not supported` in capture logs comes from this call; ignore it.

## 4. Static shadow zones (`src/atmosphere.js`)

`renderer.shadowMap.autoUpdate = false` (`main.js` 74): the 4096² map renders only when `needsUpdate` is
set, in `placeSun()` (`atmosphere.js` 129–134) and after a style change (`main.js` 253). `setShadowZone`
(106–118) sizes the orthographic sun camera per zone: half extents `{ aerial: 300, street: 60, house: 18 }`
m (full widths 600 / 120 / 36 m, texels 14.6 / 2.9 / 0.88 cm at 4096, double at 2048), near 1, far
`half * 2 + 400`, target `(-40, 0, -20)` for aerial else `(3.05, 4, -9)` (the plot centre), `normalBias`
0.25 / 0.05 / 0.02, PCF `radius` 1.5 / 2.0 / 3.0. The sun sits at `target + sunDir * (half + 200)`
(131). `setSun` (121–127) ignores moves under 0.15°, so the map re-renders during the terrace swing
(progress 0.735–0.83 and 0.868–0.89, `main.js` 180–182) and nowhere else.

`zoneFor(c)` (`main.js` 163–168): `aerial` above `y 42`; `house` inside `x 0.05–6.05, z −1.4…−15.4,
y < 10.2` or the margin box `x −2…8, z 0…−18.5, y < 12`; else `street`. For a new plot change both boxes
and the tighter `inHouse` box on line 186 to `x 0…PLOT.w`, `z 0…−PLOT.d`; move the house target to the new
centre; grow `house` so the square covers the plot plus a 2–3 m margin (a 12 × 30 m villa needs about 22).

## 5. Instancing and LOD (`src/builder.js`, `src/community.js`, `src/vegetation.js`)

One draw call per material key is the whole strategy. `meshes(geos, mats)` (`builder.js` 128–141) emits
one `Mesh` per key for the hero; `instanced(geos, mats, matrices)` (143–160) emits one `InstancedMesh`
per key with every neighbour as an instance; `instancedFrom(geo, mat, matrices, { cast, receive })`
(`vegetation.js` 110–119) does the same for a single geometry. Everything is frozen with
`matrixAutoUpdate = false` (`community.js` 277).

`buildCommunity(M, heroSpots, { lite })` (`community.js` 64–278): eight curving rows (69–72) around
`R = 260`, blocks of `BLOCK = 7` plots of `PLOT_W = 6.1` m with `GAP = 5`, over `SPAN = 0.62` rad, cut
by two `CROSS` streets. A unit whose centre lies within 72 m of the hero (91) is full detail: the
non-hero `buildShell` geometry and a copy mirrored about `x = 3.05` (`mirrorX`), so alternate units
mirror; the `room` key becomes `roomLit`/`roomDim` instances (62 % lit, `cast: false`) for fake lit
interiors (100–112). Beyond 72 m `lodHouse()` (18–33) stands in: a few boxes plus four quads carrying
the `lod` facade atlas and `lodRoof` (114–119). Units within 7 m (94) also get the shell's planting.
Lamps are five instanced meshes (pole, arm, head, light pool, beam cone; 181–194), the beams named
`lampBeams` and hidden by day (`main.js` 202). Vegetation is six instanced meshes from one palm and two
bush geometries (246–276). The desert is a single 4200 m plane (226–244). `stats { full, lod, palms }`
is returned (278) but not logged; log it while adapting.

For a new property the neighbours follow the hero automatically because they come from the same
`buildShell`; rewrite `lodHouse()` to the new massing, the row table to the masterplan, and `PLOT_W`.
Keep the 72 m full-detail radius: it bounds the heavy instance count. If calls climb, look for a new
material key or a repeated object built with `Builder.add` instead of an instance list.

## 6. Reading the capture log line

In still mode `main.js` (267–279) removes the loader, waits up to 1.5 s for two sky read-backs
(pitfall 15), renders three settle frames, resets `renderer.info`, renders once more and logs

```
[t] settled · 158 calls · 1.26M tris · 104 programs · 105 textures 9.0s
```

`calls` is `renderer.info.render.calls` for that one composer render: scene draws inside the AO or
render pass plus one call per full-screen pass (AO, volumetric, bloom mips, output, grade, SMAA). It is
counted on a frame with no shadow-map render; a zone or style change costs one extra pass over every
caster on that frame. `tris` is `render.triangles` in millions. `programs` is `renderer.info.programs.length`:
compiled shader variants, including depth variants for shadows; a jump means a new material variant.
`textures` is `memory.textures`: GPU textures alive, i.e. loaded sets (57 base files plus the current
style's extras), procedural textures, render targets, the two GI 3D textures, cached PMREM
environments (up to 8, `atmosphere.js` 158) and the shadow map. The trailing figure is seconds since
script start; earlier `[t]` marks are `textures`, `geometry`, `compiled`, `first frame`.

Template values are in §1. Low drops 13 calls (AO, volumetric and SMAA passes, fewer plants), 11
programs and 14 textures (the AO and volumetric targets). Any `error:`, `pageerror:` or `warning:` other
than the SwiftShader compile notice is a defect; the acceptance checklist requires a clean console.

## 7. Bundle composition and the npm scripts

`package.json` (`"type": "module"`): `build` = `esbuild src/main.js --bundle --minify --format=esm
--target=es2020 --outfile=dist/app.js --legal-comments=none`; `dev` = the same unminified with
`--sourcemap --watch`; `serve` = `python3 -m http.server 8080`; `bake` = `node scripts/bake-gi.mjs`.
Dependencies: `three ^0.187.0` (0.187.0 installed), `n8ao ^2.0.1`, `esbuild ^0.28.2`, `postprocessing
^6.39.6` (n8ao's peer; nothing in `src/` imports it, so it is not bundled); dev `three-mesh-bvh ^0.9.18`
(bake only). `index.html` line 176 loads `dist/app.js` as a module script, so the page needs an HTTP
server, never `file://`.

`dist/app.js` is 1,386,198 bytes. Measured with esbuild's metafile (run from the project with
`--metafile=<scratch>/meta.json` added to the build command and summed over `outputs[].inputs[].bytesInOutput`):

| Part | Bytes | Share |
| --- | --- | --- |
| `three` (core 596 KB + `examples/jsm` addons 93,794: SMAAPass 47,215, SMAAShader 13,993, Sky 9,802, UnrealBloomPass 8,485) | 690,105 | 49.8 % |
| `src/gi-data.js` (423,298 bytes of base64 in six strings: `S`, `U`, `N.minimal/japandi/desert/luxe`) | 423,386 | 30.5 % |
| `n8ao` | 158,845 | 11.5 % |
| the rest of `src/` (interior 18.6 KB, materials 12.9, stylesets 10.7, styles 8.8, main 7.7, community 7.7) | 113,692 | 8.2 % |

The GI volume ships as JavaScript because `publish_files` refuses `.bin` (pitfall 18); the price is the
4/3 base64 overhead (317 KB of raw bytes). Its size is `probes × (7 + 6 + 6 × styles) × 4/3`: 13 × 22 × 30 =
8,580 probes × 37 bytes gives the 423 KB above. A larger house raises it linearly: 25 × 22 × 62 probes at
0.5 m would be about 1.68 MB and break the 1.5 MB budget, so widen `SP` in `scripts/bake-gi.mjs` to 0.75
m or drop a style's lamp set before enlarging `DIMS`. Rebuild after every bake; `dist/app.js` embeds the data.

## 8. Texture payload

Each set is three 1024 × 1024 WebP files, `<name>_c` (colour, sRGB), `_n` (normal) and `_r`
(roughness, also used as the AO map; `styles.js` 179), loaded by `loadTextureSets('assets/tex/', …)`
(`materials.js` 8–22) with anisotropy `min(8, max)`. The 19 base sets in `SETS` (`materials.js` 5–6) are
awaited before the first frame and fill the loader from 3 % to 65 %: 6,254,334 bytes. Style extras load
on first use through `createStyler().apply()` (`styles.js` 167–171, a `pending` map prevents double
loads): Japandi `ash, limewash, microcement, papercord` 1,488,080 bytes; Desert `terracotta, clayplaster,
limewash, rattan` 1,417,776 (limewash shared); Luxe `nero, herringbone, smokedwalnut` 556,478. All 29
sets: 8,977,288 bytes; mean 302 KiB per set; largest `grass` 1,164,902 (its normal map alone 551,924),
smallest `travertine` 75,932. `preload(key)` (`styles.js` 203) exists but is not called; call it after
`ui.ready()` if instant switching matters more than bandwidth.

Normal maps are the heavy channel (`grass_n` 552 KB, `limewash_n` 480 KB, `plaster_n` 317 KB). The five
ground sets seen only at distance (grass, sidewalk, sand, asphalt, gravel) are 3,040,136 bytes, 49 % of
the base payload: re-pack those at 512 px or lower quality with `<skill>/scripts/textures.py` before
touching anything the camera meets at arm's length. Add a set by adding it to the manifest, packing it,
and entering its measured mean albedo in `SET_AVG` (SKILL.md step 4, pitfall 6).

## 9. Rendering a still: query parameters and the hash

Parsed in `main.js` 16–18, 48–49 and 100–101:

| Parameter | Effect |
| --- | --- |
| `?p=0.45` | `STILL` mode: progress fixed at `FIXED_P`, no easing, no hover (`rig.update … still: true`, 174), loader removed, `window.__ready` then `window.__shot` |
| `&q=high\|mid\|low` | forces the tier (§2) |
| `&ui=0` | adds `body.noui`; `style.css` 117 and 135 hide header, rail, cards, meter, pin, style buttons, toast |
| `&tod=day\|night` | fixes time of day (`mode`); anything else is `auto`, where `tod = smooth(progress, 0.79, 0.975)` (177), so stills before 0.79 are golden hour |
| `?style=japandi` or `#japandi` | picks the style; the hash is checked first, then `?style=`, default `minimal`; a switch writes `#key` with `history.replaceState` (255) |

Example: `http://localhost:8080/index.html?p=0.70&q=high&ui=0&tod=night&style=luxe`. `__shot` is set
only after the sky read-back wait and three settle frames (267–277) so the still has the right baked
sky level, shadow map and exposure; `__ready` fires earlier, after the first frame, and is what the
live page uses.

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
a 180 s timeout (20, pitfall 16) to `<out>/p<progress>.png`, and prints one line per still: the elapsed
seconds, then de-duplicated console `error`/`warning` lines and the `[t]` marks (at most 12). Measured
output for the template:

```
p=0.45 28.1s
  log: [t] textures 0.4s ... [t] first frame 7.4s
  log: [t] settled · 158 calls · 1.26M tris · 104 programs · 105 textures 9.0s
p=0.02 32.8s   (settled · 180 calls · 1.27M tris · 104 programs · 106 textures)
```

A still costs 28–37 s here; run two processes in parallel for a route sheet and `pkill -f chromium`
between batches. `playwright` is not in `package.json`: in this environment it resolves from
`/opt/node-tools/node_modules/playwright` (1.63.0) with browsers in `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`;
elsewhere `npm i -D playwright && npx playwright install chromium`. Use another port
(`python3 -m http.server 8097`) for a second worktree so two servers never share one.

## 11. `scripts/check-path.mjs`

`node scripts/check-path.mjs [--verbose]` samples the route every 0.001 of progress and exits 1 on any
breach of `LIMITS` (12–19): clearance 0.3 m from any solid surface, look target ≥ 2.4 m from the lens,
pitch within −35°…+40°, yaw ≤ 12° and pitch ≤ 6° per 0.005 of progress (about one wheel notch). Solid
geometry is the hero shell and interior plus the two attached neighbours mirrored about `x = 3.05` and
offset `±6.1` (40–43), minus the `SKIP` keys the lens may pass (pool, room, sheer, lights, lattice,
foliage; 30), in a 0.5 m cell grid. Chapters come from `index.html` attributes written exactly as
`data-from="…" data-to="…" data-rail="…"` (24–26). Output: a header (`route sampled at 0.001; 134508 solid
triangles; N breach run(s)`), one line per run (kind, progress range, worst value with unit, the material
hit for clearance, the card the viewer is reading, camera position with `d = −z`), a per-chapter table
(span, yaw swing, pitch range, minimum look distance and clearance; `1000000000.00 m` means nothing
solid nearby) and the uncaptioned stretches longer than 0.03 (pitfall 21).

As shipped, the template's route does not pass: 30 breach runs, among them a yaw rate of 166.97°/0.005
and a pitch of −79.79° in the Living chapter (p 0.452–0.495), a −86.10° pitch at p 0.802–0.825 with no
card, and three uncaptioned stretches (0.33–0.372, 0.742–0.83, 0.9–0.945). `src/path.js` and the cards
are the parts you rewrite for every property; rewrite them until the script exits 0 (pitfalls 19 and 21,
`camera-and-story.md`), and do not inherit these breaches. For a new plot change the mirror centre and
the `±6.1` offsets on lines 42–43 to the new `PLOT.w`, and extend `SKIP` for any new non-solid key.

## 12. Contact sheets with `<skill>/scripts/sheet.py`

```bash
python3 <skill>/scripts/sheet.py shots shots.jpg 4 500   # dir of p*.png, output, columns, thumb width
```

Frames sort by the progress in their file name, each gets a yellow label, and the JPEG (quality 88) is
written with its size printed. Needs Pillow. Sixteen 1024 × 576 frames at 4 × 500 give a 2000 × 1124 sheet;
use a thumb width of 256 for a 1024 × 576 sheet when you will read it yourself many times, because every
image you open is re-read with the conversation on each later turn (see the cost figures below).

## 13. Measuring the session's token cost

Claude Code writes the transcript to `~/.claude/projects/<cwd with "/" replaced by "-">/<session-id>.jsonl`
(here `/root/.claude/projects/-home-user-AIAGENTS/3d5ceb16-….jsonl`, 40.9 MB) and every subagent or
workflow agent to `<same dir>/<session-id>/subagents/**/agent-*.jsonl`. Each model call is a line with
`"type":"assistant"`, `message.model`, `message.id` and `message.usage`:
`input_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens` (split in
`cache_creation.ephemeral_1h_input_tokens` / `ephemeral_5m_input_tokens`) and `output_tokens`.
Streaming writes one line per content block with the same `message.id` (this session: 694 usage lines
for 305 calls, up to six per call), so de-duplicate by id or the total roughly doubles. Sum per model,
then price. The reference build was costed at Opus-class rates with a 1-hour cache: input $4, output $20,
cache read $0.20, 1-hour cache write $8 per million tokens (a 5-minute write is 1.25 × input). Check the
current price list before quoting money; quote tokens first. This script is what produced the figures:

```python
# python3 -I cost.py <session.jsonl> [agent-*.jsonl ...]
import json, sys, collections
PRICE = {'input': 4.0, 'output': 20.0, 'cache_read': 0.20, 'cache_1h': 8.0, 'cache_5m': 5.0}  # USD / M tokens
best = {}
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
    cc = u.get('cache_creation') or {}; t = tot[model]
    t['input'] += u.get('input_tokens', 0); t['output'] += u.get('output_tokens', 0)
    t['cache_read'] += u.get('cache_read_input_tokens', 0)
    t['cache_1h'] += cc.get('ephemeral_1h_input_tokens', 0 if cc else u.get('cache_creation_input_tokens', 0))
    t['cache_5m'] += cc.get('ephemeral_5m_input_tokens', 0); t['calls'] += 1
for model, t in sorted(tot.items()):
    usd = sum(t[k] * PRICE[k] / 1e6 for k in PRICE)
    print(f"{model:22s} calls {t['calls']:5d}  tokens {sum(t[k] for k in PRICE):>13,}  cache_read {t['cache_read']:>13,}  out {t['output']:>9,}  ${usd:,.2f}")
```

Run it over the main transcript plus `$(find <dir>/<session-id>/subagents -name 'agent-*.jsonl')`. Over
90 % of the tokens are cache reads of the growing conversation, which is why the reference build cost
≈ 48 M tokens (≈ $22.6) and its realism pass ≈ 24 M (≈ $10.9): keep review images small and delegate
broad reading to subagents. Report the result as calls, total tokens, the cache-read share and the price
at the stated rates.

## 14. Publishing to a claude.ai artifact

Publish from a built checkout with `mcp__claude-artifacts__publish_files`, one entry `{ as, path }` per
file, `as` equal to the repo-relative path because the page loads `dist/app.js` (`index.html` 176) and
`assets/tex/<set>_<c|n|r>.webp` (`materials.js` 14, `styles.js` 153) by those relative URLs:
`index.html`, `style.css`, `dist/app.js` and all 87 `assets/tex/*.webp`, 90 files and 10,386,034 bytes
against limits of 256 files, 20 MiB per file and 64 MiB per call. `.bin` is refused (pitfall 18), which is
why the GI data is JavaScript; `.webp`, `.js`, `.css` and `.html` are accepted. On creation omit `slug`
and give `title` and `icon`; the artifact starts private (`read: owner`). To republish, call `list_files`
(the tool requires it for an existing artifact unless the list is already in the conversation), take
`version` from `get_artifact`, pass it as `base_version` and rely on the default `mode: "patch"`: name
only the files that changed (after a rebuild, just `dist/app.js`), list dropped texture sets in `remove`,
and echo `shared_live` if the page has been shared. Query strings are not passed through to the served
page, so `?style=`, `?tod=`, `?p=` and `?q=` do nothing on the artifact URL: the only deep link is the hash
(`#japandi`, `#desert`, `#luxe`), and tier detection must stand on its own (it does; phones get `low`).
`history.replaceState` is wrapped in `try` (255) because sandboxed frames may refuse it. The reference
artifact is "Violet 2 · TH12-4M townhouse flythrough", slug `91f0dcc3-c446-4575-aa72-54724e35fe9b`,
90 files, version `1793964035-d2cb`. Nothing on the published page should rely on `npm run serve`.

## 15. Git hygiene

The repository root `.gitignore` ignores `dist/` (line 8); the project `.gitignore` re-includes it:

```
node_modules/
# the built bundle is committed so the page runs from a plain checkout
!dist/
```

so `dist/app.js` is tracked and a clone, or a publish from one, serves the page without a build step
(pitfall 9). Check with `git check-ignore -v dist/app.js` (no output, exit 1) and `git ls-files dist`.
Commit after every `npm run build` that changes behaviour, with the history's message shape
(`Violet 2 flythrough: route quality check and capture harness`). Capture directories (`shots/`, `rv/`,
`out/`, `*.jpg`) are not ignored by anything: keep them outside the tree or add them to the project
`.gitignore` before `git add -A`. The page carries no buyer contact, price or payment plan (nothing in
`index.html` matches `AED`, `price`, `payment`, `tel:` or `mailto`); the summary card (158–171) shows areas
and the "Visualisation" disclaimer only, and `README.md` line 27 says so. Keep it that way unless the
user asked otherwise in the one round of questions.

## 16. What the README must contain

Model it on the template's `README.md` (103 lines), section for section:

1. Title and one paragraph naming the unit (type, plot, project, city) and the route the camera flies.
2. Quick start: `npm install`, `npm run build`, `npm run serve`, and that module scripts need a server.
3. "What is real and what is illustrative": which figures came from which PDF and page (plot, areas,
   room sizes, levels, parking, facade language, drive times), what is invented (furniture, finishes,
   landscaping, neighbours, views), and that price and payment plan are not shown.
4. Structure: a file → role table covering every `src/` file.
5. Interior styles: the four presets, their research sources, that switching recompiles nothing, and
   the deep links (`#japandi`, `#desert`, `#luxe`, `?style=` for captures).
6. Baked global illumination: what the bake stores, when to re-run it (walls, furniture or lamps moved),
   `npm install && npm run bake`, its duration (about ten minutes at 256 rays).
7. Volumetrics: one paragraph on what the raymarch does and where the sun holds and swings.
8. Performance decisions: shadow zones (600 / 120 / 36 m), draw calls and triangles, render on demand
   and the 0.75–2 pixel-ratio range, the tiers and the phone default, the two GI texture fetches, and
   the debug parameters `?p=`, `?q=`, `?tod=`, `&ui=0`. Keep these numbers equal to the code.
9. Credits: three.js (MIT), N8AO (MIT), Poly Haven and ambientCG (CC0), the trend sources, and
   "Independent visualisation; not produced by or affiliated with the developer."

The token cost and what was verified belong in the delivery report, not the README.
