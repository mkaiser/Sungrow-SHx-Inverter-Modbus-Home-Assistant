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
from pytest_homeassistant.common import MockConfigEntry

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


async def test_an_address_typed_while_a_card_offers_the_same_inverter_goes_on(
    hass: HomeAssistant,
) -> None:
    """A WiNet-S card waiting for the inverter does not end the owner's flow.

    gerd's migration, 2026-11-21: the dongle's announcement was waiting as a
    card, and adding the inverter by address aborted "already in progress".
    The owner's flow takes the device; the card goes once the entry exists.
    """
    from homeassistant.config_entries import SOURCE_ZEROCONF

    from .test_config_flow_zeroconf import _dongle

    card = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=_dongle()
    )
    assert card["step_id"] == "discovery_confirm"

    with patch("custom_components.sungrow_modbus.async_setup_entry", return_value=True):
        result = await _submit(hass, {"return_value": (_inverter(), True, None)})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["context"]["unique_id"] == SERIAL
    assert result["data"][CONF_HOST] == ADDRESS[CONF_HOST]
    assert not [
        flow
        for flow in hass.config_entries.flow.async_progress()
        if flow["flow_id"] == card["flow_id"]
    ]


async def test_a_second_card_for_the_same_inverter_still_gives_way(
    hass: HomeAssistant,
) -> None:
    """Only a flow the owner started takes a device a card holds."""
    from homeassistant.config_entries import SOURCE_ZEROCONF

    from .test_config_flow_zeroconf import _dongle

    first = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=_dongle()
    )
    second = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=_dongle()
    )
    assert first["step_id"] == "discovery_confirm"
    assert second["type"] is FlowResultType.ABORT
    assert second["reason"] == "already_in_progress"
