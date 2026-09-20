"""The forms the config flow shows, separated from the flow that shows them.

`config_flow.py` was 2000 lines, and three quarters of what came before its
first class was **not flow logic**: `voluptuous` schemas, the option lists they
offer, and the paragraphs of prose Home Assistant renders above them. Reading
the flow meant scrolling past all of it.

So the data lives here and the decisions live there. The split is along that
line rather than along size -- anything that asks *what happens next* stayed
behind. `_alpha_placeholders` is the case worth naming: it reads
`DEVICES_MODE_OFFERED` at call time precisely so a test can patch the flag on
`config_flow`, and moving it here would quietly put it beyond that patch's
reach while every test still passed.
"""

from __future__ import annotations

from collections.abc import Mapping
from ipaddress import ip_address, ip_network
from typing import Any

import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_PORT
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
    TextSelectorConfig,
)
from sungrow_modbus.fingerprint import (
    OTHER_INVERTER_CLAIMS,
    PROXY_CLAIMS,
    TRANSPORT_CLAIMS,
)

from .const import (
    CONF_ENTITY_IDS,
    CONF_NETWORK,
    CONF_PUBLISH_ADDRESS,
    CONF_REPORTER,
    CONF_SURVEY_BATTERY,
    CONF_SURVEY_COMMENT,
    CONF_SURVEY_DUMP,
    CONF_SURVEY_OTHER_INVERTER,
    CONF_SURVEY_OTHER_INVERTER_DETAIL,
    CONF_SURVEY_POLLERS,
    CONF_SURVEY_PROXY,
    CONF_SURVEY_TRANSPORT,
    CONF_UNIT_ID,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    ENTITY_IDS_MIGRATE,
    ENTITY_IDS_NEW,
    ROLE_SLAVE,
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
    """Return the search form: a range to pick or type.

    **No port.** It asked for one, defaulted to 502, and the honest question
    behind the field -- "which number?" -- has a two-item answer this project
    already knows: `SCAN_PORTS`. A sweep tries both. Somebody whose setup
    really is elsewhere, behind a proxy or a forwarded port, has the manual
    step, which is where a specific address and a specific port belong.

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


def _other_inverter_schema(default: str) -> vol.Schema:
    """Return the "what is it" box, asked only when the answer was yes.

    Free text and published, like the comment field, so the label says to
    keep identifying details out of it. What is wanted is the make and the
    size -- those say *how large* the load error is, which is the whole
    reason the question exists.
    """
    return vol.Schema(
        {
            vol.Optional(
                CONF_SURVEY_OTHER_INVERTER_DETAIL, default=default
            ): TextSelector(),
        }
    )


#: What the greyed controls say, written once and rendered in two places.
#:
#: Both the opening step and the options page's promotion toggle explain the
#: same gate, and a gate explained twice in two wordings is a gate somebody
#: will misread. Markdown, because both slots render through `ha-markdown`.


def _testimony_schema(options: dict[str, Any] | Mapping[str, Any]) -> vol.Schema:
    """Return the questions a survey needs and no register can answer.

    Shared by the diagnostics setup step and the options page's section:
    the same questions in both places, because they produce the same fields
    of the same document and a contributor who answers one should not find
    the other asking something else.

    `suggested_value` rather than `default` on the two dropdowns -- a default
    of "" is injected when the field is left alone and "" is not one of the
    choices, which failed validation for anybody who had never answered.
    """
    return vol.Schema(
        {
            vol.Optional(
                CONF_REPORTER, default=options.get(CONF_REPORTER, "")
            ): TextSelector(),
            vol.Optional(
                CONF_SURVEY_TRANSPORT,
                description={
                    "suggested_value": options.get(CONF_SURVEY_TRANSPORT) or None
                },
            ): SelectSelector(
                SelectSelectorConfig(
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="survey_transport",
                    options=list(TRANSPORT_CLAIMS),
                )
            ),
            vol.Optional(
                CONF_SURVEY_PROXY,
                description={"suggested_value": options.get(CONF_SURVEY_PROXY) or None},
            ): SelectSelector(
                SelectSelectorConfig(
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="survey_proxy",
                    options=list(PROXY_CLAIMS),
                )
            ),
            vol.Optional(
                CONF_SURVEY_POLLERS, default=options.get(CONF_SURVEY_POLLERS, "")
            ): TextSelector(),
            # Yes or no here, and *what it is* only after a yes, on a step of
            # its own. A config flow form cannot show a field conditionally --
            # there is no re-render on change, the whole form is built before
            # it is sent -- so the choice is between a text box that sits
            # there empty for everybody with one inverter, or a second step
            # for the few who have two. The second step is the better trade:
            # it costs a click to the people the question is actually about.
            vol.Optional(
                CONF_SURVEY_OTHER_INVERTER,
                description={
                    "suggested_value": options.get(CONF_SURVEY_OTHER_INVERTER) or None
                },
            ): SelectSelector(
                SelectSelectorConfig(
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="survey_other_inverter",
                    options=list(OTHER_INVERTER_CLAIMS),
                )
            ),
            vol.Optional(
                CONF_SURVEY_BATTERY, default=options.get(CONF_SURVEY_BATTERY, "")
            ): TextSelector(),
            vol.Optional(
                CONF_SURVEY_COMMENT, default=options.get(CONF_SURVEY_COMMENT, "")
            ): TextSelector(TextSelectorConfig(multiline=True)),
            # **On by default, and still a question.** Only the last two
            # octets ever reach a document -- the third is what separates one
            # contributor's network from another's and never leaves the
            # machine -- and what the tail buys is being able to tell four
            # similar-looking files from one house apart: a master, a slave
            # and two dongles otherwise produce four documents that look
            # alike. The box is on the screen and can be cleared before
            # submitting, which is what makes it permission rather than an
            # assumption; a document from somebody who cleared it reads
            # `xxx.xxx` and is complete rather than damaged.
            vol.Required(
                CONF_PUBLISH_ADDRESS,
                default=options.get(CONF_PUBLISH_ADDRESS, True),
            ): BooleanSelector(),
            # Last, and off, because it is the expensive one: the survey is
            # two seconds without it and about five minutes with it. Asked
            # in the same breath as the testimony because it is the same
            # decision -- whether to spend something on this project -- and
            # because a contributor who has been asked for a dump by name
            # should find it where they were already answering questions.
            vol.Required(
                CONF_SURVEY_DUMP,
                default=options.get(CONF_SURVEY_DUMP, True),
            ): BooleanSelector(),
        }
    )


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
            direct = entry.get("direct")
            notes.append(
                "the inverter's own LAN port"
                if direct is True
                else "through a WiNet-S or Logger"
                if direct is False
                else "route not measured -- 6100 neither answered nor refused"
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
                # `is False` for every address, not merely falsy: an
                # undetermined route is not evidence of a dongle, and calling
                # two addresses one dongle on the strength of two failed reads
                # is the same mistake in a second place.
                if all(found[other].get("direct") is False for other in hosts):
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
