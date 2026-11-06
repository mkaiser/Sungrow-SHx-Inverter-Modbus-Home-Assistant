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
and sweeping for one cannot find it. Where an iHomeManager is installed it
drives the wallbox over 516 itself, so `wallbox_host` may find the port taken
(reported to evcc, not measured here:
[evcc cross-reference](../sources/cross-reference-evcc-summary.md)).

**Sixty seconds without Modbus traffic and the wallbox drops the
connection** and applies its fallback current, by evcc's account; evcc reads
the status every 30 s for it
([evcc cross-reference](../sources/cross-reference-evcc-summary.md)). The
integration reads the wallbox on the inverter's fast tier
(`custom_components/sungrow_modbus/coordinator.py`), inside that by default;
a fast tier set above 60 s would let the wallbox drop the session.

**Through a WiNet-S, not faster than every 10 s**: polled faster, the dongle
goes into a fault state, by an ioBroker user's account
([shcshc76 cross-reference](../sources/cross-reference-shcshc76-summary.md));
not measured here. The fast tier's default is exactly 10 s
(`DEFAULT_INTERVALS` in `src/sungrow_modbus/hybrid_inverter/registers.py`),
so the defaults sit on that edge and a shorter fast tier would cross it.

## Reading rules

- **Over TLS a read must start on a data point's first register.** 21295 ×24
  answers, 21296 ×10 times out. A pooled block must begin at one.
- **A dongle forwards any start**, and answers 0 for several registers the
  direct path reads.
- **The serial (input 21201-21206) sits just below the model name.**
  `wallbox.probe_units` reads the name. The integration reads the serial
  once, for the device page's `serial_number`, and identifies the device by
  the inverter's serial plus `-wallbox`. The serial words are masked when
  the document is published, and replaced by `wallbox.serial_anonymized_hashed`;
  see [serial anonymization](../concepts/serial-anonymization.md).

`sungrow_survey.py` sweeps port 516. A wallbox found there is read by
`device-survey/scripts/python/wallbox_direct.py` into a **wallbox
document** of its own, published in `device-survey/results/wallbox/` beside
`results/inverter/`.

The register map, with how strongly each row is held:
[wallbox registers](../sources/wallbox-registers-summary.md).

## Measured

One AC22E-01 at [gerd](installation-gerd.md): through the dongle in the
[WiNet-S survey](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-summary.md),
and at its own address in the
[wallbox document](../sources/ac22e01-gerd-anon-41346964423-wallbox-tls-summary.md).
Read directly again on 2026-10-29: holding 21250-21259 is a constant
20-digit ASCII number, shaped like an identifier, and is masked like the serial;
input 21267 ticks about once per 5 s whatever a client reads or writes,
the shape of an uptime counter; the start mode read 3, outside the
documented 0-2. Checked against Sungrow's own portal on 2026-10-30: input
21201-21206 is the serial it shows, and 21300 and 21310 count lifetime and
session energy in Wh; see
[the portal cross-check](../sources/gerd-wallbox-isolarcloud-2026-10-30-summary.md).
After a 7854 Wh session that ended at 11:33 on 2026-11-01, input 21310 still held the session's
energy, input 21313 read 0 and the start mode 3
([the dongle reading](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-2-summary.md)).
During a session on 2026-11-03, read over TLS and through the dongle, input 21313 read **527**
in both, the start mode 3, and **input 21320 held the time of the reading** rather than an end
([TLS](../sources/ac22e01-gerd-anon-41346964423-wallbox-tls-2-summary.md),
[dongle](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-3-summary.md)). Over the whole session
([the log](../sources/gerd-wallbox-charging-session-2026-11-03-summary.md))
21313 fell to 0 when the charging ended, 94 s after the power did, as the
status went 3, 5 (suspended by the vehicle), 6 (completed). Whether 21308/21310
are signed is still open: the session never left 10.7 kW.
What is fixed and what moves is in
[wallbox registers](../sources/wallbox-registers-summary.md).
RS485 at unit 248 is reported by others and never measured here; see
[the open query](../queries/does-a-wallbox-answer-unit-248-on-rs485.md).

The [control test's dry run](../sources/gerd-wallbox-dry-run-2026-11-06-summary.md) on
2026-11-06, with no car: the output current setting (holding 21203) read **0**, against 160
and 151 while charging, and input 21322 read 161 beside it, so 21322 is not the setting
echoed. Nothing is written to a wallbox outside a control test with leave.
