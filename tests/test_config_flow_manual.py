"""Typing an address: every answer the form can give, and what it says next.

The manual form is the fallback after a search found nothing, which makes it
the worst place for an error to be wrong. Each refusal is the inverter's own
answer turned into words: nothing answered, it answered without a serial (no
entity could be identified), or it answered with a model code nobody has
mapped. Past the form, the testimony page says what was measured about the
route, in the same three answers as register 6100 itself.

The probe is replaced by its result here; `test_config_flow_topology.py`
covers the probe against whole houses.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from modbus_connection import ModbusConnectionError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_MODE,
    CONF_UNIT_ID,
    DOMAIN,
    MODE_DEVICES,
)
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import SERIAL

ADDRESS = {CONF_HOST: "192.0.2.5", CONF_PORT: 502, CONF_UNIT_ID: 1}
PROBE = "custom_components.sungrow_modbus.config_flow._async_probe"


def _inverter(serial: str | None = SERIAL, code: int | None = 0x0E0F, model="SH10RT"):
    return SimpleNamespace(serial_number=serial, device_type_code=code, model=model)


async def _manual_form(hass: HomeAssistant) -> dict:
    """Walk Add integration to the address form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "setup_diagnostics"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "manual"}
    )
    assert result["step_id"] == "manual"
    return result


async def _submit(hass: HomeAssistant, probe: dict) -> dict:
    result = await _manual_form(hass)
    with patch(PROBE, **probe):
        return await hass.config_entries.flow.async_configure(
            result["flow_id"], ADDRESS
        )


@pytest.mark.parametrize(
    ("probe", "error", "placeholder"),
    [
        (
            {"side_effect": ModbusConnectionError("refused")},
            "cannot_connect",
            ("error", "refused"),
        ),
        (
            {"return_value": (_inverter(serial=None), True, None)},
            "no_serial_number",
            None,
        ),
        (
            {"return_value": (_inverter(model=None), True, None)},
            "unrecognized_inverter",
            ("code", "0x0E0F"),
        ),
        (
            {"return_value": (_inverter(code=None, model=None), True, None)},
            "unrecognized_inverter",
            ("code", "unknown"),
        ),
    ],
    ids=["nothing answered", "no serial", "unknown code", "no code at all"],
)
async def test_the_address_form_says_what_the_inverter_answered(
    hass: HomeAssistant, probe: dict, error: str, placeholder: tuple | None
) -> None:
    result = await _submit(hass, probe)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"
    assert result["errors"] == {"base": error}
    if placeholder is not None:
        key, text = placeholder
        assert text in result["description_placeholders"][key]


@pytest.mark.parametrize(
    ("direct", "says"),
    [
        (True, "its own LAN port"),
        (False, "through a communication module"),
        (None, "could not be measured"),
    ],
    ids=["answered", "refused", "unanswered"],
)
async def test_the_testimony_page_reports_the_measured_route(
    hass: HomeAssistant, direct: bool | None, says: str
) -> None:
    """A guess here would be published as `survey_transport`; a question is not."""
    result = await _submit(hass, {"return_value": (_inverter(), direct, None)})

    assert result["step_id"] == "testimony"
    measured = result["description_placeholders"]["measured"]
    assert "SH10RT" in measured
    assert says in measured


async def test_reconfigure_refuses_an_inverter_without_a_serial(
    hass: HomeAssistant,
) -> None:
    """Without a serial nothing proves it is the same inverter, so it stays put."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**ADDRESS, CONF_MODE: MODE_DEVICES},
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)

    with patch(PROBE, return_value=(_inverter(serial=None), True, None)):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {**ADDRESS, CONF_HOST: "192.0.2.6"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "no_serial_number"}
    assert entry.data[CONF_HOST] == "192.0.2.5"
