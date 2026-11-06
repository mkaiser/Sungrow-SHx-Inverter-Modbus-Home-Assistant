Todo.md contains only what is still to do (forward looking).
Anything done is removed here; history goes into git and `.wiki/wiki/log.md`.

Structure:

1. **Next steps** -- work that can start now, in order of priority.
2. **Open decisions** -- questions for the maintainer; nothing is built on
   them until they are answered.
3. **Blockers** -- work that waits on something outside this repository
   (hardware, daylight, a contributor). A next step that turns out blocked
   moves here, with what unblocks it.
4. **Future work** -- wanted, not scheduled; includes recurrent checks.


# Next steps

1. **The preview channel under the Marketplace.** In Home Assistant 2026.11
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
   allows 2026.9 and 2026.10. Nothing here waits on blocker 19.
2. **Writing to the wallbox: measure the output current's scale at gerd's.**
   The wallbox is read only (`doc/wallbox_registers.md`; no file in
   `device-survey/` writes). Three sources disagree on the output current
   setting, holding 21203: 0.1 A per count here, 0.01 A in discussion #571. On
   a mains charger that is a factor ten, so no wallbox entity is built until
   a run like the inverter's has settled it. Plan:

   1. **The test, in the library. Done 2026-11-06:**
      `src/sungrow_modbus/wallbox/control_test.py` and
      `tests/test_wallbox_control_test.py` (22 tests). It writes only through a
      `WallboxPort` the driver supplies, so `SungrowWallbox` stays read only.
      The words it offers (60, 80, 100; 6, 8 and 10 A at 0.1 A per count) are
      safe at either scale, capped by `max_amps` (10 A); the snapshot is
      flushed before the first write, and without a callback nothing is
      written; no leave is a dry run; the readback is the raw word on a fresh
      session (a same-session holding read answered another register after a
      write); the restore writes the snapshot's raw word, checks it by a raw
      read and tries five times, and an unrestored register is code 5. A
      setting that reads above the rating at 0.1 A per count and inside it at
      0.01 is reported as the scale finding (code 4) before any write.
   2. **A dry run at gerd's first. Waits on his network being routed** (not
      the case on 2026-11-06; set aside for another session, the maintainer
      says when). Read only, no leave: identifies the
      wallbox, reads the rating, the setting and what the car draws, and says
      which scale they fit. If a car is charging, "the car draws 13 A while
      the setting is 160" already excludes 0.01 A per count (1.6 A could not
      charge it). This may settle the question before one write; it needs only
      the network and the wallbox's own address.
   3. **The driver.** `device-survey/scripts/python/sungrow_wallbox_control_test.py`
      (PEP 723, `--leave` defaulting to no, a snapshot file per day, TLS 516
      unit 248 as `wallbox_direct.py` connects, a fresh session for the raw
      readback, a document with the stand-in serial). It can use only what the
      pinned wheel has (`device-survey/reference.md`), so it waits on a release
      that contains step 1.
   4. **One window with gerd and a car.** A car plugged in and charging, his
      Home Assistant and evcc off, the TLS port kept on one session (it
      refuses reconnects within seconds). Start low, never above his
      installation's limit, no phase switch with the car charging, and the
      optional stop/start only if the register reads 0 while charging. His
      consent covers any test; ask again for writes with a car attached.
   5. **Only then, entities.** A charging current number and an enable switch,
      on what was measured, through the write table
      (`scripts/generate/tables/writes.py`), with the wallbox's 60 s fallback
      in mind.

   Not to copy: evcc's `sungrow.go` reserves all rights.

   2026-11-06 at gerd's (VPN routed): a **read-only** survey of the inverter
   over the cable (178.114) identified it by its stand-in, anon-00267885816,
   so the house is gerd's. His Home Assistant was polling throughout: many
   blocks answered on one pass of two or dropped the link, so the reading is
   contention, not evidence, and is not ingested (the document sits in
   `device-survey/`, gitignored). Nothing was written. The maintainer had
   meant the wallbox, not the inverter; inverter work there waits until his
   Home Assistant is stopped. The wallbox dry run (step 2) has not run yet.

   Done 2026-11-06, beyond step 1: the enable register (holding 21211:
   disabled on 0, the wallbox must say status 8, then enabled on 1) and the
   phase setting (holding 21204, only when nothing flows, the actual mode
   input 21270 must follow) are steps, each behind its own option and each
   skipped when its register could not be read or reads something that is not
   the state it takes it for. And the driver, step 3:
   `device-survey/scripts/python/sungrow_wallbox_control_test.py`
   (`--leave`, `--enable`, `--phase`, `--start-stop`, `--max-amps`,
   `--restore`; TLS 516 unit 248 only; a snapshot flushed before the first
   write; the raw readback on a fresh session after ten quiet seconds; no
   address or serial in its report) with `tests/test_wallbox_control_test_cli.py`.
   It is in `sync_version.py`'s script list, so its pin moves with the version,
   but the pinned 0.1.0a27 wheel has no `wallbox.control_test`: it prints that
   and exits 2 until the next release, which contains it.
3. **Spoil the December release at the top of `main`'s README.** The
   maintainer targets a release in December 2026 (said 2026-11-06). `main`'s
   README opens with dated news headings that the YAML package's users read;
   a teaser there tells them what is coming before it does. It is a commit on
   `main`, which AGENTS.md keeps production: the YAML package is not touched,
   only its README, and only when the maintainer says. Draft, to approve:

   > # 2026-11-06 "A real Home Assistant integration is coming"
   >
   > A Home Assistant integration to replace this YAML package is being built
   > on the `proper-ha-integration` branch, and is targeted for **December
   > 2026**. It keeps your entity ids, so your recorder history, statistics
   > and dashboards carry on across the switch. **Nothing changes for you now:**
   > this package keeps working and is maintained until the integration has
   > everything it has. A guide for the move comes with the release.
   > If you are new, you can still install it like described in the README and
   > quickly migrate later. 
   > Own a Sungrow device and want to help? Run the survey
   > ([#786](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/786)).

   Wording to decide: "targeted" and not "will", the month or a date, and
   whether the preview's own README (this branch) says it too. What December
   needs, from the rest of this file: the ordinary setup switched on
   (open decision 1, `ONLY_SURVEY_MODE`), a stable `0.1.0` rather than an
   alpha, the production-database run (blocker 12) or a decision to go
   without it, the logo (Future work), the catalog submission (next step 4;
   its review takes months, so submit on release, not before), and the
   migration guide made current.
4. **Submitting to the catalog, when the merge is decided.** Read
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
   | HACS action and hassfest pass with no ignores | CI runs both; confirm none is ignored |
   | **At least one full GitHub release** (a tag is not enough) | **no: every release is a pre-release** |
   | `categories` in `manifest.json` | yes, three (see below) |

   Open: whether a repository whose only releases are pre-releases passes
   (not stated); so the first stable release (0.1.0, not an alpha) is the
   real gate. Drop "(preview)" from the name on `main` only. The
   Marketplace refreshes the catalog every 6 hours and a repository added from
   a link every 48 hours.

   **`categories`, investigated 2026-11-06** (core 2026.11's 1562 manifests,
   its loader and the Marketplace's code; the list is
   contributors.home-assistant.io/core/integrations/categories/):

   - *What reads them.* Core ships a custom integration's manifest
     `categories` to the frontend (`loader.py`, the integration descriptions
     behind Add integration, "the primary category first"), so they matter to
     users on 2026.11 today, not only for the catalog. hassfest warns when
     there are none (the release run's annotation); the HACS action's
     `integration_categories` check warns for none and fails an unknown
     value, one to three, no duplicates. The Marketplace's own browsing takes
     categories from the *catalog* entry, so a custom repository such as the
     preview shows none there; a wrong value loses only the categories.
   - *What comparable integrations declare.* `sofar` (our reference
     implementation), `goodwe`, `solax`, `sma`, `kostal_plenticore`,
     `enphase_envoy`, `solarlog`: exactly `["energy.solar_batteries"]`.
     `fronius` (inverter and meters): `["energy.solar_batteries",
     "energy.meters_monitoring"]`. EV chargers (`tesla_wall_connector`,
     `openevse`, `wallbox`): `["energy.ev_charging"]`. Core's own `modbus` is
     `["diy_makers"]` because it is the generic connector; a vendor integration
     is a product, so not that. No core integration lists a parent beside its
     own child (0 of 1274), so do not.
   - *Decision (2026-11-06): option C.* `categories` is
     `["energy.solar_batteries", "energy.ev_charging",
     "energy.meters_monitoring"]` and `connectivity` is `["modbus"]` (as
     `sofar`), both in `manifest.json`. The alternatives were A, the narrowest
     (`["energy.solar_batteries"]`, as `sofar`, `goodwe`, `solax`, `sma`), and B,
     without the meters. C adds the wallbox (a device of its own here, 19
     sensors and 2 binary sensors, but read only, which the description
     should say) and, as `fronius` does, the meter read through the inverter.
     `diy_makers` stays for core's generic `modbus`.
   - *Verified:* `make hassfest` (`scripts/dev/hassfest.sh`: current core's
     hassfest in the 2026.11 venv) reports 0 invalid and no warning; the same
     run on a manifest with `energy.nonsense` and `carrier_pigeon` warns for
     both, so the four values are known to core. Pushed 2026-11-06 (CI green:
     tests, hassfest, HACS), synced to the preview (`5bc5666`), installed on
     the 2026.11 testbed through the Marketplace: Add integration's
     descriptions carry the three categories and `connectivity: ["modbus"]`.
     Not seen: the dialog itself in a browser.
   refreshes the catalog every 6 hours and a repository added from a link
   every 48 hours.

# Open decisions

1. **When to offer the ordinary setup**, targeted for December 2026 (the
   maintainer, 2026-11-06) (`ONLY_SURVEY_MODE` in `const.py`;
   turning it off is the whole re-enablement, `tests/test_alpha_gate.py`),
   and **when to merge into `main`.** The merge retires the preview channel
   and opens the HACS default store, which also needs the brand in
   `home-assistant/brands` (`scripts/helpers/make_brand_icon.py` draws it).
2. **Are the entity names final?** They are reviewed and decided, English
   and German (`doc/entity_names.md`, `doc/text_translation_review.md`,
   `scripts/generate/tables/naming.py`); both ship, German as
   `translations/de.json`, and entity ids stay English in every language
   (`doc/architecture.md`). A rename later leaves existing ids alone and
   only diverges new installs, which a registry migration can close, so it
   stays cheap until release, not free. A new name goes under **To
   discuss** (`NAME_DISCUSSION` in `naming.py`).

# Blockers

1. **A wallbox charging negative, or past 32.7 kW.** Settles whether
   21308/21310 are signed. Still unnamed: input 21313 (falls to 0 when
   charging ends, not power) and input 21365 (-71 to -63, flat). A wallbox
   restart would show whether 21267 falls to near zero.
2. **An SH-T through its WiNet-S, in daylight, with export** (any SH15T
   owner; ra1k_0 says the SH20T has no LAN port of its own, #772, and
   Sungrow's SH5T-SH25T manual lists a WiNet-S2 Ethernet connection and a
   COM2 terminal, no LAN terminal: the manual's contents page, read through a
   search; its text was not fetched). So the T has **no cable path** to ask
   for, and what a dongle run can settle is its behavioural leg only. One run
   with the control test (`--enable-export-limit`) settles:
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
3. **A second wallbox's survey.** Settles whether 21211-21214 identify the
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
4. **firetribe, once more (#784).** A cable control test while the
   inverter is running (it was `Starting`) gives the first SH6.0RT-V112
   readbacks and its 13074 write scale. Their WiNet-S 0x04s are contention,
   reproduced at gerd's.

5. **A first iHomeManager survey** (#786). Unblocks building its entities
   (milestone 5). The survey reads one (unit 247, port 502, 503 or 504, one
   connection each); the integration does not, and its config flow fails such
   an endpoint with `no_serial_number`. Wait for a measured reading before
   building entities on `sungrow_modbus.ihomemanager`. Sungrow's protocol PDF:
   https://github.com/TCzerny/ha-modbus-manager/blob/main/docs/Communication%20Protocol%20of%20iHomeManager_V1.0.2.pdf

6. **A first Sungrow Logger survey** (#786). Unblocks Logger entities
   (milestone 8). The map is done from Sungrow's protocol 1.0.2.9
   (`sungrow_modbus.logger`, every field `spec`; where every document is:
   `.wiki/wiki/queries/where-are-sungrows-documents.md`); what a first
   survey settles is on `.wiki/wiki/queries/what-does-a-logger-answer.md`.
   It reached surveys with 0.1.0a26, which the survey pins. Missing:

   1. **Its TLS port, untried.** The survey asks unit 247 over TLS on 516
      (a current Logger1000 opens only that port); no Logger has answered
      there yet, so that path is held to fakes only (`tests/test_logger.py`).
   2. **What sits behind it.** Each inverter and meter answers at its
      forwarding address (the Logger's Device List page), not at a unit the
      survey guesses; `identify` looks at units 1-5 only. A DTSU666 is a
      device nothing maps.
   3. **A contributor with one.** Nobody has offered; the #262 participants
      (RafAustralia, purcell-lab, NBS23) are the leads.

7. **A fault seen on hardware.** The fifteen words are decoded from V1.1.11's
   Appendix 4; one survey has a flag set (bit 30 of the inverter alarm, a
   slave with no meter), which confirms the word order. Wanted: a reading
   during a real grid or battery fault, and the battery words through a
   dongle. V1.1.17's Appendix 4 is word for word V1.1.11's.
8. **SBH.** Answers the SBR's common block at unit 2 with the SBR's scales;
    per-module arrays unread. Needs the register document.
9. **Meter phase voltage/current (5741-5746) on dongle houses.** Read zero
    through every WiNet-S measured and are gated on a non-zero voltage.
    Whether they need reading on their own (#756) needs a survey from an
    affected owner; `layout.py` changes only on measurement.
10. **T-series energy counters.** One SH20T reads 13045 (daily export) as 0
    while exporting, and 5003/5004-5005 duplicating the export counters. A
    second T survey, ideally on a cable, before `registers.py` changes.
11. **Does a WiNet-S advertise over mDNS?** Needs a house with a dongle and
    a run on the host, not in the container.
12. **The production database.** The migration is verified at real scale
    only against the maintainer's years-old YAML install; what to collect and
    how is in `doc/maintainer_setup.md`, section 8. Offered 2026-11-06: a
    copy of the instance's files (preferred: the migration can be run and
    rolled back) or read-only API access (the entity map and statistics only),
    into the gitignored `.testdata/`, with the copy pointed at the simulator,
    never at the real inverter. Waits on the maintainer choosing and placing
    the copy; counts and mismatches are reported, no serial or address.

13. **Writing the discharge schedules, and the import limit** (#785), in
    no Sungrow document. The schedules read as diagnostic entities
    (`Capability.DISCHARGE_SCHEDULE`); writing them needs a watched write, as
    31211 did (wiki: firmware gating), from a control test run with leave. The
    site import power limit Korsberg uses at register 32998 reads 950 and
    990 at peter-sm, 2000 at two P020 houses and 4347 on an SH20T, with no
    unit or scale on record: it needs a known value (what an owner set it
    to) before it can be an entity.

14. **The discharge window on P023** (#785). It has run on P022 and P020,
    and the device pages and log say so; no P023 or SBR house has run it
    (fwitten's master, with their Home Assistant stopped, in the evening).

15. **The SG's zeros and writes.** On bleughb's two SG5.0RS through a
    WiNet-S, the meter block (5083-5104) and the per-string block (input
    7013) read 0, and holding 5020 reads nothing. Whether that is absence or
    the dongle needs an SG on a cable, or one with its own meter. Writing the
    power limitation (holding 5007-5008, which bleughb writes on both) waits
    for a watched write.

16. **The control test's restore through a WiNet-S, on hardware.** A
    dongle-only control test at gerd on the current tree, with the battery
    above 30 % and no car charging, then a cable read of every snapshot
    register. Left open in the code: a touched register goes back to the
    dongle's word, wrong only if changed over another path since the dongle
    last read it.

17. **gerd's cable restart.** On 2026-11-03 the start had to be sent three
    times (still stopped 60 s after each), where every earlier restart took
    the first. Watch whether it recurs.

18. **The SG's tracker counts beyond the SG5.0RS.** `MPPT_COUNTS` is the
    source's model table, many entries unverified; a survey of any other SG
    checks its row (wanted in `device-survey/devices-wanted.md`, row 11).
19. **Home Assistant 2026.11 and modbus-connection 4.12.7.** 2026.11.0
    (2026-11-04) pins `modbus-connection[tmodbus]==4.12.7` and
    `tmodbus==1.1.0`; the dev environment runs 2026.10.4 on 4.12.4 and
    tmodbus 0.6.2, because `pytest-homeassistant-custom-component` 0.13.375
    still pins `homeassistant==2026.10.4`, and forcing it does not work:
    2026.11 aliases `httpx` to `httpx2` on import and raises if `httpx` is
    already loaded, which the 2026.10 plugin's dependencies do first, so
    pytest stops before collecting. Once a plugin release supports 2026.11, move
    together: `requirements_dev.txt` (`homeassistant>=2026.11` and the two
    pins), the survey and control test headers (`==4.12.7`),
    `pyproject.toml`'s floor (`>=4.12.7`), `hacs.json`'s minimum
    (`2026.11.0`), the README's "Home Assistant 2026.9" and the bug
    template's version placeholder; then `make check`. With the floor at
    2026.11, `DeviceInfo` is a dataclass, and item access on it is deprecated:
    `async_remove_config_entry_device` reads `info["identifiers"]`
    (`__init__.py`), which becomes `info.identifiers`. Also on 2026.11:
    sensor, binary sensor and survey entities override
    `async_added_to_hass`. Until they implement `async_entity_id_changed`,
    an `entity_id` rename still removes and re-adds them, instead of
    updating in place. That fallback ends in 2027.11. Check the renames in
    `migration.py` against the hook before adding it.
20. **A watched forced startup (13017).** The *Force startup* button exists
    only on firmware in `CONFIRMED_ON_FIRMWARE`, and nothing can put one
    there: the control test has no check for it. One needs an inverter in
    low-SoC standby with no PV (an evening, the battery at its minimum SoC),
    writes 0xAA and watches the running state leave standby. Building that
    check is a control-test change, so it waits for a house that can give
    such an evening.

21. **The PV cut (31211, #738), beyond the four confirmed firmwares.**
    Waits on contributors; nothing here or at the maintainer's P020 (31211
    reads 0xFFFF there) can answer it.
    - More firmware confirmed: 31211 answers 0x55 but no cut has been
      watched on `SUNSTONE-H_B000.V001.P068`, `B000.V002.P067`,
      `B000.V002.P059` and `B000.V002.P057`. The survey's control test
      watches the cut, so it is asked for in the "Most wanted" table of
      `device-survey/devices-wanted.md`, never from one person.
    - One evening's watch on a confirmed device (P022, P023, P071 or P065):
      does a cut survive a night or a restart, or does iSolarCloud rewrite
      it?

22. **What register 13080 counts.** Documented as the external EMS
    heartbeat (0-1000 s, default 20 s), it reads 0 on 42 surveys, 330 on two
    houses in EMS mode 0, and 875 then 961 on ra1k_0's SH20T in EMS mode 3
    (`.wiki/wiki/queries/what-do-the-v1-1-17-only-registers-read.md`). Two
    reads of it a minute apart at that house would show whether it counts
    seconds. Nothing reads or writes it until then.

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

## A new logo and brand image

The mark today is a rayed sun above a battery, drawn from code
(`scripts/helpers/make_brand_icon.py`, written to
`custom_components/sungrow_modbus/brand/`: `icon.png` and `dark_icon.png`,
each also `@2x`). Wanted: an image that shows the whole system: PV modules,
inverters and a car charging. Open:

- **The design.** One picture at three sizes: the icon is shown at about 32
  pixels in Home Assistant's own UI, where more than two or three shapes turn
  to mush, so the icon may need to be a reduced cut of the picture (modules
  and a plug, say) while a wider image (a README and Marketplace header, the
  documentation) can carry all of it: modules, inverter and car.
- **Three drafts exist (2026-11-06)**, in the two-colour palette, at icon size on
  light and dark, in `tmp/logo-drafts/` (gitignored; `contact-sheet.png` shows
  them at 200, 64, 48 and 32 pixels, `draft_logos.py` draws them):
  *1-chain* a module, an inverter and a car stacked, joined by the flow, the
  car carrying the bolt; *2-array* a module array over the inverter with the
  car in front (the house shape is weak: it reads as an array and a box);
  *3-loop* three nodes in a ring, modules, inverter, car, with arrows around,
  which is the one that survives 32 pixels best. Pick one, or ask for another
  round; the chosen one moves into `make_brand_icon.py`, which writes `brand/`.
- **Original, never Sungrow's.** No Sungrow logo, wordmark or colours: this is
  a community integration and borrowing the trademark implies an endorsement
  (`make_brand_icon.py` says so).
- **How it is made.** Keep it reproducible: a script that draws it
  (Pillow today), or a hand-made vector in the repository with the PNGs
  exported from it by a script; either way the maintainer approves a sketch
  before it replaces the current mark.
- **Where it goes.** The integration's `brand/` folder (square, transparent,
  trimmed, 256 and 512 pixels, a dark variant), the README, the Marketplace
  and the documentation; `home-assistant/brands` is the fallback the catalog
  reads when `brand/` is missing, so it is not needed while `brand/` exists.
  Do it before the merge decision (open decision 1), when the brand becomes
  visible to everyone.

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
the README. Still proposed, in order of cost: link it from the setup's last
step; a repair or notification after setup that names the same entities; an
action that adds them to the dashboard, only on request. The guide states the
two unverified points; each is answered by one house. Feeds `legacy/doc/dashboard.md`'s
Energy dashboard row below.

## Site-wide sensors for several inverters

Each inverter is its own config entry (and the SG, the hybrid and a
master/slave cluster each have their own readings), so nothing adds them up:
the YAML package gave the second inverter `inv <n>` ids and no total. Open:
how to offer site-wide sensors, and where they live.

Where: a Home Assistant helper the user creates (Sum, or a template sensor;
documented, nothing to build); or an entity of the integration's own on a
"Site" device, which needs something above the one-entry-per-inverter rule
(`doc/architecture.md`), such as the first entry owning it or a separate
site entry. `total_site_pv_power` already exists for the inverter that has a
second one on its supply, so the Site wording has a precedent.

What adds up, and what does not. Measured on fwitten's master and slave
(committed surveys, 2026-10-29, P023 cables): the slave has no meter and no
battery. Its total imported and exported energy read 0.0, its meter values are
absent, its battery power is 0 and its battery level is the 6553.5 sentinel,
while both report PV (31.9 and 27.5 MWh total, 1.9 and 1.8 kWh that day) and
AC output (1196 and 1226 W).

- **Sums:** PV power and its MPPT parts, daily and total PV generation, AC
  output power, direct consumption totals, and battery charge and discharge
  (the slave contributes 0).
- **Master only, not a sum:** the meter's values, load power, import and
  export. Summing them would also work here, because the slave reads 0, but
  only because of this wiring; a house with two meters would be different, and
  none is measured.
- **Never summed or averaged:** battery level (the sentinel), settings, and
  any reading that is a state.
- **Energy counters:** a `total_increasing` sum drops when one member is
  unavailable and then jumps back, which the statistics read as a negative
  and then a very large generation. The Energy dashboard takes several solar
  sources, so adding each inverter there needs no sum at all (see the Energy
  dashboard item above); the sum is for cards and the power flow.

Proposal, so the choice is one decision: start with **documented helpers**
(a Sum helper over the inverters' PV power and generation sensors; the guide
in the Energy dashboard item names them), since they cost nothing and need no
change to the one-entry-per-inverter rule; build **entities of our own** only
if users ask. If built, the entry that is the cluster's master owns a "Site"
device, found by the roles the survey already measures (*measured* or
*inferred*, `doc/architecture.md`), and the sensors are unavailable, not 0,
when a member is.

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
copy (blocker 12, `doc/maintainer_setup.md` §8)
exists.

## The YAML track's documentation, for the integration

Every page says which track it applies to; the first-line documentation of
the integration is `strings.json`.

| Page | To do |
| --- | --- |
| `legacy/doc/installation.md` | Add the integration: HACS, add integration, what discovery finds |
| `legacy/doc/cleanup_entities.md` | Keep, linked from the repair as the manual fallback |
| `legacy/doc/dashboard.md` | Generated dashboard and Energy dashboard |
| `legacy/doc/faq.md` | The iHomeManager answer, once its entities ship |

## Deprecating and retiring the YAML package

Once the integration is complete (parity with the YAML package, merged into
`main`, in the HACS default store), deprecate `legacy/modbus_sungrow.yaml`
and the generated multi-inverter files, then retire them: announce it, point
every `legacy/doc/` page at the integration and `doc/integration_migration.md`,
and set a date after which the YAML package gets no further changes.

What retiring does not end: anyone may still migrate later, so the legacy-id
adoption and its guards stay as long as migration is offered.
`tests/test_sensor_descriptions.py` (ids, unit class, `state_class` against
`doc/legacy_entity_map.json`) keeps history continuous and stays.
`tests/test_registers.py`'s comparison with the YAML can then be anchored to
the specification instead; its scan-interval check goes first.

## Modbus over TLS on a WiNet-S's 516

Built for a wallbox's own
address (`wallbox_host`, `links.wallbox_tls_params`). For the dongle it is
worth building only if 516 is a *separate* session pool from 502: hold
502 until it refuses, then try 516. Also wanted: a certificate hash from a
third site, to show whether every dongle ships the same key. The
maintainer can take it from bar12's or gerd's WiNet-S (the five-second
script in `device-survey/devices-wanted.md`) when their network is
routed; the two share a subnet, so confirm the house by its stand-in
first. Port 516 timed out from the rebuilt container on 2026-11-06.
Measured 2026-11-06 over the VPN at gerd's (the one hash so far): his WiNet-S
and his wallbox serve the byte-identical certificate, SHA-256
`84505e46778f2611df26ed1ad8a4e872945f7eb33e050e617c96a73add005b5b`, serial
0x1, RSA-2048, `CN=sun`, issuer `OT.SUNGROW`, valid 2024-10-24 to 2054-10-17,
TLS 1.2 `ECDHE-RSA-AES256-GCM-SHA384`. Two different Sungrow products on one
key makes a per-device key unlikely; what is still missing is the same hash
from a house that is not gerd's.

## EVCC connection

- Hand inverter and wallbox readings to evcc, e.g. over MQTT, so evcc
  need not open a Modbus session of its own. To find out: does evcc have
  a standard configuration for that?

## Recurrent: new surveys to ingest (daily, after noon)

Every day after noon, read the general survey thread
([#786](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/786))
and any issue a survey was posted to since the last check. Comments older than
the last check are done; read only what is newer. Ingest each new
survey as `.wiki/AGENTS.md` describes (raw file, source page, entity pages,
index, log), and name the contributor (without `@`) and the issue number in
the commit; a survey signed `anonymous` stays unnamed. Then move the date
below on.

```bash
gh issue list -s all --search "updated:>=2026-11-06T19:57:00Z" -L 50
gh api 'repos/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/comments?since=2026-11-06T19:57:00Z&per_page=100' \
  -q '.[] | "\(.issue_url | split("/") | last) \(.user.login) \(.created_at)"'
```

Last checked: **2026-11-06 19:57 UTC** (#786): nothing new since peter_sm's eighth reading.

## Recurrent: a test plugin for Home Assistant 2026.11 (daily, until it ships)

Blocker 20 waits on `pytest-homeassistant-custom-component` pinning
`homeassistant==2026.11.x`. Every day, ask PyPI; while it prints
`2026.10.4`, nothing changes. Once it prints a 2026.11 pin, do blocker 19
and drop this check.

```bash
curl -s https://pypi.org/pypi/pytest-homeassistant-custom-component/json \
  | python3 -c "import json,sys; i=json.load(sys.stdin)['info']; \
print(i['version'], [r for r in i['requires_dist'] if r.startswith('homeassistant')])"
```

Last checked: **2026-11-06 19:57 UTC**: 0.13.375, still `homeassistant==2026.10.4`.

## Recurrent: llmwiki upstream check (every 6 weeks, next: 2026-12-10)

The wiki follows `@llmwiki/core` **0.1.2** (microsoft/llmwiki at `e09126f`).
Check upstream for changes to the index, log or frontmatter format
(`packages/core/src/init.ts`, `lint.ts`, `index-ops.ts`, `log.ts`) and to its
lint rules. If something changed, update `tests/test_wiki.py` and
`.wiki/AGENTS.md` together, and bump the version named in both and in
`.wiki/wiki/log.md`. Then move the date above six weeks on.
