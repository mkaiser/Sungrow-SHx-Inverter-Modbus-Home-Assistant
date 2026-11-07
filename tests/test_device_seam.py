"""Every device meets the one seam the entity layer and the diagnosis type against.

`device.Device` for all of them, `device.Inverter` for the two that can be an
entry's own inverter. Checked on instances, because a Protocol checks only
that the members exist; mypy checks their types.
"""

from __future__ import annotations

from modbus_connection.mock import MockModbusConnection
import pytest

from sungrow_modbus import SungrowInverter, inverter_kind, inverter_model
from sungrow_modbus.battery.device import SungrowBattery
from sungrow_modbus.const import DEVICE_TYPES
from sungrow_modbus.device import Device, Inverter
from sungrow_modbus.string_inverter import MODELS, SungrowStringInverter
from sungrow_modbus.wallbox.device import SungrowWallbox


def _unit():
    return MockModbusConnection().for_unit(1)


@pytest.mark.parametrize(
    "device",
    [
        SungrowInverter(_unit()),
        SungrowStringInverter(_unit()),
        SungrowBattery(_unit(), 200),
        SungrowWallbox(_unit(), 3),
    ],
    ids=type,
)
def test_every_device_meets_the_seam(device) -> None:
    assert isinstance(device, Device)
    assert device.field_names
    name = sorted(device.field_names)[0]
    device.field(name)
    with pytest.raises(AttributeError):
        device.field("no_such_field")


def test_both_inverters_are_inverters_and_nothing_else_is() -> None:
    assert isinstance(SungrowInverter(_unit()), Inverter)
    assert isinstance(SungrowStringInverter(_unit()), Inverter)
    assert not isinstance(SungrowBattery(_unit(), 200), Inverter)
    assert not isinstance(SungrowWallbox(_unit(), 3), Inverter)


def test_the_type_code_alone_decides_which_map() -> None:
    hybrid = next(iter(DEVICE_TYPES))
    sg = next(iter(MODELS))
    assert inverter_kind(hybrid) == "hybrid"
    assert inverter_kind(sg) == "string_inverter"
    assert inverter_kind(0xBEEF) is None
    assert inverter_kind(None) is None
    assert inverter_model(hybrid) == DEVICE_TYPES[hybrid]
    assert inverter_model(sg) == MODELS[sg]
