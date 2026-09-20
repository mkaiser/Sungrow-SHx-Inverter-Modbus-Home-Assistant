"""Config flow for the Sungrow Modbus integration."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import suppress
import logging
from typing import Any

from modbus_connection import (
    ModbusError,
    ModbusExceptionError,
    ModbusTcpParams,
    ServerDeviceBusyError,
)
import voluptuous as vol

from homeassistant.components import network
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import UnknownFlow, section
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.util import slugify
from sungrow_modbus import (
    COMPONENTS,
    DEFAULT_INTERVALS,
    FALLBACK_W,
    MAX_HOSTS,
    TIER_COMPONENTS,
    Capability,
    NetworkTooLarge,
    SungrowInverter,
    async_hostname,
    async_sweep,
    hosts_in,
    model_for_capacity,
    network_of,
    power_from_bms,
)
from sungrow_modbus.discovery import CONCURRENCY, TIMEOUT
from sungrow_modbus.fingerprint import OTHER_INVERTER_YES

from .config_flow_schemas import (
    _ALREADY_TRIED,
    _NOT_DETECTED,
    _PREFILLED,
    _SAME_DONGLE,
    NOT_LISTED,
    STEP_USER_DATA_SCHEMA,
    _described,
    _entity_ids_schema,
    _is_container_bridge,
    _other_inverter_schema,
    _scan_schema,
    _testimony_schema,
)
from .const import (
    AUDIENCE_ADMINS,
    AUDIENCE_USERS,
    CONF_ADD_DEVICES,
    CONF_BATTERY_MAX_POWER,
    CONF_CONTROL_TEST_EXPORT,
    CONF_CONTROL_TEST_RESTART,
    CONF_ENTITY_IDS,
    CONF_EXTERNAL_PLACEMENT,
    CONF_EXTERNAL_SOURCES,
    CONF_INTERVALS,
    CONF_LEGACY_SLOT,
    CONF_MODE,
    CONF_NETWORK,
    CONF_PERMISSIONS,
    CONF_REGISTER_DUMP,
    CONF_SURVEY_OTHER_INVERTER,
    CONF_SURVEY_OTHER_INVERTER_DETAIL,
    CONF_UNIT_ID,
    DEFAULT_EXTERNAL_PLACEMENT,
    DEFAULT_NAME,
    DEFAULT_PERMISSIONS,
    DEVICES_MODE_OFFERED,
    DOMAIN,
    ENTITY_IDS_MIGRATE,
    ENTITY_IDS_NEW,
    IDENTIFY_UNITS,
    INTERVAL_MINIMUM,
    INTERVAL_NEVER,
    MODE_DEVICES,
    MODE_DIAGNOSTICS,
    PLACEMENT_BEHIND_METER,
    PLACEMENT_SEPARATE,
    ROLE_SLAVE,
    SCAN_PORTS,
    SECTION_ADVANCED,
    SECTION_CONTROL_TEST,
    SECTION_EXTERNAL,
    SECTION_PERMISSIONS,
    SECTION_POLLING,
    SECTION_SURVEY,
)
from .migration import (
    async_legacy_ids_known,
    async_legacy_ids_live,
    async_legacy_ids_with_history,
    async_legacy_suffix,
)

_LOGGER = logging.getLogger(__name__)


_DEVICES_MODE_COMING = (
    "\n\n⚠️ **Sensors and controls are not in this release.** This is an "
    "early alpha, and it exists to gather readings: it connects to your "
    "inverter, works out what it is and which registers it answers, and "
    "creates no entities for the values. Setting up the inverter properly -- "
    "including taking over the entity IDs of the YAML package, which is the "
    "one decision here that cannot be undone -- comes in a later release, and "
    "an entry made now can be upgraded to it then without being deleted."
)

#: And what the same sentence has to say when the gate is open, because then
#: both answers really are available and the step has to explain the choice
#: rather than the restriction.
_DEVICES_MODE_OPEN = (
    "\n\nBoth answers are fine, and you can change your mind later: picking "
    "**Diagnostics only** skips the one irreversible question in this dialog, "
    "about which entity IDs to take over, because a reading does not need it."
)


def _alpha_placeholders() -> dict[str, str]:
    """Return what the two gated dialogs should say about the gate.

    A function rather than a constant because `DEVICES_MODE_OFFERED` is read
    at call time: a module-level dict would freeze the answer at import and
    quietly ignore the flag it exists to report.

    Two keys rather than one because the two places need opposite things when
    the gate is open. The opening step needs a sentence either way -- it is
    explaining a choice. The options page's promotion toggle needs one only
    while promotion is refused; with the gate open there is nothing to say
    and the helper text beside it is already complete.

    Both are always present and never absent: an unsubstituted placeholder
    renders as the literal `{devices_mode}` in the dialog, which is the one
    outcome worse than either sentence.
    """
    return {
        "mode_choice": (
            _DEVICES_MODE_OPEN if DEVICES_MODE_OFFERED else _DEVICES_MODE_COMING
        ),
        "devices_mode": "" if DEVICES_MODE_OFFERED else _DEVICES_MODE_COMING,
    }


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


#: Register 6100, as a protocol address. **Direct-only**, 9 readings out of 9.
#:
#: Sungrow documents 6100-6195 as not forwarded by a WiNet-S/S2 or Logger, and
#: that is what four houses show: it answers over the inverter's own LAN port
#: and refuses behind a dongle, without exception. So it is the one signal
#: that says which *route* a reading came in by -- which is worth showing,
#: because the two routes do not answer the same registers.
DIRECT_ONLY_REGISTER = 6099


async def _async_probe(
    hass: HomeAssistant, host: str, port: int, unit_id: int
) -> tuple[SungrowInverter, bool | None]:
    """Read the identity and the route, or raise.

    Returns the inverter and whether it answered the direct-only register, so
    the picker can say how each address reaches the machine. One extra read
    per candidate, which is worth it: a house with a cable *and* a dongle
    offers two addresses for one inverter, and they do not answer the same
    registers -- a dongle forwards 1020 of 1510 dumped addresses where a
    cable forwards 1461, and answers 0 where the inverter answers
    "unavailable".

    A config flow has no config entry yet to hang a connection hold on, which
    is what async_get_temporary_unit exists for: it shares a connection that
    is already up, and closes one it opened itself.
    """
    params = ModbusTcpParams(host=host, port=port)
    async with async_get_temporary_unit(hass, params, unit_id) as unit:
        inverter = SungrowInverter(unit)
        await inverter.async_update_identity()
        direct: bool | None
        try:
            await unit.read_input_registers(DIRECT_ONLY_REGISTER, 2)
        except (ServerDeviceBusyError, ModbusExceptionError) as err:
            # A refusal is the transport answering, and only a refusal is.
            # 0x06 is the exception that says "ask me later" rather than
            # "no such register", so it settles nothing either.
            direct = None if isinstance(err, ServerDeviceBusyError) else False
        except (ModbusError, HomeAssistantError):
            # The link did not carry the question. That is not evidence about
            # the register, and reading it as one told a house with no
            # communication module fitted that it had a dongle -- measured
            # 2026-09-20. No retry here, deliberately: this runs once per
            # candidate address in a /24 sweep, so a retry multiplies the
            # search rather than the certainty. `None` is the honest answer
            # and the prose says so.
            direct = None
        else:
            direct = True
    return inverter, direct


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
        #: Every range swept in this flow, so the picker can stop offering
        #: one that already found nothing and the form can say what was
        #: covered. A user on their third attempt otherwise has no idea.
        self._tried: list[str] = []
        self._candidates = 0
        #: The sweep in flight, so the progress step can wait on it. A sweep
        #: of a quiet /24 spends its whole time on connect timeouts, which is
        #: exactly when a silent dialog looks broken.
        self._sweep_task: asyncio.Task[None] | None = None
        #: What the sweep is doing, rendered under the bar. Held here rather
        #: than passed, because the progress step is re-entered to show it
        #: and has no other way to know.
        self._stage = ""
        #: What the contributor said about their installation, on the
        #: diagnostics path. Saved as options when the entry is created.
        self._testimony: dict[str, Any] = {}
        self._role: str | None = None
        #: Whether the user was asked for a name and gave one.
        self._named = False
        #: How many distinct inverters the search found, by serial. Decides
        #: whether the name is worth asking about at all.
        self._others = 1
        #: What this entry is for. Decided in the first step, because it
        #: decides whether the migration question is asked at all.
        self._mode = MODE_DEVICES

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask what this entry is for before asking anything about the wiring.

        Two very different intentions arrive at this dialog. Most people want
        their inverter in Home Assistant. Some want to help this project find
        out what their model answers -- and for them the flow's central
        question, whether to take over the YAML package's entity ids, is both
        irreversible and beside the point.

        So it is asked first, and cheaply: a diagnostics entry connects,
        identifies the hardware, creates no entities, and never mentions
        migration. It can be promoted to a full entry afterwards, which is
        when the id question is put.

        While `DEVICES_MODE_OFFERED` is off the first answer is not available,
        and the menu still offers it -- the step it leads to explains why and
        carries on as diagnostics. Greying it is what a first version tried
        and it cannot be done: a menu option has no disabled state at all,
        and the form that replaced the menu could only grey the whole
        control, which left the *working* answer greyed out too and read as
        a dialog where nothing worked.
        """
        return self.async_show_menu(
            step_id="user",
            menu_options=["setup_devices", "setup_diagnostics"],
            # The step description is shared with the form above, so the menu
            # has to substitute too -- an unfilled placeholder is rendered
            # literally rather than dropped.
            description_placeholders=_alpha_placeholders(),
        )

    async def async_step_setup_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Set up the inverter properly, with entities."""
        if not DEVICES_MODE_OFFERED:
            return await self.async_step_devices_later()
        self._mode = MODE_DEVICES
        return await self.async_step_find()

    async def async_step_devices_later(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Say that the ordinary setup is not in this release, and carry on.

        An abort would be the short way to write this and the wrong thing to
        do to somebody: it closes the dialog, and the way back is to start
        again and pick the other answer, having been told only that they
        chose wrong. So this is a step with one button, and the button does
        the thing they almost certainly want.

        It is also where the refusal actually lives. `_mode` is never set to
        `MODE_DEVICES` here, so a client posting the menu's step id by hand
        gets a diagnostics entry rather than a devices one -- the control on
        the screen is a courtesy and this is the rule.
        """
        if user_input is not None:
            return await self.async_step_setup_diagnostics()
        return self.async_show_form(
            step_id="devices_later",
            data_schema=vol.Schema({}),
            last_step=False,
        )

    async def async_step_setup_diagnostics(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Set up only enough to read the inverter and report on it."""
        self._mode = MODE_DIAGNOSTICS
        return await self.async_step_find()

    async def async_step_find(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Offer to look for the inverter, or to be told where it is.

        Searching first, because the question this flow opens with -- what is
        the inverter's IP address -- is one many users cannot answer without
        going to look at their router.
        """
        return self.async_show_menu(step_id="find", menu_options=["search", "manual"])

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
            if self._searched not in self._tried:
                self._tried.append(self._searched)
            try:
                # Validated here rather than inside the task, so a typed
                # range that cannot be parsed comes straight back to this
                # form. A progress step that appeared for a second and
                # returned an error would be a worse way to say the same
                # thing.
                hosts_in(self._searched)
            # `NetworkTooLarge` subclasses `ValueError`, so this order is not
            # cosmetic: catching the general one first turns "that is 16
            # million addresses" into "that is not a network", which is both
            # wrong and unhelpful.
            except NetworkTooLarge as err:
                errors["base"] = "network_too_large"
                placeholders["hosts"] = str(err.hosts)
                placeholders["limit"] = str(MAX_HOSTS)
            except ValueError as err:
                errors[CONF_NETWORK] = "invalid_network"
                placeholders["error"] = str(err)
            else:
                return await self.async_step_searching()

        return self.async_show_form(
            step_id="search",
            # Not prefilled with the range that just failed: after a sweep
            # that found nothing, the one range certainly not worth trying
            # again is the one just tried. The picker drops it and offers the
            # next candidate instead.
            data_schema=_scan_schema(
                await self._async_default_network() if not self._tried else "",
                self._tried,
            ),
            errors=errors,
            description_placeholders={
                **placeholders,
                # Says whether the field was prefilled from a real adapter or
                # left empty because nothing usable was found. Without this a
                # blank box looks like a bug rather than an honest answer.
                "detected": (
                    _ALREADY_TRIED.format(tried=", ".join(self._tried))
                    if self._tried
                    else _PREFILLED
                    if await self._async_default_network()
                    else _NOT_DETECTED
                ),
            },
            last_step=False,
        )

    async def async_step_searching(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Sweep, with a bar, because a quiet network is slow and silent.

        Every address with nothing listening costs the full connect timeout,
        so the sweep of a /24 spends most of its time proving absences. That
        is exactly when somebody wonders whether it has hung -- and the old
        form simply sat there, greyed out, for as long as it took.

        The bar is driven by addresses settled rather than by time: how long
        a sweep takes depends on how many addresses are quiet, which is the
        thing nobody knows in advance.
        """
        if self._sweep_task is None:
            self._sweep_task = self.hass.async_create_task(
                self._async_sweep_and_identify(), eager_start=False
            )

        if not self._sweep_task.done():
            return self.async_show_progress(
                step_id="searching",
                progress_action="searching",
                progress_task=self._sweep_task,
                description_placeholders={
                    "network": self._searched,
                    "stage": self._stage,
                },
            )

        self._sweep_task = None
        return self.async_show_progress_done(
            next_step_id="pick" if self._found else "nothing_found"
        )

    async def _async_sweep_and_identify(self) -> None:
        """Look on every port this project knows, and ask what answered.

        Both passes matter, and the second is the one that decides: an open
        port 502 is not a Modbus device. A sweep of the maintainer's own LAN
        turned up a gateway that accepts the connection and echoes bytes
        back, so nothing is called an inverter until it has answered a read
        of its device type register.
        """
        candidates: list[tuple[str, int]] = []
        addresses = len(hosts_in(self._searched))
        settled = 0

        # **Two phases, one bar**, and the split is the whole point of this
        # rewrite. The first version counted only the sweep, so the bar hit
        # 100% and the dialog then sat silent for 45 seconds -- measured on
        # a real /24 -- while identification ran. That phase is the slow one
        # and it is the one nobody could see: every candidate that is not a
        # Sungrow costs one Modbus read per unit id in `IDENTIFY_UNITS`,
        # each with its own timeout, before it can be ruled out.
        #
        # Weighted rather than counted, because the two phases are not the
        # same size and the number of candidates is unknown until the first
        # one ends. A connect timeout is 1 second and concurrent; a refused
        # identification is five sequential reads.
        sweeping = 0.7

        def _sweep_progress(done: int, _of: int) -> None:
            self.async_update_progress(sweeping * (settled + done) / (addresses * 2))

        for port in SCAN_PORTS:
            found = await async_sweep(
                self._searched, port=port, on_progress=_sweep_progress
            )
            # The one line that makes a failed search diagnosable afterwards.
            # A search that finds nothing leaves the user at "nothing found"
            # and left the log completely silent -- not even which network was
            # swept, which is the first thing anybody would ask and the one
            # thing that cannot be recovered from the dialog. Measured the
            # hard way: a real search failed twice on this project's own dev
            # instance and the log held nothing but two asyncio slow-task
            # warnings.
            _LOGGER.debug(
                "Swept %s on port %s: %s answered",
                self._searched,
                port,
                ", ".join(found) or "nothing",
            )
            candidates.extend((host, port) for host in found)
            settled += addresses
            self._set_stage(
                f"Checked {settled} of {addresses * len(SCAN_PORTS)} addresses; "
                f"{len({host for host, _ in candidates})} answered so far."
            )

        # **A sweep that found nothing gets one slower second chance**, and
        # this is not defensive programming -- it is a measured failure.
        #
        # `async_port_open` gives each address one connect and `wait_for`
        # measures wall clock, so an address is ruled out on a stopwatch
        # rather than on an answer. With 64 sockets in flight and a one
        # second budget, anything that slows the event loop takes the budget
        # away from connects that would have completed in six milliseconds.
        # Measured here: under an asyncio debug-mode loop -- which is exactly
        # what `hass --debug` runs -- a sweep of a /24 holding two live
        # inverters reported **nothing at all**, three runs out of three,
        # while the same sweep on a normal loop found both every time. A
        # Raspberry Pi doing something else is the same shape of problem.
        #
        # Retried only when *nothing* answered, because that is both the
        # cheapest moment to spend the time -- the alternative is telling
        # somebody their inverter does not exist -- and the case where a
        # false absence does the most damage. Half the concurrency and twice
        # the timeout, which was enough for three runs out of three under the
        # same debug loop that failed three out of three at the defaults.
        if not candidates:
            self._set_stage(
                "Nothing answered. Trying again more slowly, because a busy "
                "moment can make a sweep miss a device that is there."
            )
            for port in SCAN_PORTS:
                found = await async_sweep(
                    self._searched,
                    port=port,
                    concurrency=max(1, CONCURRENCY // 2),
                    timeout=TIMEOUT * 2,
                )
                _LOGGER.debug(
                    "Re-swept %s on port %s slowly: %s answered",
                    self._searched,
                    port,
                    ", ".join(found) or "nothing",
                )
                candidates.extend((host, port) for host in found)

        # Addresses, not address-and-port pairs. One device answering on
        # both 502 and 503 is one thing that answered, and telling somebody
        # "2 answered but none was a Sungrow" when there is one box on their
        # wall is a worse lie than saying nothing.
        self._candidates = len({host for host, _ in candidates})

        def _identifying(host: str, index: int, of: int) -> None:
            self.async_update_progress(sweeping + (1 - sweeping) * (index - 1) / of)
            self._set_stage(
                f"Asking {host} what it is ({index} of {of}). Anything that is "
                "not a Sungrow has to time out on every unit id before it can "
                "be ruled out, which is the slowest part of this."
            )

        self._found = await self._async_identify(candidates, on_candidate=_identifying)
        _LOGGER.debug(
            "Identified %s of %s candidate(s) on %s as Sungrow: %s",
            len(self._found),
            len(candidates),
            self._searched,
            ", ".join(sorted(self._found)) or "none",
        )
        self.async_update_progress(1.0)

    @callback
    def _set_stage(self, stage: str) -> None:
        """Say what is happening, and make the dialog show it.

        Home Assistant re-renders a progress step when its placeholders
        change -- but only when the step is entered again, which nothing does
        on its own while a task runs. So the flow is reconfigured from inside
        the task, which is what HACS's own device-code step does. Without it
        the first text stays on screen for the whole sweep, which is how
        "found 0 so far" was still showing after an inverter had been found.
        """
        if stage == self._stage:
            return
        self._stage = stage
        with suppress(UnknownFlow):
            self.hass.async_create_task(
                self.hass.config_entries.flow.async_configure(flow_id=self.flow_id),
                eager_start=False,
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
        """Return to the choice of *how to find* the inverter.

        Not all the way to the first menu. A sweep that found nothing says
        nothing about what the entry is for, and re-asking a question the
        user has already answered is how a dead end starts to feel like a
        loop.
        """
        return await self.async_step_find()

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
            self._role = found.get("role")
            # Only where there is more than one inverter to tell apart, and
            # counted by **serial**: two addresses of one machine are one
            # inverter, so a house with a cable and a dongle is not asked to
            # name anything.
            self._others = len({entry["serial"] for entry in self._found.values()})
            return await self.async_step_name()

        # In the order `_described` put them, not re-sorted by address: it
        # ranks a direct path above a dongle, and a plain `sorted()` here
        # threw that away and defaulted to whichever address sorted lower.
        options = [
            SelectOptionDict(value=host, label=found["label"])
            for host, found in self._found.items()
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
            description_placeholders={
                "count": str(len(self._found)),
                "note": (
                    _SAME_DONGLE
                    if any(entry.get("same_dongle") for entry in self._found.values())
                    else ""
                ),
            },
            last_step=False,
        )

    async def _async_default_network(self) -> str:
        """Return the subnet worth searching, or "" if it cannot be known.

        Anything wider than the sweep limit is offered as a /24 around the
        address instead, because prefilling a form with 65534 addresses
        invites a very long wait.

        **A container bridge is skipped**, and that is the case this method
        got wrong. Home Assistant in Docker with bridge networking sits on
        `172.17.0.2/16` and reports exactly that; a /24 around it is
        `172.17.0.0/24`, which is the bridge and never the inverter. The
        container can still *reach* the inverter -- the bridge NATs, so it
        follows the host's routing -- so a search looks like it should work
        and sweeps 254 addresses of nothing. Measured in this project's own
        devcontainer, where it offered the bridge while the inverter was two
        networks away.

        There is no way to discover the right range from inside: the bridge
        hides the host's routing, and multicast does not cross it either, so
        mDNS finds nothing. So this returns **""** rather than a guess, and
        the form says why and asks. A wrong default that looks right is worse
        than an empty field, because it sends somebody to a dead end and
        tells them their inverter is not there.
        """
        fallbacks: list[str] = []
        for adapter in await network.async_get_adapters(self.hass):
            if not adapter["enabled"]:
                continue
            for address in adapter["ipv4"]:
                if _is_container_bridge(address["address"]):
                    continue
                candidate = network_of(address["address"], address["network_prefix"])
                if address["network_prefix"] >= 22:
                    return candidate
                fallbacks.append(network_of(address["address"], 24))
        return fallbacks[0] if fallbacks else ""

    async def _async_identify(
        self,
        candidates: list[tuple[str, int]],
        on_candidate: Callable[[str, int, int], None] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Ask each candidate what it is, keeping only the ones that answer.

        Takes address **and port** together, and every candidate in one call.
        Both matter: a sweep tries more than one port now, and `_described`
        at the end is the only thing that can see that two addresses carry
        one serial -- so identifying them one at a time would describe a
        two-path inverter as two strangers.

        Every candidate unit, not just unit 1. Measured at a two-inverter
        house: the second answers on unit **2** at its own LAN port and times
        out on 1, because a cluster slave's own device address is 2 -- so
        asking only unit 1 reported that inverter absent, and a user would
        have been told their second inverter is not there. Only the rare case
        pays for it: an address with an inverter on unit 1 makes exactly the
        reads it always did.
        """
        found: dict[str, dict[str, Any]] = {}
        for index, (host, port) in enumerate(candidates, start=1):
            if on_candidate is not None:
                on_candidate(host, index, len(candidates))
            if host in found:
                # Already identified on an earlier port. `SCAN_PORTS` is
                # ordered so that is 502, the one Sungrow's own documentation
                # names.
                continue
            for unit_id in IDENTIFY_UNITS:
                try:
                    inverter, direct = await _async_probe(
                        self.hass, host, port, unit_id
                    )
                except (ModbusError, HomeAssistantError):
                    # Something is listening on the Modbus port that is not a
                    # Sungrow inverter -- common enough to be unremarkable,
                    # and measured: one of five endpoints on one subnet
                    # refuses the serial register on every unit id.
                    continue
                serial = inverter.serial_number
                if serial is None:
                    # Answered and named nothing. Something is there and
                    # talking, so a later unit answering would be a different
                    # device, and reporting it as this address's identity
                    # would be wrong.
                    break
                hostname = await async_hostname(host)
                model = inverter.model or DEFAULT_NAME
                found[host] = {
                    CONF_HOST: host,
                    CONF_PORT: port,
                    CONF_UNIT_ID: unit_id,
                    "serial": serial,
                    "model": inverter.model,
                    "hostname": hostname,
                    "direct": direct,
                    # Rebuilt by `_described`, which is the only place that
                    # knows whether this address shares a serial with another.
                    "label": f"{model} at {hostname or host}",
                }
                break
        return _described(found)

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Take the connection details from the user."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            try:
                inverter, direct = await _async_probe(
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
                    # `_found` is what `_async_measured` reads to tell the
                    # testimony step what has already been measured, and this
                    # path used to leave it empty -- so every user who typed
                    # an address was told "an unidentified model, reached
                    # through a communication module" whatever the probe had
                    # just found. Measured 2026-09-20 at a house with no
                    # communication module fitted at all, whose entry was
                    # titled SH10RT on the very next screen. It steers
                    # `survey_transport`, which is published.
                    self._found = {
                        user_input[CONF_HOST]: {
                            CONF_HOST: user_input[CONF_HOST],
                            CONF_PORT: user_input[CONF_PORT],
                            CONF_UNIT_ID: user_input[CONF_UNIT_ID],
                            "serial": serial,
                            "model": inverter.model,
                            "direct": direct,
                        }
                    }
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
        # A diagnostics entry creates no entities, so there is nothing for an
        # id to attach to and nothing to migrate. Asking would be worse than
        # pointless: it is the one decision here that cannot be undone
        # casually, and answering it wrongly to get past a dialog is exactly
        # how somebody loses years of history.
        if self._mode == MODE_DIAGNOSTICS:
            return await self.async_step_testimony()

        # Which of the YAML package's inverter slots this device was, decided
        # here because this is the only moment the evidence exists: the package
        # must still be installed for its serial sensors to be in the registry,
        # and the very next thing the migration asks is that it be removed.
        #
        # `None` means the question could not be answered, and it is stored as
        # `""` -- the single-inverter slot -- only because that is what every
        # house had before multi-inverter migration existed. A second inverter
        # in a house whose package is already gone therefore keeps the old
        # behaviour rather than guessing at somebody else's history.
        slot = async_legacy_suffix(self.hass, self.unique_id) or ""
        self._data[CONF_LEGACY_SLOT] = slot

        known = async_legacy_ids_known(self.hass, slot)
        if not known:
            # The registry is the good evidence, but not the only evidence.
            # cleanup_entities.md has told users for years to delete the
            # orphaned entries a removed YAML platform leaves behind, and the
            # recorder keeps their rows regardless. Asking it as well is what
            # stops those users being handed new ids and a stranded history
            # without ever being offered the choice.
            known = await async_legacy_ids_with_history(self.hass, slot)
        if not known:
            return self._async_create(ENTITY_IDS_NEW)

        # Checked before the question is asked, not after it is answered. The
        # requirement -- remove the YAML package first -- was written in the
        # dialog and still surprised people, because a sentence about what you
        # ought to have done reads very differently from a line telling you
        # what is true right now on this instance.
        live = async_legacy_ids_live(self.hass, slot)

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

    async def async_step_name(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask what to call this inverter, where there is more than one.

        Asked rather than derived, and only where it matters. With one
        inverter the model is a perfectly good name and a question about it
        is noise. With two, the model is the **same string** for both, and
        Home Assistant appends `_2` to whichever was set up second:
        `sensor.sh10rt_total_dc_power_2`. That suffix records click order and
        nothing else.

        Deriving something better fixes uniqueness and not legibility. The
        serial's last four, the address tail, `inv 2` as the YAML package
        does -- `sensor.sh10rt_0234_total_dc_power` is unique, permanent, and
        still does not say which roof. Only the owner knows that it is the
        one over the garage.

        The answer becomes the device name, and therefore the entity ids, and
        therefore what years of history are keyed to. So it is asked once,
        here, before anything is created -- a rename afterwards leaves every
        id already made exactly where it was.
        """
        if self._others < 2:
            return await self.async_step_entity_ids()

        if user_input is not None:
            chosen = user_input.get(CONF_NAME, "").strip()
            if chosen:
                self._title = chosen
                self._named = True
            return await self.async_step_entity_ids()

        return self.async_show_form(
            step_id="name",
            data_schema=vol.Schema(
                {vol.Optional(CONF_NAME, default=self._suggested_name()): str}
            ),
            description_placeholders={
                "count": str(self._others),
                "model": self._title,
                "suggestion": self._suggested_name(),
                "example": f"sensor.{slugify(self._suggested_name())}_total_dc_power",
            },
            last_step=False,
        )

    def _suggested_name(self) -> str:
        """Return the name to offer, which is the most the wire can say.

        The model, plus the role where a **direct** connection made it
        readable -- through a WiNet-S every inverter presents as unit 1
        whatever it is configured as, so a dongle path gets the model alone
        rather than a guess.

        It is a starting point and not an answer: two inverters in a cluster
        are genuinely "master" and "slave", and that is worth offering, but
        nothing on the wire knows which one is over the garage.
        """
        if self._role == ROLE_SLAVE:
            return f"{self._title} slave"
        return self._title

    @callback
    def _async_measured(self) -> str:
        """Say what discovery already worked out, so nobody re-answers it.

        The transport is the one that matters and the one already settled:
        register 6100 distinguishes a direct connection from a dongle, 9
        times out of 9. What an owner adds is the half no register reaches --
        whether a dongle is on its cable or its WiFi, which is not
        determinable and not guessed.
        """
        device = self._found.get(self._data.get(CONF_HOST, ""), {})
        if not device:
            # Nothing was probed for this address, so there is nothing to
            # report. Saying so beats inventing it: this used to fall through
            # to the "communication module" branch and assert a dongle at
            # every house reached by typing an address.
            return (
                "Nothing has been measured for this address yet, so please "
                "answer from what you know."
            )
        model = device.get("model") or "an unidentified model"
        direct = device.get("direct")
        if direct is True:
            route = (
                "reached through its own LAN port — register 6100 answers, which "
                "is what a cable straight into the inverter looks like"
            )
        elif direct is False:
            route = (
                "reached through a communication module, so a WiNet-S, WiNet-S2 "
                "or Logger is in the path — register 6100 was refused. Whether it "
                "is using its Ethernet socket or its WiFi is **not** determinable "
                "over Modbus, and that is the part only you can tell us"
            )
        else:
            # Neither answered nor refused: the read failed on the link. A
            # guess here is worse than a question, because this steers the
            # `survey_transport` answer and that is published.
            route = (
                "and the route could not be measured — register 6100 neither "
                "answered nor was refused, which is what a busy link looks like "
                "from here. A cable answers it and a dongle refuses it, so this "
                "is one for you to tell us"
            )
        return (
            f"Already measured, so you do not need to tell us: this is "
            f"**{model}**, {route}."
        )

    async def async_step_testimony(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask the few things a survey needs and no register can answer.

        Only on the diagnostics path, and at setup rather than later, because
        this is the entry that exists **in order** to produce a document --
        somebody who chose this mode has already said they want to help, and
        finding the questions afterwards meant finding a section of an
        options page they had no reason to open.

        Measured on a real installation: the button produced a document in
        under ten seconds with every one of these fields empty, and the
        contributor's reasonable reaction was "why was I not asked?".

        Every answer is optional, and blank is a real answer: the document
        format distinguishes an empty field -- the question was not put --
        from `unsure`, where it was put and the owner did not know. What is
        asked is what no register reaches: no register reports a battery's
        make, nothing distinguishes a cable from a dongle's Ethernet socket,
        and a Modbus proxy in the path changes what every dropped block means
        while being invisible from this end.
        """
        if user_input is not None:
            self._testimony = dict(user_input)
            if self._testimony.get(CONF_SURVEY_OTHER_INVERTER) == OTHER_INVERTER_YES:
                return await self.async_step_other_inverter()
            return self._async_create(ENTITY_IDS_NEW)

        return self.async_show_form(
            step_id="testimony",
            data_schema=_testimony_schema({}),
            description_placeholders={"measured": self._async_measured()},
            # Not the last step when the answer turns out to be yes, and Home
            # Assistant has to be told before it knows: the flag decides
            # whether the button says "Submit" or "Next". It is set here
            # because the common answer is no, and a dialog that says "Next"
            # and then finishes is the worse surprise of the two.
            last_step=True,
        )

    async def async_step_other_inverter(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask what the other inverter is, having been told there is one.

        A step rather than a field, because a config flow form is built
        before it is sent and cannot reveal a box when an answer changes. So
        the box is only ever shown to the people it is about.
        """
        if user_input is not None:
            self._testimony.update(user_input)
            return self._async_create(ENTITY_IDS_NEW)

        return self.async_show_form(
            step_id="other_inverter",
            data_schema=_other_inverter_schema(""),
            last_step=True,
        )

    def _async_create(self, entity_ids: str) -> ConfigFlowResult:
        """Create the entry with the id style already decided."""
        data = {**self._data, CONF_ENTITY_IDS: entity_ids, CONF_MODE: self._mode}
        # Stored only where the name question was actually asked and answered.
        # An entry without it keeps a `DeviceInfo` carrying no name, which is
        # what every entry created before this step has -- so nothing already
        # set up sees its device renamed by this feature arriving, and a
        # single-inverter house is not given an id derived from a name it was
        # never shown.
        if self._named:
            data[CONF_NAME] = self._title
        return self.async_create_entry(
            title=self._title,
            data=data,
            # Straight into the options, which is where the survey reads
            # them from and where the same questions are editable
            # afterwards. Two places to store one answer would be one too
            # many.
            options=self._testimony or None,
            # The last screen of the wizard, and the only place left to say
            # what happens next. A diagnostics entry has just been created
            # and has done nothing yet -- the survey is a button somebody has
            # to find and press, and the document arrives in a notification
            # they have no reason to be watching. Both were reported by a
            # contributor who ran the survey and then asked where the file
            # was. `async_create_entry` renders this as markdown on the
            # success dialog; the key is `config.create_entry.<description>`.
            description=(
                "diagnostics" if self._mode == MODE_DIAGNOSTICS else "default"
            ),
        )


class SungrowOptionsFlow(OptionsFlow):
    """Settings that can be changed after setup.

    Connection details are not here: changing the host or unit id means
    talking to a different device, which is a reconfigure rather than an
    option.
    """

    def __init__(self) -> None:
        """Start with nothing collected."""
        #: What the one page collected, held while the promotion question is
        #: put. Options are only written when a flow *ends*, so an entry
        #: promoted on the way out would otherwise lose everything typed
        #: beside the checkbox that promoted it.
        self._pending_options: dict[str, Any] | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Everything worth changing after setup, on one page.

        This was a menu of five items, each opening a form of its own. The
        menu was the problem: it made somebody guess which of five words
        held the setting they wanted, and it turned "change the interval and
        the battery maximum" into two trips through a dialog that closes
        between them.

        A config flow cannot show tabs -- the frontend has exactly seven step
        types and none of them is one -- but it can show **collapsible
        sections**, which is the same idea without the tab bar: every setting
        on one page, grouped, with the groups nobody is looking for folded
        away. `data_entry_flow.section` is the mechanism.

        Sections arrive nested, one dict per section key, which is why the
        merge below reads section by section rather than flattening.
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            intervals = {
                tier: int(value) for tier, value in user_input[SECTION_POLLING].items()
            }
            if all(value == INTERVAL_NEVER for value in intervals.values()):
                # The one refusal on this page. An entry polling nothing is
                # not a configuration, it is an entry that should be deleted.
                errors["base"] = "nothing_left_to_poll"
            else:
                external = user_input[SECTION_EXTERNAL]
                options: dict[str, Any] = {
                    **self.config_entry.options,
                    CONF_INTERVALS: intervals,
                    CONF_PERMISSIONS: {
                        **DEFAULT_PERMISSIONS,
                        **self.config_entry.options.get(CONF_PERMISSIONS, {}),
                        **user_input[SECTION_PERMISSIONS],
                    },
                    CONF_EXTERNAL_SOURCES: external.get(CONF_EXTERNAL_SOURCES, []),
                    CONF_EXTERNAL_PLACEMENT: external[CONF_EXTERNAL_PLACEMENT],
                    **user_input[SECTION_SURVEY],
                    **user_input[SECTION_CONTROL_TEST],
                    **user_input[SECTION_ADVANCED],
                }
                # The flag is checked as well as the value: a disabled
                # control is a frontend courtesy, and the payload arrives over
                # a websocket anybody with a token can write by hand.
                if options.get(
                    CONF_SURVEY_OTHER_INVERTER
                ) == OTHER_INVERTER_YES and not options.get(
                    CONF_SURVEY_OTHER_INVERTER_DETAIL
                ):
                    # Only when the answer is yes *and* nothing has been said
                    # about it yet. Asking again on every visit would punish
                    # the people who answered, and the field is on this page
                    # to edit once it has a value -- there is nothing to
                    # reveal after the first time.
                    self._pending_options = options
                    return await self.async_step_other_inverter()
                if DEVICES_MODE_OFFERED and user_input.get(CONF_ADD_DEVICES):
                    # The promotion question is asked on its own page, and
                    # that is deliberate: it is the only irreversible choice
                    # this integration offers, and it does not belong folded
                    # into a section beside a poll interval.
                    self._pending_options = options
                    return await self.async_step_promote()
                return self.async_create_entry(data=options)

        return self.async_show_form(
            step_id="init",
            data_schema=self._async_options_schema(),
            errors=errors,
            # Every section's own evidence, in one place. A form has one set
            # of placeholders and the sections share them, so each of these
            # is referenced from the section that needs it.
            description_placeholders={
                **self._async_tier_table(
                    {
                        **DEFAULT_INTERVALS,
                        **self.config_entry.options.get(CONF_INTERVALS, {}),
                    }
                ),
                "reported_load": self._async_load_now(),
                "measured": await self._async_survey_measured(),
                "battery_status": self._async_battery_status(),
                # Why the promotion toggle above is greyed, in the same words
                # the config flow uses for the same gate.
                **_alpha_placeholders(),
            },
        )

    @callback
    def _async_options_schema(self) -> vol.Schema:
        """Build the one form, in the order somebody reads it.

        Polling first because it is what people come here for, and the
        survey last because it is an offer rather than a setting. Everything
        except polling starts collapsed: an open section is a claim that you
        probably want to change this, and three of the four are things most
        owners will never touch.
        """
        options = self.config_entry.options
        current = {**DEFAULT_INTERVALS, **options.get(CONF_INTERVALS, {})}

        schema: dict[Any, Any] = {}

        # Only where it means something. An entry that already has devices
        # would be offered a box that does nothing, which is the menu item
        # this page replaced.
        if self.config_entry.data.get(CONF_MODE, MODE_DEVICES) == MODE_DIAGNOSTICS:
            # Greyed rather than dropped while the gate is closed, so an
            # owner can see that promotion exists and is coming. `read_only`
            # makes the frontend disable the field and leave it out of what
            # it submits, which is why the default above is what comes back.
            schema[vol.Required(CONF_ADD_DEVICES, default=False)] = BooleanSelector(
                BooleanSelectorConfig(read_only=True)
                if not DEVICES_MODE_OFFERED
                else BooleanSelectorConfig()
            )

        schema[vol.Required(SECTION_POLLING)] = section(
            self._async_polling_schema(current), {"collapsed": False}
        )
        schema[vol.Required(SECTION_PERMISSIONS)] = self._permissions_section()
        schema[vol.Required(SECTION_EXTERNAL)] = self._external_section()
        schema[vol.Required(SECTION_ADVANCED)] = self._advanced_section()
        schema[vol.Required(SECTION_SURVEY)] = self._survey_section()
        schema[vol.Required(SECTION_CONTROL_TEST)] = self._control_test_section()
        return vol.Schema(schema)

    def _permissions_section(self) -> Any:
        """Return the who-may-change-what ladder, one row per permission.

        Built from `DEFAULT_PERMISSIONS` rather than written out, so adding a
        permission is one line in `const.py` plus a string, and cannot be
        half-done: a permission this page never showed would silently keep its
        default forever.
        """
        permissions = {
            **DEFAULT_PERMISSIONS,
            **self.config_entry.options.get(CONF_PERMISSIONS, {}),
        }
        return section(
            vol.Schema(
                {
                    vol.Required(
                        permission,
                        default=permissions[permission],
                    ): SelectSelector(
                        SelectSelectorConfig(
                            mode=SelectSelectorMode.LIST,
                            translation_key="audience",
                            options=[AUDIENCE_ADMINS, AUDIENCE_USERS],
                        )
                    )
                    # Built from the table rather than written out, so adding a
                    # permission is one line in `const.py` and a string, and
                    # cannot be half-done: a permission the page never showed
                    # would silently keep its default forever.
                    for permission in DEFAULT_PERMISSIONS
                }
            ),
            {"collapsed": True},
        )

    def _external_section(self) -> Any:
        """Return the questions about a generator the Sungrow cannot see.

        The only entities in this integration whose existence an owner decides
        rather than a probe. A non-Sungrow inverter behind the same meter makes
        `load_power` low by exactly its output, and no register anywhere says
        so, which is why this is asked rather than measured.
        """
        options = self.config_entry.options
        return section(
            vol.Schema(
                {
                    vol.Optional(
                        CONF_EXTERNAL_SOURCES,
                        default=list(options.get(CONF_EXTERNAL_SOURCES, ())),
                    ): EntitySelector(
                        EntitySelectorConfig(
                            domain="sensor",
                            device_class=SensorDeviceClass.POWER,
                            multiple=True,
                        )
                    ),
                    vol.Required(
                        CONF_EXTERNAL_PLACEMENT,
                        default=options.get(
                            CONF_EXTERNAL_PLACEMENT, DEFAULT_EXTERNAL_PLACEMENT
                        ),
                    ): SelectSelector(
                        SelectSelectorConfig(
                            mode=SelectSelectorMode.LIST,
                            translation_key="external_placement",
                            options=[PLACEMENT_BEHIND_METER, PLACEMENT_SEPARATE],
                        )
                    ),
                }
            ),
            {"collapsed": True},
        )

    def _advanced_section(self) -> Any:
        """Return the settings that change what the entities *are*, not how often."""
        options = self.config_entry.options
        return section(
            vol.Schema(
                {
                    vol.Required(
                        CONF_BATTERY_MAX_POWER,
                        default=options.get(CONF_BATTERY_MAX_POWER, 0),
                    ): vol.All(
                        NumberSelector(
                            NumberSelectorConfig(
                                mode=NumberSelectorMode.BOX,
                                min=0,
                                max=50000,
                                step=100,
                                unit_of_measurement="W",
                            )
                        ),
                        vol.Coerce(int),
                    ),
                    vol.Required(
                        CONF_REGISTER_DUMP,
                        default=options.get(CONF_REGISTER_DUMP, False),
                    ): BooleanSelector(),
                }
            ),
            {"collapsed": True},
        )

    # The testimony a survey needs and no register can answer, plus the
    # one switch that changes what it reads. Saved here; *run* from the
    # button on the device page, or the `run_survey` action, which is
    # where a progress bar and a download link can exist and a modal
    # dialog cannot. Same questions as the diagnostics setup step asks,
    # from one schema, so the two cannot drift.

    def _survey_section(self) -> Any:
        """Return the survey's questions, which are an offer rather than a setting.

        Last on the page for that reason: nothing here changes how the
        integration behaves, and a person who never opens it loses nothing.
        """
        options = self.config_entry.options
        return section(_testimony_schema(options), {"collapsed": True})

    # What the control test is allowed to do, which is a different question
    # from whether to run it. Running it is a button; these two decide how
    # far it may go when somebody presses that button, and both default to
    # the cautious answer. Their descriptions carry the consequences,
    # because a checkbox label has no room for them and this is the only
    # place either is explained.

    def _control_test_section(self) -> Any:
        """Return the two permissions part B needs, both off by default.

        They are separate flags rather than one level because they are not
        ordered: somebody who will allow a restart is not thereby somebody who
        will allow their export to be limited.
        """
        options = self.config_entry.options
        return section(
            vol.Schema(
                {
                    vol.Required(
                        CONF_CONTROL_TEST_RESTART,
                        default=options.get(CONF_CONTROL_TEST_RESTART, False),
                    ): BooleanSelector(),
                    vol.Required(
                        CONF_CONTROL_TEST_EXPORT,
                        default=options.get(CONF_CONTROL_TEST_EXPORT, False),
                    ): BooleanSelector(),
                }
            ),
            {"collapsed": True},
        )

    async def async_step_other_inverter(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask what the other inverter is, on the way out of the options page.

        The same pattern as `async_step_promote`: options are only written
        when a flow *ends*, so everything typed on the page is held in
        `_pending_options` while this question is put, and written with it.
        Losing a page of answers to a follow-up question would be a poor
        trade for the question.
        """
        options = self._pending_options or dict(self.config_entry.options)
        if user_input is not None:
            self._pending_options = None
            return self.async_create_entry(data={**options, **user_input})

        return self.async_show_form(
            step_id="other_inverter",
            data_schema=_other_inverter_schema(
                options.get(CONF_SURVEY_OTHER_INVERTER_DETAIL, "")
            ),
        )

    async def async_step_promote(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Turn a diagnostics-only entry into a full one.

        This is where the question the diagnostics path skipped finally gets
        put, and it is put here rather than at setup for a reason: it is the
        only irreversible decision in this integration -- it decides which
        entity ids years of recorder history attach to -- and somebody who
        came to send a reading should never have had to answer it to get
        past a dialog.

        Asked only where there is something to take over. A user who never
        ran `modbus_sungrow.yaml` has no history and no decision, so the
        entry is simply promoted.
        """
        if not DEVICES_MODE_OFFERED:
            return self.async_abort(reason="devices_mode_not_offered")

        # Prefer what the entry already settled. A diagnostics entry made
        # before multi-inverter migration existed has nothing stored, so fall
        # back to asking the YAML package -- which may well still be installed
        # here, since a diagnostics entry never asked anybody to remove it.
        slot = self.config_entry.data.get(CONF_LEGACY_SLOT)
        if slot is None:
            slot = async_legacy_suffix(self.hass, self.config_entry.unique_id) or ""
        self._slot = slot

        known = async_legacy_ids_known(self.hass, slot)
        if not known:
            known = await async_legacy_ids_with_history(self.hass, slot)
        if not known:
            return await self._async_promote(ENTITY_IDS_NEW)

        live = async_legacy_ids_live(self.hass, slot)
        errors: dict[str, str] = {}
        if user_input is not None:
            choice = user_input[CONF_ENTITY_IDS]
            if choice == ENTITY_IDS_MIGRATE and live:
                # The same refusal the setup flow makes, and for the same
                # reason: adoption needs the id free in the state machine as
                # well as the registry, or the registry silently appends `_2`
                # and the history is orphaned.
                errors["base"] = "legacy_package_still_loaded"
            else:
                return await self._async_promote(choice)

        return self.async_show_form(
            step_id="promote",
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

    async def _async_promote(self, entity_ids: str) -> ConfigFlowResult:
        """Rewrite the entry's data and let the reload build the entities.

        `data` rather than `options`, because what an entry is *for* is not a
        preference: it decides whether platforms are forwarded at all, and it
        is the same field the setup flow wrote.
        """
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={
                **self.config_entry.data,
                CONF_MODE: MODE_DEVICES,
                CONF_ENTITY_IDS: entity_ids,
                # Written here as well as by the setup flow, because a
                # promoted entry's claim happens after this and reads it from
                # `data`. Left unresolved it would default to the
                # single-inverter slot, which for a second inverter is another
                # device's history.
                CONF_LEGACY_SLOT: getattr(self, "_slot", "") or "",
            },
        )
        # Updating `data` already schedules a reload, so this only has to end
        # the flow -- with whatever the options page collected on the way
        # here, or the entry's existing options when promotion was reached
        # any other way.
        return self.async_create_entry(
            data=self._pending_options
            if self._pending_options is not None
            else dict(self.config_entry.options)
        )

    @callback
    def _async_polling_schema(self, current: dict[str, int]) -> vol.Schema:
        """Return one interval field per tier.

        Nothing between 1 and 4 seconds is offered. The specification warns
        that writable registers must not be polled frequently through a
        WiNet-S, WiNet-S2 or Logger1000, and 5 seconds is already the YAML
        package's fastest tier -- going lower buys nothing and spends a
        connection the inverter has few of.
        """
        return vol.Schema(
            {
                vol.Required(tier, default=current.get(tier, default)): vol.All(
                    NumberSelector(
                        NumberSelectorConfig(
                            mode=NumberSelectorMode.BOX,
                            min=INTERVAL_NEVER,
                            max=86400,
                            step=1,
                            unit_of_measurement="s",
                        )
                    ),
                    vol.Coerce(int),
                    vol.Any(INTERVAL_NEVER, vol.Range(min=INTERVAL_MINIMUM)),
                )
                for tier, default in DEFAULT_INTERVALS.items()
            }
        )

    @callback
    def _async_tier_table(self, current: dict[str, int]) -> dict[str, str]:
        """Return a markdown table of what each tier actually reads.

        A config-flow form cannot render a data table, so this goes into the
        step description as markdown. It answers the question four bare
        numbers raise and cannot: what am I slowing down?
        """
        rows = [
            "| Tier | Interval | Registers | Includes |",
            "| --- | --- | --- | --- |",
        ]
        for tier, components in TIER_COMPONENTS.items():
            fields = sorted(
                name
                for component in components
                for name in COMPONENTS[component].declared_fields
            )
            interval = current.get(tier, DEFAULT_INTERVALS[tier])
            shown = "**never**" if interval == INTERVAL_NEVER else f"{interval} s"
            examples = ", ".join(name.replace("_", " ") for name in fields[:3])
            rows.append(f"| `{tier}` | {shown} | {len(fields)} | {examples}, … |")
        return {"tiers": "\n".join(rows)}

    @callback
    def _async_load_now(self) -> str:
        """Say what the inverter currently reports the house is using.

        Because that number is the evidence. Somebody reaches this page
        suspecting their load reading is wrong, and a negative value sitting
        on the screen while the sun is up is the symptom itself -- there is no
        clearer way to confirm the page is the right one than to show it.
        """
        runtime = getattr(self.config_entry, "runtime_data", None)
        if runtime is None:
            return "The inverter is not connected, so its load reading cannot be shown."

        device = next(iter(runtime.coordinators.values())).device
        try:
            reported = device.field("load_power")
        except (AttributeError, KeyError):
            reported = None
        if reported is None:
            return "The inverter has not reported a load figure yet."
        if reported < 0:
            return (
                f"Right now this inverter reports a house load of **{reported:.0f} W**."
                " A negative load is what an unmetered generator looks like: the"
                " house appears to be using less than nothing because something is"
                " producing that the inverter cannot see."
            )
        return (
            f"Right now this inverter reports a house load of **{reported:.0f} W**, "
            "which does not include anything it cannot see."
        )

    async def _async_survey_measured(self) -> str:
        """Say what the integration has already worked out for itself.

        So that nobody answers a question that has been measured. The
        transport is the one that matters, and what an owner adds is the half
        no register reaches -- whether a dongle is on its cable or its WiFi,
        which is not determinable and not guessed.

        **It asks register 6100, not 13265**, and the difference is a wrong
        answer rather than a detail. 13265 names the communication module
        that is *fitted*; 6100 says which path this endpoint actually is,
        because Sungrow does not forward the 6100 block through a dongle. A
        house can have both -- and gerd's does. Its own fingerprint records
        `transport: direct_lan`, `6100: answered`, and
        `WINET-SV200.001.00.P043` in the same document, with the owner's note
        saying it outright: "Register 13265 names a WiNet-S on this path too:
        it reports the module that is fitted, not the module in use."

        Keyed on 13265, this told every such house it was behind a dongle,
        which is exactly the answer that steers `survey_transport` -- and
        that field is published and feeds `doc/compatibility.md`.

        Three answers, not two, on the same reasoning as
        `control_test._detect_transport`: a refusal is the transport
        answering, a lost read is not, and a guess is worse than a question
        because this prose exists to stop people answering from guesswork.
        """
        runtime = getattr(self.config_entry, "runtime_data", None)
        if runtime is None:
            return "The inverter is not connected, so nothing has been measured yet."

        device = next(iter(runtime.coordinators.values())).device
        model = device.model or "an unidentified model"

        direct: bool | None
        try:
            await device.async_read_words("input", DIRECT_ONLY_REGISTER, 2)
        except ServerDeviceBusyError:
            direct = None
        except ModbusExceptionError:
            direct = False
        except (ModbusError, HomeAssistantError, TimeoutError, OSError):
            direct = None
        else:
            direct = True

        if direct is True:
            route = (
                "reached through its own LAN port — register 6100 answers, which "
                "no communication module forwards"
            )
        elif direct is False:
            route = (
                "reached through a communication module, so a WiNet-S, WiNet-S2 "
                "or Logger is in the path — register 6100 was refused. Whether it "
                "is using its Ethernet socket or its WiFi is **not** determinable "
                "over Modbus, and that is the part only you can tell us"
            )
        else:
            route = (
                "and the route could not be measured — register 6100 neither "
                "answered nor was refused, which is what a busy link looks like. "
                "A cable answers it and a dongle refuses it, so this one is for "
                "you to tell us"
            )

        fitted = ""
        try:
            module = device.field("communication_module_firmware_version")
        except (AttributeError, KeyError):
            module = None
        if module:
            # Worth saying, and worth saying separately: an owner who knows a
            # dongle is screwed to the wall needs to see that we know too,
            # or a correct "its own LAN port" reads as a mistake.
            fitted = (
                f" A communication module is fitted and names itself **{module}**,"
                " which is a different question from which path this endpoint is:"
                " a house can have a dongle and a cable at once."
            )

        return (
            f"Already measured, so you do not need to tell us: this is **{model}**, "
            f"{route}.{fitted}"
        )

    @callback
    def _async_battery_status(self) -> str:
        """Say what the integration currently thinks the battery will take.

        Written as a statement about *this* installation rather than as
        general advice, because a number a user is asked to confirm is only
        confirmable if they can see what it is and where it came from.
        """
        runtime = getattr(self.config_entry, "runtime_data", None)
        if runtime is None:
            return "The inverter is not connected, so nothing can be read from it."

        device = next(iter(runtime.coordinators.values())).device
        if Capability.BATTERY not in runtime.capabilities:
            return "No battery is connected, so this setting does nothing."

        def value(name: str) -> float | None:
            try:
                raw = device.field(name)
            except (AttributeError, KeyError):
                return None
            return None if raw is None else float(raw)

        capacity = value("battery_capacity_high_precision")
        reported = (
            f"Your battery reports **{capacity} kWh**" if capacity else "Your battery"
        )

        if Capability.SUNGROW_BATTERY in runtime.capabilities:
            model = model_for_capacity(capacity)
            if model is not None:
                return (
                    f"{reported}, which matches a Sungrow **{model.name}**. Its "
                    f"datasheet gives **{model.conservative_w} W** conservatively "
                    f"({model.nominal_w} W nominal), and that is what is used."
                )

        suggestion = power_from_bms(
            value("bms_max_charging_current"), value("battery_voltage")
        )
        if suggestion is not None:
            return (
                f"{reported}, which is not a Sungrow SBR or SBH. Its BMS reports a "
                f"maximum charge current that works out to about "
                f"**{suggestion} W** at the pack's current voltage — which reads "
                "high at a high state of charge, so treat it as a starting point."
            )
        return (
            f"{reported}, and its BMS does not report a maximum charge current, so "
            f"there is nothing to derive one from. Without a value here the "
            f"integration falls back to **{FALLBACK_W} W**, which is the YAML "
            "package's default rather than a recommendation."
        )
