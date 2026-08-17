#!/usr/bin/env python3
"""End-to-end proof that the catalogue is completely built.

One command, one verdict.  It answers the only question that matters about this
repository: are all 815 units actually on disk, individually, completely, and
passing every rule the build claims to enforce?

    python tools/verify_build.py
    python tools/verify_build.py --verbose

Exit code 0 means every check passed.  Anything else names what failed.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from adw.guardrails import audit, errors, warnings  # noqa: E402
from adw.models import UnitType  # noqa: E402
from adw.registry import (  # noqa: E402
    AGENTS_DIR,
    Catalogue,
    Registry,
    available_country_packs,
    load_country_pack,
)
from adw.router import coverage  # noqa: E402
from engines.base import all_engines, load_engines  # noqa: E402

EXPECTED = {
    UnitType.CORE_WORKER: 68,
    UnitType.SPECIALIST: 355,
    UnitType.PLAYBOOK_UNIVERSAL: 92,
    UnitType.PLAYBOOK_VERTICAL: 300,
}
EXPECTED_TOTAL = 815
EXPECTED_SAFETY_CRITICAL = 37
EXPECTED_REVENUE_CRITICAL = 68

PLACEHOLDER_MARKERS = ("TODO", "TBD", "FIXME", "PLACEHOLDER", "lorem ipsum", "<insert")

#: Required fields. A unit missing any of these is a stub, whatever else it has.
REQUIRED_FIELDS = (
    "mission", "function", "expected_output", "acceptance", "artifacts", "plan",
    "guardrails", "human_gates", "config_keys", "capabilities", "tools", "kpis", "inputs",
)


class Report:
    def __init__(self, verbose: bool) -> None:
        self.verbose = verbose
        self.failures: list[str] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        status = "PASS" if ok else "FAIL"
        line = f"  [{status}] {name}"
        if detail and (self.verbose or not ok):
            line += f"\n         {detail}"
        print(line)
        if not ok:
            self.failures.append(name)

    def section(self, title: str) -> None:
        print(f"\n{title}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    report = Report(args.verbose)
    print("=" * 72)
    print("ADW MASTER AGENT CATALOGUE - BUILD VERIFICATION")
    print("=" * 72)

    load_engines()
    catalogue = Catalogue.load()
    registry = Registry.load()

    # -- 1. completeness ---------------------------------------------------
    report.section("1. Completeness - every unit built, individually")
    files = list(AGENTS_DIR.rglob("*.yaml"))
    report.check(
        f"exactly {EXPECTED_TOTAL} spec files on disk",
        len(files) == EXPECTED_TOTAL,
        f"found {len(files)}",
    )
    report.check(
        f"registry loads {EXPECTED_TOTAL} units",
        len(registry) == EXPECTED_TOTAL,
        f"loaded {len(registry)}",
    )
    counts = Counter(u.type for u in registry)
    for unit_type, expected in EXPECTED.items():
        report.check(
            f"{unit_type.value:<20} {expected}",
            counts[unit_type] == expected,
            f"found {counts[unit_type]}",
        )
    catalogue_ids = {u["id"] for u in catalogue.records}
    spec_ids = {u.id for u in registry}
    report.check(
        "every catalogue row has a spec, and vice versa",
        catalogue_ids == spec_ids,
        f"missing: {sorted(catalogue_ids - spec_ids)[:5]} extra: {sorted(spec_ids - catalogue_ids)[:5]}",
    )

    # -- 2. no placeholders ------------------------------------------------
    report.section("2. No placeholders, no stubs")
    offenders = [
        f"{p.relative_to(REPO_ROOT)}: {m}"
        for p in files
        for m in PLACEHOLDER_MARKERS
        if m.lower() in p.read_text(encoding="utf-8").lower()
    ]
    report.check("no placeholder markers in any spec", not offenders, "; ".join(offenders[:5]))

    incomplete = []
    for unit in registry:
        missing = [f for f in REQUIRED_FIELDS if not getattr(unit, f)]
        if missing:
            incomplete.append(f"{unit.id}: {missing}")
    report.check("every unit populates every required field", not incomplete, "; ".join(incomplete[:5]))

    thin = [u.id for u in registry if len(u.mission.split()) < 120]
    report.check("every mission is substantive (120+ words)", not thin, f"{len(thin)} thin: {thin[:5]}")

    # The mission is the system prompt at runtime; the rest of the spec is not
    # in front of the model. A contract stated only in YAML is not a contract.
    unnamed = [
        u.id
        for u in registry
        if any(a.key not in u.mission or a.name not in u.mission for a in u.artifacts)
    ]
    report.check(
        "every mission names all its artefacts by key and name",
        not unnamed,
        f"{len(unnamed)} missions incomplete: {unnamed[:5]}",
    )
    unwarned = [
        u.id
        for u in registry
        if "from your own knowledge" not in u.mission.lower()
        or "a gate, not a gap" not in u.mission.lower()
    ]
    report.check(
        "every mission carries the anti-fabrication rule",
        not unwarned,
        f"{len(unwarned)} missions missing it: {unwarned[:5]}",
    )

    missions = Counter(u.mission for u in registry)
    duplicated = [m for m, n in missions.items() if n > 1]
    report.check(
        "no two units share a mission verbatim",
        not duplicated,
        f"{len(duplicated)} duplicated mission(s)",
    )

    # -- 3. engines carry everything ---------------------------------------
    report.section("3. Config, not code - 14 engines carry all 815")
    engines = all_engines()
    report.check("fourteen engines registered", len(engines) == 14, f"found {len(engines)}")
    unbound = [f for f in engines if not registry.by_mechanism_family.get(f)]
    report.check("every engine carries at least one unit", not unbound, str(unbound))

    overloaded = []
    for family_id, engine in engines.items():
        units = registry.by_mechanism_family[family_id]
        fallback = engine.profiles[-1].name
        share = sum(1 for u in units if u.engine_profile == fallback) / len(units)
        if share > 0.34:
            overloaded.append(f"{family_id} {share:.0%} on {fallback!r}")
    report.check("no engine leans on its fallback profile", not overloaded, "; ".join(overloaded))

    unused = []
    for family_id, engine in engines.items():
        used = {u.engine_profile for u in registry.by_mechanism_family[family_id]}
        unused += [f"{family_id}/{p.name}" for p in engine.profiles if p.name not in used]
    report.check("every declared profile is reached by a unit", not unused, "; ".join(unused[:8]))

    profiles = {f"{u.mechanism_family}:{u.engine_profile}" for u in registry}
    print(f"         {len(profiles)} distinct engine profiles carry {len(registry)} units")

    # -- 4. standing rules -------------------------------------------------
    report.section("4. Standing rules, enforced")
    violations = audit(registry)
    blocking = errors(violations)
    advisory = warnings(violations)
    report.check(
        "standing-rule audit: zero errors",
        not blocking,
        "\n         ".join(str(v) for v in blocking[:8]),
    )
    print(f"         {len(advisory)} advisory warning(s)")

    required_guardrails = {"SR-PROBABILISTIC", "SR-OWNED-CHANNELS", "SR-CONFIG-NOT-CODE", "SR-AUDIT"}
    missing = [u.id for u in registry if not required_guardrails <= {g.id for g in u.guardrails}]
    report.check("every unit carries all four standing guardrails", not missing, str(missing[:5]))

    ungated = [u.id for u in registry if not u.human_gates]
    report.check("every unit declares a human gate", not ungated, str(ungated[:5]))

    # -- 5. safety-critical protocols --------------------------------------
    report.section("5. Safety-critical protocols - recognition and routing only")
    diamonds = registry.safety_critical
    report.check(
        f"{EXPECTED_SAFETY_CRITICAL} safety-critical units",
        len(diamonds) == EXPECTED_SAFETY_CRITICAL,
        f"found {len(diamonds)}",
    )
    bad = [u.id for u in diamonds if not (u.plan and u.plan[0].interlock)]
    report.check("interlock runs first in every one", not bad, str(bad))
    bad = [u.id for u in diamonds if not (u.plan and u.plan[-1].kind.value == "stop")]
    report.check("every one terminates in a stop step", not bad, str(bad))
    bad = [u.id for u in diamonds if not any(g.severity.value == "absolute" for g in u.human_gates)]
    report.check("every one carries an absolute human gate", not bad, str(bad))

    report.check(
        f"{EXPECTED_REVENUE_CRITICAL} revenue-critical units",
        len(registry.revenue_critical) == EXPECTED_REVENUE_CRITICAL,
        f"found {len(registry.revenue_critical)}",
    )

    # -- 6. reachability and localisation ----------------------------------
    report.section("6. Reachability and localisation")
    reach = coverage(registry, catalogue)
    report.check(
        "every unit is reachable through some roster",
        not reach["unreachable"],
        str(reach["unreachable"][:5]),
    )
    packs = available_country_packs()
    report.check("country packs present", len(packs) >= 20, f"{len(packs)} packs")

    # Declaring a config key is a promise that a value exists to be read. Where
    # it does not, the unit reaches runtime, finds nothing, and fills the hole
    # from the model's own knowledge -- non-deterministically.
    declared = {k.key for u in registry for k in u.config_keys if k.resolved_by == "country_pack"}
    required = {
        k.key for u in registry for k in u.config_keys
        if k.resolved_by == "country_pack" and k.required
    }
    answered = [set(load_country_pack(c).settings) for c in packs]
    everywhere = set.intersection(*answered) if answered else set()
    anywhere = set.union(*answered) if answered else set()
    report.check(
        "every country_pack key resolves in at least one pack",
        declared <= anywhere,
        f"unresolved: {sorted(declared - anywhere)[:6]}",
    )
    report.check(
        "every required country_pack key resolves in every pack",
        required <= everywhere,
        f"missing somewhere: {sorted(required - everywhere)[:6]}",
    )
    missing_emergency = [c for c in packs if not load_country_pack(c).get("emergency_routing")]
    report.check(
        "every pack states its own emergency routing",
        not missing_emergency,
        str(missing_emergency),
    )
    print(f"         {len(declared)} country_pack keys declared, {len(everywhere)} answered by every pack")

    # -- 7. reproducibility ------------------------------------------------
    report.section("7. Reproducibility - nothing hand-edited")
    for name, command in (
        ("catalogue is in step with the workbook", ["python3", "tools/build_catalogue.py", "--check"]),
        ("specs are in step with catalogue + engines", ["python3", "tools/generate_agents.py", "--check"]),
    ):
        result = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True)
        report.check(name, result.returncode == 0, (result.stdout + result.stderr).strip()[:400])

    # -- verdict -----------------------------------------------------------
    print()
    print("=" * 72)
    if report.failures:
        print(f"VERIFICATION FAILED - {len(report.failures)} check(s) did not pass:")
        for failure in report.failures:
            print(f"  - {failure}")
        print("=" * 72)
        return 1
    print(f"VERIFICATION PASSED - all {EXPECTED_TOTAL} units built and validated")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
