# Violet 2 — TH12-4M townhouse flythrough (three.js)

Scroll-driven, real-time 3D flythrough of **plot XJ407B** (unit `VOT2/SD143/XJ407B`), a
four-bedroom **TH12-4M** mid-terrace townhouse in **Violet 2, DAMAC Hills 2, Dubai**.
The camera behaves like a stabilised drone: an aerial approach over the community, an
orbit to the street, then through the front door, every floor, out over the garden and
balconies, onto the roof terrace at sunset and back up into a blue-hour aerial.

```bash
npm install
npm run build     # bundles src/ -> dist/app.js (three.js r187 + n8ao)
npm run serve     # http://localhost:8080
```

Open `index.html` through any static server (module scripts do not run from `file://`).

## What is real and what is illustrative

Real, from the developer documents (sales offer + Violet brochure p.27):
plot 6.10 × 18.50 m (112.85 m²), room positions and sizes, three levels, two covered
parking spaces, saleable areas (589.22 / 632.92 / 296.12 / 834.00 sq ft = 2,352.26 sq ft),
facade language (white render frame, grey stone, bronze railings and lattice screen,
slatted timber pergolas), community drive times and amenities.

Illustrative: furniture and finishes, landscaping, the neighbouring cluster layout
(curving back-to-back rows modelled on the sales-offer location plan), lagoon and dunes.
The page says so in its summary card. Price and payment plan are deliberately not shown.

## Structure

| File | Role |
| --- | --- |
| `src/plan.js` | Single source of truth: plan coordinates (x across plot, d from street, z = -d), levels, rooms. Drives both the 3D model and the SVG mini-plans. |
| `src/builder.js` | Accumulates boxes/quads/geometry per material key and emits one merged mesh (or one `InstancedMesh`) per material. Box UVs are in metres so textures tile at real-world scale. |
| `src/house.js` | Exterior shell of one townhouse. Hero copy has real balusters and open doors; neighbours get alpha railing cards and fake lit interiors. |
| `src/interior.js` | Hero-only interior: floors, linings, stacked dog-leg stair, doors, kitchen, bathrooms, furniture, interior lights. |
| `src/community.js` | Curving rows of 7-unit blocks around the hero (mirrored alternates), LOD blocks with a facade atlas further out, streets, lamps, palms, lagoon, desert. |
| `src/materials.js` | PBR sets from CC0 photo-scans (Poly Haven, ambientCG) packed as WebP colour / normal / AO-roughness; shader patches for tile joints, macro variation, fresnel glass, palm sway. |
| `src/atmosphere.js` | Preetham sky with lit clouds, sun + shadow zones, PMREM environment from the sky, fog, stars, time of day. |
| `src/path.js` | Keyframed drone route (centripetal Catmull-Rom + monotone progress mapping) and gimbal rig (lag, bank, hover). |
| `src/post.js` | N8AO ambient occlusion, volumetric light, bloom, ACES output, grade/vignette/grain, SMAA. |
| `src/volumetric.js` | Shadow-map raymarched light shafts and haze, dust motes, lamp cones. |
| `src/styles.js`, `src/stylesets.js` | Interior style presets (materials) and their furniture sets. |
| `src/ui.js` | Loader, chapter cards, rail, mini-plans, plot pin. |

## Interior styles

Four presets researched from 2026 trend reporting (Dezeen, 1stDibs designer survey, Khaleej
Times on Dubai "restrained luxury", Bayut UAE trends, Domus Academy, paint colours of the
year): **Warm Minimal**, **Japandi Calm**, **Desert Organic**, **Aubergine Luxe**. A preset
re-parameterises shared material roles across the whole house (`src/styles.js`) and shows
its own living, dining and master-bedroom furniture (`src/stylesets.js`). Material types
never change, so switching recompiles nothing; a style's extra textures load on first use.
Deep link with `#japandi`, `#desert`, `#luxe` (or `?style=` for captures).

## Volumetrics

`src/volumetric.js`: a half-resolution raymarch through the sun's static shadow map gives
shafts through glazing, pergola slats and palms, and a height-weighted haze; density is
per sample (dusty air inside the house volume, thin haze outside). Dust motes sparkle only
where the shadow map says sunlight reaches them; lamp cones fade in at dusk. The sun holds
south-west through the master suite, swings north-west for the terrace and sets at the
sunset view so the rays meet the visible sun.

## Performance decisions

- Sun direction is fixed; the shadow map renders once per zone (aerial 600 m, street 120 m,
  house 36 m) instead of every frame. Time of day changes light, sky and environment only.
- ~1 M triangles but ~150 draw calls: per-material merging for the hero, instancing for
  every neighbour, palm and shrub.
- Rendering sleeps when the scroll has settled; resolution adapts to frame time
  (pixel ratio 0.75–2). Quality tiers: `?q=high|mid|low` (mobile defaults to `low`: no AO,
  no area lights, 2048 shadows).
- Debug/capture: `?p=0.42` renders a single still at that progress; `?tod=night` forces blue hour.

## Credits

three.js (MIT), N8AO (MIT), textures from Poly Haven and ambientCG (CC0).
Independent visualisation; not produced by or affiliated with the developer.
