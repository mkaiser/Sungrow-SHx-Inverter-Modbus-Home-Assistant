# Sungrow Modbus — working notes

The rules, and where everything else is. The rules here outrank every other
document, the wiki included.

| What | Where |
| --- | --- |
| What we know about Sungrow devices | the wiki: start at `.wiki/wiki/index.md`; its schema and ingest workflow are `.wiki/AGENTS.md` |
| Dev loop, every script, environment pitfalls | `doc/development.md` (`doc/development.yaml` is the copy-paste runbook) |
| How the integration is cut up, and why | `doc/architecture.md` |
| Releasing, hassfest, HACS and the preview channel | `doc/maintainer_setup.md` |
| Running the survey / its document, scripts and pinned library | `device-survey/README.md` / `device-survey/reference.md` |
| What is next, open decisions, what waits on hardware | `Todo.md` |
| Goals, decisions, register sources and licences | `doc/architecture.md` |
| Where the integration stands on Home Assistant's quality scale | `custom_components/sungrow_modbus/quality_scale.yaml`, held to the code by `tests/test_quality_scale.py` |

## Two tracks

1. **The YAML package** (`legacy/modbus_sungrow.yaml`) — shipping, in use by
   many people, on `main`. Treat as production. Until the integration reaches
   parity, it stays untouched.
2. **The Home Assistant integration** (`custom_components/sungrow_modbus` +
   the library `src/sungrow_modbus`) — on branch `proper-ha-integration`, an
   MVP that will **supersede** the YAML package.

The integration covers the inverter, the
[SBR battery](.wiki/wiki/entities/device-sbr-battery.md), the
[wallbox](.wiki/wiki/entities/device-wallbox.md) (read only; through the
dongle, or at its own address with the `wallbox_host` option) and an
[external generator](.wiki/wiki/concepts/external-generator.md). The
[iHomeManager](.wiki/wiki/entities/device-ihomemanager.md) is never measured.
One config entry is **one inverter behind one Modbus endpoint** (host + port),
plus the devices found on it,
[identified by what answers](.wiki/wiki/concepts/identify-by-what-answers.md),
never by unit id.

Home Assistant 2026.9's `modbus` integration hands a device integration a
*unit* (`async_get_unit(...)`), and everything on one host/port shares one
serialized connection: a Sungrow accepts few sessions. The library has **no
Home Assistant imports**, one subpackage per device (`inverter/`, `battery/`,
`wallbox/`), and anything that must run without HA (the control test's
engine included) lives there. Core's `sofar` integration is the reference
implementation; read its real source (`make refs`), not blog posts.

## Git: ask before every push

**Never `git push` without asking the maintainer first, every time.** An
earlier "commit and push" covers that one change, not the next one.
Committing when asked is fine; pushing is a separate question.

## Do not hand-edit

Edit the source, not the output:

- `custom_components/sungrow_modbus/{derived,number,switch,select,time}_descriptions.py`,
  `strings.json`, `translations/en.json` -- `scripts/generate/descriptions.py`,
  from `sungrow_modbus.inverter.derived` and `scripts/generate/tables/`;
- `doc/compatibility.md` -- `generate_compatibility.py`, from the surveys;
- `scripts/dev/simulator_registers.json` -- `generate_simulator_registers.py`;
- `doc/entity_name_review.md` -- `scripts/helpers/review_names.py --markdown`;
- `legacy/modbus_sungrow_multiple_inverters_{1,2,3}.yaml` --
  `generate_second_inverter_config.py`; CI regenerates and commits it,
  overwriting any hand edit.

`make gen-check` (and CI) fails on a hand edit of the first four.
`pyproject.toml`'s version and `manifest.json`'s pin move only through
`scripts/release/sync_version.py --set X.Y.Z`.

**`registers.py` and `sensor_descriptions.py` are source**, held field by
field to `doc/legacy_entity_map.json` (the record of what the YAML package
produces; never regenerated) by `tests/test_registers.py` and
`tests/test_sensor_descriptions.py`. A field that must differ is declared
where the test can see it (`layout.COUNTS`, `write_units_per_count`), never
made silently. `battery_`, `wallbox_` and `external_descriptions.py` are
source too.

## Commands

| Command | What it does |
| --- | --- |
| `make help` | Every shortcut |
| `make check` | The CI gate: ruff, pytest (wiki lint included), mypy, `gen-check` |
| `make quick` | The same without pytest, in seconds; `make hooks` runs it before every commit |
| `make gen` | Rewrite every generated file |
| `make dev` / `make sim` | HA on :8123 (login `dev`/`dev`) / the simulator on :5020 |
| `make scan-local HOST=...` | The survey on this tree's library instead of the PyPI pin |
| `pytest` · `ruff check . && ruff format .` · `mypy` | Tests (no network), lint, `--strict` over the library and the integration |

`doc/development.md` lists every script.

## The wiki

The wiki is the repository's device knowledge, after
[microsoft/llmwiki](https://github.com/microsoft/llmwiki). Before working on a
device question, read `.wiki/wiki/index.md` and the pages it points to.

- **Raw sources are immutable**: `device-survey/results/`,
  `doc/legacy_entity_map.json` and `.wiki/raw/`. Read, cite, never rewrite.
  A survey transcript is never one. The `doc/` pages are for people and are
  edited like any doc; the wiki cites its own frozen copy of one.
- **Every claim cites its source.** One with none goes into `queries/`.
- **Ingest is part of the work**: a new survey, control test or hardware
  finding updates its pages, the index and `log.md` in the same change.
  `.wiki/AGENTS.md` has the workflow.
- **`log.md` is the only place history goes.** Pages state what is true now.
- **Generated files and code are not wiki pages**; the wiki links to them.

## The control test writes

Part A of the survey only reads. Part B, the
[control test](.wiki/wiki/concepts/control-test.md), writes each control,
reads it back against the specification's scale, watches what the inverter
does, and puts everything back. Non-negotiable:

- **The [restore](.wiki/wiki/concepts/control-test-restore.md) is never
  budgeted, never deadlined and never skipped**, and it writes the snapshot's
  raw word, checked by raw read. The snapshot is flushed before the first
  write. **No snapshot file for a day means no writes that day.** Exit 5 is
  the one code that means a house is left changed.
- **Leg B's scale is hand-typed from V1.1.11, never read from
  `field.scale`.** `tests/test_control_test.py` makes the two meet.
- **A simulator cannot produce a finding**, and through a WiNet-S only the
  behavioural leg is evidence.
- **The survey writes only with leave**: its last question defaults to no,
  and a run with nobody at a terminal is a no.
- **[Register 13074](.wiki/wiki/entities/register-13074.md)'s write scale is
  probed per device, never assumed** (×10 on B001 firmware, 1:1 on
  `SAPPHIRE-H_01011.95.03`).

Before touching `device-survey/scripts/`, read
`device-survey/reference.md`: the PEP 723 header is the survey's whole install,
and it can use only what the pinned wheel has.

## Things that will bite you

- **A failed read is not a refusal.** In `modbus_connection`,
  `ModbusExceptionError` is the device answering; a connection lost, a
  timeout or a desync says nothing about the register. Probes are
  three-valued, `None` never reads as `False`, and **a test fixture raises
  the real exception type**, never a bare `ModbusError`.
- **Never catch `Exception` without a traceback.** Use `_LOGGER.exception`;
  keep the short form for what a user reads in a dialog.
- **Never put `custom_components/` on `PYTHONPATH`**: the integration's
  domain is the library's import name, and HA then reports a circular import
  far from the cause. `config/custom_components` is a symlink instead.
- **A stale editable install breaks Add integration** with
  `RequirementsNotFound`: HA checks the pin against what is installed.
  `sync_version.py --set` re-installs it.
- **`PARALLEL_UPDATES` is 1 on the write platforms**, 0 elsewhere; writes
  interlock (`doc/architecture.md`).
- **A first boot in a fresh container logs ~20 setup errors** and the UI
  404s. The next boot is clean. Not a bug.

Verified against hardware; read the page before changing code that relies on it:

| In one line | Page |
| --- | --- |
| An exception response is an answer; a timeout or a lost connection is not | [a failed read is not a refusal](.wiki/wiki/concepts/failed-read-is-not-refusal.md) |
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

## Hard constraint: migration must preserve history

Existing users' recorder history and dashboards are **keyed by `entity_id`**;
get this wrong and years of history break silently. The mechanism is
asserted in `tests/test_recorder_migration.py`, explained in
[adopting the legacy entity ids](.wiki/wiki/concepts/legacy-id-adoption.md)
and [the legacy slot](.wiki/wiki/concepts/legacy-slot.md), and the user's guide
is `doc/integration_migration.md`.

- **Claim the legacy `entity_id` at entity creation.** A rename onto an id the
  recorder already knows is refused, with only a log line.
- **Every ported entity keeps the unit class and `state_class`** of the YAML
  entry it replaces, or long-term statistics freeze flat.
- **A second inverter's slot is measured, never guessed, and `None` is not
  `""`.** A slot that could not be answered claims no legacy ids.
- **The `_inv_<n>` suffix goes on the name, not the id**, and the serial
  lookup uses platform `modbus`.

## Hard constraint: a real serial number is never published

**No real device serial or address goes into anything this repository
tracks**: not a survey, a fixture, a docstring, a commit message, a comment or
a wiki page. Most of them belong to other people.

- Published documents carry the stand-in `serial_anonymized_hashed`; the
  real serial reaches only the gitignored transcript.
- `tests/test_no_real_serials.py` matches the shape of a serial over every
  tracked file, `.wiki/` included. In tests use `A123456789` (and
  `A987654321` where two must differ); in prose, the stand-in a device's
  surveys publish. A serial can also hide as register words in a fixture,
  which the shape test misses.
- A document carries `ip_address_last_two_octets` only with its owner's
  consent; the wiki carries no address (`tests/test_wiki.py`).
- A stand-in serial is not consent: ask an owner before publishing readings.

How: [serial anonymization](.wiki/wiki/concepts/serial-anonymization.md).

## Local-only context

The maintainer's inverter details live in their own `secrets.yaml`
(`sungrow_modbus_host_ip`, `sungrow_modbus_device_address`), never here. Use
the simulator on `localhost:5020` unless you need real hardware. The
container reaches a LAN inverter outbound with no setup; multicast does not
cross the bridge, so mDNS runs on the host (`real_hardware` in
`doc/development.yaml`).
