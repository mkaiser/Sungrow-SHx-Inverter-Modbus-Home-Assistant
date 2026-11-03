---
type: source
title: sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-2.json
source_path: ../device-survey/results/inverter/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-2.json
ingested: '2026-11-02'
created: '2026-11-02'
tags:
  - survey
  - sh20t
  - pearl-h-b000-v000-p071
  - ra1k-0
  - winet_wlan
  - control-test
---

# SH20T, B000.V000.P071, ra1k_0, a WiNet-S on WiFi, the PV cut confirmed

Capability survey of one inverter, read 2026-11-01 at 23:54 UTC (in daylight, PV about 20 kW)
from Home Assistant, issue #772, with the full control test including the PV cut and a restart.
The survey derives the same name as the first reading, so the file carries `-2`. Source:
`device-survey/results/inverter/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-2.json`.

| | |
| --- | --- |
| Installation | [ra1k_0](../entities/installation-ra1k-0.md) |
| Model | [SH20T](../entities/device-sh-t.md), type code `0x0E26` |
| Stand-in serial | `anon-94125810090` |
| Inverter firmware | [`PEARL-H_B000.V000.P071`](../entities/firmware-pearl-h-b000-v000-p071.md) |
| Battery firmware | `SBHBCU-S_22011.04.11` |
| Communication module firmware | `WINET-SV300.001.03.P032` |
| Transport (owner) | a WiNet-S on WiFi |
| Transport (measured) | through a communication module (WiNet-S, WiNet-S2 or Logger); register 6100 refused |
| Battery | [SBH400](../entities/device-sbh-battery.md) (unit 2), 100 % SoC |

> iHomeManager is installed

The owner names the [iHomeManager](../entities/device-ihomemanager.md) as another poller.

## What did not answer

Refused with an exception in every round: 2629 (battery firmware), 2613 (sub-controller
firmware), and the history's PV generation (6227) and export (6596) blocks, as through every
[WiNet-S](../entities/device-winet-s.md). The meter phase registers 5741 and 5744 were refused.
Through the dongle the SBH's cells and modules components are refused with
`IllegalDataAddressError`; the summary block answers.

## What the dump adds

- [31211](../entities/register-31211.md) 0x55; 13018 0x55.
- [13074](../entities/register-13074.md) holds 20000 W, feed-in limitation (13087) off (0x55).
- The forced-charging schedule is off, window 1 10:00-16:00 at 100 %. The discharge schedules:
  weekday window 1 00:00-24:00, weekend discharge on with window 1 00:00-24:00.

## Contention

Polled by this Home Assistant, held off for the run (22 components); the iHomeManager polls too.
See [contention](../concepts/contention.md).

## Control test

Outcome **4**, a scale finding, from one readback. Through a WiNet-S, so only the behavioural leg
is evidence. See [the control test](../concepts/control-test.md).

| Field | Register | Verdict (as the dongle reported it) |
| --- | --- | --- |
| `battery_min_soc` | 13059 | matched |
| `battery_max_soc` | 13058 | matched |
| `battery_reserved_soc_for_backup` | 13100 | matched |
| `battery_max_charge_power` | 33047 | matched |
| `battery_max_discharge_power` | 33048 | matched |
| `export_power_limit` | 13074 | two points, wrong slope |
| `battery_forced_charge_discharge_power` | 13052 | matched |

- **The outcome 4 is not evidence.** [13074](../entities/register-13074.md)'s write scale was not
  determined (20000 W held, no safe probe word), so 600 W was written as word 60, the fallback of
  ten; the dongle reported 60 back, where the check expected 600. With feed-in limitation off, as
  in the first control test here, the same lead again: through a dongle, the word forwarded.
- **The PV cut did as it was told**: total DC power 20421 W before, 28 W during, 20395 W after.
  The first watched cut on an SH-T and on P071. It stops all PV, as 0xAA is meant to: there is
  no load following while the cut is on.
- The forced discharge **did as it was told**: 0, 1245.5, 0 W for 1250 W (the pack clamped the
  manufactured discharge at 2710 W).
- **A restart**: stopped 2.1 s after the command, running 147.5 s after the start command,
  generating 0.1 s later; settings survived.
- Not checked: the forced charge, the charge ceiling and the charge window (battery full), the
  export limit (no export to cap), the discharge window (no discharge to stop);
  33149/33150 (`battery_start_power` did not answer).
- Restore: every register back and read back.
