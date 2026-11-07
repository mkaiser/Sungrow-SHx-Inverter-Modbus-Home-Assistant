---
type: source
title: gerd-import-limit-2026-11-08.md
source_path: raw/gerd-import-limit-2026-11-08.md
ingested: '2026-11-08'
created: '2026-11-08'
tags: [register-32998, import-limit, forced-charge, sh80rt-v112, sapphire-h-b001-v000-p022, gerd, winet-s, contention, write]
---

# The site import limit on P022, gerd, 2026-11-08

`.wiki/raw/gerd-import-limit-2026-11-08.md` records two watched runs of
[register 32998](../entities/register-32998.md) under an EMS forced charge at
[gerd](../entities/installation-gerd.md)'s [SH8.0RT-V112](../entities/device-sh-rt.md) on
[P022](../entities/firmware-sapphire-h-b001-v000-p022.md), after dark, one over the cable and one
written through the [WiNet-S](../entities/device-winet-s.md), while the house's Home Assistant
polled.

| Claim | Evidence | Status |
| --- | --- | --- |
| On P022 the cap holds under a forced charge, over the cable | 1.00 kW cap: the 1248 W charge cut to ~496 W, import 1002 W (980-1015) | watched by this repository, one run |
| It holds when written through a WiNet-S | the dongle read 956-1009 W against 1.00 kW | one run, read through the dongle |
| On P022 it holds at the cap, not under it | 1002 W; P023 held 4-6 % under, P020 0-3 % over | one run |
| A busy WiNet-S reports stale and invented samples | after three timeouts a sample still read the pre-cap 1676 W; one read 0 for every value; 0x04 to two holding reads | one run |
| It can stop answering mid-run, and a write that times out can still land | 32998 = 2000 timed out five times, yet read 2000 over the cable minutes later | one run |
| With a Home Assistant polling, the cable can close every session for minutes | TCP 502 open, every Modbus session closed, 00:34-00:55 | one occasion |

Every word was restored: the cable read 32998 = 2000, and the dongle 13050-13052 as before.

What it says for the [contention](../concepts/contention.md) rules: a run through a dongle
that a Home Assistant also polls can lose the dongle mid-restore, so a restore must keep
retrying and may need the other path to read the result.
