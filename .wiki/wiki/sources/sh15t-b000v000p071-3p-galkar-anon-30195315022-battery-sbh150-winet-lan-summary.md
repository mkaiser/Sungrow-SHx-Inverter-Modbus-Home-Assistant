---
type: source
title: sh15t-b000v000p071-3p-galkar-anon-30195315022-battery-sbh150-winet-lan.json
source_path: ../device-survey/results/inverter/sh15t-b000v000p071-3p-galkar-anon-30195315022-battery-sbh150-winet-lan.json
ingested: '2026-10-31'
created: '2026-10-31'
tags:
  - survey
  - sh15t
  - pearl-h-b000-v000-p071
  - galkar
  - winet_lan
  - control-test
---

# SH15T, B000.V000.P071, GalKar, a WiNet-S on Ethernet, with a control test

Capability survey of one inverter, read 2026-10-31 from Home Assistant, issue #786, with a
control test. The owner sent a Home Assistant diagnostics download; this document is its `survey`
section, which carries the control test of the diagnosis run before it. Everything else in the
download (the entry, the device, the readings) is redacted or not a survey, and is not committed.
Source: `device-survey/results/inverter/sh15t-b000v000p071-3p-galkar-anon-30195315022-battery-sbh150-winet-lan.json`.

| | |
| --- | --- |
| Installation | [GalKar](../entities/installation-galkar.md) |
| Model | [SH15T](../entities/device-sh-t.md), type code `0x0E25`, three phase 3P4L |
| Stand-in serial | `anon-30195315022` |
| Inverter firmware | [`PEARL-H_B000.V000.P071`](../entities/firmware-pearl-h-b000-v000-p071.md) |
| ARM firmware | `ARM_PEARL-H_V11_V01_A` |
| DSP firmware | `MDSP_PEARL-H_V11_V01_A` |
| Battery firmware | `SBHBCU-S_22011.04.11` |
| Communication module firmware | `WINET-SV300.001.03.P033` |
| Transport (owner) | a [WiNet-S](../entities/device-winet-s.md) on Ethernet |
| Transport (measured) | through a communication module; register 6100 refused |
| Battery | [SBH](../entities/device-sbh-battery.md) (unit 2; the SBR cell and module blocks refused with 0x02) |

## What did not answer

The sub-controller (2613) and battery (2629) firmware blocks, which a WiNet-S does not forward,
and the meter phase registers 5741 and 5744, refused as through every WiNet-S in the corpus.

The diagnosis run's block read test is in the download, not in this document
([the attachment](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/786)):
2613 and 2629 refused with 0x02 every round, and **holding 13002 (17), 13050 (51), 33047 (2) and
33149 (2) answered in some rounds and were refused in others**, no reconnects. Those are the
registers a [busy WiNet-S](../queries/does-a-busy-winet-s-refuse-with-0x04.md) refused at gerd.
The owner named no other poller.

**33149 answered.** The capability table marks `battery_start_power` absent on the SH-T, and
[ra1k-0](../entities/installation-ra1k-0.md)'s control test recorded 33149 as not answering. Here a
two-word read of 33149-33150 succeeded in at least one round. Through a dongle that settles
neither way: a busy WiNet-S refuses registers that exist, and
[invents answers](../concepts/zero-means-absent.md) for some that do not. See
[P071](../entities/firmware-pearl-h-b000-v000-p071.md).

## Contention

The reading was rebuilt at download, with this Home Assistant polling throughout (16
components). See [contention](../concepts/contention.md).

## Control test

Outcome **3**: ran, with checks skipped or inconclusive. Through a WiNet-S only leg C is
evidence. See [the control test](../concepts/control-test.md).

| Field | Register | Verdict |
| --- | --- | --- |
| `battery_min_soc` | 13059 | matched (the dongle's readback) |
| `battery_max_soc` | 13058 | matched (the dongle's readback) |
| `battery_reserved_soc_for_backup` | 13100 | matched (the dongle's readback) |
| `battery_max_charge_power` | 33047 | refused with an exception |
| `battery_max_discharge_power` | 33048 | refused with an exception |
| `export_power_limit` | 13074 | refused with an exception |
| `battery_forced_charge_discharge_power` | 13052 | refused with an exception |
| `battery_charging_start_power` | 33149 | not run, `battery_start_power` not granted |
| `battery_discharging_start_power` | 33150 | not run, `battery_start_power` not granted |

- [13074](../entities/register-13074.md) write scale: **not asked**: the read of 13074 itself was
  refused with 0x04, so the run wrote through the field, divided by ten.
- Behaviour, PV 1 W, SoC 50.3 %:
  - forced charge: **did as it was told**, before -990 W, during 1248 W, after -940 W, for
    1250 W commanded. The first forced charge watched on an SH-T.
  - forced discharge: could not tell; the house moved 373 W across the measurement.
  - export limit: could not tell; its write was refused with 0x04, after a manufactured
    discharge of 3570 W (3576 W asked).
- **Restart**, the first on an SH-T: stopped 2.1 s after the command (13000 read `0x1300`),
  running again 144.6 s after the start command. `settings_survived` reads false, but through a
  dongle that reads back stale this is not evidence that a setting was lost.
- Not checked: the charge ceiling (`battery_max_soc` cannot go below 50 %), the PV cut (PV 1 W).
- Restore: every register back and read back; three needed attempts
  (`battery_reserved_soc_for_backup`, `battery_forced_charge_discharge_power`,
  `export_power_limit_mode_raw`).
