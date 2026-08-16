"""Load the catalogue and the generated unit specs, and index them.

Two loaders live here because there are two representations of the same thing:

* :class:`Catalogue` reads ``catalogue/*.yaml`` -- the normalised workbook. This
  is what the generator composes from.
* :class:`Registry` reads ``agents/**/*.yaml`` -- the 815 generated specs. This
  is what the runtime serves.

They are kept separate on purpose. If the two ever disagree, the catalogue wins
and the specs are stale: re-run ``tools/generate_agents.py``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

import yaml

from adw.models import (
    AcceptanceCriterion,
    Archetype,
    Artifact,
    Capability,
    ConfigKey,
    CountryPack,
    Department,
    EdgeCaseDomain,
    Escalation,
    Flags,
    GateSeverity,
    Guardrail,
    HumanGate,
    MechanismFamily,
    Scope,
    Step,
    StepKind,
    Unit,
    UnitType,
    Vertical,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOGUE_DIR = REPO_ROOT / "catalogue"
AGENTS_DIR = REPO_ROOT / "agents"
PACKS_DIR = REPO_ROOT / "packs" / "countries"


# --------------------------------------------------------------------------- #
# catalogue
# --------------------------------------------------------------------------- #


@dataclass
class Catalogue:
    """The normalised workbook: reference tables plus 815 raw unit records."""

    data: Mapping[str, Any]

    @classmethod
    def load(cls, path: Path | None = None) -> "Catalogue":
        path = path or CATALOGUE_DIR / "catalogue.json"
        if not path.exists():
            raise FileNotFoundError(
                f"{path} is missing. Run: python tools/build_catalogue.py"
            )
        return cls(json.loads(path.read_text(encoding="utf-8")))

    # -- reference tables --------------------------------------------------
    @cached_property
    def mechanism_families(self) -> dict[str, MechanismFamily]:
        return {
            m["id"]: MechanismFamily(**m) for m in self.data["mechanism_families"]
        }

    @cached_property
    def archetypes(self) -> dict[str, Archetype]:
        return {
            a["id"]: Archetype(**{**a, "anchor_agents": tuple(a["anchor_agents"])})
            for a in self.data["archetypes"]
        }

    @cached_property
    def verticals(self) -> dict[str, Vertical]:
        return {
            v["id"]: Vertical(
                **{
                    **v,
                    "examples": tuple(v["examples"]),
                    "archetypes": tuple(v["archetypes"]),
                    "specialist_ids": tuple(v["specialist_ids"]),
                    "playbook_ids": tuple(v["playbook_ids"]),
                }
            )
            for v in self.data["verticals"]
        }

    @cached_property
    def departments(self) -> dict[str, Department]:
        return {
            d["id"]: Department(**{**d, "unit_ids": tuple(d["unit_ids"])})
            for d in self.data["departments"]
        }

    @cached_property
    def domains(self) -> dict[str, EdgeCaseDomain]:
        return {
            d["id"]: EdgeCaseDomain(**{**d, "unit_ids": tuple(d["unit_ids"])})
            for d in self.data["edge_case_domains"]
        }

    @property
    def localization(self) -> Mapping[str, Any]:
        return self.data["localization"]

    @property
    def standing_rules(self) -> Sequence[str]:
        return self.data["standing_rules"]

    @property
    def totals(self) -> Mapping[str, int]:
        return self.data["totals"]

    # -- units -------------------------------------------------------------
    @property
    def records(self) -> list[dict[str, Any]]:
        return self.data["units"]

    def record(self, unit_id: str) -> dict[str, Any]:
        for unit in self.records:
            if unit["id"] == unit_id:
                return unit
        raise KeyError(unit_id)

    def vertical_by_number(self, number: int) -> Vertical:
        return self.verticals[f"V{number}"]


# --------------------------------------------------------------------------- #
# spec deserialisation
# --------------------------------------------------------------------------- #


def unit_from_dict(data: Mapping[str, Any], path: str = "") -> Unit:
    """Rebuild a :class:`Unit` from its on-disk YAML shape."""
    scope_data = data.get("scope", {})
    department = scope_data.get("department") or {}
    vertical = scope_data.get("vertical") or {}
    domain = scope_data.get("domain") or {}
    engine = data.get("engine", {})

    return Unit(
        id=data["id"],
        type=UnitType(data["type"]),
        scope=Scope(
            department_id=department.get("id"),
            department_name=department.get("name"),
            vertical_id=vertical.get("id"),
            vertical_name=vertical.get("name"),
            segment=vertical.get("segment"),
            domain_id=domain.get("id"),
            domain_name=domain.get("name"),
            archetypes=tuple(scope_data.get("archetypes") or ()),
        ),
        mechanism_family=engine["mechanism_family"],
        function=data["function"],
        expected_output=data["expected_output"],
        acceptance=tuple(
            AcceptanceCriterion(**a) for a in data.get("acceptance", ())
        ),
        flags=Flags(**data.get("flags", {})),
        worker=data.get("worker"),
        system_agent=data.get("system_agent"),
        trigger=data.get("trigger"),
        mission=data.get("mission", ""),
        inputs=tuple(data.get("inputs") or ()),
        artifacts=tuple(Artifact(**a) for a in data.get("artifacts", ())),
        plan=tuple(
            Step(
                id=s["id"],
                name=s["name"],
                kind=StepKind(s["kind"]),
                description=s["description"],
                produces=tuple(s.get("produces") or ()),
                interlock=bool(s.get("interlock")),
            )
            for s in data.get("plan", ())
        ),
        guardrails=tuple(Guardrail(**g) for g in data.get("guardrails", ())),
        human_gates=tuple(
            HumanGate(
                decision=g["decision"],
                severity=GateSeverity(g["severity"]),
                escalate_to=Escalation(g["escalate_to"]),
                note=g.get("note", ""),
            )
            for g in data.get("human_gates", ())
        ),
        config_keys=tuple(ConfigKey(**c) for c in data.get("config_keys", ())),
        tools=tuple(data.get("tools") or ()),
        capabilities=tuple(Capability(c) for c in data.get("capabilities") or ()),
        kpis=tuple(data.get("kpis") or ()),
        channels=tuple(data.get("channels") or ()),
        depends_on=tuple(data.get("depends_on") or ()),
        engine_profile=engine.get("profile", "default"),
        engine_config=engine.get("config", {}),
        provenance=data.get("provenance", {}),
        path=path,
        version=data.get("version", 1),
    )


# --------------------------------------------------------------------------- #
# registry
# --------------------------------------------------------------------------- #


@dataclass
class Registry:
    """The 815 generated specs, indexed every way the runtime needs them."""

    units: dict[str, Unit] = field(default_factory=dict)

    @classmethod
    def load(cls, agents_dir: Path | None = None) -> "Registry":
        agents_dir = agents_dir or AGENTS_DIR
        if not agents_dir.exists():
            raise FileNotFoundError(
                f"{agents_dir} is missing. Run: python tools/generate_agents.py"
            )
        units: dict[str, Unit] = {}
        for path in sorted(agents_dir.rglob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            unit = unit_from_dict(data, path=str(path.relative_to(REPO_ROOT)))
            if unit.id in units:
                raise ValueError(f"duplicate unit id {unit.id} at {path}")
            units[unit.id] = unit
        return cls(units)

    # -- access ------------------------------------------------------------
    def __len__(self) -> int:
        return len(self.units)

    def __iter__(self) -> Iterator[Unit]:
        return iter(self.units.values())

    def __contains__(self, unit_id: object) -> bool:
        return unit_id in self.units

    def get(self, unit_id: str) -> Unit:
        try:
            return self.units[unit_id]
        except KeyError:
            raise KeyError(f"unknown unit {unit_id!r}") from None

    # -- indexes -----------------------------------------------------------
    @cached_property
    def by_mechanism_family(self) -> dict[str, list[Unit]]:
        index: dict[str, list[Unit]] = {}
        for unit in self:
            index.setdefault(unit.mechanism_family, []).append(unit)
        return index

    @cached_property
    def by_type(self) -> dict[UnitType, list[Unit]]:
        index: dict[UnitType, list[Unit]] = {}
        for unit in self:
            index.setdefault(unit.type, []).append(unit)
        return index

    @cached_property
    def by_department(self) -> dict[str, list[Unit]]:
        index: dict[str, list[Unit]] = {}
        for unit in self:
            if unit.scope.department_id:
                index.setdefault(unit.scope.department_id, []).append(unit)
        return index

    @cached_property
    def by_vertical(self) -> dict[str, list[Unit]]:
        index: dict[str, list[Unit]] = {}
        for unit in self:
            if unit.scope.vertical_id:
                index.setdefault(unit.scope.vertical_id, []).append(unit)
        return index

    @cached_property
    def by_domain(self) -> dict[str, list[Unit]]:
        index: dict[str, list[Unit]] = {}
        for unit in self:
            if unit.scope.domain_id:
                index.setdefault(unit.scope.domain_id, []).append(unit)
        return index

    @cached_property
    def by_archetype(self) -> dict[str, list[Unit]]:
        index: dict[str, list[Unit]] = {}
        for unit in self:
            for archetype in unit.scope.archetypes:
                index.setdefault(archetype, []).append(unit)
        return index

    # -- selections --------------------------------------------------------
    @property
    def core_workers(self) -> list[Unit]:
        return self.by_type.get(UnitType.CORE_WORKER, [])

    @property
    def specialists(self) -> list[Unit]:
        return self.by_type.get(UnitType.SPECIALIST, [])

    @property
    def universal_playbooks(self) -> list[Unit]:
        return self.by_type.get(UnitType.PLAYBOOK_UNIVERSAL, [])

    @property
    def vertical_playbooks(self) -> list[Unit]:
        return self.by_type.get(UnitType.PLAYBOOK_VERTICAL, [])

    @property
    def safety_critical(self) -> list[Unit]:
        return [u for u in self if u.is_safety_critical]

    @property
    def revenue_critical(self) -> list[Unit]:
        return [u for u in self if u.is_revenue_critical]

    def search(self, term: str) -> list[Unit]:
        """Substring search across the fields an operator would look in."""
        needle = term.lower()
        hits = []
        for unit in self:
            haystack = " ".join(
                str(part or "").lower()
                for part in (
                    unit.id,
                    unit.worker,
                    unit.system_agent,
                    unit.trigger,
                    unit.function,
                    unit.expected_output,
                    unit.scope.vertical_name,
                    unit.scope.department_name,
                )
            )
            if needle in haystack:
                hits.append(unit)
        return hits


# --------------------------------------------------------------------------- #
# country packs
# --------------------------------------------------------------------------- #


def load_country_pack(code: str, packs_dir: Path | None = None) -> CountryPack:
    """Load one market's configuration."""
    packs_dir = packs_dir or PACKS_DIR
    path = packs_dir / f"{code.lower()}.yaml"
    if not path.exists():
        available = sorted(p.stem.upper() for p in packs_dir.glob("*.yaml"))
        raise KeyError(f"no country pack for {code!r}; available: {available}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return CountryPack(
        code=data["code"],
        name=data["name"],
        languages=tuple(data["language_set"]),
        messaging_channels=tuple(data["messaging_channel"]),
        review_surfaces=tuple(data["review_surface"]),
        attach_to_platforms=tuple(data["attach_to_platforms"]),
        payment_rails=tuple(data["payment_rails"]),
        tax_calendar=tuple(data["tax_filing_calendar"]),
        statutory_date_sets=tuple(data["statutory_date_sets"]),
        regulator_guardrails=tuple(data["regulator_guardrails"]),
        seasonal_calendar=tuple(data["seasonal_calendar"]),
        settings={
            **data.get("settings", {}),
            "language_set": data["language_set"],
            "messaging_channel": data["messaging_channel"],
            "review_surface": data["review_surface"],
            "attach_to_platforms": data["attach_to_platforms"],
            "payment_rails": data["payment_rails"],
            "tax_filing_calendar": data["tax_filing_calendar"],
            "statutory_date_sets": data["statutory_date_sets"],
            "regulator_guardrails": data["regulator_guardrails"],
            "seasonal_calendar": data["seasonal_calendar"],
        },
    )


def available_country_packs(packs_dir: Path | None = None) -> list[str]:
    packs_dir = packs_dir or PACKS_DIR
    return sorted(p.stem.upper() for p in packs_dir.glob("*.yaml"))


__all__ = [
    "AGENTS_DIR",
    "CATALOGUE_DIR",
    "Catalogue",
    "PACKS_DIR",
    "REPO_ROOT",
    "Registry",
    "available_country_packs",
    "load_country_pack",
    "unit_from_dict",
]
