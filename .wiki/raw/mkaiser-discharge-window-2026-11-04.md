# The maintainer's SH10RT: the discharge window check, 2026-11-04

The control test's own engine (`device-survey/scripts/python/sungrow_control_test.py
--discharge-window --allow-dark --no-restart`) on the maintainer's SH10RT
(`anon-37323352958`, SAPPHIRE-H_B001.V000.P020, third-party battery) over its own LAN
port, in the evening with no PV, the house's Home Assistant restarted just before. The
snapshot was flushed before the first write; the ordinary restore put every word back, read
back after (every entry "already holding its original value" or restored, none left changed;
exit 3 only because checks were skipped). Battery power is read as discharge power, positive
while the battery supplies the house.

## Run 1, about 20:37 inverter clock, SoC 28.8 %

The discharge window check was **not run**: the battery was discharging 495 W, under the
500 W (`EFFECT_FLOOR_W`) a stop needs to be told from the house. Forced charge did as it was
told (-472.5, 1249, -448 W); forced discharge did as it was told (458, 1251, 465.5 W).

## Run 2, about 20:49 inverter clock, SoC 27.7 %, house load raised by the owner

| Check | Commanded | Before | During | After | Drift | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| forced charge | 1250 W | -757 W ±4 | 1250 W ±0 | -730 W ±9.5 | 27 W | did as it was told |
| forced discharge | 1250 W | 726 W ±2.5 | 1251 W ±0 | 725 W ±5 | 1 W | did as it was told |
| **discharge windows moved away from now** | -- | 722.5 W ±2.5 | **0 W ±0** | 719 W ±4 | 3.5 W | **did as it was told** |

The snapshot's schedule words, before the run: weekday and weekend discharge windows 1 and 2
each held 00:00 to 24:00. After the run each read back as in the snapshot. 33047 held 4500 W
and 33048 held 3300 W, and both were restored.

Readback: 8 of 9 matched the specification's scale; `export_power_limit` kept its old word
(10000 W) because feed-in limitation is off (13087 holds 0x55), where the register ignores a
write without an exception. The PV cut is absent on P020 (31211), the charge ceiling needs a
battery above `battery_max_soc`'s 50 % floor, and nothing was restarted.
