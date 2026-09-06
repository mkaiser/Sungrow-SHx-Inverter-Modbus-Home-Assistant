# Plan: replacing the YAML package with a Home Assistant integration

> Plan of record for the `proper-ha-integration` branch, kept in the repo so it
> is available in the devcontainer. Milestone 1 is done and verified; milestone
> 2 has its read parity, its capability gating, its naming convention, its
> migration and its diagnostics, and is missing only the three registers beyond
> parity and the InfluxDB helper. Milestone 3, the writes, has not started.
> Findings that could be asserted are asserted in `tests/`, and this file
> records decisions rather than repeating them.

## Goals

Each one is a promise to somebody already running the YAML package, and each
shapes some part of the design.

| Goal | Concretely |
| --- | --- |
| **Backwards compatibility** | An existing user keeps their `entity_id`s, so history, dashboards, automations and InfluxDB carry on untouched. The default for anyone with a YAML installation. |
| **Migration forward** | Modern device-scoped ids carry recorder history *and* long-term statistics, with no reset or spike on the Energy dashboard. |
| **Migration backwards** | Reversible in both directions. Where a target id is occupied, the occupant is archived rather than deleted. One control moved either way, not two one-way doors. |
| **Honest backups** | The guide says what a backup actually covers — SQLite yes; MariaDB, PostgreSQL and InfluxDB no. |
| **Dashboards** | The Energy dashboard configured from entities the integration already knows; a generated Lovelace dashboard on request; entity metadata good enough that the auto-generated view is right for free. |
| **Third-party inverters** | A foreign inverter behind the same meter corrupts Sungrow's load figure. Corrected from entities Home Assistant already has. |
| **A setup guide worth following** | The config flow's own text is what most people read. The written guide covers the one path where a mistake costs data. |
| **Auto detection** | The user supplies a host, not a topology. Devices are identified by what answers, never by unit id. Unknown devices are reported, not dropped. |
| **Every device** | Inverter, wallbox, SBR and SBH batteries, iHomeManager — sharing one serialized connection instead of an external Modbus proxy. |
| **All models, one map** | One register map, with model and wiring differences expressed as capabilities rather than forks or comments. |

Not goals: the YAML package is not modified or deprecated until the
integration reaches parity, and nothing outside Home Assistant is rewritten
automatically — InfluxDB and Grafana get advice and a script, never
automation.

## Why an integration

Home Assistant 2026.9 shipped a modernized Modbus architecture. A device
integration collects its own connection details and asks the `modbus`
integration for a *unit* — `async_get_unit(hass, entry, ModbusTcpParams(...),
unit_id)` — so everything pointed at the same host and port **shares one
serialized connection**. That is the single biggest advantage over every
comparable project: it is what removes the external Modbus proxy that wallbox
and iHomeManager users are told to run today.

Register knowledge lives in a standalone, HA-free library on
[`modbus-connection`](https://pypi.org/project/modbus-connection/), so it tests
without Home Assistant and without hardware. Core's `sofar` integration is the
working reference for the whole shape.

## Decisions

Before milestone 1: library and integration side by side in this repo;
milestone 1 is a devcontainer, a skeleton and one real sensor end to end; the
devcontainer ships a simulator and the flow also accepts a real inverter.

Since (2026-09-05):

- **Entity ids are a choice at setup.** Existing users keep legacy ids; new
  users get modern device-scoped ones.
- **Modern ids take the device prefix from the device type register.** A
  second device of the same model is disambiguated by its Modbus unit id,
  never by Home Assistant's registration order.
- **Milestone 2 is read-only parity.** No register writes while the
  foundation is laid.
- **A config entry is one Modbus endpoint** and the devices discovered on it.
- **Scope is wider than the inverter**: wallbox, SBR and SBH batteries,
  iHomeManager, each its own milestone.
- **The production testbed is planned in now**, not after parity.
- **The domain is `sungrow_modbus`.** `SHx` was wrong for that scope, and
  plain `sungrow` is taken by
  [KRoperUK/sungrow-hass](https://github.com/KRoperUK/sungrow-hass) — two
  integrations cannot share a domain. `sungrow_modbus` also names the real
  distinction: local Modbus against a cloud API.
- **Python `Component` classes are the register description**; see
  [Registers](#registers-one-map-many-capabilities).
- **The YAML's automations are deleted, not ported**; see
  [Milestone 3](#milestone-3--controls).
- **Releases are tag-driven**, one version in `pyproject.toml` mirrored
  everywhere and checked in CI, in pytest and at release.
- **Delivery is HACS first**, core only if the migration machinery can
  eventually be dropped.
- **The brand mark is original**, not Sungrow's.
- **The library is published to PyPI as `sungrow-modbus`**, not vendored into
  the component. Decided 2026-09-05; the account exists. It was never really a
  choice — Home Assistant pip-installs a custom integration's `requirements`,
  so without it a HACS install fails at start-up — and vendoring would have
  meant a build step forever to avoid a one-time upload. Release goes through
  OIDC Trusted Publishing from `release.yml`, so no API token is stored.
- **The integration offers to create a dashboard and asks first.** Not
  generated automatically, not omitted: the user is asked. See
  [A generated Lovelace dashboard](#a-generated-lovelace-dashboard).
- **Localisation follows Home Assistant's own model**: modern ids take the
  interface language where Home Assistant says they should, and are not worked
  around. Legacy ids are unaffected and stay English. Reversed from an earlier
  decision to pin them; see [Localisation](#localisation).

Resolved, so they are not re-litigated: whether a migration is reversible (it
is, both ways), and whether one entity class can serve both id shapes (it can
— `has_entity_name` is read via `hasattr`, so it is per instance).

## Open decisions

**Needing a judgement call**

| Question | Why |
| --- | --- |
| Are the 127 entity names right? | In modern mode the name **is** the entity id. Free to change until the first release, impossible after. [The convention](#one-naming-convention-enforced) makes them consistent; it cannot make them *good*. |
| Should migration be offered per inverter? | The legacy ids are global and unprefixed, so only one device can hold them. Today the second inverter is silently not asked. Needs the `_inv_N` scheme, which needs [test system 4](#test-systems-and-when-to-use-them). |

**Settled**

- **`0.0.1` claims the PyPI name** (2026-09-06), keeping `0.1.0` free for the
  first release worth the number. Uploads are immutable, so the first version
  is permanent, and it currently describes a read-only library — a sacrificial
  version costs nothing and buys back the one number people read as "first
  real release".

**Needing hardware or data**

| Question | How it gets answered |
| --- | --- |
| Does the **WiNet-S** advertise over mDNS? | Half answered. A run on the maintainer's LAN enumerated the service types and found six devices, no Sungrow among them — but that inverter is wired **directly to its LAN port**, so no dongle was present to advertise. Needs a system that actually has one. |
| Do the seam row and the adoption path hold on a database with years of real rows? | [The testbed](#the-production-testbed). |

**Waiting on someone else:** the SBH register map (no public document), and
HACS default-store inclusion (submittable once a release exists; HACS says new
additions take months).

The manual steps behind these — the PyPI account, the mDNS check, capturing
the test systems, and reaching the remote ones — are collected in
[doc/maintainer_setup.md](maintainer_setup.md).

### Validated against a real registry

Read from the maintainer's production instance on 2026-09-05 over the
WebSocket API — 2,741 entities, of which 173 belong to the YAML package.

**Every one of the 151 entities that matched by `unique_id` had exactly the
`entity_id` the generator predicted. No mismatches.** Home Assistant's slugify
applied to the YAML's names reproduces what five years of real registry holds,
which is the assumption the whole legacy-id migration rests on, and it is no
longer an assumption.

Three things the diff turned up that the design has to accommodate:

**A unique_id prefix cannot identify the package's entities.** The YAML uses
`sg_` for 131 of them but a bare `uid_` for 17 — `uid_battery_min_soc`,
`uid_ems_mode`, `uid_start_inverter`. The maintainer's *own* template sensors
use `uid_` too: `uid_washing_machine_running`, `uid_dryer_running`. By prefix
those are indistinguishable, so a repair that offered to delete "leftovers"
matched by prefix would offer to delete somebody's washing machine. **Identify
by exact membership of the generated map**, which is what generating it was
for.

**A real registry holds more than the current YAML defines.** Nine entries —
`sg_battery_alarm`, the `sg_bms_*` group, `sg_forced_startup_*` — come from
older versions of the package or from sections since commented out. Seven more
are scenes carrying `uid_sg_*` ids that the current YAML no longer sets, so
that installation is running a version this repository has moved past. The
migration meets whatever history left behind, not a clean room.

**And two entities the map has that the instance does not** —
`sensor.export_power_limit_min` and `_max` — because that installation predates
them. Absence is normal in both directions.

## The migration problem

The integration replaces `modbus_sungrow.yaml`, so existing users must keep
their history and dashboards. Both are keyed by `entity_id`: the YAML package
yields `sensor.total_dc_power`, an integration with `has_entity_name = True`
yields `sensor.sh10rt_total_dc_power`.

### What the recorder actually does

Asserted in [tests/test_recorder_migration.py](../tests/test_recorder_migration.py)
against 2026.9.0, so a core release that changes any of it fails the suite.

- **A registry rename carries everything and copies nothing.** The recorder
  renames the `states_meta` *and* `statistics_meta` rows, so history and
  long-term statistics follow and a `total_increasing` sum keeps climbing.
- **A rename onto an id the recorder already knows is refused**, with only a
  log line. That is exactly the YAML case, so the migration cannot be "create
  modern entities, then rename them onto the legacy ids".
- **The mechanism that works is claiming the legacy id at creation.** The
  entity writes to the row already there. Preconditions: the legacy id must be
  free in the registry *and* in the state machine, or the registry silently
  appends `_2`. Removing the old entity records one empty state, so a migrated
  series carries a one-row seam.
- **Both directions are reversible.** A rename moves rather than copies, so the
  round trip returns the history. Where the legacy id is still occupied,
  archive the occupant under another name first — instant on any database
  size, and nothing is deleted.
- **Holding the id is not sufficient.** Statistics metadata pins the unit. A
  unit in the same class is converted; a unit from a different class is
  dropped and long-term statistics then **freeze flat**, repeating the last
  value forever while raw history keeps filling. Nothing looks broken. Every
  ported entity must keep the unit class *and* `state_class` of the YAML entry
  it replaces.

### What a rename cannot reach

The findings above are about Home Assistant's own database only. The InfluxDB
integration tags every point with `entity_id` set to the **object id**, writes
forward only, and never rewrites history — so a changed id starts a new series
and every Grafana panel keeps rendering data that ends. The same applies to
Prometheus, MQTT statestream, Node-RED and the user's own automations and
templates. **Core updates none of them.**

So **only the legacy-id option preserves external stores**, and the modern-id
option's warning must say that "history and statistics are migrated" is true
of the recorder alone. For InfluxDB users the cheapest fix is a Grafana regex
matching both names; rewriting the tag is manual and outside Home Assistant.
[scripts/influx_migration.py](#milestone-2--inverter-read-parity) should emit
those artefacts — offline, commands for review, the delete step commented out.

### Backups, and why history is not staged in a temporary copy

There is **no raw-state import API**, so history cannot be exported and read
back. A download is therefore not a safety net: Home Assistant already exports
CSV from the History panel and the Energy dashboard, but nothing can put it
back. (Statistics are the exception — `async_import_statistics` exists.)

Nor is a copy necessary: a rename is already non-destructive, so archiving
keeps the old data queryable and deletes nothing, at no cost and at any
database size.

For a real "undo everything", the mechanism is Home Assistant's **backup**
integration — but the guide must say what that covers:

- **Recorder on SQLite in `/config`** — included by default
  (`include_database` defaults true). Genuinely covered.
- **MariaDB or PostgreSQL** — outside `/config`, so **not** in the backup.
  Those users need `mysqldump` or `pg_dump`.
- **InfluxDB, Prometheus** — never included by anything Home Assistant does.

### How it is presented

**Built (2026-09-06).** The setup question, the adoption itself and the traps
around it are implemented in
[migration.py](../custom_components/sungrow_modbus/migration.py) and asserted
end to end against a real recorder in
[tests/test_migration.py](../tests/test_migration.py) — years of YAML history,
the integration taking over, one unbroken series and the statistics still
attached. The user-facing guide is
[doc/integration_migration.md](integration_migration.md).

1. **Detect; do not ask cold.** ✅ The registry is checked for the ids the
   YAML package would have created. No trace means a new installation: new
   ids, no question asked, no mention of a package the user has never heard
   of. Traces found means one flow step, pre-selected to *migrate*, naming
   how many entities were found and one of them.
2. **Two answers, both real.** ✅ *Migrate my existing entities* claims the
   YAML ids; *Create new entities* takes device-scoped ones and leaves the old
   history where it is. The plan previously called these "legacy" and "modern"
   ids, which framed one of them as the compromise. It is not: **only the id
   is inherited.** A migrated entity has the same translated name, device
   class, state class and diagnostic category as a fresh one, so there is
   never a second class of installation to maintain — asserted in
   `test_a_migrated_entity_is_not_a_degraded_one`.
3. **The orphaned registry rows are released, not repaired around.** ✅
   Removing the YAML package does *not* free its registry entries: a YAML
   platform entity belongs to no config entry, so nothing cleans its row up
   and it goes on reserving the id. This was found by writing the test rather
   than by reasoning about it — the first implementation produced
   `sensor.total_pv_generation_2` for every entity. The integration now
   removes each orphan as it takes its id over.

   An earlier draft here proposed a repair issue asking permission first, on
   the grounds that "deleting another platform's entries unasked would be
   unrecoverable". Two things changed that: it is not unasked — the user chose
   *migrate* on the previous screen, which is what that choice **means** — and
   it is not unrecoverable, because the registry row is not where the history
   lives. Removing it touches no recorded data at all.
4. **A live YAML package is detected and reported before the question is
   answered.** ✅ An id is handed out only if free in the registry *and* in the
   state machine. The step checks the state machine when it renders and states
   what it found — "still running, 125 of its entities are holding their IDs"
   or "not running, both answers will work" — pre-selects the answer that can
   work, and refuses migrate if picked anyway.

   The requirement was in the dialog text from the first version and still
   caught the maintainer out on a real instance. The lesson is worth keeping:
   *a sentence about what the user ought to have done reads completely
   differently from a line saying what is true right now on this machine.*
   Where the integration can check, it should check.
5. **Every dead end has a way out.** ✅ Config flow forms carry errors, not
   buttons, so a step that fails leaves the user looking at the same fields
   with nowhere to go but the close button — which is what happened the first
   time the network search was used on a real instance. Failures that are not
   simple field corrections are menus instead: the search's "nothing found"
   offers another range, entering the address, or back to the start, and the
   picker carries a "none of these" option.
6. **Switching later is one control, not a wizard.** ⬜ Still open. An options
   flow with *Entity ID style*, working in both directions; where the target
   is occupied the archive step runs first. There is deliberately **no**
   separate "migrate back" button — back is the same control the other way.
   The dialog states how many entities will be renamed, two before-and-after
   examples, that InfluxDB and hand-built cards do not follow, and to take a
   backup. Until it lands, changing one's mind means removing the config entry
   and adding it again, which loses nothing.
7. **The archive is cleaned up only on request**, via `recorder.purge_entities`
   offered by a dismissible repair. Never automatic. ⬜ Follows 6.

## Architecture

### A config entry is one Modbus endpoint

A host and port, plus the devices found on it. That covers a single inverter,
a master with slaves, an inverter and a wallbox on one dongle, an SBR on its
own host, and the iHomeManager on port 503 — uniformly. It is also exactly the
set of units sharing one serialized connection.

The integration loads as many times as needed (`single_config_entry` defaults
false), provided two things hold: **`unique_id` is the master's serial**, and
**the flow rejects a unit whose serial another entry already claims** —
`_abort_if_unique_id_configured` only checks the entry's own id.

A system-level device gives the aggregate sensors in
[additional_sensors/](../legacy/additional_sensors/) somewhere to live. In the
library, `SungrowInverter` gains siblings — `SungrowWallbox`,
`SungrowBattery`, `SungrowHomeManager` — over the same `Component` machinery.

### Device discovery

**Network search, built (2026-09-06).** The flow opens on a menu — *Search my
network* or *Enter the address myself* — because the question it used to open
with, what is the inverter's IP address, is one many users cannot answer
without going to look at their router.

Two passes, and the second is the one that matters. **An open port 502 is not
a Modbus device**: sweeping the maintainer's own LAN turned up a RAKwireless
gateway that accepts the connection and echoes bytes back. So the sweep in
[discovery.py](../src/sungrow_modbus/discovery.py) produces *candidates*, and
nothing is called an inverter until it has answered a read of its device type
register — which the flow does through Home Assistant's shared connection,
identifying model and serial in the same call.

The sweep is capped at 1024 addresses and the size is checked
**arithmetically before any address is generated**: counting by building the
list first is a line shorter and means a user who types `/8` waits twenty
seconds and several gigabytes for an error that was knowable immediately. The
range is prefilled from Home Assistant's own adapters, narrowed to a /24 when
the adapter reports something wider — a container on a Docker bridge reports a
/16.

Reverse DNS labels each result. Home routers commonly serve PTR records — a
Fritz!Box answers `<name>.fritz.box` — so the list reads as names the user
recognises rather than addresses; where there is no record the address is
shown, which is no worse than not having tried.

Still open: **mDNS**, below, which would find a WiNet-S without any sweeping at
all.


Identify by **what answers**, never by unit id: id 3 is a slave inverter on one
system and a wallbox on another.

| Kind | Identify by | Typical unit id |
| --- | --- | --- |
| Inverter | device type code, input 4999 | 1, then 2..n |
| Wallbox | serial at input 21200 | 3 via WiNet-S, 248 direct |
| SBR battery | the 10740-10788 block | 200 |
| iHomeManager | its own map, on **port 503** | 247 |
| Logger1000/3000/4000 | the **8000-range** map, e.g. device type at 8000 | 247, on port 502 |

Probe those candidates first; a wider scan is an explicit opt-in, because an
unused unit id costs a full timeout.

**An open port 502 is not a Modbus device.** The maintainer's LAN proved it
first time: `192.168.178.36` accepts TCP on 502 and echoes the request bytes
back, which decodes as plausible nonsense — it is a RAKwireless device,
unrelated. So validate the *response*, not the connection, and never present
an echo as a discovered inverter. Anything that answers but is not recognised
is **reported with what it returned**, not dropped.

**Finding the host without scanning:** a `dhcp` block in the manifest
(matching hostname or OUI) costs nothing, and zeroconf may work if the WiNet-S
advertises itself. Run on the maintainer's LAN it found six devices and no
Sungrow, which is a real negative for an inverter on its **own LAN port** —
that one serves nothing on port 80 either. It says nothing yet about a
**dongle**, which does run a web UI and is what the question is about, so one
of the remote systems is needed to close it. If a sweep is offered at all: measured, a /24
takes **1.0 s** and the ceiling is ~5,000 probes/s, so the script refuses
anything above about a /20.

### Naming

Modern mode: `has_entity_name = True` plus a device named `SH10RT` gives
`sensor.sh10rt_total_dc_power`. A second device of the same model would
collide, and Home Assistant's own answer — `_2` appended by registration order
— is unstable and lands at the wrong end of the id. Instead, a ladder used
only as far as needed:

1. **The model** — `SH10RT`, the single-inverter case.
2. **Model and unit id** — `sh10rt_2_total_dc_power`. Stable, short, already
   known, and what distinguishes the devices on the wire. Note the
   discriminator sits in the middle, where it groups and sorts.
3. **Model and a serial fragment**, for the same model at the same unit id on
   two endpoints.

The check runs against **every device the integration has registered** — entity
ids are globally unique, so two entries collide as readily as two devices in
one.

Two rules follow. **Discovery never renames something already set up**: the
newcomer takes the longer name, because renaming the incumbent would break
dashboards and InfluxDB even though the recorder would survive it. Where two
are discovered at once with no incumbent, the lowest unit id keeps the bare
name. And **the model only seeds the name; the name owns the ids** — users
should be invited to rename to "Roof" or "Garage" in the flow.

### Registers: one map, many capabilities

Keep one register map for every model. Most of it is identical across the
range, so forking per family would duplicate the majority to express a
minority. What varies is *capability* — which parts of the map a device
answers — from four sources:

| Source | Example | How it is known |
| --- | --- | --- |
| **Model** | MPPT count; features absent on RS and MG | Device type code (5000) |
| **Phase** | Three-phase registers on a single-phase unit | **Register 5002 states it**: 0 single, 1 3P4L, 2 3P3L |
| **Wiring** | Battery present; meter direct; iHomeManager instead of DTSU666 | Probed |
| **Transport** | Sungrow states the 6100-6195 block is "not supported" when forwarded by WiNet-S | **Probed**: whether that block answers says which way in we came, and a web UI on port 80 corroborates it |
| **Firmware** | Blocks appearing between versions | Neither — `UpdateReport` and the firmware log |

Two rules the specification states outright, so neither is a heuristic:
**`0xFFFF` means unavailable by definition** (`0xFFFFFFFF` for U32, `0x7FFF`
signed, `0x00` for UTF-8), and **writable registers must not be polled
frequently through a WiNet-S, WiNet-S2 or Logger1000**.

The knowledge already existed in this repo as *comments* in
`modbus_sungrow.yaml` — "only for SH\*T inverters with 3 MPPTs", "NOT
supported on SH3.0-10RS and MG5-6RL", "only valid when directly connected to
the smart energy meter". Those are now data, in
[src/sungrow_modbus/capabilities.py](../src/sungrow_modbus/capabilities.py).

Extracting them showed something about the *shape* of the knowledge that
changed the design. Every one of those comments records where a feature is
**absent**, on which model, learned from somebody's bug report — none of them
says where a feature is present. So the module models absence, from a family
table, and leaves presence to probing. Three rules of precedence follow, and
are tested: register 5002 outranks the family table on phases, a probe
outranks both, and an **unknown device type code asserts nothing** rather than
being assumed crippled, because a model nobody has written down is exactly the
one to probe.

Probe results are cached on the config entry so entities are stable across
restarts, but as a **cache with an explicit refresh** — a transient failure
must not hide entities forever, and a battery added next year must be
discoverable. **Entities exist only where the register does**, which is the
fix for the pain behind [doc/cleanup_entities.md](../legacy/doc/cleanup_entities.md). One
consequence to state in the migration guide: permanently-unavailable legacy
entities will not be recreated.

### Where register descriptions live

`modbus-connection`'s vocabulary is already a register-description format, and
it models what Modbus has and an HDL format (SystemRDL, IP-XACT) does not:
scale factors including scale-by-another-register (`scale_register=`), word order per field,
strings spanning registers, `nan=` sentinels matching the specification's own
"unavailable" convention, `enum`/`flags`/`bit`, `repeating_group` for the SBR
and firmware blocks, and `writable` with a validator. So **Python `Component`
classes stay the register description** — typed, mypy-checkable, no codegen.

The boundary that makes this work — the library knowing nothing about Home
Assistant — is asserted by
[tests/test_library_is_standalone.py](../tests/test_library_is_standalone.py)
rather than left to discipline. One convenient `from homeassistant...` import
would dissolve it silently, and the suite would keep passing because Home
Assistant is installed in the devcontainer anyway.

What does not fit there is everything *around* a register: `device_class`,
`state_class`, `translation_key`, the legacy entity id, the poll tier, the
capability gate, and which specification version introduced it. That belongs
in a **generated, committed, CI-checked data file** — never read at runtime —
diffed against the YAML (units and state classes), against V1.1.11 (existence
and width), and against a real entity registry (legacy ids). The repo already
generates and commits two artefacts this way.

## Register sources

| Device | Map from | Licence | Quality |
| --- | --- | --- | --- |
| Inverter | [modbus_sungrow.yaml](../legacy/modbus_sungrow.yaml) plus Sungrow's *Communication Protocol of Residential Hybrid Inverter* **V1.1.11 (2025-11-17)** | MIT, this repo | Field-proven, now checkable against the specification |
| SBR battery | [additional_sensors/](../legacy/additional_sensors/modbus_sungrow_SBR_battery.yaml) — 40 input registers, 10740-10788 | MIT, this repo | In use |
| SBH battery | Nothing yet | — | Needs the protocol document |
| iHomeManager | Official Sungrow PDFs, mirrored in [Jam3s97/sungrow_ihomemanager](https://github.com/Jam3s97/sungrow_ihomemanager/tree/main/Modbus%20Information) | Sungrow's documents; that repo is GPL-3.0, so implement from the spec, not their YAML | An actual specification |
| Wallbox | [evcc `charger/sungrow.go`](https://github.com/evcc-io/evcc/blob/master/charger/sungrow.go) | MIT | Reverse-engineered but corroborated by three sources; **partial** — 21231-21261 and 21267-21299 are gaps |
| Logger1000/3000/4000 | Sungrow's *Logger Communication Protocol* **AW0 1.0.2.9**, plus the field-proven map in [discussion #262](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/discussions/262) | Sungrow's document | An official specification exists |

The wallbox has no official register document; evcc is the best-licensed
source and covers AC011E-01 and AC22E-01. The maintainer also has the wallbox
project author's permission, and the values are public in photovoltaikforum.

**Audited against V1.1.11.** The YAML has kept up better than expected. Of the
seven register additions between V1.1.2 and V1.1.11, four are already covered
— the firmware block at 13250-13369, active power limitation 13089/13090, and
meter active power 5601. Three are not, and are the port's chance to go past
parity:

| Missing | Space and register | Added |
| --- | --- | --- |
| Feed-in limitation ratio | holding 13088 | V1.1.7 |
| Meter channel 2 data | input 13200-13207 | V1.1.9 |
| PV power limitation (writable) | holding 13018 | V1.1.10 |

Match on **space and register together**. An earlier pass compared addresses
alone and reported a collision between the YAML's `total_direct_energy
consumption` and the specification's PV power limitation, both at 13018 —
but one is an input register and the other a holding register, which are
separate address spaces. There was no conflict.

`DEVICE_TYPES` is now checked against Appendix 1 of that document and pinned
by [tests/test_device_types.py](../tests/test_device_types.py): all 35 models
present, names agreeing, **MG8RL (0x0D29) and MG10RL (0x0D2A) added**. Seven
entries remain that the specification dropped in V1.1.0 — the SH\*K series —
because the hardware outlived the paperwork, and the test records that as a
decision rather than an oversight.

## Roadmap

### Milestone 2 — inverter read parity

The 103 modbus entities plus the user-facing template sensors. No writes.

**Foundation done (2026-09-05/06).** The four things the rest of the milestone
rests on are in place and tested: the entity map, generated and validated
against a real registry; the model table, pinned to specification V1.1.11; the
register coverage audit, which found three registers worth adding beyond
parity; and the capability model, which turned the YAML's comments into gates.
What is left is the bulk work — porting register blocks into tiered
components, extending the simulator seed, and writing the entity
descriptions.

1. **Generate the legacy-id table; do not transcribe it.** ✅ Done.
   [scripts/generate_entity_map.py](../scripts/generate_entity_map.py) derives
   [doc/legacy_entity_map.json](legacy_entity_map.json) from the YAML package
   using Home Assistant's own `slugify`, and `--check` runs in CI and in
   pytest so it cannot go stale.

   **153 entities** — 102 modbus, 50 template, 1 filter — and the audit it
   carries is good news: **no two entities slugify to the same entity_id**,
   every one has a `unique_id` (so every one has a registry entry to migrate
   through), and no entity carries a state class without a unit. Those three
   were the ways the migration could have been quietly impossible.
2. **One coordinator per poll tier.** Measured from the YAML: realtime 5 s (2
   entities), fast 10 s (57), medium 60 s (3), slowest 600 s (37). The daily
   tier is the identity block, already read once at setup — so four
   coordinators.
3. **Derived values in the library, not HA templates.** MPPT power as V·I,
   signed battery power, running-state and alarm decoding. Their entity ids
   must be reproduced, but the arithmetic belongs in `sungrow_modbus`.
4. **The id choice, asked at setup.** ✅ Done, and by a better mechanism than
   this plan first proposed. It is not `has_entity_name` that varies: every
   entity keeps `has_entity_name = True` and its `translation_key`, and the id
   is claimed with `async_get_or_create(..., suggested_object_id=...)`, which
   the registry documents as **not** prefixed with the device name. That is
   public API — unlike `internal_integration_suggested_object_id`, which is
   private and must not be used — and it means a migrated entity is a normal
   modern entity that happens to hold an old id. See
   [How it is presented](#how-it-is-presented).
5. **Make the unit-class trap mechanical** — a test asserting every entity
   description's unit and `state_class` match the YAML entry it replaces.
6. **Extend the simulator seed to every ported address**, and assert each
   description reads non-None against it.
7. **Get the entity metadata right** — `device_class`, `state_class`,
   `suggested_display_precision`, `entity_category`. The auto-generated
   dashboard is downstream of exactly this, so it is the cheapest dashboard
   work available.
8. **The firmware block at 13250 is text, not numbers.** Read from the
   reference SH10RT it returns 21313, 20560, 18505, 21061, which spells
   "SAPPHIRE" — the family name the ARM and DSP version strings also carry. It
   needs `string()`, and would otherwise ship as four meaningless integers.
9. **Tolerate absent registers.** MPPT3/4 at `0xFFFF`, battery blocks without
   storage, and 5741-5746 silenced by an iHomeManager (issues
   [#647](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/647),
   [#651](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/651)).
10. **`scripts/influx_migration.py`**, emitting Grafana regexes and rewrite
    commands from the same mapping.

### Milestone 3 — controls

`number`, `select`, `switch` and `button` over the writable holding registers
behind the `&sg_reg_*` anchors.

**One rule, settled:** the integration never writes a register during setup or
reload — only on an explicit user action.

**The YAML's automations are deleted, not ported.** They are a workaround for
YAML Modbus having no write-then-read: a user sets a value and sees nothing
until the next poll. Core's `sofar` shows the fix in `switch.py`, `select.py`
and `button.py` — `async_request_refresh()` straight after the write. The
scenes that compute a value become a button or a service action; the readback
automations disappear; the danger-mode guard stays a dashboard affordance.

Note the specification's constraint: writable registers must not be polled
frequently through a dongle, so the settings tier needs its own slow
coordinator.

### Milestone 4 — battery modules

SBR is portable already: 40 input registers, per-module cell data, on **unit
200 and not reachable through WiNet-S at all** — so often a different endpoint
entirely. SBH needs the protocol document first.

### Milestone 5 — iHomeManager

Best documented of the lot. **Port 503, slave 247.** Grid metering, battery
and EMS control, EV charger status. An iHomeManager also changes what the
*inverter* answers, so this is not only a new device. Worth reading its
**Modbus Transfer** guide while here: a documented relay to devices behind it
would give an officially specified path to wallbox registers.

Four issues and a discussion asked for this, and [doc/faq.md](../legacy/doc/faq.md) still
answers "not at the moment" — update it when this ships.

### Milestone 6 — wallbox

29 entities over 21202-21319, on 10/60/600 s tiers, at slave 3 via WiNet-S or
248 direct — so **the unit id has no safe default**. An iHomeManager is *not*
required. The maintainer has access to an SH8RT with a battery and the newer
wallbox (confirm AC011E-01 versus AC22E-01), which turns this from
transcribing an unverified map into verifying one and probing the gaps.

This is where the shared connection pays off most visibly: the community
project tells users to run an external Modbus proxy because inverter and
wallbox contend for the dongle. Two devices on one endpoint share one
serialized connection instead.

### Milestone 7 — third-party generation behind the meter

A non-Sungrow inverter on the same supply is invisible to Sungrow, so reported
load reads **low by exactly the foreign production**, and **negative** when it
exceeds consumption. A persistently negative load is the signature of an
unmetered generator and worth surfacing, not clamping.

Home Assistant almost certainly already reads that inverter, so the correction
is arithmetic over entities the user has: name the external generation
entities and **where they sit** (behind the same meter, or separately metered
— the arithmetic differs, so ask), then derive corrected house load and total
site production. State and test the sign convention; errors here stay
plausible while being wrong.

Two boundaries: this code lives in the **integration, not the library**,
because it consumes other HA entities — a deliberate exception. And for kWh
rather than power, do not invent a sensor: the Energy dashboard already
accepts **multiple solar sources**.

### Milestone 8 — Sungrow Logger

The Logger1000/3000/4000 fronts a whole installation, and it is the case the
config-entry model turns out to have been built for. **An official protocol
document exists** — *Logger Communication Protocol AW0 1.0.2.9*, covering all
three models — which puts it ahead of the wallbox. The copy found online 404s,
so it needs obtaining from Sungrow support or another mirror; the map in
[discussion #262](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/discussions/262)
is field-proven meanwhile and was reverse-engineered with Sungrow R&D.

**It has its own register range, the 8000s**, so it is distinguishable from an
inverter and from the iHomeManager despite sharing slave id 247 with the
latter — the iHomeManager answers on port 503, the Logger on 502, and their
maps do not overlap. Identify by what answers, as everywhere else.

Known registers: device type 8000, total devices connected 8005, total faulty
devices 8006, total active power 8070, daily yield 8074, total yield 8080, max
adjustable active power 8086, and a writable on/off for the sub-inverter array
at 8002.

**Devices behind it are addressed by port *and* slave id.** Each forwarded
device needs its own TCP port — 502, 503, 504 upward — with an explicit
warning from users against putting several devices on one port. That falls out
of "an entry is one endpoint" rather than fighting it: a Logger with three
inverters is three entries, plus optionally one for the Logger itself. Worth
saying plainly in the docs, because it looks surprising.

It also makes discovery *better* than blind: **register 8005 reports how many
devices are connected**, so on finding a Logger the flow knows how many
forwarded ports to expect and can offer to add them instead of sweeping.

**Writing through a Logger is dangerous.** Users report that unless it is in
pass-through mode the Logger overrides commands and inverters can become
unresponsive. So milestone 3's rule needs an addition: where the endpoint is a
Logger, control entities stay unavailable until pass-through is confirmed.
Control *of* the Logger itself is not available at all.

**Scope boundary.** Behind a Logger people run SH10RT, SH15T and SH25T — our
map — but also **SG string inverters**, which have their own protocol document
(*Communication Protocol of PV Grid-Connected String Inverters*). Supporting
the Logger does not imply supporting the SG family.

## Cross-cutting

### The Energy dashboard

`energy.data.async_get_manager(hass)` takes the same preferences the frontend
writes, and sources are named by **statistic id**, which for a recorder-backed
sensor is its entity id — so the integration can fill in grid import/export,
solar production and battery in/out, which users otherwise pick by hand from
~120 similar names.

Four rules: **merge, never replace** (`async_update` swaps the whole
`energy_sources` list); **`manager.data is None` means never configured**, the
only state where writing unasked is defensible; **only after statistics
exist**, so not at first setup; and **validate first** with
`energy.validate.async_validate`.

### A generated Lovelace dashboard

Possible through `hass.data[LOVELACE_DATA].dashboards` plus
`LovelaceStorage.async_save` — semi-private, so keep it small and isolated.
**Decided: the integration asks.** Not created silently and not left out — the
user is offered one and says yes or no, which is the only reading under which
generating a dashboard is not presumptuous. Rules follow from that: create a
**separate** dashboard, never touch the user's Overview; write it **once, on
that explicit yes**, because users edit dashboards afterwards and a
regenerating integration would destroy their work. Do the free
thing first — good entity metadata makes the auto-generated view right for
everyone, including those who never ask.

The [dashboards/](../legacy/dashboards/) YAML references legacy ids literally, so it
should be **generated** from the same table as the legacy-id map, and come out
correct for whichever id shape the user chose.

### Localisation

Home Assistant's mechanism is `strings.json` as the English source and
`translations/<lang>.json` beside it; hassfest checks they agree. What is worth
translating: the config flow's steps, field labels, `data_description` help
text, errors and aborts; the options flow; repair issues; exception messages;
and entity names via `translation_key`.

**But translating entity names changes entity_ids, and German is one of the
languages where it does.** Home Assistant builds an entity_id from the
`object_id_language`, which is the user's own language when that language is in
`NATIVE_ENTITY_IDS` — and `de` is in that set. So a German-configured instance
shipping a German `de.json` would produce
`sensor.sh10rt_gesamte_gleichstromleistung` rather than
`sensor.sh10rt_total_dc_power`. That is Home Assistant working as designed, and
for this project's largely German user base it is not a detail.

Two consequences, one reassuring and one a decision:

**Legacy mode is immune, and by construction rather than by luck.**
`Entity._name_internal` returns `_attr_name` *before* it consults any
translation. Legacy mode sets that attribute to the literal name the YAML used,
so the object id stays English whatever the interface language is — which is
exactly what the migration needs, since `sensor.total_dc_power` has to be
claimed byte for byte.

**Modern mode follows Home Assistant and lets ids take the interface
language.** A German instance gets `sensor.sh10rt_gesamte_gleichstromleistung`,
which is what Home Assistant intends for a language in `NATIVE_ENTITY_IDS`.
The integration does not work around it.

An earlier draft of this plan decided the opposite — pinning ids to English by
overriding `Entity.suggested_object_id`, which does work and is demonstrated
in the history. It was reversed deliberately: being idiomatic is worth more
than the convenience of one set of ids, the divergence would have had to be
explained to every contributor and reviewer forever, and it would have been the
second place this integration quietly did its own thing.

Two things make that affordable. Ids are assigned **when an entity is first
registered**, so they are language-dependent at creation and stable afterwards
— changing the interface language later does not rename anything. And the
users who most need stable English ids are exactly the ones on **legacy mode**,
which is unaffected: `Entity._name_internal` returns `_attr_name` before it
consults any translation, so a legacy entity claims `sensor.total_dc_power`
byte for byte on a German instance just as on an English one. That is asserted
in [tests/test_entity_naming.py](../tests/test_entity_naming.py) alongside the
modern behaviour, so both are described rather than assumed.

Practically: the maintainer is German, so `de.json` is the natural second
language and the one with a real audience; anything further comes from
community pull requests. Translations must never gate a release — a missing
key falls back to English, which is a degraded interface rather than a broken
one.

### One naming convention, enforced

The names are not decoration. With `has_entity_name` set the object id is
slugified **from the name**, so "Sungrow inverter serial" gives
`sensor.sh10rt_sungrow_inverter_serial` where "Serial number" gives
`sensor.sh10rt_serial_number`. Names are therefore ids, and ids are free to
change now and impossible to change after release — the same argument that
settled the domain rename.

The YAML package shows what happens without a rule. In one file `Battery min
SoC` sits beside `Battery Min Soc`, fourteen names are title-cased among
sentence-cased ones, fifteen begin with the device's own name — which Home
Assistant then prefixes again, giving "SH10RT Sungrow inverter serial" — and
two abbreviate with a full stop. None of that was decided; it is five years of
contributions with nothing checking them.

So the convention is written down in [scripts/naming.py](../scripts/naming.py)
and applies to all 127 entities:

- a name never starts with the device or the manufacturer, because Home
  Assistant already prefixes the device name;
- sentence case, except for a fixed list of acronyms (`AC`, `APL`, `ARM`,
  `BDC`, `BMS`, `DC`, `DSP`, `EMS`, `MPPT`, `PV`, `SoC`, `SoH`) and single
  letters naming a phase;
- exactly **one spelling per concept**, which follows from the previous rule
  rather than needing a list: `SoC` has one canonical form, so `Soc` cannot
  appear;
- no abbreviation that costs the reader a guess — `cmd` is spelled `command`,
  and `max.` loses its full stop;
- a name ending in `raw` must carry `EntityCategory.DIAGNOSTIC`, because a raw
  enumeration code has a decoded counterpart and that is the one a dashboard
  wants. Twenty-seven entities are diagnostic: the eleven `_raw` codes, the
  power-flow bitmask, identity and firmware strings, and the two nameplate
  constants.

`scripts/generate_strings.py` applies it and writes `strings.json`;
[tests/test_naming_convention.py](../tests/test_naming_convention.py) asserts it
against the **committed** file rather than against the generator, so an entry in
the override table cannot opt itself out of the convention it exists to serve.
Eleven names are overridden by hand, each with its reason in the table — a
long list there would mean the rules are wrong, not the names.

**Legacy names are untouched, and that is the point.** Legacy mode has to
reproduce a user's existing entity_ids byte for byte, so `legacy_name` stays
whatever the YAML said, inconsistency included. The same test pins that too.

Two further mechanical checks come with it: every `translation_key` an entity
description names exists in `strings.json` and nothing in `strings.json` is
orphaned, and no two names slugify to one entity_id — which is how the registry
silently appends `_2` to whichever entity registered second. Still open: that
each `translations/*.json` carries the same keys as `strings.json`, which
matters once `de.json` exists.

The writable `number.*` entities are not ported yet, and they carry the worst of
the YAML's names (`Battery Max Soc`, `Battery Reserved SoC for Backup`). The
convention applies to them when milestone 3 lands.

### Diagnostics

**Built (2026-09-06).** Home Assistant's own diagnostics platform, so it is the
*Download diagnostics* button every integration has rather than something to
learn. [diagnostics.py](../custom_components/sungrow_modbus/diagnostics.py).

It is shaped by what bug reports on this project actually cost. Nearly every
one opens with the same round trip — which model, what is connected, which
registers answer, why is sensor X missing — and the integration already knows
all four. So the file states:

- **how each capability was decided, not only the result.** The model table,
  the probe and register 5002 are reported separately, plus
  `table_contradicted_by_device` — a capability the family table calls absent
  that the hardware answered for. That field is the bug report: it means
  [ABSENT_IN](../src/sungrow_modbus/capabilities.py) is wrong for that model,
  which is a thing only a user's hardware can tell us.
- **why an entity does not exist.** "MPPT3 is missing" is the most common
  report, and the answer is nearly always the 0xFFFF sentinel rather than a
  fault. Now it is written down instead of diagnosed.
- **`reported_unavailable` separately from a failed poll.** A register
  decoding to None is the device saying a measuring point is not there; a
  component missing its poll is a comms problem. Conflating them is most of
  what makes these reports slow.
- **which entity ids are in use**, so a migration that half-worked is visible
  at a glance.

Redaction: serial number and host, including the serial *as a register
reading* — key-based redaction of the identity block alone leaves it in
`readings`, which is what `test_the_serial_and_host_are_redacted` catches —
and the serial's address range is dropped from the raw dump, since a dump is
words and no key redaction reaches it.

The **raw register dump is opt-in**, in an options flow, because producing it
is a second full read of the map on top of normal polling and is slow through
a WiNet-S. That options flow is also where the entity-id switch belongs when
it is built.

Two things this replaces: `scripts/collect_fingerprint.py` stays, because it
runs without Home Assistant and before the integration is installed, which is
what a first-contact report needs. And the "one-click feedback upstream" idea
is now cheap — a diagnostics file is already the payload.

### Firmware, feedback, diagnostics

The integration already reads ARM and DSP versions; the specification adds a
firmware block at 13250-13369. A data file in the library can log observed
versions per device type — but it is a **log of what users reported**, never a
statement of what exists, so it may say "newer has been seen" and never "yours
is out of date". Surface the version as a diagnostic attribute always; raise a
repair **only for versions with known defects**, because Sungrow updates
generally need an installer account and nagging trains people to dismiss
repairs.

For collecting model and firmware upstream, prefer a **prefilled GitHub
issue** (`?template=...&field=value`) to a telemetry endpoint: the user sees
what is sent and presses submit, there is no infrastructure and no GDPR basis
to establish, and it lands where the work happens. Watch for `414 URI Too
Long`; keep the prefill compact.

Implement `async_get_config_entry_diagnostics` regardless — it redacts serial
and host, and it makes the unrecognised-device and firmware-sighting cases the
same flow.

## Documentation

Two products in one repo, so **every page states which track it applies to**.
The first-line documentation is `strings.json`: step descriptions and a
`data_description` per field are what people actually read.

| Page | Change |
| --- | --- |
| [README.md](../README.md) | Done — opens by splitting the two tracks |
| [doc/installation.md](../legacy/doc/installation.md) | Add the integration: HACS, add integration, what discovery finds |
| `doc/integration_migration.md` | New; the YAML-to-integration path |
| [doc/cleanup_entities.md](../legacy/doc/cleanup_entities.md) | Keep, linked from the repair as the manual fallback |
| [doc/dashboard.md](../legacy/doc/dashboard.md) | Generated dashboard and Energy dashboard |
| [doc/faq.md](../legacy/doc/faq.md) | The iHomeManager answer, once milestone 5 ships |

The migration page is the only one where a mistake costs data, so its order is
fixed: back up **and check the backup covers your recorder**; remove the YAML
package and restart; add the integration; clear the leftovers when the repair
offers; verify a known sensor is continuous; then dashboards and Energy.

## Delivery

### Versioning

One version in `pyproject.toml`, mirrored into the manifest by
[scripts/sync_version.py](../scripts/sync_version.py) — both the `version` key
and the pinned requirement. Enforced in CI, in pytest, and against the git tag
at release. Releasing is a tag:

```bash
python scripts/sync_version.py --set 0.2.0
git commit -am "Release 0.2.0" && git tag v0.2.0 && git push --follow-tags
```

`release.yml` verifies, runs ruff, pytest, hassfest and the HACS action, then
publishes a **full GitHub release** — HACS shows releases, not tags. `v*` is
the integration; the YAML package keeps its dated scheme.

### The library must be installable — today it is not

`manifest.json` asks for `sungrow-modbus==0.1.0`, and Home Assistant
pip-installs `requirements` for **custom** integrations exactly as for
built-in ones. That package is not on PyPI. It works in the devcontainer only
because `scripts/setup` installs it editable; **no HACS user has that**, since
HACS copies `custom_components/sungrow_modbus/` and not `src/`.

Publish, or vendor the library into the component and drop the requirement.
**Recommendation: publish** — the library was built standalone precisely so it
could be, and vendoring keeps a build step forever to avoid a one-time upload.
For users it also means a bug report names an exact library version, which is
the "decoding wrong" versus "wiring wrong" distinction the split exists for.

#### Publishing is not the same as splitting the repository

Two questions that are easy to conflate:

- **Publishing to PyPI** is required now, for the reason above.
- **Splitting the library into its own repository** is optional, later, and
  currently not worth it. A package can be published perfectly well from a
  monorepo. Splitting buys little and costs two release streams, cross-repo
  pull requests for any change touching both, and the end of
  `scripts/sync_version.py` keeping the versions in lockstep for free.

The benefit the two-package design exists for — testing without Home
Assistant, and telling "decoding is wrong" from "wiring is wrong" — comes from
the **package boundary**, not from separate repositories. That boundary is
enforced by
[tests/test_library_is_standalone.py](../tests/test_library_is_standalone.py).
Split when there is a reason: another consumer of the library, or someone who
wants to maintain only it.

#### Claiming the name

**PyPI has no reservation mechanism.** A name is claimed by uploading a
distribution to it, and nothing else holds it. Trusted Publishing's *pending
publisher* wires up the plumbing for a project that does not exist yet, but
PyPI's own documentation is explicit that it "does not create a project or
reserve a project's name until it is actually used to publish" — if somebody
else registers the name first, the pending publisher is invalidated.

So the name is claimed by making the first release, and the steps are:

1. A PyPI account with 2FA, which is mandatory.
2. `.github/workflows/release.yml` already carries a `pypi` job using
   OIDC Trusted Publishing, so **no API token is stored in secrets**. It needs
   to exist first, because configuring the publisher requires naming the
   workflow file.
3. On PyPI, add a **pending publisher**: owner `mkaiser`, repository
   `Sungrow-SHx-Inverter-Modbus-Home-Assistant`, workflow `release.yml`,
   environment `pypi`, project name `sungrow-modbus`.
4. Optionally rehearse against TestPyPI first.
5. Tag a release. The first publish creates the project and claims the name,
   and the pending publisher becomes a normal one.

Two details worth knowing: PyPI normalises names, so `sungrow-modbus` and
`sungrow_modbus` are the same project and claiming one claims both. And
uploads are immutable — a version number cannot be reused — so the first
upload should be one you are content to have permanently.

### Rehearsing the PyPI publish

An upload is immutable and trusted publishing fails in ways that only show at
upload time, so the first real release is a bad moment to find out the
publisher is misconfigured. [.github/workflows/testpypi.yml](../.github/workflows/testpypi.yml)
does the same three steps — build, `twine check`, OIDC upload — against
TestPyPI, manually triggered, with the version rewritten to a `.devN` suffix
from the run number so it never collides with itself. It needs its own pending
publisher on test.pypi.org and a `testpypi` GitHub environment; the steps are
in [doc/maintainer_setup.md](maintainer_setup.md).

Locally, `python -m build && twine check dist/*` catches metadata problems
without any of that, and is worth running before tagging.

### Where it is installed from

**HACS custom repository now** — works as soon as a release exists. **HACS
default store** when stable: needs a description, issues enabled, topics, one
full release, brand assets at `custom_components/sungrow_modbus/brand/`
(done -- HACS looks there before it falls back to the Home Assistant brands
repository, which this integration is not in), and the HACS action and hassfest
passing.

**Core is a real option but not for this shape of integration.** New core
integrations need at least Bronze on the quality scale, no `version` key, and
requirements from PyPI. The obstacle is not code quality — it is that the
features that make this valuable are ones core would decline: a setup option
producing non-device-scoped ids, writing the user's Energy dashboard
preferences, generating a dashboard, and reaching into recorder metadata to
archive and rename. All of them exist to carry years of installed base across.
So HACS for as long as the migration matters; core only if that machinery can
later be dropped.

## The production testbed

The maintainer's instance has run the YAML package for years. It is the only
way to verify that history and statistics survive at scale.

Collect from the production `config/`: `home-assistant_v2.db` (or a dump),
`.storage/core.entity_registry`, `core.device_registry`, `core.restore_state`,
`.storage/lovelace*`, and the exact `modbus_sungrow.yaml` in use. Keep it
under a gitignored `.testdata/` — real household data, never in the repo or
CI. A purged copy is usually enough as long as long-term statistics are kept.
Work on a copy, taken with HA stopped or via a proper SQLite backup.

Then run the migration against it and assert a known sensor's history and
statistics are continuous. It also answers the one question nothing else can:
diff the **generated** legacy-id table against the real
`unique_id` → `entity_id` map, and any divergence — hand-renamed entities, ids
that slugify differently on an older release — is a silent history-loss case.

**A lighter first look:** the instance is on the LAN and the devcontainer can
reach the LAN. `config/entity_registry/list`,
`recorder/statistics_during_period` and `/api/history/period` answer most of
it read-only, given a long-lived access token kept outside the repo. Read-only
endpoints only — no service calls, no purge — and it complements rather than
replaces the copy, which is what lets a migration actually be run and rolled
back.

### Test systems, and when to use them

Four are available: one on the LAN, three remote. The devcontainer reaches the
LAN through the bridge already, so remote sites are reachable the same way
once they are routable from the host. Check for **overlapping subnets** before
assuming, since two sites both on 192.168.178.0/24 cannot be told apart.

| # | Setup | What only this one proves | Needed by |
| --- | --- | --- | --- |
| 1 | LAN: SH10RT + **Pylontech** Force H1 14.4 kWh | A third-party battery: the generic block answers, SBR's per-module registers do not | Always — the default development target |
| 2 | Remote: SH10RT-**V112** + Sungrow battery ~9.6 kWh | A variant device type code, and a real Sungrow battery | Milestone 2 (model table), Milestone 4 |
| 3 | Remote: SH10RT-**V122** + Sungrow battery + **wallbox** | The only wallbox. Turns a reverse-engineered map into a verified one | Milestone 6 — but see below |
| 4 | Remote: **two** SH10RT + Sungrow battery | Everything multi-device: discovery of several units, the naming ladder's collision case, `_inv_N` legacy mapping, aggregate sensors | Milestone 2's id work |

**Exercise all four once, now, before milestone 2 starts.** Not because the
milestones need them yet, but because three design decisions have been made on
paper and can be checked in one read-only session:

- **The naming ladder was designed without ever seeing two inverters of the
  same model.** Setup 4 settles in minutes whether both answer, whether both
  report `0x0E03`, and what their serials are — which either validates the
  model → model+unit id → model+serial ladder or kills it before 150 entity
  descriptions are built on it.
- **The capability table is currently derived from YAML comments.** Four
  fingerprints give a real matrix to build it against, including two variant
  device type codes the table has never seen.
- **The wallbox map is partial and unverified.** A read-only dump of
  21200-21319 on setup 3 says how much of it is real and what sits in the
  gaps, months before milestone 6 needs it.

`python scripts/discover_probe.py capabilities <host> --save` records each one
as two files: a **fingerprint** saying which registers answered, and a **raw**
dump of the values. Only the fingerprint is shareable — the raw file carries
the serial number and live household readings, so it goes to a gitignored
`.testdata/` and stays there. The fingerprint has neither, which also makes it
stable enough to diff when firmware changes;
[doc/fingerprints/](fingerprints/) holds the committed ones, and the same
command is what to ask a user with an unknown model to run.

For the gaps rather than the known registers — the wallbox's undocumented
21231-21261 and 21267-21299 — `discover_probe.py dump <host> --start N
--count M` reads a raw range block by block, retrying failed blocks one
register at a time so a single bad address does not hide its neighbours. All
of it is read-only; nothing writes a register.

### The reference system

Read live on 2026-09-05; every capability axis appears at once, so check rules
against this first:

| Reading | Value | Establishes |
| --- | --- | --- |
| Device type (5000) / **output type (5002)** | `0x0E03` / `1` | SH10RT, three-phase — stated, not inferred |
| MPPT1 / MPPT3 / MPPT4 | 465.5 V / `0xFFFF` / `0xFFFF` | Two MPPTs |
| Meter registers 5741-5746 | all answer | DTSU666 directly connected |
| Battery voltage / level / temperature | 200.0 V / 100 % / 33 °C | Battery present |
| Meter phase A active power | −2878 W | Exporting; signed |

The battery is a **Pylontech**, so the generic block answers but SBR's
per-module registers will not — milestone 4 cannot be tested here. There is no
wallbox on this system, and the connection is **direct to the inverter's LAN
port**: the 6100-6195 block answers, and nothing serves HTTP on port 80.

**This inverter is also polled continuously by the YAML package**, which is
worth knowing before reading anything into connection drops. A Sungrow
inverter accepts very few Modbus sessions, so a second client competes with
that poller and the device drops one of them repeatedly — seventeen times
across one fingerprint run. It is not an idle timeout and not a fault in the
tooling; raising the delay between reads made it *worse*, because a slower run
spends longer competing. Any probe of a live system has to reconnect around
it, and this is the clearest demonstration available of why the integration
shares one serialized connection rather than opening its own.

Two firmware-axis observations from the same read, which is the axis nothing
else can predict: the firmware block at **13250 answers** (added in
specification V1.1.7), while **PV power limitation at 13018 is unavailable**
(added in V1.1.10). So this inverter's firmware sits between the two, and a
capability table keyed only on model would have got both wrong.

## Related projects

[TCzerny/ha-modbus-manager](https://github.com/TCzerny/ha-modbus-manager) is a
maintained MIT custom integration with a config flow already covering Sungrow
SHx/SG/SBR/SBH, the AC011E wallbox and the iHomeManager through YAML
templates. It came up in issue
[#724](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/724),
where a config-flow integration for this repo was closed with the observation
that Modbus Manager may already do it.

What this project has that it does not: **the 2026.9 Modbus architecture**
(shared serialized connections, which is what removes the external proxy),
**a migration that preserves history** for years of installed base on specific
entity ids, and **a typed, HA-free device library** that tests without
hardware. Those three are the reasons to build it. If they stop being true,
the honest answer is to contribute to Modbus Manager instead.

---

Milestone 1 as built — the devcontainer, simulator, library, skeleton
integration and their gotchas — is recorded in `CLAUDE.md` and in the git
history from `7b42196` onward.
