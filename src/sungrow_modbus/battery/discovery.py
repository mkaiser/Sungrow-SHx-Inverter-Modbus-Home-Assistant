"""Finding an SBR pack, on whichever unit it answers.

Which unit is not a setting: it moves with the transport, so the pack is
found by what answers where, never by configuration.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..addresses import field_address, read

#: Where an SBR's own registers answer, and why there are two.
#:
#: Measured 2026-09-08 on two houses. Over the inverter's own LAN port the
#: pack is at unit **200**; through a WiNet-S it is at unit **2** and unit 200
#: times out. So neither is a safe default and both are tried, in the order
#: that puts the unambiguous one first: **200 is only ever a battery**, while
#: unit 2 is also where a slave inverter lives.
PACK_UNITS: tuple[int, ...] = (200, 2)

#: The register that tells a slave inverter from a battery at unit 2. An
#: inverter answers its device type code; a battery does not. Without this
#: check, a master/slave installation read through a dongle would have its
#: slave filed as a battery -- not a hypothetical shape: `device-survey/`
#: holds one.
INVERTER_TYPE = field_address("device_type_code")

#: The pack's voltage, which is what a pack is recognised by: every SBR has
#: one, and no SBR reads 0 V.
PACK_VOLTAGE = field_address("voltage", "battery")


#: What a pack's voltage register may not read for the pack to be believed.
#: 0xFFFF is the specification's "no reading". **Zero matters just as much**:
#: a WiNet-S answers 0 for measuring points it does not forward -- the same
#: behaviour `capabilities.ZERO_MEANS_ABSENT` guards against -- and a Modbus
#: proxy can do likewise, so "something answered" is not "a battery is
#: there". No SBR sits at 0 V.
IMPLAUSIBLE = (0, 0xFFFF)


async def probe_units(
    unit_for: Callable[[int], Any], units: tuple[int, ...] = PACK_UNITS
) -> int | None:
    """Return the unit id an SBR answers on, or None.

    `unit_for` is called with a unit id and returns something with
    `read_input_registers`, which is how this stays testable without a device
    and without Home Assistant.

    The pack is identified by *what answers where*, never by configuration: a
    contributor does not know their battery's unit id, and the answer moves
    with the transport rather than with the hardware.

    An answer is not enough -- it has to be a plausible one. Any successful
    read is satisfied by a device answering zeros, and that is precisely what
    sits between us and a battery in most installations.
    """
    from modbus_connection import ModbusError

    for unit in units:
        try:
            words = await read(unit_for(unit), PACK_VOLTAGE)
        except (ModbusError, TimeoutError, OSError):
            continue
        if not words or int(words[0]) in IMPLAUSIBLE:
            continue
        if unit == 200:
            # Only a battery answers here, so nothing further to ask.
            return unit
        try:
            code = await read(unit_for(unit), INVERTER_TYPE)
        except (ModbusError, TimeoutError, OSError):
            # No device type code at all: a battery rather than an inverter.
            return unit
        if not code or int(code[0]) in IMPLAUSIBLE:
            # Answered, but with nothing: still a battery. A slave inverter
            # names itself here, and every model code in `const.DEVICE_TYPES`
            # is non-zero.
            return unit
        # A device type code, so this is an inverter -- a master/slave site
        # read through a dongle, which is a real shape and not a battery.
        return None
    return None
