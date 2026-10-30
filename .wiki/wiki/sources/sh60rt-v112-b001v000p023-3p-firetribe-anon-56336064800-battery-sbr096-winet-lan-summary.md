---
type: source
title: sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-winet-lan.json
source_path: ../device-survey/results/inverter/sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-winet-lan.json
ingested: '2026-10-29'
created: '2026-10-29'
tags:
  - survey
  - sh6.0rt-v112
  - sapphire-h-b001-v000-p023
  - firetribe
  - winet_lan
  - control-test
---

# SH6.0RT-V112, B001.V000.P023, firetribe, a WiNet-S on Ethernet

Capability survey of one inverter, read 2026-10-29 from Home Assistant, issue #784. Source: `device-survey/results/inverter/sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-winet-lan.json`.

| | |
| --- | --- |
| Installation | [firetribe](../entities/installation-firetribe.md) |
| Model | [SH6.0RT-V112](../entities/device-sh-rt.md), type code `0x0E0D` |
| Stand-in serial | `anon-56336064800` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| ARM firmware | `ARM_SAPPHIRE-H_V11_V01_B` |
| DSP firmware | `MDSP_SAPPHIRE-H_V11_V01_B` |
| Battery firmware | `SBRBCU-S_22011.01.30` (from the 13280 block) |
| Communication module firmware | `WINET-SV200.001.00.P044` |
| Version strings | `SAPPHIRE-H_01011.95.14`, `SAPPHIRE-H_03011.95.14` |
| Transport (owner) | a [WiNet-S](../entities/device-winet-s.md) on Ethernet |
| Transport (measured) | through a communication module; register 6100 refused |
| Battery | [SBR096](../entities/device-sbr-battery.md) (unit 2; cells and modules refused) |

## What did not answer

Refused with 0x02, every time: the sub-controller (2613) and battery (2629)
firmware blocks, which a [WiNet-S](../entities/device-winet-s.md) does not
forward; 6100; 13018; the meter phase registers 5741 and 5744. MPPT3 and MPPT4
read **present** here and unavailable on the cable: the dongle's zero, see
[zero means absent](../concepts/zero-means-absent.md).

**Intermittent**, over three rounds: the holding blocks 13002 (17), 13050 (51)
and 33149 (2) answered in some rounds and were refused with an exception in
others.

## Contention

Polled by this Home Assistant, held off for the run (14 components). The owner
reports two other clients on this WiNet-S throughout: a WARP3 wallbox and a
second Home Assistant. See [contention](../concepts/contention.md) and
[busy WiNet-S](../queries/does-a-busy-winet-s-refuse-with-0x04.md).

## Control test

Outcome **3**: ran, but checks were skipped or inconclusive. Through a
WiNet-S only leg C is evidence. See [the control test](../concepts/control-test.md).

| Field | Register | Verdict |
| --- | --- | --- |
| `battery_min_soc` | 13059 | refused, 0x04 |
| `battery_max_soc` | 13058 | refused, 0x04 |
| `battery_reserved_soc_for_backup` | 13100 | refused, 0x04 |
| `battery_max_charge_power` | 33047 | refused, 0x04 |
| `battery_max_discharge_power` | 33048 | refused, 0x04 |
| `export_power_limit` | 13074 | refused, 0x04 |
| `battery_forced_charge_discharge_power` | 13052 | refused, 0x04 |
| `battery_charging_start_power` | 33149 | refused, 0x04 |
| `battery_discharging_start_power` | 33150 | refused, 0x04 |

- Behaviour, forced charge: **the inverter did as it was told**, 1208 W for
  1250 W commanded. So writes did reach the inverter in this run.
- Behaviour, forced discharge: **could not tell** -- its power write was
  refused with 0x04.
- Export limit: not checked; feed-in limitation is off and the run had no
  leave to switch it on. The [13074](../entities/register-13074.md) write
  scale was not asked: the read of 13074 itself was refused with 0x04.
- Restore: every register back and read back.
