# Fingerprints and control tests on 0.1.0a12: what is left

Every site was re-read on the published survey (PyPI 0.1.0a12) on
2026-10-13 and published: gerd (both paths, wallbox at unit 3 through the
dongle), mkaiser, bar12 (both paths), and fwitten's master (both paths).
What the wallbox reading settled is in `doc/wallbox_registers.md`. This file
holds only what is still open.

**Status: 2026-10-14, 19:25. fwitten done for tonight: both slave
documents published (nothing lost), the master's control test merged (9 of
9 matched, restart included). `make check` green. Open at fwitten: the
slave's control test, which needs daylight. Then gerd (19:25 on): integration test
passed, control test running. Nothing committed yet.** Updated as runs finish, so a
later session can pick it up from here.

Consent: the maintainer has it from gerd, fwitten and bar12 for every test,
writes included, and all three allowed `ip_address_last_two_octets`.
Addresses are in memory (*Sungrow inverter dev connection*), never here.

## fwitten's slave: the two surveys

| Endpoint | Run | Published |
| --- | --- | --- |
| slave, LAN port (unit 2) | 17:58-18:50, exit 0; all 661 answered dump addresses and every field path kept; 23 blocks answered | **yes**, `control_test` (2026-09-25) and `export_scale` carried |
| slave, WiNet-S | 18:52-19:05, exit 0; all 1010 kept; 25 blocks answered | **yes**, `export_scale` carried |

Both run from a copy of `scripts/sungrow_read_only_survey/` **outside the
checkout**, answering: not polled, unit default (2 on the LAN port, which
answers 2 and times out on 1), transport `direct_lan` / `winet`, proxy
`no`, other inverter `no`, address `two_octets`, reporter `fwitten`, and the
2026-09-25 comment with the date changed.

Then:

1. Publish each over its committed namesake, carrying `export_scale`
   forward, and the new `control_test` (below) in place of the old. Check
   nothing the old document had is missing: every field path and every
   answered dump address.
2. `make gen` (compatibility table), then `make check`.
3. Commit. **Not pushed** until the maintainer has decided about the
   serial in the history (`plans/force-serial-number-push.md`, which wants
   the tree fix committed before any rewrite).

## fwitten: the control tests

Both inverters' own LAN ports, from a copy of `scripts/sungrow_control_test/`
outside the checkout, `--allow-dark --enable-export-limit` (dusk: ~150 W PV).
Not through the dongles: a WiNet-S reads a write back stale, so legs A and B
there are not evidence.

| Inverter | Run | Merged |
| --- | --- | --- |
| master (anon-86493117545), dry run | exit 0, identity checked by stand-in | -- |
| master, full run without restart, 18:05 | exit 3, 9 of 9 matched, all restored | superseded by the next |
| master, full run **with** restart, 19:08 | exit 3, 9 of 9 matched, all restored, running again after 381 s | **yes**, LAN document |
| slave (anon-33442450531, unit 2) | dry run at 19:07 refused: the slave is in *Standby* (no PV, no battery). **To do in daylight** | not yet; the carried 2026-09-25 block (exit 5, 13074 at x10) stays until then |

Why again: the carried `control_test` blocks predate the per-device write
scale of 13074. The master's showed 13074 written divided by ten and refused
with 0x04, and the slave's (2026-09-25, exit 5) 60 for 600, while both
sides' `export_scale` says "stores a written word as handed".

**Master, 18:05-18:20:** the scale probe answered 1:1 again, and 13074 was
written at that factor: 24900 W wrote raw 24900 and read back 24900, matched
(one point only: its 24990 W maximum leaves no second value a decade away).
Every other control matched on both points where it has two. Forced
discharge did as told (1197.5 of 1250 W). The export-limit check commanded
11880 W against a 2780 W export made by discharging, so nothing could move:
it can only catch a cap a decade too small. Exit 3 is for what dusk and a
full pack skip (forced charge, charge ceiling), not for a mismatch. Result
file in the scratchpad, `20261014-160028-control_test.json`.

**Master, with restart, 19:08-19:25** (merged; replaces the block from
the earlier run, which had its own restart): the same 9 matches, at PV 0 and
86 % SoC. Forced charge and forced discharge both did as told (1249 and
1251 W of 1250). Stopped after 2 s and **running again after 381 s**, where
the daylight run took 197 s: four start commands, 60 s apart, before the
state moved. Within the seven-minute deadline by 40 s -- see `Todo.md`.
Not generating afterwards, as expected with no PV. Settings survived.

**Slave, to do:** in daylight, `control_test.sh <slave> --unit 2
--allow-dark --enable-export-limit --restart --merge-into <its LAN
document>`. Its 2026-09-25 run ended exit 5 with `settings_survived: false`
after the restart, which is worth seeing again.

## Integration on gerd's hardware: passed, 2026-10-14

The dev instance, nothing else polling, identity checked by stand-in
(anon-00267885816 at both addresses). `DEVICES_MODE_OFFERED` set to True in
the working tree for the test and reverted afterwards.

1. **Dongle entry: passed.** SH8.0RT-V112 (130 entities), AC22E-01 hung off
   it by `via_device` with **21** entities, sensor and binary_sensor only,
   all with values that agree with the 2026-10-13 survey; SBR096 (7).
2. **`run_survey`, dump off: passed.** `wallbox` is `unit` 3 and
   `readings`, no `register_dump`; the same 32 keys, per-field keys,
   `register` and `held` as the survey's. Plus `serial_anonymized_hashed`
   (schema 21, unreleased).
3. **Dump on: passed.** 200 answered addresses, the survey's own set;
   input 21200-21205 masked the same way.
4. **Cable entry: passed**, no wallbox device; SH8.0RT-V112 (138) and
   SBR096 (17) -- a cable forwards more than the dongle. Not as the plan
   said, though: with the dongle entry *disabled*, adding the cable aborts
   `already_configured` (entries are keyed by the inverter's serial), so the
   dongle entry had to be deleted. See `Todo.md`.

Findings, all in `Todo.md`: the wallbox's firmware string reads whole by
itself (`LE-01.1E1.001.901.25`) and cut (`LE-01.1E1.001.`) from a dump, whose
block boundary splits it -- the wallbox answers the tail words as 0 to a read
that starts mid-string; the survey-dump option shows ticked in the form while
an entry never saved runs without it; HA warns that `via_device` is
deprecated (stops working in 2027.8).

## gerd: control test, then the survey again on the next release

| Step | State |
| --- | --- |
| control test, cable, `--allow-dark --enable-export-limit --restart`, 19:43 | exit 3: **9 of 9 matched**, all restored and read back; merged into the cable document |
| `--export-scale`, cable and dongle | both **x10** (0x04 refusal), limitation lifted for the write and put back; merged into both |
| after 0.1.0a13 is on PyPI: dongle survey again, so the wallbox gains `serial_anonymized_hashed` | not yet; needs gerd's VPN still up |

**The control test at gerd's.** The scale probe answered x10, and 13074
was written at it: 600 W went in as raw 600 and read back 600, slope 1 --
the per-device scale doing on gerd's firmware what it does 1:1 on fwitten's.
Every other control matched. Restart: stopped after 2 s, running again after
**369 s** (180 s in the 2026-09 daylight run). Forced discharge "could not
tell" (house load ±293 W); no export-limit check (discharging 2940 W made
only 1662 W of export, under the 1812 W a cap needs to bind against).

## Only a charging car can answer

21313 against 21308 over a session, and whether it goes to 0 when charging
stops; the signedness of 21308/21310 (expect nothing). Agree a time with
gerd when the car is plugged in and charging, and take two dongle runs about
five minutes apart with 90 s of quiet before each.

## Survey bugs found on 2026-10-13 (not fixed)

All three surfaced together when fwitten's VPN dropped mid-run on
2026-10-13 -- a clean real-world case, because the cause is known.

- **Timeouts are labelled "refused with an exception".**
  `scripts/sungrow_read_only_survey/blocks.py` catches every `ModbusError`,
  `ModbusTimeoutError` included, as `REFUSED`. The summary then prints
  *"refused with an exception (... Response timeout after 10.0 seconds ...).
  This failed by timing out rather than by refusing."* The second sentence is
  right and the first is not, and the `block_read_test` of a published
  document carries the first. CLAUDE.md: a failed read is not a refusal.
  `block_test.REFUSED` in the library has the same word list.
- **A run that read nothing exits 3, not 1.** Identification failed on every
  unit with `ModbusConnectionError`, the dump read 0 of 1510, every probe
  failed on the link, and the exit code said "the filename under-claims"
  rather than "nothing collected" (1/2). A document of nothing was written
  beside the launcher as if it were one to send.
- **Capability probes do the same, and it decides the transport.**
  `ModbusConnectionError` printed as "refused", and a 6100 that could not be
  read counted as a dongle in the path: the survey warned "you reported
  'direct_lan', but the registers say 'module'" on a path where 6100 had
  answered half an hour earlier. Probes are three-valued and `None` must
  never read as `False`.

## Done when

- [x] fwitten's slave, both paths, published
- [x] fwitten's master control test merged (with restart)
- [ ] fwitten's slave control test, in daylight
- [ ] `make gen` and `make check` green, committed
- [x] the integration passes on gerd's dongle, dump option off and on
- [ ] gerd's control test merged; gerd's dongle re-surveyed on 0.1.0a13
- [ ] the maintainer has decided about the serial in the history
