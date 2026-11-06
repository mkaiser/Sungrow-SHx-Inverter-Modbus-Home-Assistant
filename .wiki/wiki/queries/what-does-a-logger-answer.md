---
type: query
title: "What does a Sungrow Logger answer?"
tags: [logger, open, survey-wanted]
created: '2026-10-30'
query: "Which registers does a Logger answer at unit 247, and at which unit ids are the devices behind it?"
results_count: 0
---

# What does a Sungrow Logger answer?

**Open: never measured.** What is known is on [Sungrow Logger](../entities/device-logger.md):
the identity block and the type codes. A survey of one answers it; the
participants of discussion #262 own Loggers.

Leads, none measured here:

- **The rest of the 8000 block, by name.** Voyanti/ha-sungrow's
  Logger module (`sungrow_logger.py` in its repository) transcribes Sungrow's *Logger Communication
  Protocol* 1.0.2.7: about 40 input registers from 8000 to 8106 (digital
  inputs at 8021, PT100 and ADC inputs at 8027-8036, nominal and adjustable
  power at 8058-8094, total active and reactive power, daily, monthly, annual
  and total yield) and holding setpoints from 8002. It is GPL-3.0, so it
  names what exists and is never copied; the document it cites on Studocu
  now shows something else.
- **The document itself**: copies of 1.0.2.5, 1.0.2.7 and 1.0.2.9 are on
  Scribd, readable only with an account.
- **A Homey forum thread** (community.homey.app, topic 126405) reports unit
  247, the document's numbers one above the protocol address, as everywhere
  here, and writes to the Logger failing.
