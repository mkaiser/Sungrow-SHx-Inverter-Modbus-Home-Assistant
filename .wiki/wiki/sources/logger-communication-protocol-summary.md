---
type: source
title: logger-communication-protocol.md
source_path: raw/logger-communication-protocol.md
ingested: '2026-11-06'
created: '2026-11-06'
tags: [logger, specification, ports, tls]
---

# Sungrow's Logger documents

`raw/logger-communication-protocol.md` records what Sungrow's *Logger
Communication Protocol* 1.0.2.9 and 1.0.2.5 and its Logger manuals say. Both
protocol versions are marked public. Where each was found, and what could
not be found, is on [where Sungrow's documents are](../queries/where-are-sungrows-documents.md).

| Fact | Value |
| --- | --- |
| Unit | 247, fixed; devices behind it at their forwarding address |
| Input blocks | identity 8000-8006, inputs 8021-8036, array 8058-8109 |
| Holding | 8002-8016 controls (1.0.2.5), 8017-8020 gradient control and WiFi hotspot (new in 1.0.2.9) |
| Word order | 32-bit low word first, 64-bit high word first |
| Unsupported | all ones unsigned, largest positive signed |
| Broadcast | unit 0 is passed through to every inverter |
| Default port on a current Logger1000 | **516 with TLS**; 502 off, from `LOGGER-SV300.001.00.P044` |
| Cadence | at least 10 s for the holding registers behind it |

- **It agrees with everything mapped before**: the type codes and the
  identity block, as Voyanti/ha-sungrow and RafAustralia's YAML had them.
- **Its misprints**: 8092's unit is kVar for an active power, in both
  versions, and the holding table names 8003-8009 alike; the units tell
  them apart.
- **It is what `src/sungrow_modbus/logger/registers.py` now maps**, held
  `spec`, unmeasured; see [Sungrow Logger](../entities/device-logger.md).
