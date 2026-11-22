---
type: entity
title: Register 13000 (running state)
tags: [register, input, running-state]
created: '2026-10-29'
---

# Register 13000 (running state)

Input register 13000, the inverter's running state. The whole map is
`derived.RUNNING_STATES` (`src/sungrow_modbus/hybrid_inverter/derived.py`), and the
running and stopped sets are derived from its labels.

- **`0x0000` is "Running", not off.**
- **A [WiNet-S](device-winet-s.md) re-encodes it**: cable 0x0040 becomes
  0x0000, and 0x0080 becomes 0x8100. So a code seen only through a dongle says
  nothing about what the inverter sends, and the duplicates in the map are
  the dongle's. Read over both paths at once at [bar12](installation-bar12.md) on P023: cable
  0x0008 Standby is the dongle's 0x1400, cable 0x0020 Starting its 0x1600, and 0x0800 (forced
  mode) the same on both ([the run](../sources/bar12-import-limit-2026-11-07-summary.md)).
- **`0x0020 Starting`** is most of the wait after a Modbus start.
  `is_starting` recognises it.
- **One `0xCF` is enough; a night boot waits in Standby.** At [gerd](installation-gerd.md)'s
  SH8.0RT on P022, at night, a single start went Key stop `0x0002` -> Standby `0x0008` within
  3 s, stayed in Standby 279 s, then Starting, and Running at 369 s -- the same as a run that
  re-sent the start four times (368 s)
  ([the run](../sources/gerd-forced-startup-and-restart-2026-11-22-summary.md)). So
  `async_ensure_running` treats Standby after a start as progress (`is_standby`) and re-sends
  only while the word still reads a stop, in case the command was lost; every
  capability-test driver calls it on the way out. See the
  [capability test](../concepts/capability-test.md).
- **But Standby can also be where it stays.** At [peter-sm](installation-peter-sm.md)'s SH10RT-V112
  on P023, a stop after dark with the pack at 1.0 % (under its 5 % minimum) read `0x0008` at once,
  and after the start it stayed in Standby past the ten-minute deadline: with no PV and an empty
  pack there is nothing to run on. Standby after a start is progress only where the inverter has
  something to start for
  ([twenty-third reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-21-summary.md)).
- **A day of polling produces very few codes.** Over 1470 one-minute polls
  spanning 30 hours at [mkaiser](installation-mkaiser.md) on P020, over the
  cable, only four appeared and every one was in the map: Standby 1013,
  Running 452, Stop 4, Starting 1
  ([the day of polls](../sources/mkaiser-day-of-polls-2026-11-18-summary.md)).
  **`Starting` was caught once**, so a code's absence from such a listing is
  not evidence the inverter never entered it: a transient state is sampled by
  luck at that cadence.
