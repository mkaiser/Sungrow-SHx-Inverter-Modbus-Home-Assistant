"""Register maps for the Sungrow SHx inverter.

Addresses are protocol addresses, i.e. one below the register number printed
in Sungrow's communication protocol document and in the comments of
modbus_sungrow.yaml (`address: 4989 # reg 4990`).

Sungrow reports 32-bit values low word first, which the YAML package spells
`swap: word` and this library spells ``word_order="little"``.
"""

from __future__ import annotations

from modbus_connection.model import Component, gauge, integer, string, uint32


class InverterIdentity(Component):
    """Who this inverter is: read once at setup, never polled.

    Every field sits between protocol address 4951 and 5000, so the whole
    component resolves to a single block read.
    """

    register_space = "input"

    protocol_version = uint32(4951, word_order="little")
    """Sungrow Modbus protocol version."""

    arm_software = string(4953, 15)
    """ARM firmware version string."""

    dsp_software = string(4968, 15)
    """DSP firmware version string."""

    serial_number = string(4989, 10)
    """Inverter serial number, used as the Home Assistant unique id."""

    device_type_code = integer(4999, signed=False)
    """Model code; see ``const.DEVICE_TYPES``."""

    nominal_output_power = gauge(5000, 100, signed=False, unit="W")
    """Rated output power of the inverter."""


class InverterReadings(Component):
    """Live measurements polled on the fast interval."""

    register_space = "input"

    total_dc_power = uint32(5016, word_order="little", unit="W")
    """Combined DC input power over all MPP trackers."""
