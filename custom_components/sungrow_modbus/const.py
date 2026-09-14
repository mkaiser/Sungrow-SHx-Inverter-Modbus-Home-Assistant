"""Constants for the Sungrow Modbus integration."""

from datetime import timedelta

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

#: The testimony a survey needs and no register can answer.
#:
#: All optional, and all default to empty. **Empty means the question was not
#: put**, which the document format has always kept distinct from an answer of
#: "unknown" -- so leaving these alone produces an honest document rather than
#: an incomplete one.
CONF_REPORTER = "reporter"
CONF_SURVEY_COMMENT = "survey_comment"
CONF_SURVEY_BATTERY = "survey_battery"
CONF_SURVEY_TRANSPORT = "survey_transport"
CONF_SURVEY_PROXY = "survey_proxy"

#: What the owner says about anything *else* polling this inverter.
#:
#: The integration knows about itself and says so without being asked. What it
#: cannot know is another Home Assistant, the YAML package, evcc or a logger
#: on the same machine -- and that is exactly what decides whether a dropped
#: block is a register fault or two clients competing for one of the very few
#: sessions a Sungrow grants.
CONF_SURVEY_POLLERS = "survey_pollers"

#: Whether a **non-Sungrow** inverter shares the installation, and what it is.
#:
#: Two fields because the second is only asked after a yes: a text box that
#: sits there empty for everybody with one inverter is a worse dialog than a
#: question that is not put.
#:
#: This one is not politeness. A Sungrow does not measure house load, it
#: computes it -- its own output plus what the grid meter reports coming in --
#: so a second inverter feeding the same meter makes `load_power` low by
#: exactly that inverter's output. Continuously, while every register answers
#: normally and every block reads clean. From a maintainer's end that is
#: indistinguishable from a decoding fault, and no register can settle it,
#: because the inverter cannot see the thing that is confusing it.
#:
#: `external.py` already corrects for this from entities another integration
#: owns, which makes the answer useful twice: it explains a document, and it
#: says who should be told that the correction exists.
CONF_SURVEY_OTHER_INVERTER = "survey_other_inverter"
CONF_SURVEY_OTHER_INVERTER_DETAIL = "survey_other_inverter_detail"

#: Whether the last two octets of the address may be published.
#:
#: **On by default, and still asked.** The third octet is what separates one
#: contributor's network from another's and never leaves the machine at all;
#: what this covers is the last two, which is what lets somebody sending four
#: similar-looking documents tell which box each came from. The box is on the
#: screen and can be cleared before submitting, which is what makes it
#: permission rather than an assumption -- a document from somebody who
#: cleared it reads `xxx.xxx` and is complete rather than damaged.
CONF_PUBLISH_ADDRESS = "publish_address"

#: Whether a survey also sweeps the twelve raw address bands.
#:
#: On by default, and the only answer in this section that is not testimony:
#: it changes what the survey *does* rather than describing what the owner
#: knows. It lives here anyway because it belongs to the same decision --
#: somebody who has decided to contribute a reading is the only person this
#: is for.
#:
#: Not free, which is why it stays a question. The dump reads
#: 1510 addresses that nothing maps, and on a Sungrow an address with no
#: register behind it goes quiet rather than refusing -- so every empty one
#: costs a whole timeout. A measured SH10RT takes about five minutes.
#:
#: Deliberately **not** read by the diagnostics download, which builds the
#: same document: that download is a button somebody waits on, and five
#: minutes of reading behind it would look like a hang. `CONF_REGISTER_DUMP`
#: is the separate, much cheaper switch for that file -- it re-reads the
#: addresses this library already maps, and discovers nothing new by design.
CONF_SURVEY_DUMP = "survey_register_dump"

#: What an entry is for, chosen at setup and changeable afterwards.
#:
#: A contributor who wants to send a reading should not have to answer the
#: migration question at all: it is the only irreversible decision in this
#: flow, it decides which entity ids years of recorder history attach to, and
#: it has nothing whatever to do with producing a document. So there are two
#: kinds of entry.
CONF_MODE = "mode"

MODE_DEVICES = "devices"
"""The ordinary integration: entities, migration, the whole thing."""

MODE_DIAGNOSTICS = "diagnostics"
"""Connect, identify, and create no entities at all.

Still opens a Modbus connection -- so it still spends one of the very few
sessions a Sungrow grants, which is cheaper than a full entry and not free.
Promoted to a full entry later from the options flow, which is when the
entity-ids question gets asked.
"""

#: Whether the UI lets anybody *choose* devices mode. Off for the first alpha.
#:
#: This gates the door, not the room. Every line of devices mode stays built
#: and stays tested; what is switched off is the two places a person can
#: create such an entry -- the question the config flow opens with, and the
#: promotion toggle on a diagnostics entry's options page.
#:
#: Off because that path contains the one **irreversible** decision this
#: integration makes. Choosing to take over `modbus_sungrow.yaml`'s entity ids
#: decides which ids years of recorder history and every dashboard card attach
#: to, and getting it wrong breaks both silently. That is not a thing to put
#: in front of a stranger running an alpha, and an alpha's job here is to
#: gather readings anyway.
#:
#: Neither place hides anything. Both render the choice greyed out and say
#: when it is coming, because somebody evaluating this integration should be
#: able to see that the ordinary setup exists.
#:
#: **Flipping this to True is the whole re-enablement.** The menu and the
#: toggle come back exactly as they were; `tests/test_alpha_gate.py` asserts
#: both halves of that, and nothing else in the codebase branches on it.
#:
#: It does not touch an entry that already exists. An installation carrying a
#: devices entry -- from a previous build, or a backup -- loads, polls and
#: configures as it always did.
DEVICES_MODE_OFFERED = False

#: Where a contributed reading goes. The compatibility report template asks
#: for exactly what a survey produces, so the form arrives pre-shaped.
SURVEY_ISSUE_URL = (
    "https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant"
    "/issues/new?template=compatibility_report.yml"
)

#: And the route for somebody without a GitHub account, which is most people.
DISCORD_URL = "https://discord.gg/ZvYBejFkm2"

#: How long a signed survey download link stays valid. Long enough to
#: notice the notification and press it, short enough that a copied URL in
#: a chat window is not a standing grant. A fresh link comes with every
#: survey.
#:
#: Here rather than in `download.py` because two modules need it and only
#: one of them can afford to import the HTTP stack: `survey.py` names the
#: time in its notification and schedules the rewrite for when it passes,
#: and a link whose text and timer disagreed would be worse than either.
LINK_VALID = timedelta(hours=1)

#: The sections of the options page, which are also the keys its submitted
#: data arrives under -- `data_entry_flow.section` nests each group rather
#: than flattening it.
#:
#: Named for what a person is looking for rather than for the code behind
#: them: somebody opens this page to change how often it polls, to correct a
#: load reading, or to help the project, and those are the words.
SECTION_POLLING = "polling"
SECTION_PERMISSIONS = "permissions"
SECTION_EXTERNAL = "external"
SECTION_ADVANCED = "advanced"
SECTION_SURVEY = "survey"

#: The one checkbox outside every section: a diagnostics-only entry offering
#: to become an ordinary one. Not a section, because ticking it leads to a
#: question rather than saving a value.
CONF_ADD_DEVICES = "add_devices"

#: The ports a network search tries, so nobody has to know them.
#:
#: 502 is Modbus TCP: an inverter's own LAN port and a WiNet-S dongle both
#: answer there. 503 is where a Logger1000 puts it, and where an iHomeManager
#: lands when something already holds 502 -- Sungrow's setting is "Modbus TCP
#: on the iHM" rather than a port, which is why four sweeps of 503 finding
#: nothing was weaker evidence than it looked.
#:
#: 516 is deliberately absent. A WiNet-S does serve Modbus over TLS there --
#: measured at two houses, with a certificate that appears to ship with the
#: firmware -- but this integration has no TLS client, so finding it would
#: mean offering the user an endpoint nothing here can read.
#:
#: Asking for a port instead was the first version of this. It put a number
#: in front of somebody whose next question is "which number?", when the set
#: of answers worth trying is two long and known.
SCAN_PORTS: tuple[int, ...] = (502, 503)
