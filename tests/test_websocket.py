"""The results command: administrators only, and no address in its answer."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant.common import MockConfigEntry, MockUser

from custom_components.sungrow_modbus import diagnosis_settings
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


async def _settings(
    client: Any, device_id: str, part: str | None = None, **values: Any
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "type": "sungrow_modbus/diagnosis/settings",
        "device_id": device_id,
    }
    if part is not None:
        message["type"] += "/save"
        message |= {"part": part, "values": values}
    await client.send_json_auto_id(message)
    answer: dict[str, Any] = await client.receive_json()
    return answer


def _values(view: dict[str, Any], part: str) -> dict[str, Any]:
    return {row["key"]: row["value"] for row in view[part]}


async def test_settings_are_the_options_and_saving_does_not_reload(
    hass: HomeAssistant, hass_ws_client: Any, sungrow_unit: MockModbusUnit
) -> None:
    entry = await _setup(hass, sungrow_unit)
    runtime = entry.runtime_data
    client = await hass_ws_client(hass)
    device = _device(hass, entry.entry_id)
    view = (await _settings(client, device))["result"]
    assert _values(view, "tests")["capability_test_restart"] is True
    # Unanswered, nothing of the address is published.
    assert _values(view, "answers")["publish_address"] is False

    saved = await _settings(client, device, "tests", capability_test_restart=False)
    assert _values(saved["result"], "tests")["capability_test_restart"] is False
    await _settings(client, device, "answers", reporter="me", diagnosis_proxy="no")
    await _settings(client, device, "answers", diagnosis_proxy=None)
    await hass.async_block_till_done()
    assert entry.options["capability_test_restart"] is False
    assert entry.options["reporter"] == "me"
    assert "diagnosis_proxy" not in entry.options
    assert entry.runtime_data is runtime


async def test_settings_say_what_an_extended_test_misses(
    hass: HomeAssistant, hass_ws_client: Any, sungrow_unit: MockModbusUnit
) -> None:
    entry = await _setup(hass, sungrow_unit)
    client = await hass_ws_client(hass)
    device = _device(hass, entry.entry_id)
    view = (await _settings(client, device))["result"]
    keys = ["diagnosis_transport", "diagnosis_proxy", "diagnosis_other_inverter"]
    assert view["missing"] == {
        "entry_id": entry.entry_id,
        "title": "SH10RT",
        "keys": keys,
    }
    assert view["entry_id"] == entry.entry_id
    required = [row["key"] for row in view["answers"] if row.get("required")]
    assert required == keys
    saved = await _settings(
        client,
        device,
        "answers",
        diagnosis_transport="unsure",
        diagnosis_proxy="unknown",
        diagnosis_other_inverter="no",
    )
    assert saved["result"]["missing"]["keys"] == []


async def test_settings_refuse_what_is_not_theirs(
    hass: HomeAssistant, hass_ws_client: Any, sungrow_unit: MockModbusUnit
) -> None:
    entry = await _setup(hass, sungrow_unit)
    client = await hass_ws_client(hass)
    device = _device(hass, entry.entry_id)
    for part, values in (
        # The answers are not behind the lock.
        ("answers", {"capability_test_restart": False}),
        ("tests", {"permissions": {}}),
        ("tests", {"capability_test_restart": "yes"}),
        ("answers", {"diagnosis_proxy": "maybe"}),
        ("answers", {"reporter": "x" * 5000}),
    ):
        answer = await _settings(client, device, part, **values)
        assert answer["error"]["code"] == "invalid_format", values
    runner = entry.runtime_data.diagnosis
    runner.state = replace(runner.state, running=True)
    answer = await _settings(client, device, "answers", reporter="me")
    assert answer["error"]["code"] == "not_allowed"
    assert not entry.options


async def test_settings_are_for_administrators(
    hass: HomeAssistant,
    hass_ws_client: Any,
    sungrow_unit: MockModbusUnit,
    hass_read_only_access_token: str,
) -> None:
    entry = await _setup(hass, sungrow_unit)
    client = await hass_ws_client(hass, hass_read_only_access_token)
    device = _device(hass, entry.entry_id)
    for answer in (
        await _settings(client, device),
        await _settings(client, device, "answers", reporter="me"),
    ):
        assert answer["error"]["code"] == "unauthorized"


async def test_every_setting_has_a_text(hass: HomeAssistant) -> None:
    """The card shows Configure's own texts, by these paths."""
    root = Path(__file__).parent.parent / "custom_components" / "sungrow_modbus"
    options = json.loads((root / "translations" / "en.json").read_text())["options"]
    for step, kind in (("init", None), ("wallbox", "wallbox")):
        entry = MockConfigEntry(domain=DOMAIN, data={"kind": kind} if kind else {})
        for part, section in (("answers", "diagnosis"), ("tests", "capability_test")):
            texts = options["step"][step]["sections"][section]["data"]
            for key in diagnosis_settings.parts(entry)[part]:
                if key == "diagnosis_other_inverter_detail":
                    assert key in options["step"]["other_inverter"]["data"]
                else:
                    assert key in texts, (step, key)
