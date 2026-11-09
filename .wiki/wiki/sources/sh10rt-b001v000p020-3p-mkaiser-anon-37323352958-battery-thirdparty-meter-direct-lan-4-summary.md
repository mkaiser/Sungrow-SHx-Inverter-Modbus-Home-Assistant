---
type: source
title: sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-4.json
source_path: ../device-diagnosis/results/inverter/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-4.json
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

# SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port, fifth reading

The maintainer's inverter from the development Home Assistant (`make dev`, integration 0.1.0a32),
one extended run at 11:20 UTC on 2026-11-09 beside the house's own Home Assistant (YAML package),
downloaded at 11:39 UTC. **Taken from a diagnostics download**: its `diagnosis` section is committed as it was, under the
library's own name for it (`custom_components/sungrow_modbus/diagnostics.py`). No register dump, no block read test. Source:
`device-diagnosis/results/inverter/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-4.json`.

| | |
| --- | --- |
| Installation | [mkaiser](../entities/installation-mkaiser.md) |
| Model | [SH10RT](../entities/device-sh-rt.md), type code `0x0E03` |
| Stand-in serial | `anon-37323352958` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P020`](../entities/firmware-sapphire-h-b001-v000-p020.md) |
| Transport | the inverter's own LAN port, no module fitted; 6100 answered |
| Battery | third party (Pylontech Force H1), minimum SoC 10 % |

## Capability test

Outcome **3**, PV 6523 W, SoC 88.8 %; every word restored. See
[the capability test](../concepts/capability-test.md).

- Readback: nine of nine matched; [13074](../entities/register-13074.md) probed **times ten**.
- Forced charge: 1248 W for 1250 W. Forced discharge: 1251.5 W for 1250 W.
- Charge ceiling: 2748 W of charge stopped at 0 W under an 86.8 % ceiling, back to 2738 W.
- **Forced-charging window: "nothing measurable happened"** (2747 W before, 2759 W during). The
  battery was already charging from PV close to its 2835 W ceiling, so a window could add only
  about 90 W. This says nothing against the window, which did as it was told seven times the night
  before ([fourth reading](sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-3-summary.md)),
  but the run folds this verdict as established.
- No export, discharge-window or import limit check: the house could not be made to export
  enough, the battery was charging, and PV covered the forced charge.
- Restart: stopped in 2.1 s, Running after 186.6 s in daylight, settings survived.
