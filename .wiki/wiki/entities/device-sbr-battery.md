---
type: entity
title: SBR battery
tags: [battery, sbr, sub-device]
created: '2026-10-29'
---

# SBR battery

Sungrow's modular low-voltage pack for the [SH-RT](device-sh-rt.md): SBR096 to SBR256 in this
corpus, three to eight modules. In the integration it is a **device of its
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
(`hybrid_inverter.capabilities.with_sungrow_battery`, held by
`tests/test_capabilities.py`). The battery's power controls then take the
datasheet's conservative power for that model (`battery/power.py`) instead of
BMS current times voltage. The integration and the capability test grant it the
same way. An [SBH](device-sbh-battery.md) is not granted yet.

## What a dongle does not forward

Through a WiNet-S, the **cells** and **modules** components
(`sbr_battery_cells`, `sbr_battery_modules`) are refused with
`IllegalDataAddressError`. The summary block (current, state of charge,
health, temperature, totals, voltage) answers. Every SBR diagnosis shows
this. The cable path to the same pack reads all three, for example
[gerd](installation-gerd.md) on both paths.

The battery firmware string (input 2628) is not forwarded either; see
[transport detection](../concepts/transport-detection.md).

## Position words

The four position fields pack a module and a cell into one word,
`(module << 8) | cell` (`src/sungrow_modbus/battery/registers.py`): high bytes
1 to 3 on gerd's three-module SBR096, and up to 4 (`0x401`) on
[sisu70's four-module SBR128](../sources/sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-meter-direct-lan-summary.md), and up to 7 (`0x703`) on
[a seven-module SBR224](../sources/sh10rt-v112-b001v000p023-3p-anonymous-anon-40315531061-battery-sbr224-meter-direct-lan-summary.md),
and all eight on [robbensonmio's SBR256](installation-robbensonmio.md), all over the cable.
`cell_type_module_n` is non-zero for each fitted module and 0 for an empty slot (three at [mahagon](installation-mahagon.md), four at sisu70,
five on peter-sm's SBR160, seven on the SBR224, eight on the SBR256). The value itself varies:
66, 68, 75 or 76 on most packs, 1 on the SBR256 (BCU `SBRBCU-S_22011.01.27`) and on mahagon's SBR096 (BCU `SBRBCU-S_22011.01.21`), so it is not a
presence flag with one meaning.

## Per-module cell extremes

Registers 10765-10772 are each module's **highest** cell and 10773-10780 each module's
**lowest**, not sixteen single cells (`max_cell_voltage_module_n`, `min_cell_voltage_module_n`).
The owner of the SBR256 showed it in 7 of 7 samples
([issue #788](../sources/robbensonmio-sbr-cell-registers-788-summary.md)), and every cable SBR
reading in the corpus agrees: the pack's highest cell equals the module word of the module its
position names, and likewise the lowest (`tests/test_sbr_pack.py` holds it to the corpus). So the
pack-wide spread is the pack's highest cell less its lowest, which the integration shows as **Cell
voltage spread** in mV (`SbrBatteryCells.cell_voltage_spread`). Each fitted module's own highest
and lowest cell are diagnostic entities, disabled by default, created only for the modules
`SbrBatteryModules.fitted_modules` names: those whose cell type is non-zero, which on every cable
reading are exactly the modules that read a voltage (`tests/test_sbr_pack.py`). The block is
polled only while one of them is enabled. Per-module serials at 10822-10885 read NUL bytes on the SBR256.
