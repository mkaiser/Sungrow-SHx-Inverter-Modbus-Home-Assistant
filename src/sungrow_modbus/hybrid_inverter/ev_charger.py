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
no wallbox; it lists this component among the inverter's, polled on the
medium tier. The four words are writable; the integration's write table
(`scripts/generate/tables/writes.py`) is what exposes them, behind
`Capability.EV_CHARGER`, granted only while the mode reads a named code.

**What was measured** (register numbers, one above the protocol address):

* 33540, charging on/off: 0xAA on, 0x55 off. Writing off stops a charge
  within a second; writing on starts one within about ten seconds, the car
  ramped up from 6 A as the inverter raises the wallbox's offer.
* 33541, charging mode: 160 fast charge, 161 PV surplus, 163 user defined
  (162 scheduled charging, set from the app at gerd's on 2026-11-20). Switching has
  side effects: **to user defined from off switches charging on** (the car
  starts at 6 A); **while charging, to user defined, from user defined to
  fast charge, and from fast charge to PV surplus, end the session**. The
  inverter turns its charging word off only after a delay, within a second
  from user defined to fast and 16 s from fast to user defined (gerd's,
  2026-11-17). Writing the mode already set, or charging on while on, changes
  nothing. A controller that switches mode and wants a charge writes charging
  on after the session has ended, or the inverter's own off overwrites it.
* 33545, the user-defined current, 0.1 A per count. **Written only while the
  mode is user defined**: in fast charge every write was refused with
  exception 0x04. 6.0 A is the lowest the inverter takes (5.0 A refused); it
  took 33.0 A on a 32 A wallbox, so the cap at the rating is the caller's. A
  lower current applied within six seconds, a higher one was ramped (8 to
  12 A in about 20 s). The car drew about 0.5 A under the setting.
* 33546-33549, user-defined mode's daily window: its start and its end, each a
  U32 low word first, seconds since 1970 of the **local** time written as if
  it were UTC. The app's save writes it with mode 163; its end ends a session
  and moves the window a day on, its start switches charging on by itself.
  Writable only in mode 163, and only as one four-word write (gerd's,
  2026-11-20). Read here, not written.
* 33550, surplus from the grid: 0x55 no, 0xAA yes. It is the app's energy
  purchase (*Netzbezug*) in PV surplus: switched in the app, it followed within
  5 s both ways. Set to yes with PV surplus, the inverter still ended the
  charge with 1.7 kW of sun and the battery at its minimum, and started none
  with no sun: what it changes is not established.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from modbus_connection.model import Component, gauge, integer, uint32

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

    ev_charger_charging_raw = integer(
        reg(33540), signed=False, nan=0xFFFF, writable=True
    )
    """Charging on (0xAA) or off (0x55). Measured here."""

    ev_charger_mode_raw = integer(reg(33541), signed=False, nan=0xFFFF, writable=True)
    """The charging mode, as a code; see `MODES`. Measured here."""

    ev_charger_user_current = gauge(
        reg(33545), AMPS_PER_COUNT, signed=False, nan=0xFFFF, unit="A", writable=True
    )
    """The current in user-defined mode. Measured here, by what the car drew."""

    ev_charger_grid_purchase_raw = integer(
        reg(33550), signed=False, nan=0xFFFF, writable=True
    )
    """Whether PV-surplus charging may buy from the grid: the app's *Netzbezug*
    (energy purchase). Measured here: it followed the app's switch both ways."""

    ev_charger_window_start_raw = uint32(
        reg(33546), word_order="little", nan=0xFFFFFFFF
    )
    """User-defined mode's daily window, its start: local time as if UTC."""

    ev_charger_window_end_raw = uint32(reg(33548), word_order="little", nan=0xFFFFFFFF)
    """User-defined mode's daily window, its end: local time as if UTC."""

    @property
    def ev_charger_window(self) -> tuple[str, str] | None:
        """The user-defined window as two wall-clock times, or None.

        `window_times` says how the words are read.
        """
        return window_times(
            self.ev_charger_window_start_raw, self.ev_charger_window_end_raw
        )

    @property
    def ev_charger_charging(self) -> bool | None:
        """Whether charging is switched on; None for a word that is neither."""
        raw = self.ev_charger_charging_raw
        return None if raw is None else {ON: True, OFF: False}.get(raw)

    @property
    def ev_charger_mode(self) -> str | None:
        """The charging mode's name, or None for a code nobody has named."""
        raw = self.ev_charger_mode_raw
        return None if raw is None else MODES.get(raw)


#: The protocol addresses, for a caller that writes them.
CHARGING = reg(33540)
MODE = reg(33541)
USER_CURRENT = reg(33545)
GRID_SURPLUS = reg(33550)


def window_times(start: int | None, end: int | None) -> tuple[str, str] | None:
    """Return a daily window's start and end as "HH:MM", or None.

    Each word pair is the local wall-clock time stored as if it were UTC, so
    it is read back as UTC and never converted. The window repeats daily and
    moves a day on at its end, so only the times are shown, not the dates. An
    end on the day after its start at midnight is "24:00": midnight to
    midnight is a whole day, which "00:00" to "00:00" would hide. A pair that
    reads 0, or an end not after its start, is no window anybody set (a
    dongle's 0 is not evidence; wiki: zero-means-absent).
    """
    if not start or not end or end <= start:
        return None
    begins = datetime.fromtimestamp(start, UTC)
    ends = datetime.fromtimestamp(end, UTC)
    if ends - begins > timedelta(days=1):
        return None
    until = ends.strftime("%H:%M")
    if until == "00:00" and ends.date() > begins.date():
        until = "24:00"
    return begins.strftime("%H:%M"), until


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
    """Return the writes, in order, that switch to `mode` and keep `charge`.

    Leaving user-defined mode or entering PV surplus ends a session, so a
    caller that wants a charge afterwards gets charging switched on after the
    mode. User-defined mode switches charging on by itself from off, so a
    caller that had it off gets it switched off again after the mode.

    Watched from Home Assistant at gerd's on 2026-11-24, one client: fast to
    user defined and back four times ended no session, where the app's own
    user defined to fast did. To PV surplus the session ended and the word,
    written on here, read off about a minute later; with surplus there the
    inverter drives that word by itself, so it is not written again.
    """
    if mode not in MODES:
        raise ValueError(f"{mode} is not a charging mode")
    writes = [(MODE, mode)]
    if charge and mode != USER_DEFINED:
        writes.append((CHARGING, ON))
    if not charge and mode == USER_DEFINED:
        writes.append((CHARGING, OFF))
    return writes
