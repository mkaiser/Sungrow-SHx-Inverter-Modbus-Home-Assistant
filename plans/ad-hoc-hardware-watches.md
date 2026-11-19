# T012 - A safe pattern for ad-hoc hardware watches

**A safe pattern for ad-hoc hardware watches.** A one-off watcher that
writes to the house and restores in a `finally` block left the
maintainer's 13017 on for 50 minutes past its window on 2026-11-17: it
held a Home Assistant access token from the start, the token expired 29
minutes in, and all five restore attempts returned HTTP 401. The
measurement survived, the house did not go back when it should have, and
only a person noticing put it right (wiki: 13017 left on). The shipped
capability test is not affected -- it restores over its own Modbus
connection, with no credential to expire. What is wanted is a small
helper for these one-off scripts under `scripts/dev/`: mint the
credential **at the moment of restoring**, never hold one from the start,
retry the restore until the register reads back, and fail loudly where a
person will see it rather than in a background log.

It should also **look before it presses**. On 2026-11-17 a script pressed
*Diagnosis: stop* 21 seconds after auto repeat had started a run of its
own, interrupting it, and the capability test it then asked for was
refused ("a diagnosis is already running on this inverter") -- which left
the script's `finally` unable to re-arm auto repeat, so it stayed off
until a person noticed. The run's restore completed and nothing was left
changed, but the lesson is cheap: read `running_since` on *Diagnosis: test
summary* first, and treat a run in flight as a reason to wait rather than
something to press through.
