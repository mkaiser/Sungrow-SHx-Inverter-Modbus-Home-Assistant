# bar12's SH10RT-20: the site import limit, from standby, 2026-11-07

One-off scripts (not the control test's engine) on bar12's SH10RT-20 (`anon-81257679535`,
SAPPHIRE-H_B001.V000.P023, read from 13250 before the runs, SBR096), at 20:37-22:07 local time,
after dark (PV 0 W). Over the inverter's own LAN port, unit 1, except the last run, which wrote
through the WiNet-S (WiFi) while a once-a-minute read over the cable watched. Nothing else polled
the inverter. The owner allows any test, writes included.

Before the runs the battery read 0.3 % against a minimum SoC of 5 % (13059 = 50), the inverter
was in Standby (13000 = 0x0008), and the house's ~300-420 W came from the grid. The engine
(`sungrow_control_test.py --import-limit --allow-dark --no-restart --dry-run`, through the
WiNet-S) refused to run: "The inverter reports 'Standby' rather than running".

Every run kept the control test's rules: the stand-in was read and matched before anything was
written; the raw words of every register a run wrote were snapshotted and flushed to a file
before its first write; the restore ran in `finally`, 13051 and 13050 first, writing each
snapshot word and reading it back raw until it matched. Snapshot each time: 13051 = 0xCC, 13050 =
0, 13052 = 0, 32998 = 2000; the schedule run also 33208 = 0x55, 33210-33214 = 13, 25, 13, 50, 59.

Samples every ~2 s: meter active power (5601, positive is import), load (13008), battery power
(5214, negative is charging), PV (5017), SoC (13023), 13000 and every written register.

## Run 1, 20:38: an EMS forced charge from Standby, watched 90 s (cable)

13052 = 1250, 13050 = 2, 13051 = 0xAA. For 90 s the inverter stayed in Standby (0x0008), the
battery at 0 W and import at the house's ~400 W. With no charge to cap, the script wrote no cap.
Restored; every word read back.

## Run 2, 20:42: the cap with the battery empty, normal operation (cable)

32998 = 10 (0.10 kW) for 90 s, then 2000. Import stayed at the whole load: median 395 W
(389-402) against 423 W before, battery 0 W, Standby throughout. 32998 read back 10. Restored.

## Run 3, 20:47: the forced-charging schedule from Standby (cable)

33210 = 20, 33211 = 45, 33212 = 21, 33213 = 10 (a window 20:45-21:10 on the inverter's clock,
which read 20:46), 33214 = 10 (target 10 %), 33208 = 0xAA; after 120 s 32998 = 200 for 90 s;
then 32998 = 2000 for 40 s; then the restore, 33208 first.

| Time | 13000 | Import | Battery |
| --- | --- | --- | --- |
| 20:47:25, schedule on | 0x0008 Standby | ~394 W | 0 W |
| 20:49:28 | 0x0020 Starting | ~392 W | 0 W |
| 20:50:54 | 0x0040 Running | 416 W | 0 W |
| 20:50:56, 32998 back to 2000 | | | |
| 20:50:58 | 0x0040 | 1970 W | -1493 W |
| 20:51:01 onwards | 0x0040 | ~4651 W | -4099 W (33047 = 410, 4100 W) |

The schedule woke the inverter 2 min 3 s after it was switched on. The charge began 2 s after
the cap was lifted, so the run says nothing about the cap against a scheduled charge. After the
restore the charge stopped within ~5 s and the inverter was in Standby again by 20:51:57.

## Run 4, 20:54: forced startup (13017), then an EMS forced charge and the cap (cable)

13017 = 0xAA; after 180 s 13052 = 1250, 13050 = 2, 13051 = 0xAA; after 90 s 32998 = 100
(1.00 kW) for 90 s; then 32998 = 2000 for 40 s. The 13017 part is in
`bar12-forced-startup-2026-11-07.md`.

| Phase | 13000 | Import, median (min-max) | Battery, median | Load |
| --- | --- | --- | --- | --- |
| forced charge, 32998 = 2000 (settled) | 0x0800 | 1668 W | -1250 W | ~336 W |
| forced charge, 32998 = 100 | 0x0800 | 942 W (936-952) | -547 W | ~342 W |
| forced charge, 32998 = 2000 again | 0x0800 | 1664 W (1659-1670) | -1249 W | ~338 W |

The cap cut the charge from 1250 W to ~547 W and held import at 942 W, 6 % under the 1.00 kW
cap. Lifted, the charge returned to 1250 W within ~3 s. 13051, 13050, 13052 and 32998 were
restored and read back.

## Run 5, 21:28: an EMS forced charge from Standby, watched 300 s (cable)

13052 = 1250, 13050 = 2, 13051 = 0xAA, with 13017 at 0x55 (off).

| Time | 13000 | Battery |
| --- | --- | --- |
| 21:28:19, written | 0x0008 Standby | 0 W |
| 21:30:20 | 0x0020 Starting | 0 W |
| 21:31:49 | 0x0800 | -1250 W, import ~1507 W |
| 21:33:21, restored | | |
| 21:33:24 | 0x0040 Running | 0 W |
| 21:33:38 | 0x0008 Standby | 0 W |

A forced charge alone woke the inverter: Starting after 2 min 1 s, charging after 3 min 30 s.
Run 1 had not waited long enough. Restored; every word read back.

## Run 6, 22:00: the cap through the WiNet-S

Written through the WiNet-S (WiFi, unit 1), judged by the cable. 13052 = 1250, 13050 = 2, 13051 = 0xAA; after 270 s 32998 = 100 for 90 s; then
2000 for 40 s; restored through the dongle.

| Phase | Dongle: 13000 | Dongle: import | Cable, once a minute |
| --- | --- | --- | --- |
| before | 0x1400 | 148 W | 0x0008, 146 W |
| starting | 0x1600 (22:02:44) | 148 W | 0x0020 (22:03:01) |
| charging, 32998 = 2000 | 0x0800 (22:04:12) | 1504 W, battery -1249 W | |
| charging, 32998 = 100 | 0x0800 | 964 W (from 22:04:44), battery -734 W | 0x0800, 958 W and 960 W, battery -722 and -727 W |
| charging, 32998 = 2000 again | 0x0800 | 1499 W (from 22:06:14) | |
| after the restore | 0x0000, then 0x1400 | 161 W | 0x0040 (22:07:02), 198 W |

The write through the dongle reached the inverter, and the cap held: ~960 W against 1.00 kW on
the cable. The dongle reported each change within ~3 s. Its restore read back 204, 0, 0 and
2000; the cable read the inverter running, then in Standby.

## Afterwards

The inverter in Standby, 13051 = 0xCC, 13050 = 0, 13052 = 0, 32998 = 2000, the schedule's words
as before. 13017 reads 0x55 (see the forced-startup record).
