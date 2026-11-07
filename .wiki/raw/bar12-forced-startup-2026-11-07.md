# bar12's SH10RT-20: forced startup under low SoC (13017), 2026-11-07

Watched writes of holding register 13017 on bar12's SH10RT-20 (`anon-81257679535`,
SAPPHIRE-H_B001.V000.P023, SBR096), 20:54-21:58 local time, after dark (PV 0 W), with the
battery at 0.3-1.5 % against a minimum SoC of 5 % (13059 = 50). Over the inverter's own LAN port,
unit 1, except T5, written through the WiNet-S. A read-only script read 13017, 13000, SoC, the
battery and the meter over the cable once a minute throughout. Nothing else polled the inverter.
The owner allows any test, writes included. The stand-in was read and matched before every write.

Before the first write 13017 read 0 and the inverter was in Standby (13000 = 0x0008).

## Run 4 (20:54), and the restore that could not be made

13017 = 0xAA, accepted. It read back 0xAA. Standby lasted 2 min 36 s; then Starting (0x0020)
from 20:56:37. At 20:57:03 an EMS forced charge was written (see
`bar12-import-limit-2026-11-07.md`); from 20:58:07 13000 read 0x0800 and the battery charged.
The restore wrote 0 to 13017: **refused with exception 0x04** (`ServerDeviceFailureError`), 19
times over three minutes; the script was stopped. A raw read then: 13017 = 0xAA, 13000 = 0x0040
(Running), SoC 1.2 %, battery 0 W; 13050-13052 and 32998 as before.

## T0, 21:13-: the read-only watch

13017 read 0xAA, the inverter Running (0x0040) and the battery at 0 W from 21:13:42 to 21:16:43,
23 minutes after the write. It did not reset itself.

## T1, 21:17: 0x55

13017 = 0x55, accepted. It read back 0x55 at once. 13000 went from 0x0040 to **0x0008 Standby
within 20 s** (21:17:59) and stayed there for the ten minutes watched.

## T2, 21:28: no 13017

An EMS forced charge alone woke the inverter from Standby, 13017 at 0x55 throughout (in
`bar12-import-limit-2026-11-07.md`, run 5).

## T3, 21:34: 0xAA alone

13017 = 0xAA, accepted, with no other command. Standby (0x0008) until 21:38:24, Starting (0x0020)
until 21:39:49, then **Running (0x0040), battery 0 W**, until 21:44:35: 3 min 55 s to Starting, 5
min 20 s to Running. Then 13017 = 0x55, accepted: Standby within ~21 s (21:44:56).

## T4, 21:47: other words

| Word | Answer | 13017 after | 13000 |
| --- | --- | --- | --- |
| 0x01 | refused, exception 0x04 | 0x55 | 0x0008 |
| 0xFF | refused, exception 0x04 | 0x55 | 0x0008 |

0x55 was written after each, and accepted.

## T5, 21:50: through the WiNet-S

13017 = 0xAA written through the WiNet-S, accepted; the dongle read back 0xAA at once, and the
cable read 0xAA at 21:50:52. The cable: Standby until ~21:52, Starting (0x0020) at 21:52:54,
Running (0x0040) at 21:54:55, battery 0 W. The dongle reported 0x1400, 0x1600 and 0x0000 for the
same states. 0x55 through the dongle at 21:57:45, accepted and read back at once; the cable read
0x55 at 21:57:55 and Standby at 21:58:56.

## Afterwards

13017 reads 0x55, the inverter in Standby. The word before the first write, 0, is not one the
inverter takes.
