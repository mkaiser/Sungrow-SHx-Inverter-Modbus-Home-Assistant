# Deduplication, part 2: results beside the launchers, the snapshot, the wallbox

Committed as `plans/deduplication-part2.md` (step 0). Continues
`plans/handover-session.md`; item numbers follow that file's "Open" list.

## Progress (updated as work goes)

- [x] 0 filed
- [x] 2 snapshot: dry run writes none; a clean run and a confirmed `--restore`
  remove theirs; three `_run` tests in `test_control_test_cli.py`.
- [x] 3 every file beside the script (`probe.HERE`, `_workspace()` in both),
  `_checkout_root` gone, `.gitignore` by name, guard test
  `test_everything_a_run_writes_is_ignored`, docs. `make check` green.
- [x] 8 `.testdata/` emptied -- **moved**, not deleted, to
  `/home/vscode/testdata-archive-20261013/`: `fingerprints/` held 10
  `.raw.json` captures and documents from other houses matching nothing
  committed. Delete the archive once checked.
- [x] 4 launchers. The planned fix does not work: astral.sh answers Python's
  user agent with 403, and the uv installer itself needs curl or wget. The
  fallback is `python3 -m pip install --user uv` (lands in ~/.local/bin, where
  `find_uv` looks). Also fixed: `download | sh || exit 1` passed a failed
  download (sh succeeds on empty input); now downloaded whole first. Checked
  with a restricted PATH + empty HOME under `script`: pip route installs uv
  and runs the survey on PyPI 0.1.0a11; a failing curl stops with the manual.
  Docker run still for the maintainer.
- [x] 6 INCONSISTENT detail is `failed n/m`.
- [x] 5b `block_test.document(client=, reconnects=)`, `blocks.to_outcome`,
  `_block_document(outcome, client)`; `_CLIENT_LABEL` and the survey's own
  ROUNDS/ATTEMPTS gone (imported). Round-trip test replaces key-for-key.
- [x] 5a `wallbox_registers.CONFIDENCE/CODES/LOCAL_CLOCK/ENABLED/START_STOP`,
  `wallbox.readings()` + `async_mapped_words()`, `dump.WALLBOX_BANDS/MASKED`,
  `SungrowWallbox.async_read_words`. probe.py's copy gone. Integration
  `_async_wallbox`: survey shape, dump with `CONF_SURVEY_DUMP`, progress
  counted. Golden test passes on the first run (gerd dump -> committed
  readings). `make check` green, `check_pinned_library --wheel` green.
- [x] 7 Todo.md updated in the working tree, **not committed**: it carries
  the maintainer's own uncommitted notes.
- [~] 9 0.1.0a12: version moved, `make check` green (2537), hassfest clean,
  sdist+wheel build, twine check and `check_pinned_library --wheel` green.
  Committed and tagged `v0.1.0a12` locally. **Not pushed** -- waiting for
  the go-ahead; then PyPI, `make pin-check`, launchers outside a checkout.
- Simulator: `sungrow_survey.py` from the repo root writes document +
  transcript beside the script, both ignored; control test from its folder
  removes its snapshot after a clean restore; `--dry-run` writes none.
  Found, not fixed: `--simulated` exits 4 -- the simulator stores 13074 as
  handed and the run writes at the default x10, so leg B reports a wrong
  slope. Contradicts CLAUDE.md's "a simulator cannot produce a finding".
- Side task: `plans/wallbox-hardware-test-gerd.md` written (hardware test of
  the wallbox half after 5a + 0.1.0a12).

## Context

0.1.0a11 is on PyPI and the two terminal tools run on it from Windows (item 1,
confirmed by the maintainer). What remains:

- **today** results land in the repository's `.testdata/` inside a checkout
  and in the working folder outside one. **New rule: always next to the
  script** -- the `.sh`/`.ps1`/`.cmd` and the `.py` share one folder, and every
  file a run writes goes there, checkout or not, launcher or `make` or plain
  `python`. No `.testdata/` anywhere in either tool;
- the control test never deletes its snapshot, contradicting CLAUDE.md, and a
  dry run writes one; 178 files piled up;
- the survey still owns the wallbox decoder (`probe.WALLBOX_*`) and its own
  block-document renderer, and the integration publishes a `wallbox` section
  of a *different shape* under the same key;
- the library's block test keeps a long detail sentence nobody sees;
- `Todo.md` is stale; `.testdata/` is full of tool output.

Decisions taken: **always** write every file the two folders' scripts produce
next to the script, with no checkout special case; delete **everything** the tools wrote under `.testdata/`; shorten the
library wording; give the integration **full parity** for the wallbox,
register dump included.

## Steps

### 0. File this plan
Copy this file to `plans/deduplication-part2.md`.

### 2. The control test's snapshot (item 2)
`scripts/sungrow_control_test/sungrow_control_test.py`, `_run` (~line 541-631):
- **Dry run writes no snapshot**: pass `on_snapshot=None` when `args.dry_run`
  (nothing is written to the inverter, so there is nothing to restore).
- **Delete it after a clean restore**: after `outcome = await run.async_run()`,
  unlink `snapshot_path` when `not outcome.not_restored` and
  `outcome.code != 5`. Keep it, and print the `--restore` hint, otherwise.
  `--restore` mode deletes the file it restored from once the read-back
  confirms (`_restore_mode`, ~line 410).
- Tests in `tests/test_control_test_cli.py`: drive `_run` against
  `MockModbusConnection` (as `tests/test_control_test.py` drives the engine) for
  a clean run (snapshot gone), a run with `not_restored` (snapshot kept, hint
  printed), and a dry run (no snapshot ever written).
- CLAUDE.md "Rules the procedure turns on" already states the rule; make the
  sentence name both drivers.

### 3. Every result beside the script (item 3)
One rule for both folders: **anchor on `Path(__file__).resolve().parent`**, not
the working directory -- `make scan` and `make controltest` run from the repo
root, the launchers `cd` into their folder; both must land in the same place.

- `scripts/sungrow_read_only_survey/sungrow_survey.py` `_workspace()`: return
  `(here, here)` where `here` is the script's folder; drop `in_checkout` and
  the message gated on it (always print the "two files" sentence).
- `probe.py`: `capabilities --save` default and `dump --save` default become
  the script's folder (`Path(__file__).resolve().parent`, dumps as
  `<label>.dump.json`); delete `_checkout_root` (its only caller goes) and
  `doc/wallbox_registers.md`'s `.testdata/dumps/` reference follows.
- `scripts/sungrow_control_test/sungrow_control_test.py`: `_workspace()`
  returns the script's folder; drop `RESULTS_DIR` and the `parents[2]` check.
- `.gitignore`: ignore what the tools write, by name pattern, in exactly these
  two folders -- `scripts/sungrow_read_only_survey/*.json`,
  `scripts/sungrow_read_only_survey/sungrow-scan-*.log`,
  `scripts/sungrow_control_test/*-control_test.json`,
  `scripts/sungrow_control_test/*-snapshot.json`. Neither folder tracks a
  `.json` or `.log` today.
- **Guard test** (new, `tests/test_survey_dependencies.py`): for each name a run
  writes (a survey document label, a dump, a transcript, a control-test result
  and snapshot), `git check-ignore` the path inside its folder must succeed.
  This is the one thing standing between a real serial (the transcript) and a
  commit, and it has happened before.
- Rewrite the location tests: `tests/test_sungrow_survey.py` (the three
  `_workspace`/`_checkout_root` tests become "writes beside the script, from
  any working directory"), `tests/test_control_test_cli.py`
  (`test_a_run_writes_where_the_read_only_survey_writes` -> "beside itself").
- Docs: CLAUDE.md (snapshot location, "transcript stays in `.testdata/`",
  serial-constraint bullet), `scripts/sungrow_read_only_survey/README.txt`
  ("in this folder"), `doc/device-fingerprints/README.md` ("What a run writes"
  table, line ~89), `doc/maintainer_setup.md`, `doc/development.yaml` and the
  `Makefile` `controltest-restore` help (`FILE=scripts/sungrow_control_test/...`).

### 4. Testing the launchers on a clean machine (item 4)
Finding first: **`python:3.13-slim` has neither `curl` nor `wget`**, so
answering y in `read_only_survey.sh` / `control_test.sh` there ends in "Neither
curl nor wget". Fix: when both are missing but a `python3` exists, download
the installer with
`python3 -c 'import urllib.request,sys; sys.stdout.buffer.write(urllib.request.urlopen(sys.argv[1]).read())' https://astral.sh/uv/install.sh | sh`.
Same change in both `.sh` launchers (the "launchers differ only where they
must" test keeps them aligned).

How to run it (on the Windows desktop with Docker Desktop, or any Linux host),
from the repository root:

    docker run --rm -it -v "${PWD}/scripts/sungrow_read_only_survey:/s" -w /s python:3.13-slim sh ./read_only_survey.sh <inverter-ip>
    docker run --rm -it -v "${PWD}/scripts/sungrow_control_test:/c" -w /c python:3.13-slim sh ./control_test.sh <inverter-ip> --dry-run

Answer N once (expect the manual instructions, exit 1), then run again and
answer y (expect uv to install into the container and the run to start).
Results land in the mounted folder, i.e. beside the launcher on the host. For
a pristine Windows, the same with **Windows Sandbox**: copy the folder in and
double-click `read_only_survey.cmd`.

### 5. The remaining duplication (item 5)

**5a. Wallbox decoder into the library.**
- `src/sungrow_modbus/wallbox_registers.py`: add `CONFIDENCE` (field -> held
  word, transcribed from `doc/wallbox_registers.md`'s Confidence column) and
  `ENABLED` / `START_STOP` code tables.
- `src/sungrow_modbus/wallbox.py` (or a new `wallbox_dump.py`): `readings(dump)`
  that walks `COMPONENTS`, decodes each field with its own descriptor
  (`descriptor.decode(words)`), and publishes exactly today's published shape:
  names without `_raw`, `register`, `held`, `value`, `unit`, `means`
  (`"unknown code"` for an unknown code), `model` for the type code,
  `local_time`/`note` for the two epoch fields; empty strings skipped.
- `src/sungrow_modbus/dump.py`: add `WALLBOX_BANDS` and `WALLBOX_MASKED`.
- `probe.py`: delete `WALLBOX_FIELDS`, `WALLBOX_ENUMS`, `WALLBOX_MODELS`,
  `WALLBOX_DUMP_BANDS`, `WALLBOX_DUMP_MASKED`, `_wallbox_readings`,
  `_wallbox_time`, `_masked_dump`; use `dump.masked`, the library constants
  and `readings()`.
- **Integration, full parity**: `custom_components/sungrow_modbus/fingerprint.py`
  `_wallbox` sweeps `WALLBOX_BANDS` with `dump.async_dump` on the wallbox's
  unit when the existing survey-dump option (`CONF_SURVEY_DUMP`) is on, and
  publishes `{"unit", "readings": readings(masked), "register_dump": masked}`
  -- the survey's shape. Without the option: `{"unit", "readings": ...}` from
  a single read of the mapped fields, in the same per-field shape.
- Tests: repoint `tests/test_wallbox_readings.py`,
  `tests/test_wallbox_registers.py` and `tests/test_fingerprint_label.py`
  (~1052-1086) at the library. Replace the survey-vs-library agreement test
  with a golden test: the committed gerd fingerprint's `register_dump`
  decodes to exactly its committed `readings`. Add `CONFIDENCE` covers every
  field and every word is one of the five defined in the md. Add an
  integration test of the `wallbox` section's shape with and without the dump
  option.

**5b. One block-document renderer.**
- `src/sungrow_modbus/block_test.py` `document()`: keyword arguments
  `client: str = CLIENT` and `reconnects: int = 0`.
- `scripts/sungrow_read_only_survey/blocks.py`: `to_outcome(BlockOutcome) ->
  block_test.Outcome` (tuples to `Block`, 6-tuple culprits to
  `(Block, kind, detail)`).
- `sungrow_survey._block_document`: `None` -> `None`, else
  `block_test.document(blocks.to_outcome(outcome), rounds=ROUNDS,
  attempts=ATTEMPTS, client=<the client's label>, reconnects=outcome.reconnects)`;
  `ROUNDS`/`ATTEMPTS` imported from `block_test`. Pass the label explicitly and
  drop the module-global `_CLIENT_LABEL`.
- `tests/test_block_test.py` key-for-key agreement test becomes a converter
  round-trip test; `tests/test_sungrow_survey.py` block-document tests keep
  passing unchanged.

### 6. Library wording (item 6)
`src/sungrow_modbus/block_test.py` `attempt()`: INCONSISTENT detail becomes
`f"failed {failures}/{attempts}"`, matching `blocks.py`;
`tests/test_block_test.py:170` asserts the short form. Not user-visible
(`measure` discards it), so no behaviour changes.

### 7. Todo.md
Item 1 (release with schema 20) -> done in 0.1.0a11. Keep item 2 (integration
fingerprint carries `export_scale`). Replace the stale "Running the scripts
from Windows" section (`scripts\sungrow_scan`, stdlib-only, `pip install -e`)
with the launchers: `read_only_survey.cmd`, `control_test.cmd <host> --dry-run`.
Add the release of 0.1.0a12 (step 9) until it is done.

### 8. Delete the tools' local output
Everything the tools wrote under `.testdata/`: `.testdata/control-tests/`
(whole folder, run logs included), `.testdata/fingerprints/`,
`.testdata/sungrow-scan-*.log`, `.testdata/bar12-*.log`. Gitignored, so no
commit; done after step 3 so nothing writes there again. Other `.testdata/`
content (none today besides these) stays.

### 9. Release 0.1.0a12
Steps 5 and 6 change the library, and the survey imports the new names, so the
uv route needs a release: `make version VERSION=0.1.0a12` (moves pyproject,
manifest and both script pins), full gate, hassfest, one commit, annotated tag
`v0.1.0a12` with user-facing notes, `git push --follow-tags`, wait for PyPI,
then `make pin-check` green. Ask before pushing.

## Order

0 -> 2 -> 3 -> 8 -> 4 -> 6 -> 5b -> 5a -> 7 -> 9. Commit after 3 and after 5
(script/library boundaries), release last.

## Critical files

- `scripts/sungrow_read_only_survey/{sungrow_survey,probe,blocks}.py`, both
  `read_only_survey.sh` / `control_test.sh`
- `scripts/sungrow_control_test/sungrow_control_test.py`
- `src/sungrow_modbus/{wallbox_registers,wallbox,dump,block_test}.py`
- `custom_components/sungrow_modbus/fingerprint.py`
- `.gitignore`, `CLAUDE.md`, `Todo.md`, `doc/device-fingerprints/README.md`
- tests: `test_sungrow_survey`, `test_control_test_cli`,
  `test_survey_dependencies`, `test_wallbox_readings`,
  `test_wallbox_registers`, `test_fingerprint_label`, `test_block_test`

## Verification

- `make check` (ruff, mypy, gen-check, version-check, pytest) green after each
  commit; `scripts/release/check_pinned_library.py --wheel` on a local build.
- Simulator (`make sim-bg`): `read_only_survey.sh 127.0.0.1 --port 5020` and
  `make scan-sim` both write the document and transcript into
  `scripts/sungrow_read_only_survey/`; `git status` shows nothing new.
  `control_test.sh 127.0.0.1 --port 5020 --simulated --no-restart` leaves only
  `<stamp>-control_test.json` (snapshot deleted); `--dry-run` writes no
  snapshot.
- Golden: the gerd fingerprint's wallbox dump decodes through the library to
  its committed `readings`, byte for byte.
- After the release: from a copy of each folder outside the checkout, both
  launchers run through uv on PyPI 0.1.0a12; `make pin-check` green.
- Maintainer: re-run both `.cmd` launchers on Windows from a pull; results
  appear beside the `.cmd`. Optionally the Docker commands in step 4.
