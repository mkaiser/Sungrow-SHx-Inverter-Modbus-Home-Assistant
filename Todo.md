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

1. **Let the survey read a Logger over TLS on 516.** A current Logger1000
   opens only that port, with TLS, from firmware P044 (Sungrow's manual
   Ver129, `.wiki/wiki/entities/device-logger.md`); the survey reads TLS
   only from a wallbox (`device-survey/scripts/python/sungrow_survey.py`).
   Reuse the wallbox's TLS path for unit 247, so a first Logger survey
   (blocker 6) does not depend on its owner turning 502 on.

# Open decisions

1. **When to offer the ordinary setup** (`ONLY_SURVEY_MODE` in `const.py`;
   turning it off is the whole re-enablement, `tests/test_alpha_gate.py`),
   and **when to merge into `main`.** The merge retires the preview channel
   and opens the HACS default store, which also needs the brand in
   `home-assistant/brands` (`scripts/helpers/make_brand_icon.py` draws it).
2. **Are the entity names final?** They are reviewed
   (`doc/entity_names.md`, `scripts/helpers/review_names.py`). A rename
   later leaves existing ids alone and only diverges new installs, which a
   registry migration can close, so it stays cheap until release, not free.
   The sheet covers every device an entry can create (306 entities) and is
   the YAML | HACS table: each entity's legacy name and entity id beside its
   own, and the three YAML entities not ported. Compared against Sungrow's
   protocol (V1.1.2): 16 names changed to match it or each other (load
   control, battery energy totals, charging limits, device temperature).
   The sheet carries a suggested German name for each entity (`GERMAN` in
   `scripts/generate/tables/naming.py`) and German for every other text in
   `strings.json` (`german_texts.json` beside it, shown in
   `doc/text_translation_review.md`); none of it is shipped. Decided: entity
   ids stay English in every language (`doc/architecture.md`).

   Left, in order:

   1. **Decide the names, English and German together**, in
      `doc/entity_names.md` (datasheet, YAML, English and German side by
      side): the SG, SBR and wallbox sections are next. The inverter's open
      points are decided (*code* for every raw number, *Leistungsaufnahme* /
      *Energieaufnahme Verbraucher*, *Total PV input power*, *Device alarm*,
      *Feed-in limit* / *Einspeiselimit*, 31213 as *Shutdown inverter when
      limited to 0 % power*); a new question goes under **To discuss**
      (`NAME_DISCUSSION` in `naming.py`).
   2. **13017 becomes a button** *Force startup* / *Zwangsstart*: it is a
      command (reads 0 or 0x55, never 0xAA), not a state. It writes, so it
      is gated like *Cut PV generation* (`CONFIRMED_ON_FIRMWARE` only from a
      watched write), and the raw sensor goes.
   3. **Decode 31213 to a binary sensor**: the surveys read both 0x55 and
      0xAA on it (issue #554's pair), so it is a flag like 13089.
   4. **Compare the registers V1.1.2 does not list** against V1.1.16. V1.1.11
      (and V1.1.5, V1.1.9 and the SG's V1.1.58) are read: 35 of the 50 names
      match, and the open naming points they raised are on the sheet
      (*Feed-in* against *Export* for the limit family; 13075 is Sungrow's
      *Off-grid option*). 15 are in neither V1.1.2 nor V1.1.11: the four
      firmware parts (2582 ...), the serial (4990), meter phase voltage and
      current (5741-5746), 31211, 31213 and 33149/33150. V1.1.16 is not in
      the container.
   5. **If German ships:** pin the English ids with `object_id_base` first
      (`doc/architecture.md`), then have `scripts/generate/descriptions.py`
      write `translations/de.json` from the two tables.

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
   It reaches surveys with the next release, since the survey runs the
   pinned wheel. Missing:

   1. **The survey cannot read a current Logger1000** until next step 1, or
      until its owner turns port 502 on.
   2. **What sits behind it.** Each inverter and meter answers at its
      forwarding address (the Logger's Device List page), not at a unit the
      survey guesses; `identify` looks at units 1-5 only. A DTSU666 is a
      device nothing maps.
   3. **A contributor with one.** Nobody has offered; the #262 participants
      (RafAustralia, purcell-lab, NBS23) are the leads.

7. **Firmware-dependent register semantics** ([#763](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/763)).
   The pattern is `capabilities.ABSENT_ON_FIRMWARE`: a small table of
   deviations keyed on the **whole** `sungrow_version_1` string (platform
   prefix included: `PEARL-H_01011.01.45` is not older than
   `SAPPHIRE-H_01011.95.03`), each citing the survey it came from. #763's
   deviation, 13074's write scale, is measured per device and needs no
   entry; no committed survey shows another.
8. **A fault seen on hardware.** The fifteen words are decoded from V1.1.11's
   Appendix 4; one survey has a flag set (bit 30 of the inverter alarm, a
   slave with no meter), which confirms the word order. Wanted: a reading
   during a real grid or battery fault, the battery words through a dongle,
   and V1.1.16's appendix compared bit for bit.
9. **SBH.** Answers the SBR's common block at unit 2 with the SBR's scales;
    per-module arrays unread. Needs the register document.
10. **Meter phase voltage/current (5741-5746) on dongle houses.** Read zero
    through every WiNet-S measured and are gated on a non-zero voltage.
    Whether they need reading on their own (#756) needs a survey from an
    affected owner; `layout.py` changes only on measurement.
11. **T-series energy counters.** One SH20T reads 13045 (daily export) as 0
    while exporting, and 5003/5004-5005 duplicating the export counters. A
    second T survey, ideally on a cable, before `registers.py` changes.
12. **Modbus over TLS on a WiNet-S's 516.** Built for a wallbox's own
    address (`wallbox_host`, `links.wallbox_tls_params`). For the dongle it is
    worth building only if 516 is a *separate* session pool from 502: hold
    502 until it refuses, then try 516. Also wanted: a certificate hash from a
    third site, to show whether every dongle ships the same key.
13. **Does a WiNet-S advertise over mDNS?** Needs a house with a dongle and
    a run on the host, not in the container.
14. **The production database.** The migration is verified at real scale
    only against the maintainer's years-old YAML install; what to collect and
    how is in `doc/maintainer_setup.md`, section 8.

15. **Writing the discharge schedules, and the import limit** (#785), in
    no Sungrow document. The schedules read as diagnostic entities
    (`Capability.DISCHARGE_SCHEDULE`); writing them needs a watched write, as
    31211 did (wiki: firmware gating), from a control test run with leave. The
    site import power limit Korsberg uses at register 32998 reads 950 and
    990 at peter-sm, 2000 at two P020 houses and 4347 on an SH20T, with no
    unit or scale on record: it needs a known value (what an owner set it
    to) before it can be an entity.

16. **The options screenshot, and the discharge window on P023** (#785). The
    discharge window has run on P022 and P020, and the device pages and log say
    so. Left: `device-survey/images/HA-settings-configure-control-test.png`
    still shows three switches, now five; and no P023 or SBR house has run it
    (fwitten's master, with their Home Assistant stopped, in the evening).

17. **The SG's zeros and writes.** On bleughb's two SG5.0RS through a
    WiNet-S, the meter block (5083-5104) and the per-string block (input
    7013) read 0, and holding 5020 reads nothing. Whether that is absence or
    the dongle needs an SG on a cable, or one with its own meter. Writing the
    power limitation (holding 5007-5008, which bleughb writes on both) waits
    for a watched write.

18. **The control test's restore through a WiNet-S, on hardware.** A
    dongle-only control test at gerd on the current tree, with the battery
    above 30 % and no car charging, then a cable read of every snapshot
    register. Left open in the code: a touched register goes back to the
    dongle's word, wrong only if changed over another path since the dongle
    last read it.

19. **gerd's cable restart.** On 2026-11-03 the start had to be sent three
    times (still stopped 60 s after each), where every earlier restart took
    the first. Watch whether it recurs.

20. **The SG's tracker counts beyond the SG5.0RS.** `MPPT_COUNTS` is the
    source's model table, many entries unverified; a survey of any other SG
    checks its row (wanted in `device-survey/devices-wanted.md`, row 11).
21. **Home Assistant 2026.11 and modbus-connection 4.12.7.** 2026.11.0
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
    template's version placeholder; then `make check`.

# Future work

## Create a table with supported registers

Assumption (to be proven!): Inverter families of the SAME firmware version support the same capabilities / register sets.
Create a table: columns are inverter family + firmware version, rows are the supported registers/features.
Maybe indicate if you were not able to test / confirm a register / feature.

## SBR per-module entities

Each fitted module's highest and lowest cell are diagnostic entities,
disabled by default (#788), polled only while one is enabled. Left: tell
robbensonmio on #788 once it is released, and close the issue if they agree.

## The PV cut (31211, #738)

- More firmware confirmed: 31211 answers 0x55 but no cut has been watched on
  `SUNSTONE-H_B000.V001.P068`, `B000.V002.P067`, `B000.V002.P059` and `B000.V002.P057`. The
  survey's control test watches the cut, so a measurement the survey takes is
  asked for in the "Most wanted" table of `device-survey/devices-wanted.md`
  (the survey issue is written from it), never from one person.
- One evening's watch on a confirmed device: does a cut survive a night or
  a restart, or does iSolarCloud rewrite it?

## An energy counter per MPPT

Wanted: daily and total energy per tracker, so the energy dashboard can
compare strings. No register counts it: neither the hybrid's V1.1.11 nor
the SG's V1.1.58 lists energy per MPPT, only voltage and current. So it is
integrated from power: the hybrid's derived *MPPT1-4 power* already exist,
the SG would need *MPPTn power* (voltage × current) first. Open: a
`total_increasing` sensor that integrates in the integration and restores
its value across restarts, or a documented Riemann-sum helper per tracker;
and how far the polling interval and a WiNet-S's stale reads skew the sum
(the integrated total against *Total PV generation* says).

## A generated dashboard

Nothing generates one yet. Open: generate a Lovelace dashboard (asking
first), or rely on entity metadata and document the auto-generated view.

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
gh issue list -s all --search "updated:>=2026-11-05T11:30:00Z" -L 50
gh api 'repos/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/comments?since=2026-11-05T11:30:00Z&per_page=100' \
  -q '.[] | "\(.issue_url | split("/") | last) \(.user.login) \(.created_at)"'
```

Last checked: **2026-11-05 11:30 UTC** (#786).

## Recurrent: llmwiki upstream check (every 6 weeks, next: 2026-12-10)

The wiki follows `@llmwiki/core` **0.1.2** (microsoft/llmwiki at `e09126f`).
Check upstream for changes to the index, log or frontmatter format
(`packages/core/src/init.ts`, `lint.ts`, `index-ops.ts`, `log.ts`) and to its
lint rules. If something changed, update `tests/test_wiki.py` and
`.wiki/AGENTS.md` together, and bump the version named in both and in
`.wiki/wiki/log.md`. Then move the date above six weeks on.
