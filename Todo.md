Todo.md contains only next steps (forward looking).
Anything done should be removed here.

# Summary (2026-10-14, night)

0.1.0a13 on PyPI. Every site re-fingerprinted; control tests merged at
fwitten's master and gerd; the integration passed on gerd's hardware.
**In progress: `plans/wallbox-lan-sweep-and-fixes.md`** -- gerd's wallbox
answers Modbus over TLS on its own LAN address, and the issues below are
being fixed there. Still open besides:

1. **Finish the history rewrite** (force-pushed 2026-10-14): GitHub Support
   to purge the old SHAs (still served), the fork `BuggiTheBeat/...`, resume
   the preview mirror, re-clone the Windows checkout, then delete the backup
   in `/home/vscode/sungrow-rewrite/` (it holds the serial).
   `plans/force-serial-number-push.md`, steps 6-7.
2. **fwitten's slave control test, in daylight.** It sits in Standby without
   PV (no battery), and the test refuses a stopped inverter. From a copy of
   `scripts/sungrow_control_test/` outside the checkout: `control_test.sh
   <slave> --unit 2 --allow-dark --enable-export-limit --restart
   --merge-into <its LAN document>`. Its carried 2026-09-25 block (exit 5,
   13074 written at x10, settings lost after the restart) is replaced by it.
3. **A charging car at gerd's** for 21313 against 21308 over a session (does
   it go to 0 when charging stops?) and the signedness of 21308/21310. Two
   dongle runs about five minutes apart, 90 s of quiet before each, while the
   car charges.
4. Small items below.

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

- A second entry for the same inverter on another endpoint aborts
  `already_configured`, even with the first disabled (the unique id is the
  serial). Decide whether one inverter may have a cable and a dongle entry
  -- CLAUDE.md says one entry is one endpoint.
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
