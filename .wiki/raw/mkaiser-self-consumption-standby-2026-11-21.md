# The inverter self-consumption estimate in Standby, 2026-11-21 evening

The maintainer's SH10RT on P020, the integration entry (0.1.0a46) on the production Home Assistant,
battery empty (SoC 0 %), 13000 Standby since 19:58 UTC. Read from Home Assistant's REST API (states and
the recorder's history), read-only.

- 22:24 UTC, one moment: *Load power* 1986 W, *Import power* 1990 W (meter active power 1990 W),
  *Export power* 0 W, *Battery power* 0 W, *Inverter self consumption (estimated)* 4.6 W (its one-minute
  mean).
- 20:00-22:30 UTC, the recorder's series: the estimate, 1738 values, minimum -181.5 W, median 0.6 W,
  maximum 174.3 W; load 378-6877 W, median 1993 W; import 379-6875 W, median 1995 W.

Reading: in Standby the balance PV + battery - export - load reduces to import - load. The inverter's
own draw comes through the meter and is counted in the load it reports, so the estimate cannot see it;
what it shows is the difference of two readings taken at different moments, centred on zero.
