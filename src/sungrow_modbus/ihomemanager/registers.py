"""The iHomeManager registers, from Sungrow's own protocol document.

Sungrow's *Communication Protocol of iHomeManager* **V1.0.2** is the source,
with V1.0.1 beside it; both ship in TCzerny/ha-modbus-manager's `docs/`, and
`.wiki/raw/cross-reference-modbus-manager.md` compares that project's MIT template
with them. **No iHomeManager has been measured anywhere**, so every field here
is what a document says, and `CONFIDENCE` names which one:

* **spec V1.0.2** -- in V1.0.2's register tables.
* **spec V1.0.1** -- in V1.0.1 only: channel 2's phase voltages, which
  V1.0.2's table skips.
* **template** -- in the MIT template only, source unstated.
* **field** -- found by a live scan in that project's issue #86.

What the document fixes, and this map follows:

* **Unit 247**, and Modbus TCP on **502, 503 or 504, one connection each**
  (V1.0.2, table 2). So a survey that holds one port shuts out any other
  client on it until it closes.
* **A U32 sends its low word first** ("little-endian for double-word data"),
  as the inverter does. The protocol version's example -- V1.0.2 sent as
  `0x02000100` -- only decodes to 1.0.2 that way.
* **Unavailable** is 0xFFFF / 0xFFFFFFFF unsigned and 0x7FFF / 0x7FFFFFFF
  signed.
* **No serial number.** Neither revision lists one, nor does the template.
  What the device says about itself is a type code (`0x072A`), the protocol
  number ("AW0"), the protocol version and the application software version.
  An undocumented register could still hold one, which is why
  `ihomemanager.document` masks text it finds outside the documented strings.

**Read only.** The holding registers are its controls, and the survey reads
them with function code 3 to record their settings. Nothing here writes.
"""

from __future__ import annotations

from modbus_connection.model import Component, gauge, int32, integer, string, uint32

from ..addresses import reg

#: The unit an iHomeManager answers on, fixed by Sungrow ("changes are not
#: supported").
UNIT = 247

#: What input 8000 answers on every iHomeManager, by the document.
TYPE_CODE = 0x072A

#: Its Modbus TCP ports. **Each takes one connection**, so a port that does
#: not open may only be busy.
PORTS: tuple[int, ...] = (502, 503, 504)

#: Register 8024. 1, 4 and 5 are V1.0.2's; 0 and 2 are the template's.
EMS_MODE: dict[int, str] = {
    0: "AI (template only)",
    1: "self-consumption",
    2: "time plan (template only)",
    4: "VPP",
    5: "compulsory",
}

#: Register 8025.
CHARGE_COMMAND: dict[int, str] = {0xAA: "charge", 0xBB: "discharge", 0xCC: "stop"}

#: Register 8028, feed-in limitation. 1 and 0 here, not 0xAA/0x55.
FEED_IN_LIMITATION: dict[int, str] = {1: "on", 0: "off"}

#: The 0xAA/0x55 pair the other switches use: 8049, 8050 and 8051.
ENABLED: dict[int, str] = {0xAA: "on", 0x55: "off"}

#: Register 8047.
START_STOP: dict[int, str] = {0xCF: "boot", 0xCE: "shutdown"}

#: Register 8048. The template adds 0xA2/0xA3 and an Australian set.
CHARGER_MODE: dict[int, str] = {0xA0: "fast charging", 0xA1: "eco charging"}

#: Register 8552.
CHARGER_STATUS: dict[int, str] = {
    1: "idle (unplugged)",
    2: "standby (plugged)",
    3: "charging",
    6: "charging completed",
}

#: Register 8554, the same encoding as the inverter's 5002.
OUTPUT_TYPE: dict[int, str] = {
    0: "single phase",
    1: "three phase, four wire",
    2: "three phase, three wire",
}


def protocol_version(value: int | None) -> str | None:
    """Render register 8003-8004 as a version: `0x01000200` is `V1.0.2`.

    The bytes, highest first, are major, minor and patch; the lowest is not
    used by the document's one example, and is shown only when it is not 0.
    """
    if value is None:
        return None
    parts = [(int(value) >> shift) & 0xFF for shift in (24, 16, 8, 0)]
    if parts[3] == 0:
        parts = parts[:3]
    return "V" + ".".join(str(part) for part in parts)


class IHomeManagerIdentity(Component):
    """What it is, and how many devices it manages. V1.0.2 table 3, rows 1-5."""

    register_space = "input"

    device_type_code = integer(reg(8000), signed=False)
    """0x072A on every unit, by the document."""

    protocol_number = string(reg(8001), 2)
    """Text: "AW0"."""

    protocol_version_raw = uint32(reg(8003), word_order="little", nan=0xFFFFFFFF)
    """See `protocol_version`."""

    connected_devices = integer(reg(8005), signed=False, nan=0xFFFF)
    """Devices on RS485, WiFi or Ethernet; not those on a DO."""

    devices_in_fault = integer(reg(8006), signed=False, nan=0xFFFF)


class IHomeManagerSystem(Component):
    """The totals it dispatches by. V1.0.2 table 3, rows 6-17."""

    register_space = "input"

    total_rated_active_power = uint32(
        reg(8145), scale=0.1, word_order="little", nan=0xFFFFFFFF, unit="kW"
    )
    total_rated_battery_capacity = uint32(
        reg(8147), scale=0.1, word_order="little", nan=0xFFFFFFFF, unit="kWh"
    )
    battery_power_range = uint32(
        reg(8149), scale=0.1, word_order="little", nan=0xFFFFFFFF, unit="kW"
    )
    """The upper limit a charge or discharge command may ask for (8026)."""

    max_battery_charge_power = gauge(
        reg(8151), 0.1, signed=False, nan=0xFFFF, unit="kW"
    )
    min_battery_charge_power = gauge(
        reg(8152), 0.1, signed=False, nan=0xFFFF, unit="kW"
    )
    max_battery_discharge_power = gauge(
        reg(8153), 0.1, signed=False, nan=0xFFFF, unit="kW"
    )
    min_battery_discharge_power = gauge(
        reg(8154), 0.1, signed=False, nan=0xFFFF, unit="kW"
    )
    inverter_active_power = int32(
        reg(8155), scale=0.01, word_order="little", nan=0x7FFFFFFF, unit="kW"
    )
    """Summed over the connected inverters."""

    grid_active_power = int32(
        reg(8157), scale=0.01, word_order="little", nan=0x7FFFFFFF, unit="kW"
    )
    """At the grid connection point, from GRID.CT. Its sign is not documented."""

    load_active_power = int32(
        reg(8159), scale=0.01, word_order="little", nan=0x7FFFFFFF, unit="kW"
    )
    battery_power = int32(
        reg(8161), scale=0.01, word_order="little", nan=0x7FFFFFFF, unit="kW"
    )
    battery_level = gauge(reg(8163), 0.1, signed=False, nan=0xFFFF, unit="%")


class IHomeManagerEnergy(Component):
    """The grid connection point's counters, from GRID.CT. V1.0.2 rows 18-19."""

    register_space = "input"

    grid_import_energy = uint32(
        reg(8176), scale=0.1, word_order="little", nan=0xFFFFFFFF, unit="kWh"
    )
    grid_export_energy = uint32(
        reg(8178), scale=0.1, word_order="little", nan=0xFFFFFFFF, unit="kWh"
    )


class IHomeManagerSoftware(Component):
    """Its application software version, 30 characters. V1.0.2 row 20."""

    register_space = "input"

    application_software_version = string(reg(8318), 15)


class IHomeManagerMeters(Component):
    """The charger's status and the two CT channels. V1.0.2 rows 21-33.

    Channel 1 is GRID.CT, channel 2 PROD.CT. Row 21 and 22 give the unit
    "0.1 V" for a status and an output type, which is a copying slip in the
    document: both are codes.
    """

    register_space = "input"

    charger_status_raw = integer(reg(8552), signed=False, nan=0xFFFF)
    output_type_raw = integer(reg(8554), signed=False, nan=0xFFFF)
    voltage_a = gauge(reg(8555), 0.1, signed=False, nan=0xFFFF, unit="V")
    """A-B line voltage or A phase voltage, by the output type."""

    voltage_b = gauge(reg(8556), 0.1, signed=False, nan=0xFFFF, unit="V")
    voltage_c = gauge(reg(8557), 0.1, signed=False, nan=0xFFFF, unit="V")
    grid_frequency = gauge(reg(8558), 0.1, signed=False, nan=0xFFFF, unit="Hz")
    phase_a_power = int32(reg(8559), word_order="little", nan=0x7FFFFFFF, unit="W")
    phase_b_power = int32(reg(8561), word_order="little", nan=0x7FFFFFFF, unit="W")
    phase_c_power = int32(reg(8563), word_order="little", nan=0x7FFFFFFF, unit="W")
    channel_2_voltage_a = gauge(reg(8565), 0.1, signed=False, nan=0xFFFF, unit="V")
    channel_2_voltage_b = gauge(reg(8566), 0.1, signed=False, nan=0xFFFF, unit="V")
    channel_2_voltage_c = gauge(reg(8567), 0.1, signed=False, nan=0xFFFF, unit="V")
    channel_2_frequency = gauge(reg(8568), 0.1, signed=False, nan=0xFFFF, unit="Hz")
    channel_2_phase_a_power = int32(
        reg(8569), word_order="little", nan=0x7FFFFFFF, unit="W"
    )
    channel_2_phase_b_power = int32(
        reg(8571), word_order="little", nan=0x7FFFFFFF, unit="W"
    )
    channel_2_phase_c_power = int32(
        reg(8573), word_order="little", nan=0x7FFFFFFF, unit="W"
    )


class IHomeManagerCharger(Component):
    """The charger's power, total and per phase. Field only: issue #86 there."""

    register_space = "input"

    charger_power = int32(reg(8594), word_order="little", nan=0x7FFFFFFF, unit="W")
    charger_phase_a_power = int32(
        reg(8596), word_order="little", nan=0x7FFFFFFF, unit="W"
    )
    charger_phase_b_power = int32(
        reg(8598), word_order="little", nan=0x7FFFFFFF, unit="W"
    )
    charger_phase_c_power = int32(
        reg(8600), word_order="little", nan=0x7FFFFFFF, unit="W"
    )


class IHomeManagerSettings(Component):
    """Its controls, read and never written. V1.0.2 table 4.

    8031's type is S16 in table 4 and S32 in table 7 and in V1.0.1; it is
    read as one word here, and the dump keeps 8032 beside it.
    """

    register_space = "holding"

    ems_mode_raw = integer(reg(8024), signed=False, nan=0xFFFF)
    charge_command_raw = integer(reg(8025), signed=False, nan=0xFFFF)
    charge_power = uint32(
        reg(8026), scale=0.1, word_order="little", nan=0xFFFFFFFF, unit="kW"
    )
    feed_in_limitation_raw = integer(reg(8028), signed=False, nan=0xFFFF)
    feed_in_limit = uint32(
        reg(8029), scale=0.1, word_order="little", nan=0xFFFFFFFF, unit="kW"
    )
    """Template only: an absolute feed-in limit."""

    feed_in_limitation_ratio = gauge(reg(8031), 0.1, nan=0x7FFF, unit="%")
    vpp_heartbeat = integer(reg(8033), signed=False, nan=0xFFFF, unit="s")
    start_stop_raw = integer(reg(8047), signed=False, nan=0xFFFF)
    charger_mode_raw = integer(reg(8048), signed=False, nan=0xFFFF)
    charger_enabled_raw = integer(reg(8049), signed=False, nan=0xFFFF)
    grid_draw_permitted_raw = integer(reg(8050), signed=False, nan=0xFFFF)
    active_power_limitation_raw = integer(reg(8051), signed=False, nan=0xFFFF)
    active_power_limit_ratio = gauge(reg(8052), 0.1, signed=False, nan=0xFFFF, unit="%")


#: The components, by the name a document groups them under.
COMPONENTS: dict[str, type[Component]] = {
    "identity": IHomeManagerIdentity,
    "system": IHomeManagerSystem,
    "energy": IHomeManagerEnergy,
    "software": IHomeManagerSoftware,
    "meters": IHomeManagerMeters,
    "charger": IHomeManagerCharger,
    "settings": IHomeManagerSettings,
}

#: The two fields the document defines as text. Text anywhere else is
#: masked before publishing (`document.masked_text`).
TEXT_FIELDS: frozenset[str] = frozenset(
    {"protocol_number", "application_software_version"}
)

_V101 = "spec V1.0.1"
_V102 = "spec V1.0.2"

#: Which source each published field rests on, by its published name (a
#: coded field without `_raw`). Travels with every value, as the wallbox's
#: marks do.
CONFIDENCE: dict[str, str] = {
    **{
        name.removesuffix("_raw"): _V102
        for component in COMPONENTS.values()
        for name in component.declared_fields
    },
    "channel_2_voltage_a": _V101,
    "channel_2_voltage_b": _V101,
    "channel_2_voltage_c": _V101,
    "feed_in_limit": "template",
    "charger_power": "field",
    "charger_phase_a_power": "field",
    "charger_phase_b_power": "field",
    "charger_phase_c_power": "field",
}

#: What each coded field's number means, by its published name.
CODES: dict[str, dict[int, str]] = {
    "ems_mode": EMS_MODE,
    "charge_command": CHARGE_COMMAND,
    "feed_in_limitation": FEED_IN_LIMITATION,
    "start_stop": START_STOP,
    "charger_mode": CHARGER_MODE,
    "charger_enabled": ENABLED,
    "grid_draw_permitted": ENABLED,
    "active_power_limitation": ENABLED,
    "charger_status": CHARGER_STATUS,
    "output_type": OUTPUT_TYPE,
}
