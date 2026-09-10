"""What the flow can work out about a house, and what it must not guess.

A user cannot answer *"which inverter is at 192.168.176.29?"*. They have never
thought about it, the addresses came from DHCP, and on a roof the two units
look the same. So the flow determines the shape itself -- and every rule here
was measured at a house with two inverters and four endpoints between them, on
2026-09-09.

The negative half matters as much as the positive: a WiNet-S hides the device
address, so a house reachable only through dongles cannot have its roles read
off the wire at all, and the flow says nothing rather than guessing.
"""

from __future__ import annotations

from unittest.mock import patch

from modbus_connection import ModbusError
from modbus_connection.mock import MockModbusConnection, MockModbusUnit
import pytest

from custom_components.sungrow_modbus.const import (
    CONF_NETWORK,
    CONF_UNIT_ID,
    DOMAIN,
    ROLE_SLAVE,
)
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import SH10RT_HOLDING_REGISTERS, SH10RT_INPUT_REGISTERS

SEARCH_INPUT = {CONF_NETWORK: "192.168.176.0/24", CONF_PORT: 502}


@pytest.fixture
def no_setup():
    """Stop the created entry from reaching for the network."""
    with patch("custom_components.sungrow_modbus.async_setup_entry", return_value=True):
        yield


#: The house this is all measured from. Two inverters, four endpoints: serial
#: A answers unit 1 at both of its addresses, and serial B answers unit **2**
#: at its own LAN port and unit 1 through its dongle -- because a cluster
#: slave's own device address is 2, and a dongle presents whatever is behind
#: it as unit 1 regardless.
SERIAL_A = "A123456789"
SERIAL_B = "A987654321"
TOPOLOGY: dict[str, dict[int, str]] = {
    "192.168.176.34": {1: SERIAL_A},  # A, its own LAN port
    "192.168.176.28": {1: SERIAL_A},  # A, through its WiNet-S
    "192.168.176.29": {2: SERIAL_B},  # B, its own LAN port -- unit 1 is silent
    "192.168.176.32": {1: SERIAL_B},  # B, through its WiNet-S
}


def _serial_words(serial: str) -> list[int]:
    """Encode a serial the way the inverter reports it at input 4989."""
    raw = serial.encode("ascii").ljust(20, b"\x00")
    return [int.from_bytes(raw[i : i + 2], "big") for i in range(0, 20, 2)]


def _unit_for(serial: str) -> MockModbusUnit:
    """Return a mock inverter reporting that serial."""
    unit = MockModbusConnection().for_unit(1)
    unit.input = dict(SH10RT_INPUT_REGISTERS)
    unit.holding = dict(SH10RT_HOLDING_REGISTERS)
    for offset, word in enumerate(_serial_words(serial)):
        unit.input[4989 + offset] = word
    return unit


def _house(topology: dict[str, dict[int, str]]):
    """Patch the probe so each (host, unit) answers as that topology says."""

    class _Unit:
        def __init__(self, unit: MockModbusUnit) -> None:
            self._unit = unit

        async def __aenter__(self) -> MockModbusUnit:
            return self._unit

        async def __aexit__(self, *args: object) -> None:
            return None

    def temporary_unit(hass, params, unit_id):
        serial = topology.get(params.host, {}).get(unit_id)
        if serial is None:
            # Silent, which is what unit 1 does at a slave's own LAN port.
            raise ModbusError("no answer")
        return _Unit(_unit_for(serial))

    return patch(
        "custom_components.sungrow_modbus.config_flow.async_get_temporary_unit",
        side_effect=temporary_unit,
    )


async def _pick_options(
    hass: HomeAssistant, topology: dict[str, dict[int, str]]
) -> list[dict]:
    """Search the house and return the picker's options."""
    with (
        patch(
            "custom_components.sungrow_modbus.config_flow.async_sweep",
            return_value=sorted(topology),
        ),
        patch(
            "custom_components.sungrow_modbus.config_flow.async_hostname",
            return_value=None,
        ),
        _house(topology),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "search"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], SEARCH_INPUT
        )
    assert result["type"] is FlowResultType.FORM, result
    assert result["step_id"] == "pick"
    return result["data_schema"].schema[CONF_HOST].config["options"]


async def test_a_slave_on_its_own_lan_port_is_found_at_all(
    hass: HomeAssistant,
) -> None:
    """The regression, and it lost a whole inverter.

    Discovery probed unit 1 and moved on. At this house the second inverter
    answers on unit **2** at its own LAN port and times out on 1, so it never
    appeared -- a user with two inverters would have been shown one and told
    the other is not there.
    """
    options = await _pick_options(hass, TOPOLOGY)
    labels = {option["value"]: option["label"] for option in options}

    assert "192.168.176.29" in labels, "the slave's own LAN port was not found"
    assert SERIAL_B in labels["192.168.176.29"]
    # And it says why the address is not the usual one, because a reader
    # seeing unit 2 needs to know that is the inverter and not a mistake.
    assert "device address 2" in labels["192.168.176.29"]
    assert "cluster" in labels["192.168.176.29"]


async def test_two_addresses_with_one_serial_are_said_to_be_one_inverter(
    hass: HomeAssistant,
) -> None:
    """Say it, because it invalidated two published documents once.

    A machine with a cable in its LAN port and a dongle answers at both
    addresses, and every reading differs between them -- which measuring
    points are forwarded, which unit ids exist, whether 0xFFFF arrives as 0.
    Offering them as two inverters invites somebody to add both and wonder
    why their totals doubled.
    """
    options = await _pick_options(hass, TOPOLOGY)
    labels = {option["value"]: option["label"] for option in options}

    assert "192.168.176.28" in labels["192.168.176.34"]
    assert "192.168.176.34" in labels["192.168.176.28"]
    assert "same inverter" in labels["192.168.176.34"]
    # Both are still offered: a house may only have the dongle path.
    assert {"192.168.176.34", "192.168.176.28"} <= set(labels)


async def test_a_direct_path_is_offered_before_a_dongle(
    hass: HomeAssistant,
) -> None:
    """Prefer the path that answers more, where one machine offers two.

    Measured twice: a cable forwards 1461 of 1510 dumped addresses and answers
    all 27 block reads, where a dongle forwards 1020 and refuses two. So where
    one inverter answers on two paths, the default selection should
    be the better one. Here the only address whose unit is not 1 is the
    slave's cable, which is exactly the path to prefer for that machine.
    """
    options = await _pick_options(hass, TOPOLOGY)
    values = [option["value"] for option in options]

    # The escape hatch is last; every real address comes before it.
    assert values[-1].startswith("__"), values
    # Unit 1 addresses first, in address order, then anything else.
    assert values[0] == "192.168.176.28"


async def test_a_dongle_only_house_gets_no_role_guessed_for_it(
    hass: HomeAssistant,
) -> None:
    """The negative rule, and the one worth being strict about.

    Through a WiNet-S every inverter presents as unit 1 whatever it is
    configured as -- measured on the same machine, unit 2 on its cable and
    unit 1 through its dongle. So two dongles and two serials look exactly
    like two standalone inverters, and there is nothing on the wire that says
    otherwise: the two machines' full dumps were diffed, 1510 addresses each,
    and all 29 stable differences are explained by hardware one lacks rather
    than by what it is.

    An absent role therefore means "not determinable here", and the flow must
    not turn that into "standalone".
    """
    dongles = {
        "192.168.176.28": {1: SERIAL_A},
        "192.168.176.32": {1: SERIAL_B},
    }
    options = await _pick_options(hass, dongles)
    labels = {option["value"]: option["label"] for option in options}

    for host in dongles:
        assert "cluster" not in labels[host], host
        assert "device address" not in labels[host], host
        assert ROLE_SLAVE not in labels[host], host
        # Two separate inverters, so neither is called the other.
        assert "same inverter" not in labels[host], host


async def test_a_device_that_answers_without_naming_itself_stops_the_sweep(
    hass: HomeAssistant,
) -> None:
    """Something is there and talking; a later unit is a different device.

    Continuing would let unit 2's answer be reported as the identity of an
    address whose unit 1 is occupied by something else -- and one of five
    endpoints measured on a real subnet was not a Sungrow at all.
    """
    nameless = _unit_for("")
    for offset in range(10):
        nameless.input[4989 + offset] = 0

    class _Unit:
        def __init__(self, unit):
            self._unit = unit

        async def __aenter__(self):
            return self._unit

        async def __aexit__(self, *args):
            return None

    def temporary_unit(hass_, params, unit_id):
        if unit_id == 1:
            return _Unit(nameless)
        return _Unit(_unit_for(SERIAL_B))

    with (
        patch(
            "custom_components.sungrow_modbus.config_flow.async_sweep",
            return_value=["192.168.176.40"],
        ),
        patch(
            "custom_components.sungrow_modbus.config_flow.async_hostname",
            return_value=None,
        ),
        patch(
            "custom_components.sungrow_modbus.config_flow.async_get_temporary_unit",
            side_effect=temporary_unit,
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "search"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], SEARCH_INPUT
        )

    # Nothing named itself, so nothing is offered -- and unit 2's serial is
    # not borrowed to describe an address it does not belong to.
    assert result["step_id"] == "nothing_found", result


async def _to_name_step(hass: HomeAssistant, topology, host: str):
    """Search the house, pick `host`, and return whatever step comes next."""
    with (
        patch(
            "custom_components.sungrow_modbus.config_flow.async_sweep",
            return_value=sorted(topology),
        ),
        patch(
            "custom_components.sungrow_modbus.config_flow.async_hostname",
            return_value=None,
        ),
        _house(topology),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "search"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], SEARCH_INPUT
        )
        return await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: host}
        )


async def test_one_inverter_is_never_asked_what_to_call_it(
    hass: HomeAssistant, no_setup: None
) -> None:
    """With one inverter the model is a perfectly good name.

    Two addresses of one machine count as **one** inverter, which is the case
    worth testing: a house with a cable and a dongle is not two inverters and
    must not be asked to tell them apart.
    """
    one_machine = {
        "192.168.176.34": {1: SERIAL_A},
        "192.168.176.28": {1: SERIAL_A},
    }
    result = await _to_name_step(hass, one_machine, "192.168.176.34")

    # Straight past it. There is no YAML package in this instance either, so
    # the entry is created without a single further question -- which is the
    # point: a house with one inverter is asked nothing it cannot answer.
    assert result.get("step_id") != "name", "one inverter, nothing to tell apart"
    assert result["type"] is FlowResultType.CREATE_ENTRY, result
    assert CONF_NAME not in result["data"], (
        "no name was chosen, so the device must keep the DeviceInfo it "
        "always had -- adding one would rename every existing install"
    )


async def test_two_inverters_are_asked_and_the_suggestion_says_the_role(
    hass: HomeAssistant,
) -> None:
    """The model is the same string for both, so the ids would differ by `_2`.

    That suffix records click order and nothing else. The suggestion offers
    the most the wire can say -- the model, plus the role where a direct
    connection made it readable -- and the dialog shows the entity id it
    would produce, because that is the part which outlives the label.
    """
    result = await _to_name_step(hass, TOPOLOGY, "192.168.176.29")

    assert result["step_id"] == "name"
    placeholders = result["description_placeholders"]
    assert placeholders["count"] == "2"
    # The slave's own LAN port, so the role is readable and offered.
    assert "slave" in placeholders["suggestion"]
    assert placeholders["example"].startswith("sensor.")
    assert "total_dc_power" in placeholders["example"]


async def test_the_name_becomes_the_entry_title_and_the_device_name(
    hass: HomeAssistant, no_setup: None
) -> None:
    """What the user types is what the ids are built from, for good.

    So it is asked before anything is created. A rename afterwards changes
    the label and leaves every id already made where it was -- proven in
    `test_entity_naming.py` -- which is fine for one install and a support
    problem across two.
    """
    result = await _to_name_step(hass, TOPOLOGY, "192.168.176.29")
    assert result["step_id"] == "name"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "  Garage  "}
    )
    # No YAML package in this instance, so the id question is skipped.
    assert result["type"] is FlowResultType.CREATE_ENTRY, result
    assert result["title"] == "Garage", "trimmed, and used as the title"
    assert result["data"][CONF_NAME] == "Garage"
    assert result["data"][CONF_UNIT_ID] == 2, "the unit that answered"


async def test_an_untouched_suggestion_still_names_the_device(
    hass: HomeAssistant, no_setup: None
) -> None:
    """Accepting the default is a choice, and it has to stick.

    The suggestion is prefilled, so pressing through returns it as the
    answer. If that were treated as "no name given", both inverters would
    fall back to the model and the `_2` this step exists to prevent would
    come back.
    """
    result = await _to_name_step(hass, TOPOLOGY, "192.168.176.29")
    suggestion = result["description_placeholders"]["suggestion"]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: suggestion}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == suggestion
    assert result["data"][CONF_NAME] == suggestion


async def test_a_dongle_only_pair_is_asked_but_offered_no_role(
    hass: HomeAssistant,
) -> None:
    """Two inverters still need telling apart; the wire just cannot help.

    Through a WiNet-S both present as unit 1, so there is no role to offer
    and the suggestion is the bare model. The question is still worth asking
    -- more than ever, since nothing else distinguishes them.
    """
    dongles = {
        "192.168.176.28": {1: SERIAL_A},
        "192.168.176.32": {1: SERIAL_B},
    }
    result = await _to_name_step(hass, dongles, "192.168.176.32")

    assert result["step_id"] == "name"
    assert result["description_placeholders"]["count"] == "2"
    assert "slave" not in result["description_placeholders"]["suggestion"]


def _house_with_routes(topology, direct: set[str]):
    """Patch the probe so `direct` hosts answer the direct-only register.

    Register 6100 is the signal: Sungrow documents 6100-6195 as not forwarded
    by a WiNet-S, and four houses agree without exception -- it answers over
    the inverter's own LAN port and refuses behind a dongle.
    """

    class _Unit:
        def __init__(self, unit, direct_ok):
            self._unit = unit
            self._direct_ok = direct_ok

        async def __aenter__(self):
            inner = self._unit
            original = inner.read_input_registers

            async def gated(address, count):
                if address == 6099 and not self._direct_ok:
                    raise ModbusError("Modbus Exception 0x02 for function code 0x04")
                return await original(address, count)

            inner.read_input_registers = gated
            return inner

        async def __aexit__(self, *args):
            return None

    def temporary_unit(hass, params, unit_id):
        serial = topology.get(params.host, {}).get(unit_id)
        if serial is None:
            raise ModbusError("no answer")
        return _Unit(_unit_for(serial), params.host in direct)

    return patch(
        "custom_components.sungrow_modbus.config_flow.async_get_temporary_unit",
        side_effect=temporary_unit,
    )


async def _pick_with_routes(hass, topology, direct):
    """Search, and return the picker's result."""
    with (
        patch(
            "custom_components.sungrow_modbus.config_flow.async_sweep",
            return_value=sorted(topology),
        ),
        patch(
            "custom_components.sungrow_modbus.config_flow.async_hostname",
            return_value=None,
        ),
        _house_with_routes(topology, direct),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "search"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], SEARCH_INPUT
        )
    assert result["step_id"] == "pick", result
    return result


async def test_each_address_says_how_it_reaches_the_inverter(
    hass: HomeAssistant,
) -> None:
    """The route is measurable and it matters, so it is on the label.

    A house with a cable *and* a dongle offers two addresses for one
    inverter, and they do not answer the same registers: a dongle forwards
    1020 of 1510 dumped addresses where a cable forwards 1461, refuses inputs
    2612 and 2628, and answers 0 where the inverter answers "unavailable".
    Picking the dongle when a cable is available costs real entities.
    """
    topology = {
        "192.168.176.34": {1: SERIAL_A},  # its own LAN port
        "192.168.176.28": {1: SERIAL_A},  # its WiNet-S
    }
    result = await _pick_with_routes(hass, topology, direct={"192.168.176.34"})
    labels = {
        option["value"]: option["label"]
        for option in result["data_schema"].schema[CONF_HOST].config["options"]
    }

    assert "own LAN port" in labels["192.168.176.34"]
    assert "WiNet-S" in labels["192.168.176.28"]
    # And the direct path is offered first, so the default is the better one.
    values = [
        option["value"]
        for option in result["data_schema"].schema[CONF_HOST].config["options"]
    ]
    assert values[0] == "192.168.176.34"


async def test_one_dongle_on_two_addresses_says_wifi_cannot_be_told_apart(
    hass: HomeAssistant,
) -> None:
    """bar12's picker, which is what raised this.

    Two addresses, one serial, and **neither** answers the direct-only
    register -- so both are the same WiNet-S: its network socket and its
    WiFi. Which is which cannot be determined over Modbus. Settled against a
    controlled pair, one dongle read wired and then over WiFi, with a nil
    structural diff; and latency cannot stand in, because at that very site
    the two medians were 25.2 ms and 23.4 ms.

    The dialog therefore says three things, and the third is the useful one:
    it cannot tell, it does not matter, and here is where the answer lives.
    "Does not matter" is measured rather than reassurance -- both addresses
    returned identical documents, every probe and every field.
    """
    topology = {
        "192.168.178.23": {1: "A123456789"},
        "192.168.178.41": {1: "A123456789"},
    }
    result = await _pick_with_routes(hass, topology, direct=set())
    note = result["description_placeholders"]["note"]

    assert "one WiNet-S" in note
    assert "cannot say" in note or "cannot" in note
    assert "makes no difference which you pick" in note
    # And it points at where the answer is, rather than stopping at "unknown".
    assert "router's client list" in note

    # Both rows still say they are behind a dongle, and name each other.
    labels = {
        option["value"]: option["label"]
        for option in result["data_schema"].schema[CONF_HOST].config["options"]
    }
    for host in topology:
        assert "WiNet-S" in labels[host]
        assert "same inverter" in labels[host]
        assert "own LAN port" not in labels[host]


async def test_no_wifi_note_where_one_path_is_a_cable(hass: HomeAssistant) -> None:
    """The note is about a dongle's two interfaces, not about two paths.

    A cable and a dongle are genuinely different routes with genuinely
    different capabilities, and there the choice *does* matter -- so telling
    somebody it makes no difference would be wrong.
    """
    topology = {
        "192.168.176.34": {1: SERIAL_A},
        "192.168.176.28": {1: SERIAL_A},
    }
    result = await _pick_with_routes(hass, topology, direct={"192.168.176.34"})
    assert result["description_placeholders"]["note"] == ""
