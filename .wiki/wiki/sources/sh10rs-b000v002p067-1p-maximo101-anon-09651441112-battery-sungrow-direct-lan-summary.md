---
type: source
title: sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan.json
source_path: ../device-diagnosis/results/inverter/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan.json
ingested: '2026-11-18'
created: '2026-11-18'
tags:
  - diagnosis
  - sh10rs
  - sunstone-h-b000-v002-p067
  - maximo101
  - winet
---

# SH10RS, B000.V002.P067, Maximo101, through a WiNet-S2, read only

Read 2026-11-17 at 00:52 UTC from a Home Assistant diagnostics download on integration 0.1.0a43
(`command_line`: "home assistant diagnostics", schema 28), with no capability test, while the
house was in its "free energy window": an EV charging and the battery force-charging. Posted to
issue #786. Source:
`device-diagnosis/results/inverter/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan.json`.

**Six downloads, one committed.** Three pairs were posted, each pair two downloads of the same
config entry seconds apart (one from the inverter's device page, one from the battery's; the
integration gives a device page the whole entry's report). All six carry identical capability
probes, features and connection verdicts, and differ only in the power readings. The one committed
is the only one taken after the owner had answered the diagnosis's questions, so it is the only
one that says what the hardware is.

| | |
| --- | --- |
| Installation | [Maximo101](../entities/installation-maximo101.md) |
| Model | [SH10RS](../entities/device-sh-rs.md), type code `0x0D1B`, single phase |
| Stand-in serial | `anon-09651441112` |
| Inverter firmware | [`SUNSTONE-H_B000.V002.P067`](../entities/firmware-sunstone-h-b000-v002-p067.md) |
| ARM / DSP firmware | `ARM_SUNSTONE-H_V11_V01_A` / `MDSP_SUNSTONE-H_V11_V01_A` |
| Version 1 / 2 | `SUNSTONE-H_01011.02.69` / `SUNSTONE-H_03021.01.16` |
| Battery firmware | `SBRBCU-S_22011.01.30` |
| Communication module firmware | `WINET-SV300.001.03.P030` |
| Transport (owner) | the inverter's own LAN port, through a Modbus proxy |
| Transport (measured) | through a communication module; register 6100 **refused** |
| Battery | two [SBR192](../entities/device-sbr-battery.md) at unit 2, 38.6 kWh reported |
| PV | four MPPTs answer: 190.4 V, 353.4 V, 410.4 V and 40.1 V |
| At the time | 3825 W of PV, battery charging 8218 W, SoC 81.8 %, 14.0 kWh generated that day |

## Version 1 moved while the firmware string did not

Version 1 reads `SUNSTONE-H_01011.02.69` and version 2 `SUNSTONE-H_03021.01.16`, where
[brendan](../entities/installation-brendan.md)'s SH10RS, the first P067 read, had `.02.67` and
`.03021.01.15` on 2026-11-05 with the same inverter firmware string
([that reading](sh10rs-b000v002p067-1p-brendan-anon-01362170354-battery-sungrow-winet-lan-summary.md)).
So **both version strings moved under an unchanged P067** in the twelve days between the two
readings, and the inverter firmware string alone does not identify what is running.
[bigz2012](../entities/installation-bigz2012.md)'s SH10RS, read the same day in another part of
the world, carries the same `.02.69` and `.01.16`
([that reading](sh10rs-b000v002p067-1p-bigz2012-anon-10002952285-battery-sungrow-winet-lan-summary.md)),
and that owner watched version 1 move from `.02.67` to `.02.69` on their own machine between
2026-09-08 and 2026-10-18 with the inverter firmware string unchanged. So it is an update, not
two production batches.

## The owner's route and the measurement disagree

The owner answered "the inverter's own LAN port" and "a Modbus proxy: yes". The measurement says
otherwise: a [WiNet-S](../entities/device-winet-s.md) firmware string reads, **6100 is refused**,
and the meter phase registers 5741 and 5744 are refused -- the dongle's signature at every house
measured ([transport detection](../concepts/transport-detection.md)). The proxy in front of it
points at the dongle rather than the inverter's own port. The filename follows the owner's answer,
as every document's does; the table above is what was read.

So this reading does not bear on
[does a Modbus proxy carry register 6100](../queries/does-a-modbus-proxy-carry-6100.md): with a
dongle behind the proxy, 6100 would be refused either way.

## What did not answer

The battery firmware (2628) and sub-controller firmware blocks, refused with **exception 2**, and
the PV generation and export-from-PV history blocks -- as through every WiNet-S. The pack's cells
and modules at unit 2 are refused with `IllegalDataAddressError`, also as usual. 13018 reads the
unavailable value.

## The family table is wrong for this model, and the probe saves it

The diagnostics' capability section names three capabilities the model table calls absent that the
device answered for: `firmware_versions`, `mppt3` and `three_phase`.

- **`firmware_versions`**: 13250 answers here and on every other SH-RS diagnosed, against
  V1.1.16's remark that SH3.0-10RS does not support 13250-13369. The probe keeps it.
- **`mppt3`**: the SH8RS and SH10RS have four MPPTs, and all four answer here. The table excludes
  the RS family from MPPT4 for exactly that reason but keeps it in MPPT3's absent set, which is
  the inconsistency. Nothing is lost, because a probed capability survives the table.
- **`three_phase`**: the dongle answered **0** for phase B and C voltage, which the probe read as
  an answer. Register 5002 says single phase and outranks it
  ([zero means absent](../concepts/zero-means-absent.md)), so three-phase was not resolved. This
  one is the table doing its job.

## One implausible total

`total_battery_charge` reads **429,494,257.3 kWh**, about 2^32 tenths less a small remainder: the
raw double word is near 0xFFFFFFFF, so this is an unsigned reading of something the device meant
as a small negative, not a real total. `total_battery_charge_from_pv` (13,508.0 kWh) and
`total_battery_discharge` (16,638.9 kWh) beside it are ordinary. A `total_increasing` sensor taking
that value once poisons long-term statistics for good, so it is worth a sentinel or a plausibility
check; nothing in the corpus has shown this register do it before.

## Beside the inverter

The house also has an [iHomeManager](../entities/device-ihomemanager.md) and an **AC22E-01**
[wallbox](../entities/device-wallbox.md) at its own address (TLS, port 516, unit 248), added as an
entry of its own -- the preferred way to a wallbox. Three downloads of that entry were posted and
**none carries a diagnosis**: a wallbox-only entry's diagnostics report holds its entry and device
rows and stops there (`custom_components/sungrow_modbus/diagnostics.py`), although the entry has
the *Diagnosis: start* button and a capability test of its own. So a second AC22E-01 reading, which item 5 of
`device-diagnosis/devices-wanted.md` asks for, could not be ingested from what was sent.
