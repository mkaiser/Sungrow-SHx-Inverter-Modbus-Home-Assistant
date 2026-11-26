# The daily consumed energy's `last_reset` through a midnight, two houses, 2026-11-25/26

Integration 0.1.0a57 from the Marketplace at the maintainer's SH10RT (P020) and at gerd's SH8.0RT-V112 (P022), both
`manifest/get` 0.1.0a57. Read on 2026-11-26 afternoon from each Home Assistant's recorder over the websocket (state
history with attributes, hourly long-term statistics); nothing written. Times CET. The daily counters are polled
every ten minutes at both houses. No Home Assistant restart at either since 2026-11-25 08:00.

## The poll with the reset

| House | Last poll before | Values before (PV, export, import, charge, discharge -> consumed) | Poll with the reset | After |
| --- | --- | --- | --- | --- |
| mkaiser | 23:55:00 / 23:55:25 | 38.2, 12.4, 11.8, 11.2, 10.4 -> 36.8 (smoothed 36.8) | **00:05:25**: all five 0.0 | consumed 0.0, smoothed 0.0 |
| gerd | 23:50:07 | 11.2, 0.2, 21.8, 4.3, 3.9 -> 32.4 (smoothed 32.3) | **00:00:07**: all five 0.0 | consumed 0.0, smoothed 0.0; 00:10:07 import 0.1, consumed 0.1, smoothed 1.93e-08 |

`last_reset` was absent from both sensors' attributes before the reset poll, and set in that poll to its time
(mkaiser 2026-11-25T23:05:25.0127Z and .0129Z for the smoothed twin; gerd 23:00:07.2309Z and .2315Z), and was
still that value at 14:00 the next day. All five counters fell in the same poll at both houses, so nothing was held.

## Hourly statistics (change per hour, kWh)

| House | Sensor | 23:00-24:00 | 00:00-01:00 | negative hours | sum of changes 00:00-14:00 | state at 14:00 |
| --- | --- | --- | --- | --- | --- | --- |
| mkaiser | daily consumed | 0.30 | 0.20 | none | 18.1 | 18.1 |
| mkaiser | smoothed twin | 0.40 | 0.20 | none | 17.7 | 17.7 |
| mkaiser | total consumed (reference) | 0.30 | 0.30 | none | 18.2 | |
| gerd | daily consumed | 0.50 | 0.30 | none | 8.8 | 8.8 |
| gerd | smoothed twin | 0.50 | 0.30 | none | 8.6 | 8.6 |
| gerd | total consumed (reference) | 0.50 | 0.30 | none | 8.9 | |

The first hour of the new day carries the statistics' `last_reset` of the reset poll. At mkaiser the daily sensor
has 0.1 kWh less than the total over 00:00-01:00 (0.20 against 0.30): what the house used between the old day's last
poll (23:55) and the reset is in neither day, since the inverter's counters were zeroed before it was read.

## A restart at gerd's, 2026-11-26

On the maintainer's word, `ha core restart` at gerd's at 14:19:11, back at 14:20:48. Before: daily consumed 9.0,
smoothed 8.9, `last_reset` 23:00:07.2309Z / .2315Z (updated 14:10:07). First state after: daily consumed **9.2**,
smoothed 9.2, `last_reset` **unchanged** on both (updated 14:20:46). The inverter's auto repeat, ended by the restart,
was started again at 14:21 (mode extended_auto_repeat); the wallbox entry's was not running before.

After the restart, read at 15:13: the polls at 14:40:45, 15:00:45 and 15:10:45 read 9.3, 9.4 and 9.6 (smoothed 9.2,
9.3, 9.4), each with the same `last_reset`. Hourly statistics, 14:00-15:00: daily consumed change **+0.50** (state
9.30), smoothed twin +0.70 (state 9.30), total consumed +0.50; no negative hour, no new `last_reset` in the
statistics. The smoothed twin came back at the raw value (8.9 before, 9.2 after), since its average starts again.
