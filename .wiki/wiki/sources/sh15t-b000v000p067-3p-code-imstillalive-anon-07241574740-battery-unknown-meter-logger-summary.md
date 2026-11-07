---
type: source
title: sh15t-b000v000p067-3p-code-imstillalive-anon-07241574740-battery-unknown-meter-logger.json
source_path: ../device-survey/results/inverter/sh15t-b000v000p067-3p-code-imstillalive-anon-07241574740-battery-unknown-meter-logger.json
ingested: '2026-11-07'
created: '2026-11-07'
tags:
  - survey
  - sh15t
  - pearl-h-b000-v000-p067
  - code-imstillalive
  - logger
---

# SH15T, B000.V000.P067, code-imstillalive, through a Logger1000A

Capability survey of one inverter, read 2026-11-07 around 00:47 UTC with the survey button of the
integration, posted by code-imstillalive to issue #791 (announced on #786). Read only; no control
test. The second inverter of the same house, behind the same
[Logger](../entities/device-logger.md) as the
[SH25T](sh25t-b000v000p067-3p-code-imstillalive-anon-92853701430-battery-unknown-meter-logger-summary.md).
Source:
`device-survey/results/inverter/sh15t-b000v000p067-3p-code-imstillalive-anon-07241574740-battery-unknown-meter-logger.json`.

| | |
| --- | --- |
| Installation | [code-imstillalive](../entities/installation-code-imstillalive.md) |
| Model | [SH15T](../entities/device-sh-t.md), type code `0x0E25`, nominal 15.0 kW |
| Stand-in serial | `anon-07241574740` |
| Inverter firmware | [`PEARL-H_B000.V000.P067`](../entities/firmware-pearl-h-b000-v000-p067.md), version 1 `PEARL-H_01011.94.41` |
| Battery firmware | `SBRBCU-S_22011.01.30` |
| Communication module firmware | none read |
| Transport (owner) | a Logger1000A; this inverter on its own Logger port (the owner says 503, unit 2) |
| Transport (measured) | through a communication module, which did not name itself; register 6100 refused |
| Battery | [SBR](../entities/device-sbr-battery.md) by its BCU; the owner says two SBR256, and 5639 reads 51.20 kWh, twice 25.6 |

## What did not answer

Refused with an exception in every round: 2613, 2629, 6227, 6417 and 6596, as on the SH25T.
**Intermittent**, over three rounds: every holding block of the poll (13002, 13050, 33047, 33149,
31213, 31211, 33208, 33151, 33179), and the probe of 13018 had no answer, though the dump read it
(85). Another Home Assistant polled through the Logger throughout; see
[contention](../concepts/contention.md).

## What it adds

- **[31211](../entities/register-31211.md) answers 0x55** on P067, as on the SH25T.
- **33149 and 33150 answer 0xFFFF** in the dump, as on the SH25T.
- **An SBR on an SH-T**, as at [FullHD23](../entities/installation-fullhd23.md): the BCU names itself `SBRBCU`.
- **Version 1 is `PEARL-H_01011.94.41`** beside the SH25T's `.95.41`, on the same P067.
- The meter and load power read 0, as on the SH25T, whose page says why that is no reading.
