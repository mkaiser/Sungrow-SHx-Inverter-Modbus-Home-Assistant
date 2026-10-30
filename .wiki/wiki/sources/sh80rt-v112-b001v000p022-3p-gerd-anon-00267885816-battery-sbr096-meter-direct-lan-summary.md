---
type: source
title: sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan.json
source_path: ../device-survey/results/inverter/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan.json
ingested: '2026-10-29'
created: '2026-10-29'
tags:
  - survey
  - sh8-0rt-v112
  - sapphire-h-b001-v000-p022
  - gerd
  - direct_lan
  - control-test
  - export-scale
---

# SH8.0RT-V112, B001.V000.P022, gerd, the inverter's own LAN port

Capability survey of one inverter, read 2026-10-13. Source: `device-survey/results/inverter/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan.json`.

| | |
| --- | --- |
| Installation | [gerd](../entities/installation-gerd.md) |
| Model | [SH8.0RT-V112](../entities/device-sh-rt.md), type code `0x0E0E` |
| Stand-in serial | `anon-00267885816` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P022`](../entities/firmware-sapphire-h-b001-v000-p022.md) |
| ARM firmware | `ARM_SAPPHIRE-H_V11_V01_B` |
| DSP firmware | `MDSP_SAPPHIRE-H_V11_V01_B` |
| Battery firmware | `SBRBCU-S_22011.01.30` |
| Communication module firmware | `WINET-SV200.001.00.P043` |
| Version strings | `SAPPHIRE-H_01011.95.13`, `SAPPHIRE-H_03011.95.13` |
| Transport (owner) | the inverter's own LAN port |
| Transport (measured) | direct to the inverter's LAN port, with a communication module fitted as well but not in the path; register 6100 answered |
| Battery | [SBR096](../entities/device-sbr-battery.md) |

> Read by the maintainer over a VPN on 2026-10-13 with Home Assistant stopped and nothing else polling, and no Modbus proxy in the path. The owner reports the wiring: a LAN cable directly into the inverter, the WiNet-S on WLAN, and the wallbox on a LAN cable of its own. This is the inverter's own LAN port.

## What did not answer

Every component answered.

## Export write scale

Register 13074 multiplies a written word by ten: `write_units_per_count` = **10**, probed at a held 8000 W. See [register 13074](../entities/register-13074.md).

## Control test

Run 2026-10-30 in daylight, over the cable, with the PV cut, feed-in limitation and the restart allowed. Outcome **0**: every planned check ran and every readback matched. See [the control test](../concepts/control-test.md).

| Field | Register | Verdict |
| --- | --- | --- |
| `battery_min_soc` | 13059 | matched |
| `battery_max_soc` | 13058 | matched |
| `battery_reserved_soc_for_backup` | 13100 | matched |
| `battery_max_charge_power` | 33047 | matched |
| `battery_max_discharge_power` | 33048 | matched |
| `export_power_limit` | 13074 | matched |
| `battery_forced_charge_discharge_power` | 13052 | matched |
| `battery_charging_start_power` | 33149 | matched |
| `battery_discharging_start_power` | 33150 | matched |

- Behaviour, forced charge: **the inverter did as it was told** (1250 W commanded, 1250 W measured).
- Behaviour, forced discharge: **the inverter did as it was told** (1250 W commanded, 1249 W measured).
- Behaviour, PV generation cut: **the inverter did as it was told** -- DC power 2938 W, 0 W, 1913 W, judged by its bracket. See [register 31211](../entities/register-31211.md).
- Not established: the charge ceiling (the battery, at 52 %, was too low to put a ceiling under it, since `battery_max_soc` cannot go below 50 %) and the export limit (the battery could not make the house export).
- Restart: stopped after 2 s, running after 181 s; the inverter did as it was told.
- Restore: every register back and read back.
