# T092 - The daily counter's `last_reset` through a midnight

*Daily consumed energy*'s `last_reset` (T091, `src/sungrow_modbus/hybrid_inverter/daily_cycle.py`) has run in tests
only. One midnight on a real house. It was to come before the release; the maintainer released 0.1.0a57 without it and deferred it, 2026-11-25.

## Status log

- **2026-11-25**: 0.1.0a57 is released (PyPI, GitHub, the preview mirror pinned), without this test. Written, nothing run. The branch head for it is `762427a` (full gate green: 9756 passed) or later; it is
  not released, and `762427a` is not pushed. What 0.1.0a57 carries so far: T091, the switch to device-scoped ids moving an adopted id
  with a number on it (T084), the diagnosis texts in German (T007), the History fixes (T055).

## Where

The maintainer's own house (recommended: the normal case, nobody else's) or gerd's. Either needs the maintainer's word for the
install and for which house.

- The maintainer's: the API answers; **the SSH key was lost in the container rebuild**. A new one goes into the *Advanced SSH & Web
  Terminal* add-on, which the `ssh-access` skill's script (repository `mkaiser/homeassistant`) does not support: the maintainer
  pastes the public key, or says to change the add-on's options.
- gerd's: key and tunnel work. Auto repeat is on on both entries: stop it before, start it after, controls held by no test.

## Steps

1. The wheel of the release under test (`make wheel`, or the Marketplace if the house takes the preview) into the house's `/config/sungrow_build/`, required by file URL in the manifest; keep the old
   `custom_components` folder as a backup; restart Home Assistant; both entries load, no error in `system_log/list`.
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
