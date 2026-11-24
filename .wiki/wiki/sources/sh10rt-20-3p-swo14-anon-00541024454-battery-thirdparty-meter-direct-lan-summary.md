---
type: source
title: sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan.json
source_path: ../device-diagnosis/results/inverter/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan.json
ingested: '2026-11-18'
created: '2026-11-18'
tags:
  - diagnosis
  - sh10rt-20
  - sapphire-h-01011-95-03
  - swo14
  - direct_lan
  - proxy
  - capability-test
  - third-party-battery
---

# SH10RT-20 on 01011.95.03, swo14's host inverter, a BYD pack, through a Modbus proxy

Read 2026-11-17 at 13:20 UTC from a Home Assistant diagnostics download on integration 0.1.0a43
(`command_line`: "home assistant diagnostics", schema 28), carrying two capability tests run that
day at 11:59 and 13:19 UTC, with the inverter restart left out. The **host (master) of a
two-inverter cluster**; the [slave](sh10rt-20-3p-sw14-anon-25617150722-battery-none-direct-lan-summary.md)
was read separately. Posted to issue #786. Source:
`device-diagnosis/results/inverter/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan.json`.

| | |
| --- | --- |
| Installation | [swo14](../entities/installation-swo14.md) |
| Model | [SH10RT-20](../entities/device-sh-rt.md), type code `0x0E13`, three phase 3P4L |
| Stand-in serial | `anon-00541024454` |
| Inverter firmware | **not read**: the 13250 block is refused on this firmware |
| ARM / DSP firmware | `ARM_SAPPHIRE-H_V11_V01_B` / `MDSP_SAPPHIRE-H_V11_V01_B` |
| Version 1 / 2 | [`SAPPHIRE-H_01011.95.03`](../entities/firmware-sapphire-h-01011-95-03.md) / `SAPPHIRE-H_03011.95.03` |
| Communication module | none read; a WiNet-S is fitted, heard over mDNS a week later ([the reading](sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-3-summary.md)) |
| Transport (owner) | the inverter's own LAN port, through a Modbus proxy |
| Transport (measured) | direct to the inverter's LAN port; register 6100 **answered** |
| Battery | **third party: a BYD HVM 11 kWh**, 11.1 kWh reported, 202.5 V, SoH 97 % |
| Meter | 5741 and 5744 answer |
| At the time | 268 W of PV, 4303 W of load, SoC 3.3 %, an EV charging |

## The second cluster, and 6100 through a proxy

This is the **second master/slave cluster** in the corpus, after
[fwitten](../entities/installation-fwitten.md)'s, and it keeps both rules the config flow relies
on: the slave's own unit id is **2** (the host's is 1), and the slave answers **0** where a lone
inverter answers 0xFFFF for hardware it lacks
([zero means absent](../concepts/zero-means-absent.md)). Here each inverter is reached on a port
of its own through a Modbus proxy -- the host on 502, the slave on 503 -- so the unit ids are the
proxy's as well as the inverters'.

Both entries read [register 6100](../entities/register-6100.md) **through that proxy**, and the
verdict is "direct to the inverter's LAN port". That is two more readings on the "for it" side of
[does a Modbus proxy carry register 6100](../queries/does-a-modbus-proxy-carry-6100.md), and
unlike mkaiser's they are the entry's own polling connection rather than a short probe of its own.

## 13074 stores a written word as handed, on an SH10RT-20

The first run's probe wrote back the held 10000 W -- a no-op if stored as handed, 100000 W and out
of range if multiplied -- and it was **accepted**. So [13074](../entities/register-13074.md) is
1:1 here. The capability test lifted feed-in limitation for that one write, which it is allowed to
do only because the limit already held the inverter's 10000 W maximum and capping at the maximum
caps nothing, and put the mode straight back to the 0x55 it found.

That is the second installation on `01011.95.03`, and the first that is not an SH10RT-V112:
the 1:1 behaviour follows the firmware, not the model. The second run, with the established checks
skipped, did not lift the mode and reported the scale "not determined" -- the ordinary answer at a
house whose feed-in limitation is off.

## What this firmware does not have

- **The 13250 firmware block is refused with an exception**, where fwitten's pair on the same
  version **closed the connection** on it. Same conclusion, different refusal; a proxy in the path
  may well turn one into the other. `ABSENT_ON_FIRMWARE` already gates `FIRMWARE_VERSIONS` and
  `METER_CHANNEL_2` off on `01011.95.03`, and this is the second installation to show why.
- **[31211](../entities/register-31211.md) does not answer**: no PV cut, as at fwitten.
- **13017 does not answer**: no forced startup.
- MPPT3 and MPPT4 are unavailable; two trackers.

## The site import limit did nothing here

[Register 32998](../entities/register-32998.md) reads 20.00 kW, the SH-RT's usual value, and the
check ran: under a forced charge the house drew 1030 W from the grid, a cap of **520 W** left
import at 992 W, and 1020.5 W after. **Nothing moved.** Every SH-RT that obeyed was on P020, P022
or P023; this is the first measured on the older `.95.03`, and the first where the cap did not
hold. The battery was at 3.3 % against a 10 % floor, so there was little the inverter could do
except cut a charge, which is what the check expects it to do.

The integration offers the control on P020, P022 and P023 only
([firmware gating](../concepts/firmware-gating.md)), so this costs nobody a working slider -- it
is the gate being right.

## The capability test (outcome 3, twice)

Two runs, the restart not asked for; nothing is left changed and nothing contradicts an earlier
run.

- **Seven of nine readbacks matched**, and two were not run: `battery_min_soc` and
  `battery_reserved_soc_for_backup`, because at 3.3 % every admissible value was too close to the
  battery's real level to be safe.
- **Forced charge 1249 W against 1250 W commanded.** The **forced-charging window** did as it was
  told as well, from 0 W to 5911.5 W of charge.
- **EMS mode options 2, 3 and 4 were all taken.**
- **Write paths**: backup mode (13075), load control (13011, 13002), the weekend discharge enable
  (33179) and the second forced-charging window each took their own words.
- **Upper bounds**: 13058 refuses 101 % with exception 0x04, and 33047, 33048, 13052, 33149 and
  33150 all **store a value above their maximum** (10100 W over 10000 W, 1010 W over 1000 W) -- as
  at [peter-sm](../entities/installation-peter-sm.md) on P023, so the unenforced bounds are not a
  B001 habit.
- **The site import limit's range words**: 0 and 5001 both refused with exception 0x04, 5000
  taken -- exactly [mkaiser](../entities/installation-mkaiser.md)'s answer, on firmware five
  versions older.
- **The charging start threshold did nothing measurable**: a 1000 W threshold left the charge
  running at 216 W, where it had been 252 W. The discharge-window check could not tell -- the
  input drifted across the measurement.
- Not measured: the forced discharge and the charge ceiling (the battery is at its floor), the
  export limit's effect (nothing to export with, at 3.3 % against a 10 % floor), and the
  discharging start threshold.
- **Restore**: five registers of the forced-charging window written back, each read back on the
  first attempt, and 85 across the two runs already at their original word.
