---
type: source
title: gerd-forced-startup-and-restart-2026-11-22.md
source_path: raw/gerd-forced-startup-and-restart-2026-11-22.md
ingested: '2026-11-22'
created: '2026-11-22'
tags: [register-13017, register-13000, forced-startup, restart, standby, sh80rt-v112, sapphire-h-b001-v000-p022, gerd, capability-test, write]
---

# Forced startup on P022, and a restart with one start, gerd, 2026-11-22

`.wiki/raw/gerd-forced-startup-and-restart-2026-11-22.md` records a watched night window at
[gerd](../entities/installation-gerd.md)'s SH8.0RT-V112 on
[P022](../entities/firmware-sapphire-h-b001-v000-p022.md), over the cable through the Modbus
proxy, with both of his Home Assistant's entries disabled, battery at 0.3 % against its 10 %
minimum and no PV. It answers the forced startup on P022
([register 13017](../entities/register-13017.md)) and what the inverter reports between the
repeated start commands of a restart ([register 13000](../entities/register-13000.md)).

| Claim | Evidence | Status |
| --- | --- | --- |
| 13017 is a switch on P022 too: 0xAA wakes low-SoC standby, 0x55 sends it back | capability test's forced startup mode: left standby 163 s, Running 208 s, Standby 17 s after 0x55, "did as it was told", exit 0 | one engine run |
| 13017 read the factory 0 before | no forced-startup check had run there | read |
| A second wake can be slower | 0xAA by hand: Starting 241 s, Running 329 s; a third: 235 s, 321 s | two hand writes |
| On 0xAA the inverter runs in the dark with the battery idle | Running, DC 0 W, battery 0 W, SoC 0.2-0.3 % | three wakes |
| A restart stops in ~2 s, to Key stop `0x0002` | 2.2 s (engine), 2.6 s (script) | two runs |
| One start is enough; the night boot waits in Standby | single 0xCF: Key stop -> Standby in 3 s, Standby 279 s, Starting, Running at 369 s | one run, every word logged |
| The engine's re-sends change nothing | five starts (four re-sends at 60 s): Running at 368 s | one engine run |
| Settings survive the restart; no fault word set | settings survived: True; 13050-13057 all 0 | two runs |
| A dry run of the forced startup waited out the 10-min deadline | published 0.1.0a48; fixed, the fixed dry run ends at once | fixed and rerun here |
| `--restart-only` was refused at night ("Only 0 W of PV") | a restart writes no control; fixed, rerun here | fixed and rerun here |

What changed in the code: P022 joins `CONFIRMED_ON_FIRMWARE` for
`Capability.FORCED_STARTUP_CONTROL`; `async_ensure_running` counts Standby after a start as
progress (`is_standby`); the forced startup dry run returns "not run" at once; a restart alone
passes the dark guard.

Not measured: whether P022 flips 0xAA back by itself (#444); a restart in daylight with one
start; the same through the WiNet-S.
