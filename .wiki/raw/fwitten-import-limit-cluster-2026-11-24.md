# fwitten's cluster: the site import limit (32998) by master, slave and both, 2026-11-24

A script over both inverters' own cable ports at fwitten's cluster: master SH10RT-V112
(`anon-86493117545`, unit 1, SBR096, the meter) and slave SH10RT-V112 (`anon-33442450531`,
unit 2, no battery), both on SAPPHIRE-H_B001.V000.P023 (read on both after the run). The maintainer gave the go for the writes; the owner's standing leave covers them.
Both stand-ins were proved before the first write. After dark, PV 0 W on both.

Each cap was held about 90 s and then lifted to 2000 (20.00 kW) for about 60 s; each number is the
median import of the samples past the first 25 s (60 s for the charge baselines). Times are CET.
A negative battery power is charging. Before the run: 13050 = 0, 13051 = 0xCC, 13052 = 0,
32998 = 2000 on master and slave; battery 79.1 %.

## Results, as found

| Time | Step | Import, W | Samples | Battery, W | Slave AC, W | 32998 master / slave | SoC, % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 18:13:42 | idle | 11 | 12, -11..27 | 516 | 0 | 2000 / 2000 | 79.0 |
| 18:15:24 | charge 1250 W | 1776 | 12, 1771..1800 | -1249 | 0 | 2000 / 2000 | 79.5 |
| 18:16:56 | A: cap 1150 W on the master | 1783 | 19, 1775..1812 | -1249 | 0 | 115 / 2000 | 80.0 |
| 18:17:59 | A: lifted | 1776 | 11, 1772..1795 | -1249 | 0 | 2000 / 2000 | 80.3 |

Phase A: did not hold (1776 -> 1783 -> 1776 W against 1150 W), the word read back as written.

| Time | Step | Import, W | Samples | Battery, W | Slave AC, W | 32998 master / slave | SoC, % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 18:19:41 | charge 4000 W commanded, 3601 W reached | 4190 | 12, 4178..4198 | -3601 | 0 | 2000 / 2000 | 81.7 |
| 18:21:12 | B: cap 2190 W on the master | 4263 | 19, 4177..4318 | -3601 | 0 | 219 / 2000 | 82.9 |
| 18:22:14 | B: lifted | 4276 | 10, 4231..4300 | -3601 | 0 | 2000 / 2000 | 83.8 |

Phase B: did not hold (4190 -> 4263 -> 4276 W against 2190 W), the word read back as written.

| Time | Step | Import, W | Samples | Battery, W | Slave AC, W | 32998 master / slave | SoC, % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 18:23:45 | C: cap 2190 W on the slave alone | 4236 | 19, 4229..4258 | -3601 | 0 | 2000 / 219 | 85.1 |
| 18:24:49 | C: lifted | 4192 | 11, 4178..4202 | -3601 | 0 | 2000 / 2000 | 86.0 |

Phase C: did not hold (4276 -> 4236 -> 4192 W against 2190 W), the word read back as written.

| Time | Step | Import, W | Samples | Battery, W | Slave AC, W | 32998 master / slave | SoC, % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 18:26:20 | D: cap 2190 W on both | 4185 | 19, 4174..4209 | -3601 | 0 | 219 / 219 | 87.3 |
| 18:27:23 | D: lifted | 4184 | 11, 4179..4214 | -3601 | 0 | 2000 / 2000 | 88.1 |

Phase D: did not hold (4192 -> 4185 -> 4184 W against 2190 W), both words read back as written.

Exit 0, nothing ended early. In every sample of every phase: the battery charged at 1249-1250 W (A)
or 3600-3602 W (B, C, D), capped or not; the master was in forced mode (13000 = 0x0800), the slave in
Standby (0x0008) at 0 W AC; PV was 0 W on both; the master's load reading was 424-549 W. In phases B, C
and D it reached 3601 W of the 4000 W commanded, steadily; why is not known.

Not read: the slave's 13050 while the master was in forced mode.

## Restored

By the script at 18:27:24-25, each word read back. Read again at 18:27:36 by a separate client over
the same two ports: master 13050 = 0, 13051 = 0xCC, 13052 = 0, 32998 = 2000, 13000 = 0x0040,
SoC 88.2 %; slave 32998 = 2000, 13000 = 0x0008. The battery was discharging at 797 W again.
