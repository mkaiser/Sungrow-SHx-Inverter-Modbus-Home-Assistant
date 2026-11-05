---
type: query
title: "Do models on one firmware answer alike?"
tags: [firmware, capability, answered]
created: '2026-11-05'
query: "Do inverters of one platform on the same firmware version answer the same registers, whatever the model?"
results_count: 5
---

# Do models on one firmware answer alike?

**Answered, so far: yes.** `doc/firmware_support.md` pools every survey by
platform and firmware, split by link, and replays each one's register dump
through the integration's decoding and capability probe
(`scripts/generate/generate_firmware_support.py`). No cell is split: wherever
two models on one firmware were both surveyed, they answered every inverter
entity's registers alike, once what a house has fitted is set aside.

Five columns pool more than one model, and only these test the question:

| Platform, firmware, link | Models |
| --- | --- |
| [SAPPHIRE-H P020](../entities/firmware-sapphire-h-b001-v000-p020.md), direct | SH10RT, SH10RT-V112 |
| [SAPPHIRE-H P022](../entities/firmware-sapphire-h-b001-v000-p022.md), direct | SH6.0RT-20, SH8.0RT-V112 |
| [SAPPHIRE-H P023](../entities/firmware-sapphire-h-b001-v000-p023.md), direct | SH10RT-20, SH10RT-V112, SH5.0RT-V112, SH6.0RT-V112 |
| [SAPPHIRE-H P023](../entities/firmware-sapphire-h-b001-v000-p023.md), WiNet-S | the same four |
| [PEARL-H P071](../entities/firmware-pearl-h-b000-v000-p071.md), WiNet-S | SH15T, SH20T |

What does move is the firmware, within one platform and one link: the PV cut
at [register 31211](../entities/register-31211.md) is absent on P020 and
present from P022, and
[01011.95.03](../entities/firmware-sapphire-h-01011-95-03.md) lacks the
firmware block, as `ABSENT_ON_FIRMWARE` in
`src/sungrow_modbus/hybrid_inverter/capabilities.py` already records.

**Still open:** the SUNSTONE-H firmware seen so far each have one model
(SH6.0RS on P068, SH10RS on P059, P065 and P067), and every SH-RS and SH-T
reading went through a WiNet-S. A second model on one of those firmware, or
any of them over a cable, would test it there.

What the method cannot see is listed on the page: an address no dump reached
is untested; a register that reports a part the house lacks (a meter, a
Sungrow pack, a communication module) is *not fitted*; and the masked serial
and the padded strings at 2613 and 2629 ([padded
frames](../concepts/padded-frames.md)) are untested by construction.
