# T092 - The daily counter's `last_reset` through a midnight

*Daily consumed energy*'s `last_reset` (T091, `src/sungrow_modbus/hybrid_inverter/daily_cycle.py`) has run in tests
only. One midnight on a real house. It was to come before the release; the maintainer released 0.1.0a57 without it and deferred it, 2026-11-25.

## Status log

- **2026-11-25, 08:35 CET**: 0.1.0a57 is released (PyPI, GitHub, the preview mirror pinned), without this test. The maintainer's house
  and gerd's both run it through the Marketplace, with the tests' history cleared (readings kept) and auto repeat running, so each
  inverter meets its next midnight with the new code and nobody is watching it. What is left is the watching: steps below, now with the
  hourly statistics saved *beforehand*, which has not been done. Not understood: gerd's wallbox entry still reads 1/9 tests passed after
  the clear, with its step at "never run".

## Where

Both the maintainer's house and gerd's already run 0.1.0a57, so nothing needs installing: the test is watching one midnight
(the maintainer's house is the normal case; at gerd's the pack is nearly empty and the day's counters are small). Reading needs only
the token of either: the maintainer's through the API, gerd's through the tunnel.

## Steps

1. Both houses run 0.1.0a57 from the Marketplace already; check that the integration folder still reports it (`manifest/get`) and
   that no restart ended auto repeat since (a restart does).
2. Before midnight: save the states of the daily consumed energy and its smoothed twin, their attributes, and the hourly statistics of both.
3. From 23:45 to 00:30 CET: read the state, `last_reset` and the five input counters every minute. The reset of the inverter's day may not be
   at 00:00: the counters say when.
4. In the morning: the hour with the reset, and the day's change. Then restart Home Assistant once in daylight and
   once across a reset if that can be arranged.

## Passes when

- `last_reset` is set once, at the poll where the counters have begun again, and not before the first reset seen.
- The state keeps the old day's value until all five have begun again (ten minutes at most), then starts near zero.
- The statistics' change over the new day equals the state, with no negative hour at the reset; the smoothed twin the same.
- A restart neither sets `last_reset` again nor loses it.

## After

Passed: T091's question at #797. Failed: the readings go into
the wiki and the code is fixed first. Put the house back on a release from the Marketplace afterwards.
