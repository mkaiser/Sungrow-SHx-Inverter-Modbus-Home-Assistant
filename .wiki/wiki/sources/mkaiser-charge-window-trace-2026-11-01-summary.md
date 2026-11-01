---
type: source
title: mkaiser-charge-window-trace-2026-11-01.md
source_path: raw/mkaiser-charge-window-trace-2026-11-01.md
ingested: '2026-11-01'
created: '2026-11-01'
tags: [control-test, charge-window, mkaiser, sapphire-h-b001-v000-p020]
---

# The maintainer's SH10RT: a forced-charging window, sampled every 2 s

`.wiki/raw/mkaiser-charge-window-trace-2026-11-01.md`: two runs of the control test's charge
window check alone at [mkaiser](../entities/installation-mkaiser.md), on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md), over the inverter's own LAN port,
Home Assistant stopped, every sample and write logged with its time.

| Fact | Evidence |
| --- | --- |
| **The window starts a charge within 4 s** of the enable (0xAA at 33208) | -261 W after 2 s, -4499 W after 4 s |
| **It charges flat at the pack's limit** while open | -4499 to -4500 W for 80 s, from the grid (PV about 990 W) |
| **It stops within 2 s** of the enable going back to 0x55 | 0 W at the first sample after |
| **No overshoot or rebound** after it closes | 0 W for 40 s, then a slow drift to 366 W of discharge as PV fell from 990 to 720 W under a 950 W load |
| The drift after the window is the house's | PV and load explain it sample by sample |
| With the start judged by its bracket and a 20 s recovery, the same check confirms | run 2: -439, 4499, -229 W, "did as it was told", every word restored |
| SoC does not move in 80 s at 4.5 kW | 7.7 % throughout: about 0.1 kWh on a 14.4 kWh pack |

What it changed: `WINDOW_RECOVERY` (60 s to 20 s) and the start bracket in `_verdict`
(`src/sungrow_modbus/control_test/procedure.py`, `src/sungrow_modbus/control_test/effects.py`,
`tests/test_control_test_windows.py`). See [the control test](../concepts/control-test.md).
