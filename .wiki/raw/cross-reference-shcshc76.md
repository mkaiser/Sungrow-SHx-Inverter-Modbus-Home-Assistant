# Cross-reference: shcshc76/sungrow and its fork Eisbaeeer/sungrow

An ioBroker user's register tables for an SH-RT and an AC011E-01 wallbox,
read on 2026-11-06 at `shcshc76/sungrow` (created 2024-02-21, last pushed
2025-04-28). `Eisbaeeer/sungrow` is a fork of it and its wallbox files are
byte for byte the same; the ioBroker thread "Sungrow Wallbox AC011E-01
erfolgreich mit Modbus eingebunden" (forum.iobroker.net, topic 73087) links
both.

**Neither repository has a licence**, so all rights stay with the authors:
read for which register means what, never copied.

## How to read its addresses

The files are tables for ioBroker's modbus adapter, whose `_address` column
is the **protocol** address. Every number below is a register number, one
above the file's.

## AC011E01_Input-Register.tsv

| Register | The file's name and remark | This project (`src/sungrow_modbus/wallbox/registers.py`) |
| --- | --- | --- |
| 21201 | serial number, a string | the serial, 21201-21206, masked |
| 21262 | rated voltage, V | the same |
| 21263 | working mode: 0 network, 2 plug and play, 6 EMS | **rated current, 0.1 A**, read 320 here; evcc and KevinD987's map also read it as a work mode |
| 21267 | "holding register changed" | a counter, meaning open |
| 21268 | charger status: 0 disable, 1 enable | remote control status, named elsewhere |
| 21300 | total energy, 32-bit, low word first | the same, in Wh |
| 21302-21307 | phase voltages and currents R, S, T, 0.1 V and 0.1 A | the same |
| 21308 | charging power, W, 32-bit | the same |
| 21310 | session energy, 32-bit | the same, in Wh |
| 21314 | start mode: 1 EMS, 2 card | the same |
| 21316 | power regulation: 0 forbidden, 1 allowed | the same |
| 21317 | charging status, codes 1-9 | the same nine codes |
| 21318, 21320 | session start and end, Unix time | the same; this project reads them as local time |

## AC011E01_Holding-Register.tsv

| Register | The file's name and remark | This project |
| --- | --- | --- |
| 21201 | "total energy", 32-bit | not mapped; the file's input table has the same name at 21300, so this row is likely a copy |
| 21203 | output current, 0.1 A, 6-63 A | the same |
| 21204 | phase switch: 0 three phase, 1 single phase | the same |
| 21211 | charger enable: 0 disable, 1 enable | the same |
| 21212 | start/stop: 0 start, 1 stop | the same polarity |
| 21225-21230 | year, month, day, hour, minute, second | the same clock, measured here |
| 21231 | bus address, default 248 | the configured unit id; 248 is what answers over TLS here |
| 21232 | energy per km | mileage per kWh, 0.1 km/kWh |

## README.md

- The wallbox is reached **only through the WiNet-S**, not through the
  inverter's own LAN port; the inverter is best read on its LAN port, on a
  second connection.
- "Der Abfragezyklus der Wallbox sollte nicht schneller als 10 Sekunden
  sein. Fragt ihr schneller ab, geht der Winet-S auf Störung." Polling the
  wallbox faster than every 10 s puts the WiNet-S into a fault state; the
  inverter on its LAN port takes 500 ms or less.
- Each connection needs its "Forwarding Modbus ID": the unit of the device
  read through it.
