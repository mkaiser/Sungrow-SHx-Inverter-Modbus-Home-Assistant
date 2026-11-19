# T016 - The midnight-reset check judges by the wrong clock

**The midnight-reset check judges by the wrong clock.**
Found on hardware 2026-11-17, the readings checks' first failure anywhere,
and the inverter did nothing wrong
([the note](.wiki/wiki/sources/mkaiser-midnight-reset-2026-11-17-summary.md)).
`daily counters reset at midnight` recorded `daily_pv_generation fell from
4.4 to 0 at 23:04`. The development instance keeps UTC, the inverter keeps
German local time -- an hour ahead, measured in run 2's `inverter_clock` --
so the counter reset at **00:04 on the inverter's own clock**, to a clean
zero, and was judged against Home Assistant's midnight instead.

A daily counter resets on the **inverter's** clock, and nothing makes a
Home Assistant share its inverter's timezone. The observation is stamped
`dt_util.as_local(now)` in
`custom_components/sungrow_modbus/diagnosis.py`, and `_near_midnight` in
`src/sungrow_modbus/capability_test/plausibility.py` spans 23:30 to 00:30
of that clock.

**The clock is already collected** -- `inverter_clock` sits in every run's
`conditions` -- so the fix is to judge the fall against it, and to say so
when the two disagree: an inverter whose clock is set wrong is a real
condition, worth reporting as itself rather than as a counter that
misbehaves. Raise the check's revision in the same commit, per T015.

**It is one failure a night, not one failure.** The next night repeated it
to the minute -- `daily_pv_generation fell from 1.6 to 0 at 23:03` beside
the previous `4.4 to 0 at 23:04`, both 00:03 and 00:04 on the inverter's
own clock, both to a clean zero
([the second night](.wiki/wiki/sources/mkaiser-midnight-reset-night-2-2026-11-18-summary.md)).
So the inverter's counters are sound, measured twice, and the defect is
systematic: it fires every night a Home Assistant's timezone differs from
its inverter's.

It is also **sticky, and it grows**. `EventCheck.observe` keeps judging
after a failure and appends each *distinct* sentence, keeping the last
five, while `verdict()` returns the failure for as long as any is held,
whatever `passes` reaches. Each night's sentence carries that day's kWh
figure, so it is distinct and is appended rather than folded in. Raising
the revision clears the row; only the clock fix keeps it clear.

**Correction**: raising the revision does
*not* clear a readings row. `CHECK_REVISIONS` is consulted by `_current` in
`ledger.py`, which only the readback and effect tables pass through, while a
readings row joins the summary straight from `Plausibility.summary()` through
`with_plausibility` and carries no revision. Clearing one takes *Diagnosis:
tests, clear history* (the whole ledger) or a `plausibility.SCHEMA` bump
(every check's evidence). Worth its own decision: whether readings checks
should carry revisions like the write paths, so one can be re-asked alone.

## Status log

Newest first.

### 2026-11-19 -- built: the inverter's clock judges it, and a corrected check forgets

**The clock.** `_inverter_time` reads the six `system_clock_*` fields the
`clock` component already polls (holding 5000-5005, slowest tier) and
`_daily_resets` judges `_near_midnight` on that, falling back to Home
Assistant's and saying so where the inverter's did not read. Replaying the
house that found this -- Home Assistant on UTC, the inverter an hour ahead --
turns the recorded failure into:

> `pv_generation 4.4->0 reset at 00:04 by the inverter's clock, where Home
> Assistant read 23:04, the rest at zero`

**Both readings, no arithmetic.** The sentence prints what each clock read
rather than an offset in minutes, because the inverter's clock is polled
every 600 s and a stale reading would understate an offset computed from it.
Two measured numbers beside each other say the same thing and cannot be
wrong. They are printed only when the two differ by two minutes or more.

**Staleness is inside the window.** The clock is up to one poll of its
component old, 600 s by default, against a `_near_midnight` span of an hour,
so a reset at 00:04 reads somewhere in 23:54-00:04 and is judged as the
midnight it is. A fall at noon still reads at noon and still fails.

**What was decided, which the plan left open: readings checks carry
revisions.** `CHECK_REVISIONS` and `revision_of()` in `plausibility.py`,
`daily counters reset at midnight` on **2**. `as_dict` stores a revision per
check and `from_dict` drops the state of a check whose revision has moved,
that check alone. Checked against the real stored state from 2026-11-17: the
`4.4 to 0 at 23:04` failure is dropped and `lifetime counters never fall`
keeps its 926 passes.

Why not the alternatives: a `SCHEMA` bump throws away every check's evidence
at every house to correct one, and `coverage.CHECK_REVISIONS` is the write
paths' table, which a readings row never passes through (the plan's own
correction). A readings check needs no re-asking either -- ordinary polling
fills a dropped row again with nobody pressing anything -- which is what
makes dropping one cheap enough to be the right answer.

Next: the tests, then the wiki and `Todo.md`.
