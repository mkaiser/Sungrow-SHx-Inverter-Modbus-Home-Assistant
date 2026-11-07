---
type: source
title: issue-554-active-power-limit-registers.md
source_path: raw/issue-554-active-power-limit-registers.md
ingested: '2026-11-05'
created: '2026-11-05'
tags: [issue, active-power-limit, register-31213, undocumented, isolarcloud]
---

# The active power limit registers iSolarCloud writes (issue #554)

`.wiki/raw/issue-554-active-power-limit-registers.md`: what theunknown86 found by watching
iSolarCloud on their two SH15T ([SH-T](../entities/device-sh-t.md)), while asking for a way to stop
PV production at negative prices.

| Claim | Evidence | Status |
| --- | --- | --- |
| Holding 13089/13090 (documented) read 0xFFFF on 95.01 and on two SH15T | Gnarfoz and theunknown86 read them | the reporters'; firmware of the SH15T not given |
| iSolarCloud's active power limit is holding 31204 (0xAA on, 0x55 off) and 31205 (ratio, 0.1 %) | watched iSolarCloud write them | not adopted: [the cross-reference](cross-reference-modbus-manager-summary.md) settles on 13089/13090 |
| Holding 31213 is "Shutdown at active power limit ratio of 0%", 0xAA on, 0x55 off | the inverter shut down at a 0 % limit, then the register was found | see [register 31213](../entities/register-31213.md); nobody here has written it |
| The active power gradient control makes a new limit take minutes | the reporter's observation | not measured here |

**No write has been watched by this repository.** The register's meaning is the reporter's, and
the diagnoses' values for it are on the register page.
