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

From [fwitten and mkaiser](../sources/fwitten-cluster-mirror-2026-11-24-summary.md) over the cable and
[a second round](../sources/cluster-mode-33500-reads-2026-11-24-summary.md): **the WiNet-S reads the same** at fwitten (both) and gerd.

- **33500 tells a cluster member from a lone inverter**; 33501 and 33502 alone do not, since a lone
  inverter reads the master's values.
- **33501 gives the role** once 33500 is 0xAA.

Not known: what another firmware (swo14's 01011.95.03 above all), an SH-RS or an SH-T answers. A
refusal or a 0 must not read as "not a cluster" ([a failed read is not a refusal](../concepts/failed-read-is-not-refusal.md)).
