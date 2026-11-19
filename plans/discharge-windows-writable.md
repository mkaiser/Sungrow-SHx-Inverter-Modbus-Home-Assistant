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
