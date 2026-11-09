"""A wallbox at its own address, found by the scan and set up as an entry.

Read over TLS at unit 248 and identified by **its own serial**: there is no
inverter beside it to borrow an identity from. Only the directly addressed
wallbox is looked for; the dongle's unit 3 stays the inverter entry's business.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from modbus_connection import ModbusError
from modbus_connection.mock import MockModbusConnection, MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_KIND,
    CONF_NETWORK,
    CONF_UNIT_ID,
    DOMAIN,
    KIND_WALLBOX,
    WALLBOX_TLS_PORT,
    WALLBOX_TLS_UNIT,
)
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .test_config_flow_search import _finish_sweep
from .test_wallbox_entities import WORDS, _wallbox_unit

#: A stand-in serial, in the registers a wallbox keeps it: input 21201-21206.
WALLBOX_SERIAL = "W123456789"
HOST = "192.168.1.60"
DATA = {
    CONF_HOST: HOST,
    CONF_PORT: WALLBOX_TLS_PORT,
    CONF_UNIT_ID: WALLBOX_TLS_UNIT,
    CONF_KIND: KIND_WALLBOX,
}


def _serial_words(text: str) -> dict[int, int]:
    raw = text.encode("ascii").ljust(12, b"\x00")
    return {21201 + i: int.from_bytes(raw[2 * i : 2 * i + 2], "big") for i in range(6)}


def _wallbox() -> MockModbusUnit:
    words = {**WORDS, "input": {**WORDS["input"], **_serial_words(WALLBOX_SERIAL)}}
    return _wallbox_unit(WALLBOX_TLS_UNIT, words)


class _Unit:
    def __init__(self, unit: MockModbusUnit) -> None:
        self._unit = unit

    async def __aenter__(self) -> MockModbusUnit:
        return self._unit

    async def __aexit__(self, *args: object) -> None:
        return None


@pytest.fixture(autouse=True)
def _open_the_alpha_gate(devices_mode_offered: None) -> None:
    """Open the gate on the devices path, which the alpha shuts."""


async def _scan(hass: HomeAssistant, wallbox_hosts: list[str]) -> dict:
    """Search with a sweep that finds `wallbox_hosts` on port 516 only."""

    async def sweep(network: str, *, port: int, **kwargs: object) -> list[str]:
        return wallbox_hosts if port == WALLBOX_TLS_PORT else []

    def temporary(hass, params, unit_id):
        if params.port != WALLBOX_TLS_PORT:
            raise ModbusError("not here")
        return _Unit(_wallbox())

    with (
        patch("custom_components.sungrow_modbus.config_flow.async_sweep", sweep),
        patch(
            "custom_components.sungrow_modbus.config_flow.async_hostname",
            return_value=None,
        ),
        patch(
            "custom_components.sungrow_modbus.config_flow.async_get_temporary_unit",
            side_effect=temporary,
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "setup_devices"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "search"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_NETWORK: "192.168.1.0/24"}
        )
        return await _finish_sweep(hass, result)


async def test_the_scan_offers_a_wallbox_at_its_own_address(
    hass: HomeAssistant,
) -> None:
    result = await _scan(hass, [HOST])

    assert result["step_id"] == "pick"
    values = [
        option["value"]
        for option in result["data_schema"].schema[CONF_HOST].config["options"]
    ]
    assert f"wallbox:{HOST}" in values


async def test_picking_it_makes_an_entry_of_its_own(hass: HomeAssistant) -> None:
    result = await _scan(hass, [HOST])
    with patch("custom_components.sungrow_modbus.async_setup_entry", return_value=True):
        created = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: f"wallbox:{HOST}"}
        )

    assert created["type"] is FlowResultType.CREATE_ENTRY
    assert created["data"] == DATA
    assert created["result"].unique_id == WALLBOX_SERIAL


async def test_a_wallbox_already_set_up_follows_its_new_address(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**DATA, CONF_HOST: "192.168.1.99"},
        unique_id=WALLBOX_SERIAL,
    )
    entry.add_to_hass(hass)
    result = await _scan(hass, [HOST])
    with patch("custom_components.sungrow_modbus.async_setup_entry", return_value=True):
        done = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: f"wallbox:{HOST}"}
        )

    assert done["type"] is FlowResultType.ABORT
    assert done["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == HOST


async def test_an_address_that_is_not_a_wallbox_is_not_offered(
    hass: HomeAssistant,
) -> None:
    """Port 516 open is not a wallbox: only a name over TLS makes one."""

    def temporary(hass, params, unit_id):
        raise ModbusError("a TLS service that is not a wallbox")

    async def sweep(network: str, *, port: int, **kwargs: object) -> list[str]:
        return [HOST] if port == WALLBOX_TLS_PORT else []

    with (
        patch("custom_components.sungrow_modbus.config_flow.async_sweep", sweep),
        patch(
            "custom_components.sungrow_modbus.config_flow.async_get_temporary_unit",
            side_effect=temporary,
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "setup_devices"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "search"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_NETWORK: "192.168.1.0/24"}
        )
        result = await _finish_sweep(hass, result)

    assert result["step_id"] == "nothing_found"


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id=WALLBOX_SERIAL)
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=_wallbox()
    ) as get_unit:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    # Over TLS at the wallbox's own address, never the inverter's endpoint.
    params = get_unit.call_args.args[2]
    assert (params.host, params.port) == (HOST, WALLBOX_TLS_PORT)
    assert get_unit.call_args.args[3] == WALLBOX_TLS_UNIT
    return entry


async def test_the_entry_is_the_wallbox_and_nothing_else(hass: HomeAssistant) -> None:
    entry = await _setup(hass)

    assert entry.state is ConfigEntryState.LOADED
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, f"{WALLBOX_SERIAL}-wallbox"), entry.entry_id
    )
    assert device is not None
    assert device.via_device_id is None
    assert device.serial_number == WALLBOX_SERIAL
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert entities
    readings = [e for e in entities if "_diagnosis_" not in e.unique_id]
    assert all(e.unique_id.startswith(f"{WALLBOX_SERIAL}_wallbox_") for e in readings)
    assert {e.domain for e in readings} <= {"sensor", "binary_sensor"}
    # Beside the readings, a read-only diagnosis and nothing that writes.
    diagnosis = {e.unique_id.removeprefix(f"{WALLBOX_SERIAL}_") for e in entities}
    assert {"diagnosis_start", "diagnosis_stop", "diagnosis_progress"} <= diagnosis
    assert not [e for e in entities if e.domain in ("number", "switch", "select")]


async def test_a_wallbox_with_no_readable_serial_is_not_ready(
    hass: HomeAssistant,
) -> None:
    unit = MockModbusConnection().for_unit(WALLBOX_TLS_UNIT)
    unit.input = {k: v for k, v in WORDS["input"].items() if not 21201 <= k <= 21206}
    unit.holding = dict(WORDS["holding"])
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id=WALLBOX_SERIAL)
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert not await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_it_has_no_options_to_change(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wallbox_entry"


async def test_its_diagnosis_reads_it_and_publishes_only_a_stand_in(
    hass: HomeAssistant,
) -> None:
    entry = await _setup(hass)
    runner = entry.runtime_data.diagnosis
    with patch(
        "custom_components.sungrow_modbus.device_diagnosis.persistent_notification"
    ) as notification:
        assert runner.async_start()
        await hass.async_block_till_done()

    state = runner.state
    assert state.error is None, state.error
    document = state.document
    assert document["document"] == "wallbox"
    section = document["wallbox"]
    assert section["path"] == "tls"
    assert section["readings"]["model_name"]["value"] == "AC22E-01"
    assert section["serial_anonymized_hashed"].startswith("anon-")
    # The serial's words are masked; the real one appears nowhere.
    assert WALLBOX_SERIAL not in json.dumps(document)
    assert notification.async_create.called

    from custom_components.sungrow_modbus.download import _filename

    assert _filename(document).startswith("ac22e01-")


async def test_its_diagnosis_cannot_be_made_to_write(hass: HomeAssistant) -> None:
    entry = await _setup(hass)

    assert not entry.runtime_data.diagnosis.async_start(capability_test=True)
