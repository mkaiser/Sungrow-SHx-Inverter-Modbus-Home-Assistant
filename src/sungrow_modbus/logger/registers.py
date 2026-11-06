"""A Sungrow Logger's register map, from Sungrow's document.

Sungrow's *Logger Communication Protocol* AW0 1.0.2.9 (2022-06-14, marked
public, for the Logger1000, Logger3000 and Logger4000) is the source of
every field here; 1.0.2.5 lists the same input registers and the holding
registers up to 8016 (`.wiki/raw/logger-communication-protocol.md`). No
Logger has been measured here, so all of it is **spec**, and the first survey
of one is what turns a mark into a measurement.

* input 8000-8006, the identity: type code (`MODELS`), protocol, devices;
* input 8021-8036, the digital and analogue inputs a plant wires to it;
* input 8058-8109, the array behind it: limits, state, power and yields;
* holding 8002-8020, the plant controls, **read, never written**.

The document's word orders differ by width: a 32-bit value sends its low
word first, a 64-bit value its high word first. Unsupported registers answer
all ones when unsigned and the largest positive value when signed, which is
what each field's `nan` is.

Two warnings from the document itself. A write to unit 0 is passed straight
through to every inverter behind the Logger. And a latched Logger (8069)
ignores remote dispatch. Two people report writes to a Logger failing;
nothing here writes.
"""

from __future__ import annotations

from modbus_connection.model import (
    Component,
    gauge,
    int32,
    int64,
    integer,
    uint32,
    uint64,
)

from ..addresses import reg
from ..model import string

#: Where a Logger answers on its own endpoint.
UNIT = 247

#: Which Logger a type code at input 8000 names.
MODELS: dict[int, str] = {
    0x0705: "Logger3000",
    0x0710: "Logger1000",
    0x0718: "Logger4000",
}

_U16 = 0xFFFF
_S16 = 0x7FFF
_U32 = 0xFFFFFFFF
_S32 = 0x7FFFFFFF
_U64 = 0xFFFFFFFFFFFFFFFF
_S64 = 0x7FFFFFFFFFFFFFFF

#: 0xAA and 0x55, the switch codes the newer holding registers use.
SWITCH: dict[int, str] = {0xAA: "enabled", 0x55: "disabled"}

#: What each coded field's values mean, by its published name.
CODES: dict[str, dict[int, str]] = {
    "array_switch": {0: "off", 1: "on"},
    "unlatch_state": {0: "latched", 1: "unlatched"},
    "array_switch_setting": {0: "off", 1: "on"},
    **{
        f"digital_output_{n}": {0: "common to NC closed", 1: "common to NO closed"}
        for n in range(1, 5)
    },
    "power_gradient_control": SWITCH,
    "wifi_hotspot": SWITCH,
}


class LoggerIdentity(Component):
    """What it is and how many devices it fronts."""

    register_space = "input"

    device_type_code = integer(reg(8000), signed=False)
    protocol_number = string(reg(8001), 2)
    """Typed U32 by the document; text ("AW0") as on an iHomeManager."""

    protocol_version_raw = uint32(reg(8003), word_order="little", nan=_U32)
    connected_devices = integer(reg(8005), signed=False, nan=_U16)
    """Every device behind it, third-party devices included."""

    devices_in_fault = integer(reg(8006), signed=False, nan=_U16)
    """Inverters reporting a fault, third-party devices not counted."""


class LoggerInputs(Component):
    """The sensors and contacts wired to the Logger itself.

    Which model has which input differs; a model without one answers its
    unavailable value, so the field is absent rather than zero.
    """

    register_space = "input"

    digital_inputs_raw = uint32(reg(8021), word_order="little", nan=_U32)
    """One bit per input, 0 open and 1 closed: 8 on a Logger1000, 16 else."""

    pt100_1_temperature = gauge(reg(8027), 0.1, nan=_S16, unit="°C")
    pt100_2_temperature = gauge(reg(8028), 0.1, nan=_S16, unit="°C")
    ai1_voltage = gauge(reg(8029), 0.01, nan=_S16, unit="V")
    ai1_current = gauge(reg(8030), 0.01, nan=_S16, unit="mA")
    ai2_voltage = gauge(reg(8031), 0.01, nan=_S16, unit="V")
    ai2_current = gauge(reg(8032), 0.01, nan=_S16, unit="mA")
    ai3_voltage_raw = integer(reg(8033), nan=_S16)
    """In 0.01 V on a Logger1000, 0.01 mV on a Logger3000: raw for that."""

    ai4_voltage_raw = integer(reg(8034), nan=_S16)
    """As `ai3_voltage_raw`."""

    ai3_current = gauge(reg(8035), 0.01, nan=_S16, unit="mA")
    ai4_current = gauge(reg(8036), 0.01, nan=_S16, unit="mA")


class LoggerArray(Component):
    """The array of inverters behind it, as one plant."""

    register_space = "input"

    max_nominal_active_power = integer(reg(8058), signed=False, nan=_U16, unit="kW")
    min_nominal_active_power = integer(reg(8059), signed=False, nan=_U16, unit="kW")
    max_nominal_reactive_power = integer(reg(8060), signed=False, nan=_U16, unit="kvar")
    min_nominal_reactive_power = integer(reg(8061), nan=_S16, unit="kvar")
    preset_active_power = integer(reg(8066), signed=False, nan=_U16, unit="kW")
    preset_reactive_power = integer(reg(8067), nan=_S16, unit="kvar")
    array_switch_raw = integer(reg(8068), signed=False, nan=_U16)
    unlatch_state_raw = integer(reg(8069), signed=False, nan=_U16)
    """Unlatched by default; latched, it ignores remote dispatch."""

    total_active_power = uint64(reg(8070), nan=_U64, unit="W")
    daily_yield = uint32(
        reg(8074), scale=0.1, word_order="little", nan=_U32, unit="kWh"
    )
    total_reactive_power = int64(reg(8076), nan=_S64, unit="var")
    total_yield = uint64(reg(8080), scale=0.1, nan=_U64, unit="kWh")
    min_adjustable_active_power = uint32(
        reg(8084), scale=0.1, word_order="little", nan=_U32, unit="kW"
    )
    max_adjustable_active_power = uint32(
        reg(8086), scale=0.1, word_order="little", nan=_U32, unit="kW"
    )
    min_adjustable_reactive_power = int32(
        reg(8088), scale=0.1, word_order="little", nan=_S32, unit="kvar"
    )
    max_adjustable_reactive_power = int32(
        reg(8090), scale=0.1, word_order="little", nan=_S32, unit="kvar"
    )
    rated_active_power = uint32(
        reg(8092), scale=0.1, word_order="little", nan=_U32, unit="kW"
    )
    """The document's unit column says kVar, which an active power is not."""

    rated_reactive_power = uint32(
        reg(8094), scale=0.1, word_order="little", nan=_U32, unit="kvar"
    )
    grid_connected_inverters = integer(reg(8096), signed=False, nan=_U16)
    off_grid_inverters = integer(reg(8097), signed=False, nan=_U16)
    monthly_yield = uint64(reg(8098), scale=0.1, nan=_U64, unit="kWh")
    annual_yield = uint64(reg(8102), scale=0.1, nan=_U64, unit="kWh")
    apparent_power = uint64(reg(8106), nan=_U64, unit="VA")


class LoggerSettings(Component):
    """The plant controls. Read with function code 3, never written.

    The document allows one function per holding register; what a write to
    unit 0 does is pass it to every inverter.
    """

    register_space = "holding"

    array_switch_setting_raw = integer(reg(8002), signed=False, nan=_U16)
    active_power_setting = uint32(
        reg(8003), scale=0.1, word_order="little", nan=_U32, unit="kW"
    )
    active_power_ratio_setting = uint32(
        reg(8005), scale=0.1, word_order="little", nan=_U32, unit="%"
    )
    reactive_power_setting = int32(
        reg(8007), scale=0.1, word_order="little", nan=_S32, unit="kvar"
    )
    reactive_power_ratio_setting = int32(
        reg(8009), scale=0.1, word_order="little", nan=_S32, unit="%"
    )
    power_factor_setting = int32(reg(8011), scale=0.001, word_order="little", nan=_S32)
    digital_output_1_raw = integer(reg(8013), signed=False, nan=_U16)
    """Logger3000 and Logger4000 only, as are the other three."""

    digital_output_2_raw = integer(reg(8014), signed=False, nan=_U16)
    digital_output_3_raw = integer(reg(8015), signed=False, nan=_U16)
    digital_output_4_raw = integer(reg(8016), signed=False, nan=_U16)
    power_gradient_control_raw = integer(reg(8017), signed=False, nan=_U16)
    active_power_decline_gradient = integer(
        reg(8018), signed=False, nan=_U16, unit="%/min"
    )
    active_power_rise_gradient = integer(
        reg(8019), signed=False, nan=_U16, unit="%/min"
    )
    wifi_hotspot_raw = integer(reg(8020), signed=False, nan=_U16)
    """Logger1000 only."""


#: The components, by the name a document groups them under.
COMPONENTS: dict[str, type[Component]] = {
    "identity": LoggerIdentity,
    "inputs": LoggerInputs,
    "array": LoggerArray,
    "settings": LoggerSettings,
}

#: Only 8017-8020 are new in 1.0.2.9; everything else 1.0.2.5 lists too.
_NEW_IN_1029 = frozenset(
    {
        "power_gradient_control",
        "active_power_decline_gradient",
        "active_power_rise_gradient",
        "wifi_hotspot",
    }
)

#: Which document each published field rests on. None is measured.
CONFIDENCE: dict[str, str] = {
    published: "spec 1.0.2.9" if published in _NEW_IN_1029 else "spec 1.0.2.5-1.0.2.9"
    for component in COMPONENTS.values()
    for published in (name.removesuffix("_raw") for name in component.declared_fields)
}
