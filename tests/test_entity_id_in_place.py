"""A renamed entity takes its new id in place, and is not removed and re-added.

From Home Assistant 2026.11 an entity of a custom integration whose class
defines `async_added_to_hass` (or another add or remove method) is removed and
added again on an `entity_id` change, unless that class or a subclass defines
`async_entity_id_changed`. The fallback ends in 2027.11. A re-add runs the add
hook a second time: the MPP tracker's integral restarts from its restored
state, and a renamed sensor's state disappears between the two.

The legacy-id switch (`migration.async_switch_entity_ids`) renames live
entities, so this is on the migration's path.
"""

from __future__ import annotations

import importlib
import inspect
from typing import Any
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus import sensor
from custom_components.sungrow_modbus.const import CONF_UNIT_ID, DOMAIN
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity as ha_entity, entity_registry as er

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

PLATFORM_MODULES = (
    "binary_sensor",
    "button",
    "number",
    "select",
    "sensor",
    "diagnosis_entities",
    "switch",
    "time",
)

requires_readd = getattr(ha_entity, "_entity_class_requires_readd", None)


def _entity_classes() -> list[type[ha_entity.Entity]]:
    found: list[type[ha_entity.Entity]] = []
    for name in PLATFORM_MODULES:
        module = importlib.import_module(f"custom_components.sungrow_modbus.{name}")
        found.extend(
            cls
            for _, cls in inspect.getmembers(module, inspect.isclass)
            if issubclass(cls, ha_entity.Entity)
            and cls.__module__.startswith("custom_components.sungrow_modbus")
        )
    return found


@pytest.mark.skipif(requires_readd is None, reason="Home Assistant before 2026.11")
@pytest.mark.parametrize("cls", _entity_classes(), ids=lambda c: c.__name__)
def test_no_entity_class_falls_back_to_a_re_add(cls: type[ha_entity.Entity]) -> None:
    assert requires_readd is not None
    assert not requires_readd(cls)


async def test_a_rename_keeps_the_energy_total_running(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    sungrow_unit.input[5010] = 4000  # MPPT1 400.0 V
    sungrow_unit.input[5011] = 50  # 5.0 A: 2000 W
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    registry = er.async_get(hass)
    old_id = registry.async_get_entity_id("sensor", DOMAIN, f"{SERIAL}_mppt1_energy")
    assert old_id is not None
    new_id = "sensor.renamed_mppt1_energy"

    added = 0
    original = sensor.SungrowEnergySensor.async_added_to_hass

    async def counting(self: Any) -> None:
        nonlocal added
        added += 1
        await original(self)

    with patch.object(sensor.SungrowEnergySensor, "async_added_to_hass", counting):
        registry.async_update_entity(old_id, new_entity_id=new_id)
        await hass.async_block_till_done()

    assert hass.states.get(old_id) is None
    assert hass.states.get(new_id) is not None
    assert added == (1 if requires_readd is None else 0)
