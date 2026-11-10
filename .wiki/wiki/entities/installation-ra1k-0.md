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
neither was read. The second and third readings name the iHomeManager as another poller of the
inverter. There is no cable reading: the SH20T has no LAN port of its own, the owner says (issue
#772), only the WiNet-S.

- **The first capability test on an SH-T**, 2026-10-30: the forced discharge did as it was told.
- **The PV cut confirmed on P071**, 2026-11-01: total DC power 20421 W, 28 W, 20395 W
  ([third reading](../sources/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-2-summary.md)). The same run restarted the
  inverter (stopped in 2 s, running 147.5 s after the start command).
- **[13074](register-13074.md)'s write scale is not determined** here: at 20000 W no probe word is
  safe, and with feed-in limitation off the dongle reported a written word back as handed, in
  both capability tests.
- Both readings are through the WiNet-S, which refuses 5741-5746, so neither can say whether the
  iHomeManager silences them. A cable reading would.
- **Outcome 5 on 2026-11-10**: the restore of 33209 (`forced_charging_days_raw`, held at 1) was
  refused five times through the WiNet-S, as the check's own write of it had been. Every write
  was of the value it held; whether it landed is not known, and with no LAN port no cable read can
  tell. The same run had forced discharge show nothing measurable against a 13052 the dongle
  reported stale, 33048 refuse a value above its bound, and the restart take 148 s
  ([fourth reading](../sources/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-3-summary.md)).

## Diagnoses

- [SH20T, B000.V000.P071, ra1k_0, a WiNet-S on WiFi](../sources/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-summary.md)
- [SH20T, B000.V000.P071, ra1k_0, a WiNet-S on WiFi, with a capability test](../sources/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-004-005-summary.md)
- [SH20T, B000.V000.P071, ra1k_0, a WiNet-S on WiFi, the PV cut confirmed](../sources/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-2-summary.md)
- [SH20T, B000.V000.P071, ra1k_0, a WiNet-S on WiFi, outcome 5](../sources/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-3-summary.md)
