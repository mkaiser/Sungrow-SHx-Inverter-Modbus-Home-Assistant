# Sungrow's Logger documents

What Sungrow's own documents say about talking Modbus to a Logger1000,
Logger3000 or Logger4000, read on 2026-11-06. Every number is a **register
number**, as the documents print them; the protocol address is one lower,
which the documents say themselves ("communication address = protocol
address - 1"). The documents stay in the maintainer's `tmp/manuals/`, which
git ignores; this is the record of what they say.

## The documents

| Document | Where it was read | Notes |
| --- | --- | --- |
| *Logger Communication Protocol* AW0 **1.0.2.9**, revised 2022-06-14 by Song Zhenfei, 7 pages, "Confidentiality: Public" | an installer's public file server, `hg-technical.herholdts.co.za`, `Technical/05. Sungrow/Technical/Sungrow Modbus Table.pdf` (the folder is also mirrored under `MODBUS PROTO/`) | For the Logger1000, Logger3000 and Logger4000. The revision note: "added the content, modified the measuring point name, and added remarks" |
| *Logger Communication Protocol* AW0 **1.0.2.5**, TI_20210113, "Classification: Public" | the text layer of pdfcoffee.com's page for it; the PDF itself is behind a captcha there | For the Logger1000 and Logger3000 |
| *Logger Communication Protocol* 1.0.2.7, TI_20211201 | not read: Scribd (login), Studocu (garbled), and an sps-forum.de attachment that refuses automated fetches | Between the two above |
| *User Manual Data Logger Logger1000A/Logger1000B*, Logger1000A_B-UEN-Ver129-202609, 171 pages | info-support.sungrowpower.com | Ports, forwarding addresses, cadence |
| *Logger3000 User Manual*, Logger3000-UEN-Ver20-202002 | ManualsLib's printout | Forwarding addresses |
| *COM100D/COM100E Smart Communication Box User Manual*, Ver11-202201 | info-support.sungrowpower.com, linked from discussion #262 | A cabinet around a Logger; no registers |
| *Logger Modbus Protocol Data Forwarding Guide* | not found anywhere | 1.0.2.5 and 1.0.2.9 refer to it; the manuals above cover the same ground |

## Communication

- The Logger itself is **unit 247**; RS485 at 247 cannot be changed, 9600
  8N1, RTU. A device behind it answers at the **forwarding address** the
  Logger gives it.
- Ethernet, port 502 in the protocol: Logger1000 at 12.12.12.12; Logger3000
  ETH1 12.12.12.12, ETH2 13.13.13.13; a new Logger4000 adds ETH5 14.14.14.14.
- Input registers: function code 4. Holding registers: 3 to read, 6 and 16
  to write. CRC16 for RTU.
- **Word order differs by width.** U16/S16 big-endian. U32/S32 send the low
  word first (the document's own example writes 0x0000015E as `01 5E 00
  00`). U64/S64 send the high word first.
- **Unsupported registers** answer all ones when unsigned (0xFFFF,
  0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF) and the largest positive value when signed
  (0x7FFF, 0x7FFFFFFF, 0x7FFFFFFFFFFFFFFF); a reserved register cannot be read.
- **A command to broadcast unit 0 is passed straight through to the
  inverters.** A holding register supports one function only.

## Input registers

| Register | Type | Scale | Unit | Meaning | Models, remarks |
| --- | --- | --- | --- | --- | --- |
| 8000 | U16 | 1 | | Device type code | 0x0705 Logger3000, 0x0710 Logger1000, 0x0718 Logger4000 (1.0.2.9 adds the last) |
| 8001 | U32 | 1 | | Protocol number | |
| 8003 | U32 | 1 | | Protocol version | |
| 8005 | U16 | 1 | | Devices connected | 1.0.2.9: all devices, third-party included |
| 8006 | U16 | 1 | | Devices in fault | 1.0.2.9: inverters reporting a fault, third-party excluded |
| 8015, 8017 | | | | Reserved | |
| 8021 | U32 | 1 | | Digital input state, one bit per input | 8 bits on a Logger1000, 16 on a Logger3000 and Logger4000; 1.0.2.9: 0 NO, 1 NC |
| 8023, 8025 | | | | Reserved | |
| 8027, 8028 | S16 | 0.1 | °C | PT100 inputs 1 and 2 | Logger3000 (1.0.2.9: and Logger4000) |
| 8029 | S16 | 0.01 | V | Analogue input 1, voltage | |
| 8030 | S16 | 0.01 | mA | Analogue input 1, current | |
| 8031 | S16 | 0.01 | V | Analogue input 2, voltage | |
| 8032 | S16 | 0.01 | mA | Analogue input 2, current | |
| 8033, 8034 | S16 | | | Analogue inputs 3 and 4, voltage | 0.01 V on a Logger1000, 0.01 mV on a Logger3000 |
| 8035, 8036 | S16 | 0.01 | mA | Analogue inputs 3 and 4, current | |
| 8037 | | | | Reserved | |
| 8054, 8056 | S32 | 0.0001 | ° | Longitude and latitude in 1.0.2.5; **reserved in 1.0.2.9** | |
| 8058 | U16 | 1 | kW | Highest nominal active power of the array | |
| 8059 | U16 | 1 | kW | Lowest nominal active power of the array | |
| 8060 | U16 | 1 | kvar | Highest nominal reactive power | |
| 8061 | S16 | 1 | kvar | Lowest nominal reactive power | |
| 8066 | U16 | 1 | kW | Preset total active power of the inverters | |
| 8067 | S16 | 1 | kvar | Preset total reactive power | |
| 8068 | U16 | | | Array switch state: 0 off, 1 on | |
| 8069 | U16 | | | Unlatch state: 0 latched, 1 unlatched | 1.0.2.9: unlatched by default; latched, remote dispatch is not answered |
| 8070 | U64 | 1 | W | Total active power of the array | |
| 8074 | U32 | 0.1 | kWh | Daily yield | |
| 8076 | S64 | 1 | var | Total reactive power | |
| 8080 | U64 | 0.1 | kWh | Total yield | |
| 8084 | U32 | 0.1 | kW | Lowest adjustable active power | |
| 8086 | U32 | 0.1 | kW | Highest adjustable active power | |
| 8088 | S32 | 0.1 | kvar | Lowest adjustable reactive power | |
| 8090 | S32 | 0.1 | kvar | Highest adjustable reactive power | |
| 8092 | U32 | 0.1 | kVar as printed | Rated (1.0.2.5: nominal) active power | the unit is a misprint for kW, in both versions |
| 8094 | U32 | 0.1 | kvar | Rated reactive power | |
| 8096 | U16 | 1 | | Inverters connected to the grid | |
| 8097 | U16 | 1 | | Inverters off grid | |
| 8098 | U64 | 0.1 | kWh | Monthly yield | |
| 8102 | U64 | 0.1 | kWh | Annual yield | |
| 8106 | U64 | 1 | VA | Apparent power | |

## Holding registers

| Register | Type | Scale | Unit | Meaning | Remarks |
| --- | --- | --- | --- | --- | --- |
| 8002 | U16 | | | Array on/off: 0 off, 1 on | |
| 8003 | U32 | 0.1 | kW | Active power setpoint for the inverters | |
| 8005 | U32 | 0.1 | % | Active power ratio | |
| 8007 | S32 | 0.1 | kvar | Reactive power setpoint | |
| 8009 | S32 | 0.1 | % | Reactive power ratio | |
| 8011 | S32 | 0.001 | | Power factor | |
| 8013-8016 | U16 | | | Digital outputs 1-4: 0 common to NC closed, 1 common to NO closed | Logger3000; 1.0.2.9: and Logger4000 |
| 8017 | U16 | | | Array active power gradient control: 0xAA on, 0x55 off | **new in 1.0.2.9** |
| 8018 | U16 | 1 | %/min | Active power decline gradient | new in 1.0.2.9; settable only with 8017 on |
| 8019 | U16 | 1 | %/min | Active power rise gradient | new in 1.0.2.9; settable only with 8017 on |
| 8020 | U16 | | | WiFi hotspot: 0xAA on, 0x55 off | new in 1.0.2.9; Logger1000 only |

Both versions' worked examples label the write to 8005 "active power ratio",
and 1.0.2.9's table labels 8003-8009 all "setting active power"; the units
(kW, %, kvar, %) say which is which.

## What the manuals add

- **Port 516, TLS, is the one open by default** on a current Logger1000:
  "502 ... disabled by default, and SSL encryption is inactive; 516 ...
  enabled by default, and SSL encryption is applied", from firmware
  `LOGGER-SV300.001.00.P044`. Ports 502-516 serve Modbus forwarding; 2404 is
  IEC 104, 443 its web interface (Logger1000A/B manual Ver129).
- **The forwarding address** of each device behind it is listed in Device >
  Device List ("Address for Modbus Forwarding", firmware P043 or later);
  the backend reads a device at that unit (Logger1000A/B Ver129, Logger3000
  Ver20). The RS485 addresses it collects from are 1-247 for Sungrow
  inverters and 1-255 for third-party ones, never duplicated.
- **Cadence:** for the holding registers of the devices behind it, "it is
  recommended to set the intervals of northbound collection and control to
  at least 10 s" (Ver129).
- The Logger can run as Modbus TCP server, client, or RTU on a COM port;
  a COM port set to "Forwarding Is Prohibited" answers nothing.
