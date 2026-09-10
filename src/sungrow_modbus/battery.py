"""How much power a battery will take, and where that number comes from.

The YAML package asks the user: `sungrow_modbus_battery_max_power`, with a
default of 5000 W and a comment pointing at two Sungrow datasheets. That works
but it puts a safety-relevant number behind a manual step most people skip, so
the integration derives it where it can and asks only where it cannot.

Three sources, in order of how much they can be trusted:

1. **A Sungrow battery's model**, inferred from the capacity it reports. The
   datasheets give a figure per model and the YAML's own comment records them,
   so this is a lookup rather than a guess.
2. **The BMS's own maximum charge current**, times the battery voltage. This
   is the battery saying what it will take, which beats any table — but the
   voltage it is multiplied by is whatever the pack sits at right now.
3. **The user.** A third-party pack whose BMS says nothing leaves nobody but
   them to read the datasheet.

The values below are the **conservative** column, deliberately. The YAML's
comment says why: "Being conservative here is good for your battery's health.
Sungrow technical trainings recommend using the low end of the voltage range
x the rated current, instead of the nominal voltage." A default that shortens
somebody's battery life is a bad default even if the hardware permits it.
"""

from __future__ import annotations

from typing import NamedTuple


class BatteryModel(NamedTuple):
    """One Sungrow battery, and what it will take."""

    name: str
    capacity_kwh: float
    conservative_w: int
    """Rated current x the low end of the voltage range."""

    nominal_w: int
    """Rated current x nominal voltage. Higher, and harder on the pack."""


#: SBR, from DS_20240907_SBR064..256_Datasheet_V5_EN.
#: SBH, from DS_20240329_SBH100..400_Datasheet_V4_EN.
#: Both are the datasheets the YAML package's secrets.yaml cites.
MODELS: tuple[BatteryModel, ...] = (
    BatteryModel("SBR064", 6.4, 3240, 3840),
    BatteryModel("SBR096", 9.6, 4860, 5760),
    BatteryModel("SBR128", 12.8, 6480, 7680),
    BatteryModel("SBR160", 16.0, 8100, 9600),
    BatteryModel("SBR192", 19.2, 9720, 11520),
    BatteryModel("SBR224", 22.4, 11340, 13440),
    BatteryModel("SBR256", 25.6, 12960, 15360),
    BatteryModel("SBH100", 10.0, 5940, 7040),
    BatteryModel("SBH150", 15.0, 8910, 10560),
    BatteryModel("SBH200", 20.0, 11880, 14080),
    BatteryModel("SBH250", 25.0, 14850, 17600),
    BatteryModel("SBH300", 30.0, 17820, 21120),
    BatteryModel("SBH350", 35.0, 20790, 24640),
    BatteryModel("SBH400", 40.0, 23760, 28160),
)

#: What the YAML package defaults to, and therefore what a user who never
#: touched it has been running. Not a recommendation — a floor.
FALLBACK_W = 5000

#: How far a reported capacity may sit from a model's rated capacity and still
#: be that model. A pack degrades and reports a little less than its rating;
#: 0.4 kWh is comfortably inside the gap between adjacent models, the closest
#: pair being SBH250 at 25.0 and SBR256 at 25.6.
CAPACITY_TOLERANCE_KWH = 0.4


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
#: slave filed as a battery -- which is not a hypothetical shape, it is the
#: fourth site in `doc/device-fingerprints/`.
IDENTITY_REGISTER = 4999


#: What a pack's voltage register may not read for the pack to be believed.
#: 0xFFFF is the specification's "no reading". **Zero matters just as much**:
#: a WiNet-S answers 0 for measuring points it does not forward -- the same
#: behaviour `capabilities.ZERO_MEANS_ABSENT` guards against -- and a Modbus
#: proxy can do likewise, so "something answered" is not "a battery is
#: there". No SBR sits at 0 V.
IMPLAUSIBLE = (0, 0xFFFF)


async def probe_units(unit_for, units=PACK_UNITS):
    """Return the unit id an SBR answers on, or None.

    `unit_for` is called with a unit id and returns something with
    `read_input_registers`, which is how this stays testable without a device
    and without Home Assistant.

    The pack is identified by *what answers where*, never by configuration: a
    contributor does not know their battery's unit id, and the answer moves
    with the transport rather than with the hardware.

    An answer is not enough -- it has to be a plausible one. The first
    version of this took any successful read as a pack, which a device
    answering zeros satisfies, and that is precisely what sits between us and
    a battery in most installations.
    """
    from modbus_connection import ModbusError

    for unit in units:
        try:
            words = await unit_for(unit).read_input_registers(10740, 2)
        except (ModbusError, TimeoutError, OSError):
            continue
        if not words or int(words[0]) in IMPLAUSIBLE:
            continue
        if unit == 200:
            # Only a battery answers here, so nothing further to ask.
            return unit
        try:
            code = await unit_for(unit).read_input_registers(IDENTITY_REGISTER, 1)
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


def model_for_capacity(capacity_kwh: float | None) -> BatteryModel | None:
    """Return the Sungrow battery whose rated capacity this matches.

    Only meaningful once the pack is known to be a Sungrow: a third-party
    battery of the same size is not an SBR, and would be given an SBR's power
    limit by a match here.
    """
    if capacity_kwh is None:
        return None
    closest = min(MODELS, key=lambda m: abs(m.capacity_kwh - capacity_kwh))
    if abs(closest.capacity_kwh - capacity_kwh) > CAPACITY_TOLERANCE_KWH:
        return None
    return closest


def power_from_bms(
    max_charge_current_a: float | None, voltage_v: float | None
) -> int | None:
    """Return what the BMS says it will take, in watts.

    The battery's own answer, which beats any table — with the caveat that the
    voltage is wherever the pack happens to be sitting. At a high state of
    charge that reads higher than the datasheet figure, which is why this is a
    suggestion to confirm rather than a value to apply.
    """
    if not max_charge_current_a or not voltage_v:
        return None
    return int(max_charge_current_a * voltage_v)
