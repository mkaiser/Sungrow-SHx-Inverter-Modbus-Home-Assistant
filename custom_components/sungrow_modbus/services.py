"""Starting and stopping the inverter, deliberately not as entities.

Register 13000 is the one register in the map that turns the inverter off:
`0xCF` boots it, `0xCE` shuts it down. Reading it gives the running state,
which is why `running_state_raw` sits on the same address.

The YAML package exposes this as two dashboard buttons behind a toggle it
calls danger mode. This integration exposes **actions** instead, for a reason
a button cannot address: Home Assistant has no confirmation dialog for a
button press. A card copied from somebody else's screenshot, a stale
automation, or a misclick while scrolling a phone all stop somebody's
inverter, and the entity would sit in every dashboard picker offering exactly
that.

An action has to be written into a script or called from Developer Tools,
which is the first guard and is not available to a button.

The second is who may call it, and that is **configurable per entry** --
administrators only by default, or anyone who may control the device's
entities. It is checked here rather than by
`async_register_admin_service`, for two reasons. The setting belongs to a
config entry and a service belongs to the integration, so one household
running two endpoints would otherwise have to accept one answer for both. And
"anyone" has to mean *anyone who could already change a setting* -- a
read-only login must not be able to stop an inverter it cannot even set the
minimum state of charge on, which a plainly-registered service would let it
do, because Home Assistant applies `POLICY_CONTROL` to entities and not to
actions.

Hiding and showing the control stays a dashboard concern, which is where the
YAML package already solves it well — see
`legacy/dashboards/DefaultDashboard`, whose danger-mode toggle is the pattern
to copy.
"""

from __future__ import annotations

import logging

from modbus_connection import ModbusError
import voluptuous as vol

from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import (
    HomeAssistantError,
    ServiceValidationError,
    Unauthorized,
    UnknownUser,
)
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import (
    AUDIENCE_USERS,
    CONF_PERMISSIONS,
    DEFAULT_PERMISSIONS,
    DOMAIN,
    PERMISSION_CONTROL_TEST,
    PERMISSION_START_STOP,
)
from .coordinator import SungrowConfigEntry

_LOGGER = logging.getLogger(__name__)

SERVICE_START_INVERTER = "start_inverter"
SERVICE_STOP_INVERTER = "stop_inverter"

#: Running a capability survey without a button to press.
#:
#: An ordinary entry has no survey entities -- somebody who installed this for
#: solar sensors should not carry diagnostic tooling they never asked for --
#: so this is how they help if they decide to. A diagnostics-only entry has
#: the button as well, because producing a reading is the whole reason that
#: kind of entry exists.
#:
#: An action rather than an entity leaves nothing behind: no registry row, no
#: recorded history, nothing to remove afterwards.
SERVICE_RUN_SURVEY = "run_survey"

#: Part A and then part B, which writes to every control and puts it back.
SERVICE_RUN_CONTROL_TEST = "run_control_test"

#: Register 13000, from V1.1.11: "0xCF: Boot, 0xCE: Shutdown".
START = 0xCF
STOP = 0xCE

#: Register 13000 is in **both** of Sungrow's tables, and they are different
#: address spaces: Table 3 is read-only over function code 0x04, where reading
#: it gives the running state, and Table 4 is read/write over 0x03/0x06/0x10,
#: where it is Start/Stop. So the write goes to the holding-side field, which
#: is hand-written in the library because nothing reads it and it therefore
#: has no entity and no poll tier.
COMPONENT = "control"
FIELD = "start_stop"

#: The group whose refresh makes the change visible. The running state is read
#: from the *input* side, which is the realtime group -- refreshing the group
#: that was written would show the old state.
STATE_COMPONENT = "realtime_input"

SCHEMA = vol.Schema({vol.Required(ATTR_DEVICE_ID): cv.string})


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the actions once, for the integration rather than an entry.

    Registered plainly rather than as admin actions, because the audience is
    a per-entry setting and has to be read from the entry the call targets --
    see the module docstring. `_async_authorize` is the guard, and it defaults
    to exactly what an admin action would have done.
    """
    hass.services.async_register(
        DOMAIN, SERVICE_START_INVERTER, _async_start, schema=SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_STOP_INVERTER, _async_stop, schema=SCHEMA
    )
    # Not authorised the way start and stop are: this reads and writes
    # nothing, and the worst a stray call can do is spend one connection for
    # a few seconds.
    hass.services.async_register(
        DOMAIN, SERVICE_RUN_SURVEY, _async_run_survey, schema=SCHEMA
    )
    # Authorised the way start and stop are, and for the same reason: it
    # writes. The button beside it is what most people will use; this exists so
    # the run can be scripted, and so that an owner who has narrowed the
    # audience has narrowed both routes to it at once.
    hass.services.async_register(
        DOMAIN, SERVICE_RUN_CONTROL_TEST, _async_run_control_test, schema=SCHEMA
    )


async def _async_run_control_test(call: ServiceCall) -> None:
    """Run the survey and then the control test.

    Refuses when a run is already in flight, as the survey action does -- but
    here the reason is stronger than a session count: two runs writing at once
    would restore each other's probe values, and each would then report the
    other's leftovers as a finding.
    """
    entry = _async_entry_for(call.hass, call.data[ATTR_DEVICE_ID])
    await _async_authorize(call, entry, PERMISSION_CONTROL_TEST)
    _LOGGER.warning(
        "%s: control test requested through the %s.%s action by %s. It writes to "
        "every control this integration can write to, and puts each one back.",
        entry.title,
        DOMAIN,
        SERVICE_RUN_CONTROL_TEST,
        call.context.user_id or "an automation or script",
    )
    if not entry.runtime_data.survey.async_start(control_test=True):
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="survey_already_running"
        )


async def _async_start(call: ServiceCall) -> None:
    """Boot the inverter."""
    await _async_write(call, START, "start")


async def _async_stop(call: ServiceCall) -> None:
    """Shut the inverter down."""
    await _async_write(call, STOP, "stop")


async def _async_run_survey(call: ServiceCall) -> None:
    """Read the inverter and offer the document, as the button does.

    Refuses politely when one is already running: two surveys interleaving
    their reads on one serialized connection is what a Sungrow's very small
    session count cannot take.
    """
    entry = _async_entry_for(call.hass, call.data[ATTR_DEVICE_ID])
    if not entry.runtime_data.survey.async_start():
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="survey_already_running"
        )


async def _async_authorize(
    call: ServiceCall,
    entry: SungrowConfigEntry,
    permission: str = PERMISSION_START_STOP,
) -> None:
    """Raise unless the caller may do this to *this* inverter.

    Follows `homeassistant.helpers.service._async_admin_handler` where the
    cases overlap, deliberately: no user on the context means an automation,
    a script's own trigger or an internal call, which core allows and so does
    this -- the audience setting is about who may click, and an automation is
    the household's own decision expressed in advance.
    """
    if not call.context.user_id:
        return

    user = await call.hass.auth.async_get_user(call.context.user_id)
    if user is None:
        raise UnknownUser(context=call.context)
    if user.is_admin:
        return

    permissions = {**DEFAULT_PERMISSIONS, **entry.options.get(CONF_PERMISSIONS, {})}
    if permissions.get(permission) != AUDIENCE_USERS:
        raise Unauthorized(context=call.context)

    # Opened to users means users who can already change this device, not
    # everyone with a login. A read-only account can read every sensor and
    # change nothing, and stopping the inverter is not the exception to that.
    if not user.permissions.access_all_entities(POLICY_CONTROL):
        raise Unauthorized(context=call.context)


async def _async_write(call: ServiceCall, value: int, what: str) -> None:
    """Write the start/stop register of the device this call targets."""
    entry = _async_entry_for(call.hass, call.data[ATTR_DEVICE_ID])
    await _async_authorize(call, entry)
    coordinator = entry.runtime_data.coordinator_for(STATE_COMPONENT)

    # Logged at warning, not debug. Somebody working out why their inverter
    # stopped overnight should find this without turning anything on first.
    _LOGGER.warning(
        "%s: %s requested through the %s.%s_inverter action by %s",
        entry.title,
        what,
        DOMAIN,
        what,
        call.context.user_id or "an automation or script",
    )
    try:
        await coordinator.device.component(COMPONENT).write(FIELD, value)
    except ModbusError as err:
        raise HomeAssistantError(f"Could not {what} {entry.title}: {err}") from err
    await coordinator.async_refresh()


def _async_entry_for(hass: HomeAssistant, device_id: str) -> SungrowConfigEntry:
    """Return the loaded config entry behind a device id, or explain why not.

    Every failure here is the caller's mistake rather than the device's — a
    stale device id in a script that outlived a re-add, most often — so each
    says which one it was.
    """
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="device_not_found",
            translation_placeholders={"device_id": device_id},
        )

    for entry_id in device.config_entries:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is not None and entry.domain == DOMAIN:
            if not hasattr(entry, "runtime_data"):
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="entry_not_loaded",
                    translation_placeholders={"title": entry.title},
                )
            return entry

    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="not_a_sungrow_device",
        translation_placeholders={"name": device.name or device_id},
    )
