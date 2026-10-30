# Plan: replacing the YAML package with a Home Assistant integration

> Plan of record for the `proper-ha-integration` branch. What can be asserted
> is asserted in `tests/`; this file holds what is decided, what is next, and
> why. Measurements live in `device-survey/`, and what was learned on
> hardware in the wiki, `.wiki/wiki/index.md`.

## Status

| Milestone | State |
| --- | --- |
| 1 — foundations | ✅ |
| 2 — inverter read parity | ✅ read parity plus the V1.1.16 additions, capability gating, naming convention, migration, diagnostics, discovery |
| 3 — controls | ✅ numbers, switches, selects, start/stop as **actions**, and the **control test** (survey part B) |
| 4 — battery modules | ✅ **SBR**: own device, 40 registers, 17 entities. SBH needs its protocol document |
| 5 — iHomeManager | ⬜ never measured |
| 6 — wallbox | ✅ own device, 32 registers, 21 entities, read-only |
| 7 — third-party generation | ✅ two corrected sensors from another integration's entities |
| 8 — Sungrow Logger | ⬜ not started |

Released as PEP 440 pre-releases (`0.1.0aN`), named "(preview)" in both
manifests. The releases are **diagnostics-only**: `ONLY_SURVEY_MODE` in
`const.py` is on, so Add integration makes an entry that runs the survey and
creates no readings, promotion is greyed out, and the entity-id question is
never put. An existing devices entry still loads. Turning the flag off is the
whole re-enablement (`tests/test_alpha_gate.py`).

A release is `scripts/release/sync_version.py --set X`, a commit, an
**annotated** tag and `git push --follow-tags`; `release.yml` verifies the tag,
runs ruff, pytest, hassfest and the HACS action, publishes a GitHub
pre-release and the library to PyPI over OIDC. Run hassfest locally first
(command in `doc/maintainer_setup.md`).

## What is next

### Decisions for the maintainer

1. **When to offer the ordinary setup** (`ONLY_SURVEY_MODE`), and
   **when to merge into `main`.** The merge retires the preview channel and
   opens the HACS default store, which also needs the brand in
   `home-assistant/brands` (`scripts/helpers/make_brand_icon.py` draws it).
2. **Are the entity names final?** They are reviewed
   (`doc/entity_name_review.md`, `scripts/helpers/review_names.py`). A rename
   later leaves existing ids alone and only diverges new installs, which a
   registry migration can close -- so it stays cheap until release, not free.
3. **Adopting the opt-in SBR YAML sensors.** Ids like
   `sensor.sg_battery_1_max_voltage_of_cell` come from a copy-pasted file
   outside the package and are **not** adopted. Doing it would mean taking
   over entities this project never generated; the default stays "no".

### Blocked on evidence

4. **Firmware-dependent register semantics** ([#763]). The pattern is
   `capabilities.ABSENT_ON_FIRMWARE`: a small table of deviations keyed on
   the **whole** `sungrow_version_1` string (platform prefix included --
   `PEARL-H_01011.01.45` is not older than `SAPPHIRE-H_01011.95.03`), each
   citing the survey it came from. #763's deviation is 13074's write
   scale, which the per-device probe measures and stores with the firmware,
   so it needs no table entry; no committed survey shows another.
5. **A fault seen on hardware.** The fifteen words are read and decoded from
   V1.1.11's Appendix 4; one survey has a flag set (bit 30 of the inverter
   alarm, a slave with no meter), which confirms the word order. Still
   wanted: a reading during a real grid or battery fault, the battery words
   through a dongle, and V1.1.16's appendix compared bit for bit.
6. **iHomeManager (milestone 5).** Port 502 *or* 503, unit 247. Not a gateway:
   one endpoint, one device. `identify()` recognises it and the survey
   reads it (`sungrow_modbus.ihomemanager`, from Sungrow's V1.0.2 document,
   compared in
   [cross_reference_modbus_manager.md](cross_reference_modbus_manager.md)).
   Needs a survey from an owner, on a release that has the reader.
7. **Sungrow Logger (milestone 8).** Documented (*Logger Communication
   Protocol AW0 1.0.2.9*, not read here); fronts a whole installation, which
   is what the one-entry-per-endpoint model was built for. It does **not**
   forward battery data ("Logger is not supported" in the hybrid protocol's
   Note 2). The survey identifies one by its type code and reads it raw
   (`sungrow_modbus.logger`); a map needs the document and a reading.
8. **SBR per-module entities.** All 24 registers are read; an unfitted module
   answers 0 V, so the module count has to be established first. The
   encoding is a decision, not a migration. An SBR128 survey settles it.
9. **SBH.** Answers the SBR's common block at unit 2 with the SBR's scales;
    per-module arrays unread. Needs the register document.
10. **Meter phase voltage/current (5741-5746) on dongle houses.** Read zero
    through every WiNet-S measured and are gated on a non-zero voltage. Whether
    they need reading on their own (#756) needs a survey from an affected
    owner; `layout.py` changes only on measurement.
11. **T-series energy counters.** One SH20T reads 13045 (daily export) as 0
    while exporting, and 5003/5004-5005 duplicating the export counters. A
    second T survey, ideally on a cable, before `registers.py` changes.
12. **Modbus over TLS on a WiNet-S's 516.** Built for a wallbox's own
    address (`wallbox_host`, `links.wallbox_tls_params`). For the dongle it is
    worth building only if 516 is a *separate* session pool from 502 -- hold
    502 until it refuses, then try 516. Also wanted: a certificate hash from a
    third site, to show whether every dongle ships the same key.
13. **Does a WiNet-S advertise over mDNS?** Needs a house with a dongle and
    a run on the host, not in the container.

The most useful contribution is in
[devices-wanted.md](../device-survey/devices-wanted.md): a **second firmware
on a model already recorded**, the only comparison that separates firmware
from model.

## Rules that do not move

- **The integration never writes a register during setup or reload**, only on
  an explicit user action. A leftover control-test snapshot becomes a repair,
  not an automatic restore.
- **Devices are identified by what answers**, never by an open port or a unit
  id.
- **Nothing is removed from an existing install silently.** Capabilities grow
  an entry by reloading; they never remove an entity.

## Goals

| Goal | Concretely |
| --- | --- |
| **Backwards compatibility** | An existing user keeps their `entity_id`s, so history, dashboards, automations and InfluxDB carry on. The default for anyone with a YAML installation. |
| **Migration forward** | Modern device-scoped ids carry recorder history *and* long-term statistics, with no reset or spike on the Energy dashboard. |
| **Migration backwards** | Reversible both ways; an occupied target id is archived, never deleted. |
| **Honest backups** | The guide says what a backup covers — SQLite yes; MariaDB, PostgreSQL and InfluxDB no. |
| **Dashboards** | The Energy dashboard from known entities; a generated Lovelace dashboard on request. |
| **Third-party inverters** | A foreign inverter behind the same meter is added back into the load figure. |
| **Auto detection** | The user supplies a host, not a topology. Unknown devices are reported, not dropped. |
| **Every Sungrow Modbus device** | Inverter, wallbox, SBR and SBH, iHomeManager, Logger — sharing one serialized connection instead of an external Modbus proxy. |
| **All models, one map** | Model and wiring differences are capabilities, not forks. |

Not goals: nothing outside Home Assistant is rewritten automatically —
InfluxDB and Grafana get advice and a script (`scripts/helpers/influx_migration.py`).

## Decisions

- **Home Assistant 2026.9's Modbus architecture**: the integration asks core
  for a unit (`async_get_unit`), so everything on one host and port shares one
  serialized connection. Core's `sofar` is the reference.
- **A config entry is one inverter, reached through one endpoint at a
  time**, plus the devices discovered on that endpoint. Its unique id is the
  inverter's serial, so the same inverter is never set up twice; the
  endpoint is the owner's choice. **Reconfigure** moves the entry to another
  address once the same serial answers there, and **Add integration** that
  finds a configured inverter elsewhere offers the same move. Entity ids,
  history and settings stay; sub-devices are found again on the new
  endpoint; the survey's transport testimony is cleared. Two live entries
  for one inverter are deliberately not offered: both would poll a machine
  that grants very few sessions.
- **Register knowledge is a library without HA imports**, published to PyPI as
  `sungrow-modbus` (OIDC trusted publishing, no stored token).
- **Python `Component` classes are the register description.** `registers.py`
  is source, held field by field to `doc/legacy_entity_map.json` by tests.
- **The domain is `sungrow_modbus`** (`sungrow` is taken by another
  integration).
- **Entity ids are a choice at setup**: legacy ids for existing users, modern
  device-scoped ones for new users. Modern ids take the prefix from the device
  name: the model from the device type register, or, where the search found
  more than one inverter, a name the owner gives in setup (offered: the model
  plus the role, where a direct connection could read it).
  **The options page switches an entry either way** (`migration.async_plan_id_switch`):
  towards modern ids each series moves by rename; towards legacy ids an id
  that still holds the YAML package's history continues it, and the modern
  series stays under its own id. Rows already on a target id are renamed to
  `<id>_archive` first. An id the owner chose is left alone. A YAML orphan's
  restored `unavailable` state does not count as the package running; a live
  entity on the id refuses the move.
- **The config flow says each inverter's role and how it is known.** A
  device address other than 1 is a measured slave; its partner at address 1
  is the inferred master; through dongles only battery ownership survives,
  so a role built on it is "probably" and says so.
- **The fault and alarm words are counted, not split** (`inverter.faults`,
  from V1.1.11's Appendix 4). One diagnostic sensor per word reports how
  many named flags are set and names them in an `active` attribute; `Fault
  reported` and `Alarm reported` are the problem binary sensors to automate
  on. Reserved bits are never reported.
- **The diagnostics download carries the block read test, never runs it.**
  The survey button's last measurement goes in with its time; running one
  costs minutes through a dongle, and a download is waited on.
- **The `_raw` sensors exist in legacy mode only.** Modern mode exposes the
  decoded value (a binary sensor for an `0xAA`/`0x55` mode, a ratio with its
  unit); `Derived._mode_flag` returns None for anything else.
- **A parenthetical says what a value is**: `(smoothed)` for the moving
  average, `(delayed)` for the delayed binary sensors.
- **The naming rule is per device**, and one convention is enforced by test
  (`scripts/generate/tables/naming.py`).
- **Start and stop are actions, not buttons**, with an audience set per entry
  (admins only by default); the control test has an audience of its own.
  The YAML's danger-mode toggle and automations are not ported.
- **The wallbox is read-only.** No manufacturer document covers its map.
- **The opt-in SBR sensors keep no history**: partial adoption looks like a
  migration and is not one.
- **The integration offers a dashboard and asks first.** To do: nothing
  generates one yet.
- **Localisation follows Home Assistant**: modern ids take the interface
  language where HA says they should; legacy ids stay English. Only English
  ships.
- **13074's write scale is measured per device** (`sungrow_modbus.inverter.export_scale`)
  and stored with the firmware it was measured on.
- **Delivery is HACS first**, through the preview channel until the merge.
- **The brand mark is original**, not Sungrow's.

## The migration

The mechanism is settled and asserted in `tests/test_recorder_migration.py`,
`tests/test_migration.py`, `tests/test_legacy_slot.py` and
`tests/test_entity_id_switch.py`; `AGENTS.md` has the rules. In short: claim
the legacy `entity_id` at entity creation, so history continues with no
recorder API involved; modern ids are that plus one registry rename, which carries raw history and long-term
statistics. Every ported entity keeps the YAML entry's unit class and
`state_class`. A second inverter's `_inv_<n>` slot is detected from its serial
sensor -- live, else in the recorder's history -- and stored in entry data
(`CONF_LEGACY_SLOT`). Where neither matches, the slot is `""` only if no
numbered slot ever existed; otherwise it is stored as `None`, the entry
claims no legacy ids, and switching to them is refused until the serial can
be matched (`migration.async_resolve_legacy_slot`).

The user-facing order is fixed in
[integration_migration.md](integration_migration.md): back up and check the
backup covers the recorder; copy out the package's scenes and automations
that are wanted; remove the YAML package and restart; add the integration,
which releases the package's orphaned registry entries as it claims their
ids; verify a known sensor is continuous; then dashboards and Energy. A house
with several inverters adds each entry while the package still runs, so the
slot can be measured, and switches to legacy ids after removing it.

## Register sources

| Device | Map from | Licence |
| --- | --- | --- |
| Inverter | `legacy/modbus_sungrow.yaml` plus Sungrow's *Communication Protocol of Residential and Small Industrial Hybrid Inverter* **V1.1.16** | MIT, this repo |
| SBR battery | `legacy/additional_sensors/modbus_sungrow_SBR_battery.yaml`, input 10740-10788 | MIT, this repo |
| SBH battery | nothing yet | — |
| iHomeManager | Sungrow's *Communication Protocol of iHomeManager* V1.0.1/V1.0.2 and [ha-modbus-manager](https://github.com/TCzerny/ha-modbus-manager)'s 53-register map | MIT (ha-modbus-manager) |
| Wallbox | [evcc `charger/sungrow.go`](https://github.com/evcc-io/evcc/blob/master/charger/sungrow.go) and our own AC22E-01 measurement — [wallbox_registers.md](wallbox_registers.md) | MIT (evcc, KevinD987); Louisbertelsmann's used with permission, for meanings only |
| Logger1000/3000/4000 | Sungrow's *Logger Communication Protocol* AW0 1.0.2.9 and [discussion #262](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/discussions/262) | Sungrow's document |

The inverter map is audited against V1.1.16: every addition since V1.1.2 is
read, gated by a capability where the remarks column limits it, and marked
`layer: "specification"` in the entity map because it has no legacy id.
`DEVICE_TYPES` matches Appendix 1 (`tests/test_device_types.py`), and
`family_for` classifies by model name, not code range. **SH50-125CX is named
but not supported** (ten MPP trackers against a map that stops at four).
Compare registers on **space and address together** -- input and holding are
separate address spaces.

## Delivery

### Versioning

One version in `pyproject.toml`, mirrored into the manifest by
[scripts/release/sync_version.py](../scripts/release/sync_version.py) and
checked in CI, pytest and at release. `sync_version.py` accepts only the
normalised PEP 440 spellings (`0.1.0a1`, `b1`, `rc1`), and `release.yml`
marks those pre-release. `v*` tags are the integration; the YAML package keeps
its dated scheme.

### The preview phase, and what a rename costs during it

Testers are told it is a preview in three places: the version (`pip` needs
`--pre`), the "(preview)" name in `manifest.json` and `hacs.json`, and a
`preview_release` repair for somebody already running it. A rename during the
preview is a registry migration away, not a broken install.

### Where it is installed from

HACS resolves a repository to its latest stable release or its default branch,
and this repository's default branch is the YAML package. Until the merge, a
second repository whose default branch *is* the integration serves HACS,
synced by [preview-mirror/sync.yml](preview-mirror/sync.yml). It pulls rather
than being pushed to, so neither repository holds a credential, and it refuses
to publish a commit whose pinned library cannot serve it
(`scripts/release/check_pinned_library.py`). The live copy must stay identical
to this repository's; `validate.yml` checks it. `scripts/dev/hacs_testbed.sh`
installs from it the way a user does.

### Repository layout

The YAML track lives under [legacy/](../legacy/) on this branch; on `main` it
stays at the root until the integration replaces it. `scripts/` is grouped by
job — `dev/`, `generate/`, `release/` and `helpers/`. What a contributor is
handed is `device-survey/scripts/`: one launcher, `survey.{sh,cmd}`,
which reads and offers the control test at the end — and `doc/development.md` lists
every script.

## Documentation

Two products in one repo, so every page says which track it applies to. The
first-line documentation is `strings.json`: step descriptions and a
`data_description` per field.

| Page | To do |
| --- | --- |
| [installation.md](../legacy/doc/installation.md) | Add the integration: HACS, add integration, what discovery finds |
| [cleanup_entities.md](../legacy/doc/cleanup_entities.md) | Keep, linked from the repair as the manual fallback |
| [dashboard.md](../legacy/doc/dashboard.md) | Generated dashboard and Energy dashboard |
| [faq.md](../legacy/doc/faq.md) | The iHomeManager answer, once milestone 5 ships |

## The production testbed

The maintainer's instance has run the YAML package for years, and is the only
way to show history and statistics survive at scale. Collect from it
`home-assistant_v2.db`, `.storage/core.entity_registry`,
`core.device_registry`, `core.restore_state`, `.storage/lovelace*` and the
`modbus_sungrow.yaml` in use, into the gitignored `.testdata/` -- real
household data, never in the repo or CI. Run the migration against a copy and
assert a known sensor's history and statistics are continuous, and diff the
entity map against the real `unique_id` → `entity_id` map: any divergence is a
silent history-loss case. `scripts/dev/seed_migration_testbed.py` builds the
same situation on the dev instance for review in the GUI.

### Test systems

| Setup | What only this one proves |
| --- | --- |
| Reference: SH10RT, third-party battery, cable | The default development target |
| fwitten: two SH10RT-V112 (master/slave), SBR, cables and dongles | Multi-device, unit 2 slaves, the 1:1 write firmware |
| gerd: SH8.0RT-V112, SBR, wallbox, cable and dongle | The wallbox; cable against dongle on one inverter |
| bar12: SH10RT-20, SBR, cable and dongle | A second cable/dongle pair; writes allowed |

Two sites on the same subnet cannot both be routed; check before trusting an
address. `doc/maintainer_setup.md` has the access details.

[#763]: https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/763
