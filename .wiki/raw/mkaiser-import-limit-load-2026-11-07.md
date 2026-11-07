# The maintainer's SH10RT: the site import limit against house load, 2026-11-07

A one-off script (not the control test's engine) on the maintainer's SH10RT
(`anon-37323352958`, SAPPHIRE-H_B001.V000.P020, read from 13250 after the run, third-party
battery), over its own LAN port, unit 1, at 20:04-20:10 local time, after dark (PV 0 W). In
self-consumption, before the writes, the battery covered the house's ~2250 W at ~2369 W
discharge, with the meter at ~9 W, at 26.6 % state of charge. The house's Home Assistant kept
polling. The owner gave leave for the run.

The question: with the house load above the cap and the battery unable to cover it, does
import exceed the cap?

Procedure, with the control test's rules kept:

- the stand-in was read and matched before anything was written;
- the raw words of 13051, 13050, 13052 and 32998 were snapshotted and flushed to a file
  before the first write;
- the restore ran in `finally`, in the control test's order (13051, 13050, then the rest),
  with no deadline, writing each snapshot word and reading it back raw until it matched.

Snapshot: 13051 = 0xCC (204), 13050 = 0, 13052 = 0, 32998 = 2000.

The writes, in order:

1. 32998 = 200 (2.00 kW), in self-consumption;
2. after 60 s, 13052 = 0, 13050 = 2, 13051 = 0xCC (forced mode, stop: the battery held idle);
3. after 120 s, 32998 = 2000;
4. after 60 s, the restore.

The script sampled every ~2 s: PV (total DC power, 5017), meter active power (5601, positive is
import), load power (13008), battery power (5214, positive is discharging), SoC (13023) and
32998 itself.

| Phase | Samples | Meter, median (min-max) | Battery, median | Load, median |
| --- | --- | --- | --- | --- |
| self-consumption, 32998 = 2000 | 33 | 9 W (-11 to 35) | 2368 W discharging | 2249 W |
| self-consumption, 32998 = 200 | 30 | 8 W (-18 to 16) | 2366 W discharging | 2248 W |
| forced stop, 32998 = 200 | 57 | 2197 W (2194-2212, settled) | 0 W | 2177 W |
| forced stop, 32998 = 2000 | 30 | 2196 W (2184-2236) | 0 W | 2178 W |
| after the restore | 22 | -1 W (-207 to 111) | 2294 W discharging | 2180 W |

- **The cap does not hold against house load.** With the battery idle, import ran at
  ~2197 W against a 2.00 kW cap, the whole load, and the same as with the cap at 20.00 kW.
  The inverter did not shed load or discharge the battery to meet it.
- **The forced stop took effect within one sample** (~2 s): the battery went from ~2327 W
  discharging to 0 W, and import from -41 W to 2195 W.
- **In self-consumption at night, 200 changed nothing**: the battery covered the load and
  there was no import to cap.
- After the restore the battery took the load again within one sample.
- Two reads lost the connection (`ModbusConnectionError`), each answered on the retry. The
  restore's write of 32998 lost it once, and wrote 2000 and read back 2000 on the second
  attempt.

Restore: 13051 reads 204, 13050 reads 0, 13052 reads 0, 32998 reads 2000. Nothing was left
changed.
