"""Registers are read by name, and nothing reads one by a bare number.

`sungrow_modbus.addresses` is where a register's location is decided: a field
the map knows is looked up in the map, and the few it does not know are
constants there. The survey scripts, which cannot import the library, get the
same names from `scan_plan.json`. This file holds the two to each other and
keeps new literal addresses out of the code.

Tests are the exception, deliberately. A fixture that models a device should
carry the specification's numbers, not borrow the code's, or it tests the code
against itself -- the same reason the control test's leg B scale is typed by
hand.
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

import pytest

from sungrow_modbus.addresses import (
    DIRECT_ONLY_PROBE,
    IHOMEMANAGER_PROTOCOL,
    IHOMEMANAGER_TYPE,
    WALLBOX_SERIAL,
    Address,
    device_components,
    field_address,
    reg,
)

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "sungrow_scan"))

import portable  # noqa: E402

#: The code that must not read a register by a literal address.
CHECKED = (
    REPO / "src" / "sungrow_modbus",
    REPO / "custom_components" / "sungrow_modbus",
    REPO / "scripts",
)

#: Where the numbers are *supposed* to enter: the module that names them, and
#: the generators and the simulator, whose job is to turn documents into code.
EXEMPT = {
    "addresses.py",
    "registers.py",
    "battery_registers.py",
    "wallbox_registers.py",
    "generate_entity_map.py",
    "gen_simulator_registers.py",
    "simulator.py",
}

#: Read and write calls, and which positional argument is the address.
ADDRESS_ARGUMENT = {
    "read_input_registers": 0,
    "read_holding_registers": 0,
    "write_register": 0,
    "write_registers": 0,
    "async_write_word": 0,
    "async_read_words": 1,
    "_async_read_retrying": 1,
}


def _literal_addresses() -> list[str]:
    """Every read or write whose address is an integer literal."""
    found = []
    for root in CHECKED:
        for path in sorted(root.rglob("*.py")):
            if path.name in EXEMPT:
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if not isinstance(node, ast.Call):
                    continue
                name = getattr(node.func, "attr", None) or getattr(
                    node.func, "id", None
                )
                where = f"{path.relative_to(REPO)}:{node.lineno}"
                if name == "Address":
                    found.append(f"{where} constructs an Address outside addresses.py")
                    continue
                index = ADDRESS_ARGUMENT.get(name or "")
                if index is None or len(node.args) <= index:
                    continue
                argument = node.args[index]
                if isinstance(argument, ast.Constant) and isinstance(
                    argument.value, int
                ):
                    found.append(f"{where} {name}({argument.value}, ...)")
    return found


def test_no_register_is_read_by_a_literal_address() -> None:
    """Name it in `addresses`, or look it up with `field_address`."""
    assert _literal_addresses() == []


#: The register maps, where every field is declared, and the calls that
#: declare one.
MAPS = (
    REPO / "src" / "sungrow_modbus" / "registers.py",
    REPO / "src" / "sungrow_modbus" / "components.py",
    REPO / "src" / "sungrow_modbus" / "battery_registers.py",
    REPO / "src" / "sungrow_modbus" / "wallbox_registers.py",
)
FIELD_FACTORIES = {
    "integer",
    "gauge",
    "int32",
    "uint32",
    "string",
    "NumberField",
    "AsymmetricNumberField",
}


def _undeclared_fields() -> list[str]:
    """Every field in a map whose address is not written as `reg(<number>)`."""
    found = []
    for path in MAPS:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not (
                isinstance(node, ast.Call)
                and getattr(node.func, "id", None) in FIELD_FACTORIES
                and node.args
            ):
                continue
            first = node.args[0]
            if not (
                isinstance(first, ast.Call)
                and getattr(first.func, "id", None) == "reg"
                and len(first.args) == 1
                and isinstance(first.args[0], ast.Constant)
            ):
                found.append(f"{path.relative_to(REPO)}:{node.lineno}")
    return found


def test_every_map_declares_by_register_number() -> None:
    """A map says `reg(13001)`, the specification's number, never `13000`.

    Mixed conventions are the failure this prevents: one field written as a
    protocol address among fields written as register numbers is off by one,
    reads its neighbour, and decodes to something plausible.
    """
    assert _undeclared_fields() == []


def test_a_register_number_is_one_above_its_address() -> None:
    """The one conversion, and it refuses a number the document never uses."""
    assert reg(13001) == 13000
    with pytest.raises(ValueError):
        reg(0)


def test_an_address_says_both_numbers() -> None:
    """The protocol address and the register number are one apart, always.

    The confusion this settles ran through logs and documents for weeks:
    13073 in a traceback, 13074 in the specification, both correct.
    """
    where = Address("holding", 13073, 1)

    assert where.register == 13074
    assert str(where) == "holding register 13074 (address 13073)"


@pytest.mark.parametrize(
    ("name", "device", "expected"),
    [
        # Specification numbers, typed from the document rather than the map.
        ("communication_module_firmware_version", "inverter", ("input", 13264, 15)),
        ("device_type_code", "inverter", ("input", 4999, 1)),
        ("serial_number", "inverter", ("input", 4989, 10)),
        ("voltage", "battery", ("input", 10740, 1)),
        ("model_name", "wallbox", ("input", 21215, 5)),
    ],
)
def test_a_mapped_field_is_where_the_specification_says(
    name: str, device: str, expected: tuple[str, int, int]
) -> None:
    """The lookup against the document, not against itself."""
    assert tuple(field_address(name, device)) == expected  # type: ignore[arg-type]


def test_a_name_on_two_devices_needs_the_device() -> None:
    """An inverter and a wallbox both have a device type code, apart."""
    assert field_address("device_type_code") != field_address(
        "device_type_code", "wallbox"
    )


def test_an_unknown_name_is_refused() -> None:
    """A typo must fail loudly, not read address zero."""
    with pytest.raises(KeyError):
        field_address("no_such_field")


def test_the_survey_finds_every_field_where_the_library_does() -> None:
    """The plan's name lookup and the library's agree on every field.

    Two routes to one answer, one of which runs on bare Python. If they part,
    the survey reads a different register from the one the integration polls,
    and every document it writes describes the wrong thing.
    """
    plan = portable.load_plan()
    device_of = {
        component: device
        for device, components in device_components().items()
        for component in components
    }
    for row in plan["fields"]:
        device = device_of[row["component"]]
        assert portable.address(plan, row["name"], device) == tuple(
            field_address(row["name"], device)
        ), row["name"]


@pytest.mark.parametrize(
    ("name", "where"),
    [
        ("direct_only_probe", DIRECT_ONLY_PROBE),
        ("ihomemanager_type", IHOMEMANAGER_TYPE),
        ("ihomemanager_protocol", IHOMEMANAGER_PROTOCOL),
        ("wallbox_serial", WALLBOX_SERIAL),
    ],
)
def test_the_survey_names_the_unmapped_registers_as_the_library_does(
    name: str, where: Address
) -> None:
    """The registers no component maps reach the survey under the same name."""
    assert portable.address(portable.load_plan(), name) == tuple(where)
