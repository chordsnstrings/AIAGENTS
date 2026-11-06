# Handoff from the look pass

Changes the look findings need in files outside the look agent's set. Every number is in
`src/look.js` (`LOOK`), so the engine only wires them.

## src/main.js

1. **Night point-light pool** (night-lamps-flat). `buildInterior()` now returns `lamps`: bulb
   positions `[x, y, d]` in plan units (d is negated like `lights`). Each style's kit records its
   own floor lamps and pendants in `kit.lamps` (`makeKit(SB, ...)` returns the kit; keep one per
   style). Keep a fixed pool of `LOOK.lampPool` (3) `PointLight`s (decay 2, distance
   `LOOK.lampReach` 2.5 m, `castShadow false`, colour 0xffd2a0) and every chapter move them to the
   three lamps nearest the camera among the fixed lamps plus the current style's; intensity
   `LOOK.lampIntensity` (1.2) times the lamp factor `smooth(tod, 0.3, 0.95)`; cross-fade intensities
   over about 0.4 s when the pool reassigns so lamps never pop. A fixed light count means no shader
   recompiles. Tune against `LOOK.giLamp` (now 0.22: the baked lamp volume bounces off the brighter
   albedos, and the night exposure factor is 1.0), so the surroundings of a lamp are not double-lit
   by the baked pool plus the point light; the bake's `LAMP.lampShade` intensity stays 6.
2. **Bloom ramp** (night-lamps-flat). Each frame `post.bloomPass.threshold =
   LOOK.bloomThresholdK / exposure` (2.5 / exposure; never 1 / exposure, because UnrealBloom passes
   the whole texel above the threshold and by day every sunlit patch would bloom) and
   `post.bloomPass.strength = LOOK.bloomStrength` (0.15), or ramp the strength in with the lamp
   factor. Shades and bulbs then halo softly at night.
3. **Look-in exposure** (glass-no-reflection). Beside `inHouse` (main.js about line 184):
   `const lookIn = inHouseBox(look) && camera.position.distanceTo(look) < 7 ? LOOK.lookInExposure : 0;`
   and use `Math.max(inHouse, lookIn)` as the inside target. `lookInExposure` is 0.35 (about one
   stop); 0.6 blows out the facade now that the render is white.
4. **Style switching** (style-switch-failures). Wrap the boot `await styler.apply(styleKey)` in
   try/catch with a fallback to `'minimal'`; in `applyStyle(k)` drop the `k === styler.current`
   early return (the styler's own request token makes the last click win, so clicking back to the
   current style cancels a pending switch) and add `.catch(...)` that shows a toast; `ui.js:66`
   should not drop the returned promise. Pass `releaseUnused: TIER === 'low'` to `createStyler` so
   a phone frees the style-only sets (and their per-tile clones) it no longer shows.
5. **Atmosphere options**: `new Atmosphere(renderer, scene, { shadowMapSize: Q.shadow,
   envCacheSize: TIER === 'low' ? 4 : 8, probeSize: TIER === 'low' ? 128 : 256 })`. If anything is
   added to the scene after the first frame, call `atmo.refreshMaterials()`. The env-map
   assignment, the reflection probes and their refresh all happen inside `atmo.update()`; nothing
   else to wire.

## src/gi.js (performance agent)

6. **Open-sky fraction into the gradient texture's alpha** (gi-frag-math): in `set()`,
   `b[q + 3] = h(S.open[i])`. `GI_FRAG` (materials.js) now reads `texture(uGi1, gU).a` for
   specular occlusion (`clamp(open * 2.5, 0.03, 1)`); where the alpha is 0 it falls back to the
   irradiance ratio, so the page keeps rendering until this lands.
7. **Sanitise the weights** in `set()` (sky-ratio-nan): `Number.isFinite(v) ? Math.min(Math.max(v,
   0), 64) : 0`. atmosphere.js already refuses zero or non-finite read-backs and clamps the ratio
   to [0, 4].

## src/community.js

8. `M.sand.clone()` (line 214) should be `cloneEnhanced(M.sand)` (exported from materials.js)
   before setting the colour: `Material.clone()` copies neither `onBeforeCompile` nor the uniform
   objects, so the beach silently loses its macro variation and its GI lookup today.

## skills/brochure-to-walkthrough/scripts/textures.py

9. `assets/tex/linen_c.webp` and `boucle_c.webp` were re-packed with their linear contrast
   compressed around the mean (`out = mean + (lin - mean) * k`, linen k 0.4: luminance p5/p95
   0.08/0.87 to 0.27/0.60; boucle k 0.6: 0.15/0.82 to 0.26/0.66), so dividing to a near-white albedo
   no longer pushes half the texels past 1. Add a `contrast` column to `MANIFEST` (1.0 for the
   rest) and apply it in `pack()` so a re-pack from source reproduces these maps; the means
   (`SET_AVG`) are unchanged.

## skills/brochure-to-walkthrough/references (template docs)

10. Update `lighting-and-look.md` and `template-architecture.md` for: `SET_ROUGH` and `roleColor` /
    `roleRoughness` in styles.js; `pbr()` `albedo:` (parsed by the bake) and `flat:`; `enhance`
    features `shade` and `opal`; `glassRear`; the explicit env-map assignment (`env0`, `envK`,
    `envScale` in `userData`); the probes and `refreshMaterials()`; `STATES[0]` sky constants
    8.0 / 1.1 / 0.004 (and `SKY` in the bake); `BAKE_KEY` from `envKey()`; the env cache of render
    targets; `nightstand()` options, `books()`, `tray()`, `pulls()`; `kit.lamps`, `interior.lamps`;
    `drape()` `dropL / dropR / fold / hem`.

## src/path.js (not a look file)

11. `node scripts/check-path.mjs` exits 1 on the untouched main tree with the same 30 breach runs
    as on this branch (look distance 2.29-2.36 m, yaw rate up to 167 deg / 0.005 and pitch -80 deg
    in Living, Bedrooms, Master suite, the roof transit and the terrace): keyframe issues in
    `src/path.js`, none of them clearance (the per-chapter minimum clearance is unchanged by the
    decor added here: 0.35 m). The look pass did not touch the route; whoever owns path.js has to
    clear these before the check gates a build.
