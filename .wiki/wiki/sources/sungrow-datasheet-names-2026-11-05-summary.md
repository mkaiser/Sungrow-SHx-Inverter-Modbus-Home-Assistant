---
type: source
title: sungrow-datasheet-names-2026-11-05.md
source_path: raw/sungrow-datasheet-names-2026-11-05.md
ingested: '2026-11-05'
created: '2026-11-05'
tags: [specification, naming, datasheet, registers]
---

# Sungrow's register names, from five protocol documents

`.wiki/raw/sungrow-datasheet-names-2026-11-05.md`: the register names in Sungrow's hybrid
protocol V1.1.2, V1.1.5, V1.1.9 and V1.1.11 and the SG's V1.1.58, matched to the registers the
integration reads. **The documents are not in this repository and are not distributed**; the notes
record names and the few statements naming depends on. The names by register are in
`scripts/generate/tables/datasheet_names.json`, and `doc/entity_names.md` shows each beside the
YAML, English and German names.

| Claim | Evidence | Status |
| --- | --- | --- |
| V1.1.11 names 123 of the 138 hybrid registers the entities read; V1.1.58 names all 57 SG ones | text extraction, matched by space and register | the 15 unnamed: [the open question](../queries/what-does-v1-1-16-call-the-unlisted-registers.md) |
| The limit family says *Feed-in* from V1.1.9 (5622/5623, 13074, 13087, 13088), *Export* in V1.1.2 and V1.1.5 | the four hybrid documents | the integration names it *Feed-in limit* |
| Measured flows say *export* in every version (13010, 13045/13046, 13006) | the same | the integration keeps *Export power*, *exported energy* |
| Holding 13075 is *Off-grid option*; every other backup register says *Backup* | V1.1.11 | the integration says *Backup mode* |
| Holding 13017 *Forced Startup Under Low SOC Standby* is a 0xAA command that wakes an inverter in low-SoC standby, grid-connected only | V1.1.11 note 1 | see [register 13017](../entities/register-13017.md) |
| Input 13001's bits are Appendix 3's *Power Flow State* | V1.1.11 | the integration's power flow binary sensors decode them |
| Input 5017 *Total DC power* is "Total PV power" | V1.1.11 remark | the integration says *Total PV input power* |
| Nothing says what an active power limit ratio of 0 % does | V1.1.11's power regulation notes | [register 31213](../entities/register-31213.md) answers it from iSolarCloud |
