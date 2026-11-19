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
zero is the question to settle. Left besides: the daytime look, whether
the mean is steady enough and plausible while the inverter works; the
13022 path on a house that refuses 5214; its energy counterpart.
