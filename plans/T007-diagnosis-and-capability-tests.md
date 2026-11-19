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
    The dev instance's collection was re-armed and has run since
    2026-11-16. Read on 2026-11-19 it stands at **35 of 54** established
    (22 of 31 on the write side, 13 of 23 plausibility), and what it is
    still waiting for says what the collection needs rather than what the
    code owes:
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
      - **ten plausibility checks**, which no run can force: three want
        three kilowatt-hours of flow (daily exported, battery charge,
        battery discharge), five want 2 kWh on a daily counter, "battery
        level follows its power" wants 1 kWh through the pack, and "daily
        counters reset at midnight" wants a midnight (T017).
    So a re-armed auto repeat **will** want writing runs again -- there is
    real work left, which is worth knowing before parking it;
  - **anything on a WiNet-S beyond one run**, and any T-series cable.
  The night re-check and the plausibility checks need one auto-repeat
  collection at the maintainer's SH10RT over a day and a night, which
  may catch a slow PV charge for the threshold too; then ingest. The
  wallbox's tests are planned in `plans/T003-T004-wallbox_tests.md`.
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
     fifteen seconds and that was not enough to open a slot either. The other half did not show: *Diagnosis: next
     attempt* stayed `unknown` with the reason only in its `waiting_for`
     attribute, because what it waits on is a condition and not a slot.
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
