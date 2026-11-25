---
type: source
title: sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-meter-direct-lan-2.json
source_path: ../device-diagnosis/results/inverter/sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-meter-direct-lan-2.json
ingested: '2026-11-25'
created: '2026-11-25'
tags:
  - diagnosis
  - sh6.0rt-v112
  - sapphire-h-b001-v000-p023
  - firetribe
  - direct_lan
  - proxy
  - capability-test
---

# SH6.0RT-V112, B001.V000.P023, firetribe, through a Modbus proxy, second cable reading

Read 2026-11-25 at 10:13 UTC from Home Assistant (schema 29), with a capability test ended at 10:31 UTC, posted to
issue #786. Source: `device-diagnosis/results/inverter/sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-meter-direct-lan-2.json`.
The [first cable reading](sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-meter-direct-lan-summary.md)
had no test: the inverter was starting.

| | |
| --- | --- |
| Installation | [firetribe](../entities/installation-firetribe.md) |
| Model | [SH6.0RT-V112](../entities/device-sh-rt.md), type code `0x0E0D`, 6000 W rated |
| Stand-in serial | `anon-56336064800` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md), version 1 `SAPPHIRE-H_01011.95.14` |
| Battery | [SBR096](../entities/device-sbr-battery.md), three modules at unit 200, 9.6 kWh, SoH 97 % |
| Communication module | `WINET-SV200.001.00.P044`, fitted but not in the path |
| Transport (owner) | the inverter's own LAN port, through a Modbus proxy |
| Transport (measured) | direct to the inverter's LAN port; register 6100 answered |
| Other pollers (owner) | a second Home Assistant with the YAML package, and the wallbox |
| Cluster mode | [33500](../entities/register-33500.md) reads 0x55, 33501 reads 160, 33502 reads 2: a lone inverter |
| At the time | 1114 W of PV, 1820 W of load, SoC 8.8 %, backup mode on with a 10 % reserve |

Every component answered; all 39 blocks answered in the block read test, none intermittent and no reconnects.

## 13074 multiplies by ten, not by 0.1 % of the rating

The probe wrote the held 7380 back and was refused 0x04 three times: the firmware multiplies. The run then wrote
**word 60 for 600 W, and 600 read back**, and a second point gave the same slope. At 6000 W rated, 0.1 % of the rating
per count would have read 360, so the factor is **10 W per count**
([register 13074](../entities/register-13074.md)). The first `.95.14` inverter that is not 10 kW to tell the two
apart. It is a readback; the export limit's effect was not watched, since there was too little export to cap.

## Capability test (outcome 3)

- **Eight of nine readbacks matched.** The backup reserve was not written: every admissible value is too close to 8.8 %.
- **PV cut** ([31211](../entities/register-31211.md)): 1121, 0, 1119 W.
- **Discharge windows**: 958.5, 0, 993.5 W, the first on P023 and the first with an SBR.
- **Forced-charging window**: 0 W, 5394 W, then -969 W (discharging).
- **Site import limit** ([32998](../entities/register-32998.md)): a 1600 W cap took import 2217.5 → 1677 → 2223.5 W,
  **with backup mode on**. 0 and 5001 refused with 0x04, 5000 taken.
- **EMS modes** 2, 3 and 4 taken. Backup mode, load control and the weekend enable took their own words;
  the second charge window read back.
- **Upper bounds**: 13058 refuses 101 % with 0x04; 33047, 33048, 13052 store 4960 W and 33149, 33150 store 1010 W,
  above the run's maxima.
- **Restart**: stopped in 2.0 s, running after 282.6 s, generating 2.0 s later, settings survived.
- **Restored**: five registers written back on the first attempt, 41 already original.
- **Not measured**: the charge ceiling (battery too low), the export limit's effect, both start thresholds, the upper
  bound of 13059.

## The forced charge was not a measurement

The battery was **already charging at 5244 W** before the 1250 W forced charge, 5303 W during and 5339 W after, then
5358 W before the forced discharge and 0 W during and after. The run commanded none of that charge; what did is not
known. The document records "nothing measurable happened" for the forced charge, which ranks as established and so is
not asked again, and it says nothing about whether the inverter obeys. In the import limit check, later in the same run,
import stood at 2217.5 W under a forced charge and followed the cap.

The charge reached 5394 W, above the 4860 W the run takes as this pack's maximum.

## Energy history

PV's yearly slots add up to 28607.6 kWh against a lifetime 22028.5, export's to 18913.5 against 12334.3: the same 6579.1
and 6579.2 kWh too many. Direct consumption agrees to 0.1 kWh ([energy history](../concepts/energy-history.md)).
