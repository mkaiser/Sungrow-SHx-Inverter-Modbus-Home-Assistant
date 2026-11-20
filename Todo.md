Todo.md contains only what is still to do (forward looking), one sentence an
item, with its plan and its requirements. What belongs here, what belongs in a
plan under [`plans/`](plans/), and how items are numbered:
[`workflow.md`](workflow.md). Revising this file follows
[`.claude/skills/todo-housekeeping/SKILL.md`](.claude/skills/todo-housekeeping/SKILL.md)
(`/todo-housekeeping`). It has more than one writer: read it from disk and
change only your part (`AGENTS.md`).

**Next free item number: T073.** Numbers are minted in order, never reused and
never renumbered; a removed item retires its number.

Sections: **Incoming items by maintainer** (a holding area, taken in when
they ask), **Next steps** (startable now, in priority order), **Open
decisions** (for the maintainer; nothing is built on them until answered),
**Planned tests** (hardware runs with a date), **Blockers** (waiting on
hardware, daylight or a contributor), **Release**, **Future work** (wanted,
not scheduled). Next steps and blockers are grouped by device: Inverter,
Battery, Wallbox, Logger, iHomeManager, and Integration and tooling.

# Incoming items by maintainer

A holding area, not a queue: taken in only when the maintainer asks
([`workflow.md`](workflow.md)).

- Investigate / future: The make checks are very long (30 minutes). Can we cut that down?

- Investigate / future: How to properly organize the code base after release. CI/CD from github. restrict main branch to PR only. Assumption: Automated CI/CD depends on how much can the tests be stripped down.

- can folder legacy/ be deleted?

- deactivate the automatic / bot closing of issues


# Next steps

## Inverter

**T072. Daily import (13036) stuck at 0 at night on an SH6.0RS**
([#797](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/797), whose "13035" is the
protocol address): with the battery empty and the house on the grid the daily import did not count, so the daily
consumption stalled (its midnight spike is already clamped, `src/sungrow_modbus/hybrid_inverter/derived.py`).
Compare 13036 with the total import (13037/13038) over a night on an RS; icefest's SH6.0RS download on #786
(2026-11-20 01:16 UTC, not yet ingested, T061) may carry both.
*Needs*: that download ingested, or a night's readings from an RS.

What the maintainer's own inverter can answer is a planned test below (T001,
T002); the rest waits on other firmware or other houses.

## Battery

Nothing can start now (T038, T064).

## Wallbox

**The charging switch's read-back** (an off reads on for ~10 s), then T059's
retaken screenshot and a wiki source page for the 2026-11-13 run -- the
[plan](plans/T003-T004-T020-T039-T040-T059-wallbox.md), section 10. The pairing
of a TLS wallbox entry with its inverter is built and tested; its run at
gerd's (the managed test from Home Assistant) needs his tunnel and a car charging.
*Needs*: nothing.

**The rest of the gerd session** (section 9): test 4 (a mode change from the
app while charging) needs a car plugged in (tried 2026-11-20, unplugged);
7 needs the owner at the car, 5 and 6 a bright hour. Tests 1, 3 and 9 were done 2026-11-20, and the
user-defined mode's daily window (33546-33549) was mapped; section 10 now asks
what Home Assistant does with it. The tunnel now runs from the
devcontainer (`doc/development.md`, *Pitfalls*). gerd's integration was
disabled for that session: re-enable it only when told. T003 and T004
themselves still wait on a standalone wallbox (T040).

## Logger

Nothing can start now (T041). Decided, not built: the search should say which
inverters sit behind a Logger. A Logger is offered as a diagnosis-only entry;
how it is handled beyond that is open.

## iHomeManager

Nothing can start now: an owner running the preview, and a second unit's
diagnosis (T005, T006, T042).

## Integration and tooling

**T071. A migration that did not claim the legacy entity ids**
([#798](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/798)): the likeliest cause
is found and fixed, not yet confirmed by the user. An entry first set up on device-scoped ids and deleted leaves
its ids in the registry's deleted entities, and re-adding to migrate got them back ahead of the claim; the claim
now renames onto the free legacy id (`tests/test_migration.py`). The user's own way back is **Configure ->
Entity IDs -> the YAML package's**, which also takes area-prefixed ids (`tests/test_entity_id_switch.py`). Left:
the user's answer whether they had set it up before, and the fix released to the preview.
*Needs*: the maintainer posting the reply below on #798, then a release.

> Correction: choosing "migrate" should have kept your old IDs, so this is a bug. Had you added the
> integration once before and deleted it? Home Assistant then hands the deleted entities' new-style IDs
> back, ahead of the migration; the next preview fixes that. To get your old IDs now: Settings -> Devices &
> Services -> Sungrow Modbus -> **Configure** -> **Entity IDs**: the YAML package's IDs. Your old history
> continues on them. *Total DC power* is there as *Total PV input power* (`sensor.total_dc_power` on the old IDs).

**T070. Retire the comparison with the YAML package** --
[plan](plans/T070-retire-the-yaml-comparison.md). The port is finished and the
YAML is maintained by hand, so the scaffolding comes down: six test modules
and `doc/legacy_entity_map.json`. The map is a generator input as well as a
test oracle, so the legacy ids, units and state classes move into
`scripts/generate/tables/` first, proven by `make gen` leaving every generated
file byte-identical. It is what `legacy/` waits on.
*Needs*: nothing.

**T067. The *Add integration* badge, once the merge lands**: the preview
channel's badge (`marketplace_repository`, owner, repository and *Integration*
prefilled) is in the README and in step 1 of
[`doc/installing_a_preview.md`](doc/installing_a_preview.md). What is left is
`config_flow_start` (`?domain=sungrow_modbus`), which does nothing until the
integration is installed, so it belongs beside the install instructions on
`main` rather than above them here. The redirect is `marketplace_repository`,
not HACS's old `hacs_repository`, and *add integration* is
`config_flow_start`, not `config_flow` (my.home-assistant.io's FAQ lists
them).
*Needs*: T047's merge.

**T069. Retire the stale remote branches**: all of them go except
`2025-legacy`, which holds the pre-2026 YAML line. Ahead/behind `main`,
measured 2026-11-20: `experimental-archived` 17/424, last touched 2023-10-15;
`dev` 25/108 and `inverter_self_consumption` 28/108, both 2026-01-05;
`wrap-string-registers` 5/7, 2026-06-02. Tag each `archive/<name>` before
deleting it: a tag costs nothing and keeps the commits reachable, where a
deleted branch's are not.
*Needs*: `inverter_self_consumption` read against
[T002's plan](plans/T002-inverter-self-consumption.md) for anything the branch
still holds alone; the other three can go today.

--> maintainer: delete `experimental-archived, inverter_self_consumption, wrap-string-registers and dev

archive 2025-legacy to archive/2025-legacy
current main (last yaml version) to archive/

**T008. Why the search missed the maintainer's inverter**: one measurement
left -- the same sweep run from the production machine, where a modbus-proxy
holds the session -- [plan](plans/T008-search-missed-the-inverter.md).
*Needs*: a sweep from the production machine with the proxy running.

**T014. Decide the wording a fresh entry shows** now that watching the
readings is decoupled from auto repeat: "0/23 established - waiting for: ..."
where it said "no runs kept", on a house that may never run a capability test
-- which is also what *Diagnosis: tests, clear history* now leaves, since it
keeps the readings.
*Needs*: the maintainer's call, and a look at a real device page.

**T065. Name the people who answer other people's questions** in the README's
*Acknowledgements*: the discussions and the issues have a handful of regulars
who help strangers for nothing, and the list thanks contributors in the
aggregate only. `gh` can rank who replied most; it cannot tell who replied
well, and the wrong name added or a right one left out is worse than the
aggregate.
*Needs*: the maintainer's call on who belongs there.

# Open decisions

Nothing is built on these until the maintainer answers them.

**T021. Are the entity names final?** They are reviewed and decided in English
and German (`doc/entity_names.md`, `plans/_gen_text_translation_review.md`,
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

**At the maintainer's SH10RT** (T001, T002, T007) one instance serves
them all: `make dev-real`, on :8125 against `config-real/`
([`doc/development.md`](doc/development.md) for its login, its clock, and what
a restart costs an armed auto repeat). Its entities are prefixed
`hwr_sh10rt_`, and *Diagnosis: test summary* reports only when a run or a
restart makes it -- `config-real/.storage/` is what the ledger actually
holds. Two owner settings are deliberate and stay as they are:
`battery_max_soc` 90 % and the entry option `battery_max_power` 5000 W.

**T001. The site import limit (32998) at the maintainer's SH10RT, in
daylight** -- [plan](plans/T001-T063-import-limit-and-forced-startup.md). What it
settles: whether the cap is on the grid's share alone with PV counted, which
needs PV above the load, the battery part full and a forced charge above the
surplus. How: `sungrow_capability_test.py <host> --import-limit` from this
checkout, a dry run first.
*Needs*: a bright enough hour. The forced startup (13017) on firmware other
than P020 is not testable here and is T063.

**T002. *Inverter self consumption (estimated)* by day, at the maintainer's
SH10RT** -- [plan](plans/T002-inverter-self-consumption.md). It reads about
-1.9 W in Standby at night, where every term but the load's noise is zero;
what is left is the daytime look -- whether the mean is steady and plausible
while the inverter works -- and from that, whether Standby should read
`unknown` instead of a number near zero.
*Needs*: the inverter working in daylight. The 13022 path still waits on a
house that refuses 5214 (T046).

**T007. A day and a night of *Extended test (auto repeat)* at the
maintainer's SH10RT**, then ingest -- the new checks on hardware, the
auto-repeat slot schedule, the status line's wording, and the *Diagnosis:*
names on a real device page -- [plan](plans/T007-diagnosis-and-capability-tests.md).
*Needs*: a **charged battery**, which is what the nine write-side rows left
waiting all ask for, and a dusk for `ledger.TWO_MOMENTS`; the collection is
armed and observing, 37 of 55 established and none failing. The
forced-startup mode on other firmware is T063, which this house cannot
answer.

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
T -- [plan](plans/T026-sh-t-through-a-dongle.md).
*Unblocked by*: any SH15T or SH10T owner running one capability test
(`--enable-export-limit`) while the house exports.

**T063. Forced startup (13017) on firmware other than P020** -- the other
half of [the import-limit plan](plans/T001-T063-import-limit-and-forced-startup.md),
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

**T037. The discharge window on P023** (#785). It has run on P022 and P020,
which is what makes the windows writable there (T036); no P023 or SBR house
has run it, so P023 keeps the sensors and no controls.
*Unblocked by*: fwitten's master in the evening, with their Home Assistant
stopped.

## Battery

**T038. SBH.** It answers the SBR's common block at unit 2 with the SBR's
scales; the per-module arrays are unread.
*Unblocked by*: the SBH register document.

**T064. Whether the start thresholds' 1000 W maximum is the right judgement**:
the YAML's author called it a guess and asked to be told, and the inverter does
not enforce it (1010 W stored at the maintainer's on P020).
*Unblocked by*: a watched hour at a house setting a threshold above the
battery's maximum charging power, where a charge should then never start --
the behaviour `scripts/generate/tables/writes.py` already predicts.

## Wallbox

**T003. Controlling the wallbox**: the managed test from Home Assistant once the
pairing is tested (Next steps), the user-defined window and scheduled charging
(162) in the controls, a standalone wallbox, and the first writing run --
[plan](plans/T003-T004-T020-T039-T040-T059-wallbox.md), sections 10 and 11.
*Unblocked by*: gerd's AC22E-01 with a car charging and his own Home Assistant
stopped; or a standalone wallbox, which nobody has offered (T040).

**T020. Whether the standalone inference is right**: it is built, shown and
asked for, so what is left is measuring it where it matters --
[plan](plans/T003-T004-T020-T039-T040-T059-wallbox.md), section 1.
*Unblocked by*: a standalone wallbox, which nobody has offered (T003, T040).

**T039. A wallbox charging negative, or past 32.7 kW**, which settles whether
21308/21310 are signed. Input 21313 and input 21365 are still unnamed, and a
wallbox restart would show whether 21267 falls to near zero --
[plan](plans/T003-T004-T020-T039-T040-T059-wallbox.md), section 7.
*Unblocked by*: a wallbox seen charging under those conditions.

**T040. A second wallbox's diagnosis**, which settles whether 21211-21214
identify the unit -- [plan](plans/T003-T004-T020-T039-T040-T059-wallbox.md), section 6.
*Unblocked by*: the masking publishing a stand-in per masked block, plus a
terminal diagnosis carrying those blocks.

**T004. The wallbox's settings as entities** (21298, 21299, 21313): whether
any of them may be written -- [plan](plans/T003-T004-T020-T039-T040-T059-wallbox.md), section 12.
*Unblocked by*: the standalone wallbox of T003.

## Logger

**T041. A first Sungrow Logger diagnosis** (#786), which unblocks Logger
entities -- [plan](plans/T041-first-logger-diagnosis.md).
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
8051, 8052, channel 2, 8029) -- [plan](plans/T006-ihomemanager-unmeasured-fields.md).
*Unblocked by*: a second unit's diagnosis (T042), ideally single phase or with
a PROD.CT.

## Integration and tooling

**T043. mDNS and DHCP discovery: what is still open.** The zeroconf and DHCP
matchers ship; what is left is other houses, a browse the reader cannot have
spoiled, and the fields nothing explains --
[plan](plans/T043-mdns-and-dhcp-discovery.md).
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
*Unblocked by*: a diagnosis of an SH8.0RS on #655's firmware, or of SAPPHIRE
51.0x. **A third-party battery is not enough**: the maintainer's is one and
its 5214 answers (-765, -2739 and 1022 W across its readings), so what is
wanted is a house where the register is refused.

# Release

The maintainer targets a stable release in **December 2026** (said 2026-11-06).
It needs a stable `0.1.0` rather than an alpha (T048), the production-database
run or a decision to go without it (T050), the catalog submission on release
and not before (T048), and `doc/integration_migration.md` made current. The
whole of it is one plan: [`plans/T047-T053-release.md`](plans/T047-T053-release.md).

The ordinary setup is **on** (the maintainer, 2026-11-15): the opening "what
is this for?" dialog and `ONLY_DIAGNOSIS_MODE` are gone, every new entry has
entities, and the diagnosis and capability test share the device page with the
readings (`tests/test_one_setup_path.py`). `MODE_DIAGNOSTICS` stays for the
entries made while it was offered.

**T047. When to merge into `main`** -- [plan](plans/T047-T053-release.md).
*Needs*: the brand in `home-assistant/brands`, and the
`proper-ha-integration` links moved to `main`.

**T068. What a `main` link finds after the merge** --
[plan](plans/T047-T053-release.md), which has the decision and the file to
commit. Today's `main` becomes `2026-legacy`, `2025-legacy` keeps its name, and
of the 38 paths on today's `main` exactly one gets a file on the new `main`:
`modbus_sungrow.yaml`, comments only, saying the package moved and is
superseded; the header's two deep links move to `2026-legacy` in the same
motion. Everything else 404s, GitHub's rename redirect cannot change that,
and a re-download stops a working install until its owner reads the file.
*Needs*: T047's merge.

**T048. Submit to the HACS catalog once the merge is decided** --
[plan](plans/T047-T053-release.md). *Needs*: at least one full (non-pre) GitHub release;
"(preview)" dropped from the name on `main`.

**T049. The preview channel under the Marketplace**: left is a screenshot of
*Add from link* for `doc/installing_a_preview.md` --
[plan](plans/T047-T053-release.md). *Needs*: `make marketplace`.

**T050. The production database** at real scale --
[plan](plans/T047-T053-release.md). *Needs*: a copy of the maintainer's instance files,
or an IPv4 route to it (the hostname resolves to IPv6 only).

**T051. The YAML track's documentation, for the integration** --
[plan](plans/T047-T053-release.md). *Needs*: the release, after which the notes point at
the ordinary install.

**T052. Hand the preview channel's users over to the release** --
[plan](plans/T047-T053-release.md). *Needs*: the maintainer's decision on keeping the
mirror running after the release.

**T053. Deprecate and retire the YAML package, after the release** --
[plan](plans/T047-T053-release.md). *Needs*: parity, the merge, and the HACS default
store.

# Future work

Wanted, not scheduled.

**T054. How far the MPPT energy drifts** -- [plan](plans/T054-mppt-energy-drift.md).
*Needs*: a house running it a few days, on a cable and through a WiNet-S.

**T055. A generated dashboard** -- [plan](plans/T055-generated-dashboard.md).
*Needs*: the question of one default dashboard over houses that differ.

**T056. Helping users set up the Energy dashboard** --
[plan](plans/T056-energy-dashboard-help.md). *Needs*: nothing; core cannot be
pre-filled, so what is left is wording and links.

**T057. Site-wide sensors for several inverters** --
[plan](plans/T057-site-wide-sensors.md). *Needs*: users asking for them; today the
answer is documented helpers.

**T058. Renames and the databases outside Home Assistant** (InfluxDB, Grafana,
Prometheus, MQTT statestream, Node-RED) --
[plan](plans/T058-renames-outside-home-assistant.md). *Needs*: nothing; the script
and the guide exist.

**T059. The wallbox: the direct connection first** --
[plan](plans/T003-T004-T020-T039-T040-T059-wallbox.md), section 5. *Needs*: gerd's two entries side
by side, and a retaken options screenshot.

**T060. Hand inverter and wallbox readings to evcc**, so it need not open a
Modbus session of its own -- [plan](plans/T060-evcc-integration.md), which has the
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
gh issue list -s all --search "updated:>=2026-11-19T17:45:00Z" -L 50
gh api 'repos/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/comments?since=2026-11-19T17:45:00Z&per_page=100' \
  -q '.[] | "\(.issue_url | split("/") | last) \(.user.login) \(.created_at)"'
```

Last checked **2026-11-19 17:45 UTC**: nothing new since that morning, whose
one document (Maximo101's SH10RS, committed as `-2`) left two findings, both
since fixed and closed: `mppt4 carries a string` answered wrong, and a broken
`total_battery_charge` high word on every P067 machine. Their
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
