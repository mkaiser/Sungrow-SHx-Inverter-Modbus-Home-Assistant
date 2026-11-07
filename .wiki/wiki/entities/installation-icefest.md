---
type: entity
title: Installation icefest
tags: [installation, icefest]
created: '2026-11-06'
---

# Installation icefest

An [SH6.0RS](device-sh-rs.md) on [P066](firmware-sunstone-h-b000-v001-p066.md) with an
[SBR192](device-sbr-battery.md), read two ways on 2026-11-06, ten minutes apart, both from Home
Assistant's diagnostics with the capability test and a restart: through a
[WiNet-S](device-winet-s.md) on Ethernet, and over the inverter's RS485 port through a Waveshare
converter.

- **13074 stores a written word as handed** on P066, on both paths.
- **The forced-charging window cannot be written**: its days word, holding 33209, refuses with
  0x04 on both paths.
- **The dongle run's code 5 could not be settled through the dongle**: the unrestored word was the
  refused one, and a refusal there is not proof it stayed put. The RS485 run found it holding its
  original value, so the house was not left changed.
- **RS485 reads as "direct"**: register 6100 answers on it, so transport detection cannot tell it
  from the LAN port.
- The first SBR192 read on a direct link.

## Diagnoses

- [SH6.0RS, B000.V001.P066, icefest, a WiNet-S on Ethernet](../sources/sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-winet-lan-summary.md)
- [SH6.0RS, B000.V001.P066, icefest, RS485 through a Waveshare converter](../sources/sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-meter-direct-lan-summary.md)
