# MPPT energy against Daily PV generation, one day, 2026-11-21

The maintainer's SH10RT on P020, two trackers, the integration entry (0.1.0a46) on the production Home
Assistant, reading the inverter's LAN port through the modbus-proxy add-on (cable). Read from Home
Assistant's REST history API, read-only, at about 22:40 UTC.

The entry's *MPPT1 energy* and *MPPT2 energy* (voltage times current integrated over the polls,
`sungrow_modbus.energy_integral`) were first recorded at 08:41:58 UTC; their totals then (5.2895 and
9.6477 kWh) were restored from earlier, so only the rise counts.

| Span (UTC) | MPPT1 + MPPT2 rise, kWh | Daily PV generation (13002) rise, kWh | Ratio |
| --- | --- | --- | --- |
| 08:42-09:00 | 0.35 | 0.1 | 3.50 |
| 09:00-10:00 | 4.16 | 4.5 | 0.925 |
| 10:00-11:00 | 6.46 | 6.4 | 1.009 |
| 11:00-12:00 | 6.50 | 6.8 | 0.955 |
| 12:00-13:00 | 3.64 | 3.5 | 1.040 |
| 13:00-14:00 | 1.32 | 1.5 | 0.880 |
| 14:00-15:00 | 0.46 | 0.5 | 0.929 |
| **08:42-end of day** | **22.93** (MPPT1 10.97, MPPT2 11.97) | **23.3** (3.0 -> 26.3) | **0.984** |

- *Daily PV generation* changed state 38 times in the day, so it is read on a slow tier and by steps;
  the hourly ratios mostly measure where its steps fall. The day's total is the comparison.
- No gap over 3 min in *MPPT1 energy*'s updates before 16:00 UTC, through the day's two extended tests
  and an inverter restart (~3 min, during which PV was off anyway).
- Whether 13002 counts the DC side or the AC side is not established. If DC, the trackers' integral is
  1.6 % under it; if AC, the trackers (DC) should exceed it by the conversion loss, and the integral is
  under by more than 1.6 %.
