---
type: source
title: sh80rt-v112-b001v000p023-3p-tristangrichard-anon-04477133025-battery-sbr096-meter-direct-lan.json
source_path: ../device-diagnosis/results/inverter/sh80rt-v112-b001v000p023-3p-tristangrichard-anon-04477133025-battery-sbr096-meter-direct-lan.json
ingested: '2026-11-13'
created: '2026-11-13'
tags:
  - diagnosis
  - sh80rt-v112
  - sapphire-h-b001-v000-p023
  - tristangrichard
  - direct_lan
---

# SH8.0RT-V112, B001.V000.P023, tristangrichard, the inverter's own LAN port

Read 2026-11-13 at 06:01 UTC with the terminal diagnosis (`sungrow_diagnosis.py`, read only),
posted by tristangrichard to issue #786. The first SH8.0RT-V112 on P023 in the corpus. Committed
unchanged. Source:
`device-diagnosis/results/inverter/sh80rt-v112-b001v000p023-3p-tristangrichard-anon-04477133025-battery-sbr096-meter-direct-lan.json`.

| | |
| --- | --- |
| Installation | [tristangrichard](../entities/installation-tristangrichard.md) |
| Model | [SH8.0RT-V112](../entities/device-sh-rt.md), type code `0x0E0E` |
| Stand-in serial | `anon-04477133025` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| Communication module firmware | `WINET-SV200.001.00.P045` |
| Transport (owner) | the inverter's own LAN port; no other poller, no proxy |
| Transport (measured) | direct to the inverter's LAN port, with a communication module fitted as well but not in the path; register 6100 answered |
| Battery | [SBR096](../entities/device-sbr-battery.md) by its three modules (not named by the owner), firmware `SBRBCU-S_22011.01.30` |
| At the time | before dawn: PV 0 W, SoC 26.7 %, load 662 W, the battery discharging 789 W |

Every component answered, and the block read test answered all 37 blocks in both rounds with no
reconnect. The `connection` block counts **12 link drops** over the whole run, outside the block
read test; the document does not say where they fell. Every control reads as *readable*: nothing
wrote.
