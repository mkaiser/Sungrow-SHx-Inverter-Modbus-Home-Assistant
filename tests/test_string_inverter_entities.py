"""An SG string inverter as a Home Assistant entry: set up, read, surveyed.

Read only, by decision: no control test button, and both writing actions
refuse. Its sensors exist only where its field read a value, because tracker
and phase counts differ by model. No SG has been surveyed, so the words are
Sungrow's string-inverter protocol V1.1.53 as an SG5.0RS would answer it.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from modbus_connection import IllegalDataAddressError
from modbus_connection.mock import MockModbusConnection, MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_KIND,
    CONF_MODE,
    CONF_UNIT_ID,
    DOMAIN,
    KIND_STRING_INVERTER,
    MODE_DEVICES,
    MODE_DIAGNOSTICS,
)
from custom_components.sungrow_modbus.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.sungrow_modbus.string_inverter_descriptions import (
    STRING_INVERTER_DESCRIPTIONS,
)
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from sungrow_modbus import SungrowStringInverter

from .conftest import SERIAL, encode_string

ENTRY_DATA = {
    CONF_HOST: "127.0.0.1",
    CONF_PORT: 5020,
    CONF_UNIT_ID: 1,
    CONF_KIND: KIND_STRING_INVERTER,
}

#: An SG5.0RS at midday, by protocol address: two trackers, one phase.
SG_INPUT: dict[int, int] = {
    **dict(enumerate(encode_string("ARM_TEST_V1", 15), start=4953)),
    **dict(enumerate(encode_string("DSP_TEST_V1", 15), start=4968)),
    **dict(enumerate(encode_string(SERIAL, 10), start=4989)),
    4999: 0x2606,  # SG5.0RS
    5000: 50,  # 5.0 kW
    5001: 0,  # single phase
    5002: 123,
    5003: 4567,
    5004: 0,
    5007: 412,
    5010: 3601,  # MPPT1 360.1 V
    5011: 52,
    5012: 3550,  # MPPT2
    5013: 48,
    5014: 0xFFFF,  # no MPPT3
    5015: 0xFFFF,
    5016: 1890,
    5017: 0,
    5018: 2301,  # phase A
    5019: 0xFFFF,  # no phase B or C
    5020: 0xFFFF,
    5021: 80,
    5022: 0xFFFF,
    5023: 0xFFFF,
    5030: 1850,
    5031: 0,
    5034: 999,
    5035: 500,
    5037: 0x0000,
}


def _sg(words: dict[int, int] = SG_INPUT) -> MockModbusUnit:
    """Return an SG answering its realtime and identity blocks, refusing the rest.

    Refused, as an RS refuses the meter block the source calls undocumented
    on it: a block that refuses gets no entities, and a refusal is an answer.
    """
    unit = MockModbusConnection().for_unit(1)
    unit.input = dict(words)
    unit.holding = {}
    real = unit.read_input_registers

    async def answer(address: int, count: int) -> list[int]:
        unmapped = any(a not in words for a in range(address, address + count))
        if unmapped and not 4949 <= address < 5038:
            raise IllegalDataAddressError("illegal data address")
        return list(await real(address, count))

    async def refuse(address: int, count: int) -> list[int]:
        raise IllegalDataAddressError("illegal data address")

    unit.read_input_registers = answer  # type: ignore[method-assign]
    unit.read_holding_registers = refuse  # type: ignore[method-assign]
    return unit


async def _setup(
    hass: HomeAssistant, mode: str = MODE_DEVICES, words: dict[int, int] = SG_INPUT
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**ENTRY_DATA, CONF_MODE: mode},
        unique_id=SERIAL,
        title="SG5.0RS",
    )
    entry.add_to_hass(hass)
    unit = _sg(words)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def _unique_ids(hass: HomeAssistant, entry: MockConfigEntry) -> set[str]:
    registry = er.async_get(hass)
    return {
        item.unique_id
        for item in er.async_entries_for_config_entry(registry, entry.entry_id)
    }


@pytest.mark.parametrize(
    "description", STRING_INVERTER_DESCRIPTIONS, ids=lambda d: d.key
)
def test_every_description_names_a_field_that_exists(description) -> None:
    device = SungrowStringInverter(MockModbusConnection().for_unit(1))
    assert description.field in device.field_names
    assert not description.field.endswith("_raw"), "the decoded property, not the code"
    assert description.key == f"sg_{description.field}"


async def test_an_sg_entry_is_its_own_device_with_only_what_answered(
    hass: HomeAssistant,
) -> None:
    """The meter is the `fast` tier's only block and refuses: the entry is up.

    A refusal is the device answering; only a tier that hears nothing fails.
    """
    entry = await _setup(hass)

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert [(d.model, d.serial_number, d.sw_version) for d in devices] == [
        ("SG5.0RS", SERIAL, "ARM_TEST_V1")
    ]
    ids = _unique_ids(hass, entry)
    for answered in ("total_dc_power", "mppt2_voltage", "phase_a_voltage"):
        assert f"{SERIAL}_sg_{answered}" in ids
    for absent in ("mppt3_voltage", "phase_b_voltage", "meter_active_power"):
        assert f"{SERIAL}_sg_{absent}" not in ids, "unavailable or refused"
    assert all(unique_id.startswith(f"{SERIAL}_sg_") for unique_id in ids)
    assert hass.states.get("sensor.sg5_0rs_total_dc_power").state == "1890"
    assert hass.states.get("sensor.sg5_0rs_work_state").state == "run"
    assert hass.states.get("binary_sensor.sg5_0rs_fault_reported").state == "off"


async def test_a_fault_code_reports_a_fault(hass: HomeAssistant) -> None:
    await _setup(hass, words={**SG_INPUT, 5037: 0x5500})

    assert hass.states.get("sensor.sg5_0rs_work_state").state == "fault"
    assert hass.states.get("binary_sensor.sg5_0rs_fault_reported").state == "on"


async def test_an_sg5_0rs_gets_no_phase_or_tracker_it_lacks_from_their_zeros(
    hass: HomeAssistant,
) -> None:
    """Measured on two SG5.0RS (`results/string_inverter/`): B, C and MPPT3 read 0.

    Not the unavailable value the source promises, so a value alone would make
    entities that never move; the output type and the tracker count decide.
    """
    zeros = {5014: 0, 5015: 0, 5019: 0, 5020: 0, 5022: 0, 5023: 0}
    entry = await _setup(hass, words={**SG_INPUT, **zeros})

    ids = _unique_ids(hass, entry)
    assert f"{SERIAL}_sg_phase_a_voltage" in ids
    for phase in ("b", "c"):
        for quantity in ("voltage", "current"):
            assert f"{SERIAL}_sg_phase_{phase}_{quantity}" not in ids
    assert f"{SERIAL}_sg_mppt2_voltage" in ids
    assert f"{SERIAL}_sg_mppt3_voltage" not in ids, "an SG5.0RS has two trackers"


async def test_a_diagnostics_entry_surveys_an_sg_into_its_own_document(
    hass: HomeAssistant,
) -> None:
    entry = await _setup(hass, MODE_DIAGNOSTICS)
    ids = _unique_ids(hass, entry)
    assert f"{SERIAL}_run_survey" in ids
    assert f"{SERIAL}_run_control_test" not in ids, "nothing here writes to an SG"

    device = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)[0]
    await hass.services.async_call(
        DOMAIN, "run_survey", {"device_id": device.id}, blocking=True
    )
    await hass.async_block_till_done()

    state = entry.runtime_data.survey.state
    assert state.error is None
    document = state.document
    assert document["document"] == "string_inverter"
    assert document["device"]["device_type"] == "SG5.0RS"
    assert document["firmware"] == {"arm": "ARM_TEST_V1", "dsp": "DSP_TEST_V1"}
    assert SERIAL not in str(document)
    dump = document["string_inverter"]["register_dump"]["input"]
    assert all(dump.get(str(4989 + i)) is None for i in range(10))
    assert state.fields_read == len(document["string_inverter"]["readings"]) > 0


@pytest.mark.parametrize("action", ["run_control_test", "start_inverter"])
async def test_a_writing_action_refuses_an_sg(hass: HomeAssistant, action) -> None:
    entry = await _setup(hass, MODE_DIAGNOSTICS)
    device = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)[0]

    with pytest.raises(HomeAssistantError) as raised:
        await hass.services.async_call(
            DOMAIN, action, {"device_id": device.id}, blocking=True
        )
    assert raised.value.translation_key == "not_on_string_inverter"


async def test_the_diagnostics_download_carries_the_sg_document(
    hass: HomeAssistant,
) -> None:
    entry = await _setup(hass)
    report = await async_get_config_entry_diagnostics(hass, entry)

    assert report["entry"]["kind"] == KIND_STRING_INVERTER
    assert report["device"]["model"] == "SG5.0RS"
    assert report["survey"]["document"] == "string_inverter"
    assert SERIAL not in str(report)


async def test_the_config_flow_records_an_sg_and_skips_the_battery(
    hass: HomeAssistant,
) -> None:
    """Typed by hand: the identity probe answers, and the type code is an SG's."""
    probed = SimpleNamespace(serial_number=SERIAL, device_type_code=0x2606, model=None)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "setup_diagnostics"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "manual"}
    )
    with patch(
        "custom_components.sungrow_modbus.config_flow._async_probe",
        return_value=(probed, True, None),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.0.2.50", CONF_PORT: 502, CONF_UNIT_ID: 1},
        )
    assert result["step_id"] == "testimony"
    with patch("custom_components.sungrow_modbus.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "SG5.0RS"
    assert result["data"][CONF_KIND] == KIND_STRING_INVERTER
    assert result["data"][CONF_MODE] == MODE_DIAGNOSTICS
