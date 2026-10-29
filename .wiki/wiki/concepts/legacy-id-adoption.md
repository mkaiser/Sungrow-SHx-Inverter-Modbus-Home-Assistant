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
the [legacy entity map](../sources/legacy-entity-map-summary.md).

- **A registry rename carries raw history and long-term statistics**, and a
  `total_increasing` sum keeps climbing across it.
- **But a rename onto an id the recorder already knows is refused**, with only
  a log line, which is exactly the YAML case. So the mechanism is to **claim
  the legacy `entity_id` at entity creation**. History then simply continues,
  with no recorder API involved. Modern ids are that, plus one rename
  afterwards.
- **Adoption needs the legacy id free** in the registry *and* in the state
  machine, or the registry silently appends `_2`.
- **Both directions are reversible.** A rename moves the row, so the round
  trip returns history to the legacy id. Where that id is still occupied,
  archive the occupant under another name first. Nothing is copied and
  nothing is deleted. There is no raw-state import API, so staging history in
  a temporary copy is not possible, and not needed.
- **Every ported entity keeps the unit class and `state_class`** of the YAML
  entry it replaces. With the unit class wrong, long-term statistics freeze
  flat, repeating the last value forever, while raw history keeps filling, so
  nothing looks broken. `tests/test_sensor_descriptions.py` holds this field
  by field.

A house with more than one inverter: see [the legacy slot](legacy-slot.md).
