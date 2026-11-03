---
type: source
title: sh10rt-v112-b001v000p020-3p-anonymous-anon-33472554127-battery-thirdparty-meter-direct-lan-2.json
source_path: ../device-survey/results/inverter/sh10rt-v112-b001v000p020-3p-anonymous-anon-33472554127-battery-thirdparty-meter-direct-lan-2.json
ingested: '2026-11-02'
created: '2026-11-02'
tags:
  - survey
  - sh10rt-v112
  - sapphire-h-b001-v000-p020
  - anonymous
  - direct_lan
---

# SH10RT-V112, B001.V000.P020, anonymous, the inverter's own LAN port, second reading

Capability survey of one inverter, read 2026-11-01 from the terminal survey, issue #786, reads
only, ten minutes after
[the first reading](sh10rt-v112-b001v000p020-3p-anonymous-anon-33472554127-battery-thirdparty-meter-direct-lan-summary.md).
Published as `anonymous`. This time straight to the inverter: the owner stopped the proxy and
nothing else polled (`--proxy no --pollers no`). Source:
`device-survey/results/inverter/sh10rt-v112-b001v000p020-3p-anonymous-anon-33472554127-battery-thirdparty-meter-direct-lan-2.json`.

| | |
| --- | --- |
| Model | [SH10RT-V112](../entities/device-sh-rt.md), type code `0x0E0F` |
| Stand-in serial | `anon-33472554127` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P020`](../entities/firmware-sapphire-h-b001-v000-p020.md) |
| Battery firmware | none |
| Communication module firmware | `WINET-SV200.001.00.P040` |
| Transport (owner) | the inverter's own LAN port |
| Transport (measured) | direct to the inverter's LAN port, with a communication module fitted as well but not in the path; register 6100 answered |
| Battery | BYD Battery-Box Premium HVS 10.2, third party; register 5639 reads 1020 |

## What did not answer

Nothing, exactly as through the proxy: 36 of 36 blocks in all three rounds, none intermittent, no
reconnects, 233 of 245 fields decoded. The register dump holds the same settings (31211 0xFFFF,
13074 7000 W with feed-in limitation on, the same schedules, the history block whole), so the
proxy changed nothing a survey can see.

## Contention

No other poller. See [contention](../concepts/contention.md).
