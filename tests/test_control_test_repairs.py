"""The repair that puts back what an interrupted control test left behind.

This is the only path by which the integration writes a register outside an
explicit user action, and it stays inside that rule because confirming the
repair *is* the action. So what these tests pin is mostly about restraint:
setup raises the issue and does not fix it, the flow writes only once somebody
has confirmed, and a failure leaves the issue standing rather than quietly
marking the job done.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from modbus_connection import ModbusError
from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_MODE,
    CONF_UNIT_ID,
    DOMAIN,
    MODE_DIAGNOSTICS,
)
from custom_components.sungrow_modbus.control_test import _store, async_leftover
from custom_components.sungrow_modbus.repairs import async_create_fix_flow, issue_id
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

#: A minimum state of charge of 3 % is what the procedure writes, and 10 % is a
#: plausible thing for it to have been before. Left behind, this is a battery
#: that will discharge seven percent further than its owner asked it to.
LEFTOVER = {
    "taken_at": 1.0,
    "values": {"battery_min_soc": 10.0},
    "raw": {"battery_min_soc": 100},
    "bounds": {},
    "unreadable": {},
    "battery_ceiling": 5000,
    "stopped_at": None,
}


@pytest.fixture
def ready_unit(sungrow_unit: MockModbusUnit) -> MockModbusUnit:
    """Return a running inverter holding the test's value rather than its own."""
    sungrow_unit.input[12999] = 0x0000
    sungrow_unit.holding[13058] = 30  # 3.0 %, which is what a run would have left
    return sungrow_unit


async def _setup(hass: HomeAssistant, unit: MockModbusUnit) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**ENTRY_DATA, CONF_MODE: MODE_DIAGNOSTICS},
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def _with_leftover(
    hass: HomeAssistant, unit: MockModbusUnit, **overrides: Any
) -> MockConfigEntry:
    entry = await _setup(hass, unit)
    await _store(hass, entry).async_save({**LEFTOVER, **overrides})
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_setup_raises_the_issue_and_writes_nothing(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """The rule is that setup never writes a register, and it holds here too.

    Fixing this automatically would have been easy and would have been wrong:
    a Home Assistant restart is not somebody asking for their inverter to be
    written to.
    """
    entry = await _with_leftover(hass, ready_unit)

    assert ready_unit.holding[13058] == 30  # still the test's value
    issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id(entry))
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.WARNING


async def test_confirming_the_repair_puts_the_value_back(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """One confirmation, one write, and a read afterwards to prove it took."""
    entry = await _with_leftover(hass, ready_unit)
    flow = await async_create_fix_flow(
        hass, issue_id(entry), {"entry_id": entry.entry_id}
    )
    flow.hass = hass

    await flow.async_step_init()
    result = await flow.async_step_confirm({})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert ready_unit.holding[13058] == 100  # 10.0 %, the owner's value
    assert await async_leftover(hass, entry) is None
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id(entry)) is None


async def test_the_form_names_every_register_before_anything_is_written(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """Somebody confirming this is entitled to know what they are confirming."""
    entry = await _with_leftover(hass, ready_unit)
    flow = await async_create_fix_flow(
        hass, issue_id(entry), {"entry_id": entry.entry_id}
    )
    flow.hass = hass

    result = await flow.async_step_confirm()

    assert result["type"] is FlowResultType.FORM
    assert "battery_min_soc" in result["description_placeholders"]["registers"]
    assert ready_unit.holding[13058] == 30  # nothing written by showing the form


async def test_a_refused_write_leaves_the_repair_standing(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """The commonest cause is the one that caused the leftovers in the first place.

    Something else polling the inverter, or the inverter unreachable -- both
    things the owner can act on and this cannot. Marking the job done would
    hide a register that is still wrong.
    """
    entry = await _with_leftover(hass, ready_unit)
    ready_unit.fail_write(13058, ModbusError("the link went away"))
    flow = await async_create_fix_flow(
        hass, issue_id(entry), {"entry_id": entry.entry_id}
    )
    flow.hass = hass

    result = await flow.async_step_confirm({})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "restore_failed"
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id(entry)) is not None
    assert await async_leftover(hass, entry) is not None


async def test_a_run_that_stopped_the_inverter_says_so_first(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """The one consequence that costs generation rather than accuracy.

    A different issue key, so the title leads with the inverter rather than
    with a list of registers. It is the rarer case and the more expensive one.
    """
    ready_unit.input[12999] = 0x0008  # standby: it really is stopped

    entry = await _with_leftover(hass, ready_unit, stopped_at=1.0)

    issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id(entry))
    assert issue is not None
    assert issue.translation_key == "control_test_left_stopped"


async def test_fixing_that_one_starts_the_inverter_before_it_writes(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """Start the inverter first: a stopped one may not be listening."""

    def obey(event: Any) -> None:
        if event.address == 12999:
            ready_unit.input[12999] = 0x0000 if event.values[0] == 0xCF else 0x0008

    ready_unit.input[12999] = 0x0008
    ready_unit.on_write(obey)
    entry = await _with_leftover(hass, ready_unit, stopped_at=1.0)
    flow = await async_create_fix_flow(
        hass, issue_id(entry), {"entry_id": entry.entry_id}
    )
    flow.hass = hass

    result = await flow.async_step_confirm({})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert ready_unit.input[12999] == 0x0000  # running again
    assert ready_unit.holding[13058] == 100


async def test_an_already_tidy_entry_offers_a_plain_confirmation(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """Put back by a later run, or by hand. Confirming then just clears it."""
    from homeassistant.components.repairs import ConfirmRepairFlow

    entry = await _setup(hass, ready_unit)

    flow = await async_create_fix_flow(
        hass, issue_id(entry), {"entry_id": entry.entry_id}
    )

    assert isinstance(flow, ConfirmRepairFlow)
