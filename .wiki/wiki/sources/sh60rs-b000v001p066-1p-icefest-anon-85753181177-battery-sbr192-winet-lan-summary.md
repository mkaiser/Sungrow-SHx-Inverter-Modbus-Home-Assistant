---
type: source
title: sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-winet-lan.json
source_path: ../device-diagnosis/results/inverter/sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-winet-lan.json
ingested: '2026-11-06'
created: '2026-11-06'
tags:
  - diagnosis
  - sh60rs
  - sunstone-h-b000-v001-p066
  - icefest
  - winet_lan
  - capability-test
---

# SH6.0RS, B000.V001.P066, icefest, a WiNet-S on Ethernet

Capability diagnosis of one inverter, read 2026-11-06 around 20:07 UTC from Home Assistant 2026.11.0
with integration 0.1.0a27, issue #786, with the capability test and a restart. **Taken from a
diagnostics download**: the `diagnosis` section of the integration's diagnostics
(`custom_components/sungrow_modbus/diagnostics.py`), committed as it was, under the library's
own name for it. Source: `device-diagnosis/results/inverter/sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-winet-lan.json`.

| | |
| --- | --- |
| Installation | [icefest](../entities/installation-icefest.md) |
| Model | [SH6.0RS](../entities/device-sh-rs.md), type code `0x0D10`, single phase |
| Stand-in serial | `anon-85753181177` |
| Inverter firmware | [`SUNSTONE-H_B000.V001.P066`](../entities/firmware-sunstone-h-b000-v001-p066.md); version 1 `SUNSTONE-H_01011.03.66` |
| Battery firmware | `SBRBCU-S_22011.01.30` |
| Communication module firmware | `WINET-SV200.001.00.P044` |
| Transport (owner) | a WiNet-S on Ethernet |
| Transport (measured) | through a communication module; register 6100 refused |
| Battery | [SBR192](../entities/device-sbr-battery.md), at unit 2 through the dongle |

## What did not answer

Through the dongle: the battery firmware (2628), the sub-controller firmware (2612) and the three
history blocks from 6196, as on every WiNet-S ([WiNet-S](../entities/device-winet-s.md)).

## Contention

Polled by this Home Assistant throughout, coordinators not paused (22 components); no block read
test, which a diagnostics download does not take.

## Capability test

Outcome **5**: one register could not be shown to be back. PV about 230 W, the battery at 3 %.

- [13074](../entities/register-13074.md) **stores a written word as handed** (1:1): the held 5100 W
  written back was accepted, where times ten would be 51000 W, above the 6000 W maximum.
- The forced charge **did as it was told**: 1272 W for 1250 W commanded.
- **The forced-charging window could not be written**: holding 33209, the days word, refused with
  exception 0x04 (`ServerDeviceFailureError`), so the window was never set.
- **The restore of that word was refused too, five times**, and through a WiNet-S the run cannot
  read a register back (the dongle's cache is stale), so it reported the word as not restored:
  code 5. That is the procedure being right to doubt: a refusal through a dongle is not proof the
  register stayed put (a window write refused with 0x04 through gerd's WiNet-S had landed;
  [the restore](../concepts/capability-test-restore.md)). Here the reading over RS485 ten minutes later
  found it **already holding its original value**
  ([that reading](sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-meter-direct-lan-summary.md)),
  so the house was not left changed.
- Readbacks through the dongle are its cache: the maximum SoC and the charge and discharge maxima
  "kept the old value" here and matched over RS485.
- A restart: 2.0 s to stop, 163 s to run again, generating 17 s after that, settings intact.
- Not checked: the PV cut (PV under 500 W), the minimum and backup SoC (the battery too close to
  them).
