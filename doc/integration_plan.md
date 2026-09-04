# Plan: replacing the YAML package with a Home Assistant integration

> Plan of record for the `proper-ha-integration` branch. The MVP described
> under "Steps" is **done and verified**; the follow-up section at the bottom
> is the open work. Kept in the repo so it is available inside the
> devcontainer, where the original planning notes are not.

## Context

This repo is today a pure YAML package: [modbus_sungrow.yaml](modbus_sungrow.yaml) (2397 lines) declares one `modbus:` TCP hub plus ~103 modbus entities across 228 `address:` references, and layers `template:` sensors/numbers/selects/switches, automations and scenes on top. Three multi-inverter variants are regex-generated from it by [scripts/generate_second_inverter_config.py](scripts/generate_second_inverter_config.py) in CI. There is no `custom_components/`, no `hacs.json`, no tests, no devcontainer.

Home Assistant 2026.9 shipped a modernized Modbus architecture that makes a real integration the right target:

- A device integration collects its own connection details in its **own config flow** and asks the `modbus` integration for a *unit* rather than owning a socket — `async_get_unit(hass, entry, ModbusTcpParams(...), unit_id)` from `homeassistant.components.modbus`. Integrations sharing the same host/port share one serialized connection, which matters because inverters accept few simultaneous Modbus sessions.
- Register knowledge lives in a standalone, HA-free **device library** built on the new [`modbus-connection`](https://pypi.org/project/modbus-connection/) package, which provides a backend-neutral `ModbusUnit` protocol (tmodbus/pymodbus), a typed device-modelling framework, and a pytest plugin.
- Core's `sofar` integration (added 2026.9) is the working reference: `manifest.json` = `{"config_flow": true, "dependencies": ["modbus"], "integration_type": "device", "iot_class": "local_polling", "requirements": ["sofar-modbus==0.9.1"]}`, with `coordinator.py`, `config_flow.py`, `entity.py` and per-platform files, and **two** DataUpdateCoordinators (fast readings vs. slow settings).

Intended outcome of *this* change: a working development environment on a new `proper-ha-integration` branch — a devcontainer that boots a minimal HA, a `sungrow_shx` integration skeleton that loads via config flow, a `sungrow_shx_modbus` device library, and one real register read end-to-end against both a simulator and (optionally) a real inverter. The existing YAML package is left completely untouched and keeps shipping from `main`.

Decisions already made with the user:
- Device library and integration live **side by side in this repo** (split to its own PyPI package later).
- Milestone 1 = devcontainer + skeleton + **one real sensor** proven end-to-end.
- Devcontainer ships a **Modbus simulator**, and the config flow must also accept a real inverter IP.

## Target layout (new files only)

```
.devcontainer/devcontainer.json
scripts/setup                      # pip install requirements
scripts/develop                    # boot HA against ./config
scripts/simulator.py               # Sungrow Modbus TCP simulator
scripts/gen_simulator_registers.py # dump register seed from modbus_sungrow.yaml
requirements_dev.txt
pyproject.toml                     # packages src/sungrow_shx_modbus, dev tooling (ruff/mypy/pytest)
src/sungrow_shx_modbus/
  __init__.py  const.py  device.py
  components/inverter.py           # Component subclasses = register maps
tests/
  test_device.py
config/                            # git-ignored HA dev config (configuration.yaml committed as template)
custom_components/sungrow_shx/
  __init__.py  manifest.json  const.py
  config_flow.py  coordinator.py  entity.py  sensor.py
  strings.json  translations/en.json
hacs.json
.github/workflows/validate.yml     # hassfest + HACS + ruff + pytest
```

## Steps

### 1. Branch

```bash
git checkout -b proper-ha-integration
```

Nothing on `main` moves. `modbus_sungrow.yaml`, the generator, CI workflows and `dashboards/` stay exactly as they are — the YAML package remains the supported path until the integration reaches parity.

### 2. Devcontainer

Follow the custom-integration devcontainer pattern (not the HA *core* devcontainer — we are not forking core). `.devcontainer/devcontainer.json`:

- image `mcr.microsoft.com/devcontainers/base:debian`
- features: `ghcr.io/devcontainers/features/python:1` at **3.14** (HA now requires ≥3.14.2), plus apt packages `ffmpeg,libturbojpeg0,libpcap-dev`
- `forwardPorts: [8123, 5020]` — HA UI and the simulator; label 8123 "Home Assistant"
- `postCreateCommand: "scripts/setup"`
- VS Code extensions: `charliermarsh.ruff`, `ms-python.python`, `ms-python.vscode-pylance`; format-on-save with ruff
- `remoteUser: vscode`

**Windows note:** the primary working directory is on a Windows host. Clone into a *named container volume* (VS Code "Clone Repository in Container Volume") rather than bind-mounting `C:\Users\...` — bind-mounted file I/O makes HA startup and pytest painfully slow.

`requirements_dev.txt`: `homeassistant>=2026.9`, `modbus-connection[pymodbus]`, `pymodbus`, `pytest-homeassistant-custom-component`, `ruff`, `mypy`, and `-e .` for the local device library.

`scripts/setup` — `pip install -r requirements_dev.txt`.

`scripts/develop` — the blueprint pattern that avoids symlinks:

```bash
#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
if [[ ! -d "${PWD}/config" ]]; then
  mkdir -p "${PWD}/config"
  hass --config "${PWD}/config" --script ensure_config
fi
export PYTHONPATH="${PYTHONPATH}:${PWD}/custom_components"
hass --config "${PWD}/config" --debug
```

Add a `.vscode/tasks.json` task "Run Home Assistant" wrapping `scripts/develop`, and a `launch.json` debug config so breakpoints work in the integration.

`config/configuration.yaml` (committed): `default_config:`, `logger:` with `default: info` and `custom_components.sungrow_shx: debug` + `modbus: debug`. `.gitignore` gains `config/*` with `!config/configuration.yaml`, plus `__pycache__/`, `*.egg-info/`, `.pytest_cache/`.

**Gotcha:** HA validates `manifest.json` `requirements` at startup and will try to pip-install `sungrow-shx-modbus==<version>` if the installed version does not match exactly. Keep the version in `pyproject.toml` and in the manifest identical, and install the library editable *before* first boot (`scripts/setup` does this via `-e .`).

### 3. Simulator

`scripts/gen_simulator_registers.py` parses [modbus_sungrow.yaml](modbus_sungrow.yaml) with PyYAML — reuse the `!secret` SafeLoader constructor trick already written in [debug/generate_sensor_list.py](debug/generate_sensor_list.py) — walks `modbus[].sensors`, and emits a JSON seed of `{input: {addr: value}, holding: {addr: value}}` with plausible values derived from each entry's `data_type`/`scale`/`count`.

`scripts/simulator.py` starts an async pymodbus TCP server on `0.0.0.0:5020` with datastores preloaded from that seed, so `input_type: input` (FC04) and `holding` (FC03) resolve to the right addresses. This gives offline development and a CI target. Point the config flow at `localhost:5020` in the devcontainer, or at the real inverter's IP on the LAN — the config flow takes host/port/unit id, so both work with no code difference.

### 4. Device library `src/sungrow_shx_modbus/`

HA-free, `modbus-connection` only. Build `Component` subclasses whose fields are a near one-to-one translation of the YAML entries — the library documents exactly this YAML→`Component` translation, and the intent is that the class is *committed source*, not YAML loaded at runtime:

| YAML in `modbus_sungrow.yaml` | Library field |
|---|---|
| `input_type: input` | `register_space = "input"` on the Component |
| `data_type: uint16` + `scale: 0.1` | `gauge(addr, 0.1, unit="kWh")` |
| `data_type: int16` (unscaled) | `integer(addr, signed=True)` |
| `data_type: uint32` + `swap: word` | `uint32(addr, word_order="little")` |
| `data_type: string`, `count: 10` | `string(addr, length=10)` |
| `nan_value:` (used on battery start-power sensors) | `nan=<sentinel>` |
| running/alarm state codes decoded in `template:` | `enum(addr, RunningState)` / `flags(addr, AlarmFlags)` |
| write-back targets behind the `&sg_reg_*` anchors | `writable=True` fields |

Milestone-1 scope: one `Component` (e.g. `InverterReadings`) with a handful of fields including **Total DC Power** (input register, uint32), plus device identity (serial number string, device type code) needed for the unique id. Structure it per the documented library pattern — a top-level `SungrowDevice(unit)` composing Components, one per sub-system — so the remaining ~100 registers slot in later without reshaping anything.

`async_update()` pools neighbouring addresses into block reads automatically, which replaces the per-entity `scan_interval` anchors: group fields into Components matching the existing tiers (realtime 5 s / fast 10 s / medium 60 s / slowest 600 s) and give each tier its own coordinator, mirroring how `sofar` splits readings from settings.

`tests/test_device.py` uses the `modbus-connection` pytest plugin / in-memory mock backend to assert decoding of the milestone fields.

### 5. Integration `custom_components/sungrow_shx/`

`manifest.json` — mirror the `sofar` shape:

```json
{
  "domain": "sungrow_shx",
  "name": "Sungrow SHx",
  "codeowners": ["@mkaiser"],
  "config_flow": true,
  "dependencies": ["modbus"],
  "documentation": "https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant",
  "integration_type": "device",
  "iot_class": "local_polling",
  "requirements": ["sungrow-shx-modbus==0.1.0"],
  "version": "0.1.0"
}
```

(`version` is required for custom integrations; core integrations omit it.)

- `config_flow.py` — user step asking host / port / unit id. Validate by holding a temporary unit with `async_get_temporary_unit(hass, params, unit_id)` (the context-manager variant that exists precisely because a config flow has no entry yet), read the serial number, and use it as the entry `unique_id` with `_abort_if_unique_id_configured()`. Surface `ModbusConnectionError` as `cannot_connect` and an unrecognized device type as `unsupported_device`.
- `__init__.py` — `async_setup_entry` calls `async_get_unit(hass, entry, ModbusTcpParams(host, port), unit_id)`, builds `SungrowDevice(unit)`, does one identity read, registers the device, creates the coordinator(s), stores them on `entry.runtime_data` (typed `SungrowConfigEntry = ConfigEntry[SungrowRuntimeData]`), then forwards to `[Platform.SENSOR]`. `async_unload_entry` unloads platforms — the shared connection closes itself when the last holder unloads, so do not close anything manually.
- `coordinator.py` — `DataUpdateCoordinator` calling `device.async_update()`, translating `ModbusConnectionError` to `UpdateFailed`.
- `entity.py` — `SungrowEntity(CoordinatorEntity)` base with `_attr_has_entity_name = True` and shared `DeviceInfo` (identifiers = serial, manufacturer "Sungrow", model from device type).
- `sensor.py` — a `SungrowSensorEntityDescription` list driving entities from library field names. Milestone 1 ships **Total DC Power** only.
- `strings.json` + `translations/en.json` for the config flow.

`hacs.json` at the repo root so the integration can be installed via HACS from this repo alongside the YAML package.

### 6. CI

`.github/workflows/validate.yml`: `home-assistant/actions/hassfest@master`, `hacs/action@main` with `CATEGORY: integration`, `ruff check`/`ruff format --check`, and `pytest`. Leave the three existing workflows alone.

## Verification

1. Reopen the repo in the devcontainer; confirm `scripts/setup` completes and `hass --version` reports ≥ 2026.9 on Python 3.14.
2. `python scripts/gen_simulator_registers.py` then `python scripts/simulator.py` — simulator listening on 5020.
3. `pytest` — device-library decoding tests pass without any network.
4. `scripts/develop`, open <http://localhost:8123>, complete onboarding.
5. Settings → Devices & Services → Add Integration → "Sungrow SHx" → host `localhost`, port `5020`, unit id `1`. Entry is created, a device appears named by the simulated serial.
6. The **Total DC Power** sensor exists, holds the simulated value, and updates on the coordinator interval. Logs show `custom_components.sungrow_shx` debug lines and no `modbus` connection errors.
7. Repeat step 5 against the real inverter's IP on port 502 to confirm the same code path reads live data.
8. Confirm `git status` shows no modification to `modbus_sungrow.yaml`, the generated multi-inverter files, or `scripts/generate_second_inverter_config.py`.

## Explicitly out of scope here

Porting the remaining ~100 registers, the `template:` sensors/numbers/selects/switches, the automations/scenes (EMS control), the multi-inverter story, the aggregate sensors in [additional_sensors/](additional_sensors/), the SBR battery package, and any migration path for existing YAML users. Each becomes its own follow-up once the foundation above is proven.

---

## Follow-up: superseding the YAML package (added after MVP scope was agreed)

The integration is meant to **replace** `modbus_sungrow.yaml`, not sit beside
it, and a clean migration is a hard requirement: existing users keep their
recorder history and their dashboards, either automatically or through an
automated update path.

### The crux

`entity_id`. The YAML package yields `sensor.total_dc_power`; an integration
entity with `_attr_has_entity_name = True` yields
`sensor.<device name>_total_dc_power`. Dashboards reference entity ids
literally, and recorder history is keyed by them, so this naming decision
decides whether years of data and every dashboard card survive.

The shape to build is a **choice at setup time**:

- **Keep legacy ids** — history and dashboards carry on untouched. Requires
  removing the YAML entities' registry entries first, or the ids collide.
- **Modern, device-scoped ids** — idiomatic HA, with the existing data
  migrated across.

### Established by experiment

All three of the questions this section used to open with are now answered,
against Home Assistant 2026.9.0 in the devcontainer, by
[tests/test_recorder_migration.py](../tests/test_recorder_migration.py). They
are asserted rather than written down, so a core release that changes any of
it fails the suite instead of breaking users silently.

**Renaming carries everything, and copies nothing.** The recorder listens for
entity registry updates that carry `old_entity_id`
(`homeassistant/components/recorder/entity_registry.py`) and renames the
`states_meta` row *and* the `statistics_meta` row. State rows reference
`states_meta` by id, so no history is rewritten and long-term statistics
follow the same rename. A `total_increasing` sum keeps climbing across it:
the statistics compiler reads the previous sum from the statistic_id it just
inherited, so the Energy dashboard sees neither a reset nor a spike.

**A rename onto an entity_id the recorder already knows is refused.** Both
`states_meta.update_metadata` and `statistics_meta.update_statistic_id` bail
out on collision with a log line and nothing else — no exception, no repair
issue. This is precisely the situation a YAML migration is in, because
`sensor.total_dc_power` already has years of rows. So the migration cannot be
"create modern entities, then rename them onto the legacy ids".

**The mechanism that does work is to claim the legacy entity_id at creation.**
An entity registered directly on `sensor.total_dc_power` writes to the
`states_meta` row that is already there; raw history and statistics simply
continue, with no recorder API called at all. Two preconditions, both
verified: the legacy registry entry must be gone, *and* the legacy entity
must be absent from the state machine — the registry hands out an entity_id
only if it is free in both, and otherwise silently appends `_2`. Removing the
old entity records one empty state, so a migrated series carries a
single-row seam where the YAML package stopped; statistics do not see it.

**This collapses the two setup options into one mechanism plus a step.**
Keeping the legacy ids is the adoption above. Modern, device-scoped ids are
the same adoption followed by one registry rename, which is exactly the case
that carries history and statistics cleanly. Note what the rename does *not*
fix: dashboards reference entity_ids literally, so only the legacy-id option
leaves existing cards working.

**Holding the entity_id is necessary but not sufficient.** Statistics
metadata pins the unit. A unit in the same unit class as the compiled
statistics (Wh where the YAML had kWh) is converted and the series continues.
A unit from a different class is dropped from normalization, and long-term
statistics then **freeze flat** — every later period repeats the last good
state and sum — while raw history keeps filling normally. Nothing looks
broken; the Energy dashboard just reads as a system producing nothing. Every
ported entity must therefore keep the unit class *and* `state_class` of the
YAML entry it replaces. This is the constraint to check per entity while
porting the register map, not afterwards.

One thing a statistics query does *not* pin: its display unit follows the
entity's current unit, so comparing statistics across a unit change without
passing an explicit `units` argument shows a thousandfold jump that is not in
the stored data.

### Still open

- Whether the seam row and the adoption path behave the same on a database
  with years of real rows and statistics, rather than minutes of synthetic
  ones. That is what the production copy below is for.
- How the setup-time choice is presented, and how the integration is told to
  claim a legacy id per entity (`_attr_has_entity_name` is per entity class,
  so the two id shapes cannot both be static).

### Test data from production

The maintainer has a production Home Assistant instance that has run the YAML
package for several years, and has offered a copy of it. Importing it into the devcontainer
gives a realistic migration testbed — the only way to verify that history and
statistics actually survive, rather than assuming they do.

What to collect from the production `config/`:

- `home-assistant_v2.db` (or a dump, if recorder is on MariaDB/Postgres)
- `.storage/core.entity_registry`, `.storage/core.device_registry`
- `.storage/core.restore_state`
- `.storage/lovelace*` — the dashboards that must keep working
- the exact version of `modbus_sungrow.yaml` in use

Handling:

- Put it under a gitignored path (e.g. `.testdata/`). It is real household
  data and must never reach the repo or CI.
- The recorder DB may be multiple GB. A purged copy
  (`recorder.purge` with a short `keep_days`, taken on a *copy*) is usually
  enough, as long as long-term statistics are retained — those are the part
  that matters most and they survive purging.
- Work on a copy, never the original, and take it while HA is stopped (or via
  a proper SQLite backup) so the DB is consistent.

Then: stand the devcontainer up against that config, run the migration, and
assert that a known sensor's history and statistics are continuous across the
switch — same entity, no gap, no reset.
