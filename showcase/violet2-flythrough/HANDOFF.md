# Hand-off from the engine and integration pass

Every item of the three wave-one hand-offs that fell in this pass's files is applied (the
template references and `scripts/textures.py` included). What remains belongs to files this pass
does not own; each item names the finding, the file and the exact change.

## index.html (gi-data-bundle, follow-up)

The baked light now downloads as `assets/gi/S.json`, `U.json`, `U2.json` and `N-<style>.json`
beside the textures, and the bundle no longer carries it (994 KB minified, 338 KB gzip, from
1,407 KB / 576 KB). The first requests still wait for the module to download and parse. Preload
hints in `<head>`, before the stylesheet link, start them with the HTML:

```html
<link rel="preload" as="fetch" crossorigin="anonymous" href="assets/gi/S.json">
<link rel="preload" as="fetch" crossorigin="anonymous" href="assets/gi/U.json">
<link rel="preload" as="fetch" crossorigin="anonymous" href="assets/gi/U2.json">
<link rel="preload" as="fetch" crossorigin="anonymous" href="assets/gi/N-minimal.json">
<link rel="preload" as="image" type="image/webp" crossorigin="anonymous" href="assets/tex/plaster_c.webp">
<!-- likewise plaster_n, pavers_c, pavers_n, sidewalk_c, asphalt_c, grass_c, sand_c, patio_c, walnut_c -->
```

Keep `crossorigin="anonymous"` on every hint: `TextureLoader` requests images with that attribute
and `fetch()` with same-origin credentials, and a hint without it downloads the file twice. The
phone tier reads `assets/tex/512/`, so the image hints only help the other tiers; the GI hints
help every tier. `N-minimal` is the default style's lamp set; a page that opens on `#japandi`
fetches its own on demand regardless.

## src/house.js and src/proctex.js (street-pool-decals, cleanup)

The three `B.quad('pool', ...)` emitters in `buildShell()` (car-port downlights, front-door strip,
patio strip) are no longer drawn: `main.js` drops the `pool` bucket from the hero's geometries and
`community.js` from the instanced shells, because the same fittings are now splatted into the lamp
irradiance map the ground materials sample. Remove the quads, `M.pool` in `materials.js` and
`radialTexture()` in `proctex.js` when convenient; nothing else references them.

## scripts/check-path.mjs (exterior-unstaged)

The hero and the neighbours now wear `dressShell(B)` from `src/community.js` (roof pavers,
coping, condensers, a tank). The route check builds its solids from `buildShell` and
`buildInterior` only, so the kit is not in its grid. `community.js` imports cleanly under Node
(`node -e "import('./src/community.js')"` succeeds), so add `import { dressShell } from
'../src/community.js'` and call `dressShell(H)` after `buildInterior(H)`, and `dressShell(N)` after
the neighbour shell. The route as authored clears the kit by metres (it never crosses the top roof
below 40 m and passes the terrace coping 0.6 m above it), so the check will still exit 0.

## src/atmosphere.js (shadow-swing, judgement left open)

The shadow half-extents stay `{ aerial: 300, street: 60, house: 18 }`. Tightening `house` to
12–14 m doubles texel density but a fragment outside the frustum renders fully lit; it needs the
terrace frames (p 0.88–0.94) and the street frames (p 0.15–0.21) checked for a cut-off line,
which this pass did not take on.

## Not done, by choice

- KTX2/Basis textures: no encoder here and the transcoder costs 245 KB gzipped (performance pass).
- A CC0 car model for the car port: the finding's verifier advised against rounded-box cars and
  the project takes no new assets without a licence check; the port stays empty.
- `ui.js` `onStyleIntent` callback and `house.js` instanced balusters (both marked optional).
