"""Resolve which units a given business actually runs, and in what order.

Every customer gets the same 815 units in the catalogue and a different subset
switched on.  The subset is not a matter of taste: it falls out of the vertical
(which specialists and vertical playbooks exist), the archetype (which agents
anchor the funnel), and the country pack (which channels and statutory clocks
are real in that market).

The rollout order falls out of the same three facts.  The workbook's Decision
column offers Now / Next / Later / Skip; this module computes a defensible
default for each unit so an owner is editing a recommendation rather than
filling in 815 blanks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Sequence

from adw.models import BusinessProfile, CountryPack, Unit, UnitType
from adw.registry import Catalogue, Registry


class Wave(str, Enum):
    """When a unit should be switched on."""

    NOW = "now"
    NEXT = "next"
    LATER = "later"
    SKIP = "skip"


#: Archetype J is the workbook's own exception: "Weak fit - availability only
#: (deprioritise)".  Its roster is deliberately thin.
WEAK_FIT_ARCHETYPE = "ARC-J"

#: Units that are never switched off, whatever the archetype.  A1 is marked
#: "never disabled" in the catalogue; A12 is the escape hatch that makes every
#: other agent safe to run.
ALWAYS_ON = ("A1", "A12")


@dataclass(frozen=True)
class RosterEntry:
    unit: Unit
    wave: Wave
    reason: str

    @property
    def id(self) -> str:
        return self.unit.id


@dataclass
class Roster:
    """The resolved set of units for one business, with a rollout order."""

    business: BusinessProfile
    country_pack: CountryPack
    entries: list[RosterEntry] = field(default_factory=list)
    archetypes: tuple[str, ...] = ()
    anchors: tuple[str, ...] = ()

    def __len__(self) -> int:
        return len([e for e in self.entries if e.wave is not Wave.SKIP])

    def wave(self, wave: Wave) -> list[RosterEntry]:
        return [e for e in self.entries if e.wave is wave]

    def by_type(self, unit_type: UnitType) -> list[RosterEntry]:
        return [e for e in self.entries if e.unit.type is unit_type]

    @property
    def active(self) -> list[RosterEntry]:
        return [e for e in self.entries if e.wave is not Wave.SKIP]

    def summary(self) -> dict[str, int]:
        counts = {w.value: len(self.wave(w)) for w in Wave}
        counts["total"] = len(self.entries)
        counts["active"] = len(self.active)
        return counts

    def explain(self) -> str:
        lines = [
            f"{self.business.name} - {self.country_pack.name} ({self.country_pack.code})",
            f"  vertical   : {self.business.vertical_id}",
            f"  archetypes : {', '.join(self.archetypes) or '-'}",
            f"  anchors    : {', '.join(self.anchors) or '-'}",
            f"  channels   : {', '.join(self.country_pack.messaging_channels)}",
            f"  languages  : {', '.join(self.country_pack.languages)}",
            "",
        ]
        for wave in Wave:
            entries = self.wave(wave)
            lines.append(f"{wave.value.upper()} ({len(entries)})")
            for entry in entries:
                lines.append(f"  {entry.id:<9} {entry.unit.display_name:<48} {entry.reason}")
            lines.append("")
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# resolution
# --------------------------------------------------------------------------- #


def resolve_archetypes(
    profile: BusinessProfile, catalogue: Catalogue
) -> tuple[str, ...]:
    """An explicit archetype on the profile wins; otherwise take the vertical's."""
    if profile.archetypes:
        return tuple(profile.archetypes)
    vertical = catalogue.verticals.get(profile.vertical_id)
    return tuple(vertical.archetypes) if vertical else ()


def resolve_anchors(archetypes: Sequence[str], catalogue: Catalogue) -> tuple[str, ...]:
    """The anchor agents named by the business's archetypes.

    The workbook writes anchors loosely -- "A3 (dispatch window)", "matter
    overlays" -- so only the tokens that look like unit ids are kept.
    """
    anchors: list[str] = []
    for archetype_id in archetypes:
        archetype = catalogue.archetypes.get(archetype_id)
        if not archetype:
            continue
        for raw in archetype.anchor_agents:
            token = raw.split("(")[0].strip()
            if token and token[0].isalpha() and token[1:2].isdigit():
                anchors.append(token)
    return tuple(dict.fromkeys(anchors))


def _core_wave(unit: Unit, anchors: Sequence[str], weak_fit: bool) -> tuple[Wave, str]:
    if unit.id in ALWAYS_ON:
        return Wave.NOW, "always on"
    if unit.id in anchors:
        return Wave.NOW, "archetype anchor"
    if unit.is_revenue_critical:
        return Wave.NOW, "revenue-critical"
    if weak_fit:
        # Archetype J has no client record and no repeat cycle; most of the
        # relationship machinery has nothing to work with.
        if unit.mechanism_family in ("MF4", "MF5") or unit.scope.department_name in (
            "Customer Growth Team",
            "Client Care",
        ):
            return Wave.SKIP, "weak fit for a walk-in retail archetype"
        return Wave.LATER, "weak-fit archetype, availability only"
    if unit.scope.department_name in ("Front Desk", "Switchboard", "Back Office"):
        return Wave.NEXT, "core operating department"
    return Wave.LATER, "supporting department"


def _specialist_wave(unit: Unit, weak_fit: bool) -> tuple[Wave, str]:
    if unit.is_revenue_critical:
        return Wave.NOW, "revenue-critical vertical specialist"
    if weak_fit:
        return Wave.LATER, "weak-fit archetype"
    return Wave.NEXT, "vertical specialist"


def _playbook_wave(unit: Unit) -> tuple[Wave, str]:
    if unit.is_safety_critical:
        # A safety protocol is not a phase-two nicety.  If the situation can
        # occur on day one, the protocol has to exist on day one.
        return Wave.NOW, "safety-critical protocol"
    if unit.type is UnitType.PLAYBOOK_UNIVERSAL:
        return Wave.NEXT, "universal edge case"
    return Wave.NEXT, "vertical edge case"


def resolve_roster(
    profile: BusinessProfile,
    catalogue: Catalogue,
    registry: Registry,
    country_pack: CountryPack,
) -> Roster:
    """Assemble the full roster for one business."""
    if profile.vertical_id not in catalogue.verticals:
        raise KeyError(
            f"unknown vertical {profile.vertical_id!r}; "
            f"expected one of V1..V{len(catalogue.verticals)}"
        )

    archetypes = resolve_archetypes(profile, catalogue)
    anchors = resolve_anchors(archetypes, catalogue)
    weak_fit = WEAK_FIT_ARCHETYPE in archetypes

    selected: list[Unit] = []
    selected.extend(registry.core_workers)
    selected.extend(registry.by_vertical.get(profile.vertical_id, []))
    selected.extend(registry.universal_playbooks)

    entries: list[RosterEntry] = []
    for unit in selected:
        if unit.type is UnitType.CORE_WORKER:
            wave, reason = _core_wave(unit, anchors, weak_fit)
        elif unit.type is UnitType.SPECIALIST:
            wave, reason = _specialist_wave(unit, weak_fit)
        else:
            wave, reason = _playbook_wave(unit)

        # Explicit owner choices override the recommendation in both directions.
        if unit.id in profile.disabled_units:
            if unit.id in ALWAYS_ON:
                wave, reason = Wave.NOW, "always on - cannot be disabled"
            else:
                wave, reason = Wave.SKIP, "disabled by the owner"
        elif unit.id in profile.enabled_units:
            wave, reason = Wave.NOW, "enabled by the owner"

        entries.append(RosterEntry(unit=unit, wave=wave, reason=reason))

    order = {Wave.NOW: 0, Wave.NEXT: 1, Wave.LATER: 2, Wave.SKIP: 3}
    entries.sort(key=lambda e: (order[e.wave], e.unit.id))

    return Roster(
        business=profile,
        country_pack=country_pack,
        entries=entries,
        archetypes=archetypes,
        anchors=anchors,
    )


def missing_config(roster: Roster) -> dict[str, list[str]]:
    """Config keys the roster needs that the country pack cannot supply.

    Anything left here is an owner-supplied setting: opening hours, the price
    book, who takes an escalation out of hours.  Onboarding is exactly the work
    of emptying this dictionary.
    """
    outstanding: dict[str, list[str]] = {}
    pack_keys = set(roster.country_pack.settings)
    for entry in roster.active:
        for key in entry.unit.config_keys:
            if not key.required:
                continue
            if key.resolved_by == "country_pack" and key.key in pack_keys:
                continue
            outstanding.setdefault(key.key, []).append(entry.id)
    return dict(sorted(outstanding.items()))


def coverage(registry: Registry, catalogue: Catalogue) -> dict[str, object]:
    """How much of the catalogue is reachable through some roster.

    A unit that no vertical, department or domain can ever select is dead
    weight, so this is checked rather than assumed.
    """
    reachable: set[str] = {u.id for u in registry.core_workers}
    reachable |= {u.id for u in registry.universal_playbooks}
    for vertical_id in catalogue.verticals:
        reachable |= {u.id for u in registry.by_vertical.get(vertical_id, [])}
    unreachable = sorted({u.id for u in registry} - reachable)
    return {
        "total": len(registry),
        "reachable": len(reachable),
        "unreachable": unreachable,
    }


__all__ = [
    "ALWAYS_ON",
    "Roster",
    "RosterEntry",
    "WEAK_FIT_ARCHETYPE",
    "Wave",
    "coverage",
    "missing_config",
    "resolve_anchors",
    "resolve_archetypes",
    "resolve_roster",
]
