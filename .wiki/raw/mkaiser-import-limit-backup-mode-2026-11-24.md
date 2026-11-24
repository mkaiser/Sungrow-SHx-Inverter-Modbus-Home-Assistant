# The import limit with backup mode on, at the maintainer's lone SH10RT, 2026-11-24

A script over the cable at the maintainer's SH10RT (`anon-37323352958`), stand-in proved first; firmware on
record SAPPHIRE-H_B001.V000.P020, not read in this run. Lone inverter (33500 = 0x55), third-party pack, after
dark, PV 0 W, production Home Assistant polling. The maintainer gave the go. Times CET. A 2500 W charge
commanded through 13050, 13051 and 13052 throughout; house load about 2.04-2.11 kW. Each cap held 90 s, lifted
60 s; median import past the first 25 s (baselines 25-50 s). Every sample read 33000 as equal to 13075.

| Time | Step | 13075 | Cap, W (32998) | Import, W (before / during / after) | Battery during, W |
| --- | --- | --- | --- | --- | --- |
| 20:51-20:53 | 1 | 0x55, off | 3450 (345) | 4648 / 3478 / 4655 | -1353 |
| 20:54-20:57 | 2 | **0xAA, on** | 3460 (346) | 4656 / 3437 / 4698 | -1262 |
| 20:58-21:00 | 3 | 0x55, off | 3500 (350) | 4699 / 3477 / 4698 | not printed |

All three held. Without the cap the charge was 2500-2502 W. 13075 took both words and read back.

Restored by the script at 21:00:53 and read back; read again by a separate client: 13050 = 0, 13051 = 0xCC,
13052 = 0, 32998 = 2000, 13075 = 0x55. Right after, 13000 still read 0x0800 with the battery at 0 W. A few
minutes later it read 0x0040 and the battery was discharging 2101 W.
