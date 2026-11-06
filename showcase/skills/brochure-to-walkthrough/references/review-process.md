# Review process: find what is wrong, prove it, fix only that

A walkthrough is judged by people who will never read the code: a buyer scrolling on a phone, a
client comparing it with a rendered photograph. The build session is the worst judge of its own
work, because it knows what every frame is supposed to show. So the review is done by fresh
agents who only see the evidence, and every finding has to survive a second agent trying to
knock it down. Fixing unverified findings wastes a day on taste; fixing confirmed ones moves
the page.

## 1. Render the evidence

Everything the reviewers can know comes from stills and logs. Make them before anything else,
from the served page (`nohup npm run serve`), with the template's `scripts/capture.cjs`:

```bash
cd <project>; mkdir -p rv rvm nt sty/minimal sty/japandi sty/desert sty/luxe
# the route with the overlay ON, 16 frames spread across all chapters (two batches run in parallel)
node scripts/capture.cjs http://localhost:8080 rv high 0.03,0.18,0.35,0.46,0.58,0.69,0.80,0.88 "" > rv1.log 2>&1 &
node scripts/capture.cjs http://localhost:8080 rv high 0.10,0.28,0.41,0.52,0.63,0.76,0.845,0.96 "" > rv2.log 2>&1 &
W=390 H=844 node scripts/capture.cjs http://localhost:8080 rvm low 0.30,0.66 "" > rv3.log 2>&1 &   # phone
wait
node scripts/capture.cjs http://localhost:8080 nt high 0.47,1.0 "&ui=0&tod=night"                 # night
for s in minimal japandi desert luxe; do node scripts/capture.cjs http://localhost:8080 sty/$s high 0.45,0.70 "&ui=0&style=$s"; done
python3 <skill>/scripts/sheet.py rv rv.jpg 4 500      # one sheet to glance at yourself
```

Each still takes 30–50 s on the software renderer; the whole set is ~20 minutes. The logs carry
load timings and the `settled · calls · tris · programs · textures` line the performance
reviewer needs. Keep frames at 1024 × 576: reviewers open many of them, and image tokens add up.

## 2. Run the audit workflow

`scripts/review-workflow.js` (in this skill) runs four reviewers in parallel and one verifier
per reviewer, with the Workflow tool:

```
Workflow({ scriptPath: '<skill>/scripts/review-workflow.js',
           args: { project: '<abs project>', shots: '<abs dir with rv/ rvm/ nt/ sty/>', notes: '<client reference, anything accepted as a limit>' } })
```

The four dimensions and what each is told to look for:

| Reviewer | Lens | Typical confirmed findings on the reference build |
| --- | --- | --- |
| realism | archviz look-dev: exposure, light colour, contact shadows, CG materials, staging, sky, night | flat corners before GI, plastic fabric sheen, white fog at blue hour, unstaged beds |
| experience | creative director + UX: framing per chapter, pacing, copy vs picture, overlay, loading, a11y, ending | camera whips of 160° per wheel notch, bedrooms shot top-down, a garden chapter framing the neighbour's wall, 0.09 of progress with no card, copy naming rooms not on screen, card text below WCAG contrast, no next step at the end |
| performance | WebGL engineer: bundle, textures, programs, per-frame CPU, passes per tier, shadows, memory | 6 MB of textures awaited before first frame, CPU GI re-mix every change, half-float 3D texture uploads |
| robustness | graphics code reviewer: portability, races, NaN, leaks, fallbacks, black screens | async sky read-back with no fallback, render targets not disposed, iOS sampler3D precision |

Every finding must carry evidence (a frame path or `file:line`), the problem as the viewer feels
it, a concrete fix and an effort size. The verifier then opens the same frames and code and
marks each one CONFIRMED (seen it), PLAUSIBLE (reasonable taste call, not provable) or REFUTED
(evidence does not show it, code does not do that, already handled, accepted limit), and may
replace a wrong or oversized fix with a better one. The workflow returns `kept` (confirmed +
plausible, with the verifier's reason and better fix) and `refuted`.

Why the verifier matters: on the reference build the experience reviewer's 14 findings were
all confirmed, but four of their proposed fixes were wrong in detail (a runtime slew clamp that
would break `?p=` stills; a garden vantage that still showed no lawn; a wardrobe-corner camera
with the wardrobe behind the lens; a retime that would have moved the sunset off the terrace).
The better fixes came from the verifier. Read `verify_reason` and `better_fix` before acting.

## 3. Turn findings into a fix pass

Group the confirmed findings by the files they touch, then give each group to one agent that
owns those files and nothing else; agents that would both edit `main.js` run one after the
other, not in parallel. The grouping that worked:

| Wave | Agent | Owns | Typical work |
| --- | --- | --- | --- |
| 1 (parallel, own worktrees) | route & story | `path.js`, `index.html`, `ui.js`, `style.css`, a `story.js` chapter table | route re-authoring with `check-path`, chapter retime, copy, overlay, a11y, ending |
| 1 | look | `materials.js`, `styles.js`, `stylesets.js`, `softgoods.js`, `interior.js`, `atmosphere.js`, `post.js`, `volumetric.js`, `bake-gi.mjs`, `look.js` constants | material and staging fixes, calibration, re-bake |
| 2 (after merge) | engine | `main.js`, `gi.js`, `community.js`, `builder.js` | performance and robustness fixes, loading, tiers, leaks |
| 3 | verify | read-only | `check-path`, full capture set, a verifier per fixed finding |

Each wave-1 agent works in its own git worktree with its own server port and commits on its
branch; merge both, build, then run wave 2 in the main tree. Give every agent: the findings
JSON for its group (with verifier notes), the files it owns, the capture command with its port,
the acceptance checks, and the instruction to leave a note for the next wave about anything it
needed in a file it does not own.

## 4. Prove the fixes

Re-run `node scripts/check-path.mjs` (exit 0), render the same evidence set again, and run the
audit once more with `notes` listing what was fixed. A finding that comes back is not fixed.
Report to the user: what was confirmed and fixed, what was plausible and left, what was refuted
and why, and the before/after contact sheets.

## Reading the results by hand

Each workflow run writes `journal.jsonl` in its transcript directory (the Workflow tool result
names it). Lines with `"type":"result"` carry each agent's structured output, so findings and
verdicts can be read before the run finishes:

```bash
python3 -c "
import json
for l in open('<transcript dir>/journal.jsonl'):
    d = json.loads(l)
    if d.get('type') == 'result': print(json.dumps(d.get('result'), indent=1)[:4000])"
```
