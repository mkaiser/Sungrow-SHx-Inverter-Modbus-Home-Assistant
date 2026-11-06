---
type: source
title: cross-reference-shcshc76.md
source_path: raw/cross-reference-shcshc76.md
ingested: '2026-11-06'
created: '2026-11-06'
tags: [cross-reference, wallbox, winet-s, licences]
---

# Cross-reference: shcshc76/sungrow and Eisbaeeer/sungrow

`raw/cross-reference-shcshc76.md` reads an ioBroker user's AC011E-01 tables
a second time. `Eisbaeeer/sungrow`, which `doc/wallbox_registers.md`
already cited, is a fork of `shcshc76/sungrow` with the same files. Neither
has a licence: a lead, never a definition.

| | Register | Value |
| --- | --- | --- |
| Agrees | 21203, 21204, 21211, 21212, 21225-21232, 21262, 21300-21320 | names, scales, codes and the start/stop polarity |
| Differs | 21263 | a working mode there, the rated current (320) here |
| Names | 21267 | "holding register changed" |
| Names | 21268 | charger enable, 0/1 |
| Odd | holding 21201 | "total energy", likely a copied row |

- **Its addresses are protocol addresses**: the ioBroker adapter's
  `_address` column, one below every register number here.
- **It adds one operating claim**: a WiNet-S faults when the wallbox behind
  it is polled faster than every 10 s. See [wallbox](../entities/device-wallbox.md).
