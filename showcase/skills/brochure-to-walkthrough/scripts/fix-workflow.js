// Fix pass over confirmed review findings, in waves that never edit the same file twice at once.
// Run with the Workflow tool once per wave:
//   Workflow({ scriptPath: '<skill>/scripts/fix-workflow.js', args: {
//     wave: 'one' | 'two' | 'verify',
//     project: '/abs/path/to/project',                 // the project folder inside the repository
//     repoSubdir: 'showcase/violet2-flythrough',        // the same folder relative to the repository root
//     skill: '/abs/path/to/this/skill',
//     findings: { route: [...], look: [...], engine: [...] },   // confirmed findings per area, verifier notes included
//     notes: { route: '...', look: '...', engine: '...' },      // design guidance per area (optional)
//     ports: { route: 8081, look: 8082, engine: 8083 },
//     trailers: 'Co-Authored-By: ...\nClaude-Session: ...' } })   // commit trailers the session must use
// Wave one runs the route-and-story agent and the look agent in parallel, each in its own git
// worktree and on its own port, and each commits on its branch. Merge both branches into the
// working branch and rebuild before wave two, which runs the engine agent in the main tree.
// 'verify' runs one read-only checker per area against the merged result.
export const meta = {
  name: 'walkthrough-fix-pass',
  description: 'Apply confirmed review findings to a three.js property walkthrough in file-disjoint waves, then verify',
  phases: [
    { title: 'Wave one', detail: 'route & story, look: parallel in worktrees' },
    { title: 'Wave two', detail: 'engine: main.js, gi.js, community.js' },
    { title: 'Verify', detail: 'one checker per area' },
  ],
}

const P = args.project, SUB = args.repoSubdir, TR = args.trailers || '', SK = args.skill, F = args.findings || {}, N = args.notes || {}, PORTS = args.ports || {}
const OWN = {
  route: ['src/path.js', 'src/story.js (new, the chapter table)', 'index.html', 'src/ui.js', 'style.css', 'README.md (route/controls sections)', 'main.js ONLY inside the STILL block and the lines that read the chapter table'],
  look: ['src/materials.js', 'src/styles.js', 'src/stylesets.js', 'src/softgoods.js', 'src/interior.js', 'src/house.js', 'src/atmosphere.js', 'src/post.js', 'src/volumetric.js', 'src/proctex.js', 'src/vegetation.js', 'src/look.js (the look constants)', 'scripts/bake-gi.mjs', 'src/gi-data.js (by re-baking)', 'README.md (lighting/styles sections)'],
  engine: ['src/main.js', 'src/gi.js', 'src/community.js', 'src/builder.js', 'package.json', 'README.md (performance section)', 'plus anything the wave-one hand-off notes ask for'],
}
const COMMON = (area) => `You are fixing confirmed review findings in a scroll-driven three.js property walkthrough (real-time only; index.html + style.css + dist/app.js bundled by esbuild from src/*.js). Project folder: ${P} in the main tree${args.wave === 'one' ? `; you run in a fresh git worktree of the repository, so work in ${SUB} under your current working directory, not in the main tree` : ''}.
Read these first: ${SK}/references/decisions-and-pitfalls.md, ${SK}/references/template-architecture.md and, for your area, ${area === 'route' ? `${SK}/references/camera-and-story.md if it exists` : area === 'look' ? `${SK}/references/lighting-and-look.md` : `${SK}/references/performance-and-publishing.md`}.
FILES YOU OWN (edit nothing else; if a fix needs another file, write what is needed into HANDOFF.md at the project root and carry on): ${OWN[area].join(', ')}.
Setup: cd into the project; npm install; nohup python3 -m http.server ${PORTS[area] || 8080} > /dev/null 2>&1 & ; npm run build after every change you want to see. Stills: node scripts/capture.cjs http://localhost:${PORTS[area] || 8080} <dir> high <p1,p2,...> "&ui=0" (about 40 s each on the software renderer; add "&tod=night" or "&style=<key>" as needed; omit "&ui=0" to see the overlay; W=390 H=844 for a phone). Contact sheets: python3 ${SK}/scripts/sheet.py <dir> <out.jpg> <cols> <thumb-width>. Route check: node scripts/check-path.mjs (must exit 0 at the end; never loosen its limits). Open the stills you render with the Read tool and judge them; a fix is done when a still or a check shows it, not when the code looks right.
Rules: keep the template's voice (docstrings say why, comments sparse, British spelling in prose); no new runtime dependencies; never state which model you are in code, docs or commit bodies (the required trailer lines are the one exception); do not weaken a check to pass it; after each finding is fixed, note it in your running summary. Commit your work on the current branch with git (one or a few commits with clear messages; end every commit message with these trailer lines, verbatim:\n${TR}). When done, return: the branch name and worktree path (git rev-parse --abbrev-ref HEAD; pwd), a list of findings fixed with how each was verified, findings not fixed and why, and the contents of HANDOFF.md if any.
FINDINGS FOR YOUR AREA (id, severity, evidence, problem, fix, verifier reason and better fix):\n${JSON.stringify(F[area] || [], null, 1)}\n${N[area] ? `DESIGN NOTES FOR YOUR AREA:\n${N[area]}` : ''}`

if (args.wave === 'one') {
  const res = await parallel([
    () => agent(`${COMMON('route')}\nYOUR AREA: route & story. You own the camera route, the chapter table, the cards, the overlay and accessibility.`, { label: 'fix:route', phase: 'Wave one', isolation: 'worktree' }),
    () => agent(`${COMMON('look')}\nYOUR AREA: look. You own materials, styles, staging, soft goods, atmosphere, post-processing, the look constants and the GI bake. Re-bake (RAYS=16 to check, RAYS=256 to finish) after any change to geometry, albedo or lamps, and rebuild.`, { label: 'fix:look', phase: 'Wave one', isolation: 'worktree' }),
  ])
  return { route: res[0], look: res[1] }
}
if (args.wave === 'two') {
  return await agent(`${COMMON('engine')}\nYOUR AREA: engine. You own the boot and update loop, GI runtime, community and builder. Also apply every request in HANDOFF.md left by wave one, then delete HANDOFF.md.`, { label: 'fix:engine', phase: 'Wave two' })
}
if (args.wave === 'verify') {
  const areas = Object.keys(F).filter((a) => (F[a] || []).length)
  const out = await parallel(areas.map((a) => () => agent(`You are a read-only verifier for a fix pass on a three.js property walkthrough at ${P}. For EACH finding below, check whether it is now fixed: read the code it cites and render a still where the evidence was visual (node scripts/capture.cjs http://localhost:${PORTS.engine || 8080} <new dir under /tmp> high <p> "&ui=0" with the project served on that port; node scripts/check-path.mjs for route findings; open stills with the Read tool). Do not edit any project file. Return a JSON-like list: id, status FIXED | PARTLY | NOT_FIXED | REGRESSED, and one sentence of evidence each; then any regression you noticed that no finding describes.\nFINDINGS:\n${JSON.stringify(F[a], null, 1)}`, { label: `verify:${a}`, phase: 'Verify' })))
  return Object.fromEntries(areas.map((a, i) => [a, out[i]]))
}
return 'args.wave must be one, two or verify'
