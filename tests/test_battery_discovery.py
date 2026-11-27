"""Finding an SBR pack: 200 is only ever a pack, 2 may be a slave inverter.

The unit ids are what answers where (`battery.probe_units`), so each case is
a set of fake units answering, refusing or staying silent.
"""

from __future__ import annotations

from modbus_connection import IllegalDataAddressError, ModbusTimeoutError

from sungrow_modbus.battery import INVERTER_TYPE, PACK_VOLTAGE, probe_units


class Unit:
    """A unit answering `words` by protocol address, refusing the rest."""

    def __init__(self, words: dict[int, int] | None, *, silent: bool = False):
        """Answer `words`; with `silent`, time out on everything."""
        self.words = words or {}
        self.silent = silent

    async def read_input_registers(self, address: int, count: int) -> list[int]:
        """Answer, refuse with 0x02, or time out."""
        if self.silent:
            raise ModbusTimeoutError("no answer")
        if address not in self.words:
            raise IllegalDataAddressError("illegal data address")
        return [self.words[address]] + [0] * (count - 1)


def _units(**by_id: Unit):
    silent = Unit(None, silent=True)
    return lambda unit_id: by_id.get(f"u{unit_id}", silent)


async def test_a_pack_on_its_own_lan_port_answers_at_200() -> None:
    units = _units(u200=Unit({PACK_VOLTAGE.address: 1990}))
    assert await probe_units(units) == 200


async def test_a_pack_behind_a_dongle_answers_at_2_and_names_no_device_type() -> None:
    units = _units(u2=Unit({PACK_VOLTAGE.address: 1990}))
    assert await probe_units(units) == 2


async def test_a_device_type_of_zero_is_still_a_pack() -> None:
    words = {PACK_VOLTAGE.address: 1990, INVERTER_TYPE.address: 0}
    assert await probe_units(_units(u2=Unit(words))) == 2


async def test_a_slave_inverter_at_2_is_not_a_pack() -> None:
    """It answers a device type code, which no pack does."""
    words = {PACK_VOLTAGE.address: 1990, INVERTER_TYPE.address: 0x0E0F}
    assert await probe_units(_units(u2=Unit(words))) is None


async def test_a_dongles_zero_voltage_is_no_pack() -> None:
    units = _units(u200=Unit({PACK_VOLTAGE.address: 0}), u2=Unit({}))
    assert await probe_units(units) is None
