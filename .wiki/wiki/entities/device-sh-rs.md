---
type: entity
title: SH-RS hybrid inverters
tags: [inverter, sh-rs, sunstone-h, single-phase]
created: '2026-10-31'
---

# SH-RS hybrid inverters

The single-phase hybrids, SH3.0RS to SH10RS, on firmware family `SUNSTONE-H`. Seven diagnoses in
the corpus, five through a [WiNet-S](device-winet-s.md): an anonymous
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
[`SUNSTONE-H_B000.V002.P067`](firmware-sunstone-h-b000-v002-p067.md) with two SBR224. And
[icefest](installation-icefest.md)'s SH6.0RS on
[`SUNSTONE-H_B000.V001.P066`](firmware-sunstone-h-b000-v001-p066.md) with an SBR192, read twice
in ten minutes: through a [WiNet-S](../sources/sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-winet-lan-summary.md) and
[over RS485](../sources/sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-meter-direct-lan-summary.md), the first SH-RS read on a direct link.

## What is established

- **Read on a direct link once**, at icefest over RS485: every component answered there, the
  battery firmware, sub-controller and history included, as on an SH-RT's cable.
- [31211](register-31211.md) answers 0x55; the forced-charging schedule and the discharge
  schedules answer with the SH-RT's layout.
- Version 1 reads `SUNSTONE-H_01011.03.68` on P068, `SUNSTONE-H_01011.03.66` on P066, `SUNSTONE-H_01011.02.67` on P067 and `SUNSTONE-H_01011.02.65` on P065 and `SUNSTONE-H_01011.02.61` on P059: its own series, like the T's `PEARL-H_01011.01.45`
  (see [SH-T](device-sh-t.md)), never compared numerically with SH-RT's `.95.xx`.
- **Two capability tests**, both through the dongle. On P065 the PV cut did as it was told (3465 W,
  0 W, 3092 W) and the stop was refused with an exception. On P057 the restart took 4 s to stop
  and 291 s to run again; the forced checks moved the battery but the house moved more.
- [13074](register-13074.md) **stores a written word as handed** on P065, P057 and P066.
- **[Register 32998](register-32998.md) limits grid import**, at 0.01 kW, on Jam3s97's SH10RS by
  the owner's meter trace; every SH-RS diagnosed reads 1300 (13.00 kW).
- **On P066 the forced-charging window cannot be written**: its days word, holding 33209,
  refuses with 0x04 over RS485 and through the dongle alike. A restart there: 2 s to stop,
  150-165 s to run.
