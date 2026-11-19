# T020 - Nothing tells a managed wallbox from a standalone one

## What is to be built, and why

`declared_standalone` returns `False`, hard-coded, because no option asks the
owner (`custom_components/sungrow_modbus/wallbox_capability_test.py`). So a
wallbox entry never runs its own registers' checks -- only the managed ones,
and only where the dongle probe linked it to an inverter entry
(`managing_entry`). A wallbox that no inverter manages is therefore tested at
a fraction of what it could be, and nobody is ever asked why.

The device says nothing either way: input 21314 reads 1 idle and 3 charging on
every wallbox read, and the inverter's EV charger block reads its factory
state on houses with no wallbox at all
([the wallbox](../.wiki/wiki/entities/device-wallbox.md)).

## What there is to work with

Behaviour, not a register:

- an inverter rewrites a managed wallbox's output current (holding 21203)
  every few seconds, which is what the capability test already refuses to
  write over;
- `managing_entry` links the two entries where the dongle probe saw both;
- on the inverter's side, `SungrowRuntimeData.has_wallbox` now says whether
  one answers on its bus (commit `0bcda31`), which is the same question asked
  from the other end.

## The shape

1. **Infer**: managed from `managing_entry`, or from a setting that moves with
   nothing written; standalone only from a steady setting and no managing
   entry.
2. **Show** the inference on the wallbox's device page, so an owner sees what
   the integration believes before it acts on it.
3. **Ask** for the owner's word in *Configure* before anything writes the
   wallbox's own registers.

The division is the point: **an inference decides what is shown and what auto
repeat waits for; the owner decides what is written.** A wrong yes writes
registers an inverter overwrites.

## Steps

1. The inference itself, in the library, from a steady-versus-moving read of
   21203 over a few polls.
2. The device page's wording, English and German.
3. The *Configure* question, defaulting to no, and `declared_standalone`
   reading it instead of returning `False`.
4. Tests for all three, including a managed wallbox that must never be
   declared standalone by inference alone.
5. A run against a standalone wallbox, which nobody has offered yet (T003,
   item 3; `plans/wallbox_tests.md` section 8).

## Status log

| When | Status |
| --- | --- |
| 2026-11-19 | Written down as a plan; nothing built. The code side it depends on is in: the EV controls now ask for a wallbox on the inverter's bus (`0bcda31`). Blocked in practice at step 5 by having no standalone wallbox to measure. |
