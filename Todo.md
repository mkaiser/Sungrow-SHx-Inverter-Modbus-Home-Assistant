Todo.md contains only what is still to do (forward looking).
Anything done is removed here; history goes into git and `.wiki/wiki/log.md`.

Revising this file -- closing an item as done or as decided, keeping it
forward looking, reordering it, taking in new issues -- follows
[`.claude/skills/revise-todo/SKILL.md`](.claude/skills/revise-todo/SKILL.md)
(`/revise-todo`). It has more than one writer: read it from disk and change
only your part (`AGENTS.md`).

Where the last hardware session at the maintainer's SH10RT left off, and what
a fresh session needs that is written nowhere else:
[`plans/mkaiser-diagnosis/handover.md`](plans/mkaiser-diagnosis/handover.md).

Structure:

1. **Next steps** -- work that can start now, in order of priority.
2. **Open decisions** -- questions for the maintainer; nothing is built on
   them until they are answered.
3. **Planned tests** -- runs on hardware with a date: whose inverter, what
   to run, and what each result decides. Removed once run and ingested.
4. **Blockers** -- work that waits on something outside this repository
   (hardware, daylight, a contributor). A next step that turns out blocked
   moves here, with what unblocks it.
5. **Release** -- what the first stable release needs, and what follows it:
   `main`, the catalog, the preview channel, announcing it.
6. **Future work** -- wanted, not scheduled; includes recurrent checks.

Next steps and blockers are grouped by device: Inverter (hybrid and
string, with the meter read through it), Battery, Wallbox, Logger,
iHomeManager, and Integration and tooling for what belongs to none.
Numbers run on across the groups, so a reference such as "blocker 16"
stays unique.


# Next steps

## Inverter

1. **The site import limit (32998) and forced startup (13017): what is
   left.** Both are measured and shipped as controls, the number *Grid
   import limit* (W, 10 W step) and the switch *Forced startup under low
   SoC*, on the firmware the wiki lists
   ([register 32998](.wiki/wiki/entities/register-32998.md),
   [register 13017](.wiki/wiki/entities/register-13017.md), which carry what
   every run measured). Still to run:

   | Case | What it settles | How, where |
   | --- | --- | --- |
   | PV above the load, battery part full, a forced charge above the surplus | whether the cap is on the grid's share alone, PV counted | the engine's `--import-limit` check, daylight |
   | 13017 left on, on **other firmware** | whether the inverter flips `0xAA` back by itself or on PV. **Answered on P020 2026-11-17: it does not** -- 13017 held `0xAA` for 90 min 48 s, through dawn and 31 min of PV, read back from the register (wiki: register-13017, the watch). #444's ~20 min is not reproduced; other firmware, or an iSolarCloud-connected house, is what is left | a watched run, after dark, reading the register back |
   | 13017 on P022 and other firmware | whether it is a switch there too | a watched run, after dark |

   Not worth a run: a full battery at night, a forced charge into a full
   battery (the engine skips at 90 %), a forced discharge.

   **The engine refuses an inverter in low-SoC Standby** ("reports
   'Standby'"), though a forced charge wakes one by itself in ~2 min (EMS or
   schedule, bar12). Whether the import-limit check should command that
   charge and wait for the start instead of refusing: decide with the
   diagnosis's rework.
2. **The inverter's own consumption, on hardware.** Built: *Inverter self
   consumption (estimated)* (`Derived.inverter_self_consumption`, PV +
   battery - export - load, shown as a one-minute time-weighted mean, no
   legacy id: #626 never shipped). The battery term is 5214 where it
   answers, else 13022 signed by 13001's bits (as evcc), so the sensor
   exists where 5214 is refused (#655). **At night in Standby it reads about
   -1.9 W** (the maintainer's SH10RT, 2026-11-16, 23:00, battery empty), not
   the tens of watts expected: in Standby the inverter reports 0 for PV,
   battery, export and AC power, so every term but the load's noise is zero
   and the estimate collapses. So the sensor says nothing about the standby
   draw, and whether it should read `unknown` there rather than a number near
   zero is the question to settle. Left besides: the daytime look, whether
   the mean is steady enough and plausible while the inverter works; the
   13022 path on a house that refuses 5214; its energy counterpart.

## Battery

Nothing can start now (blocker 13).

## Wallbox

3. **Controlling the wallbox.** gerd's wallbox is **managed by the
   inverter**, which drives 21203 and overwrites any write to it, so the
   charge is controlled at the inverter (unit 1): charging on/off, mode, and
   the user-defined current in user-defined mode, 6 A up
   (`hybrid_inverter/ev_charger.py`; wiki:
   `gerd-wallbox-inverter-control-2026-11-14-summary.md`). Holding 21203
   scales 0.1 A, settled by the car. A standalone wallbox is the only one
   whose own registers may be written (`--standalone` from a terminal; from
   Home Assistant never, it cannot tell), never under 6 A.

   What exists: the wallbox's capability test
   (`src/sungrow_modbus/wallbox/capability_test.py`, terminal driver
   `sungrow_wallbox_capability_test.py`, TLS 516 unit 248), the managed
   wallbox's (`wallbox/managed_test.py`, `sungrow_managed_wallbox_test.py`,
   which writes the inverter's block and judges by the car), both also from
   Home Assistant on the wallbox's own entry in *Extended test (auto
   repeat)*, with the plausibility checks (`wallbox/plausibility.py`), a
   ledger per wallbox firmware (`wallbox/ledger.py`), the options *May it
   write to the wallbox* (off until switched on) and the highest charging
   current (`wallbox_max_amps`), and the EV charger controls on the
   inverter's entry: *Wallbox charge* (33540), *Wallbox charge mode*
   (33541), *Wallbox user-defined current* (33545) and *Wallbox grid
   purchase* (33550), behind `EV_CHARGER` and `EV_CHARGER_CONTROL` (watched
   on P022, gerd's, alone). `plans/wallbox_tests.md` is the procedure,
   `plans/wallbox_session_handover.md` where the last session stopped.

   Left, in order:

   1. **The mode select's timing.** The four controls ran from Home Assistant
      at gerd's with a car charging on 2026-11-17 and each did what it says
      (wiki: `gerd-wallbox-2026-11-17-afternoon-summary.md`); the number
      refuses outside user-defined mode before writing. Left: a mode change
      to or from user defined ended the session on the night of 2026-11-16
      (battery at its minimum, no PV) but not that afternoon (battery 2.8 %,
      some PV), so whether the select's charging-on, written straight after
      the mode, survives the inverter's delayed off is still unprovoked.
      Decide when a session that ends on a mode change is seen from Home
      Assistant. Firmware beyond P022 is added only from a watched write.
      Discussion #571 (rudolf992: a current set over Modbus went back to
      iSolarCloud's within seconds) is the same thing seen from the wallbox
      side.
   2. **The managed capability test from Home Assistant: link the entries.**
      From the terminal it passed twice (2026-11-16, 2026-11-17), and the
      restore that waits for the inverter and watches the car held on
      2026-11-17. From Home Assistant it cannot run at gerd's: the wallbox
      entry's `managing_entry` comes only from the inverter entry's dongle
      probe (`wallbox_elsewhere`), and an inverter entry on the LAN cable
      never sees the wallbox, so the run took the standalone path and wrote
      nothing. Needs another way to pair a TLS wallbox entry with the
      inverter that manages it (an inverter entry with `EV_CHARGER` at the
      same site, or the owner choosing it), then the write-owner refusal
      (`write_owner.py`) on hardware. Also: a leftover snapshot from a
      standalone run is put back through the wallbox's own registers even
      when an inverter now manages it; refuse that and say so instead. Open
      for both: what ends a session with nothing written (wiki:
      `why-does-a-managed-wallbox-stop-charging.md`; on 2026-11-17 the car
      was also cut to 6-8 A four times after house load spikes, within one
      session).
   3. **A standalone wallbox** (evcc's case): none measured. Idle and with
      no car, gerd's setting reads 0 (160 and 151 while charging), so an
      idle wallbox cannot separate the two scales and the meaning of 0 is
      unknown (wiki: `gerd-wallbox-dry-run-2026-11-06-summary.md`). Input
      21322 is not the setting's echo.
   4. **The wallbox entry's first writing run**, which needs a car charging,
      watched live. With no car it refuses while the wallbox is idle, as it
      should (gerd's; auto repeat ran an hour on 2026-11-10 and started no
      run, the right outcome).
   5. **The next session at gerd's**: `plans/wallbox_tests.md`
      (quantity-and-time mode, writes that repeat what is set, waking a
      sleeping car, phase switching, PV surplus in sun), with the field tool
      `scripts/dev/managed_wallbox_field.py` (read only, but `charge`).
      Inverter work there waits for his own Home Assistant to be stopped,
      on the current release, over the cable if it reaches one, the battery
      above 20 %, a car charging. Readback verdicts through a dongle are
      not evidence.

4. **The wallbox's settings as entities.** Read only: *Start charging on
   plug-in* (21298; not "Plug and Charge", which is ISO 15118's certificate
   login), *Offline charging current* (21299, 0.1 A) and *Power limit*
   (21313, 0.1 kW), with enable 21211 (status 8 while disabled); only the
   wallbox's own address answers them (wiki:
   `gerd-wallbox-app-settings-2026-11-14-summary.md`). Left: whether any of
   them may be written, which needs the standalone wallbox of item 3.3.

   The mileage check (21232) is **removed**: it proved only a display value,
   and its one run left gerd's at 5555.2 (set back to 5.0). How a day whose
   every recorded write was 50 came to hold 55552 is open
   (`plans/wallbox_tests.md`, open questions). A run that leaves a house
   changed raises a Repairs issue naming each setting and where the app sets
   it (`repairs.py`).

## Logger

Nothing can start now (blocker 16). Decided, not built: the search should
say which inverters sit behind a Logger. A Logger is offered as a
diagnosis-only entry; how it is handled beyond that is open.

## iHomeManager

1. **Its entities on hardware.** Built 2026-11-11: an iHomeManager entry
   shows 40 read-only sensors beside its diagnosis (the site's flows, the
   grid meter, the charger, its settings as set;
   `ihomemanager_descriptions.py`), tested against the one unit's words,
   released in 0.1.0a37. Not yet seen in a real Home Assistant. The entry
   holds its port while loaded; how many connections an iHomeManager takes
   at once is not measured (`doc/integration_help.md` and the FAQ say so).
2. **The fields left out of its entities, until a second unit is
   measured** (blocker 17; wiki: the iHomeManager source page). Each is
   read and kept in the diagnosis, and gets no entity:
   - **8554, the output type**: reads 0, "single phase", on a three-phase
     site (three phase voltages, three phase powers).
   - **8047 (start/stop) and 8048 (charger mode)**: read 0 and 0xA7, codes
     no document lists.
   - **8051-8052, the active power limitation and its ratio**: 8051 reads
     0, not a code of the 0xAA/0x55 pair; 8052 reads 0x7FFF, an unset value.
   - **Channel 2 (8565-8574), the PROD.CT**: all zeros on a unit with no
     CT there.
   - **8029, the feed-in limit in kW**: only in a third-party template, in
     no Sungrow document.
   A second unit, ideally single phase, on other firmware or with a
   PROD.CT, decides each: a field whose reading then makes sense gets its
   entity in `ihomemanager_descriptions.py`.

## Integration and tooling

5. **The diagnosis and its capability tests.** In the code: the three
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
        The dev instance's collection has five plausibility checks matched
        (power balance, both meter checks, daily_imported_energy and
        total_imported_energy against power). After the stopped run of
        2026-11-17 the ledger shows **15 of 52** established, the rest split
        between checks the stopped run never reached ("not run, the run ran
        out of time"), checks "the house was in no state for it", and the
        plausibility ones waiting on PV, battery movement or export. So a
        re-armed auto repeat **will** want writing runs again -- the stopped
        run left real work behind, which is worth knowing before parking it;
      - **anything on a WiNet-S beyond one run**, and any T-series cable.
      The night re-check and the plausibility checks need one auto-repeat
      collection at the maintainer's SH10RT over a day and a night, which
      may catch a slow PV charge for the threshold too; then ingest. The
      wallbox's tests are planned in `plans/wallbox_tests.md`.
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
         by blocker 19, not by this item.
      5. **The *Diagnosis:* names on a real device page**, in English and
         German, once released: that the *Diagnostic* card keeps them
         together in the order `doc/entity_names.md` shows (the frontend's
         collation was not checked in the container), and that the
         counters read sensibly after a day's runs.

6. **The search missed the maintainer's inverter** (2026-11-15, 0.1.0a40,
   production Home Assistant): two sweeps of the home /24 found port 502
   open only on the old RAK WiFi module (which accepts and echoes, not
   Modbus) and never on the SH10RT, which the YAML package was polling
   through the same Home Assistant; from the dev container the SH10RT
   accepted six of six connects in under 10 ms. The manual step identified it at once. Not retried slowly
   (that happens only when nothing answers). A sweep from the dev container,
   which holds no session, found and identified it in one round, so the port
   is not deaf to a sweep: what it does under a sweep from the address
   already polling it was the question. **Answered 2026-11-17, and the
   hypothesis is wrong**: with the dev container's own Home Assistant polling
   the inverter without a break, 12 of 12 connects from that same container
   were accepted in 7.6-21.8 ms and both full /24 sweeps found it, costing the
   poller no lost connection (wiki: why did the search miss the maintainer's
   inverter, the run). So contention does not explain the miss, and nothing
   needs to count an already-connected host as a candidate.

   **What is left is one measurement**: the production Home Assistant reaches
   this inverter through a **modbus-proxy on its own machine**, so the session
   held from that address is the proxy's, not Home Assistant's. Run the same
   sweep from the production machine with the proxy running. If it finds the
   inverter there too, the miss was never about sessions and the sweep's own
   behaviour on that host is what to look at.

7. **The new scenes on hardware.** `doc/scenes.md` has the YAML package's
   seven rewritten against the integration's option keys, with the two
   automations that need a limit reading it from the entity
   (`state_attr(..., 'max')`) instead of from a secrets file, and
   `tests/test_scenes_doc.py` holds every id, option and range in it to the
   descriptions. Nothing in it has been activated on a device. Left:
   - **Press one, at the maintainer's SH10RT.** **Done 2026-11-17**:
     *Battery Forced Charge*, installed from `doc/scenes.md` into the dev
     instance's `scenes.yaml`, set **both selects** -- EMS mode to forced and
     the battery command to charge -- and the inverter reported "Running in
     compulsory (forced) mode". The rewrite does what a pasted scene could
     not. What it did **not** do is move any energy: see item 11.
   - **Watch what `max` reads.** **Done 2026-11-17.** The attribute is there
     on hardware (*Feed-in limit* `max` = 10000.0 W, the battery numbers from
     `battery.ceiling`), and the automation itself ran: activating
     *Self-Consumption Mode (max battery discharge)* had
     `state_attr(number..., 'max')` render **7420.0 W** and write it, not
     `None` and not 0. The pattern in `doc/scenes.md` works.

     Worth keeping: **the ceiling moves with the battery's state** -- the same
     `max` read 7148 W with the pack empty, 7420 W at ~25 % and 7318 W a
     minute later, because the pack's limit falls back to what the BMS will
     take at that moment (`src/sungrow_modbus/battery/power.py`). That is the
     argument for the automation over a figure stored in the scene, and it
     belongs in `doc/scenes.md` where it tells a reader why the automation
     exists (wiki: the charge).

8. **Range checks: which bound is measured, and which is a judgement.** A
   write entity's bound is the only guard there is, because the inverter does
   not enforce its own: mkaiser's P020 stored five battery-power settings
   above their maximum, and at gerd's a **33 A** write was taken on a 32 A
   wallbox (P022). Where each bound comes from today:
   - **Derived from the device.** Battery max charge power, max discharge
     power and the forced charge/discharge power all take their ceiling from
     `battery.ceiling` -- the lower of the inverter's BDC rated power (5628)
     and the pack's own limit, which is the owner's configured value, else
     the datasheet figure for the capacity the pack reports, else the BMS's
     maximum charging current times the pack voltage. The feed-in limit takes
     its maximum and minimum from the inverter's own registers. This is what
     the YAML package could not do: its slider's maximum was a number the
     owner typed into `secrets.yaml`.
   - **Measured.** The grid import limit, 10 W to 50 kW, because 32998 takes
     1-5000 counts and refuses 5001 on P020, P022 and P023. The wallbox
     current's 6 A floor, because 5 A was refused at gerd's.
   - **A judgement, and labelled as one.** The battery charge and discharge
     start thresholds' 1000 W, which the YAML's author called a guess and
     asked to be told about. What would settle it: set a threshold above a
     battery's maximum charging power and watch charging never start, which
     is the behaviour the comment already predicts.

   **Measured 2026-11-17** at the maintainer's SH10RT (P020, battery ~22 %,
   auto repeat's own run 3; wiki: which write bounds the inverter enforces).
   Each upper-bound check wrote one value just above the maximum we offer and
   read the register back raw over the cable:

   | Control | Maximum | Written | Stored | |
   | --- | --- | --- | --- | --- |
   | `battery_max_soc` | 100 % | 101 % | -- | **refused**, exception 0x04 |
   | `battery_max_charge_power` | 7274 W | 7374 W | 7374 W | not enforced |
   | `battery_max_discharge_power` | 7274 W | 7374 W | 7374 W | not enforced |
   | `battery_forced_charge_discharge_power` | 7274 W | 7374 W | 7370 W | not enforced (see below) |
   | `battery_charging_start_power` | 1000 W | 1010 W | 1010 W | not enforced |
   | `battery_discharging_start_power` | 1000 W | 1010 W | 1010 W | not enforced |

   **Only the SoC bound is the device's.** Every battery power bound is ours,
   so the entity's maximum really is the only guard -- the premise of this
   whole item, now measured rather than inferred from five stored settings.
   - **Not derived, though the device states it.** The wallbox's user-defined
     current is capped at a flat 32 A, the largest Sungrow wallbox's rating,
     while a wallbox reports its own at 21263 -- **16.0 A** on the AC011E-01
     read on 2026-11-16. On that wallbox the slider offers twice what the
     hardware takes, and the inverter will not refuse it. Bound it per device
     from the reading where there is one, keeping 32 A only where nothing
     reports a rating. The wallbox's own entry has 21263; an inverter entry
     that manages a wallbox needs to reach the same figure.

9. **A deprecated core API in the actions.** Every call of
   `sungrow_modbus.run_capability_test` (and of the other three actions)
   logs a core warning: `DeviceEntry.config_entries` is deprecated because a
   device belongs to a single config entry, and it **stops working in Home
   Assistant 2027.10**. One use, `custom_components/sungrow_modbus/services.py`
   line 308, looping `device.config_entries` to find the entry a device
   belongs to; `DeviceEntry.config_entry_id` replaces it. The loop also picks
   the first entry whose domain is ours, which with one entry per device is
   the same answer. Cheap to fix, and it keeps the log clean for whoever
   reads it during a diagnosis.

10. **A safe pattern for ad-hoc hardware watches.** A one-off watcher that
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

11. **The new scenes, on hardware beyond the one press.** `doc/scenes.md`'s
    three faults are fixed (2026-11-17): the newer entity ids are given as a
    table rather than promised as "one substitution" -- three of them are
    named differently, not just prefixed; every scene state is quoted, since
    Home Assistant drops a whole scene whose state is a bare number, which
    cost two of the seven on a real instance; and the two forced scenes now
    carry a power, without which the inverter reports forced mode and moves
    nothing. `tests/test_scenes_doc.py` holds all three to the descriptions.

    Left: the scenes other than *Battery Forced Charge* have still never been
    activated on a device. *Zero Export Power* and *Max Export Power* need a
    house that is exporting, so they wait for sun with a battery that is not
    empty; *Battery Bypass* and *Battery Forced Discharge* need a battery with
    something in it. None of them is urgent, and the forced-charge press
    already proved the mechanism the rewrite was for.

12. **Watching the readings, after decoupling it from auto repeat.**
    Done 2026-11-17: `DiagnosisRunner` feeds the checks on its own one-minute
    timer, started where the entry registers the shutdown that cancels it, and
    `continuous.py`'s tick no longer observes. Three traps it set on the way,
    all now commented where they bite and worth remembering before touching
    this again:

    - **Priming in `__init__` is useless**: the kept readings are loaded
      afterwards and the load replaces the object.
    - **Without a reading before auto repeat's first tick it switches itself
      off**, having read "nothing left to watch" from an `unsettled()` that is
      empty only because nothing has been observed.
    - **`continuous.py` is shared with the wallbox runner.** Removing the
      observe call from its tick left a wallbox entry accumulating nothing;
      `WallboxDiagnosisRunner` starts the same timer now. This reached a push
      before CI caught it.

    Left: **the visible wording.** A fresh entry now says "0/23 established -
    waiting for: ..." where it said "no runs kept", and the counters carry the
    readings' checks instead of reading "unknown". That is the intended
    consequence -- there really is something being collected from the first
    minute -- but it has not been seen on a real device page, and it is the
    maintainer's call whether a house that never runs a capability test should
    show it.

13. **Clearing a ledger is all or nothing.**
    `DiagnosisRunner.async_clear_ledger` clears the capability ledger **and**
    removes the plausibility store with it, so an owner who wants the runs
    afresh loses every reading the checks have gathered too -- at the
    maintainer's on 2026-11-17 that would have been a day of polls and three
    settled V x I checks. Worth separating, or offering per check.

    **Not urgent, and no longer the remedy for a wrong verdict.** That is
    what `CHECK_REVISIONS` is for (`capability_test/coverage.py`): each check
    carries a revision, a run records the revisions it was measured with, and
    `ledger.py` keeps only rows measured at the current one, so raising a
    number makes every ledger ask that check again -- and only that one -- on
    update, with no clearing and nothing for a user to do. The step-as-clamp
    fix of 2026-11-17 raised the seven bound checks to 2 accordingly, and
    `tests/test_capability_ledger.py::test_a_bound_clamped_under_the_old_rule_is_asked_again`
    holds the rule and the bump together.

    The lesson, since it was nearly missed: **a change that could change a
    verdict needs its revision raised in the same commit**, which the table's
    own docstring says and the first fix did not do.

14. **The midnight-reset check judges by the wrong clock.**
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
    misbehaves. Raise the check's revision in the same commit, per item 13.

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

# Open decisions

1. **Are the entity names final?** They are reviewed and decided, English
   and German (`doc/entity_names.md`, `plans/text_translation_review.md`,
   `scripts/generate/tables/naming.py`); both ship, German as
   `translations/de.json`, and entity ids stay English in every language
   (`doc/architecture.md`). A rename later leaves existing ids alone and
   only diverges new installs, which a registry migration can close, so it
   stays cheap until release, not free. A new name goes under **To
   discuss** (`NAME_DISCUSSION` in `naming.py`).

2. **Is mDNS in the devcontainer worth a second config?** Measured
   against Docker's documentation (`doc/development.yaml`,
   `real_hardware.host_networking`): on Docker Desktop, which this
   devcontainer runs on, `--network=host` forwards TCP/UDP ports only and
   carries no LAN multicast, and WSL's mirrored mode does not change that.
   The one Windows route left is Docker Engine inside a WSL distribution in
   mirrored mode: untried, with the Hyper-V firewall and Windows' own hold
   on UDP 5353 still open, and it would put the WireGuard tunnels into the
   host's routes. The other way is to try the zeroconf matcher (blocker 18)
   on a Linux Home Assistant in a house with a dongle.

# Planned tests

1. **The site import limit (32998) at fwitten's master, when it is
   reachable** (SH10RT-V112, P023, SBR096, cable): the same model,
   firmware and battery as ulfben's (#546). P020, P022 and P023 obeyed,
   cable and WiNet-S, EMS and schedule (wiki: gerd-import-limit-2026-11-08,
   bar12-import-limit-*); what fwitten adds is the engine's own
   `--import-limit` check on P023, and ulfben's exact hardware. Its
   addresses did not answer on 2026-11-07. How: from this checkout,
   `sungrow_capability_test.py <host> --import-limit --allow-dark
   --no-restart`, a dry run first, the stand-in read before any write;
   their Home Assistant stays connected, so expect retries. After dark, a
   battery under 90 % and not in Standby. Then ingest. In discussion #546
   ulfben (2026-11-07, offers to stop evcc for it) and Jam3s97 (2026-11-08,
   an SH-RS) offered runs; no reply is planned there: the long-term logs
   asked of contributors are expected to settle it.

# Blockers

## Inverter

1. **An SH-T through its WiNet-S, in daylight, with export** (any SH15T
   owner; ra1k_0 says the SH20T has no LAN port of its own, #772, and
   Sungrow's SH5T-SH25T manual lists a WiNet-S2 Ethernet connection and a
   COM2 terminal, no LAN terminal: the manual's contents page, read through a
   search; its text was not fetched). So the T has **no cable path** to ask
   for, and what a dongle run can settle is its behavioural leg only. One run
   with the capability test (`--enable-export-limit`) settles:
   - **13074 on P071.** The dongle reported a word written with feed-in
     limitation off as handed, where B001 ignores it. Readbacks through a
     dongle are stale, so only the export check (the house must export) can
     say whether P071 stores 1:1; if it does, the integration's
     unanswered-probe fallback of ten sets a tenth of the asked export limit
     on an SH-T.
   - **An SBH on a direct link** cannot be had without a cable.
     `Capability.SUNGROW_BATTERY` is granted for an SBR found on its own unit
     (`with_sungrow_battery`); an SBH is not until its own-unit reading is
     seen without a dongle. Parked until a T is found with a direct path.
   - **Whether an iHomeManager silences 5741-5746** (#647, #651), which
     every WiNet-S refuses anyway; ra1k_0 has one.
   Still open on the T besides: whether 13018 acts as 31211 does, and
   33149-33150 (battery start power): the capability table marks them absent,
   but BiergitKraft's SH10T on `PEARL-H_B001.V001.P038` answered them through
   a WiNet-S2 in every round (#792), as GalKar's did once. That SH10T is a
   second candidate for the run above. Its first capability test was refused
   in Standby after dark, so it needs daylight with the inverter Running.

2. **firetribe, once more (#784).** A cable capability test while the
   inverter is running (it was `Starting`) gives the first SH6.0RT-V112
   readbacks and its 13074 write scale. Their WiNet-S 0x04s are contention,
   reproduced at gerd's.

3. **A fault seen on hardware.** The fifteen words are decoded from V1.1.11's
   Appendix 4; one diagnosis has a flag set (bit 30 of the inverter alarm, a
   slave with no meter), which confirms the word order. Wanted: a reading
   during a real grid or battery fault, and the battery words through a
   dongle. V1.1.17's Appendix 4 is word for word V1.1.11's.

4. **Meter phase voltage/current (5741-5746) on dongle houses.** Read zero
    through every WiNet-S measured and are gated on a non-zero voltage.
    Whether they need reading on their own (#756) needs a diagnosis from an
    affected owner; `layout.py` changes only on measurement.

5. **T-series energy counters.** One SH20T reads 13045 (daily export) as 0
   while exporting, and 5003/5004-5005 duplicating the export counters. A
   second T diagnosis, ideally on a cable, before `registers.py` changes.

6. **Writing the discharge schedules** (#785), in no Sungrow document. The schedules read as diagnostic entities
   (`Capability.DISCHARGE_SCHEDULE`); writing them needs a watched write, as
   31211 did (wiki: firmware gating), from a capability test run with leave.

7. **The discharge window on P023** (#785). It has run on P022 and P020,
   and the device pages and log say so; no P023 or SBR house has run it
   (fwitten's master, with their Home Assistant stopped, in the evening).

8. **The SG's zeros and writes.** On bleughb's two SG5.0RS through a
   WiNet-S, the meter block (5083-5104) and the per-string block (input
   7013) read 0, and holding 5020 reads nothing. Whether that is absence or
   the dongle needs an SG on a cable, or one with its own meter. Writing the
   power limitation (holding 5007-5008, which bleughb writes on both) waits
   for a watched write.

9. **gerd's cable restart.** On 2026-11-03 the start had to be sent three
   times (still stopped 60 s after each), where every earlier restart took
   the first. **Recurred on 2026-11-10 through the WiNet-S** (auto repeat in
   the dev HA): stopped after 2 s, start sent three times, running after
   182 s, generating 3.5 s later, settings survived. Twice now at gerd's,
   on both paths: look at what the inverter reports between the starts.

10. **The SG's tracker counts beyond the SG5.0RS.** `MPPT_COUNTS` is the
    source's model table, many entries unverified; a diagnosis of any other SG
    checks its row (wanted in `device-diagnosis/devices-wanted.md`, row 10).

11. **The PV cut (31211, #738), beyond the four confirmed firmwares.**
    Waits on contributors; nothing here or at the maintainer's P020 (31211
    reads 0xFFFF there) can answer it.
    - More firmware confirmed: 31211 answers 0x55 but no cut has been
      watched on `SUNSTONE-H_B000.V001.P068`, `B000.V002.P067`,
      `B000.V002.P059`, `B000.V002.P057` and `PEARL-H_B001.V001.P038`. The diagnosis's capability test
      watches the cut, so it is asked for in the "Most wanted" table of
      `device-diagnosis/devices-wanted.md`, never from one person.
    - One evening's watch on a confirmed device (P022, P023, P071 or P065):
      does a cut survive a night or a restart, or does iSolarCloud rewrite
      it?

12. **What register 13080 counts.** Documented as the external EMS
    heartbeat (0-1000 s, default 20 s), it reads 0 on 42 diagnoses, 330 on two
    houses in EMS mode 0, and 875 then 961 on ra1k_0's SH20T in EMS mode 3
    (`.wiki/wiki/queries/what-do-the-v1-1-17-only-registers-read.md`). Two
    reads of it a minute apart at that house would show whether it counts
    seconds. Nothing reads or writes it until then.

## Battery

13. **SBH.** Answers the SBR's common block at unit 2 with the SBR's scales;
     per-module arrays unread. Needs the register document.

## Wallbox

14. **A wallbox charging negative, or past 32.7 kW.** Settles whether
    21308/21310 are signed. Still unnamed: input 21313 (falls to 0 when
    charging ends, not power) and input 21365 (-71 to -63, flat). A wallbox
    restart would show whether 21267 falls to near zero.

15. **A second wallbox's diagnosis.** Settles whether 21211-21214 identify
    the unit. Three registers wait on it: input 21201-21206 (the serial as
    Sungrow's portal shows it -- gerd's hashes to his published stand-in, so
    this block is that serial; use it as the device identity?), input
    21211-21214 (a short code, masked) and holding 21250-21259 (twenty
    constant ASCII digits, masked). Whichever differ between two wallboxes
    identify a unit and stay masked; whichever match are a model constant
    and can be unmasked. A second AC22E-01 arrived 2026-11-10 (anonymous,
    #786), but both documents publish these blocks as `null` with no
    stand-in per block, so they cannot be compared: settling it needs the
    masking to publish a stand-in for each masked block (a hash compares
    without revealing), and a third reading. The AC011E-01 at unit 4
    arrived on 2026-11-16 (#786) and is ingested, but as a Home Assistant
    diagnostics download, whose wallbox section carries none of the three
    blocks: 21211 and 21212 appear in it as the charger's enable and
    start/stop, not as the short code. So this still waits on the masking
    change plus a reading that carries the blocks -- a terminal diagnosis of
    that wallbox would do it.

## Logger

16. **A first Sungrow Logger diagnosis** (#786). Unblocks Logger entities.
    The map is done from Sungrow's protocol 1.0.2.9
    (`sungrow_modbus.logger`, every field `spec`; where every document is:
    `.wiki/wiki/queries/where-are-sungrows-documents.md`); what a first
    diagnosis settles is on `.wiki/wiki/queries/what-does-a-logger-answer.md`.
    It reached diagnoses with 0.1.0a26, which the diagnosis pins. Missing:

    1. **Its TLS port, untried.** The diagnosis asks unit 247 over TLS on 516
       (a current Logger1000 opens only that port); no Logger has answered
       there yet, so that path is held to fakes only (`tests/test_logger.py`).
    2. **What sits behind it.** Each inverter and meter answers at its
       forwarding address (the Logger's Device List page), not at a unit the
       diagnosis guesses; `identify` looks at units 1-5 only. A DTSU666 is a
       device nothing maps.
    3. **A contributor with one.** Nobody has offered; the #262 participants
       are the leads: horstvogel (2025-12-23, a Logger1000 EU read over
       Modbus TCP at unit 247), RafAustralia, purcell-lab and NBS23.
    4. **The protocol number's word order.** The map reads 8001-8002 high
       word first; the one iHomeManager measured sends "AW0" low word first
       (fixed for it, 2026-11-10). Check the Logger's on its first reading.

## iHomeManager

17. **A second iHomeManager diagnosis** (#786). The first was met
    2026-11-10: one unit on SV930.001.00.P020, port 503, answered all 56
    mapped fields (wiki: the iHomeManager source page), and its protocol
    number is read low word first since. A second unit, ideally single
    phase, on other firmware or with a PROD.CT, decides the fields left out
    of its entities (iHomeManager in Next steps) and whether 4358-4362 are
    U32 (4359 and 4361 read 0). Sungrow's protocol PDF:
    https://github.com/TCzerny/ha-modbus-manager/blob/main/docs/Communication%20Protocol%20of%20iHomeManager_V1.0.2.pdf

## Integration and tooling

18. **Does a WiNet-S advertise over mDNS?** Yes (wiki: the mDNS query):
    gerd's dongle and wallbox advertise `_http._tcp` with TXT records naming
    model, serial and units, the dongle's for every device behind it, and
    python-zeroconf (Home Assistant's library) resolves and parses both; the
    inverter's LAN port answers nothing. A multicast browse on a LAN is
    answered too, at peter_sm's on 2026-11-15, whose inverter MAC prefix
    `AC:19:9F` is the first for a DHCP matcher. Built: the diagnosis's
    `network_names` (schema 27, released) and the zeroconf matcher
    (released; `WiNet-WebServer*` and `SUNGROW*` on `_http._tcp`, where the
    record only decides whether to offer, Modbus identifies on confirm and
    nothing set up is ever moved), and the DHCP matcher (0.1.0a41,
    `wifi_module.py`), which offers a port for Sungrow's one IEEE prefix
    `AC199F*` and links a RAK WiFi module (`rakmodule-*`) to the inverter
    its owner names. Outstanding:
    - **Other houses, other firmware.** One dongle and one wallbox so far;
      both matchers wait on diagnoses carrying `network_names`, and the DHCP
      matcher on a house whose inverter port takes its address by DHCP (a
      fixed address is never seen). Two prefix readings so far, both
      `AC:19:9F`: peter_sm's and the maintainer's, the second taken from the
      Windows host because the dev container's neighbour cache holds only
      the Docker gateway (wiki: telling a proxy from the inverter).
    - **A browse the reader cannot have spoiled**, at a house with a dongle.
      Taken at the maintainer's, which has none: 44 records heard and no
      Sungrow among them, from the Windows host, on the segment (wiki: an
      mDNS browse is a floor). So an inverter's own LAN port advertising
      nothing is measured, and what is left is the dongle's half from a
      reader known not to have been deaf. Schema 28's `services_heard` and
      `on_device_segment` say which a document is, from 0.1.0a43 on.
    - **Why those eight records and not the other 33.** Which records a
      firewall drops is settled over two runs of
      `.testdata/mdns-firewall-test.ps1` (wiki: an mDNS browse is a floor):
      a declined prompt degrades the browse rather than silencing it, so
      `services_heard` stays non-zero and looks healthy, and **it is the
      same eight every time** -- of the 42 instances heard allowed in both
      runs, 33 survived all four degraded browses and the same 8 were lost
      in all four, one of them an `_http._tcp`. It is the record and not the
      host: one TV's `_airplay._tcp` survived while its three other records,
      from the same address, were lost. Open: what separates the eight. Not
      the address family. The hypothesis is unicast against multicast
      answers, which Windows' "allow unicast response to multicast" would
      split exactly this way -- a packet capture on the Windows host, not a
      browse. **Nothing the integration ships waits on it**; it would only
      let the README tell a contributor what declining costs.
    - **Does `ethinfo` say wired or WiFi?** It is empty on gerd's dongle,
      which is on WiFi; it may carry the Ethernet details when the dongle is
      wired. Answer it from the corpus: compare `ethinfo` with
      `user_inputs.transport` (`winet_lan` / `winet_wlan`) as the diagnoses
      arrive. bar12 has published both transports of one dongle, so a rerun
      there is the cleanest pair. If it holds, `wifi_or_ethernet` (today
      "not determinable over Modbus") can say what the dongle reports.
    - **The fields nothing explains**: the battery's 8423 (0x20E7), the
      inverter's trailing `1;4`, the wallbox's `info=16256` (0x3F80), every
      `;1;`. More houses, compared with what Modbus measured there.
    - **Should the diagnosis record the Windows firewall state** beside
      `services_heard`? Open, and a design question rather than a
      measurement: a non-zero count currently reads as healthy when a
      declined prompt has thinned it. Binding 5353 does raise the prompt on
      every fresh interpreter -- Windows' own `mDNS (UDP-In)` rule is scoped
      to `svchost.exe` and does not cover Python -- and the README now tells
      a contributor to allow it.
    - A WiNet-S's *Visit* link for a cable entry, found by the inverter
      serial in its TXT (a link on the inverter, or the dongle as its own
      device).

19. **The capability test's restore through a WiNet-S, on hardware.** A
    dongle-only capability test at gerd on the current tree, with the battery
    above 30 % and no car charging, then a cable read of every snapshot
    register. 2026-11-10: two dongle-only runs (auto repeat, dev HA) reported
    all 46 settings written back, but the battery was at 2-3 %, so the SoC
    checks were skipped, and there was no cable read afterwards: still open.
    Left open in the code: a touched register goes back to the
    dongle's word, wrong only if changed over another path since the dongle
    last read it. 2026-11-10 at ra1k_0's SH20T (#786, outcome 5): the
    restore of 33209 (forced-charging days, held 1) was refused five times
    with 0x04, as the check's own write had been, every write of 1. The
    SH20T has no LAN port, so no cable read settles it: **ask the owner to
    check the forced-charging schedule's days in iSolarCloud.**

20. **33213 at peter_sm's: the register or the house?** Every write of 33213
    (window 1's end minute) there lost the connection, nine of nine over five
    days (wiki: the 33213 query). Until 0.1.0a32 some 37 other writes per run
    went through; in the three runs since, 13059 lost it once and 13050 and
    33047 twice each, so a link that drops on writes is now in play too. If it is the register, the time entity *Forced charging end 1*
    loses the connection at that house too, and the time platform should
    write the window in one frame or not offer it there. One run settles it,
    with only the charge window check (`--charge-window`) and then one write
    of 33213's held value on its own. No code changes before that run.
    2026-11-11: after the other drops the next write went through at once;
    after 33213's the next check's write dropped too, in all three runs,
    with reads answering for 20 s in between (wiki: the 33213 query).
21. **Battery power where 5214 is refused** (#655, #770). On ten firmwares
    5214's sign follows 13001's bits and 13022 holds the same magnitude
    (wiki: is battery power firmware dependent), so the self consumption's
    fallback to 13022 is built. Never measured: a house that refuses 5214.
    A diagnosis of #655's SH8.0RS with its firmware, or of any inverter on
    SAPPHIRE 51.0x or with a third-party battery (#770), settles whether 5214
    is missing by firmware and tests the fallback. Then decide whether the
    *Battery power* entity falls back too. Not to be asked for on #655
    (maintainer, 2026-11-11): it waits for a diagnosis that arrives.

# Release

The maintainer targets a stable release in December 2026 (said
2026-11-06). It needs: a stable `0.1.0` rather than an alpha (item 2), the
production-database run or a decision to go without it (item 4), the
catalog submission on release, not before (item 2), and
`doc/integration_migration.md` made current.

The ordinary setup is **on** (the maintainer, 2026-11-15): the opening
"what is this for?" dialog and `ONLY_DIAGNOSIS_MODE` are both gone, every
new entry has entities, and the diagnosis and capability test are on the
same device page as the readings (`tests/test_one_setup_path.py`).
`MODE_DIAGNOSTICS` stays for the entries made while it was offered.

1. **When to merge into `main`.** The merge retires the preview channel
   and opens the HACS default store, which also needs the brand in
   `home-assistant/brands` (`scripts/helpers/make_brand_icon.py` draws it).
   At the merge, the links that name the `proper-ha-integration` branch move
   to `main` (`grep -rn proper-ha-integration custom_components`: the Energy
   dashboard guide and the preview repair's entity names).

2. **Submitting to the catalog, when the merge is decided.** The catalog
   is `hacs/default`, run by the HACS team and read by the Marketplace; a PR
   from a personal account adds `owner/repository` to its `integration`
   file, alphabetically, with the template filled in. Review is automated
   checks and then "months" in the queue (read on hacs.xyz and
   contributors.home-assistant.io/marketplace, 2026-11-06; not checked
   against `hacs/default` itself). Where this repository stands:

   | Requirement | Here |
   | --- | --- |
   | Public repository, owner submits, OSI licence | yes, MIT |
   | Description, topics, issues enabled | yes |
   | `hacs.json` with `name` | yes |
   | `manifest.json`: domain, documentation, issue_tracker, codeowners, name, version | yes; the name still ends "(preview)" |
   | Brand: `brand/icon.png` in the integration, or the domain in `home-assistant/brands` | `brand/` exists |
   | HACS action and hassfest pass with no ignores | yes: CI runs both and ignores no check |
   | **At least one full GitHub release** (a tag is not enough) | **no: every release is a pre-release** |
   | `categories` in `manifest.json` | yes, three, and `connectivity: ["modbus"]` |

   Open: whether a repository whose only releases are pre-releases passes
   (not stated); so the first stable release (0.1.0, not an alpha) is the
   real gate. Drop "(preview)" from the name on `main` only. The
   Marketplace refreshes the catalog every 6 hours and a repository added from
   a link every 48 hours.

3. **The preview channel under the Marketplace.** Home Assistant 2026.11
   is the minimum (`hacs.json`), where HACS is built in as Settings →
   Marketplace, and the docs describe the Marketplace alone: a preview
   installed through HACS on 2026.9 or 2026.10 is adopted when its Home
   Assistant is upgraded, so nobody needs a HACS step (decided 2026-11-12;
   what the testbed checked is in `doc/maintainer_setup.md` §5). The testbed
   is `make marketplace` (`hacs_testbed.sh --marketplace`: 2026.11.0 from
   `.venv-marketplace/`, `config-marketplace/`, :8126, login dev/dev;
   `ARGS=--adopt-hacs` starts from a copy of `config-hacs/`).

   Left: a screenshot of *Add from link* for
   `doc/installing_a_preview.md`, in place of HACS's custom-repository
   dialog, taken on `make marketplace`.

4. **The production database.** The migration is verified at real scale
   only against the maintainer's years-old YAML install; what to collect and
   how is in `doc/maintainer_setup.md`, section 8. Two routes: a copy of the
   instance's files (preferred: the migration can be run and rolled back, in
   the gitignored `.testdata/`, pointed at the simulator, never at the real
   inverter) or read-only API access (the entity map and statistics only).
   For the API: a non-admin user's token and the instance's address are in
   `~/.claude/secrets/` (never in this repository), but the hostname resolves
   to IPv6 only and the devcontainer has no IPv6 route, so it is unreachable
   from here until Docker gets IPv6 or an IPv4 address is given. Counts and
   mismatches are reported, no serial or address.

5. **The YAML track's documentation, for the integration.** The pages
   below open with a note that they are for the YAML package, pointing at
   `doc/installing_a_preview.md` and `doc/integration_migration.md`; the
   first-line documentation of the integration is `strings.json`. At the
   release, the note points at the ordinary install instead of the preview.

   | Page | To do |
   | --- | --- |
   | `legacy/doc/cleanup_entities.md` | Link it from a repair as the manual fallback, if one is built |
   | `legacy/doc/dashboard.md` | A generated dashboard (Future work) |

6. **Handing the preview channel's users over to the release.** There is
   no one-click switch: the Marketplace refuses to install an integration
   whose domain another installed repository owns, and refuses to remove one
   while a config entry of its domain exists, so the switch is five steps --
   delete the entry, remove the preview, download this repository, restart,
   set the integration up again. Home Assistant restores a deleted entity's
   id when the same platform and unique id come back within 30 days, so the
   ids, and with them the history, should come back; the options are asked
   again. How that was read out of core 2026.11.0, and the two routes that
   do not help, are in `doc/maintainer_setup.md` §5.

   **For the maintainer to decide**: keep the mirror running after the
   release, publishing `main`'s release tags under a name without
   "(preview)", so mirror users get an ordinary *Update* and never switch
   (proposed, since the switch costs a new setup), with a repair of our own
   naming the five steps for whoever wants the main repository; archive the
   mirror once few installs use it. To check on `make marketplace` once
   `main` carries the integration: that the five steps keep the ids and the
   history on a migrated install, and that a commit-tracked install switches
   to versions once the mirror publishes a release.

7. **Deprecating and retiring the YAML package, after the release.** Once
   the integration has parity, is merged into `main` and is in the HACS
   default store: deprecate `legacy/modbus_sungrow.yaml` and the generated
   multi-inverter files, announce it, point every `legacy/doc/` page at the
   integration and `doc/integration_migration.md`, and set a date after
   which the YAML package gets no further changes.

   Retiring does not end migration, so the legacy-id adoption, its guards
   and `tests/test_sensor_descriptions.py` stay as long as migration is
   offered. `tests/test_registers.py`'s comparison with the YAML can then be
   anchored to the specification instead; its scan-interval check goes first.

# Future work

## How far the MPPT energy drifts

*MPPTn energy* integrates voltage times current over the polls
(`sungrow_modbus.energy_integral`). Wanted from a house running it a few
days: the trackers' daily sum against *Daily PV generation*, on a cable and
through a WiNet-S, which says how much the polling interval and a dongle's
stale reads cost.

**No capability test measures it** (checked 2026-11-12): auto repeat's
plausibility checks compare *Daily PV generation* with the integral of
*Total DC power*, and each tracker's V × I with *Total DC power* at one
moment, but nothing integrates the trackers the way the sensors do.
Proposed: one more check of that kind, the trackers' summed V × I
integrated against the rise of *Daily PV generation*, riding on auto repeat,
whose median ratio in the ledger and the document is the drift asked for
here, per firmware and transport. Caveat: the check judges in decades (a
scale error), so a drift of a few percent comes out `MATCH` or
`INCONCLUSIVE` and the document must carry the median itself.

## A generated dashboard

Nothing generates one yet. Open: generate a Lovelace dashboard (asking
first), or rely on entity metadata and document the auto-generated view.

**The question to settle first: one default dashboard over houses that
differ.** An entry can carry an inverter alone, or an inverter with an SBR,
a wallbox and an external generator; a wallbox or an iHomeManager entry
carries neither. An entity exists only where its capability answered
(`Capability`, measured at setup), so a dashboard written for the richest
house reads *not available* on every other one, and one written for the
poorest shows almost nothing. The routes, none chosen:

- **Generated per entry, from the capabilities that answered.** One
  dashboard, built for the house it is built in, with no empty card by
  construction. It has to be rebuilt when a capability appears later (a
  battery added, a wallbox found), which wants a repair or an action rather
  than a silent rewrite, and it must never overwrite what the owner has
  edited since.
- **One shipped dashboard of conditional cards.** A card per device behind a
  condition on an entity of that device, so a device that is not there
  leaves no gap. Nothing to generate and nothing to keep per house, but a
  condition on `unavailable` also hides a device that is merely offline,
  which is the state an owner most wants to see; the condition has to be on
  the capability (the entity existing at all), not on its state.
- **A dashboard per device, linked from one view.** Follows the device
  pages, so nothing is ever empty, but it is several dashboards and not the
  one asked for.
- **Nothing of our own**: document Home Assistant's auto-generated view,
  which is what an install gets today.

Whatever is chosen is asked for and never installed by itself: a dashboard
that appears unbidden is a change to the owner's sidebar.
`legacy/doc/dashboard.md` is the YAML package's, and the material to port
(Release item 5); `doc/energy_dashboard.md` stays what it is, the Energy
dashboard being core's and not ours.

## Helping users set up the Energy dashboard

The guide is written and linked from the README (`doc/energy_dashboard.md`:
hybrid, SG, battery, wallbox, several inverters with a Sum helper for one
power total), and the ordinary setup's success dialog links it
(`ENERGY_DASHBOARD_GUIDE_URL`).

**Nothing can pre-fill the dashboard** (checked against Home Assistant
2026.11): core's `energy` component offers an integration only the solar
*forecast* platform, and the sources are the user's own preferences, so
anything that writes them needs an explicit action and a confirmation, never
a setup step.

Still proposed, in order of cost: a repair or a notification after setup
that names the same entities; an action that adds them to the dashboard,
only on request.

Unverified, each answered by one house, and stated as open in the guide:
whether the import and export totals need a meter fitted (what a house
without one reads), and whether the *Total …* energies, which keep the YAML
package's `total` state class, behave across an inverter reset. Feeds
`legacy/doc/dashboard.md`'s Energy dashboard row.

## Site-wide sensors for several inverters

Each inverter is its own config entry, so nothing adds them up, and the
answer today is documented helpers: `doc/energy_dashboard.md` (*Several
inverters*) says what to sum, what to take from the master only and what
never to sum.

Open: entities of the integration's own, **only if users ask**. They need
something above the one-entry-per-inverter rule (`doc/architecture.md`): the
entry that is the cluster's master owns a "Site" device, found by the roles
the diagnosis already measures (*measured* or *inferred*), and the sensors
are unavailable, not 0, when a member is. `total_site_pv_power` already
exists for the inverter that has a second one on its supply, so the Site
wording has a precedent.

Names, in the existing convention (sentence case, the device name added by
Home Assistant, the ids in English). **Agreed by the maintainer
2026-11-12**; they go into `scripts/generate/tables/naming.py` when the
entities are built:

| Entity | Name | Id (device "Site") |
| --- | --- | --- |
| Summed PV power | Site PV power | `sensor.site_pv_power` |
| Summed AC output | Site AC output power | `sensor.site_ac_output_power` |
| Summed daily PV energy | Site daily PV generation | `sensor.site_daily_pv_generation` |
| Summed total PV energy | Site total PV generation | `sensor.site_total_pv_generation` |
| Summed battery charge / discharge power | Site battery power | `sensor.site_battery_power` |
| The meter's own values, taken from the master | Grid power, as on the master | no new entity |
| Inverters in the sum | Site inverters counted | `sensor.site_inverters_counted` (diagnostic) |

The device: "Sungrow site" (or the system name the owner gives in setup),
with each inverter keeping its own "SH10RT" or name. German: "Anlage" for
site ("Anlage PV-Leistung", "Anlage Tagesertrag PV"). A user who wants other
words renames the helper, not the integration.

## Renames and the databases outside Home Assistant

The stores that do not follow the recorder -- InfluxDB and with it Grafana,
Prometheus, MQTT statestream, Node-RED -- get the print-only script
(`scripts/helpers/influx_migration.py`) and a guide a user follows or hands
to an AI assistant (`doc/influx_migration_llm_guide.md`, linked from
`doc/integration_migration.md`). There is no built-in path: the integration
cannot reach the user's InfluxDB, and versions, measurement settings and
downsampling differ per installation. The legacy-id adoption keeps ids, so
most users need neither.

Open: what the integration should do when an id does change (a repair naming
the affected entities and linking the guide; an export of old and new ids),
how a rename after release is announced, and whether a real InfluxDB with
migrated data is worth testing once the production copy exists (Release item
4). The guide has never run against a real InfluxDB.

## The wallbox: the direct connection first

A wallbox with an address of its own is an entry of its own and the only one
that writes to it; an inverter entry leaves it out by its serial (decided and
built 2026-11-12: `doc/architecture.md`, wiki `device-wallbox.md`). Left:

1. **The search's result says it.** Where the search finds an inverter
   behind a WiNet-S and a wallbox on 516, the list could say that the
   wallbox will be read on its own and not through the inverter. Today the
   inverter entry simply gives it up once the wallbox entry is added.
2. **On hardware at gerd's**: his inverter entry (WiNet-S) and his wallbox
   entry side by side, to see the inverter entry give the wallbox up after a
   reload, and take it back when the wallbox entry is deleted.
3. **The options screenshot** (`HA-settings-configure-capability-test.png`)
   still shows the two wallbox fields an inverter entry no longer has;
   retake it (`doc/development.md`, *Screenshots for the docs*).

Open, unchanged: Modbus over TLS on a **WiNet-S's** own 516 for the
inverter. Worth building only if 516 is a *separate* session pool from 502:
hold 502 until it refuses, then try 516. The certificate is settled (wiki:
`device-winet-s.md`): one certificate is built into the firmware, its key is
on every unit, and verifying it gains nothing.

## EVCC connection

- Hand inverter and wallbox readings to evcc, e.g. over MQTT, so evcc
  need not open a Modbus session of its own. To find out: does evcc have
  a standard configuration for that?

## Recurrent: new diagnoses to ingest (daily, after noon)

Every day after noon, read the general diagnosis thread
([#786](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/786))
and any issue a diagnosis was posted to since the last check. Comments older than
the last check are done; read only what is newer. Ingest each new
diagnosis as `.wiki/AGENTS.md` describes (raw file, source page, entity pages,
index, log), and name the contributor (without `@`) and the issue number in
the commit; a diagnosis signed `anonymous` stays unnamed. Then move the date
below on.

```bash
gh issue list -s all --search "updated:>=2026-11-16T10:00:00Z" -L 50
gh api 'repos/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/comments?since=2026-11-16T10:00:00Z&per_page=100' \
  -q '.[] | "\(.issue_url | split("/") | last) \(.user.login) \(.created_at)"'
```

Last checked: **2026-11-16 10:00 UTC**: #786 brought the retry that was
asked for -- a diagnostics download with an **AC011E-01 at unit 4 behind a
WiNet-S**, ingested, anonymous in the document and so unnamed. It is the
third wallbox read and the first that is not an AC22E-01: it answers which
unit a WiNet-S gives a wallbox (not always 3) and confirms 21203 at 0.1 A
per count on the model whose other map reads it as 0.01 A. It carries none
of blocker 15's three masked blocks. Only the general diagnosis thread was
read, by the comment the maintainer named; the issue sweep was not run.

## Recurrent: llmwiki upstream check (every 6 weeks, next: 2026-12-10)

The wiki follows `@llmwiki/core` **0.1.2** (microsoft/llmwiki at `e09126f`).
Check upstream for changes to the index, log or frontmatter format
(`packages/core/src/init.ts`, `lint.ts`, `index-ops.ts`, `log.ts`) and to its
lint rules. If something changed, update `tests/test_wiki.py` and
`.wiki/AGENTS.md` together, and bump the version named in both and in
`.wiki/wiki/log.md`. Then move the date above six weeks on.
