---
type: concept
title: A managed wallbox's phases are the inverter's, chosen by power
tags: [wallbox, ac22e-01, phases, ems, sh-rt]
created: '2026-11-14'
---

# A managed wallbox's phases are the inverter's, chosen by power

A [wallbox](../entities/device-wallbox.md) that a hybrid inverter manages (EMS mode, on the
inverter's RS485) charges on one or three phases **as the inverter decides**. Nothing documented
lets an owner, an installer or a Modbus client choose it.

- **No setting.** Sungrow's datasheet and manual promise only *automatic* phase switching; the
  iSolarCloud manual's charger page has no phase setting; neither of gerd's accounts showed one;
  owners with installer rights cannot turn the switching off
  ([the sources](../sources/wallbox-phase-switching-sources-2026-11-14-summary.md),
  [gerd, 2026-11-14](../sources/gerd-wallbox-inverter-control-2026-11-14-summary.md)). Only with
  an iHomeManager does an installer parameter choose one- or three-phase supply, by owners'
  reports.
- **When it switches**, by owners' reports: in PV surplus (ECO) **with energy purchase off**, and in
  scheduled charging. With energy purchase on, in fast charge and in user-defined charge the
  charge stays three phase, at no less than 4.14 kW (6 A on each phase). Some SH-RT owners never
  see it switch, and one firmware is reported to have lost it
  ([the sources](../sources/wallbox-phase-switching-sources-2026-11-14-summary.md)). The
  iHomeManager's manual is said to switch at 1.38-4.14 kW, not read here.
- **The inverter has done it at gerd's**: one phase on 2026-09-08, with the wallbox's own setpoint
  (holding 21204), phases in use (input 21225) and actual mode (input 21270) all reading 1
  ([wallbox registers](../sources/wallbox-registers-summary.md)), and on 2026-10-30, when the
  portal showed the last session's 6.1 A on phase A alone
  ([the portal](../sources/gerd-wallbox-isolarcloud-2026-10-30-summary.md)). Nobody here had
  written 21204.
- **Writing the wallbox's own 21204 does not do it on a managed wallbox**: written 1 at gerd's on
  2026-11-13 with the car stopped, the actual mode stayed three phase and the setpoint went back
  to 0 (`.wiki/raw/gerd-wallbox-capability-test-2026-11-13.md`). The inverter also overwrites the
  wallbox's current within seconds
  ([gerd, 2026-11-14](../sources/gerd-wallbox-inverter-control-2026-11-14-summary.md)). 21204 is
  a control only on a wallbox nobody else manages, where evcc writes it with the charge stopped.
- **The inverter's charger block (33540-33550) has no phase word.** The two words below it,
  33538 and 33539, refused writes with charging off in fast charge and in PV surplus alike, and
  **did not move in a one-phase session** ([2026-11-24](../sources/gerd-wallbox-2026-11-24-summary.md)).
- **Grid purchase (33550) decides in PV surplus, measured** ([2026-11-24](../sources/gerd-wallbox-2026-11-24-summary.md)): off, one phase at 5.4 A,
  1.24 kW, the inverter switching its charging word on and off by itself, and no attempt lasting over 30 s at up to 1.6 kW over the house; on, three phase at the 6 A minimum whatever
  the surplus. Switched off in a three-phase charge it ends the session rather than change the phases.

**What the integration does with it**: the phases in use are a sensor (21270, and 21272, the
minimum charging power, 1380 W on one phase and 4140 W on three), never a control on a managed
wallbox. An owner who wants one phase sets *PV surplus* with grid purchase off, and the inverter
switches when the surplus is small.
