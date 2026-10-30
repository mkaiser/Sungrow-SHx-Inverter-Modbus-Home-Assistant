# Developing the Home Assistant integration

This is about the **new custom integration** (`custom_components/sungrow_modbus`)
and its device library (`src/sungrow_modbus`), not the YAML package. The
YAML package in `legacy/modbus_sungrow.yaml` is unaffected by anything here.

## Why an integration at all

Home Assistant 2026.9 modernized Modbus. A device integration now collects its
own connection details in its own config flow and asks the `modbus`
integration for a *unit*; integrations pointed at the same host and port share
a single serialized connection, which matters because a Sungrow inverter
accepts only a handful of simultaneous Modbus sessions. Register knowledge
lives in a plain Python library built on
[`modbus-connection`](https://github.com/home-assistant-libs/modbus-connection),
so it can be tested without Home Assistant and without an inverter.

## Getting a dev environment

> [doc/development.yaml](development.yaml) is the copy-paste companion to this
> page: every command in order, the optional secrets, the dev instance's login,
> and how to get the web UI to your desktop and onto the LAN. This page
> explains why; that one is what you paste.


Open the repo in the devcontainer (VS Code: *Dev Containers: Reopen in
Container*). It pins Python 3.14 - Home Assistant 2026.9 requires 3.14.2 or
newer - installs Home Assistant and the tooling via
`scripts/dev/setup.sh`, and forwards ports 8123 (Home Assistant), 5020 (the
simulator) and 8124 (the HACS testbed).

On Windows, clone into a **named container volume** (*Dev Containers: Clone
Repository in Container Volume*) rather than bind-mounting the Windows
filesystem. A bind mount works but makes Home Assistant startup and pytest
noticeably slower.

No devcontainer CLI? The devcontainer is Microsoft's Python image plus three
apt packages, so the same environment is one command:

```bash
docker run --rm -it -p 8123:8123 -p 5020:5020 -v "$PWD:/workspace" -w /workspace \
  mcr.microsoft.com/devcontainers/python:3.14-bookworm bash -lc \
  'apt-get update -qq && apt-get install -y -qq ffmpeg libturbojpeg0 libpcap-dev && scripts/dev/setup.sh && bash'
```

## Continuing a Claude Code session inside the container

The devcontainer bind-mounts the host's `~/.claude` to `/home/vscode/.claude`,
so Claude Code's auth, settings, transcripts and plan files are the same on
the host and in the container. Start a session on either side and it picks up
where the other left off; a container rebuild loses nothing.

The mount source is written as `${localEnv:HOME}${localEnv:USERPROFILE}`.
Exactly one of those is set on any given host, so the same line works on
Windows and on Linux/macOS.

One thing does *not* follow automatically: Claude Code keys project memory by
workspace path, and the workspace is `C:\...` on the host but
`/workspaces/...` in the container, so the two resolve to different project
directories. That is why the durable repo context lives in `AGENTS.md`, the
wiki in `.wiki/` and `doc/integration_plan.md` instead - all committed and
path-independent. `CLAUDE.md`, which includes `AGENTS.md`, is loaded
automatically wherever the repo is opened, and `AGENTS.md` points into the
wiki.

## Day-to-day

| Command | What it does |
| --- | --- |
| `make help` | The shortcuts for everything below; `make check` is the CI gate |
| `scripts/dev/setup.sh` (`make setup`) | Install Home Assistant, the device library (editable) and tooling |
| `scripts/dev/develop.sh` (`make dev`) | Boot Home Assistant on <http://localhost:8123> against `config/`, onboarded as `dev` / `dev` |
| `scripts/dev/simulate.sh` (`make sim`) | Regenerate the register seed and serve it on port 5020 |
| `make dev-bg`, `make sim-bg`, `make stop` | The same two in the background, logging to `/tmp/ha.log` and `/tmp/sim.log`, and stopping them |
| `make forget` | Drop the stored Sungrow config entry, so the next boot starts at *Add integration* |
| `scripts/dev/fetch_references.sh` (`make refs`) | Clone upstream sources into `.reference/` for reading, hassfest included |
| `pytest` | Library and integration tests (no network needed) |
| `ruff check . && ruff format .` | Lint and format |
| `mypy` | `--strict` over the library only |

Add the integration from *Settings → Devices & Services → Add Integration →
Sungrow Modbus*. It offers a network search or an address typed by hand; for
the second, point it at either:

- the simulator: host `localhost`, port `5020`, device address `1`
- a real inverter: its IP, port `502`, and the device address from
  `secrets.yaml` (`sungrow_modbus_device_address`, normally `1`)

The flow identifies what answers rather than trusting the address: it sweeps
units 1-5 for the inverter and finds a battery or wallbox behind it. This
release sets every new entry up as **diagnostics only** -- the entity id
question that devices mode asks is gated behind `DEVICES_MODE_OFFERED` in
`const.py` (see [Reviewing the migration by hand](#reviewing-the-migration-by-hand)).

**A real inverter on your LAN is reachable from the container without any
setup.** The Docker bridge NATs outbound, so the container follows the host's
routing — which is how the reference inverter's register dumps were read. What
does *not* cross the bridge is multicast, so mDNS discovery has to run on the
host; and inbound, which is the web UI's problem rather than the inverter's.
`real_hardware` in [development.yaml](development.yaml) has the details, the
contention warning, and the network-search caveat.

## The simulator

`scripts/generate/generate_simulator_registers.py` reads every Modbus sensor
and switch in `legacy/modbus_sungrow.yaml`, plus the specification registers
in `doc/legacy_entity_map.json` the YAML never read, and writes a register
seed to `scripts/dev/simulator_registers.json`. `scripts/dev/simulator.py`
serves that seed over Modbus TCP, unit 1, input and holding spaces apart.
Seeding from committed records means the simulator cannot drift away from the
register map; the seed is committed because tests decode it, and `make
gen-check` fails when it is stale.

A few registers carry hand-picked values so the simulator looks like an
SH10RT on a sunny afternoon rather than zeroes everywhere: `STRINGS` for the
text fields, `OVERRIDES` for identity, power and bounds, `HOLDING_ONLY` for
the Start/Stop word the control test's restart needs, and `FAULT_WORDS` with
no fault set.

A simulator stores raw words with no scale, so it can exercise the survey
(`make scan-sim`) and the control test (`make controltest-sim`) end to end
but never produce a finding about a real register.

**An iHomeManager** has its own seed, `scripts/dev/simulator_ihomemanager.json`,
hand-written from Sungrow's V1.0.2 document because no reading of one exists
to generate it from. `make sim-ihm-bg` serves it as unit 247 on :5021, and
`make scan-sim-ihm` runs the survey against it. It plants the placeholder
serial in an undocumented gap, so the masking runs end to end;
`tests/test_ihomemanager.py` holds the seed to the map. **A Logger1000**
likewise: `scripts/dev/simulator_logger.json`, `make sim-logger-bg` on :5022
and `make scan-sim-logger`, held by `tests/test_logger.py`.

## Layout

```
custom_components/sungrow_modbus/   Home Assistant integration
src/sungrow_modbus/                 device library (no Home Assistant imports)
  inverter/, battery/, wallbox/       one subpackage per device: registers, device
  ihomemanager/, logger/              registers and document only: read by the survey
  addresses, discovery, survey_document,  what spans devices
  survey, block_test, control_test, dump
tests/                              library and integration tests
scripts/dev/                        dev loop: setup, boot, simulator, HACS testbed
scripts/generate/                   everything that writes a committed file
scripts/release/                    version lockstep and the pinned-library gate
scripts/helpers/                    one-off tools
device-survey/                      published survey documents, and the survey itself
```

The split follows what Home Assistant's Modbus documentation recommends and
what core's `sofar` integration does; [architecture.md](architecture.md) has
the reasoning. The library is published to PyPI as `sungrow-modbus` from this
repository, and the version in `pyproject.toml` must stay identical to the
`requirements` entry in `custom_components/sungrow_modbus/manifest.json`,
because Home Assistant checks the installed version on every start. `make
version VERSION=X.Y.Z` moves both.

## Every script

`make help` lists the shortcuts; this is what each script behind them does.

| Script | What it does |
| --- | --- |
| **`scripts/dev/`** | **The dev loop** |
| `setup.sh` | Install HA, the device library (editable) and tooling |
| `develop.sh` | Boot HA on <http://localhost:8123> against `config/` |
| `ha_onboard.py` | Walk a fresh instance through onboarding over the API, so nobody types `dev`/`dev` into a wizard. Both boot scripts run it in the background; idempotent, and it refuses a non-loopback URL |
| `hacs_testbed.sh` | Boot a **second** HA on :8124 against `config-hacs/`, with HACS installed; see [Testing the install a user actually gets](#testing-the-install-a-user-actually-gets) |
| `ha_http_port.py` | Write a scripted instance's HTTP port where Home Assistant 2026.9 reads it, the `stable` config in `.storage/http`. `http:` in `configuration.yaml` only becomes a pending config that reverts after five minutes unless somebody promotes it. `hacs_testbed.sh` calls it |
| `simulate.sh` | Regenerate the register seed and serve it on :5020 (`simulator.py`, seed in `simulator_registers.json`) |
| `fetch_references.sh` | Clone HA core + libs into `.reference/` (gitignored) |
| `seed_migration_testbed.py` | Make the dev instance look like a house that ran the YAML package for years; see [Reviewing the migration by hand](#reviewing-the-migration-by-hand) |
| **`scripts/generate/`** | **Everything that writes a committed file; each has `--check` but the multi-inverter YAML, which CI regenerates and commits instead** |
| `descriptions.py` | The entity descriptions and names: `derived`, `numbers`, `switches`, `selects`, `strings`, or all five with no argument (`strings` last, since it reads the others) |
| `tables/writes.py` | **Input table**: which registers the integration may write and within what bounds. Feeds the number/switch/select descriptions; `tests/test_writes.py` holds `registers.py`'s writable set to it |
| `tables/naming.py` | **Input table**: the entity-name convention. Feeds `strings.json`, `review_names.py` and the Influx helper |
| `generate_compatibility.py` | Build `doc/compatibility.md` from the committed surveys |
| `generate_simulator_registers.py` | The simulator's seed, from the entity map |
| `generate_second_inverter_config.py` | The `legacy/` multi-inverter YAML files; run by CI on a change to the YAML package |
| **`scripts/release/`** | **Release gates** |
| `sync_version.py` | Single source of truth for the version: moves it into `manifest.json` and into the PEP 723 header of the survey and the control test; `--check` in CI, `--set X.Y.Z` to release |
| `check_pinned_library.py` | Do the integration's `sungrow_modbus` imports resolve against the library version `manifest.json` pins? `--wheel dist/*.whl` asks it of a local build and gates CI; with no argument it asks it of **PyPI**, which is legitimately red between releases |
| **`scripts/helpers/`** | **One-off tools** |
| `influx_migration.py` | Print Grafana regexes and rewrite recipes for InfluxDB users; connects to nothing |
| `review_names.py` | Lay the entity names out for the open naming decision -- grouped by subject, each with the entity id it produces and its legacy name. `--markdown` prints the sheet (redirect it into `doc/entity_name_review.md`); `--check` fails when that file has drifted from the names |
| `make_brand_icon.py` | Regenerate the integration's `brand/` icons (`--preview` renders a check sheet) |

What a contributor is handed, `device-survey/scripts/`, is described in
[device-survey/README.md](../device-survey/README.md#what-is-in-scripts).
`make scan HOST=...`, `make scan-sim`, `make scan-local`, `make scan-wheel`,
`make controltest-dry HOST=...` and `make controltest-local` drive it from this
tree.

## Pitfalls

Each of these is verified in a container or against hardware.

- **Python lives in `/usr/local/python/current`**, not `/usr/local/bin`, in
  the devcontainer image (`mcr.microsoft.com/devcontainers/python:3.14-bookworm`).
  Its `bin/` comes first on the image's `PATH`, ahead of the image's own pipx
  tools, so `requirements_dev.txt`'s pytest, mypy and ruff are the ones that run.
- **Core's `modbus` drives `modbus-connection` with the _tmodbus_ backend,
  not pymodbus.** `import homeassistant.components.modbus` fails outright
  without `modbus-connection[tmodbus]`. `requirements_dev.txt` mirrors the
  exact pins from `homeassistant/components/modbus/manifest.json`; bump them
  together.
- **The version in `pyproject.toml` must equal the `requirements` entry in
  `manifest.json`.** HA checks the installed version on every start and will
  try to pip-install the package if they differ. `sync_version.py --set`
  moves both, and the scripts' PEP 723 pins, **and re-installs the editable
  library** -- HA compares the pin against what is *installed*, and a stale
  install sends pip after a version not on PyPI (`RequirementsNotFound` on
  Add integration).
- **The integration's domain is also the library's import name.** Both are
  `sungrow_modbus`, so `config/custom_components` is a **symlink** to the
  repo's `custom_components/`, the way a real install looks. Putting
  `custom_components/` on `PYTHONPATH` exposes the *integration* as top-level
  `sungrow_modbus`, shadowing the library, and HA reports a circular import
  while loading the config flow, a long way from the cause.
- **The pin is a promise about a published wheel, and an editable install
  cannot test it.** `check_pinned_library.py` checks that every
  `sungrow_modbus` import *and* every device attribute the integration uses
  exists in the pinned version. It only inspects variables it can **prove**
  hold a device -- constructed from `SungrowInverter` and friends, annotated
  as one, or assigned from a `.device` -- because `device` also names
  registry entries and probe dicts, and a gate that cries wolf gets switched
  off. It knows what a device gains from `self.x =` in `__init__` and from
  the keys of a `COMPONENTS` map.
- **A workflow that installs its own tools hides its dependencies.** Anything
  CI needs -- `build` and `twine` included -- is declared in
  `requirements_dev.txt`, so `make ci` runs to the end in a fresh devcontainer.
- **A check nobody runs and a check that cannot run look identical.** The
  library ships a `py.typed` marker, without which mypy refuses the package
  and every consumer silently gets no checking; `mypy` is in `make check` and
  in CI rather than in a target somebody has to remember. It is `--strict`
  over the library only: the integration is typed against Home Assistant,
  whose annotations are not strict-clean, and a wall of ignores would hide
  the findings worth having.

## Porting registers

`legacy/modbus_sungrow.yaml` translates to `Component` fields almost one for
one:

| YAML | Library field |
| --- | --- |
| `input_type: input` | `register_space = "input"` on the component |
| `data_type: uint16`, `scale: 0.1` | `gauge(reg(n), 0.1, signed=False, unit=...)` |
| `data_type: int16` unscaled | `integer(reg(n))` |
| `data_type: uint32`, `swap: word` | `uint32(reg(n), word_order="little")` |
| `data_type: string`, `count: 10` | `string(reg(n), 10)` |
| `nan_value: 0xFFFF` | `nan=0xFFFF` |
| state code decoded in a template | `integer(reg(n))`, decoded in `inverter/derived.py` |
| register written by a template | `writable=True`, plus a row in `scripts/generate/tables/writes.py` |

Fields are declared by the register number in Sungrow's document, through
`addresses.reg()`, which subtracts one for the protocol address the YAML
writes (`address: 4989 # reg 4990`); `tests/test_addresses.py` fails on any
other spelling. Each component is one poll interval in one register space,
and neighbouring fields inside it are pooled into block reads, so grouping
fields by how often they should be polled matters more than grouping them by
address. `tests/test_registers.py` holds every field to
`doc/legacy_entity_map.json`.

## Reviewing the migration by hand

The migration is the one feature a unit test cannot fully judge. Whether the
setup dialog explains the choice well enough to make it, and whether the
history graph really is continuous afterwards, are things you have to look at.
`scripts/dev/seed_migration_testbed.py` fabricates the starting state — the
registry entries `legacy/modbus_sungrow.yaml` leaves behind, plus a month of
recorded readings and hourly statistics under the ids it used:

```console
$ scripts/dev/develop.sh                            # once, to create config/
# stop it
$ python scripts/dev/seed_migration_testbed.py
Registry:   183 entities added (183 in the source)
History:    2880 states over 30 days
Statistics: 2880 hourly rows
$ scripts/dev/simulate.sh &                         # an inverter to talk to
$ scripts/dev/develop.sh
```

The entity id question is asked only in devices mode, which this release
does not offer: set `DEVICES_MODE_OFFERED` in
`custom_components/sungrow_modbus/const.py` to `True` locally first, and do
not commit it.

Home Assistant must be **stopped** while it runs: it writes the entity
registry and the recorder database directly. `--reset` undoes it, so the same
instance can be used to try the other answer. `--from <snapshot>` uses a
registry exported from a real instance instead of the generated entity map —
more faithful, but such a file belongs in `.testdata/`, never in the repo.

## Testing the install a user actually gets

Everything above runs the working tree: `scripts/dev/develop.sh` symlinks
`config/custom_components` to this repository, so the instance on :8123 is
your editor with a UI attached. That is the wrong instrument for one class of
question — *does this install?* A manifest pinning a library version whose
wheel lacks a module the integration imports passes every test, ruff,
hassfest and the release, and fails only in a real install. HACS refusing a
repository whose default branch has no `custom_components/` is invisible
from here entirely.

`scripts/dev/hacs_testbed.sh` (`make hacs`) is the other instrument: a **second**
Home Assistant, on :8124, against `config-hacs/`, with HACS downloaded into
it. Nothing in it is symlinked. HACS installs this integration from the
preview channel, over the network, so what runs there is what was
*published*.

```console
$ make hacs                       # sets up if needed, then boots
$ make hacs ARGS=--setup-only     # prepare it without holding the terminal
$ make hacs ARGS=--update         # re-download HACS first
$ make hacs ARGS=--reset          # delete config-hacs/ and start over
```

It onboards itself (`dev` / `dev`, same as the other instance) and refuses to
run while an instance is already serving that directory, printing the pid to
kill — everything after that check writes to the directory, and one of the
things it writes is a store a running Home Assistant holds in memory.

Two steps are yours, and the script prints them before it boots:

1. **Add integration → HACS**, which asks you to authorise a GitHub account
   with a device code at <https://github.com/login/device>. There is no way
   past it: HACS 2.x has no path through its config flow that skips the
   device step, because it uses the token for GitHub API calls whose
   unauthenticated limit is 60 requests an hour. Any account works. (Its
   *catalogue* no longer comes from GitHub at all — HACS 2.x fetches that
   from `data-v2.hacs.xyz`.)
2. **HACS → ⋮ → Custom repositories**, the preview channel's URL, category
   *Integration*, then **Download** and restart.

What this instance is for is the part you cannot see from :8123:

- **The version HACS shows is a commit hash**, because the channel publishes
  no releases of its own. That is what a bug report should quote, and seeing
  it here is how you learn to ask for it.
- **The library is pip-installed from PyPI** against the pin, on the restart
  after downloading. `RequirementsNotFound` surfaces here and nowhere else —
  `scripts/release/check_pinned_library.py` is the check that catches it earlier.
- **It is not your working tree.** A change you make in this repository does
  not appear there until it reaches the preview channel, which is a commit,
  a green CI run and a sync away. That lag is the point: it is what a user
  is subject to.

Why a separate config directory rather than HACS in `config/`: HACS downloads
into `<config>/custom_components/<domain>`, so through the dev instance's
symlink it would write into this repository over tracked files, and drop its
own `hacs/` directory where hassfest and the test suite would find it. The
preview channel also ships the same domain, `sungrow_modbus`, so two copies
at one path is the conflict `doc/installing_a_preview.md` warns users about
rather than an upgrade.

## The survey on the device page

A capability survey is what this project learns from. A tester with the
integration runs it from a pair of buttons on the device page, with three
diagnostic sensors beside them; a contributor without it runs
`device-survey/scripts/survey.sh` instead:

| Entity | What it is for |
| --- | --- |
| `button.<name>_run_capability_survey` | Starts one. Unavailable while a run is in flight; the runner refuses a second anyway |
| `button.<name>_run_control_write_test` | Part B: the same survey, and then it **writes** to every control and puts each one back. See below |
| `sensor.<name>_survey_progress` | Percent complete. Counted reads, not elapsed time — the same survey is under a second on a cable and minutes over a VPN |
| `sensor.<name>_survey_step` | What is being read right now. **Its recorded history is the point**: 19 probes, the block read test's reads and one assembly step in order — plus 52 band sweeps when a dump was asked for — which is what says *where* a slow link stalls rather than that it did |
| `sensor.<name>_survey_finished` | When the last run ended, with `fields_read` and `has_document` as attributes |

They exist in both setup modes. A *Diagnostics only* entry has no readings at
all, and these five are the entirety of its device page — which is also why
it has one: Home Assistant registers a device only as a side effect of an
entity carrying its `device_info`. The control test is there too: that mode is
for the contributor who has hardware and offered to help, which is exactly whose
inverter this project needs a write measurement from.

### Part B, which writes

The survey answers *what is here* entirely by reading. It cannot answer *and
does writing to it work*, and that second question has a whole class of bug
behind it: `encode` and `decode` share one scale factor, so a wrong factor in
`registers.py` returns the value you wrote, intact, while the inverter acts on
something ten times bigger. The registers mix units on adjacent addresses —
13052 counts in 1 W, 33047 next door in 0.01 kW — which is where such a factor
comes from.

So the control test writes each control and checks it three ways: through the
library, against the **raw register word** compared to a scale typed by hand
from the specification and never read from the map, and by watching what the
inverter actually does. Only the second catches a wrong factor in our code;
only the third catches a firmware that disagrees with the document.

The same engine runs from a terminal — `make controltest-dry HOST=…` first,
which writes nothing — and `doc/development.yaml`'s `control_test` section is
the runbook. What matters if you touch it:

- **the restore is never budgeted, deadlined or skipped**, and it reads before
  it writes, because a restore is a statement about where the register *is*
  rather than about whether a write succeeded;
- **the snapshot is flushed before the first write** and removed only once
  everything is back *and read back*, so one left on disk is the list of what
  may still be changed — in Home Assistant it becomes a repair with a fix flow;
- **the run refuses more often than it runs**, on a stopped inverter, in the
  dark, at a state of charge where a probe value would command a grid charge,
  and it says which. In Home Assistant that guard list is the only protection a
  button press has, since a button gets no confirmation dialog.

`survey.py` owns both parts and holds the state; `survey_document.py` does the
reading and calls back with a fraction and a label; `control_test.py` does the
writing and reports into the tail of the same progress bar; `survey_entities.py`
turns that into states over one dispatcher signal per entry. Nothing in
`survey.py` talks Modbus.

**Three things that are easy to get wrong here.**

The progress sensor has **no `state_class`**, deliberately and with a comment
saying so. A measurement state class makes the recorder keep long-term
statistics, and those are the one thing that outlives the entity: deleting
the config entry takes the entities, the device and their states with it, but
statistics rows survive and become an "entity no longer exists" repair for
somebody who uninstalled weeks ago. Hourly averages of a progress bar are
worth nothing anyway.

The download link is **signed and short-lived** — an hour — and the
notification that carries it is not. Left alone, an hour later there is a
notification in the sidebar pointing at a URL that now 401s, which reads as a
broken integration. So the message names the time, a timer rewrites it when
that passes, and starting a new run cancels the old timer; both notifications
share one `notification_id`, so a stale timer would otherwise stamp
"expired" on a link minutes old. The timer is dropped on unload, or the test
harness calls it a lingering timer and is right to.

The route that does not expire is **Download diagnostics** on the same page.
`diagnostics.py` builds the same document through the same `async_build`,
reading the saved testimony from `entry.options`. Treat the notification as
the convenience and that button as the guarantee.

The raw band sweep is gated **twice, on purpose**. `survey_register_dump` in
the options says the owner is willing to spend the time; `allow_dump=True` on
`async_build` says the caller can afford to wait for it. Only the survey
runner behind the two buttons passes the second, because only it is a
background task with a progress bar. `diagnostics.py` builds the same document and
leaves it off — five minutes of reading behind a download button reads as a
hang, and an owner who enabled the option was answering a question about
surveys. Reading the option directly inside `async_build` would be the
obvious simplification and would break exactly that.

Two switches in the options are called a register dump and they do different
things. *Battery, wallbox and diagnostics* → *Include a raw register dump in
diagnostics* (`CONF_REGISTER_DUMP`) re-reads the addresses the library already
maps, into the diagnostics file, in seconds. *Contribute a capability survey*
→ *Also sweep the raw register bands* (`CONF_SURVEY_DUMP`) sweeps
`sungrow_modbus.dump.DUMP_BANDS`
— 1510 addresses, mostly unmapped — into the survey document, in about five
minutes. Only the second can discover a register. The survey's `--dump` reads
the same bands.

To see any of this against a real run, the recorder is the fastest way in —
the dev instance keeps it:

```console
$ sqlite3 config/home-assistant_v2.db \
    "select m.entity_id, s.state, datetime(s.last_updated_ts,'unixepoch','localtime')
     from states s join states_meta m on s.metadata_id = m.metadata_id
     where m.entity_id like '%survey%' order by s.last_updated_ts"
```

Persistent notifications are **not** states — they live in memory behind the
websocket command
`persistent_notification/get`, so a survey that "produced no notification" is
worth checking there before believing it.

## Naming entities

Entity names are entity ids. With `has_entity_name` set, Home Assistant
slugifies the object id **from the name**, so "Sungrow inverter serial" gives
`sensor.sh10rt_sungrow_inverter_serial` and "Serial number" gives
`sensor.sh10rt_serial_number`. A name is cheap to get right before release and
impossible to change afterwards.

The convention is in [scripts/generate/tables/naming.py](../scripts/generate/tables/naming.py) — sentence case,
a fixed acronym list, no device name at the front, no guessable abbreviations,
and `_raw` entities under `EntityCategory.DIAGNOSTIC`. Do not write a name into
`strings.json` by hand:

```console
$ python scripts/generate/descriptions.py strings
```

`tests/test_naming_convention.py` checks the committed `strings.json` against
the convention rather than against the generator, so an override has to obey
the rules like everything else. If a name genuinely needs to break them, add it
to `OVERRIDES` **with the reason** — the table is short on purpose.

`legacy_name` on each description is the exception and must never be
normalised: legacy mode reproduces a user's existing entity_ids byte for byte,
so the YAML's inconsistency is preserved there deliberately.

## First boot

`scripts/dev/develop.sh` boots against `config/configuration.yaml`, which
deliberately avoids `default_config:`. That keeps the dev instance small:
Home Assistant pip-installs each component's requirements the first time it
sets it up, and `default_config` drags in bluetooth, dhcp, usb, ssdp,
conversation and video handling that a Modbus integration never touches.

Even so, the very first boot installs a handful of packages (the frontend
above all) and takes a few minutes before <http://localhost:8123> answers with
something other than a 404. That is once per container, not once per run:
the first boot logs ~20 setup errors while its dependencies are still
downloading, and the next boot comes up in about two seconds with no errors
at all. If the UI 404s on your very first run, give it a minute
and reload rather than going looking for a bug.

## Superseding the YAML package

The integration replaces `legacy/modbus_sungrow.yaml`, and existing users
must keep their recorder history and their dashboards. Both are keyed by
`entity_id`: the YAML package produces `sensor.total_dc_power`, an
integration entity with `_attr_has_entity_name = True` produces
`sensor.<device name>_total_dc_power`, and getting that wrong breaks years of
data and every dashboard card silently.

So setup offers the choice: **keep the legacy ids**, which claims each one at
entity creation so history simply continues, or **take modern, device-scoped
ids**, which is that plus one registry rename. A rename carries raw states
*and* long-term statistics and is reversible, so neither direction is a
one-way door. Both are asserted against Home Assistant itself in
[tests/test_recorder_migration.py](../tests/test_recorder_migration.py); the
user's guide is [integration_migration.md](integration_migration.md), and
[integration_plan.md](integration_plan.md) has the traps. Read those before
touching entity ids.
