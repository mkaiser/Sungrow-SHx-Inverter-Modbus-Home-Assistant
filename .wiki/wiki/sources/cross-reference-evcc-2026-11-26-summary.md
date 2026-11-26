---
type: source
title: cross-reference-evcc-2026-11-26.md
source_path: raw/cross-reference-evcc-2026-11-26.md
ingested: '2026-11-26'
created: '2026-11-26'
tags: [cross-reference, wallbox, ac22e-01, phases, evcc, licences]
---

# Cross-reference: evcc's wallbox phase switch

`raw/cross-reference-evcc-2026-11-26.md` reads evcc's Sungrow wallbox driver again, at commit
`49b5a8d10`, after a report that evcc switches a standalone AC22E-01 between one and three phases.
The first reading is [cross-reference-evcc.md](cross-reference-evcc-summary.md).

| Finding | Held as |
| --- | --- |
| A maintainer's colleague's AC22E-01, **driven by evcc alone, no inverter managing it**, switches 1p/3p from evcc | reported, not measured; no reading, firmware or wiring |
| evcc sets the phases with holding **21204** (0 three, 1 one), reads them at input **21270** | evcc's driver; all rights reserved, never copied |
| Charging, it stops first (21212 = 1), writes 21204, then starts again (21211 = 1, 21212 = 0, the current to 21203) | evcc's driver and `charger/helper.go` |
| **evcc's Modbus has no TLS**: it reaches a wallbox at unit 248 over RS485, a gateway or plain Modbus TCP, not over the wallbox's own TLS port 516 | `util/modbus/` (MIT) |
| The driver's 16 registers, 30 s heartbeat and codes are unchanged since the first reading | the diff between the two commits |

- **No register is new**, and the capability test already switches a standalone wallbox's phase in
  evcc's order (`src/sungrow_modbus/wallbox/capability_test.py`).
- **It does not contradict gerd's managed wallbox**, where 21204 did not take
  ([the run](gerd-wallbox-capability-test-2026-11-13-summary.md)): the colleague's is the standalone
  case, the first one reported switching. Watching one is item 6 of
  `device-diagnosis/devices-wanted.md`.
