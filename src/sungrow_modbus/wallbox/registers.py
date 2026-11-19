"""The AC011E/AC22E wallbox registers, which Sungrow does not document.

In its own module for the same reason the battery's map is:
`hybrid_inverter/registers.py` is held field by field to
`doc/legacy_entity_map.json`, the inverter's record, and the wallbox is not in
it. The YAML package never covered a wallbox at all, so unlike the SBR there
is not even an opt-in file to port -- there is only measurement.

**Every address here comes from `doc/wallbox_registers.md`**, which is what
three independent sources agree on: readings taken off one AC22E-01, through
a WiNet-S and at its own address, and the two community projects that made
their own maps. That document carries a confidence mark per register, and this module
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
here anyway: the diagnosis then carries it for whoever recognises it, and it
gets no entity, because inventing a meaning is worse than admitting there
isn't one.

**Not at unit 1.** A wallbox answers at unit 3 through a WiNet-S, and at
unit 248 at its own LAN address over TLS on port 516; never through the
inverter's own LAN port. A sweep for port 502 does not find it, so it is
asked for on a connection that exists, or at an address its owner gives. See
`sungrow_modbus.wallbox.probe_units`.

**Over TLS a read must start on a data point's first register**, or it times
out. Every component here starts on one, so the same components poll either
path; `doc/wallbox_registers.md` has the map of valid starts.

**Codes stay integers.** The raw code is the field and the meaning is a
property, the same shape the SBR's packed position words take, so a document
publishes the number the charger sent beside what it is taken to mean.

From github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant (MIT),
where `doc/architecture.md` records which document or measurement each
register comes from. Keep this line with any copy -- `doc/attribution.md`.
"""

from __future__ import annotations

from modbus_connection.model import Component, gauge, integer, uint32

from ..addresses import reg
from ..model import RegisterValue, energy_counter, string

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

#: Whether the charge point is enabled, holding 21211.
ENABLED: dict[int, str] = {0: "disabled", 1: "enabled"}

#: The start/stop command, holding 21212. **0 is start and 1 is stop**, the
#: opposite polarity to `ENABLED`.
START_STOP: dict[int, str] = {0: "start", 1: "stop"}

#: Whether a plugged-in car starts charging by itself, holding 21298.
PLUG_AND_PLAY: dict[int, str] = {0: "off", 1: "on"}

#: Which wallbox a device type code names.
#:
#: `0x3F80` was read here; the other two come from the community projects, so
#: a device answering either is recognised without ever having been measured.
MODELS: dict[int, str] = {
    0x3F80: "AC22E-01",
    0x20DA: "AC011E-01",
    0x20ED: "AC007-00",
}


def _meaning(table: dict[int, str], code: RegisterValue) -> str | None:
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

    On the slow tier with the ratings and settings -- none of it changes in
    the course of a session, and it is what the device and its entities are
    named from.
    """

    register_space = "input"

    model_name = string(reg(21216), 5)
    """Model as text. Read `AC22E-01`. Two sources."""

    device_type_code = integer(reg(21224), signed=False)
    """Model as a code. Read `0x3F80`. Two sources.

    Cross-checks the name above, and is the field `MODELS` is looked up by --
    a device answering `0x20DA` is an AC011E-01 that nobody here has read.
    """

    phase_count = integer(reg(21225), signed=False)
    """How many phases are wired. Read 1. Two sources.

    Not the same question as `phase_mode`, which is how many it is *using*.
    """

    version_string = string(reg(21226), 10)
    """Firmware as text. Read `LE-01.1E1.001.901.25`. Measured here.

    Whole only when read in one request starting at 21226: the wallbox
    answers a read that starts inside a string with zeros for the rest of it,
    which is why `dump.WALLBOX_BANDS` gives it a band of its own.
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
    band, 21262-21273, so pooling it with the live block would read nearly
    forty registers nobody is watching on every fast poll.
    """

    register_space = "input"

    nominal_voltage = integer(reg(21262), signed=False, unit="V")
    """Rated voltage. Read 230 V. Three sources."""

    rated_current = gauge(reg(21263), 0.1, signed=False, unit="A")
    """Rated current. Read 32.0 A. Measured here."""

    phase_mode_raw = integer(reg(21270), signed=False)
    """Single or three phase, as a code. Read 1. Three sources."""

    minimum_charging_power = integer(reg(21272), signed=False, unit="W")
    """Lowest power it will deliver. Read 1380 W. Named elsewhere.

    1380 W is 6 A at 230 V, which is the minimum a Type 2 charge point may
    offer -- so the value is consistent with the name, which is what "named
    elsewhere" means and all it means.
    """

    maximum_charging_power = integer(reg(21273), signed=False, unit="W")
    """Highest power it will deliver. Read 22080 W. Two sources.

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

    lifetime_energy = energy_counter(
        reg(21300), scale=1, word_order="little", unit="Wh"
    )
    """Energy delivered since installation. Measured here.

    Read 280557 Wh. Low word first, which is what this is -- read the other
    way round a 280 kWh counter reads as 1.2 GWh, and that is the mistake
    this field is most likely to hide.
    """

    phase_a_voltage = gauge(reg(21302), 0.1, signed=False, unit="V")
    """Phase A voltage. Three sources."""

    phase_a_current = gauge(reg(21303), 0.1, signed=False, unit="A")
    """Phase A current. Three sources."""

    phase_b_voltage = gauge(reg(21304), 0.1, signed=False, unit="V")
    """Phase B voltage. Three sources."""

    phase_b_current = gauge(reg(21305), 0.1, signed=False, unit="A")
    """Phase B current. Three sources."""

    phase_c_voltage = gauge(reg(21306), 0.1, signed=False, unit="V")
    """Phase C voltage. Three sources."""

    phase_c_current = gauge(reg(21307), 0.1, signed=False, unit="A")
    """Phase C current. Three sources."""

    charging_power = uint32(reg(21308), word_order="little", unit="W")
    """Power being delivered. Three sources."""

    session_energy = energy_counter(reg(21310), scale=1, word_order="little", unit="Wh")
    """Energy delivered this session. Three sources.

    Read 105 Wh against a lifetime 280557 Wh, which is the pairing that
    identifies which of the two counters is which.
    """

    control_pilot_voltage = gauge(reg(21312), 0.01, signed=False, unit="V")
    """Control pilot voltage. Read 9.04 V. Two sources.

    The Type 2 signalling line, and its value is diagnostic in itself: 12 V
    is nothing plugged in, 9 V a vehicle connected and not charging, 6 V a
    vehicle charging. Read 9.04 with a car plugged in and finished, which
    agrees.
    """

    unnamed_register_21313 = integer(reg(21313), signed=False)
    """Register 21313, which **nobody can name**. Read 0. Open.

    Named for its address on purpose. Three independent measurements of this
    wallbox family exist and none of them knows what this is, so it is
    carried in the diagnosis for whoever recognises it and gets no entity --
    inventing a meaning would be worse than the gap.
    """

    start_mode_raw = integer(reg(21314), signed=False)
    """How a session starts, as a code. Read 1. Two sources."""

    power_request = integer(reg(21315), signed=False)
    """Whether it is asking for power. Named elsewhere."""

    power_control_allowed = integer(reg(21316), signed=False)
    """Whether an EMS may set its power. Named elsewhere."""

    charging_status_raw = integer(reg(21317), signed=False)
    """Session state, as a code. Read 6. Three sources.

    See `CHARGING_STATUS`, which is the one table in this file that could not
    be measured: a finished session settles on 6, and only a source with the
    whole table says 6 means *completed* rather than idle.
    """

    charging_started = uint32(reg(21318), word_order="little")
    """When this session began. Named elsewhere.

    An epoch-shaped number that is the **wallbox's own local time**, not UTC
    -- decoded as UTC it read two hours off in Berlin and matched the wall
    clock exactly. The inverter's clock registers have the same quirk. So
    anything rendering this must not attach a zone.
    """

    charging_ended = uint32(reg(21320), word_order="little")
    """When this session ended. Named elsewhere.

    Equal to `charging_started` on the reading taken, because the session had
    finished -- which is consistent and is also why neither field is better
    than "named elsewhere" on one reading.
    """

    available_current = gauge(reg(21322), 0.1, signed=False, unit="A")
    """Current currently available to the vehicle. Measured here.

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

    Read, not written. The integration never writes to a wallbox: the write
    table in `scripts/generate/tables/writes.py` is the only place a writable register
    is declared, and no wallbox register is in it. `capability_test` writes three of
    these, through a port, with leave, to measure the output current's scale.
    Starting somebody's car charging from a stale automation is not a thing to
    enable on one measurement of one unit.
    """

    register_space = "holding"

    output_current_setting = gauge(reg(21203), 0.1, signed=False, unit="A")
    """Current the charge point is set to offer. Two sources.

    Under an inverter's management the inverter writes it (gerd's,
    2026-11-17): in user-defined mode it is the user current exactly, and the
    car draws about 0.7 A less; in fast charge it is the inverter's offer,
    24-28 A on a car that took 16 A, so it is not the car's current there.
    """

    phase_mode_setpoint_raw = integer(reg(21204), signed=False)
    """Single or three phase, as configured. Three sources."""

    charger_enabled_raw = integer(reg(21211), signed=False)
    """Whether the charge point is enabled. Read 1. Two sources."""

    start_stop_raw = integer(reg(21212), signed=False)
    """Start/stop command state. Two sources.

    Note the polarity, which is the trap: **0 is start and 1 is stop**, the
    opposite way round from `charger_enabled` above where 1 is enabled. Both
    were read on the same session -- enabled 1, start_stop 1 -- on a wallbox
    that had finished charging and was not stopped.
    """

    mileage_per_kwh = gauge(reg(21232), 0.1, signed=False, unit="km/kWh")
    """Range added per kWh, as configured: the app's *Fahrstrecke pro kWh*.
    Named elsewhere, and checked against the app (5.0 read 50).

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


class WallboxAppSettings(Component):
    """The settings Sungrow's app offers as the charger's system parameters.

    Holding registers, read and never written. Mapped on 2026-11-14 at gerd's
    AC22E-01: each setting changed in iSolarCloud and back, the wallbox read
    whole after every save, and only these words moved (wiki:
    `gerd-wallbox-app-settings-2026-11-14`). Each has an echo in the input
    space (21362 and 21363), not read. **Only the wallbox's own address
    answers them**: a WiNet-S forwards holding registers only below 21250, so
    behind a dongle this component fails alone and its entities stay
    unavailable.
    """

    register_space = "holding"

    plug_and_play_raw = integer(reg(21298), signed=False)
    """Plug&Play: 1, a plugged-in car starts charging by itself; 0, it waits
    for a start. Measured here, against the app."""

    offline_current = gauge(reg(21299), 0.1, signed=False, unit="A")
    """The current offered without a connection to an EMS (the app's
    *Offline-Ladestrom*, 6-32 A). Measured here, against the app.

    It does not follow the power limit: it stayed 32 A at an 11 kW limit, in
    the registers and the app alike.
    """

    power_limit = gauge(reg(21313), 0.1, signed=False, unit="kW")
    """The power limit (the app's *Leistungsgrenze*): 22 or 11 kW. Measured
    here, against the app; the rated current (input 21263) and the maximum
    charging power (input 21273) follow it. Not input 21313, which is unnamed.
    """

    @property
    def plug_and_play(self) -> bool | None:
        """Whether a plugged-in car starts charging without a start command."""
        code = self.plug_and_play_raw
        return None if code is None else int(code) == 1


#: The wallbox's components, by the name a description refers to them by.
COMPONENTS: dict[str, type[Component]] = {
    "wallbox_identity": WallboxIdentity,
    "wallbox_ratings": WallboxRatings,
    "wallbox_live": WallboxLive,
    "wallbox_settings": WallboxSettings,
    "wallbox_app_settings": WallboxAppSettings,
}


#: How strongly each field is held, as `doc/wallbox_registers.md`'s
#: Confidence column marks it, by the name a document publishes it under --
#: a coded field without its `_raw`. Travels with every published value, so a
#: reader of one diagnosis need not find that document to know how much to
#: trust a line. The marks are the five the module docstring defines.
CONFIDENCE: dict[str, str] = {
    "model_name": "two sources",
    "device_type_code": "two sources",
    "phase_count": "two sources",
    "version_string": "measured here",
    "nominal_voltage": "three sources",
    "rated_current": "measured here",
    "phase_mode": "three sources",
    "minimum_charging_power": "named elsewhere",
    "maximum_charging_power": "two sources",
    "lifetime_energy": "measured here",
    "phase_a_voltage": "three sources",
    "phase_a_current": "three sources",
    "phase_b_voltage": "three sources",
    "phase_b_current": "three sources",
    "phase_c_voltage": "three sources",
    "phase_c_current": "three sources",
    "charging_power": "three sources",
    "session_energy": "three sources",
    "control_pilot_voltage": "two sources",
    "unnamed_register_21313": "open",
    "start_mode": "two sources",
    "power_request": "named elsewhere",
    "power_control_allowed": "named elsewhere",
    "charging_status": "three sources",
    "charging_started": "named elsewhere",
    "charging_ended": "named elsewhere",
    "available_current": "measured here",
    "output_current_setting": "two sources",
    "phase_mode_setpoint": "three sources",
    "charger_enabled": "two sources",
    "start_stop": "two sources",
    "mileage_per_kwh": "named elsewhere",
    "plug_and_play": "measured here",
    "offline_current": "measured here",
    "power_limit": "measured here",
}

#: What each coded field's number means, by its published name.
CODES: dict[str, dict[int, str]] = {
    "phase_mode": PHASE_MODE,
    "phase_mode_setpoint": PHASE_MODE,
    "start_mode": START_MODE,
    "charging_status": CHARGING_STATUS,
    "charger_enabled": ENABLED,
    "start_stop": START_STOP,
    "plug_and_play": PLUG_AND_PLAY,
}

#: The two epoch-shaped fields whose value is the wallbox's local clock.
LOCAL_CLOCK: frozenset[str] = frozenset({"charging_started", "charging_ended"})
