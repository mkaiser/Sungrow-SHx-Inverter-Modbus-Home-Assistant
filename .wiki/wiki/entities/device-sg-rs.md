---
type: entity
title: SG-RS string inverters
tags: [inverter, sg-rs, sunstone-s, single-phase, string-inverter]
created: '2026-11-04'
---

# SG-RS string inverters

The single-phase PV-only inverters, SG5.0RS and its siblings, on firmware family `SUNSTONE-S`.
Two surveys in the corpus, both [bleughb](installation-bleughb.md)'s SG5.0RS, both through a
[WiNet-S](device-winet-s.md) on WiFi:
[anon-85541281016](../sources/sg5-0rs-1p-bleughb-anon-85541281016-summary.md) and
[anon-91627862515](../sources/sg5-0rs-1p-bleughb-anon-91627862515-summary.md). The map the integration reads is
the protocol document's, `src/sungrow_modbus/string_inverter/registers.py`.

## What is established

- **The type code is `0x2606`**, single phase, unit 1; ARM `ARM_SUNSTONE-S_V11_V01_A`, DSP
  `MDSP_SUNSTONE-S_V11_V01_A` on both. No inverter firmware string was read, so no firmware page.
- **The read block answers through the dongle**: input 4949-5228 and 7012-7031, holding 4999-5048
  (holding 5019 unread), in one round (both surveys).
- **The meter block (input 5083-5104) and the per-string block (7012-7031) read 0**, on machines
  that make 4.6 to 4.8 kW AC. The owner's meter is read by another poller, so the inverter has no
  meter of its own; a zero here says nothing about the capability
  ([zero means absent](../concepts/zero-means-absent.md)).
- **Holding 5006 and 5007 are the power limitation** (switch `0xAA` or `0x55`, then 0.1 % of
  rated power), and the owner writes both on two machines
  ([source](../sources/bleughb-sg-power-limitation-registers-786-summary.md)). Both surveys read the
  limit switched on at 100.0 %. Not watched by this repository: the integration does not write to an SG.
- Two MPPTs carry current; MPPT3 and up read 0.
