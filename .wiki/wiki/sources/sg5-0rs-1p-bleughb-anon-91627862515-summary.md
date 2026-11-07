---
type: source
title: sg5-0rs-1p-bleughb-anon-91627862515.json
source_path: ../device-diagnosis/results/string_inverter/sg5-0rs-1p-bleughb-anon-91627862515.json
ingested: '2026-11-04'
created: '2026-11-04'
tags: [diagnosis, string-inverter, sg5-0rs, bleughb, winet_wlan]
---

# SG5.0RS, bleughb, "North", a WiNet-S on WiFi

The second SG5.0RS at [bleughb](../entities/installation-bleughb.md), read two minutes before
the [first](sg5-0rs-1p-bleughb-anon-85541281016-summary.md), from the same kind of diagnostics
download (issue #786, 2026-11-04). The owner names the other as "SG50.RS".

| | |
| --- | --- |
| Model | [SG5.0RS](../entities/device-sg-rs.md), type code `0x2606`, single phase |
| Stand-in serial | `anon-91627862515` |
| ARM / DSP firmware | `ARM_SUNSTONE-S_V11_V01_A` / `MDSP_SUNSTONE-S_V11_V01_A`, the same as its pair |
| Transport | a WiNet-S on WiFi, unit 1, port 502; the pair is another inverter |
| Read at | 4631 W on AC, 5020 W on DC, work state 0 (run) |

## What answered

The same blocks as its pair: input 4950-5229 and 7013-7032, holding 5000-5049, with 5020
unread. The two machines' holding words agree except the clock, 5004 and 5005. 5007 reads 170 and
5008 reads 1000, 5010 reads 85, 5011 reads 500. The meter block and the per-string block read 0, as on the
first.

Its total generation is 27196 kWh and its running time 14645 h, against 21826 kWh and 13797 h on
the first.
