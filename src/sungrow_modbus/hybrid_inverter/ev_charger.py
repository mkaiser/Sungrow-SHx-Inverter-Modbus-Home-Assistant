"""The hybrid inverter's EV charger block: how it drives a wallbox it manages.

A Sungrow wallbox on a hybrid inverter's bus (its EV charger settings in
iSolarCloud) is under the inverter's energy management. The inverter then
writes the wallbox's own output current (holding 21203 on the wallbox) every
few seconds, and **a write to the wallbox's own registers is overwritten
within seconds**: the charge is controlled here, at the inverter, at unit 1.
Measured at gerd's (SH8.0RT-V112, AC22E-01) on 2026-11-14, over the
inverter's LAN cable and through its WiNet-S alike; the wiki's
`gerd-wallbox-inverter-control-2026-11-14` source has every write and what the
car did.

In its own module, as the wallbox's and the battery's maps are:
`registers.py` is held field by field to the YAML package's record, which has
no wallbox. Read only here. Nothing is writable until the integration's write
table names it; the words and their order are below, as measured.

**What was measured** (register numbers, one above the protocol address):

* 33540, charging on/off: 0xAA on, 0x55 off. Writing off stops a charge
  within a second; writing on starts one within about ten seconds, the car
  ramped up from 6 A as the inverter raises the wallbox's offer.
* 33541, charging mode: 160 fast charge, 161 PV surplus, 163 user defined
  (162 quantity and time, by the ioBroker thread, not seen). Switching has
  side effects: **to user defined switches charging on**; **from user defined
  to fast charge, and from fast charge to PV surplus, end the session**. A
  controller that switches mode and wants a charge writes charging on after.
* 33545, the user-defined current, 0.1 A per count. **Written only while the
  mode is user defined**: in fast charge every write was refused with
  exception 0x04. 6.0 A is the lowest the inverter takes (5.0 A refused); it
  took 33.0 A on a 32 A wallbox, so the cap at the rating is the caller's. A
  lower current applied within six seconds, a higher one was ramped (8 to
  12 A in about 20 s). The car drew about 0.5 A under the setting.
* 33550, surplus from the grid: 0x55 no, 0xAA yes (ioBroker thread). Set to
  yes with PV surplus, the inverter still ended the charge with 1.7 kW of sun
  and the battery at its minimum: what it does is not established.
"""

from __future__ import annotations

from modbus_connection.model import Component, gauge, integer

from ..addresses import reg

#: The words of the on/off register and of the grid-surplus flag.
ON = 0xAA
OFF = 0x55

FAST = 160
PV_SURPLUS = 161
QUANTITY_AND_TIME = 162
USER_DEFINED = 163

#: What the charging mode's codes mean. 162 is from the ioBroker thread only.
MODES: dict[int, str] = {
    FAST: "fast",
    PV_SURPLUS: "pv_surplus",
    QUANTITY_AND_TIME: "quantity_and_time",
    USER_DEFINED: "user_defined",
}

#: The user-defined current's scale, in amperes per count. Settled by what the
#: car drew, not by a readback.
AMPS_PER_COUNT = 0.1

#: The lowest user-defined current the inverter takes. 5.0 A was refused.
MIN_AMPS = 6.0


class EvChargerControl(Component):
    """The inverter's settings for the wallbox it manages, at unit 1."""

    register_space = "holding"

    charging_raw = integer(reg(33540), signed=False)
    """Charging on (0xAA) or off (0x55). Measured here."""

    mode_raw = integer(reg(33541), signed=False)
    """The charging mode, as a code; see `MODES`. Measured here."""

    user_current = gauge(reg(33545), AMPS_PER_COUNT, signed=False, unit="A")
    """The current in user-defined mode. Measured here, by what the car drew."""

    grid_surplus_raw = integer(reg(33550), signed=False)
    """Whether PV-surplus charging may take from the grid. Named elsewhere."""

    @property
    def charging(self) -> bool | None:
        """Whether charging is switched on; None for a word that is neither."""
        raw = self.charging_raw
        return None if raw is None else {ON: True, OFF: False}.get(raw)

    @property
    def mode(self) -> str | None:
        """The charging mode's name, or None for a code nobody has named."""
        raw = self.mode_raw
        return None if raw is None else MODES.get(raw)


#: The protocol addresses, for a caller that writes them.
CHARGING = reg(33540)
MODE = reg(33541)
USER_CURRENT = reg(33545)
GRID_SURPLUS = reg(33550)


def manages_a_wallbox(mode_raw: int | None) -> bool | None:
    """Return True when the inverter's block shows a wallbox under its management.

    None when it cannot be told: the register did not answer, or holds a code
    nobody has named. What an inverter with no wallbox reads here is not
    measured, so a 0 says nothing either way.
    """
    if mode_raw is None:
        return None
    return True if mode_raw in MODES else None


def user_current_word(amps: float, rating_a: float) -> int:
    """Return the word for a user-defined current, or raise ValueError.

    Between 6 A and the wallbox's rating: the inverter refuses less and does
    not stop at the rating itself.
    """
    if not MIN_AMPS <= amps <= rating_a:
        raise ValueError(
            f"{amps} A is outside {MIN_AMPS} A to the wallbox's {rating_a} A rating"
        )
    return round(amps / AMPS_PER_COUNT)


def mode_writes(mode: int, *, charge: bool) -> list[tuple[int, int]]:
    """Return the writes, in order, that switch to `mode`.

    Leaving user-defined mode or entering PV surplus ends a session, so a
    caller that wants a charge afterwards gets charging switched on after the
    mode. User-defined mode switches it on by itself.
    """
    if mode not in MODES:
        raise ValueError(f"{mode} is not a charging mode")
    writes = [(MODE, mode)]
    if charge and mode != USER_DEFINED:
        writes.append((CHARGING, ON))
    return writes


def current_writes(
    amps: float, *, mode_raw: int, rating_a: float
) -> list[tuple[int, int]]:
    """Return the writes that set the user-defined current, or raise ValueError.

    Only in user-defined mode: in any other the inverter refuses the write.
    """
    if mode_raw != USER_DEFINED:
        raise ValueError(
            "the user-defined current is written only in user-defined mode; "
            "the inverter refuses it in any other"
        )
    return [(USER_CURRENT, user_current_word(amps, rating_a))]


def charging_writes(on: bool) -> list[tuple[int, int]]:
    """Return the write that starts or stops a charge."""
    return [(CHARGING, ON if on else OFF)]
