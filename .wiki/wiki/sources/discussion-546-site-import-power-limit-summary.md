---
type: source
title: discussion-546-site-import-power-limit.md
source_path: raw/discussion-546-site-import-power-limit.md
ingested: '2026-11-07'
created: '2026-11-07'
tags: [register-32998, import-limit, sh-rs, sh-rt, write, jam3s97, korsberg, ulfben]
---

# Site import power limit, register 32998 (discussion #546)

`.wiki/raw/discussion-546-site-import-power-limit.md`: three owners on the undocumented holding
[register 32998](../entities/register-32998.md), which iSolarCloud calls "Site import power limit".

| Claim | Evidence | Status |
| --- | --- | --- |
| The unit is 0.01 kW: 1300 is 13.00 kW | [Jam3s97](../entities/installation-jam3s97.md) wrote 1300, read 1300, and the meter held a 13.00 kW cap; Korsberg's YAML reads 9.5 kW where a [peter-sm](../entities/installation-peter-sm.md) dump holds 950; ulfben reads 11.00 kW | three owners agree; one write watched at the meter, not by this repository |
| On an [SH10RS](../entities/device-sh-rs.md) the inverter holds grid import to the cap | Jam3s97: median 11,977 W for 43 min at 12.00 kW, 12,924 W for 16 min at 13.00 kW, overshoots of 563 W and 258 W gone by the next ~10 s sample | the owner's meter trace, through a WiNet-S and over RS485 alike |
| The device refuses a write above 5000 (50.00 kW) with an exception, and accepts 5000 | Jam3s97's boundary writes | one SH10RS; iSolarCloud shows [0.01, 50.00] there and on ulfben's SH10RT-V112 |
| On ulfben's [SH10RT-V112](../entities/device-sh-rt.md) the limit does not hold during a forced charge: the battery charges at full power | ulfben, before and after an update to ARM 95.14, battery 01.30, WiNet-S P045 | the owner's report, no meter trace; [open](../queries/does-the-import-limit-hold-during-a-forced-charge.md) |

ulfben's "95.14" is the version register 2582 carries (`SAPPHIRE-H_01011.95.14`); the thread does not
give register 13250, so which B001 firmware it pairs with is not on record here. In this corpus
`01011.95.14` sits beside [P023](../entities/firmware-sapphire-h-b001-v000-p023.md)
(`src/sungrow_modbus/hybrid_inverter/capabilities.py`).

**No write has been watched by this repository**, so nothing here enters `CONFIRMED_ON_FIRMWARE`
([firmware gating](../concepts/firmware-gating.md)), and the integration does not read the register.
