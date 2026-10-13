# Handover: survey deduplication and the two terminal tools

State at hand-over, 2026-10-13, on `proper-ha-integration`.

## Where things stand

- `daba75a` **Release 0.1.0a11**, pushed, tagged `v0.1.0a11`, **on PyPI**.
  The survey and the control test run on the published `sungrow-modbus`
  library through PEP 723 headers and uv launchers; the survey's own copy of
  the library (`portable.py`, `scan_plan.json`, its generator, the tables in
  `probe.py` and the tests that kept them equal) is gone.
- `af21106` **not pushed.** Script-only changes, so no PyPI release is needed:
  - one file to send from each tool, both in `.testdata/fingerprints/` (or
    the working folder outside a checkout); no `.raw.json`, no `*-private.md`;
  - the survey always runs the raw register dump and names the library
    version; `tzdata` in its header; multi-line PEP 723 dependency lists;
  - `tmodbus` connection lines counted, not printed;
  - control test: permission wording, measured restart times, "press Enter";
  - the integration's restart option text (`strings.json`) -- this one ships
    with the next **integration** release.

Folders: `scripts/sungrow_read_only_survey/` (`read_only_survey.{sh,ps1,cmd}`)
and `scripts/sungrow_control_test/` (`control_test.{sh,ps1,cmd}`).

## Open

1. **Push `af21106`**, then re-test on Windows from a pull:
   - `read_only_survey.cmd`: the PowerShell launcher's new multi-line header
     parsing has never run on Windows; `read_at_local` should now show
     `+02:00`, not `+00:00` (tzdata); the end should report dropped
     connections as one line.
   - `control_test.cmd <host> --dry-run`: the permission question, the
     "Press Enter" pause, Ctrl+C at that pause (expect `exit 1 ... cancelled
     before anything was written`), and the two files in
     `.testdata\fingerprints\`.
2. **The control test never deletes its snapshot.** CLAUDE.md says the
   snapshot is "removed only once everything is back and read back", and a
   leftover becomes a repair -- true for the integration, not for the CLI:
   nothing in `sungrow_control_test.py` unlinks it. 178 have piled up in the
   old `.testdata/control-tests/`. Decide: delete it after a clean restore
   (exit 0/3/4), keep it on 5. A dry run writes one too, though it writes
   nothing to the inverter -- probably should not.
3. **Undecided: write results next to the launcher.** Today a run inside a
   checkout writes to the repository's `.testdata/`, outside one to the
   working folder. The proposal was always `scripts/<tool>/` beside the
   `.cmd`, with `.gitignore` rules and a test that the source tree stays
   clean. The maintainer asked what it meant; no decision yet.
4. **Not run: a clean `python:3.13-slim` container** with no uv, answering
   N and then y. Covered here by an empty `HOME` and a bare `PATH` (both
   answers worked, uv installed and the survey started), but never in a
   pristine image -- the container had no Docker.
5. **Remaining duplication in the survey**, outside the plan's scope:
   `probe.WALLBOX_FIELDS` / `WALLBOX_MODELS` mirror
   `sungrow_modbus.wallbox_registers` (with a confidence column the library
   lacks), and `sungrow_survey._block_document` produces the same shape as
   `block_test.document` from a different outcome type.
6. **Wording drift, library vs script:** `block_test.attempt` still says
   "failed 1/2 -- most likely another Modbus client, not this register";
   `blocks.py` now says only "failed 1/2". Shorten the library's too if the
   device page shows it per block (a library change, so a release).
7. **`Todo.md` is stale:** item 1 (release the library with schema 20) was
   done by 0.1.0a11. Item 2 -- the integration's own fingerprint carrying
   `export_scale` -- is still open.
8. **Local clutter, safe to delete:** `.testdata/fingerprints/*.raw.json`,
   `one-machine*.raw.json` (leaked by the old `_save` tests), and the old
   `.testdata/control-tests/` folder. A snapshot there still restores with
   `--restore <path>`.

## Answered in this session, for reference

- **The forced-charge wait is long enough.** The check reads 20 s before,
  waits 8 s (`SETTLE`), reads 20 s during, undoes, waits 8 s, reads 20 s
  after; verdicts compare medians. Across every recorded run at four houses
  the ten samples inside the "during" window spread by 0 W -- the battery was
  at the commanded power before the first sample -- with one exception, a
  pack that accepted less (1098.5 W of 1250, spread 157 W).
- **What the survey's private file held** beyond the public one: the serial
  (as a field and as raw words 4990-4999, and a wallbox's) and the full IP
  address. The time to the second, port and unit are in the public document.
