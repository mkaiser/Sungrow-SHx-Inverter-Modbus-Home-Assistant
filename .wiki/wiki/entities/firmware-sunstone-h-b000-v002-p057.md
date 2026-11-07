---
type: entity
title: SUNSTONE-H_B000.V002.P057
tags: [firmware, sunstone-h-b000-v002-p057]
created: '2026-11-02'
---

# SUNSTONE-H_B000.V002.P057

[SH-RS](device-sh-rs.md) firmware; version 1 reads `SUNSTONE-H_01011.02.57`. Only read through a
[WiNet-S](device-winet-s.md), at [bleughb](installation-bleughb.md).

- [Register 31211](register-31211.md) answers 0x55; the PV cut is not confirmed here (no PV on
  this AC-coupled inverter), so the switch waits.
- [Register 13074](register-13074.md) **stores a written word as handed**, by the probe's
  acceptance, as on [P065](firmware-sunstone-h-b000-v002-p065.md).
- A restart: stopped in 4 s, running 291 s after the start command.

## Diagnoses

- [SH10RS, B000.V002.P057, bleughb, a WiNet-S on WiFi, with a capability test](../sources/sh10rs-b000v002p057-1p-bleughb-anon-92100523190-battery-sungrow-winet-wlan-summary.md)
