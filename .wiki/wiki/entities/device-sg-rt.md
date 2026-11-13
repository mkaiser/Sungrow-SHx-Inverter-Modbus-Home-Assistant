---
type: entity
title: SG-RT string inverters
tags: [inverter, sg-rt, beryl-s, three-phase, string-inverter]
created: '2026-11-13'
---

# SG-RT string inverters

The three-phase PV-only inverters, SG10RT and its siblings, on firmware family `BERYL-S`. One
diagnosis in the corpus: an anonymous SG10RT on its own [WiNet-S](device-winet-s.md)
([anon-05631532143](../sources/sg10rt-3p-anonymous-anon-05631532143-summary.md)). The map the
integration reads is the protocol document's, `src/sungrow_modbus/string_inverter/registers.py`,
the same as for the [SG-RS](device-sg-rs.md).

## What is established

- **The SG10RT's type code is `0x2433`**, three phase 3P4L, unit 1; ARM `LCD_BERYL-S_V11_V01_A`,
  DSP `MDSP_BERYL-S_V11_V01_A`. No inverter firmware string was read, so no firmware page.
- **The read block answers through the dongle** as on the SG-RS: input 4950-5229 and 7013-7032,
  holding 5000-5049 (holding 5020 unread), with the serial blanked.
- **Two MPPTs carry voltage**; MPPT3 to MPPT12 read 0, which matches the tracker count the
  integration holds for the model.
- **Holding 5007 / 5008 read `0xAA` / 100.0 %**, the power limitation switched on at full power,
  as on the SG-RS.
- **The meter block reads 0**, and says nothing about a meter
  ([zero means absent](../concepts/zero-means-absent.md)).

Read at dusk with 0 A on every MPPT and phase: nothing yet shows how the currents or the
per-string block (7013-7032) read under load. A daylight reading is offered.
