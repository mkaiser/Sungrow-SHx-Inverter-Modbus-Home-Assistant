---
type: entity
title: Installation ra1k-0
tags: [installation, ra1k-0]
created: '2026-10-29'
---

# Installation ra1k-0

An [SH20T](device-sh-t.md) on [P071](firmware-pearl-h-b000-v000-p071.md) with an
[SBH400](device-sbh-battery.md), through a [WiNet-S](device-winet-s.md) on WiFi. The owner reports an
[iHomeManager](device-ihomemanager.md) and an AC22E-01 [wallbox](device-wallbox.md) installed too;
neither was read. The second reading names the iHomeManager as another poller of the inverter.

- **The first control test on an SH-T**, 2026-10-30: the forced discharge did as it was told.
- **[13074](register-13074.md)'s write scale is not determined** here: at 20000 W no probe word is
  safe, and with feed-in limitation off the dongle reported a written word back as handed.
- Both readings are through the WiNet-S, which refuses 5741-5746, so neither can say whether the
  iHomeManager silences them. A cable reading would.

## Surveys

- [SH20T, B000.V000.P071, ra1k_0, a WiNet-S on WiFi](../sources/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-summary.md)
- [SH20T, B000.V000.P071, ra1k_0, a WiNet-S on WiFi, with a control test](../sources/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-004-005-summary.md)
