"""Config flow for the Sungrow SHx Inverter integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Final

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SLAVE
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_BATTERY_MAX_POWER,
    CONF_SBR_SLAVE,
    CONF_SCAN_INTERVAL_FAST,
    CONF_SCAN_INTERVAL_MEDIUM,
    CONF_SCAN_INTERVAL_REALTIME,
    CONF_SCAN_INTERVAL_SLOWEST,
    CONF_WAIT_MS,
    DEFAULT_BATTERY_MAX_POWER,
    DEFAULT_PORT,
    DEFAULT_SBR_SLAVE,
    DEFAULT_SCAN_FAST,
    DEFAULT_SCAN_MEDIUM,
    DEFAULT_SCAN_REALTIME,
    DEFAULT_SCAN_SLOWEST,
    DEFAULT_SLAVE,
    DEFAULT_WAIT_MS,
    DOMAIN,
)
from .descriptions import DEVICE_TYPE_MAP

_LOGGER: Final = logging.getLogger(__name__)

# Sungrow SHx serial number lives in 10 consecutive *input* registers
# starting at register 4990 (0-indexed 4989). Confirmed in
# ``modbus_sungrow.yaml`` line 94-101 and ``descriptions.py`` line 109.
SERIAL_REGISTER: Final = 4989
SERIAL_LENGTH: Final = 10
# Device type code (input register 5000 / 0-indexed 4999), see
# ``descriptions.py`` line 110 and ``modbus_sungrow.yaml`` line 113-119.
DEVICE_TYPE_REGISTER: Final = 4999
# Firmware string lives at 0-indexed 13249, length 15 registers (see
# ``descriptions.py`` line 191).
FIRMWARE_REGISTER: Final = 13249
FIRMWARE_LENGTH: Final = 15

CONNECT_TIMEOUT: Final = 5.0


def _user_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Build the user/reconfigure form schema, prefilled with ``defaults``."""
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_HOST,
                default=d.get(CONF_HOST, vol.UNDEFINED),
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Required(
                CONF_PORT,
                default=d.get(CONF_PORT, DEFAULT_PORT),
            ): NumberSelector(
                NumberSelectorConfig(min=1, max=65535, step=1, mode=NumberSelectorMode.BOX)
            ),
            vol.Required(
                CONF_SLAVE,
                default=d.get(CONF_SLAVE, DEFAULT_SLAVE),
            ): NumberSelector(
                NumberSelectorConfig(min=1, max=247, step=1, mode=NumberSelectorMode.BOX)
            ),
            vol.Required(
                CONF_SBR_SLAVE,
                default=d.get(CONF_SBR_SLAVE, DEFAULT_SBR_SLAVE),
            ): NumberSelector(
                NumberSelectorConfig(min=0, max=247, step=1, mode=NumberSelectorMode.BOX)
            ),
            vol.Required(
                CONF_BATTERY_MAX_POWER,
                default=d.get(CONF_BATTERY_MAX_POWER, DEFAULT_BATTERY_MAX_POWER),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0, max=50000, step=100, unit_of_measurement="W",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_WAIT_MS,
                default=d.get(CONF_WAIT_MS, DEFAULT_WAIT_MS),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0, max=1000, step=1, unit_of_measurement="ms",
                    mode=NumberSelectorMode.BOX,
                )
            ),
        }
    )


def _options_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Build the options form schema, prefilled with ``defaults``."""
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_SCAN_INTERVAL_REALTIME,
                default=d.get(CONF_SCAN_INTERVAL_REALTIME, DEFAULT_SCAN_REALTIME),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1, max=300, step=1, unit_of_measurement="s",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_SCAN_INTERVAL_FAST,
                default=d.get(CONF_SCAN_INTERVAL_FAST, DEFAULT_SCAN_FAST),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1, max=300, step=1, unit_of_measurement="s",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_SCAN_INTERVAL_MEDIUM,
                default=d.get(CONF_SCAN_INTERVAL_MEDIUM, DEFAULT_SCAN_MEDIUM),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=10, max=3600, step=1, unit_of_measurement="s",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_SCAN_INTERVAL_SLOWEST,
                default=d.get(CONF_SCAN_INTERVAL_SLOWEST, DEFAULT_SCAN_SLOWEST),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=60, max=7200, step=1, unit_of_measurement="s",
                    mode=NumberSelectorMode.BOX,
                )
            ),
        }
    )


def _coerce_ints(data: dict[str, Any]) -> dict[str, Any]:
    """NumberSelector returns floats; cast the integer-valued keys."""
    out = dict(data)
    for key in (
        CONF_PORT,
        CONF_SLAVE,
        CONF_SBR_SLAVE,
        CONF_BATTERY_MAX_POWER,
        CONF_WAIT_MS,
        CONF_SCAN_INTERVAL_REALTIME,
        CONF_SCAN_INTERVAL_FAST,
        CONF_SCAN_INTERVAL_MEDIUM,
        CONF_SCAN_INTERVAL_SLOWEST,
    ):
        if key in out and out[key] is not None:
            try:
                out[key] = int(out[key])
            except (TypeError, ValueError):
                pass
    return out


def _registers_to_string(registers: list[int]) -> str:
    """Decode a Sungrow ASCII-string register block to a trimmed ``str``."""
    data = bytearray()
    for reg in registers:
        data.append((reg >> 8) & 0xFF)
        data.append(reg & 0xFF)
    # Strip NULs, spaces, and any trailing junk.
    return data.decode("ascii", errors="ignore").strip().rstrip("\x00").strip()


async def _validate_connection(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, str]:
    """Open a Modbus TCP session and probe the inverter identity registers.

    Returns a dict with ``serial``, ``model`` and ``firmware`` keys on
    success. Raises :class:`CannotConnect` on transport errors and
    :class:`InvalidSlave` if the inverter rejects the probe.
    """
    # Imported lazily so the module is importable during static analysis
    # on hosts where pymodbus isn't installed yet.
    from pymodbus.client import AsyncModbusTcpClient  # noqa: PLC0415
    from pymodbus.exceptions import (  # noqa: PLC0415
        ConnectionException,
        ModbusException,
    )

    host: str = data[CONF_HOST]
    port: int = int(data[CONF_PORT])
    slave: int = int(data[CONF_SLAVE])

    client = AsyncModbusTcpClient(host=host, port=port, timeout=CONNECT_TIMEOUT)

    try:
        try:
            connected = await asyncio.wait_for(
                client.connect(), timeout=CONNECT_TIMEOUT
            )
        except (asyncio.TimeoutError, OSError, ConnectionException) as err:
            raise CannotConnect(f"Could not connect to {host}:{port}: {err}") from err
        if not connected:
            raise CannotConnect(f"Could not connect to {host}:{port}")

        # --- Serial number (input registers 4990..4999, 10 regs) -----------
        try:
            serial_rsp = await client.read_input_registers(
                address=SERIAL_REGISTER, count=SERIAL_LENGTH, device_id=slave
            )
        except ModbusException as err:
            raise CannotConnect(f"Modbus error reading serial: {err}") from err
        except (asyncio.TimeoutError, OSError, ConnectionException) as err:
            raise CannotConnect(f"Transport error reading serial: {err}") from err

        if serial_rsp is None or serial_rsp.isError():
            raise InvalidSlave(
                f"Inverter at {host}:{port} rejected probe on slave {slave}"
            )

        serial = _registers_to_string(serial_rsp.registers)
        if not serial:
            raise InvalidSlave(
                f"Empty serial from {host}:{port} slave {slave}"
            )

        # --- Device type code (input register 5000) ------------------------
        model: str = ""
        try:
            dev_rsp = await client.read_input_registers(
                address=DEVICE_TYPE_REGISTER, count=1, device_id=slave
            )
        except (ModbusException, asyncio.TimeoutError, OSError, ConnectionException):
            dev_rsp = None
        if dev_rsp is not None and not dev_rsp.isError() and dev_rsp.registers:
            code = dev_rsp.registers[0]
            _LOGGER.debug(f"device code: {code}")
            model = DEVICE_TYPE_MAP.get(code, f"SHx (0x{code:04X})")

        # --- Firmware (best-effort; optional) ------------------------------
        firmware = ""
        try:
            fw_rsp = await client.read_input_registers(
                address=FIRMWARE_REGISTER, count=FIRMWARE_LENGTH, device_id=slave
            )
        except (ModbusException, asyncio.TimeoutError, OSError, ConnectionException):
            fw_rsp = None
        if fw_rsp is not None and not fw_rsp.isError() and fw_rsp.registers:
            firmware = _registers_to_string(fw_rsp.registers)

        return {"serial": serial, "model": model, "firmware": firmware}
    finally:
        try:
            client.close()
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Error closing Modbus client", exc_info=True)


class SungrowConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sungrow SHx."""

    VERSION = 1

    async def _async_process_input(
        self, user_input: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, str], str | None]:
        """Validate ``user_input`` and return (data, errors, title).

        ``title`` is ``None`` when validation failed.
        """
        errors: dict[str, str] = {}
        data = _coerce_ints(user_input)
        title: str | None = None
        try:
            info = await _validate_connection(self.hass, data)
        except CannotConnect as err:
            _LOGGER.debug("CannotConnect during validation: %s", err)
            errors["base"] = "cannot_connect"
        except InvalidSlave as err:
            _LOGGER.debug("InvalidSlave during validation: %s", err)
            errors["base"] = "invalid_slave"
        except Exception:  # noqa: BLE001
            _LOGGER.error("Unexpected error validating Sungrow", exc_info=True)
            errors["base"] = "unknown"
        else:
            serial = info["serial"]
            model = info.get("model") or ""
            if model:
                title = f"Sungrow {model} ({serial[-6:]})"
            else:
                title = f"Sungrow Inverter ({data[CONF_HOST]})"
            # Stash identity bits alongside the user-supplied data.
            data = {**data, "serial": serial, "model": model,
                    "firmware": info.get("firmware", "")}
        return data, errors, title

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data, errors, title = await self._async_process_input(user_input)
            if not errors and title is not None:
                await self.async_set_unique_id(data["serial"])
                self._abort_if_unique_id_configured(updates=data)
                return self.async_create_entry(title=title, data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow reconfiguring host/port/slave on an existing entry."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            data, errors, _title = await self._async_process_input(user_input)
            if not errors:
                await self.async_set_unique_id(data["serial"])
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry=entry, data_updates=data
                )
            defaults: dict[str, Any] = {**entry.data, **user_input}
        else:
            defaults = dict(entry.data)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_user_schema(defaults),
            errors=errors,
            description_placeholders={"device": entry.title},
        )

    async def async_step_import(
        self, import_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle an import from YAML.

        Delegates connection validation + entry creation to
        ``async_step_user`` (reuses all the serial/model probing) and,
        on success, raises a Repairs issue instructing the user to
        delete the transient ``sungrow_shx:`` YAML block.
        """
        _LOGGER.debug("async_step_import called with: %s", import_data)
        result = await self.async_step_user(import_data)

        # Only raise the follow-up repair when we actually created an
        # entry. Aborts (e.g. already_configured) or form redisplays
        # shouldn't surface a "please delete YAML" nag.
        if result.get("type") == "create_entry":
            # Avoid importing at module scope to keep repairs optional.
            from .repairs import async_raise_imported_from_yaml_issue  # noqa: PLC0415

            entry_id = (result.get("result") and result["result"].entry_id) or ""
            async_raise_imported_from_yaml_issue(
                self.hass, entry_id, result.get("title") or "Sungrow SHx"
            )
        return result

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> SungrowOptionsFlow:  # type: ignore[override]
        """Return the options flow handler."""
        return SungrowOptionsFlow()


class SungrowOptionsFlow(OptionsFlowWithReload):
    """Handle options for the Sungrow SHx integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the polling intervals."""
        if user_input is not None:
            return self.async_create_entry(
                title="", data=_coerce_ints(user_input)
            )

        current = {**self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(current),
        )


class CannotConnect(HomeAssistantError):
    """Raised when we cannot establish a Modbus TCP session."""


class InvalidSlave(HomeAssistantError):
    """Raised when the remote responds but rejects the probe registers."""


class UnknownError(HomeAssistantError):
    """Raised for unexpected validation failures."""
