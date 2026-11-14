"""A wallbox test that did not put everything back becomes a repair.

On 2026-11-13 a run at gerd's left the wallbox disabled and its mileage
changed, and Home Assistant said so only in its log. Now it raises an issue
naming each setting, its value and where the app sets it; the fix writes it
back and checks the house, not only the word (wiki:
gerd-wallbox-capability-test-2026-11-13).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from custom_components.sungrow_modbus import repairs, wallbox_capability_test as wbt
from custom_components.sungrow_modbus.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from sungrow_modbus.hybrid_inverter import ev_charger as ev
from sungrow_modbus.wallbox import capability_test as wct

from .test_capability_test_ha import InstantClock
from .test_wallbox_capability_test_ha import _setup, _wallbox


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pass every wait at once, in the library's own default clock."""
    monkeypatch.setattr(wct, "RealClock", InstantClock)


def _leftover(**raw: int) -> dict[str, Any]:
    words = {getattr(wct, name): word for name, word in raw.items()}
    return {
        "raw": {str(address): word for address, word in words.items()},
        "touched": list(words),
        "managed": False,
        "charging_at_start": False,
    }


async def _reload_with(hass: HomeAssistant, entry: Any, data: dict[str, Any]) -> None:
    """Leave a snapshot behind, as a run cut off by a restart does."""
    await wbt.snapshot_store(hass, entry).async_save(data)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit",
        return_value=entry.runtime_data.wallbox.device._unit,
    ):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()


def _issue(hass: HomeAssistant, entry: Any) -> ir.IssueEntry | None:
    return ir.async_get(hass).async_get_issue(DOMAIN, repairs.wallbox_issue_id(entry))


async def test_a_wallbox_left_disabled_is_an_error_naming_the_apps_switch(
    hass: HomeAssistant,
) -> None:
    wallbox = _wallbox(charging=False)
    entry = await _setup(hass, wallbox)
    wallbox.holding[wct.ENABLED] = 0
    wallbox.input[wct.CHARGING_STATUS_ADDRESS] = wct.DISABLED_STATUS

    await _reload_with(hass, entry, _leftover(ENABLED=1, OUTPUT_CURRENT=320))

    issue = _issue(hass, entry)
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.ERROR
    assert issue.is_fixable
    settings = issue.translation_placeholders["settings"]
    assert "Ladegerät aktivieren" in settings
    assert "32 A" in settings


async def test_a_changed_setpoint_alone_is_a_warning(hass: HomeAssistant) -> None:
    wallbox = _wallbox(charging=False)
    entry = await _setup(hass, wallbox)

    await _reload_with(hass, entry, _leftover(OUTPUT_CURRENT=160))

    issue = _issue(hass, entry)
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.WARNING


async def test_no_leftover_no_issue(hass: HomeAssistant) -> None:
    entry = await _setup(hass, _wallbox(charging=False))
    assert _issue(hass, entry) is None


async def test_the_fix_puts_it_back_and_takes_the_issue_down(
    hass: HomeAssistant,
) -> None:
    wallbox = _wallbox(charging=False)
    entry = await _setup(hass, wallbox)
    wallbox.holding[wct.PHASE_SETPOINT] = 1
    await _reload_with(hass, entry, _leftover(PHASE_SETPOINT=0))
    assert _issue(hass, entry) is not None

    assert await wbt.async_restore_leftover(hass, entry)

    assert wallbox.holding[wct.PHASE_SETPOINT] == 0
    assert _issue(hass, entry) is None
    assert await wbt.async_leftover(hass, entry) is None


async def test_a_wallbox_still_disabled_is_not_called_restored(
    hass: HomeAssistant,
) -> None:
    """The word may read back as written; the house is judged by the status."""
    wallbox = _wallbox(charging=False)
    entry = await _setup(hass, wallbox)
    wallbox.holding[wct.ENABLED] = 0
    wallbox.input[wct.CHARGING_STATUS_ADDRESS] = wct.DISABLED_STATUS
    await _reload_with(hass, entry, _leftover(ENABLED=1))

    assert not await wbt.async_restore_leftover(hass, entry)

    assert _issue(hass, entry) is not None
    assert await wbt.async_leftover(hass, entry) is not None


async def test_the_fix_flow_says_what_to_do_by_hand_when_it_cannot(
    hass: HomeAssistant,
) -> None:
    wallbox = _wallbox(charging=False)
    entry = await _setup(hass, wallbox)
    wallbox.holding[wct.ENABLED] = 0
    wallbox.input[wct.CHARGING_STATUS_ADDRESS] = wct.DISABLED_STATUS
    await _reload_with(hass, entry, _leftover(ENABLED=1))

    flow = await repairs.async_create_fix_flow(
        hass, repairs.wallbox_issue_id(entry), {"entry_id": entry.entry_id}
    )
    assert isinstance(flow, repairs.WallboxTestRepairFlow)
    flow.hass = hass
    shown = await flow.async_step_init()
    assert "Ladegerät aktivieren" in shown["description_placeholders"]["settings"]
    result = await flow.async_step_confirm({})

    assert result["type"] == "abort"
    assert result["reason"] == "restore_failed"
    assert "app" in result["description_placeholders"]["error"]


async def test_a_managed_leftover_names_the_inverters_settings(
    hass: HomeAssistant,
) -> None:
    lines = await repairs.async_wallbox_settings(
        hass,
        {
            "raw": {ev.CHARGING: ev.ON, ev.MODE: ev.FAST, ev.USER_CURRENT: 100},
            "touched": [ev.CHARGING, ev.MODE, ev.USER_CURRENT],
        },
    )
    assert "charge on" in lines
    assert "fast charge" in lines
    assert "10 A" in lines
