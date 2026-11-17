# The maintainer's SH10RT: the discharging start threshold, settled, 2026-11-17

The companion to the charging start threshold, settled an hour later at `anon-37323352958`
(SAPPHIRE-H_B001.V000.P020), in a run auto repeat started by itself at 12:05 local. The battery
was at 11 %, discharging a couple of hundred watts into the house under a thin sky.

From the capability ledger's seventh block:

| Field | Value |
| --- | --- |
| check | discharging start threshold |
| commanded | 1000 W |
| before | 205.0 W |
| during | 0.0 W |
| after | 221.0 W |
| verdict | **the inverter did as it was told** |

The threshold was raised above the few hundred watts the battery was giving; the discharge
stopped; when the threshold went back, it resumed at 221 W. Both start thresholds are now
established on this firmware.

## The same check, failed and passed, three hours apart

This is the cleanest demonstration of what the drift gate does at low power, because it is one
check at one house on one day, twice:

| Time | before | during | after | Outcome |
| --- | --- | --- | --- | --- |
| 09:40 | 216.5 W | 0.0 W | **0.0 W** | could not tell: "the input drifted across the measurement" |
| 12:05 | 205.0 W | 0.0 W | **221.0 W** | the inverter did as it was told |

The commanded value, the check, the register and the inverter were identical. The measurements
started from almost the same place -- 216.5 W and 205.0 W. The only difference is that the first
time the discharge did not come back inside the window and the house had moved past the 150 W
floor by the end, and the second time it came back to within 16 W of where it began.

So the earlier reading here -- that the start thresholds might never settle at a house with
people in it -- is wrong, and the correction is now measured rather than argued: **the window is
catchable, and both halves were caught within three hours of each other once auto repeat was left
running to keep trying.** What the gate costs is attempts, not the result.

## The owner's ceiling, a third time

The same run recorded `battery_ceiling_w = 5000`, the owner's configured figure, as did the two
before it. Every run taken before that option reached the capability test recorded the
unconstrained BMS-derived ceiling instead, between 7096 and 7274.
