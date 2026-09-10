"""Config flow for the Sungrow Modbus integration."""

from __future__ import annotations

import asyncio
from ipaddress import ip_address, ip_network
import logging
from typing import Any

from modbus_connection import ModbusError, ModbusTcpParams
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
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)
from homeassistant.util import slugify
from sungrow_modbus import (
    COMPONENTS,
    DEFAULT_INTERVALS,
    DEFAULT_PORT as MODBUS_PORT,
    FALLBACK_W,
    MAX_HOSTS,
    TIER_COMPONENTS,
    Capability,
    NetworkTooLarge,
    SungrowInverter,
    async_hostname,
    async_sweep,
    model_for_capacity,
    network_of,
    power_from_bms,
)
from sungrow_modbus.fingerprint import PROXY_CLAIMS, TRANSPORT_CLAIMS

from .const import (
    AUDIENCE_ADMINS,
    AUDIENCE_USERS,
    CONF_BATTERY_MAX_POWER,
    CONF_ENTITY_IDS,
    CONF_EXTERNAL_PLACEMENT,
    CONF_EXTERNAL_SOURCES,
    CONF_INTERVALS,
    CONF_MODE,
    CONF_NETWORK,
    CONF_PERMISSIONS,
    CONF_PUBLISH_ADDRESS,
    CONF_REGISTER_DUMP,
    CONF_REPORTER,
    CONF_SURVEY_BATTERY,
    CONF_SURVEY_COMMENT,
    CONF_SURVEY_POLLERS,
    CONF_SURVEY_PROXY,
    CONF_SURVEY_TRANSPORT,
    CONF_UNIT_ID,
    DEFAULT_EXTERNAL_PLACEMENT,
    DEFAULT_NAME,
    DEFAULT_PERMISSIONS,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    DOMAIN,
    ENTITY_IDS_MIGRATE,
    ENTITY_IDS_NEW,
    IDENTIFY_UNITS,
    INTERVAL_MINIMUM,
    INTERVAL_NEVER,
    MODE_DEVICES,
    MODE_DIAGNOSTICS,
    PERMISSION_START_STOP,
    PLACEMENT_BEHIND_METER,
    PLACEMENT_SEPARATE,
    ROLE_SLAVE,
)
from .fingerprint import async_build, summarise
from .migration import (
    async_legacy_ids_known,
    async_legacy_ids_live,
    async_legacy_ids_with_history,
)

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
#: Ranges to offer when there is nothing to detect, or when what was detected
#: found nothing.
#:
#: Guesses, and labelled as such in the form -- but not arbitrary ones. These
#: are the factory defaults of the routers this project's users actually have,
#: and `192.168.178.0/24` is first among them because it is the Fritz!Box
#: default and this integration's audience is heavily German. A pick list of
#: five is a different proposition from a blank CIDR field: somebody who does
#: not know what their range is can usually recognise it.
COMMON_NETWORKS = (
    "192.168.178.0/24",
    "192.168.1.0/24",
    "192.168.0.0/24",
    "192.168.2.0/24",
    "10.0.0.0/24",
)


def _network_options(detected: str, tried: list[str]) -> list[SelectOptionDict]:
    """Return the ranges worth offering, best first and nothing repeated.

    What was detected comes first when there is one, then the common
    defaults, and anything already swept is dropped -- offering a range that
    just found nothing is the one option guaranteed to be useless.
    """
    seen: list[str] = []
    for candidate in (detected, *COMMON_NETWORKS):
        if candidate and candidate not in seen and candidate not in tried:
            seen.append(candidate)
    return [
        SelectOptionDict(
            value=network,
            label=(
                f"{network} — this machine's own network"
                if network == detected
                else f"{network} — a common router default"
            ),
        )
        for network in seen
    ]


def _scan_schema(default_network: str, tried: list[str] | None = None) -> vol.Schema:
    """Return the search form: a range to pick or type, and a port.

    A **selector rather than a text box**, so the range is something to
    choose. It still accepts anything typed -- `custom_value=True` -- because
    no list can cover every network, but a user who does not know their range
    in CIDR should not have to produce one from nothing. That is the state
    somebody is in after a sweep of the detected network found nothing, and
    after this integration could not detect one at all, which is what Home
    Assistant in a container looks like.
    """
    options = _network_options(default_network, tried or [])
    return vol.Schema(
        {
            vol.Required(
                CONF_NETWORK,
                default=default_network or (options[0]["value"] if options else ""),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=options,
                    custom_value=True,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(CONF_PORT, default=MODBUS_PORT): vol.All(
                NumberSelector(
                    NumberSelectorConfig(mode=NumberSelectorMode.BOX, min=1, max=65535)
                ),
                vol.Coerce(int),
            ),
        }
    )


#: Shown when the range could be worked out from a network adapter.
_PREFILLED = (
    "The range below is the network Home Assistant is on, which on a home "
    "network is almost always the right one."
)

#: Shown when it could not, which is what a container bridge produces.
#:
#: Home Assistant in Docker with bridge networking sees only its own bridge,
#: and a sweep of that finds nothing however long it runs -- while the
#: inverter stays perfectly reachable, because the bridge forwards outbound
#: traffic. So the honest thing is an empty field and this sentence, rather
#: than a default that looks right and leads nowhere.
_NOT_DETECTED = (
    "**Home Assistant could not work out which network to search.** It is "
    "running in a container that can see only its own virtual network, so "
    "there is nothing here to detect your inverter's range from -- your "
    "inverter is still reachable, it just cannot be guessed at. Type the "
    "range your inverter is on, for example `192.168.1.0/24`; if you do not "
    "know it, the address of any computer on the same network gives it to "
    "you -- replace the last number with 0 and add `/24`."
)

#: Shown when two addresses are one inverter behind one dongle.
#:
#: That is a WiNet-S's Ethernet socket and its WiFi radio, and **which is
#: which cannot be determined over Modbus**. Settled against a controlled
#: pair -- one dongle read wired and then over WiFi -- with a nil structural
#: diff, and latency cannot stand in: measured at four houses, direct-LAN
#: medians run 2.0 to 61.5 ms and dongle medians 24.3 to 48.3, and one
#: house's cable is slower than its own dongle.
#:
#: So the dialog says it cannot tell, says it does not matter, and says where
#: the answer actually lives. "It does not matter" is the load-bearing part
#: and it is measured: the same dongle is on both, and both addresses
#: returned identical documents -- every probe, every field, even the TLS
#: certificate.
_SAME_DONGLE = (
    "\n\n**Two of these are one inverter behind one WiNet-S** — its network "
    "socket and its WiFi, which have separate addresses. Modbus cannot say "
    "which is which: nothing in the protocol reports it, and the round-trip "
    "times are too close to tell apart.\n\nIt makes no difference which you "
    "pick. Both go through the same dongle to the same inverter, and both "
    "answer identically — measured on a dongle read on both of its addresses, "
    "where every register matched. If you want to know anyway, your router's "
    "client list shows them as two devices with different MAC addresses, and "
    "the WiNet-S web interface names the one it is using."
)

#: Shown on a second attempt, so a user can see what has been covered.
_ALREADY_TRIED = (
    "Already searched, and nothing answered as an inverter: **{tried}**. "
    "Pick another range below, or type one. If you do not know it, the "
    "address of any computer on the same network as the inverter gives it "
    "to you -- replace the last number with 0 and add `/24`."
)

#: Ranges Docker and Podman hand out to bridge networks by default.
#:
#: `172.17.0.0/16` is Docker's own bridge and the first of a pool it allocates
#: from `172.16.0.0/12`; Podman uses `10.88.0.0/16`. An address in one of
#: these belongs to the container's own network rather than to the network the
#: inverter is on, so sweeping it finds nothing however long it takes.
#:
#: Deliberately *not* every private range: a great many real home networks are
#: `192.168.x.x` and plenty are `10.x.x.x`, and excluding those would break
#: detection for the installations where it works. What is excluded is the
#: narrow band that is a container bridge and essentially never a house.
CONTAINER_BRIDGES = ("172.16.0.0/12", "10.88.0.0/16")


def _is_container_bridge(address: str) -> bool:
    """Whether this address belongs to a container's own bridge network."""
    try:
        parsed = ip_address(address)
    except ValueError:
        return False
    return any(parsed in ip_network(cidr) for cidr in CONTAINER_BRIDGES)


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
) -> tuple[SungrowInverter, bool]:
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
        try:
            await unit.read_input_registers(DIRECT_ONLY_REGISTER, 2)
        except (ModbusError, HomeAssistantError):
            direct = False
        else:
            direct = True
    return inverter, direct


def _described(found: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Work out what the set of answers means, and say it in the labels.

    Three things a user cannot answer and the wire can, all measured at a
    two-inverter house on 2026-09-09:

    **Two addresses reporting one serial are one inverter.** A machine with a
    cable in its own LAN port and a WiNet-S dongle answers at both, and every
    reading differs between them -- which measuring points are forwarded,
    which unit ids exist, whether 0xFFFF arrives as 0. The identity is the
    serial and only the serial. Both are still offered, because a house may
    only have the dongle, but the direct path is offered **first**: measured
    twice, a cable forwards 1461 of 1510 dumped addresses and answers all 27
    block reads where a dongle forwards 1020 and refuses two.

    **A device address that is not 1 is a cluster slave.** That is what the
    second inverter is configured as, and it is the only role signal the
    protocol carries -- looked for and not found: the two machines' full
    dumps were diffed, 1510 addresses each, and all 29 stable differences are
    explained by hardware the slave lacks rather than by what it *is*.

    **But a dongle hides the address**, so the role is only readable on a
    direct path. Through a WiNet-S every inverter presents as unit 1 whatever
    it is configured as -- the same machine reads unit 2 on its cable and
    unit 1 through its dongle. So a house whose inverters are each reachable
    only through their own dongle cannot have its roles read at all, and this
    says nothing rather than guessing.
    """
    by_serial: dict[str, list[str]] = {}
    for host, entry in found.items():
        by_serial.setdefault(entry["serial"], []).append(host)

    for serial, hosts in by_serial.items():
        for host in hosts:
            entry = found[host]
            model = entry["model"] or DEFAULT_NAME
            notes: list[str] = []
            # How this address reaches the machine, which is measurable and
            # matters: the two routes do not answer the same registers.
            notes.append(
                "the inverter's own LAN port"
                if entry.get("direct")
                else "through a WiNet-S or Logger"
            )
            # The role, where a direct path makes it readable.
            if entry[CONF_UNIT_ID] != DEFAULT_UNIT_ID:
                entry["role"] = ROLE_SLAVE
                notes.append(
                    f"device address {entry[CONF_UNIT_ID]}, so a second"
                    " inverter in a cluster"
                )
            if len(hosts) > 1:
                others = ", ".join(other for other in sorted(hosts) if other != host)
                notes.append(f"the same inverter as {others}")
                # Two addresses, one serial, and **both** behind a dongle: its
                # Ethernet socket and its WiFi radio. Which is which cannot be
                # told from here, and saying so beats leaving somebody to
                # wonder -- settled against a controlled pair, one dongle read
                # wired and then over WiFi, with a nil structural diff, and
                # latency cannot stand in either: at this very site the two
                # medians were 25.2 ms and 23.4 ms.
                #
                # It also does not matter, which is the useful half: the same
                # dongle is on both, and both addresses returned identical
                # documents -- every probe, every field, even the TLS
                # certificate.
                if not any(found[other]["direct"] for other in hosts):
                    entry["same_dongle"] = True
            entry["notes"] = notes
            entry["label"] = " -- ".join(
                [f"{model} at {entry.get('hostname') or host}", *notes]
            )
            # Serial last, and always: it is printed on the unit's label, so
            # it is the one identifier somebody can walk up to the hardware
            # and check. A model and an address mean nothing on a roof.
            entry["label"] += f" (serial {serial})"

    # A direct path first, so the default selection is the better one -- and
    # it is measurably better rather than a preference: measured twice, a
    # cable forwards 1461 of 1510 dumped addresses and answers all 27 block
    # reads, where a dongle forwards 1020, refuses inputs 2612 and 2628, and
    # answers 0 where the inverter answers "unavailable", which fabricates
    # capabilities. Picking the dongle where a cable exists costs entities.
    #
    # This used to sort on the unit id alone, which decided nothing between
    # two addresses both on unit 1 and fell through to the address string --
    # so a house with a cable and a dongle defaulted to whichever happened to
    # sort lower. The route is now read, so it can be used.
    return dict(
        sorted(
            found.items(),
            key=lambda item: (
                not item[1].get("direct"),
                item[1][CONF_UNIT_ID] != DEFAULT_UNIT_ID,
                item[0],
            ),
        )
    )


_LOGGER = logging.getLogger(__name__)

#: Where a contributed reading goes. The compatibility report template asks
#: for exactly what a survey produces, so the form arrives pre-shaped.
SURVEY_ISSUE_URL = (
    "https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant"
    "/issues/new?template=compatibility_report.yml"
)

#: And the route for somebody without a GitHub account, which is most people.
DISCORD_URL = "https://discord.gg/ZvYBejFkm2"


def _async_survey_notice(
    hass: HomeAssistant, entry: ConfigEntry, document: dict[str, Any]
) -> None:
    """Leave the result somewhere it survives the dialog closing.

    A config-flow page is gone the moment it is dismissed, and what it says
    here -- which menu the file is behind, and where to send it -- is needed
    *after* that. A persistent notification is the only surface in Home
    Assistant that keeps a short instruction until somebody acts on it.
    """
    from homeassistant.components import persistent_notification

    persistent_notification.async_create(
        hass,
        title=f"Sungrow survey ready: {entry.title}",
        notification_id=f"{DOMAIN}_survey_{entry.entry_id}",
        message=(
            f"{summarise(document)}\n\n"
            "**To send it:** Settings → Devices & services → Sungrow Modbus "
            "→ the three dots beside this entry → **Download diagnostics**. "
            "The file lands in your browser's downloads.\n\n"
            f"Attach it to [a compatibility report]({SURVEY_ISSUE_URL}) or "
            f"post it on [Discord]({DISCORD_URL}). Nothing was written to "
            "your inverter, and the serial number is replaced by a stand-in "
            "before it reaches the file."
        ),
    )


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
        """
        return self.async_show_menu(
            step_id="user", menu_options=["setup_devices", "setup_diagnostics"]
        )

    async def async_step_setup_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Set up the inverter properly, with entities."""
        self._mode = MODE_DEVICES
        return await self.async_step_find()

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
        self, candidates: list[str], port: int
    ) -> dict[str, dict[str, Any]]:
        """Ask each candidate what it is, keeping only the ones that answer.

        Every candidate unit, not just unit 1. Measured at a two-inverter
        house: the second answers on unit **2** at its own LAN port and times
        out on 1, because a cluster slave's own device address is 2 -- so
        asking only unit 1 reported that inverter absent, and a user would
        have been told their second inverter is not there. Only the rare case
        pays for it: an address with an inverter on unit 1 makes exactly the
        reads it always did.
        """
        found: dict[str, dict[str, Any]] = {}
        for host in candidates:
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
                inverter, _direct = await _async_probe(
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
        # A diagnostics entry creates no entities, so there is nothing for an
        # id to attach to and nothing to migrate. Asking would be worse than
        # pointless: it is the one decision here that cannot be undone
        # casually, and answering it wrongly to get past a dialog is exactly
        # how somebody loses years of history.
        if self._mode == MODE_DIAGNOSTICS:
            return self._async_create(ENTITY_IDS_NEW)

        known = async_legacy_ids_known(self.hass)
        if not known:
            # The registry is the good evidence, but not the only evidence.
            # cleanup_entities.md has told users for years to delete the
            # orphaned entries a removed YAML platform leaves behind, and the
            # recorder keeps their rows regardless. Asking it as well is what
            # stops those users being handed new ids and a stranded history
            # without ever being offered the choice.
            known = await async_legacy_ids_with_history(self.hass)
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
        return self.async_create_entry(title=self._title, data=data)


class SungrowOptionsFlow(OptionsFlow):
    """Settings that can be changed after setup.

    Connection details are not here: changing the host or unit id means
    talking to a different device, which is a reconfigure rather than an
    option.
    """

    def __init__(self) -> None:
        """Start with no survey in flight."""
        #: Answers given on the survey page, held until the flow ends.
        self._testimony: dict[str, Any] = {}
        #: The task reading the inverter, so the progress step can wait on it.
        self._survey_task: asyncio.Task[None] | None = None
        #: What it produced, or why it did not.
        self._document: dict[str, Any] | None = None
        self._survey_error: str | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Offer the things worth changing after setup.

        Built rather than fixed, for one entry in it: a diagnostics-only
        entry has no entities and needs a way to become an ordinary one, and
        offering that to an entry that is already ordinary would be a menu
        item that does nothing.
        """
        options = ["polling", "permissions", "external", "survey", "settings"]
        if self.config_entry.data.get(CONF_MODE, MODE_DEVICES) == MODE_DIAGNOSTICS:
            # First, because it is the only reason somebody with this kind of
            # entry opens this menu.
            options.insert(0, "promote")
        return self.async_show_menu(step_id="init", menu_options=options)

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
        known = async_legacy_ids_known(self.hass)
        if not known:
            known = await async_legacy_ids_with_history(self.hass)
        if not known:
            return await self._async_promote(ENTITY_IDS_NEW)

        live = async_legacy_ids_live(self.hass)
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
            },
        )
        # Updating `data` already schedules a reload, so this only has to end
        # the flow without touching the options.
        return self.async_create_entry(data=dict(self.config_entry.options))

    async def async_step_permissions(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Decide who may do the things that are not entities.

        Which is a short list, and saying so on the screen matters more than
        the setting itself: an owner who comes here expecting to lock down the
        export limit or the EMS mode needs to know that this page cannot do
        that and what does -- Home Assistant checks entity control centrally,
        by user group, before any integration sees the call.
        """
        if user_input is not None:
            permissions = {
                **DEFAULT_PERMISSIONS,
                **self.config_entry.options.get(CONF_PERMISSIONS, {}),
                **user_input,
            }
            return self.async_create_entry(
                data={**self.config_entry.options, CONF_PERMISSIONS: permissions}
            )

        current = {
            **DEFAULT_PERMISSIONS,
            **self.config_entry.options.get(CONF_PERMISSIONS, {}),
        }
        return self.async_show_form(
            step_id="permissions",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        PERMISSION_START_STOP,
                        default=current[PERMISSION_START_STOP],
                    ): SelectSelector(
                        SelectSelectorConfig(
                            mode=SelectSelectorMode.LIST,
                            translation_key="audience",
                            options=[AUDIENCE_ADMINS, AUDIENCE_USERS],
                        )
                    )
                }
            ),
        )

    async def async_step_polling(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Set how often each tier is polled.

        The most useful knob this integration has, because the scarce resource
        is not bandwidth but connections: a Sungrow accepts very few Modbus
        sessions at once, and most reported dropouts are two clients competing
        for one. Slowing a tier, or turning it off, is the cheapest fix there
        is -- and data nobody looks at is the cheapest thing to stop reading.
        """
        errors: dict[str, str] = {}
        current = {
            **DEFAULT_INTERVALS,
            **self.config_entry.options.get(CONF_INTERVALS, {}),
        }

        if user_input is not None:
            current = {tier: int(user_input[tier]) for tier in DEFAULT_INTERVALS}
            if all(value == INTERVAL_NEVER for value in current.values()):
                errors["base"] = "nothing_left_to_poll"
            else:
                return self.async_create_entry(
                    data={**self.config_entry.options, CONF_INTERVALS: current}
                )

        return self.async_show_form(
            step_id="polling",
            data_schema=self._async_polling_schema(current),
            errors=errors,
            description_placeholders=self._async_tier_table(current),
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

    async def async_step_external(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Name a generator the Sungrow cannot see, and say where it sits.

        The one page in this flow that fixes a **wrong number** rather than
        changing a preference. A non-Sungrow inverter on the same supply
        makes `load_power` low by exactly its output, because the inverter
        computes load from its own production and its grid meter -- so the
        figure looks like a measurement and is not one.

        Nothing can be probed here. The inverter cannot see the generator by
        definition, so the placement has to be asked, and asking it is the
        difference between removing an error and introducing one.
        """
        if user_input is not None:
            return self.async_create_entry(
                data={
                    **self.config_entry.options,
                    CONF_EXTERNAL_SOURCES: user_input.get(CONF_EXTERNAL_SOURCES, []),
                    CONF_EXTERNAL_PLACEMENT: user_input[CONF_EXTERNAL_PLACEMENT],
                }
            )

        options = self.config_entry.options
        return self.async_show_form(
            step_id="external",
            data_schema=vol.Schema(
                {
                    # Filtered to power sensors at the picker, which is worth
                    # more than validating afterwards: the unit has to be a
                    # power unit for the sum to mean anything, and a device
                    # class is how Home Assistant knows that before anybody
                    # submits the form.
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
            description_placeholders={"reported_load": self._async_load_now()},
        )

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

    async def async_step_survey(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the testimony a capability survey needs and cannot read.

        Every answer here is optional, and leaving one blank is a real
        answer: the document format distinguishes an empty field -- **the
        question was not put** -- from `unknown`, where it was put and the
        owner did not know. So an untouched page still produces an honest
        document, just a less useful one.

        Why any of it is asked at all: no register reports a battery's make,
        nothing distinguishes a cable from a dongle's Ethernet socket, and a
        Modbus proxy in the path changes what every dropped block means while
        being completely invisible from this end.
        """
        if user_input is not None:
            # Held rather than saved. The survey has to run with these
            # answers in it so the contributor can see what their reading
            # actually found, and options are only persisted when a flow
            # ends -- so the document is built first and the answers are
            # committed by the step that follows.
            self._testimony = dict(user_input)
            return await self.async_step_survey_run()

        options = self.config_entry.options
        return self.async_show_form(
            step_id="survey",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_REPORTER, default=options.get(CONF_REPORTER, "")
                    ): TextSelector(),
                    vol.Optional(
                        CONF_SURVEY_TRANSPORT,
                        default=options.get(CONF_SURVEY_TRANSPORT, ""),
                    ): SelectSelector(
                        SelectSelectorConfig(
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key="survey_transport",
                            options=list(TRANSPORT_CLAIMS),
                        )
                    ),
                    vol.Optional(
                        CONF_SURVEY_PROXY,
                        default=options.get(CONF_SURVEY_PROXY, ""),
                    ): SelectSelector(
                        SelectSelectorConfig(
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key="survey_proxy",
                            options=list(PROXY_CLAIMS),
                        )
                    ),
                    vol.Optional(
                        CONF_SURVEY_POLLERS,
                        default=options.get(CONF_SURVEY_POLLERS, ""),
                    ): TextSelector(),
                    vol.Optional(
                        CONF_SURVEY_BATTERY,
                        default=options.get(CONF_SURVEY_BATTERY, ""),
                    ): TextSelector(),
                    vol.Optional(
                        CONF_SURVEY_COMMENT,
                        default=options.get(CONF_SURVEY_COMMENT, ""),
                    ): TextSelector(TextSelectorConfig(multiline=True)),
                    # Off unless somebody turns it on, every time. The third
                    # octet is what separates one contributor's network from
                    # another's, and a document reading `xxx.xxx` is complete
                    # rather than damaged.
                    vol.Required(
                        CONF_PUBLISH_ADDRESS,
                        default=options.get(CONF_PUBLISH_ADDRESS, False),
                    ): BooleanSelector(),
                }
            ),
            description_placeholders={"measured": self._async_survey_measured()},
        )

    @callback
    def _async_survey_measured(self) -> str:
        """Say what the integration has already worked out for itself.

        So that nobody answers a question that has been measured. The
        transport is the one that matters: register 6100 settles direct
        against dongle 9 times out of 9, and what an owner adds is the half
        no register reaches -- whether a dongle is on its cable or its WiFi,
        which is not determinable and not guessed.
        """
        runtime = getattr(self.config_entry, "runtime_data", None)
        if runtime is None:
            return "The inverter is not connected, so nothing has been measured yet."

        device = next(iter(runtime.coordinators.values())).device
        model = device.model or "an unidentified model"
        try:
            module = device.field("communication_module_firmware_version")
        except (AttributeError, KeyError):
            module = None

        if module:
            route = (
                f"a communication module, which names itself **{module}** — so a "
                "WiNet-S, WiNet-S2 or Logger is in the path. Whether it is using "
                "its Ethernet socket or its WiFi is **not** determinable over "
                "Modbus, and that is the part only you can tell us"
            )
        else:
            route = (
                "no communication module — nothing answered register 13265, which "
                "is what a cable straight into the inverter looks like"
            )
        return (
            f"Already measured, so you do not need to tell us: this is **{model}**, "
            f"reached through {route}."
        )

    async def async_step_survey_run(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Read the inverter, with a spinner, because it takes a moment.

        Nineteen probe reads and five timing reads. On a direct cable that is
        under a second; through a WiNet-S over a VPN it has been fifteen. A
        form that simply closed and left nothing behind was the first version
        of this and it was indefensible -- the user had no way to tell
        whether anything had happened, and the honest answer was that nothing
        had until they went and downloaded diagnostics.
        """
        if self._survey_task is None:
            self._survey_task = self.hass.async_create_task(
                self._async_run_survey(), eager_start=False
            )

        if not self._survey_task.done():
            return self.async_show_progress(
                step_id="survey_run",
                progress_action="running_survey",
                progress_task=self._survey_task,
            )

        return self.async_show_progress_done(next_step_id="survey_result")

    async def _async_run_survey(self) -> None:
        """Build the document and keep it, or keep the failure instead.

        Failures are shown rather than raised. Somebody who has just offered
        to help should be told what went wrong, not dropped back into a menu
        -- and a link that fails here is worth reporting in its own right.
        """
        merged = {**self.config_entry.options, **self._testimony}
        try:
            self._document = await async_build(self.hass, self.config_entry, merged)
        except Exception as err:  # the message is the useful part
            _LOGGER.warning("Survey failed for %s: %s", self.config_entry.title, err)
            self._survey_error = f"{type(err).__name__}: {err}"

    async def async_step_survey_result(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Say what was found, where the file is, and what to do with it.

        The three things missing from the first version, and the third was
        the worst: a contributor who fills in a form and is told nothing has
        no idea whether they have helped, and no idea that the file they are
        being asked for is behind a menu on a different page.
        """
        if user_input is not None:
            if self._document is not None:
                _async_survey_notice(self.hass, self.config_entry, self._document)
            return self.async_create_entry(
                data={**self.config_entry.options, **self._testimony}
            )

        if self._document is None:
            return self.async_show_form(
                step_id="survey_failed",
                data_schema=vol.Schema({}),
                description_placeholders={"error": self._survey_error or "unknown"},
            )

        return self.async_show_form(
            step_id="survey_result",
            data_schema=vol.Schema({}),
            description_placeholders={
                "found": summarise(self._document),
                "issue_url": SURVEY_ISSUE_URL,
                "discord_url": DISCORD_URL,
            },
        )

    async def async_step_survey_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Save the answers anyway, so the attempt is not wasted."""
        return self.async_create_entry(
            data={**self.config_entry.options, **self._testimony}
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Everything that is not a poll interval."""
        if user_input is not None:
            return self.async_create_entry(
                data={**self.config_entry.options, **user_input}
            )

        options = self.config_entry.options
        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
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
            description_placeholders={"battery_status": self._async_battery_status()},
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
