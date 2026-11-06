---
type: source
title: hybrid-protocol-v1-1-17.md
source_path: raw/hybrid-protocol-v1-1-17.md
ingested: '2026-11-06'
created: '2026-11-06'
tags: [specification, hybrid, device-types, naming]
---

# Sungrow's hybrid protocol V1.1.17

`raw/hybrid-protocol-v1-1-17.md` records Sungrow's *Communication Protocol of
Residential and Small Industrial Hybrid Inverter* V1.1.17 (2026-09-30), the
newest version found and the first of the line this project read in full
since V1.1.11. The PDF is not redistributable and stays local; where it
was found is on [where Sungrow's documents are](../queries/where-are-sungrows-documents.md).

| Fact | Value |
| --- | --- |
| Registers added or removed since V1.1.11 | none |
| New device types since V1.1.11 | MG7.5RL, MG12RL, SH5/6/8/10RL, SH110/125CX, SH50/80/100CX, SH3/3.6/4RL, MG10/12/15/20/25TL |
| Only types this project lacked | MG10/12/15/20/25TL, 0xE53-0xE57: now `Family.TL`, apart from MG*RL |
| Appendices 2-4 (states, alarms, fault codes) | the same as V1.1.11's, word for word |
| 4990-4999 | listed: the serial number, UTF-8 |
| 2582, 2597, 2613, 2629, 5741-5746, 31211, 31213, 33149, 33150 | **not listed** |
| 13017 | only 0xAA; works grid-connected, **not off-grid** |
| 13088 | the ratio form of 13074; the ratio wins when both are set |
| Unread here, listed | 31222, 13080, 13043, 13015/13016, 33042, 33148, 33274 |

- **It answers [what V1.1.16 calls the unlisted registers](../queries/what-does-v1-1-16-call-the-unlisted-registers.md):**
  V1.1.16 differs from V1.1.17 in device types only, so what V1.1.17 omits,
  V1.1.16 omits.
- **It corrects `doc/architecture.md`'s `DEVICE_TYPES` claim**: Appendix 1
  gained five types, and the table now holds them
  (`src/sungrow_modbus/const.py`, `tests/test_device_types.py`).
