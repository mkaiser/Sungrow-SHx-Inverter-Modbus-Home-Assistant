---
type: source
title: sh10rt-20-3p-swo14-anon-25617150722-battery-none-direct-lan-2.json
source_path: ../device-diagnosis/results/inverter/sh10rt-20-3p-swo14-anon-25617150722-battery-none-direct-lan-2.json
ingested: '2026-11-24'
created: '2026-11-24'
tags:
  - diagnosis
  - sh10rt-20
  - sapphire-h-01011-95-03
  - swo14
  - direct_lan
  - proxy
  - capability-test
  - cluster-slave
  - outcome-5
---

# SH10RT-20 on 01011.95.03, swo14's slave, the car charging: outcome 5

Read 2026-11-24 at 14:13 UTC, 35 minutes after the [reading without the car](../sources/sh10rt-20-3p-swo14-anon-25617150722-battery-none-direct-lan-summary.md),
from a Home Assistant diagnostics download on integration 0.1.0a54 (schema 29; the `diagnosis` section, committed unchanged, with no register dump or block read test). Posted to issue #786. Source: `device-diagnosis/results/inverter/sh10rt-20-3p-swo14-anon-25617150722-battery-none-direct-lan-2.json`. It carries that document's run and one more, ended 14:07 UTC.

| | |
| --- | --- |
| Installation | [swo14](../entities/installation-swo14.md), slave |
| Stand-in serial | `anon-25617150722` |
| Firmware | [`SAPPHIRE-H_01011.95.03`](../entities/firmware-sapphire-h-01011-95-03.md) |
| At the time | PV 356 W, running state 0x0080 |

## Outcome 5: EMS mode 0 would not go back, and it reads 0 six minutes later

The snapshot held EMS mode (13050) **0**. At the restore it read **2** (forced), and five writes of 0
each read back 2: "wrote it back but read 2". Every other register held its original word.

- **This run did not set it.** The EMS mode check was established and skipped, and every check that commands
  the battery declined for want of a battery.
- **The house is not left changed**: this document's own readings, at 14:13 UTC, show 13050 = 0.
- **The host's run overlapped it.** The host's second run was still going (its inverter clock read 15:08:36
  local late in the run, the slave's 15:06:37) and its export check holds EMS mode 2 at 13050 while it
  discharges the battery. The overlap is from those clocks; the minute of the host's write is not recorded.

Whether the host imposes its mode on the slave, or another writer (evcc, the YAML package) did it, is open:
[the query](../queries/does-a-cluster-slave-mirror-the-masters-ems-mode.md).
