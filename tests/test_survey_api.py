"""Tests for the backend-neutral survey consumer API."""

from modbus_connection import ModbusExceptionError
import pytest

from sungrow_modbus import (
    assemble_document,
    attach_control_test,
    battery_pack_section,
    capability_registers,
    connection_block,
    local_time,
    measured_connection,
    publish_document,
    readings_section,
    wallbox_section,
)
from sungrow_modbus.fingerprint import publishable
from sungrow_modbus.survey import (
    NextStep,
    async_probe_fields,
    async_probe_words,
    async_read_retrying,
    failure_state,
    next_steps,
    summarise,
)


def test_next_steps_are_structured_and_document_derived() -> None:
    document = {
        "connection": {"verdict": "through a communication module (WiNet-S)"},
        "capability_probes": {"one": {"state": "present"}},
        "firmware": {},
        "block_read_test": {
            "never_answered": [{"component": "meter", "register": 5741}],
            "intermittent": [{"component": "battery"}],
        },
        "user_inputs": {"other_inverter": "yes"},
    }

    steps = next_steps(document)

    assert all(isinstance(step, NextStep) for step in steps)
    assert [step.key for step in steps] == [
        "block-read-failure",
        "contention",
        "direct-transport-check",
        "firmware-missing",
        "external-inverter",
    ]
    assert "5741" in steps[0].detail


def test_summary_does_not_require_home_assistant() -> None:
    document = {
        "device": {"serial_anonymized_hashed": "anon-123"},
        "connection": {"verdict": "direct to the inverter's LAN port"},
        "capability_probes": {"probe": {"state": "present"}},
        "firmware": {"inverter": "V1.2.3"},
        "readings": {"values": {"power": 100}},
    }

    text = summarise(document)

    assert "1 registers probed" in text
    assert "anon-123" in text
    assert "V1.2.3" in text


@pytest.mark.asyncio
async def test_async_read_retrying_is_configurable_and_retries_failures() -> None:
    attempts = 0

    async def read(address: int, count: int) -> list[int]:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise TimeoutError
        return [address, count]

    assert await async_read_retrying(read, 10, 2, delay=0) == [10, 2]
    assert attempts == 3


def test_failure_state_distinguishes_refusal_from_no_answer() -> None:
    assert failure_state(ModbusExceptionError(2)) == "refused"
    assert failure_state(TimeoutError()) == "no answer"


def test_connection_block_uses_the_shared_transport_verdict() -> None:
    direct = connection_block("answered", None)
    module = connection_block("refused", "V1.2.3")
    unknown = connection_block("no answer", None)

    assert direct["verdict"] == "direct to the inverter's LAN port"
    assert "communication module" in str(module["verdict"])
    assert str(unknown["verdict"]).startswith("not determined")


def test_publishable_is_case_insensitive_and_blocks_serial_names() -> None:
    assert publishable("battery voltage")
    assert not publishable("Sungrow inverter serial")
    assert not publishable("WALLBOX_SERIAL")


def test_local_time_preserves_fallback_and_applies_zone() -> None:
    assert local_time("2026-09-07T22:00:33+00:00") == "2026-09-08T00:00:33+02:00"
    assert local_time("nonsense") == "nonsense"


def test_capability_registers_never_publish_serial_values() -> None:
    result = capability_registers(
        {"battery voltage": "present", "wallbox serial": "present"},
        {"battery voltage": [123], "wallbox serial": [16690, 13633]},
    )
    assert result["battery voltage"]["values"] == [123]
    assert "values" not in result["wallbox serial"]


def test_assemble_document_keeps_common_privacy_shape() -> None:
    document = assemble_document(
        command_line="home assistant diagnostics",
        read_at="2026-10-15T12:00:00Z",
        user_inputs={"reporter": "anonymous"},
        host="192.168.178.35",
        publish_address=False,
        device_type_code="0x0E03",
        output_type=1,
        serial="A123456789",
        firmware={"inverter": "V1"},
        connection={"verdict": "direct"},
        readings={"values": {}},
        capability_probes={},
    )
    assert document["ip_address_last_two_octets"] == "xxx.xxx"
    assert document["device"]["serial_anonymized_hashed"].startswith("anon-")


def test_measured_connection_excludes_owner_testimony() -> None:
    assert measured_connection(
        {"reported_by_hand": "direct_lan", "verdict": "direct"}
    ) == {"verdict": "direct"}


def test_publish_document_adds_optional_privacy_safe_sections() -> None:
    document = publish_document(
        {
            "read_at": "2026-10-15T12:00:00Z",
            "connection": {"reported_by_hand": "direct_lan", "verdict": "direct"},
            "firmware": {"inverter": "V1"},
            "readings": {"values": {"power": 123}},
            "registers": {"wallbox serial": [16690, 13633]},
            "register_dump": {"21200": [16690, 13633]},
            "block_read_test": {"status": "pass"},
        },
        {
            "device_type_code": 0x0E03,
            "output_type": 1,
            "registers": {"wallbox serial": "present"},
        },
        command_line="probe.py capabilities <host>",
        host="192.168.178.35",
        publish_address=False,
        user_inputs={"reporter": "anonymous"},
        serial="A123456789",
    )
    assert document["connection"] == {"verdict": "direct"}
    assert "values" not in document["capability_probes"]["wallbox serial"]
    assert document["block_read_test"] == {"status": "pass"}


def _assembled(**sections: object) -> dict:
    return assemble_document(
        command_line="home assistant diagnostics",
        read_at="2026-10-15T12:00:00Z",
        user_inputs={"reporter": "anonymous"},
        host="192.168.178.35",
        publish_address=False,
        device_type_code="0x0E03",
        output_type=1,
        serial="A123456789",
        firmware={"inverter": "V1"},
        connection={"reported_by_hand": "direct_lan", "verdict": "direct"},
        readings={"values": {}},
        capability_probes={},
        **sections,
    )


def test_both_producers_get_one_section_order() -> None:
    """Home Assistant's `contention` sits after the probes, before the rest."""
    document = _assembled(
        contention={"polled_by": "this Home Assistant, throughout"},
        register_dump={"identity": {"4950": [1, 2]}},
        wallbox={"unit": 3},
        block_read_test={"status": "pass"},
        battery_pack={"unit": 200, "readings": {"values": {"soc": 50}}},
        control_test={"verdict": "pass"},
    )
    keys = list(document)
    assert keys[keys.index("capability_probes") :] == [
        "capability_probes",
        "contention",
        "register_dump",
        "wallbox",
        "block_read_test",
        "battery_pack",
        "control_test",
    ]
    # Testimony never reaches the measured section, whoever the caller is.
    assert document["connection"] == {"verdict": "direct"}


def test_a_pack_with_no_value_read_is_left_out() -> None:
    document = _assembled(
        battery_pack={
            "unit": 200,
            "readings": {"values": {}, "components_that_did_not_answer": ["pack"]},
        }
    )
    assert "battery_pack" not in document


def test_a_control_test_block_carrying_the_serial_is_refused() -> None:
    with pytest.raises(ValueError, match="carries the serial"):
        _assembled(control_test={"note": "A123456789"})

    document = _assembled()
    with pytest.raises(ValueError, match="carries the serial"):
        attach_control_test(document, {"note": "A123456789"}, serial="A123456789")
    assert "control_test" not in document
    attach_control_test(document, {"verdict": "pass"}, serial="A123456789")
    assert document["control_test"] == {"verdict": "pass"}


@pytest.mark.asyncio
async def test_async_probe_fields_returns_raw_values_and_states() -> None:
    class Unit:
        async def read_input_registers(self, address: int, count: int) -> list[int]:
            if address == 10:
                return [42] * count
            raise TimeoutError

        async def read_holding_registers(self, address: int, count: int) -> list[int]:
            return [99] * count

    raw, states = await async_probe_fields(
        Unit(),
        (
            ("answer", "input", 10, 1, "test"),
            ("missing", "input", 11, 1, "test"),
        ),
        attempts=lambda _label: 1,
    )

    assert raw == {"answer": [42]}
    assert states == {"answer": "present", "missing": "no answer"}


@pytest.mark.asyncio
async def test_async_probe_words_announces_each_probe_before_reading() -> None:
    events: list[str] = []

    async def read_words(space: str, address: int, count: int) -> list[int]:
        events.append(f"read {space} {address}")
        if space == "holding":
            raise ModbusExceptionError(2)
        return [7] * count

    raw, states = await async_probe_words(
        read_words,
        (
            ("first", "input", 10, 2, "test"),
            ("second", "holding", 20, 1, "test"),
        ),
        attempts=lambda _label: 1,
        on_probe=lambda label: events.append(f"step {label}"),
    )

    assert events == ["step first", "read input 10", "step second", "read holding 20"]
    assert raw == {"first": [7, 7]}
    assert states == {"first": "present", "second": "refused"}


class _Device:
    """A library device's field surface, with a serial among its fields."""

    def __init__(self, fields: dict[str, object]) -> None:
        self._fields = fields

    @property
    def field_names(self) -> frozenset[str]:
        return frozenset(self._fields) | {"broken"}

    def field(self, name: str) -> object:
        if name == "broken":
            raise KeyError(name)
        return self._fields[name]


def test_readings_section_keeps_unavailable_values_and_failed_components() -> None:
    device = _Device({"b_power": 5, "a_voltage": None, "serial_number": "A123456789"})

    assert readings_section(device, ["meter", "battery"]) == {
        "values": {"a_voltage": None, "b_power": 5},
        "components_that_did_not_answer": ["battery", "meter"],
    }


def test_readings_section_names_what_individual_reads_recovered_and_missed() -> None:
    device = _Device({"b_power": 5, "a_voltage": None})

    report = readings_section(
        device,
        ["meter"],
        salvaged={"a_voltage": 230.1, "b_power": 9, "inverter_serial": "A123456789"},
        unreadable=["c_current", "serial_words"],
    )

    # Recovered values fill gaps only; the component read wins where it had one.
    assert report["values"] == {"a_voltage": 230.1, "b_power": 5}
    assert report["fields_read_individually"] == ["a_voltage", "b_power"]
    assert report["fields_that_did_not_read"] == ["c_current"]


def test_battery_pack_section_is_absent_rather_than_empty() -> None:
    assert battery_pack_section(_Device({"soc": None}), 200) is None
    assert battery_pack_section(_Device({"soc": 51, "health": None}), 2) == {
        "unit": 2,
        "readings": {
            "values": {"health": None, "soc": 51},
            "components_that_did_not_answer": [],
        },
    }


def test_a_failed_battery_component_is_absent_not_unavailable() -> None:
    device = _Device({"soc": 51, "max_cell_voltage": None})

    section = battery_pack_section(
        device,
        2,
        ["sbr_battery_cells (IllegalDataAddressError)"],
        unanswered_fields=["max_cell_voltage"],
    )

    assert section is not None
    assert section["readings"] == {
        "values": {"soc": 51},
        "components_that_did_not_answer": [
            "sbr_battery_cells (IllegalDataAddressError)"
        ],
    }


def test_wallbox_section_carries_only_what_was_read() -> None:
    assert wallbox_section(3, readings={"state": {"value": 1}}) == {
        "unit": 3,
        "readings": {"state": {"value": 1}},
    }
    section = wallbox_section(
        248, readings={}, serial_stand_in="anon-12345678901", path="tls"
    )
    assert section["path"] == "tls"
    assert section["serial_anonymized_hashed"] == "anon-12345678901"
    assert "register_dump" not in section


@pytest.mark.parametrize("state", ["answered", "present", "unavailable"])
def test_any_answer_from_6100_means_the_path_forwards_it(state: str) -> None:
    """A sentinel is still an answer; only a dongle's refusal means a dongle."""
    block = connection_block(state, None)

    assert block["winet_restricted_block_6100"] == "answered"
    assert block["verdict"] == "direct to the inverter's LAN port"


def test_a_refused_6100_means_a_communication_module() -> None:
    block = connection_block("refused", "WINET-SV200.001.00.P028")

    assert block["winet_restricted_block_6100"] == "refused"
    assert block["verdict"].startswith("through a communication module")


@pytest.mark.asyncio
async def test_a_dump_says_which_address_it_waits_on_when_a_block_fails() -> None:
    """The fallback can take a timeout per address; a caller must be able to say so."""
    from sungrow_modbus import dump

    async def read(space: str, address: int, count: int) -> list[int]:
        if count > 1 or address == 101:
            raise ModbusExceptionError(2)
        return [address]

    narrowed: list[tuple[int, int, int]] = []
    result = await dump.async_dump(
        read,
        bands=(("input", 100, 3, "test band"),),
        on_narrow=lambda *args: narrowed.append(args),
    )

    assert narrowed == [(100, 1, 3), (101, 2, 3), (102, 3, 3)]
    assert result["input"] == {"100": 100, "101": None, "102": 102}


@pytest.mark.parametrize(
    ("states", "unit"),
    [
        ({"unit 200 SBR battery module block": "present"}, 200),
        # Forwarded by a WiNet-S to unit 2, where no inverter answers.
        (
            {
                "unit 200 SBR battery module block": "no answer",
                "unit 2 SBR battery module block": "present",
                "unit 2 inverter device type code": "no answer",
            },
            2,
        ),
        # A slave inverter at unit 2 is not the master's pack.
        (
            {
                "unit 2 SBR battery module block": "present",
                "unit 2 inverter device type code": "present",
            },
            None,
        ),
        ({}, None),
    ],
)
def test_the_pack_unit_is_decided_once(states: dict, unit: int | None) -> None:
    from sungrow_modbus import battery_pack_unit

    assert battery_pack_unit(states) == unit


def test_a_wallbox_is_found_through_a_dongle_or_at_its_own_address() -> None:
    from sungrow_modbus import wallbox_unit

    assert wallbox_unit({"unit 3 wallbox serial": "present"}) == 3
    assert wallbox_unit({"unit 248 wallbox serial (direct)": "present"}) == 248
    assert wallbox_unit({"unit 3 wallbox serial": "no answer"}) is None


@pytest.mark.asyncio
async def test_unread_firmware_is_absent_and_empty_firmware_is_none() -> None:
    from sungrow_modbus.fingerprint import FIRMWARE_STRINGS
    from sungrow_modbus.survey import async_read_firmware

    addresses = {name: address for name, _space, address, _count in FIRMWARE_STRINGS}
    text = [int.from_bytes(b"SA", "big"), int.from_bytes(b"P_", "big")]
    text += [int.from_bytes(b"V1", "big")] + [0] * 12

    class Unit:
        async def read_input_registers(self, address: int, count: int) -> list[int]:
            if address == addresses["dsp"]:
                raise ModbusExceptionError(2)
            if address == addresses["battery"]:
                return [0] * count
            return text[:count]

        async def read_holding_registers(self, address: int, count: int):
            raise AssertionError("firmware is input registers")

    firmware = await async_read_firmware(Unit())

    assert "dsp" not in firmware
    assert firmware["battery"] is None
    assert firmware["inverter"] == "SAP_V1"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("raises", "state"),
    [
        (None, "answered"),
        (ModbusExceptionError(2), "refused"),
        (TimeoutError(), "no answer"),
    ],
)
async def test_6100_is_answered_refused_or_unanswered(raises, state) -> None:
    """A dongle refuses 6100; a lost link says nothing; never one as the other."""
    from sungrow_modbus.survey import async_read_6100

    class Unit:
        async def read_input_registers(self, address: int, count: int) -> list[int]:
            if raises is not None:
                raise raises
            return [0xFFFF] * count

    assert await async_read_6100(Unit(), attempts=1) == state
