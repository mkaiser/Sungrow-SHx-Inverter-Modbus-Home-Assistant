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
- **The house's own battery limits bind before a forced command.** Where
  `battery_max_charge_power` or `battery_max_discharge_power` (33047/33048)
  holds less than the command, the forced check and the manufactured export
  are commanded under it; below `EFFECT_FLOOR_W` the check is skipped with
  the limit named (`ControlTest._under_cap`). At
  [peter-sm](../entities/installation-peter-sm.md)'s second reading both were
  10 W, and the run reported "nothing measurable happened" for an inverter
  obeying its owner; with 10000 W in the third, all three checks acted. A 0 is not a limit: a dongle answers 0 for what it does not forward.
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
- **A stop is judged by its bracket, ahead of drift.** A check whose outcome
  is that something ceases (the PV cut, the charge ceiling) is `CONFIRMED`
  when the window during is under 200 W and both neighbours are at least
  500 W (`STOP_BRACKET_W`), however far apart those neighbours are. At
  [gerd](../entities/installation-gerd.md) the drift gate called two cuts to
  0 W inconclusive (2066 -> 0 -> 2516 W, 3063 -> 0 -> 2201 W); a cloud dims
  PV, it does not take it to 0 W and give it back.
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

## Timed windows

`--charge-window` writes a forced-charging window around the inverter's own clock (holding
5000-5005) and expects a charge; `--discharge-window` moves every discharge window away from now
and expects the discharge to stop. The ordinary restore puts every word back.

**The charge window works on P020, P022 and P023**: every run raised charge power while the
window was open (battery charge power before, during, after):

| Run | Before | During | After | Verdict |
| --- | --- | --- | --- | --- |
| [fwitten master, P023, cable](../sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan-2-summary.md) | 3258.5 W | 3599 W | 3339.5 W | did as it was told |
| [gerd, P022, WiNet-S](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-2-summary.md) | 1656 W | 4400 W | 1681.5 W | did as it was told |
| [gerd, P022, cable](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-2-summary.md) | 2218 W | 4399.5 W | 1875 W | could not tell |
| [mkaiser, P020, cable](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-2-summary.md) | 772 W | 4499 W | -245.5 W | could not tell |

The two "could not tell" were the rule's, not the inverter's. A [2 s trace](../sources/mkaiser-charge-window-trace-2026-11-01-summary.md) at mkaiser shows
the window starting a flat 4499 W charge within 4 s and stopping within 2 s of the enable going
back, with no rebound; the house then drifted as PV fell. So **a start is now judged by its
bracket, ahead of drift**: a window standing `WINDOW_START_W` above both neighbours is the
setting's doing, as a stop between two windows of real power is (`STOP_BRACKET_W`). And the wait
after the window is 20 s, not 60. Replayed, all four runs confirm; at mkaiser the fixed check
confirmed live.
**The discharge window works on P020 and P022**: moving every window away from now stopped the
discharge and the restore brought it back (battery discharge power before, during, after):

| Run | Before | During | After | Verdict |
| --- | --- | --- | --- | --- |
| [gerd, P022, cable](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-3-summary.md) | 3799 W | 0 W | 3800 W | did as it was told |
| [mkaiser, P020, cable](../sources/mkaiser-discharge-window-2026-11-04-summary.md) | 722.5 W | 0 W | 719 W | did as it was told |

The check needs the battery discharging at least 500 W: a first mkaiser run at 495 W skipped it,
naming the floor, and a run with the house load raised passed. The snapshot's windows were 00:00
to 24:00 at mkaiser, so the stop is the window leaving "now", not a switch.

## Drivers

The engine is the package `src/sungrow_modbus/control_test/`, one module per
phase (`preflight`, `readback`, `effects`, `restore`) put together in
`engine.py`, so both drivers share it:

- `device-survey/scripts/python/sungrow_control_test.py`, through the
  survey;
- the **Run control write test** button on the device page.

Both publish into one survey document (the `control_test` block).
Every survey with such a block is tagged `control-test` in the
[index](../index.md).
