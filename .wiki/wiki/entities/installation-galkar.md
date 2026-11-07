---
type: entity
title: Installation GalKar
tags: [installation, galkar]
created: '2026-10-31'
---

# Installation GalKar

An [SH15T](device-sh-t.md) on [P071](firmware-pearl-h-b000-v000-p071.md) with an
[SBH](device-sbh-battery.md) pack, through a [WiNet-S](device-winet-s.md) on Ethernet. One reading,
with a capability test, sent as a Home Assistant diagnostics download.

- **The first forced charge and the first restart watched on an SH-T**: the forced charge did as
  it was told (1248 W for 1250 W), and the inverter stopped in 2 s and ran again 145 s after the
  start command.
- **The dongle answered like a busy one**: four holding blocks came and went with 0x04, the four
  power controls' writes were refused, and so was the read of
  [13074](register-13074.md), whose write scale stays undetermined on P071.
- **33149-33150 answered once**, where the capability table and [ra1k-0](installation-ra1k-0.md)'s
  run say the SH-T has no battery start power. Not settled through a dongle.

## Diagnoses

- [SH15T, B000.V000.P071, GalKar, a WiNet-S on Ethernet, with a capability test](../sources/sh15t-b000v000p071-3p-galkar-anon-30195315022-battery-sbh150-winet-lan-summary.md)
