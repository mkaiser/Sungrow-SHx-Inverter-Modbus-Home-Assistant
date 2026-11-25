---
type: source
title: gerd-ha-migration-2026-11-21.md
source_path: raw/gerd-ha-migration-2026-11-21.md
ingested: '2026-11-21'
created: '2026-11-21'
tags:
  - migration
  - history
  - recorder
  - energy-dashboard
  - modbus-proxy
  - gerd
  - home-assistant
---

# gerd's own Home Assistant, 2026-11-21: the integration goes in, behind a proxy

The first setup of the integration on a production Home Assistant that had run the YAML package, over
[gerd](../entities/installation-gerd.md)'s SH8.0RT-V112 and AC22E-01, through a modbus-proxy add-on in
front of both paths. Source: `raw/gerd-ha-migration-2026-11-21.md`.

| Fact | Evidence |
| --- | --- |
| **Legacy ids are adopted from `restored` placeholders**: 150 ids known, all adopted, the old Energy sensors now belong to `sungrow_modbus` under their old ids | the setup dialog, then the registry |
| Ids already held by other rows keep `_2` (seven here; the raw note says the owner's own templates, which [the registry contradicts](gerd-entity-id-switch-2026-11-25-summary.md): an older YAML package's); `_1`/`_2` that name slots are not collisions | the registry, after two minutes |
| **After a gap of more than ten days in an adopted counter's statistics, its running sum restarts at 0**, and the Energy dashboard shows the hour of the first start as minus the whole sum the series had built up. All five counters it uses showed it; `validate_statistics` named none | the hourly rows; the old series ended 12.6 days before |
| `recorder/adjust_sum_statistics` (old final sum minus the new first sum, from the first new hour) makes the series continuous and the day after plausible; the gap's energy is in no hour | the daily change after the adjustment |
| A modbus-proxy add-on's top-level `upstreamhost` is ignored once its `devices:` list is set: the cable's proxy never started and its port refused | the add-on's log and the refused port |
| Through one proxy per path the integration set up the cable entry and, from its own card, the wallbox entry; unit 3 answered only through the dongle's port | reads on both ports, then the entries |
| A **pending zeroconf card for the same inverter makes the manual add abort `already_in_progress`**; dismissing the card lets it through | the manual flow's abort |
| The Marketplace's update entity did not see a new mirror commit for over an hour; reloading its config entry did | the entity before and after |
| The inverter entry's options default every capability test and `publish_address` to **on** | the options form |
| An entity with a device is shown as "device name + name"; a row's own `name:` drops the prefix | the owner's dashboard |

## What it means

- The migration guide now says what a long gap does to the Energy dashboard and how to repair it
  (`doc/integration_migration.md`); whether the integration should repair it itself is
  an open decision in `Todo.md`.
- The proxy's `devices:` behaviour belongs to the add-on, not to the integration; the integration
  needed nothing from the proxy beyond one session per path
  ([contention](../concepts/contention.md)).

## Not answered

- Whether the gap's own energy should be attributed anywhere: the repair leaves it out.
- The wallbox's unavailable entities (seven): which are absent for want of a car and which for want of a
  feature of this model.
