---
type: query
title: "Where are Sungrow's documents?"
tags: [specification, logger, ihomemanager, wallbox, answered]
created: '2026-11-06'
query: "Where can each Sungrow protocol document and community register map be read, and which searches came up empty?"
results_count: 25
---

# Where are Sungrow's documents?

**Answered for every device this project reads, as searched on 2026-11-05
and 2026-11-06.** Look here before searching again. Copies are kept in the
maintainer's gitignored `tmp/manuals/`, never committed: the iHomeManager
protocol forbids redistribution, and the rest are Sungrow's.

## Protocol documents

| Document | Where | How it was read |
| --- | --- | --- |
| Logger protocol AW0 **1.0.2.9** (Logger1000/3000/4000) | an installer's open file server: `hg-technical.herholdts.co.za/Technical/05. Sungrow/Technical/Sungrow Modbus Table.pdf`. The folder was renamed once (`05 Sungrow` to `05. Sungrow`): list `/Technical/` if the path breaks | PDF; [summary](../sources/logger-communication-protocol-summary.md) |
| Logger protocol AW0 1.0.2.5 | pdfcoffee.com, "TI - 20210113 - Logger - Communication Protocol - V1.0.2.5 - EN" | the page's text layer; its download is behind a captcha |
| Logger protocol 1.0.2.7 | Scribd (login), Studocu (garbled), an sps-forum.de attachment (403 to scripts) | **not read**, and not needed: 1.0.2.5 and 1.0.2.9 bracket it |
| *Logger Modbus Protocol Data Forwarding Guide* | **found nowhere**; the Logger manuals cover it | — |
| iHomeManager protocol V1.0.1 and *Modbus Transfer User Guide* | GitHub attachments `files/22764216` and `files/22764134` under `github.com/user-attachments/files/`; also in Jam3s97/sungrow_ihomemanager's `Modbus Information` folder | PDF |
| iHomeManager protocol V1.0.2 (2026-01-21, marked test) | GitHub attachment `files/26009392`, `iHM.Communication.Protocol-20260121-test.1.pdf`; also TCzerny/ha-modbus-manager's `docs/` folder | PDF; no redistribution |
| Hybrid protocol V1.1.9 | openHAB's forum upload (community-openhab-org S3); bohdan-s/Sungrow-Inverter's `Modbus Information` folder | PDF |
| SG protocol V1.1.53 | shop.kpenergy.fi product sheets | PDF |
| SG protocol V1.1.2 | photovoltaicsolar.in, `Sungrow_Manual/Modbus RS485 RTU Protocol.pdf` | PDF |
| **Wallbox protocol** `AC011E-01_Modbus_Protocol_V1.0.16_EN_Confidential.pdf` | **not public**: named in evcc discussion #7104 | owners report Sungrow support refusing it; the wallbox's names stay this project's own |

## Manuals with facts the protocols lack

| Document | Where | What it adds |
| --- | --- | --- |
| Logger1000A/B user manual Ver129-202609 | info-support.sungrowpower.com (`/cms/...` path; search the site for "Logger1000A_B-UEN") | port 516 with TLS by default, forwarding addresses, 10 s cadence |
| Logger3000 user manual Ver20-202002 | ManualsLib, manual 1904222 | forwarding addresses |
| Logger1000 quick guides TD_202002 V1.2 and TD_202006 V1.4 | service.sungrowpower.com.au, `files/Web_Files/FAQ/` | commissioning only |
| Third-party meter via Logger1000, TI_20201127 | sungrowpowerservice.com, `Files/KnowledgeBase/Monitoring/TechDoc/` | meter point tables |
| COM100D/E user manual Ver11 | info-support.sungrowpower.com, linked from discussion #262 | **no registers**: a cabinet around a Logger |
| iHomeManager user manual (German) | ger.sungrowpower.com | installation only |

## Community register maps

| Map | Licence | Status |
| --- | --- | --- |
| evcc's Sungrow templates; `charger/sungrow.go` | MIT; **the Go driver reserves all rights** | read: [evcc](../sources/cross-reference-evcc-summary.md) |
| TCzerny/ha-modbus-manager | MIT | read: [ha-modbus-manager](../sources/cross-reference-modbus-manager-summary.md) |
| KevinD987/sungrow-ac011e | MIT | read, in `doc/wallbox_registers.md` |
| Louisbertelsmann/Sungrow-Wallbox-Modbus-HomeAssistant | none; used with permission | read, in `doc/wallbox_registers.md` |
| shcshc76/sungrow and its fork Eisbaeeer/sungrow | none | read: [shcshc76](../sources/cross-reference-shcshc76-summary.md) |
| Voyanti/ha-sungrow (Logger module) | GPL-3.0 | read for what exists; superseded by the Logger protocol |
| RafAustralia/Sungrow-Logger1000a-Modbus | none | read; agrees with the Logger protocol |
| Jam3s97/sungrow_ihomemanager | GPL-3.0 | read for what exists |
| hjsmoostrong-beep/sungrow-modbus-analysis | MIT | a traffic capture of a plant behind a Logger; it calls unit 247 a weather station, but polls the Logger's own 8061-8085 |

## Searches that found nothing

- GitHub code search for the Logger protocol's title, "Sub Inverter Array",
  `Logger3000`: no hits beyond the maps above. The `gh search code` limit is
  10 requests a minute.
- No public copy of any wallbox protocol, on any site.
- No Wayback Machine copy of the Logger protocol.
