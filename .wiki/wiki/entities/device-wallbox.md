---
type: entity
title: Sungrow AC wallbox
tags: [wallbox, ac22e-01, ac011e-01, sub-device, tls]
created: '2026-10-29'
---

# Sungrow AC wallbox

AC011E-01 and AC22E-01. In the integration it is a **device of its own**,
with 32 fields in four components (`src/sungrow_modbus/wallbox/`). It is
**read only**: nothing writes to it.

## Two ways in

| Path | Protocol | Unit | In the integration |
| --- | --- | --- | --- |
| through the [WiNet-S](device-winet-s.md) | Modbus TCP, port 502 | **3** | found behind the inverter's entry by itself |
| at its own LAN address | Modbus TCP inside TLS, port **516** | **248** | when the inverter's entry has the `wallbox_host` **option** |

`wallbox_host` is an option, not an entry, so the device and its entity ids
are the same either way. Never reachable through the inverter's own LAN port
(every unit 0-255 swept). It needs no [iHomeManager](device-ihomemanager.md),
and sweeping for one cannot find it.

## Reading rules

- **Over TLS a read must start on a data point's first register.** 21295 ×24
  answers, 21296 ×10 times out. A pooled block must begin at one.
- **A dongle forwards any start**, and answers 0 for several registers the
  direct path reads.
- **The serial (input 21201-21206) sits just below the model name.**
  `wallbox.probe_units` reads the name. The serial words are masked when
  the document is published, and replaced by `wallbox.serial_anonymized_hashed`;
  see [serial anonymization](../concepts/serial-anonymization.md).

`sungrow_survey.py` sweeps port 516. A wallbox found there is read by
`device-survey/scripts/python/wallbox_direct.py` into a **wallbox
document** of its own, published in `device-survey/wallbox/` beside
`inverter/`.

The register map, with how strongly each row is held:
[wallbox registers](../sources/wallbox-registers-summary.md).

## Measured

One AC22E-01 at [gerd](installation-gerd.md): through the dongle in the
[WiNet-S survey](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-summary.md),
and at its own address in the
[wallbox document](../sources/ac22e01-gerd-anon-41346964423-wallbox-tls-summary.md).
Read directly again on 2026-10-29: holding 21250-21259 is a constant
20-digit ASCII number, shaped like an identifier, and is masked like the serial;
input 21267 counts up every few seconds; the start mode read 3, outside the
documented 0-2. What is fixed and what moves is in
[wallbox registers](../sources/wallbox-registers-summary.md).
RS485 at unit 248 is reported by others and never measured here; see
[the open query](../queries/does-a-wallbox-answer-unit-248-on-rs485.md).
