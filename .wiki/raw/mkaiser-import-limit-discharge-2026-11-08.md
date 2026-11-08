# The maintainer's SH10RT: the site import limit against a lowered discharge limit, 2026-11-08

A one-off script (not the capability test's engine) on the maintainer's SH10RT
(`anon-37323352958`, SAPPHIRE-H_B001.V000.P020, third-party battery), over its own LAN port,
unit 1, at 17:27-17:32 local time, after dark (PV 0 W). The house's Home Assistant kept polling;
six reads lost the connection and were retried. The owner gave leave for the run.

Before the run: the inverter Running (13000 = 0x0040) in self-consumption, the battery at 29.3 %
against a minimum of 25 % (13059 = 250, lowered on purpose that morning) and discharging ~1100 W
into a ~1000 W load, the meter at ~0 W; 32998 = 2000, battery max discharge power 33048 = 330
(3300 W), 33047 = 450.

The question: with the house's load above the battery's discharge limit, does a cap on grid
import make the battery discharge past its limit, or cut the load? Expected no to both.

The capability test's rules were kept: the stand-in was read and matched before anything was
written; the raw words of 32998 and 33048 were snapshotted and flushed to a file before the first
write; the restore ran in `finally`, 32998 first, writing each snapshot word and reading it back
raw until it matched.

Samples every ~2-3 s: meter (5601, positive is import), load (13008), battery (5214, positive is
discharging), PV (5017), SoC (13023), 13000 and the written registers. Medians over the last two
thirds of each phase.

| Phase | Samples | Meter, median (min-max) | Battery, median | Load, median |
| --- | --- | --- | --- | --- |
| self-consumption | 13 | 8 W (-22 to 52) | 1153 W | 1086 W |
| 33048 = 50 (500 W), 32998 = 2000 | 44 | 670 W (597 to 813) | 499 W | 1109 W |
| 33048 = 50, 32998 = 5 (0.05 kW) | 34 | 709 W (578 to 785) | 499 W | 1130 W |
| 33048 = 50, 32998 = 2000 again | 19 | 542 W (450 to 749) | 499 W | 980 W |
| after the restore | 15 | -29 W (-97 to 46) | 1144 W | 1048 W |

- **The discharge limit held**: at 500 W the battery gave 499 W in every phase, the 0.05 kW cap
  included.
- **The cap did not hold import**: under a 50 W cap the grid supplied ~700 W, the load less the
  battery's limit, and the load was not cut.
- PV read 0 W and the SoC 29.3 % throughout; the inverter stayed Running.
- Restore: 32998 reads 2000, 33048 reads 330; the battery went back to ~1140 W within the first
  sample.
