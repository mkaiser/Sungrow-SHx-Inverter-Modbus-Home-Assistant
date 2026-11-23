---
type: source
title: sh15t-b000v000p071-3p-galkar-anon-30195315022-battery-sbh150-winet-lan-2.json
source_path: ../device-diagnosis/results/inverter/sh15t-b000v000p071-3p-galkar-anon-30195315022-battery-sbh150-winet-lan-2.json
ingested: '2026-11-23'
created: '2026-11-23'
tags:
  - diagnosis
  - sh15t
  - pearl-h-b000-v000-p071
  - galkar
  - winet_lan
  - capability-test
  - export-limit
---

# SH15T, B000.V000.P071, GalKar, a WiNet-S on Ethernet, second reading: the export limit in daylight

Read 2026-11-23 from Home Assistant (schema 28; the owner reports 0.1.0a49), with one capability test
run at 05:32 UTC, posted to issue #786 as a gist. A **diagnostics download**: the diagnosis section,
committed unchanged. Source: `device-diagnosis/results/inverter/sh15t-b000v000p071-3p-galkar-anon-30195315022-battery-sbh150-winet-lan-2.json`.

| | |
| --- | --- |
| Installation | [GalKar](../entities/installation-galkar.md) |
| Model | [SH15T](../entities/device-sh-t.md), type code `0x0E25` |
| Stand-in serial | `anon-30195315022` |
| Inverter firmware | [`PEARL-H_B000.V000.P071`](../entities/firmware-pearl-h-b000-v000-p071.md) |
| Communication module | [WiNet-S](../entities/device-winet-s.md), `WINET-SV300.001.03.P033`, on Ethernet; 6100 refused |
| Other pollers | the YAML package |
| Battery | [SBH](../entities/device-sbh-battery.md)150, SoC 22.2 %; the SBR cell and module blocks refused with 0x02 |
| At the time | PV 1989 W, 13074 reading 0 W, feed-in limitation (13087) off, maximum 20800 W |

## The export limit

| What | Value |
| --- | --- |
| Asked | 1250 W, with feed-in limitation switched on |
| Word written to [13074](../entities/register-13074.md) | **125**: the write scale could not be asked (its read was refused with 0x04), so the run divided by ten |
| Export before, during, after | 2539 W, **106.5 W** (MAD 36.5), 2528 W |
| 13088 before, during | 0 %, **0.5 %** |

The figure is near 125 W, so the inverter **stored the word as handed**; times ten would have held
1250 W. The bracket came back within 11 W, so the house did not move. Two things keep it from being
exact: 13074 was not read back (a dongle's readback is stale), and 0.5 % of the 15000 W rating is
75 W, where 125 W is 0.8 % and 1250 W would be 8.3 %. A cap left at the held 0 W is not what 13088
shows. The verdict "off by a decade" is the run's fallback factor and not a register fault.

## The other checks

| Check | Verdict |
| --- | --- |
| forced charge | did as it was told, 1250 W (1117 W before, 1260 W after, so the charge alone proves little) |
| forced discharge | could not tell: -1277 W, 1248 W, 1248 W; the discharge had not let go by the third window |
| PV generation cut | did as it was told: 2247 W, 7 W, 1623 W |
| restart | stopped 2.0 s, running 181 s after the start command |
| forced-charging window | could not tell: the write of 33208 was refused with 0x04 |
| 13058 above 100 % | refused, 0x04 |
| 33047, 33048, 13052 at 11010 W | taken; a dongle cannot say whether stored |
| `battery_min_soc` (13059) readback | matched (the dongle's) |
| 13058, 13100, 33047, 33048, 13074, 13052 readbacks | refused with 0x04 |

Those refusals and the block read test's intermittent holding 13002, 13050, 33047 and 33149 are a
[busy WiNet-S](../queries/does-a-busy-winet-s-refuse-with-0x04.md); the YAML package polls it too.

## Outcome 5

Sixteen of seventeen settings were written back (the dongle took the writes; not read back). **33208** was
refused on all five restore writes, each of the value it held, 1. The check's own write was refused as
well. The owner read 33208 = 1 and 33207 = 0x55 hours later, through the WiNet-S (issue #786):
nothing seems left changed, as far as a dongle's read can say. The same shape as
[ra1k-0](../entities/installation-ra1k-0.md)'s 33209.

## Plausibility, 4176 observations (2026-11-20 to 11-23)

Power balance (0.886), battery V×I (0.984), tracker V×I (1.072), phase V×I (1.052), the meter's phases
and the meter against export (1.000) matched, and the lifetime counters never fell. The daily-counter
checks against power had no trail in three days.

## 33149-33150

Answered in some rounds of the download's block read test and refused in others, as in the first reading; `null` in this
document's readings. Still [unsettled](../entities/firmware-pearl-h-b000-v000-p071.md).
