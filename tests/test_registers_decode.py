"""Every ported register decodes against the simulator's seed.

The register map is generated, so the addresses match the YAML by
construction. What that cannot catch is a register whose *width* or *space* is
wrong — a uint32 read as one register, or an input register looked for among
the holding ones. Both produce an entity that is simply never populated, which
on real hardware looks like an unsupported model rather than a bug.

So this drives the whole map against the seed the simulator uses, and requires
every field to come back with a value.
"""

from __future__ import annotations

import json
from pathlib import Path

from modbus_connection.mock import MockModbusConnection
import pytest

from custom_components.sungrow_modbus.sensor_descriptions import SENSOR_DESCRIPTIONS
from sungrow_modbus import TIERS, SungrowInverter

SEED = Path(__file__).resolve().parent.parent / "scripts" / "simulator_registers.json"


@pytest.fixture(scope="module")
def inverter() -> SungrowInverter:
    """Return an inverter backed by the simulator's register seed."""
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    unit = MockModbusConnection().for_unit(1)
    unit.input = {int(a): v for a, v in seed.get("input", {}).items()}
    unit.holding = {int(a): v for a, v in seed.get("holding", {}).items()}
    return SungrowInverter(unit)


@pytest.fixture(scope="module")
async def polled(inverter: SungrowInverter) -> SungrowInverter:
    """Return the same inverter, with every tier read once."""
    await inverter.async_update_identity()
    for interval in TIERS:
        await inverter.async_update_tier(interval)
    return inverter


async def test_the_seed_covers_every_tier(polled: SungrowInverter) -> None:
    for interval in TIERS:
        report = await polled.async_update_tier(interval)
        assert not report.failed, f"tier {interval}: {report.failed}"


@pytest.mark.parametrize("description", SENSOR_DESCRIPTIONS, ids=lambda d: d.key)
async def test_each_sensor_reads_a_value(polled: SungrowInverter, description) -> None:
    component = polled.component(description.component)
    value = getattr(component, description.field)
    assert value is not None, (
        f"{description.key} decoded to None — check its width and register space"
    )


async def test_the_identity_block_decodes(polled: SungrowInverter) -> None:
    assert polled.serial_number
    assert polled.device_type_code is not None
    assert polled.output_type is not None
