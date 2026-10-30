---
type: entity
title: Sungrow Logger
tags: [logger, unmeasured]
created: '2026-10-30'
---

# Sungrow Logger

Sungrow's Logger1000, Logger3000 and Logger4000: a plant controller that
fronts inverters and meters. **Never measured here.**

- **Where it answers:** unit 247, like the
  [iHomeManager](device-ihomemanager.md), in the same protocol family: a
  type code at input 8000 and its device counts at 8005-8006, by the map
  posted in discussion #262.
- **How it is told apart:** by that type code. 0x0705 is a Logger3000, 0x0710
  a Logger1000, 0x0718 a Logger4000, and 0x072A an iHomeManager
  (`src/sungrow_modbus/logger/registers.py`, from Voyanti/ha-sungrow, which
  cites Sungrow's *Logger Communication Protocol*).
- **What sits behind it:** each inverter and meter gets a unit id of its own
  on the Logger's endpoint. So the survey's `identify`, which stops at the
  first inverter on units 1-5, does not see the Logger there; it asks unit
  247 when the owner answers `logger` for the transport.
- **How it is read:** its identity decoded, the rest of the 8000 block raw,
  any text masked and published as a stand-in
  (`device-survey/scripts/python/ihomemanager_direct.py`, `tests/test_logger.py`).
- **The document:** Sungrow's *Logger Communication Protocol* 1.0.2.5, 1.0.2.7
  and 1.0.2.9 exist only behind logins; it has not been read here. See
  [what a Logger answers](../queries/what-does-a-logger-answer.md).
