# Architecture

## The shape of the problem

The workbook describes 815 automation units. The naive build is 815 implementations.
The workbook forbids it in its own standing rules:

> Config, not code — vertical and country differences resolve to config; 14 engines
> carry all 815 units.

So the architecture has exactly one job: make that sentence structurally true, rather
than aspirationally true. Everything below follows from it.

```
                    catalogue/ADW_MASTER_AGENT_CATALOGUE.xlsx
                                     │
                        tools/build_catalogue.py
                                     │
                    catalogue/catalogue.json  ── the normalised workbook
                    catalogue/*.yaml             (815 records + reference tables)
                                     │
                        tools/generate_agents.py
                                     │
                    ┌────────────────┴────────────────┐
                    │       engines/mf01..mf14        │   ← the only behaviour
                    │  Engine.compose(record) → Unit  │
                    └────────────────┬────────────────┘
                                     │
                        adw/guardrails.py  ── audit gates the write
                                     │
                          agents/**/*.yaml (815)
                                     │
                    ┌────────────────┴────────────────┐
                    │   adw.registry   adw.router     │   ← the runtime
                    └─────────────────────────────────┘
```

Three properties fall out of this and are each covered by tests:

- **No per-agent code exists.** `grep` the repository: there is no module, class or
  branch named after any of the 815 units. If one appeared, `test_engines.py` would
  not catch it — but the reviewer would, because there is nowhere for it to live.
- **Everything generated is regenerable.** `make check` fails if any file on disk
  differs from what the build would produce. A hand-edit to a spec cannot survive.
- **The standing rules gate the build.** `tools/generate_agents.py` runs the audit
  before writing. A breach is a non-zero exit, not a warning.

---

## Layers

### 1. The catalogue (data)

`tools/build_catalogue.py` reads the nine workbook sheets and joins them. The master
sheet is ordered — core workers, specialists, universal playbooks, vertical playbooks,
each block matching its detail sheet — so the join is positional, and **every pairing
is asserted on a shared field**. A re-ordered workbook fails loudly instead of
silently mis-attributing 355 rows.

The build also mints stable ids the workbook lacks. Specialists appear in the master
sheet as a repeated `V1`, `V1`, `V1`…; they become `V1-S1` … `V1-S5`. Every unit gets
a deterministic path, and colliding paths are a build error.

Two workbook conventions become typed data here:

- **Expected output is the acceptance test**, per the workbook's own legend. Its
  semicolon-separated clauses are split into independently checkable criteria, and
  each criterion is matched to the evidence a reviewer would actually look at
  (a calendar entry with a confirmation id, a payment ledger row, a signed consent
  record).
- **`What stays human` is a gate**, not a note. `Nothing — protocol is absolute`
  becomes an `ABSOLUTE` gate; `Goodwill refunds above threshold` becomes a `BLOCKING`
  gate routed to the approval queue; `Whether to fight or concede` routes to the owner.

### 2. The engines (behaviour)

`engines/base.py` defines the contract. A subclass implements five hooks — `profiles`,
`base_plan`, `base_artifacts`, `mission_body`, `family_guardrails` — and
`Engine.compose()` does everything else identically for all 815 units:

| Composed by | What it guarantees |
| --- | --- |
| Acceptance criteria | Derived from the workbook clause, never invented |
| Standing guardrails | All four attached to every unit, no exceptions |
| Safety interlock | Diamond units get an interlock first and a `stop` last |
| Human gates | Every unit has at least one; diamonds get an absolute one |
| Config keys | Market- and vertical-dependent values declared, never inlined |
| Audit trail | Every unit ends in a `record` step with a retained trail |

Because those live in `compose()` rather than in the fourteen subclasses, they cannot
drift apart. An engine author cannot forget the safety interlock, because they never
write it.

#### Profiles are the mechanism

A profile is a preset within a family: a name, a summary, match tokens, and whatever
extra steps, artefacts, tools and config keys that shape needs. Profile selection is
substring matching against the unit's worker title, system agent name, trigger,
function and expected output — first hit wins, so profiles are ordered
specific-before-general, and the last profile is the unconditional fallback.

This is what lets MF2 carry eighty units — `claim_adjudication`, `defect_ncr`,
`change_control`, `deposit_cancellation`, `dispute_resolution` and so on — with no
per-unit code. `tests/test_engines.py` enforces the discipline in both directions:

- No fallback may carry more than a third of its family (unmodelled shapes).
- No declared profile may go unused (dead config, or a broken match token).

### 3. The audit (enforcement)

`adw/guardrails.py` implements one check per standing rule, plus a structural one:

| Check | Rejects |
| --- | --- |
| `check_probabilistic_authority` | A `decide`/`act` step that clears, diagnoses, advises or approves without a preceding blocking gate |
| `check_safety_protocol` | A diamond unit missing its interlock, its `stop`, or its absolute gate — or containing resolution language |
| `check_owned_channels` | A unit that publishes without declaring a `connected_accounts` grant |
| `check_config_not_code` | A de-globalised term (`DHA`, `RERA`, `ICP`…) or a market literal stated as fact rather than resolved from config |
| `check_structure` | Empty missions, plans that never record, steps producing undeclared artefacts |

The checks are themselves tested: `test_guardrails.py` builds deliberately broken
units and asserts each check fails on them. A check that cannot fail is not a check.

### 4. The runtime

`adw/registry.py` loads the 815 specs and indexes them by family, type, department,
vertical, domain and archetype. `adw/router.py` resolves a `BusinessProfile` into a
roster and a rollout order.

Roster selection is mechanical: 68 core workers + that vertical's specialists and
playbooks + 92 universal playbooks. The *ordering* is where the archetype earns its
keep — anchor agents and revenue-critical units go to **Now**, safety protocols go to
**Now** unconditionally, and Archetype J's recall and reactivation machinery is
skipped rather than shipped inert into a business with no client record.

`missing_config()` closes the loop: it lists the required config keys the country pack
cannot answer. Those are exactly the owner-supplied facts — the price book, opening
hours, who takes a 2am escalation — so onboarding is the work of emptying that list.

---

## Design decisions worth stating

**Positional joins with assertions, not fuzzy matching.** The master sheet duplicates
every detail sheet. Fuzzy-matching the two would quietly tolerate a re-ordered
workbook. Asserting on a shared field at every pairing turns that into a crash.

**Expected output split into clauses, not stored as prose.** A single sentence is not
checkable. `"Invoices issued, retried, receipted; live AR aging"` is four things, and
a run that does three of them has failed.

**Safety handled by construction, not by review.** The 37 diamond units get their
interlock and terminal stop from `compose()`, and the audit independently verifies
what `compose()` produced. Two mechanisms, because the workbook is unambiguous that
for these units escalation *is* the product.

**Country packs are exhaustive, not partial.** Every pack answers every field of the
Localization sheet. A pack with holes would push some unit into inferring the missing
value at runtime, which is the hard-coding the config-not-code rule exists to prevent.
`test_country_packs.py` also rejects two packs sharing a signature, which is what a
blindly copied pack looks like.

**Generated docs, generated specs, generated packs.** Everything derivable is derived
and checked in CI. The only hand-authored artefacts are the workbook, the fourteen
engines, the runtime and the tests.
