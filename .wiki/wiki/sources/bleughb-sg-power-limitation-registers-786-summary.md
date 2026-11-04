---
type: source
title: bleughb-sg-power-limitation-registers-786.md
source_path: raw/bleughb-sg-power-limitation-registers-786.md
ingested: '2026-11-04'
created: '2026-11-04'
tags: [string-inverter, sg5-0rs, bleughb, power-limitation, write]
---

# SG power limitation, holding 5006 and 5007 (issue #786)

`.wiki/raw/bleughb-sg-power-limitation-registers-786.md`: how [bleughb](../entities/installation-bleughb.md)
curtails two [SG5.0RS](../entities/device-sg-rs.md) during negative feed-in prices, with the
built-in `modbus` integration. The note gives protocol addresses; the register numbers are one higher.

| Claim | Evidence | Status |
| --- | --- | --- |
| Register 5007 is the power-limitation switch: 170 (`0xAA`) on, 85 (`0x55`) off | the owner writes it, reads 170 back | the owner's; the survey reads 170 on both machines |
| Register 5008 is the setting, 0.1 %, 0-1000 of rated power; 45 % is written 450 | the owner writes it every ~30 s; 1000 reads back | the survey reads 1000 on both |
| Write 170, wait 1-2 s, then the setting | the owner's automation | not watched here |
| The limit applies to AC output as a share of the 5 kW rating | the owner's report | not measured: nothing here saw the output move |
| Register 5011 is the export limit value, 500 | read back | the survey reads 500 at 5010 |

Where the note and a survey differ: the note lists register 5039 as "5" and the surveys read 50
(protocol 5038, holding), which fits 5.0 kW at 0.1 kW; the survey is the evidence.

**No write has been watched by this repository**, so nothing here enters `CONFIRMED_ON_FIRMWARE`
([firmware gating](../concepts/firmware-gating.md)), and the integration stays read only on an SG.
The note's firmware is the placeholder `<FIRMWARE>`; the surveys carry the ARM and DSP names only.
