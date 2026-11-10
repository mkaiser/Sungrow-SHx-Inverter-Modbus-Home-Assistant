---
type: entity
title: iHomeManager
tags: [ihomemanager]
created: '2026-10-29'
---

# iHomeManager

Sungrow's energy manager. **Measured once here**, from Home Assistant, on port 503, firmware
`iHomeManager-SV930.001.00.P020`: all 56 mapped fields answered
([the diagnosis](../sources/ihomemanager-ihomemanager-sv930-001-00-p020-anonymous-port503-summary.md)). evcc's users have read a few
registers on theirs ([evcc cross-reference](../sources/cross-reference-evcc-summary.md)).

- **Measured here:** 8028 reads 0x55 for off; 8555-8557 are line to line (416-419 V) and
  4358-4362 phase to neutral (240-241 V); the protocol number at 8001-8002 is "AW0" read low
  word first, which the map, reading it high word first, publishes as "0"; 8554 reads 0, which the
  map calls single phase, on a three-phase site; and inputs 8645-8650 hold a masked text whose
  stand-in matches an inverter's, so the undocumented range carries a managed device's serial
  ([the diagnosis](../sources/ihomemanager-ihomemanager-sv930-001-00-p020-anonymous-port503-summary.md)).


- **Where it answers:** slave 247, on port **502, 503 or 504**, and **each
  port takes one TCP connection**, so a port another client holds looks
  closed (Sungrow's V1.0.2 document, table 2, as
  `src/sungrow_modbus/ihomemanager/registers.py` records it).
- **Its Modbus TCP is off until opened** in the iSolarCloud app:
  *iHomeManager settings → Forwarding channel settings*, port 502, 503 or 504,
  SSL off (Sungrow's *iHomeManager Modbus Transfer User Guide*, 2025).
- **Port 516 is not an iHomeManager's**: it is a [WiNet-S](device-winet-s.md)'s
  or a [wallbox](device-wallbox.md)'s Modbus over TLS. An iHomeManager is a *client* there: it
  drives the wallbox over 516, so that wallbox is not free for another client at its own
  address (reported in evcc's discussion #20739, [evcc cross-reference](../sources/cross-reference-evcc-summary.md)).
- **Where a unit contradicts the document** (both from the
  [evcc cross-reference](../sources/cross-reference-evcc-summary.md)):
  - **Holding 8028, feed-in limitation, reads 0x55 off and 0xAA on**, where V1.0.2 says 0 and 1.
    On firmware `iHomeManager-SV930.001.00.P015`, 0xAA with 8031 at 20 % cut the feed-in of
    two SH10RT-20. The map decodes both pairs.
  - **Phase-to-neutral voltages are at input 4358, 4360 and 4362** (0.1 V, a 0 between each),
    which no document lists; 8555-8557 are line to line on a three-phase site. Read as
    `phase_voltages`, held `field`.
- **No serial number** in either revision of Sungrow's document, nor in the
  MIT template. What it says about itself is a type code (`0x072A`), the
  protocol number ("AW0"), the protocol version and its application software
  version.
- **What it is not:** a gateway. It forwards system energy dispatch data,
  not the devices behind it, so its inverters are separate endpoints.
- **How it is noticed:** `identify()` probes input 8000 on unit 247, and
  calls it an iHomeManager **only for type code 0x072A**. A Sungrow Logger
  answers a type code there too, with its device counts at 8005-8006, by the
  map posted in discussion #262; any other code is reported by its number
  and not read (`discovery.UNIT_247_DEVICE`).
- **In Home Assistant:** the network search asks unit 247 on every open
  port 502-505 and offers an iHomeManager as an entry of its own that only
  runs its diagnosis: no entities measure it. *Diagnosis: start* builds the
  same document as the terminal (`custom_components/sungrow_modbus/device_diagnosis.py`,
  from the library's `ihomemanager` package). Identified by kind, host and
  port, since it documents no serial. Run on a real unit once
  ([the diagnosis](../sources/ihomemanager-ihomemanager-sv930-001-00-p020-anonymous-port503-summary.md)).
- **How it is read:** `sungrow_diagnosis.py` reads it with
  `device-diagnosis/scripts/python/ihomemanager_direct.py`, into a document of
  its own (`"document": "ihomemanager"`): every register the document defines,
  then the gaps between them. Any text in a gap is masked and published only
  as a stand-in, since an undocumented serial would sit there; see
  [serial anonymization](../concepts/serial-anonymization.md). It reaches
  contributors with the first release that has `sungrow_modbus.ihomemanager`.
- **The map:** Sungrow's V1.0.2 document, in
  `src/sungrow_modbus/ihomemanager/registers.py`, each field marked with its
  source; compared with the MIT template in the
  [cross-reference](../sources/cross-reference-modbus-manager-summary.md).

[ra1k-0](installation-ra1k-0.md) reports an iHomeManager installed, and names it
as a poller of the inverter. What is still open about the registers:
[what an iHomeManager answers](../queries/what-does-an-ihomemanager-answer.md).
