---
type: entity
title: SBR battery
tags: [battery, sbr, sub-device]
created: '2026-10-29'
---

# SBR battery

Sungrow's modular low-voltage pack for the [SH-RT](device-sh-rt.md): SBR096,
SBR128 and SBR160 in this corpus. In the integration it is a **device of its
own**, with 40 fields in three components (`src/sungrow_modbus/battery/`).
It is hung off the inverter with `via_device` and identified by the
inverter's serial, because it reports no usable serial of its own.

## How it is reached

| Path | Unit |
| --- | --- |
| the inverter's own LAN port | **200** |
| through a [WiNet-S](device-winet-s.md) | **2** |

Sub-devices are found again whenever an entry's endpoint changes, so moving
between cable and dongle keeps the pack. See
[identify by what answers](../concepts/identify-by-what-answers.md).

## Its write bounds

Once a pack answers on its own unit and register 5639's capacity names an
SBR model, the inverter is granted `Capability.SUNGROW_BATTERY`
(`inverter.capabilities.with_sungrow_battery`, held by
`tests/test_capabilities.py`). The battery's power controls then take the
datasheet's conservative power for that model (`battery/power.py`) instead of
BMS current times voltage. The integration and the control test grant it the
same way. An [SBH](device-sbh-battery.md) is not granted yet.

## What a dongle does not forward

Through a WiNet-S, the **cells** and **modules** components
(`sbr_battery_cells`, `sbr_battery_modules`) are refused with
`IllegalDataAddressError`. The summary block (current, state of charge,
health, temperature, totals, voltage) answers. Every SBR survey shows
this. The cable path to the same pack reads all three, for example
[gerd](installation-gerd.md) on both paths.

The battery firmware string (input 2628) is not forwarded either; see
[transport detection](../concepts/transport-detection.md).
