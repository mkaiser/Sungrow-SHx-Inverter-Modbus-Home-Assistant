---
type: source
title: legacy_entity_map.json
source_path: ../doc/legacy_entity_map.json
ingested: '2026-10-29'
created: '2026-10-29'
tags: [yaml-package, migration, entity-id]
---

# The legacy entity map

`doc/legacy_entity_map.json` records what the YAML package produces: the
entity ids, units and state classes users have. **It is not regenerated.**
`tests/test_registers.py` and `tests/test_sensor_descriptions.py` hold
`registers.py` and `sensor_descriptions.py` to it field by field. Where a
field must differ, the difference is declared where the test can see it:
`layout.COUNTS` for a string length, and `write_units_per_count` for
[13074](../entities/register-13074.md)'s write scale.

It also seeds the simulator (`generate_simulator_registers.py`).

Used by [adopting the legacy entity ids](../concepts/legacy-id-adoption.md).
