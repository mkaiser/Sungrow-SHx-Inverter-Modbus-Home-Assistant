---
type: source
title: sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-6.json
source_path: ../device-diagnosis/results/inverter/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-6.json
ingested: '2026-11-23'
created: '2026-11-23'
tags:
  - diagnosis
  - sh10rt
  - sapphire-h-b001-v000-p020
  - mkaiser
  - direct_lan
  - capability-test
  - plausibility
---

# SH10RT, B001.V000.P020, mkaiser, seventh reading: every check established

Read 2026-11-23 21:00 UTC from the owner's production Home Assistant (schema 28), after
*Extended test (auto repeat)* finished by itself: 26 runs, 2026-11-22 06:47 to 2026-11-23 14:53 UTC. A
**diagnostics download**: the diagnosis section, committed unchanged. Source:
`device-diagnosis/results/inverter/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-6.json`.

| | |
| --- | --- |
| Installation | [mkaiser](../entities/installation-mkaiser.md) |
| Model | [SH10RT](../entities/device-sh-rt.md), type code `0x0E03` |
| Stand-in serial | `anon-37323352958` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P020`](../entities/firmware-sapphire-h-b001-v000-p020.md) |
| Transport | the inverter's own LAN port, through a modbus-proxy; 6100 answered |
| Other pollers | the YAML package, through the same proxy |
| Battery | Pylontech Force H1 (third party) |

**56 of 56 checks established, 0 failed, 0 contradictions**: 31 of the capability test (the restart is counted
apart) and 25 plausibility; 51 passed and five bounds not enforced. The document's outcome is 3, the
worst of its runs (the first twenty ended with 3, skipping checks their moment did not allow), and every setting of every
run was put back.

## The runs, by situation

| Runs (UTC) | Situation | Settled |
| --- | --- | --- |
| 1-20, 2026-11-22 06:47 to 15:34 | battery at 0 to 3.7 % | run 1, before dawn: seven of nine readbacks, the charge window, import limit, bounds, write paths and the restart; run 4 the forced charge by day, run 10 the charging threshold, run 14 the discharge windows; run 1 probed [13074](../entities/register-13074.md) (times ten), later runs found feed-in limitation off and could not |
| 21, 16:08 | low-SoC Standby after dark | forced startup |
| 22-26, 2026-11-23 08:15 to 14:53 | battery at 13.7 to 100 %, PV up to 7.3 kW | 13059 and 13100 readbacks (22), forced discharge and export limit (23), charge ceiling (24), 13059's bound (25), discharging threshold (26) |

## What was watched

| Check | Commanded | Before, during, after |
| --- | --- | --- |
| forced charge | 1250 W | 0, 1250, 0 W |
| forced-charging window | | 0, 4499, 0 W |
| forced discharge | 1250 W | -3686, 1017, -3729 W |
| **export power limit** | 1250 W | 6674, **1247.5**, 7360 W, over a made discharge of 4710 W; 13088 100 % to 12.5 % |
| charge ceiling | 53 % | 4499, 0, 4499 W |
| site import limit (32998) | 2800 W | 3428, 2850.5, 3429 W |
| discharge windows away from now | | 517.5, 0, 439 W |
| charging start threshold | 1000 W | 523, 0, 631 W |
| discharging start threshold | 1000 W | 229, 0, 272 W |
| [forced startup](../entities/register-13017.md) | 0xAA | left standby 122 s, Running 206 s, back 16 s after 0x55 |
| restart | | stopped 2.0 s, running 234.5 s, settings survived |

- **13059 refuses 51 %** and 13058 101 %, both with 0x04. Not enforced, stored and read back:
  33047, 33048 and 13052 at 5100 W (maximum 5000), 33149 and 33150 at 1010 W.
- All nine readbacks matched; EMS modes 2, 3 and 4 were taken; no PV cut here (31211 absent).
- Seventeen of 2026-11-22's runs were due for 13059 and 13100 alone, which an empty battery
  has no safe probe value for.

## Plausibility, 2751 observations (2026-11-21 22:43 to 2026-11-23 21:00 UTC)

| Check | Median ratio or events |
| --- | --- |
| power balance / battery V×I / tracker V×I / phase V×I | 0.918 / 0.994 / 0.991 / 0.985 |
| meter phases / meter against export | 1.000 / 1.000 |
| daily PV, imported, exported, charge, discharge against power | 1.007, 0.998, 1.005, 0.985, 0.997 |
| lifetime counters against the daily ones (eight) | 1.000 each |
| lifetime counters never fall; contain each other | 2745 events each, none against |
| daily counters keep up with the totals | 372 moves, none stuck |
| battery level follows its power | 15 events, none against |
| daily counters reset at midnight | two midnights, none against; 00:02 and 00:07 |
| running states | Standby 1340, Starting 3, Running 1407, forced mode (0x0800) 1 |
