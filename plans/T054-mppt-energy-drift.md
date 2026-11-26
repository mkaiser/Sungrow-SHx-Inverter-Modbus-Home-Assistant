# T054 - How far the MPPT energy drifts

*MPPTn energy* integrates voltage times current over the polls
(`sungrow_modbus.energy_integral`). Wanted from a house running it a few
days: the trackers' daily sum against *Daily PV generation*, on a cable and
through a WiNet-S, which says how much the polling interval and a dongle's
stale reads cost.

**No capability test measures it** (checked 2026-11-12): auto repeat's
plausibility checks compare *Daily PV generation* with the integral of
*Total DC power*, and each tracker's V × I with *Total DC power* at one
moment, but nothing integrates the trackers the way the sensors do.
Proposed: one more check of that kind, the trackers' summed V × I
integrated against the rise of *Daily PV generation*, riding on auto repeat,
whose median ratio in the ledger and the document is the drift asked for
here, per firmware and transport. Caveat: the check judges in decades (a
scale error), so a drift of a few percent comes out `MATCH` or
`INCONCLUSIVE` and the document must carry the median itself.

## Measured

Both houses read over the cable, through a modbus proxy; days are local.

| House, transport | Span | Trackers' rise / *Daily PV generation* |
| --- | --- | --- |
| mkaiser SH10RT P020, cable | 2026-11-22 to 11-26, five whole days | 150.13 / 151.3 kWh = **0.992** (days 0.978-0.994) |
| gerd SH8.0RT-V112 P022, cable | 2026-11-21 to 11-26, six days | 61.36 / 62.3 kWh = **0.985** (days 0.970-0.995) |

Wiki: mppt-energy-days-2026-11-26 (and the first day, mkaiser-mppt-energy-day-2026-11-21).

- **13002 counts DC.** At mkaiser's its day follows the integral of 5017 (*Total DC power*) within
  0.1-0.4 %, even on a day 31 kWh of it went to load and grid. So the comparison carries no conversion
  loss, and the integral really is 1-2 % short.
- **The polling costs nothing measurable on the cable**: 5017, polled and integrated the same way, lands
  on 13002; the shortfall is V x I against 5017 (0.8-1.4 % on sunny days). Why (the current's 0.1 A step,
  or 5017 computed from finer readings) is not established and does not change what the sensor is for.
- So *MPPTn energy* is right for comparing trackers and not a stand-in for 13002 in the Energy
  dashboard, which is what `doc/energy_dashboard.md` already tells people.

## Left

A house through a WiNet-S, where stale reads would hit the integral rather than V x I. No house runs an
inverter entry through one today: gerd's WiNet-S (proxy port 503) has none, and adding one there puts a
second poller on a dongle that tolerates few sessions, so it waits for the maintainer's word or a
contributor's house. The auto-repeat check proposed above is not worth building for this alone: on the
cable the answer is a percent or two, and the check would judge it `MATCH` anyway.

## Status log

- 2026-11-21: one cable day at mkaiser's from the production recorder.
- 2026-11-26: five more days there and six at gerd's, both cable; 13002 settled as DC. Left: a WiNet-S house.
