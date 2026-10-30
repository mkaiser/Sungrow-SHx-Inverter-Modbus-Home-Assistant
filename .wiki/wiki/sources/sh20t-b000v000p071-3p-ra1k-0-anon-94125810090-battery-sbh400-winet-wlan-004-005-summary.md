---
type: source
title: sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-004-005.json
source_path: ../device-survey/inverter/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-004-005.json
ingested: '2026-10-30'
created: '2026-10-30'
tags:
  - survey
  - sh20t
  - pearl-h-b000-v000-p071
  - ra1k-0
  - winet_wlan
  - control-test
---

# SH20T, B000.V000.P071, ra1k_0, a WiNet-S on WiFi, with a control test

Capability survey of one inverter, read 2026-10-30 from Home Assistant, issue #772, with a
control test: the first on any [SH-T](../entities/device-sh-t.md). The issue carried two files
a minute apart; this is the second, which holds the first's reading plus the control test. The
filename carries the address tail because this installation's September reading, under the same
label, came from a different one. Source: `device-survey/inverter/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-004-005.json`.

| | |
| --- | --- |
| Installation | [ra1k_0](../entities/installation-ra1k-0.md) |
| Model | [SH20T](../entities/device-sh-t.md), type code `0x0E26` |
| Stand-in serial | `anon-94125810090` |
| Inverter firmware | [`PEARL-H_B000.V000.P071`](../entities/firmware-pearl-h-b000-v000-p071.md) |
| ARM firmware | `ARM_PEARL-H_V11_V01_A` |
| DSP firmware | `MDSP_PEARL-H_V11_V01_A` |
| Battery firmware | `SBHBCU-S_22011.04.11` |
| Communication module firmware | `WINET-SV300.001.03.P032` |
| Transport (owner) | a [WiNet-S](../entities/device-winet-s.md) on WiFi |
| Transport (measured) | through a communication module; register 6100 refused |
| Battery | [SBH400](../entities/device-sbh-battery.md) (unit 2; the SBR cell and module blocks refused with 0x02) |

> iHomeManager is installed

## What did not answer

Refused with 0x02, every round: the sub-controller (2613) and battery (2629) firmware blocks,
which a WiNet-S does not forward. Every other block answered, 26 in all, none intermittent.
The meter phase registers 5741 and 5744 are refused, as through every WiNet-S in the corpus,
so this reading cannot say whether the [iHomeManager](../entities/device-ihomemanager.md)
silences them.

## Contention

Polled by this Home Assistant, held off for the run (14 components). The owner names the
[iHomeManager](../entities/device-ihomemanager.md) as another poller. Nothing in the block read
test shows it: no reconnects, nothing intermittent. See [contention](../concepts/contention.md).

## Control test

Outcome **4**: a scale finding. Through a WiNet-S only leg C is evidence, so the finding is a
lead, not a measurement. See [the control test](../concepts/control-test.md).

| Field | Register | Verdict |
| --- | --- | --- |
| `battery_min_soc` | 13059 | matched |
| `battery_max_soc` | 13058 | matched |
| `battery_reserved_soc_for_backup` | 13100 | matched |
| `battery_max_charge_power` | 33047 | matched, two points |
| `battery_max_discharge_power` | 33048 | matched, two points |
| `export_power_limit` | 13074 | two points, wrong slope |
| `battery_forced_charge_discharge_power` | 13052 | matched, two points |
| `battery_charging_start_power` | 33149 | not run, 33149 does not answer |
| `battery_discharging_start_power` | 33150 | not run, 33149 does not answer |

- [13074](../entities/register-13074.md) write scale: **not determined**. The register held
  20000 W in bounds 0-20000 W. Ten times 20000 wraps to 3392 W in sixteen bits, which a
  multiplying firmware would accept as a new limit, so the probe declined to ask.
- 13074 readback: the run fell back to dividing by ten, wrote word 60 for 600 W, and the dongle
  reported **60**, with the slope of the two points about 0.11. Feed-in limitation was **off**
  (13087 = 0x55) and stayed off. On B001 a write with the mode off changes nothing; here the
  dongle reported the handed word. Either P071 stores 13074 as handed with the mode off, or the
  dongle reports the word it forwarded. Only a cable reading, or the behavioural export check
  with the mode on, can tell which.
- Behaviour, forced discharge: **the inverter did as it was told**, 1252 W for 1250 W
  commanded. The first watched write on an SH-T: 13050-13052 act on P071.
- Forced charge, charge ceiling, export limit: not checked (SoC 100 %, not charging, and
  feed-in limitation off with no leave to switch it on).
- Restore: every register back and read back; `ems_mode_selection` needed one attempt.
