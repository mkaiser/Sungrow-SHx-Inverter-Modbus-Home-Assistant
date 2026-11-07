---
type: source
title: sh25t-b000v000p067-3p-code-imstillalive-anon-92853701430-battery-unknown-meter-logger.json
source_path: ../device-diagnosis/results/inverter/sh25t-b000v000p067-3p-code-imstillalive-anon-92853701430-battery-unknown-meter-logger.json
ingested: '2026-11-07'
created: '2026-11-07'
tags:
  - diagnosis
  - sh25t
  - pearl-h-b000-v000-p067
  - code-imstillalive
  - logger
---

# SH25T, B000.V000.P067, code-imstillalive, through a Logger1000A

Capability diagnosis of one inverter, read 2026-11-07 around 00:43 UTC with the diagnosis button of the
integration, posted by code-imstillalive to issue #791 (announced on #786). Read only; no capability
test. The first SH25T, and the first reading of any inverter through a
[Sungrow Logger](../entities/device-logger.md). Source:
`device-diagnosis/results/inverter/sh25t-b000v000p067-3p-code-imstillalive-anon-92853701430-battery-unknown-meter-logger.json`.

| | |
| --- | --- |
| Installation | [code-imstillalive](../entities/installation-code-imstillalive.md) |
| Model | [SH25T](../entities/device-sh-t.md), type code `0x0E28`, nominal 25.0 kW |
| Stand-in serial | `anon-92853701430` |
| Inverter firmware | [`PEARL-H_B000.V000.P067`](../entities/firmware-pearl-h-b000-v000-p067.md), version 1 `PEARL-H_01011.95.41` |
| Battery firmware | `SBHBCU-S_22011.04.10` |
| Communication module firmware | none read |
| Transport (owner) | a Logger1000A; this inverter on its own Logger port (the owner says 502, unit 1) |
| Transport (measured) | through a communication module, which did not name itself; register 6100 refused |
| Battery | [SBH](../entities/device-sbh-battery.md) by its BCU; the owner says two SBH200 |

## What did not answer

Refused with an exception in every round of the block read test: the sub-controller and battery
firmware blocks (2613, 2629) and the history blocks (6227, 6417, 6596), the same set a
[WiNet-S](../entities/device-winet-s.md) refuses. **Intermittent**: the clock (holding 5000, 6),
once. Another Home Assistant polled every device through the Logger throughout, so the owner
reads the one miss as [contention](../concepts/contention.md).

## What it adds

- **[31211](../entities/register-31211.md) answers 0x55** on P067; 13018 answers 85.
- **33149 and 33150 answer 0xFFFF** (block test and dump), so the battery start powers read as
  unavailable on this firmware, where P071's readings disagreed with each other.
- **13074 holds 25000 W**, the top of the range the inverter reports (0 to 25000 W), with the limitation mode
  0x55. Its write scale is not measured.
- **The meter reads 0** on every phase, and the load power 0. The owner lists the house's
  DTSU666-20 as a device of the Logger's own (its own port, unit 5), so the inverter may have no
  meter of its own to report; a zero is not a reading of one
  ([zero means absent](../concepts/zero-means-absent.md)).
- **5639 reads 70.96 kWh**, where two SBH200 rate at about 40 kWh. Unexplained.
