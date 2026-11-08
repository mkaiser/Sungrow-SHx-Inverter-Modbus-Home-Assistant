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
Numbers run on across the groups, so a reference such as "blocker 17"
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
   (P020, wiki: mkaiser-import-limit-export-2026-11-08).

   | # | PV | Battery | Command | Question | How, where |
   | --- | --- | --- | --- | --- | --- |
   | a | none | part full | normal operation, load above the battery's discharge limit (33048 lowered) | does the cap draw on the battery past its limit? expected no | script, the maintainer's SH10RT, any evening |
   | e | above the load | part full | forced charge above the surplus | the grid's share capped, PV counted | the engine check, daylight |

   Not worth a run: a full battery at night, a forced charge into a full
   battery (the engine skips at 90 %), a forced discharge.

   **The engine refuses an inverter in low-SoC Standby** ("reports
   'Standby'"), though a forced charge wakes one by itself in ~2 min (EMS
   or schedule, bar12). Whether the import-limit check should command its
   charge and wait for the start instead of refusing: decide with the
   diagnosis's rework.

   **Register 13017 is a switch, not a command** (wiki:
   bar12-forced-startup-2026-11-07, P023): 0xAA wakes a low-SoC standby
   inverter and keeps it running, 0x55 sends it back, both read back,
   every other word is refused, and the factory 0 cannot be written back.
   It is now the switch *Forced startup under low SoC*, on P023 only.
   Still unmeasured: whether the inverter resets it by itself
   later or on PV (#444 reports 0xAA to 0x55 after ~20 min), and any other
   firmware (the maintainer's SH10RT on P020, with its battery at minimum).

## Battery

Nothing can start now (blocker 14).

## Wallbox

2. **Writing to the wallbox: measure the output current's scale at gerd's.**
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

   Left, in order:

   1. **A release that contains the procedure**, so the driver's pinned wheel
      has it (until then it says so and exits 2). Or run it from a checkout,
      as the dry run was.
   2. **One window with gerd and a car charging**, so the setting holds a
      real current: his Home Assistant and evcc off, one TLS session, the
      lowest current first, never above his installation's limit, no phase
      switch with the car charging. His consent covers any test; ask again
      for writes with a car attached. A car drawing more than a tenth of the
      setting already rules out 0.01 A per count before the first write.
   3. **Then entities**: a charging current number and an enable switch, on
      what was measured, through the write table
      (`scripts/generate/tables/writes.py`), with the wallbox's 60 s
      fallback in mind.

   Not to copy: evcc's `sungrow.go` reserves all rights. Inverter work at
   gerd's waits until his Home Assistant is stopped: a read-only diagnosis
   on 2026-11-06 ran into it and is not evidence.

## Logger

Nothing can start now (blocker 17).

## iHomeManager

Nothing can start now (blocker 18).

## Integration and tooling

3. **Home Assistant 2026.11: the diagnosis's headers.** The
   dev environment and CI run 2026.11.0 with modbus-connection 4.12.7 and
   tmodbus 1.1.0, tested with core's own `pytest-homeassistant` (2026.11.0),
   which replaced `pytest-homeassistant-custom-component` (that one stops at
   2026.10.4 and is declared broken upstream). The integration keeps
   supporting 2026.9 (`requirements_dev.txt` says why). Left:
   1. **The diagnosis's PEP 723 headers** (`sungrow_diagnosis.py`,
      `sungrow_capability_test.py`, `sungrow_wallbox_capability_test.py`) still pin
      `modbus-connection[tmodbus]==4.12.4`; to 4.12.7 with tmodbus 1.1.0, a
      new transport for contributors' runs, so after one diagnosis on hardware
      with it (`device-diagnosis/reference.md` first).
4. **The diagnosis and its capability tests.** In the code: two modes
   (*Run read-only diagnosis*, *Run diagnosis with capability tests*), a
   `features` section in every document (schema 25), the *Diagnosis* column
   and the measured findings in `doc/firmware_support.md`, and the forced
   startup mode (`diagnosis.sh tests <host> --forced-startup`). What each
   capability can be tested with is `doc/capability_tests.md`. Left:
   1. **A first forced startup run on hardware**: an inverter in low-SoC
      standby, at night with an empty battery. The SH-RT's factory 0 goes
      back as 0x55, the one `RESTORE_EQUIVALENT` (AGENTS.md).
   2. **New capability tests, for the maintainer to pick**
      (`doc/capability_tests.md`, *Could still test*): a no-op write of
      backup mode and load control; out-of-range refusal probes for the
      `number` bounds; window 2 read back with the schedule off; the
      wallbox's current scale in the feature report; the EMS mode codes.
   3. **Outside the repository**: issue #786's title still says survey, and
      the repository variable `SURVEY_ISSUE` keeps its name.
   4. **Capability test runs over a day.** Home Assistant keeps every run per
      firmware and folds them into one schema-3 block
      (`capability_test/ledger.py`; the *Capability test status* sensor, a
      notification rewritten per run, *Clear capability test history*), and
      *Continuous capability test mode* starts runs when a missing check is
      due (`continuous.py`).
      Left:
      1. **The CLI's `--merge-into` appends** through `ledger.fold`
         rather than replacing the block (`--replace` for the old way).
         Waits on a release: the PEP 723 header pins a wheel without
         `ledger`.
      2. **Continuous mode for an ordinary entry.** The switch exists on a
         diagnostics-only entry; an ordinary entry has no diagnosis
         entities, so it would need an action pair (start / stop), with
         its `services` strings and German.
      3. **One hardware day** at the maintainer's SH10RT with the switch
         on: the import limit established at night, the PV cut in sun,
         ingested as one document. Also tells whether `NEEDS`' margins
         start runs that the checks then skip.
      4. **Translate** the status line and the notification once their
         wording settles; English for now.

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
   battery under 90 % and not in Standby. Then ingest, and the reply to
   #546 (drafted in the session of 2026-11-07; its table is in the wiki's
   register 32998 page).

2. **Tonight, 2026-11-08: 13017 and Todo row a at the maintainer's SH10RT
   (P020, cable).** Run as `/sh10rt-tonight` (a personal command in
   `~/.claude/commands/`, which carries the address; the scripts are in
   `~/.claude/sungrow-scripts/`). The prompt, without the address:

   > Run tonight's two hardware tests at the maintainer's own SH10RT, then
   > ingest them. Read `AGENTS.md` and the wiki pages register-13017,
   > register-32998 and capability-test-restore first. The inverter: the
   > maintainer's own (address in their `secrets.yaml`), unit 1, stand-in
   > `anon-37323352958`, `SAPPHIRE-H_B001.V000.P020`; the VPN off, the
   > stand-in checked before any write; the house's Home Assistant stays
   > connected, so retry lost reads. Changed on purpose on 2026-11-08: the
   > minimum SoC 13059 = 250 (25 %, was 100), so the battery reaches its
   > minimum tonight. 13017 reads 0 and P020 refuses a write of 0.
   >
   > 1. **13017**, with PV < 30 W and the inverter in low-SoC Standby
   >    (0x0008; wait up to an hour, else skip): 0xAA watched 10 min
   >    (expect Starting, then Running, battery idle); 0x55 watched 3 min
   >    (expect Standby); 0x01 (expect refused), then 0x55. 13017 stays at
   >    0x55.
   > 2. **Charge** with an EMS forced charge of 4500 W in 15-minute chunks,
   >    each restored, until the SoC reads 30 % or more; wait ~2 min.
   > 3. **Row a**, with PV < 30 W and the battery discharging into the
   >    house: 33048 lowered to about half the load (e.g. 25 = 250 W),
   >    90 s; then 32998 = 5 (0.05 kW), 90 s; then 2000; restore 32998 and
   >    33048. Does the battery discharge past its limit to meet the cap
   >    (expected no)? If the lowered limit stops the discharge, retry once
   >    with a larger one.
   >
   > Afterwards: 13059 back to 100 (10 %) unless told to keep 25 %; ingest
   > (raw mkaiser-forced-startup-2026-11-08 and
   > mkaiser-import-limit-discharge-2026-11-08, their source pages,
   > register-13017, register-32998, P020, installation-mkaiser, index,
   > log; no address anywhere); if the start was watched, P020 into
   > `CONFIRMED_ON_FIRMWARE` for `FORCED_STARTUP_CONTROL` with
   > `tests/test_forced_startup.py`, `make gen`, `make check`; this item
   > and row a out of Todo.md; commit only your files; ask before pushing.

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
   Still open on the T besides: whether 13018 acts as 31211 does.

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

6. **Writing the discharge schedules, and the import limit** (#785), in
   no Sungrow document. The schedules read as diagnostic entities
   (`Capability.DISCHARGE_SCHEDULE`); writing them needs a watched write, as
   31211 did (wiki: firmware gating), from a capability test run with leave.

   **The import limit, register 32998, can become a control now.** Watched
   writes exist on P020 (three runs, the maintainer's SH10RT), P022 (gerd,
   cable and WiNet-S) and P023 (bar12, cable and WiNet-S, EMS and
   schedule); everywhere the cap held every charge commanded, on grid
   import alone, and 1-5000 (0.01-50.00 kW) is the accepted range (wiki:
   register 32998). The one contrary report (ulfben, #546) is unexplained;
   the reply is drafted. To decide before building:
   - a number in **kW** (0.01 step), which the number generator does not
     offer yet (`%` and `W` only), or in W with a 10 W step;
   - the read-only sensor *Grid import limit* beside it, or replaced by it
     (the number shows the same value);
   - a new `IMPORT_LIMIT` capability (does 32998 answer) and
     `IMPORT_LIMIT_CONTROL` in `CONFIRMED_ON_FIRMWARE` for P020, P022 and
     P023, as 31211's cut is gated;
   - the help text: it caps a charge from the grid, never the house load.

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
   the first. Watch whether it recurs.

10. **The SG's tracker counts beyond the SG5.0RS.** `MPPT_COUNTS` is the
    source's model table, many entries unverified; a diagnosis of any other SG
    checks its row (wanted in `device-diagnosis/devices-wanted.md`, row 10).

11. **A watched forced startup (13017).** The *Force startup* button exists
    only on firmware in `CONFIRMED_ON_FIRMWARE`, and nothing can put one
    there: the capability test has no check for it. One needs an inverter in
    low-SoC standby with no PV (an evening, the battery at its minimum SoC),
    writes 0xAA and watches the running state leave standby. Building that
    check is a capability-test change, so it waits for a house that can give
    such an evening.

12. **The PV cut (31211, #738), beyond the four confirmed firmwares.**
    Waits on contributors; nothing here or at the maintainer's P020 (31211
    reads 0xFFFF there) can answer it.
    - More firmware confirmed: 31211 answers 0x55 but no cut has been
      watched on `SUNSTONE-H_B000.V001.P068`, `B000.V002.P067`,
      `B000.V002.P059` and `B000.V002.P057`. The diagnosis's capability test
      watches the cut, so it is asked for in the "Most wanted" table of
      `device-diagnosis/devices-wanted.md`, never from one person.
    - One evening's watch on a confirmed device (P022, P023, P071 or P065):
      does a cut survive a night or a restart, or does iSolarCloud rewrite
      it?

13. **What register 13080 counts.** Documented as the external EMS
    heartbeat (0-1000 s, default 20 s), it reads 0 on 42 diagnoses, 330 on two
    houses in EMS mode 0, and 875 then 961 on ra1k_0's SH20T in EMS mode 3
    (`.wiki/wiki/queries/what-do-the-v1-1-17-only-registers-read.md`). Two
    reads of it a minute apart at that house would show whether it counts
    seconds. Nothing reads or writes it until then.

## Battery

14. **SBH.** Answers the SBR's common block at unit 2 with the SBR's scales;
     per-module arrays unread. Needs the register document.

## Wallbox

15. **A wallbox charging negative, or past 32.7 kW.** Settles whether
    21308/21310 are signed. Still unnamed: input 21313 (falls to 0 when
    charging ends, not power) and input 21365 (-71 to -63, flat). A wallbox
    restart would show whether 21267 falls to near zero.

16. **A second wallbox's diagnosis.** Settles whether 21211-21214 identify the
    unit. The wallbox reports its own serial (input 21201-21206, 11 ASCII
    characters, as Sungrow's portal shows it); the
    integration shows it on the device page, identifies the device by the
    inverter's serial plus `-wallbox`, and publishes it only as a stand-in.
    Three registers wait on a second unit:
    input 21201-21206 (the serial: use it as the device identity?), input
    21211-21214 (a short code, masked), and holding 21250-21259 (twenty
    constant ASCII digits, masked). Whichever differ between
    two wallboxes identify a unit and stay masked; whichever match are a model
    constant and can be unmasked. ra1k_0's AC22E-01 would be one.

## Logger

17. **A first Sungrow Logger diagnosis** (#786). Unblocks Logger entities.
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
       (RafAustralia, purcell-lab, NBS23) are the leads.

## iHomeManager

18. **A first iHomeManager diagnosis** (#786). Unblocks building its entities.
    The diagnosis reads one (unit 247, port 502, 503 or 504, one
    connection each); the integration does not, and its config flow fails such
    an endpoint with `no_serial_number`. Wait for a measured reading before
    building entities on `sungrow_modbus.ihomemanager`. Sungrow's protocol PDF:
    https://github.com/TCzerny/ha-modbus-manager/blob/main/docs/Communication%20Protocol%20of%20iHomeManager_V1.0.2.pdf

## Integration and tooling

19. **Does a WiNet-S advertise over mDNS?** Needs a house with a dongle and
    a run on the host, not in the container.

20. **The capability test's restore through a WiNet-S, on hardware.** A
    dongle-only capability test at gerd on the current tree, with the battery
    above 30 % and no car charging, then a cable read of every snapshot
    register. Left open in the code: a touched register goes back to the
    dongle's word, wrong only if changed over another path since the dongle
    last read it.

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

   Open, needing the maintainer to connect GitHub on :8126 (a device code,
   read-only): does *Add from link* install the channel from a fresh
   `make marketplace ARGS=--reset`, and at a commit hash? Only that is left
   of the three questions.

   Then correct `doc/installing_a_preview.md` and `doc/maintainer_setup.md`
   §5 (done for the takeover and the update; *Add from link* still states only
   what the Marketplace's page says). Keep the HACS path while `hacs.json`
   allows 2026.9 and 2026.10. Nothing here waits on next step 3.

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

5. **The YAML track's documentation, for the integration.** The four pages
   below open with a note that they are for the YAML package, pointing at
   `doc/installing_a_preview.md` and `doc/integration_migration.md`; the
   first-line documentation of the integration is `strings.json`. At the
   release, the note points at the ordinary install instead of the preview.

   | Page | To do |
   | --- | --- |
   | `legacy/doc/cleanup_entities.md` | Link it from a repair as the manual fallback, if one is built |
   | `legacy/doc/dashboard.md` | A generated dashboard (Future work) |
   | `legacy/doc/faq.md` | The iHomeManager answer, once its entities ship |

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
Node-RED. Today they get advice and a print-only script
(`scripts/helpers/influx_migration.py`, `doc/integration_migration.md`),
and the legacy-id adoption keeps ids so most users never need either.
Open: what the integration should do when an id does change (a repair that
names the affected entities and links the recipe; a list of old and new ids
a user can export), how a rename after release is announced, and whether a
real InfluxDB with the migrated data is worth testing once the production
copy (Release item 4, `doc/maintainer_setup.md` §8)
exists.

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
gh issue list -s all --search "updated:>=2026-11-07T10:40:00Z" -L 50
gh api 'repos/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/comments?since=2026-11-07T10:40:00Z&per_page=100' \
  -q '.[] | "\(.issue_url | split("/") | last) \(.user.login) \(.created_at)"'
```

Last checked: **2026-11-07 10:40 UTC** (#786, #791): code-imstillalive's
SH25T and SH15T through a Logger1000A, and peter_sm's ninth and tenth
readings (Korsberg's diagnostics downloads), ingested.

## Recurrent: llmwiki upstream check (every 6 weeks, next: 2026-12-10)

The wiki follows `@llmwiki/core` **0.1.2** (microsoft/llmwiki at `e09126f`).
Check upstream for changes to the index, log or frontmatter format
(`packages/core/src/init.ts`, `lint.ts`, `index-ops.ts`, `log.ts`) and to its
lint rules. If something changed, update `tests/test_wiki.py` and
`.wiki/AGENTS.md` together, and bump the version named in both and in
`.wiki/wiki/log.md`. Then move the date above six weeks on.
