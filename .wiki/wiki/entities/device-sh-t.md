---
type: entity
title: SH-T hybrid inverters
tags: [inverter, sh-t, pearl-h, three-phase]
created: '2026-10-29'
---

# SH-T hybrid inverters

The larger three-phase hybrids: SH15T and SH20T in this corpus, on firmware
family `PEARL-H`, here always [`PEARL-H_B000.V000.P071`](firmware-pearl-h-b000-v000-p071.md).
They pair with the [SBH](device-sbh-battery.md) high-voltage battery.

## What is established

- **Only read through a WiNet-S.** No T-series survey was taken at an
  inverter's own LAN port, so nothing here separates the machine from the
  [dongle](device-winet-s.md). ra1k-0's owner says the SH20T has no LAN port of its own
  (issue #772).
- **31211 answers 0x55** on P071, as on SH-RT P022/P023, and **the PV cut acts**: 20421 W,
  28 W, 20395 W at [ra1k-0](installation-ra1k-0.md), through a WiNet-S; see
  [register 31211](register-31211.md). The T also has 13018, which is unwritten.
- **Three control tests**, two at [ra1k-0](installation-ra1k-0.md) and one at
  [GalKar](installation-galkar.md), all through a WiNet-S, so only their behavioural legs are
  evidence: the forced discharge did as it was told (1252 W and 1245.5 W for 1250 W), and so did
  the forced charge (1248 W for 1250 W) and the PV cut. Two restarts: stopped in 2 s, running
  145 s (GalKar) and 147.5 s (ra1k-0) after the start command. Its readbacks matched the specification except [13074](register-13074.md), whose
  write scale is not determined on P071. Everything else about writes on this family is
  carried over from SH-RT, not measured.

## Version strings are their own series

Version 1 on the T reads `PEARL-H_01011.01.45` (ra1k-0 and jm493), where every
SH-RT reads `SAPPHIRE-H_01011.95.xx`. The platform is part of the string and
the numbering restarts with it, so `.01.45` is not older than `.95.03`.
Anything gated on Version 1 matches the whole string, platform included, and
never compares the numeric tail across platforms.

## Surveys

[fullhd23](installation-fullhd23.md), [GalKar](installation-galkar.md),
[jm493](installation-jm493.md) and [ra1k-0](installation-ra1k-0.md), all through a WiNet-S.
