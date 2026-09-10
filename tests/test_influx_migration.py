"""The InfluxDB helper prints artefacts; it must never do anything else.

Home Assistant's recorder follows a renamed entity and nothing outside it
does, so this script exists to hand InfluxDB and Grafana users the text they
need. Its value is entirely in being correct and inert: a wrong object id
produces a regex matching nothing, and a `sed` that is not anchored rewrites
the wrong series.
"""

from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "scripts")

from influx_migration import flux, grafana, influxql, pairs

ROWS = pairs("SH10RT")


def test_every_entity_is_covered() -> None:
    from custom_components.sungrow_modbus.derived_descriptions import (
        DERIVED_BINARY_SENSORS,
        DERIVED_SENSORS,
    )
    from custom_components.sungrow_modbus.sensor_descriptions import SENSOR_DESCRIPTIONS

    expected = {
        d.key
        for d in (*SENSOR_DESCRIPTIONS, *DERIVED_SENSORS, *DERIVED_BINARY_SENSORS)
        if d.legacy_name
    }
    assert {key for key, _, _ in ROWS} == expected


def test_it_maps_object_ids_not_entity_ids() -> None:
    """The InfluxDB integration tags points with the object id.

    Emitting `sensor.total_dc_power` would produce a filter matching nothing,
    and the mistake is invisible until somebody's dashboard stays empty.
    """
    for _, legacy, modern in ROWS:
        assert "." not in legacy
        assert "." not in modern


def test_the_modern_id_carries_the_device_prefix() -> None:
    lookup = {key: (legacy, modern) for key, legacy, modern in ROWS}
    assert lookup["total_dc_power"] == ("total_dc_power", "sh10rt_total_dc_power")


def test_no_two_entities_map_to_the_same_id() -> None:
    # A collision either way would silently merge two series.
    assert len({legacy for _, legacy, _ in ROWS}) == len(ROWS)
    assert len({modern for _, _, modern in ROWS}) == len(ROWS)


def test_the_grafana_regex_matches_both_names_and_nothing_else() -> None:
    import re

    text = grafana(ROWS, reverse=False)
    line = next(x for x in text.splitlines() if x.startswith("/^(total_dc_power|"))
    pattern = re.compile(line.split("    #")[0].strip().strip("/"))
    assert pattern.fullmatch("total_dc_power")
    assert pattern.fullmatch("sh10rt_total_dc_power")
    # Anchored, so it must not swallow a longer id that merely contains it.
    assert not pattern.fullmatch("total_dc_power_2")


def test_the_sed_commands_are_anchored_on_the_tag() -> None:
    """An unanchored rewrite would catch any id this one is a prefix of."""
    text = influxql(ROWS, reverse=False, database="homeassistant")
    for line in text.splitlines():
        if line.startswith("sed "):
            assert ",entity_id=" in line
            assert line.count(",/") >= 1, line


def test_the_destructive_steps_are_present_but_commented_out() -> None:
    """Nobody has ever regretted keeping the old series a week longer."""
    recipe = influxql(ROWS, reverse=False, database="homeassistant")
    assert "# DROP DATABASE homeassistant" in recipe
    assert "\nDROP DATABASE" not in recipe

    queries = flux(ROWS, reverse=False, bucket="homeassistant")
    assert "deleting the old series is deliberately not written out" in queries.lower()
    # A copy, not a move: `to()` writes the new tag and leaves the old series.
    assert queries.count("|> to(bucket:") == len(ROWS)


@pytest.mark.parametrize("reverse", [False, True])
def test_both_directions_are_offered(reverse: bool) -> None:
    """The migration is reversible, so its helper has to be too."""
    text = grafana(ROWS, reverse=reverse)
    source = "sh10rt_total_dc_power" if reverse else "total_dc_power"
    target = "total_dc_power" if reverse else "sh10rt_total_dc_power"
    assert f"/^({source}|{target})$/" in text
