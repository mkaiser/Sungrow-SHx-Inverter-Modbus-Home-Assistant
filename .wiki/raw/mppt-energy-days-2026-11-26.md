# MPPT energy against Daily PV generation, six days at two houses, 2026-11-21 to 2026-11-26

Read on 2026-11-26 at about 20:10 UTC, after sunset, from the Home Assistant REST history API of two houses, read-only.
Days are local days (23:00 to 23:00 UTC). Both inverter entries read the inverter's own LAN port through a
modbus-proxy add-on (cable); neither house has an inverter entry through a WiNet-S.

- **mkaiser**: SH10RT on B001.V000.P020, two trackers, 0.1.0a46 to 0.1.0a57 over the span, auto repeat on most
  days. Beside the entry the YAML package still runs through the same proxy; its *Total DC power* (5017) is the
  only reading of 5017 in that house.
- **gerd**: SH8.0RT-V112 on B001.V000.P022, two trackers, 0.1.0a46 to 0.1.0a57. The entity ids changed to
  device-scoped ones on 2026-11-25 (renamed in the registry, so the history is continuous). Both entries were
  disabled 2026-11-22 04:46-07:57 UTC, before most of that day's sun.

Columns: *Trackers* is the rise of *MPPT1 energy* + *MPPT2 energy* (`sungrow_modbus.energy_integral`, V x I over the
polls); *13002* is *Daily PV generation*'s highest state that day; *Split* is the day's *Daily direct energy
consumption* + *Daily battery charge from PV* + *Daily exported energy from PV*; *5017 integral* is the YAML
package's *Total DC power* integrated over its state changes, holding each value until the next, gaps over 10 min
not counted.

## mkaiser, SH10RT, P020, cable

| Day | Trackers, kWh | 13002, kWh | Trackers / 13002 | Split, kWh | 5017 integral, kWh |
| --- | --- | --- | --- | --- | --- |
| 2026-11-21 | 22.93 (from 08:42 UTC) | 26.3 (23.3 from 08:42) | 0.984 from 08:42 | 9.9 + 11.1 + 5.3 = 26.3 | 26.38 |
| 2026-11-22 | 5.96 | 6.1 | 0.978 | 5.7 + 0.4 + 0.0 = 6.1 | 6.21 |
| 2026-11-23 | 41.68 | 42.0 | 0.992 | 10.4 + 10.6 + 21.0 = 42.0 | 42.03 |
| 2026-11-24 | 36.85 | 37.1 | 0.993 | 16.8 + 11.0 + 9.3 = 37.1 | 37.19 |
| 2026-11-25 | 37.97 | 38.2 | 0.994 | 14.8 + 11.1 + 12.3 = 38.2 | 38.31 |
| 2026-11-26 | 27.67 | 27.9 | 0.992 | 13.4 + 11.8 + 2.7 = 27.9 | 28.06 |

- Over the five whole days (22nd-26th): trackers 150.13 kWh, 13002 151.3 kWh, ratio **0.992**; the 5017 integral
  151.80 kWh, 1.003 of 13002.
- The integration's own *MPPT1 power* + *MPPT2 power* integrated the same way as 5017 gives the trackers' figure
  to within 0.04 kWh a day, so the integral adds nothing over the polled V x I; the trackers' V x I sits 0.8-1.4 %
  under the YAML package's 5017 integral on the four sunny days (4 % on the dull 22nd).
- No update gap over 150 s in either *MPPTn energy* between 07:00 and 15:00 UTC on any day.

## gerd, SH8.0RT-V112, P022, cable

| Day | Trackers, kWh | 13002, kWh | Trackers / 13002 | Split, kWh |
| --- | --- | --- | --- | --- |
| 2026-11-21 | 9.45 | 9.5 | 0.995 | 4.2 + 5.2 + 0.1 = 9.5 |
| 2026-11-22 | 7.37 | 7.6 | 0.970 | 3.9 + 3.6 + 0.1 = 7.6 |
| 2026-11-23 | 11.54 | 11.7 | 0.987 | 8.0 + 3.7 + 0.0 = 11.7 |
| 2026-11-24 | 11.02 | 11.2 | 0.984 | 5.7 + 5.4 + 0.1 = 11.2 |
| 2026-11-25 | 11.09 | 11.2 | 0.990 | 7.0 + 4.1 + 0.1 = 11.2 |
| 2026-11-26 | 10.89 | 11.1 | 0.981 | 5.4 + 5.6 + 0.1 = 11.1 |

- Over the six days: trackers 61.36 kWh, 13002 62.3 kWh, ratio **0.985**. gerd's house has no reading of 5017.
- 2026-11-22, the lowest, is the day both entries were disabled until 07:57 UTC.

## Both houses

- On every day at both houses, 13002 equals the split exactly (to its 0.1 kWh): the inverter's daily PV figure is
  the sum of the PV it sent to the load, the battery and the grid.
- At mkaiser's, 13002 follows the integral of 5017 (DC) within 0.1-0.4 % every day, including 2026-11-23, when
  31 kWh of it went to the load and the grid, where a conversion loss of even 2 % would have shown as 0.6 kWh.
  13002 counts on the DC side, and so does its split.
- 13002 steps by 0.1 kWh, so a day under about 10 kWh carries 1 % of rounding in the ratio by itself.
