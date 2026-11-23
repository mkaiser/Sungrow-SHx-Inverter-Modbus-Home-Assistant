"""The results command: administrators only, and no address in its answer."""

from __future__ import annotations

from dataclasses import replace
from typing import Any
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant.common import MockConfigEntry, MockUser

from custom_components.sungrow_modbus.const import CONF_UNIT_ID, DOMAIN
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component

from .conftest import SERIAL

HOST = "192.0.2.7"


async def _setup(hass: HomeAssistant, unit: MockModbusUnit) -> MockConfigEntry:
    assert await async_setup_component(hass, "websocket_api", {})
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST, CONF_PORT: 502, CONF_UNIT_ID: 1},
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def _device(hass: HomeAssistant, entry_id: str) -> str:
    registry = dr.async_get(hass)
    device = next(
        device
        for device in dr.async_entries_for_config_entry(registry, entry_id)
        if (DOMAIN, SERIAL) in device.identifiers
    )
    return device.id


async def _ask(client: Any, device_id: str) -> dict[str, Any]:
    await client.send_json_auto_id(
        {"type": "sungrow_modbus/diagnosis/results", "device_id": device_id}
    )
    answer: dict[str, Any] = await client.receive_json()
    return answer


async def test_an_entry_with_nothing_kept_answers(
    hass: HomeAssistant, hass_ws_client: Any, sungrow_unit: MockModbusUnit
) -> None:
    entry = await _setup(hass, sungrow_unit)
    answer = await _ask(await hass_ws_client(hass), _device(hass, entry.entry_id))
    assert answer["success"]
    assert answer["result"]["runs"] == []
    assert answer["result"]["document_url"] is None


async def test_the_address_and_the_serial_stay_out(
    hass: HomeAssistant, hass_ws_client: Any, sungrow_unit: MockModbusUnit
) -> None:
    entry = await _setup(hass, sungrow_unit)
    runner = entry.runtime_data.diagnosis
    kept = {
        "summary": {
            "forced charge": {
                "kind": "effect",
                "verdict": None,
                "run": 0,
                "read_at": None,
                "established": False,
            }
        },
        "still_missing": [
            {"name": "forced charge", "kind": "effect", "why": f"lost {HOST}:502"}
        ],
        "runs": [{"read_at": None, "outcome": 1, "outcome_means": f"no {HOST}"}],
    }
    runner.state = replace(runner.state, capability_test=kept)
    answer = await _ask(await hass_ws_client(hass), _device(hass, entry.entry_id))
    text = str(answer["result"])
    assert HOST not in text
    assert SERIAL not in text
    row = next(r for r in answer["result"]["rows"] if r["name"] == "forced charge")
    assert row["waits_for"] == "lost the device:502"


async def test_a_plain_user_is_refused(
    hass: HomeAssistant,
    hass_ws_client: Any,
    hass_read_only_access_token: str,
    sungrow_unit: MockModbusUnit,
    hass_read_only_user: MockUser,
) -> None:
    entry = await _setup(hass, sungrow_unit)
    answer = await _ask(
        await hass_ws_client(hass, hass_read_only_access_token),
        _device(hass, entry.entry_id),
    )
    assert not answer["success"]
    assert answer["error"]["code"] == "unauthorized"


async def test_another_device_is_not_found(
    hass: HomeAssistant, hass_ws_client: Any, sungrow_unit: MockModbusUnit
) -> None:
    await _setup(hass, sungrow_unit)
    answer = await _ask(await hass_ws_client(hass), "no such device")
    assert answer["error"]["code"] == "not_found"
