"""The owner's controls and a capability test never write at the same time.

`custom_components/sungrow_modbus/write_owner.py`: while a run holds an entry's
controls they refuse before a byte is sent, the binary sensor says so, a run
holds them from before its snapshot until its restore, auto repeat waits after
the owner wrote, and the owner's write replaces a leftover snapshot's entry.
"""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

from modbus_connection.mock import MockModbusConnection, MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus.const import CONF_UNIT_ID, DOMAIN
from custom_components.sungrow_modbus.write_owner import (
    EV_CHARGER,
    OWNER_QUIET,
    OWNER_QUIET_EV,
    async_test_owns_writes,
    holder,
    owner_quiet_until,
)
from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN, SERVICE_TURN_OFF
from homeassistant.const import ATTR_ENTITY_ID, CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.util import dt as dt_util
from sungrow_modbus.hybrid_inverter import ev_charger as ev

from .conftest import SERIAL, encode_string
from .test_wallbox_entities import _wallbox_unit

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

#: Protocol address of register 13250, the inverter's firmware.
INVERTER_FIRMWARE_ADDRESS = 13249
WATCHED = "SAPPHIRE-H_B001.V000.P022"

MIN_SOC = "number.sh10rt_battery_min_soc"
EXPORT_LIMIT = "number.sh10rt_feed_in_limit"

#: Protocol addresses of 13059 and 13058, minimum and maximum SoC.
MIN_SOC_ADDRESS = 13058
MAX_SOC_ADDRESS = 13057

WALLBOX_SERIAL = "A987654321"
RUN_BY = "AC22E-01"


@pytest.fixture
async def entry(hass: HomeAssistant, sungrow_unit: MockModbusUnit) -> MockConfigEntry:
    """Set up an ordinary entry on watched firmware: SoC limits, EV controls."""
    sungrow_unit.input[12999] = 0x0000  # running
    sungrow_unit.input[INVERTER_FIRMWARE_ADDRESS] = encode_string(WATCHED, 15)
    sungrow_unit.holding[MIN_SOC_ADDRESS] = 100
    sungrow_unit.holding[MAX_SOC_ADDRESS] = 900
    sungrow_unit.holding[ev.CHARGING] = ev.ON
    sungrow_unit.holding[ev.MODE] = ev.FAST
    sungrow_unit.holding[ev.USER_CURRENT] = 160
    sungrow_unit.holding[ev.GRID_SURPLUS] = ev.OFF
    # The feed-in limit's bounds, input 5622 and 5623, in tens of watts.
    sungrow_unit.input[5621] = 0
    sungrow_unit.input[5622] = 1000
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    empty = MockModbusConnection().for_unit(9)
    empty.input = {}
    empty.holding = {}

    # A wallbox at unit 3, because the EV charger controls ask for one on the
    # bus: 33541 reading a named mode is the block's factory state at houses
    # with none (wiki: device-wallbox).
    def units(_hass, _entry, _params, unit_id):
        if unit_id == 1:
            return sungrow_unit
        return _wallbox_unit(unit_id) if unit_id == 3 else empty

    with patch("custom_components.sungrow_modbus.async_get_unit", side_effect=units):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def _entity_id(hass: HomeAssistant, domain: str, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(
        domain, DOMAIN, f"{SERIAL}_{key}"
    )
    assert entity_id is not None, f"{domain}.{key}"
    return entity_id


async def _set(hass: HomeAssistant, entity_id: str, value: float) -> None:
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: value},
        blocking=True,
    )


def _writes(unit: MockModbusUnit) -> list[Any]:
    """Collect every write the unit receives from now on."""
    seen: list[Any] = []
    unit.on_write(seen.append)
    return seen


# --- the controls refuse while a run holds them -------------------------------


async def test_every_kind_of_control_refuses_while_a_run_holds_them(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    """A number, a switch, a select and the export limit: nothing reaches the wire."""
    seen = _writes(sungrow_unit)
    calls = [
        (NUMBER_DOMAIN, SERVICE_SET_VALUE, MIN_SOC, {ATTR_VALUE: 20}),
        (NUMBER_DOMAIN, SERVICE_SET_VALUE, EXPORT_LIMIT, {ATTR_VALUE: 500}),
        (
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            _entity_id(hass, "switch", "ev_charger_charging"),
            {},
        ),
        (
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            _entity_id(hass, "select", "ev_charger_mode"),
            {ATTR_OPTION: "pv_surplus"},
        ),
    ]
    async with async_test_owns_writes([entry], RUN_BY):
        for domain, service, entity_id, data in calls:
            with pytest.raises(ServiceValidationError) as raised:
                await hass.services.async_call(
                    domain,
                    service,
                    {ATTR_ENTITY_ID: entity_id, **data},
                    blocking=True,
                )
            assert raised.value.translation_key == "test_has_link"
            assert raised.value.translation_placeholders["by"] == RUN_BY
            assert raised.value.translation_placeholders["target"] == entity_id

    assert seen == []
    assert sungrow_unit.holding[MIN_SOC_ADDRESS] == 100
    assert sungrow_unit.holding[ev.CHARGING] == ev.ON
    assert sungrow_unit.holding[ev.MODE] == ev.FAST


async def test_the_controls_stay_available_while_held(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """Home Assistant drops a call to an unavailable entity without a word."""
    async with async_test_owns_writes([entry], RUN_BY):
        assert hass.states.get(MIN_SOC).state != "unavailable"


async def test_they_write_again_once_the_run_lets_go(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    async with async_test_owns_writes([entry], RUN_BY):
        pass
    await _set(hass, MIN_SOC, 20)
    assert sungrow_unit.holding[MIN_SOC_ADDRESS] == 200
    assert holder(entry.runtime_data) is None


async def test_start_and_stop_refuse_while_held(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    """A run may have stopped the inverter itself; its restore starts it."""
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, SERIAL), entry.entry_id
    )
    assert device is not None
    seen = _writes(sungrow_unit)
    async with async_test_owns_writes([entry], RUN_BY):
        with pytest.raises(ServiceValidationError) as raised:
            await hass.services.async_call(
                DOMAIN, "stop_inverter", {"device_id": device.id}, blocking=True
            )
    assert raised.value.translation_key == "test_has_link"
    assert seen == []


async def test_one_run_letting_go_does_not_release_another(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    async with async_test_owns_writes([entry], "first"):
        async with async_test_owns_writes([entry], "second"):
            pass
        owner = holder(entry.runtime_data)
        assert owner is not None
        assert owner.by == "first"
    assert holder(entry.runtime_data) is None


async def test_the_binary_sensor_shows_the_hold(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    entity_id = _entity_id(hass, "binary_sensor", "controls_held_by_test")
    assert hass.states.get(entity_id).state == "off"
    assert er.async_get(hass).async_get(entity_id).entity_category == "diagnostic"

    async with async_test_owns_writes([entry], RUN_BY):
        await hass.async_block_till_done()
        state = hass.states.get(entity_id)
        assert state.state == "on"
        assert state.attributes["held_by"] == RUN_BY

    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "off"


# --- a run holds them ---------------------------------------------------------


async def test_the_capability_test_holds_the_controls_for_its_whole_run(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """From before the snapshot (inside the library's run) to the restore."""
    from custom_components.sungrow_modbus.capability_test import CapabilityTestRunner

    seen: list[Any] = []

    class Test:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        def request_stop(self) -> None:
            pass

        async def async_run(self) -> Any:
            seen.append(holder(entry.runtime_data))
            with pytest.raises(ServiceValidationError):
                await _set(hass, MIN_SOC, 20)
            return SimpleNamespace(not_restored=())

    with (
        patch("custom_components.sungrow_modbus.capability_test.CapabilityTest", Test),
        patch(
            "custom_components.sungrow_modbus.capability_test.document",
            return_value={},
        ),
    ):
        await CapabilityTestRunner(hass, entry).async_run()

    assert seen[0] is not None
    assert seen[0].by == "SH10RT"
    assert holder(entry.runtime_data) is None


async def test_a_managed_wallbox_run_holds_the_inverters_controls(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """The EV charger block it writes is the inverter entry's."""
    from custom_components.sungrow_modbus import wallbox_capability_test as wbt

    wallbox_entry = MockConfigEntry(
        domain=DOMAIN, data={}, unique_id=WALLBOX_SERIAL, title=RUN_BY
    )
    wallbox_entry.add_to_hass(hass)
    wallbox_entry.runtime_data = SimpleNamespace(
        wallbox=SimpleNamespace(device=SimpleNamespace(field=lambda _name: None)),
        write_owners=[],
        diagnosis=None,
    )
    seen: list[Any] = []

    class Managed:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        async def async_run(self) -> Any:
            seen.append(holder(entry.runtime_data))
            seen.append(holder(wallbox_entry.runtime_data))
            return SimpleNamespace(restored=True)

    with (
        patch.object(wbt.mt, "ManagedWallboxTest", Managed),
        patch.object(wbt.ledger, "managed_block", return_value={}),
    ):
        await wbt.WallboxTestRunner(hass, wallbox_entry)._async_run_managed(entry, None)

    assert [owner.by for owner in seen] == [RUN_BY, RUN_BY]
    assert holder(entry.runtime_data) is None


# --- auto repeat waits after the owner wrote ------------------------------------


async def test_a_write_is_recorded_per_component(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    await _set(hass, MIN_SOC, 20)
    runtime = entry.runtime_data
    assert owner_quiet_until(runtime, OWNER_QUIET) is not None
    # Not the EV charger's: a wallbox run need not wait for a SoC limit.
    assert owner_quiet_until(runtime, OWNER_QUIET_EV, (EV_CHARGER,)) is None

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: _entity_id(hass, "switch", "ev_charger_charging")},
        blocking=True,
    )
    assert owner_quiet_until(runtime, OWNER_QUIET_EV, (EV_CHARGER,)) is not None


def test_the_quiet_time_runs_out() -> None:
    now = dt_util.utcnow()
    runtime = SimpleNamespace(owner_writes={EV_CHARGER: now})
    assert owner_quiet_until(runtime, OWNER_QUIET, now=now) == now + OWNER_QUIET
    later = now + OWNER_QUIET + timedelta(seconds=1)
    assert owner_quiet_until(runtime, OWNER_QUIET, now=later) is None


async def test_auto_repeat_waits_after_the_owner_changed_a_control(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    await _set(hass, MIN_SOC, 20)
    continuous = entry.runtime_data.diagnosis.continuous
    continuous.started_at = dt_util.utcnow()

    started = continuous._inverter_tick(dt_util.utcnow(), None, [("check", "need")])

    assert started is False
    assert continuous.waiting.startswith("the owner changed a control")
    assert not entry.runtime_data.diagnosis.state.running


# --- the owner's write replaces a leftover snapshot's entry ---------------------


async def _leave_snapshot(
    hass: HomeAssistant, entry: MockConfigEntry, values: dict[str, float]
) -> None:
    from custom_components.sungrow_modbus.capability_test import _store

    await _store(hass, entry).async_save(
        {
            "taken_at": 1.0,
            "values": values,
            "raw": {name: int(value * 10) for name, value in values.items()},
            "bounds": {},
            "unreadable": {},
            "battery_ceiling": 5000,
            "stopped_at": None,
            "touched": list(values),
        }
    )


async def test_an_owner_write_drops_that_field_from_a_leftover(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """The next restore must not write the old minimum back over the owner's."""
    from custom_components.sungrow_modbus.capability_test import async_leftover
    from custom_components.sungrow_modbus.repairs import issue_id

    await _leave_snapshot(
        hass, entry, {"battery_min_soc": 5.0, "battery_max_soc": 95.0}
    )

    await _set(hass, MIN_SOC, 20)

    snapshot = await async_leftover(hass, entry)
    assert snapshot is not None
    assert set(snapshot.values) == {"battery_max_soc"}
    assert set(snapshot.raw) == {"battery_max_soc"}
    assert snapshot.touched == ["battery_max_soc"]
    issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id(entry))
    assert issue is not None
    assert "battery_min_soc" not in issue.translation_placeholders["registers"]


async def test_a_leftover_with_nothing_left_is_forgotten(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    from custom_components.sungrow_modbus.capability_test import async_leftover
    from custom_components.sungrow_modbus.repairs import async_raise, issue_id

    await _leave_snapshot(hass, entry, {"battery_min_soc": 5.0})
    snapshot = await async_leftover(hass, entry)
    assert snapshot is not None
    async_raise(hass, entry, snapshot)

    await _set(hass, MIN_SOC, 20)

    assert await async_leftover(hass, entry) is None
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id(entry)) is None


async def test_an_untouched_field_stays_in_the_leftover(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    from custom_components.sungrow_modbus.capability_test import async_leftover

    await _leave_snapshot(hass, entry, {"battery_max_soc": 95.0})

    await _set(hass, MIN_SOC, 20)

    snapshot = await async_leftover(hass, entry)
    assert snapshot is not None
    assert set(snapshot.values) == {"battery_max_soc"}


async def test_an_owner_write_takes_its_word_into_a_managed_leftover(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """A managed restore writes all three words; the owner's are the ones to keep.

    Charging switched off by the owner also means the restore must not start
    the charge again.
    """
    from custom_components.sungrow_modbus.wallbox_capability_test import (
        async_keep_leftover,
        async_leftover,
    )

    wallbox_entry = MockConfigEntry(
        domain=DOMAIN, data={}, unique_id=WALLBOX_SERIAL, title=RUN_BY
    )
    wallbox_entry.add_to_hass(hass)
    wallbox_entry.runtime_data = SimpleNamespace()
    entry.runtime_data.wallbox_elsewhere = WALLBOX_SERIAL
    await async_keep_leftover(
        hass,
        wallbox_entry,
        {
            "raw": {ev.CHARGING: ev.ON, ev.MODE: ev.USER_DEFINED, ev.USER_CURRENT: 80},
            "touched": [ev.MODE],
            "managed": True,
            "charging_at_start": True,
        },
    )

    with patch(
        "custom_components.sungrow_modbus.repairs.async_raise_wallbox", AsyncMock()
    ) as raised:
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: _entity_id(hass, "switch", "ev_charger_charging")},
            blocking=True,
        )
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: _entity_id(hass, "select", "ev_charger_mode"),
                ATTR_OPTION: "pv_surplus",
            },
            blocking=True,
        )

    leftover = await async_leftover(hass, wallbox_entry)
    assert leftover is not None
    assert leftover["raw"][ev.CHARGING] == ev.OFF
    assert leftover["raw"][ev.MODE] == ev.PV_SURPLUS
    assert leftover["raw"][ev.USER_CURRENT] == 80
    assert leftover["charging_at_start"] is False
    assert raised.await_count == 2
