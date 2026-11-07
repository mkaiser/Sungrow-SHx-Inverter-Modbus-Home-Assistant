"""What an inverter is, hybrid or string: the identity block both answer.

An SH hybrid and an SG string inverter share input 4952-5002 register for
register: protocol, ARM and DSP versions, serial, type code, rating, output
type. Everything past the PV block differs, so the type code at input 5000
decides which map applies (`inverter_kind`), and nothing else does.

Declared by the register number printed in Sungrow's communication protocol
documents; `reg()` turns it into the protocol address, one below. Sungrow
reports 32-bit values low word first (``word_order="little"``).
"""

from __future__ import annotations

from typing import Literal

from modbus_connection.model import Component, gauge, integer, uint32

from .addresses import reg
from .model import string

#: The two kinds of inverter, as `inverter_kind` and `discovery.Identity`
#: name them. `string_inverter` is also the `document` key of an SG's diagnosis.
HYBRID = "hybrid"
STRING_INVERTER = "string_inverter"

InverterKind = Literal["hybrid", "string_inverter"]


class InverterIdentity(Component):
    """Who this inverter is: read once at setup, never polled.

    Every field sits between protocol address 4951 and 5001, so the whole
    component resolves to a single block read.
    """

    register_space = "input"

    protocol_version = uint32(reg(4952), word_order="little")
    """Sungrow Modbus protocol version."""

    arm_software = string(reg(4954), 15)
    """ARM firmware version string."""

    dsp_software = string(reg(4969), 15)
    """DSP firmware version string."""

    serial_number = string(reg(4990), 10)
    """Inverter serial number, used as the Home Assistant unique id."""

    device_type_code = integer(reg(5000), signed=False)
    """Model code; `inverter_kind` says which map it calls for."""

    nominal_output_power = gauge(reg(5001), 100, signed=False, unit="W")
    """Rated output power of the inverter."""

    output_type = integer(reg(5002), signed=False)
    """0 single phase, 1 three-phase 3P4L, 2 three-phase 3P3L.

    Sungrow states the phase count outright here, so it is never inferred from
    the model — see `capabilities.resolve`.
    """


def inverter_kind(device_type_code: int | None) -> InverterKind | None:
    """Return which map a type code at input 5000 calls for, or None if unknown.

    An unknown code is not a hybrid: it is a model nobody has mapped, and
    the caller decides what to do with it. No code is both
    (`tests/test_string_inverter.py`).
    """
    from .const import DEVICE_TYPES
    from .string_inverter.registers import MODELS

    if device_type_code is None:
        return None
    if device_type_code in MODELS:
        return "string_inverter"
    if device_type_code in DEVICE_TYPES:
        return "hybrid"
    return None


def inverter_model(device_type_code: int | None) -> str | None:
    """Name the model a type code stands for, hybrid or SG, or None."""
    from .const import model_for
    from .string_inverter.registers import model_for as string_inverter_model_for

    return model_for(device_type_code) or string_inverter_model_for(device_type_code)
