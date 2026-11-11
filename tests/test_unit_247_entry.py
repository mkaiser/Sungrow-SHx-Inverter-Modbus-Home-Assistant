"""An iHomeManager or a Logger, found by the search and set up for its diagnosis.

Neither had been read here when these were written, so the registers are
built the way Sungrow's documents describe them (as `tests/test_ihomemanager.py` and
`tests/test_logger.py` do). A simulator cannot produce a finding: these tests
check the wiring, never what a device answers.
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
    CONF_TLS,
    CONF_UNIT_ID,
    DOMAIN,
    KIND_IHOMEMANAGER,
    KIND_LOGGER,
)
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from sungrow_modbus.dump import IHOMEMANAGER_BANDS, LOGGER_BANDS

from .test_config_flow_search import _finish_sweep

HOST = "192.168.1.70"
#: Text where a serial could be, planted in a gap no field reads.
GAP_TEXT = [0x4131, 0x3233, 0x3435, 0x3637, 0x3839]


def _filled(inputs: dict[int, int], bands) -> dict[int, int]:
    for space, start, count, _why in bands:
        if space == "input":
            for address in range(start, start + count):
                inputs.setdefault(address, 0)
    return inputs


def _unit(kind: str) -> MockModbusUnit:
    unit = MockModbusConnection().for_unit(247)
    if kind == KIND_IHOMEMANAGER:
        # 8001-8002 low word first, as the unit measured on 2026-11-10 sends "AW0".
        inputs = {7999: 0x072A, 8000: 0x3000, 8001: 0x4157, 8002: 0x0200, 8003: 0x0100}
        inputs.update({8400 + i: w for i, w in enumerate(GAP_TEXT)})
        unit.input = _filled(inputs, IHOMEMANAGER_BANDS)
        unit.holding = {
            a: 0
            for space, start, count, _ in IHOMEMANAGER_BANDS
            if space == "holding"
            for a in range(start, start + count)
        }
    else:
        inputs = {7999: 0x0710, 8000: 0x4157, 8001: 0x3000, 8002: 0x0200, 8003: 0x0100}
        inputs.update({8039 + i: w for i, w in enumerate(GAP_TEXT)})
        unit.input = _filled(inputs, LOGGER_BANDS)
        unit.holding = dict.fromkeys(range(7999, 8199), 0)
    return unit


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


async def _scan(hass: HomeAssistant, answers: dict[int, str]) -> dict:
    """Search a network where HOST has `answers`: port to the kind at unit 247."""

    async def sweep(network: str, *, port: int, **kwargs: object) -> list[str]:
        return [HOST] if port in answers else []

    def temporary(hass, params, unit_id):
        kind = answers.get(params.port)
        if unit_id != 247 or kind is None:
            raise ModbusError("nothing here")
        return _Unit(_unit(kind))

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


def _values(result: dict) -> list[str]:
    return [
        option["value"]
        for option in result["data_schema"].schema[CONF_HOST].config["options"]
    ]


async def test_the_search_offers_an_ihomemanager_on_a_plain_port(
    hass: HomeAssistant,
) -> None:
    result = await _scan(hass, {504: KIND_IHOMEMANAGER})

    assert result["step_id"] == "pick"
    assert f"unit247:{HOST}:504" in _values(result)
    with patch("custom_components.sungrow_modbus.async_setup_entry", return_value=True):
        created = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: f"unit247:{HOST}:504"}
        )
    assert created["type"] is FlowResultType.CREATE_ENTRY
    assert created["data"] == {
        CONF_HOST: HOST,
        CONF_PORT: 504,
        CONF_UNIT_ID: 247,
        CONF_KIND: KIND_IHOMEMANAGER,
        CONF_TLS: False,
    }


async def test_the_search_offers_a_logger_over_tls_where_no_wallbox_answers(
    hass: HomeAssistant,
) -> None:
    """A current Logger1000 opens only 516, with TLS, like a wallbox does."""
    result = await _scan(hass, {516: KIND_LOGGER})

    assert result["step_id"] == "pick"
    assert f"unit247:{HOST}:516" in _values(result)
    with patch("custom_components.sungrow_modbus.async_setup_entry", return_value=True):
        created = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: f"unit247:{HOST}:516"}
        )
    assert created["data"][CONF_TLS] is True
    assert created["data"][CONF_KIND] == KIND_LOGGER


async def _setup(hass: HomeAssistant, kind: str, port: int = 502) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: HOST,
            CONF_PORT: port,
            CONF_UNIT_ID: 247,
            CONF_KIND: kind,
            CONF_TLS: False,
        },
        unique_id=f"{kind}-{HOST}-{port}",
        title=kind,
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=_unit(kind)
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_a_logger_entry_is_a_diagnosis_and_nothing_measured(
    hass: HomeAssistant,
) -> None:
    """An iHomeManager's readings are `tests/test_ihomemanager_entities.py`'s."""
    entry = await _setup(hass, KIND_LOGGER)

    assert entry.state is ConfigEntryState.LOADED
    keys = {
        e.unique_id.removeprefix(f"{entry.unique_id}_")
        for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    }
    assert keys == {
        "diagnosis_start",
        "diagnosis_stop",
        "diagnosis_progress",
        "diagnosis_step",
        "diagnosis_finished",
    }


@pytest.mark.parametrize("kind", [KIND_IHOMEMANAGER, KIND_LOGGER])
async def test_its_diagnosis_masks_text_that_could_be_a_serial(
    hass: HomeAssistant, kind: str
) -> None:
    entry = await _setup(hass, kind)
    runner = entry.runtime_data.diagnosis
    with patch(
        "custom_components.sungrow_modbus.device_diagnosis.persistent_notification"
    ):
        assert runner.async_start()
        await hass.async_block_till_done()

    assert runner.state.error is None, runner.state.error
    document = runner.state.document
    assert document["document"] == kind
    assert document[kind]["masked_text"], "the planted text was not masked"
    assert "A123456789" not in json.dumps(document)

    from custom_components.sungrow_modbus.download import _filename

    assert _filename(document).endswith("port502.json")


async def test_a_device_that_no_longer_answers_waits(hass: HomeAssistant) -> None:
    silent = MockModbusConnection().for_unit(247)
    silent.input = {}
    silent.holding = {}
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: HOST,
            CONF_PORT: 502,
            CONF_UNIT_ID: 247,
            CONF_KIND: KIND_LOGGER,
            CONF_TLS: False,
        },
        unique_id=f"logger-{HOST}-502",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=silent):
        assert not await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_it_has_no_options(hass: HomeAssistant) -> None:
    entry = await _setup(hass, KIND_IHOMEMANAGER)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unit_247_entry"
