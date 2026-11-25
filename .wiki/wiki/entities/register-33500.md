---
type: entity
title: Register 33500 (cluster mode)
tags: [register, holding, cluster, undocumented]
created: '2026-11-24'
---

# Register 33500 (cluster mode)

A holding register in no Sungrow document here (protocol 33499), named "master/slave mode" in another
project's map, with 33501 the role and 33502 the slave count
(`.wiki/raw/cross-reference-modbus-manager.md`).

| | 33500 | 33501 | 33502 |
| --- | --- | --- | --- |
| [fwitten](installation-fwitten.md)'s master, P023 | 0xAA | 160 | 2 |
| fwitten's slave, P023 | 0xAA | 161 | 2 |
| [mkaiser](installation-mkaiser.md)'s lone SH10RT, P020 | 0x55 | 160 | 2 |
| [gerd](installation-gerd.md)'s lone SH8.0RT-V112, P022 | 0x55 | 160 | 2 |
| [bar12](installation-bar12.md)'s lone SH10RT-20, P023 ([the reads](../sources/cluster-mode-33500-bar12-2026-11-24-summary.md)) | 0x55 | 160 | 2 |
| [firetribe](installation-firetribe.md)'s lone SH6.0RT-V112, P023 ([the diagnosis](../sources/sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-meter-direct-lan-2-summary.md)) | 0x55 | 160 | 2 |

From [fwitten and mkaiser](../sources/fwitten-cluster-mirror-2026-11-24-summary.md) over the cable and
[a second round](../sources/cluster-mode-33500-reads-2026-11-24-summary.md): **the WiNet-S reads the same** at fwitten (both) and gerd.

- **33500 tells a cluster member from a lone inverter**; 33501 and 33502 alone do not, since a lone
  inverter reads the master's values.
- **They are read whole in one request**, over the cable and a WiNet-S ([the reads](../sources/cluster-mode-33500-two-words-2026-11-24-summary.md)).
- **33501 gives the role** once 33500 is 0xAA.

Not known: what another firmware (swo14's 01011.95.03 above all), an SH-RS or an SH-T answers. A
refusal or a 0 must not read as "not a cluster" ([a failed read is not a refusal](../concepts/failed-read-is-not-refusal.md)).
