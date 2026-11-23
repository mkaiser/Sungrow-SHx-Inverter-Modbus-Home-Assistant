# T007 - The diagnosis and its capability tests

**The diagnosis and its capability tests.** In the code: the three
modes of *Diagnosis: mode* (read-only, extended test single run, auto
repeat), *Diagnosis: start* and *Diagnosis: stop*, a `features` section
in every document (schema 25), and the forced startup mode
(`diagnosis.sh tests <host> --forced-startup`). What each capability can
be tested with is `doc/capability_tests.md`. Left:
1. **The forced startup mode on other firmware.** The engine's own mode
  (`--forced-startup`, or the action's `forced_startup: true`) **ran on
  hardware 2026-11-16** at the maintainer's SH10RT on P020, from Home
  Assistant, in low-SoC standby after dark: left standby after 123 s,
  Running after 208 s, back in standby 16 s after 0x55, no finding, and
  the restore had nothing to put back (wiki: register-13017, the engine
  run). The mode itself is settled; what is left is **P022, P023 and the
  SH-T's 0x55 firmware**, each needing a house in low-SoC standby after
  dark, and the SH-RT's factory 0 going back as 0x55, the one
  `RESTORE_EQUIVALENT` (AGENTS.md), on a house that has never run it.
2. **The new checks on hardware** (`doc/capability_tests.md`). First
  run 2026-11-08 to 11-10 at peter_sm (P023, cable, five runs) and
  ra1k_0 (P071, WiNet-S, one run), ingested; what each took is on their
  installation pages. Not yet seen on hardware:
  - **the start thresholds**: **both done 2026-11-17** at the
    maintainer's, the first runs of either anywhere -- 1000 W commanded
    against 230 W of PV charging, charging stopped and came back at
    309 W; and an hour later against 205 W of discharge, stopped and back
    at 221 W (wiki: the charging start threshold, the discharging start
    threshold). The discharging one failed once first, on drift, which is
    how we know the gate at low power costs attempts rather than
    outcomes;
  - **`ledger.TWO_MOMENTS`**: a check established by day measured again
    at night, on one firmware; needs auto repeat across a dusk;
  - **the plausibility checks** (`capability_test/plausibility.py`): the
    first block from hardware came from the maintainer's production Home
    Assistant on 2026-11-15 (0.1.0a40, three runs, 26 of 53 checks
    settled, 0 failed); its diagnostics download is kept locally and is
    **still to ingest**, and the history was cleared for a fresh start.
    The dev instance's collection has run since 2026-11-16, re-armed
    2026-11-19 21:30 CET on `e8f1c84`. Read after that night's midnight it
    stands at **37 of 55** established (22 of 31 on the write side, 15 of
    24 plausibility), 0 failed, and what it is still waiting for says what
    the collection needs rather than what the code owes:
      - **export power limit** -- "export, or a battery to discharge into
        the grid"; **charge ceiling** -- "the battery charging, above
        55 %"; **upper bound of `battery_min_soc`** -- "the battery above
        57 %". These three are the write-side checks this house has never
        answered, and each wants a charged battery, which November has not
        given it;
      - **six other upper bounds** (`battery_max_soc`,
        `max_charge_power`, `max_discharge_power`,
        `forced_charge_discharge_power`, `charging_start_power`,
        `discharging_start_power`) -- each "a run", so auto repeat takes
        them as budget frees;
      - **nine plausibility checks**, which no run can force: three want
        three kilowatt-hours of flow (daily exported, battery charge,
        battery discharge), five want 2 kWh on a daily counter, and
        "battery level follows its power" wants 1 kWh through the pack.
        *Daily counters reset at midnight* and *lifetime battery counters
        contain each other* are answered (wiki: eight in one poll).
    So a re-armed auto repeat **will** want writing runs again -- there is
    real work left, which is worth knowing before parking it;
  - **anything on a WiNet-S beyond one run**, and any T-series cable.
  The night re-check and the plausibility checks need one auto-repeat
  collection at the maintainer's SH10RT over a day and a night, which
  may catch a slow PV charge for the threshold too; then ingest. The
  wallbox's tests are planned in `plans/T003-T004-T020-T039-T040-T059-wallbox.md`.
3. **Outside the repository**: issue #786's title still says survey, and
  the repository variable `SURVEY_ISSUE` keeps its name.
4. **Capability test runs over a day.** Home Assistant folds every run
  per firmware into one schema-3 block (`capability_test/ledger.py`, the
  *Diagnosis: test summary* sensor, a notification rewritten per run,
  *Diagnosis: tests, clear history*), and *Extended test (auto repeat)*
  starts runs when a missing check is due (`continuous.py`), leaving out
  what is established, the restart included. The terminal's
  `--merge-into` folds a run into the runs a document carries
  (`--replace` puts it in their place). Left:
  1. **The slot schedule on hardware**: one night at the maintainer's
     SH10RT, to see that low-SoC Standby starts no run and *Diagnosis: next
     start* names the next slot. **Half seen over the night of 2026-11-16
     to 11-17**: auto repeat ran from 21:16 to 06:37, **9 h 20 min of
     low-SoC Standby**, and started **zero** runs
     (`continuous_runs_started` 0 throughout), with the status line
     reading *waiting for changed test conditions: waiting for the
     inverter to run*. The inverter stirred once by itself at 22:48 for
     fifteen seconds and that was not enough to open a slot either. **The
     night of 2026-11-19 to 11-20 repeated it**: zero runs from 21:30 to
     00:25 CET, battery at 0 %, the same status line (wiki: eight in one
     poll). So that half is measured twice and settled. The other half
     still did not show: *Diagnosis: next attempt* stayed `unknown` with
     the reason only in its `waiting_for` attribute, because what it waits
     on is a condition and not a slot.
     Decide whether that sensor should name a time at all when nothing is
     scheduled, or say what it is waiting for in its state. Runs are kept
     with no cap, so a long collection grows the stored ledger and the
     diagnostics download (19 runs were 265 kB); clear the history
     between collections.
  2. **The charge window with no room to charge**: the headroom under
     `snapshot.battery_ceiling` is now looked at before the window is
     written (2026-11-09); the 300 W floor after it still skips a battery
     charging a few hundred watts with kilowatts of headroom, unless the
     bracket confirms the start first.
  3. **Translate** the status line, the step sensor's states (*waiting
     for changed test conditions*, *stopped*) and the notifications once
     their wording settles; English for now. One wording to settle first:
     for about half a minute after a run ends the status line reads
     *waiting for changed test conditions: a run is in progress*, which
     contradicts itself -- the run is finished, progress is 100 and the
     controls are released, but the continuous state has not caught up
     (seen 2026-11-16, 23:20:11 to 23:20:41).
  4. **Diagnosis: stop on hardware** -- **done 2026-11-17**, at the
     maintainer's SH10RT. Pressed 60 s into part B, after six settings had
     been written and during the forced charge probe: the restore ran to
     completion in ~50 s, all seventeen touched settings read back at their
     pre-run values with zero mismatches, the snapshot store was dropped,
     the owner's controls were released and **no restart started** (wiki:
     the stop). Nothing is left here; a stop through a WiNet-S is covered
     by T044, not by this item.
  5. **The *Diagnosis:* names on a real device page**, in English and
     German, once released: that the *Diagnostic* card keeps them
     together in the order `doc/entity_names.md` shows (the frontend's
     collation was not checked in the container), and that the
     counters read sensibly after a day's runs.

## Status log

| When | Status |
| --- | --- |
| 2026-11-23, 19:37 CET | **The collection at mkaiser's production entry is complete: 56 of 56, 0 failed** (51 passed, 5 bounds not enforced), 26 runs, every setting put back each time; auto repeat switched itself off. Today's runs 22-26 settled 13059 and 13100's readback, the forced discharge (1250 W asked: -3686 W to 1017 W), the export limit (1250 W asked, 6674 W to 1247.5 W), the charge ceiling at 53 % (4499 W to 0 and back), 13059 refusing 51 % with 0x04, and the discharging threshold (229 W to 0, 272 W after); run 21 the forced startup (122 s, 206 s, 16 s). The last two readings' checks settled on the evening's discharge. **Not ingested**, by the maintainer's word for the morning of 2026-11-24: a copy of both stores is in `tmp/mkaiser-t007-2026-11-23/`, local only. |
| 2026-11-23 | **Auto repeat's spacing changed** (0.1.0a51): no fixed 30-minute slot, but 5 min after a run that settled a check and 30, then 60, after vain ones, a newly possible check shortening it once; the two SoC readbacks wait for 15 %. Not yet watched on hardware: what to look at is *Diagnosis: next attempt* and the Log after the next collection starts, at mkaiser's after the ingest. |
| 2026-11-20 | **The night ran and T017 is answered.** Home Assistant was restarted at 21:29 CET on 2026-11-19 so that `e8f1c84`'s revision-2 midnight check was loaded, and auto repeat re-armed at 21:30 (the leave never survives a restart). At the inverter's midnight **eight daily counters fell to zero in one poll**, none standing: the reset is atomic here, which is what T017 asked, and the row that had failed three nights on Home Assistant's UTC clock now passes. `lifetime battery counters contain each other` settled too, 175 passes, the first time anywhere; the house stands at **37 of 55, 0 failed**, 11 runs kept. Ingested as `.wiki/raw/mkaiser-midnight-reset-answered-2026-11-20.md` with its source page, the SH-RT, P020, mkaiser and capability-test pages, the index and `log.md`. **Zero runs started for the second night running** (battery 0 %, low-SoC Standby), so item 4.1's lower half is settled and only the *Diagnosis: next attempt* wording is left. The collection is still armed and observing; nothing here is uncommitted. What it waits on now is a **charged battery**, for the nine write-side rows, and a dusk for `TWO_MOMENTS`. |
