---
type: source
title: sh10rt-20-3p-sw14-anon-25617150722-battery-none-direct-lan.json
source_path: ../device-diagnosis/results/inverter/sh10rt-20-3p-sw14-anon-25617150722-battery-none-direct-lan.json
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
  - cluster-slave
---

# SH10RT-20 on 01011.95.03, swo14's slave inverter, no battery of its own

Read 2026-11-17 at 12:59 UTC from a Home Assistant diagnostics download on integration 0.1.0a43
(schema 28), with one capability test run at 12:00 UTC and the restart left out. The **slave of
the cluster** whose host is
[here](sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-summary.md); the
battery is on the host. Posted to issue #786. Source:
`device-diagnosis/results/inverter/sh10rt-20-3p-sw14-anon-25617150722-battery-none-direct-lan.json`.

The document's `reporter` reads `sw14`, a typo for the handle on the host's two documents and on
the issue, so the derived filename carries it. It is the same house and the same owner.

| | |
| --- | --- |
| Installation | [swo14](../entities/installation-swo14.md) |
| Model | [SH10RT-20](../entities/device-sh-rt.md), type code `0x0E13`, three phase 3P4L |
| Stand-in serial | `anon-25617150722` |
| Inverter firmware | **not read**: the 13250 block is refused on this firmware |
| Version 1 / 2 | [`SAPPHIRE-H_01011.95.03`](../entities/firmware-sapphire-h-01011-95-03.md) / `SAPPHIRE-H_03011.95.03` |
| Unit id | **2**, on the proxy's port 503 (the host is unit 1 on 502) |
| Transport (measured) | direct to the inverter's LAN port; register 6100 answered |
| Battery | none; the pack is on the host |
| Meter | 5741 and 5744 read **unavailable** (the meter is the host's) |
| At the time | 697 W of PV, 1.4 kWh generated that day |

## What a cluster slave answers

The second slave in the corpus, after [fwitten](../entities/installation-fwitten.md)'s, and it
agrees with it where it matters: **zeros, not sentinels**, for the battery it does not have --
5639 capacity 0, voltage 0, temperature 0, state of health 0 -- which is what
[zero means absent](../concepts/zero-means-absent.md) was written for.

Two differences from fwitten's slave, both on `01011.95.03` as well:

- **[Register 13023](../entities/register-13023.md) (battery level) reads 0 here**, where
  fwitten's slave answered **0xFFFF** on [P023](../entities/firmware-sapphire-h-b001-v000-p023.md).
  Both are handled -- 0xFFFF by the `NAN_BEYOND_YAML` sentinel, 0 by the zero rule -- but the
  firmware, not the role, decides which one arrives.
- **Register 5214 (battery power) answers `0x7FFFFFFF`**, the signed 32-bit unavailable value,
  which the map did not declare: it decodes to **2,147,483,647 W**. 13022 beside it reads 65535
  and is declared, so `battery_power_unsigned` is correctly unavailable while `battery_power`
  shows 2.1 GW. The capability test printed it too ("battery discharge power carried on at
  2147483647 W"). Fixed in this ingest by declaring the sentinel
  (`src/sungrow_modbus/hybrid_inverter/registers.py`), and it bears on
  [is battery power firmware dependent](../queries/is-battery-power-firmware-dependent.md): this
  is the first reading of what 5214 answers with no battery at all.

## 13074 stores a written word as handed here too

The probe wrote back the held **9580 W** -- a no-op if stored as handed, 95800 W and out of range
if multiplied -- and it was accepted. So [13074](../entities/register-13074.md) is 1:1 on this
machine as on the host, both on `01011.95.03`. Its maximum reads 9580 W where the host's reads
10000 W, so this inverter is derated.

## The capability test (outcome 3)

One run, outcome 3; nothing left changed.

- **Three readbacks matched**: the export limit (600 W), and both start thresholds.
- **EMS mode options 2, 3 and 4 were all taken**, and the write paths -- backup mode, load
  control, the weekend discharge enable and the second forced-charging window -- each took their
  own words. So a slave with no battery still accepts every battery-shaped command.
- **The charging start thresholds store values above their maximum** (1010 W over 1000 W), as on
  the host.
- **Nothing behavioural could be measured**: with no battery the forced charge power cannot be
  resolved, so the forced charge, the forced-charging window, the discharge window and the charge
  ceiling were all skipped, and the house could not be made to export.
- **The import limit check did not run**: 32998 reads 20.00 kW in the ordinary readings, but the
  capability test counts it absent because its snapshot gates it behind the battery -- "the device
  does not have it (battery did not answer)". A slave's import limit is therefore unmeasured, and
  would need the gate to separate the register from the pack.
- **Restore**: five registers of the forced-charging window written back, each read back on the
  first attempt; 32 were already at their original word.
