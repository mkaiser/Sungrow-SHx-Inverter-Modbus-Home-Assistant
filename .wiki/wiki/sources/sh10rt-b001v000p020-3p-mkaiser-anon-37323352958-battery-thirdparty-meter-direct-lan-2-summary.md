---
type: source
title: sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-2.json
source_path: ../device-diagnosis/results/inverter/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-2.json
ingested: '2026-11-01'
created: '2026-11-01'
tags:
  - diagnosis
  - sh10rt
  - sapphire-h-b001-v000-p020
  - mkaiser
  - direct_lan
  - capability-test
---

# SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port, second reading

Read by the maintainer on 2026-11-01 around noon, the house's Home Assistant stopped, with the full
capability test on this tree's library (timed windows included). Source:
`device-diagnosis/results/inverter/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-2.json`.

| | |
| --- | --- |
| Installation | [mkaiser](../entities/installation-mkaiser.md) |
| Model | [SH10RT](../entities/device-sh-rt.md), type code `0x0E03` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P020`](../entities/firmware-sapphire-h-b001-v000-p020.md), version 1 `SAPPHIRE-H_01011.95.12` |
| Transport | the inverter's own LAN port; 6100 answered |
| Battery | third party (Pylontech Force H1), SoC 2.2 % |
| Answered | 232 of 245 fields; 36 of 36 blocks |

## Energy history

The whole block (inputs 6101-6826) answered. Each quantity's 2026 yearly slot equals the sum of
its monthly values exactly: PV 12109.6 kWh, direct consumption 3159.3 kWh, export from PV
6732.6 kWh. November reads this morning's 2.5 kWh. The first non-zero year is 2021. **The 2024
slots are implausible**: 37461.2 kWh of PV and 32834.6 kWh of export in one year from a 10 kW
inverter, where 2025 reads 12550.6 kWh. Unexplained; see [energy history](../concepts/energy-history.md).

Register 32998 reads 2000.

## Capability test

Outcome **3**. See [the capability test](../concepts/capability-test.md).

- Readback: 7 matched (`battery_max_soc`, both battery power limits, 13074, 13052, both start
  powers); `battery_min_soc` and the backup reserve not written, the battery being too close to
  every admissible value.
- [13074](../entities/register-13074.md): the probe was refused three times, **times ten**; 900 W
  went out as raw 900.
- Forced charge: did as it was told (875 W, 1250 W, 805 W).
- **Forced-charging window: could not tell.** Charge power went from 772 W to 4499 W while the
  window was open and fell to -245.5 W after it, so the 1017.5 W drift between before and after
  outweighed the bracket. The rise is the window's doing on any reading; the verdict is the rule's.
- Discharge window: not checked, the battery was charging.
- PV cut: [31211](../entities/register-31211.md) absent on P020.
- Restart: stopped in 2.0 s, Running after 186.5 s, settings survived.
