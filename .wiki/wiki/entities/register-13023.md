---
type: entity
title: Register 13023 (battery level)
tags: [register, input, battery, soc]
created: '2026-11-14'
---

# Register 13023 (battery level)

Input 13023, 0.1 %, is **the battery's charge within the usable window**, between the minimum SoC
(holding 13059) and the maximum SoC (holding 13058):

    battery level = (pack SoC - min SoC) / (max SoC - min SoC) x 100 %

It is **not** the absolute state of charge that iSolarCloud shows. That is the pack's own
(input 10744 on an [SBR](device-sbr-battery.md), `battery_pack.readings.values.state_of_charge` in a
diagnosis). The two agree only when the minimum is 0 % and the maximum 100 %.

- **The maintainer says so, and gerd's readings fit**: 1.5 % at a pack SoC of 11.4 %, minimum 10 %,
  maximum 100 % ([gerd, 2026-11-14](../sources/gerd-battery-level-2026-11-14-summary.md)).
- **The corpus fits too.** In the diagnoses under `device-diagnosis/results/inverter/` that hold
  both values, with a minimum above 0 % or a maximum below 100 % (57 on 2026-11-14), the window
  matches the inverter's figure within 2 points in 48 and within 1 point in 45 (median error
  0.3 points). A plain offset (pack SoC minus minimum) matches within 2 points in only 18. The two
  are read seconds to minutes apart, so a charging or discharging battery accounts for small
  differences.
- **Four pairs miss by more than 5 points, all at [peter-sm](installation-peter-sm.md)**, one with
  the inverter at 0.0 % against the pack at 50.3 %. Why is not established; neither explanation
  fits them.
- **0 % means the battery is at its minimum, not empty.** An inverter reading 0 % has stopped
  discharging; the pack still holds the minimum. For example biergitkraft's SH10T read 0 % at a
  pack SoC of 15 % and a minimum of 15 %
  ([the diagnosis](../sources/sh10t-b001v001p038-3p-biergitkraft-anon-38431301666-battery-sbh100-winet-lan-summary.md)).
- **The figure moves when the window does.** Changing 13058 or 13059 changes 13023 with no change
  in the battery.

The integration's battery level sensor reads this register
(`src/sungrow_modbus/hybrid_inverter/registers.py`, `battery_level`), as the YAML package does; the
SBR's own state of charge is a separate entity where the pack answers.
