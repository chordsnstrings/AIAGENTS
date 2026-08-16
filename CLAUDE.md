# Working in this repository

This repo implements the ADW MASTER AGENT CATALOGUE: **815 automation units** carried
by **14 mechanism-family engines**. Read `docs/ARCHITECTURE.md` before changing
anything structural.

## The one rule that shapes everything

> Config, not code — vertical and country differences resolve to config; 14 engines
> carry all 815 units.

**There is no per-agent code in this repository and there must never be.** If you find
yourself writing a module, class or `if unit.id == ...` branch named after a specific
agent, the design has been broken. The correct move is one of:

- add or sharpen a **profile** on the relevant engine (`engines/mfNN_*.py`), or
- add a **config key** the unit reads from a country pack or vertical overlay, or
- fix the **workbook row** and rebuild.

## What is generated vs. hand-authored

| Generated — never edit by hand | Hand-authored |
| --- | --- |
| `catalogue/*.json`, `catalogue/*.yaml` | `catalogue/ADW_MASTER_AGENT_CATALOGUE.xlsx` |
| `agents/**/*.yaml` (all 815) | `engines/*.py` |
| `packs/countries/*.yaml` | `adw/*.py` |
| `docs/CATALOGUE.md`, `docs/departments/`, `docs/verticals/`, `docs/domains/`, `docs/engines/` | `tests/*.py`, `README.md`, `docs/ARCHITECTURE.md` |

Country packs are generated from the table in `tools/build_country_packs.py` — edit
that table, not the YAML.

`make check` fails if anything generated is stale, so a hand-edit cannot land.

## Standard loop

```bash
make build      # normalise workbook -> compose through engines -> write 815 specs
make test       # counts, completeness, standing rules, roster coverage
make audit      # standing-rule audit with per-violation detail
```

Useful during engine work:

```bash
python3 tools/mf_report.py MF7              # every unit the family must carry
python3 tools/check_engine.py MF7 --verbose # which profile each unit landed on
python3 tools/generate_agents.py --only MF7 # regenerate just that family
```

## Invariants the build enforces

These are asserted in `tools/` and `tests/`. If you change one, change it deliberately
and in a diff — do not weaken a check to make a build pass.

- Exactly **815** spec files on disk: 68 / 355 / 92 / 300.
- **37** safety-critical (◆) units, **68** revenue-critical (`*`) units.
- Every unit: non-empty mission, plan, artefacts, acceptance criteria, guardrails,
  human gates, config keys, tools and KPIs. No placeholders, no stubs.
- Every unit carries all four standing guardrails.
- Every ◆ unit: interlock first, `stop` last, absolute human gate, no resolution
  language. **Recognition and routing only — escalation is the product.**
- No engine fallback profile carries more than a third of its family.
- Every declared profile is reached by at least one unit.
- Every unit is reachable through some roster.

## Style

- Match the surrounding voice: `engines/base.py` sets it. Docstrings explain *why* a
  thing is shaped the way it is; comments are sparse and never restate the code.
- British-leaning spelling in prose (`artefact`, `recognise`, `behaviour`),
  `snake_case` identifiers.
- Python 3.10+, `from __future__ import annotations`, fully type-annotated.
- Runtime dependencies: PyYAML only. `openpyxl` is build-time.
