---
type: query
title: "What does an iHomeManager answer?"
tags: [ihomemanager, open, survey-wanted]
created: '2026-10-29'
query: "Which of the 53 mapped iHomeManager registers answer on a real unit, on which port?"
results_count: 0
---

# What does an iHomeManager answer?

**Open: never measured.** The map is the 53 registers in the
[cross-reference](../sources/cross-reference-modbus-manager-summary.md). What
is known about the device is on [iHomeManager](../entities/device-ihomemanager.md).

What answers it: a survey of one, at slave 247 on port 502 or 503.
[ra1k-0](../entities/installation-ra1k-0.md) reports one installed, and polling
the inverter. `sungrow_survey.py` now reads one into a publishable document,
from the first release that carries `sungrow_modbus.ihomemanager`; the
question waits on somebody running it.

A second question rides on the same house: whether an iHomeManager silences the
inverter's meter phase registers 5741-5746 (issues #647, #651). Both of
ra1k-0's readings are through a WiNet-S, which refuses those registers anyway,
so only a reading of the inverter's own LAN port answers it.
