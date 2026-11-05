---
type: query
title: "What does V1.1.16 call the registers no datasheet here lists?"
tags: [specification, naming, open]
created: '2026-11-05'
query: "Which of the 15 hybrid registers the integration reads, and that neither V1.1.2 nor V1.1.11 lists, does V1.1.16 name, and how?"
results_count: 0
---

# What does V1.1.16 call the registers no datasheet here lists?

**Open.** The integration reads 15 hybrid registers that neither V1.1.2 nor V1.1.11 lists
([the datasheet notes](../sources/sungrow-datasheet-names-2026-11-05-summary.md)):

| Registers | What they are, and from where |
| --- | --- |
| input 2582, 2597, 2613, 2629 | firmware version parts, from the surveys |
| input 4990 | the serial number |
| input 5741-5746 | the meter's phase voltages and currents |
| holding 31211 | [PV generation cut](../entities/register-31211.md), found by watching iSolarCloud |
| holding 31213 | [shutdown at a 0 % power limit](../entities/register-31213.md), the same |
| holding 33149, 33150 | battery charging and discharging start power |

V1.1.16, which `doc/architecture.md` names as the map's reference, is not in the repository. Its
register table answers this for the documented ones; 31211 and 31213 may stay undocumented.
