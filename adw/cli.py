"""Command line for the ADW catalogue.

    python -m adw catalogue
    python -m adw list --type specialist --vertical V7
    python -m adw show A1
    python -m adw engines
    python -m adw roster --vertical V7 --country UK --name "Northgate Dental"
    python -m adw audit
    python -m adw search "missed call"
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from adw.guardrails import Severity, audit, errors, warnings
from adw.models import BusinessProfile, Unit, UnitType
from adw.registry import (
    Catalogue,
    Registry,
    available_country_packs,
    load_country_pack,
)
from adw.router import coverage, missing_config, resolve_roster

MARK = {"revenue": "*", "safety": "D"}


def _marks(unit: Unit) -> str:
    return "".join(
        [
            MARK["revenue"] if unit.is_revenue_critical else "",
            MARK["safety"] if unit.is_safety_critical else "",
        ]
    ).ljust(2)


def _where(unit: Unit) -> str:
    return (
        unit.scope.vertical_name
        or unit.scope.department_name
        or unit.scope.domain_name
        or "-"
    )


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #


def cmd_catalogue(args: argparse.Namespace) -> int:
    catalogue = Catalogue.load()
    totals = catalogue.totals
    print("ADW MASTER AGENT CATALOGUE")
    print(f"  source: {catalogue.data['source']}  version {catalogue.data['version']}")
    print()
    for key, value in totals.items():
        print(f"  {key:<22} {value}")
    print()
    print("STANDING RULES")
    for rule in catalogue.standing_rules:
        print(f"  - {rule}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    registry = Registry.load()
    units: Sequence[Unit] = list(registry)

    if args.type:
        units = [u for u in units if u.type is UnitType(args.type)]
    if args.vertical:
        units = [u for u in units if u.scope.vertical_id == args.vertical.upper()]
    if args.department:
        units = [
            u
            for u in units
            if (u.scope.department_id or "").upper() == args.department.upper()
            or (u.scope.department_name or "").lower() == args.department.lower()
        ]
    if args.mf:
        units = [u for u in units if u.mechanism_family == args.mf.upper()]
    if args.archetype:
        units = [u for u in units if args.archetype.upper() in u.scope.archetypes]
    if args.safety_critical:
        units = [u for u in units if u.is_safety_critical]
    if args.revenue_critical:
        units = [u for u in units if u.is_revenue_critical]

    units = sorted(units, key=lambda u: u.id)
    if args.json:
        print(json.dumps([u.to_dict() for u in units], indent=2, ensure_ascii=False))
        return 0

    for unit in units:
        print(
            f"{unit.id:<9} {_marks(unit)} {unit.mechanism_family:<5} "
            f"{unit.display_name[:52]:<52} {_where(unit)}"
        )
    print(f"\n{len(units)} unit(s)")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    registry = Registry.load()
    unit = registry.get(args.unit_id.upper())

    if args.json:
        print(json.dumps(unit.to_dict(), indent=2, ensure_ascii=False))
        return 0

    print(f"{unit.id} - {unit.display_name}")
    print(f"  type      : {unit.type.value}")
    print(f"  where     : {_where(unit)}")
    print(f"  engine    : {unit.mechanism_family} / profile {unit.engine_profile}")
    print(f"  flags     : revenue-critical={unit.is_revenue_critical} "
          f"safety-critical={unit.is_safety_critical}")
    print(f"  spec      : {unit.path}")
    print()
    print("FUNCTION")
    print(f"  {unit.function}")
    print()
    print("MISSION")
    for line in unit.mission.splitlines():
        print(f"  {line}")
    print()
    print("EXPECTED OUTPUT (the acceptance test)")
    print(f"  {unit.expected_output}")
    for criterion in unit.acceptance:
        print(f"    [{criterion.id}] {criterion.criterion}")
        print(f"        evidence: {criterion.evidence}")
    print()
    print("PLAN")
    for plan_step in unit.plan:
        lock = "  [INTERLOCK]" if plan_step.interlock else ""
        print(f"  {plan_step.kind.value:<8} {plan_step.name}{lock}")
        print(f"           {plan_step.description}")
    print()
    print("ARTEFACTS")
    for artifact in unit.artifacts:
        print(f"  {artifact.key:<50} {artifact.format}")
    print()
    print("HUMAN GATES")
    for gate in unit.human_gates:
        print(f"  [{gate.severity.value}] {gate.decision} -> {gate.escalate_to.value}")
        if gate.note:
            print(f"        {gate.note}")
    print()
    print("GUARDRAILS")
    for guardrail in unit.guardrails:
        print(f"  [{guardrail.id}] {guardrail.rule}")
        print(f"        check: {guardrail.check}")
    print()
    print("CONFIG KEYS")
    for key in unit.config_keys:
        flag = " (required)" if key.required else ""
        print(f"  {key.key:<26} <- {key.resolved_by}{flag}")
    print()
    print(f"KPIS     : {', '.join(unit.kpis) or '-'}")
    print(f"TOOLS    : {', '.join(unit.tools) or '-'}")
    print(f"CHANNELS : {', '.join(unit.channels) or '-'}")
    return 0


def cmd_engines(args: argparse.Namespace) -> int:
    from engines.base import all_engines

    registry = Registry.load()
    print(f"{'MF':<6}{'family':<44}{'units':>6}  {'profiles':>8}  status")
    for family_id, engine in all_engines().items():
        units = registry.by_mechanism_family.get(family_id, [])
        profiles = {u.engine_profile for u in units}
        print(
            f"{family_id:<6}{engine.family:<44}{len(units):>6}  {len(profiles):>8}  "
            f"{engine.what_it_does[:40]}"
        )
    print(f"\n{len(registry)} units carried by {len(all_engines())} engines")
    return 0


def cmd_roster(args: argparse.Namespace) -> int:
    catalogue = Catalogue.load()
    registry = Registry.load()
    pack = load_country_pack(args.country)
    profile = BusinessProfile(
        name=args.name,
        vertical_id=args.vertical.upper(),
        country=pack.code,
        archetypes=tuple(a.upper() for a in (args.archetype or [])),
        enabled_units=tuple(u.upper() for u in (args.enable or [])),
        disabled_units=tuple(u.upper() for u in (args.disable or [])),
    )
    roster = resolve_roster(profile, catalogue, registry, pack)

    if args.json:
        print(
            json.dumps(
                {
                    "business": roster.business.name,
                    "vertical": roster.business.vertical_id,
                    "country": pack.code,
                    "archetypes": list(roster.archetypes),
                    "anchors": list(roster.anchors),
                    "summary": roster.summary(),
                    "entries": [
                        {"id": e.id, "name": e.unit.display_name, "wave": e.wave.value, "reason": e.reason}
                        for e in roster.entries
                    ],
                    "missing_config": missing_config(roster),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    print(roster.explain())
    outstanding = missing_config(roster)
    if outstanding:
        print(f"ONBOARDING - {len(outstanding)} setting(s) the owner must supply")
        for key, unit_ids in outstanding.items():
            print(f"  {key:<26} needed by {len(unit_ids)} unit(s)")
    print()
    print("SUMMARY", roster.summary())
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    registry = Registry.load()
    catalogue = Catalogue.load()
    violations = audit(registry)
    blocking = errors(violations)
    advisory = warnings(violations)

    if args.severity == "error":
        shown = blocking
    elif args.severity == "warning":
        shown = advisory
    else:
        shown = violations

    for violation in shown:
        print(violation)

    reach = coverage(registry, catalogue)
    print()
    print(f"units audited      : {len(registry)}")
    print(f"errors             : {len(blocking)}")
    print(f"warnings           : {len(advisory)}")
    print(f"reachable by roster: {reach['reachable']}/{reach['total']}")
    if reach["unreachable"]:
        print(f"UNREACHABLE        : {reach['unreachable']}")
    return 1 if blocking else 0


def cmd_search(args: argparse.Namespace) -> int:
    registry = Registry.load()
    hits = registry.search(args.term)
    for unit in sorted(hits, key=lambda u: u.id):
        print(f"{unit.id:<9} {_marks(unit)} {unit.display_name[:52]:<52} {_where(unit)}")
    print(f"\n{len(hits)} match(es) for {args.term!r}")
    return 0


def cmd_verticals(args: argparse.Namespace) -> int:
    catalogue = Catalogue.load()
    for vertical in catalogue.verticals.values():
        print(
            f"{vertical.id:<5} {vertical.name:<40} "
            f"[{','.join(a.split('-')[-1] for a in vertical.archetypes)}] "
            f"{vertical.segment:<20} "
            f"{len(vertical.specialist_ids)} specialists, "
            f"{len(vertical.playbook_ids)} playbooks"
        )
    print(f"\n{len(catalogue.verticals)} verticals")
    return 0


def cmd_archetypes(args: argparse.Namespace) -> int:
    catalogue = Catalogue.load()
    for archetype in catalogue.archetypes.values():
        print(f"{archetype.id}  {archetype.name}")
        print(f"       recognise by : {archetype.recognise_by}")
        print(f"       primary lever: {archetype.primary_lever}")
        print(f"       anchors      : {', '.join(archetype.anchor_agents)}")
    return 0


def cmd_packs(args: argparse.Namespace) -> int:
    codes = available_country_packs()
    for code in codes:
        pack = load_country_pack(code)
        print(f"{pack.code:<4} {pack.name:<22} {'/'.join(pack.languages):<28} "
              f"{'/'.join(pack.messaging_channels[:2])}")
    print(f"\n{len(codes)} country packs")
    return 0


# --------------------------------------------------------------------------- #
# parser
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="adw", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("catalogue", help="totals and standing rules").set_defaults(func=cmd_catalogue)

    p_list = sub.add_parser("list", help="list units")
    p_list.add_argument("--type", choices=[t.value for t in UnitType])
    p_list.add_argument("--vertical", help="e.g. V7")
    p_list.add_argument("--department", help="e.g. DEPT-01 or 'Front Desk'")
    p_list.add_argument("--mf", help="e.g. MF14")
    p_list.add_argument("--archetype", help="e.g. ARC-A")
    p_list.add_argument("--safety-critical", action="store_true")
    p_list.add_argument("--revenue-critical", action="store_true")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="show one unit in full")
    p_show.add_argument("unit_id")
    p_show.add_argument("--json", action="store_true")
    p_show.set_defaults(func=cmd_show)

    sub.add_parser("engines", help="the fourteen engines and their load").set_defaults(func=cmd_engines)

    p_roster = sub.add_parser("roster", help="resolve a roster for one business")
    p_roster.add_argument("--vertical", required=True, help="e.g. V7")
    p_roster.add_argument("--country", default="US", help="country pack code, e.g. UK")
    p_roster.add_argument("--name", default="Example Business")
    p_roster.add_argument("--archetype", action="append", help="override the vertical's archetype")
    p_roster.add_argument("--enable", action="append", help="force a unit into wave now")
    p_roster.add_argument("--disable", action="append", help="force a unit to skip")
    p_roster.add_argument("--json", action="store_true")
    p_roster.set_defaults(func=cmd_roster)

    p_audit = sub.add_parser("audit", help="run the standing-rule audit")
    p_audit.add_argument("--severity", choices=["all", "error", "warning"], default="all")
    p_audit.set_defaults(func=cmd_audit)

    p_search = sub.add_parser("search", help="substring search across units")
    p_search.add_argument("term")
    p_search.set_defaults(func=cmd_search)

    sub.add_parser("verticals", help="the sixty vertical clusters").set_defaults(func=cmd_verticals)
    sub.add_parser("archetypes", help="the ten funnel archetypes").set_defaults(func=cmd_archetypes)
    sub.add_parser("packs", help="available country packs").set_defaults(func=cmd_packs)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (KeyError, FileNotFoundError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
