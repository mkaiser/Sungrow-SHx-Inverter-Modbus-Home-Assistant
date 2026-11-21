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

| House, transport | Span | Trackers' rise / *Daily PV generation* rise |
| --- | --- | --- |
| mkaiser SH10RT P020, cable via proxy | 2026-11-21, 08:42 UTC to sunset | 22.93 / 23.3 kWh = **0.984** (hourly 0.88-1.04) |

Wiki: mkaiser-mppt-energy-day-2026-11-21. Open with it: whether 13002 counts
DC or AC. If AC, the trackers' DC energy should exceed it by the conversion
loss, and the integral's shortfall is larger than 1.6 %.

## Status log

- 2026-11-21: one cable day measured from the production recorder (above).
  gerd's Home Assistant refused connections that evening, so no WiNet-S day.
  Next: a few more days on the cable from the same recorder, and a WiNet-S
  house (gerd's, with the entry on port 503, or the proposed auto-repeat
  check, which is not built: the maintainer's call).
