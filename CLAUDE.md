# Sungrow Modbus — working notes

This repo has **two tracks**. Know which one you are touching.

1. **The YAML package** (`legacy/modbus_sungrow.yaml`) — shipping, in use by many
   people, on `main`. Treat as production.
2. **The new Home Assistant integration** (`custom_components/sungrow_modbus` +
   `src/sungrow_modbus`) — on branch `proper-ha-integration`. The
   long-term replacement, currently an MVP.

The integration is intended to **supersede** the YAML package, not sit beside
it forever. Until it reaches parity, the YAML package stays untouched.

Its scope is wider than the YAML package's: besides the inverter it is to
cover the **wallbox** (AC011E-01 / AC22E-01, slave 3 via WiNet-S or 248
direct), the **SBR/SBH battery modules** (SBR is unit 200 and not reachable
via WiNet-S at all) and the **iHomeManager** (port **503**, slave 247 — the
only one of them with an official Sungrow register document). A wallbox does
*not* require an iHomeManager.

One config entry is **one Modbus endpoint** (host + port) plus the devices
discovered on it, which is exactly the set sharing one serialized connection.
The config flow probes and identifies devices by what answers, never by unit
id. `doc/integration_plan.md` has the register sources, their licences, and
the milestone order.

## Do not hand-edit

- `legacy/modbus_sungrow_multiple_inverters_{1,2,3}.yaml` are generated from
  `legacy/modbus_sungrow.yaml` by `scripts/generate_second_inverter_config.py`
  and committed by CI. Edit the source, not the output.

## The integration, in one paragraph

Home Assistant 2026.9 modernized Modbus. A device integration runs its own
config flow and asks the `modbus` integration for a *unit*
(`async_get_unit(hass, entry, ModbusTcpParams(...), unit_id)`); everything
pointed at the same host/port then shares one serialized connection, which
matters because a Sungrow inverter accepts few simultaneous sessions. Register
knowledge lives in `src/sungrow_modbus`, a plain Python library on
`modbus-connection` with **no Home Assistant imports**, so it tests without HA
and without hardware. Core's `sofar` integration is the reference
implementation for this pattern — read its real source, not blog posts.

## Commands

| Command | What it does |
| --- | --- |
| `scripts/setup` | Install HA, the device library (editable) and tooling |
| `scripts/develop` | Boot HA on <http://localhost:8123> against `config/` |
| `scripts/simulate` | Regenerate the register seed and serve it on :5020 |
| `scripts/fetch_references` | Clone HA core + libs into `.reference/` (gitignored) |
| `scripts/discover_probe.py` | Probe for Sungrow devices: `mdns`, `sweep <cidr>`, `units <host>`, `capabilities <host>`, `dump <host>` |
| `scripts/sync_version.py` | Single source of truth for the version; `--check` in CI, `--set X.Y.Z` to release |
| `scripts/generate_entity_map.py` | Derive `doc/legacy_entity_map.json` from the YAML package; `--check` in CI |
| `scripts/generate_strings.py` | Write the entity names to the convention in `scripts/naming.py`; `--check` in CI |
| `scripts/seed_migration_testbed.py` | Make the dev instance look like a house that ran the YAML package for years, so the migration can be reviewed in the GUI |
| `scripts/collect_fingerprint.py` | Standalone, dependency-free report users run against their own inverter |
| `scripts/make_brand_icon.py` | Regenerate `brand/` icons (`--preview` renders a check sheet) |
| `pytest` | Device library + integration tests, no network needed |
| `ruff check . && ruff format .` | Lint and format |

`doc/development.yaml` is the copy-paste runbook — commands, the optional
secrets, the dev login, port forwarding to the desktop and to the LAN.
`doc/development.md` is the fuller guide. `doc/integration_plan.md` is the
plan of record, including the migration work that is still open.

## Things that will bite you

These each cost real debugging time. They are not guesses — each was hit and
verified in a container.

- **Home Assistant 2026.9 requires Python ≥ 3.14.2.** The
  `mcr.microsoft.com/devcontainers/python` images only go to 3.13, which is
  why the devcontainer uses `python:3.14-bookworm`.
- **Core's `modbus` drives `modbus-connection` with the _tmodbus_ backend,
  not pymodbus.** `import homeassistant.components.modbus` fails outright
  without `modbus-connection[tmodbus]`. `requirements_dev.txt` mirrors the
  exact pins from `homeassistant/components/modbus/manifest.json`; bump them
  together.
- **The version in `pyproject.toml` must equal the `requirements` entry in
  `custom_components/sungrow_modbus/manifest.json`.** HA checks the installed
  version on every start and will try to pip-install the package if they
  differ. Never edit either by hand: `python scripts/sync_version.py --set X.Y.Z`
  moves both, `--check` is enforced in CI, in pytest and at release.
- **The integration's domain is also the library's import name.** Both are
  `sungrow_modbus`. So `config/custom_components` is a **symlink** to the
  repo's `custom_components/`, the way a real install looks. Putting
  `custom_components/` on `PYTHONPATH` instead — which `scripts/develop` used
  to do, and which worked until the domain was renamed — exposes the
  *integration* as top-level `sungrow_modbus`, shadowing the library, and
  `from sungrow_modbus import TIERS` then imports the integration from inside
  itself. Home Assistant reports it as a circular import while loading the
  config flow, a long way from the cause.
- **`--set` must re-install the library, not just edit the files.** Bumping
  the version does not touch an installed editable package's metadata, and
  Home Assistant compares the manifest pin against what is *installed*. Left
  alone it asks pip for a version that is not on PyPI yet and the config flow
  dies with `RequirementsNotFound` at the moment somebody clicks Add
  integration. `scripts/sync_version.py --set` now does the re-install, and
  `--check` fails on the drift.
- **Addresses are protocol addresses**, one below the register number in
  Sungrow's document and in the YAML comments (`address: 4989 # reg 4990`).
- **Ask the inverter, do not infer.** Register 5002 reports the output type
  (0 single, 1 3P4L, 2 3P3L); 5000 is the device type code. Sungrow's own
  protocol document also warns that some measuring points are *not*
  forwarded by WiNet-S over TCP/IP, so capability varies by transport too.
- **`swap: word` in the YAML means `word_order="little"`** in the library.
  Sungrow sends 32-bit values low word first.
- **A first boot in a fresh container logs ~20 setup errors** while HA
  downloads component requirements, and the UI 404s. The next boot is clean
  in ~2s. Not a bug.
- **Not every register answers.** An SH10RT returns 0xFFFF for MPPT3/4, and
  battery blocks are absent without storage. A poll losing one block is
  normal; that is what `UpdateReport` is for.

## Hard constraint: migration must preserve history

The integration replaces the YAML package, so existing users must keep their
recorder history and their dashboards. Both are keyed by `entity_id`.

The YAML package produces `sensor.total_dc_power`. An integration entity with
`_attr_has_entity_name = True` produces `sensor.<device name>_total_dc_power`.
Get this wrong and years of history and every dashboard card break silently.

The intended shape is a choice at setup: keep the legacy ids, or take modern
ids and migrate the data across. How that works is **settled and asserted**
in `tests/test_recorder_migration.py`; `doc/integration_plan.md` has the
detail. In short:

- A registry rename carries raw history *and* long-term statistics, and a
  `total_increasing` sum keeps climbing across it.
- But a rename onto an id the recorder already knows is **refused** with only
  a log line, which is exactly the YAML case. So the mechanism is to claim the
  legacy `entity_id` at entity creation — history then simply continues, no
  recorder API involved. Modern ids are that plus one rename afterwards.
- Adoption needs the legacy id free in the registry *and* in the state
  machine, or the registry silently appends `_2`.
- **Both directions are reversible.** A rename moves the row, so the round
  trip returns history to the legacy id; where that id is still occupied,
  archive the occupant under another name first. Nothing is copied, nothing
  is deleted. There is no raw-state import API, so staging history in a
  temporary copy is not possible — and not needed.
- Every ported entity must keep the **unit class** and `state_class` of the
  YAML entry it replaces. Get the unit class wrong and long-term statistics
  freeze flat — repeating the last value forever — while raw history keeps
  filling, so nothing looks broken. Check this per entity while porting.

## Local-only context

Connection details for the maintainer's own inverter are deliberately **not**
in this repo — it is public. They live in his own `secrets.yaml`
(`sungrow_modbus_host_ip`, `sungrow_modbus_device_address`). Use the simulator
on `localhost:5020` unless you specifically need real hardware.

The container **can** reach a LAN inverter outbound with no setup — the Docker
bridge NATs, so it follows the host's routing. Multicast does not cross it, so
mDNS must run on the host. See `real_hardware` in `doc/development.yaml`.
