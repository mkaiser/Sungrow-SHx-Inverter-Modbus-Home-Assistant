# Developing the Home Assistant integration

This is about the **new custom integration** (`custom_components/sungrow_modbus`)
and its device library (`src/sungrow_modbus`), not the YAML package. The
YAML package in `modbus_sungrow.yaml` is unaffected and keeps working as it
always has.

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
`scripts/setup.sh`, and forwards ports 8123 and 5020.

On Windows, clone into a **named container volume** (*Dev Containers: Clone
Repository in Container Volume*) rather than bind-mounting the Windows
filesystem. A bind mount works but makes Home Assistant startup and pytest
noticeably slower.

No devcontainer CLI? The devcontainer is a stock image plus three apt
packages, so the same environment is one command:

```bash
docker run --rm -it -p 8123:8123 -p 5020:5020 -v "$PWD:/workspace" -w /workspace \
  python:3.14-bookworm bash -lc \
  'apt-get update -qq && apt-get install -y -qq ffmpeg libturbojpeg0 libpcap-dev && scripts/setup.sh && bash'
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
directories. That is why the durable repo context lives in `CLAUDE.md` and
`doc/integration_plan.md` instead - both are committed, path-independent, and
`CLAUDE.md` is loaded automatically wherever the repo is opened.

## Day-to-day

| Command | What it does |
| --- | --- |
| `make help` | The shortcuts for everything below; `make check` is the CI gate |
| `scripts/setup.sh` | Install Home Assistant, the device library (editable) and tooling |
| `scripts/develop.sh` | Boot Home Assistant on <http://localhost:8123> against `config/` |
| `scripts/simulate.sh` | Regenerate the register seed and serve it on port 5020 |
| `scripts/fetch_references.sh` | Clone upstream sources into `.reference/` for reading |
| `pytest` | Run the device library tests (no network needed) |
| `ruff check . && ruff format .` | Lint and format |

Add the integration from *Settings → Devices & Services → Add Integration →
Sungrow Modbus*, then point it at either:

- the simulator: host `localhost`, port `5020`, unit id `1`
- a real inverter: its IP, port `502`, and the unit id from `secrets.yaml`
  (`sungrow_modbus_device_address`, normally `1`)

**A real inverter on your LAN is reachable from the container without any
setup.** The Docker bridge NATs outbound, so the container follows the host's
routing — which is how the reference inverter's register dumps were read. What
does *not* cross the bridge is multicast, so mDNS discovery has to run on the
host; and inbound, which is the web UI's problem rather than the inverter's.
`real_hardware` in [development.yaml](development.yaml) has the details, the
contention warning, and the network-search caveat.

## The simulator

`scripts/gen_simulator_registers.py` reads `modbus_sungrow.yaml` — still the
most complete description of the SHx register map we have — and writes a
register seed to `scripts/simulator_registers.json`. `scripts/simulator.py`
serves that seed over Modbus TCP. Seeding from the YAML package means the
simulator cannot drift away from the register map the integration is being
ported from.

A few registers carry hand-picked values (in `OVERRIDES` and `STRINGS`) so an
inverter that looks like an SH10RT on a sunny afternoon comes back rather than
zeroes everywhere.

## Layout

```
custom_components/sungrow_modbus/   Home Assistant integration (thin)
src/sungrow_modbus/          device library (no Home Assistant imports)
  components.py                  register maps as typed Component classes
  device.py                      SungrowInverter, composed of components
tests/                           device library tests, against the mock backend
scripts/                         dev environment, simulator, reference sources
```

The split follows what Home Assistant's Modbus documentation recommends and
what core's `sofar` integration does. The library is kept in this repo for now
and can be broken out into its own PyPI package once its shape settles; the
version in `pyproject.toml` must stay identical to the `requirements` entry in
`custom_components/sungrow_modbus/manifest.json`, because Home Assistant checks
the installed version on every start.

## Porting registers

`modbus_sungrow.yaml` translates to `Component` fields almost one for one:

| YAML | Library field |
| --- | --- |
| `input_type: input` | `register_space = "input"` on the component |
| `data_type: uint16`, `scale: 0.1` | `gauge(addr, 0.1, signed=False, unit=...)` |
| `data_type: int16` unscaled | `integer(addr)` |
| `data_type: uint32`, `swap: word` | `uint32(addr, word_order="little")` |
| `data_type: string`, `count: 10` | `string(addr, 10)` |
| `nan_value: 0xFFFF` | `nan=0xFFFF` |
| state code decoded in a template | `enum(addr, SomeIntEnum)` |
| register written by a template | `writable=True` |

Addresses are protocol addresses, i.e. one below the register number in
Sungrow's document (`address: 4989 # reg 4990`). Neighbouring fields are
pooled into block reads automatically, so grouping fields by how often they
should be polled matters more than grouping them by address.

## Reviewing the migration by hand

The migration is the one feature a unit test cannot fully judge. Whether the
setup dialog explains the choice well enough to make it, and whether the
history graph really is continuous afterwards, are things you have to look at.
`scripts/seed_migration_testbed.py` fabricates the starting state — the
registry entries `modbus_sungrow.yaml` leaves behind, plus a month of recorded
readings and hourly statistics under the ids it used:

```console
$ scripts/develop.sh                            # once, to create config/
# stop it
$ python scripts/seed_migration_testbed.py
Registry:   153 entities added
History:    2880 states over 30 days
Statistics: 2880 hourly rows
$ scripts/simulate.sh &                         # an inverter to talk to
$ scripts/develop.sh
```

Home Assistant must be **stopped** while it runs: it writes the entity
registry and the recorder database directly. `--reset` undoes it, so the same
instance can be used to try the other answer. `--from <snapshot>` uses a
registry exported from a real instance instead of the generated entity map —
more faithful, but such a file belongs in `.testdata/`, never in the repo.

## Testing the install a user actually gets

Everything above runs the working tree: `scripts/develop.sh` symlinks
`config/custom_components` to this repository, so the instance on :8123 is
your editor with a UI attached. That is the wrong instrument for one class of
question — *does this install?* — and the two failures that cost most time on
this project were both of that class. A manifest pinning a library version
whose wheel lacks a module the integration imports passes every test, ruff,
hassfest and the release, and fails only in a real install. HACS refusing a
repository whose default branch has no `custom_components/` is invisible
from here entirely.

`scripts/hacs_testbed.sh` (`make hacs`) is the other instrument: a **second**
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
  `scripts/check_pinned_library.py` is the check that catches it earlier.
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

A capability survey is what this project learns from, and it used to cost a
contributor a Python run on a machine that can reach the inverter. It is now
a button on the device page, with three diagnostic sensors beside it:

| Entity | What it is for |
| --- | --- |
| `button.<name>_run_capability_survey` | Starts one. Unavailable while a run is in flight; the runner refuses a second anyway |
| `sensor.<name>_survey_progress` | Percent complete. Counted reads, not elapsed time — the same survey is under a second on a cable and minutes over a VPN |
| `sensor.<name>_survey_step` | What is being read right now. **Its recorded history is the point**: 19 probes and 5 timing reads in order — plus 52 band sweeps when a dump was asked for — which is what says *where* a slow link stalls rather than that it did |
| `sensor.<name>_survey_finished` | When the last run ended, with `fields_read` and `has_document` as attributes |

They exist in both setup modes. A *Diagnostics only* entry has no readings at
all, and these four are the entirety of its device page — which is also why
it has one: Home Assistant registers a device only as a side effect of an
entity carrying its `device_info`.

`survey.py` owns the run and holds the state; `fingerprint.py` does the
reading and calls back with a fraction and a label; `survey_entities.py`
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
`async_build` says the caller can afford to wait for it. Only the button and
the `run_survey` action pass the second, because only they are background
tasks with a progress bar. `diagnostics.py` builds the same document and
leaves it off — five minutes of reading behind a download button reads as a
hang, and an owner who enabled the option was answering a question about
surveys. Reading the option directly inside `async_build` would be the
obvious simplification and would break exactly that.

Two switches in the options are called a register dump and they do different
things. Advanced → *Include a raw register dump in diagnostics*
(`CONF_REGISTER_DUMP`) re-reads the addresses the library already maps, into
the diagnostics file, in seconds. Help this project → *Also sweep the raw
register bands* (`CONF_SURVEY_DUMP`) sweeps `sungrow_modbus.dump.DUMP_BANDS`
— 1510 addresses, mostly unmapped — into the survey document, in about five
minutes. Only the second can discover a register. The bands are duplicated in
`scripts/sungrow_scan/probe.py` because that has to run from a zip with the
library absent, and `tests/test_dump_bands.py` is what stops the two drifting.

To see any of this against a real run, the recorder is the fastest way in —
the dev instance keeps it:

```console
$ sqlite3 config/home-assistant_v2.db \
    "select m.entity_id, s.state, datetime(s.last_updated_ts,'unixepoch','localtime')
     from states s join states_meta m on s.metadata_id = m.metadata_id
     where m.entity_id like '%survey%' order by s.last_updated_ts"
```

Persistent notifications are **not** states and never have been since 2022.10
— they live in memory behind the websocket command
`persistent_notification/get`, so a survey that "produced no notification" is
worth checking there before believing it.

## Naming entities

Entity names are entity ids. With `has_entity_name` set, Home Assistant
slugifies the object id **from the name**, so "Sungrow inverter serial" gives
`sensor.sh10rt_sungrow_inverter_serial` and "Serial number" gives
`sensor.sh10rt_serial_number`. A name is cheap to get right before release and
impossible to change afterwards.

The convention is in [scripts/naming.py](../scripts/naming.py) — sentence case,
a fixed acronym list, no device name at the front, no guessable abbreviations,
and `_raw` entities under `EntityCategory.DIAGNOSTIC`. Do not write a name into
`strings.json` by hand:

```console
$ python scripts/generate_strings.py
Wrote 127 entity names
```

`tests/test_naming_convention.py` checks the committed `strings.json` against
the convention rather than against the generator, so an override has to obey
the rules like everything else. If a name genuinely needs to break them, add it
to `OVERRIDES` **with the reason** — the table is short on purpose.

`legacy_name` on each description is the exception and must never be
normalised: legacy mode reproduces a user's existing entity_ids byte for byte,
so the YAML's inconsistency is preserved there deliberately.

## First boot

`scripts/develop.sh` boots against `config/configuration.yaml`, which
deliberately avoids `default_config:`. That keeps the dev instance small:
Home Assistant pip-installs each component's requirements the first time it
sets it up, and `default_config` drags in bluetooth, dhcp, usb, ssdp,
conversation and video handling that a Modbus integration never touches.

Even so, the very first boot installs a handful of packages (the frontend
above all) and takes a few minutes before <http://localhost:8123> answers with
something other than a 404. That is once per container, not once per run:
measured in a clean container, the first boot logs ~20 setup errors while its
dependencies are still downloading, and the next boot comes up in 2.2 seconds
with no errors at all. If the UI 404s on your very first run, give it a minute
and reload rather than going looking for a bug.

## Open question: superseding the YAML package

The intent is for this integration to replace `modbus_sungrow.yaml`, not to
live alongside it forever, and a clean migration is a hard requirement:
existing users must keep their recorder history and their dashboards.

The crux is `entity_id`. The YAML package produces `sensor.total_dc_power`;
an integration entity with `_attr_has_entity_name = True` produces
`sensor.<device name>_total_dc_power`. Dashboards reference entity ids
directly, and recorder history is keyed by them, so the naming decision
decides whether years of data and every dashboard card survive the switch.

The shape being considered is to let the user choose during setup:

- **keep the legacy ids**, so history and dashboards carry on untouched -
  which requires the YAML entities to be removed first, or the ids collide;
- **take modern, device-scoped ids** and migrate the existing data across.

Both were open questions; both are now settled and asserted against Home
Assistant itself in [tests/test_recorder_migration.py](../tests/test_recorder_migration.py).
A registry rename carries raw states *and* long-term statistics, and it is
reversible, so neither direction is a one-way door. The mechanism and its traps
are in [doc/integration_plan.md](integration_plan.md); read that before
touching entity ids.
