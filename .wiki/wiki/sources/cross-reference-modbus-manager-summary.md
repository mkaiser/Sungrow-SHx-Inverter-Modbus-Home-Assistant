---
type: source
title: cross_reference_modbus_manager.md
source_path: ../doc/cross_reference_modbus_manager.md
ingested: '2026-10-29'
created: '2026-10-29'
tags: [ihomemanager, cross-reference, licences]
---

# Cross-reference: TCzerny/ha-modbus-manager

`doc/cross_reference_modbus_manager.md` compares this project's registers,
one by one, with TCzerny/ha-modbus-manager, read at commit `1faff77`.

- **Its SHx template derives from this repository's YAML package**, so the
  overlap is not independent evidence. Where it diverges, someone usually
  measured something.
- **It is MIT**, so it is the licence-clean source of the
  [iHomeManager](../entities/device-ihomemanager.md)'s 53-register map. The
  only other implementation is GPL-3.0.
- **It ships Sungrow protocol PDFs**, including the hybrid protocol
  V1.1.16 (2026-07-03). This project's audit is pinned to **V1.1.11**, which
  is also the specification behind the control test's hand-typed scales
  ([control test](../concepts/control-test.md)).
