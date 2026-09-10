"""Register maps for the Sungrow inverter.

Addresses are protocol addresses, i.e. one below the register number printed
in Sungrow's communication protocol document and in the comments of
modbus_sungrow.yaml (`address: 4989 # reg 4990`).

Sungrow reports 32-bit values low word first, which the YAML package spells
`swap: word` and this library spells ``word_order="little"``.
"""

from __future__ import annotations

from modbus_connection.model import Component, gauge, integer, string, uint32


class InverterControl(Component):
    """The start/stop register, and only that.

    Register 13000 appears in **both** of Sungrow's tables, and they are
    different address spaces rather than two descriptions of one thing:

    * Table 3 is read-only over function code 0x04 -- the *input* space --
      where reading 13000 gives the running state, which is what
      `running_state_raw` does;
    * Table 4 is read/write over 0x03, 0x06 and 0x10 -- the *holding* space --
      where 13000 is "Start/Stop", `0xCF` to boot and `0xCE` to shut down.

    So the YAML package reads one space and writes the other, correctly, and
    the library refuses to write the input field -- which is how this was
    noticed. Hence a separate component, in the right space.

    Never polled. There is nothing here worth a poll: the running state comes
    from the input side, and a write is followed by a refresh of *that*.
    """

    register_space = "holding"

    start_stop = integer(12999, signed=False, writable=True)
    """Register 13000: 0xCF boots the inverter, 0xCE shuts it down."""


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

    output_type = integer(5001, signed=False)
    """0 single phase, 1 three-phase 3P4L, 2 three-phase 3P3L.

    Sungrow states the phase count outright here, so it is never inferred from
    the model — see `capabilities.resolve`.
    """


#: The firmware block added in protocol V1.1.7 at register 13250 is **ASCII
#: text**, not numbers: read from the reference SH10RT it comes back as
#: 21313, 20560, 18505, 21061, which is "SAPPHIRE" — the same family name the
#: ARM and DSP version strings carry. Port it with `string()`, not `integer()`.
FIRMWARE_BLOCK_IS_TEXT = True


class InverterReadings(Component):
    """Live measurements polled on the fast interval."""

    register_space = "input"

    total_dc_power = uint32(5016, word_order="little", unit="W")
    """Combined DC input power over all MPP trackers."""
