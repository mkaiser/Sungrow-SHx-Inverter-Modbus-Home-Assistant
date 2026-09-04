"""Config flow for the Sungrow SHx integration."""

from __future__ import annotations

from typing import Any

from modbus_connection import ModbusError, ModbusTcpParams
import voluptuous as vol

from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)
from sungrow_shx_modbus import SungrowInverter

from .const import CONF_UNIT_ID, DEFAULT_NAME, DEFAULT_PORT, DEFAULT_UNIT_ID, DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): TextSelector(),
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
            NumberSelector(
                NumberSelectorConfig(mode=NumberSelectorMode.BOX, min=1, max=65535)
            ),
            vol.Coerce(int),
        ),
        vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): vol.All(
            NumberSelector(
                NumberSelectorConfig(mode=NumberSelectorMode.BOX, min=1, max=247)
            ),
            vol.Coerce(int),
        ),
    }
)


async def _async_probe(
    hass: HomeAssistant, host: str, port: int, unit_id: int
) -> SungrowInverter:
    """Read the inverter identity over a temporary unit, or raise.

    A config flow has no config entry yet to hang a connection hold on, which
    is what async_get_temporary_unit exists for: it shares a connection that
    is already up, and closes one it opened itself.
    """
    params = ModbusTcpParams(host=host, port=port)
    async with async_get_temporary_unit(hass, params, unit_id) as unit:
        inverter = SungrowInverter(unit)
        await inverter.async_update_identity()
    return inverter


class SungrowConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a Sungrow SHx config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial connection step."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            try:
                inverter = await _async_probe(
                    self.hass,
                    user_input[CONF_HOST],
                    user_input[CONF_PORT],
                    user_input[CONF_UNIT_ID],
                )
            except (ModbusError, HomeAssistantError) as err:
                errors["base"] = "cannot_connect"
                placeholders["error"] = str(err)
            else:
                serial = inverter.serial_number
                code = inverter.device_type_code
                if serial is None:
                    errors["base"] = "no_serial_number"
                elif inverter.model is None:
                    errors["base"] = "unrecognized_inverter"
                    placeholders["code"] = (
                        "unknown" if code is None else f"0x{code:04X}"
                    )
                else:
                    await self.async_set_unique_id(serial)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=inverter.model or DEFAULT_NAME, data=user_input
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders=placeholders,
        )
