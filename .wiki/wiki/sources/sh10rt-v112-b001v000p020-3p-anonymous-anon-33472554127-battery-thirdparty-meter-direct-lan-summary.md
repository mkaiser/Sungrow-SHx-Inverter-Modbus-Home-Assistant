---
type: source
title: sh10rt-v112-b001v000p020-3p-anonymous-anon-33472554127-battery-thirdparty-meter-direct-lan.json
source_path: ../device-survey/results/inverter/sh10rt-v112-b001v000p020-3p-anonymous-anon-33472554127-battery-thirdparty-meter-direct-lan.json
ingested: '2026-11-02'
created: '2026-11-02'
tags:
  - survey
  - sh10rt-v112
  - sapphire-h-b001-v000-p020
  - anonymous
  - direct_lan
  - modbus-proxy
---

# SH10RT-V112, B001.V000.P020, anonymous, through a Modbus proxy to the inverter's own LAN port

Capability survey of one inverter, read 2026-11-01 from the terminal survey, issue #786, reads
only. Published as `anonymous`. **The first survey through a Modbus proxy**: the owner's note
says a Home Assistant add-on (modbus-proxy 1.1.0) listened on the Home Assistant host with the
inverter as its upstream, and Home Assistant's YAML package polled through it during the run
(`--proxy yes --pollers yes`). A second run minutes later went straight to the inverter:
[the second reading](sh10rt-v112-b001v000p020-3p-anonymous-anon-33472554127-battery-thirdparty-meter-direct-lan-2-summary.md).
Source: `device-survey/results/inverter/sh10rt-v112-b001v000p020-3p-anonymous-anon-33472554127-battery-thirdparty-meter-direct-lan.json`.

| | |
| --- | --- |
| Model | [SH10RT-V112](../entities/device-sh-rt.md), type code `0x0E0F` |
| Stand-in serial | `anon-33472554127` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P020`](../entities/firmware-sapphire-h-b001-v000-p020.md) |
| ARM firmware | `ARM_SAPPHIRE-H_V11_V01_B` |
| DSP firmware | `MDSP_SAPPHIRE-H_V11_V01_B` |
| Battery firmware | none (the Sungrow battery version registers read empty) |
| Communication module firmware | `WINET-SV200.001.00.P040` |
| Transport (owner) | the inverter's own LAN port, through a Modbus proxy |
| Transport (measured) | direct to the inverter's LAN port, with a communication module fitted as well but not in the path; register 6100 answered |
| Battery | BYD Battery-Box Premium HVS 10.2, third party; register 5639 reads 1020 (10.2 kWh) |

## What did not answer

Nothing: all 36 blocks answered in all three rounds, none intermittent, no reconnects, with
another client polling through the same proxy. MPPT3, MPPT4 and 13018 read the specification's
unavailable value. No SBR at unit 200 or 2, no wallbox at unit 3 or 248. 233 of 245 fields
decoded, the same count as the direct run.

**A proxy is transparent to transport detection**: register 6100, the block a
[WiNet-S](../entities/device-winet-s.md) does not forward, answered through it, so the survey
still saw the inverter's own port. See [transport detection](../concepts/transport-detection.md).

## What the dump adds

- [31211](../entities/register-31211.md) reads 0xFFFF, as on every P020.
- [13074](../entities/register-13074.md) holds 7000 W with feed-in limitation (13087) on (0xAA).
- The discharge schedules, registers 33151-33158 and 33179-33187: weekday windows 1 and 2 both
  00:00-24:00; weekend discharge 0xAA (on), windows 1 and 2 both 00:00-24:00. The forced-charging
  schedule (33208-33219) is off, days 1, every window 00:00-00:00.
- The history block, inputs 6101-6826, answers whole over the cable on P020; monthly PV
  generation (6227-6238) holds values up to November and 0 for December. See
  [energy history](../concepts/energy-history.md).
- Register 32998 holds 2000, in no documented unit.

## Contention

The YAML package was polling through the proxy for the whole run, and the block read test
still saw no reconnect and no inconsistent read. See [contention](../concepts/contention.md).
