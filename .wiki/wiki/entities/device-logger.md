---
type: entity
title: Sungrow Logger
tags: [logger, unmeasured, specification]
created: '2026-10-30'
updated: '2026-11-06'
---

# Sungrow Logger

Sungrow's Logger1000, Logger3000 and Logger4000: a plant controller that
fronts inverters and meters. **Documented, never measured here.**

- **The document:** Sungrow's *Logger Communication Protocol* 1.0.2.9,
  marked public, with 1.0.2.5 beside it
  ([Logger documents](../sources/logger-communication-protocol-summary.md)).
  `src/sungrow_modbus/logger/registers.py` maps all of it: identity
  8000-8006, inputs 8021-8036, the array 8058-8109, and the plant controls at
  holding 8002-8020, read and never written. Every field is held `spec`.
- **Where it answers:** unit 247, fixed, like the
  [iHomeManager](device-ihomemanager.md), in the same protocol family.
- **How it is told apart:** by the type code at input 8000. 0x0705 is a
  Logger3000, 0x0710 a Logger1000, 0x0718 a Logger4000, and 0x072A an
  iHomeManager.
- **Word order differs by width:** a 32-bit value sends its low word first, a
  64-bit value its high word first. The yields and the array's power are
  64-bit (`tests/test_logger.py`).
- **Which port:** a current Logger1000 opens only **port 516, with TLS**, by
  default; 502 is off from firmware `LOGGER-SV300.001.00.P044`. That is the
  wallbox's arrangement ([wallbox](device-wallbox.md)), so a survey of a
  Logger needs TLS on 516, or the owner turning 502 on.
- **What sits behind it:** each inverter and meter answers on the Logger's
  endpoint at its **forwarding address**, which the Logger's web page lists
  under Device List. The survey's `identify` stops at the first inverter on
  units 1-5, so it asks unit 247 only when the owner answers `logger` for the
  transport.
- **Writes:** a command to unit 0 reaches every inverter behind it, and a
  latched Logger (8069) ignores remote dispatch. Two people report writes
  failing ([what a Logger answers](../queries/what-does-a-logger-answer.md)).
  Nothing here writes.
- **How it is read:** every documented field decoded, every word of
  8000-8199 published raw, any text no field reads masked and published as a
  stand-in (`src/sungrow_modbus/logger/document.py`, `src/sungrow_modbus/dump.py`).
