---
type: source
title: daily-reset-midnight-2026-11-26.md
source_path: raw/daily-reset-midnight-2026-11-26.md
ingested: '2026-11-26'
created: '2026-11-26'
tags: [last-reset, daily-consumed-energy, statistics, restart, sh10rt, sh8-0rt-v112, mkaiser, gerd]
---

# The daily consumed energy's `last_reset` through a midnight, 2026-11-25/26

`.wiki/raw/daily-reset-midnight-2026-11-26.md`: integration 0.1.0a57 at [mkaiser](../entities/installation-mkaiser.md)'s
[SH10RT](../entities/device-sh-rt.md) on [P020](../entities/firmware-sapphire-h-b001-v000-p020.md) and at
[gerd](../entities/installation-gerd.md)'s SH8.0RT-V112 on [P022](../entities/firmware-sapphire-h-b001-v000-p022.md),
read from each recorder the next afternoon, and one restart at gerd's.

| Claim | Evidence | Status |
| --- | --- | --- |
| **`last_reset` is set once, in the poll where the counters begin again**, and not before | mkaiser 00:05:25, gerd 00:00:07: all five counters (PV, export, import, battery charge and discharge) at 0.0 in that poll; absent before it; unchanged at 14:00 | two houses, one night |
| The state keeps the old day's value up to the reset, then starts near zero | 36.8 -> 0.0 and 32.4 -> 0.0; nothing held, the five fell together | two houses |
| **The statistics book the new day as the state**, no negative hour | changes 00:00-14:00 add to 18.1 (state 18.1) and 8.8 (8.8); smoothed twin 17.7 (17.7) and 8.6 (8.6); `total_consumed_energy` 18.2 and 8.9 | two houses |
| **A restart neither sets `last_reset` again nor loses it** | gerd, 14:19-14:21: 9.0 before, 9.2 after, `last_reset` unchanged; the hour's change +0.50, as the total's | one restart |
| The readings check agrees at mkaiser | *daily counters reset at midnight*: 2 events, none against, after this night (the integration's results view, 2026-11-26 08:55) | |
| What the house uses between the old day's last poll and the reset is in neither day | mkaiser: 0.20 against the total's 0.30 over 00:00-01:00, with a ten-minute poll | one house |

Code: `src/sungrow_modbus/hybrid_inverter/daily_cycle.py`, `custom_components/sungrow_modbus/sensor.py`
(`SungrowDailyTotalSensor`).
