# ADW Master Agent Catalogue

Every automation unit in `ADW MASTER AGENT CATALOGUE.xlsx`, built.

**815 units** — 68 core workers, 355 vertical specialists, 92 universal playbooks,
300 vertical playbooks — across **10 departments**, **60 verticals** and **10 archetypes**,
carried by **14 mechanism-family engines** and **29 country packs**.

Each unit has a complete, individually materialised spec on disk: mission, plan,
named artefacts, acceptance criteria, guardrails, human gates, config keys, tools and
KPIs. Nothing is sampled, stubbed or templated over.

```
catalogue/ADW_MASTER_AGENT_CATALOGUE.xlsx   the workbook (source of truth)
        -> tools/build_catalogue.py         normalise
catalogue/catalogue.json                    815 joined records + reference tables
        -> tools/generate_agents.py         compose through the engines
agents/**/*.yaml                            815 unit specs
        -> adw.registry / adw.router        serve
```

---

## The three standing rules

The workbook states three rules. They are not commentary — every one of them is
enforced in `adw/guardrails.py` and fails the build when breached.

**Config, not code.** Vertical and country differences resolve to configuration;
fourteen engines carry all 815 units. There is no per-agent code anywhere in this
repository. Adding an agent means adding a workbook row and re-running the build.

**Customer-owned channels.** Growth and social output publishes only from the
customer's connected accounts. Any unit that sends or publishes must declare a
`connected_accounts` grant; the audit rejects it otherwise.

**Probabilistic components flag, collect and draft — never clear, diagnose, advise
or approve.** A plan step that performs a prohibited act without a preceding
blocking human gate is a build error, not a code-review note.

A fourth rule comes from the legend: a **◆ diamond** marks a safety-critical
protocol — *recognition and routing only*. Those 37 units run their interlock
first, terminate in a `stop` step, carry an absolute human gate, and are rejected
if their text contains resolution language ("clear the hazard", "make safe"). For
these, escalation **is** the product.

---

## Quick start

```bash
pip install -e ".[dev]"

python -m adw catalogue                 # totals and standing rules
python -m adw engines                   # the 14 engines and their load
python -m adw list --vertical V7        # units for clinical & health
python -m adw show A1                   # one unit, in full
python -m adw audit                     # standing-rule audit over all 815
python -m adw roster --vertical V7 --country UK --name "Northgate Dental"
python -m adw search "missed call"

make build                              # regenerate everything from the workbook
make test                               # 100+ tests including the full audit
```

---

## Layout

| Path | What it is |
| --- | --- |
| `catalogue/` | The workbook plus its normalised form: units, verticals, archetypes, mechanism families, departments, edge-case domains, localization |
| `engines/` | The 14 mechanism-family engines and the `Engine` contract in `base.py` |
| `agents/core/<department>/` | 68 core workers |
| `agents/verticals/<vertical>/` | 355 industry specialists |
| `agents/playbooks/universal/<domain>/` | 92 universal edge-case playbooks |
| `agents/playbooks/vertical/<vertical>/` | 300 vertical edge-case playbooks |
| `packs/countries/` | 29 country packs — the only place a market-specific fact lives |
| `adw/` | Runtime: models, registry, guardrails, router, CLI |
| `tools/` | The build scripts. Everything generated is regenerable and checked in CI |
| `tests/` | Catalogue, spec, engine, guardrail, router and country-pack suites |

---

## How a unit is built

A unit spec is never written by hand. `tools/generate_agents.py` hands each catalogue
record to the engine its mechanism family names, and the engine **composes** it:

1. **Profile selection.** Each engine offers presets — MF2 has eleven, from
   `claim_adjudication` to `change_control` — matched against the unit's worker
   title, system agent name, trigger, function and expected output. This is how one
   engine covers eighty differently-named workers without a line of per-unit code.
2. **Plan.** The family's step skeleton plus the profile's extra steps, in
   `observe → gather → assess → decide → draft/act → notify → record` order.
3. **Artefacts.** The workbook's *Expected output* is the acceptance test, so each
   of its clauses becomes a first-class artefact with a stable key and the evidence
   a reviewer would look at.
4. **Guardrails and gates.** The four standing guardrails always; pricing,
   regulated-surface and safety guardrails when the unit's subject matter earns them.
   Every *What stays human* cell becomes a typed `HumanGate` with a severity and an
   escalation target.
5. **Config keys.** Everything market- or vertical-dependent is declared, never
   inlined — which is what makes the config-not-code rule checkable.

Then `adw/guardrails.py` audits the composed unit **before** it reaches disk. A
breach fails the generator.

## How a roster is resolved

`adw/router.py` turns a business profile into the units it actually runs, and the
order to switch them on:

- **Selection** = 68 core workers + that vertical's specialists and playbooks + 92
  universal playbooks.
- **Waves** — the workbook's Now / Next / Later / Skip — computed from the archetype's
  anchor agents, the revenue-critical flag and the safety-critical flag. Safety
  protocols are always *Now*: if the situation can happen on day one, the protocol
  exists on day one.
- **Archetype J** (retail, walk-in, no client record) is the workbook's own weak fit,
  so its recall and reactivation machinery is skipped rather than shipped inert.
- **`missing_config()`** lists what the country pack cannot answer — the price book,
  opening hours, who takes an escalation at 2am. Onboarding is the work of emptying
  that list.

`A1` (Receptionist) and `A12` (Handover Clerk) are always on: the catalogue marks A1
"never disabled", and A12 is the escape hatch that makes every other agent safe to run.

---

## The 14 engines

| MF | Family | Units | Status |
| --- | --- | ---: | --- |
| MF1 | Conversational intake & triage | 98 | existing |
| MF2 | Case / matter state machine | 80 | existing |
| MF3 | Exception-queue triage | 52 | existing |
| MF4 | Clock & calendar engine | 73 | existing |
| MF5 | Sequence engine | 54 | existing |
| MF6 | Document collection & assembly | 100 | existing |
| MF7 | Watcher / surveillance | 92 | existing |
| MF8 | Reconciliation | 32 | existing |
| MF9 | Vision assessment | 12 | existing |
| MF10 | Capacity & scheduling optimization | 53 | existing |
| MF11 | Telephony / voice | 3 | **new** |
| MF12 | Publishing & platform connectors | 12 | **new** |
| MF13 | Creative generation | 13 | **new** |
| MF14 | Protocol & incident playbooks | 141 | **new** |

## The 10 archetypes

| | Archetype | Primary lever |
| --- | --- | --- |
| A | Emergency trades | Speed to lead (sub-60s) |
| B | Booked personal services | Reminders + rebooking |
| C | Regulated professions | Qualification, then progress updates |
| D | Project trades | Quote follow-up |
| E | Recurring B2B contracts | Renewal calendar |
| F | Hospitality & venues | Response speed on high-value enquiries |
| G | Clinical & health | Recall + reactivation |
| H | Education & training | Trial-to-paid + term-break retention |
| I | Property & lettings | Statutory dates + viewing speed |
| J | Retail product-led | Weak fit — availability only |

---

## Changing the catalogue

The workbook is the source of truth. Nothing under `catalogue/` (except the `.xlsx`),
`agents/` or `packs/` is edited by hand.

```bash
# 1. edit catalogue/ADW_MASTER_AGENT_CATALOGUE.xlsx
make build      # normalise -> compose -> write, with the audit gating the write
make test       # counts, completeness, standing rules, roster coverage
```

`make check` fails if anything on disk is stale, so a workbook edit that was never
rebuilt cannot land.

Changing *behaviour* means editing an engine — and that change lands across every
unit that family carries, which is the point of the config-not-code rule.
