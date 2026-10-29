---
type: concept
title: The control test
tags: [control-test, writes, scale, survey]
created: '2026-10-29'
---

# The control test

Part B of a survey. Part A answers "what is here" entirely by reading. Part B
**writes** each control, reads the register back against the
specification's scale, watches what the inverter does, and puts everything
back.

## Why reading is not enough

`NumberField.encode` and `decode` share one `scale`, so a wrong scale in
`registers.py` is **invisible to a readback through the library**: write
700 W, get 700 W back, every test green. The registers also mix units on
adjacent addresses: 13052 is 1 W per count, and 33047 next door is 0.01 kW.
That is where such an error would come from, and
[register 13074](../entities/register-13074.md) is where one was found.

## Three legs

| Leg | Mechanism | Catches |
| --- | --- | --- |
| **A, plumbing** | library write, library read | the write landed at the right address |
| **B, scale** | raw word vs `spec_units_per_count`, typed by hand from V1.1.11 and **never read from `field.scale`** | a wrong scale in `registers.py` |
| **C, behaviour** | what the inverter physically does | a *firmware* whose idea of the scale differs |

A column derived from the thing under test proves nothing, which is why leg
B's scale is hand-typed. `tests/test_control_test.py` makes the two meet, so a
decade error fails the suite on the commit that introduces it.

**Through a [WiNet-S](../entities/device-winet-s.md), only leg C survives**:
the dongle forwards the write and reads it back stale. A run through a
dongle says so above its readback table.

## Rules the procedure turns on

- **The restore comes first in every sense.** See
  [the restore](control-test-restore.md).
- **Probe values must be able to show a decade error.** Both `10*v` and
  `v/10` have to stay inside the accepted range. Otherwise the error can only
  surface as exception 0x04, which is also what a legitimately out-of-range
  value returns, so it is not evidence. `battery_max_soc` has no such window
  at all (50..100), and the report says so rather than claiming a pass.
- **What the behavioural checks command is a stated constant**,
  `FORCED_EFFECT_W` (1250 W), clamped to the register's live bounds. It is
  never derived from other probes, which could walk it up to the pack's
  ceiling.
- **A pack's ceiling moves, so a clamp is normal near a full battery.** A
  manufactured discharge aims `FORCE_EXPORT_HEADROOM` below the ceiling and
  accepts a clamp within `CLAMP_TOLERANCE`. Decade verdicts are classified
  **first** and excluded, so the tolerance can never absorb the error the
  procedure exists to find.
- **Leg B on 13074 needs the mode lifted**: see
  [register 13074](../entities/register-13074.md).
- **The button and the survey always run `allow_dark`; the control test on
  its own does not.** Somebody on Home Assistant OS has no terminal, and
  somebody who agreed at the end of a survey has given the leave once. The
  readback half finds a factor-10 error whether or not the sun is up; the
  behavioural half skips itself and says why.
- **Under fluctuating PV the answer is a bracket, not a model.** When the
  before and after readings disagree, the run reports `INCONCLUSIVE`, never a
  failure. It uses medians, not means: a cloud edge is a step, and an MPPT
  search is a spike.
- **The charge-ceiling check is the only safe behavioural test of a
  state-of-charge limit.** Lowering `max_soc` under a charging battery
  **stops** a charge. Raising `min_soc` above the battery would buy
  electricity, which the guards refuse. A `CONFIRMED` shows that the register
  is an enforced ceiling, not that its scale is right.
- **A simulator cannot produce a finding.** It stores raw words with no
  scale, so legs A and B agree by construction and leg C has no signal. Hence
  `--simulated`, which skips the behavioural phase and stamps the report.
- **A run holds this entry's own polling off the inverter**, through
  `SungrowRuntimeData.async_paused()` and the `polling_paused` flag that each
  coordinator reads at the *poll*. Clearing `update_interval` does not cancel
  a timer that is already scheduled. A paused coordinator returns what it
  last had, so entities hold their values.

## Stop and start

A Modbus stop is nearly instant, and the recovery is not. It takes about
2 s to stop. The return to `0x0040 Running` takes 3 to 4 minutes in daylight
and over six at night, then up to 20 s more to generate. Much of the wait is
`0x0020 Starting` ([register 13000](../entities/register-13000.md)). The
deadline is ten minutes, with five each for the stop and for generation. The
terminal prints a dot every `WAIT_TICK` (10 s) while it waits.

## Drivers

The engine is `src/sungrow_modbus/control_test.py`, so both drivers share it:

- `device-survey/scripts/python/sungrow_control_test.py`, through the
  survey;
- the **Run control write test** button on the device page.

Both publish into one survey document (the `control_test` block).
Every survey with such a block is tagged `control-test` in the
[index](../index.md).
