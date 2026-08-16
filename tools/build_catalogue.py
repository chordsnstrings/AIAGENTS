#!/usr/bin/env python3
"""Normalise the ADW master workbook into the repository's source-of-truth catalogue.

The workbook (``catalogue/ADW_MASTER_AGENT_CATALOGUE.xlsx``) is the human-editable
artefact.  Everything downstream -- the 815 unit specs, the engine bindings, the
router tables -- is generated from the normalised catalogue this script emits, so
re-running it after a workbook edit is the only supported way to change the
catalogue.

Outputs (all under ``catalogue/``):

    catalogue.json          every unit, fully joined and de-duplicated
    units.yaml              the same units, YAML, for review in diffs
    departments.yaml        the 10 universal-core departments
    verticals.yaml          the 60 vertical clusters
    archetypes.yaml         the 10 funnel archetypes
    mechanism_families.yaml the 14 engines
    localization.yaml       the country-pack config fields
    edge_case_domains.yaml  the 9 universal edge-case domains

Usage:
    python tools/build_catalogue.py [--workbook PATH] [--out DIR] [--check]

``--check`` regenerates into a temporary directory and fails if the committed
catalogue differs, which is what CI runs.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
import unicodedata
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Any, Iterable

try:
    import openpyxl
except ImportError:  # pragma: no cover - dependency guard
    sys.exit("openpyxl is required: pip install openpyxl")

try:
    import yaml
except ImportError:  # pragma: no cover - dependency guard
    sys.exit("PyYAML is required: pip install pyyaml")

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKBOOK = REPO_ROOT / "catalogue" / "ADW_MASTER_AGENT_CATALOGUE.xlsx"
DEFAULT_OUT = REPO_ROOT / "catalogue"

# Sheet names as they appear in the workbook.
SHEET_MASTER = "Master (All 815)"
SHEET_CORE = "Universal Core"
SHEET_VERTICALS = "Verticals"
SHEET_EDGE_UNIVERSAL = "Edge Cases (Universal)"
SHEET_EDGE_VERTICAL = "Edge Cases (Vertical)"
SHEET_ARCHETYPES = "Archetypes"
SHEET_MECHANISMS = "Mechanism Families"
SHEET_LOCALIZATION = "Localization"

# Flag glyphs used in the workbook.
FLAG_REVENUE_CRITICAL = "*"
FLAG_SAFETY_CRITICAL = "◆"  # diamond

UNIT_TYPES = {
    "Core worker": "core_worker",
    "Specialist": "specialist",
    "Playbook (universal)": "playbook_universal",
    "Playbook (vertical)": "playbook_vertical",
}

EXPECTED_COUNTS = {
    "core_worker": 68,
    "specialist": 355,
    "playbook_universal": 92,
    "playbook_vertical": 300,
}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def slugify(value: str, max_len: int = 60) -> str:
    """Lowercase ASCII slug, safe as a file name component."""
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", " ", value)
    value = re.sub(r"[\s_-]+", "-", value).strip("-").lower()
    return value[:max_len].rstrip("-") or "unnamed"


def clean(value: Any) -> str:
    """Normalise a workbook cell into a trimmed string with tidy punctuation."""
    if value is None:
        return ""
    text = str(value).strip()
    # The workbook uses a hyphen where an em dash is meant; normalise the
    # unicode zoo so downstream string matching is predictable.
    text = text.replace("–", "-").replace("—", "-")
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def read_sheet(workbook, sheet_name: str) -> list[dict[str, str]]:
    """Read a sheet into dicts, locating the header row and skipping banners."""
    sheet = workbook[sheet_name]
    rows = [[clean(cell) for cell in row] for row in sheet.iter_rows(values_only=True)]
    header_index = next(
        (i for i, row in enumerate(rows) if sum(1 for c in row if c) >= 2), None
    )
    if header_index is None:
        raise ValueError(f"no header row found in sheet {sheet_name!r}")
    header = rows[header_index]
    records = []
    for row in rows[header_index + 1 :]:
        if not any(row):
            continue
        records.append({h: v for h, v in zip(header, row) if h})
    return records


def forward_fill(records: list[dict[str, str]], columns: Iterable[str]) -> None:
    """Fill merged-cell gaps down a column, in place."""
    carried: dict[str, str] = {}
    for record in records:
        for column in columns:
            value = record.get(column, "")
            if value:
                carried[column] = value
            else:
                record[column] = carried.get(column, "")


def split_list(value: str) -> list[str]:
    """Split a workbook cell holding a comma/slash separated list."""
    if not value:
        return []
    parts = re.split(r"\s*[,;/]\s*", value)
    return [p.strip() for p in parts if p.strip()]


def parse_expected_output(value: str) -> list[str]:
    """Split an Expected output cell into individual acceptance criteria.

    The workbook writes acceptance tests as one sentence with clauses separated
    by semicolons, and occasionally by a dash-introduced qualifier.  Each clause
    is independently checkable, so each becomes its own criterion.
    """
    if not value:
        return []
    text = value.rstrip(".")
    chunks: list[str] = []
    for semi in text.split(";"):
        semi = semi.strip()
        if not semi:
            continue
        # A " - " qualifier at the end restates the acceptance bar; keep it as
        # its own criterion rather than losing it inside a longer clause.
        dash_parts = re.split(r"\s+-\s+", semi)
        for part in dash_parts:
            part = part.strip(" -")
            if part:
                chunks.append(part[0].upper() + part[1:])
    return chunks


def parse_human_gates(value: str) -> list[str]:
    """Normalise the 'What stays human' cell into an explicit gate list."""
    text = clean(value)
    if not text:
        return []
    lowered = text.lower()
    if lowered in {"none", "n/a", "-"}:
        return []
    if lowered.startswith("nothing"):
        # "Nothing - protocol is absolute": no discretion exists, the protocol
        # itself is the gate.  Preserved verbatim so the guardrail layer can
        # recognise it.
        return [text]
    return [p.strip() for p in re.split(r"\s*;\s*", text) if p.strip()]


def parse_archetypes(value: str) -> list[str]:
    """'D/E' -> ['ARC-D', 'ARC-E']."""
    return [f"ARC-{p.strip().upper()}" for p in value.split("/") if p.strip()]


def yaml_dump(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            data,
            handle,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
            width=100,
        )


# --------------------------------------------------------------------------- #
# reference-table extraction
# --------------------------------------------------------------------------- #
def build_archetypes(workbook) -> list[dict[str, Any]]:
    out = []
    for row in read_sheet(workbook, SHEET_ARCHETYPES):
        code = row["Archetype"]
        out.append(
            {
                "id": code,
                "letter": code.split("-")[-1],
                "name": row["Name"],
                "recognise_by": row["Recognise it by"],
                "primary_lever": row["Primary lever"],
                "anchor_agents": split_list(row["Anchor agents"]),
                "slug": slugify(row["Name"]),
            }
        )
    return out


def build_mechanism_families(workbook) -> list[dict[str, Any]]:
    out = []
    for row in read_sheet(workbook, SHEET_MECHANISMS):
        code = row["Code"]
        number = int(code.replace("MF", ""))
        out.append(
            {
                "id": code,
                "number": number,
                "family": row["Family"],
                "what_it_does": row["What it does"],
                "status": row["Status"],
                "slug": slugify(row["Family"]),
                "module": f"engines.mf{number:02d}_{slugify(row['Family']).replace('-', '_')}",
            }
        )
    return out


def build_localization(workbook) -> dict[str, Any]:
    config_fields: list[dict[str, Any]] = []
    globalized: list[dict[str, Any]] = []
    in_globalized = False
    for row in read_sheet(workbook, SHEET_LOCALIZATION):
        field = row["Config field"]
        value = row["Global instances"]
        if field == "GLOBALIZED AGENTS":
            in_globalized = True
            continue
        if in_globalized:
            # "was X - Y" documents the rename from a UAE-anchored name.
            former, _, note = value.partition(" - ")
            globalized.append(
                {
                    "system_agent": field,
                    "formerly": former.replace("was ", "").strip(),
                    "resolution": note.strip() or former.strip(),
                    "key": slugify(field).replace("-", "_"),
                }
            )
        else:
            config_fields.append(
                {
                    "field": field,
                    "key": slugify(field).replace("-", "_"),
                    "global_instances": [
                        p.strip() for p in value.split(" - ") if p.strip()
                    ],
                }
            )
    return {"config_fields": config_fields, "globalized_agents": globalized}


def build_departments(core_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    order: "OrderedDict[str, list[str]]" = OrderedDict()
    for row in core_rows:
        order.setdefault(row["Department"], []).append(row["ID"])
    out = []
    for index, (name, ids) in enumerate(order.items(), start=1):
        out.append(
            {
                "id": f"DEPT-{index:02d}",
                "name": name,
                "slug": slugify(name),
                "prefix": ids[0][0],
                "unit_ids": ids,
                "headcount": len(ids),
            }
        )
    return out


def build_verticals(
    vertical_rows: list[dict[str, str]], edge_rows: list[dict[str, str]]
) -> list[dict[str, Any]]:
    order: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
    for row in vertical_rows:
        number = int(row["V#"])
        entry = order.setdefault(
            number,
            {
                "id": f"V{number}",
                "number": number,
                "name": row["Vertical cluster"],
                "slug": f"v{number:02d}-{slugify(row['Vertical cluster'], 40)}",
                "segment": row["Segment"],
                "examples": split_list(row["Examples"]),
                "archetypes": parse_archetypes(row["Arch."]),
                "specialist_ids": [],
                "playbook_ids": [],
            },
        )
        entry["specialist_ids"].append(f"V{number}-S{len(entry['specialist_ids']) + 1}")
    counters: Counter[int] = Counter()
    for row in edge_rows:
        number = int(row["V#"])
        counters[number] += 1
        order[number]["playbook_ids"].append(f"V{number}-E{counters[number]}")
    return list(order.values())


def build_edge_case_domains(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    order: "OrderedDict[str, list[str]]" = OrderedDict()
    for row in rows:
        order.setdefault(row["Domain"], []).append(row["Code"])
    return [
        {
            "id": f"DOM-{index:02d}",
            "name": name,
            "slug": slugify(name),
            "prefix": codes[0].split("-")[0],
            "unit_ids": codes,
            "playbook_count": len(codes),
        }
        for index, (name, codes) in enumerate(order.items(), start=1)
    ]


# --------------------------------------------------------------------------- #
# unit extraction
# --------------------------------------------------------------------------- #
def flags_from_cell(value: str) -> dict[str, bool]:
    return {
        "revenue_critical": FLAG_REVENUE_CRITICAL in value,
        "safety_critical": FLAG_SAFETY_CRITICAL in value,
    }


def build_units(
    master_rows: list[dict[str, str]],
    core_rows: list[dict[str, str]],
    vertical_rows: list[dict[str, str]],
    edge_universal_rows: list[dict[str, str]],
    edge_vertical_rows: list[dict[str, str]],
    departments: list[dict[str, Any]],
    verticals: list[dict[str, Any]],
    domains: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Join the master sheet against the four detail sheets.

    The master sheet is ordered: core workers, specialists, universal playbooks,
    vertical playbooks -- each block in the same order as its detail sheet.  The
    join is positional within each block and every pairing is asserted on a
    shared field, so a re-ordered workbook fails loudly rather than silently
    mis-attributing a row.
    """
    by_type: dict[str, list[dict[str, str]]] = {}
    for row in master_rows:
        by_type.setdefault(row["Type"], []).append(row)

    department_by_name = {d["name"]: d for d in departments}
    vertical_by_number = {v["number"]: v for v in verticals}
    domain_by_name = {d["name"]: d for d in domains}

    units: list[dict[str, Any]] = []

    # -- core workers -------------------------------------------------------
    for master, detail in zip(by_type["Core worker"], core_rows):
        assert master["Ref"] == detail["ID"], (master["Ref"], detail["ID"])
        department = department_by_name[detail["Department"]]
        units.append(
            {
                "id": detail["ID"],
                "type": "core_worker",
                "worker": detail["Worker"],
                "system_agent": detail["System agent"],
                "department": {"id": department["id"], "name": department["name"]},
                "vertical": None,
                "archetypes": [],
                "trigger": None,
                "function": detail["Function"],
                "expected_output": detail["Expected output"],
                "acceptance_criteria": parse_expected_output(detail["Expected output"]),
                "mechanism_family": detail["MF"],
                "flags": flags_from_cell(detail["*"] or master["Flags"]),
                "human_gates": parse_human_gates(master["What stays human"]),
                "slug": slugify(detail["Worker"]),
                "path": f"agents/core/{department['slug']}/{detail['ID'].lower()}-{slugify(detail['Worker'])}.yaml",
            }
        )

    # -- vertical specialists ----------------------------------------------
    specialist_counter: Counter[int] = Counter()
    for master, detail in zip(by_type["Specialist"], vertical_rows):
        assert master["Worker / Playbook"] == detail["Worker"]
        assert master["System name / Trigger"] == detail["System agent"]
        number = int(detail["V#"])
        specialist_counter[number] += 1
        unit_id = f"V{number}-S{specialist_counter[number]}"
        vertical = vertical_by_number[number]
        units.append(
            {
                "id": unit_id,
                "type": "specialist",
                "worker": detail["Worker"],
                "system_agent": detail["System agent"],
                "department": None,
                "vertical": {
                    "id": vertical["id"],
                    "number": number,
                    "name": vertical["name"],
                    "segment": vertical["segment"],
                },
                "archetypes": vertical["archetypes"],
                "trigger": None,
                "function": detail["Function"],
                "expected_output": detail["Expected output"],
                "acceptance_criteria": parse_expected_output(detail["Expected output"]),
                "mechanism_family": detail["MF"],
                "flags": flags_from_cell(detail["*"] or master["Flags"]),
                "human_gates": parse_human_gates(master["What stays human"]),
                "slug": slugify(detail["Worker"]),
                "path": f"agents/verticals/{vertical['slug']}/{unit_id.lower()}-{slugify(detail['Worker'])}.yaml",
            }
        )

    # -- universal playbooks ------------------------------------------------
    for master, detail in zip(by_type["Playbook (universal)"], edge_universal_rows):
        assert master["Ref"] == detail["Code"], (master["Ref"], detail["Code"])
        domain = domain_by_name[detail["Domain"]]
        units.append(
            {
                "id": detail["Code"],
                "type": "playbook_universal",
                "worker": None,
                "system_agent": None,
                "department": None,
                "vertical": None,
                "archetypes": [],
                "domain": {"id": domain["id"], "name": domain["name"]},
                "trigger": detail["Trigger / edge case"],
                "function": detail["Automated handling"],
                "expected_output": detail["Expected output"],
                "acceptance_criteria": parse_expected_output(detail["Expected output"]),
                "mechanism_family": detail["MF"],
                "flags": flags_from_cell(master["Flags"]),
                "human_gates": parse_human_gates(detail["What stays human"]),
                "slug": slugify(detail["Trigger / edge case"]),
                "path": f"agents/playbooks/universal/{domain['slug']}/{detail['Code'].lower()}-{slugify(detail['Trigger / edge case'])}.yaml",
            }
        )

    # -- vertical playbooks -------------------------------------------------
    playbook_counter: Counter[int] = Counter()
    for master, detail in zip(by_type["Playbook (vertical)"], edge_vertical_rows):
        assert master["Worker / Playbook"] == detail["Trigger / edge case"]
        number = int(detail["V#"])
        playbook_counter[number] += 1
        unit_id = f"V{number}-E{playbook_counter[number]}"
        assert master["Ref"] == unit_id, (master["Ref"], unit_id)
        vertical = vertical_by_number[number]
        units.append(
            {
                "id": unit_id,
                "type": "playbook_vertical",
                "worker": None,
                "system_agent": None,
                "department": None,
                "vertical": {
                    "id": vertical["id"],
                    "number": number,
                    "name": vertical["name"],
                    "segment": vertical["segment"],
                },
                "archetypes": vertical["archetypes"],
                "trigger": detail["Trigger / edge case"],
                "function": detail["Automated handling"],
                "expected_output": detail["Expected output"],
                "acceptance_criteria": parse_expected_output(detail["Expected output"]),
                "mechanism_family": detail["MF"],
                "flags": flags_from_cell(master["Flags"]),
                "human_gates": parse_human_gates(detail["What stays human"]),
                "slug": slugify(detail["Trigger / edge case"]),
                "path": f"agents/playbooks/vertical/{vertical['slug']}/{unit_id.lower()}-{slugify(detail['Trigger / edge case'])}.yaml",
            }
        )

    return units


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def build(workbook_path: Path, out_dir: Path) -> dict[str, Any]:
    workbook = openpyxl.load_workbook(workbook_path, data_only=True)

    master_rows = read_sheet(workbook, SHEET_MASTER)
    core_rows = read_sheet(workbook, SHEET_CORE)
    vertical_rows = read_sheet(workbook, SHEET_VERTICALS)
    edge_universal_rows = read_sheet(workbook, SHEET_EDGE_UNIVERSAL)
    edge_vertical_rows = read_sheet(workbook, SHEET_EDGE_VERTICAL)

    forward_fill(core_rows, ["Department"])
    forward_fill(vertical_rows, ["V#", "Vertical cluster", "Segment", "Examples", "Arch."])
    forward_fill(edge_universal_rows, ["Domain"])
    forward_fill(edge_vertical_rows, ["V#", "Vertical cluster"])

    archetypes = build_archetypes(workbook)
    mechanism_families = build_mechanism_families(workbook)
    localization = build_localization(workbook)
    departments = build_departments(core_rows)
    verticals = build_verticals(vertical_rows, edge_vertical_rows)
    domains = build_edge_case_domains(edge_universal_rows)

    units = build_units(
        master_rows,
        core_rows,
        vertical_rows,
        edge_universal_rows,
        edge_vertical_rows,
        departments,
        verticals,
        domains,
    )

    # -- invariants ---------------------------------------------------------
    counts = Counter(u["type"] for u in units)
    for unit_type, expected in EXPECTED_COUNTS.items():
        if counts[unit_type] != expected:
            raise AssertionError(
                f"{unit_type}: extracted {counts[unit_type]}, workbook declares {expected}"
            )
    if len(units) != 815:
        raise AssertionError(f"extracted {len(units)} units, expected 815")
    ids = [u["id"] for u in units]
    duplicates = [i for i, n in Counter(ids).items() if n > 1]
    if duplicates:
        raise AssertionError(f"duplicate unit ids: {duplicates}")
    paths = [u["path"] for u in units]
    duplicate_paths = [p for p, n in Counter(paths).items() if n > 1]
    if duplicate_paths:
        raise AssertionError(f"colliding unit paths: {duplicate_paths}")
    known_mfs = {m["id"] for m in mechanism_families}
    unknown = {u["mechanism_family"] for u in units} - known_mfs
    if unknown:
        raise AssertionError(f"units bound to unknown mechanism families: {unknown}")

    catalogue = {
        "version": "2",
        "source": workbook_path.name,
        "totals": {
            "units": len(units),
            **{k: counts[k] for k in EXPECTED_COUNTS},
            "departments": len(departments),
            "verticals": len(verticals),
            "archetypes": len(archetypes),
            "mechanism_families": len(mechanism_families),
            "edge_case_domains": len(domains),
        },
        "standing_rules": [
            "Config, not code - vertical and country differences resolve to config; "
            "14 engines carry all 815 units.",
            "Customer-owned channels - growth and social publish only from the "
            "customer's connected accounts.",
            "Probabilistic components flag, collect and draft - never clear, "
            "diagnose, advise or approve.",
        ],
        "departments": departments,
        "verticals": verticals,
        "archetypes": archetypes,
        "mechanism_families": mechanism_families,
        "edge_case_domains": domains,
        "localization": localization,
        "units": units,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "catalogue.json").open("w", encoding="utf-8") as handle:
        json.dump(catalogue, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    yaml_dump(departments, out_dir / "departments.yaml")
    yaml_dump(verticals, out_dir / "verticals.yaml")
    yaml_dump(archetypes, out_dir / "archetypes.yaml")
    yaml_dump(mechanism_families, out_dir / "mechanism_families.yaml")
    yaml_dump(domains, out_dir / "edge_case_domains.yaml")
    yaml_dump(localization, out_dir / "localization.yaml")
    yaml_dump(units, out_dir / "units.yaml")
    return catalogue


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="regenerate into a temp dir and diff against the committed catalogue",
    )
    args = parser.parse_args(argv)

    if args.check:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            build(args.workbook, tmp_dir)
            stale = []
            for generated in sorted(tmp_dir.iterdir()):
                committed = args.out / generated.name
                if not committed.exists() or committed.read_bytes() != generated.read_bytes():
                    stale.append(generated.name)
            if stale:
                print("catalogue is stale, re-run build_catalogue.py:", ", ".join(stale))
                return 1
            print("catalogue is up to date")
            return 0

    catalogue = build(args.workbook, args.out)
    totals = catalogue["totals"]
    print(f"catalogue written to {args.out}")
    for key, value in totals.items():
        print(f"  {key:22} {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
