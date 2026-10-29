---
type: concept
title: Transport detection
tags: [transport, winet-s, capabilities]
created: '2026-10-29'
---

# Transport detection

Whether a reading came over a cable to the inverter's own LAN port or through
a [WiNet-S](../entities/device-winet-s.md) changes what can be read, so
capability varies by transport as well as by model.

- **Measure it with [register 6100](../entities/register-6100.md)**: it
  answers on a cable and is refused through a dongle.
- **Not with 13265**, which names the fitted module, not the one in the path.
- **Not with round-trip time**, which times the reader's path.
- **WiFi versus Ethernet is not determinable** over Modbus.
  `user_inputs.transport` is the only source.
- The survey's verdict (`connection.verdict`) compares the owner's answer
  with the measurement. Exit 4 means they still disagree, and that document
  is not published until it is settled.

## What differs by transport

| Read | Cable | WiNet-S |
| --- | --- | --- |
| input 2612, 2628 (sub-controller, battery firmware) | answers ([padded](padded-frames.md)) | exception 0x02 |
| input 6100 | answers | refused |
| SBR cells and modules | answer | refused ([SBR](../entities/device-sbr-battery.md)) |
| a wallbox | never | unit 3 ([wallbox](../entities/device-wallbox.md)) |
| a write's readback | current | stale |
| dumped addresses that answer | about 1461 of 1510 | about 1020 |

Which unit ids answer depends on transport too; see
[identify by what answers](identify-by-what-answers.md).
