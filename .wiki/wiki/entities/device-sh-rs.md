---
type: entity
title: SH-RS hybrid inverters
tags: [inverter, sh-rs, sunstone-h, single-phase]
created: '2026-10-31'
---

# SH-RS hybrid inverters

The single-phase hybrids, SH3.0RS to SH10RS, on firmware family `SUNSTONE-H`. Ten diagnoses in
the corpus, seven of them named for a [WiNet-S](device-winet-s.md) and two more measured behind
one: an anonymous
[SH10RS](../sources/sh10rs-b000v002p059-1p-anonymous-anon-27241675299-battery-sungrow-winet-lan-summary.md) on
[`SUNSTONE-H_B000.V002.P059`](firmware-sunstone-h-b000-v002-p059.md) with an SBR, an
[SH6.0RS](../sources/sh60rs-b000v001p068-1p-anonymous-anon-17579213881-battery-sbr192-winet-summary.md)
on [`SUNSTONE-H_B000.V001.P068`](firmware-sunstone-h-b000-v001-p068.md) with an
[SBR192](device-sbr-battery.md), and [Jam3s97](installation-jam3s97.md)'s
[SH10RS](../sources/sh10rs-b000v002p065-1p-jam3s97-anon-35122522532-battery-sbh300-winet-lan-summary.md)
on [`SUNSTONE-H_B000.V002.P065`](firmware-sunstone-h-b000-v002-p065.md) with an
[SBH](device-sbh-battery.md), and [bleughb](installation-bleughb.md)'s AC-coupled
[SH10RS](../sources/sh10rs-b000v002p057-1p-bleughb-anon-92100523190-battery-sungrow-winet-wlan-summary.md) on
[`SUNSTONE-H_B000.V002.P057`](firmware-sunstone-h-b000-v002-p057.md) with an SBH250, and [brendan](installation-brendan.md)'s
[SH10RS](../sources/sh10rs-b000v002p067-1p-brendan-anon-01362170354-battery-sungrow-winet-lan-summary.md) on
[`SUNSTONE-H_B000.V002.P067`](firmware-sunstone-h-b000-v002-p067.md) with two SBR224, and
[Maximo101](installation-maximo101.md)'s
[SH10RS](../sources/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-summary.md)
on the same firmware with two SBR192, read
[again two days later](../sources/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-2-summary.md), and [bigz2012](installation-bigz2012.md)'s
[SH10RS](../sources/sh10rs-b000v002p067-1p-bigz2012-anon-10002952285-battery-sungrow-winet-lan-summary.md)
on the same firmware again with two SBR224 and the PV cut confirmed. And
[icefest](installation-icefest.md)'s SH6.0RS on
[`SUNSTONE-H_B000.V001.P066`](firmware-sunstone-h-b000-v001-p066.md) with an SBR192, read twice
in ten minutes: through a [WiNet-S](../sources/sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-winet-lan-summary.md) and
[over RS485](../sources/sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-meter-direct-lan-summary.md), the first SH-RS read on a direct link.

## What is established

- **Read on a direct link once**, at icefest over RS485: every component answered there, the
  battery firmware, sub-controller and history included, as on an SH-RT's cable.
- [31211](register-31211.md) answers 0x55; the forced-charging schedule and the discharge
  schedules answer with the SH-RT's layout.
- Version 1 reads `SUNSTONE-H_01011.03.68` on P068, `SUNSTONE-H_01011.03.66` on P066,
  `SUNSTONE-H_01011.02.67` and then `SUNSTONE-H_01011.02.69` on P067 -- it moved under an
  unchanged firmware string, see [P067](firmware-sunstone-h-b000-v002-p067.md) -- and
  `SUNSTONE-H_01011.02.65` on P065 and `SUNSTONE-H_01011.02.61` on P059: its own series, like the T's `PEARL-H_01011.01.45`
  (see [SH-T](device-sh-t.md)), never compared numerically with SH-RT's `.95.xx`.
- **Three capability tests**, all through the dongle. On P065 the PV cut did as it was told
  (3465 W, 0 W, 3092 W) and the stop was refused with an exception. On
  [P067](firmware-sunstone-h-b000-v002-p067.md) it did as well, at
  [bigz2012](installation-bigz2012.md)'s (3467 W, 0 W, 3641 W), with the forced charge and
  discharge acting beside it (1234 W and 1256 W against 1250 W). On P057 the restart took 4 s to
  stop and 291 s to run again; the forced checks moved the battery but the house moved more.
- **Neither start-power register answers on any SH-RS**: 33149 and 33150 are absent, which is
  what #743 concluded and what the P067 capability test states outright.
- [13074](register-13074.md) **stores a written word as handed** on P065, P057 and P066.
- **The PV cut is watched on P065, P066 and P067**, and the site import limit (32998) on P066
  ([icefest](../sources/sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-meter-direct-lan-2-summary.md)) -- the first SH-RS on which it was.
- **[Register 32998](register-32998.md) limits grid import**, at 0.01 kW, on Jam3s97's SH10RS by
  the owner's meter trace; every SH-RS diagnosed reads 1300 (13.00 kW).
- **13250 answers on every SH-RS read**, so the firmware strings are available here, against
  V1.1.16's remark that SH3.0-10RS does not support 13250-13369. The model table keeps
  `FIRMWARE_VERSIONS` in the RS family's absent set and the probe overrides it on every machine
  ([Maximo101](../sources/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-summary.md)
  names the override; every SH-RS source page above reads the strings).
- **The SH8RS and SH10RS have four MPPTs**, and all four answer. The table excludes the RS family
  from `MPPT4`'s absent set for that reason but leaves it in `MPPT3`'s, which the probe then
  overrides. It costs nothing -- a probed capability survives the table -- and an SH3.0-6RS with
  two trackers is still right by the table.
- **A tracker that answers need not carry a string**, and the current says which. At
  [Maximo101](installation-maximo101.md)'s, `mppt4` reads 39.5 V to 53.6 V with **0.0 A** in every
  download, at 3.8 kW of PV and at 10.5 kW alike, while the other three account for
  `total_dc_power` to within 1 %
  ([that reading](../sources/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-2-summary.md)).
  A floating input drifts above 50 V, which the
  [capability test](../concepts/capability-test.md)'s `mppt4 carries a string` check once took as
  evidence on its own; since 2026-11-19 it asks for the tracker's current with the voltage, which
  is what reads this machine right.
- **On P066 the forced-charging window cannot be written**: its days word, holding 33209,
  refuses with 0x04 over RS485 and through the dongle alike. A restart there: 2 s to stop,
  150-165 s to run.
