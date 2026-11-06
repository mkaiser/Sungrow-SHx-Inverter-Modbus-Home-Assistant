# Cross-reference: evcc

This project's registers, compared with every Sungrow driver and template in
[evcc-io/evcc](https://github.com/evcc-io/evcc), read at commit `bcea759cd9`
(2026-11-05), together with the evcc issues and discussions that changed
them. evcc writes **protocol** addresses; every number below is a register
number, one above, as in the rest of this repository.

## What was read, and under what licence

| File | Device | Licence |
| --- | --- | --- |
| `templates/definition/meter/sungrow-hybrid.yaml` | SH hybrid: grid, PV, battery, battery control | MIT, as evcc's repository |
| `templates/definition/meter/sungrow-inverter.yaml` | SG string inverter: grid, PV, curtailment | MIT |
| `templates/definition/meter/sungrow-ihm.yaml` | iHomeManager: grid, PV, battery, curtailment | MIT |
| `templates/definition/meter/sungrow-meter.yaml` | DTSU666 read directly over RS485, unit 254 | MIT; not a device this project reads |
| `templates/definition/charger/sungrow.yaml` and `charger/sungrow.go` | AC011E-01, AC22E-01 | **The Go driver is not MIT.** Its header: "This module is NOT covered by the MIT license. All rights reserved." Used here for which register means what, never copied |
| `templates/definition/charger/ocpp-sungrow.yaml` | AC011E over OCPP | MIT; no registers |

## The hybrid

Every one of the template's 25 registers is in this project's map with the
same meaning, type and scale: 5001 nominal output power (0.1 kW), 5628 BDC
rated power, 5639 high-precision battery capacity (0.01 kWh), 5017 total DC
power, 5603-5608 meter phase power, 5741-5746 meter phase voltage and current
(the latter only on the inverter's own LAN port, which the template states as
this project does), 13003, 13010, 13027, 13037, 13041, 13046, 13023, and the
controls 13050 EMS mode, 13051 charge/discharge command, 13052 forced power
in watts, 33047/33048 maximum charge and discharge power in 0.01 kW.

**One difference, of design.** evcc takes battery power from 13022, which is
unsigned, and signs it from bit 1 of 13001 (or a negative battery current at
13021). This project reads the signed 5214, as the YAML package does, and
does not map 13021 or 13022.

## The SG string inverter

The template's 5083 meter power, 5099 import energy, 5031 total active power,
5144 PV generation and the power limitation pair agree with this project's
map: 5007 switch 0xAA on and 0x55 off, 5008 the setting in 0.1 %.

**A behaviour this project had not recorded**, in the template's comment:
while the limitation is off, the inverter resets 5008 to its 110 % default,
so the switch must be written before the setting, or the setting is
discarded on the way back.

## The iHomeManager

The template uses 8145, 8155, 8157, 8161, 8163, 8176, 8178, 8559-8564, 8028
and 8031, each where Sungrow's V1.0.2 document puts it. Two things it does
differently were measured on real units, by evcc users, and they are the
first readings of an iHomeManager this project has:

1. **8028, feed-in limitation, reads 0x55 off and 0xAA on.** The V1.0.2
   document says 0 off and 1 on. Measured on firmware
   `iHomeManager-SV930.001.00.P015`, build B003: with the limitation off,
   8028 = 0x55 and 8031 = 0; with 8028 = 0xAA and 8031 = 200 (20 %), the
   plant's feed-in fell to about 4 kW, across two SH10RT-20 behind it
   ([evcc#33775](https://github.com/evcc-io/evcc/issues/33775),
   [evcc#33776](https://github.com/evcc-io/evcc/pull/33776)).
2. **Phase-to-neutral voltages at input 4358, 4360 and 4362**, 0.1 V, which
   no document lists. A raw read of the block gave 0, 2247, 0, 2244, 0, 2252
   for registers 4357-4362, and iSolarCloud showed the same voltages
   ([evcc#34169](https://github.com/evcc-io/evcc/issues/34169), following
   [evcc#27983](https://github.com/evcc-io/evcc/issues/27983)). The zero
   between each is consistent with a U32 sent low word first. The
   documented 8555-8557 hold the **line-to-line** voltages on a three-phase
   site ([evcc#27985](https://github.com/evcc-io/evcc/pull/27985)), which is
   what the document's output type (8554) says they would.

## The wallbox

All 16 registers of the Go driver are in this project's map with the same
meaning. Input: 21225 phase count, 21268 remote control status, 21270 actual
phase mode, 21300 lifetime energy (U32, low word first), 21302-21307 phase
voltage and current, 21308 power, 21310 session energy, 21314 start mode,
21315 power request, 21316 power control allowed, 21317 charging status
(codes 1-9, the same meanings). Holding: 21203 output current, 21204 phase
mode, 21211 availability, 21212 start/stop.

- **21263 (input)**: the driver reads it as a work mode, 0 network, 2 plug
  and play, 6 EMS, and only prints it in its diagnosis. This project measured
  320 there, a rated current of 32.0 A; the disagreement was already known
  from the AC011E project and ha-modbus-manager.
- **21203's scale is 0.1 A in the driver's code.** Its comment says 0.01 A,
  but it writes ten times the current in amperes, starting from 60 (6 A).
  That agrees with this project's reading against discussion #571's 0.01 A.
- **Not an independent source.** The driver was written from
  Louisbertelsmann's YAML
  ([evcc#11742](https://github.com/evcc-io/evcc/issues/11742),
  [evcc#13247](https://github.com/evcc-io/evcc/pull/13247), "UNTESTED!"), so
  where they agree that is one source, not two.
- **Sixty seconds without traffic and the wallbox drops the connection** and
  applies its fallback current. The driver reads the charging status every
  30 s for that reason
  ([evcc#27388](https://github.com/evcc-io/evcc/pull/27388)).
- **Phase switching is done with charging disabled**
  ([evcc#23716](https://github.com/evcc-io/evcc/pull/23716)).
- **Sungrow's own document exists** as `AC011E-01_Modbus_Protocol_V1.0.16_EN_Confidential.pdf`,
  sent to evcc's maintainer and marked confidential
  ([discussion #7104](https://github.com/evcc-io/evcc/discussions/7104)).
  It is not public, and nothing here comes from it.
- From [discussion #20739](https://github.com/evcc-io/evcc/discussions/20739),
  as reported and not measured here: an iHomeManager talks to the wallbox
  over its port 516 with TLS, so a wallbox with an iHomeManager is not free
  for another client there; and the installer view of the iEnergyCharge app
  once offered to switch SSL off on 516, a setting the same user could no
  longer find later.
