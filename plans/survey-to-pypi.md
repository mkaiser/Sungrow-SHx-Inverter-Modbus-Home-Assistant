# Survey-to-PyPI migration

## Objective

Move reusable fingerprinting and survey logic out of
`device-fingerprints/scripts/python` and into the `sungrow-modbus` PyPI package.
The fingerprint directory should contain only user-facing scripts:

- CLI argument parsing and interactive questions
- terminal output and transcripts
- connection setup and file writing
- optional raw-socket diagnostics

The package must remain backend-neutral, headless, deterministic, and free of
implicit prompts, filesystem writes, or report submission.

## Decisions

- Home Assistant and the terminal tools should consume the same package API.
- Home Assistant-specific lifecycle, progress entities, config-entry options,
  notifications, diagnostics downloads, and translated UI stay in
  `custom_components/`.
- mDNS is supported by the PyPI package as an optional feature, not a base
  dependency:

  ```text
  pip install sungrow-modbus[discovery]
  ```

- The package returns structured next steps. It does not automatically open
  issues, submit reports, or modify repositories.
- Existing fingerprint document schema, labels, serial masking, address
  privacy, and compatibility output must remain stable.

## Current state

### Completed

- Added [`src/sungrow_modbus/survey.py`](../src/sungrow_modbus/survey.py):
  - `NextStep`
  - `next_steps(document)`
  - `summarise(document)`
- Home Assistant summary rendering delegates to the package API.
- The terminal survey renders shared structured next-step recommendations.
- Added optional package mDNS discovery in
  [`src/sungrow_modbus/discovery.py`](../src/sungrow_modbus/discovery.py).
- Added `discovery = ["zeroconf>=0.39.0"]` to `pyproject.toml`.
- Added package exports for survey helpers and discovery identities.
- Added package API tests in `tests/test_survey_api.py`.
- Added direct package endpoint-identification tests in
  `tests/test_discovery_identity.py`.
- Added backend-neutral `async_read_retrying()` and `failure_state()` to
  `src/sungrow_modbus/survey.py`; the CLI probe now consumes these package
  primitives instead of carrying its own retry and Modbus error taxonomy.
- Added backend-neutral `async_probe_fields()` to
  `src/sungrow_modbus/survey.py`; the CLI now delegates its standard
  capability-probe reads, retry budgets, raw values, and state classification
  to the package.
- Added package `fingerprint.device_block()` and switched both the CLI and
  Home Assistant fingerprint builder to use it for device-code lookup,
  output-type vocabulary, and serial stand-ins.
- Added package `fingerprint.connection_block()` and switched both the CLI
  and Home Assistant fingerprint builder to use shared connection and
  transport shaping.
- Removed the Home Assistant compatibility wrapper for connection shaping;
  the integration now calls the package helper directly.
- Switched the CLI's published-field filtering to the package's
  `fingerprint.publishable()` primitive, preserving its compatibility export
  for existing script consumers and tests.
- Added shared package primitives for local timestamp rendering and
  privacy-safe capability-register shaping; the CLI now delegates both.
- Added the shared `base_document()` package builder (now
  `assemble_document()`, see todo 2) and moved Home
  Assistant's common document metadata construction onto it.
- Added shared `measured_connection()` shaping so owner testimony is kept out
  of measured connection data; the CLI now delegates this filtering too.
- Removed the obsolete `device-fingerprints/probe.sh` wrapper. Current
  command lines use `python/probe.py`; historical fingerprints may retain
  `probe.sh` as the tool name they were collected with.
- Historical command-line validation accepts both the retired `probe.sh`
  provenance and the current `python/probe.py` invocation without rewriting
  evidence documents.
- Consolidated all user-facing launchers and Python entry points under
  `device-fingerprints/scripts/`; the obsolete top-level `python/` directory
  no longer exists.
- Updated `device-fingerprints/README.md` with the package boundary and mDNS
  installation instructions.
- Validation completed:
  - strict `mypy --strict src/sungrow_modbus`
  - Ruff on the changed package, integration, scripts, and tests
  - focused fingerprint and Home Assistant tests: 237 passed

### In progress

- Endpoint discovery, retry/error classification, standard capability probes,
  device shaping, connection shaping, privacy filtering, timestamps, and
  shared summaries are now package APIs consumed by both clients.
- User-facing tools have been relocated to
  `device-fingerprints/scripts/`; the old `device-fingerprints/python/`
  directory and `probe.sh` wrapper are removed.
- The remaining extraction work is the larger survey/document pipeline:
  decoded readings, block tests, battery and wallbox composition, and the
  final publishable document builder.
- Added the package-level `fingerprint.publish_document()` builder and routed
  the CLI's publish step through it. It now owns the common document shape,
  connection testimony filtering, capability privacy, register-dump masking,
  wallbox serial masking/readings, and optional battery/block/control sections.
- Added a direct regression test for `publish_document()` covering connection
  testimony removal, serial capability suppression, and optional block output.
- `probe.py`, `sungrow_survey.py`, and `wallbox_direct.py` still contain
  orchestration that should become thin adapters around those package APIs.
- Home Assistant's fingerprint builder now delegates every section that
  needs no HA runtime object to the package: capability probes
  (`survey.async_probe_words`, one attempt each, progress announced before
  each read), decoded readings (`fingerprint.readings_section`), the battery
  pack (`fingerprint.battery_pack_section`) and the wallbox
  (`fingerprint.wallbox_section` / `wallbox_from_dump`, which own the
  wallbox mask and stand-in). What remains HA-side is testimony from entry
  options, firmware from polled fields, contention, step counting and the
  control-test guard.
- **Finding: the two producers disagreed on `readings`.** Every terminal
  document keeps unavailable fields as `None` *inside* `values` and uses
  `fields_that_did_not_read` only for fields that failed a read of their own
  (after `fields_read_individually` salvage). The Home Assistant builder
  dropped `None` from `values` and listed those fields under
  `fields_that_did_not_read` -- the same key with a different meaning.
  Resolved toward the corpus: `fingerprint.readings_section()` now
  implements the terminal format (including the salvage overlay), the CLI's
  `_async_decoded_readings` builds its report with it, and HA gets the same
  output. `battery_pack_section()` likewise keeps `None` values.
  Held by `test_readings_mean_what_they_mean_in_a_terminal_survey`. The one
  committed HA document (ra1k-0's SH20T, schema 18) keeps the old meaning,
  which schema 22 now marks.
- `wallbox_direct.py` is now a thin adapter: its document, label and reader
  come from `fingerprint.wallbox_document()`, `fingerprint.wallbox_label_for()`
  (re-exported as `wallbox_direct.label_for`), `fingerprint.wallbox_section()`
  and `survey.word_reader()`. What stays is the TLS link, the identify probe,
  the progress echo and the file write. `dump.answered()` replaces three
  copies of the answered-word count (`wallbox_direct`, `sungrow_survey` x2).
- **Resolved (decision 2026-10-15: use the terminal section): HA's
  `battery_pack` was narrower than the CLI's.** `SungrowBattery` had only
  the polled `pack` and `cells` components; the CLI also read
  `SbrBatteryModules`. (The unpacked cell/module positions were never
  missing: they are properties in the component's class body, so they are
  already in `field_names`.) Now `battery_device.SURVEY_COMPONENTS` holds the
  modules block -- read by `async_update(survey=True)`, never by the poll,
  since it makes no entity yet -- and `PUBLISHED_NAMES` gives each component
  its document name. `fingerprint.battery_readings()` /
  `battery_pack_section()` produce the terminal shape: a failed
  component's fields are *absent* (via `SungrowBattery.fields_of()`), not
  None, and `components_that_did_not_answer` names them. The CLI's
  `_async_battery_readings` and HA's `_async_battery_pack` both build on it.
  Held by `test_a_survey_reads_the_module_block_the_poll_leaves_alone`.
- Firmware: `fingerprint.FIRMWARE_FIELDS` (moved from HA) is the one table
  of published firmware names; `FIRMWARE_STRINGS` is now derived from it
  through `addresses.field_address`, removing five literal addresses from
  `src/`, and `fingerprint.firmware_section(device)` is HA's builder. The CLI
  still reads firmware raw before the components (it has no polled device
  yet at that point) through the derived `FIRMWARE_STRINGS`.
- HA's `fingerprint.py` is 509 lines (from 628) and holds only adapters:
  testimony from entry options, contention from the runtime, progress
  steps, the dump/block-test affordability switches and the control-test
  guard. Dead `_hex` and `_device_block` removed.
- The decoded-readings algorithm is in the library:
  `survey.async_decoded_readings()` (identity retried, multi-pass component
  reads with a pause between passes, field-by-field salvage of what still
  failed) and `survey.async_read_field_by_field()`. It prints nothing;
  progress comes back through `on_component`, `on_passes_done` and
  `on_note`. `probe._async_decoded_readings` is now a 20-line wrapper that
  draws the bar. Held by
  `test_the_library_reads_without_printing_and_reports_through_callbacks`.
- **Finding and fix: HA could misreport the transport.** The CLI publishes
  `winet_restricted_block_6100: answered` for any answer; HA published the
  probe state, and `connection_block` counted only `present` as reaching the
  block -- so a 6100 that answered with the 0xFFFF sentinel gave the verdict
  "through a communication module" on a cable. `connection_block` now maps
  `present` and `unavailable` to `fingerprint.ANSWERED_6100` before deciding,
  so both producers publish `answered`. Part of schema 22.
- `device-fingerprints/README.md` ("Shared survey logic", with a table of
  the package API) and `doc/architecture.md` (the survey boundary) describe
  the current split; stale `python/` paths in the README fixed.
- **Structural comparison (2026-10-15 23:22)** of an HA document built in the
  test harness against gerd's committed direct-LAN CLI document: identical
  `readings.values` keys, identical probe set apart from the CLI's own
  unit-discovery probes, identical sections apart from those the fixture
  has no data for (battery, block test, dump, control test, export scale).
  Differences left, both deliberate: HA alone publishes `contention` and
  `user_inputs.other_pollers` (it can measure its own polling, a terminal
  cannot); the CLI alone publishes `unit N ...` discovery probes (HA
  discovers in the config flow).
- **Second filename builder removed.** `probe.py` still carried
  `_derive_label`, `_battery_token`, `_firmware_token`, `_all_zero` and
  `_slug` -- ~300 lines reached only by `tests/test_fingerprint_label.py`,
  while a run names its file with the package's `label_for`. The label tests
  now build the published document through `publish_document` and ask
  `label_for` / `_battery_word` / the new `fingerprint.firmware_word`; all
  186 pass, so the two derivations agreed on every case, and the CLI copy is
  gone.
- **Register dump has one implementation.** `probe._async_dump_bands` was a
  second copy of `dump.async_dump`; it is now a wrapper that prints the band
  list and draws the bar. `dump.async_dump` gained `on_narrow(address,
  number, size)`, called before each single-address fallback read, so the
  bar still says which register it waits on.
- **Sibling units decided once.** `fingerprint.SIBLING_PROBES` (with
  `PRESENCE_WORDS`) is the one table of the unit 200 / 2 / 3 / 248 presence
  probes; `battery_pack_unit()`, `slave_inverter_at()` and `wallbox_unit()`
  are the decisions, and the package's `_battery_word` uses
  `battery_pack_unit()` instead of its own copy of the pack-or-slave rule.
  `survey.async_probe_siblings()` reads them; the CLI run prints each answer
  through `on_probe` and picks the pack and wallbox units from the
  decisions. One visible change: "unit 2 is an inverter, not a pack" is now
  printed whenever that is so, not only when unit 200 was silent.
- Firmware and text: `survey.async_read_firmware()` reads the five strings
  raw for the CLI (unread absent, empty None), `model.words_text()` is the one
  words-to-text decode (`discovery.py` x2 and the CLI's serial use it; the
  serial keeps its whitespace because its stand-in is hashed from it).
- `probe.py` is 2325 lines (from 3125 at the start of this session).
- **Schema 22 (decision 2026-10-15: bump).** Released 0.1.0a14 is at 21;
  this worktree had already moved to 22 with no history entry and no
  document carrying it, so the readings/battery unification takes 22. The
  entry is on `fingerprint.SCHEMA`.
- `publish_document()` builds its wallbox section through
  `wallbox_from_dump()`, so the CLI and HA share one masking path.
- Removed `probe._document_legacy` (no callers); its rationale now sits on
  `assemble_document()` and `publish_document()`.
- Fixed the stale `device-fingerprints/python/` paths left by the move into
  `device-fingerprints/scripts/python/` (Makefile, settings, sync_version,
  generate_compatibility, tests, docstrings).
- Latest validation (2026-10-16 00:37): `make ci` green, 2947 passed / 4 skipped; `check_pinned_library.py --wheel` green;
  strict mypy and ruff clean. Earlier `make ci` green -- version check, gen
  check, ruff, `ruff format --check`, strict mypy, 2911 passed / 4 skipped,
  wheel and sdist built. `ruff format .` was needed on 11 files whose path
  expressions became one line after the relocation.

## Decisions taken 2026-10-15

- Schema bump for the readings/battery/6100 unification: it is 22.
- Home Assistant publishes the terminal survey's (larger) `battery_pack`.
- **The run sequence stays in the scripts for now.** Every step is a package
  call; the order of the steps and their terminal output remain in
  `probe.capabilities()` and `sungrow_survey.py`. No
  `async_capability_survey(..., on_event)` until there is a second consumer
  for it.

## Remaining todos

1. **Last duplicates in the scripts** -- ✅ done 2026-10-16 00:37
   - ✅ (2026-10-16 00:06) The 6100 transport read is one package call,
     `survey.async_read_6100(unit, attempts=...)` (`answered` / `refused` /
     `no answer`), used by `probe._async_connection` and
     `sungrow_survey._check_transport`. The latter also computed its verdict
     with its own copy of `connection_block`'s rule; it now calls
     `connection_block`. `fingerprint.TRANSPORT_NOT_DETERMINED` moved from
     `probe.py` into the package.
   - ✅ (2026-10-16 00:16; decision: both clients into the library) The block
     read test has one implementation, `sungrow_modbus.block_test`, used by
     the integration and by `blocks.py`. New `sungrow_modbus.raw_client`
     (async, strict, function codes 3/4 only; a test checks that) carries the
     padded-frame / wrong-length diagnosis and counts reconnects.
     `block_test` gained `PADDED`, `WRONG_LENGTH`, reconnect-aware `attempt`,
     `Outcome.reconnects`, `declared()`, and `on_result` / `on_narrowing` /
     `on_narrow` callbacks; the narrowing-budget rationale moved onto
     `block_test.NARROW_BUDGET`. `blocks.py` (854 -> ~390 lines) is argument
     parsing, the printed lines and `report()`; the script-local
     `raw_client.py` and `blocks.BlockOutcome` / `to_outcome` are gone, and
     `sungrow_survey.py` awaits the measurement instead of running it in a
     thread. Tests: `test_block_read_test.py` rewritten against the library,
     plus three raw-client tests over a local socket. Full suite 2943 passed.
   - ✅ `sungrow_survey.py` audit (2026-10-16 00:22, finished 00:37). Mostly terminal I/O
     (prompts, transcript, summary text), which stays. Found:
     - ✅ **Address tail diverged**: every terminal document zero-fills
       (`178.041`) and sorts as text; HA's `address_tail` did not (`107.5`).
       `fingerprint.last_two_octets()` (moved from `probe.py`) is now the one
       rule and `address_tail()` uses it; `publish_document`'s
       `address_value` override is gone. Part of schema 22.
     - ✅ **When the block test may change `layout.py`** (00:34):
       `block_test.findings(outcome, through_module=...)` returns one
       `Finding` per component and outcome with an `Advice` (forwarding
       limit / not narrowed / not evidence / already isolated / isolate);
       `register_ranges()` and `refused_outright()` moved with it, and the
       script's `_advice()` keeps the sentences. **Bug found and fixed:** the
       old check matched words in the failure *detail*, and a padded frame's
       detail ("declared 11 registers, frame sized for 15") contains none of
       them -- so the case `layout.COUNTS` exists for was advised "timed out,
       do not add it to layout.py". A deterministic hangup, which the
       comment beside the rule lists as evidence, was likewise missed. Now
       decided by outcome kind (`block_test.EVIDENCE`), with a detail that
       mentions a timeout still overriding. Regression tests added.
     - Left in the script on purpose: prompts, transcript, the summary
       text, exit codes, the shared-serial note, and the run sequence
       (decision 2026-10-15).
     - ✅ **Transport vocabulary** (00:25): `fingerprint.REPORTED_TRANSPORTS`
       (verdict, table label, filename word per key; `TRANSPORT_WORDS` is
       derived from it), `claim_of()`, `effective_verdict()` and
       `transport_contradiction()` -- the last replacing three copies of the
       check. `probe.py` keeps only `TRANSPORT_MENU` (its wording) and
       composes the old 4-tuple; `generate_compatibility.py` no longer
       imports `probe.py` at all.
     - ✅ `fingerprint.collected_nothing(document)` (00:27).
     - ✅ Register 13265 (00:31): `survey.async_read_module(unit)`, decoded by
       the field through the new `addresses.declared_field()` (moved from
       `probe._field`).

2. **One document builder for both producers** -- ✅ done 2026-10-16
   - `fingerprint.assemble_document()` (replacing the unreleased
     `base_document()`) takes sections already shaped and is the only place
     that decides which sections exist, their order, and what is removed
     before publishing: testimony out of `connection`, the dump masked, a
     `battery_pack` with no value dropped, part B's block checked for the
     serial. Home Assistant's `async_build` calls it directly;
     `publish_document(raw, fingerprint)` is now only the terminal's
     unpacker on top of it (it shapes the wallbox dump through
     `wallbox_from_dump`).
   - The serial guard on the control-test block moved into the package as
     `fingerprint.attach_control_test(document, block, serial=...)`; HA's
     `attach_control_test` (part B is attached after part A is built) is a
     one-line wrapper. The terminal now gets the same guard.
   - **Two HA differences resolved toward the corpus:** a pack whose survey
     read returned no value is no longer published (the CLI never did), and
     the optional sections follow the terminal order -- HA's `contention`
     after `capability_probes`, then `register_dump`, `wallbox`,
     `block_read_test`, `battery_pack`, `control_test`. Diagnostics key
     order changes; no committed document does.
   - Tests in `tests/test_survey_api.py`: one section order, the empty pack
     left out, the serial guard on both doors.

3. **Release**
   - Until the next `sungrow-modbus` release, the PyPI wheel lacks the new
     package API, so `survey.sh` / `.cmd` from this tree fail for
     everyone -- the maintainer included. Seen 2026-10-16: `ImportError:
     cannot import name 'raw_client' from 'sungrow_modbus'`, from uv's cache
     of the 0.1.0a14 wheel. The tree still says 0.1.0a14 too, so the pin
     cannot tell the two apart. `check_pinned_library.py` (no argument) is
     red for the same reason. A release (`scripts/release/sync_version.py
     --set X.Y.Z`) closes it.
   - Meanwhile (2026-10-16): `make scan-local HOST=...` runs the real
     launcher on this tree (`SUNGROW_MODBUS_LIBRARY`, uv `--with-editable`),
     `make scan-wheel` on a fresh wheel, `make controltest-local` the
     control test; a tester can be sent the wheel from `make wheel`. The
     preamble says `NOT a release` (from `direct_url.json`).

4. **Commit**
   - Stage the remaining new/untracked files (`AGENTS.md`, this plan if it
     is to be kept) and commit the migration; the full suite and `make ci`
     are green on the working tree.

## Validation notes

The `git ls-files --stage` assertions now pass: the relocation is staged as
renames in the index, so the full suite is a usable gate again.
`src/sungrow_modbus/survey.py`, `tests/test_survey_api.py` and
`tests/test_discovery_identity.py` are staged.

`check_pinned_library.py` with no argument is expected to be red until the
next release: the integration and the scripts now import package helpers
(`async_probe_words`, `readings_section`, `wallbox_section`, ...) that the
PyPI wheel does not have yet. `--wheel` against a local build is the gate.
