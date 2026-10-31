---
type: entity
title: iHomeManager
tags: [ihomemanager, unmeasured]
created: '2026-10-29'
---

# iHomeManager

Sungrow's energy manager. **Never measured here.**

- **Where it answers:** slave 247, on port **502, 503 or 504**, and **each
  port takes one TCP connection**, so a port another client holds looks
  closed (Sungrow's V1.0.2 document, table 2, as
  `src/sungrow_modbus/ihomemanager/registers.py` records it).
- **Its Modbus TCP is off until opened** in the iSolarCloud app:
  *iHomeManager settings → Forwarding channel settings*, port 502, 503 or 504,
  SSL off (Sungrow's *iHomeManager Modbus Transfer User Guide*, 2025).
- **Port 516 is not an iHomeManager's**: it is a [WiNet-S](device-winet-s.md)'s
  or a [wallbox](device-wallbox.md)'s Modbus over TLS.
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
- **How it is read:** `sungrow_survey.py` reads it with
  `device-survey/scripts/python/ihomemanager_direct.py`, into a document of
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
as a poller of the inverter, but it was not read: a Home Assistant survey reads
the one endpoint the entry is configured against. Next step:
[survey one](../queries/what-does-an-ihomemanager-answer.md).
