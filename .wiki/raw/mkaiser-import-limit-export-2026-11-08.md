# The maintainer's SH10RT: the site import limit with PV surplus and export, 2026-11-08

One-off scripts (not the capability test's engine) on the maintainer's SH10RT
(`anon-37323352958`, SAPPHIRE-H_B001.V000.P020, read from 13250 before the runs, third-party
battery), over its own LAN port, unit 1, at 10:38-10:47 local time, with ~900-1240 W of PV. The
house's Home Assistant kept polling; seven reads in each run lost the connection and were
retried. The owner gave leave for the runs.

Before the runs: the inverter Running (13000 = 0x0040), the battery at 0.0 % against a minimum
of 10 % (13059 = 100) and at 0 W, PV 906 W, load 585 W, the meter at -84 W (exporting); 32998 =
2000, battery max charge power 33047 = 450 (4500 W), EMS mode 0 (self-consumption).

Each run kept the capability test's rules: the stand-in was read and matched before anything
was written; the raw words of every register it wrote were snapshotted and flushed to a file
before the first write; the restore ran in `finally`, writing each snapshot word and reading it
back raw until it matched.

Samples every ~3-8 s: meter (5601, positive is import), load (13008), battery (5214, negative is
charging), PV (5017), SoC (13023), 13000 and every written register.

## Run c, 10:38: PV above the load, the battery charging from it

32998 = 1 (0.01 kW) for 90 s after 40 s at 2000; then 2000 for 40 s; then the restore.

The battery began charging from the surplus during the baseline (0 → -183 → -300 W), so there
was no export.

| Phase | Meter, median (min-max) | Battery, median | PV | Load |
| --- | --- | --- | --- | --- |
| 32998 = 2000 | 16 W (-31 to 20) | -288 W | ~905 W | ~410 W |
| 32998 = 1 | 41 W (-293 to 1228) | -292 W | ~915 W | ~420 W |
| 32998 = 2000 again | 20 W (0 to 58) | -300 W | ~935 W | ~415 W |

The charge from PV went on at ~-300 W under the cap. Import stayed at 20-60 W against a 10 W
cap. One sample, at 10:40:39, read 1228 W of import with the load at 417 W and the battery at
-185 W; the next read 176 W, then 109 W. Restore: 32998 reads 2000.

## Run d, 10:42: export, the charge limited to 100 W

33047 = 10 (100 W); after 60 s 32998 = 1 for 90 s; then 2000 for 40 s; then the restore,
32998 first.

| Phase | Meter, median (min-max) | Battery, median | PV | Load |
| --- | --- | --- | --- | --- |
| before, 33047 = 450 | 14 W (5 to 21) | -377 W | ~1000 W | ~400 W |
| 33047 = 10, 32998 = 2000 | -307 W (-328 to -285) | 0 W | 1021-1069 W | ~410 W |
| 33047 = 10, 32998 = 1 | -296 W (-331 to -268) | 0 W | 1069-1147 W | ~450-490 W |
| 33047 = 10, 32998 = 2000 again | -367 W (-379 to -342) | 0 W | 1159-1198 W | ~485 W |
| after the restore | 18 W (8 to 74) | -536 W | ~1230 W | ~480 W |

- With the charge limit at 100 W the battery took nothing (0 W), and the surplus went to the grid.
- **Under the 0.01 kW cap export went on**, following PV and the load, and PV rose with the sun.
  The cap did not curtail PV.
- Restore: 32998 reads 2000, 33047 reads 450; the battery charged from the surplus again within
  one sample.
