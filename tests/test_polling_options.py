"""Poll intervals are a setting, and the reason is contention.

A Sungrow inverter accepts very few Modbus sessions at once. When something
else polls the same inverter -- the YAML package, another Home Assistant, a
logger -- the two compete for one, and that is what most reported dropouts
turn out to be. Slowing a group down or switching it off is the cheapest fix
available, so it has to be reachable without editing anything.
"""

from __future__ import annotations

from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    AUDIENCE_ADMINS,
    AUDIENCE_USERS,
    CONF_INTERVALS,
    CONF_PERMISSIONS,
    CONF_UNIT_ID,
    DOMAIN,
    INTERVAL_NEVER,
    PERMISSION_START_STOP,
    SECTION_ADVANCED,
    SECTION_EXTERNAL,
    SECTION_PERMISSIONS,
    SECTION_POLLING,
    SECTION_SURVEY,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from sungrow_modbus import COMPONENTS, DEFAULT_INTERVALS, TIER_COMPONENTS

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}


def _submission(**sections: dict) -> dict:
    """Build a full options submission, overriding one section at a time.

    The options page is one form of sections now, and every section key is
    required -- the frontend always submits all of them. Fields *inside* a
    section may be left out, because each carries a default, which is what
    keeps these tests about the thing they are testing.
    """
    payload: dict = {
        SECTION_POLLING: {"realtime": 5, "fast": 30, "medium": 60, "slowest": 600},
        SECTION_PERMISSIONS: {},
        SECTION_EXTERNAL: {},
        SECTION_ADVANCED: {},
        SECTION_SURVEY: {},
    }
    payload.update(sections)
    return payload


async def _setup(
    hass: HomeAssistant, unit: MockModbusUnit, options: dict | None = None
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=ENTRY_DATA,
        options=options or {},
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_the_defaults_are_the_yaml_packages_own_tiers(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Somebody who changes nothing sees the freshness they are used to."""
    entry = await _setup(hass, sungrow_unit)
    assert entry.runtime_data.intervals == DEFAULT_INTERVALS
    assert DEFAULT_INTERVALS == {
        "realtime": 5,
        "fast": 10,
        "medium": 60,
        "slowest": 600,
    }


async def test_a_configured_interval_is_what_the_coordinator_uses(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    entry = await _setup(
        hass, sungrow_unit, {CONF_INTERVALS: {"fast": 60, "slowest": 3600}}
    )

    runtime = entry.runtime_data
    assert runtime.interval_of("fast_input") == 60
    assert runtime.interval_of("slowest_input") == 3600
    # Untouched groups keep their defaults.
    assert runtime.interval_of("realtime_input") == 5

    fast = runtime.coordinator_for("fast_input")
    assert fast.update_interval.total_seconds() == 60


async def test_a_group_set_to_never_is_not_polled_and_has_no_entities(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The point of the setting: stop asking for data nobody looks at."""
    entry = await _setup(
        hass, sungrow_unit, {CONF_INTERVALS: {"slowest": INTERVAL_NEVER}}
    )

    assert entry.state is ConfigEntryState.LOADED
    runtime = entry.runtime_data
    assert "slowest_input" not in runtime.coordinators
    # And the entities that group would have fed are simply absent, rather
    # than present and permanently unavailable.
    assert hass.states.get("sensor.sh10rt_total_pv_generation") is None
    # While a group that is still polled is unaffected.
    assert hass.states.get("sensor.sh10rt_total_dc_power") is not None


async def test_turning_everything_off_is_refused_rather_than_silently_empty(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """An integration with no entities at all is a bug report, not a setting."""
    entry = await _setup(
        hass,
        sungrow_unit,
        {CONF_INTERVALS: dict.fromkeys(DEFAULT_INTERVALS, INTERVAL_NEVER)},
    )
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert "set to never" in str(entry.reason)


async def test_the_options_flow_shows_what_each_group_contains(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Four bare numbers cannot answer "what am I slowing down?"."""
    entry = await _setup(hass, sungrow_unit)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    # One page, not a menu: every setting is on it, grouped into sections.
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    table = result["description_placeholders"]["tiers"]
    for tier in DEFAULT_INTERVALS:
        assert f"`{tier}`" in table
    # The register counts, so the trade is visible. Derived rather than
    # written down: this assertion was a literal `| 61 |` and broke the first
    # time a register was added to a tier, which says nothing about the table
    # being right and everything about the number having moved.
    for tier, components in TIER_COMPONENTS.items():
        count = len(
            {name for c in components for name in COMPONENTS[c].declared_fields}
        )
        assert f"| {count} |" in table, f"{tier} should show its {count} registers"
    assert "load power" in table


async def test_setting_an_interval_through_the_flow_takes_effect(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    entry = await _setup(hass, sungrow_unit)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            _submission(
                polling={
                    "realtime": 5,
                    "fast": 30,
                    "medium": 60,
                    "slowest": INTERVAL_NEVER,
                }
            ),
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_INTERVALS] == {
        "realtime": 5,
        "fast": 30,
        "medium": 60,
        "slowest": 0,
    }
    assert entry.runtime_data.interval_of("fast_input") == 30
    assert "slowest_input" not in entry.runtime_data.coordinators


@pytest.mark.parametrize("interval", [1, 2, 4])
async def test_an_interval_below_five_seconds_is_not_accepted(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit, interval: int
) -> None:
    """Sungrow's protocol warns against polling frequently through a dongle.

    5 seconds is already the fastest the YAML package ever used, so anything
    lower spends a connection the inverter has few of and buys nothing.
    """
    entry = await _setup(hass, sungrow_unit)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    with pytest.raises(InvalidData):
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            _submission(
                polling={
                    "realtime": interval,
                    "fast": 10,
                    "medium": 60,
                    "slowest": 600,
                }
            ),
        )


async def test_a_derived_value_follows_the_configured_fastest_group(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Which group writes a derived value depends on the intervals, not the names.

    `export_power` is computed from a register in the realtime group. Slow
    that group below the fast one and the derived value should follow the fast
    one instead -- otherwise it would visibly lag the sensors it is computed
    from, which is the one thing the template sensors never did.
    """
    entry = await _setup(hass, sungrow_unit, {CONF_INTERVALS: {"realtime": 300}})
    runtime = entry.runtime_data

    assert runtime.interval_of("realtime_input") == 300
    # Asserted on the *interval*, not the component name. `battery_power` has
    # since been isolated into its own component in the same fast tier, so
    # the pair is a tie between two fast-tier groups and either satisfies what
    # this is protecting: the derived value must not be written by a group
    # slower than the registers it is computed from. Pinning a name made an
    # unrelated `layout.py` entry fail this test.
    chosen = runtime.fastest_component(("export_power_raw", "battery_power"))
    assert runtime.interval_of(chosen) == runtime.interval_of("fast_input")
    assert runtime.interval_of(chosen) < runtime.interval_of("realtime_input")


async def test_the_permissions_step_saves_the_audience(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The screen an owner reaches to hand start/stop to the household."""
    entry = await _setup(hass, sungrow_unit)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"

    # The safe answer is what the form offers before anything is chosen --
    # inside the section it belongs to, which is where the defaults now live.
    schema = result["data_schema"](_submission())
    assert schema[SECTION_PERMISSIONS][PERMISSION_START_STOP] == AUDIENCE_ADMINS

    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            _submission(permissions={PERMISSION_START_STOP: AUDIENCE_USERS}),
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_PERMISSIONS] == {PERMISSION_START_STOP: AUDIENCE_USERS}


async def test_the_permissions_step_leaves_the_other_options_alone(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Changing one section must not quietly undo another.

    One page means one save, so every section is written on every submit --
    which is exactly when a form that offered the *wrong* default would eat a
    setting. The protection is that each section is filled from the entry's
    current options, so a value nobody touched survives the round trip.

    What changed with the sections: the saved intervals are now the complete
    set rather than the single key that was configured. That is the page
    reporting what it showed, and the value that matters is still 30.
    """
    entry = await _setup(hass, sungrow_unit, {CONF_INTERVALS: {"realtime": 30}})

    result = await hass.config_entries.options.async_init(entry.entry_id)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        # Only the permissions section is given; everything else takes the
        # defaults the form was built with.
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                SECTION_POLLING: {},
                SECTION_PERMISSIONS: {PERMISSION_START_STOP: AUDIENCE_USERS},
                SECTION_EXTERNAL: {},
                SECTION_ADVANCED: {},
                SECTION_SURVEY: {},
            },
        )
        await hass.async_block_till_done()

    assert entry.options[CONF_INTERVALS]["realtime"] == 30
    assert entry.options[CONF_INTERVALS]["fast"] == DEFAULT_INTERVALS["fast"]
    assert entry.options[CONF_PERMISSIONS] == {PERMISSION_START_STOP: AUDIENCE_USERS}
