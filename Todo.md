Todo.md contains only what is still to do (forward looking), one sentence an
item, with its plan and its requirements. What belongs here, what belongs in a
plan under [`plans/`](plans/), and how items are numbered:
[`workflow.md`](workflow.md). Revising this file follows
[`.claude/skills/revise-todo/SKILL.md`](.claude/skills/revise-todo/SKILL.md)
(`/revise-todo`). It has more than one writer: read it from disk and change
only your part (`AGENTS.md`).

**Next free item number: T064.** Numbers are minted in order, never reused and
never renumbered; a removed item retires its number.

Where the last hardware session at the maintainer's SH10RT left off, and what
a fresh session needs that is written nowhere else:
[`plans/mkaiser-diagnosis/handover.md`](plans/mkaiser-diagnosis/handover.md).

Sections: **From the maintainer** (their inbox, read first), **Next steps**
(startable now, in priority order), **Open
decisions** (for the maintainer; nothing is built on them until answered),
**Planned tests** (hardware runs with a date), **Blockers** (waiting on
hardware, daylight or a contributor), **Release**, **Future work** (wanted,
not scheduled). Next steps and blockers are grouped by device: Inverter,
Battery, Wallbox, Logger, iHomeManager, and Integration and tooling.

# From the maintainer

Anything the maintainer puts here, in any form. **Read this section first**,
before deciding what to work on: an entry here outranks the priority order
below. Do it if it is small, otherwise file it as a numbered item with a plan;
remove what you took in, in the same edit, and say what you did with it. An
entry you cannot act on stays, with one line saying what it waits on. Only the
maintainer writes new entries here (`workflow.md`).

*(empty)*

# Next steps

## Inverter

Nothing can start now. What the maintainer's own inverter can answer is a
planned test below (T001, T002); the rest waits on a house with other
firmware.

## Battery

Nothing can start now (T038).

## Wallbox

Nothing can start now (T003, T004); a standalone wallbox is what unblocks
both (T040).

## Logger

Nothing can start now (T041). Decided, not built: the search should say which
inverters sit behind a Logger. A Logger is offered as a diagnosis-only entry;
how it is handled beyond that is open.

## iHomeManager

Nothing can start now: an owner running the preview, and a second unit's
diagnosis (T005, T006, T042).

## Integration and tooling

**T008. Why the search missed the maintainer's inverter**: one measurement
left -- the same sweep run from the production machine, where a modbus-proxy
holds the session -- [plan](plans/search-missed-the-inverter.md).
*Needs*: a sweep from the production machine with the proxy running.

**T009. Activate the scenes of `doc/scenes.md` on hardware.** *Battery Forced
Charge* was pressed at the maintainer's on 2026-11-17 and the ceiling it
reads moves with the pack -- [plan](plans/scenes-on-hardware.md).
*Needs*: the finding written into `doc/scenes.md`.

**T010. Bound every write entity from what the device states**, where it
states it: the wallbox's user-defined current is capped at a flat 32 A while
the wallbox reports 16.0 A at 21263 -- [plan](plans/range-checks.md).
*Needs*: nothing; the readings are in the corpus.

**T012. A safe pattern for ad-hoc hardware watches**, after an expiring access
token left the maintainer's 13017 on for 50 minutes past its window --
[plan](plans/ad-hoc-hardware-watches.md).
*Needs*: nothing.

**T014. Decide the wording a fresh entry shows** now that watching the
readings is decoupled from auto repeat: "0/23 established - waiting for: ..."
where it said "no runs kept", on a house that may never run a capability test.
*Needs*: the maintainer's call, and a look at a real device page.

**T015. Separate clearing the capability ledger from clearing the
plausibility store** -- [plan](plans/clearing-a-ledger.md).
*Needs*: nothing; not urgent.

**T018. Should `mppt3 / mppt4 carries a string` ask for the current?** It
grants a tracker on voltage alone, which is wrong at Maximo101's SH10RS --
[plan](plans/tracker-current-check.md).
*Needs*: nothing; a verdict change raises the check's revision in
`plausibility.CHECK_REVISIONS`, which costs that check's evidence alone.

**T020. Tell a managed wallbox from a standalone one**: infer it from
behaviour, show the inference, and still ask the owner before writing a
wallbox's own registers -- [plan](plans/managed-vs-standalone-wallbox.md).
*Needs*: nothing for steps 1-4; a standalone wallbox to measure against
(T003) before the inference can be trusted.

# Open decisions

Nothing is built on these until the maintainer answers them.

**T021. Are the entity names final?** They are reviewed and decided in English
and German (`doc/entity_names.md`, `plans/text_translation_review.md`,
`scripts/generate/tables/naming.py`), and entity ids stay English in every
language. A rename later leaves existing ids alone and only diverges new
installs, which a registry migration can close: cheap until the release, not
free. A new name goes under **To discuss** (`NAME_DISCUSSION` in `naming.py`).

**T023. Should a battery or wallbox be looked for again while an entry runs?**
Both are found at setup only (`dynamic-devices` on the quality scale), and
looking again costs sessions on an inverter that grants few.

**T024. Which entities should start disabled?** The quality scale's
`entity-disabled-by-default` asks for the rarely used ones to start off. Only
entities the YAML package never had can qualify: a ported one must stay
enabled, or its history stops (`AGENTS.md`).

# Planned tests

Hardware runs with a date. Removed once run and ingested.

**T001. The site import limit (32998) at the maintainer's SH10RT, in
daylight** -- [plan](plans/import-limit-and-forced-startup.md). What it
settles: whether the cap is on the grid's share alone with PV counted, which
needs PV above the load, the battery part full and a forced charge above the
surplus. How: `sungrow_capability_test.py <host> --import-limit` from this
checkout, a dry run first.
*Needs*: a bright enough hour. The forced startup (13017) on firmware other
than P020 is not testable here and is T063.

**T002. *Inverter self consumption (estimated)* by day, at the maintainer's
SH10RT** -- [plan](plans/inverter-self-consumption.md). It reads about
-1.9 W in Standby at night, where every term but the load's noise is zero;
what is left is the daytime look -- whether the mean is steady and plausible
while the inverter works -- and from that, whether Standby should read
`unknown` instead of a number near zero.
*Needs*: the inverter working in daylight. The 13022 path still waits on a
house that refuses 5214 (T046).

**T025. The site import limit (32998) at fwitten's master, when it is
reachable** (SH10RT-V112, P023, SBR096, cable -- ulfben's exact hardware,
#546): what it adds is the engine's own `--import-limit` check on P023.
How: `sungrow_capability_test.py <host> --import-limit --allow-dark
--no-restart` from this checkout, a dry run first, the stand-in read before
any write; their Home Assistant stays connected, so expect retries. After
dark, battery under 90 %, not in Standby. Then ingest.
*Needs*: fwitten's addresses to answer (they did not on 2026-11-07).

# Blockers

Each waits on something outside this repository. A measurement the diagnosis
takes is asked for in `device-diagnosis/devices-wanted.md`'s table, never from
a named person.

## Inverter

**T026. An SH-T through its WiNet-S, in daylight, with export**: settles
13074's scale on P071, an SBH on a direct link, and 13018 / 33149-33150 on the
T -- [plan](plans/sh-t-through-a-dongle.md).
*Unblocked by*: any SH15T or SH10T owner running one capability test
(`--enable-export-limit`) while the house exports.

**T063. Forced startup (13017) on firmware other than P020** -- the other
half of [the import-limit plan](plans/import-limit-and-forced-startup.md),
which its own house cannot answer: the maintainer's SH10RT is P020.
*Unblocked by*: a watched run after dark at a house on P022, P023 or an SH-T,
in low-SoC standby.

**T027. firetribe, once more** (#784): a cable capability test with the
inverter *running* gives the first SH6.0RT-V112 readbacks and its 13074 write
scale. Their WiNet-S 0x04s are contention, reproduced at gerd's.
*Unblocked by*: firetribe rerunning it.

**T028. A fault seen on hardware.** The fifteen words are decoded from
V1.1.11's Appendix 4 and one diagnosis confirms the word order (bit 30, a
slave with no meter).
*Unblocked by*: a reading during a real grid or battery fault, and the battery
words through a dongle.

**T029. Meter phase voltage/current (5741-5746) on dongle houses** read zero
through every WiNet-S measured and are gated on a non-zero voltage; whether
they need reading on their own is #756. `layout.py` changes only on
measurement.
*Unblocked by*: a diagnosis from an affected owner.

**T030. T-series energy counters.** One SH20T reads 13045 (daily export) as 0
while exporting, and 5003/5004-5005 duplicate the export counters.
*Unblocked by*: a second T diagnosis, ideally on a cable, before
`registers.py` changes.

**T031. The SG's zeros and writes.** On bleughb's two SG5.0RS through a
WiNet-S the meter block (5083-5104), the per-string block (input 7013) and
holding 5020 read nothing; writing the power limitation (holding 5007-5008)
waits for a watched write.
*Unblocked by*: an SG on a cable, or one with its own meter.

**T032. gerd's cable restart**: the start had to be sent three times on
2026-11-03 (cable) and again on 2026-11-10 (WiNet-S, running after 182 s).
Look at what the inverter reports between the starts.
*Unblocked by*: another restart at gerd's, watched.

**T033. The SG's tracker counts beyond the SG5.0RS.** `MPPT_COUNTS` is the
source's model table, many rows unverified.
*Unblocked by*: a diagnosis of any other SG (devices-wanted, row 10).

**T034. The PV cut (31211, #738) beyond the four confirmed firmwares**, and
whether a cut survives a night or a restart or iSolarCloud rewrites it.
Nothing here or at the maintainer's P020 can answer it.
*Unblocked by*: a capability test on `SUNSTONE-H_B000.V001.P068`,
`B000.V002.P067`, `B000.V002.P059`, `B000.V002.P057` or
`PEARL-H_B001.V001.P038`; one evening's watch on a confirmed device.

**T035. What register 13080 counts.** Documented as the external EMS heartbeat
(0-1000 s), it reads 0 on 42 diagnoses, 330 on two houses in EMS mode 0, and
875 then 961 on ra1k_0's SH20T in EMS mode 3. Nothing reads or writes it until
then.
*Unblocked by*: two reads of it a minute apart at that house.

**T036. The discharge windows: writing them** (#785), in no Sungrow document.
They read as diagnostic entities (`Capability.DISCHARGE_SCHEDULE`).
*Unblocked by*: a watched write, as 31211 had (wiki: firmware gating).

**T037. The discharge window on P023** (#785). It has run on P022 and P020;
no P023 or SBR house has run it.
*Unblocked by*: fwitten's master in the evening, with their Home Assistant
stopped.

## Battery

**T038. SBH.** It answers the SBR's common block at unit 2 with the SBR's
scales; the per-module arrays are unread.
*Unblocked by*: the SBH register document.

## Wallbox

**T039. A wallbox charging negative, or past 32.7 kW**, which settles whether
21308/21310 are signed. Input 21313 and input 21365 are still unnamed, and a
wallbox restart would show whether 21267 falls to near zero.
*Unblocked by*: a wallbox seen charging under those conditions.

**T040. A second wallbox's diagnosis**, which settles whether 21211-21214
identify the unit -- [plan](plans/wallbox-identity-blocks.md).
*Unblocked by*: the masking publishing a stand-in per masked block, plus a
terminal diagnosis carrying those blocks.

**T003. Controlling the wallbox**: the mode select's timing, pairing a TLS
wallbox entry with the inverter that manages it, a standalone wallbox, and
the first writing run -- [plan](plans/wallbox_tests.md), section 8.
*Unblocked by*: gerd's AC22E-01 with a car charging and his own Home Assistant
stopped; or a standalone wallbox, which nobody has offered (T040).

**T004. The wallbox's settings as entities** (21298, 21299, 21313): whether
any of them may be written -- [plan](plans/wallbox_tests.md), section 9.
*Unblocked by*: the standalone wallbox of T003.

## Logger

**T041. A first Sungrow Logger diagnosis** (#786), which unblocks Logger
entities -- [plan](plans/first-logger-diagnosis.md).
*Unblocked by*: a contributor with a Logger1000/3000/4000; nobody has offered.

## iHomeManager

**T042. A second iHomeManager diagnosis** (#786), which decides the fields
left out of its entities (T006) and whether 4358-4362 are U32. The first unit
(SV930.001.00.P020, port 503) answered all 56 mapped fields.
*Unblocked by*: a second unit, ideally single phase, on other firmware or with
a PROD.CT.

**T005. See an iHomeManager entry in a real Home Assistant.** Its 40 read-only
sensors were built 2026-11-11 against the one unit's words and released in
0.1.0a37, but no real instance has shown them; how many connections a unit
takes at once is unmeasured.
*Unblocked by*: an iHomeManager owner running the preview.

**T006. The iHomeManager fields left out of its entities** (8554, 8047, 8048,
8051, 8052, channel 2, 8029) -- [plan](plans/ihomemanager-unmeasured-fields.md).
*Unblocked by*: a second unit's diagnosis (T042), ideally single phase or with
a PROD.CT.

## Integration and tooling

**T043. mDNS and DHCP discovery: what is still open.** The zeroconf and DHCP
matchers ship; what is left is other houses, a browse the reader cannot have
spoiled, and the fields nothing explains --
[plan](plans/mdns-and-dhcp-discovery.md).
*Unblocked by*: diagnoses carrying `network_names` from houses with a dongle,
and one whose inverter port takes its address by DHCP.

**T044. The capability test's restore through a WiNet-S, on hardware.** Two
dongle-only runs reported all 46 settings written back, but the battery was at
2-3 % (SoC checks skipped) and no cable read followed. At ra1k_0's SH20T the
restore of 33209 was refused five times with 0x04, and that model has no LAN
port.
*Unblocked by*: a dongle-only run at gerd's with the battery above 30 % and no
car charging, then a cable read of every snapshot register; and ra1k_0
checking the forced-charging schedule's days in iSolarCloud.

**T045. 33213 at peter_sm's: the register or the house?** Every write of 33213
there lost the connection, nine of nine over five days, and since 0.1.0a32
other writes drop too. If it is the register, the time entity *Forced charging
end 1* must write the window in one frame or not be offered there. No code
changes before the run.
*Unblocked by*: one run at peter_sm's with `--charge-window` only, then a
single write of 33213's held value.

**T046. Battery power where 5214 is refused** (#655, #770). The fallback to
13022 is built on ten firmwares' evidence but has never met a house that
refuses 5214; then decide whether the *Battery power* entity falls back too.
Not to be asked for on #655 (maintainer, 2026-11-11).
*Unblocked by*: a diagnosis of an SH8.0RS on #655's firmware, of SAPPHIRE
51.0x, or of an inverter with a third-party battery.

**T007. The diagnosis and its capability tests**: the forced-startup mode on
other firmware, the new checks on hardware, the auto-repeat slot schedule, the
status line's wording and translation, and the *Diagnosis:* names on a real
device page -- [plan](plans/diagnosis-and-capability-tests.md).
*Unblocked by*: one auto-repeat collection at the maintainer's SH10RT over a
day and a night, then ingest; and a house in low-SoC standby after dark on
P022, P023 or an SH-T for the forced-startup mode.

**T013. The scenes other than *Battery Forced Charge*, on hardware** --
[plan](plans/scenes-on-hardware.md), *Beyond the one press*.
*Unblocked by*: sun with a battery that is not empty (the two export scenes),
and a battery with something in it (bypass, forced discharge).

**T017. Does the inverter reset its daily counters in one step?** --
[plan](plans/daily-counter-reset.md).
*Unblocked by*: a midnight at a house where the check names every counter that
fell (0.1.0a44 on).

# Release

The maintainer targets a stable release in **December 2026** (said 2026-11-06).
It needs a stable `0.1.0` rather than an alpha (T048), the production-database
run or a decision to go without it (T050), the catalog submission on release
and not before (T048), and `doc/integration_migration.md` made current. The
whole of it is one plan: [`plans/release.md`](plans/release.md).

The ordinary setup is **on** (the maintainer, 2026-11-15): the opening "what
is this for?" dialog and `ONLY_DIAGNOSIS_MODE` are gone, every new entry has
entities, and the diagnosis and capability test share the device page with the
readings (`tests/test_one_setup_path.py`). `MODE_DIAGNOSTICS` stays for the
entries made while it was offered.

**T047. When to merge into `main`** -- [plan](plans/release.md).
*Needs*: the brand in `home-assistant/brands`, and the
`proper-ha-integration` links moved to `main`.

**T048. Submit to the HACS catalog once the merge is decided** --
[plan](plans/release.md). *Needs*: at least one full (non-pre) GitHub release;
"(preview)" dropped from the name on `main`.

**T049. The preview channel under the Marketplace**: left is a screenshot of
*Add from link* for `doc/installing_a_preview.md` --
[plan](plans/release.md). *Needs*: `make marketplace`.

**T050. The production database** at real scale --
[plan](plans/release.md). *Needs*: a copy of the maintainer's instance files,
or an IPv4 route to it (the hostname resolves to IPv6 only).

**T051. The YAML track's documentation, for the integration** --
[plan](plans/release.md). *Needs*: the release, after which the notes point at
the ordinary install.

**T052. Hand the preview channel's users over to the release** --
[plan](plans/release.md). *Needs*: the maintainer's decision on keeping the
mirror running after the release.

**T053. Deprecate and retire the YAML package, after the release** --
[plan](plans/release.md). *Needs*: parity, the merge, and the HACS default
store.

# Future work

Wanted, not scheduled.

**T054. How far the MPPT energy drifts** -- [plan](plans/mppt-energy-drift.md).
*Needs*: a house running it a few days, on a cable and through a WiNet-S.

**T055. A generated dashboard** -- [plan](plans/generated-dashboard.md).
*Needs*: the question of one default dashboard over houses that differ.

**T056. Helping users set up the Energy dashboard** --
[plan](plans/energy-dashboard-help.md). *Needs*: nothing; core cannot be
pre-filled, so what is left is wording and links.

**T057. Site-wide sensors for several inverters** --
[plan](plans/site-wide-sensors.md). *Needs*: users asking for them; today the
answer is documented helpers.

**T058. Renames and the databases outside Home Assistant** (InfluxDB, Grafana,
Prometheus, MQTT statestream, Node-RED) --
[plan](plans/renames-outside-home-assistant.md). *Needs*: nothing; the script
and the guide exist.

**T059. The wallbox: the direct connection first** --
[plan](plans/wallbox-direct-connection.md). *Needs*: gerd's two entries side
by side, and a retaken options screenshot.

**T060. Hand inverter and wallbox readings to evcc**, so it need not open a
Modbus session of its own -- [plan](plans/evcc-integration.md), which has the
route (evcc's `homeassistant` templates) and what is left to write
(`doc/evcc.md`).
*Needs*: nothing; no integration code changes.

## T061. Recurrent: new diagnoses to ingest (daily, after noon)

Every day after noon, read the general diagnosis thread
([#786](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/786))
and any issue a diagnosis was posted to since the last check. Comments older than
the last check are done; read only what is newer. Ingest each new
diagnosis as `.wiki/AGENTS.md` describes (raw file, source page, entity pages,
index, log), and name the contributor (without `@`) and the issue number in
the commit; a diagnosis signed `anonymous` stays unnamed. Then move the date
below on.

```bash
gh issue list -s all --search "updated:>=2026-11-19T07:30:00Z" -L 50
gh api 'repos/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/comments?since=2026-11-19T07:30:00Z&per_page=100' \
  -q '.[] | "\(.issue_url | split("/") | last) \(.user.login) \(.created_at)"'
```

Last checked **2026-11-19 07:30 UTC**: one contributor on #786, one document
ingested (Maximo101's SH10RS, committed as `-2`). It left two findings, both
now items of their own: `mppt4 carries a string` answered wrong (T018) and a
broken `total_battery_charge` high word on every P067 machine, which is fixed
and closed (T019). Their
**AC22E-01** still could not be ingested -- the 0.1.0a44 download carries
`"diagnosis": null` because an upgrade restarts Home Assistant and a wallbox
entry's download hands over the last run's document from memory
(`DiagnosisState.document`). **Worth asking that house again**, in this order:
*Diagnosis: start* on the wallbox's own device page, then Download diagnostics
in the same session -- and worth weighing whether a wallbox entry's download
should build its document on the spot, as an inverter entry's does.

## T062. Recurrent: llmwiki upstream check (every 6 weeks, next: 2026-12-10)

The wiki follows `@llmwiki/core` **0.1.2** (microsoft/llmwiki at `e09126f`).
Check upstream for changes to the index, log or frontmatter format
(`packages/core/src/init.ts`, `lint.ts`, `index-ops.ts`, `log.ts`) and to its
lint rules. If something changed, update `tests/test_wiki.py` and
`.wiki/AGENTS.md` together, and bump the version named in both and in
`.wiki/wiki/log.md`. Then move the date above six weeks on.
