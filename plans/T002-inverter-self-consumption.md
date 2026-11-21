# T002 - The inverter's own consumption, on hardware

Built: *Inverter self
consumption (estimated)* (`Derived.inverter_self_consumption`, PV +
battery - export - load, shown as a one-minute time-weighted mean, no
legacy id: #626 never shipped). The battery term is 5214 where it
answers, else 13022 signed by 13001's bits (as evcc), so the sensor
exists where 5214 is refused (#655). **At night in Standby it reads about
-1.9 W** (the maintainer's SH10RT, 2026-11-16, 23:00, battery empty), not
the tens of watts expected: in Standby the inverter reports 0 for PV,
battery, export and AC power, so every term but the load's noise is zero
and the estimate collapses. So the sensor says nothing about the standby
draw, and whether it should read `unknown` there rather than a number near
zero is the question to settle. **By day it is plausible and noisy**
(the same house, 2026-11-21, 5.5 h of the one-minute mean while Running:
median 248 W, hourly medians 143-365 W rising with the power converted,
10th-90th percentile 104-416 W, single values from -178 to 601 W;
wiki: mkaiser-production-install-2026-11-21). So an hour's mean is worth
showing and a single minute is not: a longer window, or the energy
counterpart, is the form that reads well. Left besides: the Standby
decision above; the 13022 path on a house that refuses 5214; the energy
counterpart.
