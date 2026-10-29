---
type: entity
title: WiNet-S communication module
tags: [dongle, winet-s, transport]
created: '2026-10-29'
---

# WiNet-S communication module

Sungrow's WiFi/Ethernet dongle. It plugs into the inverter, forwards Modbus
TCP on port 502, and serves the same Modbus inside TLS on **port 516**. Much of
what a survey sees through it is the dongle's doing, not the inverter's.

## What it changes

| Behaviour | Consequence | Page |
| --- | --- | --- |
| Refuses input **6100** (0x02) | the measurement of transport | [register 6100](register-6100.md) |
| Does not forward inputs **2612** and **2628** (sub-controller and battery firmware) | capability gating by transport, not a `layout.ISOLATE` case | [transport detection](../concepts/transport-detection.md) |
| Answers **an empty string** where the inverter refuses (13249, 13264, 13279) | "the block answered" is not evidence | [zero means absent](../concepts/zero-means-absent.md) |
| Answers **0** where the inverter answers 0xFFFF | invents MPPT3, MPPT4, a second meter channel | [zero means absent](../concepts/zero-means-absent.md) |
| Re-encodes **13000** (cable 0x0040 → 0x0000, 0x0080 → 0x8100) | duplicate running-state codes | [register 13000](register-13000.md) |
| Forwards a write and **reads it back stale**, indefinitely | legs A and B of the control test are not evidence; only leg C survives | [control test](../concepts/control-test.md) |
| Answers **0x04** to reads it answers alone, while other clients poll it ([firetribe](installation-firetribe.md), and reproduced at [gerd](installation-gerd.md)) | 0x04 through a dongle settles nothing, like 0x06 | [busy WiNet-S](../queries/does-a-busy-winet-s-refuse-with-0x04.md) |
| Refuses the SBR's cells and modules blocks | fewer pack fields | [SBR battery](device-sbr-battery.md) |
| Carries a [wallbox](device-wallbox.md) at unit **3** | moving to a cable loses it unless `wallbox_host` is set | [identify by what answers](../concepts/identify-by-what-answers.md) |

A dongle forwards about 1020 of 1510 dumped addresses, where a cable forwards
1461.

## What cannot be learned through it

- **WiFi or Ethernet.** Not determinable over Modbus. `user_inputs.transport`
  in a survey is the only source.
- **Round-trip time** times the path from the reader, usually a VPN. It says
  nothing about the inverter and is not recorded.

## Port 516

Real Modbus behind TLS 1.2. It refuses the same registers as 502, and it
exhausts under rapid reconnects the same way. The certificate is
Sungrow-signed (issuer `OT.SUNGROW`, CN `sun`) and byte-identical to the
wallbox's at the same house, so this TLS authenticates nothing.
`sungrow_survey.py` reports a WiNet-S's 516 without reading it.
