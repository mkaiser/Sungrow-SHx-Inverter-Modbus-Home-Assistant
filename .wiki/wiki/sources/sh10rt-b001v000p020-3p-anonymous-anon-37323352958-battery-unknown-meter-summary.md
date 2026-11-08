---
type: source
title: sh10rt-b001v000p020-3p-anonymous-anon-37323352958-battery-unknown-meter.json
source_path: ../device-diagnosis/results/inverter/sh10rt-b001v000p020-3p-anonymous-anon-37323352958-battery-unknown-meter.json
ingested: '2026-11-08'
created: '2026-11-08'
tags:
  - diagnosis
  - sh10rt
  - sapphire-h-b001-v000-p020
  - mkaiser
  - direct_lan
  - capability-test
---

# SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port, third reading

The maintainer's inverter, read from the Home Assistant 2026.11 Marketplace testbed: the preview
integration 0.1.0a30 installed through *Add from link*, on this tree's library. Two extended runs
that day, at 15:55 and 19:21 UTC, the second after dark. The entry's questions were left blank,
so the document says `anonymous` and `battery-unknown`; the stand-in serial is mkaiser's. **Taken
from a diagnostics download**: its `diagnosis` section is committed as it was, under the
library's own name for it (`custom_components/sungrow_modbus/diagnostics.py`). No register dump
or block read test. Source:
`device-diagnosis/results/inverter/sh10rt-b001v000p020-3p-anonymous-anon-37323352958-battery-unknown-meter.json`.

| | |
| --- | --- |
| Installation | [mkaiser](../entities/installation-mkaiser.md) |
| Model | [SH10RT](../entities/device-sh-rt.md), type code `0x0E03` |
| Stand-in serial | `anon-37323352958` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P020`](../entities/firmware-sapphire-h-b001-v000-p020.md) |
| Transport (measured) | not determined: register 6100 got no answer |
| Battery | third party, SoC 37.3 % then 21.1 % |

## Capability test

Outcome **3** both times; every word restored both times, none left changed. See
[the capability test](../concepts/capability-test.md).

- Readback: all nine matched in the first run, the minimum SoC and the backup reserve included;
  in the second, eight matched and the write of 33149 (charging start power) lost the connection,
  which the run reported as "refused with an exception".
- [13074](../entities/register-13074.md)'s write-scale probe settled nothing: its write of the
  limit (protocol address 13073) lost the connection in both runs, so the limit went out divided by ten, as on every
  B001 firmware measured; in the first run export then held at 1252.5 W against 1250 W. The
  second run had no export check: discharging 3300 W produced no export.
- Forced charge did as it was told both runs; forced discharge in the first, and in the second it
  was not measured, the house drawing 627 W more afterwards.
- [32998](../entities/register-32998.md), the site import limit, did as it was told both runs
  (1630 W met at 1609 W, 1870 W at 1820.5 W); 0 and 5001 refused with 0x04, 5000 taken in the
  first run and its write lost in the second.
- **Forced-charging window: did as it was told** in the second run, charge power from -633 W to
  4499 W and back to -665 W. In the first run its write at protocol address 33213 lost the connection, the write
  [the peter-sm query](../queries/does-writing-33213-drop-the-link-at-peter-sm.md) is about.
- **Discharge windows away from now: could not tell** in both runs, reported as "refused with an
  exception". That report counts a lost connection as a refusal too (33149 above), so which it
  was is not recorded; the library now reports a drop as a drop.
  The same windows (each 00:00 to 24:00) obeyed on
  [2026-11-04](mkaiser-discharge-window-2026-11-04-summary.md).
- Charge ceiling not checked: the battery was below the 50 % the ceiling can go to.
- PV cut: [31211](../entities/register-31211.md) absent on P020.
- Restart: stopped in 2.0 s both times; Running after 234.7 s at dusk and 365.7 s after dark;
  settings survived.

## What it adds

The forced-charging window, inconclusive at the
[second reading](sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-2-summary.md),
is now established on P020. Writes lost the connection at four protocol addresses (13073 twice,
33213, 33148, 32997) with this Home Assistant polling throughout: losses at changing addresses are what
[contention](../concepts/contention.md) looks like, so none of them is evidence about its register.
And the run showed that a lost connection was being reported as a refusal, which would fold as
established; the library now tells the two apart
([a failed read is not a refusal](../concepts/failed-read-is-not-refusal.md)).
