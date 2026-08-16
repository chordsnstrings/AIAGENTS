"""Country packs are the only place a market-specific fact may live.

If a pack is incomplete, some unit will end up inferring the missing value at
runtime -- which is precisely the hard-coding the config-not-code rule exists to
prevent.  So every pack must answer every field of the workbook's Localization
sheet, for every market.
"""

from __future__ import annotations

import pytest

from adw.registry import available_country_packs, load_country_pack

REQUIRED_LISTS = (
    "languages",
    "messaging_channels",
    "review_surfaces",
    "attach_to_platforms",
    "payment_rails",
    "tax_calendar",
    "statutory_date_sets",
    "regulator_guardrails",
    "seasonal_calendar",
)

REQUIRED_SETTINGS = ("date_format", "currency", "week_starts", "measurement")


def test_packs_exist():
    codes = available_country_packs()
    assert len(codes) >= 20
    assert {"US", "UK", "DE", "IN", "AE", "JP", "BR"} <= set(codes)


@pytest.mark.parametrize("code", available_country_packs())
def test_every_pack_answers_every_localization_field(code):
    pack = load_country_pack(code)
    for field in REQUIRED_LISTS:
        values = getattr(pack, field)
        assert values, f"{code}: {field} is empty"
        assert all(isinstance(v, str) and v.strip() for v in values), f"{code}: {field}"


@pytest.mark.parametrize("code", available_country_packs())
def test_every_pack_declares_its_formatting_settings(code):
    pack = load_country_pack(code)
    for setting in REQUIRED_SETTINGS:
        assert pack.get(setting), f"{code}: {setting} missing"


@pytest.mark.parametrize("code", available_country_packs())
def test_pack_code_matches_its_filename(code):
    assert load_country_pack(code).code == code


def test_localization_sheet_fields_all_have_a_pack_field(catalogue):
    """Every config field the workbook names must be answerable from a pack."""
    pack = load_country_pack("UK")
    for entry in catalogue.localization["config_fields"]:
        assert pack.get(entry["key"]) is not None, entry["key"]


def test_globalized_agents_are_named_by_their_global_names(catalogue, registry):
    """The workbook renamed eight UAE-anchored agents. The specs must use the new names."""
    globalized = catalogue.localization["globalized_agents"]
    assert len(globalized) == 8
    system_names = {u.system_agent for u in registry if u.system_agent}
    for entry in globalized:
        assert entry["system_agent"] in system_names, entry["system_agent"]


def test_no_pack_leaks_into_another(country_packs):
    """Two markets sharing an identical config would mean one was copied blindly."""
    signatures = {}
    for code, pack in country_packs.items():
        signature = (
            tuple(pack.languages),
            tuple(pack.payment_rails),
            tuple(pack.statutory_date_sets),
        )
        assert signature not in signatures, f"{code} duplicates {signatures.get(signature)}"
        signatures[signature] = code


def test_unknown_pack_raises():
    with pytest.raises(KeyError):
        load_country_pack("ZZ")
