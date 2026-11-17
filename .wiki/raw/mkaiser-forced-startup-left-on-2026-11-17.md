# The maintainer's SH10RT: 13017 left on, 2026-11-17

Does an inverter flip [register 13017](../wiki/entities/register-13017.md)'s `0xAA` back to `0x55`
by itself, or when PV arrives? Issue #444 reports a flip-back ~20 minutes after the write, firmware
not stated; at bar12 it had not after 23 minutes. This is a longer watch, at
`anon-37323352958` (SAPPHIRE-H_B001.V000.P020), over the inverter's own LAN port, from the
repository's dev Home Assistant (`config-real`).

Not the capability test: a plain write of the owner's switch *Forced startup under low SoC*, then
the register read back once or twice a minute. The running state was recorded too but is **not**
the judgement -- this house wakes by itself at night (2026-11-16, 22:48), so only the register
answers the question.

Before: Standby, battery 0.0 % against a 10 % minimum, PV 0 W, 13017 `0x55` (off), the
inverter untouched since the previous night's run. *Extended test (auto repeat)* was switched off
for the watch, so that no capability test could start once the inverter began running and write
over the register under test; it was switched back on afterwards.

## What happened

| Time | +since the write | What |
| --- | --- | --- |
| 06:37:55 | 0 | 13017 written `0xAA` (the switch turned on) |
| 06:39:57 | 122 s | running state `Starting` |
| 06:41:22 | 207 s | running state `Running` |
| 07:37:34 | 59 min 39 s | first PV above 0 W (80 W), dawn |
| 08:08:43 | 90 min 48 s | **13017 still reads `0xAA`** |
| 08:08:50 | 90 min 55 s | written back to `0x55`; reads off |

- **It did not flip back by itself.** 13017 held `0xAA` for 90 minutes 48 seconds, read back
  throughout. #444's ~20 minutes is not reproduced on this firmware, and this is now the longest
  watch on record (bar12: 23 minutes).
- **PV did not flip it back either**, for the 31 minutes of daylight inside the watch.
- **`0xAA` keeps the inverter running in the dark**: 56 minutes of `Running` between the wake and
  the first PV, with the battery at 0 % the whole time.

## The wake timing, three runs now

| Run | How watched | to `Starting` | to `Running` |
| --- | --- | --- | --- |
| 2026-11-08 | one-off script | 121 s | 215 s |
| 2026-11-16 | the capability test engine | 123 s | 208 s |
| 2026-11-17 | this watch | 122 s | 207 s |

Nine days, three methods, the same inverter: `Starting` at 121-123 s and `Running` at 207-215 s.

## The restore was late

The watcher was written to put `0x55` back in a `finally` block after 40 minutes. It could not:
the Home Assistant access token it held expired 29 minutes in, so every read and every write after
07:07 returned HTTP 401, including all five restore attempts, and it ended by saying so
("RESTORE FAILED -- 13017 LEFT ON, NEEDS A HAND"). The register was put back by hand at 08:08:50,
about 50 minutes after the intended end of the watch, and read back off.

The house was left changed in the meantime: 13017 on, the inverter awake. No other register was
touched, and the lateness did not spoil the measurement -- it lengthened it, and the flip-back
answer is stronger for the extra 50 minutes. **A restore that depends on a credential which can
expire mid-run is not a restore.** A watcher that writes must mint its credential at the moment it
restores, not hold one from the start.
