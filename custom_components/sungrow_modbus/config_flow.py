"""Config flow for the Sungrow Modbus integration."""

from __future__ import annotations

from typing import Any

from modbus_connection import ModbusError, ModbusTcpParams
import voluptuous as vol

from homeassistant.components import network
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)
from sungrow_modbus import (
    DEFAULT_PORT as MODBUS_PORT,
    MAX_HOSTS,
    NetworkTooLarge,
    SungrowInverter,
    async_hostname,
    async_sweep,
    network_of,
)

from .const import (
    CONF_ENTITY_IDS,
    CONF_NETWORK,
    CONF_REGISTER_DUMP,
    CONF_UNIT_ID,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    DOMAIN,
    ENTITY_IDS_MIGRATE,
    ENTITY_IDS_NEW,
)
from .migration import async_legacy_ids_known, async_legacy_ids_live

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


#: Sweeping is a network event -- an ARP entry and a SYN per address -- so the
#: range is asked for rather than guessed at, prefilled with the one Home
#: Assistant is actually on.
def _scan_schema(default_network: str) -> vol.Schema:
    """Return the search form, prefilled with this instance's own subnet."""
    return vol.Schema(
        {
            vol.Required(CONF_NETWORK, default=default_network): TextSelector(),
            vol.Required(CONF_PORT, default=MODBUS_PORT): vol.All(
                NumberSelector(
                    NumberSelectorConfig(mode=NumberSelectorMode.BOX, min=1, max=65535)
                ),
                vol.Coerce(int),
            ),
        }
    )


#: Sentinel value for the picker's escape hatch, which cannot collide with a
#: host address.
NOT_LISTED = "__not_listed__"


def _entity_ids_schema(default: str) -> vol.Schema:
    """Return the migrate-or-start-fresh choice, pre-selecting what can work."""
    return vol.Schema(
        {
            vol.Required(CONF_ENTITY_IDS, default=default): SelectSelector(
                SelectSelectorConfig(
                    options=[ENTITY_IDS_MIGRATE, ENTITY_IDS_NEW],
                    mode=SelectSelectorMode.LIST,
                    translation_key=CONF_ENTITY_IDS,
                )
            )
        }
    )


#: Substituted into the step description. Two states, both stated as facts
#: about this instance right now rather than as instructions -- "it is still
#: running" lands where "it must be removed first" did not.
_PACKAGE_LOADED = (
    "\u26a0\ufe0f **The YAML package is still running.** {live} of its entities are "
    "live on this instance right now and are holding their entity IDs, so "
    "migrating cannot work yet.\n\n"
    "To migrate: remove `modbus_sungrow.yaml` from your configuration — or "
    "comment out the line that includes it — then **restart Home Assistant** "
    "and add this integration again. Until then only starting fresh will work."
)

_PACKAGE_NOT_LOADED = (
    "\u2705 **The YAML package is not running**, so its entity IDs are free to "
    "take over. Both answers below will work."
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
    """Handle a Sungrow Modbus config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> SungrowOptionsFlow:
        """Return the options flow, which is where diagnostics are turned up."""
        return SungrowOptionsFlow()

    def __init__(self) -> None:
        """Start with no connection details and no id choice."""
        self._data: dict[str, Any] = {}
        self._title = DEFAULT_NAME
        self._found: dict[str, dict[str, Any]] = {}
        self._searched = ""
        self._candidates = 0

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Offer to look for the inverter, or to be told where it is.

        Searching first, because the question this flow opens with -- what is
        the inverter's IP address -- is one many users cannot answer without
        going to look at their router.
        """
        return self.async_show_menu(step_id="user", menu_options=["search", "manual"])

    async def async_step_search(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Sweep a subnet and identify whatever answers.

        Two passes, and the second is the one that matters: an open port 502
        is not a Modbus device. A sweep of the maintainer's own LAN turned up
        a gateway that accepts the connection and echoes bytes back, so
        nothing is called an inverter until it has answered a read of its
        device type register.
        """
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            # Remembered whether it succeeds or not, so a retry offers the
            # range that was tried rather than starting from the detected one
            # again -- the user is usually correcting it, not rejecting it.
            self._searched = user_input[CONF_NETWORK]
            try:
                candidates = await async_sweep(
                    user_input[CONF_NETWORK], port=user_input[CONF_PORT]
                )
            except NetworkTooLarge as err:
                errors["base"] = "network_too_large"
                placeholders["hosts"] = str(err.hosts)
                placeholders["limit"] = str(MAX_HOSTS)
            except ValueError as err:
                errors[CONF_NETWORK] = "invalid_network"
                placeholders["error"] = str(err)
            else:
                self._found = await self._async_identify(
                    candidates, user_input[CONF_PORT]
                )
                if self._found:
                    return await self.async_step_pick()
                # A form can only carry an error, and an error leaves the user
                # on a form with nowhere to go but the close button. A search
                # that finds nothing is a dead end, so it gets a menu.
                self._candidates = len(candidates)
                return await self.async_step_nothing_found()

        return self.async_show_form(
            step_id="search",
            data_schema=_scan_schema(
                self._searched or await self._async_default_network()
            ),
            errors=errors,
            description_placeholders=placeholders,
            last_step=False,
        )

    async def async_step_nothing_found(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Say what was looked at, and offer a way onwards from it.

        Home Assistant renders a menu as buttons, which is the only way to
        give a step somewhere to go other than forwards: a form with an error
        leaves the user staring at the same fields with no way back to the
        menu they came from.
        """
        return self.async_show_menu(
            step_id="nothing_found",
            menu_options=["search", "manual", "start_over"],
            description_placeholders={
                "scanned": self._searched,
                "candidates": str(self._candidates),
            },
        )

    async def async_step_start_over(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Return to the first menu."""
        return await self.async_step_user()

    async def async_step_pick(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user choose between the inverters that answered."""
        if user_input is not None:
            if user_input[CONF_HOST] == NOT_LISTED:
                return await self.async_step_manual()
            found = self._found[user_input[CONF_HOST]]
            await self.async_set_unique_id(found["serial"])
            self._abort_if_unique_id_configured()
            self._data = {
                CONF_HOST: found[CONF_HOST],
                CONF_PORT: found[CONF_PORT],
                CONF_UNIT_ID: found[CONF_UNIT_ID],
            }
            self._title = found["model"] or DEFAULT_NAME
            return await self.async_step_entity_ids()

        options = [
            SelectOptionDict(value=host, label=found["label"])
            for host, found in sorted(self._found.items())
        ]
        # The search can identify a real inverter that is not the one the user
        # meant -- a neighbour's, on a shared network, or the second of two.
        # Without this the only way out of the list is to abandon the flow.
        options.append(
            SelectOptionDict(value=NOT_LISTED, label="None of these — let me choose")
        )
        return self.async_show_form(
            step_id="pick",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, default=options[0]["value"]
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=options, mode=SelectSelectorMode.LIST
                        )
                    )
                }
            ),
            description_placeholders={"count": str(len(self._found))},
            last_step=False,
        )

    async def _async_default_network(self) -> str:
        """Return the subnet Home Assistant is on, to prefill the search with.

        Anything wider than the sweep limit is offered as a /24 around the
        address instead: a container on a Docker bridge reports a /16, and
        prefilling a form with 65534 addresses invites a very long wait.
        """
        with_prefix: list[str] = []
        for adapter in await network.async_get_adapters(self.hass):
            if not adapter["enabled"]:
                continue
            for address in adapter["ipv4"]:
                candidate = network_of(address["address"], address["network_prefix"])
                if address["network_prefix"] >= 22:
                    return candidate
                with_prefix.append(network_of(address["address"], 24))
        return with_prefix[0] if with_prefix else "192.168.1.0/24"

    async def _async_identify(
        self, candidates: list[str], port: int
    ) -> dict[str, dict[str, Any]]:
        """Ask each candidate what it is, keeping only the ones that answer."""
        found: dict[str, dict[str, Any]] = {}
        for host in candidates:
            try:
                inverter = await _async_probe(self.hass, host, port, DEFAULT_UNIT_ID)
            except (ModbusError, HomeAssistantError):
                # Something is listening on the Modbus port that is not a
                # Sungrow inverter, which is common enough to be unremarkable.
                continue
            serial = inverter.serial_number
            if serial is None:
                continue
            hostname = await async_hostname(host)
            model = inverter.model or DEFAULT_NAME
            found[host] = {
                CONF_HOST: host,
                CONF_PORT: port,
                CONF_UNIT_ID: DEFAULT_UNIT_ID,
                "serial": serial,
                "model": inverter.model,
                "label": f"{model} at {hostname or host}",
            }
        return found

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Take the connection details from the user."""
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
                    self._data = dict(user_input)
                    self._title = inverter.model or DEFAULT_NAME
                    return await self.async_step_entity_ids()

        return self.async_show_form(
            step_id="manual",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_entity_ids(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask whether to take over the YAML package's entity ids.

        Only asked when there is something to take over. A user who never ran
        `modbus_sungrow.yaml` has no history to preserve and no decision to
        make, so they are not shown a question about a package they have never
        heard of — the entry is created with device-scoped ids directly.
        """
        known = async_legacy_ids_known(self.hass)
        if not known:
            return self._async_create(ENTITY_IDS_NEW)

        # Checked before the question is asked, not after it is answered. The
        # requirement -- remove the YAML package first -- was written in the
        # dialog and still surprised people, because a sentence about what you
        # ought to have done reads very differently from a line telling you
        # what is true right now on this instance.
        live = async_legacy_ids_live(self.hass)

        errors: dict[str, str] = {}
        if user_input is not None:
            choice = user_input[CONF_ENTITY_IDS]
            if choice == ENTITY_IDS_MIGRATE and live:
                # Adoption needs the id free in the state machine as well as
                # in the registry. With the YAML package still loaded the
                # registry would hand out `sensor.total_dc_power_2` instead,
                # silently, and the history would be orphaned.
                errors["base"] = "legacy_package_still_loaded"
            else:
                return self._async_create(choice)

        return self.async_show_form(
            step_id="entity_ids",
            # Pre-selecting the only answer that can work, so the default is
            # never one that will be refused.
            data_schema=_entity_ids_schema(
                ENTITY_IDS_NEW if live else ENTITY_IDS_MIGRATE
            ),
            errors=errors,
            description_placeholders={
                "count": str(len(known)),
                "example": sorted(known)[0],
                "status": (
                    _PACKAGE_LOADED.format(live=len(live))
                    if live
                    else _PACKAGE_NOT_LOADED
                ),
            },
        )

    def _async_create(self, entity_ids: str) -> ConfigFlowResult:
        """Create the entry with the id style already decided."""
        return self.async_create_entry(
            title=self._title, data={**self._data, CONF_ENTITY_IDS: entity_ids}
        )


class SungrowOptionsFlow(OptionsFlow):
    """Settings that can be changed after setup.

    Connection details are not here: changing the host or unit id means
    talking to a different device, which is a reconfigure rather than an
    option.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the options, and save them."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_REGISTER_DUMP,
                        default=self.config_entry.options.get(
                            CONF_REGISTER_DUMP, False
                        ),
                    ): BooleanSelector()
                }
            ),
        )
