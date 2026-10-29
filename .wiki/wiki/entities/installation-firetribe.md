---
type: entity
title: Installation firetribe
tags: [installation, firetribe]
created: '2026-10-29'
---

# Installation firetribe

An [SH6.0RT-V112](device-sh-rt.md) on [P023](firmware-sapphire-h-b001-v000-p023.md) with an
[SBR096](device-sbr-battery.md), read from Home Assistant on the cable and through the
[WiNet-S](device-winet-s.md) on Ethernet, issue #784. Both paths are in use at once: a
WARP3 wallbox and a second Home Assistant poll the WiNet-S, and this Home Assistant the
inverter's own port. Each path was surveyed twice; the second reading, with a control
test, is the committed one.

## Surveys

- [SH6.0RT-V112, B001.V000.P023, firetribe, the inverter's own LAN port](../sources/sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-meter-direct-lan-summary.md)
- [SH6.0RT-V112, B001.V000.P023, firetribe, a WiNet-S on Ethernet](../sources/sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-winet-lan-summary.md)

## What it shows

- The first SH6.0RT-V112 in the corpus: every block answers on the cable.
- Through the busy WiNet-S, holding reads and control writes were refused with
  **0x04** in some attempts, while the forced charge was obeyed: a busy
  dongle's 0x04, reproduced at gerd. See
  [busy WiNet-S](../queries/does-a-busy-winet-s-refuse-with-0x04.md).
