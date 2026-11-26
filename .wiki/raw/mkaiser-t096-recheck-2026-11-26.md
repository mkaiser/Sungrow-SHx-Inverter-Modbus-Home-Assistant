# The forced discharge and the charge ceiling again, at the maintainer's SH10RT, 2026-11-26

Production Home Assistant at the maintainer's SH10RT (`anon-37323352958`), SAPPHIRE-H_B001.V000.P020, cable
through the modbus-proxy add-on, integration 0.1.0a57, Pylontech Force H1. Read over the websocket; the
maintainer gave the go for the test run. Times CET.

## What the recorder holds from 2026-11-25 (read 2026-11-26, before any write)

Throughout: `battery_min_soc` 0 %, `battery_reserved_soc_for_backup` 0 %, `battery_max_soc` 90 %, EMS mode
self-consumption, running state Running.

**Forced discharge, run 1.** 08:00:00 the battery read 8.8 % and 0 W while the house drew about 2 kW, before the
diagnosis started (08:07). The check commanded 1250 W and saw 0 / 0 / 0 W. The run's conditions: SoC 8.8 %,
PV 222 W. The check's own guard is `battery_min_soc` + 5 %, so 0 % + 5 % let it run; the ledger waits for
30 % before starting a run for it. On 2026-11-26 at 08:55 the battery read 8.0 % and 0 W with 1993 W of load:
this pack does not discharge at these levels, whatever 13058 says.

**Charge ceiling, run 5.** From 10:55 to 11:10 the battery charged at 4498-4500 W from PV (7268 W) while
exporting 0-450 W; SoC 47.7 % rising 1.1 % every two minutes. 11:09:11 "charge ceiling at 53.5 %" with SoC
55.5 %; the charge stayed at 4499 W (before, during, after; MAD 0), samples 11:11:05 to 11:12:15 at
4498-4499 W, SoC 56.6 % at 11:11:24. On 2026-11-23 the same check at 53 % stopped the same 4499 W
charge (4499 / 0 / 4499 W).

## Run 14, 2026-11-26 12:16-12:26, skip established off, restart off

Auto repeat stopped first (the skip switch refuses off while it runs), started again after. Battery 59 %,
charging 2.4-4.5 kW from PV under passing cloud. Samples every ~10 s from Home Assistant (battery power,
positive = discharge):

| Time | Step | Battery, W |
| --- | --- | --- |
| 12:17:13-12:18:16 | forced charge at 1250 W | 356, -521, -670, **-1250, -1250**, 292, 448 |
| 12:18:27-12:19:31 | forced discharge at 1250 W | 508, 546, 626, **1250, 1251, 1251**, -2587 |
| 12:19:39-12:19:52 | charge ceiling at 57 % | -2619, -2364 (nothing written) |
| 12:20:07-12:21:12 | export limit at 1250 W | export 3644, 3712, **1250, 1260, 1250**, 6883 |

The judge's verdicts: forced charge, forced discharge, export limit, discharging start threshold and site
import limit "could not tell" (the house 245-3138 W different afterwards); the charge ceiling "not measured --
the house moved by 1004 W on its own before anything was written". Readbacks all matched; the five upper bounds
again took 5100 W over 5000 W and 1010 W over 1000 W; 13058 refused 51 %. Restored 45 of 45. The ledger keeps
run 1's forced discharge and run 5's charge ceiling, since an inconclusive run does not replace them.

**The forced discharge acts at 59 %**: 1250-1251 W for a 1250 W command over three samples, from about 600 W
before it. With run 1's 0 W at 8.8 % (the pack idle under load before any write), run 1 measured the pack's own
floor, not the command.

## Run 16, 2026-11-26 13:04-13:09, skip established off, every optional check and the restart off

Started by a watcher once the battery (70 %) charged at 4498 W with battery and load each within 300 W over two
minutes. Auto repeat stopped first and started again after; the test options put back at 13:09:27.

| Check | Commanded | Before / during / after |
| --- | --- | --- |
| forced charge | 1250 W | 4499 / 1247 / 4499 W charge |
| forced discharge | 1250 W | -4499 / **1252** / -4498.5 W discharge |
| charge ceiling | 69 % at 71 % SoC | 4499 / **0** / 4499 W charge |

All three "the inverter did as it was told"; the ledger took them over run 1's and run 5's verdicts (not as
disputed). Restored 15 of 15, none left. Counts after: 53 passed, 0 failed, 5 not supported (the unenforced upper
bounds), 1 inconclusive (charging start threshold), 58 of 59 established.

What is left unexplained: run 5's ceiling at 53.5 % under 55.5 % carried a 4499 W charge on, where the same check
stopped the same charge at 53 % on 2026-11-23 and at 69 % today. One miss in three, not reproduced.
