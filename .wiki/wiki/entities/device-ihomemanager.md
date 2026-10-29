---
type: entity
title: iHomeManager
tags: [ihomemanager, unmeasured]
created: '2026-10-29'
---

# iHomeManager

Sungrow's energy manager. **Never measured here.**

- **Where it answers:** slave 247, on port **502 or 503**. Sungrow's
  setting is "Modbus TCP on the iHM", which lands on 502 on some units and
  on 503 where 502 is busy.
- **What it is not:** a gateway. It forwards system energy dispatch data,
  not the devices behind it, so its inverters are separate endpoints.
- **How it is noticed:** `identify()` probes input 8000 on unit 247. A
  contributor who owns one is told what they have, and `sungrow_survey.py`
  reports it without surveying it.
- **The map:** 53 registers in the MIT-licensed
  [cross-reference](../sources/cross-reference-modbus-manager-summary.md).

[ra1k-0](installation-ra1k-0.md) reports an iHomeManager installed, but it
was not read. Next step: [survey one](../queries/what-does-an-ihomemanager-answer.md).
