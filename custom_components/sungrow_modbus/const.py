"""Constants for the Sungrow Modbus integration."""

DOMAIN = "sungrow_modbus"

DEFAULT_NAME = "Sungrow SHx"
DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 1

#: Unit ids the config flow tries when looking for an inverter, in order.
#:
#: 1 first, because it is what Sungrow's app and manual assume and what all
#: but one measured machine uses. Then 2, measured on 2026-09-09 at a house
#: with two inverters: the second answers on unit **2** at its own LAN port
#: and times out on 1, because a cluster slave's own device address is 2.
#: Discovery asked only unit 1 and reported that inverter absent. Then 3 to 5,
#: which the specification allows for further slaves and which nothing has
#: been measured on.
#:
#: The same list exists in `scripts/sungrow_scan/probe.py` as
#: `IDENTIFY_UNITS`, and the duplication is deliberate rather than sloppy:
#: that directory ships as a zip and may not import this package or the
#: library. Two short tuples that must agree is a smaller problem than a
#: survey that cannot run standalone.
IDENTIFY_UNITS: tuple[int, ...] = (1, 2, 3, 4, 5)

#: What a device address says about an inverter's role in a cluster.
#:
#: Only readable over a direct connection: a WiNet-S presents its inverter as
#: unit 1 whatever the inverter is configured as, measured on the same machine
#: read both ways. So an absent role means "not determinable here", never
#: "standalone".
ROLE_SLAVE = "slave"

CONF_UNIT_ID = "unit_id"

#: The subnet a discovery sweep covers. Asked for, never assumed: every
#: address probed is an ARP entry and a SYN on somebody's network.
CONF_NETWORK = "network"

#: Which entity ids the integration's entities claim. The entities themselves
#: are identical either way — device-scoped naming, translation keys, device
#: and state classes — so this is only about which id, and therefore whose
#: recorder history and which dashboard cards, they attach to.
CONF_ENTITY_IDS = "entity_ids"

ENTITY_IDS_MIGRATE = "migrate"
"""Take over the ids modbus_sungrow.yaml used, so history carries on."""

ENTITY_IDS_NEW = "new"
"""Create device-scoped ids, leaving the YAML package's history where it is."""

#: Poll interval per tier, in seconds, as `{tier name: seconds}`. Absent
#: means the defaults, which are the YAML package's own tiers — 5, 10, 60 and
#: 600 — so an existing user sees the freshness they are used to.
CONF_INTERVALS = "intervals"

#: A tier set to this is not polled at all, and its entities are not created.
#: Worth having: a Sungrow accepts very few Modbus connections, and the
#: cheapest way to stop competing for one is to stop asking for data nobody
#: looks at.
INTERVAL_NEVER = 0

#: The lowest interval offered. The specification warns that writable
#: registers must not be polled frequently through a WiNet-S, WiNet-S2 or
#: Logger1000, and 5 seconds is already the YAML's fastest tier -- fast enough
#: that going lower buys nothing and costs a connection the inverter has few
#: of.
INTERVAL_MINIMUM = 5

#: An option, not entry data: whether diagnostics include a raw register dump.
#: Off by default because producing it is a second full read of the register
#: map on top of the ordinary polling, which through a WiNet-S is slow enough
#: to disturb it.
CONF_REGISTER_DUMP = "register_dump"

#: Maximum battery charge power in watts, when the integration cannot work it
#: out. A Sungrow pack is identified from the capacity it reports and looked
#: up in `sungrow_modbus.battery`; a third-party pack that reports a BMS
#: current gets a suggestion from it; anything else has to be told.
CONF_BATTERY_MAX_POWER = "battery_max_power"

#: Who may perform the operations that are not entities, as
#: `{operation: audience}`. An option rather than entry data, and per entry
#: because one entry is one endpoint and one household may run more than one.
#:
#: Only operations the integration authorizes **itself** can appear here.
#: Entity control is not one of them: Home Assistant checks
#: `POLICY_CONTROL` centrally, before the integration is reached, and gates it
#: by user group -- so a normal user can already change every setting this
#: integration exposes, and a read-only user none of them. Start and stop are
#: different only because they are actions rather than entities, and an action
#: is authorized by whoever registered it.
CONF_PERMISSIONS = "permissions"

#: Administrators only, which is what Home Assistant's own
#: `async_register_admin_service` enforces.
AUDIENCE_ADMINS = "admins"

#: Anyone who may control this device's entities -- so a normal household
#: login, but **not** a read-only one. Checked with
#: `access_all_entities(POLICY_CONTROL)`, the same permission that decides
#: whether they could change the state-of-charge limits.
AUDIENCE_USERS = "users"

#: Stopping the inverter. Admins only unless the owner decides otherwise:
#: there is no way back from a stopped inverter except another call, and the
#: house is on the grid until somebody makes it.
PERMISSION_START_STOP = "start_stop"

#: The safe end of every choice. Changing one is a deliberate act by an
#: administrator, and an absent key reads as the default rather than as
#: permission.
DEFAULT_PERMISSIONS: dict[str, str] = {
    PERMISSION_START_STOP: AUDIENCE_ADMINS,
}

#: Entities reporting generation the Sungrow cannot see, as a list of ids.
#:
#: An option rather than entry data: it is a statement about the house, not
#: about the endpoint, and an owner who installs a second inverter later must
#: be able to say so without deleting the entry.
CONF_EXTERNAL_SOURCES = "external_sources"

#: Where that generation sits relative to the Sungrow's grid meter.
#:
#: Asked because the arithmetic differs and nothing can read the answer. See
#: `external.py`: behind the same meter the foreign output offsets grid
#: import and the load figure needs correcting; separately metered it never
#: touches that meter and correcting would introduce the error.
CONF_EXTERNAL_PLACEMENT = "external_placement"

PLACEMENT_BEHIND_METER = "behind_meter"
"""On the house side of the Sungrow's grid meter -- the common case."""

PLACEMENT_SEPARATE = "separately_metered"
"""Its own supply point, so none of it passes the Sungrow's meter."""

#: The default, and the reason is that it is both the common wiring and the
#: only one where anything is wrong today. Somebody who has gone to the
#: trouble of naming their other inverter's power sensor is telling us their
#: load figure looks wrong, which is the behind-the-meter symptom.
DEFAULT_EXTERNAL_PLACEMENT = PLACEMENT_BEHIND_METER
