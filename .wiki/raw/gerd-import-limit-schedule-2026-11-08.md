# gerd's SH8.0RT-V112: the site import limit against a scheduled charge, P022, 2026-11-08

One-off scripts (not the capability test's engine) on gerd's SH8.0RT-V112 (`anon-00267885816`,
SAPPHIRE-H_B001.V000.P022, SBR096), written through the WiNet-S (WiFi, unit 1) at 09:36-09:55
local time, with 0-280 W of PV. The inverter's own LAN port closed every Modbus session through
the night and the morning, while the house's Home Assistant polled; it answered once at 09:45:35.
The owner allows any test, writes included.

Before the runs: the battery at 0.5 % (minimum 10 %), the inverter running (13000 reads 0x0000
through the dongle), the house's ~330 W from the grid and PV; 32998 = 2000, the forced-charging
schedule off (33208 = 0x55, 33210-33214 = 0); battery max charge power 33047 = 440 (4400 W).

Each run kept the capability test's rules: the stand-in was read and matched before anything
was written; the raw words of 33208, 33210-33214 and 32998 were snapshotted and flushed to a file
before the first write; the restore ran in `finally`, 33208 first, writing each snapshot word
and reading it back raw until it matched. Every window was set to end on its own within 16
minutes, so a restore that could not get through would not leave a charge running.

Samples through the dongle every ~3 s when a read answered: meter (5601, positive is import),
load (13008), battery (5214, negative is charging), PV (5017), SoC (13023), 13000 and every
written register.

## Run 1, 09:36: window 09:35-09:51, target 5 %

33210 = 9, 33211 = 35, 33212 = 9, 33213 = 51, 33214 = 5, 33208 = 0xAA; after 300 s 32998 = 100
(1.00 kW) for 90 s; then 2000 for 45 s; then the restore.

The charge started within ~10 s of the schedule going on: battery -4399 W, import ~4.6-4.8 kW.
**It stopped at 09:41:15, 21 s before the cap was written**, at a reported SoC of 4.4 %: the 5 %
target was reached (the reported SoC lags). It did not resume when the cap was lifted. The run
says nothing about the cap.

Through the dongle, 33208 read back as written (0xAA, then 0x55 after the restore), but
**33210-33214 read 0 throughout**, before and after their writes, though the window took
effect. The cable, at 09:45:35, read 33208 = 0x55, 33209-33214 = 1, 0, 0, 0, 0, 0, 32998 = 2000,
13050-13052 = 0, 0xCC, 0.

## Run 2, 09:47: window 09:46-10:02, target 15 %

33210 = 9, 33211 = 46, 33212 = 10, 33213 = 2, 33214 = 15, 33208 = 0xAA; after 240 s 32998 = 100
for 90 s; then 2000 for 45 s; then the restore.

| Time | Import | Battery | PV | Load | SoC |
| --- | --- | --- | --- | --- | --- |
| 09:47:15, before | -23 W | 133 W discharging | 0 W | 132 W | 4.3 % |
| 09:47:24, schedule on | 4666 W | -4399 W | 0 W | 132 W | 4.3 % |
| 09:51:17, 32998 = 100 | | | | | |
| 09:51:18 | 4667 W | -4399 W | 0 W | 248 W | 7.6 % |
| 09:51:24 | 4667 W (stale) | **-862 W** | 0 W | 248 W | 7.7 % |
| 09:51:40-09:53:15 | every read timed out | | | | |
| 09:53:30 | **994 W** | -862 W | 250 W | 288 W | 8.1 % |
| 09:53:32, 32998 = 2000 | | | | | |
| 09:53:53 | 4740 W | -4399 W | 257 W | 354 W | 8.3 % |

Within ~7 s of the cap the charge fell from 4399 W to 862 W; the meter in that sample still
carried the pre-cap figure. The one complete sample under the cap read 994 W of import against
1.00 kW, with 250 W of PV and 288 W of load: the charge was what the cap left. Lifted, the charge
returned to 4399 W within ~20 s. The restore wrote and read back (through the dongle) 33208 =
0x55, 33210-33214 = 0 and 32998 = 2000; afterwards the battery stopped charging. The cable, at
09:56:40, read 33208 = 0x55, 33209-33214 = 1, 0, 0, 0, 0, 0, 32998 = 2000, 13050-13052 = 0, 0xCC,
0: nothing left changed.
