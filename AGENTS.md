# Sungrow Modbus — working notes

The rules, and where everything else is. The rules here outrank every other
document, the wiki included. Each rule is written down once; everywhere else
links to it.

## Where everything is

| What | Where |
| --- | --- |
| What we know about Sungrow devices | the wiki: start at `.wiki/wiki/index.md`; its schema and ingest workflow are `.wiki/AGENTS.md` |
| How the integration is cut up, what one config entry is, the goals, the decisions, the register sources and their licences | `doc/architecture.md` |
| Dev loop, every script, environment pitfalls | `doc/development.md` (`doc/development.yaml` is the copy-paste runbook) |
| Releasing, hassfest, the Marketplace and the preview channel | `doc/maintainer_setup.md` |
| Running the diagnosis / its document, scripts and pinned library | `device-diagnosis/README.md` / `device-diagnosis/reference.md` |
| What is next, open decisions, what waits on hardware | `Todo.md` |
| How work is written down and how agents share one tree: `Todo.md`, `plans/`, item numbers, commits and pushes | `workflow.md` |
| Recurring procedures (ingest new diagnoses, release, run a diagnosis for a contributor, revise `Todo.md`, close a session) | `.claude/skills/`, each pointing at the document it follows; any agent can follow them, not only Claude Code |
| Where the integration stands on Home Assistant's quality scale | `custom_components/sungrow_modbus/quality_scale.yaml`, held to the code by `tests/test_quality_scale.py` |

## Two tracks

1. **The YAML package** (`legacy/modbus_sungrow.yaml`) — shipping, in use by
   many people, on `main`. Treat as production. Until the integration reaches
   parity, it stays untouched.
2. **The Home Assistant integration** (`custom_components/sungrow_modbus` +
   the library `src/sungrow_modbus`) — on branch `proper-ha-integration`, an
   MVP that will **supersede** the YAML package.

Which devices an entry covers, what one config entry is, why the library has
no Home Assistant imports, and the minimum Home Assistant version are all in
`doc/architecture.md`. Core's `sofar` integration is the reference
implementation; read its real source (`make refs`), not blog posts.

## Commands

`make check` is the CI gate: ruff, pytest (the wiki lint included), mypy and
`gen-check`. `make quick` is the same without pytest, in seconds, and
`make hooks` runs it before every commit. `make help` lists every shortcut,
and `doc/development.md` says what each script behind them does.

## The rules

Each line below is the whole rule; the page beside it is the evidence and the
how. Read that page before changing code that relies on it.

**Hard constraints.** Broken, each of these costs somebody their house's
settings, their history or their privacy — silently, and usually without a
failing test.

| In one line | Page |
| --- | --- |
| **No real serial and no address go into anything this repository tracks** — not a diagnosis, a fixture, a docstring, a commit message, a comment or a wiki page. Most of them belong to other people. Stand-ins only, and a stand-in is not consent: ask an owner before publishing their readings | [serial anonymization](.wiki/wiki/concepts/serial-anonymization.md), `tests/test_no_real_serials.py` |
| **Existing users' history and dashboards are keyed by `entity_id`**: claim the legacy id at entity creation, keep the unit class and `state_class` of the entry you replace, and measure a second inverter's slot rather than guess it | [adopting the legacy entity ids](.wiki/wiki/concepts/legacy-id-adoption.md), [the legacy slot](.wiki/wiki/concepts/legacy-slot.md), `tests/test_recorder_migration.py`, `doc/integration_migration.md` |
| **The capability test's restore is never budgeted, never deadlined and never skipped**; no snapshot file for a day means no writes that day, and exit 5 is the one code that means a house is left changed | [the restore](.wiki/wiki/concepts/capability-test-restore.md) |
| **The diagnosis writes only with leave**, a simulator cannot produce a finding, and leg B's scale is hand-typed from V1.1.11 rather than read from `field.scale` | [the capability test](.wiki/wiki/concepts/capability-test.md) |
| **Never `git push` without asking the maintainer first, every time**, and commit only the paths you changed | `workflow.md` |

**Verified against hardware.**

| In one line | Page |
| --- | --- |
| An exception response is an answer; a timeout or a lost connection is not. Probes are three-valued, `None` never reads as `False`, and a test fixture raises the real exception type | [a failed read is not a refusal](.wiki/wiki/concepts/failed-read-is-not-refusal.md) |
| 13000's `0x0000` is Running, and a dongle re-encodes the codes | [register 13000](.wiki/wiki/entities/register-13000.md) |
| Addresses are protocol addresses; maps use `reg()`; no literal addresses outside tests | [protocol addresses](.wiki/wiki/concepts/protocol-addresses.md) |
| Firmware is read before anything decides on it; `CONFIRMED_ON_FIRMWARE` only from a watched write | [firmware gating](.wiki/wiki/concepts/firmware-gating.md) |
| A dongle's 0, and an all-NUL string, are not evidence of a capability | [zero means absent](.wiki/wiki/concepts/zero-means-absent.md) |
| A lifetime counter past a million kWh is a broken word, not a reading; one a wrap short is caught by what it contains | [a million kWh is not a reading](.wiki/wiki/concepts/a-million-kwh-is-not-a-reading.md) |
| 2612 and 2628 send padded frames; add to `layout.py` only from `blocks.py`'s strict measurement | [padded frames](.wiki/wiki/concepts/padded-frames.md) |
| Few sessions, and 90 s of quiet to recover; a short retry is not a retry | [contention](.wiki/wiki/concepts/contention.md) |
| 6100 decides transport: not 13265, and not round-trip time | [transport detection](.wiki/wiki/concepts/transport-detection.md) |
| What a WiNet-S refuses, invents, re-encodes and reads back stale | [WiNet-S](.wiki/wiki/entities/device-winet-s.md) |
| Sweep unit ids, never trust a port; which units answer depends on transport | [identify by what answers](.wiki/wiki/concepts/identify-by-what-answers.md) |
| A wallbox is at unit 3 behind a dongle (2 or 4 reported, tried too), or 248 over TLS on 516; over TLS a read starts on a data point's first register | [wallbox](.wiki/wiki/entities/device-wallbox.md) |
| 13074's write scale is probed per device, never assumed (×10 on B001 firmware, 1:1 on `SAPPHIRE-H_01011.95.03`) | [register 13074](.wiki/wiki/entities/register-13074.md) |

**In the code and the tree.**

| In one line | Where |
| --- | --- |
| `PARALLEL_UPDATES` is 1 on the write platforms and 0 elsewhere, because the writes interlock. Never catch `Exception` without a traceback | `doc/architecture.md` |
| The traps this container sets: `custom_components/` on `PYTHONPATH`, a stale editable install breaking *Add integration*, a noisy first boot that is not a bug | `doc/development.md`, *Pitfalls* and *First boot* |
| The diagnosis's PEP 723 header is its whole install, so it can use only what the pinned wheel has. Read this before touching `device-diagnosis/scripts/` | `device-diagnosis/reference.md` |
| The maintainer's inverter details live in their own `secrets.yaml`, never here; use the simulator unless you need real hardware | `doc/development.md`, `doc/development.yaml`'s `real_hardware` |

## Do not hand-edit

Edit the source, not the output (`workflow.md`). Here that means:

- `custom_components/sungrow_modbus/{derived,number,switch,select,time,button}_descriptions.py`,
  `strings.json`, `translations/{en,de}.json` -- `scripts/generate/descriptions.py`,
  from `sungrow_modbus.hybrid_inverter.derived` and `scripts/generate/tables/`;
- `doc/compatibility.md` and `doc/firmware_support.md` --
  `generate_compatibility.py` and `generate_firmware_support.py`, from the diagnoses;
- the coverage table in `device-diagnosis/devices-wanted.md`, between its
  markers -- `generate_devices_wanted.py`, from the diagnoses;
- `scripts/dev/simulator_registers.json` -- `generate_simulator_registers.py`;
- `doc/entity_names.md` and `plans/_gen_text_translation_review.md` --
  `scripts/helpers/review_names.py --markdown` and `--texts`;
- `legacy/modbus_sungrow_multiple_inverters_{1,2,3}.yaml` --
  `generate_second_inverter_config.py`; CI regenerates and commits it,
  overwriting any hand edit.

`make gen` rewrites them all; `make gen-check` (and CI) fails on a hand edit
of the first five. `pyproject.toml`'s version and `manifest.json`'s pin move
only through `scripts/release/sync_version.py --set X.Y.Z`.

**`registers.py` and `sensor_descriptions.py` are source**, held field by
field to `doc/legacy_entity_map.json` (the record of what the YAML package
produces; never regenerated) by `tests/test_registers.py` and
`tests/test_sensor_descriptions.py`. A field that must differ is declared
where the test can see it (`layout.COUNTS`, `write_units_per_count`), never
made silently. `battery_`, `wallbox_` and `external_descriptions.py` are
source too.

## The wiki

The wiki is the repository's device knowledge, after
[microsoft/llmwiki](https://github.com/microsoft/llmwiki). Before working on a
device question, read `.wiki/wiki/index.md` and the pages it points to.
**Ingest is part of the work**: a new diagnosis, capability test or hardware
finding updates its pages, the index and `log.md` in the same change. The
rest — what counts as evidence, which sources are immutable, naming, the lint
— is `.wiki/AGENTS.md`.
