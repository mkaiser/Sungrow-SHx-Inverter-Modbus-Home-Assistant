---
type: entity
title: Installation bleughb
tags: [installation, bleughb]
created: '2026-11-02'
---

# Installation bleughb

An AC-coupled [SH10RS](device-sh-rs.md) on [P057](firmware-sunstone-h-b000-v002-p057.md) with an
[SBH250](device-sbh-battery.md) and no PV of its own, through a [WiNet-S](device-winet-s.md) on
WiFi, beside two [SG5.0RS](device-sg-rs.md) string inverters that make the PV, both surveyed from Home
Assistant's diagnostics on 2026-11-04. The hybrid has one reading, with a control test.

- **13074 stores a written word as handed** on P057, the second SH-RS firmware measured, both 1:1.
- The forced checks moved the battery but could not be told from a house that changed by 1.4 to
  1.8 kW, and the PV cut cannot be watched here at all.
- A restart: 4 s to stop, 291 s to run again.
- **The SG5.0RS pair** read through the same WiNet-S kind of link, each with the power limitation
  at holding 5006 and 5007 switched on at 100 %; the owner curtails both during negative prices
  ([note](../sources/bleughb-sg-power-limitation-registers-786-summary.md)).

## Surveys

- [SG5.0RS, anon-85541281016](../sources/sg5-0rs-1p-bleughb-anon-85541281016-summary.md)
- [SG5.0RS, anon-91627862515](../sources/sg5-0rs-1p-bleughb-anon-91627862515-summary.md)
- [SH10RS, B000.V002.P057, bleughb, a WiNet-S on WiFi, with a control test](../sources/sh10rs-b000v002p057-1p-bleughb-anon-92100523190-battery-sungrow-winet-wlan-summary.md)
