# Sungrow SHx — working notes

This repo has **two tracks**. Know which one you are touching.

1. **The YAML package** (`modbus_sungrow.yaml`) — shipping, in use by many
   people, on `main`. Treat as production.
2. **The new Home Assistant integration** (`custom_components/sungrow_shx` +
   `src/sungrow_shx_modbus`) — on branch `proper-ha-integration`. The
   long-term replacement, currently an MVP.

The integration is intended to **supersede** the YAML package, not sit beside
it forever. Until it reaches parity, the YAML package stays untouched.

## Do not hand-edit

- `modbus_sungrow_multiple_inverters_{1,2,3}.yaml` are generated from
  `modbus_sungrow.yaml` by `scripts/generate_second_inverter_config.py` and
  committed by CI. Edit the source, not the output.

## The integration, in one paragraph

Home Assistant 2026.9 modernized Modbus. A device integration runs its own
config flow and asks the `modbus` integration for a *unit*
(`async_get_unit(hass, entry, ModbusTcpParams(...), unit_id)`); everything
pointed at the same host/port then shares one serialized connection, which
matters because a Sungrow inverter accepts few simultaneous sessions. Register
knowledge lives in `src/sungrow_shx_modbus`, a plain Python library on
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
| `pytest` | Device library + integration tests, no network needed |
| `ruff check . && ruff format .` | Lint and format |

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
  `custom_components/sungrow_shx/manifest.json`.** HA checks the installed
  version on every start and will try to pip-install the package if they
  differ.
- **Addresses are protocol addresses**, one below the register number in
  Sungrow's document and in the YAML comments (`address: 4989 # reg 4990`).
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
- Every ported entity must keep the **unit class** and `state_class` of the
  YAML entry it replaces. Get the unit class wrong and long-term statistics
  freeze flat — repeating the last value forever — while raw history keeps
  filling, so nothing looks broken. Check this per entity while porting.

## Local-only context

Connection details for the maintainer's own inverter are deliberately **not**
in this repo — it is public. They live in his own `secrets.yaml`
(`sungrow_modbus_host_ip`, `sungrow_modbus_device_address`). Use the simulator
on `localhost:5020` unless you specifically need real hardware.
