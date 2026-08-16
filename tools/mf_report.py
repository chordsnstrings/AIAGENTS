#!/usr/bin/env python3
"""Print every catalogue unit bound to a mechanism family.

Used when writing or reviewing an engine: the engine's profiles must cover every
unit listed here, because these are the units it has to carry.

    python tools/mf_report.py MF1
    python tools/mf_report.py            # counts for all fourteen
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

CATALOGUE = Path(__file__).resolve().parent.parent / "catalogue" / "catalogue.json"


def main(argv: list[str]) -> int:
    catalogue = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    families = {m["id"]: m for m in catalogue["mechanism_families"]}
    units = catalogue["units"]

    if len(argv) < 2:
        counts = Counter(u["mechanism_family"] for u in units)
        for family_id, family in families.items():
            print(f"{family_id:<5} {counts[family_id]:>4}  {family['family']}")
        return 0

    family_id = argv[1].upper()
    family = families[family_id]
    selected = [u for u in units if u["mechanism_family"] == family_id]
    print(f"{family_id} - {family['family']}")
    print(f"  {family['what_it_does']}")
    print(f"  status: {family['status']}   units: {len(selected)}")
    print()
    for unit in selected:
        name = unit["worker"] or unit["trigger"]
        system = f" [{unit['system_agent']}]" if unit["system_agent"] else ""
        marks = "".join(
            m
            for m, on in (("*", unit["flags"]["revenue_critical"]), ("D", unit["flags"]["safety_critical"]))
            if on
        )
        where = (
            (unit.get("vertical") or {}).get("name")
            or (unit.get("department") or {}).get("name")
            or (unit.get("domain") or {}).get("name")
            or "-"
        )
        print(f"{unit['id']:<9} {marks:<2} {name}{system}")
        print(f"          where: {where}")
        print(f"          does : {unit['function']}")
        print(f"          out  : {unit['expected_output']}")
        if unit["human_gates"]:
            print(f"          human: {'; '.join(unit['human_gates'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
