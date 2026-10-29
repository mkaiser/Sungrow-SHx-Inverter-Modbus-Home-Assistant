---
type: entity
title: Register 6100 (transport probe)
tags: [register, input, transport]
created: '2026-10-29'
---

# Register 6100 (transport probe)

Input 6100 **answers on a cable and is refused through a dongle**. That makes
it the question that decides transport, and every survey's
`connection.winet_restricted_block_6100` records the answer.

Register 13265 is not a substitute. It names the module that is *fitted*,
not the one in the path, and through a dongle it can answer empty, so it is
wrong in both directions. Report it beside 6100 as a separate fact.

See [transport detection](../concepts/transport-detection.md).
