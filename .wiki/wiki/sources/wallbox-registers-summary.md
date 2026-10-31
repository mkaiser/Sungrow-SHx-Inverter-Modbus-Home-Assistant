---
type: source
title: wallbox_registers.md
source_path: raw/wallbox-registers.md
ingested: '2026-10-29'
created: '2026-10-29'
tags: [wallbox, registers, ac22e-01]
---

# The wallbox registers

`raw/wallbox-registers.md`, a frozen copy of `doc/wallbox_registers.md`: Sungrow publishes no register document for its
AC wallboxes, so this is what the measurements agree on. It was read off one
AC22E-01 at [gerd](../entities/installation-gerd.md), through the dongle at
unit 3 (once while a car charged, once idle) and at its own address over TLS
at unit 248. It was then compared with two community projects, discussion
#571 on this repository, and a GPL-3.0 project read for what exists rather
than copied.

- **Every row carries a confidence mark**: three sources, two sources,
  measured here, named elsewhere, or open.
- **It caught a charging session ending**, which is what tells a register
  that resets from one that keeps climbing or one that freezes.
- **It gives register numbers**, as this wiki does
  ([protocol addresses](../concepts/protocol-addresses.md)).

The device page is [wallbox](../entities/device-wallbox.md).
