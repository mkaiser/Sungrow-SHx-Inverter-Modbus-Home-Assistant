---
type: source
title: bar12-tls-certificate-2026-11-06.md
source_path: raw/bar12-tls-certificate-2026-11-06.md
ingested: '2026-11-06'
created: '2026-11-06'
tags:
  - winet-s
  - tls
  - bar12
---

# bar12's WiNet-S, its TLS certificate, 2026-11-06

Port 516 of [bar12](../entities/installation-bar12.md)'s [WiNet-S](../entities/device-winet-s.md),
the house confirmed through the same address by its stand-in. Source:
`raw/bar12-tls-certificate-2026-11-06.md`.

- **The same certificate as gerd's**, byte for byte: SHA-256
  `84505e46778f2611df26ed1ad8a4e872945f7eb33e050e617c96a73add005b5b`, serial number 1, valid
  2024-10-24 to 2054-10-17 ([gerd's](gerd-tls-certificate-2026-11-06-summary.md), from his
  WiNet-S and his wallbox).
- Two unrelated houses and two products on one certificate: it is built into the firmware, and its
  private key ships with every unit. Port 516's TLS encrypts the link and authenticates nothing; a
  client gains nothing by verifying it.
