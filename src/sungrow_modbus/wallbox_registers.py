"""The AC011E/AC22E wallbox registers, which Sungrow does not document.

Hand-written, and in its own module for the same reason
`battery_registers.py` is: `registers.py` is **generated** from
`doc/legacy_entity_map.json`, which is the inverter's map, and the wallbox is
not in it. The YAML package never covered a wallbox at all, so unlike the SBR
there is not even an opt-in file to port -- there is only measurement.

**Every address here comes from `doc/wallbox_registers.md`**, which is what
three independent sources agree on: one reading taken off an AC22E-01 through
a WiNet-S on 2026-09-08, and the two community projects that made their own
maps. That document carries a confidence mark per register, and this module
repeats it per field, because a name is worth exactly what its evidence is:

* **three sources** -- measured here and named the same way by both projects.
  As solid as this gets without a manufacturer document.
* **two sources** -- measured here and named by one of them.
* **measured here** -- established from how it behaved across the session;
  neither project names it.
* **named elsewhere** -- one or both projects name it, and the value read here
  is consistent but does not by itself prove it.
* **open** -- nobody, including this measurement, can name it.

That last mark applies to exactly one register, 21313, and it is declared
here anyway: the survey then carries it for whoever recognises it, and it
gets no entity, because inventing a meaning is worse than admitting there
isn't one.

**Not at unit 1.** A wallbox answers at unit 3 through a WiNet-S and 248
direct, and a full sweep of one /24 found it on *neither* an address of its
own -- only behind the endpoint that already answered. So it cannot be found
by looking for it; it has to be asked for on a connection that exists. See
`sungrow_modbus.wallbox.probe_units`.

**Codes stay integers.** `modbus_connection` has an `enum()` field, and using
it here would be neater to read -- but `scripts/generate_scan_plan.py`
records this map into a committed artefact that a contributor's zip decodes
from with its own decoder, and that decoder produces an `int` where an
`enum()` field produces an `Enum`. The two would disagree, and
`tests/test_portable_decoder.py` compares them field by field for good
reason. So the raw code is the field and the meaning is a property, which is
the same shape the SBR's packed position words take.
"""

from __future__ import annotations

from modbus_connection.model import Component, gauge, integer, string, uint32

#: What register 21317's charging status codes mean.
#:
#: The one table here that **cannot** be measured. Watching a session end
#: shows the register settle on 6, and only a source with the whole table
#: says 6 is *Completed* rather than idle -- a distinction every finished
#: charge depends on. Both community projects agree on it.
CHARGING_STATUS: dict[int, str] = {
    1: "idle",
    2: "standby",
    3: "charging",
    4: "suspended by the charge point",
    5: "suspended by the vehicle",
    6: "completed",
    7: "reserved",
    8: "disabled",
    9: "fault",
}

#: Single or three phase, for both the reading and the setpoint.
PHASE_MODE: dict[int, str] = {0: "three phase", 1: "single phase"}

#: How a session is started. `2` is a card swipe.
START_MODE: dict[int, str] = {
    0: "stopped",
    1: "start with EMS",
    2: "start by swiping",
}

#: Which wallbox a device type code names.
#:
#: `0x3F80` was read here; the other two come from the community projects, so
#: a device answering either is recognised without ever having been measured.
MODELS: dict[int, str] = {
    0x3F80: "AC22E-01",
    0x20DA: "AC011E-01",
    0x20ED: "AC007-00",
}


def _meaning(table: dict[int, str], code: object) -> str | None:
    """Return what a code means, or None -- never a made-up label.

    `None` for an unknown code rather than "unknown", because an entity
    reporting the string "unknown" looks like a reading and sorts among real
    ones. A missing value is the honest form of not knowing.
    """
    if code is None:
        return None
    return table.get(int(code))


class WallboxIdentity(Component):
    """What the wallbox is: model, type code, phase count, firmware.

    Read once at setup rather than polled -- none of it changes while the
    integration is loaded, and it is what the device and its entities are
    named from.
    """

    register_space = "input"

    model_name = string(21215, 5)
    """Model as text (reg 21216-21220). Read `AC22E-01`. Two sources."""

    device_type_code = integer(21223, signed=False)
    """Model as a code (reg 21224). Read `0x3F80`. Two sources.

    Cross-checks the name above, and is the field `MODELS` is looked up by --
    a device answering `0x20DA` is an AC011E-01 that nobody here has read.
    """

    phase_count = integer(21224, signed=False)
    """How many phases are wired (reg 21225). Read 1. Two sources.

    Not the same question as `phase_mode`, which is how many it is *using*.
    """

    version_string = string(21225, 10)
    """Firmware as text (reg 21226-21235). Read `LE-01.1E1.001.`.

    Measured here, and known to be a **fragment**: the string is cut off at
    ten registers and the document records that rather than guessing the
    length.
    """

    @property
    def model(self) -> str | None:
        """Name the model from its type code, falling back to the text."""
        named = _meaning(MODELS, self.device_type_code)
        if named is not None:
            return named
        text = self.model_name
        return text or None


class WallboxRatings(Component):
    """What it is rated for, and what it is allowed to draw.

    Its own component because it moves on the scale of a configuration
    change, not a charging session -- and because it sits in its own address
    band, 21262-21273, so pooling it with the live block would read thirty
    registers nobody is watching every ten seconds.
    """

    register_space = "input"

    nominal_voltage = integer(21261, signed=False, unit="V")
    """Rated voltage (reg 21262). Read 230 V. Three sources."""

    rated_current = gauge(21262, 0.1, signed=False, unit="A")
    """Rated current (reg 21263). Read 32.0 A. Measured here."""

    phase_mode_raw = integer(21269, signed=False)
    """Single or three phase, as a code (reg 21270). Read 1. Three sources."""

    minimum_charging_power = integer(21271, signed=False, unit="W")
    """Lowest power it will deliver (reg 21272). Read 1380 W. Named elsewhere.

    1380 W is 6 A at 230 V, which is the minimum a Type 2 charge point may
    offer -- so the value is consistent with the name, which is what "named
    elsewhere" means and all it means.
    """

    maximum_charging_power = integer(21272, signed=False, unit="W")
    """Highest power it will deliver (reg 21273). Read 22080 W. Two sources.

    22080 W is 32 A across three phases at 230 V, and this unit is an
    AC22E-01 -- the 22 in the model name. That agreement is why this one is
    solid.
    """

    @property
    def phase_mode(self) -> str | None:
        """Whether it is charging on one phase or three."""
        return _meaning(PHASE_MODE, self.phase_mode_raw)


class WallboxLive(Component):
    """What it is doing right now: power, current, session, status.

    The block worth polling quickly, and the only one that is. Twenty-three
    registers in one read.
    """

    register_space = "input"

    lifetime_energy = uint32(21299, word_order="little", unit="Wh")
    """Energy delivered since installation (reg 21300-21301). Measured here.

    Read 280557 Wh. Low word first, which is what this is -- read the other
    way round a 280 kWh counter reads as 1.2 GWh, and that is the mistake
    this field is most likely to hide.
    """

    phase_a_voltage = gauge(21301, 0.1, signed=False, unit="V")
    """Phase A voltage (reg 21302). Three sources."""

    phase_a_current = gauge(21302, 0.1, signed=False, unit="A")
    """Phase A current (reg 21303). Three sources."""

    phase_b_voltage = gauge(21303, 0.1, signed=False, unit="V")
    """Phase B voltage (reg 21304). Three sources."""

    phase_b_current = gauge(21304, 0.1, signed=False, unit="A")
    """Phase B current (reg 21305). Three sources."""

    phase_c_voltage = gauge(21305, 0.1, signed=False, unit="V")
    """Phase C voltage (reg 21306). Three sources."""

    phase_c_current = gauge(21306, 0.1, signed=False, unit="A")
    """Phase C current (reg 21307). Three sources."""

    charging_power = uint32(21307, word_order="little", unit="W")
    """Power being delivered (reg 21308-21309). Three sources."""

    session_energy = uint32(21309, word_order="little", unit="Wh")
    """Energy delivered this session (reg 21310-21311). Three sources.

    Read 105 Wh against a lifetime 280557 Wh, which is the pairing that
    identifies which of the two counters is which.
    """

    control_pilot_voltage = gauge(21311, 0.01, signed=False, unit="V")
    """Control pilot voltage (reg 21312). Read 9.04 V. Two sources.

    The Type 2 signalling line, and its value is diagnostic in itself: 12 V
    is nothing plugged in, 9 V a vehicle connected and not charging, 6 V a
    vehicle charging. Read 9.04 with a car plugged in and finished, which
    agrees.
    """

    unnamed_register_21313 = integer(21312, signed=False)
    """Register 21313, which **nobody can name**. Read 0. Open.

    Named for its address on purpose. Three independent measurements of this
    wallbox family exist and none of them knows what this is, so it is
    carried in the survey for whoever recognises it and gets no entity --
    inventing a meaning would be worse than the gap.
    """

    start_mode_raw = integer(21313, signed=False)
    """How a session starts, as a code (reg 21314). Read 1. Two sources."""

    power_request = integer(21314, signed=False)
    """Whether it is asking for power (reg 21315). Named elsewhere."""

    power_control_allowed = integer(21315, signed=False)
    """Whether an EMS may set its power (reg 21316). Named elsewhere."""

    charging_status_raw = integer(21316, signed=False)
    """Session state, as a code (reg 21317). Read 6. Three sources.

    See `CHARGING_STATUS`, which is the one table in this file that could not
    be measured: a finished session settles on 6, and only a source with the
    whole table says 6 means *completed* rather than idle.
    """

    charging_started = uint32(21317, word_order="little")
    """When this session began (reg 21318-21319). Named elsewhere.

    An epoch-shaped number that is the **wallbox's own local time**, not UTC
    -- decoded as UTC it read two hours off in Berlin and matched the wall
    clock exactly. The inverter's clock registers have the same quirk. So
    anything rendering this must not attach a zone.
    """

    charging_ended = uint32(21319, word_order="little")
    """When this session ended (reg 21320-21321). Named elsewhere.

    Equal to `charging_started` on the reading taken, because the session had
    finished -- which is consistent and is also why neither field is better
    than "named elsewhere" on one reading.
    """

    available_current = gauge(21321, 0.1, signed=False, unit="A")
    """Current currently available to the vehicle (reg 21322). Measured here.

    Read 16.1 A while `output_current_setting` held 15.1, so the two are not
    the same number and this is the one the vehicle sees.
    """

    @property
    def charging_status(self) -> str | None:
        """What the session is doing, in words."""
        return _meaning(CHARGING_STATUS, self.charging_status_raw)

    @property
    def start_mode(self) -> str | None:
        """How this session was started."""
        return _meaning(START_MODE, self.start_mode_raw)

    @property
    def charging(self) -> bool | None:
        """Whether power is flowing to a vehicle right now.

        From the status code rather than from the power, deliberately: a
        vehicle that has stopped drawing mid-session reads 0 W and is still
        charging as far as the charge point is concerned, and the two states
        need telling apart.
        """
        code = self.charging_status_raw
        if code is None:
            return None
        return int(code) == 3


class WallboxSettings(Component):
    """The holding registers, which are settings rather than readings.

    Read, not written. Nothing in this library writes to a wallbox: the write
    table in `scripts/writes.py` is the only place a writable register is
    declared, and no wallbox register is in it. Starting somebody's car
    charging from a stale automation is not a thing to enable on one
    measurement of one unit.
    """

    register_space = "holding"

    output_current_setting = gauge(21202, 0.1, signed=False, unit="A")
    """Current the charge point is set to offer (reg 21203). Two sources."""

    phase_mode_setpoint_raw = integer(21203, signed=False)
    """Single or three phase, as configured (reg 21204). Three sources."""

    charger_enabled_raw = integer(21210, signed=False)
    """Whether the charge point is enabled (reg 21211). Read 1. Two sources."""

    start_stop_raw = integer(21211, signed=False)
    """Start/stop command state (reg 21212). Two sources.

    Note the polarity, which is the trap: **0 is start and 1 is stop**, the
    opposite way round from `charger_enabled` above where 1 is enabled. Both
    were read on the same session -- enabled 1, start_stop 1 -- on a wallbox
    that had finished charging and was not stopped.
    """

    mileage_per_kwh = gauge(21231, 0.1, signed=False, unit="km/kWh")
    """Range added per kWh, as configured (reg 21232). Named elsewhere.

    A display preference rather than a measurement: it is what the wallbox
    multiplies by to show a driver how far they have charged.
    """

    @property
    def phase_mode_setpoint(self) -> str | None:
        """How many phases it is configured to use."""
        return _meaning(PHASE_MODE, self.phase_mode_setpoint_raw)

    @property
    def charger_enabled(self) -> bool | None:
        """Whether the charge point is enabled at all."""
        code = self.charger_enabled_raw
        return None if code is None else int(code) == 1

    @property
    def stopped(self) -> bool | None:
        """Whether the charge point has been commanded to stop.

        Named for the `1` rather than for the `0`, so the polarity is in the
        name and cannot be read backwards by somebody skimming.
        """
        code = self.start_stop_raw
        return None if code is None else int(code) == 1


#: The wallbox's components, by the name a description refers to them by.
COMPONENTS: dict[str, type[Component]] = {
    "wallbox_identity": WallboxIdentity,
    "wallbox_ratings": WallboxRatings,
    "wallbox_live": WallboxLive,
    "wallbox_settings": WallboxSettings,
}
