---
type: concept
title: Contention
tags: [modbus, sessions, polling]
created: '2026-10-29'
---

# Contention

A Sungrow accepts **very few simultaneous sessions**, and the recovery is
**90 seconds of quiet**.

- **The signature is progressive**: each retry dies a little further into the
  poll. A bad block fails at the same address every time. Repetition tells
  them apart.
- **A short retry is not a retry.** The control test's opening reads back off
  for **5, 20, 45 and 90** seconds.
- **The contention is often self-inflicted**: probes and runs opened back to
  back, on top of a polling YAML package.
- **This is why one config entry is one serialized connection.** Home
  Assistant's `modbus` integration shares one connection between everything
  pointed at the same host and port. Two writes issued at once queue, and the
  second one's timeout starts while it is still waiting. So
  `PARALLEL_UPDATES` is 1 on the write platforms.
- **A WiNet-S port 516 exhausts under rapid reconnects** just as 502 does
  ([WiNet-S](../entities/device-winet-s.md)).

Surveys read while Home Assistant polled carry a `contention` block
saying who polled and whether the block read test ran; for example
[sisu70](../entities/installation-sisu70.md).
