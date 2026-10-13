# Sungrow Modbus — working notes

This repo has **two tracks**. Know which one you are touching.

1. **The YAML package** (`legacy/modbus_sungrow.yaml`) — shipping, in use by many
   people, on `main`. Treat as production.
2. **The new Home Assistant integration** (`custom_components/sungrow_modbus` +
   `src/sungrow_modbus`) — on branch `proper-ha-integration`. The
   long-term replacement, currently an MVP.

The integration is intended to **supersede** the YAML package, not sit beside
it forever. Until it reaches parity, the YAML package stays untouched.

Its scope is wider than the YAML package's. Two of the three extra devices
are now done:

- ✅ the **SBR battery** — its own device, 40 registers in three components,
  on unit **200** direct or **2** through a WiNet-S.
- ✅ the **wallbox** (AC011E-01 / AC22E-01) — its own device, 32 registers in
  four components, at unit **3** through a WiNet-S or **248** direct. Read
  only; nothing writes to it. Unit 248 is the charger's own RS485 address,
  reachable only through a serial gateway wired to the charger — never over
  Modbus TCP.
- ⬜ the **iHomeManager** (port **502 *or* 503**, slave 247) — **never
  measured**; to do: survey one. `identify()` probes input 8000 on unit 247, so
  a contributor who owns one is told what they have, and `sungrow_survey.py`
  reports it without surveying it. Not 503 alone: Sungrow's setting is "Modbus
  TCP on the iHM", which lands on 502 on some units and 503 where 502 is busy.
  It is **not a gateway**: it forwards
  system energy dispatch data, not the devices behind it, so its inverters
  are separate endpoints. `doc/cross_reference_modbus_manager.md` has the
  53-register map, MIT-licensed.

A wallbox does *not* require an iHomeManager, and cannot be found by sweeping
for one: it answers only behind an endpoint that already answered.

It also covers a **generator the Sungrow cannot see**. A non-Sungrow inverter
behind the same grid meter makes `load_power` low by exactly its output --
the inverter computes load from its own output plus grid import -- so
`external.py` adds it back from entities another integration owns. The one
place a value here comes from Home Assistant rather than Modbus, which is why
it is not in `src/`, and the one place an entity's existence is an **option**
rather than a probed fact.

One config entry is **one Modbus endpoint** (host + port) plus the devices
discovered on it, which is exactly the set sharing one serialized connection.
The config flow probes and identifies devices by what answers, never by unit
id. `doc/integration_plan.md` has the register sources, their licences, and
what is next.

## Do not hand-edit

Everything under `scripts/generate/` writes a committed file, and `make
gen-check` (and CI) fails on a hand edit of any of them:

- `custom_components/sungrow_modbus/{derived,number,switch,select}_descriptions.py`
  and `strings.json` / `translations/en.json` -- `scripts/generate/descriptions.py`,
  from `sungrow_modbus.derived` and the tables in `scripts/generate/tables/`;
- `doc/compatibility.md` -- `generate_compatibility.py`, from the fingerprints;
- `legacy/modbus_sungrow_multiple_inverters_{1,2,3}.yaml` --
  `generate_second_inverter_config.py`, from `legacy/modbus_sungrow.yaml`,
  committed by CI. Edit the source, not the output.

**`src/sungrow_modbus/registers.py` and `sensor_descriptions.py` are source.**
`doc/legacy_entity_map.json` is the record of what the YAML package produces
-- the entity ids, units and state classes users have -- and is not
regenerated. `tests/test_registers.py` and `tests/test_sensor_descriptions.py` hold the
two files to it, field by field. Where a field must differ from the YAML, the
difference is declared where the test can see it -- `layout.COUNTS` for a
string length, `write_units_per_count` for 13074's write scale, asserted in
`tests/test_writes.py` -- never made silently.

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
| `make help` | Every command below as a shortcut. `make check` is the CI gate, `make dev` and `make sim` the dev loop, `make gen` rewrites every generated file |
| **`scripts/dev/`** | **The dev loop** |
| `scripts/dev/setup.sh` | Install HA, the device library (editable) and tooling |
| `scripts/dev/develop.sh` | Boot HA on <http://localhost:8123> against `config/` |
| `scripts/dev/ha_onboard.py` | Walk a fresh instance through onboarding over the API, so nobody types `dev`/`dev` into a wizard. Both boot scripts run it in the background; idempotent, and it refuses a non-loopback URL |
| `scripts/dev/hacs_testbed.sh` | Boot a **second** HA on :8124 against `config-hacs/`, with HACS installed, to test the install a user gets. Nothing is symlinked there: HACS downloads the integration from the preview channel, so what runs is what was published, not the working tree |
| `scripts/dev/simulate.sh` | Regenerate the register seed and serve it on :5020 (`simulator.py`, seed in `simulator_registers.json`) |
| `scripts/dev/fetch_references.sh` | Clone HA core + libs into `.reference/` (gitignored) |
| `scripts/dev/seed_migration_testbed.py` | Make the dev instance look like a house that ran the YAML package for years, so the migration can be reviewed in the GUI |
| **`scripts/generate/`** | **Everything that writes a committed file; each has `--check`, all are in CI** |
| `scripts/generate/descriptions.py` | The entity descriptions and names: `derived`, `numbers`, `switches`, `selects`, `strings`, or all five with no argument (`strings` last, since it reads the others) |
| `scripts/generate/tables/writes.py` | **Input table**: which registers the integration may write and within what bounds. Feeds the number/switch/select descriptions; `tests/test_writes.py` holds `registers.py`'s writable set to it |
| `scripts/generate/tables/naming.py` | **Input table**: the entity-name convention. Feeds `strings.json`, `review_names.py` and the Influx helper |
| `scripts/generate/generate_compatibility.py` | Build `doc/compatibility.md` from the committed fingerprints |
| `scripts/generate/generate_simulator_registers.py` | The simulator's seed, from the entity map |
| `scripts/generate/generate_second_inverter_config.py` | The `legacy/` multi-inverter YAML files; run by CI on a change to the YAML package |
| **`scripts/release/`** | **Release gates** |
| `scripts/release/sync_version.py` | Single source of truth for the version: moves it into `manifest.json` and into the PEP 723 header of the survey and the control test; `--check` in CI, `--set X.Y.Z` to release |
| `scripts/release/check_pinned_library.py` | Do the integration's `sungrow_modbus` imports resolve against the library version `manifest.json` pins? `--wheel dist/*.whl` asks it of a local build and gates CI; with no argument it asks it of **PyPI**, which is legitimately red between releases |
| **`scripts/sungrow_control_test/`** | **Writes to a real inverter; runs on the published library** |
| `scripts/sungrow_control_test/control_test.sh`, `control_test.cmd` | The launchers, built like the survey's and tested to stay alike (`test_the_two_folders_launchers_differ_only_where_they_must`): uv, else a ready Python, else offer to install uv. Every argument and the test's exit code pass through, exit 5 included |
| `scripts/sungrow_control_test/sungrow_control_test.py` | **Part B, from a terminal**: writes each control, reads the register back against the specification's scale, watches what the inverter does, and puts everything back. `make controltest-dry HOST=...` first -- it resolves the whole plan and writes nothing. `--restore <snapshot>` is the way out of a run that died halfway. `--export-scale` asks how this firmware writes 13074 with one write that changes nothing, and does nothing else |
| **`scripts/sungrow_read_only_survey/`** | **Part A, read only, runs on the published library** |
| `scripts/sungrow_read_only_survey/read_only_survey.sh`, `read_only_survey.cmd` | **What a contributor runs.** Find `uv` (PATH, then `~/.local/bin`) and hand it `sungrow_survey.py`; else use a Python 3.13+ that has exactly the pinned library; else offer to install uv, asking first. Every argument and the survey's exit code pass through. `read_only_survey.cmd` only starts `read_only_survey.ps1`, which does the Windows half |
| `scripts/sungrow_read_only_survey/sungrow_survey.py` | **The one entry point for a survey** (`make scan HOST=...`, or `make scan-sim` against the simulator): finds the devices, asks what no register can answer, runs the block read test, reads every register, writes the document and a transcript, and prints a maintainer-facing summary. Exit code says what happened (`0` fine, `3` the filename under-claims, `4` the transport is disputed, `1`/`2` nothing collected) |
| `scripts/sungrow_read_only_survey/probe.py` | Probe for Sungrow devices: `mdns`, `sweep <cidr>` (502, 503 for a Logger or iHomeManager, 516 for an iHomeManager's TLS port — found, not readable), `units <host>`, `capabilities <host>`, `dump <host>` |
| `scripts/sungrow_read_only_survey/blocks.py` | The block read test: which read inside a component fails, and whether it is a fault or contention. `--client library` fails where the integration does; `--client raw` names the count a padded frame needs; `--narrow-budget` bounds the narrowing, which is unaffordable on a link where reads time out |
| `scripts/sungrow_read_only_survey/raw_client.py` | The bare-socket client behind `blocks.py --client raw`: a measuring instrument that trusts `byte_count`, not a second copy of the library's client. Not runnable by itself |
| **`scripts/helpers/`** | **One-off tools** |
| `scripts/helpers/influx_migration.py` | Print Grafana regexes and rewrite recipes for InfluxDB users; connects to nothing |
| `scripts/helpers/review_names.py` | Lay the entity names out for the open naming decision — grouped by subject, each with the entity id it produces and its legacy name. `--markdown` prints the sheet (redirect it into `doc/entity_name_review.md`); `--check` fails when that file has drifted, which it silently had by 47 entities |
| `scripts/helpers/make_brand_icon.py` | Regenerate the integration's `brand/` icons (`--preview` renders a check sheet) |
| `pytest` | Device library + integration tests, no network needed |
| `ruff check . && ruff format .` | Lint and format |
| `mypy` | `--strict` over **the library only** (`packages = ["sungrow_modbus"]`). In `make check` and in CI. The integration is deliberately out of scope: it is typed against Home Assistant, whose own annotations are not strict-clean, so checking it would mean a wall of ignores that hides the findings worth having |

`doc/development.yaml` is the copy-paste runbook — commands, the optional
secrets, the dev login, port forwarding to the desktop and to the LAN.
`doc/development.md` is the fuller guide. `doc/integration_plan.md` is the
plan of record, including the migration work that is still open.

## The survey has two parts, and part B writes

Part A is the capability survey: it asks what is here and answers it entirely by
reading. Part B is the **control test**, and it exists because a whole class of
bug is invisible to reading. `NumberField.encode` and `decode` share one
`scale`, so a wrong scale in `registers.py` is *invisible to a readback through
the library*: write 700 W, get 700 W back, every test green. The registers also
mix units on adjacent addresses -- 13052 is 1 W per count and 33047 next door is
0.01 kW -- which is where such an error would come from.

So every value is checked on three legs, and the middle one is the point:

| Leg | Mechanism | Catches |
| --- | --- | --- |
| **A, plumbing** | library write, library read | the write landed at the right address |
| **B, scale** | raw word vs `spec_units_per_count`, typed by hand from V1.1.11 and **never read from `field.scale`** | a wrong scale in `registers.py` |
| **C, behaviour** | what the inverter physically does | a *firmware* whose idea of the scale differs |

A column derived from the thing under test proves nothing, which is why leg B's
scale is hand-typed. `tests/test_control_test.py` makes the two meet, so a
decade error fails the suite on the commit that introduces it rather than on
somebody's roof.

The engine is in the library so both drivers share it: `scripts/sungrow_control_test/sungrow_control_test.py`
and the `Run control write test` button on the device page, which runs part A
then part B and publishes both in one fingerprint document (`control_test`,
schema 19). `--export-scale --merge-into` adds the `export_scale` block
(schema 20), and a full run writes 13074 at the factor that probe answers.

### Rules the procedure turns on

- **The restore is never budgeted, never deadlined and never skipped.** Every
  early exit goes through it. The snapshot is flushed *before the first write*
  -- `.testdata/control-tests/` from the CLI, HA's own store from the
  integration -- and removed only once everything is back **and read back**. A
  leftover snapshot on the next setup becomes a repair. **No snapshot file for
  a day means no writes that day.**
- **A restore writes the snapshot's raw word, and checks it by raw read.**
  Writing the *value* back goes through the scale under test, which can leave a
  register a decade off. The scaled write is only the fallback, for firmware
  that multiplies the raw word too.
- **A restore is a statement about where the register is, not about whether a
  write succeeded.** It reads before it writes, so a register that held its
  value throughout is never reported unrestored. Exit 5 is the one code meaning
  a house is left changed.
- **Probe values must be able to show a decade error.** Both `10*v` and `v/10`
  have to stay inside the accepted range, or the error can only surface as
  exception 0x04 -- which is also what a legitimately out-of-range value
  returns, so it is not evidence. `battery_max_soc` has no such window at all
  (50..100) and the report says so rather than claiming a pass.
- **What the behavioural checks command is a stated constant**,
  `FORCED_EFFECT_W` (1250 W), clamped to the register's live bounds -- never
  derived from other probes, which can walk it up to the pack's ceiling.
- **A pack's ceiling moves, so a clamp is normal near a full battery.** A
  manufactured discharge aims `FORCE_EXPORT_HEADROOM` below the ceiling and
  accepts a clamp within `CLAMP_TOLERANCE`. Decade verdicts are classified
  **first** and excluded, so the tolerance can never absorb the error the
  procedure exists to find.
- **Leg B on 13074 needs the mode lifted, and the run lifts it.** The register
  ignores writes while feed-in limitation is off, which is most houses.
  `_lift_export_mode` switches it on for that probe alone and back to **the
  snapshot's word** the moment the register is restored -- seconds, not the
  phase, because while it is up the house is capped at a probe value. Only
  with `--enable-export-limit`, because it curtails a real house.
- **The button always runs `allow_dark`, and the CLI does not.** Somebody on
  Home Assistant OS has no terminal, so a run refused for want of sun is one
  they can never make. The readback half finds a factor-10 error whether or not
  the sun is up; the behavioural half self-skips and says why.
- **Under fluctuating PV the answer is a bracket, not a model.** When the
  before and after readings disagree the run reports `INCONCLUSIVE`, never a
  failure. Medians, not means: a cloud edge is a step and an MPPT search a
  spike.
- **The export limit check can only catch a decade too small.** A cap ten
  times too large leaves the export where it was. Leg B is the only way to
  catch that direction.
- **The charge-ceiling check is the only safe behavioural test of a
  state-of-charge limit**: lowering `max_soc` under a charging battery
  **stops** a charge, while raising `min_soc` above the battery buys
  electricity, which the guards refuse. A `CONFIRMED` shows the register is an
  enforced ceiling, not that its scale is right.
- **A simulator cannot produce a finding.** It stores raw words with no scale,
  so legs A and B agree by construction and leg C has no signal. Hence
  `--simulated`, which skips the behavioural phase and stamps the report.
- **A run holds this entry's own polling off the inverter**, through
  `SungrowRuntimeData.async_paused()` and the `polling_paused` flag each
  coordinator reads -- at the *poll*, because clearing `update_interval` does
  not cancel a timer already scheduled. A paused coordinator returns what it
  last had, so entities hold their values.
- **A Modbus stop is nearly instant and the recovery is not**: about 2 s to
  stopped, 3 to 4 minutes back to `0x0040 Running` depending on the model,
  then up to 20 s to generate. Much of the wait is `0x0020 Starting`, which
  `is_starting` recognises; the deadline is seven minutes. A start can take
  several `0xCF` commands before the state moves, so it is retried from the
  `finally` rather than sent once.

### Register 13074's write scale is per device

13074 (export power limit) **reads** in watts, agreeing with its 10000 W
maximum from register 5623. On most measured firmware it **writes in tens of
watts**: the word is multiplied by ten **before** the range check, so a plain
write sets ten times what was asked, or is refused with 0x04 when ten times is
out of range. On fwitten's SH10RT-V112 pair it stores the word as handed. **The
write scale of 13074 is per device**, and only while feed-in limitation (13087)
is on: with it off the register ignores writes -- no exception, no change.

- `registers.AsymmetricNumberField` carries the common case:
  `write_units_per_count=10`, `scale` 1 because that is what the register
  contains. It cannot live in `modbus-connection`, whose `NumberField` shares
  one scale by design.
- **`sungrow_modbus.export_scale` asks the inverter**, with one write that
  changes nothing on either firmware: write the held word back when ten times
  it would be out of range, or a tenth of it when that tenth is below the
  minimum. The answer is the **refusal**, which survives a dongle's stale
  readback. Where no such word exists it declines, and with feed-in
  limitation off it needs leave to lift the mode.
  `tests/test_export_scale.py` sweeps both firmwares and asserts the register
  never moves; `scripts/sungrow_control_test/sungrow_control_test.py --export-scale` runs
  it from a terminal.
- `number.SungrowExportLimitNumber` probes on the first write, stores the
  factor in entry data (`CONF_EXPORT_WRITE_SCALE`) with the firmware it was
  measured on, re-measures after a firmware change, and writes the raw word
  itself. An unanswered probe falls back to ten and is not stored. The update
  listener skips the reload when that key is all that changed (`_built_from`).
- Measured by the probe on both sides: bar12 answers times ten, fwitten's
  master and slave answer 1:1, each over the inverter's own LAN port.

The readings behind this are in `doc/device-fingerprints/`.

## How the integration is cut up

`doc/architecture.md` has the diagram and the reasoning; the short version,
because it decides where a change belongs:

- **`config_flow.py` decides, `config_flow_schemas.py` describes.** Schemas,
  option lists and the prose above them live in the second; the steps that
  choose between them live in the first. `_alpha_placeholders` stays in
  `config_flow` and reads `DEVICES_MODE_OFFERED` at call time, so a test can
  patch the flag there.
- **Anything that must work without Home Assistant lives in `src/`.** The
  control test's engine is there for that reason; what is here is a snapshot
  store, a shutdown hook, a progress callback and the options.
- **`SungrowSubDeviceCoordinator` is what the pack and the wallbox share.**
  Both are reached through the inverter's connection, hung off it with
  `via_device`, and identified by *its* serial because neither reports a usable
  one. The subclasses hold only what differs: how a model name is found, and
  how often each block is worth reading.
- **`async_setup_entry` is a list of named steps**, each a function that can
  be read on its own.
- **The generated `*_descriptions.py` are not hand-edited** -- all but
  `sensor_descriptions.py`, which is source. `make gen-check` fails on it.

## The survey runs on the published library

A tester who has the integration gets **part A on the device page** and a
download link for the document. A contributor without it runs `read_only_survey.sh` or
`read_only_survey.cmd`, which hand `sungrow_survey.py` to `uv run --script`: uv reads
the script's **PEP 723 header** and fetches a Python and exactly the
`sungrow-modbus` version it pins. So the register map, the decoding and the
fingerprint tables all come from the library; the directory keeps no copy.

Two things follow:

- **The header is the survey's whole install.** Module-level imports in
  `scripts/sungrow_read_only_survey/` are the standard library, the sibling modules,
  `sungrow_modbus` and `modbus_connection`, and the header must declare
  every one -- `[tmodbus]` included, since the library depends on bare
  `modbus-connection`. `tests/test_survey_dependencies.py` reads the imports
  and the header and holds them to each other.
- **The survey can use only what the pinned wheel has.** The pin is the
  version `pyproject.toml` declares, moved by `sync_version.py`, so between
  releases the PyPI wheel lags the tree. `check_pinned_library.py` reads the
  survey's and the control test's imports beside the integration's, so
  `--wheel` gates a release and the no-argument form says what PyPI lacks.

`scripts/sungrow_control_test/` is built the same way and kept separate: the
same header and pin on `sungrow_control_test.py`, and launchers named
`control_test.{sh,ps1,cmd}` beside it. The two folders stay apart because the
survey's promise is that nothing in its folder can write.

## Things that will bite you

Each of these is verified in a container or against hardware.

### Environment, versions and the install

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
  differ. Never edit either by hand: `scripts/release/sync_version.py --set
  X.Y.Z` moves both, and the scripts' PEP 723 pins, **and re-installs the
  editable library** -- HA compares the
  pin against what is *installed*, and a stale install sends pip after a
  version not on PyPI (`RequirementsNotFound` on Add integration). `--check`
  runs in CI, in pytest and at release.
- **The integration's domain is also the library's import name.** Both are
  `sungrow_modbus`. So `config/custom_components` is a **symlink** to the
  repo's `custom_components/`, the way a real install looks. Never put
  `custom_components/` on `PYTHONPATH`: that exposes the *integration* as
  top-level `sungrow_modbus`, shadowing the library, and HA reports a circular
  import while loading the config flow, a long way from the cause.
- **The pin is a promise about a published wheel, and an editable install
  cannot test it.** `scripts/release/check_pinned_library.py` checks that every
  `sungrow_modbus` import *and* every device attribute the integration uses
  exists in the pinned version: `--wheel` against a local build gates CI, and
  with no argument it asks PyPI, which is legitimately red mid-development. It
  only inspects variables it can **prove** hold a device -- constructed from
  `SungrowInverter` and friends, annotated as one, or assigned from a
  `.device` -- because `device` also names registry entries and probe dicts,
  and a gate that cries wolf gets switched off. It knows what a device gains
  from `self.x =` in `__init__` and from the keys of a `COMPONENTS` map.
- **A repair issue is `title` + `description` *or* `title` + `fix_flow`, never
  both.** `hassfest` says so as *"two or more values in the same group of
  exclusion 'fixable'"*. For a fixable issue the text belongs in the fix
  flow's step. **Run hassfest locally before tagging:**

      python -c "import sys; sys.path.append('.reference/core'); \
        sys.argv=['hassfest','--integration-path','custom_components/sungrow_modbus',\
        '--action','validate']; \
        from script.hassfest.__main__ import main; raise SystemExit(main())"

  Appended to `sys.path`, not prepended, so the **installed** Home Assistant
  wins: `.reference/core` is a partial clone with no `homeassistant.generated`.
- **A failed read is not a refusal.** An exception *response* is the device
  answering -- it is there and it declined, which is evidence. A connection
  lost, a timeout or a desync is the link failing to carry the question, and
  says nothing about the register. In `modbus_connection`,
  **`ModbusExceptionError`** and its subclasses are answers;
  `ModbusConnectionError` / `ModbusTimeoutError` / `ModbusProtocolError` are
  not. `ServerDeviceBusyError` (0x06) is an answer that settles nothing. So
  probes are **three-valued** -- yes, no, undetermined -- and `None` must never
  read as `False`; a probe that decides something published gets retries; the
  CLI exits **1** on a link failure and prints the exit codes last, because a
  pasted transcript loses `$?`. **A test fixture that fakes a refusal with a
  bare `ModbusError` cannot see any of this.** Raise the real type.
- **Never catch `Exception` without a traceback.** Use `_LOGGER.exception`;
  keep the short form for whatever a user reads in a dialog. A failed restore
  in `repairs.py` is the only record of why somebody's inverter still carries
  a test's values, and an error inside a downloaded diagnostics file is held by
  the one person who cannot act on it.
- **A workflow that installs its own tools hides its dependencies.** Anything
  CI needs -- `build` and `twine` included -- is declared in
  `requirements_dev.txt`, so `make ci` runs to the end in a fresh devcontainer.
- **A check nobody runs and a check that cannot run look identical.** The
  library ships a `py.typed` marker, without which mypy refuses the package
  and every consumer silently gets no checking; `mypy` is in `make check` and
  in CI rather than in a target somebody has to remember.
- **`PARALLEL_UPDATES` is 1 on the write platforms, and 0 everywhere else.**
  Everything on this endpoint is serialized behind one connection, so two
  writes issued at once queue, and the second one's timeout starts while it is
  still waiting. And these registers **interlock**: `battery_min_soc` and
  `battery_max_soc` are refused if they cross, so their order matters.
  `sensor` and `binary_sensor` are 0 because the coordinator polls; `button`
  is 0 because a press schedules the run and the runner refuses a second.
- **A first boot in a fresh container logs ~20 setup errors** while HA
  downloads component requirements, and the UI 404s. The next boot is clean
  in ~2s. Not a bug.

### Reading registers

- **Register 13000: `0x0000` is "Running", not off.** The whole map is in
  `derived.RUNNING_STATES`, and the running and stopped sets are derived from
  its labels. The duplicates are a dongle's doing: a WiNet-S re-encodes 13000
  (cable 0x0040 becomes 0x0000, 0x0080 becomes 0x8100), so a code seen only
  through a dongle says nothing about what the inverter sends.
- **Addresses are protocol addresses**, one below the register number in
  Sungrow's document and in the YAML comments (`address: 4989 # reg 4990`).
  **The register maps are written in the document's numbers**, through
  `addresses.reg()`: `power_flow_status = integer(reg(13001))`.
  `tests/test_addresses.py` fails on a field declared any other way.
- **No register is read by a literal address.** A mapped field is looked up
  with `addresses.field_address(name, device)`; the few registers no component
  maps are named constants in `addresses.py` (`DIRECT_ONLY_PROBE`, ...), and
  `Address.register` gives the document's number beside the protocol one. The
  survey scripts import the same names. `tests/test_addresses.py` fails on a
  new literal.
  **Tests are exempt on purpose**: a fixture carries the specification's
  numbers, not the code's.
- **Ask the inverter, do not infer.** Register 5002 reports the output type
  (0 single, 1 3P4L, 2 3P3L); 5000 is the device type code. Some measuring
  points are *not* forwarded by WiNet-S over TCP/IP, so capability varies by
  transport too.
- **`swap: word` in the YAML means `word_order="little"`** in the library.
  Sungrow sends 32-bit values low word first.
- **Not every register answers.** An SH10RT returns 0xFFFF for MPPT3/4, and
  battery blocks are absent without storage. A poll losing one block is
  normal; that is what `UpdateReport` is for.
- **An empty string is a reading of nothing, not a reading of "".** Sungrow
  fills a UTF-8 field it cannot answer with 0x00, so it decodes to `""`.
  `present()` in `model.py` maps it to None, or an absent battery's firmware
  string counts as evidence of one.
- **Some registers come back in a padded frame.** At 2612 and 2628 the
  inverter sends a frame sized for **15 registers while declaring the correct
  byte count**, and `modbus-connection` rejects it. Asking for exactly 15
  makes the two agree -- `layout.COUNTS` -- and `layout.ISOLATE` keeps each in
  a read of its own, or the failure takes the whole pooled block with it.
- **A lenient Modbus client will tell you the register is fine.** A raw
  socket trusts `byte_count` and reads the padded frames perfectly while the
  shipping stack cannot. `scripts/sungrow_read_only_survey/blocks.py` is as strict as
  the shipping stack and reports both numbers plus the count that reconciles
  them. Add to `src/sungrow_modbus/layout.py` only from *its* measurement.
- **A Sungrow accepts very few simultaneous sessions, and the recovery is
  90 seconds of quiet.** Contention's signature is *progressive*: each retry
  dies a little further into the poll. A bad block fails at the same address
  every time. **A short retry is not a retry** -- the control test's opening
  reads back off **5, 20, 45 and 90** seconds -- and **the contention is often
  self-inflicted**: probes and runs opened back to back, on top of a polling
  YAML package.
- **A failed read does not always fail quickly.** Over a slow link a refusal
  can arrive as a 10 s timeout instead of exception 0x02, and a timeout is not
  evidence about the register. `blocks.NARROW_BUDGET` bounds the narrowing of
  failing blocks and marks what it did not reach. Over a slow link, check for
  `not narrowed` before believing a range, and never put a timeout-only
  finding in `layout.py`.

### What a WiNet-S does, and does not

- **A WiNet-S does not forward input 2612 or 2628** (sub-controller and
  battery firmware strings): exception 0x02, while a cable reads them. That is
  the dongle, not the machine, so it is **not** a `layout.ISOLATE` case; it
  belongs in capability gating by transport. A dongle forwards about 1020 of
  1510 dumped addresses where a cable forwards 1461.
- **A WiNet-S answers an empty string where the inverter refuses the read.**
  Inputs 13249, 13264 and 13279 (inverter, module and battery firmware
  strings) can time out on the inverter's own LAN port -- after which the
  inverter closes the session, so `_async_update_components` retries a lost
  connection once per component -- and answer with every character 0x00
  through the dongle. **"The block answered" is not evidence**:
  `ZERO_MEANS_ABSENT` handles numbers and `present()` strings.
- **A WiNet-S answers 0 where the inverter answers 0xFFFF**, which invents
  capabilities such as MPPT3, MPPT4 and a second meter channel.
  `ZERO_MEANS_ABSENT` in `capabilities.py` is the guard; capabilities are
  re-probed every poll and the entry reloads when they **grow**, since nothing
  ever removes an entity.
- **Round-trip time says nothing about the inverter**, so it is not recorded.
  It times the path from whoever reads, usually a VPN. Do not use it as
  evidence about transport.
- **WiFi versus Ethernet on a WiNet-S is not determinable** over Modbus, for
  reads or writes. `user_inputs.transport` is the only source.
- **Transport is register 6100's question**: input 6100 answers on a cable
  and is refused through a dongle. Register 13265 names the module that is
  *fitted*, not the one in the path, and through a dongle it can answer
  empty -- so it is wrong in both directions. Report it beside 6100 as a
  separate fact, never decide transport with it.
- **A WiNet-S forwards a write and then reads it back stale, and waiting does
  not help.** The write lands; the dongle keeps reporting an old value for as
  long as anyone has watched. So through a dongle legs A and B are not
  evidence and **only leg C survives**; a run through a dongle says so above
  its readback table.
- **A WiNet-S serves Modbus over TLS on port 516**, not an iHomeManager. It is
  real Modbus behind TLS 1.2, refuses the same registers as 502, and exhausts
  under rapid reconnects like 502. Its certificate may be identical on every
  dongle, which would mean this TLS authenticates nothing; a hash from a third
  site would settle it. `sungrow_survey.py` sweeps 516 and reports it without
  reading it.

### Finding devices

- **Identify by what answers, never by an open port.** Not every endpoint on
  502 is a Sungrow, and an inverter is not always unit 1: a cluster slave
  answers on unit **2**. `identify()` and the config flow sweep
  `discovery.IDENTIFY_UNITS` (1, then 2-5),
  returns which unit answered, and names the exception type on failure,
  because a refusal and a timeout lead to different next steps.
- **Which unit ids answer depends on the transport.** The SBR answers unit
  200 on the LAN port and unit **2** through a dongle; a wallbox answers unit
  3 through a dongle. One config entry is one endpoint, so a house may need
  two entries to see everything.
- **A wallbox is only reachable through an endpoint that already answered**,
  even with its own LAN cable. A config flow cannot find one by sweeping; it
  has to ask the endpoints it already has. Its registers are undocumented by
  Sungrow; `doc/wallbox_registers.md` is what three measurements agree on.

### Shipping it

- **HACS reads the *default branch* unless there is a stable release**, and
  this repository's default branch is the YAML package, so the integration
  cannot be added to HACS from here while it is pre-release
  (`version_to_download()` in HACS's `repositories/base.py`). The **preview
  channel** is the way in: a second repository whose default branch *is* the
  integration, synced by `doc/preview-mirror/sync.yml`, which must stay
  byte-identical to the copy running there. `scripts/dev/hacs_testbed.sh`
  installs from it the way a user does. **HACS itself requires a GitHub
  account.**

## Hard constraint: migration must preserve history

The integration replaces the YAML package, so existing users must keep their
recorder history and their dashboards. Both are keyed by `entity_id`.

The YAML package produces `sensor.total_dc_power`. An integration entity with
`_attr_has_entity_name = True` produces `sensor.<device name>_total_dc_power`.
Get this wrong and years of history and every dashboard card break silently.

The intended shape is a choice at setup: keep the legacy ids, or take modern
ids and migrate the data across. How that works is **settled and asserted**
in `tests/test_recorder_migration.py`; `doc/integration_migration.md` is the
user's guide. In short:

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

### A second inverter keeps its own history

The YAML ids are global and unprefixed, so only one device can hold them.
`modbus_sungrow_multiple_inverters_<n>.yaml` appends ` inv <n>` to every name
and `_inv_<n>` to every unique_id, and which physical inverter was `inv 2` is
something only the house knows -- so the integration **measures it rather than
asking**: that file's `sensor.sungrow_inverter_serial_inv_<n>` holds its
inverter's serial as its *state*, and an entry already knows the serial it is
talking to. `migration.async_legacy_suffix` matches them.

Three rules, each of which can lose somebody's history if broken:

- **`None` is not `""`.** No match means the question could not be answered.
  Reading it as the unsuffixed slot hands a second inverter the first one's
  years of readings, silently, and no later guess undoes it.
- **The slot is stored in `data` under `CONF_LEGACY_SLOT`**, because detection
  needs the YAML package installed and the migration's next instruction is to
  remove it. Re-deriving at a later start answers `None`.
- **The suffix goes on the name, not the id.** The YAML names the entity
  `Total DC power inv 2` and Home Assistant slugifies that. Appending `_inv_2`
  to the finished id agrees today and stops agreeing the first time a name
  contains something `slugify` treats differently.

And the lookup that finds the serial sensor uses platform **`modbus`**, not
`sensor` -- the YAML reads it over Modbus, so that is what registered it.
Getting it wrong costs nothing visible: it simply never matches, and a
two-inverter house migrates as though it had one.

## Hard constraint: a real serial number is never published

**No real device serial goes into anything this repository tracks.** Not a
fingerprint, not a test fixture, not a docstring, not a commit message, not a
comment explaining a bug. This repository is public, and most of the serials
that pass through it belong to **other people** who lent a VPN or sent a
reading.

A serial is a device's identity. Sungrow's own support uses it to identify an
installation, it is printed on the unit's case, and it is the one field in a
fingerprint that could tie a published reading to a household. That is why
the survey was built around removing it rather than around asking people to
be careful:

- every published document carries a **stand-in**, in a field named for what
  it is: `serial_anonymized_hashed`. Derived by hash, so one device always
  maps to one stand-in and files stay diffable, and the shape is preserved so
  the string decoder stays under test;
- the real serial, the host and the exact time go only to `.testdata/`, which
  is gitignored;
- `RAW_DIR` in `probe.py` is **fixed**, so `--save doc/device-fingerprints`
  cannot write a real serial there even when asked to;
- `NEVER_PUBLISH = ("serial",)` filters anything whose *name* mentions a
  serial, values and key lists alike;
- a wallbox's serial sits two registers below the model name, so
  `wallbox.probe_units` reads the **name**, and the serial is masked at the
  publishing boundary too.

**The source tree is checked as well.** `tests/test_no_real_serials.py`
matches the **shape** of a serial over every tracked file and requires each
hit to be on a list of strings known to be invented, so a new serial in a
fixture fails the suite until somebody adds it there deliberately -- the
moment to ask where it came from.

So when a test needs a serial, use an obviously fake one — `A123456789`, or
`A987654321` where two must differ. When prose needs to name a device, use
the stand-in its fingerprints publish. Neither costs anything: nothing in
this project depends on a serial being real.

The same applies to **addresses**. A published document carries
`ip_address_last_two_octets` and only when its owner agreed to that; the full
address stays in `.testdata/`. And to **consent**: a stand-in serial is not
consent, so ask an owner before publishing readings from their installation.

## Local-only context

Connection details for the maintainer's own inverter are deliberately **not**
in this repo — it is public. They live in his own `secrets.yaml`
(`sungrow_modbus_host_ip`, `sungrow_modbus_device_address`). Use the simulator
on `localhost:5020` unless you specifically need real hardware.

The container **can** reach a LAN inverter outbound with no setup — the Docker
bridge NATs, so it follows the host's routing. Multicast does not cross it, so
mDNS must run on the host. See `real_hardware` in `doc/development.yaml`.
