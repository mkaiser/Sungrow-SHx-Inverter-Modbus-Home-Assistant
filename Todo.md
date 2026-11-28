Todo.md contains only what is still to do (forward looking), one sentence an
item, with its plan and its requirements. What belongs here, what belongs in a
plan under [`plans/`](plans/), and how items are numbered:
[`workflow.md`](workflow.md). Revising this file follows
[`.claude/skills/todo-housekeeping/SKILL.md`](.claude/skills/todo-housekeeping/SKILL.md)
(`/todo-housekeeping`). It has more than one writer: read it from disk and
change only your part (`AGENTS.md`).

**Next free item number: T113.** Numbers are minted in order, never reused and
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

I1: Display the INtegrations Version number somewhere in the Diagnostics Tab (Dashboard)

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
controls, left are the maintainer's look and a release of the History fixes, 13017
switched on *before* the battery is low, and at gerd's whether it replaces the two hand-made dashboards -- [plan](plans/T055-generated-dashboard.md).

**T091. *Daily consumed energy*'s `last_reset`**: built (`hybrid_inverter/daily_cycle.py`); released in 0.1.0a57, and it passed a midnight and a restart at two houses (`.wiki/wiki/sources/daily-reset-midnight-2026-11-26-summary.md`); ask at #797. Known limit: with one counter alone above 0.5 kWh, its
misread as zero looks like a reset and counts that day twice. *Needs*: the maintainer's go to post there.

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

*From the code review and the documents pass (T100)*, grouped by topic; each item's file and line, and the
fix proposed, are in [the code review](plans/_code-review.md), *Reported*, and in [the documents pass](plans/_improve-doc.md), *Code that looks wrong*.

**T101. Restore safety: the capability test's restore can still be cut short** (hard constraint). Both
`_shielded` helpers (`capability_test/engine.py`, `wallbox/capability_test.py`) give way on a fourth
cancellation, where `wallbox/managed_test._shielded` loops until done; a stop write that comes back `DROPPED`
sends no start and ends without exit 5 (`capability_test/restore.py`, beside T079); a snapshot flush that raises
inside the restore (`base._touch`) leaves the fields after it unrestored.
*Needs*: the maintainer's review of each change, since it touches the restore and exit 5's meaning.

**T102. Restore safety: 13074's probe** (hard constraint). The write that lifts feed-in limitation sits
outside the `try` that restores 13087, and `_put_back` stops at its first failed read
(`hybrid_inverter/export_scale.py`); `readback._measure_export_scale` catches only `ModbusError`, so a timeout
ends the run as code 1.
*Needs*: the maintainer's review, as T101.

**T103. Snapshots left behind or not on disk**: a wallbox run the owner stops keeps its snapshot although
everything was restored (`wallbox_capability_test.py`); removing a wallbox entry leaves its snapshot in
`.storage/` (`__init__.py`); the inverter script's snapshot is not `fsync`ed before the first write
(`sungrow_capability_test.py`, where the wallbox scripts' `_save` is); a two-word owner write whose second word
fails never records the first, so a leftover snapshot's repair writes it back (`entity.py`).

**T104. A busy dongle's answer read as a refusal**: any `ModbusExceptionError` confirms "5 A refused" or
stops the user-current check in `wallbox/managed_test.py`, and `scripts/dev/managed_wallbox_field.py scan`
files a WiNet-S's 0x04/0x06 as refused and stops at its first timeout; both should ask a
`SETTLES_NOTHING` answer again, as `export_scale._ask` does.

**T105. Addresses kept out of what is published**: a guard test that every IPv4 literal in a tracked file is a
listed stand-in (the allow-list wants the maintainer's review before it gates, as the wiki and `doc/` carry
addresses too); the diagnosis summary, which says it is safe to paste, prints the real host in its run-later
and unreadable lines (`sungrow_diagnosis.py`).

**T106. User-visible texts that the code contradicts**, in `strings.json` and `german_texts.json`: the sweep's
"2181 addresses across sixteen bands" (2197 in eighteen), the capability test permissions' "off by default"
(all six default on), start and stop's "admin rights are required" (a per-entry option), `wallbox_max_amps`'s
"an offer below the 6 A minimum", and the unused `{devices_mode}` placeholder and `devices_mode_not_offered`
abort; then `make gen`, and a test holding the sweep text to `DUMP_BANDS`. Proposed wording in [the code review](plans/_code-review.md), *Reported*.
*Needs*: the maintainer's leave to edit those keys in `strings.json`, the one place their English lives.

**T107. Tooling fixes**: `screenshot.py` defaults to :8125, `make dev-real`'s port, and its
`diagnosis-running` shot starts an extended run that writes (a port of its own, and refuse unless the host is
the simulator), and it waits for a setup step that no longer exists; `sync_version.py --set` writes
`pyproject.toml` before it knows the rest can be written, and ignores `--expect` without `--check`;
`generate_devices_wanted.py` points at the wanted list's "item 7" by number; `generate_simulator_registers.py`'s
keys are literal addresses rather than `reg()`; `ihomemanager_direct._destination` overwrites the last
candidate where `probe._destination` falls back to a timestamped name; the managed wallbox test script
cannot target a slave inverter (`--unit`) or try a wallbox at unit 2 or 4.

**T108. Structure, no behaviour change**: fold the two mDNS browses into `network_names` and move `probe.py
mdns` once the pin has it; share the coordinator's component transition log with the iHomeManager's, so
`log-when-unavailable` holds there too; read `DeviceInfo` by attribute in `__init__.py`; split
`config_flow.py` (2,856 lines) only together with one helper for the setup flow's `entity_ids` and the
options flow's `promote`; move the private helpers 38 test modules import from each other into helper modules
beside `tests/corpus.py`.

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

**T109. Legacy slot: an entry with no stored slot** (hard constraint). `SungrowOptionsFlow._async_slot`
(`config_flow.py`) measures an absent `CONF_LEGACY_SLOT` and writes the result when the entry switches
**Entity IDs**, where `migration.stored_legacy_slot` reads an absent key as the unsuffixed slot; the result can
refuse the way back to legacy ids, or take another slot. Proposed: measure only for a diagnostics entry or a
stored `None`, and read an absent key on a devices entry as `""`. The wiki's legacy-slot page and the migration
guide describe that, not the code. [the code review](plans/_code-review.md), *Reported*, area 5.

**T110. Kept capability test runs whose transport is unknown**: `ledger.fold_key` keys a run with
`direct_connection` None as a dongle run, so on a cable house one such run wipes up to 30 days of kept cable
runs. Proposed: `async_ledger_add` treats an unsettled run like a dry run, kept only for its own document, at
the price of auto repeat asking again. [the code review](plans/_code-review.md), *Reported*, areas 3 and 6.

**T111. Other owners' addresses in git history**: the ones taken out of fixtures, documents and a skill
in T100 are still in the history of `tests/`, `doc/` and `.claude/skills/`. Rewriting published history is
the maintainer's call, as it was for the serial fragment.

# Planned tests

Hardware runs with a date. Removed once run and ingested.

**At the maintainer's SH10RT** one instance serves: `make dev-real`, on :8125 against `config-real/`
([`doc/development.md`](doc/development.md) for its login, its clock, and what
a restart costs an armed auto repeat). Its entities are prefixed
`hwr_sh10rt_`, and *Diagnosis: test summary* reports only when a run or a
restart makes it -- `config-real/.storage/` is what the ledger actually
holds. Two owner settings are deliberate and stay as they are:
`battery_max_soc` 90 % and the entry option `battery_max_power` 5000 W.

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

**T094. A forced charge check against a battery already charging is not a verdict.** At firetribe the battery charged at
5244 W before a 1250 W command, and "nothing measurable happened" was recorded as established
([the source](.wiki/wiki/sources/sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-meter-direct-lan-2-summary.md)).
*Needs*: the check to answer "could not tell" there, and its revision raised, so kept rows are asked again.

**T095. A wallbox's session energy falling in the test's own restart reads as a failure**: at gerd's AC22E-01 on 0.1.0a57
"wallbox energy counters never fall" failed on 1600 to 218 Wh and 1279 to 274 Wh, two falls on 2026-11-25, when the extended test ran twice.
The stop/start check most likely restarts the count while the session minutes run on; inferred from the timing, not watched.
*Needs*: the fall and the test's stop matched by time, then the check to ignore that fall.

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

**T112. A lost answer at unit 2 is filed as a battery pack**: `battery/discovery.py` reads a timeout on the
device type read as "no type code, a pack", so a slave inverter whose answer was lost may be granted
`SUNGROW_BATTERY`, which moves write bounds. The fix counts only a refusal outside `SETTLES_NOTHING` as a pack,
once it is known what a pack at unit 2 answers to 5000 through a WiNet-S.
*Unblocked by*: that read, through a WiNet-S with a pack (a diagnosis that records it).

## Wallbox

**T003. Controlling the wallbox**: the managed half is done (the test passed from Home Assistant at gerd's on 2026-11-24);
left are the user-defined window and scheduled charging (162) in the controls, which the maintainer decides, and a
standalone wallbox -- [plan](plans/T003-T004-T020-T039-T040-T059-wallbox.md), sections 10 and 11.
*Unblocked by*: a standalone wallbox's capability test (T040); a maintainer's colleague runs a standalone AC22E-01
under evcc, phases switching, if it is on the LAN and evcc is stopped for the run (2026-11-26).

**T020. Whether the standalone inference is right**: it is built, shown and
asked for, so what is left is measuring it where it matters --
[plan](plans/T003-T004-T020-T039-T040-T059-wallbox.md), section 1.
*Unblocked by*: a standalone wallbox, the colleague's of T003 the first candidate (T040).

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
commit. Today's `main` becomes `archive/2026-legacy`, beside
`archive/2025-legacy`, and
of the 38 paths on today's `main` exactly one gets a file on the new `main`:
`modbus_sungrow.yaml`, comments only, saying the package moved and is
superseded; the header's two deep links move to `archive/2026-legacy` in the same
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

**T056. Helping users set up the Energy dashboard**: built and released in 0.1.0a54 (the Energy view lists the sensors and can
add them); left is what a house without a meter reads -- [plan](plans/T056-energy-dashboard-help.md). *Needs*: one such house.

**T057. Site-wide sensors for several inverters** --
[plan](plans/T057-site-wide-sensors.md). *Needs*: users asking for them; today the
answer is documented helpers.

**T058. Renames and the databases outside Home Assistant** (InfluxDB, Grafana,
Prometheus, MQTT statestream, Node-RED) --
[plan](plans/T058-renames-outside-home-assistant.md). *Needs*: nothing; the script
and the guide exist.

**T014. Decide the wording a fresh entry shows** now that watching the
readings is decoupled from auto repeat: "0/23 established - waiting for: ..."
where it said "no runs kept", on a house that may never run a capability test
-- which is also what *Diagnosis: tests, clear history* now leaves, since it
keeps the readings.
*Needs*: the maintainer's call, and a look at a real device page.

**T084. A clean migration at gerd's**: his installation grew through every preview, so a fresh one from the YAML package's
history, the package stopped first, shows what a first-time user gets. It touches his production history.
His installation is on device-scoped ids since 2026-11-25 ([the source](.wiki/wiki/sources/gerd-entity-id-switch-2026-11-25-summary.md)).
*Needs*: a plan, a full backup and his consent.

**T085. The RAK module's web page** (the dongle before the WiNet-S): how it is reached and with which documented login.
*Needs*: a house with one, and the maintainer's word before any login is tried.

**T060. Watch evcc drive a Sungrow through Home Assistant**, following [the guide](doc/evcc.md)
-- [plan](plans/T060-evcc-integration.md).
*Needs*: evcc at gerd's with a car, and `verifybatterymodes` on the maintainer's SH10RT.

**T099. The forced-charge window's 300 W floor skips a battery charging slowly with headroom**: a pack taking a few hundred
watts with kilowatts under `snapshot.battery_ceiling` is not tested unless the bracket confirms the start first
(`src/sungrow_modbus/capability_test/effects.py`); decide whether the floor should follow the headroom.
*Needs*: nothing.

**T093. EMHASS beside evcc, planning the battery under a dynamic tariff** --
[plan](plans/T093-emhass.md).
*Needs*: a house with a dynamic tariff whose owner wants it; T060.

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
gh issue list -s all --search "updated:>=2026-11-25T14:24:00Z" -L 50
gh api 'repos/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/comments?since=2026-11-25T14:24:00Z&per_page=100' \
  -q '.[] | "\(.issue_url | split("/") | last) \(.user.login) \(.created_at)"'
```

Last checked **2026-11-25 14:24 UTC**: Firetribe's second cable reading (#786) is ingested; benji-beit's SH5.0RT
was offered for Wednesday 2026-11-25, and the maintainer answered to wait; what it was wanted for (13074 on a `.95.14`
that is not 10 kW) is settled by Firetribe's.
Firetribe also asked why 0.1.0a57's dashboard does not show: answered 2026-11-25, waiting for Firetribe.
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
