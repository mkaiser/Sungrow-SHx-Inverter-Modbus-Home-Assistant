# Sungrow Modbus — working notes

## This repository is an LLM wiki

What this project knows about Sungrow devices is organized after
[microsoft/llmwiki](https://github.com/microsoft/llmwiki), in three layers.
This file keeps the rules and the working notes about the repository, and it
points into the wiki for the device knowledge.

| Layer | Owner | Where | Rule |
| --- | --- | --- | --- |
| **Raw sources** | humans, and the survey | `device-survey/` (inverter and wallbox documents, control tests), `doc/legacy_entity_map.json`, `doc/cross_reference_modbus_manager.md`, `doc/wallbox_registers.md`, `.wiki/raw/` for anything with no other home | **Immutable to the wiki.** Read, cite, never rewrite. Each stays where its tooling writes or reads it |
| **The wiki** | the LLM | `.wiki/wiki/`: `index.md`, `log.md`, `entities/`, `concepts/`, `sources/`, `queries/` | Compiled knowledge, cross-linked, kept current on every ingest |
| **The schema** | both | `.wiki/AGENTS.md` | Page types, frontmatter, naming, the ingest workflow, lint rules |

- **Entities** are things that exist: a device (`sbr-battery`, `winet-s`), a
  register (`register-13074`), a firmware (`sapphire-h-b001-v000-p023`), an
  installation under its owner's handle (`fwitten`). **Concepts** are what
  the measurements taught: the three legs of the control test, contention, a
  failed read not being a refusal, adoption of legacy entity ids.
- **Every claim on a page cites its source**: a survey, a test or a
  file. A claim with no source is a question, and goes into `queries/` until
  one answers it.
- **Ingest is part of the work.** A new survey, a control test or a
  hardware finding is ingested in the same change that uses it: update the
  entity and concept pages it touches, note where it contradicts them, add
  an index entry, and append one line to `log.md`.
- **`log.md` is the only place history goes.** Pages state what is true now.
- **Code, tests and generated files are not wiki pages.** `doc/compatibility.md`,
  `doc/entity_name_review.md` and the `*_descriptions.py` stay generated. The
  wiki links to them and never copies them.
- **The rules in this file outrank the wiki**: asking before a push, files
  that must not be hand-edited, history-preserving migration, and **no real
  serial number or address on any page**. `.wiki/` is tracked, so
  `tests/test_no_real_serials.py` covers it. A survey transcript is never a
  raw source.

Before working on a device question, read `.wiki/wiki/index.md` and the
pages it points to. `.wiki/AGENTS.md` is the wiki's schema, and it has the
ingest workflow. `tests/test_wiki.py` lints the wiki in `make check`.

## Two tracks

This repo has **two tracks**. Know which one you are touching.

1. **The YAML package** (`legacy/modbus_sungrow.yaml`) — shipping, in use by many
   people, on `main`. Treat as production.
2. **The new Home Assistant integration** (`custom_components/sungrow_modbus` +
   `src/sungrow_modbus`) — on branch `proper-ha-integration`. The
   long-term replacement, currently an MVP.

The integration is intended to **supersede** the YAML package, not sit beside
it forever. Until it reaches parity, the YAML package stays untouched.

Its scope is wider than the YAML package's. Each device has its page in the
wiki:

- ✅ the [SBR battery](.wiki/wiki/entities/device-sbr-battery.md): its own device, 40 fields
  in three components.
- ✅ the [wallbox](.wiki/wiki/entities/device-wallbox.md) (AC011E-01 / AC22E-01): its own
  device, 32 fields in four components, read only. It is reached through the
  dongle, or at its own address when the inverter's entry has the
  **`wallbox_host` option** set. That is an option, not an entry, so the
  entity ids are the same either way.
- ⬜ the [iHomeManager](.wiki/wiki/entities/device-ihomemanager.md): **never measured**.
  To do: survey one.
- a [generator the Sungrow cannot see](.wiki/wiki/concepts/external-generator.md), added
  back by `external.py`. This is the one place a value comes from Home
  Assistant rather than Modbus.

One config entry is **one inverter, reached through one Modbus endpoint**
(host + port), plus the devices discovered on it, which are identified
[by what answers](.wiki/wiki/concepts/identify-by-what-answers.md), never by unit id.
`doc/integration_plan.md` has the register sources, their licences, and what
is next.

## Git: ask before every push

**Never `git push` without asking the maintainer first, every time.** An
earlier "commit and push" covers that one change, not the next one in the
same session. Committing when asked is fine; pushing is a separate question.

## Do not hand-edit

Everything under `scripts/generate/` writes a committed file, and so does
`scripts/helpers/review_names.py`. Edit the source, not the output:

- `custom_components/sungrow_modbus/{derived,number,switch,select}_descriptions.py`
  and `strings.json` / `translations/en.json` -- `scripts/generate/descriptions.py`,
  from `sungrow_modbus.inverter.derived` and the tables in `scripts/generate/tables/`;
- `doc/compatibility.md` -- `generate_compatibility.py`, from the surveys;
- `scripts/dev/simulator_registers.json` -- `generate_simulator_registers.py`,
  from the YAML package and the entity map;
- `doc/entity_name_review.md` -- `review_names.py --markdown`;
- `legacy/modbus_sungrow_multiple_inverters_{1,2,3}.yaml` --
  `generate_second_inverter_config.py`, from `legacy/modbus_sungrow.yaml`.

`make gen-check` (and CI) fails on a hand edit of the first four. The last has
no `--check`: CI regenerates and commits it on a change to the YAML package,
overwriting any hand edit.

**`src/sungrow_modbus/inverter/registers.py` and `sensor_descriptions.py` are source.**
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
| `scripts/dev/ha_http_port.py` | Write a scripted instance's HTTP port where Home Assistant 2026.9 reads it, the `stable` config in `.storage/http`. `http:` in `configuration.yaml` only becomes a pending config that reverts after five minutes unless somebody promotes it. `hacs_testbed.sh` calls it |
| `scripts/dev/simulate.sh` | Regenerate the register seed and serve it on :5020 (`simulator.py`, seed in `simulator_registers.json`) |
| `scripts/dev/fetch_references.sh` | Clone HA core + libs into `.reference/` (gitignored) |
| `scripts/dev/seed_migration_testbed.py` | Make the dev instance look like a house that ran the YAML package for years, so the migration can be reviewed in the GUI |
| **`scripts/generate/`** | **Everything that writes a committed file; each has `--check` but the multi-inverter YAML, which CI regenerates and commits instead** |
| `scripts/generate/descriptions.py` | The entity descriptions and names: `derived`, `numbers`, `switches`, `selects`, `strings`, or all five with no argument (`strings` last, since it reads the others) |
| `scripts/generate/tables/writes.py` | **Input table**: which registers the integration may write and within what bounds. Feeds the number/switch/select descriptions; `tests/test_writes.py` holds `registers.py`'s writable set to it |
| `scripts/generate/tables/naming.py` | **Input table**: the entity-name convention. Feeds `strings.json`, `review_names.py` and the Influx helper |
| `scripts/generate/generate_compatibility.py` | Build `doc/compatibility.md` from the committed surveys |
| `scripts/generate/generate_simulator_registers.py` | The simulator's seed, from the entity map |
| `scripts/generate/generate_second_inverter_config.py` | The `legacy/` multi-inverter YAML files; run by CI on a change to the YAML package |
| **`scripts/release/`** | **Release gates** |
| `scripts/release/sync_version.py` | Single source of truth for the version: moves it into `manifest.json` and into the PEP 723 header of the survey and the control test; `--check` in CI, `--set X.Y.Z` to release |
| `scripts/release/check_pinned_library.py` | Do the integration's `sungrow_modbus` imports resolve against the library version `manifest.json` pins? `--wheel dist/*.whl` asks it of a local build and gates CI; with no argument it asks it of **PyPI**, which is legitimately red between releases |
| **`device-survey/scripts/`** | **What a contributor is handed; runs on the published library** |
| `device-survey/scripts/survey.sh`, `survey.cmd` | **What a contributor runs.** Find `uv` (PATH, then `~/.local/bin`) and hand it `sungrow_survey.py`; else use a Python 3.13+ that has exactly the pinned library; else offer to install uv, asking first. Every argument and the survey's exit code pass through. `survey.sh control ...` hands the rest to `sungrow_control_test.py` -- the restore above all. `survey.cmd` only starts `survey.ps1`, which does the Windows half. `SUNGROW_MODBUS_LIBRARY=<wheel or source folder>` lays an unreleased library over the pin: `make scan-local` / `controltest-local` from this tree, `make scan-wheel` from a fresh `make wheel` |
| `device-survey/scripts/python/sungrow_survey.py` | **The one entry point for a survey** (`make scan HOST=...`, or `make scan-sim` against the simulator): finds the devices, asks what no register can answer -- last of all whether the control test may run -- runs the block read test, reads every register, writes the document and a transcript, runs part B into that document when allowed, and prints a maintainer-facing summary. Exit code says what happened (`0` fine, `3` the filename under-claims, `4` the transport is disputed, `1`/`2` nothing collected, `5` the control test left something changed) |
| `device-survey/scripts/python/sungrow_control_test.py` | **Part B**: writes each control, reads the register back against the specification's scale, watches what the inverter does, and puts everything back. The survey imports it and runs it with `--restart --enable-export-limit --allow-dark --yes --merge-into <document>`; on its own (`survey.sh control ...`, or `make controltest-dry HOST=...` which resolves the whole plan and writes nothing) it has the modes the survey never needs. `--restore <snapshot>` is the way out of a run that died halfway. `--export-scale` asks how this firmware writes 13074 with one write that changes nothing, and does nothing else |
| `device-survey/scripts/python/probe.py` | Probe for Sungrow devices: `mdns`, `sweep <cidr>` (502, 503 for a Logger or iHomeManager, 516 for Modbus over TLS on a WiNet-S or a wallbox — found, not read here; `sungrow_survey.py` reads a wallbox there), `units <host>`, `capabilities <host>`, `dump <host>` |
| `device-survey/scripts/python/blocks.py` | The block read test from a terminal, around the library's `block_test`: which read inside a component fails, and whether it is a fault or contention. `--client library` fails where the integration does; `--client raw` (the library's `raw_client`, a strict socket) names the count a padded frame needs; `--narrow-budget` bounds the narrowing, which is unaffordable on a link where reads time out |
| **`scripts/helpers/`** | **One-off tools** |
| `scripts/helpers/influx_migration.py` | Print Grafana regexes and rewrite recipes for InfluxDB users; connects to nothing |
| `scripts/helpers/review_names.py` | Lay the entity names out for the open naming decision — grouped by subject, each with the entity id it produces and its legacy name. `--markdown` prints the sheet (redirect it into `doc/entity_name_review.md`); `--check` fails when that file has drifted from the names |
| `scripts/helpers/make_brand_icon.py` | Regenerate the integration's `brand/` icons (`--preview` renders a check sheet) |
| `pytest` | Device library + integration tests, no network needed |
| `pytest tests/test_wiki.py` | Lint the wiki: llmwiki's rules, plus every source tracked, every survey ingested, every named path existing, and no address on a page |
| `ruff check . && ruff format .` | Lint and format |
| `mypy` | `--strict` over **the library only** (`packages = ["sungrow_modbus"]`). In `make check` and in CI. The integration is deliberately out of scope: it is typed against Home Assistant, whose own annotations are not strict-clean, so checking it would mean a wall of ignores that hides the findings worth having |

`doc/development.yaml` is the copy-paste runbook — commands, the optional
secrets, the dev login, port forwarding to the desktop and to the LAN.
`doc/development.md` is the fuller guide. `doc/integration_plan.md` is the
plan of record, including the migration work that is still open.

## The survey has two parts, and part B writes

Part A, the capability survey, only reads. Part B, the **control test**,
writes each control, reads it back against the specification's scale, watches
what the inverter does, and puts everything back. It exists because a wrong
scale in `registers.py` is invisible to a readback through the library. The
three legs and the rules the procedure turns on are in
[the control test](.wiki/wiki/concepts/control-test.md) and
[its restore](.wiki/wiki/concepts/control-test-restore.md). These rules are
non-negotiable:

- **The restore is never budgeted, never deadlined and never skipped**, and
  it writes the snapshot's raw word, checked by raw read. The snapshot is
  flushed before the first write. **No snapshot file for a day means no writes
  that day.** Exit 5 is the one code that means a house is left changed.
- **Leg B's scale is hand-typed from V1.1.11, never read from
  `field.scale`.** A column derived from the thing under test proves nothing,
  and `tests/test_control_test.py` makes the two meet.
- **A simulator cannot produce a finding**, and through a WiNet-S only the
  behavioural leg is evidence.

The engine is in the library (`src/sungrow_modbus/control_test.py`), so both
drivers share it: `sungrow_control_test.py`, through the survey, and the
device page's **Run control write test** button.

### Register 13074's write scale is per device

It writes **times ten** on every B001 firmware measured, and 1:1 on
`SAPPHIRE-H_01011.95.03`. It does either only while feed-in limitation
(13087) is on. So it is probed per device, never assumed:
`registers.AsymmetricNumberField`, `inverter.export_scale` and
`number.SungrowExportLimitNumber`. See
[register 13074](.wiki/wiki/entities/register-13074.md).

## How the integration is cut up

`doc/architecture.md` has the diagram and the reasoning; the short version,
because it decides where a change belongs:

- **`config_flow.py` decides, `config_flow_schemas.py` describes.** Schemas,
  option lists and the prose above them live in the second; the steps that
  choose between them live in the first. `_alpha_placeholders` stays in
  `config_flow` and reads `DEVICES_MODE_OFFERED` at call time, so a test can
  patch the flag there.
- **The library has one subpackage per device**: `inverter/`, `battery/`,
  `wallbox/`, each with its `registers` and `device` modules. What spans
  devices -- `addresses`, `discovery`, `dump`, `survey_document`, `survey`,
  `block_test`, `control_test` -- sits at the top.
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
- **The generated `*_descriptions.py` are not hand-edited**: `derived`,
  `number`, `switch` and `select`. `sensor_`, `battery_`, `wallbox_` and
  `external_descriptions.py` are source. `make gen-check` fails on a hand
  edit of a generated one.

## The survey runs on the published library

A tester who has the integration gets **part A on the device page** and a
download link for the document. A contributor without it runs `survey.sh` or
`survey.cmd`, which hand `sungrow_survey.py` to `uv run --script`: uv reads
the script's **PEP 723 header** and fetches a Python and exactly the
`sungrow-modbus` version it pins. So the register map, the decoding and the
survey tables all come from the library; the directory keeps no copy.

Two things follow:

- **The header is the survey's whole install.** Module-level imports in
  `device-survey/scripts/` are the standard library, the sibling modules,
  `sungrow_modbus` and `modbus_connection`, and the header must declare
  every one -- `[tmodbus]` included, since the library depends on bare
  `modbus-connection`. `tests/test_survey_dependencies.py` reads the imports
  and the header and holds them to each other.
- **An unreleased library is tried through the launcher, not around it.**
  `SUNGROW_MODBUS_LIBRARY` makes uv lay a wheel (`--with`) or a source
  folder (`--with-editable`) over the pin; `make scan-local`, `scan-wheel`
  and `controltest-local` set it. The tree and PyPI share a version number,
  so the survey's preamble tells them apart by `direct_url.json` and says
  `NOT a release`. Unset, the launchers behave exactly as a contributor's.
- **The survey can use only what the pinned wheel has.** The pin is the
  version `pyproject.toml` declares, moved by `sync_version.py`, so between
  releases the PyPI wheel lags the tree. `check_pinned_library.py` reads the
  survey's and the control test's imports beside the integration's, so
  `--wheel` gates a release and the no-argument form says what PyPI lacks.

The control test sits beside the survey under the same header and pin, and
has no launcher of its own: the survey imports it, and `survey.sh control
...` starts it. **The survey writes only with leave**: its last question, which
names the forced charge and discharge, the feed-in limitation, the PV cut and
the restart, defaults to no, and a run with nobody at a terminal is a no. One
yes covers all four, and the run then needs nobody at the keyboard (`--yes`), since the
question came a quarter of an hour before the first write.

## Things that will bite you

Each of these is verified in a container or against hardware.

### Environment, versions and the install

- **Home Assistant requires Python ≥ 3.14.2** (2026.9 and 2026.10 alike).
  The devcontainer is `mcr.microsoft.com/devcontainers/python:3.14-bookworm`,
  where Python lives in `/usr/local/python/current` rather than
  `/usr/local/bin`; its `bin/` comes first on the image's `PATH`, ahead of
  the image's own pipx tools, so `requirements_dev.txt`'s pytest, mypy and
  ruff are the ones that run.

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
  not. `ServerDeviceBusyError` (0x06) is an answer that settles nothing, and
  so is 0x04 from a WiNet-S other clients poll (`model.SETTLES_NOTHING`). So
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

### Reading registers, the WiNet-S, and finding devices

Each of these was verified against hardware, and code depends on every one.
Read the page before changing code that relies on it.

| In one line | Page |
| --- | --- |
| An exception response is an answer; a timeout or a lost connection is not. Probes are three-valued, and a fixture raises the real exception type | [a failed read is not a refusal](.wiki/wiki/concepts/failed-read-is-not-refusal.md) |
| 13000's `0x0000` is Running, and a dongle re-encodes the codes | [register 13000](.wiki/wiki/entities/register-13000.md) |
| Addresses are protocol addresses; maps use `reg()`; no literal addresses outside tests | [protocol addresses](.wiki/wiki/concepts/protocol-addresses.md) |
| Firmware is read before anything decides on it; `CONFIRMED_ON_FIRMWARE` only from a watched write | [firmware gating](.wiki/wiki/concepts/firmware-gating.md) |
| A dongle's 0, and an all-NUL string, are not evidence of a capability | [zero means absent](.wiki/wiki/concepts/zero-means-absent.md) |
| 2612 and 2628 send padded frames; add to `layout.py` only from `blocks.py`'s strict measurement | [padded frames](.wiki/wiki/concepts/padded-frames.md) |
| Few sessions, and 90 s of quiet to recover; a short retry is not a retry | [contention](.wiki/wiki/concepts/contention.md) |
| 6100 decides transport: not 13265, and not round-trip time | [transport detection](.wiki/wiki/concepts/transport-detection.md) |
| What a WiNet-S refuses, invents, re-encodes and reads back stale | [WiNet-S](.wiki/wiki/entities/device-winet-s.md) |
| Sweep unit ids, never trust a port; which units answer depends on transport | [identify by what answers](.wiki/wiki/concepts/identify-by-what-answers.md) |
| A wallbox is at unit 3 behind a dongle, or 248 over TLS on 516; over TLS a read starts on a data point's first register | [wallbox](.wiki/wiki/entities/device-wallbox.md) |

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
recorder history and their dashboards, and **both are keyed by
`entity_id`**. Get this wrong and years of history and every dashboard card
break silently. The mechanism is settled and asserted in
`tests/test_recorder_migration.py`, the user's guide is
`doc/integration_migration.md`, and how it works is in
[adopting the legacy entity ids](.wiki/wiki/concepts/legacy-id-adoption.md) and
[the legacy slot of a second inverter](.wiki/wiki/concepts/legacy-slot.md). Breaking
any of these loses somebody's history:

- **Claim the legacy `entity_id` at entity creation.** A rename onto an id the
  recorder already knows is refused, with only a log line.
- **Every ported entity keeps the unit class and `state_class`** of the YAML
  entry it replaces. Otherwise long-term statistics freeze flat while nothing
  looks broken.
- **A second inverter's slot is measured, never guessed, and `None` is not
  `""`.** A slot that could not be answered claims no legacy ids.
- **The `_inv_<n>` suffix goes on the name, not the id**, and the serial
  lookup uses platform `modbus`.

## Hard constraint: a real serial number is never published

**No real device serial goes into anything this repository tracks.** Not a
survey, not a test fixture, not a docstring, not a commit message, not a
comment explaining a bug, and not a wiki page. This repository is public, and
most of the serials that pass through it belong to **other people** who lent
a VPN or sent a reading.

- Every published document carries a **stand-in**,
  `serial_anonymized_hashed`. The real serial and the full address reach only
  the survey's transcript, which is gitignored and never a wiki source.
- `tests/test_no_real_serials.py` matches the **shape** of a serial over every
  tracked file. When a test needs a serial, use `A123456789`, or `A987654321`
  where two must differ. When prose names a device, use the stand-in its
  surveys publish.
- **Addresses** are handled the same way. A document carries
  `ip_address_last_two_octets` only when its owner agreed, and the wiki
  carries none (`tests/test_wiki.py` checks).
- **Consent**: a stand-in serial is not consent. Ask an owner before
  publishing readings from their installation.

How the survey carries this out: [serial anonymization](.wiki/wiki/concepts/serial-anonymization.md).

## Local-only context

Connection details for the maintainer's own inverter are deliberately **not**
in this repo — it is public. They live in his own `secrets.yaml`
(`sungrow_modbus_host_ip`, `sungrow_modbus_device_address`). Use the simulator
on `localhost:5020` unless you specifically need real hardware.

The container **can** reach a LAN inverter outbound with no setup — the Docker
bridge NATs, so it follows the host's routing. Multicast does not cross it, so
mDNS must run on the host. See `real_hardware` in `doc/development.yaml`.
