---
type: source
title: sh10rt-v112-b001v000p023-3p-anonymous-anon-14076202309-battery-unknown-winet.json
source_path: ../device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-anonymous-anon-14076202309-battery-unknown-winet.json
ingested: '2026-11-16'
created: '2026-11-16'
tags:
  - diagnosis
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - anonymous
  - winet
  - wallbox
  - ac011e-01
---

# SH10RT-V112, B001.V000.P023, anonymous, through a WiNet-S, with an AC011E-01 at unit 4

Read 2026-11-16 at 09:20 UTC, posted to issue #786; the reporter field is empty, so it stays
anonymous. A **Home Assistant diagnostics download**, so it carries the diagnosis section alone:
no register dump and no block read test, which the download does not afford. Committed
unchanged. Source:
`device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-anonymous-anon-14076202309-battery-unknown-winet.json`.

| | |
| --- | --- |
| Model | [SH10RT-V112](../entities/device-sh-rt.md), type code `0x0E0F` |
| Stand-in serial | `anon-14076202309` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| Communication module firmware | `WINET-SV200.001.00.P045` |
| Transport (owner) | not said: a diagnostics download puts none of the questions |
| Transport (measured) | through a communication module; [6100](../entities/register-6100.md) refused, 5741 and 5744 refused, 2612 and 2628 unanswered -- the [WiNet-S](../entities/device-winet-s.md) pattern throughout |
| Battery | an SBR, firmware `SBRBCU-S_22011.01.30`, 9.6 kWh by 5639, modules not named |
| At the time | PV 1118 W, SoC 0.0 %, load 1918 W |
| Polling | this Home Assistant throughout, 24 components at 5/10/60/600 s, coordinators not paused |

## The wallbox: an AC011E-01 at unit 4

The third wallbox read anywhere and the first that is not an AC22E-01: the other two are
[gerd](../entities/installation-gerd.md)'s, at unit 3 behind a dongle and at its own
address over TLS, and an anonymous one at its own address. It is also the first found at a
unit other than 3.

| | |
| --- | --- |
| Reached | unit **4**, through the dongle |
| Stand-in serial | `anon-36410490032` |
| Model name (21216) | `AC011E-01`, type code `0x20DA` |
| Version (21226) | `AC011K-AE-25_V1.7.18` |
| Rating | 16 A, three phase, 230 V nominal |
| At the time | idle (21317 = 1), pilot 12.5 V, charger enabled, start mode "start with EMS" |
| Totals | 4028.413 kWh lifetime, 55.796 kWh this session |

What it settles:

- **A wallbox answers at unit 4 behind a WiNet-S**, which until now was reported and never
  measured ([the query](../queries/which-unit-does-a-winet-s-give-a-wallbox.md)). The search
  tries 3, then 2 and 4, so it was found without a setting.
- **The output current setting (21203) is 0.1 A per count on an AC011E-01 too.** gerd's
  AC22E-01 ruled 0.01 A out on 2026-11-14, reading 316 against a 16.0 A draw
  ([the session](gerd-wallbox-inverter-control-2026-11-14-summary.md)); the map that reads it as
  0.01 A is AC011E-based (`doc/wallbox_registers.md`), so the disagreement stood until an
  AC011E-01 was read. This one reads **6.0 A** idle, the minimum a wallbox offers and where
  gerd's ramp starts. At 0.01 A it would be 0.6 A, which no wallbox can deliver.
- **The 4.14 kW minimum is the wallbox's own**: 21272 reads 4140 W, which is 6 A over three
  phases at 230 V, the figure the 2023 EV Power Guide names
  ([the sources](wallbox-phase-switching-sources-2026-11-14-summary.md)). 21273 reads 11040 W,
  16 A over the same three phases.
- **The model name and the version string disagree about the model**: 21216 says `AC011E-01`
  where the version says `AC011K-AE-25`, which is the part number an owner buys. The map keys on
  the type code and the `AC` prefix, so neither reading is relied on for identity.

`power_control_allowed` (21316) and `power_request` (21315) both read 0, and 21313 is published
twice -- as `unnamed_register_21313`, still open, and as `power_limit`, 0.0 kW.

## The inverter

Every feature probed read as **readable**: nothing wrote, as a diagnostics download never does.
`13018` answered `65535`, which is unavailable rather than a refusal
([zero means absent](../concepts/zero-means-absent.md)); `31211` answered, as it does on
[P023](../entities/firmware-sapphire-h-b001-v000-p023.md). Five components did not answer:
battery firmware, sub-controller firmware and the three history blocks, all of which a WiNet-S
withholds.
