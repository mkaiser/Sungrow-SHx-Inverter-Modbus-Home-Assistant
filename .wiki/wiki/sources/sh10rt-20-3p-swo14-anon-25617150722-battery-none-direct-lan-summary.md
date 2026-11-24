---
type: source
title: sh10rt-20-3p-swo14-anon-25617150722-battery-none-direct-lan.json
source_path: ../device-diagnosis/results/inverter/sh10rt-20-3p-swo14-anon-25617150722-battery-none-direct-lan.json
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
---

# SH10RT-20 on 01011.95.03, swo14's slave, no car charging

Read 2026-11-24 at 13:38 UTC from a Home Assistant diagnostics download on integration 0.1.0a54 (schema 29; the `diagnosis` section, committed unchanged, with no register dump or block read test). Posted to issue #786. Source: `device-diagnosis/results/inverter/sh10rt-20-3p-swo14-anon-25617150722-battery-none-direct-lan.json`. The second reading of this inverter: the
[first](../sources/sh10rt-20-3p-sw14-anon-25617150722-battery-none-direct-lan-summary.md) was filed under `sw14`.

| | |
| --- | --- |
| Installation | [swo14](../entities/installation-swo14.md), slave, unit 2 on the proxy's port 503 |
| Stand-in serial | `anon-25617150722` |
| Firmware | [`SAPPHIRE-H_01011.95.03`](../entities/firmware-sapphire-h-01011-95-03.md) |
| Battery, meter | none; both on the host |
| WiNet-S | fitted, heard over mDNS |
| At the time | PV 502 W |

One run, ended 10:56 UTC, **outcome 0**: three of three readbacks matched, 13074 stored as handed (the held
9580 W accepted), EMS modes 2, 3 and 4 taken, the write paths took their own words, both start
thresholds store 1010 W over 1000 W. Every behavioural check needs a battery. As on 2026-11-17,
13023 reads 0 and 5214 is unavailable.
