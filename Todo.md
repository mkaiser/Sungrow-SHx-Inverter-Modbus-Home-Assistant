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

1. **Release, then ask ra1k_0 (#772) to run `survey.sh`.** The survey now
   reads an iHomeManager (`sungrow_modbus.ihomemanager`), but contributors
   run the published wheel, so it reaches them with the next release. One
   run at that house could read the iHomeManager, the SH20T's own LAN port
   (blocker 2) and their AC22E-01 (blocker 3, a second wallbox).
2. **Finish the survey issue, #786.** It is open and the integration's
   notification, the docs and the issue form point there. Left: pin it, and
   link it from the default branch's README (the YAML package, `main`; that
   change is yours). `.github/workflows/survey-issue.yml` writes
   `devices-wanted.md` into the issue *body* once the repository variable
   `SURVEY_ISSUE` is set, which would replace the hand-written body: move that
   text into `scripts/helpers/survey_issue_body.py` first, or leave the
   variable unset.


# Open decisions

## Naming

- Deferred up to now. Create a table (YAML | HACS) with sensor names,
  automations etc. Is there a good way for localization support, e.g.
  English / German?

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
     confirmed; a watched cut puts P071 into `CONFIRMED_ON_FIRMWARE`.
     [plans/cut-pv-generation.md](plans/cut-pv-generation.md).
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


# Future work

## EVCC connection

- Hand inverter and wallbox readings to evcc, e.g. over MQTT, so evcc
  need not open a Modbus session of its own. To find out: does evcc have
  a standard configuration for that?

## iHomeManager in the integration

Milestone 5. The survey reads one (unit 247, port 502, 503 or 504, one
connection each); the integration does not, and its config flow fails such
an endpoint with `no_serial_number`. Wait for a measured reading before
building entities on `sungrow_modbus.ihomemanager`. Sungrow's protocol PDF:
https://github.com/TCzerny/ha-modbus-manager/blob/main/docs/Communication%20Protocol%20of%20iHomeManager_V1.0.2.pdf

## Sungrow Logger

Milestone 8, Logger1000/3000/4000. The survey names one by its type code at
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

## Recurrent: llmwiki upstream check (every 6 weeks, next: 2026-12-10)

The wiki follows `@llmwiki/core` **0.1.2** (microsoft/llmwiki at `e09126f`).
Check upstream for changes to the index, log or frontmatter format
(`packages/core/src/init.ts`, `lint.ts`, `index-ops.ts`, `log.ts`) and to its
lint rules. If something changed, update `tests/test_wiki.py` and
`.wiki/AGENTS.md` together, and bump the version named in both and in
`.wiki/wiki/log.md`. Then move the date above six weeks on.
