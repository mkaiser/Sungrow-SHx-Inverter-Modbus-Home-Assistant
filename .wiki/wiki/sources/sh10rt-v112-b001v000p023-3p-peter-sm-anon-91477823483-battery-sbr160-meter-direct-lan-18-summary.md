---
type: source
title: sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-18.json
source_path: ../device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-18.json
ingested: '2026-11-15'
created: '2026-11-15'
tags:
  - diagnosis
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - peter-sm
  - direct_lan
  - capability-test
  - mdns
---

# SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, twentieth reading

Read 2026-11-15 at 08:26 UTC from Home Assistant on integration 0.1.0a40 (`command_line`: "home
assistant diagnostics", schema 27), with a capability test run at 08:42 UTC; posted by Korsberg to
issue #786 under the first reading's file name. Committed unchanged as `-18`. Source:
`device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-18.json`.

| | |
| --- | --- |
| Installation | [peter-sm](../entities/installation-peter-sm.md) |
| Model | [SH10RT-V112](../entities/device-sh-rt.md) |
| Stand-in serial | `anon-91477823483` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| Communication module firmware | `WINET-SV200.001.00.P045` |
| Transport (owner) | the inverter's own LAN port |
| Transport (measured) | direct to the inverter's LAN port, with a communication module fitted as well but not in the path; register 6100 answered |
| Battery | [SBR160](../entities/device-sbr-battery.md), five modules, firmware `SBRBCU-S_22011.01.30` |
| At the time | morning, overcast: PV 478 W, SoC 80.8 %, load 489 W |

The block read test (Home Assistant's own connection, its polling held off) answered 33 blocks in
every round and 5 intermittently, with no reconnects.

## The first `network_names` from a house

The first committed diagnosis with schema 27's `network_names` section. Home Assistant's own
zeroconf instance browsed `_http._tcp` for 2 s and **got an answer by multicast on the house's
LAN**: one service, the [WiNet-S](../entities/device-winet-s.md) fitted to this inverter
(`this_device: true`), instance `WiNet-WebServer`, port 80, server `SUNGROW` plus the dongle's
stand-in. Its TXT record has the layout measured at [gerd](gerd-mdns-2026-11-11-summary.md):

- `board`: `SUNGROW;1;WiNet-S;<dongle stand-in>;1;`
- `inverter`: `1;3599;<inverter stand-in>;1;516;SH10RT;1;4;`, the same trailing `1;4` as gerd's
- `ethinfo`: **an address** (masked as `<address>` in the document), where gerd's is empty

The inverter's own LAN port advertised nothing. The reverse-DNS label is masked; the MAC vendor
prefix of the address Home Assistant connects to, the inverter's own LAN port, is `AC:19:9F`.
See [does a WiNet-S advertise over mDNS](../queries/does-a-winet-s-advertise-over-mdns.md).

## The capability test (outcome 3)

Ran, with checks skipped or inconclusive; nothing is left changed, and nothing contradicts an
earlier run.

- **All nine readbacks matched**; [13074](../entities/register-13074.md)'s write scale was again
  answered by refusal: the held 9200 written back drew exception 0x04 three times, so it is
  multiplied by ten.
- **Write paths**: backup mode (13075), load control (13011, 13002), the weekend discharge enable
  (33179) and the second forced-charging window (six registers, schedule off) each took its own
  words.
- **EMS mode options 2, 3 and 4 were all taken**, mode 3 included, whose write lost the connection
  in two of the three runs before.
- **Upper bounds**: 13059 refuses 51 % and 13058 101 % (exception 0x04); 33048, 13052, 33149 and
  33150 store a value above their maximum (8200 W over 8100 W, 1010 W over 1000 W), as in the
  [sixteenth reading](sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-14-summary.md).
  **The write of 33047 above its bound lost the connection**, a third time.
- **The charge window's write of 33213 (word 56) lost the connection, a tenth time of ten**, and
  the discharge-window check after it lost it on its first write, 33154, as in every run since the
  sixteenth reading ([the query](../queries/does-writing-33213-drop-the-link-at-peter-sm.md)).
- **Forced discharge**: could not tell, the input drifted across the measurement. Forced charge,
  charge ceiling, export limit, PV cut and both start thresholds were not tried: the house holds
  `battery_max_charge_power` at 10 W, the battery was not charging, export stayed under what a cap
  needs, and PV (402 W) was under the 500 W a cut needs.
- **A Modbus restart did as it was told**: stopped in 2.0 s, running 271 s after the start
  command, generating 8.1 s later; settings survived.
- **Restore**: four settings written back, each read back on the first attempt; 42 were already
  at their original word.
