---
type: concept
title: The capability test
tags: [capability-test, writes, scale, diagnosis]
created: '2026-10-29'
---

# The capability test

Part B of a diagnosis. Part A answers "what is here" entirely by reading. Part B
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
B's scale is hand-typed. `tests/test_capability_test.py` makes the two meet, so a
decade error fails the suite on the commit that introduces it.

**Through a [WiNet-S](../entities/device-winet-s.md), only leg C survives**:
the dongle forwards the write and reads it back stale. A run through a
dongle says so above its readback table.

## Rules the procedure turns on

- **The restore comes first in every sense.** See
  [the restore](capability-test-restore.md).
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
  the limit named (`CapabilityTest._under_cap`). At
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
- **The button and the diagnosis always run `allow_dark`; the capability test on
  its own does not.** Somebody on Home Assistant OS has no terminal, and
  somebody who agreed at the end of a diagnosis has given the leave once. The
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

## Import limit

`--import-limit` writes [register 32998](../entities/register-32998.md), the site import limit,
under a forced charge it commands itself. It sizes a cap halfway between the import under the
charge and the import with no charge (load less PV), and judges import against that cap,
bracketed by the same forced charge before and after. A decade off would show as the wrong
scale. With the charge stopped, it then writes 0, 5001 and 5000 once each and records which
the inverter refuses, by exception type; a lost link is recorded as not answered. Every write
is followed by the snapshot's word, and the ordinary restore puts it back again. It skips
itself when PV covers most of the charge, so it measures best after dark.

**It confirms the cap on P020**: at mkaiser, over the cable, a cap of 1580 W took import from
2192 W to 1549 W and back to 2206 W, and 0 and 5001 were refused with 0x04
([the run](../sources/mkaiser-import-limit-engine-2026-11-07-summary.md)), as two runs by script had found
([night](../sources/mkaiser-import-limit-2026-11-07-summary.md),
[PV](../sources/mkaiser-import-limit-pv-2026-11-07-summary.md)).

**Opening the PV isolator is not the same as night.** With 0 W of PV the SH10RT first went to
Standby with the battery idle, and the run refused to start. Minutes later it was Running on the
battery and the next run went through ([the run](../sources/mkaiser-import-limit-engine-2026-11-07-summary.md)).

## Several runs, one document

One run answers only what its moment allowed: every behavioural check looks at
the house first and skips itself with a note. The import limit needs a charge
drawn from the grid, which PV covers at noon; the PV cut needs PV; the charge
ceiling needs a charging battery. Collected as separate notes, one situation
each, the import limit alone took five raw sources at
[mkaiser](../entities/installation-mkaiser.md).

So Home Assistant keeps every finished run per inverter firmware and folds
them into one schema-3 block (`sungrow_modbus.capability_test.ledger`;
`device-diagnosis/reference.md` has the shape). The strongest verdict per check
is shown, a decade finding outranks a later match and is listed as a
contradiction, and `still_missing` names what is still to come and why. The
device's **Diagnosis: test summary** sensor (with how long a run in flight has
taken) and a notification rewritten after each run show the progress; five
counters (**Diagnosis: tests passed**, *failed*, *not supported*,
*inconclusive*, *not run yet*, from `ledger.counts`) split the checks by
outcome as `n/total`; **Download diagnostics** carries every run.

Runs on different transports are never folded: through a
[WiNet-S](../entities/device-winet-s.md) a readback is the dongle's cache.

The terminal's `--merge-into` folds a run into a document's runs the same way.

The mode *Extended test (auto repeat)* does the coming back, on a diagnostics-only
entry only: an ordinary entry has no diagnosis entities, and its owner reaches
the capability test through the action. Pressing *Diagnosis: start* in that
mode is the leave: it lasts until *Diagnosis: stop*, and ends at every
restart. Every run it starts leaves out what the kept runs established, the
inverter restart included, so a restart is measured once per collection.
*Diagnosis: current step* says what it waits for. Once a minute it compares the polled readings with what each missing
check needs (`ledger.NEEDS`: the import limit needs PV under 200 W and room in
the battery, the PV cut needs PV above 700 W) and starts the ordinary run when
one is due: its own snapshot, its own restore, the entry's options as for the
button. At most one run in each 30-minute slot counted from the press of
*Diagnosis: start*, none while the inverter is not running, two minutes of
quiet after a run, no daily cap, and it switches itself off when nothing a
moment can answer is left (`custom_components/sungrow_modbus/continuous.py`).
A night of runs at [mkaiser](../entities/installation-mkaiser.md) showed why it
waits on the running state: ten runs started into low-SoC Standby, and each was
refused (the [fourth reading](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-3-summary.md)). A check the options
refuse is never waited for.

## Write paths and readings

Two kinds of check settle what a scale readback and a watched effect cannot
(`src/sungrow_modbus/capability_test/writepath.py`,
`src/sungrow_modbus/capability_test/plausibility.py`;
`doc/capability_tests.md` lists them):

- **Write paths**, inside a run: backup mode, load control and the weekend
  discharge enable written with their own word; the second forced-charging
  window read back with the schedule off, over a cable; each EMS mode option
  once, put back at once; and each number offered a step above its maximum,
  so a refusal records the bound the firmware enforces.
- **Readings checked against each other**, between runs while auto repeat is
  on: power against voltage times current, daily counters against the power
  that fills them, lifetime against daily counters, a meter's phases against
  its total. Read only, and how a *sensor's* scale is tested; a median a
  clean decade off is the finding, a ratio merely off is not. The rows count
  in the same counters, and auto repeat stays on until each has an answer.

Not measured on hardware yet.

## Drivers

The engine is the package `src/sungrow_modbus/capability_test/`, one module per
phase (`preflight`, `readback`, `effects`, `restore`) put together in
`engine.py`, so both drivers share it:

- `device-diagnosis/scripts/python/sungrow_capability_test.py`, through the
  diagnosis;
- **Diagnosis: start** on the device page, in an extended mode, and
  the `run_capability_test` action.

Both publish into one diagnosis document (the `capability_test` block; up to
schema 24 `control_test`), and the document's `features` section says per
feature set how far the run tested it. `doc/capability_tests.md` lists, per
capability, what each mode can establish and what is still untested.

The **forced startup** check is a mode of its own (`--forced-startup`, or the
action's `forced_startup: true`), because it needs the inverter in low-SoC
standby, the state every other check refuses: see
[register 13017](../entities/register-13017.md).
Every diagnosis with such a block is tagged `capability-test` in the
[index](../index.md).
