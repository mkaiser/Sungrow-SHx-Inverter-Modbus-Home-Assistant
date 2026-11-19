# T036 - Let the discharge windows be written

**The discharge windows read, and nothing writes them.** Registers
33151-33158 (weekday) and 33179-33187 (weekend) are in no Sungrow document
(#785); Korsberg has driven them for years, and the integration shows them as
four read-only derived sensors (`weekday_discharge_window_1` and its three
siblings, `Capability.DISCHARGE_SCHEDULE`).

## The evidence is in, and it is why this is no longer blocked

The capability's own words say "read only until a watched write confirms what
writing does". That write has happened **twice**, both times moving every
window away from now and watching the battery stop:

| Run | Before | During | After | Verdict |
| --- | --- | --- | --- | --- |
| [gerd, P022, cable](../.wiki/wiki/sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-3-summary.md) | 3799 W | 0 W | 3800 W | did as it was told |
| [mkaiser, P020, cable](../.wiki/wiki/sources/mkaiser-discharge-window-2026-11-04-summary.md) | 722.5 W | 0 W | 719 W | did as it was told |

Both restored whole, every schedule word read back original. That is the same
standard that granted `PV_GENERATION_CUT_CONTROL`, and it is met here on two
firmwares.

## What to build

1. **`Capability.DISCHARGE_SCHEDULE_CONTROL`**, never probed, granted by
   `resolve` only where `DISCHARGE_SCHEDULE` answered **and** the firmware is
   in `CONFIRMED_ON_FIRMWARE` -- `SAPPHIRE-H_B001.V000.P020` and
   `SAPPHIRE-H_B001.V000.P022`, the two above. `CONTROL_REQUIRES` carries the
   read it depends on, so a firmware entry can never grant control over a
   block this device does not answer.
2. **The sixteen window registers `writable=True`** in `registers.py`, and
   33179 (the weekend enable, `0xAA`/`0x55`) as a switch beside the
   forced-charging enable.
3. **Eight `TIMES` entries** (`scripts/generate/tables/writes.py`), one per
   start and end of weekday windows 1 and 2 and weekend windows 1 and 2,
   `requires` the new capability; then `make gen` for
   `time_descriptions.py`, `switch_descriptions.py`, `strings.json` and both
   translations, with names in `naming.py` and `german_texts.json`.
4. **Tests**: that the entities appear only on the two firmwares, that they
   are absent where the read capability is absent, and the write path.

## Decide first: the hour that is 24

**A window here ends at hour 24, and a Home Assistant `time` entity cannot
hold it.** `InverterDischargeWeekday`'s own words record hours **0-24**, 24:00
being the end of the day, and the maintainer's snapshot had every window at
`00:00 to 24:00` -- the factory state, and the one every untouched house is
in. A `time` entity takes 00:00 to 23:59, so the eight `TIMES` entries of step
3 can read such a window but can never write it back, and an owner who nudges
one window can never restore the other.

The forced-charging windows do not have this problem: V1.1.16 documents them
as 0~23, which is why `TIMES` fits them.

Three ways, and the choice is the maintainer's:

- **23:59 instead of 24:00.** One minute of the day is lost and every
  untouched window silently rewrites itself on the first save. Cheap, and
  wrong in a way nobody would see until they looked.
- **A `time` entity per window, plus a switch for "to the end of the day"**,
  which writes 24:00 to the end hour. Honest, and two entities for one idea.
- **Numbers rather than times**: four `number` entities per window, hour
  0-24 and minute 0-59. Ugly beside the forced-charging windows, which are
  `time`, and the inconsistency is itself a bug report waiting to happen.

**Answered 2026-11-19 (maintainer): a `time` entity per edge, plus an "all
day" switch per window** that writes hour 24, minute 0 to the end. So the
factory state reads as `00:00` with the switch **on**, and turning the switch
off hands the end back to its `time` entity. That keeps the forced-charging
windows and these the same shape, which is what a reader compares them
against, and costs one switch per window -- four in all -- rather than a
minute of the day or sixteen numbers.

Step 3 therefore adds eight `TIMES` entries **and** four switches, all
requiring the new capability.

## Not in this item

- **P023 and SBR houses** have never run the discharge-window check (T037):
  the capability stays off there until one does.
- **Writing a window the inverter is inside** is what the capability test
  avoids by moving windows *away* from now. What an owner's write does mid
  window is unmeasured, and the entities should not pretend otherwise.

## Status log

Newest first.

### 2026-11-19 -- scoped, and stopped on the 24:00 question

Read the two runs, the capability's gating, the `TIMES` generator and the
registers. The build is four steps and none of them is hard; the entity shape
is a real decision and it is the maintainer's, so it is written up above and
nothing is built yet. Next: their answer, then steps 1-4 in one commit with
the capability and its tests.

### 2026-11-19 -- built, all four steps

1. **`Capability.DISCHARGE_SCHEDULE_CONTROL`**, never probed, in
   `CONFIRMED_ON_FIRMWARE` for `SAPPHIRE-H_B001.V000.P020` and
   `SAPPHIRE-H_B001.V000.P022` with both runs cited, and in
   `CONTROL_REQUIRES` against the read. `resolve` needed no change: it
   already adds a confirmed write where the read it acts on resolved.
   Checked: P020 with the read grants it, P023 does not, and no read means
   no control on any firmware.
2. **The sixteen window registers and the weekend enable are `writable`**,
   with why in `InverterDischargeWeekday`'s own words, including what hour 24
   costs.
3. **Eight `TIMES` entries, four `WINDOW_ENDS` switches and the weekend
   enable**, generated into `time_descriptions.py` and
   `switch_descriptions.py`, with English and German names. The platform
   learned one thing: a switch with a `minute_field` writes a time rather
   than a mode code, hour then minute, in the order `SungrowTime` uses.
4. **Tests**: the shape of an *all day* switch, that all four windows have
   one, and that every discharge control is gated on the watched-write
   capability.

**The sub-decision the shape left open: what *all day* writes when turned
off.** There is nothing to hand back to -- while the switch was on, the end
held 24:00 and the `time` beside it showed nothing, so no previous value
exists. It writes **23:59**, the latest a `time` can hold, and the owner sets
the end they want from there. The alternative, refusing to turn off until a
time is set, makes a switch that will not switch.

### 2026-11-19 -- the two guards the new control had to pass

The full suite failed twice, and both failures were the procedure asking to
be followed rather than bugs.

**Every writable register is probed or excused** (`test_capability_test.py`).
The seventeen new writable fields are now excused in
`procedure.NOT_PROBED`, beside the forced-charging schedule and for the same
reason: hours, minutes and one mode flag count in ones, so a readback walk
has no scale to catch, and a window written into the schedule decides when
the battery may discharge. They are written only by the discharge window
check, which moves every window away from now and judges by the battery
stopping.

**Nothing is confirmed without a document that shows it**
(`test_pv_generation_cut.py`). This control is the first whose two firmwares
are evidenced *differently*: P022 by gerd's committed diagnosis (`discharge
windows away from now`, confirmed), P020 by the maintainer's raw note -- that
house's own diagnosis says *could not tell*. The test partitioned
capabilities into "the cut, from diagnoses" and "everything else, from raw
notes", which no longer holds, so it now carries both tables and asks each
firmware for **either** kind of evidence. Checked that each half is
load-bearing: P020 passes only by the note, P022 only by the diagnosis, and
P023 satisfies neither, which is what keeps it out.
