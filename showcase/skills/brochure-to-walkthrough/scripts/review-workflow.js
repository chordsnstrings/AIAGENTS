// Four-dimension audit of a walkthrough project with adversarial verification. Run with the
// Workflow tool: Workflow({ scriptPath: '<skill>/scripts/review-workflow.js', args: {
//   project: '/abs/path/to/project', shots: '/abs/path/with/stills', notes: 'extra context' } })
// Before running, render the evidence into `shots`: 16 route frames with the overlay on
// (rv/p*.png), phone frames (rvm/), night (nt/), each style (sty/<key>/) and interiors with the
// overlay off; keep the capture logs beside them (rv*.log). Every finding is tied to a frame or
// file:line and comes with a concrete fix; a verifier then tries to refute each one by opening
// the same evidence, so only what was actually seen survives.
export const meta = {
  name: 'walkthrough-review',
  description: 'Audit a three.js property walkthrough: realism, experience, performance, robustness, each finding adversarially verified',
  phases: [
    { title: 'Review', detail: 'four specialist reviewers inspect frames and code' },
    { title: 'Verify', detail: 'one skeptic per dimension tries to refute each finding' },
  ],
}

const P = args.project, S = args.shots
const CONTEXT = `Project: a scroll-driven three.js drone walkthrough of a property at ${P} (index.html + style.css + dist/app.js bundled from src/*.js; real-time only). Key files: src/main.js (boot, tiers, update loop, exposure, GI mixing, still mode), src/path.js (keyframes, DroneRig), src/atmosphere.js, src/post.js, src/materials.js (PBR sets, enhance() shader patches, GI lookup), src/gi.js + scripts/bake-gi.mjs, src/styles.js, src/stylesets.js, src/interior.js, src/softgoods.js, src/house.js, src/community.js, src/volumetric.js, src/ui.js, src/plan.js.
Rendered evidence (PNG, open with the Read tool) under ${S}: rv/p*.png route frames with overlay (p = scroll progress; chapters are the data-from/data-to ranges in index.html), rvm/ phone frames, nt/ night, sty/<style>/ per style, interiors with the overlay off; capture logs rv*.log hold load timings and "settled · calls · tris · programs · textures" lines.
${args.notes || ''}
Known, accepted limits (do not report): frames come from a software renderer, so frame rate cannot be measured; the overlay UI is part of the design.
Rules: READ-ONLY review. Do not edit, create or delete files in the project. Read-only shell commands are fine (grep, sed -n, wc, ls, node -e). If you truly need one extra frame: cd ${P} && node scripts/capture.cjs http://localhost:8080 <new-dir-under-${S}> high <p> "&ui=0" (about 40 s per frame; at most 2; never write into the existing evidence dirs).`

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'short unique slug' },
          title: { type: 'string' },
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
          evidence: { type: 'string', description: 'frame path(s) and/or file:line references that show the problem' },
          problem: { type: 'string', description: 'what is wrong and why it matters to the viewer or the client' },
          fix: { type: 'string', description: 'concrete fix: files, approach, values' },
          effort: { type: 'string', enum: ['S', 'M', 'L'] },
        },
        required: ['id', 'title', 'severity', 'evidence', 'problem', 'fix', 'effort'],
      },
    },
  },
  required: ['findings'],
}
const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          verdict: { type: 'string', enum: ['CONFIRMED', 'PLAUSIBLE', 'REFUTED'] },
          reason: { type: 'string', description: 'what you checked and what you saw' },
          better_fix: { type: 'string', description: 'corrected or simpler fix if the proposed one is wrong or overkill; empty if fine' },
        },
        required: ['id', 'verdict', 'reason', 'better_fix'],
      },
    },
  },
  required: ['verdicts'],
}

const DIMS = [
  { key: 'realism', prompt: `You are a senior archviz lighting and look-dev artist. Open every frame and judge photorealism against a photographic standard: exposure jumps or blown/crushed areas, flat or wrong-coloured light, missing contact shadows, materials that read as CG (plastic sheen, repeating or stretched textures, wrong scale), fake-looking soft goods and decor, empty or unstaged rooms, shimmer-prone detail, sky/fog/atmosphere problems, night-mode problems, exterior realism. Cross-check suspected causes in materials.js, styles.js, main.js, softgoods.js, interior.js, atmosphere.js, post.js. Report the 8-14 improvements that would most raise realism.` },
  { key: 'experience', prompt: `You are a creative director and UX lead for luxury real-estate web experiences. Open all route frames and the phone frames, and read src/path.js, index.html, style.css and src/ui.js. Judge camera framing per chapter (is the room's best view shown?), pacing (dead stretches, whips, does it feel like a drone; sample DronePath numerically if useful), whether card text matches what is on screen at that progress, overlay readability and overlap on desktop and phone, loading experience, discoverability of controls, accessibility (keyboard, reduced motion, contrast, focus), and the ending. Report the 8-14 most valuable improvements.` },
  { key: 'performance', prompt: `You are a WebGL performance engineer. Read src/main.js, materials.js, post.js, atmosphere.js, gi.js, community.js, volumetric.js, builder.js, package.json and the capture logs. Measure what you can: bundle size and its parts, texture payload, sets loaded at start, program count, per-frame CPU work in update(), post passes per tier, shadow sizes, mobile choices, memory. Identify the 8-12 changes with the best payoff for load time, frame time on mid-range laptops and phones, and memory, with numbers.` },
  { key: 'robustness', prompt: `You are a meticulous graphics-code reviewer. Review src/gi.js, the shader features in src/materials.js, async read-backs and caches in src/atmosphere.js, src/softgoods.js and the decor helpers in src/interior.js, role handling in src/styles.js, exposure/GI mixing in src/main.js, and scripts/bake-gi.mjs for correctness and compatibility: WebGL2 portability (sampler3D precision, half-float 3D textures with linear filtering, iOS Safari), races, NaN/Infinity risks, leaks (render targets, textures, geometries created per call), missing fallbacks, anything that could fail to load or render black. Report every real bug or risk (aim for 6-14) with file:line, a failure scenario and a fix.` },
]

const results = await pipeline(
  DIMS,
  (d) => agent(`${CONTEXT}\n\nYOUR DIMENSION: ${d.key}.\n${d.prompt}\nBe specific; every finding tied to a frame or file:line with a concrete fix.`, { label: `review:${d.key}`, phase: 'Review', schema: FINDINGS }),
  (r, d) => {
    if (!r || !r.findings || !r.findings.length) return { key: d.key, findings: [], verdicts: [] }
    return agent(`${CONTEXT}\n\nYou are an adversarial verifier for the "${d.key}" review. For EACH finding below, try to refute it: open the cited frames and read the cited code yourself. REFUTED if the evidence does not show the problem, the code does not behave as claimed, it is already handled, or it is an accepted limit. CONFIRMED only if you saw it yourself. PLAUSIBLE for reasonable but unprovable visual/UX judgements. If a proposed fix is wrong, risky or overkill, give a better one.\n\nFINDINGS:\n${JSON.stringify(r.findings, null, 1)}`, { label: `verify:${d.key}`, phase: 'Verify', schema: VERDICTS })
      .then((v) => ({ key: d.key, findings: r.findings, verdicts: (v && v.verdicts) || [] }))
  },
)

const out = []
for (const res of results.filter(Boolean)) {
  const byId = new Map(res.verdicts.map((v) => [v.id, v]))
  for (const f of res.findings) {
    const v = byId.get(f.id)
    out.push({ area: res.key, ...f, verdict: v ? v.verdict : 'UNVERIFIED', verify_reason: v ? v.reason : '', better_fix: v ? v.better_fix : '' })
  }
}
const kept = out.filter((f) => f.verdict !== 'REFUTED')
log(`${out.length} findings, ${kept.length} survived verification`)
return { kept, refuted: out.filter((f) => f.verdict === 'REFUTED').map((f) => ({ area: f.area, id: f.id, title: f.title, reason: f.verify_reason })) }
