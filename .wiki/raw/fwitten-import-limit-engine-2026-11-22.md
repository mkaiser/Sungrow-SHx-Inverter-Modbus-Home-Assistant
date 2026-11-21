# fwitten's cluster master: the capability test's import limit check, 2026-11-21/22

The capability test's engine (`sungrow_capability_test.py --import-limit --allow-dark
--no-restart --yes`, this checkout at commit `aeecd62`, library from `src/`) on fwitten's
master SH10RT-V112 (`anon-86493117545`, SAPPHIRE-H_B001.V000.P023, SBR096), over its own LAN
port, unit 1, the master of a master/slave cluster whose slave (`anon-33442450531`) has no
battery. Run from 23:53 to 00:00:49 CET, after dark. The house's Home Assistant kept polling.
The owner's standing leave covers writes; the maintainer gave the go for this run.

Reached through the maintainer's host's WireGuard tunnel. Identity checked before any write:
the serial stand-ins at all four of the house's endpoints matched the ones on record.

## Before the run

Read raw at 23:50: 13000 = 0x0040 (Running), SoC 15.5 %, PV 0 W (5017-5018 = 0). A dry run
first (exit 0, nothing written); it dropped the connection once.

## The run

Conditions: PV 0 W, SoC 15.2 %, direct connection, battery ceiling 4860 W. One connection drop,
re-opened. Exit 3 (checks skipped or inconclusive); none of the skips is the import limit check.

The import limit check, as the report gives it:

| Check | Observable | Commanded | Before | During | After | Drift | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| site import limit | grid import power | 1090 W | 1724 W ±6 | 1718 W ±7 | 1710 W ±4 | 14 W | nothing measurable happened -- nothing moved by more than the house moves on its own |

- Sizing: under the engine's forced charge of 1250 W the house imported 1715 W (median of one
  window), so the load past the charge was about 470 W. The cap was set halfway down: 1090 W,
  word 109. Obeyed, import would have fallen to about 1090 W with the charge cut to about 620 W.
- During the cap, import stayed at 1718 W: the cap was not met, by about 630 W.
- The same run's forced charge check had shown the charge commanded through 13050/13051/13052
  doing as it was told: battery charge power 1250 W ±0 during, from -492.5 W before.
- The words probed afterwards, with the charge stopped:
  - 0: refused, `ServerDeviceFailureError`, exception 0x04 for function code 0x06;
  - 5001: refused, the same;
  - 5000: taken.
- The report does not say whether the word 109 read back during the cap; the write raised no
  error, and the restore found 32998 "already holding its original value".

The other rows of the same run:

- Readback: nine controls matched at the specification's word. 13074 was written at the factor
  the export-scale probe found, ×10 (the held 24990 written back refused with 0x04 three times),
  as at this house's earlier P023 runs.
- Forced discharge at 1250 W: could not tell (the house was 487 W different afterwards).
- Export limit at 1250 W, export made by discharging 3190 W (the pack accepted 3190 of 3195 W):
  nothing measurable happened, export 2572 → 2567 → 2574 W; feed-in ratio 100 % → 5 %.
- Backup mode (13075 took 170), load control (13011 took 85, 13002 took 3), EMS mode options
  (2, 3, 4 taken; 0 held): did as told.
- Upper bounds: battery_max_soc 101 % refused with 0x04; the max charge, max discharge and forced
  powers took and stored 4960 W above the 4860 W maximum, and both start powers took 1010 W
  above 1000 W -- not enforced.
- Not run: charge ceiling (battery too low), PV cut, charging and discharging thresholds,
  discharge window and charge window 2 (no leave), battery_min_soc upper bound, restart.

Restore: "Every setting this run touched was put back and read back at its original value."
Read raw afterwards, at 00:02:

| Register | Master | Slave (unit 2) |
| --- | --- | --- |
| 32998 | 2000 | 2000 |
| 13050 | 0 | 0 |
| 13051 | 0xCC | 0xCC |
| 13052 | 0 | 0 |
| 13000 | 0x0040 | 0x0008 |
| 13023 | 143 (14.3 %) | 65535 |

The report file is `device-diagnosis/20261121-225348-capability_test.json` (gitignored).
