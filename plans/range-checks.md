# T010 - Range checks: which bound is measured, and which is a judgement

**Range checks: which bound is measured, and which is a judgement.** A
write entity's bound is the only guard there is, because the inverter does
not enforce its own: mkaiser's P020 stored five battery-power settings
above their maximum, and at gerd's a **33 A** write was taken on a 32 A
wallbox (P022). Where each bound comes from today:
- **Derived from the device.** Battery max charge power, max discharge
 power and the forced charge/discharge power all take their ceiling from
 `battery.ceiling` -- the lower of the inverter's BDC rated power (5628)
 and the pack's own limit, which is the owner's configured value, else
 the datasheet figure for the capacity the pack reports, else the BMS's
 maximum charging current times the pack voltage. The feed-in limit takes
 its maximum and minimum from the inverter's own registers. This is what
 the YAML package could not do: its slider's maximum was a number the
 owner typed into `secrets.yaml`.
- **Measured.** The grid import limit, 10 W to 50 kW, because 32998 takes
 1-5000 counts and refuses 5001 on P020, P022 and P023. The wallbox
 current's 6 A floor, because 5 A was refused at gerd's.
- **A judgement, and labelled as one.** The battery charge and discharge
 start thresholds' 1000 W, which the YAML's author called a guess and
 asked to be told about. What would settle it: set a threshold above a
 battery's maximum charging power and watch charging never start, which
 is the behaviour the comment already predicts.

**Measured 2026-11-17** at the maintainer's SH10RT (P020, battery ~22 %,
auto repeat's own run 3; wiki: which write bounds the inverter enforces).
Each upper-bound check wrote one value just above the maximum we offer and
read the register back raw over the cable:

| Control | Maximum | Written | Stored | |
| --- | --- | --- | --- | --- |
| `battery_max_soc` | 100 % | 101 % | -- | **refused**, exception 0x04 |
| `battery_max_charge_power` | 7274 W | 7374 W | 7374 W | not enforced |
| `battery_max_discharge_power` | 7274 W | 7374 W | 7374 W | not enforced |
| `battery_forced_charge_discharge_power` | 7274 W | 7374 W | 7370 W | not enforced (see below) |
| `battery_charging_start_power` | 1000 W | 1010 W | 1010 W | not enforced |
| `battery_discharging_start_power` | 1000 W | 1010 W | 1010 W | not enforced |

**Only the SoC bound is the device's.** Every battery power bound is ours,
so the entity's maximum really is the only guard -- the premise of this
whole item, now measured rather than inferred from five stored settings.
- **Not derived, though the device states it.** The wallbox's user-defined
 current is capped at a flat 32 A, the largest Sungrow wallbox's rating,
 while a wallbox reports its own at 21263 -- **16.0 A** on the AC011E-01
 read on 2026-11-16. On that wallbox the slider offers twice what the
 hardware takes, and the inverter will not refuse it. Bound it per device
 from the reading where there is one, keeping 32 A only where nothing
 reports a rating. The wallbox's own entry has 21263; an inverter entry
 that manages a wallbox needs to reach the same figure.
