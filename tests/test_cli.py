"""The CLI is how an operator reads the catalogue, so it is tested like a feature.

Each command is exercised against the real 815 specs rather than fixtures: a CLI
that works on a toy registry and falls over on the shipped one is not tested.
"""

from __future__ import annotations

import json

import pytest

from adw.cli import main


def run(capsys, *argv: str) -> tuple[int, str]:
    code = main(list(argv))
    return code, capsys.readouterr().out


def test_catalogue_reports_the_totals(capsys):
    code, out = run(capsys, "catalogue")
    assert code == 0
    assert "815" in out
    assert "Config, not code" in out


def test_engines_lists_all_fourteen(capsys):
    code, out = run(capsys, "engines")
    assert code == 0
    for n in range(1, 15):
        assert f"MF{n}" in out
    assert "815 units carried by 14 engines" in out


def test_list_without_filters_shows_everything(capsys):
    code, out = run(capsys, "list")
    assert code == 0
    assert "815 unit(s)" in out


@pytest.mark.parametrize(
    "argv,expected",
    [
        (("list", "--type", "core_worker"), "68 unit(s)"),
        (("list", "--type", "specialist"), "355 unit(s)"),
        (("list", "--type", "playbook_universal"), "92 unit(s)"),
        (("list", "--type", "playbook_vertical"), "300 unit(s)"),
        (("list", "--safety-critical"), "37 unit(s)"),
        (("list", "--revenue-critical"), "68 unit(s)"),
    ],
)
def test_list_filters(capsys, argv, expected):
    code, out = run(capsys, *argv)
    assert code == 0
    assert expected in out


def test_list_by_vertical(capsys):
    code, out = run(capsys, "list", "--vertical", "V7")
    assert code == 0
    # Six specialists plus five playbooks for clinical & health.
    assert "11 unit(s)" in out


def test_list_by_department(capsys):
    code, out = run(capsys, "list", "--department", "Front Desk")
    assert code == 0
    assert "12 unit(s)" in out


def test_list_json_is_parseable(capsys):
    code, out = run(capsys, "list", "--mf", "MF11", "--json")
    assert code == 0
    data = json.loads(out)
    assert len(data) == 3
    assert {u["id"] for u in data} == {"F1", "F2", "F4"}


def test_show_renders_a_full_unit(capsys):
    code, out = run(capsys, "show", "A1")
    assert code == 0
    for section in ("MISSION", "PLAN", "ARTEFACTS", "HUMAN GATES", "GUARDRAILS", "CONFIG KEYS"):
        assert section in out
    assert "Receptionist" in out


def test_show_is_case_insensitive(capsys):
    code, out = run(capsys, "show", "v1-s1")
    assert code == 0
    assert "Night Dispatcher" in out


def test_show_json_round_trips(capsys):
    code, out = run(capsys, "show", "CUS-01", "--json")
    assert code == 0
    data = json.loads(out)
    assert data["id"] == "CUS-01"
    assert data["kind"] == "playbook"


def test_show_unknown_unit_exits_nonzero(capsys):
    code, _ = run(capsys, "show", "NOPE-99")
    assert code == 2


def test_roster_resolves_and_explains(capsys):
    code, out = run(capsys, "roster", "--vertical", "V7", "--country", "UK", "--name", "Test Dental")
    assert code == 0
    assert "Test Dental" in out
    assert "United Kingdom" in out
    assert "NOW" in out and "NEXT" in out
    assert "ONBOARDING" in out


def test_roster_json_carries_waves_and_missing_config(capsys):
    code, out = run(capsys, "roster", "--vertical", "V1", "--country", "US", "--json")
    assert code == 0
    data = json.loads(out)
    assert data["summary"]["total"] == 68 + 5 + 5 + 92
    assert data["archetypes"] == ["ARC-A"]
    assert "escalation_contacts" in data["missing_config"]


def test_roster_unknown_country_exits_nonzero(capsys):
    code, _ = run(capsys, "roster", "--vertical", "V1", "--country", "ZZ")
    assert code == 2


def test_audit_passes_on_the_shipped_catalogue(capsys):
    code, out = run(capsys, "audit", "--severity", "error")
    assert code == 0, out
    assert "errors             : 0" in out
    assert "reachable by roster: 815/815" in out


def test_search_finds_by_worker_title(capsys):
    code, out = run(capsys, "search", "missed call")
    assert code == 0
    assert "F2" in out


def test_verticals_lists_sixty(capsys):
    code, out = run(capsys, "verticals")
    assert code == 0
    assert "60 verticals" in out


def test_archetypes_lists_ten(capsys):
    code, out = run(capsys, "archetypes")
    assert code == 0
    for letter in "ABCDEFGHIJ":
        assert f"ARC-{letter}" in out


def test_packs_lists_the_country_packs(capsys):
    code, out = run(capsys, "packs")
    assert code == 0
    assert "country packs" in out
    assert "United Arab Emirates" in out
