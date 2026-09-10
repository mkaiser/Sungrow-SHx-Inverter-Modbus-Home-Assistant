"""The portable decoder must agree with the library, field for field.

`scripts/sungrow_scan/` is handed to contributors as a zip, so it cannot
import `sungrow_modbus` -- it decodes registers itself, from the description
in `scan_plan.json`. That makes two decoders for one job, which is a liability
the whole project otherwise avoids: `layout.py` exists because *one*
reimplementation of the block plan agreed with the library by luck.

So the second decoder is not trusted, it is checked. Every field in the map is
decoded both ways over the simulator's committed register seed, and the values
must be identical -- not close, identical, because a fingerprint's value is
compared against other fingerprints and a rounding difference in the tenth
field would be invisible and wrong.

The seed is the right corpus: `scripts/gen_simulator_registers.py` derives it
from the YAML package, so it covers every ported address, and
`tests/test_registers_decode.py` already drives the library against it.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "sungrow_scan"))

from portable import (  # noqa: E402
    NetworkTooLarge,
    battery_model_for_capacity,
    decode,
    hosts_in,
    model_for,
    network_of,
    present,
)

PLAN = json.loads((REPO / "scripts" / "sungrow_scan" / "scan_plan.json").read_text())
SEED = json.loads((REPO / "scripts" / "simulator_registers.json").read_text())

#: Written to, never read: the library refuses to decode a field it only
#: knows how to write, and the scanner never reads it either.
WRITE_ONLY = {"control"}

FIELDS = [f for f in PLAN["fields"] if f["component"] not in WRITE_ONLY]


def _words(field: dict) -> list[int]:
    """Return the seed's words for one field, padding what it does not seed.

    An unseeded address reads 0 on the simulator, which is what the real
    thing does for a register it has nothing for -- and 0 is a more
    interesting input than a sentinel here, because it exercises the sign
    folding and the scaling rather than short-circuiting on the nan check.
    """
    space = SEED.get(field["space"], {})
    words = []
    for offset in range(field["count"]):
        value = space.get(str(field["address"] + offset), 0)
        words.append(value[0] if isinstance(value, list) else value)
    return words


def test_the_corpus_is_not_empty() -> None:
    """A plan or seed that failed to load would make every test below vacuous."""
    assert len(FIELDS) > 100, len(FIELDS)
    assert SEED.get("input")


@pytest.mark.parametrize("field", FIELDS, ids=lambda f: f["name"])
def test_the_portable_decoder_agrees_with_the_library(field: dict) -> None:
    """Every field in the plan, decoded both ways, compared.

    The component lookup lives in `_library_field` rather than here. It was
    duplicated, and when the SBR's two components entered the plan both
    copies raised `KeyError` -- so a field the plan names but this file
    cannot resolve fails loudly instead of silently going unchecked, which is
    the behaviour to keep.
    """
    words = _words(field)
    theirs = _library_field(field).decode(words)
    mine = decode(field, words)

    assert mine == theirs, (
        f"{field['name']}: portable decoded {mine!r}, the library {theirs!r} "
        f"from {words!r}"
    )
    assert type(mine) is type(theirs), (
        f"{field['name']}: portable returned {type(mine).__name__}, "
        f"the library {type(theirs).__name__}"
    )


@pytest.mark.parametrize(
    ("words", "field", "expected"),
    [
        # The sentinel is matched before sign folding, or 0x7FFFFFFF becomes a
        # very large positive number instead of "unavailable".
        (
            [0x7FFF, 0xFFFF],
            {
                "kind": "number",
                "word_order": "big",
                "nan": [0x7FFFFFFF],
                "signed": True,
                "scale": 1.0,
                "offset": 0.0,
                "decimals": 0,
            },
            None,
        ),
        # Low word first is how Sungrow sends 32-bit values.
        (
            [0x0002, 0x0000],
            {
                "kind": "number",
                "word_order": "little",
                "nan": [],
                "signed": False,
                "scale": 1.0,
                "offset": 0.0,
                "decimals": 0,
            },
            2,
        ),
        # An unscaled integer stays an integer.
        (
            [1234],
            {
                "kind": "number",
                "word_order": "big",
                "nan": [],
                "signed": False,
                "scale": 1.0,
                "offset": 0.0,
                "decimals": 0,
            },
            1234,
        ),
        # A negative signed 16-bit value.
        (
            [0xFFFF],
            {
                "kind": "number",
                "word_order": "big",
                "nan": [],
                "signed": True,
                "scale": 1.0,
                "offset": 0.0,
                "decimals": 0,
            },
            -1,
        ),
        # A string decodes to "" here; turning that into "no reading" is
        # `present`'s job, a layer up, exactly as in the library.
        ([0, 0, 0], {"kind": "string"}, ""),
    ],
)
def test_the_cases_worth_naming(words, field, expected) -> None:
    """The four decodings that have each been got wrong somewhere before."""
    assert decode(field, words) == expected


@pytest.mark.parametrize("field", FIELDS, ids=lambda f: f["name"])
def test_present_agrees_with_the_library_one_layer_up(field: dict) -> None:
    """The seam above the decoder, which is where an empty string becomes None.

    Checked separately from the decoder so a disagreement says which layer is
    wrong. The first version of the portable decoder did both jobs at once and
    disagreed with the library on four firmware strings -- correct answer,
    wrong layer, and impossible to see from a single comparison.
    """
    from sungrow_modbus.model import present as library_present

    words = _words(field)
    assert present(decode(field, words)) == library_present(
        _library_field(field).decode(words)
    )


def _library_field(field: dict):
    """Return the library's own field object for one plan entry.

    Every component the plan can name, including the two that are not on the
    inverter's unit at all. Those are looked up here rather than skipped
    because this file is the *whole* mitigation for having a second decoder:
    a field the equality test cannot find is a field where the two
    implementations are free to disagree, and the SBR's fifteen arrived in
    the plan without a line of decoder being written for them.
    """
    from modbus_connection.mock import MockModbusConnection

    from sungrow_modbus.battery_registers import (
        SbrBatteryCells,
        SbrBatteryModules,
        SbrBatteryPack,
    )
    from sungrow_modbus.components import InverterIdentity
    from sungrow_modbus.registers import COMPONENTS
    from sungrow_modbus.wallbox_registers import COMPONENTS as WALLBOX_COMPONENTS

    named = {
        **COMPONENTS,
        **WALLBOX_COMPONENTS,
        "identity": InverterIdentity,
        "sbr_battery_pack": SbrBatteryPack,
        "sbr_battery_cells": SbrBatteryCells,
        "sbr_battery_modules": SbrBatteryModules,
    }
    unit = MockModbusConnection().for_unit(1)
    return named[field["component"]](unit).resolved_fields[field["name"]].field


def test_the_model_table_names_every_inverter_the_library_knows() -> None:
    """A stale table names the wrong inverter, in the file and its name."""
    from sungrow_modbus.const import DEVICE_TYPES

    for code, name in DEVICE_TYPES.items():
        assert model_for(PLAN, code) == name, f"0x{code:04X}"
    assert model_for(PLAN, None) is None
    assert model_for(PLAN, 0xFFFF) is None, "an unknown code is not a guess"


@pytest.mark.parametrize(
    "capacity",
    # Each rated size, then either side of the tolerance around one of them.
    [None, 0.0, 6.4, 9.6, 12.8, 25.6, 9.2, 9.9, 10.5, 100.0],
)
def test_the_battery_table_matches_the_library_including_its_tolerance(
    capacity,
) -> None:
    """The tolerance is the part worth pinning: it decides a name.

    A pack 0.5 kWh off an SBR096 is not an SBR096, and calling it one would
    hand a third-party battery an SBR's power limits in the document that
    argues for them.
    """
    from sungrow_modbus.battery import model_for_capacity

    theirs = model_for_capacity(capacity)
    mine = battery_model_for_capacity(PLAN, capacity)
    if theirs is None:
        assert mine is None
    else:
        assert mine == {"name": theirs.name, "capacity_kwh": theirs.capacity_kwh}


@pytest.mark.parametrize(
    "network", ["192.168.178.0/24", "10.0.0.0/29", "192.168.1.5/32", "172.16.4.0/23"]
)
def test_the_portable_sweep_lists_the_same_addresses(network: str) -> None:
    """Same addresses in the same order, or a sweep skips somebody's inverter."""
    from sungrow_modbus import hosts_in as library_hosts_in

    assert hosts_in(network) == library_hosts_in(network)


def test_a_network_too_large_to_sweep_is_refused_the_same_way() -> None:
    """Refused arithmetically: the /8 must not be listed before it is rejected."""
    from sungrow_modbus.discovery import NetworkTooLarge as LibraryTooLarge

    with pytest.raises(NetworkTooLarge) as mine:
        hosts_in("10.0.0.0/8")
    with pytest.raises(LibraryTooLarge) as theirs:
        from sungrow_modbus import hosts_in as library_hosts_in

        library_hosts_in("10.0.0.0/8")
    assert str(mine.value) == str(theirs.value)


@pytest.mark.parametrize(
    ("address", "prefix"), [("192.168.178.35", 24), ("10.1.2.3", 16), ("10.1.2.3", 30)]
)
def test_the_portable_network_of_agrees(address: str, prefix: int) -> None:
    from sungrow_modbus import network_of as library_network_of

    assert network_of(address, prefix) == library_network_of(address, prefix)
