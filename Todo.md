Todo.md contains only what is still to do (forward looking), one sentence an
item, with its plan and its requirements. What belongs here, what belongs in a
plan under [`plans/`](plans/), and how items are numbered:
[`workflow.md`](workflow.md). Revising this file follows
[`.claude/skills/todo-housekeeping/SKILL.md`](.claude/skills/todo-housekeeping/SKILL.md)
(`/todo-housekeeping`). It has more than one writer: read it from disk and
change only your part (`AGENTS.md`).

**Next free item number: T092.** Numbers are minted in order, never reused and
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
([`workflow.md`](workflow.md)). An entry is numbered **I1**, **I2** ... to be addressed by; next: **I4**.

# Next steps

## Inverter

**T072. Daily import (13036) stuck at 0 at night on an SH6.0RS**
([#797](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/797), whose "13035" is the
protocol address): with the battery empty and the house on the grid the daily import did not count, so the daily
consumption stalled (its midnight spike is already clamped, `src/sungrow_modbus/hybrid_inverter/derived.py`).
The readings check *daily counters keep up with the totals* names exactly this (a total rising
1 kWh with its daily counter unmoved), so a morning diagnosis download from an RS that ran the
integration overnight answers it, with no writes and no capability test.
*Needs*: that download from an RS house, the reporter's or icefest's, on a build with the check; the
reporter (Diegocampy) offered on #797 to test once the fix is out.

**T090. Which firmware and models support the site import limit, and is only a cluster without it?**
[Plan](plans/T090-import-limit-support.md). *Needs*: owners' diagnoses (an SH-T, another SH-RS, a lone 01011.95.03, a second cluster);
the daylight cap at fwitten, which the maintainer deferred.

The rest waits on other firmware or other houses.

## Battery

Nothing can start now (T038, T064).

## Wallbox

**gerd's wallbox, what is left**: why one-phase surplus charging ends after 10-30 s (four attempts on 2026-11-24, at up to
1.6 kW over the house), and what a plug-in does in PV surplus -- [the source](.wiki/wiki/sources/gerd-wallbox-2026-11-24-summary.md).
*Needs*: a brighter day there, over 3 kW of surplus with the battery nearly full; someone at the car for the plug-in.

## Logger

Nothing can start now (T041). Decided, not built: the search should say which
inverters sit behind a Logger. A Logger is offered as a diagnosis-only entry;
how it is handled beyond that is open.

## iHomeManager

Nothing can start now: an owner running the preview, and a second unit's
diagnosis (T005, T006, T042).

## Integration and tooling

**T055. The integration's own dashboard**: after the maintainer's review of the Diagnosis view (0.1.0a54) and the wallbox's
controls, left are the maintainer's look and their word on *Daily consumed energy*'s `last_reset` and two tile names (in the plan), a release of the History fixes, 13017
switched on *before* the battery is low, and at gerd's whether it replaces the two hand-made dashboards -- [plan](plans/T055-generated-dashboard.md).
*Needs*: 0.1.0a55 at gerd's.

**T091. *Daily consumed energy*'s `last_reset`**: built (`hybrid_inverter/daily_cycle.py`); after its release, see on a real house that the day's
statistics follow the sensor through a midnight and a restart. *Needs*: a release.

**T081. The included cards**: keep Power and Energy Flow Card Plus current with a weekly workflow that opens a pull request
to bump the pin (never a bot that merges), and credit their author in the README, a dashboard link and every release note -- [plan](plans/T081-included-cards-updates-and-credit.md).
*Needs*: the maintainer's word on the plan; *Allow GitHub Actions to create pull requests* switched on.

**T079. A night restart on an empty pack reads as a house left changed**: at peter-sm the
capability test stopped the inverter after dark with the pack at 1.0 % (under its 5 % minimum) and
no PV; it stayed in Standby past the deadline, as it would have anyway, and the run reported
outcome 5 and "the link dropped" with no poll refused and every setting restored
([the reading](.wiki/wiki/sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-21-summary.md)).
Two fixes to weigh, both in `capability_test/restore.py` and the pre-flight: do not restart when the
pack is at its minimum with no PV (nothing can come back to Running), and do not call a deadline a
dropped link when no poll was refused. Outcome 5 is the hard-constraint code, so its meaning
changes only with the maintainer.
*Needs*: the maintainer's call on what Standby at the deadline means.

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

**T074. Should the integration repair the Energy dashboard's sums after a long gap itself?** After more than ten
days between the YAML package's last statistics and the first start, each lifetime counter's sum restarts at 0
and the dashboard shows one hugely negative hour; the migration guide gives the manual repair
(`recorder/adjust_sum_statistics`, [the guide](doc/integration_migration.md)), and a Repairs issue with a fix
could do it in one click, at the price of writing to the user's statistics
([the source](.wiki/wiki/sources/gerd-ha-migration-2026-11-21-summary.md)).

**T024. Which entities should start disabled?** The quality scale's
`entity-disabled-by-default` asks for the rarely used ones to start off. Only
entities the YAML package never had can qualify: a ported one must stay
enabled, or its history stops (`AGENTS.md`).

# Planned tests

Hardware runs with a date. Removed once run and ingested.

**At the maintainer's SH10RT** (T007) one instance serves: `make dev-real`, on :8125 against `config-real/`
([`doc/development.md`](doc/development.md) for its login, its clock, and what
a restart costs an armed auto repeat). Its entities are prefixed
`hwr_sh10rt_`, and *Diagnosis: test summary* reports only when a run or a
restart makes it -- `config-real/.storage/` is what the ledger actually
holds. Two owner settings are deliberate and stay as they are:
`battery_max_soc` 90 % and the entry option `battery_max_power` 5000 W.

**T007. The diagnosis's new spacing on hardware**: an auto repeat collection there, watching *Diagnosis: next attempt*
and the log -- [plan](plans/T007-diagnosis-and-capability-tests.md). The forced startup on an SH-T is T063.
*Needs*: a date.

# Blockers

Each waits on something outside this repository. A measurement the diagnosis
takes is asked for in `device-diagnosis/devices-wanted.md`'s table, never from
a named person.

## Inverter

**T026. A second SH-T through its WiNet-S, in daylight, with export**: confirms
13074's scale on P071 (GalKar's SH15T: stored as handed, by one watched limit), an SBH on a direct link, and 13018 / 33149-33150 on the
T -- [plan](plans/T026-sh-t-through-a-dongle.md).
*Unblocked by*: any SH15T or SH10T owner running one capability test
(`--enable-export-limit`) while the house exports.

**T080. The export-limit fallback on an SH-T**: decided (maintainer, 2026-11-24): ten stays the general fallback, because
a wrong one sets ten times the limit and a wrong ten only a tenth; P071 alone gets one, once a second watched run
confirms it stores the word as handed ([register 13074](.wiki/wiki/entities/register-13074.md)) -- [plan](plans/T026-sh-t-through-a-dongle.md).
*Unblocked by*: T026's run, at a P071 house.

**T063. Forced startup (13017) on an SH-T** -- the switch is confirmed on
P020, P022 and P023 ([register 13017](.wiki/wiki/entities/register-13017.md));
every SH-T reads `0x55` and gets no switch until a watched wake.
*Unblocked by*: a watched run after dark at an SH-T house (P071), in low-SoC
standby.

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

**T033. The SG's tracker counts beyond the SG5.0RS.** `MPPT_COUNTS` is the
source's model table, many rows unverified.
*Unblocked by*: a diagnosis of any other SG (devices-wanted, row 9).

**T034. The PV cut (31211, #738) beyond the four confirmed firmwares**, and
whether a cut survives a night or a restart or iSolarCloud rewrites it.
No firmware here or at the maintainer's P020 extends the list; the survival
half needs only a confirmed device.
*Unblocked by*: a capability test on `SUNSTONE-H_B000.V001.P068`,
`B000.V002.P067`, `B000.V002.P059`, `B000.V002.P057` or
`PEARL-H_B001.V001.P038`; one evening's watch on a confirmed device -- gerd's
P022 is one, and the overnight leg leaves 31211 set, which costs him a
morning's generation if the restore fails, so ask for that leg explicitly and
measure the restart first.

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

**T003. Controlling the wallbox**: the managed half is done (the test passed from Home Assistant at gerd's on 2026-11-24);
left are the user-defined window and scheduled charging (162) in the controls, which the maintainer decides, and a
standalone wallbox -- [plan](plans/T003-T004-T020-T039-T040-T059-wallbox.md), sections 10 and 11.
*Unblocked by*: a standalone wallbox, which nobody has offered (T040).

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

**T043. DHCP discovery at one house**: the matcher ships and nobody has been seen found by it; a diagnosis
says so from schema 29 -- [plan](plans/T043-mdns-and-dhcp-discovery.md).
*Unblocked by*: a diagnosis from a house whose inverter port takes its address by DHCP.

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
refuses 5214; then decide whether the *Battery power* entity falls back too,
and check *Inverter self consumption (estimated)* on that path there (its other questions are
settled: a 15-minute mean, an energy sensor, and the number kept in Standby).
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
After it: `main` takes pull requests only, with CI as the gate.
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

**T054. How far the MPPT energy drifts** -- [plan](plans/T054-mppt-energy-drift.md)
(one cable day: 0.984 of *Daily PV generation*).
*Needs*: more days from the production recorder, and a house through a WiNet-S.

**T056. Helping users set up the Energy dashboard**: built and released in 0.1.0a54 (the Energy view lists the sensors and can
add them); left is what a house without a meter reads -- [plan](plans/T056-energy-dashboard-help.md). *Needs*: one such house.

**T057. Site-wide sensors for several inverters** --
[plan](plans/T057-site-wide-sensors.md). *Needs*: users asking for them; today the
answer is documented helpers.

**T058. Renames and the databases outside Home Assistant** (InfluxDB, Grafana,
Prometheus, MQTT statestream, Node-RED) --
[plan](plans/T058-renames-outside-home-assistant.md). *Needs*: nothing; the script
and the guide exist.

**T069. Retire the stale remote branches** (deferred by the maintainer, 2026-11-24): `experimental-archived`, `inverter_self_consumption`,
`wrap-string-registers` and `dev` go (maintainer), each tagged `archive/<name>` first so the commits stay reachable.
*Needs*: `inverter_self_consumption` read against the integration's *Inverter self consumption (estimated)* first; and whether
`2025-legacy` and today's `main` are to be named under `archive/`, as the maintainer wrote, or keep the names
`2025-legacy` and `2026-legacy` that T068 and every published link rely on.

**T014. Decide the wording a fresh entry shows** now that watching the
readings is decoupled from auto repeat: "0/23 established - waiting for: ..."
where it said "no runs kept", on a house that may never run a capability test
-- which is also what *Diagnosis: tests, clear history* now leaves, since it
keeps the readings.
*Needs*: the maintainer's call, and a look at a real device page.

**T084. A clean migration at gerd's**: his installation grew through every preview, so a fresh one from the YAML package's
history, the package stopped first, shows what a first-time user gets. It touches his production history.
*Needs*: a plan, a full backup and his consent.

**T085. The RAK module's web page** (the dongle before the WiNet-S): how it is reached and with which documented login.
*Needs*: a house with one, and the maintainer's word before any login is tried.

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
gh issue list -s all --search "updated:>=2026-11-24T21:45:00Z" -L 50
gh api 'repos/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/comments?since=2026-11-24T21:45:00Z&per_page=100' \
  -q '.[] | "\(.issue_url | split("/") | last) \(.user.login) \(.created_at)"'
```

Last checked **2026-11-24 21:45 UTC**: swo14's four readings (#786) are ingested; benji-beit's SH5.0RT
was offered for Wednesday 2026-11-25, and the maintainer answered to wait.
Maximo101's
**AC22E-01** was not ingested: the 0.1.0a44 download carried `"diagnosis": null`. Since 0.1.0a45 a wallbox entry's download
reads the wallbox on the spot, so **Download diagnostics on a current version is worth asking that house for**.

## T062. Recurrent: llmwiki upstream check (every 6 weeks, next: 2026-12-10)

The wiki follows `@llmwiki/core` **0.1.2** (microsoft/llmwiki at `e09126f`).
Check upstream for changes to the index, log or frontmatter format
(`packages/core/src/init.ts`, `lint.ts`, `index-ops.ts`, `log.ts`) and to its
lint rules. If something changed, update `tests/test_wiki.py` and
`.wiki/AGENTS.md` together, and bump the version named in both and in
`.wiki/wiki/log.md`. Then move the date above six weeks on.
