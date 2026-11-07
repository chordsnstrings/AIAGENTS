# Decisions made and pitfalls met on the reference build

The reference build (Violet 2, DAMAC Hills 2, plot XJ407B, TH12-4M townhouse: 6.1 × 18.5 m plot,
ground + first + roof level, four bedrooms) took five passes: a first flythrough, a volumetric and
interior-styles pass, a realism pass to match an AI-rendered photographic reference, a reviewed fix
pass (route, engine, performance, robustness) and a look polish round. Every decision below was paid
for with a wrong render first. Read this before changing the template so
the same wall is not walked into twice.

## Decisions that shape the template

| Decision | Why |
| --- | --- |
| Real-time three.js only, no generated images or video | The client asked for "as realistic as possible", interactive styles and day/night with no per-view spend. A baked-lighting real-time scene gives one consistent house from every angle; generated frames drift between rooms. |
| `src/plan.js` is the single source of truth | Plot size, levels, every room's x/d range and label drive both the 3D model and the SVG mini-plans in the cards. If a size is wrong it is wrong in one place. Coordinates: x across the plot, d from the street, world z = −d. |
| One merged mesh per material (`Builder`), box UVs in metres | ~150 draw calls for ~1.2 M triangles. Metre UVs make a texture tile at real scale on any box without per-object fiddling. Repeated things (neighbours, palms, shrubs, lamps) are `InstancedMesh`. |
| Finishes named by the albedo they should read as, not by a tint | A tint over a photo-scan whose own mean is 0.21 reads orange or dark. `SET_AVG` (mean linear albedo of each packed colour map) lets a role say `albedo: 0xe8e2d9` and the styler divides out the scan's mean. The GI bake uses the same numbers, so bounce light matches the picture. |
| Baked irradiance volume instead of area lights | RectAreaLights through the windows gave flat, over-bright interiors and cost a full-screen pass. The L1 spherical-harmonic volume (0.5 m probes, sky / sun-bounce / per-style lamps stored separately, mixed per moment on the CPU into two 3D textures) gives soft bounce and corner shadowing for two texture fetches per pixel. |
| Interiors exposed like a photograph, not like physics | Physically, indoor irradiance is ~1 % of the sunlit exterior. A photographer opens up about two stops indoors. The page does the same: exposure ×4.2 by day, ×0.9 at night (`LOOK.insideExposureDay/Night` in `src/look.js`), plus a fill factor on the baked daylight (`LOOK.giFill` 3.4) for bounces past the two the bake traces. |
| Exposure metered over the frame, not the centre ray | A photographer's meter weighs the whole frame. `main.js` casts a 5 × 3 grid of view rays: indoors the look-out lift follows the share of the frame leaving through *sunlit* glazing within reach (glazing in the house's own shade is no brighter than the room), outdoors the look-in lift follows the share of the frame that is room. One centre ray misjudged both ways (pitfall 28). |
| Night rooms lit by lamp pools, not ceiling fills | Point lights under each ceiling lit every wall to one level: an even wash with no pools. The baked lamp volume is now only the room's fill (`giLamp` 0.06) and a pool of three point lights parked on the bulbs nearest the camera carries the falloff; only the terrace fire keeps a point light of its own. |
| Light walls and ceilings in every style, contrast in the joinery | The client's reference had pale walls with dark wardrobes and brass. A `joinery` role (doors, wardrobes, kitchen runs) takes the dark tone per style; walls stay light so the GI has something to bounce off. |
| Soft goods are procedural, not simulated | Duvet with a rolled top edge and pleated drop, pillows with a piped seam and a plumped dent, a throw at the foot, sheers with uneven pleats and backlit emissive. Smooth noise plus a drape rule is enough at flythrough distance; a cloth sim is not. |
| Sun direction fixed per zone, shadow map rendered once per zone | A 4096² shadow map every frame is unaffordable. Time of day changes light colour, sky, fog, exposure and the environment map only; the sun swings once for the terrace sunset. |
| Render on demand, adaptive pixel ratio, three quality tiers | Scroll pages sit idle most of the time. Rendering sleeps when progress has settled. Tiers are pixel budgets (`src/tiers.js`: 3.7 / 2.1 / 0.6 MP), so a retina laptop and a 4K monitor land on comparable frame costs, and the ratio then walks a ladder on measured frame cost. `low` (phones, `?q=low`) keeps AO only in the house and street zones, drops the volumetric march and reads the 512 px textures. |
| Scroll progress → camera through a monotone cubic | Catmull-Rom alone speeds up and slows down between unevenly spaced keys; a monotone cubic from progress to spline parameter keeps speed changes smooth and lets a key hold. Orientation is unwrapped yaw and pitch on the same cubic, never a look point (pitfall 19). |
| One chapter table (`src/story.js`) | Card windows, rail stops, the sunset, the sun swing and the plot pin all derive from `CHAPTERS`, so a retime cannot leave the sunset on the wrong chapter. `check-path.mjs` asserts its rules. |
| Baked light fetched as JSON beside the textures | The bundle stays code only; the GI downloads in parallel with the textures, and only the style on screen decodes its lamps (pitfall 25). |
| Review by rendered stills, in contact sheets | A software renderer (SwiftShader) in headless Chromium renders any progress value in ~30–50 s. Contact sheets of 8–16 stills across the route are the fastest way to see the whole film at once. |
| Multi-agent review with adversarial verification before polishing | Four specialist reviewers (realism, experience, performance, robustness) each followed by a verifier that tries to refute every finding. Only confirmed findings get fixed. |

## Calibration numbers worth keeping

The final values after the polish round. Most live in `src/look.js` (`LOOK`); the rest are named.

- Sun: golden hour elevation 18°, azimuth −55° (south-west through the master suite), swinging to −128°
  and 11.5° in the stair core, then down to 4° over the terrace (`story.js` `SUN`); intensity 4.3 × (1,
  0.81, 0.6). The bake carries the sun bounce for both directions (`U`, `U2`) and the page cross-fades
  them with the swing.
- Time-of-day states (`atmosphere.js` `STATES`): t=0 golden hour (turbidity 8, Rayleigh 2.6, Mie 0.005,
  g 0.62, gain 0.56, exposure 0.7, env 0.55), t=0.5 sunset (exposure 0.88), t=1 blue hour (exposure 2.0,
  env 1.4, sun 0, twilight fog colour). Fog darkens with smoothstep(t, 0.55, 0.92). `bake-gi.mjs` `SKY`
  repeats the golden-hour row.
- Bloom: threshold `bloomThresholdK / exposure` = `2.5 / exposure`, strength 0.15, radius 0.32, and the
  bright pass passes only the excess over the threshold, capped at `bloomCap` 1.0 thresholds; lamps halo
  at night, a low sun's Mie glow cannot flood the frame.
- Indoor exposure `lerp(insideExposureDay 4.2, insideExposureNight 0.9, tod)` × style `inside` (japandi
  1.05, the rest 1.0); `giFill` 3.4; `giSunBalance` (0.92, 1.0, 1.12) on the sun bounce; `giWhiteBalance`
  (1.0, 1.0, 0.97) on the baked sky; `giLamp` 0.06 with `giLampDay` 0.44 (lamps at 44 % of that by day);
  look-in 0.35 × the share of the frame that is room; look-out 0.85 × `min(1, 2.5 × share of frame
  leaving through sunlit glazing)`, faded out towards night; garden shade ×2.2. Targets: a white duvet at
  about 0.85 of the range with its weave visible, walls light and neutral-warm, windows and sun-struck
  sheers at the edge of clipping but not over it.
- GI bake: 13 × 22 × 30 probes at 0.5 m from (0, 0, −15.6); 256 rays; 3 passes; lamps `downlight 18 cd
  (downward cos² lobe)`, `bulb 4`, `lampShade 6`, `led 1.2 per 0.6 m`, `fire 8`; softening radius per
  fixture; probes with > 25 % back-face hits refilled from neighbours. Indoor sky irradiance ends a small
  fraction of the open sky's (indoor mean about 0.15 against a volume maximum of about 1.9 for `S`); that
  is correct, the exposure handles it. Output: `assets/gi/*.json`, 492 KB in
  seven files (286 KB gzip), fetched beside the textures.
- Night: a baked lamp irradiance map outside (R8, 0.24 m per texel, each lamp splatted within 15 m as
  `I cos³θ / d²` windowed to zero) on the ground materials at `streetLamp` 1.2; indoors the baked lamp
  fill plus a pool of three point lights (`lampPool` 3, `lampReach` 4 m, `lampIntensity` 3.0) parked on
  the bulbs nearest the camera; the terrace fire as the one fixed point light (dusk 7, 7 m).
- Volumetrics: 28 steps at half resolution (20 on mid, none on low), outside density 0.0024 (0.0013 from
  the air), inside 0.03 within the house box less the open roof terrace, max distance 55 m street / 280 m
  aerial / 20 m inside; dust 1.5 motes per m³ (0.8 on low) at `dustSun` 0.05.
- Shadow map 2048 on every tier (texels 29 / 5.9 / 1.8 cm); zone extents aerial 300 m, street 60 m,
  house 18 m (half size); far houses and far palms cast only from the air.
- Bundle 996 KB minified (338 KB gzip) with no baked data in it; 157–186 draw calls, 0.84–0.89 M
  triangles, 120 programs per frame on the software renderer.
- Reference costs: first complete build ≈ 48 M tokens (≈ $22.6 at Opus API prices); the realism pass ≈
  24 M tokens (≈ $10.9). Most of it is re-reading the conversation, so keep review images small (1024 ×
  576 contact sheets, not full frames).

## Pitfalls, in the order they bit

1. **Textures cloned before they loaded** rendered black. Load every set, then clone with per-material repeat.
2. **n8ao 2.0.1 on three r187 crashes** (`Cannot read properties of undefined (reading 'length')`) because the shim's `depthDownsampleTarget.texture` getter returns an array. `post.js` patches the getter to return `textures[0]`.
3. **Sky dome scaled past the camera far plane** (30000 vs far 9000) vanished. Sky 9000, stars 3600.
4. **Bloom threshold 1.6 made the whole image milky.** Raised in steps to 9 and the Mie glare reduced;
   the final form is a threshold riding with the exposure (`2.5 / exposure`) and a bright pass that
   blooms only the excess (pitfall 29).
5. **Window area lights overexposed interiors** and still looked flat. Replaced by the baked volume.
6. **Wood looked orange, stone green, palm trunks like birch, the desert red.** Tints on photo-scans multiply the scan's cast. Measure the scan's mean albedo (`scripts/textures.py --measure`), neutralise grey-ish scans at pack time, name finishes by albedo.
7. **The camera flew through the opposite row and under a pergola.** `scripts/check-path.mjs` now reports clearance against the hero, its interior, the rooftop kit (`dressShell`) and both attached neighbours; keep ≥ 0.3 m.
8. **Chairs faced the wall** (backrest at the front): the sign of the local depth axis. Build one chair, render it, then place the rest.
9. **`dist/` was ignored by the repository's root `.gitignore`.** The project `.gitignore` re-includes it (`!dist/`) because the published artifact serves the bundle.
10. **A white veil over everything when looking out of windows** was blamed on volumetrics; the real cause was sky Mie bloom. Fix the cause, not the symptom: compare with the effect switched off.
11. **Limewash and clay plaster looked blotchy.** Re-pack as low-contrast neutral maps and tint; normal scale 0.3.
12. **Fog turned white at blue hour.** The Preetham sky has no twilight; `atmosphere.js` patches a twilight gradient and blends the horizon into the fog colour, and fog darkens with time of day.
13. **The baked lamp component came out 1000× too bright.** Three bugs at once: a downlight lobe written as `max(0, −dir.y)` (pointing up), per-cluster intensity scaled by cluster size, and a stochastic `lamps.length / 2` weighting on top of next-event estimation. Replaced with analytic direct light from clustered fixtures with a softening radius, and bounces only through the probe volume.
14. **L1 spherical harmonics ring** (dark halos behind strong lights). Reconstruct non-linearly (Hazel / Geomerics) in the shader.
15. **The sky brightness read-back is asynchronous.** `LightProbeGenerator` resolves a frame or more later, so the baked sky level flicked between the fitted curve and the measured value. `skyRatio()` now holds the last measured ratio while a read-back is pending and uses the curve only where nothing was ever measured; a zero or non-finite read-back (a lost context, a driver refusing the half-float read) is dropped, or it would turn the whole volume into NaN; the still-capture mode waits up to 1.5 s for two read-backs.
16. **Playwright's 30 s screenshot timeout fails on SwiftShader.** Pass `timeout: 180000`, and kill stray Chromium processes between batches.
17. **The local static server dies when the session's worker restarts.** Start it with `nohup`, check it answers before a capture batch.
18. **Artifact publishing**: `publish_files` accepts relative files but refuses `.bin`; query strings are not passed to the page, so deep links use the `#hash` (style) only.
19. **Camera whips.** Interpolating a look *point* on a spline flips the view when the point passes near the lens: 167° of yaw in one wheel notch, pitch −80°. The implemented design: `path.js` interpolates orientation as unwrapped yaw and pitch, authored look targets stay ≥ 2.4 m from the lens, and `check-path.mjs` holds the route to its limits (yaw ≤ 12° and pitch ≤ 6° per 0.005, pitch −35..+40°, clearance 0.3 m) with no runtime slew clamp; the template's route exits 0.
20. **Card copy that names what is not on screen** (a "kitchen" card while the camera looks down the hall) costs credibility. Shoot what the copy says, or rewrite the copy; check every card against a still at its mid progress.
21. **Uncaptioned stretches** (roof transit of 0.09 progress with no card) are where people stop scrolling. No stretch longer than 0.03 without a card; the chapter table in `story.js` is checked for it.
22. **Additive light decals.** The street lamps' pools were 9 × 9 m additive quads: hard-rimmed ellipses that lit black asphalt as brightly as paving and stacked where lamps faced each other. Bake an irradiance map over the ground instead and let each surface's own albedo take it (`community.js` `bakeLampMap`); window every splat to zero, because a `(1 + (d/h)²)^-1.5` profile alone is still 0.2 at the quad's edge.
23. **A 2D lamp map is a plan.** Looked up by world xz, it lit the balcony floor over a lit car port. Fade it out above head height.
24. **A `ShaderMaterial` on an `InstancedMesh` must apply `instanceMatrix` itself.** The lamp beam cones never did, so all 133 drew stacked at the origin: one blazing cone at the hero's front corner that looked like a volumetric effect and survived the march being switched off. `?hide=lampBeams` found it in one still; `?q=low` (no march) and a `?cam=` view from the side had already excluded the march and the dust.
25. **Baked GI inside the bundle.** 423 KB of base64 in `dist/app.js` was 44 % of the gzipped critical path and decoded every style's lamps at boot. The host refuses `.bin`, so the components went to `assets/gi/*.json`, fetched before the textures and decoded per style on demand; the bundle dropped from 1,407 KB to 994 KB.
26. **Semi-open spaces inside the probe box read as enclosed.** A car port under a balcony or a balcony under a pergola has a low open-sky fraction (rays hit the opposite row), so the volume, fill and lamps included, lights it: the hero's car port takes its night pools from the baked downlights, never from the lamp map as well, or it is lit twice.
27. **Measure before tuning.** A downscaled review image showed the bedding as clipped white; the pixels read 0.70–0.76 with no clipping. Crop at full size and take region means; the ACES shoulder makes 0.77 → 0.87 on screen a half stop in the scene.

28. **Exposure metered by the centre ray.** In the master suite the centre ray left by the party wall a
    hand's width from the front corner while the sunlit front glazing filled the right of the frame, so
    the room was exposed as if it had no window and clipped white (mean luma 194, 12 % clipped). From the
    garden the centre ray entered the living room while two thirds of the frame was shaded paving, so the
    view took the full look-in lift on top of the shade lift and washed milky. Meter the frame: a 5 × 3
    ray grid, sunlit glazing only from inside, the room's share from outside (luma 124, nothing clipped;
    `gardenShadeExposure` 2.5 → 2.2).
29. **Bloom passed the whole texel above the threshold.** Stock `UnrealBloomPass` lets a pixel over the
    threshold through whole, so a low sun's Mie glow, tens of times the threshold over a quarter of the
    sky, bloomed into a white veil across the roof terrace. `post.js` blooms only the excess, capped at
    `LOOK.bloomCap` thresholds. Diagnose a veil with `?off=bloom` and `?off=vol` before touching a number.
30. **The open roof terrace was dusty room air.** It sits inside the volumetric house box, so the march gave
    it room density and, looking into a low sun, washed half the sunset frame white. `volumetric.js` cuts
    the terrace out of the box (`uCutMin`/`uCutMax`) and `inHouseBox` excludes it too.
31. **A paler sky needs more Rayleigh, not less.** In three's Preetham model the blue channel's extinction
    saturates first, so a thick scattering column lifts red and green towards it; Rayleigh 1.1 left a deep
    #2c65a5 overhead. Rayleigh 2.6, Mie 0.005, g 0.62 with the gain cut to 0.56 (to hold the sky's
    irradiance, so exposures and the baked fill keep their level) gives #6599b7. Change `bake-gi.mjs` `SKY`
    with `STATES[0]` and re-bake.
32. **`Material.clone()` drops `onBeforeCompile`.** A clone copies neither the shader patch nor the uniform
    objects (`userData` survives only as JSON), so the beach's sand clone silently lost its macro variation
    and GI. Clone enhanced materials with `cloneEnhanced(m)`, which re-applies the features.
33. **Ceiling fill lights made night an even wash.** Point lights under the living-room and landing
    ceilings lit every wall to one level, and the baked lamp volume at `giLamp` 0.22 did the same. The
    fills are gone, `giLamp` is 0.06 (the day level kept through `giLampDay` 0.44) and the bulb pool
    carries the falloff (3.0 at 4 m reach).
34. **Metals indoors mirrored nothing.** Specular occlusion by the open-sky fraction left a brass pull in a
    room that sees little sky reflecting almost nothing: a black slot (#2d1e15 against #311f15 doors).
    `GI_FRAG` fills the hidden part with the room's own light (a mid albedo times the irradiance over π);
    the pulls read as brass (#5f4121).
35. **A disposed PMREM texture frees nothing.** three registers no dispose listener for a render-target
    texture, so a cache of textures leaked every environment. Cache the render target and dispose that; pin
    the bake's reference env and the one on screen.
36. **Keys stepped from the eased progress.** A second arrow press mid-flight found the camera still short
    of the first landing and asked for it again. Step from the landing last requested until the flight
    reaches it, the visitor takes over (wheel, touch, pointer) or 4 s pass.
37. **Only one chapter was readable to a screen reader**, because inactive cards are `aria-hidden`. A skip
    link leads to a visually hidden section holding every chapter's text, cloned from the cards.
38. **Phones downloaded the desktop textures.** The 1024 px preloads in `index.html` ran on every device,
    then the low tier fetched the 512 px set as well. The preloads carry `media="(pointer: fine) and
    (min-width: 900px)"`; the GI preloads have none.

## Research that fed the interior styles

Dezeen (2026 interiors), 1stDibs 2026 designer survey, Khaleej Times on Dubai "restrained luxury", Bayut UAE interior trends, Domus Academy, and the paint colours of the year. The four presets: Warm Minimal (travertine, pale oak, ivory bouclé, lavender accent), Japandi Calm (oak slats, limewash, paper cord, black ash), Desert Organic (clay plaster arches, terracotta, rattan, caramel elm), Aubergine Luxe (nero marble, fluted walnut, brass, velvet). Credit the sources in the page's summary fine print.
