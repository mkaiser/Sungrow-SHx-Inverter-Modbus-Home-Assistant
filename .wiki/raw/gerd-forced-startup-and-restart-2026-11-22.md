# gerd: forced startup (13017) on P022, then a watched restart, 2026-11-22

Watched night run at gerd's SH8.0RT-V112 (`SAPPHIRE-H_B001.V000.P022`, SBR096,
stand-in anon-00267885816), over the cable through the Modbus proxy on his Home
Assistant host, unit 1. Both of his Home Assistant's sungrow_modbus entries
(inverter and AC22E-01 wallbox) were disabled for the run, so nothing else polled
or wrote. Times are CET. A side logger read input 13000-13002, 13050-13057,
13022-13023, 5017-5018 and holding 13017 every ~3 s through the same proxy,
printing a line on every change.

## Before

05:46 CET: running state 13000 = `0x0008` (Standby), 13001 = `0x0028`, battery 0.3 %
against its 10 % minimum (HA's nominal 10.3 %), DC power 0, every fault word 0,
**13017 = 0**, the factory value: no forced-startup check had run here before.

## Dry run

`diagnosis.sh tests <proxy> --forced-startup --dry-run --yes` on the published
0.1.0a48 sat in "forced startup under low SoC", polling, for the whole 10-minute
wake deadline: the dry run skipped the write and then waited for a wake that
could not come. Fixed in the library (the check returns "not run" at once in a
dry run); the fixed dry run against gerd finished at once, preflight admitted
low-SoC standby (SoC 0.3 %, PV 0 W), exit 0.

## The forced startup (T063)

`--forced-startup --yes`, started 05:54 CET, on the fixed library.

- 05:54:55: 13017 reads `0xAA` (170); running state still `0x0008`.
- 05:56:58: running state `0x0020` (Starting), 13017 still `0xAA`.
- 05:58:22: `0x0040` (Running). DC power 0, battery power 0, SoC 0.3 %: running in the dark on 0xAA alone, battery idle.
- 05:58:25: the check writes `0x55` (85).
- 05:58:41: `0x0008` (Standby) again.
- Every fault and alarm word (13050-13057) read 0 throughout.

The run's own verdict: "the inverter did as it was told -- left standby after 163 s;
running after 208 s; back in standby 17 s after 0x55", exit 0, one dropped
connection re-opened (the side logger shares the proxy). 13017 is left at `0x55`:
the factory 0 is refused by the register, so the restore keeps the off word.

## The restart (T032)

The forced startup check ends in standby, and a restart needs a running inverter,
so 13017 was set to `0xAA` by hand at 05:59:18 (read back `0xAA`) to hold it running
through the restart, and set back to `0x55` afterwards.
- The second wake was slower: Starting (`0x0020`) at 06:03:21, 241 s after 0xAA, a
  brief SoC tick to 0.2 % at 06:04:34, Running at 06:04:47, 329 s after 0xAA.
- 06:05: the first `--restart-only` was refused before any write: "Only 0 W of PV".
  A restart alone writes no control and needs no sun, so the PV guard should not
  apply to it; fixed in the library (`restart_only` passes the dark guard as
  `--allow-dark` does), and rerun.
- Rerun, `--restart-only --restart --yes`, started 06:07:52, with 13017 at `0xAA` and the
  inverter Running at 0.2 % SoC, no PV. With three clients on the proxy (the run, the
  side logger, a one-off probe) the link stopped answering for ~2 minutes before the
  stop; the side logger was stopped at 06:10 to give the run the link, so the words
  between the starts were not logged by it.
- The run: stopped after **2.2 s** (stop word `0x0002`, Key stop), **four** "still stopped
  after 60s, sending start again" (five starts in all), Running again after **368 s**,
  generating not measured (night), settings survived, 0 polls refused, exit 0.
- 06:22:21: 13017 set back to `0x55` by hand (read back `0x55`).

So the repeated starts of 2026-11-03 and 2026-11-10 reproduce: the engine re-sends
every 60 s while the state reads stopped, and a night start here takes over 6 min.
What the re-sends do is the next run's question: one start only, every word logged.

### One start only, every word logged

A script on one connection (nothing else on the link): 13017 = `0xAA` at 06:23:24,
waited for Running, stop, then **a single start**, watched up to 10 min with no re-send,
reading 13000 (input and holding), 13001, 13017 and 13050-13057 every ~2 s.

| CET | t (s) | Event / word |
| --- | --- | --- |
| 06:23:24 | 0 | 13017 `0xAA` written; Standby `0x0008` |
| 06:27:19 | 235 | Starting `0x0020` |
| 06:28:45 | 321 | Running `0x0040` |
| 06:29:05 | 341 | **stop** `0xCE` written (holding 13000 reads back 206) |
| 06:29:08 | 344 | Key stop `0x0002` (2.6 s after the stop) |
| 06:29:18 | 354 | **start** `0xCF` written, the only one (holding 13000 reads back 207) |
| 06:29:21 | 357 | Standby `0x0008`, 3 s after the start |
| 06:34:00 | 637 | Starting `0x0020`, 283 s after the start |
| 06:35:27 | 723 | Running `0x0040`, **369 s after the one start** |
| 06:35:58 | 754 | 13017 `0x55` written |
| 06:36:23 | 779 | Standby `0x0008` |

Every fault and alarm word read 0 throughout; 13001 stayed `0x0028`.

**So one start is enough.** The engine's run with five starts came back in 368 s; one
start came back in 369 s. What the inverter reports between the starts is Standby:
after a start it leaves Key stop at once and waits in Standby for ~4.5 min at night
before Starting. The engine counted Standby as stopped and re-sent every 60 s into a
boot that was already under way, which is the "start sent three times" of 2026-11-03
and 2026-11-10. Fixed: after a start, Standby is progress like Starting, and only a word
still reading a stop earns a re-send.

### The fix on hardware, in daylight

08:52 CET (the inverter already Running on PV, 147 W; 13017 `0xAA` written first and
`0x55` after): `--restart-only` on the fixed library sent **one start, no re-send**:
stopped after 2.2 s, Running after 180.0 s, generating 5.2 s after that, settings
survived, exit 0. The daylight time matches the 180.8 s of 2026-11-03, which took three
starts. 08:57: both Home Assistant entries re-enabled.
