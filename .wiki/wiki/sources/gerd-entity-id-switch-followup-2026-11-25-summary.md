---
type: source
title: gerd-entity-id-switch-followup-2026-11-25.md
source_path: raw/gerd-entity-id-switch-followup-2026-11-25.md
ingested: '2026-11-25'
created: '2026-11-25'
tags: [migration, history, recorder, gerd, home-assistant]
---

# gerd's own Home Assistant, 2026-11-25: after the switch

Follows [the switch](gerd-entity-id-switch-2026-11-25-summary.md) at [gerd](../entities/installation-gerd.md)'s.
Source: `raw/gerd-entity-id-switch-followup-2026-11-25.md`.

| Fact | Evidence |
| --- | --- |
| The dashboards draw on the new ids without an error card | Chromium, the first view of each |
| A sum can have older restarts: look through a whole series before joining it, not at the seam only | four drops in two totals, at the same two dates |
| A daily counter rounded to whole kWh as `total_increasing` has a sum of about 5.4 times the days' end values; the cause (a fall taken for a reset) is inferred | the older series |
| The newer daily counter, `total` without `last_reset`, has a sum that does not grow | 315 days of it |
