"""Constants for the Sungrow Modbus integration."""

from datetime import timedelta

# The unit ids the config flow tries when looking for an inverter, in order.
# The reasoning is in the library, beside the list.
from sungrow_modbus.discovery import IDENTIFY_UNITS as IDENTIFY_UNITS

DOMAIN = "sungrow_modbus"

DEFAULT_NAME = "Sungrow SHx"
DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 1

#: What a device address says about an inverter's role in a cluster.
#:
#: Only readable over a direct connection: a WiNet-S presents its inverter as
#: unit 1 whatever the inverter is configured as, measured on the same machine
#: read both ways. So an absent role means "not determinable here", never
#: "standalone".
ROLE_SLAVE = "slave"
ROLE_MASTER = "master"

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

#: An option: the wallbox's own LAN address, when it is reached there rather
#: than through a WiNet-S. Empty or absent: the endpoint is probed for one at
#: unit 3. Set: only that address is asked, so a dongle cannot find the same
#: wallbox a second time.
#:
#: Measured on an AC22E-01: the wallbox serves Modbus TCP inside TLS on its
#: own address, with no port 502, and answers only as unit 248. So the port
#: and the unit are constants, not options -- they are the only values
#: anybody has measured. The certificate is Sungrow-signed and identical
#: across devices, so there is nothing to verify it against.
CONF_WALLBOX_HOST = "wallbox_host"
WALLBOX_TLS_PORT = 516
WALLBOX_TLS_UNIT = 248

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

#: Running the control test, which writes to every control and puts it back.
#:
#: Admins only by default, for a reason the survey button does not share: this
#: one commands a charge, limits an export and moves the state-of-charge
#: limits. It restores all of it and re-reads to prove it did, but for the
#: minute it is running the house is doing what the test says rather than what
#: its owner set.
PERMISSION_CONTROL_TEST = "control_test"

#: The safe end of every choice. Changing one is a deliberate act by an
#: administrator, and an absent key reads as the default rather than as
#: permission.
DEFAULT_PERMISSIONS: dict[str, str] = {
    PERMISSION_START_STOP: AUDIENCE_ADMINS,
    PERMISSION_CONTROL_TEST: AUDIENCE_ADMINS,
}

#: Let the control test stop and start the inverter, and time how long it takes.
#:
#: Off by default and asked for in its own options step, with the consequences
#: spelled out there rather than in a label. Everything else the control test
#: does is a setting that goes back; this one takes the house off its own
#: generation for as long as the inverter takes to boot -- 3 to 4 minutes on
#: the models measured so far -- which is why it is not on by default.
CONF_CONTROL_TEST_RESTART = "control_test_restart"

#: Let the control test switch feed-in limitation on for the duration.
#:
#: Off by default. It is the one setting whose failed restore leaves the house
#: generating less than it could, so a run will not turn it on unless somebody
#: has said it may; where it is already on, the test uses it and this changes
#: nothing.
CONF_CONTROL_TEST_EXPORT = "control_test_export_limit"

#: Let the control test cut PV generation for about a minute (register 31211).
#:
#: Off by default: it is the one check that takes generation away on purpose.
#: It is also the only evidence that writing 31211 does what it should, which
#: is what the `Cut PV generation` switch waits for on each firmware.
CONF_CONTROL_TEST_PV_CUT = "control_test_pv_cut"

#: Which slot of a multi-inverter YAML install this entry's device was.
#:
#: `""` for a single-inverter package, `"_inv_2"` for the second inverter of a
#: multi-inverter one. Entry **data** rather than an option: it is a fact about
#: which history belongs to this device, settled once when the entry was made
#: and never a preference to revise. Changing it later would point an entry at
#: another inverter's years of readings.
#:
#: Written at setup because that is the only moment it can be: working it out
#: means reading the YAML package's own serial sensors, and the migration tells
#: people to remove the package afterwards. A diagnostics entry stores none,
#: because its setup never asks the id question; promotion and the options
#: page's id switch then ask the YAML package, and fall back to `""`.
CONF_LEGACY_SLOT = "legacy_slot"

#: How this inverter's firmware writes register 13074: 10 if it multiplies a
#: written word by ten, 1 if it stores it as handed. Measured, not assumed --
#: three houses multiply and fwitten's pair does not, and no register tells
#: them apart -- by `sungrow_modbus.inverter.export_scale` on the first write to the
#: export limit, and kept here so the probe runs once per inverter.
#:
#: Entry **data**, because it is a fact about the firmware on the far end of
#: this endpoint and not a preference. Absent until the probe has answered;
#: a probe that cannot answer writes at ten, the common case, and stores
#: nothing, so the next write asks again.
CONF_EXPORT_WRITE_SCALE = "export_write_scale"

#: The firmware `CONF_EXPORT_WRITE_SCALE` was measured on, as the device's
#: `firmware` string. A different one discards the factor and measures again,
#: because a firmware update is exactly what changed this register's behaviour
#: for the YAML package's users (#763: "Firmware update changed the behaviour
#: of Export Power Limit"). Kept beside the factor, in `data`, for its reasons.
CONF_EXPORT_WRITE_SCALE_FIRMWARE = "export_write_scale_firmware"

#: The publishable record of the write that measured `CONF_EXPORT_WRITE_SCALE`:
#: `export_scale.document` plus the day it was asked. The factor alone is what
#: writing needs; a survey document carries this, as the terminal's
#: `--export-scale --merge-into` does, so a reading from Home Assistant says
#: how its firmware writes 13074 and shows the one write behind the answer.
#: Stored and discarded together with the factor.
CONF_EXPORT_WRITE_SCALE_PROBE = "export_write_scale_probe"

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

#: On unless the user turned it off. One value for the form and for every
#: reader of the option, so the form cannot show it ticked while a survey
#: reading an entry whose options were never saved runs without it.
DEFAULT_SURVEY_DUMP = True

#: What an entry is for, chosen at setup and changeable afterwards.
#:
#: A contributor who wants to send a reading should not have to answer the
#: migration question at all: it decides which entity ids years of recorder
#: history attach to, and it has nothing whatever to do with producing a
#: document. So there are two
#: kinds of entry.
CONF_MODE = "mode"

MODE_DEVICES = "devices"
"""The ordinary integration: entities, migration, the whole thing."""

MODE_DIAGNOSTICS = "diagnostics"
"""Connect, identify, poll, and create only the survey's entities.

Two buttons and three sensors, which give the entry a device page; no
readings, no controls, no migration.

Still opens a Modbus connection -- so it still spends one of the very few
sessions a Sungrow grants, which is cheaper than a full entry and not free.
Promoted to a full entry later from the options flow, which is when the
entity-ids question gets asked.
"""

#: Whether the UI offers only the survey, so nobody can *choose* devices
#: mode. On during the alpha.
#:
#: This gates the door, not the room. Every line of devices mode stays built
#: and stays tested; what is shut is the two places a person can
#: create such an entry -- the question the config flow opens with, and the
#: promotion toggle on a diagnostics entry's options page.
#:
#: On because that path contains the **weightiest** decision this
#: integration makes. Choosing to take over `modbus_sungrow.yaml`'s entity ids
#: decides which ids years of recorder history and every dashboard card attach
#: to, and getting it wrong breaks both silently. That is not a thing to put
#: in front of a stranger running an alpha, and an alpha's job here is to
#: gather readings anyway.
#:
#: The opening menu offers only the survey and says the ordinary setup comes
#: later; the promotion toggle is greyed. `setup_devices` and `promote`
#: refuse too, so a hand-written request cannot get round the screen.
#:
#: **Flipping this to False is the whole re-enablement.**
#: `tests/test_alpha_gate.py` asserts both halves of that, and nothing outside
#: the config flow branches on it.
#:
#: It does not touch an entry that already exists. A devices entry -- from a
#: backup, or made while the gate was open -- loads, polls and configures
#: normally.
ONLY_SURVEY_MODE = True

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

#: The two consents part B needs, on their own so their description can say
#: what they cost. Collapsed by default, like every section whose settings most
#: people never touch.
SECTION_CONTROL_TEST = "control_test"

#: The one checkbox outside every section: a diagnostics-only entry offering
#: to become an ordinary one. Not a section, because ticking it leads to a
#: question rather than saving a value.
CONF_ADD_DEVICES = "add_devices"

#: The ports a network search tries, so nobody has to know them.
#:
#: 502 is Modbus TCP: an inverter's own LAN port and a WiNet-S dongle both
#: answer there. 503 is where a Logger1000 puts it, and where an iHomeManager
#: lands when something already holds 502 -- Sungrow's setting is "Modbus TCP
#: on the iHM" rather than a port.
#:
#: 516 is deliberately absent. A WiNet-S serves the same Modbus over TLS
#: there, which offers nothing 502 does not; a wallbox serves it on its own
#: address, and that is `CONF_WALLBOX_HOST`, entered on the options page,
#: rather than an inverter endpoint a search should offer.
#:
#: Not a question in the form: somebody whose next question would be "which
#: number?" is better served by trying the two that are known.
SCAN_PORTS: tuple[int, ...] = (502, 503)
