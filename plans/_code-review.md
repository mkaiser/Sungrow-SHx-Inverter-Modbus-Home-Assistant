# Reviewing and cleaning up the code

T100. A prompt for one session per area. Paste the **Prompt** section and
name the area; the rest is what the sessions fill in as they work. Once every
area is done, `plans/_improve-doc.md` aligns the documents with the result.

## Prompt

Review and clean up one area of this repository (named below, or the first
area in the **Status** table that is not done). **Fix what you find**, bugs
included, unless the exceptions below apply.

Read `AGENTS.md` first; its rules outrank this prompt. Then read
`doc/architecture.md` and `doc/development.md`, and the wiki pages that
`AGENTS.md` links for the rules your area relies on.

### The areas, in order

The library comes before the integration, because the integration imports it.

| # | Area | Paths |
| ---: | --- | --- |
| 1 | Library core | `src/sungrow_modbus/` top-level modules: `raw_client.py`, `device.py`, `discovery.py`, `identity.py`, `addresses.py`, `features.py`, `model.py`, `network_names.py`, `energy_integral.py`, `const.py` |
| 2 | Library devices | `src/sungrow_modbus/hybrid_inverter/`, `string_inverter/`, `battery/`, `ihomemanager/`, `logger/`, `wallbox/`, `cards/` |
| 3 | Library diagnosis and capability test | `src/sungrow_modbus/capability_test/`, `diagnosis.py`, `diagnosis_document.py`, `block_test.py`, `dump.py` |
| 4 | Integration core | `custom_components/sungrow_modbus/`: `__init__.py`, `coordinator.py`, `continuous.py`, `entity.py`, the platforms, `services.py`, `websocket.py`, `repairs.py`, `write_owner.py`, `external.py`, `ihomemanager.py` |
| 5 | Integration flows and migration | `config_flow.py`, `config_flow_schemas.py`, `entry_migration.py`, `migration.py` |
| 6 | Integration diagnosis, capability test, dashboard | `diagnosis*.py`, `device_diagnosis.py`, `capability_test.py`, `wallbox_*.py`, `dashboard.py`, `download.py`, `route.py`, `testimony.py`, `network_records.py`, `wifi_module.py`, `links.py`, `texts.py`, `diagnostics.py`, `frontend/` |
| 7 | Diagnosis scripts | `device-diagnosis/scripts/` (read `device-diagnosis/reference.md` first: the PEP 723 header is the whole install) |
| 8 | Tooling | `scripts/` (dev, generate, helpers, release), `Makefile` |
| 9 | Tests | `tests/` |

### What to look for

- **Correctness.** Exception handling (`except Exception` only with a
  traceback; an exception response is an answer, a timeout is not; `None`
  never read as `False`), async misuse (blocking calls in the loop, tasks
  never awaited or cancelled), the write interlock (`PARALLEL_UPDATES`),
  connections and files left open, off-by-one in register counts.
- **The rules in `AGENTS.md`'s tables**, in the code that relies on them:
  `reg()` and no literal addresses outside tests, firmware read before it
  gates, a 0 or an all-NUL string is not a capability, the million-kWh guard,
  contention and its 90 s of quiet.
- **Dead code.** Unused functions, classes, constants and modules (`uvx
  vulture <paths> --min-confidence 60`, then grep every candidate's callers,
  tests and generators before removing it), and leftovers in the tree.
- **Duplication**, within the area and across the library / integration line
  (`diagnosis.py` and `diagnosis_document.py` exist on both sides). Shared
  logic belongs in the library, which has no Home Assistant imports.
- **Structure.** A module over ~1,000 lines is split only where there is a
  clear seam; a split that just moves lines is not a cleanup.
- **Coverage.** `pytest tests/<the area's tests> --cov=<area>
  --cov-report=term-missing`; a branch you touch gets a test. The floor in
  `pyproject.toml` (`fail_under`) only ever rises.
- **Comments and docstrings that no longer describe the code** they sit on:
  correct them, forward-looking only (no "was", "now", "since 0.x").
- **The quality scale**: the `todo` rules in `quality_scale.yaml` that the
  area could close.

### When not to fix

Report it under **Reported**, with file:line and what you would change, and
leave the code as it is, when the fix would:

- change a legacy `entity_id`, a unit class or a `state_class`, or a row of
  `scripts/generate/tables/legacy_entities.py`;
- touch the capability test's restore, its snapshot, its exit codes, or
  13074's probed scale;
- contradict a hardware-verified fact (the `AGENTS.md` tables, a wiki page
  citing a diagnosis or capability test);
- change an address, scale or `state_class` in `registers.py` or
  `sensor_descriptions.py` (they are right because they were reviewed);
- change what a user sees or has stored (an option, a config entry's data, a
  service's fields) beyond fixing a plain bug.

### Rules for the work

- **Edit the source, not the output**: a generated file is fixed in
  `scripts/generate/` and rewritten by `make gen` (`AGENTS.md`'s list).
- **A bug fix comes with a test** that fails without it. A test fixture
  raises the real exception type.
- `make quick` after each change; `make check` before each commit (6-10
  minutes: give it a long timeout and read the exit code and the pytest
  summary, not the last line).
- One commit per coherent change, naming your own paths
  (`git commit -- <paths>`), message prefixed `T100` and saying why. Never
  push without asking (`AGENTS.md`).
- A new script needs `git update-index --chmod=+x`.
- No real serial and no address in anything you write, tests included.

### Done means, per area

- `make check` green.
- The area's row in **Status** filled in, its findings under **Fixed** or
  **Reported**, and a **Log** entry -- after every subtask, not at the end.

## Status

| # | Area | Findings | Fixed | Reported | State |
| ---: | --- | ---: | ---: | ---: | --- |
| 1 | Library core | 7 | 5 | 2 | done |
| 2 | Library devices | 12 | 7 | 5 | done |
| 3 | Library diagnosis and capability test | 9 | 4 | 5 | done |
| 4 | Integration core | 11 | 5 | 6 | done |
| 5 | Integration flows and migration | 7 | 4 | 3 | done |
| 6 | Integration diagnosis, capability test, dashboard | 7 | 5 | 2 | done |
| 7 | Diagnosis scripts | 12 | 6 | 6 | done |
| 8 | Tooling | 12 | 6 | 6 | done |
| 9 | Tests | 11 | 8 | 3 | done |

## Fixed

**Area 1, library core**

- `raw_client.py:138` -- a connect that timed out (`TimedOut`, an `OSError`)
  was rewrapped as a plain `Dropped`, so the block read test reported a host
  that never accepts as a hang-up, not a timeout. Kept as raised;
  `tests/test_block_read_test.py::test_a_connect_that_times_out_stays_a_timeout`.
- `discovery.py:112` -- `async_mdns_services` left its browsers running and
  its `AsyncZeroconf` (port 5353) open when cancelled or failing. Closed in a
  `finally`; `tests/test_discovery.py::test_an_mdns_browse_cancelled_midway_closes_what_it_opened`.
- `network_names.py:289` -- `_async_browse` left its private zeroconf open
  when the browser failed to start. The browser is built inside the `try`;
  `tests/test_network_names.py::test_a_browse_that_fails_to_start_closes_its_own_zeroconf`.
- `model.py:48` -- `UpdateReport.__or__` could name a component both updated
  and failed (failed in the first pass, read in the second). The later pass
  wins either way. No caller merges overlapping passes today, so latent;
  `tests/test_device.py::test_a_later_pass_settles_a_component_either_way`.
- Docstrings that no longer described the code: `discovery.py` said it
  opens no Modbus connection (`async_identify` does); `__init__.py` said
  hybrid inverters only; `device.py` left the iHomeManager out of
  `MappedDevice`'s users; `const.py` and `addresses.reg` told history.
  `discovery.async_hostname` caught `socket.gaierror` beside its base
  `OSError`; dropped.

**Area 2, library devices**

- `hybrid_inverter/smoothing.py:117` -- `TimeWeightedAverage.value` is asked
  by the sensor whenever Home Assistant writes state, but only a feed dropped
  the samples past the window; asked later, they were integrated with
  negative weights (10 then 20, asked a quarter of an hour on: 40). It leaves
  them out as the leak would;
  `tests/test_smoothing.py::test_the_average_asked_without_a_reading_leaves_aged_samples_out`.
- `wallbox/capability_test.py:444` -- `_write` filed `ModbusTimeoutError` and
  `ModbusConnectionError` (both `ModbusError`s) as `REFUSED`, which the ledger
  ranks as established and never asks again. Only a `ModbusExceptionError` is
  a refusal; the rest is `DROPPED`;
  `tests/test_wallbox_capability_test.py::test_a_write_that_times_out_is_dropped_not_refused`.
- `wallbox/plausibility.py:304` -- a restored collection forgot the last
  21313 word, so every restart logged a change that did not happen;
  `tests/test_wallbox_capability_test.py::test_a_restart_logs_no_21313_change_that_did_not_happen`.
- `string_inverter/device.py`, `ihomemanager/device.py` -- the same update
  loop twice (retry a lost link once, then fail the poll). It lives in
  `MappedDevice` behind `lost_link_fails_the_poll`; `device.py`'s docstring
  said only the hybrid retries. The iHomeManager's retry got the SG's tests.
- `string_inverter/document.py:47` -- literal protocol addresses (serial
  4989, firmware 4953 and 4968, dump keys "4999" and "5001"). The serial band
  comes from `DUMP_MASKED`, the rest from `reg()`.
- Dead code: `ev_charger.current_writes` and `charging_writes` (tests only),
  `SungrowWallbox.serial_hint`, `DelayOn.true_since`, the wallbox test's
  `BELOW_MINIMUM_A`. vulture's other candidates are register fields and
  properties read by name through the descriptions, or have callers in the
  integration or the diagnosis scripts.
- Comments: `derived.py`'s mode-pair comment sat above
  `SIGNED_13022_FIRMWARE`; `battery/power.py` told the capacity tolerance as
  history; the wallbox test's `enable` and `below_minimum` options described
  writes they never make; both wallbox tests typed "AC" beside
  `discovery.NAME_PREFIX`. Plus tests for `battery.probe_units`' unit-2 branch
  (`tests/test_battery_discovery.py`), which nothing exercised.

**Area 3, library diagnosis and capability test**

- `diagnosis_document.PROBES` and every band table in `dump.py` typed
  protocol addresses one below the register numbers their labels quote.
  Written through `reg()`; the tables are equal word for word (compared
  before and after). `last_two_octets`' docstring named two contributors'
  home networks; it says what they show instead.
- `diagnosis.async_read_retrying` and `dump._async_read_retrying` -- the same
  loop twice, each carrying the rule that an exception response is an answer
  and a busy one settles nothing. One implementation in `dump.py` (which
  imports nothing heavy), re-exported by `diagnosis` under the name the
  diagnosis scripts import. `tests/test_addresses.py` checks both by the
  right argument (it looked at the dump's `space`).
- Area 2's three `readings` decoders (wallbox, iHomeManager and Logger, SG):
  the word gathering and the any-word-missing rule live in
  `dump.decoded_fields`; each document keeps what it publishes (the
  wallbox's decoded None and model, the SG's missing `held`). The readings
  are identical over synthetic dumps before and after, so no committed
  document's shape moves;
  `tests/test_dump_reads.py::test_a_field_with_a_masked_word_is_not_decoded`.
- `capability_test/procedure.py`: `MIN_PV_W`'s description sat under
  `PV_CUT_ON`, and `ENUMERATIONS`' comment a hundred lines above it over the
  write-path probes. Moved. vulture's candidates are all published result
  fields (`RestartResult.stop_word_seen`, `ProbeResult.expected_slope`, via
  `_asdict`) or have callers in the integration and the diagnosis scripts,
  so nothing removed.

**Area 4, integration core**

- `coordinator.py:813` -- `SungrowRuntimeData.async_paused` set a flag, so of
  two runs holding one entry (a wallbox entry's managed test pauses the
  inverter entry it writes through, beside that entry's own diagnosis) the
  first to end resumed polling under the other. A count, the flag clearing
  with the last hold;
  `tests/test_polling_pause.py::test_the_first_of_two_overlapping_pauses_does_not_resume_polling`.
- `services.py:261` -- `start_inverter` and `stop_inverter` looked up the
  realtime tier's coordinator, which an owner may set to never: both failed
  with a `KeyError`. The write goes through whichever tier is polled, the
  read-back only where the realtime one is;
  `tests/test_services.py::test_stopping_works_with_the_realtime_tier_set_to_never`.
- `__init__.py:1338` -- `async_remove_entry` removed the capability test's
  snapshot and left the inverter's and the wallbox's ledgers and
  plausibility stores in `.storage/` for good. They go with the entry;
  `tests/test_capability_test_ha.py::test_removing_the_entry_takes_the_kept_runs_and_checks_with_it`.
- Dead code and duplication: `SungrowRuntimeData.served_components` had no
  caller; `continuous.py` read polled values through two copies of one
  nested helper and a third variant, one method now. vulture's other
  candidates are Home Assistant hooks called by name, description fields
  read by the generator and migration, or have callers in area 6.
- Comments: the diagnosis entities on every entry were explained by what
  ordinary entries used to lack (`__init__`, `button`, `sensor`, `select`,
  `services`, whose `run_diagnosis` comment still said an ordinary entry
  has no diagnosis entities); `SungrowDeviceEntity` said the wallbox serial
  is never read, where the coordinator reads it and a wallbox entry is keyed
  by it; `polling_paused` claimed to be declared last; `switch` and `select`
  repeated `number.py`'s `PARALLEL_UPDATES` reasoning word for word and
  point at it.

**Area 5, integration flows and migration**

- `config_flow.py:517` -- `_async_claim` found an **ignored** card's entry
  by the serial and offered to move it to the new address; confirming left
  the owner with the card's empty entry, never set up, and nothing running.
  The owner's own flow goes on and Home Assistant puts the new entry in the
  ignored one's place; a discovery (DHCP) leaves it ignored;
  `tests/test_config_flow_connection.py::test_adding_an_ignored_inverter_sets_it_up_instead_of_moving_the_card`,
  `tests/test_config_flow_dhcp.py::test_an_inverter_the_owner_ignored_stays_ignored`.
- `config_flow.py:1255` -- `_set_stage` wrapped `suppress(UnknownFlow)`
  around *creating* the refresh task, which never raises; a dialog closed
  mid-sweep left the task failing with an exception nobody retrieved.
  Caught inside the task;
  `tests/test_config_flow_search.py::test_a_stage_shown_after_the_dialog_closed_raises_nothing`.
- `entry_migration.py:206` -- an `assert` comparing two constants ran in the
  migration path. A test, beside the two untested branches (an entry
  already current, one too new to migrate).
- Duplication and comments: the six capability test permissions were
  written out field by field in the options page; one tuple
  (`const.CAPABILITY_TEST_OPTIONS`) builds the section. Docstrings and
  comments that told history (the preview's opening question, the
  diagnostics path's success dialog, where the raw dump sat until a date)
  or named a setup step that no longer asks the diagnosis's questions; one
  comment twice in `_permissions_section`; the search step repeated the
  sweep's docstring. vulture's candidates are flow steps Home Assistant
  calls by name and functions `__init__.py` and the tests import, so
  nothing removed.

**Area 6, integration diagnosis, capability test, dashboard**

- `diagnosis.py:569` -- auto repeat's wallbox run reaches *Diagnosis: stop*
  as a cancellation, and `_async_run_wallbox` caught only `Exception`: the
  wallbox test put everything back, but the state said running for good, so
  the readings' checks (which skip while a run is in flight) stopped too. It
  ends stopped, as `_async_run_stoppable` does;
  `tests/test_wallbox_capability_test_ha.py::test_a_wallbox_run_the_owner_stops_ends_stopped_with_everything_back`.
- Area 5's handover: the capability test permissions were built field by
  field in both part B drivers (`capability_test._options`,
  `diagnosis._control_options`) and listed a third time in
  `diagnosis_settings._ALLOWED`. `diagnosis_settings.permissions` reads them
  once, `_ALLOWED` is `const.CAPABILITY_TEST_OPTIONS`;
  `tests/test_capability_test_ha.py::test_each_permission_sets_its_own_field_of_the_run`.
- `DiagnosisRunner._async_run` ran the wallbox's checks after part B when the
  entry consented, but only a wallbox entry consents and its runner replaces
  `_async_run`: never ran. Removed.
- Dead code: `diagnosis.async_runner` (no caller), a second import of
  `async_clear_wallbox` inside `wallbox_capability_test.async_restore_leftover`,
  and `testimony.unanswered`'s question list nobody passed (it and the
  refusal build on `missing_keys`). vulture's other candidates are entity
  properties, Home Assistant hooks (`async_get_device_diagnostics`) and
  functions the flows, `__init__` and the tests import.
- Comments: `diagnosis_entities` described its entities as a diagnostics
  entry's alone (the start and stop buttons are on every inverter entry) and
  the held-controls sensor as an ordinary entry's one diagnosis entity; the
  mode select, the readings' timer, `async_clear_ledger` and the wallbox
  runner's observing told what changed; the skip switch compared itself with
  a retired switch; the shutdown guard said it goes once the inverter runs,
  where it goes with the run.

**Area 7, diagnosis scripts**

- `probe.py` `cmd_dump` -- every failed single read went into `refused`, so
  a lost answer or a busy WiNet-S (0x04/0x06, `model.SETTLES_NOTHING`) read
  as a register that does not exist. Only an exception response outside
  `SETTLES_NOTHING` is a refusal; the rest is `no_answer` in the saved dump;
  `tests/test_diagnosis_readings.py::test_the_raw_dump_files_a_timeout_apart_from_a_refusal`.
- `probe.py` `_ask_battery` -- `has_battery` started `False`, so a battery
  voltage the link lost said "none attached" and skipped the brand question.
  It stays `None` and the brand is asked;
  `tests/test_diagnosis_readings.py::test_a_battery_read_that_timed_out_is_not_no_battery`.
- `probe.py` `cmd_units` -- retried every failed read and printed the last
  error, so a refusal followed by a lost answer showed as silence. It reads
  through `async_read_retrying`, which raises an exception response at once;
  `tests/test_diagnosis_readings.py::test_the_unit_sweep_prints_a_refusal_as_a_refusal`.
- Guards for libraries older than the pin: the pinned 0.1.0a58 has
  `wallbox.capability_test`, `managed_test` and `ledger`, every wallbox and
  inverter `Options` field, `capability_test.DRY_RUN_MEANS` and schema 23.
  The `ImportError` exits, the options-field checks (`NEW_FLAGS`,
  `_window_leave`), the copied `DRY_RUN_MEANS` and `with_link_drops`'
  `SCHEMA < 23` branch are gone, with the comments that said the pin lacked
  them. `check_pinned_library.py` resolves every import.
- `sungrow_diagnosis.py`: the wallbox, iHomeManager/Logger and SG paths
  carried the address, reporter and comment prompts three times word for
  word; one `_ask_consent`, with
  `tests/test_diagnosis_replay.py::test_a_device_read_by_its_own_map_is_asked_only_what_no_flag_answers`.
- Dead code, stale counts and comments: `probe.State` (no reader), the
  sweep's unread `settled`, an orphan comment above the proxy answers; the
  diagnosis announced 2181 raw addresses (it counts `DUMP_BANDS`, 2197), the
  pack read said 17 registers (42); comments that told history (the
  round-trip time, 13265's former role, the script's former path, the dump
  budget, `--start-only`, exit 1), and `COULD_NOT_RUN`'s comment sat above
  `RESTORED`. vulture's other candidates are the `DiagnosisSource` and
  `WallboxPort` methods the library calls by name, and the re-exports below.

**Area 8, tooling**

- `Makefile` `build` -- globbed `dist/`, where `python -m build` leaves
  older versions' files: `check_pinned_library.py --wheel` got two paths in
  one argument (no such wheel, exit 2) and `fetch_cards.py --check` archives
  that never carried the cards. It names this version's wheel and sdist, as
  `wheel` does, and the pitfall that asked for the checks by hand went;
  `tests/test_makefile.py::test_the_build_checks_only_what_it_built`.
- `scripts/dev/seed_migration_testbed.py` -- said Home Assistant must be
  stopped and never looked: a running instance writes its in-memory registry
  over the seed. It reads the run lock's pid, as `hacs_testbed.sh` does. A
  second seed doubled the history and stopped on the statistics table's
  unique start time with the registry written; refused until `--reset`.
  Its docstring named a `const.ONLY_DIAGNOSIS_MODE` that does not exist;
  `tests/test_seed_migration_testbed.py`.
- `scripts/dev/ha_watch.py` -- promised that a long-lived token only reads a
  production instance, but `Watch.press` pressed wherever the instance
  pointed. It refuses off loopback before the note or any write;
  `tests/test_ha_watch.py::test_an_instance_off_loopback_is_never_pressed`.
- `scripts/dev/ha_onboard.py:294` caught `Exception` without a traceback, so
  a bug in the script read as an instance refusing. It folds the HTTP,
  connection, payload and JSON errors into one line and lets the rest out;
  `tests/test_dev_instances.py::test_a_bug_in_the_script_keeps_its_traceback`.
- `scripts/generate/tables/writes.py`: `START_STOP` copied 13000's two words
  and nothing read it (the actions take theirs from `services.py`); the
  docstring said the write path never ran on hardware and that the power
  limits, EMS mode, forced charging and backup mode were still to come, all
  of them rows. No row changed; `make gen` writes the same files.
- Comments and help texts: the Makefile counted six description targets
  (eight), called `dev-real` a third instance and its header a second, read
  "Diagnosis an installation" and used `FILE` undeclared;
  `hacs_testbed.sh --marketplace --setup-only` pointed at `make hacs`;
  `check_pinned_library.py` counted two pinned scripts (four);
  `descriptions.py`, `generate_compatibility.py`, `review_names.py` and
  `fetch_cards.py` told what their code replaced, and
  `generate_compatibility`'s imports sat on both sides of its constants.
  `doc/development.md`'s generate row named a multi-inverter YAML generator
  that does not exist and `ha_watch.py` had no row. vulture's other
  candidates are `TypedDict` keys of the write table, names the tests import
  (`ha_http_port.MINOR_VERSION`, `naming.GERMAN_TERMS`, `GERMAN_EXEMPT`,
  `violations`, `writes.WRITABLE_FIELDS`) and `Watch.wait_for_quiet`, which
  watch scripts call, so nothing else removed.

**Area 9, tests**

- Area 7's item: `test_diagnosis_document_label.py` and
  `test_diagnosis_replay.py` import `NEVER_PUBLISH`, `WIFI_OR_ETHERNET`,
  `transport_verdict` and `ModbusExceptionError` from the library, so
  `probe.py` drops its three `noqa: F401` re-exports and `blocks.py` its
  four (nothing else, scripts included, read them).
  `test_block_test.py::test_the_outcome_words_and_the_budget_are_the_terminal_tools`
  compared each re-export with itself and could not fail; it checks that
  neither terminal tool assigns a shared word of its own.
- Fakes that raised the wrong type: refusals as a bare `ModbusError`
  ("Modbus Exception 0x02") raise `IllegalDataAddressError`, rejected writes
  `IllegalDataValueError`, lost links `ModbusConnectionError` and silent units
  or response timeouts `ModbusTimeoutError`, in place of `ModbusError` or
  `RuntimeError` (thirteen modules). The repair test named a refused write
  fails one that does not land, as its docstring says. Plain `TimeoutError`
  fakes stay: `ModbusTimeoutError` is one.
- `test_diagnosis_document_label.py` -- two assertions that nothing of the
  serial survives looked for a ten-digit number the input `A123456789`
  never held, so neither could fail, and the number was no stand-in. They
  look for the input's own digits.
- `test_wallbox_capability_test.py::test_the_fallback_waits_in_silence_and_reports_what_the_car_is_given`
  built a timing wallbox it never ran. It times every read and write on the
  run's clock and asserts a gap of `SILENCE_SECONDS` with nothing sent (a
  sample taken midway fails it).
- Other owners' LAN addresses in fixtures: a contributor's two inverters and
  dongles in the topology, proxy and connection tests, and three more
  houses' cable, dongle and wallbox addresses in the document, diagnosis and
  wallbox CLI tests. Stand-ins on 192.168.60.0/24 and new tails on
  192.168.178.0/24, in the same order, so every sorted list and label reads
  as before. The maintainer's own address stays.
- Duplication: six identical `FakeClock`s and `InstantClock` (imported by
  four wallbox modules from `test_capability_test_ha`) live in
  `conftest.py`; the patch that keeps a created entry off the network,
  written six times in the config flow tests, is conftest's `no_setup`;
  `ready_unit`, which `test_cluster_busy` imported from another test module
  behind three `noqa`s, is conftest's (`test_capability_test_repairs`
  overrides it). Each module's `mock_recorder_before_hass` stays: overridden
  in `conftest.py` it would start a recorder before every `hass`.
- Thirty-odd docstrings and comments told a test's history ("it used to",
  "removed on", "that path is gone"); each says what the test holds and what
  would go wrong without it, measurements keeping their dates. One test name
  lost its "now", and `device-diagnosis/reference.md` names it as it is.
  vulture's other candidates are fixtures used by name, attributes of fakes
  the code reads, and Home Assistant hooks, so nothing else removed.

**From the documents pass**

Part B's *Code that looks wrong* items that were simply wrong prose
(`plans/_improve-doc.md`), aligned with the code:

- The sweep's size: `const.py`, `dump.py` and
  `tests/test_diagnosis_register_dump.py` (module docstring and
  `test_an_asked_for_dump_covers_every_band`) said 2181 addresses in sixteen
  bands; they name `dump.DUMP_BANDS` (2197 in eighteen) instead of a count.
  The test docstring's "off unless somebody asks" says on until the owner
  turns it off (`DEFAULT_DIAGNOSIS_DUMP`), and `dump.py`'s "a switch that is
  off" a switch the owner can turn off.
- `const.py`'s `CONF_CAPABILITY_TEST_WALLBOX` comment lists what the wallbox test writes
  as 21203, 21204 and 21212, never 21211 (not 21211 and 21232);
  `continuous.py`'s `WALLBOX_ALONE_INTERVAL` comment drops "a pause under
  6 A", which the test never offers, and the `CONF_WALLBOX_MAX_AMPS` comment
  "below the minimum" among the checks waiting for an explicit cap.
- `services.yaml`'s `run_diagnosis` comment: every entry has the diagnosis
  buttons, so the action is their counterpart for a script.
- **Not done, waiting on the maintainer**: the user-visible texts themselves.
  The options' sweep description (2181, sixteen), `add_devices`'s dead
  `{devices_mode}` placeholder and the never-raised
  `devices_mode_not_offered` abort, `run_capability_test`'s "off by default",
  start's and stop's "admin rights are required", and `wallbox_max_amps`'s
  "an offer below the 6 A minimum". Their only English source is
  `strings.json` itself (`descriptions.py`'s `render_strings` regenerates the
  `entity` block and keeps the rest), and the session was told not to edit
  that file by hand, so neither it nor the German in `german_texts.json` was
  changed. Proposed: edit those keys in `strings.json` and
  `german_texts.json` together, `make gen`, and a test that finds
  `sum(count)` and `len(DUMP_BANDS)` in the sweep description in both
  languages. Proposed wording: "sweeps 2197 addresses across eighteen bands"
  / "2197 Adressen in achtzehn Bereichen"; `add_devices` ending at "then
  creates them." and the abort removed; for `run_capability_test`, "What it
  may do -- the restart, the export limit, the PV cut and the rest -- is set
  in the integration's options, each allowed until it is switched off
  there."; for start and stop, "only an administrator may call this unless
  the integration's options allow every user"; for `wallbox_max_amps`, the
  waiting checks are "an offer above the rating, and the silence test".

## Reported

**Area 1, library core**

- `doc/architecture.md:7` says the library "never opens a socket".
  `raw_client`, `discovery` (the sweep, `async_identify`) and `network_names`
  (mDNS, `arp`) do, for the diagnosis and the config flow; what holds is that
  the integration's entities poll only through Home Assistant's shared
  connection. For the documents pass (`plans/_improve-doc.md`).
- Two zeroconf browses: `discovery.async_mdns_services` (every service type,
  used only by `device-diagnosis/scripts/python/probe.py`) and
  `network_names._async_browse` (`_http._tcp`, the diagnosis and Home
  Assistant). Folding the first into `network_names` is area 7's call, since
  the diagnosis scripts run on the pinned wheel and the old name must stay
  until the pin moves.

**Area 2, library devices**

- `hybrid_inverter/export_scale.py:285` (13074's probed scale, not touched):
  the write that lifts feed-in limitation sits outside the `try` whose
  `finally` restores 13087, so a lift that times out after landing leaves the
  house capped with no restore attempted. Would move it inside the `try`.
  And `_put_back` (`:401`) reads inside its loop without catching, so a
  failed read ends the attempts instead of trying the next word.
- `wallbox/capability_test.py:519` (the restore, not touched): `_shielded`
  re-shields three cancellations, then awaits the restore unshielded, so a
  fourth cancel cancels it. `managed_test._shielded` loops until it is done;
  would do the same here.
- `battery/discovery.py:76`: a timeout or a lost link on the device type read
  at unit 2 is read as "no device type code, a pack". A slave inverter whose
  answer was lost would be filed as a pack, and may be granted
  `SUNGROW_BATTERY`, which moves write bounds. Would count only a
  `ModbusExceptionError` outside `SETTLES_NOTHING` as a pack -- after a
  measurement of what a pack at unit 2 answers to 5000 through a WiNet-S, a
  refusal or a timeout, which nothing here records.
- `wallbox/managed_test.py:390`, `:409`, `:439`: any `ModbusExceptionError`
  is a refusal, so a busy WiNet-S's 0x04 or 0x06 (`model.SETTLES_NOTHING`)
  confirms "5 A refused" or stops the user-current check. Would ask again
  before believing it, as `export_scale._ask` does.
- Three copies of one decoder: `wallbox/document.readings`,
  `ihomemanager/document.readings` (the Logger reuses it) and
  `string_inverter/document.readings`. They differ in what they publish (the
  SG's has no `held`, the wallbox's keeps a decoded None, its type code names
  a model), so folding them changes committed documents' shape; for area 3,
  beside `diagnosis_document`.

**Area 3, library diagnosis and capability test**

- `capability_test/engine.py:48` (the restore, not touched): `_shielded`
  re-shields three cancellations and then awaits the restore unshielded, so a
  fourth cancel cancels it -- the same as area 2's wallbox finding. Would
  loop until the task is done, as `wallbox/managed_test._shielded` does.
- `capability_test/restore.py:446` (the restart, not touched): a stop write
  that comes back `DROPPED` (a timeout) clears `stopped_at` and returns
  `SKIPPED` without sending a start or reading the running state. A stop
  that landed before the answer was lost leaves the inverter stopped, with
  no exit 5. Would treat a dropped stop as possibly landed: keep
  `stopped_at`, call `async_ensure_running`, and judge by the state.
- `capability_test/base.py:362` (the restore, not touched): `_touch` flushes
  the snapshot through `on_snapshot` from inside `_write`, and the restore
  writes through `_write`. On a cable a restore can write a field the run
  never touched, which appends it and flushes; a flush that raises (a full
  disk, Home Assistant's store) escapes `async_restore` and the fields after
  it are never put back. Would catch and log a failed flush inside the
  restore, or skip `_touch` there.
- `capability_test/readback.py:392` (13074's probed scale, not touched):
  `_measure_export_scale` catches only `ModbusError` around
  `export_scale.async_probe`; a plain `TimeoutError` or `OSError` ends the
  whole run as code 1 (the restore still runs). Would catch
  `(ModbusError, TimeoutError, OSError)` like every other read here.
- `capability_test/ledger.py:180`: `fold_key` reads `direct_connection` with
  `bool()`, so a run whose transport could not be settled (`None`, usually
  contention on a cable) keys as a dongle run. In Home Assistant
  (`capability_test.py:170`) one such run then wipes the kept cable runs and
  starts a ledger whose readback rows are read as a dongle's cache. Would key
  the three values apart -- which changes which kept runs fold, so it is the
  maintainer's call, beside area 6.

**Area 4, integration core**

- `entity.py:396` (the owner's write against a leftover snapshot, not
  touched): `_async_write` sends a time, a window-end switch or the EV
  charger mode as two words; when the first lands and the second fails,
  `async_owner_wrote` is never called, so a leftover snapshot's repair still
  writes the landed register back and auto repeat does not wait
  `OWNER_QUIET`. Would record the writes that landed before re-raising.
- `__init__.py:1338` (the snapshot, not touched): removing a wallbox entry
  leaves its leftover snapshot (`wallbox_capability_test.snapshot_store`)
  in `.storage/`, where the inverter's is removed. Would remove it the same
  way, as the inverter's docstring already argues.
- `quality_scale.yaml`: `dynamic-devices` stays todo -- a pack or wallbox
  found after setup would need a periodic probe on the inverter's few
  sessions and a reload, which changes what an entry does unasked.
  `entity-disabled-by-default` stays todo -- the candidates are entities the
  YAML package never had (pack, wallbox, SG, diagnosis), and disabling them
  changes what existing entries show; the maintainer's call which.
- `doc/architecture.md:95` says `button`'s `PARALLEL_UPDATES` is 0; it is 1,
  because the command buttons write. `:124` says an ordinary entry forwards
  all five platforms; it forwards seven. For the documents pass.
- `ihomemanager.py:47`: its coordinator logs no component going quiet or
  coming back (`_log_transitions` lives on `InverterCoordinator`), so
  `log-when-unavailable` holds per component only for the inverters. Would
  move the transition log into a base both share.
- `__init__.py:1334` reads `DeviceInfo` by key (`info["identifiers"]`), the
  compatibility layer Home Assistant keeps for the TypedDict it replaced;
  `coordinator.py` builds it by keyword for that reason. Would read the
  attribute, once mypy's `UndefinedType` is handled.

**Area 5, integration flows and migration**

- `config_flow.py:2470` (a config entry's stored slot, not touched):
  `SungrowOptionsFlow._async_slot` reads `data.get(CONF_LEGACY_SLOT)`, so
  an absent key and a stored `None` both measure again. But
  `migration.stored_legacy_slot` reads an absent key as the unsuffixed slot
  (an entry that predates the slot claims what it always claimed). A
  devices entry with no key that switches ids in the options gets the slot
  measured and **written** (`async_step_entity_ids`, `:2528`): `None` where
  a numbered YAML slot ever ran, which refuses the way back to legacy ids,
  or another slot than the one its entities were claimed from, which the
  plan then uses to decide which entities are on legacy ids. Would measure
  only for a diagnostics entry or a stored `None`, and read an absent key on
  a devices entry as `""` -- the maintainer's call, since it decides what is
  stored.
- `config_flow.py` is 2,856 lines. The one clear seam is
  `SungrowOptionsFlow` (about 950 lines), but the two flows share
  `_flow_texts`, `_async_legacy_ids`, `_entity_ids_placeholders` and the
  slot-unknown and promotion logic, and `async_get_options_flow` needs the
  class back, so a split moves lines and adds an import cycle to break.
  Left whole; worth it only together with folding the setup flow's
  `entity_ids` and the options flow's `promote` (the same slot, known and
  live checks, ending differently) into one helper.
- Area 6: the capability test permissions are listed again in
  `diagnosis_settings._ALLOWED` (`:78`), and the permission object is built field
  by field twice (`capability_test.py:283`, `diagnosis.py:721`). Would
  build both from `const.CAPABILITY_TEST_OPTIONS`.

**Area 6, integration diagnosis, capability test, dashboard**

- Area 3's `fold_key` (`capability_test/ledger.py:180`), assessed from Home
  Assistant's side (`capability_test.py:144`, `async_ledger_add`): a run
  whose transport could not be settled (`direct_connection` None, usually
  contention on a cable) keys as a dongle run, so on a cable house it wipes
  every kept cable run (up to 30 days), starts a ledger whose readback the
  fold reads as a dongle's cache (`ledger.py:271` checks `is True`), and the
  next cable run wipes it in turn. Keying None apart would not stop the wipe
  and would split stored dongle ledgers that already hold such runs, so
  `fold_key` should stay. Would instead have `async_ledger_add` treat an
  unsettled run like a dry run: returned alone for its own document, the
  kept runs untouched. The cost is that run's effects not being kept, so
  auto repeat asks again -- which changes what is kept, so the maintainer's
  call.
- `wallbox_capability_test.py:597` and `:664` (the snapshot, not touched): a
  stop cancels the wallbox run; the library puts everything back under its
  shield and re-raises the cancellation, so `store.async_remove()` is
  skipped and a fully restored run leaves its snapshot. Setup then logs a
  run that did not finish, and the next run writes the snapshot's words
  again first. Would catch the cancellation there, remove the snapshot when
  every restore row (`restorer.restores`, the managed test's `restored`) is
  back, and re-raise -- or give `WallboxTestRunner.request_stop` a real stop
  at the next step, as the inverter's runner has, so a stop never cancels.

**Area 7, diagnosis scripts**

- Area 1's two zeroconf browses: `probe.py mdns` stays on
  `discovery.async_mdns_services`. The pinned wheel has
  `network_names.async_browse_result`, so the move is allowed, but it
  browses `_http._tcp` only and keeps only Sungrow records, where `probe.py
  mdns` lists every service type the LAN announces -- the point of the
  command (does a dongle advertise under a type nobody knows?). The fold
  belongs in the library: give `network_names._async_browse` the service
  types and a filter, have `async_mdns_services` delegate to it under its
  old name, and move `probe.py` only once that is in the pinned wheel.
- `sungrow_capability_test.py:619` (the snapshot, not touched): `keep`
  writes the snapshot with `Path.write_text`, closed but not `fsync`ed,
  where both wallbox scripts' `_save` flush it to the disk before the first
  write. A power cut at the house shortly after the first write can leave
  an empty snapshot and nothing to `--restore` from. Would write it through
  the same flushed `_save`.
- `sungrow_managed_wallbox_test.py:106` and `:285` (where the managed test
  writes, not touched): the inverter is always unit 1 and the wallbox,
  without `--wallbox`, unit 3. A slave inverter (unit 2 at its own port)
  cannot be targeted, and a wallbox at 2 or 4 behind a dongle is not
  tried. Would take `--unit` for the inverter and try 3, 2, 4 as
  `wallbox.probe_units` does.
- `sungrow_diagnosis.py:1185` (an address in output): `_summary` says it is
  paste-safe because it quotes only the document, but `_summary_control`
  (`:1306`) prints the real host in the run-later line and
  `_summary_unreadable` (`:1365`) prints `host:port`. The transcript is
  private by design; the summary is the part people paste. Would print the
  `<host>` placeholder (the run-later line) and the address tail.
- `ihomemanager_direct.py:178`: `_destination`, when all nineteen
  candidates are taken by other addresses, returns the last and overwrites
  it, where `probe._destination` falls back to a timestamped name. Would do
  the same.
- For area 9: tests import library names through the scripts --
  `probe.NEVER_PUBLISH`, `WIFI_OR_ETHERNET`, `transport_verdict`,
  `ModbusExceptionError` (`test_diagnosis_document_label.py`,
  `test_diagnosis_replay.py`) and `blocks.DROPPED`, `REFUSED`,
  `INCONSISTENT`, `TIMED_OUT` (`test_block_test.py:88`, a comparison of a
  re-export with itself). Importing them from the library would let the
  scripts drop the `noqa: F401` re-exports.

**Area 8, tooling**

- `scripts/dev/screenshot.py:403` (where a shot writes): its default and the
  documented scratch instance are on :8125, which is also `make dev-real`'s,
  the instance pointed at real hardware, and the loopback guard passes both.
  The `diagnosis-running` shot starts an **extended** run, which writes to
  the inverter. Would move the scratch instance to a port of its own (in
  `doc/development.md`'s *Screenshots for the docs* too), and have that shot
  refuse unless the entry's host is the simulator's.
- `scripts/dev/managed_wallbox_field.py:285` (`scan`): any
  `ModbusExceptionError` is filed as "refused", a busy WiNet-S's 0x04 or
  0x06 (`model.SETTLES_NOTHING`) included, and a timeout on one block ends
  the scan with what it read unsaved. Would ask a busy answer again, file a
  lost one as no answer, and keep going.
- `scripts/release/sync_version.py:306`: `--set` writes `pyproject.toml`
  before it finds out whether the manifest and the four script headers can
  be rewritten, so a failure leaves them disagreeing (`--check` catches it,
  nothing undoes it); `--expect` without `--check` is ignored silently.
  Would render every file first and write only when all succeed, and make
  `--expect` imply `--check`. Release tooling, so the maintainer's call.
- `scripts/generate/generate_devices_wanted.py:278`: the generated Version 1
  row's "see item 7" names the hand-written wanted list by its number, so a
  renumbered list leaves the table pointing at another item. Would link the
  item's anchor, or take the number from the list.
- `scripts/generate/generate_simulator_registers.py`: `OVERRIDES`,
  `HOLDING_ONLY` and `FAULT_WORDS` key by protocol address beside comments in
  register numbers ("holding 33208-33219" over 33207...33218). It is exempt
  from `tests/test_addresses.py` on purpose; writing the keys through
  `reg()`, as area 3 did for `dump.py`, would leave the seed byte for byte
  the same and the comments readable at a glance.
- For the documents pass: `doc/development.md`'s *Layout* names
  `inverter/` (it is `hybrid_inverter/`) and leaves out `string_inverter/`,
  `logger/` and `cards/`; its *Two options are called a register dump*
  paragraph says 2181 addresses (`DUMP_BANDS` counts 2197, area 7).

**Area 9, tests**

- The other owners' addresses taken out of the fixtures (above) are still in
  the git history of `tests/`. Rewriting published history is the
  maintainer's call, as it was for the serial fragment.
- `tests/test_no_real_serials.py` matches a serial's shape (`A` and ten
  characters) and words that spell one, so it missed a bare ten-digit run,
  and nothing checks addresses at all. Would add a guard that every IPv4
  literal in a tracked file is a known stand-in (192.168.1.0/24,
  192.168.60.0/24, 10.0.0.0/8, documentation ranges, the maintainer's own),
  listed in the test; the wiki and `doc/` carry addresses too, so the
  allow-list wants the maintainer's review before it gates.
- Test modules import private helpers from each other 38 times
  (`_setup`, `_house`, `_probe`, `_wallbox_unit`, `FakeWallbox`, `WORDS`,
  ...; `test_wallbox_*` form a web around `test_wallbox_entry` and
  `test_wallbox_entities`). Each works, but a test module is then also a
  library, and renaming a helper breaks a file that does not mention it in
  its name. Would move the shared ones into helper modules beside
  `corpus.py` (one for the config flow's fake house, one for the wallbox's
  words and units), in a change of its own.

## Log

- 2026-11-28, area 1 (library core): done. Read every module; vulture's
  candidates all have callers (the diagnosis scripts, the config flow,
  tests), so nothing removed. Four bugs fixed with tests, docstrings
  corrected, two findings reported. Coverage in the area's own tests:
  `discovery` 74 % and `network_names` 70 % (the zeroconf and `arp` paths run
  only against fakes), the rest 86-100 %. `make check` green (9837 passed).
  Next: area 2, library devices.
- 2026-11-28, area 2 (library devices): done. Read every module but the
  register maps field by field (their addresses, scales and state classes are
  reviewed source). Three bugs fixed with tests, one duplicated loop folded
  into `MappedDevice`, literal addresses, dead code and stale comments
  cleaned, five findings reported (two in the restore and 13074's probe).
  Coverage in the area: `battery/discovery` 74 % to 100 %, the rest 85-100 %
  before (`ihomemanager/device` 85 %, its retry now tested). No quality-scale
  rule is the library's to close. `make check` green (9855 passed). Next:
  area 3, library diagnosis and capability test.
- 2026-11-28, area 3 (library diagnosis and capability test): done. Read
  `diagnosis`, `diagnosis_document`, `block_test`, `dump` and the capability
  test's base, engine, procedure, preflight, readback and restore in full;
  `effects`, `writepath`, `ledger` and `plausibility` by their exception
  handling, transport and None paths. Four fixes (literal addresses, one read
  retry, one dump decoder for three documents, misplaced comments), no
  document shape changed; five findings reported, four of them in the
  restore, the restart or 13074's probe. Coverage in the area 91 % (`effects`
  82 %, `diagnosis` 81 %: the live-link paths). No quality-scale rule is the
  library's to close. `make check` green (9856 passed). Next: area 4,
  integration core.
- 2026-11-28, area 4 (integration core): done. Read `__init__`,
  `coordinator`, `continuous`, `entity`, every platform, `services`,
  `websocket`, `repairs`, `write_owner`, `external` and `ihomemanager` in
  full; `PARALLEL_UPDATES` is 1 on all five writing platforms and 0 on
  sensor and binary_sensor, every broad `except` logs a traceback or
  re-raises, and no literal address is in code. Three bugs fixed with tests
  (overlapping pauses, start and stop with the realtime tier off, stores
  left behind by a removed entry), dead code, a duplicated helper and stale
  comments cleaned; six findings reported, two of them at the snapshot. No
  entity id, unit or state class touched. Coverage in the area's tests
  85-100 % (`ihomemanager` 85 %, `repairs` 89 %: the restore's failure
  paths). No quality-scale rule closed: the two `todo` rules this area could
  close change what existing entries show. `make check` green (9859
  passed). Next: area 5, integration flows and migration.
- 2026-11-28, area 5 (integration flows and migration): done. Read
  `config_flow`, `config_flow_schemas`, `entry_migration` and `migration` in
  full against the legacy id, slot, transport and contention pages; no
  legacy id claim, unit class, state class, stored entry data or version
  semantics touched. Probes hold the three answers (6100 through
  `route.async_direct`, the battery read `None` on any failure), units are
  swept, every broad `except` names its types. Two bugs fixed with tests
  (an ignored card offered as an entry to move, the stage refresh's
  `UnknownFlow`), a runtime assert made a test, a permission list and
  stale comments cleaned; three findings reported, one at the stored slot.
  Coverage in the area's tests: `config_flow` 97 %, `config_flow_schemas`
  98 %, `entry_migration` 100 %, `migration` 92 % (the recorder's failure
  paths and the claim's taken-id branch). `config-flow-test-coverage` stays
  todo, its comment brought to the measured figure. `make check` green
  (9864 passed). Next: area 6, integration diagnosis, capability test,
  dashboard.
- 2026-11-28, area 6 (integration diagnosis, capability test, dashboard):
  done. Read `capability_test`, `wallbox_capability_test`, `diagnosis`,
  `wallbox_diagnosis`, `device_diagnosis`, `diagnosis_document`,
  `diagnosis_entities`, `diagnosis_settings`, `diagnostics`, `download`,
  `route`, `testimony`, `network_records`, `wifi_module`, `links`, `texts`
  and `dashboard` in full, the frontend by its exports and error paths. No
  restore, snapshot, exit code or 13074 path touched; the snapshot is
  flushed before the first write and removed only after a clean restore on
  both drivers, a run refuses over a leftover, and every published document
  and download goes through the library's serial door, with host and the
  wallbox's managing serial redacted. One bug fixed with a test (a stopped
  wallbox run left showing as running), the permissions read in one place
  (area 5's handover), dead code and stale comments cleaned; two findings
  reported, area 3's `fold_key` with a recommendation and one at the
  wallbox's snapshot. Coverage in the area's own tests: `device_diagnosis`
  48 % and `diagnosis_settings` 32 % there (their callers are the
  unit-247 entries' and the websocket's tests, outside this set),
  `wifi_module` 69 %, the others
  72-100 %. No quality-scale rule is this area's to close. `make check`
  green (9866 passed). Next: area 7, diagnosis scripts.
- 2026-11-28, area 7 (diagnosis scripts): done. Read `probe`,
  `sungrow_diagnosis`, `sungrow_capability_test`, both wallbox tests,
  `blocks` and the three direct readers in full, the launchers by their
  dispatch and exit codes. Checked every library import against the pinned
  0.1.0a58 wheel (`check_pinned_library.py`); nothing new is imported, and
  the guards for older wheels went. No restore, snapshot, exit code, leave
  or 13074 path touched; the capability test still runs only on a yes or
  `--capability-test yes`, and nobody at a terminal is a no. Three bugs
  fixed with tests (timeouts filed as refusals twice, a lost battery read
  taken for no battery), one duplicated prompt block, dead code and stale
  comments cleaned; six findings reported, one at the snapshot and one
  where the managed test writes, plus area 1's zeroconf question (stays,
  for the library). Coverage of the scripts in their tests: 63 % (`probe`
  49 %, `blocks` 45 %: the live-link subcommands; the device readers
  80-100 %). No quality-scale rule is the scripts' to close. `make check`
  green (9870 passed). Next: area 8, tooling.
- 2026-11-28, area 8 (tooling): done. Read the Makefile, every script under
  `scripts/dev`, `scripts/release` and `scripts/helpers` in full, and the
  generators by their inputs, comments and `--check` paths; the input tables
  by their comments only (no row of `legacy_entities.py`, `writes.py`,
  `naming.py` or the two JSON tables changed). `make gen` writes the same
  files after every commit. The hardware and Home Assistant scripts keep
  their guards: `ha_onboard`, `screenshot` and `ha_watch` refuse off
  loopback (`ha_watch` now for a press by token too), `managed_wallbox_field`
  writes only on `charge`, flushes its snapshot first and restores until a
  fresh session reads it back, and the seed refuses a running instance.
  Four bugs fixed with tests (the build's globs, the seed's two guards, a
  press by token off loopback), one broad `except` narrowed, dead code and
  stale comments cleaned; six findings reported, one where a screenshot
  writes. Coverage of the scripts in their tests: `seed_migration_testbed`
  92 %, `ha_http_port` 93 %, `check_pinned_library` 87 %, `ha_watch` 76 %,
  `check_line_endings` 72 %, `sync_version` 53 %, `ha_onboard` 42 % (its
  HTTP paths run only against a live instance); the generators run as
  subprocesses under `gen-check`. No quality-scale rule is the tooling's to
  close. `make check` green (9881 passed). Next: area 9, tests.
- 2026-11-28, area 9 (tests): done. Read `conftest.py` and every fixture
  that fakes a failure, scanned all 150 modules for assertion-free tests,
  tautological asserts, broad `raises`/`except`, skips, wall-clock and long
  sleeps, cross-module imports and history wording, and every IPv4 literal
  against the known houses. No guard test weakened: `test_no_real_serials`,
  `test_recorder_migration`, `test_quality_scale`, the wiki lint and
  `test_addresses` are untouched, and the outcome-word test is tighter.
  Eight fixes (area 7's re-exports, wrong exception types, two assertions
  that could not fail, other owners' addresses, three duplicated fixtures,
  history docstrings); three findings reported, one at the address guard
  that is missing. No skip or xfail that should run: the conditional skips
  guard unreadable files and a Home Assistant without its rule list. The
  waits in fixtures are cancelled by the code's own timeouts; nothing
  sleeps for real, so the suite's time is unchanged. `fail_under` stays
  93.9 (only tests and two script imports changed). `make check` green
  (9882 passed, 1 skipped). Next: `plans/_improve-doc.md`.
