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
| `mppt3`, `mppt4` | the third and fourth tracker's sensors | the tracker's voltage; `0xFFFF` is absent, 0 cannot tell | reads it, and the raw dump | the plausibility check *mppt3 carries a string* settles it in daylight; nothing further |
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
| `discharge_schedule` | weekday and weekend discharge windows (sensors so far) | reads them | **leg C**, *discharge windows away from now*: both days' windows moved off the clock, watched until the battery stops. **Write path**: the weekend enable (33179) written with its own word, with the same leave | nothing missing |
| `pv_generation_cut` → `pv_generation_cut_control` | *Cut PV generation* (31211) | reads 31211 | **leg C**, *PV generation cut*: 0xAA cuts PV, watched to zero, given 500 W of PV. The control is granted only on firmware where a watched cut is on record (`CONFIRMED_ON_FIRMWARE`) | every firmware not yet on record: the same check in daylight |
| `forced_startup` → `forced_startup_control` | *Forced startup under low SoC* (13017) | reads 13017 | **leg C**, `diagnosis.sh tests <host> --forced-startup`, a mode of its own: only in low-SoC standby (battery within 5 % of its minimum, no PV). It writes 0xAA and watches Starting and Running, writes 0x55 and watches Standby, then restores; the factory 0 goes back as 0x55. The control is granted per watched firmware | not on a button, because the button refuses a sleeping inverter: in Home Assistant it is the `run_capability_test` action with `forced_startup: true`. No run on hardware is on record yet |

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

The output current's scale (holding 21203, 0.1 A or 0.01 A per count) is measured by
`sungrow_wallbox_capability_test.py`, at the wallbox's own address over TLS. It is a dry run
without `--leave`; with it, the current is stepped to 6, 8 and 10 A. Enable, phase switching and
start/stop are optional flags. Its document is separate and does not appear in the inverter's
feature report yet. Folding it in is the next step.

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
| daily counters reset at midnight | a fall only between 23:30 and 00:30, to under 0.5 kWh | a midnight | the inverter's clock, or a counter that is not daily |
| battery level follows its power | 1 kWh out lowers the level, 1 kWh in raises it | 1 kWh through the battery | a level read from the wrong register |
| running states | every 13000 code seen is in the table | a day of polls | a code nobody has named |
| mppt3 / mppt4 carries a string | a voltage in daylight | PV above 1000 W | a tracker granted with nothing on it |
