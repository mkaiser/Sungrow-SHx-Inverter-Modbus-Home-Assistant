---
type: concept
title: Adopting the legacy entity ids
tags: [migration, history, entity-id, recorder]
created: '2026-10-29'
---

# Adopting the legacy entity ids

The integration replaces the YAML package, so existing users must keep their
recorder history and their dashboards. **Both are keyed by `entity_id`.** The
YAML package produces `sensor.total_dc_power`, while an entity with
`_attr_has_entity_name = True` produces `sensor.<device name>_total_dc_power`.
Get this wrong and years of history and every dashboard card break silently.

Settled and asserted in `tests/test_recorder_migration.py`. The user's guide
is `doc/integration_migration.md`, and the record of what the YAML produces is
`scripts/generate/tables/legacy_entities.py`.

- **A registry rename carries raw history and long-term statistics**, and a
  `total_increasing` sum keeps climbing across it.
- **But a rename onto an id the recorder already knows is refused**, with only
  a log line, which is exactly the YAML case. So the mechanism is to **claim
  the legacy `entity_id` at entity creation**. History then simply continues,
  with no recorder API involved. Modern ids are that, plus one rename
  afterwards.
- **Adoption needs the legacy id free** in the registry *and* in the state
  machine, or the registry silently appends `_2`.
- **A deleted entry's ids come back ahead of the claim.** Deleting a config
  entry keeps its entities in the registry's deleted entities, and
  `async_get_or_create` for the same unique id restores the old entity id
  rather than the `suggested_object_id` passed in. So an inverter first set up
  on device-scoped ids, deleted, and added again to migrate came back on the
  device-scoped ids (#798, Home Assistant 2026.11.2). The claim then renames
  the entry onto the legacy id when that id is free
  (`custom_components/sungrow_modbus/migration.py`, `tests/test_migration.py`).
- **A device in an area gets the area in front of a device-scoped id**
  (`sensor.<area>_<device>_<entity>`) when its ids are recreated; the switch to
  legacy ids in the options still moves those (`tests/test_entity_id_switch.py`).
- **Both directions are reversible.** A rename moves the row, so the round
  trip returns history to the legacy id. Where that id is still occupied,
  archive the occupant under another name first. Nothing is copied and
  nothing is deleted. There is no raw-state import API, so staging history in
  a temporary copy is not possible, and not needed.
- **Every ported entity keeps the unit class and `state_class`** of the YAML
  entry it replaces. With the unit class wrong, long-term statistics freeze
  flat, repeating the last value forever, while raw history keeps filling, so
  nothing looks broken. `scripts/generate/tables/legacy_entities.py` records
  both, and the generated descriptions take them from it; the hand-written
  `sensor_descriptions.py` has no test holding it there.

- **Adoption on a production instance** held at [gerd](../entities/installation-gerd.md)'s: 150 ids
  adopted from `restored` placeholders, and the ids an older YAML package version had taken stayed `_2`, as they were under the YAML
  ([the source](../sources/gerd-ha-migration-2026-11-21-summary.md); the cause is corrected in
  [the switch](../sources/gerd-entity-id-switch-2026-11-25-summary.md)).
- **The switch to device-scoped ids carried the statistics there** (119 renames), but left out the six adopted `_2` ids (the switch
  takes such a number for its own since, `tests/test_entity_id_switch.py`), and the
  Energy dashboard's cost sensors needed a restart after its preferences were saved
  ([the source](../sources/gerd-entity-id-switch-2026-11-25-summary.md)).
- **A gap of more than ten days in the old series restarts each lifetime counter's sum at 0.** Home
  Assistant continues a sum from the short-term table, which keeps ten days; with no row there it
  starts again, and the Energy dashboard shows the first hour as minus everything the series had built
  up. The ids and the history are right, only the sum is not continuous, and `validate_statistics` says
  nothing. `recorder/adjust_sum_statistics` repairs it
  (`doc/integration_migration.md`, the section on the Energy dashboard).

A house with more than one inverter: see [the legacy slot](legacy-slot.md).
