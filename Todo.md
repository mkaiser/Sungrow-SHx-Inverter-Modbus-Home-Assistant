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

1. **Bring back the YAML package's history sensors, for cable users.** Its
   monthly and yearly PV generation (6227-6238, 6250-6289), monthly and
   yearly direct consumption (6417-6428, 6429-6468) and monthly and yearly
   export (6596-6607, 6608-6647) are all in V1.1.16. They went because most
   YAML users read through a WiNet-S, which refuses the block: inputs
   6196-6198 answer on every cable survey and are refused on every dongle
   one (wiki: WiNet-S, the history registers), and V1.1.16 marks the whole
   block 6100-6826 "WiNet-S/S2 and Logger is not supported". The survey
   dump reads all of it from 0.1.0a23. Gate them on a capability
   probed at 6227, so a dongle house gets none of them. Every other sensor
   the YAML ever dropped was renamed and is still read, or moved (grid
   frequency to 5242, battery power to 5214, battery capacity to 5639), or
   went for cause: grid state's 13030 is reserved in V1.1.16, and the manual
   MPP scan at holding 30230 is in no Sungrow document. What needs deciding
   first is open decision 4.


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
3. **Adopting the opt-in SBR YAML sensors.** Ids like
   `sensor.sg_battery_1_max_voltage_of_cell` come from a copy-pasted file
   outside the package and are **not** adopted. Doing it would mean taking
   over entities this project never generated; the default stays "no".
4. **How many history entities.** Twelve monthly and up to twenty yearly
   values per quantity is ~100 entities. Options: only the current month
   and year as sensors (and the rest as attributes), or the YAML's full set
   so its users' history continues under the same ids. The YAML's ids
   (`sensor.monthly_pv_generation_01_january`...) still hold years of
   history at some houses.


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
2. **An SH-T on its own LAN port, in daylight** (ra1k_0, #772, is the
   lead; any SH15T/SH20T owner will do). Every T so far was read through a
   WiNet-S, and one run with the control test (`--cut-pv`,
   `--enable-export-limit`) settles four things:
   - **13074 on P071.** The dongle reported a word written with feed-in
     limitation off as handed, where B001 ignores it. If P071 really stores
     1:1, the integration's unanswered-probe fallback of ten sets a tenth of
     the asked export limit on an SH-T.
   - **The PV cut on P071** (holding 31211, #738): P022 and P023 are
     confirmed; a watched cut puts P071 into `CONFIRMED_ON_FIRMWARE`
     (`test_nothing_is_confirmed_without_a_document_that_shows_it` wants
     the survey committed). On a T, watch whether 13018 acts as well.
   - **An SBH on a direct link.** `Capability.SUNGROW_BATTERY` is granted
     for an SBR found on its own unit (`with_sungrow_battery`); an SBH is
     not until its own-unit reading is seen without a dongle.
   - **Whether an iHomeManager silences 5741-5746** (#647, #651), which
     every WiNet-S refuses anyway; ra1k_0 has one.
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

15. **Discharge schedules and the import limit, not in any Sungrow document**
    (#785). Korsberg has used them for years, as protocol addresses:
    weekday discharge 33150-33157 (registers 33151-33158: two windows,
    hour and minute), weekend discharge enable 33178 (0x55/0xAA) and two
    windows 33179-33186 (registers 33179-33187), and a site import power
    limit at 32997 (register 32998). His survey's dump agrees on the
    schedules (weekday 00:00-24:00, weekend enabled, 00:00-24:00), on one
    house. Read-only entities need the same values from a second house;
    writes need a watched write, as 31211 did (wiki: firmware gating).
    The survey's dump reads 32997 and the forced-charging block from
    0.1.0a22.


# Future work

## SBR per-module entities

All 24 registers are read, and the position encoding holds on three and four
modules (wiki: SBR battery). `cell_type_module_n` is non-zero for each fitted
module, which gives the module count. What is left is deciding the entities.

## Two specification registers not read

Holding 33042 (charge cutoff voltage, wide range) and holding 33274 (load
rated power), both in V1.1.16; ha-modbus-manager carries them commented out.
The survey dump reads both from 0.1.0a23.

## The PV cut (31211, #738)

- Ask the PR author on #738 for their 13250 string, or a survey; close #738
  with a pointer to the release that ships the switch.
- One evening's watch on a confirmed device: does a cut survive a night or
  a restart, or does iSolarCloud rewrite it?
- A run through a WiNet-S: whether the dongle forwards the write.

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

## EVCC connection

- Hand inverter and wallbox readings to evcc, e.g. over MQTT, so evcc
  need not open a Modbus session of its own. To find out: does evcc have
  a standard configuration for that?

## Recurrent: llmwiki upstream check (every 6 weeks, next: 2026-12-10)

The wiki follows `@llmwiki/core` **0.1.2** (microsoft/llmwiki at `e09126f`).
Check upstream for changes to the index, log or frontmatter format
(`packages/core/src/init.ts`, `lint.ts`, `index-ops.ts`, `log.ts`) and to its
lint rules. If something changed, update `tests/test_wiki.py` and
`.wiki/AGENTS.md` together, and bump the version named in both and in
`.wiki/wiki/log.md`. Then move the date above six weeks on.
