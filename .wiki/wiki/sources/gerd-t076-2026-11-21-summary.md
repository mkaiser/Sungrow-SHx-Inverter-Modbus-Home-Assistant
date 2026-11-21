---
type: source
title: gerd-t076-2026-11-21.md
source_path: raw/gerd-t076-2026-11-21.md
ingested: '2026-11-21'
created: '2026-11-21'
tags:
  - capability-test
  - discharge-window
  - start-threshold
  - deployment
  - gerd
  - sapphire-h-b001-v000-p022
---

# gerd's own Home Assistant, 2026-11-21 evening: the capability test's fixes installed

The released 0.1.0a46 plus the three capability-test fixes of the day, installed on
[gerd](../entities/installation-gerd.md)'s Home Assistant over SSH, then one extended run with the test
history cleared and the restart not allowed. Source: `raw/gerd-t076-2026-11-21.md`. SH8.0RT-V112 on
[P022](../entities/firmware-sapphire-h-b001-v000-p022.md), battery 15-18 %, after dark.

| Fact | Evidence |
| --- | --- |
| **Moving every discharge window away from now stops the discharge on P022**: 533.5 W, 0 W, 468 W | the run's effect row |
| **The discharging start threshold (33150) stops a discharge under it**: 1000 W over 497.5 W, 0 W during, 646.5 W after | the run's effect row |
| Forced charge 1250 W measured 1250 W; the forced-charging window charged 4399 W; the site import limit held 1320 W at 1322 W | the run's effect rows |
| The five power limits store a step over their maximum, `battery_max_soc` refuses 101 % with 0x04, again | the run's upper-bound rows |
| 13052's 8000 W, outside its battery-derived bounds, was written back to itself and taken, so the run tested it as before | the run, 13052 restored "already holding its original value" |
| A URL requirement in a custom integration's manifest is always passed to the installer, so a local wheel can stand in for a release | `homeassistant.util.package.is_installed` |
| After a run the step sensor kept what the last tick said during it ("a run is in progress") for up to a minute, until the next tick; now it looks again as the run ends | the sensor against *last finished* |

Exit 0, everything restored, no restart. The morning's "discharge windows: not supported"
([the day](gerd-auto-repeat-2026-11-21-summary.md)) is overturned: it was a procedure error, and this run
on the fixed procedure confirms the windows.
