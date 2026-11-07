---
type: entity
title: Sungrow Logger
tags: [logger, unmeasured, specification]
created: '2026-10-30'
updated: '2026-11-06'
---

# Sungrow Logger

Sungrow's Logger1000, Logger3000 and Logger4000: a plant controller that
fronts inverters and meters. **Documented; the Logger itself never measured here.** Two
inverters have been read *through* one ([code-imstillalive](installation-code-imstillalive.md)).

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
  wallbox's arrangement ([wallbox](device-wallbox.md)). The diagnosis asks
  unit 247 over TLS on 516 wherever no wallbox answers there, and wherever a
  typed address answers nothing on its plain port
  (`device-diagnosis/scripts/python/ihomemanager_direct.py`, `tests/test_logger.py`).
- **What sits behind it:** each inverter and meter answers on the Logger's
  endpoint at its **forwarding address**, which the Logger's web page lists
  under Device List. At code-imstillalive's Logger1000A each device is also on
  a port of its own, by the owner (SH25T on 502 at unit 1, SH15T on 503 at
  unit 2, the meter on 504, the Logger on 505 at unit 247, each battery tower
  on another), and **an inverter reached that way reads like one behind a
  WiNet-S**: 6100, 2613, 2629 and the history blocks refused
  ([the SH25T](../sources/sh25t-b000v000p067-3p-code-imstillalive-anon-92853701430-battery-unknown-meter-logger-summary.md)). The diagnosis's `identify` stops at the first inverter on
  units 1-5, so it asks unit 247 only when the owner answers `logger` for the
  transport.
- **Writes:** a command to unit 0 reaches every inverter behind it, and a
  latched Logger (8069) ignores remote dispatch. Two people report writes
  failing ([what a Logger answers](../queries/what-does-a-logger-answer.md)).
  Nothing here writes.
- **How it is read:** every documented field decoded, every word of
  8000-8199 published raw, any text no field reads masked and published as a
  stand-in (`src/sungrow_modbus/logger/document.py`, `src/sungrow_modbus/dump.py`).
