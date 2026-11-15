---
type: source
title: sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-5.json
source_path: ../device-diagnosis/results/inverter/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-5.json
ingested: '2026-11-15'
created: '2026-11-15'
tags:
  - diagnosis
  - sh10rt
  - sapphire-h-b001-v000-p020
  - mkaiser
  - direct_lan
  - capability-test
  - plausibility
---

# SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port, sixth reading

Read 2026-11-15 from Home Assistant on integration 0.1.0a40 (`command_line`: "home assistant
diagnostics", schema 27), with a capability test run three times by *Extended test (auto repeat)*
from 10:39 to 11:29 UTC and stopped by the owner. A **diagnostics download**: the diagnosis
section, committed unchanged as `-5`, with no register dump and no block read test. Source:
`device-diagnosis/results/inverter/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-5.json`.

| | |
| --- | --- |
| Installation | [mkaiser](../entities/installation-mkaiser.md) |
| Model | [SH10RT](../entities/device-sh-rt.md), type code `0x0E03` |
| Stand-in serial | `anon-37323352958` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P020`](../entities/firmware-sapphire-h-b001-v000-p020.md) |
| Communication module | none named; the inverter's own LAN port |
| Battery | Pylontech Force H1 (third party) |
| At the time | an overcast morning, the battery near empty (SoC ~2.2 %) |

The first mkaiser reading to carry a `plausibility` block. Outcome 3: three runs, nothing left
changed, nothing contradicted, 26 of 53 checks established, **0 failed**.

## The capability test

- **Passed**, among 20: EMS mode options, backup/load-control/weekend-enable write paths, every
  battery-power readback, `export_power_limit`, forced charge, **the forced-charging window**
  (before this it was only ever "could not tell" here), window-2 encoding, the site import limit,
  tracker V×I, `battery_max_soc` and its upper bound, power balance, meter phases, meter against
  export.
- **Five battery-power upper bounds are not enforced**: 33047/33048 (or 13052) stored 7204 W above
  the 7104 W maximum, and 33149/33150 stored 1010 W above 1000 W; the writes took and read back.
  Measured before only on [P023](../entities/firmware-sapphire-h-b001-v000-p023.md)
  ([peter-sm](../entities/installation-peter-sm.md)); first seen on P020 here.
- **Skipped**, the battery near empty: forced discharge, the charge ceiling, the export limit, the
  discharge window and both start thresholds. `battery_min_soc` and the backup reserve could not
  be read back in the state the house was in.
- **Inconclusive**: battery V×I (the battery idle, nothing to measure).
- A Modbus restart did as it was told: stopped in 2.0 s, running 186.5 s later, generating 4.0 s
  after that; settings survived.

## Plausibility, 67 observations (11:29 to 11:44 UTC)

The first plausibility block measured on hardware (`capability_test/plausibility.py`):

| Check | Verdict | Median ratio | Observations |
| --- | --- | --- | --- |
| power balance | matched | 0.828 | 67 |
| tracker voltage times current | matched | 0.934 | 67 |
| meter phases add up | matched | 0.999 | 22 |
| meter against export power | matched | 1.000 | 22 |
| battery voltage times current | could not tell | 0.000 (battery idle) | 21 |
| phase voltage times current | not established (needs 1000 W delivered) | | 20 |
| daily PV generation against power | not established (needs 3 kWh of flow) | | 3 |
