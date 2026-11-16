---
type: entity
title: Register 6100 (transport probe)
tags: [register, input, transport]
created: '2026-10-29'
---

# Register 6100 (transport probe)

Input 6100 **answers on a cable and is refused through a dongle**. That makes
it the question that decides transport, and every diagnosis's
`connection.winet_restricted_block_6100` records the answer.

A **Modbus proxy forwards it**, so through one the answer describes the
inverter's own path rather than the hop to the proxy. Not for every
session: a config entry's probe of a proxy read it as neither answered nor
refused three times, where the same entry read it as answered at the
inverter's own LAN port
([open](../queries/does-a-modbus-proxy-carry-6100.md),
[the reading](../sources/mkaiser-modbus-proxy-2026-11-16-summary.md)).

Register 13265 is not a substitute. It names the module that is *fitted*,
not the one in the path, and through a dongle it can answer empty, so it is
wrong in both directions. Report it beside 6100 as a separate fact.

See [transport detection](../concepts/transport-detection.md).
