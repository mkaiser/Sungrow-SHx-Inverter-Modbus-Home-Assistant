---
type: source
title: sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan-2.json
source_path: ../device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan-2.json
ingested: '2026-11-01'
created: '2026-11-01'
tags:
  - diagnosis
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - fwitten
  - direct_lan
  - capability-test
---

# SH10RT-V112, B001.V000.P023, fwitten master, the inverter's own LAN port, second reading

Read by the maintainer over a VPN on 2026-11-01 around noon, **with the owner's Home Assistant
polling**, with the full capability test on this tree's library (timed windows included). Source:
`device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan-2.json`.

| | |
| --- | --- |
| Installation | [fwitten](../entities/installation-fwitten.md), the master |
| Model | [SH10RT-V112](../entities/device-sh-rt.md), type code `0x0E0F` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md), version 1 `SAPPHIRE-H_01011.95.14` |
| Transport | the inverter's own LAN port; 6100 answered; 13265 names the fitted WiNet-S |
| Battery | [SBR096](../entities/device-sbr-battery.md), SoC 58.4 % |
| Answered | 236 of 245 fields; 36 of 36 blocks, despite the other poller |

## Energy history

The whole block answered, and each 2026 yearly slot equals the sum of its months exactly: PV
11596.5 kWh, direct consumption 0, export from PV 16654.7 kWh. **Export from PV exceeds PV
generation**, and direct consumption has read 0 since 2025; this master carries the cluster's
meter, so its export may count the slave's PV. Unexplained; see
[energy history](../concepts/energy-history.md). The first non-zero year is 2023.

Register 32998 reads 2000.

## Capability test

Outcome **3**, 9 of 9 readbacks matched. See [the capability test](../concepts/capability-test.md).

- [13074](../entities/register-13074.md): the probe was refused three times, **times ten**; 600 W
  went out as raw 600.
- Behaviour: forced charge (3241.5, 1247, 3060.5 W), forced discharge (1251 W for 1250 W) and the
  charge ceiling (2487, 0, 2661 W) did as they were told; the export limit could not tell
  (5533.5, 4281.5, 5813 W for 1250 W, export made by discharging 3400 W).
- **PV cut: did as it was told** (2002, 0, 2224 W), the second confirmation on P023.
- **Forced-charging window: did as it was told**: charge power 3258.5 W before, 3599 W during,
  3339.5 W after, a 340.5 W rise against an 81 W drift. The battery was already charging from PV,
  so the rise is small; the [mkaiser](sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-2-summary.md)
  run shows a larger one.
- Discharge window: not checked, the battery was charging.
- Restart: stopped in 2.0 s, Running after 194.5 s, settings survived.
