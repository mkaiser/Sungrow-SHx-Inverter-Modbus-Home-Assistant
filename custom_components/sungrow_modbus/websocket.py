"""What the dashboard's Diagnosis view asks for and saves, over the websocket.

Commands rather than entities. The results are some sixty rows with evidence,
which as attributes the state machine would push to every browser on every
change and the recorder would have to be told to leave out; the settings are
the entry's options.
"""

from __future__ import annotations

import json
from typing import Any

import probatio

from homeassistant.components import websocket_api
from homeassistant.const import ATTR_DEVICE_ID, CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, device_registry as dr
from sungrow_modbus.capability_test import results

from . import diagnosis_settings
from .const import DOMAIN
from .coordinator import SungrowConfigEntry
from .download import async_download_url


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the commands. Called once, from `async_setup`."""
    for command in (ws_results, ws_settings, ws_save_settings):
        websocket_api.async_register_command(hass, command)


def _entry_of(hass: HomeAssistant, device_id: str) -> SungrowConfigEntry | None:
    """Return the loaded entry behind a device of this integration, or None."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None or device.config_entry_id is None:
        return None
    entry = hass.config_entries.async_get_entry(device.config_entry_id)
    if entry is None or entry.domain != DOMAIN or not hasattr(entry, "runtime_data"):
        return None
    return entry


@websocket_api.websocket_command(
    {
        probatio.Required("type"): "sungrow_modbus/diagnosis/results",
        probatio.Required(ATTR_DEVICE_ID): cv.string,
    }
)
@websocket_api.require_admin
@callback
def ws_results(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Send the kept runs and the readings' checks of a device's entry.

    The evidence is text the library wrote, and a lost connection's text names
    the address it lost: that is taken out, since a screenshot of this card is
    what gets posted when somebody asks what a check means.
    """
    entry = _entry_of(hass, msg[ATTR_DEVICE_ID])
    if entry is None:
        connection.send_error(
            msg["id"], websocket_api.ERR_NOT_FOUND, "No loaded Sungrow Modbus device"
        )
        return
    runner = entry.runtime_data.diagnosis
    view: dict[str, Any] = results.view(runner.tests)
    if host := entry.data.get(CONF_HOST):
        view = json.loads(json.dumps(view).replace(str(host), "the device"))
    view["document_url"] = (
        async_download_url(hass, entry) if runner.state.document is not None else None
    )
    connection.send_result(msg["id"], view)


@websocket_api.websocket_command(
    {
        probatio.Required("type"): "sungrow_modbus/diagnosis/settings",
        probatio.Required(ATTR_DEVICE_ID): cv.string,
    }
)
@websocket_api.require_admin
@callback
def ws_settings(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Send the diagnosis's options of a device's entry."""
    if (entry := _entry_of(hass, msg[ATTR_DEVICE_ID])) is None:
        connection.send_error(
            msg["id"], websocket_api.ERR_NOT_FOUND, "No loaded Sungrow Modbus device"
        )
        return
    connection.send_result(msg["id"], diagnosis_settings.view(hass, entry))


@websocket_api.websocket_command(
    {
        probatio.Required("type"): "sungrow_modbus/diagnosis/settings/save",
        probatio.Required(ATTR_DEVICE_ID): cv.string,
        probatio.Required("part"): probatio.In(
            [diagnosis_settings.ANSWERS, diagnosis_settings.TESTS]
        ),
        probatio.Required("values"): dict,
    }
)
@websocket_api.require_admin
@callback
def ws_save_settings(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Save options of the diagnosis. Not during a run, which has read them."""
    if (entry := _entry_of(hass, msg[ATTR_DEVICE_ID])) is None:
        connection.send_error(
            msg["id"], websocket_api.ERR_NOT_FOUND, "No loaded Sungrow Modbus device"
        )
        return
    if entry.runtime_data.diagnosis.state.running:
        connection.send_error(
            msg["id"], websocket_api.ERR_NOT_ALLOWED, "A diagnosis is running"
        )
        return
    try:
        options = diagnosis_settings.changed(entry, msg["part"], msg["values"])
    except ValueError as err:
        connection.send_error(
            msg["id"], websocket_api.ERR_INVALID_FORMAT, f"Not a value for {err}"
        )
        return
    hass.config_entries.async_update_entry(entry, options=options)
    connection.send_result(msg["id"], diagnosis_settings.view(hass, entry))
