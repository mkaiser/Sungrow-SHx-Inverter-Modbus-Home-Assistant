---
type: concept
title: A generator the inverter cannot see
tags: [load-power, external, options]
created: '2026-10-29'
---

# A generator the inverter cannot see

A non-Sungrow inverter behind the same grid meter makes `load_power` low by
exactly its output. The [SH-RT](../entities/device-sh-rt.md) computes load
from its own output plus grid import, so it never sees the other generator.

`custom_components/sungrow_modbus/external.py` adds that output back from
entities another integration owns. It is the one place a value comes from
Home Assistant rather than Modbus, which is why it is not in `src/`. It is
also the one place where an entity's existence is an **option** rather than
a probed fact.
