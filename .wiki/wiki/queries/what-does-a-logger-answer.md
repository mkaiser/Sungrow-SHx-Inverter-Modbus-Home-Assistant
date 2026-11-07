---
type: query
title: "What does a Sungrow Logger answer?"
tags: [logger, open, survey-wanted]
created: '2026-10-30'
query: "Does a real Logger answer what its protocol document lists, at unit 247, and at which unit ids are the devices behind it?"
results_count: 0
---

# What does a Sungrow Logger answer?

**Open: the Logger itself never measured; inverters behind one have been.** Sungrow's protocol 1.0.2.9 lists what
a Logger should answer
([Logger documents](../sources/logger-communication-protocol-summary.md)),
and [Sungrow Logger](../entities/device-logger.md) holds it as `spec`. A
survey of one turns that into a measurement; the participants of discussion
#262 own Loggers.

What a first survey settles:

- **Whether the 64-bit values send their high word first**, as the document
  says, while the 32-bit ones send their low word first.
- **Which inputs a Logger1000 answers** with its unavailable value: the
  PT100s are documented for the Logger3000 and Logger4000 only.
- **Whether 8001 is text** ("AW0", as an iHomeManager answers) or the U32 the
  document types it as.
- **Whether port 502 answers at all**: a current Logger1000 opens only 516,
  with TLS.
- **At which unit ids the inverters behind it answer**, against the
  forwarding addresses its web page lists. *Partly answered*: at
  [code-imstillalive](../entities/installation-code-imstillalive.md) two inverters
  answered, each on a Logger port of its own at the unit the owner gives
  (502 at 1, 503 at 2), and refused what a WiNet-S refuses
  ([the SH25T](../sources/sh25t-b000v000p067-3p-code-imstillalive-anon-92853701430-battery-unknown-meter-logger-summary.md)). The
  owner's Logger refuses input 4951 at unit 247 with exception 2 (by the
  owner, issue #791), so the
  integration cannot be set up on it; `ihomemanager_direct.py` reads it.

Reports, none measured here:

- **A Homey forum thread** (community.homey.app, topic 126405) reports unit
  247, the document's numbers one above the protocol address, and writes to
  the Logger failing.
- **A traffic capture** of a plant with six inverters behind a Logger
  (hjsmoostrong-beep/sungrow-modbus-analysis) shows a monitoring system
  polling unit 247's 8061-8085.
