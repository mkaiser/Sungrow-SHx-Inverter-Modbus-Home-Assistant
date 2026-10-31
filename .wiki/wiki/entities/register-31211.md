---
type: entity
title: Register 31211 (PV generation cut)
tags: [register, holding, pv-cut, firmware-gated, undocumented]
created: '2026-10-29'
---

# Register 31211 (PV generation cut)

Holding register 31211 stops PV production when written `0xAA`, and `0x55`
lets PV run again. **It is not in Sungrow's protocol document**: it was found
by watching what iSolarCloud writes.

## Where it answers

By the committed register dumps (asserted in `tests/test_pv_generation_cut.py`):

| Inverter firmware (13250) | 31211 |
| --- | --- |
| [B001.V000.P020](firmware-sapphire-h-b001-v000-p020.md) | 0xFFFF |
| 13250 refused, 2582 = [01011.95.03](firmware-sapphire-h-01011-95-03.md) | 0xFFFF |
| [B001.V000.P022](firmware-sapphire-h-b001-v000-p022.md) | 0x55 |
| [B001.V000.P023](firmware-sapphire-h-b001-v000-p023.md) | 0x55 |
| [PEARL-H_B000.V000.P071](firmware-pearl-h-b000-v000-p071.md) | 0x55 |

The same two inverters at [fwitten](installation-fwitten.md) answer the
sentinel on 95.03 and 0x55 on P023, so the firmware decides. The string that
decides is 13250, not 2582.

## In the integration

| What the device shows | Entity |
| --- | --- |
| 0xFFFF, 0, or anything but 0x55/0xAA | none |
| 0x55 or 0xAA | binary sensor **PV generation cut** |
| ...and its firmware is in `CONFIRMED_ON_FIRMWARE` | switch **Cut PV generation** |

`CONFIRMED_ON_FIRMWARE` holds P022 and P023, each confirmed by a control test
over the inverter's own LAN port: P023 on fwitten's master (1213 W, 0 W,
1199 W), P022 on [gerd's](installation-gerd.md) SH8.0RT-V112 (2938 W, 0 W,
1913 W; [the survey](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-summary.md)). See [firmware gating](../concepts/firmware-gating.md).

**The cut is a ramp.** After `0xAA`, DC power holds for about 6 s and reaches
0 W about 20 s after the write. After `0x55` it returns about 8 s later and is
full within about 20 s. `PV_CUT_SETTLE` (35 s) waits out the ramp.

What is still open is in `Todo.md`; the question is [does the PV cut work on P022 and P071](../queries/does-the-pv-cut-work-on-p022-and-p071.md).
