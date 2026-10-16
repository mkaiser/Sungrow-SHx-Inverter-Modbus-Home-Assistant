# Plan: replacing the YAML package with a Home Assistant integration

> Plan of record for the `proper-ha-integration` branch. What can be asserted
> is asserted in `tests/`; this file holds what is decided, what is next, and
> why. Measurements live in `device-fingerprints/`, and the rules learned
> on hardware in `CLAUDE.md`.

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
manifests. A release is `scripts/release/sync_version.py --set X`, a commit, an
**annotated** tag and `git push --follow-tags`; `release.yml` verifies the tag,
runs ruff, pytest, hassfest and the HACS action, publishes a GitHub
pre-release and the library to PyPI over OIDC. Run hassfest locally first
(command in `CLAUDE.md`).

## What is next

### Decisions for the maintainer

1. **When to merge into `main`.** That retires the preview channel and opens
   the HACS default store, which also needs the brand in
   `home-assistant/brands` (`scripts/helpers/make_brand_icon.py` draws it).
2. **Are the entity names final?** They are reviewed
   (`doc/entity_name_review.md`, `scripts/helpers/review_names.py`). A rename
   later leaves existing ids alone and only diverges new installs, which a
   registry migration can close -- so it stays cheap until release, not free.
3. **Adopting the opt-in SBR YAML sensors.** Ids like
   `sensor.sg_battery_1_max_voltage_of_cell` come from a copy-pasted file
   outside the package and are **not** adopted. Doing it would mean taking
   over entities this project never generated; the default stays "no".

### Work with no blocker

4. **13074 at fwitten.** Run `sungrow_control_test.py --export-scale` against
   the 1:1 firmware it was built for, and confirm a fresh install there sets
   up and probes correctly. Needs the VPN route into the devcontainer.
5. **Firmware-dependent register semantics** ([#763]). Built on the pattern
   `capabilities.ABSENT_ON_FIRMWARE` already uses: a small table of
   deviations keyed on the **whole** `sungrow_version_1` string (platform
   prefix included -- `PEARL-H_01011.01.45` is not older than
   `SAPPHIRE-H_01011.95.03`), each citing the fingerprint it came from. No
   forks of the map, no runtime `if`s in properties.
6. **Transport as three values in the scan scripts.** `probe._async_connection`
   and `sungrow_survey._check_transport` still publish a timed-out read of 6100
   as `"refused"`, i.e. a dongle. Add `"undetermined"`; it changes the
   document and `transport_verdict`'s truth table. The library's exception
   taxonomy already separates the two: `ModbusExceptionError` is a refusal,
   `ModbusTimeoutError` is not.
7. **Switching an entry between legacy and modern ids** in the options flow.
   Until then the answer is to remove and re-add the entry, which keeps
   history (`doc/integration_migration.md` says so).
8. **The topology step** in the config flow: present the derived role and say
   which claims are measured and which inferred.
9. **The block read test in the diagnostics download.** It runs from the
   survey button; the download leaves it out. The count that reconciles a
   padded frame still needs `blocks.py --client raw`.
10. **The fault and alarm block** (input 13052-13079, fourteen U32s,
    Appendix 4, ~450 flags). Needs a decision on representation before any
    entity; the largest piece of the specification not yet read.

### Blocked on evidence

11. **iHomeManager (milestone 5).** Port 502 *or* 503, unit 247. Not a gateway:
    one endpoint, one device. `identify()` recognises it and the survey
    reports it; the map is in
    [cross_reference_modbus_manager.md](cross_reference_modbus_manager.md)
    (MIT). Needs a survey from an owner.
12. **Sungrow Logger (milestone 8).** Documented (*Logger Communication
    Protocol AW0 1.0.2.9*); fronts a whole installation, which is what the
    one-entry-per-endpoint model was built for. It does **not** forward
    battery data ("Logger is not supported" in the hybrid protocol's Note 2).
13. **SBR per-module entities.** All 24 registers are read; an unfitted module
    answers 0 V, so the module count has to be established first. The
    encoding is a decision, not a migration. An SBR128 survey settles it.
14. **SBH.** Answers the SBR's common block at unit 2 with the SBR's scales;
    per-module arrays unread. Needs the register document.
15. **Meter phase voltage/current (5741-5746) on dongle houses.** Read zero
    through every WiNet-S measured and are gated on a non-zero voltage. Whether
    they need reading on their own (#756) needs a survey from an affected
    owner; `layout.py` changes only on measurement.
16. **T-series energy counters.** One SH20T reads 13045 (daily export) as 0
    while exporting, and 5003/5004-5005 duplicating the export counters. A
    second T survey, ideally on a cable, before `registers.py` changes.
17. **Modbus over TLS on 516.** The path exists (`ModbusTlsParams` through
    `async_get_unit`). Worth building only if 516 is a *separate* session pool
    from 502 -- hold 502 until it refuses, then try 516. Also wanted: a
    certificate hash from a third site, to show whether every dongle ships the
    same key.
18. **Does a WiNet-S advertise over mDNS?** Needs a house with a dongle and
    a run on the host, not in the container.

The most useful contribution is in
[devices-wanted.md](device-fingerprints/devices-wanted.md): a **second firmware
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
- **A config entry is one Modbus endpoint** and the devices discovered on it.
- **Register knowledge is a library without HA imports**, published to PyPI as
  `sungrow-modbus` (OIDC trusted publishing, no stored token).
- **Python `Component` classes are the register description.** `registers.py`
  is source, held field by field to `doc/legacy_entity_map.json` by tests.
- **The domain is `sungrow_modbus`** (`sungrow` is taken by another
  integration).
- **Entity ids are a choice at setup**: legacy ids for existing users, modern
  device-scoped ones for new users. Modern ids take the prefix from the device
  type register; a second device of the same model is told apart by unit id.
- **The `_raw` sensors exist in legacy mode only.** Modern mode exposes the
  decoded value (a binary sensor for an `0xAA`/`0x55` mode, a ratio with its
  unit); `Derived._mode_flag` returns None for anything else.
- **A parenthetical says what a value is**: `(smoothed)` for the moving
  average, `(delayed)` for the delayed binary sensors.
- **The naming rule is per device**, and one convention is enforced by test
  (`scripts/generate/tables/naming.py`).
- **Start and stop are actions, not buttons**, with an audience set per entry
  (admins only by default). The YAML's danger-mode toggle and automations are
  not ported.
- **The wallbox is read-only.** No manufacturer document covers its map.
- **The opt-in SBR sensors keep no history**: partial adoption looks like a
  migration and is not one.
- **The integration offers a dashboard and asks first.**
- **Localisation follows Home Assistant**: modern ids take the interface
  language where HA says they should; legacy ids stay English.
- **13074's write scale is measured per device** (`sungrow_modbus.export_scale`)
  and stored with the firmware it was measured on.
- **Delivery is HACS first**, through the preview channel until the merge.
- **The brand mark is original**, not Sungrow's.

## The migration

The mechanism is settled and asserted in `tests/test_recorder_migration.py`;
`CLAUDE.md` has the rules. In short: claim the legacy `entity_id` at entity
creation, so history continues with no recorder API involved; modern ids are
that plus one registry rename, which carries raw history and long-term
statistics. Every ported entity keeps the YAML entry's unit class and
`state_class`. A second inverter's `_inv_<n>` slot is detected from its serial
sensor and stored in entry data.

The user-facing order is fixed in
[integration_migration.md](integration_migration.md): back up and check the
backup covers the recorder; remove the YAML package and restart; add the
integration; clear the leftovers when the repair offers; verify a known sensor
is continuous; then dashboards and Energy.

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
handed is `device-fingerprints/scripts/`: one launcher, `survey.{sh,cmd}`,
which reads and offers the control test at the end — and `CLAUDE.md` lists
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
