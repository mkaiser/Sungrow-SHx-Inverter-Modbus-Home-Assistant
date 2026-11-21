# T070 - Retire the comparison with the YAML package

The port is finished: every register the integration reads lives in Python,
and the YAML package is maintained by hand from here on. So the scaffolding
that held the Python to the YAML comes down (the maintainer, 2026-11-20) --
six test modules and `doc/legacy_entity_map.json` -- and with it goes the last
thing pinning `legacy/` in place.

**What is given up, stated once.** Those tests caught a scale off by ten and a
wrong `state_class` while the maps were being written, and the map is also the
record proving an existing user's `entity_id`, unit class and `state_class`
survive migration. After this, a typo in `registers.py` is caught by a house
noticing. That is the accepted trade for a hand-maintained YAML and a single
source of truth in Python.

## What goes

Six modules, whole (`wc -l`, 2026-11-20):

| File | Tests | Holds |
| --- | --- | --- |
| `tests/test_registers.py` (203) | 8 | every field of `registers.py` against the map |
| `tests/test_sensor_descriptions.py` (419) | 18 | names, units, state classes against the map |
| `tests/test_writes.py` (278) | 9 | `scripts/generate/tables/writes.py`'s bounds against the YAML's `number:` templates |
| `tests/test_scenes_doc.py` (176) | 5 | `doc/scenes.md` against the YAML's scenes |
| `tests/test_sbr_pack.py` (683) | 25 | one test reads the SBR YAML; **24 decode pack readings and probe units** |
| `tests/test_legacy_slot.py` (540) | 24 | two read the YAML; **22 are the slot-detection behaviour** |

Whole files is the maintainer's call. It drops the 46 tests in the last two
rows that have nothing to do with the YAML, so expect the coverage floor to
move (below).

Then `doc/legacy_entity_map.json`, and the wiki's record of it as an immutable
source: `.wiki/wiki/sources/legacy-entity-map-summary.md`, its entry in
`.wiki/wiki/index.md`, and the row in `.wiki/AGENTS.md`'s source table.
`tests/test_wiki.py`'s **source-exists** lint fails if the page outlives the
file, so they go in one commit.

## The refactor that has to come first

`doc/legacy_entity_map.json` is **not only a test oracle**. It is an input to
the generator that writes committed files, so deleting it without this step
turns `make gen`, `gen-check`, `make check` and CI red.

`scripts/generate/descriptions.py` reads it in four places:

- `_registers()` -- the modbus sensor rows, by object id, for addresses;
- `_by_unique_id("number")`, `("switch")`, `("select")` -- those platforms'
  legacy unique ids;
- `_legacy()` -- the `template` and `filter` entities that `derived` replaces.

Out of those it emits `legacy_unique_id`, `state_class`,
`native_unit_of_measurement` and names into
`{derived,number,switch,select,time,button}_descriptions.py`, `strings.json`
and `translations/{en,de}.json`.

So the three fields move into Python, beside the tables that already hold the
rest of the generator's knowledge (`scripts/generate/tables/`), and the
generator reads them from there.

**The safety net is byte-identical output.** `make gen` after the move must
leave every generated file unchanged -- `git diff --exit-code` over
`custom_components/sungrow_modbus/` proves no legacy id, unit or state class
moved, and therefore that no existing user's history detaches. If that diff is
not empty, the move is wrong, not the output.

Two more readers to re-anchor in the same change:

- `scripts/generate/generate_simulator_registers.py:224` -- the simulator's
  seed takes the map's addresses the YAML never read;
- `scripts/dev/seed_migration_testbed.py:54` -- the migration testbed's
  entities come from the map, which is how legacy-id adoption is rehearsed.

## The paper trail

`AGENTS.md`'s *Do not hand-edit* section states the rule being retired --
"`registers.py` and `sensor_descriptions.py` are source, held field by field
to `doc/legacy_entity_map.json` ... by `tests/test_registers.py` and
`tests/test_sensor_descriptions.py`" -- and it is a rule, so it is rewritten
rather than quietly left standing. The same claim appears in
`doc/architecture.md`'s diagram, `doc/development.md` (two places),
`doc/development.yaml` (two), `plans/_improve-doc.md`, and the module
docstrings of `sensor_descriptions.py` and `battery_descriptions.py`.

Coverage: CI runs `pytest --cov` against `fail_under = 93` in
`pyproject.toml`, whose comment says the floor is what the suite covers today.
Re-measure after the deletions and move the floor to the new figure, with the
reason in the comment.

## What it unblocks

`legacy/` can then go, which is what the maintainer asked (incoming note,
2026-11-20). After this plan the folder's remaining readers are
`tests/test_attribution.py` (the provenance surface) and
`scripts/generate/generate_second_inverter_config.py` with its one test, plus
seven documentation links: this branch's `README.md:119-123`,
`doc/integration_migration.md:68` and `doc/energy_dashboard.md:5`. Deleting
the folder means deleting those pages and the links together, in one change.

## Order, and how each step is verified

1. Move the three fields into `scripts/generate/tables/`; `make gen`, then
   `git diff --exit-code custom_components/sungrow_modbus/` -- **empty**.
2. Re-anchor `generate_simulator_registers.py` and
   `seed_migration_testbed.py`; `make gen-check` green, and the seeder still
   runs (`scripts/dev/seed_migration_testbed.py --help` at least).
3. Delete the six test modules and `doc/legacy_entity_map.json`.
4. Delete the wiki source page, its index entry and the `.wiki/AGENTS.md`
   row; `pytest tests/test_wiki.py` green.
5. Rewrite the rule in `AGENTS.md` and the six other places that state it.
6. `pytest -q --cov` -> read the new coverage figure, set `fail_under` to it.
7. `make check`, which is the only thing that proves the gate survived.

## Status log

| When | Status |
| --- | --- |
| 2026-11-20 | **Written, nothing executed.** The decision is the maintainer's, taken today: whole files, and the refactor in the same change rather than deferred. Measured while planning, so the next session need not: `scripts/generate/descriptions.py` reads the map at lines 54, 66, 79, 90, 368 and emits `legacy_unique_id`, `state_class` and `native_unit_of_measurement` at 422, 434, 438, 465, 476, 480, 577 and 1007; `doc/legacy_entity_map.json` holds 302 entities with no `min`/`max`/`step` and no `scene` domain, which is why `test_writes.py` and `test_scenes_doc.py` read the YAML directly and cannot simply be repointed. The generator that built the map, `scripts/generate_entity_map.py`, was retired in `bf58897` and is recoverable from git if extending it ever beats deleting it. Nothing is uncommitted. **Start at step 1**: the field move, with `git diff --exit-code custom_components/sungrow_modbus/` after `make gen` as the gate on whether it was faithful. |
| 2026-11-21 | **Steps 1-5 done; the gate is running.** The map is now `scripts/generate/tables/legacy_entities.py`, row for row and every field (checked equal to the JSON before the JSON went); `make gen` left `custom_components/` byte-identical. More readers than this plan listed were repointed: `scripts/helpers/review_names.py`, `tests/test_entity_wiring.py`, `tests/test_naming_convention.py`, `tests/test_migration.py` and `validate.yml`'s path filter. `tests/test_entity_map.py` became `tests/test_legacy_entities.py`, computing its invariants from the table; its state-class-without-unit check went, because it asserted the JSON's stored summary, which was stale -- 11 YAML sensors (`power_factor`, the `_raw` codes) carry a state class and no unit. The maintainer kept three write-safety tests out of `test_writes.py` that never read the YAML (writable set equals `writes.py`, the danger-mode registers stay unwritable, 13074's raw word), now `tests/test_write_safety.py`. Every comment and doc that cited a removed test now says what holds instead, or that review does. |
| 2026-11-21 | **Done.** `make check` with `--cov`: 8589 passed, 1 skipped, coverage 93.93 % (the removed modules covered little the rest did not), so `fail_under` rises from 93 to 93.9. `legacy/` is not deletable yet: `generate_simulator_registers.py` still reads `legacy/modbus_sungrow.yaml` for every YAML sensor and switch -- a reader this plan's *What it unblocks* missed -- and `generate_second_inverter_config.py` lost its only test with `test_legacy_slot.py`. |
| 2026-11-21 | **`legacy/` removed**, at the maintainer's ask for the cleanest solution. The simulator seed now comes from the library's inverter map alone (`COMPONENTS`, `ev_charger` left out so the simulated house has no managed wallbox); against the YAML-derived seed the only change is 2612 and 2628 widening from 11 to 15 words, the measured count in `layout.COUNTS`. `generate_second_inverter_config.py` went with it: `main` carries its own copy and the workflow that regenerates the multi-inverter files. Links to the YAML package's pages point at `blob/2026-legacy/...`, which resolves once T047 renames `main`; `test_attribution.py` checks the root notice only. `doc/preview-mirror/sync.yml` keeps its "no `legacy/`" comment, still true, unedited to avoid drift with the mirror. |
