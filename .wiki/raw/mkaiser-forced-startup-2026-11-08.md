# The maintainer's SH10RT: forced startup under low SoC (13017), 2026-11-08

One-off scripts (not the capability test's engine) on the maintainer's SH10RT
(`anon-37323352958`, SAPPHIRE-H_B001.V000.P020, third-party battery), over its own LAN port,
unit 1, at 18:44-19:02 local time, after dark (PV 0 W). The house's Home Assistant kept polling;
lost reads were retried. The owner gave leave for the runs, and set the minimum SoC for them.

## Getting to low-SoC Standby

The minimum SoC (13059) had been 100 (10 %); that morning it was set to 250 (25 %) so the battery
would reach it after dark. At 17:43, with the SoC reading ~28 %, the owner raised it to 500
(50 %). The inverter then reported **0x8000 (Stop)** while **charging the battery from the grid
at 4499 W**, the battery's charge limit (33047 = 450), with the meter at ~5750 W of import
against a ~1080 W load; the SoC read 0.0 %. Set back to 250 at 17:45 (read back 250), it was
Running and discharging ~850 W within ~50 s, the SoC reading 29.3 % after ~3 minutes of that
charge. The owner then set 13059 to 360 (36 %).

At 18:44: 13000 = 0x0008 (Standby), the battery at 0 W, PV 0 W, the SoC reading 0.0 %, the whole
~4.15 kW load imported; 13017 = 0, the factory word.

## The writes

Each by a script that read and matched the stand-in first, wrote one word, said whether the
inverter accepted it, and then read 13017, 13000, SoC (13023), battery (5214) and meter (5601)
every ~10 s.

| Time | Write | Answer | 13017 reads | What the inverter did |
| --- | --- | --- | --- | --- |
| 18:45:05 | 0xAA | accepted | 0xAA | Standby until 18:47:06, then Starting (0x0020) for ~1.5 min, Running (0x0040) from 18:48:40 to the end of the watch at 18:54:58; the battery at 0 W throughout |
| 18:55:49 | 0x55 | accepted | 0x55 | Running at the first read, Standby (0x0008) at 18:56:10 and for the 3 minutes watched |
| 18:59:09 | 0x01 | refused, `ServerDeviceFailureError` (exception 0x04) | 0x55 | Standby |
| 19:00:11 | 0x55 | accepted | 0x55 | Standby |

- 0xAA woke the inverter from low-SoC Standby with no other command: Starting after 2 min 1 s,
  Running after 3 min 35 s, and it stayed Running with 13017 at 0xAA for the 6 minutes watched.
- 0x55 sent it back to Standby within ~21 s.
- 0x01 was refused; 13017 kept 0x55. A write of 0 was refused that morning (exception 0x04,
  10:49). So the factory 0 cannot be written back, and 13017 is left at 0x55, which is off.
- The meter read ~2.1 kW of import from 18:45, before the start, to the end: the house's load.

## Afterwards

13059 = 100 (10 %), written at 19:01 and read back 100. For the 90 s watched after it the
inverter stayed in Standby, the SoC reading 28.8 %, the battery at 0 W.
