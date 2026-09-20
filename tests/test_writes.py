"""The write table cannot drift from the sources it was read out of.

Milestone 3 is being taken in slices, safest first, and every bound in
`scripts/writes.py` was read from two sources that agree: the YAML package's
own `number:` templates, which are field-proven, and specification V1.1.11.
This re-extracts the YAML's and fails if the table has drifted — a bound typed
twice is a bound that disagrees with itself eventually, and the number
deciding how far a battery discharges is not one to get wrong.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest
import yaml

sys.path.insert(0, "scripts")

from writes import NUMBERS, WRITABLE_FIELDS

from sungrow_modbus import Capability
from sungrow_modbus.registers import InverterFastHolding

YAML_PACKAGE = Path(__file__).resolve().parent.parent / "legacy" / "modbus_sungrow.yaml"


class _Loader(yaml.SafeLoader):
    """Load the package without a real secrets.yaml."""


_Loader.add_constructor(
    "!secret", lambda loader, node: f"!secret {loader.construct_scalar(node)}"
)


def _yaml_numbers() -> dict[str, dict]:
    """Return the YAML's `number:` templates, by unique_id."""
    document = yaml.load(YAML_PACKAGE.read_text(encoding="utf-8"), Loader=_Loader)
    found: dict[str, dict] = {}
    for block in document.get("template", []) or []:
        for raw in block.get("number", []) or []:
            found[raw["unique_id"]] = raw
    return found


YAML_NUMBERS = _yaml_numbers()


def _is_static(bound: object) -> bool:
    """Whether the YAML states this bound as a number at all.

    Two of its bounds are not numbers: `!secret
    sungrow_modbus_battery_max_power`, which the user supplies, and a Jinja
    template reading another sensor. Those are exactly the ones the
    integration resolves at runtime instead, so there is nothing to compare —
    and the test below asserts it does resolve them rather than skipping
    quietly.
    """
    return isinstance(bound, (int, float)) and not isinstance(bound, bool)


@pytest.mark.parametrize("row", NUMBERS, ids=lambda row: row["field"])
def test_the_bounds_match_the_yaml_package(row: dict) -> None:
    template = YAML_NUMBERS[row["legacy_unique_id"]]
    assert row["step"] == template["step"], "step"

    if _is_static(template["min"]):
        assert row["minimum"] == template["min"], "minimum"
    if _is_static(template["max"]):
        assert row["maximum"] == template["max"], "maximum"


@pytest.mark.parametrize("row", NUMBERS, ids=lambda row: row["field"])
def test_a_bound_the_yaml_could_not_state_is_resolved_not_invented(row: dict) -> None:
    """Where the YAML asked the user or read a sensor, so must this.

    Hardcoding a battery's maximum charge power because the YAML's was a
    `!secret` would be the worst outcome here: a number that looks
    authoritative and is not.
    """
    template = YAML_NUMBERS[row["legacy_unique_id"]]
    if not _is_static(template["max"]):
        assert row.get("maximum_field") or row.get("maximum_from_battery"), (
            f"{row['field']}: the YAML would not state a maximum, so this "
            "must read one rather than assume one"
        )
    if not _is_static(template["min"]):
        assert row.get("minimum_field"), row["field"]


@pytest.mark.parametrize("row", NUMBERS, ids=lambda row: row["field"])
def test_it_writes_the_register_the_yaml_wrote(row: dict) -> None:
    """The same register, or the setting would land somewhere else entirely."""
    import json

    entity_map = json.loads(
        (
            Path(__file__).resolve().parent.parent / "doc" / "legacy_entity_map.json"
        ).read_text(encoding="utf-8")
    )["entities"]
    # Sensors only: `switch.export_power_limit` shares its object id with
    # `sensor.export_power_limit` and points at the mode flag at 13086 rather
    # than the value at 13073.
    address = {
        e["entity_id"].split(".", 1)[1]: e["address"]
        for e in entity_map
        if e["layer"] == "modbus"
        and e["domain"] == "sensor"
        and e.get("address") is not None
    }[row["field"]]

    template = YAML_NUMBERS[row["legacy_unique_id"]]
    written = [
        step["data_template"]["address"]
        for step in template["set_value"]
        if "data_template" in step and "address" in step["data_template"]
    ]
    assert written == [address]


def test_only_declared_fields_are_writable() -> None:
    """The safety property: the library refuses everything else.

    A register the integration cannot write is a register it cannot write by
    accident, so the set of writable fields in the register map must be
    exactly this table -- no more.
    """
    from sungrow_modbus import COMPONENTS

    writable = {
        name
        for component in COMPONENTS.values()
        for name, field in component.declared_fields.items()
        if getattr(field, "writable", False)
    }
    assert writable == set(WRITABLE_FIELDS)


def test_the_dangerous_registers_are_not_writable_yet() -> None:
    """Named individually, so adding one is a deliberate act.

    These are what the YAML package guards behind its danger-mode toggle. The
    list shrinks one deliberate commit at a time: when this test fails because
    a field was made writable, that is the question being asked -- did you
    mean to?
    """
    for field in (
        # Power limiting, distinct from feed-in limiting -- and its
        # shutdown-at-zero behaviour.
        "active_power_limitation_raw",
        "active_power_limitation_ratio_raw",
        "apl_shutdown_at_zero_raw",
        # SHT-only, and the reference hardware answers 0xFFFF.
        "pv_power_limitation_raw",
        # The most dangerous register in the map. Reading it gives the running
        # state; writing 0xCF or 0xCE to it boots or shuts down the inverter,
        # which is what the YAML's start/stop buttons do. Nothing should be
        # able to write this by accident, and a `button` is the only shape
        # that cannot be nudged by a slider or a stale automation.
        "running_state_raw",
    ):
        assert field not in WRITABLE_FIELDS


@pytest.mark.parametrize("row", NUMBERS, ids=lambda row: row["field"])
def test_every_control_declares_the_capability_it_needs(row: dict) -> None:
    """One table decides which hardware gets which control.

    This was a conditional in `generate_numbers.py` until 2026-09-18 --
    `BATTERY` for everything except the export limit -- which silently
    overrode what the start-power pair's own comment in this table claimed.
    On an SH*RS, where those registers are reported absent (issue #743),
    `BATTERY` is present whenever a battery is, so both entities were created
    **writable** against registers that are not there.

    `export_power_limit` is the one control that needs no capability: it is
    the inverter's limit, not the battery's, and an inverter always has one.
    """
    capability = row.get("requires")
    if row["field"] == "export_power_limit":
        assert capability is None
        return
    assert capability is not None, "every other control is hardware-dependent"
    assert hasattr(Capability, capability), f"no such capability: {capability}"


def test_the_start_power_pair_is_gated_on_its_own_capability() -> None:
    """Named rather than left to the parametrised test above.

    `Capability.BATTERY_START_POWER` exists, is probed, and is family-gated as
    absent on RS -- and for a while it gated nothing at all. The point of the
    capability is that these two are the registers it was defined for.
    """
    gated = {
        row["field"] for row in NUMBERS if row.get("requires") == "BATTERY_START_POWER"
    }
    assert gated == {
        "battery_charging_start_power",
        "battery_discharging_start_power",
    }


def test_the_export_limit_writes_in_tens_and_reads_in_ones() -> None:
    """Register 13074 is the one place the two directions disagree.

    It reads in watts -- 10000 back against a 10000 W maximum from register
    5623, which is the read side agreeing with its own bounds -- and writes in
    tens of watts, multiplying the word it is handed by ten before storing it.
    Measured six times on the reference SH10RT with feed-in limitation on,
    including values no rounding could produce, and replicated at a second
    house on an SH10RT-20 through a dongle.

    Every other register in the map shares one scale between `encode` and
    `decode`, so the obvious tidy-up is to make this one an `integer()` like
    its neighbours. That tidy-up sets ten times what the user asked for, and
    it is invisible to a readback through the library because `encode` and
    `decode` would agree with each other while both disagreed with the device.
    So the assertion is deliberately about the **raw word**, which is the only
    place the difference shows.
    """
    field = InverterFastHolding.__dict__["export_power_limit"]

    # The write side: what actually goes on the wire for a value a user types.
    assert field.encode(900) == [90]
    assert field.encode(10000) == [1000]
    assert field.encode(0) == [0]

    # The read side is untouched, and must stay so: the register contains watts.
    assert field.decode([900]) == 900
    assert field.decode([10000]) == 10000

    # Stated as the round trip through a device that behaves as measured.
    for watts in (100, 900, 3400, 10000):
        (word,) = field.encode(watts)
        assert field.decode([word * 10]) == watts
