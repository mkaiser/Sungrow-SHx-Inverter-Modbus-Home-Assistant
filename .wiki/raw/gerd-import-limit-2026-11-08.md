# gerd's SH8.0RT-V112: the site import limit on P022, 2026-11-08

One-off scripts (not the capability test's engine) on gerd's SH8.0RT-V112 (`anon-00267885816`,
SAPPHIRE-H_B001.V000.P022, read from 13250 before the runs, SBR096), at 00:26-00:46 local time,
after dark (PV 0 W). The first run over the inverter's own LAN port, the second written through
the WiNet-S (WiFi, unit 1). The owner allows any test, writes included. The house's own Home
Assistant was polling: about a third of the reads lost the connection and were retried.

Before the runs: the inverter Running (13000 = 0x0040), SoC 5.2 % against a minimum of 10 %
(13059 = 100), the battery discharging ~500-550 W into a ~390 W load, the meter ~20-70 W;
13050 = 0, 13051 = 0xCC, 13052 = 0, 32998 = 2000, 13017 = 0, the forced-charging schedule off
(33208 = 0x55); battery max charge power 33047 = 440 (4400 W). The wallbox behind the dongle
(unit 3, AC22E-01) read charging status 1, every phase current 0 A and a control pilot of
11.9 V: no car connected.

Each run kept the capability test's rules: the stand-in was read and matched before anything was
written; the raw words of 13051, 13050, 13052 and 32998 were snapshotted and flushed to a file
before the first write; the restore ran in `finally`, 13051 and 13050 first, writing each
snapshot word and reading it back raw until it matched. Snapshot each time: 13051 = 0xCC,
13050 = 0, 13052 = 0, 32998 = 2000.

Samples every ~2.5 s, when a read answered: meter active power (5601, positive is import), load
(13008), battery power (5214, negative is charging), PV (5017), SoC (13023), 13000 and every
written register.

## G1, 00:27: over the cable

13052 = 1250, 13050 = 2, 13051 = 0xAA; after 150 s 32998 = 100 (1.00 kW) for 90 s; then 32998 =
2000 for 45 s; then the restore.

| Phase | 13000 | Import, median (min-max) | Battery, median |
| --- | --- | --- | --- |
| before the writes | 0x0040 | 22 W | 550 W discharging |
| forced charge, 32998 = 2000 | 0x0800 (from 00:27:47) | 1816 W (1783-1884) | -1248 W |
| forced charge, 32998 = 100 | 0x0800 | 1002 W (980-1015) | -496 W |
| forced charge, 32998 = 2000 again | 0x0800 | ~2 kW | -1247 W |
| after the restore | 0x0040 | 20 W (-38 to 78) | 744 W discharging |

The cap cut the charge from 1248 W to ~496 W and held import at 1002 W against 1.00 kW. 119 reads
lost the connection and were retried. The restore: 13051 read 204 at once; 13050, 13052 and
32998 each lost the connection once, and on the second attempt wrote and read back 0, 0 and 2000.

## G2, 00:35: through the WiNet-S

The same writes, through the dongle, with 120 s at the cap. A once-a-minute read of the cable
lost every attempt from 00:34 to 00:43.

| Phase | Dongle: 13000 | Dongle: import | Dongle: battery |
| --- | --- | --- | --- |
| before the writes | 0x0000 | 12 W | 595 W discharging |
| forced charge, 32998 = 2000 | 0x0800 (from 00:35:04) | 1676-1750 W | -1250 W |
| forced charge, 32998 = 100, 00:38:17-00:38:40 | 0x0800 | 956-1009 W (median 982 W) | -549 to -612 W |

Through the dongle the cap held: import 956-1009 W against 1.00 kW. The first sample after the
cap, at 00:38:10 after three timeouts, still read 1676 W and -1250 W; at 00:38:14 a sample read
0 for every value (meter, load, battery, PV, SoC). At 00:38:44 and 00:38:47 the dongle answered
reads of 13050 and 13051 with exception 0x04.

From 00:39 the dongle stopped answering: reads and writes timed out (`ModbusTimeoutError`). The
write of 32998 = 2000 that lifts the cap timed out five times, and the run went to its restore.
The restore wrote and read back 13051 = 204, 13050 = 0 and 13052 = 0 at 00:42:38, after four
timeouts. Its write of 32998 timed out every 20 s until 00:45:29.

At 00:45:46 a read over the cable answered: 32998 = 2000, so the lift (or a restore attempt) had
landed although no answer came back. The restore loop was then stopped. From 00:46 the cable
closed every Modbus session (TCP 502 accepted, then `ModbusConnectionError`), still at 00:55. At
00:53:15 the dongle read 13050 = 0, 13051 = 0xCC, 13052 = 0, 32998 = 2000, 13000 = 0x0000, battery
322 W discharging, meter 18 W: nothing left changed.
