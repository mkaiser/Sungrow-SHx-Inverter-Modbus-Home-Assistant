---
type: source
title: gerd-entity-id-switch-2026-11-25.md
source_path: raw/gerd-entity-id-switch-2026-11-25.md
ingested: '2026-11-25'
created: '2026-11-25'
tags: [migration, history, recorder, energy-dashboard, gerd, home-assistant]
---

# gerd's own Home Assistant, 2026-11-25: to device-scoped ids

The *Entity IDs* switch on the production instance of [gerd](../entities/installation-gerd.md), on 0.1.0a55.
Source: `raw/gerd-entity-id-switch-2026-11-25.md`.

| Fact | Evidence |
| --- | --- |
| 119 entities renamed, 20 legacy-only ones removed, nothing archived; every renamed id with statistics has them under the new id | the preview, the registry and the statistic ids before and after |
| **The switch leaves out an adopted id that is not the legacy id it expects**: six `_2` ids stayed and were renamed by hand | the registry |
| The `_2` ids were made by the YAML package's own change of unique id or platform, not by the owner's templates | both rows of each pair are in the registry of before the integration |
| After `energy/save_prefs` the automatic cost sensors were unavailable until Home Assistant restarted | their states before and after |
| Older hours can be joined onto a series with `recorder/import_statistics`; the rows already there stay identical | five series compared before and after |
| An older daily consumed energy's `sum` was about 13 times the lifetime counter's, so it was not joined | the two series |

## Not answered

Both open points of the raw note are taken up in [the follow-up](gerd-entity-id-switch-followup-2026-11-25-summary.md).
