Todo.md contains only what is still to do (forward looking).
Anything done is removed here; history goes into git and `.wiki/wiki/log.md`.

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

1. **The site import limit (32998): the cases still open.** Measured
   (wiki: mkaiser-import-limit-*, bar12-import-limit-*, gerd-import-limit-*): under a charge the cap is on grid import alone, PV counted,
   on P020, P022 and P023, over the cable and through a WiNet-S, whether
   the charge is commanded by the EMS registers or the forced-charging
   schedule (on P022 the schedule only through the dongle, wiki:
   gerd-import-limit-schedule-2026-11-08); it settles within ~2-6 s, 0-3 % over the cap on P020, at it
   on P022, ~5 % under on P023; 0 and 5001 are refused.
   It does not cap house load: not with the battery held idle by a forced
   stop (P020), and not with the battery empty in normal operation (P023).
   With PV above the load it disturbs neither a charge from PV nor export
   (P020, wiki: mkaiser-import-limit-export-2026-11-08), and with the
   discharge limit below the load it does not draw on the battery past it
   (P020, wiki: mkaiser-import-limit-discharge-2026-11-08). It is the
   number *Grid import limit* (W, 10 W step) on P020, P022 and P023, where it
   replaces the read-only sensor.

   | # | PV | Battery | Command | Question | How, where |
   | --- | --- | --- | --- | --- | --- |
   | e | above the load | part full | forced charge above the surplus | the grid's share capped, PV counted | the engine check, daylight |

   Not worth a run: a full battery at night, a forced charge into a full
   battery (the engine skips at 90 %), a forced discharge.

   **The engine refuses an inverter in low-SoC Standby** ("reports
   'Standby'"), though a forced charge wakes one by itself in ~2 min (EMS
   or schedule, bar12). Whether the import-limit check should command its
   charge and wait for the start instead of refusing: decide with the
   diagnosis's rework.

   **Register 13017 is a switch, not a command** (wiki:
   bar12-forced-startup-2026-11-07 on P023, mkaiser-forced-startup-2026-11-08
   on P020): 0xAA wakes a low-SoC standby inverter and keeps it running,
   0x55 sends it back, both read back, every other word is refused, and the
   factory 0 cannot be written back. It is the switch *Forced startup under
   low SoC*, on P020 and P023. Still unmeasured: whether the inverter resets
   it by itself later or on PV (#444 reports 0xAA to 0x55 after ~20 min),
   and P022 or any other firmware.
2. **The inverter's own consumption, on hardware.** Built: *Inverter self
   consumption (estimated)* (`Derived.inverter_self_consumption`, PV +
   battery - export - load, shown as a one-minute time-weighted mean, no
   legacy id: #626 never shipped). The battery term is 5214 where it
   answers, else 13022 signed by 13001's bits (as evcc), so the sensor
   exists where 5214 is refused (#655). Left: look at it on the
   maintainer's SH10RT by day and night, whether the mean is steady enough
   and plausible (tens of watts at night); the 13022 path on a house that
   refuses 5214; its energy counterpart.

## Battery

Nothing can start now (blocker 13).

## Wallbox

3. **Writing to the wallbox: measure the output current's scale at gerd's.**
   The wallbox is read only. Three sources disagree on the output current
   setting, holding 21203: 0.1 A per count here, 0.01 A in discussion #571, a
   factor ten on a mains charger. No wallbox control is built until a measured
   run settles it.

   Built and tested (59 tests, 99 % of the procedure): the procedure,
   `src/sungrow_modbus/wallbox/capability_test.py`, and its terminal driver,
   `device-diagnosis/scripts/python/sungrow_wallbox_capability_test.py` (TLS 516,
   unit 248 only; no `--leave` is a dry run; `--enable`, `--phase`,
   `--start-stop`, `--max-amps`, `--restore`). It offers 6, 8 and 10 A, safe at
   either scale; flushes a snapshot before the first write; reads the raw word
   back on a fresh session (a same-session read after a write answered another
   register); restores the snapshot's raw word, never skipped. The enable step
   disables and re-enables (status 8 in between); the phase step switches only
   when nothing flows. It refuses to write when the setting reads 0.

   What gerd's wallbox said in the dry run (wiki:
   `gerd-wallbox-dry-run-2026-11-06-summary.md`): idle, with no car, the
   setting reads **0** (160 and 151 while charging), so an idle wallbox cannot
   separate the two scales and the meaning of 0 is not known. Input 21322 is
   not the setting's echo.

   Built in the tree, not released (`plans/wallbox_capability_tests.md`,
   steps 1 to 4): the wallbox's tests run from Home Assistant's *Extended test
   (auto repeat)* (`custom_components/sungrow_modbus/wallbox_capability_test.py`,
   `DiagnosisRunner.async_start_wallbox`, the wallbox tick in `continuous.py`),
   over the entry's own connection (no fresh session, so only what the car
   does counts), with a snapshot flushed first and put back first by the next
   run if one is left, a ledger per wallbox firmware
   (`wallbox/ledger.py`, counted with the inverter's checks), and the new
   checks: current follow across the range with timings, below the minimum,
   above the rating, available current against the setting, timed start/stop
   and enable, phase switch while charging (stop seen before 21204 is
   written), 75 s of silence, the mileage no-op. The plausibility checks are
   `wallbox/plausibility.py`, fed by auto repeat's tick. The options are
   *May it write to the wallbox* (off until switched on) and *the highest
   charging current* (`wallbox_max_amps`); the three checks that go beyond
   the default 10 A wait until the owner sets it.

   Left, in order:

   0. Released in 0.1.0a34; the terminal driver pins it.
   1. **One window with gerd and a car charging**, so the setting holds a
      real current: his evcc off, the option on and `wallbox_max_amps` set to
      what his installation takes, the first run watched live before auto
      repeat is left alone with it. His consent covers any test while
      charging. Then ingest a day of it (plan step 5): the wiki's wallbox
      pages, `doc/wallbox_registers.md`, `log.md`.
   2. **Then entities**: a charging current number and an enable switch, on
      what was measured, through the write table
      (`scripts/generate/tables/writes.py`), with the wallbox's 60 s
      fallback in mind, and a report in discussion #571 (rudolf992,
      2026-04-27, unmeasured): in EMS mode the current set over Modbus went
      back to iSolarCloud's value within seconds.

   **The search finds every device** (`plans/device_scan_and_diagnosis.md`,
   its status log is current): a wallbox at its own address is an entry of
   its own, with read-only entities, a diagnosis and **its own capability
   test** (`wallbox_diagnosis.py`; leave and cap in its options; auto repeat
   every 15 minutes). Checked at gerd's in the dev HA with no car: it refuses
   to write while idle, as it should. Auto repeat ran there 2026-11-10 from
   09:30 for an hour: no car came, so no run started (the right outcome).
   Item 1 above applies to it too: its
   first writing run needs a car charging, watched live. A `wallbox_host`
   entry is never moved onto one (decided). A Logger (unit 247) is offered
   as a diagnosis-only entry, untested on hardware: asked for in
   `device-diagnosis/devices-wanted.md`. An iHomeManager's entry has its
   readings too (iHomeManager, below). Not yet: the search
   showing which inverters sit behind a Logger (decided yes; how a Logger is
   handled beyond that is open).

   Not to copy: evcc's `sungrow.go` reserves all rights. Inverter work at
   gerd's waits until his Home Assistant is stopped: a read-only diagnosis
   on 2026-11-06 ran into it and is not evidence. On 2026-11-10 inverter
   auto repeat through his WiNet-S (dev HA, 09:31 to 12:10) ran without a
   guard refusal: 5 runs, 0 findings, every setting put back; readback
   verdicts through a dongle are not evidence (since 0.1.0a36 a dongle's
   "kept its old value" is inconclusive, no longer "not supported").
   Whether his own Home Assistant was polling then is not known. Both auto
   repeats are stopped; next is his own HA on 0.1.0a36, over the cable if
   it reaches one, battery above 20 %, a car charging.

## Logger

Nothing can start now (blocker 16).

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

5. **The diagnosis and its capability tests.** In the code: three modes in
   *Diagnosis: mode* (read-only, extended test single run and auto repeat),
   started by *Diagnosis: start* and ended early by *Diagnosis: stop*, a
   `features` section in every document (schema 25), the *Diagnosis* column
   and the measured findings in `doc/firmware_support.md`, and the forced
   startup mode (`diagnosis.sh tests <host> --forced-startup`). What each
   capability can be tested with is `doc/capability_tests.md`. Left:
   1. **A first run of the forced startup mode on hardware.** The start is
      watched by one-off scripts on P020 and P023 (wiki: register-13017);
      the engine's own mode (`--forced-startup`, or the action's
      `forced_startup: true`) has not run on an inverter yet: one in
      low-SoC standby, after dark. The SH-RT's factory 0 goes back as
      0x55, the one `RESTORE_EQUIVALENT` (AGENTS.md).
   2. **The new checks on hardware** (`doc/capability_tests.md`). First run
      on 2026-11-08 to 11-10, at peter_sm (P023, cable, five runs) and
      ra1k_0 (P071, WiNet-S, one run); ingested. Ran:
      - the write paths (backup mode, load control, weekend enable): taken at
        both;
      - window 2 read back with the schedule off: taken at peter_sm; not at
        ra1k_0 (its schedule is on);
      - each EMS option: taken at ra1k_0; at peter_sm mode 3 lost the
        connection in two runs of three;
      - each number a step above its maximum: 13058 and 13059 refuse on P023,
        33048 on P071; P023 stores the rest (not enforced), and through the
        dongle whether it stored them cannot be read;
      - the discharging start threshold: confirmed at peter_sm; skipped at
        ra1k_0 (33149 did not answer the run's probe);
      - 13088 beside the export check: at peter_sm it follows 13074 as a
        share of the rating (12.5 % for 1250 W of 10 kW).
      Not yet seen on hardware:
      - **the charging start threshold**: needs a battery charging a few
        hundred watts from PV;
      - **`ledger.TWO_MOMENTS`**: a check established by day measured again
        at night, on one firmware; needs auto repeat across a dusk;
      - **the plausibility checks** (`capability_test/plausibility.py`): no
        committed document carries a `plausibility` block, because they are
        fed only by auto repeat;
      - **anything on a WiNet-S beyond one run**, and any T-series cable.
      The night re-check and the plausibility checks need one auto-repeat
      collection at the maintainer's SH10RT over a day and a night, which
      may catch a slow PV charge for the threshold too; then ingest. The
      wallbox's tests are planned in `plans/wallbox_capability_tests.md`.
   3. **Outside the repository**: issue #786's title still says survey, and
      the repository variable `SURVEY_ISSUE` keeps its name.
   4. **Capability test runs over a day.** Home Assistant keeps every run per
      firmware and folds them into one schema-3 block
      (`capability_test/ledger.py`; the *Diagnosis: test summary* sensor
      with a run's elapsed time, five counters by outcome, a notification
      rewritten per run, *Diagnosis: tests, clear history*), and the mode
      *Extended test (auto repeat)* starts runs when a missing check is due
      (`continuous.py`), leaving out what is established, the restart
      included. The terminal's `--merge-into` folds a run into
      the runs a document carries (`--replace` puts it in their place).
      Released in 0.1.0a30. Left:
      1. **The slot schedule on hardware**: one night at the maintainer's
         SH10RT, to see that low-SoC Standby starts no run and *Diagnosis: next
         start* names the next slot. Runs are kept with no cap, so a long
         collection grows the stored ledger and the diagnostics download
         (19 runs were 265 kB); clear the history between collections.
      2. **The charge window with no room to charge**: the headroom under
         `snapshot.battery_ceiling` is now looked at before the window is
         written (2026-11-09); the 300 W floor after it still skips a battery
         charging a few hundred watts with kilowatts of headroom, unless the
         bracket confirms the start first.
      3. **Translate** the status line, the step sensor's states (*waiting
         for changed test conditions*, *stopped*) and the notifications once
         their wording settles; English for now.
      4. **Diagnosis: stop on hardware**, mid part B: that the restore reads
         every word back and no restart starts. Only the simulator has seen
         it.
      5. **The *Diagnosis:* names on a real device page**, in English and
         German, once released: that the *Diagnostic* card keeps them
         together in the order `doc/entity_names.md` shows (the frontend's
         collation was not checked in the container), and that the
         counters read sensibly after a day's runs.

# Open decisions

1. **Are the entity names final?** They are reviewed and decided, English
   and German (`doc/entity_names.md`, `plans/text_translation_review.md`,
   `scripts/generate/tables/naming.py`); both ship, German as
   `translations/de.json`, and entity ids stay English in every language
   (`doc/architecture.md`). A rename later leaves existing ids alone and
   only diverges new installs, which a registry migration can close, so it
   stays cheap until release, not free. A new name goes under **To
   discuss** (`NAME_DISCUSSION` in `naming.py`).

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

15. **A second wallbox's diagnosis.** Settles whether 21211-21214 identify the
    unit. The wallbox reports its own serial (input 21201-21206, 11 ASCII
    characters, as Sungrow's portal shows it); the
    integration shows it on the device page, identifies the device by the
    inverter's serial plus `-wallbox`, and publishes it only as a stand-in.
    Three registers wait on a second unit:
    input 21201-21206 (the serial: use it as the device identity?), input
    21211-21214 (a short code, masked), and holding 21250-21259 (twenty
    constant ASCII digits, masked). Whichever differ between
    two wallboxes identify a unit and stay masked; whichever match are a model
    constant and can be unmasked. 2026-11-10: a second AC22E-01 arrived
    (anonymous, #786), but both documents publish these blocks as `null`,
    with no stand-in per block, so the files cannot say whether they
    differ. Settling it needs the masking to publish a stand-in for each
    masked block (a hash compares without revealing), and a third reading,
    or the two owners comparing their own transcripts. 2026-11-11: gerd's
    serial as iSolarCloud shows it hashes to gerd's published stand-in, so
    21201-21206 is the serial the portal shows (checked locally, recorded
    nowhere).

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

17. **A first iHomeManager diagnosis** (#786). **Met 2026-11-10**: one unit
    on SV930.001.00.P020, port 503, answered all 56 mapped fields (wiki: the
    iHomeManager source page). Its protocol number is read low word first
    since. Still open from that one unit: whether 4358-4362 are U32 (4359 and
    4361 read 0), what 8554 means (0, "single phase", on a three-phase site),
    and the codes 8047 = 0, 8048 = 0xA7 and 8051 = 0, which the map does
    not know. A second unit, on other firmware, would say which of these
    are the device's; until then the entities leave 8554 and those codes
    out. Sungrow's protocol PDF:
    https://github.com/TCzerny/ha-modbus-manager/blob/main/docs/Communication%20Protocol%20of%20iHomeManager_V1.0.2.pdf

## Integration and tooling

18. **Does a WiNet-S advertise over mDNS?** Yes at gerd, asked by unicast over
    the VPN (wiki: the mDNS query): the dongle and the wallbox advertise
    `_http._tcp` with TXT records naming model, serial and units, the dongle's
    for every device behind it. 2026-11-11: python-zeroconf (HA's library)
    resolves both and parses the TXT into properties, by QU queries from
    port 5353 aimed at each device; the inverter's LAN port answers nothing.
    Outstanding:
    - **A multicast browse on a LAN.** Nothing multicast crosses the VPN or
      the container. `probe.py mdns` on a machine in a house with a dongle
      (`pip install sungrow-modbus[discovery]`), or the diagnosis step below.
    - **Other firmware, other houses.** One dongle and one wallbox so far.
    - **Does `ethinfo` say wired or WiFi?** It is empty on gerd's dongle,
      which is on WiFi; it may carry the Ethernet details when the dongle is
      wired. Answer it from the diagnoses already covered: once the
      diagnosis records the dongle's TXT, compare `ethinfo` with
      `user_inputs.transport` (`winet_lan` / `winet_wlan`) across the corpus.
      bar12 has published both transports of one dongle, so a rerun there is
      the cleanest pair. If it holds, `wifi_or_ethernet` (today "not
      determinable over Modbus") can say what the dongle reports.
    - **The fields nothing explains**: the battery's 8423 (0x20E7), the
      inverter's trailing `1;4`, the wallbox's `info=16256` (0x3F80), every
      `;1;`. More houses, compared with what Modbus measured there.
    - **mDNS in the diagnosis.** Part A runs on the contributor's machine in
      the LAN, where multicast works: browse `_http._tcp` for a few seconds,
      keep the Sungrow records (TXT, port, model), serials and host names
      replaced by stand-ins before anything reaches the document, and record
      "no answer" as that, never as "no dongle" (container, VLAN, firewall).
      Needs `async_mdns_services` in a released wheel and `zeroconf` in the
      PEP 723 header (`device-diagnosis/reference.md`); check whether binding
      port 5353 raises a Windows firewall prompt. In Home Assistant, the
      device page's diagnosis browses through HA's shared zeroconf instance
      (`zeroconf` in `after_dependencies`), not sockets of its own.
    - Then decide on a `zeroconf` matcher in the manifest: the records as a
      hint that the Modbus check confirms, the sweep kept for cable-only
      inverters. And a WiNet-S's *Visit* link for a cable entry, found by
      the inverter serial in its TXT (a link on the inverter, or the dongle
      as its own device).

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
2026-11-06). It needs: the ordinary setup switched on (item 1,
`ONLY_DIAGNOSIS_MODE`), a stable `0.1.0` rather than an alpha (item 2), the
production-database run or a decision to go without it (item 4), the
catalog submission on release, not before (item 2), and
`doc/integration_migration.md` made current.

1. **When to offer the ordinary setup**, targeted for December 2026 (the
   maintainer, 2026-11-06) (`ONLY_DIAGNOSIS_MODE` in `const.py`;
   turning it off is the whole re-enablement, `tests/test_alpha_gate.py`),
   and **when to merge into `main`.** The merge retires the preview channel
   and opens the HACS default store, which also needs the brand in
   `home-assistant/brands` (`scripts/helpers/make_brand_icon.py` draws it).
   At the merge, the links that name the `proper-ha-integration` branch move
   to `main` (`grep -rn proper-ha-integration custom_components`: the Energy
   dashboard guide and the preview repair's entity names).

2. **Submitting to the catalog, when the merge is decided.** Read
   2026-11-06 (a subagent's reading of hacs.xyz and
   contributors.home-assistant.io/marketplace; not checked against
   `hacs/default` itself): the route is unchanged. The catalog is still
   `hacs/default`, run by the HACS team and read by the Marketplace; a PR
   from a personal account adds `owner/repository` to its `integration`
   file, alphabetically, with the template filled in. Review is automated
   checks and then "months" in the queue. Where this repository stands:

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

3. **The preview channel under the Marketplace.** In Home Assistant 2026.11
   HACS is built in as Settings → Marketplace, and the HACS installer stops
   at 2026.11. The Marketplace offers stable releases only, unless the user
   turns on a repository's *Pre-release* switch. The preview channel
   publishes no releases, so it is tracked by commit hash. The testbed is
   `make marketplace` (`hacs_testbed.sh --marketplace`: 2026.11.0 from
   `.venv-marketplace/`, `config-marketplace/`, :8126, login dev/dev;
   `ARGS=--adopt-hacs` starts from a copy of `config-hacs/`).

   Verified on 2026.11.0, 2026-11-06, adopting a HACS install of preview
   0.1.0a17 (commit `2d735b1`): the Marketplace took over 4 entities and 2
   devices, adopted HACS's stored data, removed `custom_components/hacs`, and
   kept the preview as an installed, commit-tracked repository. It reported
   `pending_upgrade` (available `e0d1840`) with no GitHub connection, and
   `marketplace/repository/install` installed it without one (only
   *detect* and *add*, that is *Add from link*, are marked `requires_github`
   in the source). After a restart Home Assistant pip-installed
   `sungrow-modbus==0.1.0a26` from PyPI against the manifest pin, with
   `modbus-connection` 4.12.7 and `tmodbus` 1.1.0, and the integration
   loaded (the copied entry then failed only to reach its old inverter
   address). The stored `hacs/integration` entry was gone after the restart.

   Verified on 2026.11.0, 2026-11-08, from a fresh `make marketplace
   ARGS=--reset`: with GitHub connected, *Add from link* (the preview
   repository's URL, type *Integration*) added and downloaded the channel at
   commit `d0fbbee`, its HEAD, with no *Pre-release* switch turned on
   (`switch.sungrow_modbus_preview_pre_release` exists, off). Home Assistant
   then pip-installed `sungrow-modbus==0.1.0a30` from PyPI, and the
   maintainer's SH10RT was found, added and diagnosed. All three questions
   are answered, and the docs say so. Keep the HACS path in them while
   `hacs.json` allows 2026.9 and 2026.10.

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

6. **Handing the preview channel's users over to the release.** Read in
   core 2026.11.0's Marketplace source (`.venv-marketplace`,
   `components/marketplace`), 2026-11-07; nothing tried on the testbed yet.

   **There is no one-click switch.** The Marketplace refuses to install an
   integration whose domain another installed repository owns ("The
   sungrow_modbus directory belongs to ...-preview", `async_pre_install` in
   `repositories/integration.py`), and refuses to remove one while a config
   entry of its domain exists ("still set up ... Delete it under Settings >
   Devices & services before uninstalling it", `repository_in_use` in
   `websocket/repository.py`). So the switch is five steps: **delete the
   entry**, **Remove** the preview, **Download** from this repository,
   restart, and **set the integration up again**. Home Assistant restores a
   deleted entity's id when the same platform and unique id come back within
   30 days (`ORPHANED_ENTITY_KEEP_SECONDS` in `entity_registry.py`), so the
   ids, and with them the history, should come back; the options are asked
   again. Not tried: that the restore and the legacy-id claim agree on a
   migrated install. Two more routes that do not help:
   - The catalog's `removed` feed raises a repair for an installed
     repository it lists (`async_handle_removed_repositories` in `base.py`),
     but that repair is not fixable: it only links the repository's page.
     Unknown: whether `hacs/default` takes a removal entry for a repository
     that was never in the catalog.
   - A GitHub rename carries over by repository id
     (`_async_take_over_catalog_entry`), but two repositories cannot be
     merged into one, so no rename moves the mirror's users.

   The options:
   1. **Zero clicks: keep the mirror going after the release.** `sync.yml`
      follows `main`'s release tags and publishes the same release on the
      mirror, with the name lacking "(preview)". Mirror users get an
      ordinary **Update** and never have to switch. Costs a second
      repository for as long as anyone is on it.
   2. **A repair of our own** that names the three steps above, raised when
      the integration was installed from the mirror (a marker `sync.yml`
      writes, such as a constant in `const.py`; the Marketplace's stored data
      also names the repository, but that is its internals). A fix flow that
      drives the Marketplace's remove and install would use its websocket
      API (`marketplace/repository/install`) from a custom integration: not
      worth the fragility.

   Proposal: 1 at the release, since the switch costs a new setup, with 2
   alongside it for whoever wants the main repository; archive the mirror
   once few installs use it. To check on `make marketplace` once `main`
   carries the integration: the five steps keep the ids and history on a
   migrated install, and a commit-tracked install switches to versions once
   the mirror publishes a release.

7. **Deprecating and retiring the YAML package, after the release.** Once
   the integration is complete (parity with the YAML package, merged into
   `main`, in the HACS default store), deprecate `legacy/modbus_sungrow.yaml`
   and the generated multi-inverter files, then retire them: announce it,
   point every `legacy/doc/` page at the integration and
   `doc/integration_migration.md`, and set a date after which the YAML
   package gets no further changes.

   What retiring does not end: anyone may still migrate later, so the legacy-id
   adoption and its guards stay as long as migration is offered.
   `tests/test_sensor_descriptions.py` (ids, unit class, `state_class` against
   `doc/legacy_entity_map.json`) keeps history continuous and stays.
   `tests/test_registers.py`'s comparison with the YAML can then be anchored to
   the specification instead; its scan-interval check goes first.

# Future work

## How far the MPPT energy drifts

*MPPTn energy* integrates voltage times current over the polls
(`sungrow_modbus.energy_integral`). Wanted from a house running it a few
days: the trackers' daily sum against *Daily PV generation*, on a cable and
through a WiNet-S, which says how much the polling interval and a dongle's
stale reads cost.

## A generated dashboard

Nothing generates one yet. Open: generate a Lovelace dashboard (asking
first), or rely on entity metadata and document the auto-generated view.

## Helping users set up the Energy dashboard

Investigated 2026-11-06 against Home Assistant 2026.11. Findings:

- **No hook to pre-fill it.** Core's `energy` component has one platform hook
  for integrations, the solar *forecast* (`async_get_solar_forecast`, for a
  forecast provider, not for an inverter). The sources are saved through
  `energy/save_prefs`, and `EnergyManager.async_update` could merge entries
  from the integration, but that edits the user's own preferences: only with
  an explicit action and a confirmation, never on setup.
- **What the dashboard accepts.** An energy-class sensor in kWh with the
  state class `total` or `total_increasing` (Wh and kWh both). Ours qualify,
  54 entities (hybrid 18, derived 13, SG 21, wallbox 2, in Wh). Offered in a
  list of that size the user
  picks by name, and several names are traps: *Daily …* resets at midnight,
  *Total PV generation & battery discharge* double counts, *(smoothed)* is for
  a card, *MPPTn energy* is the integrated estimate.
- **What to pick** (hybrid, names as shipped): grid consumption *Total
  imported energy*, grid return *Total exported energy*, solar *Total PV
  generation*, battery in *Total battery charge energy*, out *Total battery
  discharge energy*, and under individual devices the wallbox's *Total
  charged energy*. An SG: its *Total PV generation*, *Total exported energy*
  and *Total imported energy*. Several inverters: each is a solar source of
  its own, so no sum is needed; the battery comes from the inverter that has
  it.
- **Unverified:** whether the import and export totals need a meter fitted
  (what a house without one reads), and whether the *Total …* energies, which
  keep the YAML package's `total` state class, behave across an inverter
  reset. Both want a house to check before a guide states them.

Done: the user guide, `doc/energy_dashboard.md` (hybrid, SG, battery,
wallbox, several inverters with a Sum helper for one power total), linked from
the README. The ordinary setup's success dialog links it
(`ENERGY_DASHBOARD_GUIDE_URL`). Still proposed, in order of cost: a repair or
notification after setup that names the same entities; an action that adds
them to the dashboard, only on request. The guide states the
two unverified points; each is answered by one house. Feeds `legacy/doc/dashboard.md`'s
Energy dashboard row below.

## Site-wide sensors for several inverters

Each inverter is its own config entry, so nothing adds them up. Today the
answer is documented helpers: `doc/energy_dashboard.md` (*Several
inverters*) says what to sum with a Sum helper, what to take from the master
only and what never to sum, from fwitten's master and slave (committed
diagnoses, 2026-10-29, P023 cables; the slave has no meter and no battery).

Open: entities of the integration's own, **only if users ask**. They need
something above the one-entry-per-inverter rule (`doc/architecture.md`): the
entry that is the cluster's master owns a "Site" device, found by the roles
the diagnosis already measures (*measured* or *inferred*), and the sensors are
unavailable, not 0, when a member is. `total_site_pv_power` already exists
for the inverter that has a second one on its supply, so the Site wording
has a precedent.

Naming suggestions, in the existing convention (sentence case, the device
name added by Home Assistant, the ids in English):

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

How to deal with entity renames, the user-visible ones and the ones a
future name change would cause, for the stores that do not follow the
recorder: InfluxDB, and with it Grafana, Prometheus, MQTT statestream and
Node-RED. They get the print-only script (`scripts/helpers/influx_migration.py`)
and a step-by-step guide a user follows or hands to an AI assistant
(`doc/influx_migration_llm_guide.md`, linked from
`doc/integration_migration.md`). No built-in path: the integration cannot
reach the user's InfluxDB, and versions, measurement settings and
downsampling differ per installation. The legacy-id adoption keeps ids, so
most users need neither. Checked against the maintainer's production
registry (local only, never committed): every YAML statistic a description
replaces keeps its unit class and sum/mean kind, and the YAML templates'
values match `derived` over three days of history.
Open: what the integration should do when an id does change (a repair that
names the affected entities and links the guide; a list of old and new ids
a user can export), how a rename after release is announced, and whether a
real InfluxDB with the migrated data is worth testing once the production
copy (Release item 4, `doc/maintainer_setup.md` §8) exists. The guide has
not yet been run against a real InfluxDB.

## Modbus over TLS on a WiNet-S's 516

Built for a wallbox's own address (`wallbox_host`,
`links.wallbox_tls_params`). For the dongle it is worth building only if 516
is a *separate* session pool from 502: hold 502 until it refuses, then try
516. The certificate is settled (wiki: `device-winet-s.md`): gerd's WiNet-S,
his wallbox and bar12's WiNet-S serve one certificate, so it is built into the
firmware, its key is on every unit, and verifying it gains nothing.

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
gh issue list -s all --search "updated:>=2026-11-11T20:00:00Z" -L 50
gh api 'repos/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/comments?since=2026-11-11T20:00:00Z&per_page=100' \
  -q '.[] | "\(.issue_url | split("/") | last) \(.user.login) \(.created_at)"'
```

Last checked: **2026-11-11 20:00 UTC**: nothing new since 2026-11-10 15:19 in
#786 or any issue; every issue and discussion this file cites was read, and the
leads in discussions #262, #546 and #571 are recorded where they apply.

## Recurrent: llmwiki upstream check (every 6 weeks, next: 2026-12-10)

The wiki follows `@llmwiki/core` **0.1.2** (microsoft/llmwiki at `e09126f`).
Check upstream for changes to the index, log or frontmatter format
(`packages/core/src/init.ts`, `lint.ts`, `index-ops.ts`, `log.ts`) and to its
lint rules. If something changed, update `tests/test_wiki.py` and
`.wiki/AGENTS.md` together, and bump the version named in both and in
`.wiki/wiki/log.md`. Then move the date above six weeks on.
