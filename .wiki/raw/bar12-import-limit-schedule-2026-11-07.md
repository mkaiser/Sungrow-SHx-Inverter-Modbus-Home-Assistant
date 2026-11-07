# bar12's SH10RT-20: the site import limit against a scheduled charge, 2026-11-07

A one-off script (not the capability test's engine) on bar12's SH10RT-20 (`anon-81257679535`,
SAPPHIRE-H_B001.V000.P023, SBR096), over the inverter's own LAN port, unit 1, at 22:44-22:53
local time, after dark (PV 0 W). Nothing else polled the inverter. The owner allows any test,
writes included. It follows the evening's runs in `bar12-import-limit-2026-11-07.md`, where a
scheduled charge began only after the cap was lifted.

Before the run: the inverter in Standby (13000 = 0x0008), SoC 1.8 % against a minimum of 5 %,
13017 = 0x55, the inverter's clock 22:43:36, the house's ~210 W from the grid; battery max
charge power 33047 = 410 (4100 W).

The capability test's rules were kept: the stand-in was read and matched before anything was
written; the raw words of 33208, 33210-33214 and 32998 were snapshotted and flushed to a file
before the first write; the restore ran in `finally`, 33208 first, writing each snapshot word
and reading it back raw until it matched. Snapshot: 33208 = 0x55, 33210 = 13, 33211 = 25,
33212 = 13, 33213 = 50, 33214 = 59, 32998 = 2000.

The writes: 33210 = 22, 33211 = 42, 33212 = 23, 33213 = 10 (a window 22:42-23:10 on the
inverter's clock), 33214 = 10 (target 10 %), 33208 = 0xAA; after 330 s, 32998 = 100 (1.00 kW)
for 90 s; then 32998 = 2000 for 45 s; then the restore.

Samples every ~2.5 s: meter active power (5601, positive is import), load (13008), battery power
(5214, negative is charging), PV (5017), SoC (13023), 13000 and every written register.

| Time | 13000 | Import | Battery | Load |
| --- | --- | --- | --- | --- |
| 22:44:51, schedule on | 0x0008 Standby | ~210 W | 0 W | |
| 22:46:52 | 0x0020 Starting | ~210 W | 0 W | |
| 22:48:21 | 0x0040 Running | 4475 W | -4099 W | |
| 22:50:21, 32998 = 100 | | | | |
| 22:50:24 | 0x0040 | 4647 W | -4099 W | 338 W |
| 22:50:26 | 0x0040 | 947 W | -509 W | 339 W |
| 22:50:28-22:50:38 | 0x0040 | 947-959 W | -510 to -517 W | 381-388 W |
| 22:51:40-22:51:50 | 0x0040 | 957-964 W | -686 to -690 W | 212-217 W |
| 22:51:52, 32998 = 2000 | | | | |
| 22:51:55 | 0x0040 | 4473 W | -4099 W | 209 W |

- **The cap holds a charge commanded by the forced-charging schedule.** At 1.00 kW the charge
  fell from 4099 W to ~510 W within one sample (~2 s), and import held at 947-964 W (median
  956 W), 4-5 % under the cap.
- **It follows the load**: when the house load fell from ~385 W to ~215 W, the charge rose from
  ~512 W to ~688 W and import stayed at the cap.
- Lifted, the charge returned to 4099 W within ~3 s.
- The schedule woke the inverter from Standby: Starting 2 min 1 s after it was switched on,
  charging after 3 min 30 s.

Restore: 33208 reads 0x55, 33210-33214 read 13, 25, 13, 50, 59, 32998 reads 2000. Within ~3 s of
the schedule going off the charge stopped. The inverter stayed Running afterwards, the battery
(SoC 4.2 %) discharging ~150 W into the house, 13017 at 0x55.
