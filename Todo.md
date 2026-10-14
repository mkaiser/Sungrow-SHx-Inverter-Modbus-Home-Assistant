Todo.md contains only next steps (forward looking).
Anything done should be removed here.

# Summary (2026-10-14)

Library and survey: 0.1.0a12 on PyPI, survey and control test run on it.
Every site was re-fingerprinted on 2026-10-13. Still open:

1. **fwitten** -- re-fingerprinted and the master control-tested on
   2026-10-14, `make check` green, **not committed**. Left: the slave's
   control test, in daylight (it sits in Standby without PV).
   `plans/fingerprint-results.md`.
2. **The leaked wallbox serial in the public history** -- your decision:
   rewrite and force-push, or not. `plans/force-serial-number-push.md`.
   Tell gerd either way. Nothing is pushed until this is decided.
3. **Survey bugs** found on 2026-10-13, none fixed: timeouts labelled
   "refused", a run that read nothing exits 3, a lost link decides the
   transport verdict. Details in `plans/fingerprint-results.md`.
4. **A charging car at gerd's** for 21313 and the signedness of
   21308/21310.
5. Small items below.

# Next steps

## Fingerprinting

- Write the actual used console command (for bypassing the CLI questions
  and answers) to the fingerprint json file. Today `command_line` holds
  the equivalent `probe.py capabilities ... --unit 2 --transport
  direct_lan --proxy no --dump` line; `sungrow_survey.py` itself takes no
  flags for the answers, so there is no command that replays a survey.
- `tests/test_no_real_serials.py`: decode runs of 16-bit integers that
  are printable ASCII pairs to text before matching the serial shape, so a
  serial stored as register words fails the suite (how gerd's leaked).
- `control_test.sh --simulated` exits 4: the simulator stores 13074 as
  handed and the run writes at the default x10 when the scale probe gives
  no answer, so leg B reports a wrong slope. Contradicts "a simulator
  cannot produce a finding".
- A dry run of the control test prints "exit 0: every planned check ran
  and every readback matched" although nothing ran.
- The fwitten master's LAN port takes ~39 min per survey: 13199 and the
  three firmware strings time out (10 s each) instead of refusing, and
  the narrowing retries them register by register.
- The control test's restart deadline (7 min) is tight at night: after a
  Modbus stop with no PV, fwitten's master took 381 s and gerd's 369 s to
  run again, where daylight runs took 197 s and 180 s. Raise it, or say in CLAUDE.md that a
  dark restart is slower.
- Windows: a `ConnectionResetError [WinError 10054]` traceback during
  identification; harmless, but reads as a failure.

## Naming footprint

`...-battery-sbr096-meter.json`: `-meter` does **not** mean direct LAN. It
means the meter's phase registers (input 5741) answered. Direct LAN adds no
transport word at all (`TRANSPORT_WORDS["direct_lan"] == ""`); a dongle adds
`-winet`, `-winet-lan` or `-winet-wlan`. The two coincide because a WiNet-S
does not forward 5741, so a dongle document never says `-meter`.
Decide whether direct LAN should get its own word (e.g. `-lan`) -- that
renames every cable document.

## Integration

- The wallbox's firmware string (input 21226, 10 words) is cut to
  `LE-01.1E1.001.` when decoded from a dump: the dump's block boundary
  splits it, and the wallbox answers the tail as 0 to a read that starts
  mid-string. Read whole it is `LE-01.1E1.001.901.25`. Align the wallbox
  bands to field boundaries, or decode strings from their own read.
- The options form shows *survey register dump* ticked (`default=True`),
  while `survey.py` and `fingerprint.py` read
  `options.get(CONF_SURVEY_DUMP, False)`: an entry whose options were
  never saved runs without the dump. Make the two defaults one.
- A second entry for the same inverter on another endpoint aborts
  `already_configured`, even with the first disabled (the unique id is the
  serial). Decide whether one inverter may have a cable and a dongle entry
  -- CLAUDE.md says one entry is one endpoint.
- `device_registry.async_get_or_create(via_device=...)` is deprecated;
  use `via_device_id` (binary_sensor.py:47, sensor.py:87/98). Stops
  working in Home Assistant 2027.8.

- Optional: have the integration's own fingerprint carry `export_scale`
  once its entity has probed. It stores only the factor in entry data, not
  the write behind it.

## Maintainer, on your machines

- `control_test.cmd <host> --dry-run` on Windows from a pull: the
  permission question, "Press Enter", Ctrl+C at that pause (expect exit 1,
  nothing written), results beside the `.cmd`.
- Clean-machine test of the launchers (Docker or Windows Sandbox), answering
  N then y:

      docker run --rm -it -v "${PWD}/scripts/sungrow_read_only_survey:/s" -w /s python:3.13-slim sh ./read_only_survey.sh <inverter-ip>
      docker run --rm -it -v "${PWD}/scripts/sungrow_control_test:/c" -w /c python:3.13-slim sh ./control_test.sh <inverter-ip> --dry-run

- Delete `/home/vscode/testdata-archive-20261013/` (old `.testdata/`
  output, moved rather than deleted) once checked.

## Running the scripts from Windows

Each folder has a launcher that fetches uv and the pinned library, and writes
its results beside itself:

    cd <repo>\scripts\sungrow_read_only_survey
    read_only_survey.cmd                         # asks which network to sweep
    read_only_survey.cmd <ip1> <ip2>             # skip the sweep once the hosts are known

    cd <repo>\scripts\sungrow_control_test
    control_test.cmd <ip> --dry-run              # writes nothing
    control_test.cmd <ip> --unit 2 --export-scale
