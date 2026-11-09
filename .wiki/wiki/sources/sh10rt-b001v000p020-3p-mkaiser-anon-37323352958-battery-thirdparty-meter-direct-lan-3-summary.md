---
type: source
title: sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-3.json
source_path: ../device-diagnosis/results/inverter/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-3.json
ingested: '2026-11-09'
created: '2026-11-09'
tags:
  - diagnosis
  - sh10rt
  - sapphire-h-b001-v000-p020
  - mkaiser
  - direct_lan
  - capability-test
---

# SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port, fourth reading: a night of auto repeat

The maintainer's inverter, run overnight in *Extended test (auto repeat)* from a Home Assistant OS
instance (Home Assistant 2026.11.0, integration 0.1.0a32), and downloaded 2026-11-09 at 11:06 UTC.
It carries **19 capability test runs**, from 2026-11-08 20:46 to 2026-11-09 11:03 UTC. **Taken from a diagnostics download**: its `diagnosis` section is committed as it was, under the
library's own name for it (`custom_components/sungrow_modbus/diagnostics.py`). No
register dump, no block read test. Source:
`device-diagnosis/results/inverter/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-3.json`.

| | |
| --- | --- |
| Installation | [mkaiser](../entities/installation-mkaiser.md) |
| Model | [SH10RT](../entities/device-sh-rt.md), type code `0x0E03` |
| Stand-in serial | `anon-37323352958` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P020`](../entities/firmware-sapphire-h-b001-v000-p020.md) |
| Transport | the inverter's own LAN port, no module fitted; 6100 answered |
| Battery | third party (Pylontech Force H1), minimum SoC 10 % |

## The runs

Every run that wrote restored every word; none left a register changed. See
[the capability test](../concepts/capability-test.md).

| When (UTC) | Runs | State | What ran |
| --- | --- | --- | --- |
| 20:46-23:45 | 7 | after dark, SoC 5.5-8.8 % | readbacks, forced charge, charge window, import limit, restart |
| 00:09-04:39 | 10 | **Standby**, the battery at its floor | refused, nothing written (outcome 2) |
| 08:39 | 1 | PV 4539 W, SoC 12.2 % | readbacks, forced charge, charge window |
| 11:03 | 1 | PV 7021 W, SoC 88.8 % | forced discharge, charge ceiling, restart (outcome 0) |

- **Readbacks**: every one matched in every run that wrote it; [13074](../entities/register-13074.md)
  probed **times ten** each time (10000 W written back refused with 0x04 three times). The last
  run skipped what the earlier ones had established.
- **Forced charge**: did as it was told in all eight runs that ran it, 1248-1249.5 W for 1250 W.
- **Forced-charging window**: did as it was told seven times, charge power to 4499 W and back.
  Skipped once (22:54): the window would have crossed midnight on the inverter's clock.
- **[32998](../entities/register-32998.md), the site import limit**: did as it was told seven times,
  import held 23-47 W under each cap (for example 2830 W against 2806.5 W, 960 W against 924 W).
- **Forced discharge** (11:03): 1252 W for 1250 W.
- **Charge ceiling** (11:03): `battery_max_soc` put to 86.8 % under an 88.8 % battery stopped a
  2742 W charge at 0 W, and it came back to 2736 W.
- **Discharge windows away from now: could not tell.** The raw write lost the connection in the
  three runs from 20:46 to 21:46; afterwards the battery discharged under 500 W, too little to see
  a stop. Losses at this house are [contention](../concepts/contention.md)'s pattern (see
  [the third reading](sh10rt-b001v000p020-3p-anonymous-anon-37323352958-battery-unknown-meter-summary.md)).
- **Restart**: stopped in 2.0 s each time; Running after **366.9-367.3 s after dark** (four
  runs) and **186.3 s in daylight**; settings survived.
- **Export limit effect**: never measured. At night the battery was too low to make export; in the
  last run the battery's 2700 W against a 2230 W house left 470 W of export, under the 1812 W a cap
  needs.
- PV cut: [31211](../entities/register-31211.md) absent on P020.

## What it adds

On P020, folded over the night: nine readbacks, the forced charge and discharge, the
forced-charging window, the site import limit and the charge ceiling established; the export
limit's effect and the discharge windows still missing. No contradictions. **The charge ceiling
is new on this firmware.** Auto repeat waited out the low-SoC Standby without writing.
