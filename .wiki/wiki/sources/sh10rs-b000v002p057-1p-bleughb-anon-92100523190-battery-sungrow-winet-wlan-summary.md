---
type: source
title: sh10rs-b000v002p057-1p-bleughb-anon-92100523190-battery-sungrow-winet-wlan.json
source_path: ../device-survey/results/inverter/sh10rs-b000v002p057-1p-bleughb-anon-92100523190-battery-sungrow-winet-wlan.json
ingested: '2026-11-02'
created: '2026-11-02'
tags:
  - survey
  - sh10rs
  - sunstone-h-b000-v002-p057
  - bleughb
  - winet_wlan
  - control-test
---

# SH10RS, B000.V002.P057, bleughb, a WiNet-S on WiFi, with a control test

Capability survey of one inverter, read 2026-11-02 in the evening from Home Assistant on
0.1.0a24, issue #789, with the control test. **Taken from a diagnostics download**: the owner
attached the integration's diagnostics, whose `survey` section is the publishable survey
(`custom_components/sungrow_modbus/diagnostics.py`); that section is committed as it was
written, under the name the library derives for it (`survey_document.label_for`). A diagnostics
download carries no register dump and runs no block read test, so this document has neither.
Source: `device-survey/results/inverter/sh10rs-b000v002p057-1p-bleughb-anon-92100523190-battery-sungrow-winet-wlan.json`.

| | |
| --- | --- |
| Installation | [bleughb](../entities/installation-bleughb.md) |
| Model | [SH10RS](../entities/device-sh-rs.md), type code `0x0D1B` |
| Stand-in serial | `anon-92100523190` |
| Inverter firmware | [`SUNSTONE-H_B000.V002.P057`](../entities/firmware-sunstone-h-b000-v002-p057.md) |
| ARM firmware | `ARM_SUNSTONE-H_V11_V01_A` |
| DSP firmware | `MDSP_SUNSTONE-H_V11_V01_A` |
| Battery firmware | `SBHBCU-S_22011.04.07` |
| Communication module firmware | `WINET-SV300.001.03.P021` |
| Version strings | `SUNSTONE-H_01011.02.57`, `SUNSTONE-H_03021.01.10` |
| Transport (owner) | a WiNet-S on WiFi |
| Transport (measured) | through a communication module (WiNet-S, WiNet-S2 or Logger); register 6100 refused |
| Battery | [SBH250](../entities/device-sbh-battery.md) (unit 2), 22 % SoC |

> I actually have TWO SG5.0RS and an AC coupled, no PV connected single SH10.RS with SBH250

AC-coupled: no PV is connected to this inverter; the two SG5.0RS string inverters make the PV.

## What did not answer

The meter phase registers 5741 and 5744 were refused, as through every
[WiNet-S](../entities/device-winet-s.md); 13018 reads unavailable. Through the dongle the SBH's
cells and modules are refused with `IllegalDataAddressError`; the summary block answers.
[31211](../entities/register-31211.md) reads 0x55 (from `readings`, there being no dump).

## Contention

Polled by this Home Assistant throughout (22 components, not paused), and an energy meter polls
too, by the owner's note. See [contention](../concepts/contention.md).

## Control test

Outcome **3**: ran, with checks skipped. Through a WiNet-S, so only the behavioural leg is
evidence. See [the control test](../concepts/control-test.md).

| Field | Register | Verdict (as the dongle reported it) |
| --- | --- | --- |
| `battery_min_soc` | 13059 | matched |
| `battery_max_soc` | 13058 | matched |
| `battery_reserved_soc_for_backup` | 13100 | matched |
| `battery_max_charge_power` | 33047 | matched |
| `battery_max_discharge_power` | 33048 | matched |
| `export_power_limit` | 13074 | refused with an exception |
| `battery_forced_charge_discharge_power` | 13052 | matched |

- [13074](../entities/register-13074.md) write scale: **stored as handed**, by the probe's
  acceptance: the held 10000 W written back was accepted, where ten times it (100000 W) is above
  the 20000 W maximum. An acceptance survives a dongle's stale readback. The same answer as on
  [P065](../entities/firmware-sunstone-h-b000-v002-p065.md). The readback's own write was then
  refused with an exception, which through a polled dongle is not evidence.
- Behaviour, PV 0 W, SoC 18.6 %: the forced charge (-516.5, 1280, 1280 W) and the forced
  discharge (-1280, 125, 137 W) both moved, but **could not be told**: the house changed by
  1796 W and 1417 W across the measurement, as a house with two other inverters can.
- **A restart**: stopped 4.0 s after the command, running 291.3 s after the start command; no PV
  to generate. Settings survived.
- Not checked: the charge ceiling (battery low), the export limit (no export to cap), the PV cut
  (no PV), the charge window (the inverter's clock did not read), the discharge window (137 W);
  33149/33150 (`battery_start_power` did not answer).
- Restore: every register back and read back.
