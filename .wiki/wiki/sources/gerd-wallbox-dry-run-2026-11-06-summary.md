---
type: source
title: gerd-wallbox-dry-run-2026-11-06.md
source_path: raw/gerd-wallbox-dry-run-2026-11-06.md
ingested: '2026-11-06'
created: '2026-11-06'
tags:
  - wallbox
  - ac22e-01
  - gerd
  - capability-test
  - tls
---

# gerd's wallbox, the capability test's dry run, 2026-11-06

The wallbox [capability test](../concepts/capability-test.md)'s first run on hardware, as a dry run
(read only) at [gerd](../entities/installation-gerd.md)'s [wallbox](../entities/device-wallbox.md)
over TLS, with no car connected. Source: `raw/gerd-wallbox-dry-run-2026-11-06.md`.

- **The output current setting (holding 21203) reads 0 with no car**, where the charging
  sessions read 160 and 151. So the scale question cannot be answered from an idle wallbox: 0
  is 0 at either scale, and only a car charging separates them.
- **Available current (input 21322) reads 161 while the setting is 0.** The one earlier reading
  had the two equal (160 against 160), which suggested an echo; this one does not, so 21322 is
  not the setting echoed.
- **Start/stop reads 1 while idle**, as after a finished charge, and enabled reads 1; the phase
  setting reads 0, three phase.

The run wrote nothing. What it changes in the plan: the behavioural leg needs a car charging, and
a setting of 0 when idle means the restore puts back a 0, whose meaning (no limit set, or none
offered) is not established.
