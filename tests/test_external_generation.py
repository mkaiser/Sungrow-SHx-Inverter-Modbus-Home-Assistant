"""A generator the Sungrow cannot see, and the reading it makes wrong.

The inverter computes house load from its own output and its grid meter, so a
non-Sungrow inverter behind the same meter makes `load_power` **low by exactly
that inverter's output** and negative once it outproduces the house. Nothing
in the register map hints at it: every input to the figure was measured, so
the wrong answer looks like a reading.

What is asserted here is mostly the *refusals* -- the places where this could
quietly produce a plausible wrong number instead of admitting it does not
know. A partial sum, a unit guessed at, a correction applied to wiring it does
not suit, a negative load tidied away to zero: each is a number a dashboard
would show without complaint.
"""

from __future__ import annotations

from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_EXTERNAL_PLACEMENT,
    CONF_EXTERNAL_SOURCES,
    CONF_UNIT_ID,
    DOMAIN,
    PLACEMENT_BEHIND_METER,
    PLACEMENT_SEPARATE,
)
from custom_components.sungrow_modbus.external import combined, external_power
from homeassistant.const import CONF_HOST, CONF_PORT, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

FOREIGN = "sensor.fronius_power"
SECOND = "sensor.microinverter_power"

CORRECTED = "sensor.sh10rt_corrected_load_power"
SITE = "sensor.sh10rt_total_site_pv_power"
REPORTED = "sensor.sh10rt_load_power"


def _report(
    hass: HomeAssistant, entity_id: str, value: object, unit: str = "W"
) -> None:
    """Publish a foreign inverter's reading, as its own integration would."""
    hass.states.async_set(
        entity_id,
        value,
        {"unit_of_measurement": unit, "device_class": "power"},
    )


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


def _behind(*sources: str) -> dict:
    return {
        CONF_EXTERNAL_SOURCES: list(sources),
        CONF_EXTERNAL_PLACEMENT: PLACEMENT_BEHIND_METER,
    }


# -- the arithmetic, on its own ------------------------------------------------


async def test_the_total_is_in_watts_whatever_the_source_reports(
    hass: HomeAssistant,
) -> None:
    """A source reporting kW is as likely as one in W, and mixing them is 1000x."""
    _report(hass, FOREIGN, "3.4", unit="kW")
    _report(hass, SECOND, "250", unit="W")

    assert external_power(hass, (FOREIGN, SECOND)) == (3650.0, ())


async def test_no_sources_is_a_total_of_zero_not_unknown(
    hass: HomeAssistant,
) -> None:
    """Nothing to correct for is a known quantity, unlike a silent source."""
    assert external_power(hass, ()) == (0.0, ())


@pytest.mark.parametrize(
    ("value", "unit"),
    [
        (STATE_UNAVAILABLE, "W"),
        (STATE_UNKNOWN, "W"),
        ("not a number", "W"),
        # A power sensor with no unit, or a unit that is not power. Guessing
        # watts here is the 1000x error this refuses to make.
        ("1200", None),
        ("1200", "kWh"),
    ],
)
async def test_a_source_that_is_not_usable_makes_the_total_unknown(
    hass: HomeAssistant, value: str, unit: str | None
) -> None:
    """Never a partial sum: that is the original error wearing a measurement."""
    _report(hass, FOREIGN, "1000", unit="W")
    hass.states.async_set(
        SECOND,
        value,
        {"unit_of_measurement": unit, "device_class": "power"} if unit else {},
    )

    total, missing = external_power(hass, (FOREIGN, SECOND))
    assert total is None
    assert missing == (SECOND,)


async def test_a_source_that_does_not_exist_at_all_is_named(
    hass: HomeAssistant,
) -> None:
    """A renamed or deleted entity has to say so, not read as zero."""
    assert external_power(hass, ("sensor.gone",)) == (None, ("sensor.gone",))


def test_a_house_making_more_than_it_uses_stays_negative() -> None:
    """The sign convention, and the refusal to tidy it away.

    A negative corrected load is the signature of unmetered generation, and
    clamping it at zero would hide exactly the condition an owner needs to
    see. Stated as a test because a `max(0, …)` is the obvious thing for
    somebody to add later.
    """
    assert combined(-200.0, 3000.0) == 2800.0
    assert combined(500.0, 4000.0) == 4500.0
    # The house is drawing 500 W and the foreign inverter making 4 kW, so the
    # supply is exporting: true load 4.5 kW is wrong, and this is the case
    # the placement question exists to get right -- see the module docstring.
    assert combined(None, 1000.0) is None
    assert combined(1000.0, None) is None


# -- the entities --------------------------------------------------------------


async def test_nothing_is_created_when_no_source_is_named(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The common case: one inverter, and no second opinion to add."""
    await _setup(hass, sungrow_unit)

    assert hass.states.get(REPORTED) is not None
    assert hass.states.get(CORRECTED) is None
    assert hass.states.get(SITE) is None


async def test_the_corrected_load_is_the_reported_load_plus_the_foreign_power(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The whole point, on an inverter answering as an SH10RT."""
    _report(hass, FOREIGN, "1500", unit="W")
    await _setup(hass, sungrow_unit, _behind(FOREIGN))

    reported = float(hass.states.get(REPORTED).state)
    assert float(hass.states.get(CORRECTED).state) == pytest.approx(reported + 1500)


async def test_separately_metered_generation_does_not_correct_the_load(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """It never passed this meter, so the load figure is already right.

    Site production still counts it -- the site makes what it makes -- which
    is why one entity appears and the other does not.
    """
    _report(hass, FOREIGN, "1500", unit="W")
    await _setup(
        hass,
        sungrow_unit,
        {
            CONF_EXTERNAL_SOURCES: [FOREIGN],
            CONF_EXTERNAL_PLACEMENT: PLACEMENT_SEPARATE,
        },
    )

    assert hass.states.get(CORRECTED) is None
    assert hass.states.get(SITE) is not None


async def test_site_production_adds_the_foreign_inverter(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Both halves, however the other one is metered."""
    _report(hass, FOREIGN, "2.0", unit="kW")
    await _setup(hass, sungrow_unit, _behind(FOREIGN))

    sungrow = float(hass.states.get("sensor.sh10rt_total_dc_power").state)
    assert float(hass.states.get(SITE).state) == pytest.approx(sungrow + 2000)


async def test_a_silent_source_makes_the_entity_unknown_and_says_which(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Unknown rather than uncorrected, and the attribute answers "why?".

    Reporting the uncorrected figure would be indistinguishable from a
    correct reading, which is the failure this design refuses.
    """
    _report(hass, FOREIGN, STATE_UNAVAILABLE)
    await _setup(hass, sungrow_unit, _behind(FOREIGN))

    state = hass.states.get(CORRECTED)
    assert state.state == STATE_UNKNOWN
    assert state.attributes["external_sources"] == [FOREIGN]
    assert state.attributes["external_sources_not_reporting"] == [FOREIGN]


async def test_the_attributes_keep_one_shape_when_everything_answers(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Both keys always, so the recorder sees one shape rather than two."""
    _report(hass, FOREIGN, "900")
    await _setup(hass, sungrow_unit, _behind(FOREIGN))

    attributes = hass.states.get(CORRECTED).attributes
    assert attributes["external_sources"] == [FOREIGN]
    assert attributes["external_sources_not_reporting"] == []


# -- the options flow ----------------------------------------------------------


async def test_the_options_flow_records_the_sources_and_creates_the_entities(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Configurable after setup, because a house gains an inverter later."""
    _report(hass, FOREIGN, "1200")
    entry = await _setup(hass, sungrow_unit)
    assert hass.states.get(CORRECTED) is None

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "external"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "external"

    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_EXTERNAL_SOURCES: [FOREIGN],
                CONF_EXTERNAL_PLACEMENT: PLACEMENT_BEHIND_METER,
            },
        )
        await hass.async_block_till_done()

    assert entry.options[CONF_EXTERNAL_SOURCES] == [FOREIGN]
    assert entry.options[CONF_EXTERNAL_PLACEMENT] == PLACEMENT_BEHIND_METER
    # The entry reloads on an options change, which is what builds them.
    assert hass.states.get(CORRECTED) is not None


async def test_emptying_the_list_removes_the_correction(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Reversible, and by the same page that turned it on."""
    _report(hass, FOREIGN, "1200")
    entry = await _setup(hass, sungrow_unit, _behind(FOREIGN))
    assert hass.states.get(CORRECTED) is not None

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "external"}
    )
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_EXTERNAL_SOURCES: [],
                CONF_EXTERNAL_PLACEMENT: PLACEMENT_BEHIND_METER,
            },
        )
        await hass.async_block_till_done()

    assert entry.options[CONF_EXTERNAL_SOURCES] == []
    # Gone rather than left behind as `unavailable`. These two are the one
    # case where this integration removes a registry entry, because an owner
    # unnaming their other inverter is a decision and not a missed reading --
    # see `_async_drop_unused_corrections`.
    assert hass.states.get(CORRECTED) is None
    assert (
        er.async_get(hass).async_get_entity_id(
            "sensor", DOMAIN, f"{SERIAL}_corrected_load_power"
        )
        is None
    )
