# The maintainer's SH10RT: the site import limit under a forced charge, 2026-11-07

A one-off script (not the control test's engine, which has no import limit check) on the
maintainer's SH10RT (`anon-37323352958`, SAPPHIRE-H_B001.V000.P020, third-party battery), over
its own LAN port, unit 1, shortly after midnight with no PV: in self-consumption the battery
covered the house's ~410 W with the meter at ~0 W. The house's Home Assistant kept polling.
The run was given leave by the owner.

Procedure, the control test's rules kept:

- the stand-in was read and matched before anything was written;
- the raw words of 13051, 13050, 13052 and 32998 were snapshotted and flushed to a file
  before the first write;
- the restore ran in `finally`, in the control test's order (13051, 13050, then the rest),
  with no deadline, writing each snapshot word and reading it back raw until it matched.

Snapshot: 13051 = 0xCC (204), 13050 = 0, 13052 = 0, 32998 = 2000.

Writes: 13052 = 4500, 13050 = 2, 13051 = 0xAA (forced charge 4500 W); after 120 s,
32998 = 200; after 180 s, 32998 = 2000; after 60 s, the restore.

Sampled every ~5 s: meter active power (5601, positive is import), load power (13008),
battery power (5214, negative is charging), SoC (13023) and 32998 itself.

| Phase | Samples | Meter, median (min-max) | Battery, median | Load, median |
| --- | --- | --- | --- | --- |
| self-consumption, before writes | 15 | 7 W (-13 to 30) | 460 W | 405 W |
| forced charge 4500 W, 32998 = 2000 | 24 | 5088 W (5077-5113) | -4501 W | 408 W |
| forced charge 4500 W, 32998 = 200 | 32 | 1978 W (1957-1999) | -1495 W | 404 W |
| forced charge 4500 W, 32998 = 2000 again | 12 | 5084 W (5077-5112) | -4501 W | 406 W |
| after the restore | 9 | 10 W (-5 to 35) | 461 W | 404 W |

- Import fell from 5088 W to 1975 W in the first sample after the write (within ~5 s), and
  rose back to 5084 W in the first sample after the second write. No sample during the cap
  exceeded 2000 W.
- The inverter met the cap by cutting the battery's charge, from 4500 W to ~1500 W
  (cap minus house load minus ~80 W of losses); the house load was untouched.
- 32998 read back 200 and then 2000 on the cable.
- Seven reads lost the connection (`ModbusConnectionError`), each answered on the next try;
  one was the restore's readback of 32998, which read 2000 on the retry.

Restore: 13051 reads 204, 13050 reads 0, 13052 reads 0, 32998 reads 2000. Nothing was left
changed.
