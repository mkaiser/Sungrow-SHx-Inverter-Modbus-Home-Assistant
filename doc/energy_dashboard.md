# Setting up Home Assistant's Energy dashboard

> **Not in the preview releases yet.** The preview releases set an entry up
> for diagnostics only and create no readings, so there is nothing to pick
> yet. This guide describes the ordinary setup, which comes in a later
> release. For the YAML package, see
> [legacy/doc/dashboard.md](../legacy/doc/dashboard.md).

Home Assistant's Energy dashboard (**Settings → Dashboards → Energy**, then
the pencil at the top right) asks you to pick sensors. The integration
creates more than fifty energy sensors, and several have names that look right
and are not, so this lists the ones to pick. Pick by **name**: an entity's id
starts with your device's name, which you chose.

Names are the English ones; on a German system they are German
([entity_names.md](entity_names.md) has both). Entity ids stay English.

## A hybrid inverter (SH…RT, SH…RS, SH…T)

| In the dashboard | Pick | Not |
| --- | --- | --- |
| **Grid → Grid consumption** | *Total imported energy* | *Daily imported energy* |
| **Grid → Return to grid** | *Total exported energy* | *Total exported energy from PV*, which leaves out what the battery exported |
| **Solar panels → Solar production energy** | *Total PV generation* | *Total PV generation & battery discharge*, which counts the battery's output again |
| **Home battery storage → Energy charged into the battery** | *Total battery charge energy* | *Total battery charge energy from PV*, which leaves out grid charging |
| **Home battery storage → Energy discharged from the battery** | *Total battery discharge energy* | |

The optional power sensors, which only draw the *Now* tab:

| In the dashboard | Pick |
| --- | --- |
| **Grid power** | *Meter active power* |
| **Solar production power** | *Total PV input power* |
| **Battery power** | *Battery discharging power signed* |

Leave out the *Daily …* and *… this month / this year* sensors (they reset on
their own, and the dashboard keeps its own history), the *(smoothed)* ones
(made for a card) and the *MPPTn energy* sensors (an estimate from voltage
times current, useful for comparing strings, not for the totals).

## A string inverter (SG)

An SG has no battery and, unless a meter is fitted, nothing to say about the
grid. **Solar production energy** takes *Total PV generation*; with a meter,
**Grid consumption** takes *Total imported energy* and **Return to grid**
*Total exported energy*.

## The battery

An SBR battery's own sensors (cell voltages, modules) are diagnostics. The
dashboard's battery is the inverter's: the two *Total battery …* sensors above.

## A wallbox

Under **Individual devices**, add the wallbox's *Total charged energy* (the
lifetime counter, in Wh), so the dashboard can show what the car used. It is
read only: this integration reports the wallbox, it does not control it.

## Several inverters

Add **each** inverter as its own **Solar panels** source; the dashboard adds
them up, so no sum sensor is needed, and one inverter being unreachable then
leaves a gap in its own source only. The battery, the meter and the grid
sensors come from the inverter that has them; in a master/slave pair the
slave has neither, and reads 0 for them.

For a card, the *Now* tab or the power flow you want one total power. Make it
yourself with a **Sum** helper (**Settings → Devices & services → Helpers →
Create helper → Combine the state of several sensors → Sum**) over each
inverter's *Total PV input power*. Do not make a sum of the energy totals for
the Energy dashboard: a sum of counters falls when one inverter is unavailable
and then jumps back, which the statistics read as negative and then
enormous generation.

The same goes for other totals of the whole house, each a Sum helper over one
sensor per inverter:

| Sum it | Take it from the master only | Never sum it |
| --- | --- | --- |
| *Total PV input power*, the *MPPTn power* sensors, *Total active power* (AC output), *Daily PV generation* (for a card) | the meter's readings, *Load power*, *Total imported energy*, *Total exported energy* | *Battery level*, any setting, any state such as the running state |

The meter and load readings belong to the inverter the meter is wired to. In a
master/slave pair the slave reads 0 for them, so a sum would come out right,
but only for that wiring.
A Sum helper is unavailable while one of its sensors is (unless you tick
*Ignore non-numeric*), which is the honest answer: a total missing an inverter
is not the house's total.

## What is not yet checked

- Whether *Total imported energy* and *Total exported energy* need a meter
  fitted: what a house without one reads is not measured.
- Whether the *Total …* energies, which keep the YAML package's state class
  so that history carries over, behave across an inverter reset or a firmware
  upgrade.

Tell us what you see at your house in
[the survey thread](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/786).
