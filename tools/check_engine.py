#!/usr/bin/env python3
"""Compose every unit of a mechanism family and report how well its engine fits.

An engine's job is to carry its units without any of them falling through to a
generic default, so this reports the profile each unit lands on and fails when
too many land on the fallback.

    python tools/check_engine.py MF1
    python tools/check_engine.py            # every family
    python tools/check_engine.py MF1 --verbose
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from engines.base import all_engines, get_engine  # noqa: E402

CATALOGUE = REPO_ROOT / "catalogue" / "catalogue.json"

#: A fallback profile carrying more than this share of a family's units means the
#: family's real shapes have not been modelled.
MAX_FALLBACK_SHARE = 0.34


def check(family_id: str, units: list[dict], verbose: bool) -> bool:
    engine = get_engine(family_id)
    fallback = engine.profiles[-1].name
    counts: Counter[str] = Counter()
    problems: list[str] = []

    for unit in units:
        try:
            composed = engine.compose(unit)
        except Exception as error:  # pragma: no cover - surfaced to the caller
            problems.append(f"{unit['id']}: compose failed: {error!r}")
            continue
        counts[composed.engine_profile] += 1

        if not composed.mission.strip():
            problems.append(f"{unit['id']}: empty mission")
        if not composed.plan:
            problems.append(f"{unit['id']}: empty plan")
        if not composed.artifacts:
            problems.append(f"{unit['id']}: no artefacts")
        if not composed.acceptance:
            problems.append(f"{unit['id']}: no acceptance criteria")
        if composed.is_safety_critical:
            if not any(s.interlock for s in composed.plan):
                problems.append(f"{unit['id']}: safety-critical without an interlock step")
            if composed.plan[-1].kind.value != "stop":
                problems.append(f"{unit['id']}: safety-critical plan does not end in stop")
        if verbose:
            print(f"  {unit['id']:<9} -> {composed.engine_profile}")

    total = sum(counts.values())
    share = counts[fallback] / total if total else 0.0
    status = "ok"
    if share > MAX_FALLBACK_SHARE:
        problems.append(
            f"fallback profile {fallback!r} carries {counts[fallback]}/{total} units "
            f"({share:.0%} > {MAX_FALLBACK_SHARE:.0%})"
        )
    if problems:
        status = "FAIL"

    print(f"{family_id:<5} {engine.family:<42} units={total:<4} profiles={len(counts):<3} {status}")
    for name, count in counts.most_common():
        marker = "  (fallback)" if name == fallback else ""
        print(f"        {count:>4}  {name}{marker}")
    for problem in problems:
        print(f"        !! {problem}")
    return not problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family", nargs="?", help="e.g. MF1; omit for all")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    catalogue = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    by_family: dict[str, list[dict]] = {}
    for unit in catalogue["units"]:
        by_family.setdefault(unit["mechanism_family"], []).append(unit)

    families = [args.family.upper()] if args.family else list(all_engines())
    ok = True
    for family_id in families:
        ok &= check(family_id, by_family.get(family_id, []), args.verbose)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
