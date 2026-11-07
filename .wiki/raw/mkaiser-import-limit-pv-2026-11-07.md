# The maintainer's SH10RT: the site import limit with PV, 2026-11-07

A one-off script (not the control test's engine, which has no import limit check) on the
maintainer's SH10RT (`anon-37323352958`, SAPPHIRE-H_B001.V000.P020, third-party battery), over
its own LAN port, unit 1, at 09:29-09:37 local time with ~1.1 kW of PV. In self-consumption,
before the writes, PV covered the house's ~610 W and charged the battery at ~375 W, with the
meter at ~0 W. The house's Home Assistant kept polling. The owner gave leave for the run.

Procedure, with the control test's rules kept:

- the stand-in was read and matched before anything was written;
- the raw words of 13051, 13050, 13052 and 32998 were snapshotted and flushed to a file
  before the first write;
- the restore ran in `finally`, in the control test's order (13051, 13050, then the rest),
  with no deadline, writing each snapshot word and reading it back raw until it matched.

Snapshot: 13051 = 0xCC (204), 13050 = 0, 13052 = 0, 32998 = 2000.

The writes, in order:

1. 13052 = 4500, 13050 = 2, 13051 = 0xAA (a forced charge at 4500 W);
2. after 60 s, 32998 = 200;
3. after 90 s, 32998 = 1;
4. after 90 s, 32998 = 2000;
5. after 30 s, 13051, 13050 and 13052 back to the snapshot (self-consumption);
6. after 30 s, 32998 = 200; after 45 s, 32998 = 2000;
7. then the bounds: 0, 5001 and 5000, each followed by 2000.

The script sampled every ~2 s: PV (total DC power, 5017), meter active power (5601, positive is
import), load power (13008), battery power (5214, negative is charging), SoC (13023) and 32998
itself.

| Phase | Samples | PV | Meter, median (min-max) | Battery, median | Load, median |
| --- | --- | --- | --- | --- | --- |
| self-consumption, before writes | 30 | 1100 W | -6 W (-21 to 14) | 375 W charging | 614 W |
| forced charge 4500 W, 32998 = 2000 | 28 | 1158 W | 5360 W | -4501 W | 1796 W |
| forced charge 4500 W, 32998 = 200, load ~1810 W | 26 | 1110 W | 2010 W (1975-2025) | -1205 W | 1810 W |
| forced charge 4500 W, 32998 = 200, load ~615 W | 14 | 1103 W | 2047 W (2017-2060) | -2396 W | 615 W |
| forced charge 4500 W, 32998 = 1 | 43 | 1067 W | 20 W (0-31, settled) | -375 W | 593 W |
| forced charge 4500 W, 32998 = 2000 again | 15 | 1048 W | 4269 W | -4501 W | 597 W |
| self-consumption, 32998 = 2000 | 13 | 1033 W | 15 W | -353 W | 587 W |
| self-consumption, 32998 = 200 | 22 | 1022 W | -4 W (-20 to 18) | -347 W | 558 W |
| after the restore | 21 | 915 W | 0 W (-31 to 24) | -267 W | 547 W |

The settled ranges leave out the samples taken during each transition.

- **At 200 the cap is on grid import alone.** The battery took PV + 2.00 kW - load, less
  ~100 W of losses: ~1205 W with a house load of ~1810 W, and ~2396 W after the load fell to
  ~615 W. The load fell on its own, not by any write. The inverter followed the load step
  within ~4 s and kept import at the cap. The settled import ran 0-3 % above 2000 W
  (median 2010 W, then 2047 W).
- **At 1 (0.01 kW) the forced charge drew only on PV.** Import settled at ~15 W (0-31 W), and
  the battery charged at PV minus load (~375 W), the same as in self-consumption.
- **Settle time, with ~2 s samples:** cap 2000 to 200, ~4-6 s (one sample in between);
  200 to 1, ≤4 s; 1 to 2000, ~4-6 s.
- **In self-consumption, 200 changed nothing.** There was no import to cap. With 1 kW of PV
  and the battery at 19 % there was no export either, so the run says nothing about export.
- **The bounds:** 0 and 5001 were both refused with an exception response 0x04 (server device
  failure, `ServerDeviceFailureError`); 5000 was accepted and read back 5000. The device
  answered each refusal; neither lost the link.
- The cable read back every word written (200, 1, 2000, 5000).
- Four reads lost the connection (`ModbusConnectionError`), and each answered on the retry.
  Two of them hit the restore of 32998, which wrote 2000 and read back 2000 on the third
  attempt.

Restore: 13051 reads 204, 13050 reads 0, 13052 reads 0, 32998 reads 2000. Nothing was left
changed.
