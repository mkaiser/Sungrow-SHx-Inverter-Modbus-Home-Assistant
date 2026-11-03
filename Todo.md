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

1. **Review the SG work (#790), squash, then push (ask first).** Committed
   on this branch: read-only SG string inverter support (map, terminal
   survey, HA entry, sensors), the shared device seam (`device.py`,
   `identity.py`) and the rename `inverter/` → `hybrid_inverter/`.
   `make check` is green on it. None of the five commits since `origin` is
   pushed.
2. **A release.** The integration's manifest pin and the survey's PEP 723
   header must both point at a release that has `hybrid_inverter/` and
   `string_inverter/`, so the rename and everything importing it ship in
   one release (`check_pinned_library.py` catches a mismatch). Until then
   bleughb cannot run the SG survey: the pinned 0.1.0a24 wheel has neither
   path. It also ships schema 23 (`connection.link_drops`, written only
   where the library's `SCHEMA >= 23`).
3. **The SG's documentation and what it lacks.**
   - `doc/architecture.md` "Register sources": a row for the SG map,
     ha-modbus-manager `sungrow_sg_dynamic.yaml` (MIT, TCzerny, commit
     `4a1e662`), built from Sungrow's *Communication Protocol of
     Residential and Commercial PV Grid-Connected Inverters* V1.1.53.
   - A wiki page `entities/device-sg.md`, after today's ingest is done
     (another session holds the wiki until then): what SG and SH share
     (the identity block, input 4950-5002, and the core PV registers
     5003-5035, MPPT4 at 5115-5116) and everything that differs (no 13000
     block, no battery or EMS, other holding registers).
   - `generate_compatibility.py` reads only `results/inverter/`; SG
     documents need a table of their own.
   - Not built: SG binary sensors, Energy dashboard hints, an SG in the
     simulator (`make sim` serves only a hybrid).
4. **Ingest gerd's surveys of 2026-11-03** (uncommitted, in `device-survey/`,
   gitignored there): the cable survey with a full control test (exit 0, 9/9
   matched, 13074 ×10, PV cut, both windows confirmed, Running after 181 s),
   the dongle survey with the wallbox at unit 3 (control test exit 3: battery
   at 10 %, the WiNet-S refused the stop and the window write with an
   exception), and the wallbox over TLS, all read while a car charged at
   10.7 kW. The wallbox log of the session is still being written (one TLS
   session, 30 s); ingest it with the documents.
   - New on hardware: the cable restart needed the start sent three times
     (still stopped 60 s after each), where every earlier restart took the
     first. Watch whether it recurs.
5. **The control test's restore through a WiNet-S** (fixed in the tree,
   uncommitted: `control_test/restore.py`, three tests in
   `test_control_test.py`). It read first and wrote only when the register
   differed, and through a dongle the read is a stale cache, so a write that
   landed was "already holding its original value" and never undone. At
   gerd's it left a forced-charging window changed on 2026-11-01 and again
   on 2026-11-03 (forced charging off, so inert; put back over the cable).
   Now only a confirmed cable reads first; a dongle always writes the
   snapshot's word, counts an accepted write as the evidence, and writes
   13074 at its measured factor alone. The snapshot is read from the same
   cache, so through a dongle the restore now puts back **only the fields the
   run touched** (`Snapshot.touched`, flushed before each write), and a
   restore with no preflight (`--restore`, the HA repair) measures the
   transport first (uncommitted). Left: a touched register goes back to the
   dongle's word, wrong only if changed over another path since the dongle
   last read it. Wants a dongle-only control test at gerd on this tree, with
   the battery above 30 % and no car charging, then a cable read of every
   snapshot register. The HA control test button shares this code, so it
   needs a release.


# Open decisions

1. **When to offer the ordinary setup** (`ONLY_SURVEY_MODE` in `const.py`;
   turning it off is the whole re-enablement, `tests/test_alpha_gate.py`),
   and **when to merge into `main`.** The merge retires the preview channel
   and opens the HACS default store, which also needs the brand in
   `home-assistant/brands` (`scripts/helpers/make_brand_icon.py` draws it).
2. **Are the entity names final?** They are reviewed
   (`doc/entity_name_review.md`, `scripts/helpers/review_names.py`). A rename
   later leaves existing ids alone and only diverges new installs, which a
   registry migration can close, so it stays cheap until release, not free.
   Wanted with it: a table (YAML | HACS) of sensor names, automations etc.,
   and whether localisation (English / German) is worth it.

# Blockers

1. **A charging car at gerd's.** Settles what input 21313 does over a session
   (does it go to 0 when charging stops?) and whether 21308/21310 are signed.
   Two dongle runs about five minutes apart, 90 s of quiet before each, while
   the car charges. `doc/wallbox_registers.md` has both questions. The
   same session would show what input 21267, input 21365, holding 21312 and
   start mode 3 at input 21314 do, which a reading with no car cannot.
   Input 21267 is not a write counter (measured 2026-10-29); it looks like
   uptime in tens of seconds. A wallbox restart would confirm it: the count
   should fall to near zero.
   **In progress 2026-11-03:** a car charged from before 11:55 UTC at a
   steady 10.7 kW, logged every 30 s over TLS. So far 21313 wandered
   297-527 at constant power (it does not follow power), the high words of
   21308/21310 stayed 0, 21267 counted up, start mode read 3 throughout.
   What is still missing is the end of the session.
2. **An SH-T on its own LAN port, in daylight** (any SH15T owner with
   one; ra1k_0 says the SH20T has none, #772). Every T so far was read
   through a WiNet-S, and one run with the control test
   (`--enable-export-limit`) settles three things:
   - **13074 on P071.** The dongle reported a word written with feed-in
     limitation off as handed, where B001 ignores it. If P071 really stores
     1:1, the integration's unanswered-probe fallback of ten sets a tenth of
     the asked export limit on an SH-T.
   - **An SBH on a direct link.** `Capability.SUNGROW_BATTERY` is granted
     for an SBR found on its own unit (`with_sungrow_battery`); an SBH is
     not until its own-unit reading is seen without a dongle.
   - **Whether an iHomeManager silences 5741-5746** (#647, #651), which
     every WiNet-S refuses anyway; ra1k_0 has one.
   Still open on the T besides: whether 13018 acts as 31211 does.
3. **A second wallbox's survey.** Settles whether 21211-21214 identify the
   unit. The wallbox reports its own serial (input 21201-21206, 11 ASCII
   characters, confirmed against Sungrow's portal 2026-10-30); the
   integration shows it on the device page, identifies the device by the
   inverter's serial plus `-wallbox`, and publishes it only as a stand-in.
   Three registers wait on a second unit:
   input 21201-21206 (the serial: use it as the device identity?), input
   21211-21214 (a short code, masked), and holding 21250-21259 (twenty
   constant ASCII digits, masked since 2026-10-29). Whichever differ between
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

6. **A first Sungrow Logger survey** (#786). Unblocks a Logger map
   (milestone 8). Logger1000/3000/4000. The survey names one by its type code at
   unit 247, decodes its identity block and publishes the rest of its 8000
   block raw (`sungrow_modbus.logger`); behind an inverter it asks unit 247
   only when the owner answers `logger` for the transport. Missing for a map:

   1. **Sungrow's *Logger Communication Protocol*.** Not on GitHub (searched
      2026-10-30); copies of 1.0.2.5, 1.0.2.7 (`TI_20211201`) and 1.0.2.9 are
      on Scribd, behind a login, and Sungrow's support portal does not list
      it. A firmware archive on GitHub that collected Sungrow documents
      (sungrow-firmware/firmware) answers HTTP 451, so do not commit the PDF
      here: keep it local and cite it, as with the inverter's. What is known
      without it: type codes at input 8000 are 0x0705 Logger3000, 0x0710
      Logger1000, 0x0718 Logger4000 (as Voyanti/ha-sungrow, GPL-3.0, cites the
      document); and register numbers in the document are one above the
      protocol address, as everywhere here (Homey community thread 126405).
      Existing maps, read for what exists and never copied:
      RafAustralia/Sungrow-Logger1000a-Modbus (no licence, read only) and
      Voyanti/ha-sungrow's `src/sungrow_logger.py` (GPL-3.0, Logger1000 only,
      read only; writes reported failing at Homey).
   2. **What sits behind it.** A Logger gives each connected inverter and meter
      a unit id of its own on its endpoint (a DTSU666-20 at unit 5 in #262),
      and wants a port per client (502, 503, 504...). `identify` looks at units
      1-5 only, so an inverter at a higher unit is not reached yet; a DTSU666
      is a device nothing maps.
   3. **A contributor with one.** Nobody has offered; the #262 participants
      (RafAustralia, purcell-lab, NBS23) are the leads. RafAustralia notes the
      Logger1000A targets the T and commercial lines rather than RS/RT.

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

16. **The discharge window on hardware** (#785). The charge window is
    settled: it raised charging at all five houses' runs on 2026-11-01
    (P020, P022, P023, cable and dongle), and a 2 s trace at mkaiser showed
    it starting in 4 s and stopping in 2 s; a start is now judged by its
    bracket. `--discharge-window` has run nowhere: it needs the battery
    discharging at least 500 W, so an evening run. fwitten's master is the
    lead (SBR096, P023), with their Home Assistant stopped; mkaiser once
    its battery is above its floor. Then the device and
    firmware pages, the log, and the options screenshot in
    `device-survey/images/` (it shows three switches, now five).

17. **A first SG survey** (#789, #790). The whole SG map is the protocol
    document's, unmeasured; bleughb has two SG5.0RS and offered, once the
    release is out. Settles what an RS answers: the meter block (5083-5104,
    undocumented on RS by the source), the per-string currents at input
    7013, the holding block from 5000, and whether the tiers suit it.
    Writes (the power limitation, holding 5007-5008) wait for a watched one.

# Future work

## Create a table with supported registers

Assumption (to be proven!): Inverter families of the SAME firmware version support the same capabilities / register sets.
Create a table: columns are inverter family + firmware version, rows are the supported registers/features.
Maybe indicate if you were not able to test / confirm a register / feature.

## Small fixes

- The preview mirror's `sync.yml` uses `actions/checkout@v4`, which GitHub
  now forces from Node 20 to Node 24 with a warning. Move to v5 in
  `doc/preview-mirror/sync.yml` and the mirror's copy together (they must stay
  byte-identical; the change needs a push to the preview repository).
- `tests/test_control_test_cli.py` fails when run alone (`No module named
  'probe'`): it relies on another test putting `device-survey/scripts/python`
  on `sys.path` first. Green in the full suite.

## SBR per-module entities

All 24 registers are read, and the position encoding and the per-module
highest/lowest cell words hold on three to eight modules (wiki: SBR battery,
#788). `cell_type_module_n` is non-zero for each fitted module, which gives
the module count, though its value differs by pack (1 on an SBR256, 66-76
elsewhere). The pack-wide cell spread ships as a sensor (#788); what is left
is deciding the sixteen per-module entities.

## Two specification registers not read

Holding 33042 (charge cutoff voltage, wide range) and holding 33274 (load
rated power), both in V1.1.16; ha-modbus-manager carries them commented out.
The survey dump reads both from 0.1.0a23.

## The PV cut (31211, #738)

- Ask the PR author on #738 for their 13250 string, or a survey; close #738
  with a pointer to the release that ships the switch.
- One evening's watch on a confirmed device: does a cut survive a night or
  a restart, or does iSolarCloud rewrite it?

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
gh issue list -s all --search "updated:>=2026-11-02T21:52:00Z" -L 50
gh api 'repos/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/comments?since=2026-11-02T21:52:00Z&per_page=100' \
  -q '.[] | "\(.issue_url | split("/") | last) \(.user.login) \(.created_at)"'
```

Last checked: **2026-11-02 21:52 UTC** (#789).

## Recurrent: llmwiki upstream check (every 6 weeks, next: 2026-12-10)

The wiki follows `@llmwiki/core` **0.1.2** (microsoft/llmwiki at `e09126f`).
Check upstream for changes to the index, log or frontmatter format
(`packages/core/src/init.ts`, `lint.ts`, `index-ops.ts`, `log.ts`) and to its
lint rules. If something changed, update `tests/test_wiki.py` and
`.wiki/AGENTS.md` together, and bump the version named in both and in
`.wiki/wiki/log.md`. Then move the date above six weeks on.
