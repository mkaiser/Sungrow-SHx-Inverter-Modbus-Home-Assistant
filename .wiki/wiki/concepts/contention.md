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
- **A short retry is not a retry.** The capability test's opening reads back off
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
- **A Modbus proxy in front of the inverter's port shares it cleanly.** An anonymous SH10RT-V112
  read through a modbus-proxy add-on while Home Assistant's YAML package polled through the same
  proxy answered 36 of 36 blocks in every round with no reconnect, exactly as a direct run ten
  minutes later with nothing else polling
  ([through the proxy](../sources/sh10rt-v112-b001v000p020-3p-anonymous-anon-33472554127-battery-thirdparty-meter-direct-lan-summary.md),
  [direct](../sources/sh10rt-v112-b001v000p020-3p-anonymous-anon-33472554127-battery-thirdparty-meter-direct-lan-2-summary.md)).
  Register 6100 answered through it, so transport detection still sees the cable.
- **One write lost the connection at the same place twice**: the charge window's write of
  register 33213 at [peter-sm](../entities/installation-peter-sm.md), in both capability tests of
  2026-11-02, over the cable. Whether that is the register or the link is
  [open](../queries/does-writing-33213-drop-the-link-at-peter-sm.md).

Diagnoses read while Home Assistant polled carry a `contention` block
saying who polled and whether the block read test ran; for example
[sisu70](../entities/installation-sisu70.md).
