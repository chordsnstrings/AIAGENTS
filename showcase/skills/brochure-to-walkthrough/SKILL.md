---
name: brochure-to-walkthrough
description: Turn a property brochure or floor-plan PDF (townhouse, villa, apartment, off-plan unit) into a complete, polished, scroll-driven real-time three.js drone walkthrough web page - aerial approach, street, facade, every room at true size, roof or garden, sunset finale - with photoreal PBR finishes, baked global illumination, four switchable interior styles, day/night, chapter cards with mini floor plans, and a published shareable page. Use this whenever someone wants a 3D flythrough, flyover, walkthrough, virtual tour, scrollytelling page or "scene in three.js" of a property from a PDF, plan, sales offer or listing, and whenever they ask for "as realistic as possible", real-time, interactive styles, or no image-generation spend. Prefer it over AI-video approaches (the ModelArk property-flythrough skill) unless the user explicitly wants generated footage.
---

# Brochure PDF → real-time three.js walkthrough

One HTML page: scrolling flies a drone from the community, along the street, through the front
door and every room, up to the roof, and out into the sunset, while chapter cards give each
room's name and true size with a mini plan. Everything renders live in the browser from a
template this skill ships (`assets/template/`): a finished, reviewed build of a 4-bedroom
townhouse that reached photographic interiors. Your job is to adapt the template to the new
property and bring it back to the same polish, not to rebuild it.

Reference build: Violet 2 (DAMAC Hills 2) TH12-4M, 6.1 × 18.5 m plot, three levels. Per property
the plan, shell, interior and style-set files (about 1,100 lines), the route and chapter tables and
the cards are rewritten; the engine is reused. Whole build ≈ 48 M tokens; a realism pass ≈ 24 M.
Budget for it and keep review images small.

## Inputs and the one round of questions

Collect: the developer brochure (floor plans with room dimensions, area schedule, facade renders,
masterplan and amenities) and the sales offer or unit plan (unit type and number, plot, floor
areas, orientation if given). Ask once, in a single AskUserQuestion, only what the PDFs cannot
answer: branding (default none), price and buyer details on the page (default no), interior
styles wanted (default the four researched presets), day + night (default yes), where to publish
(default a claude.ai artifact). Then do not ask again; decide and state your decisions.

## Rules that matter

1. **Sizes stay honest.** Every room in `src/plan.js` has the brochure's dimensions; the mini plans
   and the 3D rooms come from the same table. Label the page "Visualisation"; furniture and
   finishes are illustrative and the summary says so. Never invent community facts; pull them
   from the PDFs or leave them out.
2. **No per-view spend.** No image or video generation; the realism comes from the template's
   PBR scans, baked GI and calibrated exposure. If the user shows a generated reference image,
   match its lighting, staging and palette in the real-time scene.
3. **The camera is a drone, not a mouse-look.** Orientation turns at most 12° per 0.005 of scroll,
   pitch stays within −35°…+40°, the look target stays ≥ 2.4 m from the lens, the lens stays
   ≥ 0.3 m from any surface, and no stretch longer than 0.03 of progress goes without a card.
   `scripts/check-path.mjs` (in the template) enforces all of this; a route that fails it is not
   finished.
4. **Copy matches the picture.** Every card is checked against a still at its mid progress: if the
   card says kitchen, the kitchen is on screen. Rewrite copy or re-aim the camera until true.
5. **Light walls, contrast in the joinery, soft goods that drape.** Every style keeps pale walls and
   ceilings (the GI needs them), puts its dark tone in a `joinery` role, and stages beds with the
   procedural duvet, pillows, throw, prints, flowers and a rug. Empty rooms read as CG.
6. **Verify with stills, not hope.** Render contact sheets across the whole route after every
   structural change, at desktop and phone sizes, day and night, every style. Read them.
7. **Report faithfully.** Say what was checked (software renderer only, no real GPU timing), what
   was not, and what the token cost was.

## Pipeline

Read `references/template-architecture.md` before step 3 and keep it open; it says which file
owns what and what to change for a new property.

### 1. Extract the unit
- `pdftotext -layout` both PDFs; read the unit type, saleable and plot areas, floor areas,
  parking, orientation, community facts (amenities, travel times) and the developer's finish
  descriptions.
- `pdftoppm -r 150 -png` the plan pages; crop the exact unit (end vs middle units differ) and
  read every room label and dimension. Where the PDF is image-only, read the page images.
- Write a facts note (unit, plot w × d, levels and heights, rooms per level with x/d ranges and
  sizes, facade materials, landscaping, what surrounds the plot). This becomes `plan.js`.

### 2. Stand the template up
```bash
cp -r <skill>/assets/template <dest> && cd <dest> && npm install && npm run build
nohup npm run serve > /dev/null 2>&1 &         # http://localhost:8080
node scripts/capture.cjs http://localhost:8080 shots high 0.0,0.45 "&ui=0"
```
The two stills prove the toolchain (Chromium + SwiftShader, about a minute per still including
start-up). Keep the server under `nohup`; it dies with the session worker otherwise.

### 3. Plan, shell, interior
- `src/plan.js`: PLOT, H (level heights), ROOMS (f, key, name, x[], d[], size), STAIR, FACTS.
  x runs across the plot, d from the street, world z = −d.
- `src/house.js`: openings, glazing, railings, pergola, roof block, neighbour variant.
- `src/interior.js`: floors, walls, stairs, doors, kitchen, bathrooms, fixed joinery, bedrooms,
  decor (prints, rugs, vases); `src/stylesets.js`: the per-style living/dining/master furniture.
- Check each room from a still before moving on (`?p=` on the current route, or a temporary
  keyframe). Chairs facing the wall and doors swinging into walls are found this way, not later.
- `src/community.js`: rows, streets, landscape and landmarks from the masterplan; adjacent
  neighbours are mirrored copies of the shell; farther rows use the LOD atlas.
- The house boxes that are this plot's numbers: `inHouseBox`, `zoneFor`, the garden-shade box,
  the glazing faces `frameShare` tests and the dust boxes in `src/main.js`; `uBoxMin`/`uBoxMax`
  and the terrace cut in `src/volumetric.js`.

### 4. Finishes and styles
- Textures: the template ships 29 packed CC0 sets (`assets/tex/`, and `assets/tex/512/` for the
  phone tier). Add a finish to `MANIFEST` in `<skill>/scripts/textures.py`, then
  `python3 <skill>/scripts/textures.py dl assets/tex <name>`,
  `python3 <skill>/scripts/textures.py --downscale 512 assets/tex`, and put its mean linear albedo
  (`--measure assets/tex <name>`) in `SET_AVG` and the mean of its `_r` green (roughness) channel
  in `SET_ROUGH` (`src/styles.js`).
- Styles: keep the four researched presets unless asked; re-tune `roles` to the brochure's
  palette by albedo (`albedo:` not `color:` for walls, floors and ceilings). Style furniture
  positions follow the new living/dining/master layout.
- Read `references/lighting-and-look.md` for every knob and the calibration order.

### 5. Light it
Freeze geometry first (the bake traces it), then:
```bash
RAYS=16 npm run bake     # about 2 min, enough to see; writes assets/gi/*.json, no rebuild needed
node scripts/capture.cjs http://localhost:8080 gi high 0.385,0.56,0.655,0.85 "&ui=0"
RAYS=256 npm run bake    # about 12 min, final
```
The photographic constants are `LOOK` in `src/look.js`. Tune in this order: `insideExposureDay`
(headroom for sheers and sun patches), `giFill`, `giSunBalance` and `giWhiteBalance`, the night
(`giLamp`, `lampIntensity`, `insideExposureNight`, `streetLamp`), then per-style `inside`.
Interiors should read like a photograph taken at the window's exposure plus two stops: bright,
soft, no blown windows, no grey corners. Diagnose a stray veil or highlight in a still with
`&off=vol,bloom` (drops the march or the bloom), `&hide=<material key>` and `&cam=x,y,z,lx,ly,lz`.

### 6. Route and story
`src/story.js` `CHAPTERS` holds every chapter's card window, rail label and `jump`; the sunset, sun
swing and plot pin follow from it. `src/path.js` `KEYS` are `[progress, position, look, fov,
lensShift?]`; `index.html` cards name their chapter with `data-chapter`. Author each chapter as
a hold or a slow arc around a fixed target: bedrooms from a 3/4 eye-height view showing bed,
window light, wardrobes and prints; the garden from the lawn looking back at the lit glazing;
the kitchen actually in frame on the kitchen card. Run
`node scripts/check-path.mjs` until it exits 0, then contact-sheet the route:
```bash
node scripts/capture.cjs http://localhost:8080 rv high 0.03,0.1,0.18,0.28,0.35,0.41,0.46,0.52,0.58,0.63,0.69,0.76,0.8,0.845,0.88,0.96 ""
python3 <skill>/scripts/sheet.py rv rv.jpg 4 500
```
Read `references/camera-and-story.md` for the composition rules per chapter, pacing, copy,
overlay and accessibility.

### 7. Review, then fix only what is confirmed
Run the four-dimension audit (`references/review-process.md`, `scripts/review-workflow.js`):
realism, experience, performance, robustness, each finding adversarially verified. Fix confirmed
findings; list plausible ones for the user. Re-run `check-path` and the contact sheets after.

### 8. Deliver
- `npm run build`; README with what is real vs illustrative, controls, structure, credits
  (texture sources, interior-trend research), re-bake instructions.
- Publish: `publish_files` with `index.html`, `style.css`, `dist/app.js`, `assets/gi/*.json`,
  `assets/tex/*.webp`, `assets/tex/512/*.webp` and `assets/poster.jpg` (patch mode on republish;
  `.bin` is refused; deep links are `#style` hashes only).
- Commit including `dist/` (the page runs from a plain checkout). No buyer contact or price
  unless asked.
- Report: link, what was verified, known limits, token cost
  (`references/performance-and-publishing.md` shows how to compute it).

## Acceptance checklist

- `node scripts/check-path.mjs` exits 0; no card gap > 0.03.
- A still at each card's mid progress shows what the card names; sizes match the PDF.
- Desktop (1024 × 576 and 1440 × 900) and phone (390 × 844, `?q=low`) sheets read well with the
  overlay; night sheet and all four styles checked.
- Console clean in the capture logs (a forced `?q=low` at desktop width warns about the unused
  1024 px preloads; that alone is expected); ~150–190 draw calls, ≤ 1.3 M triangles on high,
  bundle ≤ 1.5 MB, textures ≤ 10 MB per tier.
- Overlay: every card fits at 1024 × 576; the skip link, the hidden chapter text and the
  always-visible visualisation line on the summary card are present.
- Interiors: bright soft daylight, no blown glazing, beds staged, prints and flowers present,
  joinery contrasting, no flat grey corners; night: warm lamplight, no glowing hero shell.
- README, credits and the summary's "visualisation" disclaimer present.

## When things look wrong

`references/decisions-and-pitfalls.md` lists the 38 ways the reference build went wrong and the
fix for each (black textures, n8ao crash, milky bloom, orange wood, white fog, whip pans, lamps
1000× too bright, SH ringing, beams stacked at the origin, centre-ray exposure, a bloom veil over
the terrace...). Check it before debugging from scratch, and isolate with `?off=`, `?hide=` and
`?cam=` stills before changing a number.

## References

| Read when | File |
| --- | --- |
| Before touching any file | `references/template-architecture.md` |
| Calibrating lighting, materials, styles, soft goods | `references/lighting-and-look.md` |
| Authoring the route, cards, overlay | `references/camera-and-story.md` |
| Budgets, captures, cost, publishing | `references/performance-and-publishing.md` |
| Running the audit | `references/review-process.md`, `scripts/review-workflow.js` |
| Something renders wrong | `references/decisions-and-pitfalls.md` |
