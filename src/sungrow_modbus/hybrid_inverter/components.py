"""The hybrid's start/stop block, outside the polled tiers.

Declared by the register number printed in Sungrow's communication protocol
document and in the comments of modbus_sungrow.yaml; `reg()` turns it into the
protocol address, one below (`address: 4989 # reg 4990`).

Sungrow reports 32-bit values low word first, which the YAML package spells
`swap: word` and this library spells ``word_order="little"``.
"""

from __future__ import annotations

from modbus_connection.model import Component, integer

from ..addresses import reg


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
    the library refuses to write the input field. Hence a separate component,
    in the right space.

    Never polled. There is nothing here worth a poll: the running state comes
    from the input side, and a write is followed by a refresh of *that*.
    """

    register_space = "holding"

    start_stop = integer(reg(13000), signed=False, writable=True)
    """Register 13000: 0xCF boots the inverter, 0xCE shuts it down."""
