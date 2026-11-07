---
type: query
title: "What do the registers only V1.1.17 lists read?"
tags: [specification, hybrid, drm, ems, answered]
created: '2026-11-06'
query: "Do 31222, 13043 and 13080, which the hybrid map does not read but V1.1.17 lists, read anything worth an entity on the diagnoses already committed?"
results_count: 3
---

# What do the registers only V1.1.17 lists read?

**Answered from the diagnoses already on file, without a new one.** The hybrid
diagnosis's register dump reads all three
(`src/sungrow_modbus/dump.py`), so every inverter document in
`device-diagnosis/results/inverter/` holds their words. The registers are named
by [Sungrow's hybrid protocol V1.1.17](../sources/hybrid-protocol-v1-1-17-summary.md).

| Register | Document | What the diagnoses read | Entity? |
| --- | --- | --- | --- |
| holding **31222** | Feed-in limitation value, wide range, 0.01 kW | **Exactly a tenth of 13074 on all 46 diagnoses that read both** (13074 = 10000 W, 31222 = 1000) | no: the same limit in a finer unit, which only matters above 65.5 kW, where 13074's 16 bits in watts run out |
| input **13043** | DRM state, 1-9 is DRM0-DRM8, anything else invalid | **255 on 26 diagnoses, 0 on 22**; never 1-9 | no: no house uses a demand response enabling device, so it reads "invalid" everywhere |
| holding **13080** | External EMS heartbeat, 0-1000 s, "default 20 s" | **0 on 42 diagnoses**; 330 on an SH10RS (P059) and an SH15T (P071), both with EMS mode 0; **875, then 961** on an SH20T (P071) in EMS mode 3 with the meter detection off, in two diagnoses | **open**, below |

## 13080 is not what its name says

A heartbeat setting with a 20 s default would read 20, or 0 where unused.
Three things are read instead: a constant 330 on two houses in EMS mode 0, and a
number that moved from 875 to 961 between two diagnoses at the house with an
iHomeManager. Neither fits a fixed timeout, and the second fits something that
counts. The document gives no unit for a count, so what it is stays open; a
read of the register on the SH20T twice, a minute apart, would say whether it
counts seconds.

Until then nothing in the integration reads or writes it; the document lists
it as read-write.
