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
  on unit **200** direct or **2** through a WiNet-S. The earlier claim that it
  is "not reachable via WiNet-S at all" was wrong and is measured: it is
  reachable, under a different number.
- ✅ the **wallbox** (AC011E-01 / AC22E-01) — its own device, 32 registers in
  four components, at unit **3** through a WiNet-S or **248** direct. Read
  only; nothing writes to it. Unit 248 is the charger's own RS485 address,
  reachable only through a serial gateway wired to the charger — never over
  Modbus TCP, which is why it has never answered there.
- ⬜ the **iHomeManager** (port **502 *or* 503**, slave 247) — still the only
  one **never measured**, but no longer unfindable and no longer short of a
  map. `identify()` probes input 8000 on unit 247, so a contributor who owns
  one is told what they have rather than that nothing answered, and
  `collect.py` reports it without surveying it. Not 503 alone: Sungrow's
  setting is "Modbus TCP on the iHM", which lands on 502 on some units and
  503 where 502 is busy — so the four sweeps that found nothing on 503 are
  weaker evidence than they looked. And it is **not a gateway**: it forwards
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
the milestone order.

## Do not hand-edit

- `legacy/modbus_sungrow_multiple_inverters_{1,2,3}.yaml` are generated from
  `legacy/modbus_sungrow.yaml` by `scripts/generate_second_inverter_config.py`
  and committed by CI. Edit the source, not the output.
- **`src/sungrow_modbus/registers.py` is generated too**, by
  `scripts/generate_registers.py` from `doc/legacy_entity_map.json`, and
  `make gen-check` fails on a hand edit. Its own header says so; the table of
  commands above does not list the generator, which is how a hand edit gets
  made in the first place. A property the entity map cannot express -- a write
  scale that differs from the read scale, say -- goes in a **stated override**
  in the generator, next to `WRITE_UNITS_PER_COUNT`, not in the output.

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
| `scripts/setup.sh` | Install HA, the device library (editable) and tooling |
| `scripts/develop.sh` | Boot HA on <http://localhost:8123> against `config/` |
| `scripts/ha_onboard.py` | Walk a fresh instance through onboarding over the API, so nobody types `dev`/`dev` into a wizard. Both boot scripts run it in the background; idempotent, and it refuses a non-loopback URL |
| `scripts/hacs_testbed.sh` | Boot a **second** HA on :8124 against `config-hacs/`, with HACS installed, to test the install a user gets. Nothing is symlinked there: HACS downloads the integration from the preview channel, so what runs is what was published, not the working tree |
| `scripts/simulate.sh` | Regenerate the register seed and serve it on :5020 |
| `scripts/fetch_references.sh` | Clone HA core + libs into `.reference/` (gitignored) |
| `scripts/sungrow_control_test.py` | **Part B, from a terminal**: writes each control, reads the register back against the specification's scale, watches what the inverter does, and puts everything back. `make controltest-dry HOST=...` first -- it resolves the whole plan and writes nothing. `--restore <snapshot>` is the way out of a run that died halfway |
| `scripts/sungrow_scan/collect.py` | **The one entry point for a survey** (`make scan HOST=...`, or `make scan-sim` against the simulator): finds the devices, asks what no register can answer, runs the block read test, reads every register, writes the document and a transcript, and prints a maintainer-facing summary. Exit code says what happened (`0` fine, `3` the filename under-claims, `4` the transport is disputed, `1`/`2` nothing collected) |
| `scripts/sungrow_scan/probe.py` | Probe for Sungrow devices: `mdns`, `sweep <cidr>` (502, 503 for a Logger or iHomeManager, 516 for an iHomeManager's TLS port — found, not readable), `units <host>`, `capabilities <host>`, `dump <host>`. Uses the library where it is installed and `portable.py`'s client where it is not, so it runs for somebody who has installed nothing |
| `scripts/sync_version.py` | Single source of truth for the version; `--check` in CI, `--set X.Y.Z` to release |
| `scripts/check_pinned_library.py` | Do the integration's `sungrow_modbus` imports resolve against the library version `manifest.json` pins? `--wheel dist/*.whl` asks it of a local build and gates CI; with no argument it asks it of **PyPI**, which is legitimately red between releases |
| `scripts/generate_entity_map.py` | Derive `doc/legacy_entity_map.json` from the YAML package; `--check` in CI |
| `scripts/generate_registers.py` | Derive the inverter's `Component` classes from `doc/legacy_entity_map.json` — 99 read registers are too many to transcribe by hand, and a scale off by ten produces a plausible-looking number. A property the entity map cannot express goes in a **stated override** here, next to `WRITE_UNITS_PER_COUNT`; `--check` in CI |
| `scripts/generate_sensors.py` | Write the `sensor` descriptions from the same entity map, so an entity cannot quietly disagree with the register it reads or the YAML entry it replaces; `--check` in CI |
| `scripts/generate_derived.py` | Write the entity descriptions for the computed values in `sungrow_modbus.derived`; `--check` in CI |
| `scripts/generate_numbers.py` | Write the `number` descriptions from the write table in `scripts/writes.py`; `--check` in CI |
| `scripts/generate_switches.py` | Write the `switch` descriptions from the write table; `--check` in CI |
| `scripts/generate_selects.py` | Write the `select` descriptions and their option labels from the write table; `--check` in CI |
| `scripts/generate_strings.py` | Write the entity names to the convention in `scripts/naming.py`; `--check` in CI |
| `scripts/influx_migration.py` | Print Grafana regexes and rewrite recipes for InfluxDB users; connects to nothing |
| `scripts/seed_migration_testbed.py` | Make the dev instance look like a house that ran the YAML package for years, so the migration can be reviewed in the GUI |
| `scripts/generate_compatibility.py` | Build `doc/compatibility.md` from the committed fingerprints; `--check` in CI |
| `scripts/generate_scan_plan.py` | Record the library's block reads and register decoding into `scripts/sungrow_scan/scan_plan.json`, so the scanner works without it. Covers the inverter, the SBR pack and the wallbox — the last two marked with the **role** whose unit they answer on rather than a number, because that moves with the transport; `--check` in CI |
| `scripts/sungrow_scan/portable.py` | The stdlib-only Modbus client, register decoder and plan loader the other two build on, and a one-file report users run against their own inverter |
| `scripts/sungrow_scan/blocks.py` | The block read test: which read inside a component fails, and whether it is a fault or contention. `--client library` fails where the integration does; `--client raw` names the count a padded frame needs; `--narrow-budget` bounds the narrowing, which is unaffordable on a link where reads time out |
| `scripts/review_names.py` | Lay the entity names out for the open naming decision — grouped by subject, each with the entity id it produces and its legacy name. `--markdown` prints the sheet (redirect it into `doc/entity_name_review.md`); `--check` fails when that file has drifted, which it silently had by 47 entities |
| `scripts/make_brand_icon.py` | Regenerate the integration's `brand/` icons (`--preview` renders a check sheet) |
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

The engine is in the library so both drivers share it: `scripts/sungrow_control_test.py`
and the `Run control write test` button on the device page, which runs part A
then part B and publishes both in one fingerprint document (`control_test`,
schema 19).

### Rules the procedure turns on

- **The restore is never budgeted, never deadlined and never skipped.** Every
  early exit goes through it. The snapshot is flushed *before the first write* --
  `.testdata/control-tests/` from the CLI, HA's own store from the integration --
  and removed only once everything is back **and read back**. A leftover
  snapshot on the next setup becomes a repair. Corollary worth keeping: **no
  snapshot file for a day means no writes that day.**
- **A restore is a statement about where the register is, not about whether a
  write succeeded.** It reads before it writes. Reporting a register as
  unrestored when it had held its original value the whole time was the worst
  false alarm this tool has produced -- exit 5 is the one code meaning a house
  is left changed.
- **Probe values must be able to show a decade error.** Both `10*v` and `v/10`
  have to stay inside the accepted range, or the error can only surface as
  exception 0x04 -- which is also what a legitimately out-of-range value
  returns, so it is not evidence. `battery_max_soc` has no such window at all
  (50..100) and the report says so rather than claiming a pass.
- **What the behavioural checks command is a stated constant**, `FORCED_EFFECT_W`
  (1250 W), clamped to the register's live bounds. It was derived from the
  battery's own ceiling, and the derivation borrowed `choose_probe`, which
  escapes the decade window once earlier probes have spent it -- resolving a
  **5800 W forced charge against a 5883 W pack** at a real house. A number that
  must be reconstructed from three functions is a number nobody checks.
- **A pack's ceiling moves, so a clamp is normal near a full battery.** The same
  house read 10000 W in the afternoon and 3200 W at 99.8 % that night. A
  manufactured discharge aims `FORCE_EXPORT_HEADROOM` below the ceiling and
  accepts a clamp within `CLAMP_TOLERANCE`, because the device saying "I will
  give you 3150 of the 3158 you asked for" is a yes. Decade verdicts are
  classified **first** and excluded, so the tolerance can never absorb the error
  the procedure exists to find.
- **Leg B on 13074 needs the mode lifted, and the run lifts it.** The register
  ignores writes entirely while feed-in limitation is off, so at any house with
  it off -- which is most of them -- the probe read `UNCHANGED` and the one leg
  that can catch a cap read a decade *too large* never ran. So the register
  carrying the only firmware quirk this project has found was also the one whose
  readback was routinely unavailable. `_lift_export_mode` switches it on for
  that probe alone, and back to **the snapshot's word** the moment the register
  is restored -- seconds, not the phase, because while it is up the house is
  capped at whatever 13074 is holding, which is a probe value. Only with
  `--enable-export-limit`, because it curtails a real house.
- **The button always runs `allow_dark`, and the CLI does not.** A CLI user
  chose the moment; somebody on Home Assistant OS has no terminal, so a run
  refused for want of sun is a run they can never make -- and in a German
  December that is most of the day. What the refusal costs them is the readback
  half, which is the half that finds a factor-10 error and does not care whether
  the sun is up. The behavioural half still self-skips and says why.
- **Under fluctuating PV the answer is a bracket, not a model.** Before and
  after are two readings of the same undisturbed house; when they disagree the
  run reports `INCONCLUSIVE` and never a failure. Medians, not means: a cloud
  edge is a step change and an MPPT search is a spike, so a mean survives
  neither.
- **The export limit check can only catch a decade too small.** A cap read ten
  times too large leaves the export where it was, indistinguishable from the
  write doing nothing. Leg B is the only way to catch that direction.
- **The charge-ceiling check is the only safe behavioural test of a
  state-of-charge limit**, because of its direction: lowering `max_soc` under a
  charging battery **stops** a charge. Raising `min_soc` above the battery is an
  instruction to buy electricity, which the guards refuse. Read a `CONFIRMED`
  narrowly: it shows the register is a ceiling the inverter enforces, not that
  its scale is right, since 95 % and 9.5 % both stop a charge.
- **A simulator cannot produce a finding.** It stores raw words with no scale,
  so legs A and B agree there by construction and leg C has no signal. Hence
  `--simulated`, which skips the behavioural phase and stamps the report.
- **A run holds this entry's own polling off the inverter.** Every coordinator
  on an entry shares one serialized connection, so a survey that ran while they
  kept firing measured the inverter *and* the contention it was causing.
  `SungrowRuntimeData.async_paused()` is the mechanism, `polling_paused` the flag
  each coordinator reads. Paused at the *poll* rather than by clearing
  `update_interval`, which does not cancel the timer already scheduled. A paused
  coordinator returns what it last had, so entities hold their values.
- **A Modbus stop is nearly instant and the recovery is not**: **2 s** to
  stopped, **about four minutes** back to `0x0040 Running`, ~20 s more to
  generate. Half the wait is `0x0020 Starting`, which contains neither "stop"
  nor "running" and so belonged to neither set -- the first version of the wait
  told owners to start the machine by hand while it was starting perfectly well.
  `is_starting` exists for that; the deadline is seven minutes.

### Register 13074 reads in watts and writes in tens of watts

The factor-10 error the whole procedure was built to find, and the one live bug
it has produced. Measured six times on the reference SH10RT with feed-in
limitation **on**, including values no rounding could produce (123 → 1230,
47 → 470), then replicated at two further houses on two more models over both
transports.

The read side is right and agrees with its own bounds: 13074 reads 10000 against
a 10000 W maximum from register 5623. **The write side is a decade out**, so one
scale for both directions -- what every other register in this map wants -- sets
ten times what the user asked for. Somebody limiting export to 900 W gets 9000 W.

It also explains every refusal on this register: the multiply happens **before**
the range check, so 3400 becomes 34000, fails against a 10000 W maximum and
returns exception 0x04. Writing 1000 is how you actually put 10000 back.

**Only while feed-in limitation is on.** With 13087 at 0x55 the register ignores
writes entirely -- no exception, no change. A register that is inert in one mode
and wrong by a decade in the other is why `UNCHANGED` is in the verdict
vocabulary at all, and it is what the fix is still blind to: set a limit with
that switch off and you get no limit and no error.

**Fixed for the integration** by `registers.AsymmetricNumberField`, a stated
override in `scripts/generate_registers.py` (`WRITE_UNITS_PER_COUNT`). `scale`
stays 1 because that is what the register *contains*; only the write side is
divided. It cannot live in `modbus-connection` -- `NumberField` shares one
`scale` by design and that library is Home Assistant core's dependency.

**The YAML package on `main` still has it**, and has had for years:
`number.export_power_limit` writes `{{ value | int }}` to the same register.
That is the one place a user of the shipping package is worse off than a user of
the alpha.

`doc/integration_plan.md` has the measurements, the replications and the two
hardware confirmations -- raw word over a cable, and behaviour through a dongle.

## How the integration is cut up

`doc/architecture.md` has the diagram and the reasoning; the short version,
because it decides where a change belongs:

- **`config_flow.py` decides, `config_flow_schemas.py` describes.** Schemas,
  option lists and the prose above them live in the second; the steps that
  choose between them live in the first. One thing deliberately stayed behind:
  `_alpha_placeholders` reads `DEVICES_MODE_OFFERED` at call time so a test can
  patch the flag on `config_flow`, and moving it would put it beyond that
  patch's reach **while every test still passed**.
- **Anything that must work without Home Assistant lives in `src/`.** The
  control test's engine is there for that reason; what is here is a snapshot
  store, a shutdown hook, a progress callback and the options.
- **`SungrowSubDeviceCoordinator` is what the pack and the wallbox share.**
  Both are reached through the inverter's connection, hung off it with
  `via_device`, and identified by *its* serial because neither reports a usable
  one. The subclasses hold only what differs: how a model name is found, and
  how often each block is worth reading.
- **`async_setup_entry` is a list of named steps**, not a wall. It was 177
  lines; each step is now a function that can be read on its own.
- **The generated `*_descriptions.py` are not hand-edited**, like
  `registers.py`. `make gen-check` fails on it.

## The survey is installed, not posted

There was a `sungrow_scan.zip`: the whole `scripts/sungrow_scan/` directory,
packaged so a contributor could unpack it and run the survey with a bare
Python. It was retired once `scripts/hacs_testbed.sh` made the HACS install
testable, because a tester who has the integration gets **part A on the device
page** and a download link for the document, which is the same evidence with
none of the unpacking.

Two things survived it and are not the same thing:

- **`portable.py` is still handed over on its own.** It is one file, stdlib
  only, read-only by construction -- only the two Modbus *read* function codes
  exist in it -- and it is what `doc/compatibility.md` points a contributor at
  when they will not install anything. `tests/test_scan_is_standalone.py` keeps
  it importable by itself.
- **The no-third-party-imports rule still covers the whole directory**, because
  `collect.py` and `blocks.py` import `portable`. A convenient
  `from sungrow_modbus import ...` anywhere in there reaches the file that is
  still downloaded alone. The zip is gone; the boundary it protected is not.

What went with it: `make zip`, `make zip-verify`, `make zip-sim`, the CI step
that unpacked it, and the *runtime* half of the standalone proof. The static
half -- reading the imports -- is what remains, and it is the half that catches
the mistake anyone would actually make. `make scan-sim` replaces `zip-sim`.

## Things that will bite you

These each cost real debugging time. They are not guesses — each was hit
and verified in a container or against hardware.

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
  differ. Never edit either by hand: `python scripts/sync_version.py --set X.Y.Z`
  moves both, `--check` is enforced in CI, in pytest and at release.
- **The integration's domain is also the library's import name.** Both are
  `sungrow_modbus`. So `config/custom_components` is a **symlink** to the
  repo's `custom_components/`, the way a real install looks. Putting
  `custom_components/` on `PYTHONPATH` instead — which `scripts/develop.sh` used
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
- **The pin is a promise about a published wheel, and an editable install
  cannot test it.** `--check` above only compares two version *strings*. What
  it cannot see is the integration importing a library module that the pinned
  version does not have -- which happened between a1 and a2 with
  `sungrow_modbus.fingerprint`, passing every test, ruff, hassfest and the
  release, and failing only in a real install. `scripts/check_pinned_library.py`
  is the check: `--wheel` against a local build gates CI, and with no argument
  it asks the same of PyPI, which is legitimately red mid-development.

  **It checks attributes too, since 2026-09-19.** An import resolving was only
  half the promise: a wheel can satisfy every `from sungrow_modbus import X`
  and still lack the method somebody added beside it, which fails at runtime on
  an inverter rather than in CI. That is not hypothetical -- `field_names`,
  `probed_capabilities` and `inverter_serial` were added to the library and used
  from the integration in one sitting, with this script green throughout.

  It only inspects variables it can **prove** hold a device: constructed from
  `SungrowInverter` and friends, annotated as one, or assigned from a
  `.device`. Anything else is left alone, because `device` is also what Home
  Assistant calls a registry entry and what the config flow calls a dict of
  probe results -- and a release gate that cries wolf gets switched off. It
  also has to know what a device gains from `self.x =` in `__init__` and from
  the keys of a `COMPONENTS` map, neither of which appears in a class body.
- **A repair issue is `title` + `description` *or* `title` + `fix_flow`, never
  both.** Home Assistant's translation schema makes them mutually exclusive,
  and `hassfest` says so as *"two or more values in the same group of exclusion
  'fixable'"*, which does not obviously mean "delete the description". For a
  fixable issue the text belongs in the fix flow's step, where the person
  reading it is about to press the button.

  **Run it before tagging**, and run it *locally* rather than trusting the
  branch to be green:

      python -c "import sys; sys.path.append('.reference/core'); \
        sys.argv=['hassfest','--integration-path','custom_components/sungrow_modbus',\
        '--action','validate']; \
        from script.hassfest.__main__ import main; raise SystemExit(main())"

  Appended to `sys.path`, not prepended, so the **installed** Home Assistant
  wins: `.reference/core` is a partial clone with no `homeassistant.generated`,
  and putting it first fails on an import that has nothing to do with this
  integration. This repository has already released a tag on a red hassfest
  once; it is two seconds to check.
- **A broad `except` without a traceback is a silent failure with extra steps.**
  Three places caught `Exception` and logged only the message, and the worst was
  the one that matters most: a **failed restore** in `repairs.py`, which means
  somebody's inverter is still carrying a test's values and this line is the
  only record of why. `diagnostics.py` had no logger at all and put the error
  inside a downloaded JSON file, where it is held by the one person who cannot
  act on it. Use `_LOGGER.exception`; keep the short form for whatever a user
  reads in a dialog. A bare `KeyError: 'realtime'` names nothing.
- **`make ci` could not run in a fresh devcontainer.** It is documented as
  "the full CI job", and it died on `twine: not found` -- because the GitHub
  workflows install `build` and `twine` themselves with
  `pip install --upgrade build twine`, and `requirements_dev.txt`, which is
  what `scripts/setup.sh` installs, listed neither. So the one command that
  claims parity with CI had never been run locally to the end. Both are
  declared now. The general shape: **a workflow that installs its own tools is
  a workflow whose dependencies are invisible to everybody else.**
- **A type checker with nothing to check reports success-shaped nothing.**
  `make typecheck` existed, was documented, and had **never checked a single
  file**: without a `py.typed` marker mypy refuses the package outright, and
  PEP 561 says an unmarked package is untyped, so every consumer was silently
  getting no checking either. The marker is one empty file, it ships in the
  wheel, and adding it surfaced 24 strict errors in code that had passed every
  gate for months. The lesson is the shape of the failure, not the fix: **a
  check nobody runs and a check that cannot run look identical from the
  outside**, which is why `mypy` is in `make check` and in CI now rather than
  sitting in a target for somebody to remember.
- **`PARALLEL_UPDATES` is 1 on the write platforms, and 0 everywhere else.**
  Not a style choice. Everything on this endpoint is already serialized behind
  one connection, so two writes issued at once do not go faster -- they queue,
  and the second one's timeout starts while it is still waiting. And these
  registers **interlock**: `battery_min_soc` and `battery_max_soc` are refused
  if they cross, so an automation that sets both in one call has an ordering
  that matters and must not be raced. `sensor` and `binary_sensor` are 0
  because the coordinator does their polling and the entities never talk to
  the inverter; `button` is 0 because a press schedules the run and returns,
  and the runner refuses a second run itself.
- **A first boot in a fresh container logs ~20 setup errors** while HA
  downloads component requirements, and the UI 404s. The next boot is clean
  in ~2s. Not a bug.

### Reading registers

- **Register 13000 does not mean what zero looks like it means: `0x0000` is
  "Running".** The whole map is in `derived.RUNNING_STATES`, and the obvious
  guess -- that zero is off -- is wrong. Guessing it cost a first draft of the
  control test a guard that refused to run on every healthy inverter, and would
  have gone on to mistake a working inverter for a stopped one during a
  restart. Both sets are now derived from the labels rather than typed out.
- **Addresses are protocol addresses**, one below the register number in
  Sungrow's document and in the YAML comments (`address: 4989 # reg 4990`).
- **Ask the inverter, do not infer.** Register 5002 reports the output type
  (0 single, 1 3P4L, 2 3P3L); 5000 is the device type code. Sungrow's own
  protocol document also warns that some measuring points are *not*
  forwarded by WiNet-S over TCP/IP, so capability varies by transport too.
- **`swap: word` in the YAML means `word_order="little"`** in the library.
  Sungrow sends 32-bit values low word first.
- **Not every register answers.** An SH10RT returns 0xFFFF for MPPT3/4, and
  battery blocks are absent without storage. A poll losing one block is
  normal; that is what `UpdateReport` is for.
- **An empty string is a reading of nothing, not a reading of "".** Sungrow
  fills a UTF-8 field it cannot answer with 0x00, and unlike 0xFFFF that is
  not declared per field, so it decodes to `""` and sails through as a value.
  `present()` in `model.py` maps it to None — without it a capability probe
  counts an absent Sungrow battery's firmware string as evidence of one.
- **Some registers come back in a padded frame.** At 2612 and 2628 the
  inverter sends a frame sized for **15 registers while declaring the correct
  byte count** — `mbap_len` 33 against `byte_count` 22 for a request of 11.
  The data is right; the frame is not, and `modbus-connection` validates
  against the MBAP length and rejects the whole answer. Asking for exactly 15
  makes the two agree, which is why `layout.COUNTS` works and why it is a
  workaround rather than a correction. Because the library pools neighbours
  into one block read, those two fields failed the whole 58-register
  `slowest_input` request and left **36 unrelated entities permanently
  empty**.
- **A lenient Modbus client will tell you the register is fine.** The first
  diagnosis of the above was wrong for a day because a raw-socket probe trusts
  `byte_count` and reads these registers perfectly, while the shipping stack
  cannot read them at all. `scripts/sungrow_scan/blocks.py` is deliberately as strict
  as the shipping stack, and reports both numbers plus the count that
  reconciles them. Add to `scripts/layout.py` only from *its* measurement.
- **A Sungrow accepts very few simultaneous sessions, and the recovery is
  90 seconds of quiet.** This is the most common practical failure here: it has
  killed whole runs, twice, before a single register was written.

  Its signature is a *progressive* one, and that is what tells it from a bad
  block. Reads died at 5010, then 5114, then 5241 — each retry reaching a
  little further into the poll before the link dropped. A bad block fails at
  the same address every time.

  Two consequences. **A short retry is not a retry**: a three-second backoff
  spends every attempt inside the window where nothing can work, which is why
  the control test's opening reads back off **5, 20, 45 and 90** seconds. And
  **the contention is often self-inflicted** — a probe and two runs opened back
  to back, on top of a polling YAML package. "It worked yesterday" says nothing
  about the link, only about how many sessions have recently been spent.
- **A failed read does not always fail quickly, and that changes what a
  diagnostic costs.** Three houses refuse an unmapped register with exception
  0x02 in milliseconds. On a fourth, read over a VPN, the same reads instead
  produced `Response timeout after 10.0 seconds` and `Connection lost before
  response was received` — so with `--attempts 3` every failed read cost 30
  seconds. Worth stating what this does **not** establish: from this end a
  silent inverter and a tunnel that lost the answer look identical, so a
  timeout is not evidence about the register the way an exception 0x02 is.
  Either way the cost is real. Narrowing a failing block walks a binary tree
  over it, about 29 reads for fifteen registers — free on the first three
  links, a quarter of an hour on the fourth. Four such blocks outran a
  survey's own cap and the run was killed **before writing a document**.
  Hence `blocks.NARROW_BUDGET`, which bounds the whole narrowing phase,
  divides it across the blocks that failed, and marks what it did not reach
  rather than reporting a wide range as if it were narrow. When reading a
  survey taken over a slow link: check for `not narrowed` before believing a
  range, and do not put a timeout-only finding in `scripts/layout.py`.

### What a WiNet-S does, and does not

- **A WiNet-S does not forward input 2612 or 2628** — the sub-controller and
  battery firmware strings. Both refuse with exception 0x02, three attempts
  out of three, and both read perfectly over a cable on the same machine.
  Replicated across two houses, two inverter models (SH8.0RT-V112, SH10RT-20)
  and two dongle firmwares (P043, P040), against two direct-LAN readings where
  all 27 blocks answer — so this is what the dongle does, not what one machine
  does. It is therefore **not** a `layout.ISOLATE` case: isolating them would
  cost every direct-LAN user a per-field read for a dongle's behaviour and
  still leave a dongle user without the fields. It belongs in capability
  gating by transport. The same pairing shows a dongle forwarding **1020 of
  1510** dumped addresses where a cable forwards 1461, twice, to the address.
- **A WiNet-S also answers an empty string where the inverter refuses the
  read.** Measured on one SH10RT-V112 read both ways within six minutes, with
  nothing else polling: input 13249, 13264 and 13279 — the inverter, module
  and battery firmware strings — **fail 3/3 on the inverter's own LAN port**
  and answer through its dongle, with every character 0x00. So `present()`
  maps them to None and the fields are absent either way; the cable refuses
  the read, the dongle invents an empty answer for it. The same pair refuses
  2612 and 2628 through the dongle while the cable reads them, so the two
  paths fail *complementary* sets of blocks. Consequence for capability
  probing: **"the block answered" is not evidence.** A dongle can answer
  without knowing, which is what `ZERO_MEANS_ABSENT` handles for numbers and
  the emptiness check in `present()` handles for strings.
- **A WiNet-S answers 0 where the inverter answers 0xFFFF**, which invents
  capabilities: measured on one inverter read both ways, the dongle granted
  MPPT3, MPPT4 and a second meter channel that its own LAN port correctly
  refused — ten entities reporting zero forever. `ZERO_MEANS_ABSENT` in
  `capabilities.py` is the guard. It costs a real third tracker its entities
  until sunrise, which is affordable only because capabilities are re-probed
  every poll and the entry reloads when they **grow**; nothing ever removes an
  entity, so granting on zero has no recovery at all.
- **WiFi versus Ethernet on a WiNet-S is not determinable.** Settled against a
  controlled pair — one dongle, read wired then over WiFi — with a nil
  structural diff, and **extended to writes on 2026-09-19**: the same control
  test over each of bar12's two interfaces dropped the same four registers and
  accepted the same five. Latency cannot stand in either: direct-LAN medians span
  2.0-61.5 ms and WiNet medians 24.3-48.3 across four houses, and one house's
  direct link is slower than its own dongle. Register 6100 does distinguish
  direct from dongle, 9/9 — and register 13265 names the module that is
  *fitted*, which is not the same as the module in the path.
- **A WiNet-S forwards a write and then reads it back stale, and waiting does
  not help.** Settled at the one site with both a cable and a dongle to one
  inverter. The two paths disagreed *before* anything was written -- 33047 read
  450 through the dongle and 440 over the cable, same minute -- and a write sent
  through the dongle arrived: 430 written over it, and the cable then read 430,
  while the dongle went on reporting 450. Polled every 5 s for **two minutes**
  it never once reported a value the cable had confirmed, and the figure it kept
  returning was **hours** old. So there is no settling time to wait out, and
  offering one would only make a stale answer look ripe.

  **This replaces an earlier claim that a dongle may drop a write entirely.** It
  does not; the write lands and the readback is stale. The four bar12 readings
  that produced that claim are not evidence of anything and stay unresolved.

  **What it costs the control test:** leg A cannot tell a dropped write from a
  stale read, and leg B reads the raw word over the same path. **Only leg C
  survives a dongle**, which is how the factor-10 error was confirmed at bar12
  while its readback reported nothing. A run through a dongle says so above its
  readback table, where a reader skimming for `matched` will see it.
  `identify` has the discriminator: **input 6100 answers on a cable and is
  refused through a dongle.**
- **A WiNet-S serves Modbus over TLS on port 516, and it works.** Measured at
  two houses on two dongle firmwares, and it corrects what the web says: this
  was written up from
  [discussion #571](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/discussions/571)
  as an *iHomeManager* port and it is not one. It was open on both dongles and
  **neither inverter's own LAN port**, at a house with no iHomeManager at all.
  It is genuinely Modbus, genuinely TLS 1.2, and reads real registers; a plain
  socket gets the connection accepted and then closed, which is why it looks
  dead without a TLS client.

  **It is not a workaround for what a dongle will not forward.** Inputs 2612 and
  2628 refuse with exception 0x02 over TLS exactly as on 502, and the SBR's cell
  block refuses on both. Same firmware behaviour behind a different wrapper.
  Rapid reconnects exhaust it exactly as they do on 502, so a failed handshake is
  usually a fact about session count, not about TLS.

  **Its certificate looks baked into the firmware** -- identical subject, issuer
  and thirty-year validity on two unrelated houses -- which would mean the
  private key ships with every dongle and this TLS authenticates nothing. **Not
  proven**: the two hashes compared are two interfaces of one dongle. A hash from
  a third site would settle it. `collect.py` sweeps 516 and reports it; reading
  it would need a TLS client the survey does not have, and on this evidence
  verifying the certificate would achieve nothing. Detail in
  `doc/integration_plan.md`.

### Finding devices

- **An open port 502 is not an inverter, and unit 1 is not always where it
  is.** Both halves measured on 2026-09-09 at one house, by sweeping the /24
  rather than assuming. Of five endpoints answering on 502, four were the two
  inverters and their two dongles — and one of those four answers on unit
  **2**, because a cluster slave's own device address is 2 and unit 1 there
  times out. `identify()` asked unit 1 and gave up, so that inverter was
  reported absent; it now sweeps `IDENTIFY_UNITS` (1, then 2-5) and returns
  which unit answered, paying the extra probes only where the first fails.
  The fifth endpoint was **not a Sungrow at all**: it refuses input 4989 on
  every unit with exception 0x02, ignores the unit id entirely, and answers
  only registers 0-19. So identify by what answers, never by an open port —
  and `identify`'s error names the exception type, because a refusal and a
  timeout lead to different next steps. Nothing answered on **port 503** on
  that subnet, so the iHomeManager still has no measurement at any house.
- **Which unit ids answer depends on the transport.** On one SH8.0RT the SBR
  answered unit 200 on the LAN port and unit **2** through the dongle, while
  the wallbox answered unit 3 *only* through the dongle. One config entry is
  one endpoint, so a house like that may need two entries to see everything.
  Re-measured on the same machine on 2026-09-08, both paths within four
  minutes — the pair is in `doc/device-fingerprints/`. Replicated the same
  day at a second house, on an SH10RT-20 whose SBR answers unit **2** through
  its dongle and nothing at 200.
- **A wallbox is only reachable through an endpoint that already answered, even
  when it has its own LAN cable.** Measured at a site whose owner confirms a
  cable into the wallbox: a full sweep of the /24 found Modbus TCP on exactly
  two addresses, the inverter and its dongle, and the wallbox answered only as
  unit 3 behind the dongle -- never at 248, never on an address of its own.
  Nothing answered on 503 either, so no iHomeManager. **A config flow therefore
  cannot find a wallbox by sweeping for it; it has to ask the endpoints it
  already has.** Its registers are undocumented by Sungrow;
  `doc/wallbox_registers.md` is what three independent measurements agree on,
  and the survey decodes 32 of them into every fingerprint. One register, 21313,
  is nameable by nobody.

### Shipping it

- **HACS reads the *default branch* unless there is a stable release**, so a
  pre-release-only repository whose integration is not on the default branch
  cannot be added to HACS at all. Read out of HACS's source, not assumed:
  `version_to_download()` in `repositories/base.py` consults
  `data.last_version` -- set only from the first release that is **not** a
  pre-release -- then a user-selected tag, then `default_branch`. It never
  consults `data.prerelease`; `show_beta` only changes which versions are
  offered *after* registration. `repositories/integration.py` then looks for
  the first directory under `custom_components` at that ref and raises
  *"Repository structure for main is not compliant"* when there is none --
  which is this repository exactly, since `main` is the YAML package. So
  "cut a release" is not the same as "available in HACS", and the fix is
  either the default branch or a stable version, never a `show_beta` hint to
  the user. The third way out is the one taken: a **preview channel**, a
  second repository whose default branch *is* the integration, synced by
  `doc/preview-mirror/sync.yml`. `scripts/hacs_testbed.sh` installs from it
  the way a user does. Worth knowing before sending anybody there: **HACS
  itself requires a GitHub account** -- its config flow hands straight to a
  device-code step with no path around it, because it uses the token for
  GitHub API calls limited to 60 an hour unauthenticated. Its catalogue does
  not come from GitHub any more (`data-v2.hacs.xyz`), but the account is
  still mandatory.

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
- **The suffix goes on the name, not the id.** The generator writes
  `Total DC power inv 2` and Home Assistant slugified that. Appending `_inv_2`
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
  serial, values and key lists alike — added after `sungrow_inverter_serial`
  reached a published document's `fields_read_individually`;
- a wallbox's serial sits two registers below the model name, so
  `wallbox.probe_units` reads the **name**, keeping a serial out of a
  capability probe entirely. It is masked at the publishing boundary too,
  after `A25A…` was once published as the words `[16690, 13633]`.

**And the source tree is checked, because for a while it was not.** Those
protections all guard *documents*. Over one session six real serials reached
test fixtures and docstrings — three houses' worth belonging to other people —
and were a `git push` away from publication. Every one was a fixture or an
illustration and not one needed to be real.
`tests/test_no_real_serials.py` now asserts it over every tracked file: it
matches the **shape** of a serial rather than embedding real ones, and
requires each hit to be on a list of strings known to be invented. A new
serial in a fixture fails the suite until somebody adds it there deliberately,
which is the moment to ask where it came from.

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
