# What the diagnosis can test, capability by capability

Every capability the integration knows (`sungrow_modbus.hybrid_inverter.capabilities.Capability`),
and every control it creates. For each one:

- **Gates**: what the capability or control turns on in the integration.
- **Decided by**: how the integration decides that this inverter has it.
- **Read-only diagnosis**: what a read-only diagnosis establishes.
- **Capability test today**: what *Diagnosis with capability tests* does, and how.
- **Could still test**: what a test could still settle, and how.

Two kinds of evidence settle a write; [the capability test](../.wiki/wiki/concepts/capability-test.md)
has the whole procedure:

- A **readback** (leg B): the raw word against the specification's scale. It is evidence
  over a cable only, because a WiNet-S answers a written register stale.
- A **watched effect** (leg C): what the inverter did. It holds through any link.

A refusal is the device answering, through any link. Two more kinds settle what neither of
those can:

- A **write path** (`capability_test/writepath.py`): a control written with its own word, or,
  for the numbers, a step above the maximum. Taken, refused or clamped is the answer; nothing in
  the house changes for longer than one write.
- A **plausibility check** (`capability_test/plausibility.py`): readings checked against each
  other every minute while *Extended test (auto repeat)* runs, for days. It writes nothing, and
  is how a sensor's scale is tested: a power that is not its voltage times its current, a daily
  counter that does not rise by what its power integrated to. Listed at the end.

The per-firmware results are in [firmware_support.md](firmware_support.md): the *Survey* column
says what the diagnosis reaches, and *What the capability test measured* says what it found. Each
diagnosis document carries its own `features` section ([reference](../device-diagnosis/reference.md)).

## Capabilities that only gate readings

Nothing here can be written, so a read is the whole test.

| Capability | Gates | Decided by | Read-only diagnosis | Could still test |
| --- | --- | --- | --- | --- |
| `mppt3`, `mppt4` | the third and fourth tracker's sensors | the tracker's voltage; `0xFFFF` is absent, 0 cannot tell | reads it, and the raw dump | the plausibility check *mppt3 carries a string* settles it in daylight, from the tracker's current and not its voltage alone; nothing further |
| `three_phase` | phase B and C | the device type and output type (5002) | reads both | nothing further |
| `meter_direct` | the meter block | the block answers | reads it; a WiNet-S refuses it | nothing further |
| `meter_channel_2` | 13200-13207 | the second channel answers | reads it | nothing further |
| `meter_phase_measurements` | 5741-5746 | the registers answer, over a cable | reads them; a dongle answers 0 | nothing further |
| `sungrow_battery` | the pack's own unit, and the datasheet's write bounds | the pack answers on unit 200 (cable) or 2 (dongle), and 5639 names an SBR | reads the pack | an SBH over a cable, to grant it there too |
| `firmware_versions`, `sub_controller_firmware`, `battery_firmware` | the firmware strings | the strings answer; 2613 and 2629 arrive padded | reads them; the block read test names the count | nothing further |
| `energy_history` | monthly and yearly totals, 6227-6637 | a monthly PV value is not zero | reads them over a cable; no dongle forwards them | nothing further |
| `pv_power_limitation` | 13018, SH-T only | the register answers | reads it | write it with a watched PV limit: not a control yet, so first the readback and the watched effect on an SH-T |
| `active_power_limit` | 13089-13090 (state and ratio) | the registers answer | reads them | the ratio is read-only here; a watched write would make it a control, in daylight with export |
| `feed_in_limitation_ratio` | 13088 | the register answers | reads it; the export check records it before and during its limit (`conditions.feed_in_ratio`) | a rule relating it to 13074, once runs on several firmwares have recorded it |

## Capabilities that gate controls

| Capability | Controls | Read-only diagnosis | Capability test today, and how | Could still test |
| --- | --- | --- | --- | --- |
| `battery` | min, max and backup SoC; max charge and discharge power; forced charge/discharge, its power and the EMS mode | reads every one | **leg B**: each is written at a value that shows a decade either way, read back by raw word, two points where the range allows. **Leg C**: forced charge, forced discharge (the power is watched), the charge ceiling (max SoC under the battery), the site import limit; with auto repeat, each once by day and once by night. **Write path**: *upper bound of* each number but the backup reserve, a step above its maximum (the min SoC only under a battery above 57 %) | nothing missing |
| `battery_start_power` | charge and discharge start thresholds | reads them | **leg B** readback; **leg C**, *charging / discharging start threshold*: with the battery moving 200 to 800 W, all of it through the battery, the threshold set to its 1000 W maximum and the flow watched to stop | nothing missing |
| `forced_charging` | the forced-charging schedule: switch, days, two windows, two targets | reads them | **leg C**, *forced-charging window*: window 1 around the inverter's clock, a target a few percent up, watched until the battery charges, then put back; not written where the pack has no room under its ceiling. **Write path**, *forced-charging window 2 encoding*: window 2, its target and the days written elsewhere and read back, only with the schedule off and over a cable, with the same leave | nothing missing |
| `discharge_schedule` → `discharge_schedule_control` | the four windows, as a `time` per edge with an *all day* switch, and the weekend enable | reads them | **leg C**, *discharge windows away from now*: both days' windows moved off the clock, watched until the battery stops. **Write path**: the weekend enable (33179) written with its own word, with the same leave | nothing missing |
| `pv_generation_cut` → `pv_generation_cut_control` | *Cut PV generation* (31211) | reads 31211 | **leg C**, *PV generation cut*: 0xAA cuts PV, watched to zero, given 500 W of PV. The control is granted only on firmware where a watched cut is on record (`CONFIRMED_ON_FIRMWARE`) | every firmware not yet on record: the same check in daylight |
| `forced_startup` → `forced_startup_control` | *Low-SoC standby* (13017; off is 0xAA) | reads 13017 | **leg C**, `diagnosis.sh tests <host> --forced-startup`, a mode of its own: only in low-SoC standby (battery within 5 % of its minimum, no PV). It writes 0xAA and watches Starting and Running, writes 0x55 and watches Standby, then restores; the factory 0 goes back as 0x55. The control is granted per watched firmware | not on a button, because the button refuses a sleeping inverter. In Home Assistant **auto repeat runs it by itself** when it finds the inverter in low-SoC standby and no kept run has established it (a slot of its own, no option: it writes 0x55 back), and the `run_capability_test` action with `forced_startup: true` runs it on demand. Watched on P020, P022 and P023 |

## Controls no capability gates

| Control | Register | Read-only diagnosis | Capability test today, and how | Could still test |
| --- | --- | --- | --- | --- |
| Feed-in limit and its mode | 13074, 13087 | reads them | **leg B** readback at the factor this firmware writes; **leg C**, *export power limit*: the mode switched on, export capped and watched; and `--export-scale`, one write each firmware refuses or accepts, so it holds through a dongle (×10 on B001, 1:1 on 01011.95.03) | nothing missing |
| Site import limit | 32998 (a number on P020, P022 and P023; a sensor elsewhere) | reads it | **leg C**, *site import limit*: capped during a forced charge, watched as grid import comes down | the cap on more firmware |
| EMS mode | 13050 | reads it | written to forced mode (2) by the forced checks and put back; **write path**, *EMS mode options*: each of 0, 2, 3 and 4 once, the snapshot's word straight after each, refusals named | nothing missing |
| Backup mode | 13075 | reads it | **write path**: its own word written back | nothing missing |
| Load control and its mode | 13011, 13002 | reads them | **write path**: their own words written back; switching a real load is not something to test | nothing missing |
| Stop and start | 13000 (actions, not entities) | reads the running state | the **restart**: stop, then start, timed until Running, with the settings checked after | nothing missing |

## The wallbox

The output current's scale (holding 21203) is **0.1 A per count**, settled on 2026-11-14 by a
car following it at gerd's. `sungrow_wallbox_capability_test.py` tests a wallbox's own registers at
its own address over TLS: a dry run without `--leave`, and **with it only on a wallbox declared
`--standalone`**. A wallbox a hybrid inverter manages (its EV charger in iSolarCloud) has its
current driven by the inverter, which overwrites a write within seconds; it is controlled at the
inverter instead (`src/sungrow_modbus/hybrid_inverter/ev_charger.py`). The test also refuses a
setting that moves with nothing written, never disables the charge point and never offers under
6 A. From Home Assistant the same answer is the entry's own option, *No inverter manages
this wallbox* in **Configure**, off until it is switched on: the integration shows what it makes
of the wallbox's behaviour but never writes on its own reading
(`src/sungrow_modbus/wallbox/management.py`, below). Its document is separate from the inverter's
feature report.

**Who drives a wallbox is inferred, and shown, but never acted on.** An inverter that manages a
charge rewrites the wallbox's output current every few seconds, so a setting that moves during a
charge with nothing here writing it says *managed*, and one that holds still through a charge
suggests *standalone*; an idle wallbox says nothing, however long it is watched. The answer is the
`management` attribute of *Diagnosis: test summary* on the wallbox's device page, with the counts
behind it. It decides what is shown and what the summary says it awaits -- **what may be written
is the owner's answer alone**, because a wrong *standalone* writes registers an inverter
overwrites within seconds.

A **managed** wallbox has a test of its own, `sungrow_managed_wallbox_test.py`
(`src/sungrow_modbus/wallbox/managed_test.py`): it writes only the inverter's EV charger block
and reads the wallbox for what the car does. With a car charging it switches to user-defined mode,
offers 6, 8 and 10 A (never above the cap or the rating) and times the car following each, offers
5 A for the inverter to refuse, and with `--start-stop` stops the charge for 15 s and starts it.
The restore puts the house back: the user current while still in user-defined mode, then the mode,
then charging on, and it waits for the car to charge again; a car that does not is exit 5, with
what to do on site. In Home Assistant it runs from the wallbox's own entry, in the extended
modes with the owner's leave, wherever an inverter entry here left the wallbox to it: it writes
through that inverter entry's connection and holds both entries' polling off. A wallbox with no
such inverter entry awaits no check at all, so auto repeat does not wait for a run that could not
write.

**A run that cannot put everything back** (either test), or a snapshot found when the entry
starts, raises a Repairs issue that names each setting, the value it should have and where the app
sets it; an error where the wallbox may be left disabled or the charge switched. The fix writes it
back and checks the house, not only the word: a standalone wallbox whose enable was touched must
not report status 8 (*disabled*), and the managed test waits for the charge
(`custom_components/sungrow_modbus/repairs.py`). The mileage check is gone: its one run on
hardware left the app's *Fahrstrecke pro kWh* wrong.

## The controls during a run

A run and the owner's controls never write at the same time
(`custom_components/sungrow_modbus/write_owner.py`):

- **While a run writes, the controls refuse.** From just before part B's snapshot until its
  restore is checked, every control of that entry (numbers, switches, selects, times, buttons,
  the feed-in limit and the start and stop actions) refuses before anything is sent, with an
  error naming the run and since when. A wallbox run that writes an inverter's EV charger block
  holds that inverter entry's controls too. The read-only part A holds nothing.
- **They stay available.** Home Assistant silently drops a call to an unavailable entity, so an
  automation would believe it had written. Instead it gets the error, and can catch it with
  `continue_on_error`. *Diagnosis: controls held by test* is on for the duration, naming the run
  in `held_by`; a dashboard can hide the controls behind it.
- **Auto repeat waits after the owner wrote**: 10 minutes after a change to any control, before
  an inverter run, and an hour after a change to the wallbox's charging, before a wallbox run.
  *Diagnosis: current step* says until when. A run started by hand does not wait.
- **The owner's value beats a leftover snapshot.** A run that did not finish leaves its
  snapshot, and its repair (or, for a wallbox, the next run) writes it back. A control the owner
  set since then is taken out of it: the inverter's snapshot drops that setting, and a managed
  wallbox's keeps the owner's word instead, the charge left off if the owner switched it off.
- **What cannot be held**: a write that does not go through these entities, such as
  `modbus.write_register` or another program on a connection of its own. Leave those off while
  auto repeat runs.

## Readings checked against each other

Read only, every minute between runs while *Extended test (auto repeat)* is on; the rows count
in the diagnosis's test counters, and auto repeat stays on until each has an answer. A check
reaches a verdict only from the moments that meet its need. A median off by a clean decade is a
finding; a ratio merely off (losses, reactive power) is *could not tell*, never a failure.

| Check | Relation | Needs | Catches |
| --- | --- | --- | --- |
| power balance | load = PV + battery − export | a 500 W load | a scale or sign in any of the four |
| battery voltage times current | V × I = battery power | 300 W through the battery | a decade in 13020, 5631 or 5214 |
| tracker voltage times current | Σ MPPT V × I = DC power | 300 W of PV | a decade in the tracker registers |
| phase voltage times current | Σ phase V × \|I\| ≈ active power | 1000 W out | a decade in the phase registers |
| meter phases add up | Σ phase power = meter total | 300 W through the meter | a phase register's scale or sign |
| meter against export power | \|5601\| = \|13010\| | 300 W through the meter | one of the two a decade off |
| *daily counter* against power | the counter's rise = ∫ power dt, a kWh at a time | three kWh of flow | a daily energy register a decade off |
| *total* against *daily counter* | the lifetime counter rises with the daily one, 2 kWh at a time | 2 kWh on the daily counter | a lifetime register a decade off |
| lifetime counters never fall | — | a day of polls | a wrong register or word order |
| lifetime battery counters contain each other | charge ≥ charge from PV, and ≥ discharge | 100 kWh through the battery | a broken word in a lifetime counter |
| daily counters reset at midnight | a fall only between 23:30 and 00:30 **of the inverter's clock**, to under 0.5 kWh | a midnight | a counter that is not daily |
| daily counters keep up with the totals | each daily counter moves while its lifetime counter rises; a total rising 1 kWh with its daily counter unmoved names it | 100 moves | a daily counter stuck at 0, as #797's daily import through a night on the grid (T072) |
| battery level follows its power | 1 kWh out lowers the level, 1 kWh in raises it | 1 kWh through the battery | a level read from the wrong register |
| running states | every 13000 code seen is in the table | a day of polls | a code nobody has named |
| mppt3 / mppt4 carries a string | a voltage **and** current in daylight; the voltage alone only where the model reports no tracker current | PV above 1000 W | a tracker granted with nothing on it, which an unloaded input's drift above 50 V looks like |

**The midnight check also measures the reset itself.** Its sentence names every daily counter
that fell in the same poll, and every one that had not fallen yet, whether it passes or fails.
That is what says whether a device zeroes its counters together or over several polls -- which
decides whether a poll can land between two of them and read a day's energy from two different
days.

**The midnight check judges on the inverter's clock.** A daily counter resets on the inverter's
own midnight, and nothing requires a Home Assistant to keep its inverter's timezone: judged by
the observer's clock, an hour of difference turns a clean reset at 00:04 into a counter falling
at 23:04. Where the two clocks differ the sentence prints both readings, because a clock set
wrong is worth reporting as itself.

**The containment check needs no particular weather, and nothing to happen.** It is arithmetic
between counters read in the same block -- a battery cannot give out more than it took in, and
charging from PV is a part of charging -- so it is settled by one poll, where every other check
here waits for sun, a load or a midnight. It is what finds a lifetime counter whose high word is
wrong but whose reading still looks like a number a house could have. A 10 % margin, because
Sungrow's own counters cross each other honestly by up to about 4 %.

**The discharge windows can be written where a watched write is on record.**
They are in no Sungrow document (#785), so answering the registers says
nothing about what writing them does; moving every window away from now and
watching the battery stop does, and that is on record at two houses on
`SAPPHIRE-H_B001.V000.P020` and `SAPPHIRE-H_B001.V000.P022`. On those two the
windows become entities you can set; everywhere else they stay sensors until
the same check runs there. **A window's end carries an *all day* switch**
beside its time, because the end of the day is hour **24** and a Home
Assistant time entity holds 23:59 at most: with the switch on the end reads
24:00 and the time shows nothing, and turning it off writes 23:59 for you to
correct.

**The tracker check reads a voltage, not a string.** It grants the tracker at 50 V in daylight,
and an unloaded input can drift past that: on an SH10RS `mppt4` reads 39.5 V to 53.6 V at 0.0 A
while the three live trackers account for the whole of `total_dc_power`. So a *matched* verdict
on `mppt3` or `mppt4` says the input answers a voltage, and the tracker's current says whether
anything is on it.
