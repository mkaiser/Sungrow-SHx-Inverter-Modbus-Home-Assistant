---
type: entity
title: SG-RS string inverters
tags: [inverter, sg-rs, sunstone-s, single-phase, string-inverter]
created: '2026-11-04'
---

# SG-RS string inverters

The single-phase PV-only inverters, SG5.0RS and its siblings, on firmware family `SUNSTONE-S`.
Two diagnoses in the corpus, both [bleughb](installation-bleughb.md)'s SG5.0RS, both through a
[WiNet-S](device-winet-s.md) on WiFi:
[anon-85541281016](../sources/sg5-0rs-1p-bleughb-anon-85541281016-summary.md) and
[anon-91627862515](../sources/sg5-0rs-1p-bleughb-anon-91627862515-summary.md). The map the integration reads is
the protocol document's, `src/sungrow_modbus/string_inverter/registers.py`.

## What is established

- **The type code is `0x2606`**, single phase, unit 1; ARM `ARM_SUNSTONE-S_V11_V01_A`, DSP
  `MDSP_SUNSTONE-S_V11_V01_A` on both. No inverter firmware string was read, so no firmware page.
- **The read block answers through the dongle**: input 4950-5229 and 7013-7032, holding 5000-5049
  (holding 5020 unread), in one round (both diagnoses).
- **The meter block (input 5083-5104) and the per-string block (7013-7032) read 0**, on machines
  that make 4.6 to 4.8 kW AC. The owner's meter is read by another poller, so the inverter has no
  meter of its own; a zero here says nothing about the capability
  ([zero means absent](../concepts/zero-means-absent.md)).
- **Holding 5007 and 5008 are the power limitation** (switch `0xAA` or `0x55`, then 0.1 % of
  rated power), and the owner writes both on two machines
  ([source](../sources/bleughb-sg-power-limitation-registers-786-summary.md)). Both diagnoses read the
  limit switched on at 100.0 %. Not watched by this repository: the integration does not write to an SG.
  **While the switch is off the inverter resets 5008 to 110 %**, so a writer sets the switch
  first and the limit second, as evcc's template does
  ([evcc cross-reference](../sources/cross-reference-evcc-summary.md)); unmeasured here.
- Two MPPTs carry current; MPPT3 and up read 0.
- **Phases B and C read 0, not the unavailable value**, on a single-phase machine; so do
  MPPT3 to MPPT12. The integration therefore decides by the output type (input 5002) and the
  source's tracker count per model, which says 2 for the SG5.0RS, as measured
  (`SungrowStringInverter.serves`, `src/sungrow_modbus/string_inverter/device.py`).

## What an SG shares with a hybrid, and what not

By the two protocols, as `src/sungrow_modbus/string_inverter/registers.py` maps them:

- **Shared, register for register**: the identity block (input 4950-5002: firmware, serial, type
  code, rated power, output type) and the core PV and AC block, 5003-5035, with MPPT4 at
  5115-5116. Measured on the SG at bleughb; on hybrids throughout the corpus.
- **Not on an SG**: the 13000 block, the battery, the EMS and every hybrid control. The holding
  registers from 5000 mean other things: the clock at 5000-5005 and the power limitation at
  5007-5008, where a hybrid has neither.
- What it answers is in `doc/compatibility.md`, under "String inverters (SG)".
