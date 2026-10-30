---
type: entity
title: PEARL-H_B000.V000.P071
tags: [firmware, pearl-h-b000-v000-p071]
created: '2026-10-29'
---

# PEARL-H_B000.V000.P071

[SH-T](device-sh-t.md) firmware. Only read through a [WiNet-S](device-winet-s.md).

- [Register 31211](register-31211.md) answers 0x55. The T also has 13018.
- The write scale of [register 13074](register-13074.md) is **not determined** on this firmware.
  At [ra1k-0](installation-ra1k-0.md) the probe declined to ask (20000 W held, and ten times
  that wraps into range), and with feed-in limitation off the dongle reported a written word
  back as handed, where B001 ignores the write. A lead, through a WiNet-S.
- The forced discharge acts: 1252 W for 1250 W commanded, at [ra1k-0](installation-ra1k-0.md).
- 33149/33150 (battery start power) do not answer.

## Surveys

- [SH15T, B000.V000.P071, FullHD23, a WiNet-S on Ethernet](../sources/sh15t-b000v000p071-3p-fullhd23-anon-08484305020-battery-unknown-winet-lan-summary.md)
- [SH15T, B000.V000.P071, jm493, a WiNet-S on Ethernet](../sources/sh15t-b000v000p071-3p-jm493-anon-00578206904-battery-sbh200-winet-lan-summary.md)
- [SH20T, B000.V000.P071, ra1k_0, a WiNet-S on WiFi](../sources/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-summary.md)
- [SH20T, B000.V000.P071, ra1k_0, a WiNet-S on WiFi, with a control test](../sources/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-004-005-summary.md)
