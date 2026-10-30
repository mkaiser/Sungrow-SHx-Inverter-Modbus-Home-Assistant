---
type: source
title: gerd-wallbox-isolarcloud-2026-10-30.md
source_path: raw/gerd-wallbox-isolarcloud-2026-10-30.md
ingested: '2026-10-30'
created: '2026-10-30'
tags: [wallbox, ac22e-01, gerd, isolarcloud]
---

# gerd's wallbox: Sungrow's portal beside a direct read

`.wiki/raw/gerd-wallbox-isolarcloud-2026-10-30.md`: the owner's iSolarCloud
device page for the [wallbox](../entities/device-wallbox.md) at
[gerd](../entities/installation-gerd.md), and a direct read of the same unit
about five minutes later. The first time a register here is checked against
something Sungrow itself shows.

| Fact | Evidence |
| --- | --- |
| **Input 21201-21206 is the serial** | the portal's S/N hashes to `anon-41346964423`, the stand-in derived from those words |
| **The serial's first four characters are this unit's**, not a model prefix the tests may carry | the same S/N |
| **21300 counts lifetime energy in Wh** | 635310 read, 635.28 kWh shown |
| **21310 counts session energy in Wh** | 279 read, 0.28 kWh shown |
| The session had ended | 21317 = 6 (completed), power and phase currents 0 |
| The portal shows a session's last phase current after it ends | 6.10 A on phase A with 0 W and status `--` |

The portal's charging power, 0 W, agrees with 21308. It cannot settle
whether 21308 or 21310 is signed, nor what 21313 does while charging: both
need a car that is charging.
