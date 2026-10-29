## [2026-10-29] initialized | wiki

Wiki knowledge base initialized, in the format of `@llmwiki/core` 0.1.2
(microsoft/llmwiki at `e09126f`).

## [2026-10-29] ingested | 23 fingerprints

Every committed document in `device-fingerprints/inverter/` and
`device-fingerprints/wallbox/`, one source page each, with entity pages for
models, firmware and installations.

## [2026-10-29] ingested | register and reference documents

`doc/legacy_entity_map.json`, `doc/wallbox_registers.md`,
`doc/cross_reference_modbus_manager.md`, and
`github-issues-user-findings.md`, which moved into `raw/`.

## [2026-10-29] ported | AGENTS.md

The device knowledge in the root `AGENTS.md` (the control test, register
13074, reading registers, the WiNet-S, finding devices, migration, serials)
moved into concept and entity pages. `AGENTS.md` keeps the rules and links
here.


## [2026-10-29] renamed | fingerprint -> survey

What earlier entries call a fingerprint is a survey document: it records a
device's capabilities and configuration, and identifies nothing.
`device-fingerprints/` is now `device-survey/`, and the library and
integration modules are `survey_document`. Source pages, tags and links
follow.
