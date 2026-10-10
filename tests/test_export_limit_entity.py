"""The export limit entity writes at the scale its own inverter measured.

Register 13074 multiplies a written word by ten at three houses and stores it
as handed at fwitten's pair. The library's field divides by ten for everyone,
so the entity asks the inverter once -- `sungrow_modbus.export_scale` -- keeps
the answer in the entry, and writes the raw word itself.

The double here is the firmware as measured, not as the probe reasons about
it: the multiply happens **before** the range check, a refusal is exception
0x04 and leaves the register alone, and with feed-in limitation off a write
is ignored without an exception.
"""

from __future__ import annotations

from unittest.mock import patch

from modbus_connection import IllegalDataValueError
from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_EXPORT_WRITE_SCALE,
    CONF_EXPORT_WRITE_SCALE_FIRMWARE,
    CONF_UNIT_ID,
    DOMAIN,
)
from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.const import ATTR_ENTITY_ID, CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .conftest import SERIAL, encode_string

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

LIMIT_ENTITY = "number.sh10rt_export_power_limit"

# Protocol addresses, one below the specification's register numbers.
LIMIT = 13073  # reg 13074
MODE = 13086  # reg 13087
MINIMUM = 5621  # reg 5622, input, tens of watts
MAXIMUM = 5622  # reg 5623, input, tens of watts

VERSION_1 = 2581  # reg 2582, the ARM firmware version string

ON, OFF = 0xAA, 0x55


def _firmware(unit: MockModbusUnit, *, multiplies: bool):
    """Return a `write_register` that behaves like one of the two firmwares."""

    async def write_register(address: int, value: int) -> None:
        if address == MODE:
            unit.holding[MODE] = value
            return
        if address != LIMIT:
            unit.holding[address] = value
            return
        if unit.holding[MODE] != ON:
            return  # ignored, and silently
        stored = value * 10 if multiplies else value
        minimum = unit.input[MINIMUM] * 10
        maximum = unit.input[MAXIMUM] * 10
        if not minimum <= stored <= maximum:
            raise IllegalDataValueError(0x04)
        unit.holding[LIMIT] = stored

    return write_register


async def _setup(
    hass: HomeAssistant,
    unit: MockModbusUnit,
    *,
    held: int,
    minimum: int,
    maximum: int,
    mode: int,
    data: dict | None = None,
    firmware: str | None = None,
) -> MockConfigEntry:
    unit.holding[LIMIT] = held
    unit.holding[MODE] = mode
    if firmware is not None:
        unit.input[VERSION_1] = encode_string(firmware, 11)
    unit.input[MINIMUM] = minimum // 10
    unit.input[MAXIMUM] = maximum // 10
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**ENTRY_DATA, **(data or {})},
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def _set(hass: HomeAssistant, value: float) -> None:
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: LIMIT_ENTITY, ATTR_VALUE: value},
        blocking=True,
    )


@pytest.mark.parametrize(
    ("house", "multiplies", "held", "minimum", "maximum", "mode", "asked", "factor"),
    [
        # bar12, 2026-10-10: limitation off, limit at the 10 kW maximum, so
        # the probe may lift the mode for its one write. Refused: times ten.
        ("bar12", True, 10000, 0, 10000, OFF, 9000, 10),
        # fwitten's slave, 2026-09-25: limitation on, cluster-sized bounds.
        ("fwitten slave", False, 11880, 11880, 24990, ON, 12000, 1),
    ],
)
async def test_the_first_write_measures_and_then_sets_what_was_asked(
    hass: HomeAssistant,
    sungrow_unit: MockModbusUnit,
    house,
    multiplies,
    held,
    minimum,
    maximum,
    mode,
    asked,
    factor,
) -> None:
    """The register holds what was asked, on either firmware.

    At fwitten the constant divide sends a tenth of the asked word, which that
    firmware stores as a tenth of the watts -- or refuses outright against an
    11880 W minimum. That is what this exists to stop.
    """
    entry = await _setup(
        hass, sungrow_unit, held=held, minimum=minimum, maximum=maximum, mode=mode
    )
    if mode == OFF:
        # The register ignores writes while limitation is off; the user
        # switches it on, as they would to use the limit at all.
        sungrow_unit.holding[MODE] = ON
    with (
        patch.object(
            type(sungrow_unit),
            "write_register",
            side_effect=_firmware(sungrow_unit, multiplies=multiplies),
        ),
        patch.object(hass.config_entries, "async_reload") as reload,
    ):
        await _set(hass, asked)
        await hass.async_block_till_done()

    assert entry.data[CONF_EXPORT_WRITE_SCALE] == factor, house
    assert sungrow_unit.holding[LIMIT] == asked, house
    assert float(hass.states.get(LIMIT_ENTITY).state) == asked
    # Storing the factor is an entry update, and the update listener reloads
    # on those -- which here would tear the entity down under its own write.
    reload.assert_not_called()


async def test_the_probe_lifts_the_mode_only_for_its_write_and_puts_it_back(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """bar12's case exactly: off, at the maximum, and left off afterwards."""
    entry = await _setup(
        hass, sungrow_unit, held=10000, minimum=0, maximum=10000, mode=OFF
    )
    writes: list[tuple[int, int]] = []
    firmware = _firmware(sungrow_unit, multiplies=True)

    async def recording(address: int, value: int) -> None:
        writes.append((address, value))
        await firmware(address, value)

    with patch.object(type(sungrow_unit), "write_register", side_effect=recording):
        await _set(hass, 10000)

    assert entry.data[CONF_EXPORT_WRITE_SCALE] == 10
    assert sungrow_unit.holding[MODE] == OFF
    # Lift, the probe's held word (refused), put the mode back, then the
    # user's own write -- which the inverter ignores, because the user has
    # left limitation off. The entity does not switch it on for them.
    assert writes == [(MODE, ON), (LIMIT, 10000), (MODE, OFF), (LIMIT, 1000)]
    assert sungrow_unit.holding[LIMIT] == 10000


async def test_a_measured_factor_is_used_without_asking_again(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """One probe per inverter: the second write is one write."""
    await _setup(
        hass,
        sungrow_unit,
        held=11880,
        minimum=11880,
        maximum=24990,
        mode=ON,
        data={CONF_EXPORT_WRITE_SCALE: 1},
    )
    writes: list[tuple[int, int]] = []
    firmware = _firmware(sungrow_unit, multiplies=False)

    async def recording(address: int, value: int) -> None:
        writes.append((address, value))
        await firmware(address, value)

    with patch.object(type(sungrow_unit), "write_register", side_effect=recording):
        await _set(hass, 20000)

    assert writes == [(LIMIT, 20000)]
    assert sungrow_unit.holding[LIMIT] == 20000


async def test_an_unanswered_probe_falls_back_to_ten_and_asks_next_time(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A zero-export house: no word tells the firmwares apart, so none is sent.

    The fallback is what every entry did before the probe existed, and it is
    not stored, so a later write -- with a held value that allows asking --
    gets a real answer.
    """
    entry = await _setup(hass, sungrow_unit, held=0, minimum=0, maximum=10000, mode=ON)
    writes: list[tuple[int, int]] = []
    firmware = _firmware(sungrow_unit, multiplies=True)

    async def recording(address: int, value: int) -> None:
        writes.append((address, value))
        await firmware(address, value)

    with patch.object(type(sungrow_unit), "write_register", side_effect=recording):
        await _set(hass, 5000)

    assert writes == [(LIMIT, 500)]
    assert sungrow_unit.holding[LIMIT] == 5000
    assert CONF_EXPORT_WRITE_SCALE not in entry.data


async def test_a_failed_read_writes_nothing_and_says_so(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Guessing a factor when the bounds cannot be read would be guessing at a house."""
    entry = await _setup(
        hass, sungrow_unit, held=10000, minimum=0, maximum=10000, mode=ON
    )
    writes: list[tuple[int, int]] = []

    async def recording(address: int, value: int) -> None:
        writes.append((address, value))

    with (
        patch(
            "sungrow_modbus.export_scale._word",
            side_effect=IllegalDataValueError(0x02),
        ),
        patch.object(type(sungrow_unit), "write_register", side_effect=recording),
        pytest.raises(HomeAssistantError, match="write scale"),
    ):
        await _set(hass, 5000)

    assert writes == []
    assert CONF_EXPORT_WRITE_SCALE not in entry.data


async def test_a_factor_from_other_firmware_is_measured_again(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """#763: a firmware update changed how this register is written.

    Stored as 1:1 on 95.03, running 95.14 now, and 95.14 multiplies: trusting
    the stored factor would set ten times what was asked.
    """
    entry = await _setup(
        hass,
        sungrow_unit,
        held=10000,
        minimum=0,
        maximum=10000,
        mode=ON,
        data={
            CONF_EXPORT_WRITE_SCALE: 1,
            CONF_EXPORT_WRITE_SCALE_FIRMWARE: "SAPPHIRE-H_01011.95.03",
        },
        firmware="SAPPHIRE-H_01011.95.14",
    )
    with (
        patch.object(
            type(sungrow_unit),
            "write_register",
            side_effect=_firmware(sungrow_unit, multiplies=True),
        ),
        patch.object(hass.config_entries, "async_reload") as reload,
    ):
        await _set(hass, 600)
        await hass.async_block_till_done()

    assert entry.data[CONF_EXPORT_WRITE_SCALE] == 10
    assert entry.data[CONF_EXPORT_WRITE_SCALE_FIRMWARE] == "SAPPHIRE-H_01011.95.14"
    assert sungrow_unit.holding[LIMIT] == 600
    reload.assert_not_called()


async def test_a_factor_stored_before_firmware_was_recorded_is_adopted(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """An entry from before this existed keeps its factor and gains a firmware."""
    entry = await _setup(
        hass,
        sungrow_unit,
        held=11880,
        minimum=11880,
        maximum=24990,
        mode=ON,
        data={CONF_EXPORT_WRITE_SCALE: 1},
        firmware="SAPPHIRE-H_01011.95.03",
    )
    writes: list[tuple[int, int]] = []
    firmware = _firmware(sungrow_unit, multiplies=False)

    async def recording(address: int, value: int) -> None:
        writes.append((address, value))
        await firmware(address, value)

    with (
        patch.object(type(sungrow_unit), "write_register", side_effect=recording),
        patch.object(hass.config_entries, "async_reload") as reload,
    ):
        await _set(hass, 20000)
        await hass.async_block_till_done()

    assert writes == [(LIMIT, 20000)]
    assert entry.data[CONF_EXPORT_WRITE_SCALE_FIRMWARE] == "SAPPHIRE-H_01011.95.03"
    reload.assert_not_called()
