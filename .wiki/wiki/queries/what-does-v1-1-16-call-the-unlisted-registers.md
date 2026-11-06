---
type: query
title: "What does V1.1.16 call the registers no datasheet here lists?"
tags: [specification, naming, answered]
created: '2026-11-05'
query: "Which of the 15 hybrid registers the integration reads, and that neither V1.1.2 nor V1.1.11 lists, does V1.1.16 name, and how?"
results_count: 1
---

# What does V1.1.16 call the registers no datasheet here lists?

**Answered: one of the 15, the serial.** V1.1.16 is not available, but V1.1.17
([hybrid protocol V1.1.17](../sources/hybrid-protocol-v1-1-17-summary.md))
differs from it in device types only, so the registers V1.1.17 lists are the
ones V1.1.16 listed.

| Registers | What they are | In V1.1.17 |
| --- | --- | --- |
| input 4990 | the serial number | **yes**: `SN`, 4990-4999, UTF-8 |
| input 2582, 2597, 2613, 2629 | firmware version parts, from the surveys | no; the document's firmware strings are 13250-13294 |
| input 5741-5746 | the meter's phase voltages and currents | no; the meter's phase *power* is 5603/5605/5607 |
| holding 31211 | [PV generation cut](../entities/register-31211.md) | no |
| holding 31213 | [shutdown at a 0 % power limit](../entities/register-31213.md) | no |
| holding 33149, 33150 | battery charging and discharging start power | no; 33148 is "Charging/Discharging Power - Wide range" |

The other fourteen stay named by the surveys and by watching iSolarCloud,
unnamed by Sungrow. Their names on the sheet remain this project's own.
