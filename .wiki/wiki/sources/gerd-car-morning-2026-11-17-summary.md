---
type: source
title: gerd-car-morning-2026-11-17.md
source_path: raw/gerd-car-morning-2026-11-17.md
ingested: '2026-11-17'
created: '2026-11-17'
tags:
  - wallbox
  - gerd
  - ems
---

# gerd's car, the morning of 2026-11-17

The owner's report, relayed by the maintainer, after [the wallbox night](gerd-wallbox-night-2026-11-16-summary.md)
at [gerd](../entities/installation-gerd.md). Source: `raw/gerd-car-morning-2026-11-17.md`. Nothing measured
over Modbus.

| Fact | Evidence |
| --- | --- |
| **The car reached 100 %** after it had sat `suspended by the vehicle` at about 89 % from 02:19 to at least 06:05; when and how it resumed is not known | the owner, relayed |
| **The car reports that its Internet connection is not established** | the owner, relayed: the car's own message |

## What it means, and what it does not

- The suspension at 02:19 did not end the charge for good: the car finished it, so it was a pause, not a
  limit reached.
- A car without its Internet connection cannot have reported to its app, so the app's word on that night is
  suspect: its "charge done at 47 %" at 21:33, and the reason for the 02:19 suspension, which the app was to
  give. Whether the connection was already down then was not reported.
- Nothing here says the missing connection caused the suspension.
  [The query](../queries/why-does-a-managed-wallbox-stop-charging.md) keeps it open.
