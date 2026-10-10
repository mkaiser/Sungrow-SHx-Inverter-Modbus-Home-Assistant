# What users reported: the last 50 GitHub issues

Scope: issues **#654 to #775** (opened 2026-01-11 to 2026-10-09), open and
closed, read in full with every comment (about 300). Pull requests are
excluded. Issues are cited by number and nobody is named. Two threads quote
real device serials (#736, #751), and those are deliberately left out of this
file.

Status labels below are checked against the code on `proper-ha-integration`
as of 2026-10-10:

- **covered**: the integration already handles it, with the place named
- **partly**: handled in part; the rest is spelled out
- **open**: not handled; a proposal follows

## The short version

Almost every issue here has the same root cause: **a YAML package cannot
decide anything.** It polls every register for every user, so a register that
one model, firmware or transport does not have floods the log and leaves
entities unavailable. It writes 13074 with one fixed scale, so it was wrong
for someone whichever way the scale was set: four changes in six months, each
fixing one group and breaking another. And it cannot sequence or protect a
write, so scenes left batteries capped at 0.1 kW. The maintainers' reply,
repeated across many threads, was "comment it out yourself; YAML has no
logic". That is the integration's case in users' own words.

What the integration already gets right because of this: capability gating
by family and transport, a per-device probe of 13074's write scale, `nan`
on every S32 power field, NUL-stripped strings, serialized writes, and
history-preserving migration. What is still missing: a **fault code**, a
**forced charge/discharge service**, **firmware-level** register gating,
**visibility of the feed-in ratio** that silently overrides the W limit, and
a **repair issue for the stale-session case**, which is the most common
support answer.

## Themes at a glance

| | Theme | Issues | Status |
| :---: | --- | --- | --- |
| A | Registers that never answer: log floods, unavailable entities | #654 #655 #660 #664 #673 #674 #678 #742 #756 #770 | partly |
| B | 13074 export limit off by ten | #666 #677 #707 #734 #746 #763 | covered by design, unproven at 1:1 |
| C | Feed-in **ratio** 13088 overrides the W limit | #763 #768 | partly |
| D | Battery power limits and start power on RS / T / SBH | #654 #679 #705 #743 #751 | partly |
| E | Sessions, contention, "Not connected" | #656 #685 #702 #726 #731 #769 | partly |
| F | Bogus values: 0x7FFFFFFF, NUL padding, energy spikes | #692 #708 #736 | covered, one test missing |
| G | Fault and alarm codes | #745 | open |
| H | EMS mode, scenes, control API | #677 #680 #684 #701 #721 #739 | partly |
| I | Wallbox and other devices | #686 #712 | partly |
| J | Models and surveys | #662 #772 #775 | partly |
| K | Migration, packaging, releases | #663 #667 #694 #699 #748 #750 #767 | covered, lessons to add |
| L | Questions that are really documentation | #695 #765 (#660) | open |

---

## A. Registers that never answer

### What users reported

- **5740–5745** (meter phase voltage/current, undocumented) return an
  exception on **SH10RT-20 with firmware 95.14**, over the LAN port as well
  as the WiNet-S. Three owners confirmed it (#756). Others see the same
  registers fail only through a WiNet-S (#660, #678), and SHxRS owners
  without a meter see them fail too (#678).
- **13249 / 13264 / 13279** (inverter, module and battery firmware strings)
  time out with "No response received after 3 retries" on old firmware
  (SAPPHIRE 51.0x, #660, #673) and on SHxRS (#655, #674). A side effect hurt
  more than the missing strings: **every other sensor slowed to a
  five-minute cadence** (#664), and **HA took minutes to boot** (#742). The
  only fix offered was to comment them out.
- **2596 / 2612 / 2628** (version strings 2–4) fail on SHxRS and through a
  WiNet-S (#654, #674, #678).
- On an SH8.0RS over WiNet-S WLAN: 5014/5015 (MPPT3), 5213 (battery power),
  5241, 5630 and 5638 fail every poll (#655).
- An SH10RT-20 owner on WiNet-S WLAN had registers fail at random, and
  `switch.load_adjustment_mode` went unavailable every few minutes. The
  iSolarCloud app showed everything **offline** while HA polled (#678,
  2026-09-11).
- A third-party battery (StarkCMR emulating a BYD) shows no battery power
  sensor (#770).

### What it means for the integration

**Partly covered.**

- `capabilities.py` already gates by family: firmware strings 13250+ are
  excluded for RS/MG/RL/CX, 2612/2628 by transport (6100), and MPPT3/4 and
  the second meter channel through `ZERO_MEANS_ABSENT`.
- `UpdateReport` lets one block fail without emptying the rest, and
  `_async_update_components` retries a lost connection once per component.
  #664 and #742 cannot happen.

**Open:**

1. **Gate by firmware, not only by family.** 5740–5745 on RT-20 95.14 is a
   firmware regression inside a family that otherwise has them. Proposal: a
   block that answers exception 0x02 (never a timeout) on *N* consecutive
   polls is marked absent for this entry, logged once at INFO, and named in
   diagnostics. It is re-probed on reload or once a day, so a firmware update
   that brings it back is noticed. Timeouts must not count: a timeout is not
   evidence about the register (CLAUDE.md, "A failed read is not a
   refusal").
2. Ask #756's three reporters for a survey. Three RT-20s on 95.14, over
   cable, is the cheapest way to pin down the firmware boundary.
3. #770: ask for a survey. A third-party BMS behind the inverter is a case
   with no fingerprint yet.

---

## B. Export power limit 13074 off by ten

### What users reported

The longest-running problem on the YAML side, in six threads:

| When | Issue | What happened |
| --- | --- | --- |
| 2026-02 | #666 | SH10RS: "5000 W becomes 500 W". A `/10` for RS was added and reported as fixed by one owner, not by another |
| 2026-02/03 | #677 | Four RS owners: the `/10` makes it worse. Reverted 2026-03-08. Also found: firmware version strings on "latest" RS units are not comparable, and Sungrow support installs "special" builds |
| 2026-03/04 | #707 | SH10RT-20 and SH8.0RT-V112: the RT `/10` is wrong for them. Removed for all models 2026-04-27 |
| 2026-05 | #734 | SH-RT on firmware before 95.13: entering 800 sets 8000 W. Answered as "a firmware bug, update" |
| 2026-07 | #746 | SH8.0RT 95.13: the limit can be switched **on** from HA but not **off**. A direct Modbus write works; a scene plus `update_entity` is the workaround |
| 2026-08/09 | #763 | SH10RT-20 on 95.14, LAN port: "700 sets 7000". Second owner confirms. The WiNet web UI takes 0.0–10.0 kW |

### What it means for the integration

**Covered by design.** This is exactly the per-device factor the project
measured: ×10 at three houses, 1:1 at fwitten. `export_scale` probes it with
a write that changes nothing, `SungrowExportLimitNumber` stores the answer
in `CONF_EXPORT_WRITE_SCALE`, and an unanswered probe falls back to ten
without storing it.

**Open:**

1. **The 1:1 side is still unrun on hardware** (CLAUDE.md). #666 and #677
   suggest that some SHxRS units store 1:1 and others multiply. The RS owners
   in those threads are the most valuable testers this project has for the
   probe. Ask them to press the device page probe on the preview channel.
2. Record the reported firmware strings (#677, #707, #734, #763) in
   `doc/compatibility.md` as **reported, unmeasured**, so a later fingerprint
   can confirm or contradict them.
3. #746: check that turning the limitation **off** (13087 → 0x55) is
   confirmed by reading the register back, not assumed from the write. The
   YAML switch reverted because its state came from the write.
4. #765 (export while the battery is not full, RT-20 master/slave) may be a
   limit set ten times too low by an earlier package version. Worth one line
   in the troubleshooting docs: "check 13074 and 13088 first".

---

## C. Feed-in ratio 13088 overrides the W limit

### What users reported

- The YAML `TODO` for "Feed-in limitation ratio" sits right above
  "Active power limitation" and reads as a wrong address (#768). The register
  number versus address offset confused the reporter as well.
- One installer set **60 %** (German rule) through iSolarCloud. Both 13088
  and 13074 then held matching values (#768).
- The spec says that when both are configured, **the ratio wins**. Nobody
  knows how to "unconfigure" it or what happens when they conflict (#763,
  #768).

### What it means for the integration

**Partly covered.** `feed_in_limitation_ratio` is mapped (`registers.py`,
13088, `nan=65535`) and gated by capability.

**Open:** expose it as a read-only sensor **next to** the export limit
number, and raise a repair or attribute when a non-zero ratio implies a lower
cap than 13074. "I set 7000 W and nothing changed" then explains itself. Do
not offer a write: the ratio is usually an installer's grid-code setting and
the user is often not allowed to change it (#768).

---

## D. Battery power limits and start power on RS / T / SBH

### What users reported

- **33148/33149** (charging/discharging start power) read **655350 W**,
  which is 0xFFFF ×10, on SH6.0RS, SH10RS, SH15T and SH10T. They never take a
  write (#654, #743). One commit had swapped the comment's register and
  address, which sent people chasing a wrong-address theory (#654).
- **SH10RS refuses 33047/33048 above 10 600 W** with exception 0x04, while
  the secrets default allowed 14 000+ (#705). BDC rated power **5628 reads 0**
  on that model (#705).
- SBR default max power: datasheets from 2021, 2023 and 2024 disagree. The
  installer training says to use *lowest* voltage × 30 A (#679).
- A wallbox's own battery management overwrote max charge/discharge, which
  looked like the integration failing (#654).
- **SBH via WiNet-S unit 2** (SH20T + SBH150): 10740–10750 (voltage,
  current, temperature, SOC, SOH, totals) work. The SBR cell blocks from
  10756 on return 0x02. 19938 looks like a BMS current limit (50.0 A) (#751).

### What it means for the integration

**Partly covered.**

- `BATTERY_START_POWER` is gated off for RS and T (`capabilities.py`,
  citing #743).
- The max-power number is bounded by the pack and by 5628 (`battery.py`,
  `number.py`), using the lower of the two, with the conservative voltage
  #679 asks for.
- SBH on unit 2 through a dongle is supported, and a dongle's missing cell
  block is documented in `battery_registers.py`.

**Open:**

1. **5628 = 0 must not mean "unbounded".** When BDC rated power reads 0,
   fall back to a per-model table (SH10RS: 10 600 W measured in #705), and
   otherwise to the pack limit alone.
2. On a write refused with **0x04**, tell the user "above what this inverter
   accepts" in the error, rather than a generic Modbus failure.
3. Compare #751's SBH table with `battery_registers.py`. Does the SBH path
   skip 10756+ on a cable too, not only through a dongle? Is 19938 worth a
   diagnostic sensor?
4. Docs: "another controller (wallbox, EMS, evcc) can overwrite these
   values" (#654).

---

## E. Sessions, contention, "Not connected"

### What users reported

- After an HA update everything goes "Not connected" while `nc` reaches 502.
  The fix each time was **unplugging the inverter's LAN for 10–60 s**,
  because the inverter still held the old session (#656, two users; #731).
- A **second Modbus master** breaks it: FHEM reading the same inverter
  (#769), an evcc Modbus proxy (#678), a proxy's `connection_time` delay
  (#674).
- A synchronous client gets "Broken pipe" on its second read: the inverter
  drops the session between requests (#702).
- While HA polls through a WiNet-S, **iSolarCloud shows the devices
  offline** (#678).
- Inverter reboots every 3–4 min while polled, with a BYD battery (#726).
  BMS fault 714 after updating (#685). Both owners later traced it to
  firmware. The project could not reproduce either.
- UI freeze with a WebSocket backlog (#685); not this project's doing.

### What it means for the integration

**Partly covered.** One config entry is one serialized connection shared by
every device on the endpoint, the opening reads back off 5/20/45/90 s, and
polling pauses during a survey. That removes the self-inflicted half.

**Open:**

1. **Repair issue for the stale-session case.** When TCP connects but N
   consecutive Modbus requests fail, raise: "the inverter is not answering
   Modbus. Another client (evcc, FHEM, a proxy, an old HA session) is the
   usual cause. Stop it, or unplug the inverter's network cable for a
   minute." This is the single most repeated support answer in these 50
   issues.
2. Diagnostics: consecutive failures and the time of the last good poll.
3. Docs: "one master per endpoint". Proxies are a known source of random
   failures (#674, #678). Note that the WiNet-S serves iSolarCloud too, and
   heavy polling starves it (#678).

---

## F. Bogus values

### What users reported

- The meter was disconnected while the system ran. Load and export power
  read **2 147 483 647 W**, and the inverter's own totals were corrupted;
  fixing them took iSolarCloud corrections plus SQL (#692). The YAML then
  added `nan_value`.
- String sensors carried **trailing NULs**, which crashes a **PostgreSQL**
  recorder and poisons unrelated rows in the same transaction (#736). The
  YAML fix (template wrappers) caused `_2` entity id collisions.
- `daily_consumed_energy` / `total_consumed_energy` dip negative at
  midnight and spike during the day, because the template recomputes on each
  of its five inputs separately (#708).

### What it means for the integration

**Covered:**

- Every S32 power field declares `nan=2147483647`: `load_power`,
  `export_power_raw` and the meter channels (`registers.py`).
- `modbus_connection`'s string decoder already `rstrip("\x00")`, and
  `model.present()` maps an all-NUL string to None.
- Derived values are computed from one coherent poll, not one input at a
  time.

**Open:** a regression test that a padded string (`'SBRBCU-S_22011.01.30\x00\x00'`)
reaches HA without NULs, so a library change cannot bring #736 back. A test
that a derived `total_increasing` value does not decrease across the
midnight reset of the daily registers (#708).

---

## G. Fault and alarm codes

### What users reported

An SH10RT owner with recurring BMS faults wanted HA to report them. They
found **input 5453 = 714** (BMS communication fault) during an active fault
and 0 otherwise (#745). The maintainer pointed at the documented fault
registers and the bit map in Appendix 4 of the protocol.

### What it means for the integration

**Open.** Only running-state labels exist (`derived.RUNNING_STATES`).
Proposal:

- A `sensor` (enum) **active fault code** with a lookup table from the
  protocol appendix, and a `binary_sensor` (device class `problem`) on top
  of it for automations.
- Survey first whether 5453 answers on a cable **and** through a dongle,
  before gating it.
- The documented fault bitfields: decode them into an attribute listing the
  active faults.

---

## H. EMS mode, scenes, control API

### What users reported

- **External EMS** reverts to self-consumption after ~20 s, even when set
  from iSolarCloud (#721). The spec ties it to a heartbeat whose details are
  not public.
- Scenes cannot render templates, so "limited discharge" set max discharge
  to near zero and nothing set it back. One house ran on grid power with a
  full battery until the installer intervened (#677, #680). A scene id typo
  (#684). Turning the dashboard's danger mode on froze one HA (#701).
- Dragging a slider queues writes and logs "set_value: Already running"
  (#654).
- A user building a price- and forecast-driven planner wanted a
  brand-neutral command interface: `ForcedCharge(W)`, `ForcedDischarge(W)`,
  `Solar(W)` (#739).
- Sungrow training warns against frequent writes to holding registers,
  which wear out flash. One user wrote 13074 every 15 s, and Sungrow support
  said that was fine (#654).

### What it means for the integration

**Partly covered.** Writes are serialized (`PARALLEL_UPDATES = 1`) and
debounced, and there are no scenes to get wrong.

**Open:**

1. **Services** `sungrow_modbus.force_charge(power_w)`,
   `force_discharge(power_w)` and `self_consumption()`. Each sets EMS mode,
   command and power **in the right order**, reads them back, and skips
   writes whose value is already held, which also limits flash wear. This
   replaces the scenes and gives #739 its API.
2. **External EMS and VPP**: the `ems_mode` select currently offers both as
   writable options (`select_descriptions.py`), which reproduces #721 for
   anyone who picks them. Make them read-only (displayed, not selectable)
   until the heartbeat is understood.
3. Skip-if-unchanged for every number write, in one place.

---

## I. Wallbox and other devices

### What users reported

- Owners want the AC011E reached through the inverter, as in an earlier fork
  (#686). A modular YAML was judged impractical.
- An **AC113-01** wallbox (SH5.0RT-20) gave no values with the documented
  YAML recipe (#712).

### What it means for the integration

**Partly covered.** AC011E-01 / AC22E-01 are their own device at unit 3 (via
WiNet-S) or 248 (direct serial). **Open:** the AC113 is unknown to this
project. Ask for a survey. The iHomeManager is still unmeasured.

---

## J. Models and surveys

### What users reported

- An **SG6.0RS** (string inverter, no battery) showed mostly unavailable
  entities. It uses a different, conflicting register map (#662).
- Unprompted fingerprints arrived: SH20T over WiNet-S WLAN (#772), SH15T +
  SBH200 over WiNet-S LAN (#775). The maintainer asked people to wait for the
  announced call.

### What it means for the integration

**Partly covered.** #772 and #775 are survey input.
**Open:** the config flow should **refuse an SG** by its device type code
(register 5000) with a clear "string inverters are not supported" message,
instead of creating entities that never answer. `family_for()` returns
None for an unknown code today, which means "probe it" rather than "refuse".

---

## K. Migration, packaging, releases

### What users reported

- Entity ids ending in `_2` after the 2026 rewrite. The old entity still
  held the id and was hidden by the "unavailable" filter (#694, #750, #736).
- Missing secrets and aliases, a file never saved, a mangled include (#663,
  #667, #748).
- Automations broke because sliders changed from `input_number` to template
  `number` (#666).
- No release notifications (#699).
- The plan to build a proper integration on HA 2026.9's Modbus (#767), which
  is this branch.

### What it means for the integration

**Covered:** claiming the legacy `entity_id` at creation
(`migration.py`), so history continues; a config flow instead of
`secrets.yaml`; versioned releases through HACS and the preview channel.

**Open:**

1. Detect `_2` leftovers from the YAML era (an entity named like a legacy
   id plus `_2`) and offer to fold them in the migration repair. #694 is the
   exact case.
2. Migration notes: list the automation actions that change
   (`input_number.set_value` → `number.set_value`, scenes → services).
3. Tell #699 and #767 about the preview channel once it is announced.

---

## L. Questions that are really documentation

- **Backup load is not part of load power** (#695). The user had to add
  "total backup power" to get the real house load. Proposal: a derived
  `house_load_incl_backup` sensor in `derived.py`, named so nobody mistakes
  it for `load_power`.
- **Charging and exporting at once, with the battery not full**, on RT-20
  master/slave (#765). No answer was given. FAQ: check 13074/13088, battery
  max charge power on **both** units, and the BMS current limit.
- **Load power follows DC power** (#660). The answer was that this usually
  means CT or meter wiring, not Modbus. FAQ entry.
- **Old firmware**: many problems disappeared after a firmware update
  (#673, #678, #685). The survey's firmware strings make "which firmware are
  you on" answerable without iSolarCloud installer access.

---

## Prioritised backlog

From the open items above, ordered by how many reports each would have
prevented:

1. **Repair issue for stale sessions and second masters** (E). It is the
   most repeated support answer.
2. **Firmware-level absence**: retire a block after consistent 0x02 answers
   and re-probe later (A).
3. **Force charge / discharge / self-consumption services**, with external
   EMS and VPP made read-only in the select (H).
4. **Active fault code sensor** and a problem binary sensor (G).
5. **Feed-in ratio sensor and an override warning** (C).
6. **BDC = 0 fallback** and a clear message on 0x04 (D).
7. **SG refusal** in the config flow (J).
8. Regression tests: NUL-padded strings, monotonic derived totals (F).
9. Survey asks: the RS owners in #666/#677 and RT-20 owners in #734/#763
   (13074 scale, especially the 1:1 side); #756 (5740–5745 on 95.14); #770
   (third-party BMS); #712 (AC113).
10. Docs and FAQ: one master per endpoint, backup load, firmware first (E, L).

---

## Appendix: all 50 issues

| # | State | Opened | Comments | Title | Theme |
| ---: | --- | --- | ---: | --- | :---: |
| [#775](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/775) | open | 2026-10-09 | 0 | Fingerprint for SH15T + SBH200 via WiNet-S-lan | J |
| [#772](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/772) | open | 2026-09-16 | 1 | Survey finished: SH20T | J |
| [#770](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/770) | open | 2026-09-11 | 0 | Cant see battery power sensor | A |
| [#769](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/769) | open | 2026-09-09 | 7 | Modbus "Not connected" errors after upgrading to HA Core 2026.9.1, raw pymodbus connects fine | E |
| [#768](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/768) | open | 2026-09-09 | 6 | Wrong TODO for Feed-in Limitation Ratio (and missing sensor for it) | C |
| [#767](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/767) | open | 2026-09-04 | 3 | Try AI to generate a backwards compatible yaml alternative | K |
| [#765](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/765) | closed | 2026-09-03 | 0 | Battery charging slower than before / excessive grid export | L |
| [#763](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/763) | open | 2026-08-26 | 4 | Firmware update changed the behaviour of Export Power Limit | B |
| [#756](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/756) | open | 2026-07-30 | 6 | SH10RT-20 (FW 95.14): Smart Meter registers 5740–5745 return Modbus Exception while power registerswork Description | A |
| [#751](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/751) | closed | 2026-07-18 | 2 | Support direct SBH battery registers via WiNet-S forwarded Unit ID on SHxxT inverters | D |
| [#750](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/750) | closed | 2026-07-17 | 2 | sungrow_device_type in dashboard, but not in yaml | K |
| [#748](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/748) | closed | 2026-07-10 | 1 | Integration doesn't seem to load | K |
| [#746](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/746) | closed | 2026-07-01 | 7 | Max Power Export scene fails to re-enable export | B |
| [#745](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/745) | closed | 2026-06-26 | 3 | Missing active fault entity in SH10RT Modbus integration | G |
| [#743](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/743) | closed | 2026-06-18 | 3 | Unable to set Battery dis/charging start power. SH10RS | D |
| [#742](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/742) | closed | 2026-06-11 | 1 | Several ModBus Errors: "No response received after 3 retries, continue with next request" with different registers | A |
| [#739](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/739) | closed | 2026-06-05 | 4 | Inverter Command Listener | H |
| [#736](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/736) | closed | 2026-05-31 | 9 | string sensors expose trailing NUL (0x00) padding → recorder crash on PostgreSQL | F |
| [#734](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/734) | closed | 2026-05-28 | 5 | Scale on entity: number.export_power_limit | B |
| [#731](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/731) | closed | 2026-05-17 | 4 | Modbus TCP: "Not connected" loop after 2026.5.2 update (asyncio.Lock regression) | E |
| [#726](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/726) | closed | 2026-05-10 | 7 | Inverter reboots every 3-4 minutes when integration is active | E |
| [#721](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/721) | closed | 2026-04-30 | 5 | EMS Mode selection doesn't work properly | H |
| [#712](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/712) | closed | 2026-04-20 | 0 | No values for Wallbox entities | I |
| [#708](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/708) | closed | 2026-03-31 | 3 | `daily_consumed_energy` / `total_consumed_energy`: Negative spikes at midnight + intraday upward spikes since 2025-03-21 | F |
| [#707](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/707) | closed | 2026-03-30 | 2 | Export Power Limit not working with SH10RT-20 | B |
| [#705](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/705) | closed | 2026-03-27 | 9 | SH10RS / SBH250 maximums not working properly | D |
| [#702](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/702) | closed | 2026-03-25 | 0 | [OT] Inverters returns eof | E |
| [#701](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/701) | closed | 2026-03-24 | 2 | "Danger Mode" turn on, block my total HA | H |
| [#699](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/699) | closed | 2026-03-19 | 2 | Use "releases" feature for better visibility of new features/updates | K |
| [#695](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/695) | closed | 2026-03-09 | 0 | Question regarding total power and backup-power load | L |
| [#694](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/694) | closed | 2026-03-07 | 4 | Migrating not working, removed meter sensor but cannot rename _2 to old name. | K |
| [#692](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/692) | closed | 2026-03-05 | 7 | Load/Export power absurdly high when smart meter gets disconnected (2,147,483,647 W) | F |
| [#686](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/686) | closed | 2026-02-20 | 6 | Plans for Adding Sungrow Wallbox? | I |
| [#685](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/685) | closed | 2026-02-20 | 12 | UI freeze and WebSocket buffer overflows (Client unable to keep up) - appearing after 2 years of stability | E |
| [#684](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/684) | closed | 2026-02-17 | 1 | small bug: entity_id: scene.set_max_export_power | H |
| [#680](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/680) | closed | 2026-02-16 | 2 | Bug in Self-Consumption Mode (max battery discharge) scene? | H |
| [#679](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/679) | closed | 2026-02-16 | 1 | secrets.yaml sungrow_modbus_battery_max_power: default values to high | D |
| [#678](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/678) | open | 2026-02-16 | 34 | pymodbus returned isError True | A |
| [#677](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/677) | closed | 2026-02-10 | 29 | Scenes not working - max export power, and battery control. | B |
| [#674](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/674) | closed | 2026-02-08 | 13 | Several ModBus Errors: "No response received after 3 retries, continue with next request" with different registers | A |
| [#673](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/673) | closed | 2026-02-07 | 10 | Modbus Error: "No response received" and "extra data" on SH5.0RT-V112 (Internal LAN) with 2026-02-06 version | A |
| [#667](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/667) | closed | 2026-02-03 | 2 | sbr_modbus_slave is not defined in secrets.yaml | K |
| [#666](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/666) | closed | 2026-02-01 | 40 | Export Power Limit problems | B |
| [#664](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/664) | closed | 2026-01-30 | 5 | Updates to HA are no faster than 5 min interval | A |
| [#663](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/663) | closed | 2026-01-26 | 2 | undefined alias sg_hub_name | K |
| [#662](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/662) | closed | 2026-01-25 | 5 | Sungrow SG6.0RS many unavailable entities | J |
| [#660](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/660) | closed | 2026-01-19 | 15 | After some Times, connection error to the inverter | A |
| [#656](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/656) | closed | 2026-01-13 | 3 | All Sensors unavailable after Home Assistant 2026.1.0 Update | E |
| [#655](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/655) | closed | 2026-01-13 | 10 | excessive amount of errors and sensor unavailable | A |
| [#654](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/654) | closed | 2026-01-11 | 31 | Battery max charge/discharge and battery charging/discharging start power not working + other unavailable sensors | D |
