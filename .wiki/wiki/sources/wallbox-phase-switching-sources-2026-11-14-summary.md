---
type: source
title: wallbox-phase-switching-sources-2026-11-14.md
source_path: raw/wallbox-phase-switching-sources-2026-11-14.md
ingested: '2026-11-14'
created: '2026-11-14'
tags: [wallbox, ac22e-01, ac011e-01, phases, ems, cross-reference]
---

# Phase switching on a Sungrow wallbox: Sungrow's documents, ha-modbus-manager and a forum

`.wiki/raw/wallbox-phase-switching-sources-2026-11-14.md`: what five Sungrow documents (the
AC22E-01 datasheet and manual, the SH-RT manual, the iSolarCloud manual, the EV Power Guide),
TCzerny/ha-modbus-manager's two wallbox pages and the 873 posts of Photovoltaikforum's AC22E-01
thread say about choosing a [wallbox](../entities/device-wallbox.md)'s phases. Reports and
documents, not measurements.

| Fact | Evidence |
| --- | --- |
| **The AC22E-01 switches phases automatically**; no document names a setting for it | datasheet V6, manual Ver18-202509 |
| **No phase setting in iSolarCloud**: the charger page has mode, energy purchase, battery cut-off SoC, current, mileage | iSolarCloud manual V146 Ver28-202610 |
| The SH-RT manual says nothing on modes or phases; it names the minimum charger firmware (AC22E-01 LE-01.1E1.001.101.32) | SH-RT manual Ver24-202503 §3.5 |
| On an SH-RT the charging modes need the wallbox on the inverter's RS485; other hybrids need an iHomeManager | datasheet footnote, AC22E-01 manual §5 |
| ECO falls back at the minimum charging power: holds it if energy purchase is allowed, stops otherwise | iSolarCloud manual, logger charging management |
| The 2023 guide's AC011E-01 minimum is 4.14 kW (6 A, three phase), one phase only for a one-phase car | EV Power Guide |
| **Owners see a one-phase charge in PV surplus with energy purchase off**, three phase at 4.1 kW or more with it on | forum posts 4766620, 4889688, 4935414 |
| Some SH-RT owners never see it switch | forum posts 4454227, 4756920, 4867251 |
| Automatic switching cannot be turned off, even with installer rights | forum post 4901132 |
| With an iHomeManager an installer parameter sets 1- or 3-phase supply; without one, it is missing | forum posts 4754737, 4755326, 4755356 |
| The wallbox's own 21204 selects the phases, offered as a select by ha-modbus-manager's template for a wallbox reached directly | `README_sungrow_ac011e_wallbox.md` |
| The iHomeManager's map has no phase word | `README_sungrow_wallbox_connection.md` |
| Whether a write to the wallbox's 21xxx collides with the inverter's management is open there too | the same |
| A phase change at 22 kW tripped a breaker; the 11/22 kW rating is an installer setting in iEnergyCharge | forum post 4901435 |

Not read: the iHomeManager's manual (ManualsLib answered with a bot check), so its 1.38-4.14 kW
rule is still second hand.

What it changes: [a managed wallbox's phases](../concepts/managed-wallbox-phases.md), and the
open question of [an inverter-side phase word](../queries/can-a-managed-wallbox-be-set-to-one-phase.md).
