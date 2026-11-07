---
type: source
title: sh10rs-b000v002p065-1p-jam3s97-anon-35122522532-battery-sbh300-winet-lan.json
source_path: ../device-diagnosis/results/inverter/sh10rs-b000v002p065-1p-jam3s97-anon-35122522532-battery-sbh300-winet-lan.json
ingested: '2026-11-01'
created: '2026-11-01'
tags:
  - diagnosis
  - sh10rs
  - sunstone-h-b000-v002-p065
  - jam3s97
  - winet
  - capability-test
---

# SH10RS, B000.V002.P065, Jam3s97, a WiNet-S on Ethernet, with a capability test

Capability diagnosis of one inverter, read 2026-11-01 in the morning from the terminal diagnosis, issue
#786, with the capability test (`--capability-test yes`) and the owner's other pollers running
(`--pollers yes`). The contributor also attached the capability test as a file of its own; it is
identical to the document's `capability_test` block, so only the diagnosis is committed. Source:
`device-diagnosis/results/inverter/sh10rs-b000v002p065-1p-jam3s97-anon-35122522532-battery-sbh300-winet-lan.json`.

| | |
| --- | --- |
| Installation | [Jam3s97](../entities/installation-jam3s97.md) |
| Model | [SH10RS](../entities/device-sh-rs.md), type code `0x0D1B`, single phase |
| Stand-in serial | `anon-35122522532` |
| Inverter firmware | [`SUNSTONE-H_B000.V002.P065`](../entities/firmware-sunstone-h-b000-v002-p065.md) |
| ARM firmware | `ARM_SUNSTONE-H_V11_V01_A` |
| DSP firmware | `MDSP_SUNSTONE-H_V11_V01_A` |
| Version 1 / 2 | `SUNSTONE-H_01011.02.65` / `SUNSTONE-H_03021.01.14` |
| Battery firmware | `SBHBCU-S_22011.04.08`, with bytes after its NUL as on the [SH6.0RS](sh60rs-b000v001p068-1p-anonymous-anon-17579213881-battery-sbr192-winet-summary.md) |
| Communication module firmware | `WINET-SV300.001.03.P032` |
| Transport (owner) | a [WiNet-S](../entities/device-winet-s.md) on Ethernet |
| Transport (measured) | through a communication module; register 6100 refused |
| Battery | [SBH](../entities/device-sbh-battery.md) (the owner's file names an SBH300; unit 2, 30.41 kWh at 5639, the SBR cell and module blocks refused with 0x02) |
| PV | four MPPTs answer |

## What did not answer

The sub-controller (2613) and battery (2629) firmware blocks every round (0x02), and the meter
phase registers 5741 and 5744, as through every WiNet-S. 13018 reads the unavailable value.
33149-33150 (battery start power) were not granted, though a two-word read of 33149 answered in
the block test. The history block (inputs 6101-6826) is refused except 64 words that read 0
(and 6499, which reads 6): a dongle's 0 is [not evidence](../concepts/zero-means-absent.md).

**Intermittent, with the owner's pollers running**: 13000, 5011 and 5115 dropped the connection
in some rounds; holding 33208 (12 words) was refused with an exception in some rounds; 31211
read inconsistently. See [contention](../concepts/contention.md).

## What the dump adds

- [Register 31211](../entities/register-31211.md) answers **0x55**.
- The forced-charging schedule answers (33208 = 0x55, off), as do the discharge schedules,
  with the SH-RT's layout (weekend discharge 0xAA).
- Holding 5000-5005 hold the inverter's clock, as on the SH-RT.
- [Register 32998](../entities/register-32998.md) reads 1300, where peter-sm's SH-RT reads 950: 13.00 kW, at the
  0.01 kW the owner later measured ([discussion #546](discussion-546-site-import-power-limit-summary.md)).

## Capability test

Outcome **3**: ran, with checks skipped or inconclusive. Through a WiNet-S only leg C is
evidence. See [the capability test](../concepts/capability-test.md). PV 4052 W, SoC 100 %.

| Field | Register | Verdict |
| --- | --- | --- |
| `battery_min_soc` | 13059 | matched (the dongle's readback) |
| `battery_max_soc` | 13058 | matched (the dongle's readback) |
| `battery_reserved_soc_for_backup` | 13100 | matched (the dongle's readback) |
| `export_power_limit` | 13074 | matched, raw 600 for 600 W (the dongle's readback) |
| battery power limits, forced power | 33047, 33048, 13052 | not run, bounds not resolved |
| battery start powers | 33149, 33150 | not run, `battery_start_power` not granted |

- [13074](../entities/register-13074.md) write scale: **stored as handed**. With feed-in
  limitation on (13087 = 0xAA), the probe wrote the held 5300 back, which a times-ten firmware
  refuses as 53000 W over the 10000 W maximum; it was accepted. An acceptance through a dongle
  is the inverter's, since a refusal survives one (measured at bar12).
- Behaviour:
  - **PV cut: did as it was told**, total DC power 3465 W before, 0 W during, 3092 W after. The
    first cut watched on an SH-RS, and the first through a WiNet-S: the dongle forwards the
    write.
  - export limit: could not tell; the house moved 459 W across the measurement.
  - no battery check: the battery was full, so no forced power could be resolved, and nothing
    was charging for the ceiling check.
- **Restart: not run**, the stop command was refused with an exception. Through a busy dongle
  that does not show the RS refuses it.
- Every setting already held its original value at the restore.
