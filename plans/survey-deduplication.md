# Survey deduplication: the survey runs on the PyPI library via `uv`

## Why

`scripts/sungrow_survey/` carries its own copy of the library's knowledge:

- `portable.py` (658 lines): a stdlib Modbus client, the register decoder, the plan
  loader, and copies of `model_for`, `model_for_capacity`, `hosts_in` and `network_of`;
- `scan_plan.json`, generated from the library by `scripts/generate/generate_scan_plan.py`;
- literal tables in `probe.py`: `FINGERPRINT`, `FIRMWARE`, `SCHEMA`,
  `OTHER_INVERTER_ANSWERS`, `NEVER_PUBLISH`, `WIFI_OR_ETHERNET`, `IDENTIFY_UNITS`, ...;
- a library-or-not branch in `probe.py` (`have_library`, `_require_library`, ...);
- about 20 tests whose only job is to keep the copies equal
  (`test_fingerprint_tables_agree.py`, `test_portable_decoder.py`,
  `test_portable_readings.py`, ...).

The copy exists because contributors run the survey with a bare Python 3.11 and
install nothing. `sungrow-modbus` is now on PyPI, and `uv` fetches both a
suitable Python (≥ 3.13) and the library on demand. So the survey becomes a
PEP 723 script that depends on the library, and the copy goes away.

Contributors start it through a launcher, `survey.sh` or `survey.cmd`. The
launcher:

- uses `uv` when it finds it;
- otherwise uses a Python that already has the pinned library;
- otherwise offers to install `uv`, and asks first.

## Phase 1: entry point

**PEP 723 header** at the top of `scripts/sungrow_survey/sungrow_survey.py`, under the shebang:

```python
# /// script
# requires-python = ">=3.13"
# dependencies = ["sungrow-modbus==0.1.0a10", "modbus-connection[tmodbus]>=4.10.0"]
# ///
```

- The `[tmodbus]` extra is needed because the library depends on bare
  `modbus-connection`, while `probe.py` and `blocks.py` import
  `modbus_connection.tmodbus`.
- An exact `==` pin lets uv resolve a pre-release without `--prerelease`.
- Plain `python sungrow_survey.py` ignores the header, so `make scan` keeps
  using the editable library. Until phase 3 the survey also still runs on a
  bare Python, because the fallbacks are still there.

**`scripts/release/sync_version.py`** mirrors the version into that pin, and
`--check` fails when the pin differs. That makes it the third place the
version lives, after `pyproject.toml` and `manifest.json`.

**Launchers** in `scripts/sungrow_survey/`. All three read the pin from the
PEP 723 header, so the version lives in one place, and all three forward every
argument:

| File | Role |
|---|---|
| `survey.sh` | Linux/macOS, `#!/bin/sh`, executable bit |
| `survey.ps1` | Windows logic |
| `survey.cmd` | Double-clickable: `powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0survey.ps1" %*`, then `pause` only when started from Explorer |

Logic (the same in sh and ps1), with the working directory set to the script's folder:

1. **Is `uv` there?** Check PATH, then `~/.local/bin/uv`
   (`%USERPROFILE%\.local\bin\uv.exe`), which covers an earlier install that is
   not on PATH yet. If found, run `uv run --script sungrow_survey.py <args>`.
2. **Are the requirements met without uv?** Look for `python3`/`python`
   (`py -3.13`/`python` on Windows) that is ≥ 3.13, where
   `importlib.metadata.version("sungrow-modbus")` equals the pin and
   `import modbus_connection.tmodbus` works. If so, run it directly.
3. **Otherwise**, say what is missing and ask `Install uv (from astral.sh)? [y/N]`.
   - On yes, run the official installer, `curl -LsSf https://astral.sh/uv/install.sh | sh`
     (falling back to `wget -qO-`) or `irm https://astral.sh/uv/install.ps1 | iex`,
     then go back to step 1.
   - On no, or with no terminal to ask on, print the manual instructions and exit 1.

The launcher passes the survey's exit code through: codes 0 to 5 mean
something. The launcher's own failures use 1.

**Tests.** `tests/test_scan_is_standalone.py` checks that:

- the header exists;
- its pin equals the version in `pyproject.toml`;
- `survey.sh` has a shebang and the executable bit.

## Phase 2: the library holds what the survey still copies

- Move `IDENTIFY_UNITS` into `sungrow_modbus.discovery`;
  `custom_components/sungrow_modbus/const.py` re-exports it.
- `probe.py` imports `PROBES`, `FIRMWARE`, `SCHEMA`, `UNAVAILABLE`,
  `STAND_IN_PREFIX`, `NEVER_PUBLISH`, `OTHER_INVERTER_CLAIMS`,
  `WIFI_OR_ETHERNET`, `OUTPUT_TYPES`, `stand_in`, `classify` and
  `transport_verdict` from `sungrow_modbus.fingerprint`, and its literals go.
- `tests/test_fingerprint_tables_agree.py` goes. Its two checks that are not about
  agreement (`..._known_one`, `..._protocol_addresses`) move to
  `tests/test_fingerprint_label.py`.
- **Release order:** the scripts may import only what the pinned wheel has.
  `scripts/release/check_pinned_library.py` scans `scripts/sungrow_survey/*.py`
  as well as the integration, so `--wheel` gates it in CI.

## Phase 3: one stack in `probe.py` and `sungrow_survey.py`

- Delete these functions and every `from portable import ...` branch:
  - `have_library`, `_require_library`, `_modbus_error`;
  - `_model_for`, `_battery_model_for_capacity`.
- Replace them with module-level library imports:
  - from `modbus_connection`: `ModbusTcpParams`, `tmodbus.ModbusConnection`, `ModbusError`;
  - from the library: `model_for`, `model_for_capacity`, `hosts_in`, `network_of`,
    `COMPONENTS`, `addresses.field_address`;
  - `battery_registers` for the pack units.
- In `sungrow_survey.py`:
  - `portable.hosts_in`/`NetworkTooLarge` become `sungrow_modbus.discovery`;
  - 13265 is read through the library and decoded with `model.present`;
  - the "plan ... verified against the library" summary line goes.
- The document's "which client took it" field becomes a constant (the library).

## Phase 4: `blocks.py` keeps its lenient instrument

- `--client raw` is a measuring instrument, not a copy. It trusts `byte_count`
  on purpose, to name the count a padded frame needs.
- `portable.py` shrinks to that client (`Connection`, `Dropped`,
  `_recv_exactly`, `ModbusError`) and is renamed `raw_client.py`.
- The block plan comes from `sungrow_modbus.block_test.inverter_blocks()`, and
  the component and field lists from the library, not from `load_plan()`.

## Phase 5: delete the plan and its guards

- Remove:
  - `scan_plan.json` and `scripts/generate/generate_scan_plan.py`;
  - its entry in `Makefile`'s `GENERATORS`;
  - its `--check` step in `.github/workflows/validate.yml`.
- Delete these tests:
  - `tests/test_portable_decoder.py` and `tests/test_portable_readings.py`;
  - `test_the_scan_plan_matches_the_library` in `tests/test_registers.py`;
  - the plan half of `tests/test_addresses.py`;
  - `test_it_reads_exactly_the_blocks_the_scan_plan_records` in `tests/test_block_test.py`.
- `tests/test_scan_is_standalone.py` becomes `test_survey_dependencies.py`.
  Module-level imports may only be the standard library, the sibling modules,
  `sungrow_modbus` and `modbus_connection`, and the PEP 723 dependencies must
  cover them.
- Check `tests/test_makefile.py`, `tests/test_sungrow_survey.py` and
  `tests/test_survey_register_dump.py` for references to the plan or `portable`.

## Phase 6: documentation

- `scripts/sungrow_survey/README.txt`: run `./survey.sh`, or double-click
  `survey.cmd`. Python 3.11 is no longer mentioned.
- `CLAUDE.md`:
  - replace "The survey runs with nothing installed";
  - in the commands table, add the launchers and remove the
    `generate_scan_plan.py` and `portable.py` rows;
  - remove `scan_plan.json` from "Do not hand-edit".
- `src/sungrow_modbus/fingerprint.py`: the docstring describes one producer of
  the tables and two consumers.
- `custom_components/sungrow_modbus/const.py`: the duplication comment goes.
- `doc/development.yaml` and `doc/integration_plan.md`, plus the docstrings in
  `battery_registers.py`, `wallbox_registers.py` and `block_test.py` that cite
  the plan.

## Verification

- `pytest`, `make check` and `python scripts/release/sync_version.py --check` pass.
- Against the simulator (`make sim-bg`):
  - `scripts/sungrow_survey/survey.sh 127.0.0.1 --port 5020` with uv installed:
    the document appears under `.testdata/` and the exit code comes through;
  - the same with uv hidden from PATH, from the devcontainer venv (editable
    library at the pinned version);
  - from a clean `python:3.13-slim` container with no uv: answer `N` (prints
    instructions, exits 1), then `y` (installs uv, runs the survey).
- Windows: `survey.ps1`/`survey.cmd` need a manual run on a Windows machine.
- After each later phase: `make check`, `make scan-sim`, and
  `python scripts/release/check_pinned_library.py --wheel dist/*.whl`.
