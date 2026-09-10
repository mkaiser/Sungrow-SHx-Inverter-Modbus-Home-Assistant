# Plan: replacing the YAML package with a Home Assistant integration

> Plan of record for the `proper-ha-integration` branch, kept in the repo so
> it is available in the devcontainer. Findings that can be asserted are
> asserted in `tests/`; this file records decisions and the measurements
> behind them rather than repeating what the code says.

**Status, 2026-09-09.**

| | State |
| --- | --- |
| Milestone 1 — foundations | ✅ done and verified |
| Milestone 2 — inverter read parity | ✅ complete: read parity and three registers past it, capability gating, the naming convention, the migration, diagnostics and discovery |
| Milestone 3 — controls | ✅ all five slices, including start/stop as **actions** rather than buttons |
| Milestone 4 — battery modules | ✅ **SBR done**: its own device, all 40 registers in three components, 17 entities, the unit found by probing rather than asked. SBH needs its protocol document |
| Milestone 5 — iHomeManager | not started, and **nothing has ever been measured** — a sweep of one house on port 503 found nothing at all |
| Milestone 6 — wallbox | ✅ **done**: 32 registers in four components, 21 entities on a device of its own, found by asking the endpoint rather than sweeping. Read-only |
| Milestone 7 — third-party generation | ✅ **done**: two corrected sensors from another integration's entities, gated on where the foreign inverter sits relative to the grid meter. No hardware needed and none involved |
| Milestone 8 — Sungrow Logger | not started |

**Version `0.1.0a1` is set and ready to tag** (2026-09-09). A PEP 440
pre-release, which `pip` will not install without `--pre`, matched by the
"(preview)" name in both manifests and by the repair notice an install
already running will see — the three places in [The preview
phase](#the-preview-phase-and-what-a-rename-costs-during-it).

Cutting it is `git tag v0.1.0a1 && git push --follow-tags`. `release.yml`
then verifies the tag against both files, runs ruff, pytest, hassfest and the
HACS action, publishes a GitHub release marked **pre-release**, and publishes
the library to PyPI over OIDC. The `0.0.1` that was to claim the name was
never uploaded, so this is the first real version and `0.1.0` stays free for
the release worth the number.

## What is next

Ordered by what it buys, not by milestone number. Everything below is either
a decision only the maintainer can take, or work whose blocker is named.

### Decisions waiting on the maintainer

1. **The preview is out, and installable through HACS.** ✅
   `v0.1.0a1` and `v0.1.0a2` are released, both marked pre-release, and
   `sungrow-modbus` is on PyPI at both versions. A preview channel serves
   them to HACS. What is left is a decision rather than work: **when to
   merge into `main`**, which retires the channel and unlocks the HACS
   default store.

   Four things this cost, all of them fixed, and the last is the one worth
   remembering:

   - **`git push --follow-tags` pushes only _annotated_ tags.** The first
     v0.1.0a1 was lightweight, so the push said nothing and reached nothing
     -- while this document and `release.yml`'s own header both instructed
     exactly that.
   - **The branch's `Validate` run was already red on hassfest** when that
     tag went up, and the release failed the same way. hassfest is in CI;
     nobody read it.
   - **One hassfest finding was a real bug.** A device filter on `target` in
     services.yaml is forbidden *because* target expansion delivers
     `device_id` as a list while `services.SCHEMA` requires a string, so
     start_inverter and stop_inverter would have been rejected for anyone
     using the target picker.
   - **A green release can still ship a broken install.** After a1, the
     integration began importing `sungrow_modbus.fingerprint` while
     manifest.json still pinned `sungrow-modbus==0.1.0a1`, whose wheel does
     not contain that module -- so installing the branch raised ImportError
     the moment somebody clicked Add integration. A checkout hides it
     completely, because there the library is installed editable from `src/`.
     Found by opening the published wheel, not by any test. **Between
     releases, the branch is only safe to install as a tag**, which is what
     `doc/installing_a_preview.md` tells people, and the preview channel
     enforces by syncing releases and refusing one whose pin is not yet on
     PyPI.

   **Why a preview channel exists at all.** HACS resolves a repository to
   the latest *stable* release, or else to the **default branch** -- read out
   of its own source (`repositories/base.py`, `version_to_download`), which
   never consults a pre-release for that decision, and `show_beta` only
   changes what is offered *after* a repository is accepted. This
   repository's default branch is the YAML package, with no
   `custom_components/` at all, so HACS rejects it: *"Repository structure
   for main is not compliant"*. A separate repository whose default branch
   *is* the integration passes.

   [doc/preview-mirror/sync.yml](preview-mirror/sync.yml) is the whole
   mechanism and the source of record for it -- the live copy runs in the
   preview repository, which is archived when this ends. It **pulls rather
   than being pushed to**, so no credential exists in either repository:
   this one is public, and it writes only to itself. That required giving up
   on a verbatim copy, because an exact mirror must force-overwrite the
   default branch, which would delete the syncing workflow -- a scheduled
   workflow can only run from the default branch. Copying just
   `custom_components/`, `hacs.json` and a README of its own keeps the
   workflow and keeps that repository small.

   **The default store** -- searchable in HACS without adding a URL -- is a
   separate PR to `hacs/default`, and this repository already satisfies the
   easy half: a description, topics and a passing `hacs/action` run. What it
   lacks is the integration's brand in `home-assistant/brands`, which
   `scripts/make_brand_icon.py` produces the icons for. Not worth submitting
   while it is a preview, and it needs the merge to `main` first.

   One more thing that was wrong and is fixed: `release.yml` decided
   pre-release status by looking for a **hyphen** in the version.
   `sync_version.py` requires the normalised PEP 440 spelling, so every
   pre-release this project can cut has no hyphen -- and `0.1.0a1` would
   have been published as **stable**, which is what HACS offers as the
   latest. The preview labelling exists to prevent exactly that.
2. **Whether entity names are final enough** to stop being cheap to change.
   They are settled and reviewed; the preview exists so that changing one is
   still possible, with a registry migration.

### Work with no blocker

3. **The rest of the interface survey.** The survey itself is **built** --
   see [Fingerprinting from the interface](#fingerprinting-from-the-interface)
   -- and two pieces of it are deliberately not: the **block read test**,
   which is 26 block reads times three rounds plus narrowing and belongs in
   a background task rather than a form, and **pausing the coordinators** for
   the duration, without which every document from the interface is taken
   under contention and says so.
4. **Firmware-dependent register semantics**, which nothing here supports
   today and issue
   [#763](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/763)
   needs. Designed in [When a firmware changes what a register
   means](#when-a-firmware-changes-what-a-register-means).
5. **Migration per inverter.** The legacy ids are global and unprefixed, so
   only one device can hold them, and today the second inverter is silently
   not asked. Needs the `_inv_N` scheme.
6. **The config flow's topology step.** What can be determined is measured
   and written up in [Working out the topology](#working-out-the-topology);
   discovery and the name question are done. What remains is presenting the
   role it derives, and saying which claims are measured and which inferred.

### Work blocked on evidence, not effort

7. **Milestone 5 — iHomeManager.** Never measured, on any network — but no
   longer unfindable, and no longer short of a licence-clean map. `identify()`
   probes input 8000 on unit 247, so a contributor who owns one is told what
   they have instead of that nothing is there, and
   [ha-modbus-manager](https://github.com/TCzerny/ha-modbus-manager) publishes
   53 registers for it under **MIT**. Two things its documentation settles
   before any code is written: an iHM answers on port **502 or 503**, not 503
   alone, so the four sweeps that found nothing on 503 are weaker evidence
   than they looked; and it is **not a gateway** — Sungrow's own note is that
   it forwards system energy dispatch data and not the devices behind it, so
   it is one endpoint with one device on it. `collect.py` reports it and does
   not survey it, because every block that survey reads is an inverter's. See
   [cross_reference_modbus_manager.md](cross_reference_modbus_manager.md).
8. **Milestone 8 — Sungrow Logger.** Also unmeasured, also documented —
   *Logger Communication Protocol AW0 1.0.2.9*. It fronts a whole
   installation, which is the shape the one-entry-per-endpoint model was
   built for, so a reading would test that design rather than only add a
   device.

   **It will not carry the batteries, and that is documented.** Note 2 under
   the hybrid protocol's fault block, on where a battery's Modbus address
   comes from: over RS485 it is the pack's own address, and four parallel
   packs are 200-203; through a WiNet-S it is "the WiNet internal forwarding
   address", which is the mechanism behind the measured 200-on-a-cable,
   2-through-a-dongle finding in [CLAUDE.md](../CLAUDE.md). The note then
   ends: **"Logger is not supported."** So a Logger reading gives the
   installation and not the storage behind it — worth knowing before
   designing it, rather than being found by a contributor whose battery
   entities never appear.
8. **The SBR's per-module entities.** All 24 registers are read; none is an
   entity, because an unfitted module answers 0 V and something has to
   establish the module count first. An SBR128 settles it.
9. **SBH support**, which needs a register document nobody has.

What would help most from a contributor is in
[devices-wanted.md](device-fingerprints/devices-wanted.md), and the single
most useful reading is the least obvious one: **a second firmware on a model
already recorded**, because that is the only comparison that separates a
firmware-related capability from a model-related one.

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
| **Every Sungrow modbus-compatible device** | Inverter, wallbox, SBR and SBH batteries, iHomeManager — sharing one serialized connection instead of an external Modbus proxy. |
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
  [Milestone 3](#milestone-3--controls-).
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

### Taken while porting, with the reasoning

These were open questions that the work answered. Kept in full because each
records *why*, and a decision without its reasoning gets re-opened by the
next person to find the code surprising.


- **The `_raw` sensors go, in modern mode only** (2026-09-09). Legacy mode
  keeps all twelve, because that is what history is keyed to. Modern mode
  does not create them at all: *"I prefer a clean cut more over 100%
  backwards compatibility. Also those values are not very valuable, so having
  them erased wouldn't be a big deal for the users."* A user who chooses
  modern ids therefore loses those twelve, which is the point of choosing
  them.

  **Carried out, and no "raw" survives in modern mode** (2026-09-09). Eight
  of the twelve were redundant — `backup_mode_raw` beside
  `switch.backup_mode`, `running_state_raw` beside the decoded `Running
  state`, and six more. The other four looked like lost capability and turned
  out to be already answered, by the fingerprints and by the specification
  audit rather than by anything new:

  | Register | Was | Now |
  | --- | --- | --- |
  | 13090 | `sensor.active_power_limitation_ratio_raw` | **not raw at all** — a scale of 0.1, a unit, and 100.0 % on every machine surveyed. The word was describing its neighbour. Renamed `Active power limitation ratio` |
  | 13089 | `sensor.active_power_limitation_raw` | a **mode**: 170 (`0xAA`) at one house, 85 (`0x55`) at another, so both halves observed. Now `binary_sensor` **Active power limitation** |
  | 13018 | `sensor.pv_power_limitation_raw` | a **mode** by Sungrow's own V1.1.10 document, `0xAA` limit / `0x55` allow, "Only SHT are supported" — which is why all three SH inverters read `0xFFFF`. Now `binary_sensor` **PV power limitation** |
  | 31213 | `sensor.apl_shutdown_at_zero_raw` | **stays a number**, renamed `Active power limitation shutdown at zero`. Undocumented: absent from Sungrow's protocol document, contributed through issue #554, untested, and all three inverters read the same single value — so its `0xAA`/`0x55` pair is assumed rather than observed. It becomes a flag when a machine shows a second value |

  `Derived._mode_flag` returns **None** for anything that is neither value,
  including the `0xFFFF` an SH answers for an SHT-only mode: "we do not know"
  and "limiting is off" are different claims, and the second made up out of
  the first is how ten entities once reported zero forever.
- **A parenthetical says what the value is, not what produced it**
  (2026-09-09). `Daily consumed energy (filtered)` becomes **(smoothed)** and
  the seven `(delay)` binary sensors become **(delayed)**. Both words came
  from the YAML package naming a mechanism — `filter` was the platform it
  used, `delay_on` the template option — and "filtered" is ambiguous besides:
  a filter might reject outliers, cut high frequencies or drop readings, where
  this one is a 300-second time-weighted average, which is what
  `sungrow_modbus.smoothing` has called it all along.

  They do **not** share a word, and that is deliberate. `(smoothed)` averages
  a number symmetrically; `(delayed)` is a boolean that rises after sixty
  seconds and falls at once. Calling the second one smoothed would promise
  flicker suppression in both directions, and an automation built on that
  promise breaks the first time a reading dips.
- **The 15 substantive entity renames are accepted** (2026-09-09). Reviewed
  against [entity_name_review.md](entity_name_review.md) and approved as
  proposed: `Sungrow inverter serial` → **Serial number**, `Sungrow inverter
  state` → **Running state**, `Sungrow device type` → **Device type**,
  `Sungrow Arm Software` → **ARM software version**, `Sungrow Version 1-4` →
  **Firmware version part 1-4**, `Inverter temperature` → **Temperature**,
  `Inverter rated output` → **Rated output power**, `Inverter Firmware
  Version` → **Firmware version**, and the rest of the `Sungrow …` prefix
  strips. The other 19 renames are capitalisation and punctuation and needed
  no decision. So the *wording* is settled; what remains open are the two
  questions above, which the review surfaced.
- **`0.0.1` claims the PyPI name** (2026-09-06), keeping `0.1.0` free for the
  first release worth the number. Uploads are immutable, so the first version
  is permanent, and it currently describes a read-only library — a sacrificial
  version costs nothing and buys back the one number people read as "first
  real release".
- **The opt-in SBR sensors keep no history** (2026-09-09). Of the forty in
  `legacy/additional_sensors/`, eleven have a modern entity to hand history
  to; the other twenty-nine are deliberate omissions. Adopting a quarter of a
  device's history is worse than adopting none, because a partly-migrated set
  looks migrated. See [the decision](#decided-the-opt-in-sbr-sensors-keep-no-history).
- **The naming rule is scoped per device** (2026-09-09). It read as global
  because the integration made one device; there are three now, and its own
  reasoning is that a *device page* lists every domain together. A wallbox
  reporting "Phase A current" is not competing with an inverter reporting the
  same. A collision within one device still fails.
- **The wallbox is read-only** (2026-09-09). The registers that start and stop
  a charge are known, and no manufacturer document covers the map. Starting
  somebody's car from a stale automation is not shippable on one measurement
  of one unit.
- **An entity name is cheap now and awkward later, not impossible.** A name
  supplies an entity id at *creation* only, so a rename leaves an existing
  install's ids alone — proven in `tests/test_entity_naming.py`. What a late
  rename costs is divergence between houses, which a registry migration
  closes. This repository asserted the opposite in three files until it was
  tested.

## Still open

What has not been decided, and what each one is waiting for. The
**to-do list is [What is next](#what-is-next)**; this section is only the
questions, so that a decision cannot hide in a task list.

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
[scripts/influx_migration.py](#milestone-2--inverter-read-parity-) should emit
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
3. **Two sources of evidence, because the registry is not the only one.** ✅
   A YAML entity is identified by a registry lookup on `(domain, platform,
   unique_id)` — never by entity_id. **69 of the 127 legacy ids carry nothing
   Sungrow-specific**: `sensor.battery_level`, `sensor.grid_frequency`,
   `binary_sensor.battery_charging`. Matching on those would have counted a
   battery integration's entity as one of ours, offered to migrate on the
   strength of it, and deleted its registry entry to take the id. The lookup
   also follows **renames**, which slugifying the YAML's name cannot: a
   renamed entity took its history with it.

   When the registry has nothing, the **recorder** is asked instead.
   [cleanup_entities.md](../legacy/doc/cleanup_entities.md) has told users for
   years to delete the orphans a removed YAML platform leaves behind, so a
   clean registry sitting over years of rows is a normal state rather than an
   exotic one — and without that second source those users get device-scoped
   ids, a stranded history and no offer at all. `recorder` is an
   `after_dependencies` entry, so no recorder simply means no history to
   preserve.
4. **The orphaned registry rows are released, not repaired around.** ✅
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
5. **A live YAML package is detected and reported before the question is
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
6. **Every dead end has a way out.** ✅ Config flow forms carry errors, not
   buttons, so a step that fails leaves the user looking at the same fields
   with nowhere to go but the close button — which is what happened the first
   time the network search was used on a real instance. Failures that are not
   simple field corrections are menus instead: the search's "nothing found"
   offers another range, entering the address, or back to the start, and the
   picker carries a "none of these" option.
7. **Switching later is one control, not a wizard.** ⬜ Still open. An options
   flow with *Entity ID style*, working in both directions; where the target
   is occupied the archive step runs first. There is deliberately **no**
   separate "migrate back" button — back is the same control the other way.
   The dialog states how many entities will be renamed, two before-and-after
   examples, that InfluxDB and hand-built cards do not follow, and to take a
   backup. Until it lands, changing one's mind means removing the config entry
   and adding it again, which loses nothing.
8. **The archive is cleaned up only on request**, via `recorder.purge_entities`
   offered by a dismissible repair. Never automatic. ⬜ Follows 7.

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
| Inverter | [modbus_sungrow.yaml](../legacy/modbus_sungrow.yaml) plus Sungrow's *Communication Protocol of Residential and Small Industrial Hybrid Inverter* **V1.1.16 (2026-07-03)** | MIT, this repo | Field-proven, now checkable against the specification |
| SBR battery | [additional_sensors/](../legacy/additional_sensors/modbus_sungrow_SBR_battery.yaml) — 40 input registers, 10740-10788 | MIT, this repo | In use |
| SBH battery | Nothing yet | — | Needs the protocol document |
| iHomeManager | Official Sungrow PDFs — *Communication Protocol of iHomeManager* V1.0.1 and V1.0.2, both shipped in [ha-modbus-manager](https://github.com/TCzerny/ha-modbus-manager)'s `docs/` — plus that project's own 53-register template | **MIT** (ha-modbus-manager), so its map is usable directly. Sungrow's documents alongside it. The earlier note here said the only referencing project was GPL-3.0 and the spec was the only licence-clean route; that is no longer the case | A specification, and now a second implementation to check it against. §3.4 Charger Control is listed in the V1.0.2 table of contents and **missing from the PDF**, so the published read-write table is known to be incomplete |
| Wallbox | [evcc `charger/sungrow.go`](https://github.com/evcc-io/evcc/blob/master/charger/sungrow.go), plus a live measurement of an AC22E-01 cross-checked against two projects — see [wallbox_registers.md](wallbox_registers.md) | MIT (evcc, and KevinD987); Louisbertelsmann's carries no licence file and is used with the author's permission, for register *meanings* only | Measured through a charging session that ended, so the counters, the status codes and the timestamps are separated by behaviour rather than inference. Register 21313 is the only line nobody can name |
| Logger1000/3000/4000 | Sungrow's *Logger Communication Protocol* **AW0 1.0.2.9**, plus the field-proven map in [discussion #262](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/discussions/262) | Sungrow's document | An official specification exists. Scope limit known in advance: the hybrid protocol's Note 2 ends "Logger is not supported", so a Logger does not forward battery data |

The wallbox has no official register document; evcc is the best-licensed
source and covers AC011E-01 and AC22E-01. The maintainer also has the wallbox
project author's permission, and the values are public in photovoltaikforum.

Since 2026-09-08 there is a measurement of our own: an AC22E-01 read through a
WiNet-S while a car was charging and then finished charging, which is what
separates a session counter from a lifetime one and a timestamp from an energy
reading. It settled one disagreement between the two projects — the lifetime
counter is 32-bit — and confirmed one hypothesis against an independent
measurement on the other model, the control-pilot voltage at register 21312.
`doc/wallbox_registers.md` carries the table and marks every line by how many
sources hold it.

**Audited against V1.1.11, then re-audited against V1.1.16.** The YAML has
kept up better than expected. Of the
seven register additions between V1.1.2 and V1.1.11, four are already covered
— the firmware block at 13250-13369, active power limitation 13089/13090, and
meter active power 5601. Three are not, and are the port's chance to go past
parity:

| Missing | Space and register | Added | Now |
| --- | --- | --- | --- |
| Feed-in limitation ratio | holding 13088 | V1.1.7 | ✅ `feed_in_limitation_ratio`, U16 0-1000, 0.1 % |
| Meter channel 2 data | input 13200-13207 | V1.1.9 | ✅ four S32 powers, 1 W |
| PV power limitation (writable) | holding 13018 | V1.1.10 | ✅ read as `pv_power_limitation_raw` |

**All three are in**, read out of V1.1.11 rather than inferred, and they go
through the same generated pipeline as everything else: declared once in
`SPECIFICATION_ADDITIONS`, from which the entity map, the register map, the
descriptions, the names and the simulator seed all follow. They carry
`layer: "specification"` so what is *not* from the YAML stays visible — no
`unique_id`, no legacy name, nothing to migrate, because there is no history
of them.

Three things the specification settled that guessing would have got wrong:

- **Feed-in limitation ratio is not the active power limit ratio.** The YAML
  already reads 13090; 13088 is a different measurement of a different thing —
  feed-in limitation controls the **grid connection point**, power limiting
  controls the **inverter's AC output**.
- **PV power limitation is a mode, not a power.** `0xAA` limit, `0x55` allow,
  U16 — a power sensor in watts would have been wrong in unit, class and
  meaning. And "Only SHT are supported", which is why the reference SH10RT
  answers `0xFFFF`.
- **Meter channel 2 needs a dual-channel meter** (a DTSU666-**20**), and S32
  is little-endian across the two registers — the same `swap: word` the YAML
  uses everywhere, with `0x7FFFFFFF` as the unavailable sentinel rather than
  `0xFFFF`.

Each is gated by a new capability, so none of them creates a dead entity on
hardware that does not have it.

Match on **space and register together**. An earlier pass compared addresses
alone and reported a collision between the YAML's `total_direct_energy
consumption` and the specification's PV power limitation, both at 13018 —
but one is an input register and the other a holding register, which are
separate address spaces. There was no conflict.

**The re-audit against V1.1.16 found four more things**, and the count above
is itself one short. Between V1.1.2 and V1.1.11 the specification added
**eight** registers, not seven: V1.1.7's change list has "Add Forced Startup
Under Low SOC Standby (13017)" as its sixth item, and the tally above passes
over it — the other two items in that list, remarks on read-only registers
and the retirement of the protocol number, add no register and are rightly
excluded. So 13017 is an eighth addition and was simply missed. It is in now,
gated by the remarks column, which excludes only SH50~125CX.

Three groups V1.1.16 defines that neither the YAML nor the V1.1.11 pass
picked up, all now in `SPECIFICATION_ADDITIONS`:

| Added | Space and register | Note |
| --- | --- | --- |
| Backup current, voltage, frequency | input 5720-5722, 5731-5734 | The YAML reads backup *power* at 5723-5726 and stops |
| Self-consumption of today | input 13029 | U16, 0.1 %, a ratio and not a counter |
| Forced startup under low SoC | holding 13017 | The missed V1.1.7 addition |

And one group left out deliberately, because it is bigger than it looks: the
**fault and alarm block is fourteen consecutive U32s at input 13052-13079**,
and **Appendix 4 defines every bit** across six pages. Roughly 450 named
flags do not map onto entities without a decision about representation, and
taking the five that another project happens to expose would be the wrong
cut. It is the largest single piece of specification this port still does not
read.

The remarks column turned out to be where the per-model capability facts
live, and two `ABSENT_IN` entries had been recorded from older, narrower
wordings — the YAML's "MG5-6RL" and V1.1.9's "MG5-10RL" named the models that
existed when they were written. The full table, and the one conclusion that
had to be reached twice, are in
[cross_reference_modbus_manager.md](cross_reference_modbus_manager.md).

`DEVICE_TYPES` is now checked against Appendix 1 of **V1.1.16** and pinned
by [tests/test_device_types.py](../tests/test_device_types.py): all 49 models
present and names agreeing, where the V1.1.11 pass had 35. Seven
entries remain that the specification dropped in V1.1.0 — the SH\*K series —
because the hardware outlived the paperwork, and the test records that as a
decision rather than an oversight.

The fourteen models V1.1.12 to V1.1.16 added also **falsified how families
were classified**. That was a table of device-type code ranges, whose comment
said Sungrow "allocates them in blocks and new models land inside those
blocks"; in fact MG5RL-MG10RL take 0x0D27-0x0D2A, SH5RL-SH10RL follow at
0x0D2B-0x0D2E, and MG12RL and MG7.5RL appear *above* them. Widening the MG
range to reach MG12RL would have called four single-phase inverters
three-phase. `family_for` reads the model name instead, `Family` gains **RL**
and **CX**, and a test now asserts that every model in the table classifies
to something — the check the range table lacked, which is why nine models
resolved to `None` and lost their gating in silence.

**SH50-125CX is named but not supported.** Ten MPP trackers against a
register map that stops at four, no reading from one, and an Appendix 1 row
that contradicts itself on SH50CX's tracker count. The names are in so the
specification's many "SH50~125CX are not supported" remarks can be recorded,
and the family is in so a CX is not silently treated as something else.

## Roadmap

### Milestone 2 — inverter read parity ✅

The 103 modbus entities plus the user-facing template sensors, and three
registers past parity. No writes — those are milestone 3.

**Done.** The numbered list below is the record of how, each item marked with
what it settled; four of them are the foundation the rest rested on: the
entity map, generated and validated against a real registry; the model table,
pinned to specification V1.1.11; the register coverage audit; and the
capability model, which turned the YAML's comments into gates.

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
10. **`scripts/influx_migration.py`** ✅ Done. Emits, from the same mapping
    the entities are generated from: a Grafana regex per entity matching both
    names — the cheapest fix, since no data moves and it survives migrating
    back — Flux that *copies* each series to the new tag on InfluxDB 2.x, and
    the export/`sed`/import recipe for 1.x, where a tag is part of the series
    key and InfluxQL cannot rewrite one at all. Both directions, because the
    migration is reversible.

    It connects to nothing and executes nothing, and the destructive steps are
    printed commented out. Rewriting somebody's time-series database is not a
    thing to do on the strength of a script that has never seen their data.

### Milestone 3 — controls ✅

**In slices, safest first, because the write path had never run against real
hardware.** Each slice is declared in
[scripts/writes.py](../scripts/writes.py) and nowhere else:
`generate_registers.py` marks exactly those fields `writable=True`, so the
library refuses a write to any register the integration has not deliberately
exposed, and a test asserts the writable set *is* that table. Another names
the registers still held back individually, so shrinking that list is a
deliberate commit rather than a side effect.

| Step | What | State |
| --- | --- | --- |
| 1 | The three state-of-charge limits | ✅ |
| 2 | Battery charge/discharge maxima, export power limit | ✅ |
| 3 | The three mode flags — off-grid, feed-in limitation, load on/off | ✅ |
| 4 | The selects — EMS mode, forced charge/discharge, load control mode | ✅ |
| 5 | Inverter start and stop — **actions, not buttons** | ✅ |

**Start and stop are actions, not entities**, decided by the maintainer over
a disabled-by-default button. Home Assistant has no confirmation dialog for a
button press, so a card copied from somebody's screenshot, a stale automation
or a misclick while scrolling a phone all stop an inverter — and the entity
would sit in every dashboard picker and automation editor offering exactly
that. An action has to be written into a script or called from Developer
Tools, which is the first guard and is not available to a button. The second
is who may call it, and that is a per-entry option — administrators only by
default. See [Who may change what](#who-may-change-what).

Hiding and showing the control stays a dashboard concern, where the YAML
package already solves it: `legacy/dashboards/DefaultDashboard`'s danger-mode
toggle is the pattern to point users at.

### Parity: what is ported, and the three things that are not

Measured rather than assumed, on 2026-09-07, by asking which YAML entities
have no counterpart. It came to fifteen, and the answer was different for each
group — which is why the count is now asserted both ways in
`test_entity_wiring.py` rather than written down here as a number.

Ported since:

- **The two start-power numbers**, above.
- **The seven `(delay)` binary sensors**, which repeat a power-flow bit only
  once it has held for a minute so a card does not flicker, and **the one
  `(filtered)` sensor**, a five-minute moving average of the daily
  consumption. Both are time-dependent rather than pure functions of the
  registers, so they live in `sungrow_modbus.smoothing` rather than in
  `derived.py`, with the clock passed in — which is what lets them be tested
  to the second without waiting one.

  The average is Home Assistant's `time_simple_moving_average`, **time
  weighted**: each value is held until the next sample arrives and the average
  is of that step function, so an inverter answering irregularly — which one
  behind a WiNet-S does — is not given extra weight for samples that happened
  to arrive close together. Reproduced from core's `TimeSMAFilter` and checked
  against it, running both over the same twelve samples, because the claim is
  that it *is* that filter.

  Two things the port had to get right that the YAML gets for free. Core's
  filter copies the unit, device class and **state class** off the source
  state, so the entity map records none for the filtered sensor and the
  replacement takes the source's — get the state class wrong and long-term
  statistics freeze flat while raw history keeps filling. And its registry
  entry belongs to the `filter` platform, not `template` or `modbus`, so the
  migration has to look it up under that platform or the entity quietly
  arrives device-prefixed with none of its history.

Deliberately not ported, and listed for users in
[integration_migration.md](integration_migration.md):

| Was | Now | Why |
| --- | --- | --- |
| `button.start_inverter` | Action `sungrow_modbus.start_inverter` | No confirmation dialog for a button press, and an action's audience can be chosen |
| `button.stop_inverter` | Action `sungrow_modbus.stop_inverter` | Same |
| `switch.sungrow_dashboard_enable_danger_mode` | A Toggle helper, if the old dashboard is kept | Never a device setting; the integration's answer is the permission ladder |

**Register 13000 is in both of Sungrow's tables, and they are different
address spaces.** Table 3 is read-only over function code 0x04 — reading
13000 there gives the running state, which is what `running_state_raw` does.
Table 4 is read/write over 0x03/0x06/0x10, where 13000 is Start/Stop. So the
YAML reads one space and writes the other, correctly, and marking
`running_state_raw` writable was wrong: the library refused it, which is how
this was noticed rather than shipped. The holding-side field is hand-written
in `components.InverterControl`, never polled, and the write is followed by a
refresh of the **realtime** group — refreshing the group that was written
would show the old state.

`UNCONFIRMED` is now **empty**. It held
`battery_charging_start_power` and `battery_discharging_start_power`, at YAML
addresses 33148/33149 — registers 33149/33150, neither of which exists in
V1.1.11, where register 33148 is "Charging/Discharging Power - Wide range" and
a different thing. Released by the maintainer on 2026-09-07 after the round
trip was verified on hardware; see [Verified against real
hardware](#verified-against-real-hardware-2026-09-07). The table is kept
rather than deleted, so shrinking it stays a deliberate commit.

**A write refreshes immediately, and that is not a detail.**
`async_request_refresh` goes through the coordinator's debouncer, whose
cooldown is **ten seconds** — so a second change inside that window is written
to the register and never read back, and the interface shows the previous
value. That is precisely the readback problem the YAML needed
`homeassistant.update_entity` for, and it would have shipped as a regression;
it was caught by a test that changes a value twice. The debouncer exists to
coalesce storms of *automatic* refreshes. An explicit user action is not a
storm.

**An unrecognised value is unknown, not the default.** The YAML's selects
fall back to their default option when a register holds something their map
does not have — which tells the user the inverter is in self-consumption mode
when it is in something else, and hides the one case worth noticing: Sungrow
adding a value nobody has written down yet. `current_option` returns `None`
instead.

The option keys and the register values are **one generated table**, and the
labels come out of the same rows into `strings.json`. Two tables, one for
reading and one for writing, eventually disagree — and the codes are not
sequential (`0xAA` charge, `0xBB` discharge, `0xCC` stop; EMS mode skips 1),
so nothing here can be a range check.

**A mode flag has three states, not two.** The YAML's switches treat anything
that is not the `on` code as off, so a register answering the specification's
0xFFFF reads as a feature the user has switched off rather than one their
model does not have. `is_on` returns `None` for anything that is neither code.

Names to keep straight, because the YAML's are not the specification's and
users have the YAML's:

| YAML | Specification | Register |
| --- | --- | --- |
| Backup Mode | Off-grid option | 13075 |
| Export power limit (switch) | Feed-in Limitation | 13087 |
| Load adjustment mode (switch) | Load ON/OFF mode | 13011 |


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

### Milestone 4 — battery modules ✅ (SBR)

**SBR done.** All 40 input registers are read, in three components, with 17
entities on a device of its own. SBH is not started and needs a register
document nobody has.

Which **unit id** the pack answers on depends on the transport, and this row
said the wrong thing until it was measured:

| Path | The SBR module block answers at |
| --- | --- |
| The inverter's own LAN port | unit **200** |
| Through a WiNet-S | unit **2**, and *nothing* at 200 |

Measured on one SH8.0RT-V112 read both ways four minutes apart, and again on
an SH10RT-20 at another house — the readings are in
[device-fingerprints/](device-fingerprints/). So the earlier claim that an SBR
is "not reachable through WiNet-S at all", and therefore often needs a second
config entry, was wrong: it is reachable on the endpoint that is already
there, under a different number. **Probe both**, and note that unit 2 is also
where a slave inverter lives, so the device type code has to be read alongside
to tell them apart — a slave answers it and a battery does not.

✅ **Wired to Home Assistant** (2026-09-09). `SungrowBattery` in
[battery_device.py](../src/sungrow_modbus/battery_device.py) holds the two
components; `SungrowBatteryCoordinator` polls them on the inverter's *medium*
interval, sharing the inverter's connection because one config entry is one
endpoint and a Sungrow accepts very few sessions; and the pack is **its own
device**, hung off the inverter with `via_device`. Seventeen entities.

Three things worth knowing about it:

- **The unit id is never asked.** `battery.probe_units` finds it, and
  discriminates against a slave inverter, which also lives at unit 2 on a
  direct connection and answers a device type code where a pack does not.
  Finding nothing is the common case, not a failure, and a pack that answers
  its probe and then fails a full read is skipped rather than failing the
  entry — the inverter is already polling fine by then.
- **Two gates, because the two blocks fail separately.** The pack summary is
  created where a pack answered; the cell entities need a **non-zero**
  reading. A successful read is not enough: one dongle firmware answers that
  whole block with zeros, which decode to values, and nothing ever removes an
  entity.
- **The device is identified by the inverter's serial with a suffix.** An SBR
  reports no serial of its own — the whole 10740-10789 band was read and
  there is none in it — and its *model name* comes from register 5639 on the
  inverter, so a pack whose size the inverter does not report is called
  "Battery" and keeps all its readings.

The descriptions are hand-written in
[battery_descriptions.py](../custom_components/sungrow_modbus/battery_descriptions.py),
for the same reason `battery_registers.py` is: the generated
`sensor_descriptions.py` comes from the YAML package's entity map, and these
registers are not in it. So they are the only hand-written descriptions in the
integration, which makes them the ones a rule stops covering by accident —
hence they go through `naming.OVERRIDES` and are checked by
`test_naming_convention.py` like everything else, and
`test_battery_entities.py` asserts every `field` resolves and that no key
collides with one of the inverter's.

#### Decided: the opt-in SBR sensors keep no history

**Settled 2026-09-09: leave it.** A user who copied
`legacy/additional_sensors/modbus_sungrow_SBR_battery.yaml` into their
configuration gets new ids, and their old entities go unavailable exactly as
if they had removed the file.

One correction to the record first, because the decision was nearly taken on
a wrong premise. This section used to say the adoption *could not* work
because the additional file is not in `doc/legacy_entity_map.json`. That is
not how detection works: the map is an input to the **generator**, while
`async_legacy_entities` reads the **registry**, matching each description's
`legacy_unique_id` and platform. It also follows renames and matches on
unique_id rather than entity_id, so even an edited copy-paste would be found.
The mechanism was available.

What decided it was the coverage, now that all forty registers are read:

| | Count | What |
| --- | --- | --- |
| Could adopt | **11** | voltage, current, temperature, SoC, SoH, the two lifetime counters, the four pack-level extremes |
| Could not | **29** | the four raw position words, 24 per-module registers, the DC contactor |

The 29 are not an oversight. The four position words are deliberately
replaced by six module-and-cell entities, because `780` is not a cell anybody
can look up -- so adopting the raw word would reintroduce exactly the `_raw`
value modern mode banishes. The 24 per-module registers have no entities
because an unfitted module answers **0 V**, indistinguishable from a fault,
and five of eight slots are empty on a typical SBR096; building them would
create entities reporting zero forever, which is the failure
`ZERO_MEANS_ABSENT` exists to prevent. The contactor's code table is
undocumented.

So the choice was between adopting 11 of 40 and adopting none, and none is
the cleaner cut -- the same reasoning already applied to the nineteen
legacy-only inverter sensors: *"I prefer a clean cut more over 100%
backwards compatibility."* Adopting a quarter of a device's history is worse
than adopting none of it, because a partly-migrated set looks migrated.

Worth saying plainly in the release notes rather than leaving to be
discovered: this file was always an opt-in extra, and the integration reads
**every register it read**, on a device of its own, with better names. What
does not carry over is the history.

**The cell data does not survive a dongle — settled 2026-09-09.** It was
open on one path's evidence: read at unit 2 on bar12's SBR096, the pack-level
registers answered true while every per-module register read **0**, and one
path cannot say whether the dongle withheld them or the pack never filled
them in.

One SBR096 read both ways within seconds answers it:

| Block | Cable, unit 200 | Dongle, unit 2 |
| --- | --- | --- |
| Pack, input 10740 x9 | reads | reads, identical values |
| Cells, input 10756 x8 | **reads true** — 3.3337 V / 3.3251 V, 22.9 / 21.9 °C | **exception 0x02** |

So the pack populates them and the dongle loses them. "Never populated" is
ruled out. And it loses them **two different ways** across two dongle
firmwares — refusing here, answering zeros at bar12 — which is why
`ZERO_MEANS_ABSENT` has to cover this block and not only the inverter's
optional trackers. The rule stands as written: pack-level fields may be
granted on a reading, cell-level ones need a non-zero reading or a direct
path.

The same reading found the four `*_position` registers to be **packed**,
`(module << 8) | index` — see [the decision above](#settled-a-dongle-withholds-the-sbrs-cell-data-and-it-is-packed).
Decoded in `SbrBatteryCells` as eight properties, tested against all eight
samples known.

✅ **The survey now carries it** (schema 15, `battery_pack`). It used to
probe unit 200 and unit 2 with a two-register read, record "present", and
stop — so no document anywhere held a single battery reading, and the
question above stayed open until somebody read nine registers by hand.

Seventeen registers in two reads, on whichever unit answered, against an
inverter dump of 1510. The two blocks are read and reported **separately**,
because they fail separately: pooled, a dongle's refusal of the cells would
take the state of charge with it and the document would call the pack
unreadable when only half of it was.

And **no second decoder**, which was the point of doing it this way.
`generate_scan_plan.py` records `SbrBatteryPack` and `SbrBatteryCells` the
same way it records the inverter's, marked `"unit": "battery"`, and
`_field_detail` needed no teaching — it already handled every scale, sentinel
and word order those fifteen fields use. `portable.read_fields` grew a `role`
argument to select them, and `tests/test_portable_decoder.py` now compares all
fifteen against the library with nothing written to make them agree. The unit
ids travel in the plan as `battery_pack_units`, copied from
`battery.PACK_UNITS`, because `probe.py` runs from a zip where the library
does not exist.

Two guards worth naming, both from measurements rather than caution. A slave
inverter also lives at unit 2 on a direct connection, so the read is skipped
where the device type code answers there — the same discriminator
`_battery_token` uses, and without it a slave would be read as its own
battery. And the key is `battery_pack`, not `battery`: that name already holds
what the *owner typed* about their battery, and the first attempt overwrote
their testimony with a measurement.
`test_a_supplied_value_lands_only_in_user_inputs` caught it.

**Twenty-five more registers — measured, and now ported.** The same
reading covered the whole 10740-10789 band, which is wider than the two
components. What is there, all of it confirmed against
`legacy/additional_sensors/modbus_sungrow_SBR_battery.yaml` -- whose
*addresses* are right even though its comments are not, four consecutive ones
being labelled "reg 10777, Module 5" and three more "Cell Type of Module 5":

| Addresses | What | Measured |
| --- | --- | --- |
| 10764-10771 | max cell voltage of module 1-8 | 3.3507, 3.3484, 3.3487 V, then five zeros |
| 10772-10779 | min cell voltage of module 1-8 | 3.3436, 3.3448, 3.3449 V, then five zeros |
| 10780-10787 | cell type of module 1-8 | 66, 66, 66, then five zeros |
| 10788 | DC contactor state | 2 |
| 10749, 10750 | undocumented | 1 and 4 |
| 10751-10755, 10789 | 0xFFFF, 0xFFFF... and 0 | declared unavailable |

✅ The first four rows are in `SbrBatteryModules`, a third component
because it fails a third way: a module that is not fitted answers **0**
whatever the transport, so an SBR096 reports five empty slots on a perfectly
good link. Both cautions were taken. The eight-module families are eight
explicit fields each rather than a `repeating_group`, which would break an
assumption `scripts/generate_scan_plan.py` relies on — the plan agrees with
the library today partly because this map has none. And **none of these is an
entity**: the survey carries all forty registers now, while nothing invents a
meaning for a number whose enum nobody has, and nothing creates an entity
that would report 0 V for an absent module for the life of an install.

What still gates the per-module entities is the **module count**. Deriving it
from which cell-type registers are non-zero would work on the one pack
measured, and an SBR128 is what would show whether four modules report a
fourth cell type or something else — see
[devices-wanted.md](device-fingerprints/devices-wanted.md).

The three registers the YAML does *not* read stay unported: 10749, 10750 and
10789 answered 1, 4 and 0, and nothing says what they are.

**What the simulator cannot do.** `scripts/simulate.sh` serves one unit id and
its seed has none of these addresses, so it cannot stand in for a pack on unit
200 beside an inverter on unit 1. The tests use the words one SBR096 actually
said instead, which is the better fixture: both dongle behaviours measured —
fwitten's refusal and bar12's zeros — are asserted, including that a zeroed
position becomes an absence and never "module 0, cell 0".

### Milestone 5 — iHomeManager

Best documented of the lot. **Port 503, slave 247.** Grid metering, battery
and EMS control, EV charger status. An iHomeManager also changes what the
*inverter* answers, so this is not only a new device. Worth reading its
**Modbus Transfer** guide while here: a documented relay to devices behind it
would give an officially specified path to wallbox registers.

Four issues and a discussion asked for this, and [doc/faq.md](../legacy/doc/faq.md) still
answers "not at the moment" — update it when this ships.

### Milestone 6 — wallbox ✅

**Done 2026-09-09.** 32 registers in four components, **21 entities** on a
device of its own, at unit 3 through a WiNet-S or 248 direct — so the unit id
has no safe default and is never asked for. An iHomeManager is *not* required.

Four things settled in the doing, each recorded where it belongs:

- **Two intervals, not the plan's three.** The live block — 23 registers that
  move while a car charges — polls on the inverter's fast tier; identity,
  ratings and settings refresh every thirtieth poll. Reading a rated current
  every ten seconds would spend a Sungrow's scarce session time on a number
  that cannot change. A slow component not read this time keeps its values
  rather than being reported failed, or its entities would go unavailable four
  polls out of five.
- **Read only.** The registers that start and stop a charge are known —
  holding 21211 and 21212 — and no manufacturer document covers this map.
  Starting somebody's car from a stale automation is not a thing to ship on
  one measurement of one unit. `scripts/writes.py` holds no wallbox register
  and a test asserts none is writable.
- **Three kinds of register get no entity**: the raw codes, whose decoded
  properties are the entities; register 21313, which none of the four sources
  can name; and the two session timestamps, epoch-shaped numbers holding the
  wallbox's *local* time, where a `timestamp` entity needs a real instant this
  project cannot supply. All three are still read, so the survey carries them.
- **The naming rule is now scoped per device.** It read as global because the
  integration used to make one device, and its own reasoning is that "a device
  page lists every domain together" — there are three pages now. A wallbox
  reporting "Phase A current" is not competing with an inverter reporting the
  same: separate pages, separate device-name prefixes, separate ids. A
  collision *within* one device still fails.

A fourth source turned up while checking this work and is folded into
[wallbox_registers.md](wallbox_registers.md): it measured the same model,
confirmed the status table and the phase scales, and disagreed twice — see
[where the sources disagree](wallbox_registers.md#where-the-sources-disagree-and-what-settles-it).

**Measured 2026-09-08, so this is no longer a transcription job.** The
maintainer's access is an SH8.0RT-V112 with an SBR096 and an **AC22E-01**
(register 21224 reads `0x3F80`), and it was read through a charging session
that ended. [wallbox_registers.md](wallbox_registers.md) has the table, marked
by how many independent sources hold each line, and three results that change
what this milestone has to do:

- the status register's nine codes are known, including that `6` is
  *Completed* rather than idle — an integration that got that wrong would
  mislabel every finished charge;
- the lifetime counter is 32-bit, which two projects disagreed about;
- one register, 21313, is nameable by nobody, and an entity should not be
  invented for it.

Also measured there: a wallbox with its own LAN cable still answers **only**
at unit 3 behind the dongle's endpoint, never at 248 and never on an address
of its own. A sweep cannot discover one, so the config flow has to ask the
endpoints it already has.

This is where the shared connection pays off most visibly: the community
project tells users to run an external Modbus proxy because inverter and
wallbox contend for the dongle. Two devices on one endpoint share one
serialized connection instead.

### Milestone 7 — third-party generation behind the meter ✅

**Done**, and it is the only milestone that fixed a **wrong number** rather
than adding a missing one.

A non-Sungrow inverter on the same supply is invisible to the Sungrow, which
computes house load from its own AC output and its grid meter:

    reported load = inverter output + grid import

correct while it is the only generator. Add a Fronius or a microinverter
behind the same meter and the true load is that plus the foreign production,
so the reported figure is **low by exactly that production** and **negative**
once it exceeds what the house uses. Every input to the figure was measured,
which is why the wrong answer looks like a reading and why no register hints
at it.

**What was built.** `external.py` holds the arithmetic and the sign
convention; `external_descriptions.py` the two entities:

| Entity | Value | Created when |
| --- | --- | --- |
| `corrected_load_power` | `load_power` + foreign production | the foreign inverter is **behind the same meter** |
| `total_site_pv_power` | `total_dc_power` + foreign production | any placement |

The options flow's **Another inverter** page names the source entities --
filtered to power sensors at the picker, so the unit is known before anybody
submits -- and asks where they sit. It also prints the inverter's *current*
load reading, because a negative number on screen while the sun is up is the
symptom itself and the shortest proof the page is the right one.

**Four decisions worth keeping.** Each is a place this could have produced a
plausible wrong number instead of admitting it did not know, and each is
asserted in `tests/test_external_generation.py`:

- **The placement is asked, never guessed.** Separately metered production
  never passes the Sungrow's meter, so its load figure is already right and
  correcting it would *introduce* the error. `corrected_load_power` is
  therefore not created at all in that case -- an entity knowingly duplicating
  another is worse than no entity.
- **A silent source makes the value unknown, not unchanged.** Treating an
  unavailable generator as producing nothing gives back exactly the error this
  removes, and it would be indistinguishable from a correct reading. The cost
  is real and documented: a PV integration reporting `unavailable` overnight
  takes these entities to unknown with it, and the page says to prefer a
  source that reports zero. `external_sources_not_reporting` names which one.
- **The unit is required, not assumed.** A power sensor is very likely W or
  kW and guessing between them is an error of a thousand that would look
  entirely plausible in the result. A source with no power unit counts as not
  reporting.
- **A negative corrected load is left negative.** It is the signature of
  unmetered generation and the reason an owner would come looking. A
  `max(0, …)` is the obvious thing for somebody to add later, so a test holds
  it.

**And no kWh sensor**, deliberately: the Energy dashboard already accepts
several solar sources, so a household adds both inverters there and gets a
correct total with no help from here. A second, divergent answer beside the
dashboard's own would have to survive restarts and unavailable sources to be
worth anything. Power is different -- nothing in Home Assistant corrects a
*load* figure another integration computed wrongly, which is the actual gap.

Two boundaries held. The code lives in the **integration, not the library**,
because it consumes other Home Assistant entities -- the one deliberate
exception to the library's no-HA-imports rule, and the reason `external.py`
is not in `src/`. And these are the only entities whose existence depends on
an **option** rather than on what the hardware answered, which is also why
they are the only ones this integration ever *removes* from the registry:
absent hardware can come back, an owner who unnamed their other inverter has
decided.

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

## Fingerprinting from the interface

**Built**, in 0.1.0a2, except for the two pieces named at the end -- which
are the two that make it harder than it looks.

A fingerprint used to cost a contributor a Python run on a machine that can
reach the inverter. That is why every document in
`doc/device-fingerprints/` comes from one of four houses, all known to the
maintainer, and why one axis of `compatibility.md` is still entirely
unmeasured. Somebody who has already installed the integration has, by
definition, a working connection to their inverter — and had no way to turn
it into evidence.

**What was built.** `custom_components/sungrow_modbus/fingerprint.py`
assembles a survey document and `diagnostics.py` carries it as a
`fingerprint` section, so the delivery mechanism is a button Home Assistant
already has: it produces a JSON file a user attaches to an issue, it is
reachable with no entities involved, and it already redacts. The document is
the **same schema** `collect.py` writes -- schema 17, which admits the
second producer -- so one generator keeps producing `compatibility.md` from
both.

The register knowledge moved to `sungrow_modbus.fingerprint`, where both
producers reach it: the 19 curated probes, the five firmware strings, the
four-state vocabulary (`present`, `unavailable`, `refused`, `no answer`),
the stand-in derivation, the transport verdict and the sentence about WiFi
versus Ethernet. `probe.py` keeps literal copies, because that directory
ships as a zip and cannot import the library, and
`tests/test_fingerprint_tables_agree.py` is what makes that duplication
safe -- a probe label *is* the published format, so renaming one on one side
would silently unrelate every new reading from every old one.

**What is asked, because no register answers it.** An options page collects
the testimony: which cable, whether a Modbus proxy is in the path, whether
anything else was polling, who is reporting, and whether the address may be
published. All optional, and empty stays distinct from `unknown` -- the
question not put against the owner not knowing. The page opens by saying
what has already been measured, so nobody is asked whether they use a dongle
when register 6100 settled it 9 times out of 9.

Submitting it runs the survey behind a progress step and then reports what
was found, where the file is, and where to send it. That last part is not
decoration: the file sits behind a menu on a different page, which nobody
would guess, and a reading nobody sends is worth nothing. The same text is
left under Notifications, because a config-flow page is gone the moment it
is dismissed and that is exactly when the instructions are needed.

**Two pieces deliberately left out**, and both are the reasons this was
harder than it looked:

1. **A fingerprint taken from inside Home Assistant is taken under
   contention** — and this project discards documents taken while something
   else was polling, because contention and a register fault are hard to tell
   apart from the result. Four documents were thrown away for exactly this.
   So for now the document *admits it*, in a `contention` section outside
   `user_inputs` -- a measurement, since the integration knows what it was
   doing rather than being told -- naming the components, their intervals and
   `coordinators_paused: false`. Holding the coordinators off for the
   duration is the fix and is not done. A *second* poller outside the entry
   — another Home Assistant, the YAML package, evcc — remains undetectable
   either way, which is why the question is asked.
2. **The block read test is the expensive part**, and is not run at all.
   Twenty-six block reads times three rounds, plus binary-tree narrowing over
   whatever failed, which on a slow link ran a survey past its own cap.
   `blocks.NARROW_BUDGET` exists for that and would have to be enforced
   harder inside Home Assistant, where a config-flow step cannot sit for a
   quarter of an hour. The realistic shape is a background task with a
   progress notification, not a form that blocks. Until then a document from
   the interface carries no block evidence, and
   `test_a_collect_run_at_schema_16_carries_its_block_read_test` is keyed on
   the tool so that absence is legitimate rather than a lie.

### A diagnostics-only setup mode

**Built**, in 0.1.0a2. A contributor who wants to send a reading
should not have to answer the migration question at all — it is the one
irreversible decision in the flow, and it has nothing to do with producing a
document.

The shape: a first step asking what the entry is *for*. **Diagnostics only**
connects, identifies what answers, probes capabilities, registers the device
and creates **no entities** — so `PLATFORMS` is empty for that entry, the
entity-ids question is never asked, and `async_claim_legacy_ids` never runs.
**Full integration** is today's flow, unchanged.

Then the options flow can switch an entry from diagnostics-only to full
later, which it already does correctly: an options change reloads the entry,
and the entity-ids choice would be asked at that point instead.

Three things to be honest about:

- An entry with no entities is unusual but entirely legal, and the
  diagnostics download does not depend on any existing.
- It still opens a Modbus connection, so it still spends one of the very few
  sessions a Sungrow grants. Diagnostics-only is cheaper than a full entry
  but not free.
- It must not become a way to end up with a half-configured integration by
  accident. The step has to read as *"help this project by sending a
  reading"* rather than as a mode with fewer features.

## When a firmware changes what a register means

**Not supported today**, and issue
[#763](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/763)
is the case that needs it: after a firmware update, writing the export power
limit at register 13074 behaves as though the value were 0.1% of rated power
rather than watts — write 700, get 7000 W.

**What exists.** Capabilities gate whether a group of registers is *read at
all*, probed by reading rather than inferred, and that is the only
variability the model has. `Capability.FIRMWARE_VERSIONS` means "the version
registers answered", not "which version". A register's address, scale, unit
and sign are class attributes in `registers.py`, fixed at import:

    export_power_limit = integer(13073, signed=False, unit="W", writable=True)

One interpretation, compiled in. Nothing consumes a version string to change
it.

**What is already in place to build on.** The input is read and recorded:
`sungrow_version_1` and `_2`, `inverter_firmware_version`,
`sungrow_arm_software`, `sungrow_dsp_software` and `sungrow_protocol_version`
all reach every fingerprint, and every writable register is declared in one
table (`scripts/writes.py`) that generates the `number`, `switch` and
`select` descriptions. So there is exactly one place a version-dependent
scale would have to be expressed.

**Which field to gate on, measured rather than assumed.** `sungrow_version_1`
is the one that tracks updatable firmware and the one the issue quotes. It
varies across the committed documents — `01011.95.03`, `.95.12`, `.95.13` —
and it read on **9 of 9**, where `inverter_firmware_version` read on only 5
because four documents refuse that block. ARM and DSP are constant across all
nine and, per that thread, identify hardware rather than firmware, so they
are the wrong thing to key on. `sungrow_protocol_version` is constant at
16781568 everywhere so far; it is semantically the *right* field if Sungrow
bumps it when meanings change, and there is no evidence yet that it does.

**What the mechanism should not be.** Not a fork of the register map, and not
a runtime `if` in a property. The honest shape is what `layout.py` already is
for padded frames: a small, explicit table of *deviations*, each carrying the
measurement it came from — field, the version range it applies to, and the
scale or unit that replaces the default. Then a register keeps one definition
and the exceptions are enumerable, reviewable and testable, instead of the
map meaning different things depending on where you read it.

**And it is blocked on evidence, not effort.** Every measured machine reads
13073 in watts and matches its own maximum at 5622 — 10000 on the 10 kW
machines, 8000 on gerd's 8 kW one, 24990 on fwitten's — so the deviation has
never been observed here. Worse, the two explanations in the thread are
indistinguishable from the reports so far: "0.1% of rated power" and "units
of 10 W" predict the same number on a 10 kW inverter, and every reporter
appears to have one. Writing a version-gated scale on that basis would be
guessing in the one place the integration *writes to somebody's inverter*.
What is needed first is in
[devices-wanted.md](device-fingerprints/devices-wanted.md) — a survey from a
machine on `.95.14` or later, ideally one that is not 10 kW.

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

### The `_raw` sensors, and what a user should have to know

Twelve entities end in `_raw`. They are the register's own number, before
anything interprets it: `running_state_raw` is a bitfield, `backup_mode_raw`
is 170 or 85, `ems_mode_selection_raw` is 0, 2 or 3. The review's verdict is
that a user should never meet any of that — a person wants to know whether
backup mode is on.

What is actually there, measured against the descriptions rather than assumed:

| | Count | What they are |
| --- | --- | --- |
| Already have a friendly form | **8** | `backup_mode_raw` / `switch.backup_mode`; `running_state_raw` / the decoded `Running state`; `export_power_raw` / `Export power`; and the three mode selections beside their `select`, plus two switches |
| Are the **only** exposure | **4** | `active_power_limitation_raw`, `active_power_limitation_ratio_raw`, `apl_shutdown_at_zero_raw`, `pv_power_limitation_raw` |

All twelve are already `EntityCategory.DIAGNOSTIC`, so Home Assistant files
them under Diagnostic on the device page and keeps them off dashboards and out
of auto-generated areas. The user is not being shown them; they are being
*offered* them.

**The constraint is the migration, not the design.** All twelve exist in the
YAML package — `sensor.running_state_raw` and the rest — so a user who has run
it for years has history keyed to those ids. Legacy mode must keep creating
them; anything else stops that history dead, which is the one thing this port
promised not to do.

So the recommendation splits by mode:

- **Legacy mode: keep all twelve, unchanged.** Non-negotiable.
- **Modern mode: keep them, `entity_registry_enabled_default=False`.** They
  stay in the registry, so a diagnosis can enable one in two clicks and an
  existing automation that references one keeps working when enabled; a new
  user never sees them. This costs nothing to build and nothing to reverse.
- **Give the four without a friendly form one**, and then their raw twin is
  redundant like the other eight: two power limits are `number` entities
  already described in `scripts/writes.py`, the APL shutdown flag is a
  `binary_sensor`, and the ratio is a plain percentage sensor.

The alternative — deleting them in modern mode — is the wrong shape of
decision to take now: it cannot be undone for somebody who has already
migrated, where disabling by default can.

### Ten names, shared by more than one entity

Found by regenerating the review sheet after the unit fix, and it is the same
class of thing as the `_raw` decision above. On one device, Home Assistant
will show these names two or three times over:

| Name | Entities | What they actually are |
| --- | --- | --- |
| `Battery max SoC`, `Battery min SoC`, `Battery reserved SoC for backup`, `Battery max charge power`, `Battery max discharge power`, `Battery charging start power`, `Battery discharging start power`, `Battery forced charge/discharge power` | a **`number`** and a **`sensor`** each, 8 pairs | The same register, settable and readable. A `number` already displays its value, so the sensor beside it is redundant |
| `Export power limit` | `number`, `sensor`, **and** `switch.export_power_limit_mode` | A value, a read of that value, and the on/off that enables limiting at all |
| `Load adjustment mode` | `select.load_adjustment_mode` and `switch.load_adjustment_mode_enable` | The mode, and the on/off that enables it |

**None of this was introduced by the convention** — every one of those names
is what the YAML package calls the same entity, and the YAML has both
`number.battery_max_soc` and `sensor.battery_max_soc` too. It is inherited,
and legacy mode has to keep inheriting it.

Two things follow, and the first is already decided in spirit:

1. **Modern mode drops the eight read-only sensors that duplicate a
   `number`.** Same reasoning as the `_raw` removal, same clean cut: the
   number shows the value *and* sets it, so the sensor is a second copy of
   the first. Legacy mode keeps both, as ever.
2. **Both switches are renamed** (2026-09-09), because a switch sharing its
   name with the value it gates is unreadable in a list:
   - `switch.export_power_limit_mode` → **Export power limit mode**
   - `switch.load_adjustment_mode_enable` → **Load adjustment**

   `Export power limiting` was proposed first and rejected on the evidence:
   the three names in this map that end in `-ing` — Battery charging, Battery
   discharging, PV generating — are all **binary sensors** meaning "this is
   happening right now", so an `-ing` switch would read as something observed
   rather than something toggled. A switch named for the mode register it
   writes is already the pattern here — `switch.backup_mode` is "Backup
   mode" — so this follows it, and the number keeps the name a user looks
   for. `test_the_ing_ending_is_reserved_for_things_that_are_happening` holds
   the line.

The convention now enforces it mechanically, the way it already enforces one
spelling of SoC: **no two entities a user sees may share a name**, asserted
against the committed `strings.json`. Scoped to what modern mode creates,
because legacy mode reproduces the YAML's duplicates on purpose — and with
the seventeen `legacy_only` sensors excluded, **139 entities carry 139
distinct names**.

### Working out the topology

A user cannot answer *"which inverter is at 192.168.176.29?"*. They have never
thought about it, the addresses came from DHCP, and on a roof the two units
look the same. So the flow has to determine the shape itself, and every part
of it is measurable. This is what the four surveyed houses show.

**The identity is the serial, and only the serial.** Two endpoints reporting
the same serial are one inverter reached two ways, not two inverters. That is
the condition that produced two withdrawn documents before it was checked, and
it is now measured at three of the four sites — gerd (cable and dongle), bar12
(two dongle interfaces) and fwitten, whose four addresses are **two**
inverters:

| Inverter | Serial | Endpoints | Battery |
| --- | --- | --- | --- |
| A | `…234` | `.34` unit **1** direct, `.28` unit **1** dongle | unit **200** direct, unit **2** through the dongle |
| B | `…237` | `.29` unit **2** direct, `.32` unit **1** dongle | none of its own |

**A slave inverter is one whose own device address is not 1.** Inverter B
answers at unit 2 on its *own* endpoint, because a Sungrow cluster slave is
configured with device address 2. So the address is the role: address 1 is a
master or a standalone inverter, anything else is a cluster member. Which also
means the flow must probe unit 1 **and** unit 2 for an inverter, or a house
whose slave has its own dongle looks like a house with one inverter.

**"Unit 2" means different things at different endpoints of one house.** At
fwitten's `.28` unit 2 is inverter A's battery, forwarded by the dongle; at
`.29` unit 2 is inverter B. The discriminator is already built and measured:
a device type code at 4999 answers for an inverter and not for a battery —
`sungrow_modbus.battery.probe_units` and its tests. A reading of *zero* there
is not an inverter either, because a device answering zeros for everything is
what a dongle does for what it does not forward.

**A cluster member has no hardware of its own, and says so in zeros.** The
slave answers 0 for battery voltage, level, temperature and capacity where a
lone inverter answers 0xFFFF — measured on this pair, and the reason
`ZERO_MEANS_ABSENT` exists. So the flow must not attribute the master's
battery to the slave.

**But a dongle hides the address, so role-from-address only works on a
cable.** Measured 2026-09-09 with `identify` sweeping units 1 to 5 against
all four of this house's endpoints:

| | Unit that answered | Battery capacity (5639) | Meter voltage (5741) |
| --- | --- | --- | --- |
| A, cable `.34` | 1 | 960 | present, 231.8 V |
| A, dongle `.28` | 1 | 960 | **refused** |
| B, cable `.29` | **2** | 0 | unavailable, 0xFFFF |
| B, dongle `.32` | **1** | 0 | **refused** |

Inverter B's own device address is 2, and its **dongle answers as unit 1
anyway**. So "the address is the role" holds only for the endpoint that is a
direct connection; through a WiNet-S every inverter presents as unit 1
whatever it is configured as. And the meter, the other obvious
discriminator, is refused through a dongle on *both* machines — 5741-5746
are among the measuring points a WiNet-S does not forward.

That leaves a real gap: **a house whose two inverters are each reachable only
through their own dongle cannot have its roles read off the wire at all.**
Two endpoints, two serials, both unit 1, both refusing the meter. The one
signal that survives the dongle is battery ownership — 5639 reads 960 on the
master and 0 on the slave, forwarded in both directions — and that is an
inference about what a machine *has*, not what it *is*. A cluster whose
battery sat on the slave would defeat it.

**And there is no role register.** Looked for one rather than assumed: the two
machines' full dumps on the same transport were diffed, 1510 addresses each,
with the master's own four-hour-apart pair used to exclude anything volatile.
80 addresses differ, 29 of them stably — and every one of the 29 is explained
by what the machine *has* rather than what it is: battery capacity, state of
health, total charge, running state, the meter block. Nothing that reads like
a role, a cluster index or a member count.

So the conclusion for the flow is the one already reached for the name, and
for the same reason: **infer, present, and let the user correct it.** The
inference is strong where a cable exists and weak where only dongles do, and
the flow should say which — "device address 2, so a cluster slave" is a
measurement, while "no battery of its own, so probably the slave" is a guess
worth showing as one.

So the algorithm, per endpoint found by the sweep:

1. Read the serial and device type code at unit **1**, then at unit **2**.
   Each distinct serial is one inverter; its **device address** is its role.
2. Probe unit 200 and unit 2 for a battery, discriminating on the device type
   code. Probe units 3 and 248 for a wallbox.
3. Group endpoints by serial. Where one inverter has two, **prefer the direct
   path**: measured twice, a cable forwards 1461 of 1510 dumped addresses and
   answers all 27 block reads, where the dongle forwards 1020 and refuses two
   blocks. Offer the other path rather than hiding it — some houses only have
   the dongle.
4. Present what was found in terms the user can *verify against the hardware*:
   the model, the **serial** (it is printed on the unit's label, and is the
   only identifier somebody can walk up and check), the address, the role, and
   what is attached. Then ask the one thing measurement cannot supply: what to
   call each one. `Roof` and `Garage` are what a dashboard wants, and neither
   an address nor a serial will ever mean anything to the person reading it.

**Naming, and why asking beats deriving.** Today the entry title is
`inverter.model` (`config_flow.py:396`) and `DeviceInfo` carries no `name`, so
two SH10RTs both become "SH10RT" and Home Assistant appends `_2` to whichever
was set up second: `sensor.sh10rt_total_dc_power_2`. The suffix records click
order and nothing else. Deriving something better — the serial's last four,
the address tail, `inv 2` as the YAML package does — fixes uniqueness and not
legibility: `sensor.sh10rt_0234_total_dc_power` is unique, permanent, and
still does not say which roof. So the flow asks, once, only when it has found
more than one inverter, having first shown the user everything it knows about
each. The answer becomes the device name, and therefore the entity ids, and
therefore what the history is keyed to for good.

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

Three further mechanical checks come with it: every `translation_key` an entity
description names exists in `strings.json` and nothing in `strings.json` is
orphaned; no two names slugify to one entity_id — which is how the registry
silently appends `_2` to whichever entity registered second; and each
`translations/*.json` carries only keys `strings.json` has, with `en.json`
required to be complete because it is the source. A translation *missing* a key
falls back to English harmlessly; one carrying a key that no longer exists is
dead weight that reads as maintained, and neither shows up in the UI or in
review. Hassfest validates the shape of these files but never compares them,
because core's translations come from Lokalise and cannot drift. These do not.

**The writable platforms are held to the convention too, since milestone 3
landed.** They carry the worst of the YAML's names (`Battery Max Soc`,
`Battery Reserved SoC for Backup`) and comply. Adding them exposed a flaw in
the test rather than in the names: it keyed descriptions by their key, and the
YAML names the same concept in two domains — `battery_max_soc` is a sensor
that reads the register and a number that writes it — so one of each pair was
being dropped before it was checked. Five entities. Now keyed by entity_id,
which is the same lesson `migration.py` learned about `(platform, key)`.

### Poll intervals are a setting

**Built (2026-09-07).** Four groups, each with its own interval, configurable
in the options flow from 5 seconds to never.

This is the most useful knob the integration has, and the reason is
contention rather than bandwidth. A Sungrow accepts very few Modbus sessions
at once; when something else polls the same inverter — the YAML package,
another Home Assistant, EVCC, a logger — the two compete for one, and that is
what most reported dropouts turn out to be. It is also what broke the
maintainer's own first setup attempt. Slowing a group down, or switching it
off, is the cheapest fix available, and data nobody looks at is the cheapest
thing to stop reading.

Three decisions worth keeping:

- **Tiers are named, not keyed by interval.** They used to be
  `{5: (...), 10: (...)}`, which cannot survive the interval becoming a
  setting: slowing the fast group to 60 seconds would have merged it with the
  medium one.
- **5 seconds is the floor.** The specification warns that writable registers
  must not be polled frequently through a WiNet-S, WiNet-S2 or Logger1000, and
  5 seconds is already the fastest the YAML package ever used. Lower spends a
  connection the inverter has few of and buys nothing. `0` means never.
- **Never means no coordinator and no entities**, rather than entities that
  are permanently unavailable. Turning every group off is refused outright —
  an integration with no entities at all is a bug report, not a setting.

A derived value still follows the **fastest group it actually reads**, which
is now resolved from the configured intervals rather than the defaults: slow
the realtime group below the fast one and `export_power` moves to the fast
one, because otherwise it would visibly lag the sensors it is computed from.

The step's description carries a markdown table of what each group contains
and how many registers that is, because four bare numbers cannot answer the
question they raise — what am I slowing down? A config-flow form has no table
widget, so it goes in the description.

#### Moving a register between groups — decided, parked (2026-09-07)

⬜ **Deliberately deferred, not dropped.** Parked in favour of write parity;
the design is settled so it can be picked up without re-deciding anything.

Feasible, and verified rather than assumed: a field descriptor can be lifted
into a dynamically built `Component` class, and both the original and the new
class keep reading correctly. What it needs is the component set built **per
config entry** instead of taken from the module-level `COMPONENTS`, which
touches the device, the coordinator, the entity wiring and diagnostics.

Settled by the maintainer:

1. **Granularity: by register.** Every register individually, not a curated
   subset.
2. **Presentation: one screen.** The whole table at once, not a menu of groups.
3. **Defaults come from the register descriptions**, and the table shows what
   the default is per row — so a user can see where they have diverged, and
   put it back.

The cost to surface in that table, because it inverts what somebody reaching
for this setting expects: the library pools neighbouring registers into single
reads, so moving one out of a **tight** block splits it and costs two reads
where it cost one. Measured on the current map, moving `total_pv_generation`
out of `slowest` costs one extra read and does not split anything, because
that block already spanned 46 registers — but the number is computable, so the
table should show **reads**, not only register counts, and say what a move
costs before it is made.

There is a second cost, discovered the hard way on 2026-09-07 and worth
knowing before this screen is designed, because it points the opposite way. A
`Component` either updates or raises, so **every register sharing a read
shares its fate**: two firmware strings the reference inverter answers with a
length of their own choosing failed the whole 58-register `slowest_input`
request, and 36 unrelated entities had never once had a value. Pooling is
strictly better for the wire and strictly worse for blast radius. So a register
moved into a tier of its own is not only slower to fetch — it is also *safer*,
and a user who moves a register because it keeps failing is doing something
reasonable rather than something the table should discourage. `scripts/layout.py`
records the registers where that trade has already been made by hand, and is
the honest answer for a register proved bad; this screen is the answer for a
user who suspects one. They should agree about what a tier means.

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

Two things this replaces: `scripts/sungrow_scan/portable.py` stays, because it
runs without Home Assistant and before the integration is installed, which is
what a first-contact report needs. And the "one-click feedback upstream" idea
is now cheap — a diagnostics file is already the payload.

### Verified against real hardware (2026-09-07)

Milestone 3 shipped having only ever written to a simulator. Run against the
reference SH10RT over direct LAN, at about 2 ms round trip:

- **The write path works.** `battery_min_soc` read 10.0 %, was written
  11.0 %, **read back 11.0 %**, and was restored to 10.0 %. Function code 6,
  the 0.1 %-per-count scale and the read-after-write are correct on hardware,
  not only against a mock.
- **The inverter range-checks, and says so properly.** Writing 70 % — above
  the specification's documented 50.0 % maximum — returns **Modbus exception
  0x04** on function code 6. `modbus-connection` raises that as
  `ServerDeviceFailureError`, a `ModbusError` but *not* a
  `ModbusConnectionError`, so it surfaces as "Could not write …" rather than
  being mislabelled as contention. The entity refuses out-of-range values
  before sending anyway, so this is the second of two guards.
- **Registers 33149/33150 exist after all, and take a write.** The two held
  back because V1.1.11 does not document them read `[20, 10]` — 200 W and
  100 W at the YAML's scale, exactly what "charging/discharging start power"
  should look like, six reads out of six. The YAML's addresses are right and
  the registers are real; they are simply absent from this revision of the
  document.

  **Released by the maintainer on 2026-09-07** and round-tripped on hardware,
  each register separately: written back unchanged, then one step up (200 →
  210 W, 100 → 110 W), read back at the new value, and restored — with both
  confirmed at 200 W and 100 W afterwards. `UNCONFIRMED` is now empty, and
  kept rather than deleted so that shrinking it stays a deliberate commit.
  `Capability.BATTERY_START_POWER` still gates them, because they are reported
  absent on SHxRS (issue #743) and nothing is known about other families.

  Two of the three writes needed a retry. Each operation was given its own
  connection, its own retries and a restore in `finally`, and the restore is
  what mattered: an earlier attempt lost the connection *during the restore
  write* and left the register at 210 W, which took a second pass to put back.
  Anything that writes to this inverter has to assume the link will drop
  between two of its steps.
- **Contention, again.** A first attempt died mid-way with "Connection lost"
  on a perfectly good block while the production instance was polling. The
  restore ran from its `finally` and put the setting back, which is why it was
  written that way.

### Telling one connection from another

Users mostly do not know how their inverter is attached, and reasonably
confuse a WiNet-S with the inverter's own LAN port — so it is **worked out
from two signals the specification gives**, not asked:

- **registers 6100-6195** are documented "WiNet-S/S2 and Logger is not
  supported", so if they answer, we are not behind one;
- **register 13265**, Communication Module Firmware Information, names the
  module if there is one. A direct-LAN inverter has none and returns the
  specification's UTF-8 unavailable, which decodes to an empty string.

Both agreed on the reference system, and both are recorded rather than only
the conclusion — the conclusion is a reading of them, and somebody may later
read them differently. Where they disagree, the verdict says so.

**WiFi versus Ethernet on a WiNet-S cannot be determined over Modbus.**
Settled on 2026-09-08 against the controlled case: bar12's SH10RT-20, one
dongle, read wired and then over WiFi. The structural diff is **nil** —
identical capability probe states, identical failed components, identical
fields filled, identical firmware strings. Nothing in the register space
moves.

Latency was the standing hypothesis and does not survive either. Across four
installations the direct-LAN medians span 2.0 to 61.5 ms and the WiNet medians
24.3 to 48.3, so they overlap — and gerd's direct link is *slower* than his
own dongle, because he reaches it over a VPN. Jitter fails too: the same
dongle spread 1.6 ms wired and 4.9 over WiFi, while another house's wired
WiNet spread 8.6. It measures the path between the client and the device, not
how the device is attached.

So the samples stay as evidence, `--transport` carries what only the owner
knows, and no code guesses. The sentence this replaces claimed "about 2 ms
with almost no spread" as a general fact and shipped inside every published
fingerprint for a week.

**Register 13265 reports what is attached, not the route taken.** gerd's
SH8.0RT names its WiNet-S on a reading taken through the inverter's own LAN
port, which is why a named module can never overrule 6100 — and why that
combination now gets a verdict of its own. Being on the direct path is worth
telling somebody about: the route they are not using forwards fewer measuring
points and answers zero where the inverter answers "unavailable".

### What a survey cannot tell you while something else is polling

Recorded on 2026-09-09, because it invalidated a set of readings and the
reason is not obvious.

Four scans were taken at a house over a VPN. The block read test reported
four blocks that "never answered" -- `meter_channel_2` and the three
15-register firmware strings -- and the summary recommended all four for
`scripts/layout.py`. Home Assistant was still polling the same inverters at
the time. So the readings are contention, or a register fault, and **the
measurement as taken cannot say which**. They are archived under
`.testdata/contended-ha-was-polling/` rather than published, and the four
scans re-taken with the YAML package stopped.

The uncomfortable part is that the tool did not flag it, and the reason is a
real defect rather than bad luck:

- **A regular poller does not look intermittent.** The fault-versus-contention
  rule is *fails in every round while its neighbours answer* -- and that rule
  assumes contention is a moment. Home Assistant's fastest tier polls every
  five seconds, indefinitely, so a competing read is not a moment: it is a
  state. Three attempts at one block can all land inside it and the block is
  then filed as a deterministic fault.
- **The survey uses the weaker of the two measurements it has.**
  `collect.py` calls `measure(attempts=3, rounds=1)`. `--rounds` exists for
  exactly this: `blocks.py`'s own help says three back-to-back reads can all
  land in the same busy moment, where three rounds with the other blocks in
  between cannot. The survey does not use it. Several rounds is the fix, and
  it costs the tally phase three times its length -- which on a slow link is
  minutes, against a wrong `layout.py` entry that is permanent.
- **The question is asked and the answer is testimony.** Phase 2 asks whether
  anything else is polling and the document records the answer under
  `user_inputs`, which is right -- but "no" was given here in good faith and
  was wrong, because stopping the YAML package is a separate act from
  believing it is stopped. Nothing verifies it, and nothing can: another
  client's reads are invisible from this end.

What follows, in order of how much it buys:

1. ✅ **Fixed.** `collect.py` runs **three rounds of two attempts** rather
   than one round of three -- six reads per block either way, spread instead
   of bunched. The tally phase costs three passes over the plan, which on a
   fast link is seconds; a wrong `layout.py` entry is permanent.
2. A block that fails every round should still say what it would take to be
   sure -- the survey knows it was told nothing else is polling, and can say
   that the claim is load-bearing for this finding.
3. ✅ **Fixed**, schema 16. `block_read_test` carries three lists kept
   deliberately apart -- `answered`, `never_answered`, `intermittent` --
   plus the narrowed ranges, how many rounds and attempts were used, and
   **which Modbus client read it**, since a refusal from the library client
   is a refusal the integration will also hit. Absent rather than empty when
   no test ran, and keyed on `command_line` in the test that enforces it:
   `collect.py` always runs one, the bare `capabilities` subcommand never
   does.
4. ✅ **Fixed.** The summary no longer recommends `layout.py` for a finding
   that cannot support it. A range the budget marked `not narrowed` now says
   it names no single register and prints the command that finishes it; a
   failure that only ever *timed out* says a timeout cannot tell a silent
   inverter from a lost answer. Both used to get the same sentence as a clean
   exception 0x02 -- which also asserted "read directly from the inverter, so
   this is the device refusing", and that does not follow: over a VPN the
   direct-LAN verdict is about the last hop, not the whole path.

5. ✅ **Fixed.** The summary says when a finding is already fixed. Re-taken with
   the YAML package stopped, the same four blocks failed 3 of 3 again -- so
   for these four it was not contention after all. But all four are already
   in `layout.ISOLATE`, from this same house on 2026-09-07, and the summary
   printed nine numbered recommendations to add what is already there. The
   isolation is in fact *working*: each of these failures now costs one field
   instead of a tier, which is the outcome the module exists for, and the
   survey reported it as an outstanding problem. `layout.py` is not in the
   zip, so the fact travels in `scan_plan.json` as `isolated` on the eight
   component entries that exist only because a field was moved out of its
   tier -- and the advice now ends "nothing to do", pointing at
   `doc/compatibility.md` instead, which is where another machine refusing a
   known-bad register actually belongs.

Worth keeping in proportion: none of this touches a *reading*. Values,
capability probes and the register dump are unaffected by who else was
polling -- a contended read is absent, not wrong. It is only the
fault-versus-contention verdict that is at stake, and that verdict is the one
thing feeding a permanent change to the register map.

And one thing this house does settle, because it is the same measurement
taken twice a day apart with the competing poller present and then absent:
these four blocks fail either way. Which of the two spellings they fail with
-- a closed connection on 2026-09-07, a timeout today -- moved between the
sessions, so the *spelling* is the link's and not the register's. The failure
is the inverter's.

#### The check came out negative, which is worth as much as a positive would

The two readings of this machine, forty minutes apart with Home Assistant
polling and then stopped, were compared leaf by leaf: 988 leaves, 122
differing, and **every one of them a live number** -- PV voltages, phase
voltages, meter current, the battery's own registers, the latency figures and
the timestamp. Every structural fact was identical: the same four missed
components, the same seven fields that did not read, the same capability
verdict on every probe including MPPT3/4 and the second meter channel, and
the same 816 addresses dumped with the same six bands unreached. Even the
latency medians agree -- 23.8 ms against 24.0 -- so Home Assistant's polling
did not measurably load the link either.

So the discarded readings were, in substance, right. Two things follow, and
the second is the one that matters:

- **Discarding them was still correct**, for a reason that has nothing to do
  with the values. Their `user_inputs.comment` says "with nothing else
  polling the inverter", and that was untrue when it was written. A document
  whose testimony is false should not be published whatever its numbers say,
  because the testimony is what a later reader weighs the numbers against.
- **A negative result is a result.** The concern was real -- a periodic
  poller does look like a fault to a single-round test, and that defect is
  still worth fixing -- but at this house, on this link, it changed nothing.
  Which means the four failing blocks are the inverter's, and the fix already
  in `layout.ISOLATE` is the right fix, now confirmed rather than assumed.

#### Settled: a dongle withholds the SBR's cell data, and it is packed

The open question from milestone 4 -- whether the per-module cell registers
are withheld by a WiNet-S or never populated by the pack -- is answered. One
SBR096 read both ways within seconds on 2026-09-09, on the inverter's own LAN
port at unit 200 and through its dongle at unit 2:

| Block | Cable, unit 200 | Dongle, unit 2 |
| --- | --- | --- |
| `SbrBatteryPack`, input 10740 x9 | reads | reads, identical values |
| `SbrBatteryCells`, input 10756 x8 | **reads true** | **exception 0x02** |

The pack populates them; the dongle loses them. And it loses them two
different ways across two dongle firmwares -- refusing here, answering
**zeros** at another house -- which is why `ZERO_MEANS_ABSENT` has to cover
this block and not only the inverter's own optional trackers.

**A second finding, which changes what these fields should become.** The four
`*_position` registers are not plain numbers. They pack a module and a cell
into one word, `(module << 8) | cell`:

| Word | Hex | Module | Cell | Source |
| --- | --- | --- | --- | --- |
| 780 | 0x030C | 3 | 12 | measured, max cell voltage |
| 266 | 0x010A | 1 | 10 | measured, min cell voltage |
| 770 | 0x0302 | 3 | 2 | measured, max module temperature |
| 257 | 0x0101 | 1 | 1 | measured, min module temperature |
| 518 | 0x0206 | 2 | 6 | legacy YAML's own comment |
| 788 | 0x0314 | 3 | 20 | legacy YAML's own comment |
| 514 | 0x0202 | 2 | 2 | legacy YAML's own comment |
| 257 | 0x0101 | 1 | 1 | legacy YAML's own comment |

Eight samples, two houses, nothing contradicting -- and then **proved from a
single reading**, which is worth more than the eight.

Reading the per-module registers alongside the pack's own makes the claim
checkable without appeal to another house. On this SBR096: module 1's highest
cell is 3.3507 V, module 2's is 3.3484 and module 3's is 3.3487. The pack's
own `max_cell_voltage` reads **3.3507** -- module 1's, the highest of the
three -- and `max_cell_position` reads 260, which is `0x0104`: module 1, cell
4. The minimum agrees the same way: pack 3.3436 V, which is module 1's, and
position 275 = `0x0113`, module 1, cell 19. Whichever module holds the
extreme the pack quotes, the high byte names *that* module. Cell 19 also puts
a floor under the twenty-cell claim.

The same reading counts the modules: the per-module registers for 4 to 8 read
0 and so do their cell types, so this pack is three modules -- 9.6 kWh at
3.2 each, which is what an SBR096 is, and why every high byte ever seen is
1, 2 or 3.

One thing still does not close: 60 cells at the measured 3.34 V comes to
slightly more than the 200.0 V the pack reports for itself, consistently
across two readings. Pack voltage is measured separately from cell voltage
and 0.1 percent is inside a BMS's tolerance, so it is noted rather than
explained. An SBR128 would add the last brick with a high byte of 4.

So the legacy package publishes a raw word and leaves the reader to work out
what cell 780 is. **Decided (2026-09-09): two values per position**, one for
the module and one for the index within it, because each is then a number a
template can compare and a dashboard can graph. A single `3-12` string would
have cost four entities instead of eight and been useless to a template; the
raw word is what `_raw` is banished from modern mode for.

Implemented in `SbrBatteryCells` as eight properties over the four registers,
which stay as declared fields because they are what is read and what legacy
mode reproduces -- legacy keeps the raw word, encoding wart and all.

One asymmetry came out of doing it, and it is why the eight are not named
alike. The high byte is the module in all eight samples. The low byte is not
the same thing in both pairs:

| Register pair | Low bytes seen | Named |
| --- | --- | --- |
| max/min **cell voltage** position | 6, 10, 12, 20 | `_number` -- a cell, of a module's twenty |
| max/min **module temperature** position | 1, 2, and only ever those | `_sensor` -- inferred |

A module with twenty cells and two temperature sensors fits both rows and
nothing contradicts it, but four samples of a field that only ever holds two
values is thin evidence for a name. So `_sensor` is marked as an inference in
the code, the raw word is kept beside it, and
`test_a_cell_index_and_a_sensor_index_are_told_apart_by_their_range` fails
loudly if a ninth sample ever holds a 3 there.

A zero word decodes to None on both halves rather than to module 0 -- the
registers are one-based, and zero is what one of the two dongle firmwares
returns for this whole block. Module 0 reported forever is the failure
`ZERO_MEANS_ABSENT` exists to prevent.

**Not yet entities.** The SBR is a separate device on its own unit and none of
it is wired to Home Assistant yet; that is milestone 4. What exists now is the
decoding, tested against all eight samples.

#### Discovery asks unit 1 and gives up, which loses a cluster slave

Found while scanning this house's **second** inverter at its own LAN port.
Phase 1 printed one line:

    192.168.176.29:502  no serial at unit 1 (ModbusTimeoutError)

and then phase 2 asked for the unit id with a default of 1. The device is at
unit **2** -- a cluster slave's own device address -- and the scan only
succeeded because the operator already knew that and typed it. A contributor
would have been told their inverter is not there.

`identify()` in `probe.py` hard-codes `connection.for_unit(1)` and returns as
soon as that read fails. It never tries the other units, although
`CANDIDATE_UNITS` right next to it lists 2, 3, 4 and 5 with what convention
says each one is, and `probe.py units <host>` already sweeps exactly that
list. So the knowledge is in the file; the survey's own discovery does not
use it.

This is the same requirement as the config flow's, met earlier in the
pipeline: *users do not know which address belongs to which inverter, so the
logic has to work it out.*

**Fixed 2026-09-09**, and verified against the house that found it:

1. ✅ `identify()` tries `IDENTIFY_UNITS` -- 1, then 2 to 5 -- and returns
   **which unit answered** in a new `Identity.unit`. Only the rare case pays:
   an address with an inverter on unit 1 makes exactly the two reads it
   always did.
2. ✅ Phase 2's unit prompt defaults to what answered, and says why when that
   is not 1, or the number reads as a mistake against the paragraph above it
   calling 1 usual.
3. The config flow reuses the same probe order, so a house like this one is
   discovered rather than reported absent. **Still to do.**

Measured after the fix, all five endpoints on that subnet:

| Address | Identified as | Unit |
| --- | --- | --- |
| `…34` | SH10RT-V112, serial A (cable) | 1 |
| `…28` | SH10RT-V112, serial A (its dongle) | 1 |
| `…29` | SH10RT-V112, serial B (cable) | **2** -- was "no serial at unit 1" |
| `…32` | SH10RT-V112, serial B (its dongle) | 1 |
| `…35` | **not a Sungrow at all** | none |

#### An open port 502 is not an inverter

The fifth address is the other half of the same lesson, and it was found only
because the /24 was swept rather than assumed. It refuses input 4989 on every
unit id with exception 0x02, **ignores the unit id altogether** -- units 1, 3,
247 and 248 all answer identically -- and answers only registers 0-19, with
small integers and gaps. Some other vendor's Modbus device on a home network.

So discovery cannot treat an open 502 as an inverter, which is what "identify
by what answers, never by unit id" means in practice. `identify` handles it:
no serial means no device, and the message names the **exception type**, so a
refusal is distinguishable from silence -- a distinction `scripts/layout.py`
now depends on.

Two things this rules out for that address, both worth stating because both
would have contradicted a measured rule: it is not a wallbox, which would
answer 21200 and does not, and it is not an iHomeManager, which lives on port
503 and unit 247 -- and a full sweep of the subnet on **port 503 found
nothing at all**. So milestone 5 still has no measurement anywhere, at any
house.
 Its two inverters are four
   endpoints between them -- `…234` at unit 1 on two addresses, `…237` at
   unit 1 on one and unit 2 on another -- and no register says which of the
   two is the master. What identifies a device is its serial; what a *role*
   needs is a comparison across endpoints, which is why identity has to be
   established for every target before any question is asked.

Cost of the extra probing: four reads against an address that answered
nothing at unit 1, which on this link is four timeouts. Worth it -- it is
paid once per address, and only where the first attempt failed.

#### A dongle answers with zeros where the inverter refuses -- strings too

The A machine at this house was read both ways within six minutes, cable then
dongle, with nothing else polling either time. The two paths fail
**complementary** sets of blocks, which is the clearest pairing measured so
far:

| Block | The inverter's own LAN port | Through its WiNet-S |
| --- | --- | --- |
| input 2612, 2628 (sub-controller, battery firmware) | read, 3/3 | **exception 0x02**, 3/3, narrowed to every single register |
| input 13249, 13264, 13279 (inverter, module, battery firmware) | **fail**, 3/3 | answer -- and decode to `""` |
| input 13199 (meter channel 2) | **fail**, 3/3 | answers |

The right-hand column of the middle row is the finding. Those three blocks
answer through the dongle and their strings come back **filled with 0x00**,
so `present()` in `model.py` maps them to None and the fields are absent
anyway. Same outcome by a different route: the cable refuses the read, the
dongle invents an empty answer for it.

This is the string-shaped case of a behaviour already known for numbers -- *a
WiNet-S answers 0 where the inverter answers 0xFFFF*, which invented MPPT3,
MPPT4 and a second meter channel at another house. It now has a second shape
and a third house. Two consequences:

- `present()`'s mapping of `""` to None is not a nicety, it is the guard that
  stops three firmware strings becoming three entities reporting nothing
  forever. It was already there, for the Sungrow-battery probe; this is an
  independent confirmation from a different register family.
- **A capability probe must not treat "the block answered" as evidence.**
  What the dongle proves it can do is answer, not know. Every string probe
  needs the emptiness check, and every numeric one needs
  `ZERO_MEANS_ABSENT`.

And the SBR's unit map moved with the transport for the **third** house
running: unit 200 answered on the cable and nothing at unit 2, unit 2
answered through the dongle and nothing at 200. Same battery, same six
minutes. That is the rule the config flow's device discovery depends on, and
it is now measured on three houses and two inverter models.

#### A dump's address count is not comparable across links

The other thing this pair exposes. The cable path dumped **816** addresses
with six bands unreached; the dongle path dumped the full **1510**. Read
naively that says a WiNet-S forwards nearly twice what the inverter's own LAN
port does, which is the reverse of the rule measured at two other houses.

It is the budget, not the transport. An address that answers costs
milliseconds; one that does not costs a whole 10-second timeout in the
single-read fallback, and on this link the slow band alone -- `input
13199+160`, five blocks of mostly-unmapped registers -- ate most of the 600
seconds. The dongle path is faster to *fail*, so it gets further.

`register_dump.bands_not_reached` is in the document, so the fact is
recorded. But nothing enforces reading it: any comparison of dump sizes
across two documents must check that list first, and a document with a
non-empty one cannot be used as evidence about coverage at all.

### Knowing what a firmware answers, since Sungrow will not say

Raised by the maintainer as the thing this plan most needed, and it is now
most of a milestone in its own right: *collect as many device fingerprints as
possible, structurally, because Sungrow publishes no release notes and the
register specification has been proven unreliable.*

Both halves of that have been demonstrated rather than assumed. The
specification says register 13018 exists from V1.1.10; one house answers it
and another does not. It says nothing about 2612 and 2628 refusing through a
WiNet-S, which they do at every house measured. It does not mention that a
dongle answers **0** where the inverter answers the specification's
"unavailable", which invented ten entities at one house before
`ZERO_MEANS_ABSENT` caught it.

So capability is measured, and the structure for measuring it exists:

- **One command**, [scripts/sungrow_scan/collect.py](../scripts/sungrow_scan/collect.py),
  which finds the devices, asks only what no register can answer, runs the
  block read test, reads every register in the map, dumps 1510 raw addresses,
  and writes a publishable document plus a private one. It ships as a **zip**
  a contributor runs on bare Python with nothing installed, proven end to end
  against the simulator.
- **A document schema that says what it measured**, at version 15, with the
  claims a person typed kept in `user_inputs` where they cannot be mistaken
  for readings. Nine documents from four houses are committed in
  [device-fingerprints/](device-fingerprints/), and
  [compatibility.md](compatibility.md) is generated from them with `--check`
  in CI.
- **Rules promoted out of the readings** once replicated, into `CLAUDE.md`
  and `scripts/layout.py` — and only from a measurement that can carry the
  weight: a range the narrowing budget cut short names no register, and a
  read that only ever *timed out* cannot tell a silent inverter from a lost
  answer.

**And the question itself is now generated, not asserted.**
[compatibility.md](compatibility.md) has a *What can be attributed to
firmware* section, built from the committed documents: it finds every pair of
readings that agree on model and transport and differ only in firmware, and
reports which capability probes moved. Where no such pair exists — which is
where the corpus is today — it says so and names the reading that would
create one, per model, rather than asking generally for more data.

That distinction is the useful part. The most valuable contribution here is
**not a new model**: it is a second reading of a model already recorded, on a
different firmware, and nothing about a wanted list makes that obvious.

What is still thin is coverage. Nine documents, four houses, and **four**
inverter models between them — SH10RT, SH10RT-20, SH10RT-V112 and
SH8.0RT-V112, every one of them a three-phase RT. There is **no measurement
at all** of an iHomeManager, a Logger, an SBH pack, a single-phase inverter,
or any SH-series hybrid outside the RT family.

Firmware coverage is better than it first looks, and the correction is worth
recording because it was made from reading one field instead of five: the
documents carry **two inverter firmwares** (`B001.V000.P020` and `P022`),
**two WiNet-S firmwares** (`P040`, `P043`) and **two SBR BCU firmwares**
(`22011.01.27`, `.30`). Only the ARM and DSP strings have never varied. So
the 2612/2628 dongle rule is not a single-firmware observation — it holds
across two of each, which is most of why it is stated as a rule.
Every one of those is a capability question this project currently cannot
answer, and the survey exists so that one contributor with the hardware
settles it in twenty minutes.

### Fingerprints: one file, and a name that identifies nobody

One document per setup rather than the previous `capabilities` plus
`readings`, which carried the same register labels twice. It gains the
**firmware versions**, because which registers a device answers moves between
versions and two fingerprints are only comparable if both say which firmware
they were taken on; the **connection verdict and its evidence**; and
`reporter`, which defaults to **anonymous** because a fingerprint is worth
having either way.

The filename is derived from capability facts plus six hex characters of the
serial's hash — `sh10rt-3p-mkaiser-373233-battery-thirdparty-meter`. Hashed from the **real** serial rather than from the stand-in, so that changing how the stand-in is written never renames anybody's files again; it did once, which is how the coupling was noticed.

**The wiring is named only when it is unusual**, which is worth explaining
because it looks like an inconsistency. 3P4L — three phases and a neutral — is
an ordinary domestic supply, and spelling it out said "normal" on every
filename. 3P3L must be named, and the register table says why:

```
22. A-B line voltage / phase A voltage   5019  U16  0.1V
    Refer to Output type (address: 5002)
    0: phase voltage; 1: phase voltage; 2: line voltage
```

With no neutral there is no phase-to-neutral voltage, so on 3P3L registers
5019-5021 carry **line** voltages, about 1.73× higher. Same registers,
different measurement.

**Which is a latent correctness issue, recorded rather than guessed at.** Both
3P4L and 3P3L resolve `THREE_PHASE` and get the same entities, and those
entities are named `Phase A voltage` for everybody. On a 3P3L inverter that
name — and `phase_a_power`, computed from it — describes a line quantity.
Nobody has 3P3L hardware to test against, so
[capabilities.py](../src/sungrow_modbus/capabilities.py) states it next to
`OUTPUT_TYPES` and a fingerprint from such a system is what would unblock it.

`w` is used rather than the specification's `L` because a lowercase L beside a
digit reads as a one: the first person to see `3p4l` read it as "forty-one". It used
to default to the **serial number**, falling back to the host, which are the
two things the publishable file exists not to carry. Six hex is 24 bits: two
same-shape setups collide 0.7 % of the time by the five-hundredth fingerprint,
where ten *bits* would collide essentially always by the hundredth. The hash
comes from the stand-in rather than the real serial, so no new derivation
exists and the filename can be verified from the published file alone.

**The battery word has six states, all prefixed `battery-` so they read as
one field, and the awkward one carries the design.** `battery-sbr` or
`battery-sbh` when unit 200 answers and the reported capacity matches a
datasheet model — the family only, since the size would be a claim the
capacity does not quite support; `battery-sungrow` when unit 200 answers but
the capacity does not. `battery-thirdparty` when unit 200 is silent *and the
connection is direct*, because unit 200 would have answered. `battery-unknown`
for the same silence *behind a dongle*, because the specification puts the
per-module block at unit 200 only on a direct path — "the battery
communication address will be the WiNet internal forwarding address" otherwise
— so there it is no evidence at all, and calling it third-party would be
inventing a fact. Plus `battery-none` and `battery-unreadable`.

Capacity is consulted only after unit 200 has established the pack is a
Sungrow one, and the reference system shows why: the Pylontech reports **0**
there, so capacity alone would call a 14.4 kWh pack no battery.

**A battery's make cannot be read.** Nothing in the specification exposes a
type, brand or manufacturer register, so Modbus distinguishes a Sungrow pack
from a third-party one — the per-module block at unit 200 answers or does not
— and no more. The make is free text, recorded as
`user_inputs.battery`.

### Knowing who uses it, and what they have

**Install counts are free and already public.** Home Assistant's own
analytics reports `{domain, version}` for every custom integration when the
user has opted into usage analytics, and the aggregate is published at
[analytics.home-assistant.io/custom_integrations.json](https://analytics.home-assistant.io/custom_integrations.json)
— 4,242 integrations as of 2026-09-07, with a per-version breakdown. Once
`sungrow_modbus` is released it appears there with no work and no phone-home.

Two things that follow from actually reading that file:

- **The YAML package is invisible to it.** Analytics sees custom
  *integrations*; a YAML package reports nothing. Releasing this would be the
  first time this project has any install number at all.
- **`sungrow` has 522 installs** — which retroactively settles the domain
  rename. That name is genuinely occupied by somebody else's integration.

For scale on the same data: `solarman` 9,912, `huawei_solar` 5,988,
`solaredge_modbus_multi` 2,879, `solax_modbus` 2,822, `foxess_modbus` 1,168;
the median custom integration has 20.

**Setup detail has to be consented to, and is.** Analytics stops at domain and
version — nothing reports models or topology, and an integration that sent
that unasked would breach Home Assistant's rules and this project's own
position on privacy. So it is user-submitted, through three pieces that now
exist:

1. **The diagnostics download**, which carries no serial number, no host
   address and **no timestamp** — which is precisely what lets a user attach
   it to a public issue without a private channel existing at all.
2. **A structured issue form**,
   [compatibility_report.yml](../.github/ISSUE_TEMPLATE/compatibility_report.yml):
   model, inverter count, transport, battery type and size, meter, wallbox.
   Transport is asked for because the specification warns some measuring
   points are not forwarded over a WiNet-S, so the same inverter answers a
   different subset depending on the route in.
3. **[doc/compatibility.md](compatibility.md)**, generated from the committed
   fingerprints by `scripts/generate_compatibility.py`. It reports only what a
   fingerprint contains: a model with none is listed **untested** rather than
   assumed to work, because "probably fine" is the claim that wastes a user's
   evening.

### Who may change what

Home Assistant's permission model is real rather than decorative:
`helpers/service.py` enforces `POLICY_CONTROL` on every entity service call,
and the three built-in groups have genuinely different policies. What it has
**no** interface for is per-entity policy — expressible in the auth store's
format, but only by hand-editing `.storage/auth`, which is not something to
document for users.

So the ladder an installation can express is coarse, and the shape each
control takes is what decides where it sits. Settled, and asserted in
[tests/test_permissions.py](../tests/test_permissions.py):

| Group | Readings | Settings (SoC, EMS mode, limits) | Start/stop |
| --- | --- | --- | --- |
| admin | yes | yes | **yes** |
| normal user (`system-users`) | yes | **yes** | owner's choice |
| read-only (`system-read-only`) | yes | no | **no**, either way |

The middle row is the decision. A normal user may change every entity this
integration has — the maintainer's call, and the right one: the state of
charge limits and the EMS mode are settings a household member may reasonably
adjust. Stopping the inverter is not an entity at all, so its audience is
ours to decide — and **since 2026-09-07 it is the owner's**, in
*Options → Permissions*, defaulting to administrators only. **A `button`
could not have been gated at all**, which is the concrete reason start/stop is
an action.

Three things about that setting are deliberate, and each is asserted:

- **It is per config entry.** One entry is one endpoint, and a household may
  have two inverters with different answers. That is why the check is not
  `async_register_admin_service` — a service belongs to the integration, and
  its admin flag could only ever have one value for the whole house.
- **"Users" means users who can already control this device**, checked with
  `access_all_entities(POLICY_CONTROL)` — the same permission that decides
  whether they could change the minimum state of charge. Without that check
  the option would hand start/stop to a read-only account, because Home
  Assistant applies `POLICY_CONTROL` to entities and **not** to actions: a
  plainly-registered service has nothing behind it.
- **A call with no user is allowed**, which is core's own rule in
  `_async_admin_handler`. An automation or a script's own trigger acts for the
  household rather than for a person, and an automation an admin wrote must
  not stop working the moment it next runs on a schedule.

**What this page deliberately does not offer is a per-setting permission.**
Home Assistant authorizes entity control centrally, before any integration is
asked, so the integration cannot restrict the export limit to admins while
leaving the SoC limits open — not without enforcing it itself in the entity's
setter, which is possible (`entity.async_set_context` runs before the
coroutine, so the calling user is readable) and was rejected: the control
would still appear in every dashboard and picker, looking available, and
refuse on use. The supported answer is the read-only group, and the
Permissions screen says so rather than leaving somebody hunting for a setting
that cannot exist.

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

### The preview phase, and what a rename costs during it

The first releases are for testers, and are labelled so in three places
because three different people read three different things:

| Where | What it says | Who sees it |
| --- | --- | --- |
| The version | `0.1.0a1` — a PEP 440 pre-release, which `pip` will not install without `--pre` | a machine, and anybody reading the tag list |
| `manifest.json` / `hacs.json` name | "Sungrow Modbus (preview)" | somebody about to install it |
| A repair issue, `preview_release` | one paragraph in Settings > Repairs | **somebody already running it** |

Only the third reaches an existing install, which is why it exists at all;
[scripts/sync_version.py](../scripts/sync_version.py) accepts only the
normalised spellings (`0.1.0a1`, `b1`, `rc1`) and rejects `0.1.0-alpha.1` with
the reason, because pip would rewrite it and the manifest pin would then no
longer match what is installed.

**The rename policy.** During the preview, an entity name may still change.
That is cheaper than it was long believed here: a name supplies an entity id
at *creation only*, so a rename leaves an existing install's ids alone —
proven in
`tests/test_entity_naming.py::test_renaming_later_does_not_move_an_existing_id`.
What a late rename actually costs is **divergence**: a house set up in week
one and a house set up in week six answer the same question under two
different ids, which is a documentation and support problem rather than a data
one. So the rule for the preview is:

- A rename ships **with a registry migration** that moves the early ids onto
  the new name's id, in the entry's migration step, so the two converge.
- History follows the rename, raw and long-term both, per
  `tests/test_recorder_migration.py`. Nothing is copied and nothing deleted.
- Legacy mode is **out of scope for renames entirely.** Its ids are the YAML
  package's and reproduced byte for byte; nothing in this policy touches them.

Once the preview ends, the name is the id and a rename needs the migration
above plus a release note — the same mechanism, a higher bar.

### The library must be installable — proven, not yet released

`manifest.json` asks for `sungrow-modbus==0.0.1`, and Home Assistant
pip-installs `requirements` for **custom** integrations exactly as for
built-in ones. It works in the devcontainer only because `scripts/setup.sh`
installs it editable; **no HACS user has that**, since HACS copies
`custom_components/sungrow_modbus/` and not `src/`.

**Status (2026-09-06).** The whole path is exercised except the irreversible
step. `sungrow-modbus 0.0.1.dev1` was published to **TestPyPI** over OIDC by
[testpypi.yml](../.github/workflows/testpypi.yml) and installed from there
into a clean environment, so trusted publishing is confirmed working — the one
thing no amount of local testing could prove. `validate.yml` also builds the
package and runs `twine check --strict` on **every push**, so a package that
will not build is caught immediately rather than at tag time. What remains is
tagging `v0.0.1`, which claims the name on the real index.

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
4. Rehearse against TestPyPI first — **done, and it passed.** It needs its
   own account and its own pending publisher on test.pypi.org, naming
   `testpypi.yml` and the `testpypi` environment. Worth the ten minutes:
   trusted publishing fails in ways that only appear at upload time.
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
(done), and the HACS action and hassfest
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

### Repository layout

The YAML track lives under [legacy/](../legacy/) **on this branch only** — the
package, its generated variants, its dashboards, its tooling and its
documentation. On `main` it stays at the repository root, where every
installation instruction, forum post and issue says it is; renaming what
thousands of people download is a decision for the day the integration can
actually replace it, and it cannot write registers yet.

The move was recorded as renames, so history follows the files, and everything
that resolved a path rather than merely naming the file was repointed: three
generators, three workflows including the two that run inside the moved
directories, and the links in this document.

One trap it sprang, worth remembering for any future move: hatchling reads the
sdist's `include` entries gitignore-style, so a bare `"README.md"` matches at
every depth and the library's sdist quietly began shipping six of
`legacy/dashboards`' READMEs. The patterns are anchored with a leading slash
now, and `validate.yml` builds the package on every push, which is what caught
it.

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

`python scripts/sungrow_scan/probe.py capabilities <host> --save` records each one
as two files: a **fingerprint** saying which registers answered, and a **raw**
dump of the values. Only the fingerprint is shareable — the raw file carries
the serial number and live household readings, so it goes to a gitignored
`.testdata/` and stays there. The fingerprint has neither, which also makes it
stable enough to diff when firmware changes;
[doc/device-fingerprints/](fingerprints/) holds the committed ones, and the same
command is what to ask a user with an unknown model to run.

For the gaps rather than the known registers — the wallbox's undocumented
21231-21261 and 21267-21299 — `probe.py dump <host> --start N
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

## Appendix: what one session of measuring changed, 2026-09-09

Kept as a short list because the detail is in the sections that own it, and
because the pattern is worth seeing in one place: **almost everything here
came from pointing the tool at hardware, and several findings contradicted
what this repository already believed.**

Four houses' worth of readings, four scans discarded and re-taken, and:

| Found | Where it landed |
| --- | --- |
| A cluster slave answers on unit **2** at its own LAN port, and both the survey and the config flow asked only unit 1 — losing a whole inverter | `IDENTIFY_UNITS`, in two places |
| A **dongle presents its inverter as unit 1** whatever it is configured as, so the role is only readable on a cable | [Working out the topology](#working-out-the-topology) |
| **No role register exists** — 1510 addresses diffed per machine; all 29 stable differences are explained by hardware the slave lacks | the same section |
| An **open port 502 is not an inverter** — one of five endpoints was some other vendor's device | `identify` returns nothing rather than guessing |
| A **WiNet-S answers empty strings** where the inverter refuses the read — the string-shaped case of `ZERO_MEANS_ABSENT` | `CLAUDE.md` |
| The SBR's cell data is **withheld by the dongle**, two different ways across two firmwares — refusing at one house, zeros at another | [Milestone 4](#milestone-4--battery-modules--sbr) |
| The SBR's four position registers are **packed**, `(module << 8) \| cell` — proved inside one reading rather than inferred | `SbrBatteryCells` |
| Narrowing a failing block was **unbounded**, and cost a whole survey on a link where refusals arrive as timeouts | `blocks.NARROW_BUDGET` |
| A **timeout is not evidence** about a register, where an exception 0x02 is | `scripts/layout.py` |
| Port **516 on a WiNet-S is Modbus over TLS**, and works — reported elsewhere as an iHomeManager port, which it is not. Replicated at a second site on another dongle firmware, and its certificate looks shared across devices | `collect.py`, `CLAUDE.md` |
| A **fourth wallbox source** confirmed the status table and disagreed on a scale, which the reading settles | [wallbox_registers.md](wallbox_registers.md) |

Two of those were mistakes in this repository's own documents rather than
gaps: the claim that an SBR is "not reachable via WiNet-S at all", and the
claim that an entity name is impossible to change after release. Both were
written confidently and both were wrong, which is the argument for measuring
rather than reasoning — and for `tests/` holding whatever can be asserted.

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
